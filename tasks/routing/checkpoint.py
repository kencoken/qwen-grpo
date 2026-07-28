"""The v1 checkpoint/resume contract (211_f §11, 208_s F1).

v1 boundary: a checkpoint may exist ONLY when the optimizer has
consumed the complete generation buffer — generated_groups ==
consumed_groups. GRPOTrainer does not persist buffered rollout inputs,
so a between-boundary checkpoint cannot be made sound by recording
identities; persisting the buffer is explicitly out of the v1
contract. `GroupAccountant` is the driver-side enforcement point: it
tracks the two counters separately and refuses to authorize a
checkpoint anywhere else.

Resume is fail-closed on ANY identity mismatch. Segment merging
excludes post-checkpoint rows of an aborted segment from the resumed
trajectory (they remain preserved evidence) and refuses missing or
duplicated groups. `isolated_rng` snapshots and restores the python /
numpy / torch (and CUDA, when present) RNG states so checkpoint
evaluations never change subsequent rollout sampling (208_s).
"""

from __future__ import annotations

import contextlib
import random
from typing import Any, Iterator, Mapping

from tasks.conductor.types import InfrastructureError

from .charter import content_sha256

CHECKPOINT_SCHEMA = "routing-dev-checkpoint-v1"

# Every identity a checkpoint binds and a resume re-verifies.
IDENTITY_KEYS = (
    "routing_source_sha256", "environment_manifest_sha256",
    "config_sha256", "prompt_sha256", "training_cohort_sha256",
    "renderer_schedule_sha256", "surface_manifest_sha256",
    "worker_pool_fingerprint", "cache_identity", "seed",
)
_COUNTER_KEYS = ("generated_groups", "consumed_groups",
                 "optimizer_updates", "sampled_completions")
_RNG_KEYS = ("python", "numpy", "torch_cpu", "torch_cuda")


class GroupAccountant:
    """Separate generated / optimizer-consumed group counters with the
    v1 checkpoint boundary enforced at authorization time."""

    def __init__(self) -> None:
        self.generated_groups = 0
        self.consumed_groups = 0
        self.optimizer_updates = 0
        self.sampled_completions = 0

    def record_generation(self, groups: int, completions: int) -> None:
        if groups < 1 or completions < groups:
            raise InfrastructureError(
                f"bad generation record: {groups} groups, "
                f"{completions} completions")
        self.generated_groups += groups
        self.sampled_completions += completions

    def record_update(self, consumed_groups: int) -> None:
        if consumed_groups < 1:
            raise InfrastructureError("an update must consume >= 1 group")
        if self.consumed_groups + consumed_groups > self.generated_groups:
            raise InfrastructureError(
                "optimizer cannot consume groups that were never "
                "generated")
        self.consumed_groups += consumed_groups
        self.optimizer_updates += 1

    def at_v1_boundary(self) -> bool:
        return self.generated_groups == self.consumed_groups

    @classmethod
    def restore(cls, counters: Mapping[str, int]) -> "GroupAccountant":
        """Rebuild from VALIDATED checkpoint counters (the
        `validate_resume` output) — never from raw ints. Restored
        state must itself sit on the v1 boundary."""
        missing = set(_COUNTER_KEYS) - set(counters)
        if missing:
            raise InfrastructureError(
                f"restored counters missing {sorted(missing)}")
        for key in _COUNTER_KEYS:
            value = counters[key]
            if not isinstance(value, int) or isinstance(value, bool) \
                    or value < 0:
                raise InfrastructureError(f"bad counter {key}={value!r}")
        if counters["generated_groups"] != counters["consumed_groups"]:
            raise InfrastructureError(
                "restored counters violate the v1 boundary")
        if counters["sampled_completions"] < counters["generated_groups"]:
            raise InfrastructureError(
                "restored counters are impossible: fewer completions "
                "than groups")
        accountant = cls()
        accountant.generated_groups = counters["generated_groups"]
        accountant.consumed_groups = counters["consumed_groups"]
        accountant.optimizer_updates = counters["optimizer_updates"]
        accountant.sampled_completions = counters["sampled_completions"]
        return accountant

    def authorize_checkpoint(self) -> dict[str, int]:
        """The ONLY way to get counters into a checkpoint record."""
        if not self.at_v1_boundary():
            raise InfrastructureError(
                f"v1 boundary violation: {self.generated_groups} groups "
                f"generated but only {self.consumed_groups} consumed — "
                "checkpoints exist only after the optimizer consumed "
                "the complete generation buffer (211_f §11)")
        return {"generated_groups": self.generated_groups,
                "consumed_groups": self.consumed_groups,
                "optimizer_updates": self.optimizer_updates,
                "sampled_completions": self.sampled_completions}


# The state artifacts every checkpoint bundle MUST persist and hash
# (214_s P1: the record binds the restorable state, not just
# metadata). `scaler` is required whenever mixed precision is active;
# pass it as None only for full-precision runs — the key is always
# present so its absence is a decision, never an oversight.
REQUIRED_STATE_ARTIFACTS = ("adapter", "optimizer", "scheduler", "rng")
OPTIONAL_STATE_ARTIFACTS = ("scaler",)


def hash_state_artifacts(checkpoint_dir: str | Path,
                         filenames: Mapping[str, str]
                         ) -> dict[str, str | None]:
    """Hash every persisted state file in the bundle directory:
    {artifact_name: filename}. Missing required files refuse."""
    import hashlib
    from pathlib import Path as _Path
    checkpoint_dir = _Path(checkpoint_dir)
    hashes: dict[str, str | None] = {}
    for name in REQUIRED_STATE_ARTIFACTS + OPTIONAL_STATE_ARTIFACTS:
        filename = filenames.get(name)
        if filename is None:
            if name in REQUIRED_STATE_ARTIFACTS:
                raise InfrastructureError(
                    f"checkpoint bundle missing required state "
                    f"artifact {name!r}")
            hashes[name] = None
            continue
        path = checkpoint_dir / filename
        if not path.exists():
            raise InfrastructureError(
                f"declared state artifact {name!r} ({filename}) is "
                "absent from the bundle")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _validate_artifact_hashes(hashes: Mapping[str, Any]) -> dict:
    expected_keys = set(REQUIRED_STATE_ARTIFACTS) \
        | set(OPTIONAL_STATE_ARTIFACTS)
    if set(hashes) != expected_keys:
        raise InfrastructureError(
            f"state artifact hashes must cover exactly "
            f"{sorted(expected_keys)}, got {sorted(hashes)}")
    for name in REQUIRED_STATE_ARTIFACTS:
        value = hashes[name]
        if not isinstance(value, str) or len(value) != 64:
            raise InfrastructureError(
                f"state artifact {name!r} needs a sha256, got "
                f"{value!r}")
    return dict(hashes)


def build_checkpoint_record(*, identities: Mapping[str, Any],
                            counters: Mapping[str, int],
                            rng_state: Mapping[str, Any],
                            state_artifact_hashes: Mapping[str, Any],
                            sampler_position: Mapping[str, Any],
                            run_id: str, segment_id: str,
                            parent_checkpoint: str | None
                            ) -> dict[str, Any]:
    """The persisted contract record: binds the identities, counters,
    the COMPLETE serialized RNG snapshot, and the content hash of
    every state artifact in the bundle (adapter, optimizer, scheduler,
    rng, scaler-or-None), so the record cannot describe state it does
    not actually bind (214_s P1)."""
    missing = set(IDENTITY_KEYS) - set(identities)
    if missing:
        raise InfrastructureError(
            f"checkpoint identities missing {sorted(missing)}")
    missing = set(_COUNTER_KEYS) - set(counters)
    if missing:
        raise InfrastructureError(
            f"checkpoint counters missing {sorted(missing)}")
    if counters["generated_groups"] != counters["consumed_groups"]:
        raise InfrastructureError(
            "v1 boundary violation in counters — use "
            "GroupAccountant.authorize_checkpoint")
    missing = set(_RNG_KEYS) - set(rng_state)
    if missing:
        raise InfrastructureError(
            f"checkpoint rng_state missing {sorted(missing)} "
            "(torch_cuda may be None on CPU, never absent)")
    if not isinstance(sampler_position, Mapping) or not sampler_position:
        raise InfrastructureError(
            "checkpoint needs the dataloader/sampler position (or state "
            "sufficient to reconstruct it exactly)")
    record = {
        "schema": CHECKPOINT_SCHEMA,
        "identities": {key: identities[key] for key in IDENTITY_KEYS},
        "counters": {key: int(counters[key]) for key in _COUNTER_KEYS},
        "rng_state_sha256": content_sha256(
            {key: rng_state[key] for key in _RNG_KEYS}),
        "state_artifact_sha256":
            _validate_artifact_hashes(state_artifact_hashes),
        "sampler_position": dict(sampler_position),
        "run_id": run_id,
        "segment_id": segment_id,
        "parent_checkpoint": parent_checkpoint,
    }
    record["checkpoint_sha256"] = content_sha256(record)
    return record


def validate_resume(checkpoint: Mapping[str, Any],
                    current_identities: Mapping[str, Any],
                    recomputed_artifact_hashes: Mapping[str, Any]
                    | None = None) -> dict[str, Any]:
    """Fail-closed: EVERY bound identity must match the resuming
    process exactly; the record must rehash; when the resume path
    passes the artifact hashes it recomputed from the bundle on disk
    (it always should — `hash_state_artifacts`), they must equal the
    bound ones. Returns the counters and sampler position to restore.
    A changed training parameter is a FORK, never a resume — it shows
    up here as an identity mismatch."""
    if checkpoint.get("schema") != CHECKPOINT_SCHEMA:
        raise InfrastructureError(
            f"not a {CHECKPOINT_SCHEMA} record: "
            f"{checkpoint.get('schema')!r}")
    body = {k: v for k, v in checkpoint.items()
            if k != "checkpoint_sha256"}
    if content_sha256(body) != checkpoint.get("checkpoint_sha256"):
        raise InfrastructureError("checkpoint record does not rehash")
    mismatches = []
    for key in IDENTITY_KEYS:
        if checkpoint["identities"][key] != current_identities.get(key):
            mismatches.append(key)
    if mismatches:
        raise InfrastructureError(
            f"resume identity mismatch on {mismatches} — a changed "
            "training parameter is a checkpoint FORK, never a pure "
            "resume (211_f §11)")
    if recomputed_artifact_hashes is not None:
        bound = checkpoint["state_artifact_sha256"]
        if _validate_artifact_hashes(recomputed_artifact_hashes) != bound:
            raise InfrastructureError(
                "checkpoint state artifacts on disk do not match the "
                "bound hashes — the bundle was altered (214_s P1)")
    counters = checkpoint["counters"]
    if counters["generated_groups"] != counters["consumed_groups"]:
        raise InfrastructureError(
            "checkpoint violates the v1 boundary — refusing to resume "
            "from it")
    return {"counters": dict(counters),
            "sampler_position": dict(checkpoint["sampler_position"])}


# --- segment merging --------------------------------------------------------------

def merge_segments(segments: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Merge a launch's segments into one trajectory, with identity,
    parent-linkage and cutoff enforcement (214_s P1). Each segment:

        {"segment_id", "run_id", "config_sha256",
         "status": "complete" | "aborted",
         "checkpoint_id": str | None       (the checkpoint it ENDED at
            — for aborted, the LAST VALID checkpoint before the abort),
         "parent_checkpoint": str | None   (the checkpoint it resumed
            FROM; None only for the first segment),
         "resume_from_consumed_groups": int  (0 for the first segment),
         "checkpoint_consumed_groups": int   (consumed counter at
            checkpoint_id),
         "groups": [{"global_group_index": int, ...}, ...]}

    Enforced: one run_id and one config across all segments (a config
    change is a fork, merged separately); segments are ordered by
    parent linkage — each resumes from its predecessor's end
    checkpoint and consumed counter; a COMPLETE segment's rows are
    exactly [resume_from, cutoff) — rows beyond its own checkpoint are
    impossible and refuse; an ABORTED segment's rows at or beyond its
    last valid checkpoint are EXCLUDED from the trajectory but
    returned as preserved evidence. The merged trajectory must be
    duplicate-free, contiguous and zero-based."""
    if not segments:
        raise InfrastructureError("no segments to merge")
    run_ids = {segment.get("run_id") for segment in segments}
    configs = {segment.get("config_sha256") for segment in segments}
    if len(run_ids) != 1 or None in run_ids:
        raise InfrastructureError(
            f"segments span run_ids {sorted(map(str, run_ids))} — one "
            "launch has one run identity")
    if len(configs) != 1 or None in configs:
        raise InfrastructureError(
            "segments span multiple configs — a config change is a "
            "FORK and merges separately (211_f §11)")
    trajectory: list[Mapping[str, Any]] = []
    excluded: list[Mapping[str, Any]] = []
    for position, segment in enumerate(segments):
        status = segment.get("status")
        if status not in ("complete", "aborted"):
            raise InfrastructureError(
                f"segment {segment.get('segment_id')!r} has "
                f"non-terminal status {status!r}")
        resume_from = segment["resume_from_consumed_groups"]
        cutoff = segment["checkpoint_consumed_groups"]
        for name, value in (("resume_from_consumed_groups", resume_from),
                            ("checkpoint_consumed_groups", cutoff)):
            if not isinstance(value, int) or isinstance(value, bool) \
                    or value < 0:
                raise InfrastructureError(f"bad {name} {value!r}")
        if cutoff < resume_from:
            raise InfrastructureError(
                f"segment {segment['segment_id']!r}: checkpoint "
                f"cutoff {cutoff} precedes its resume point "
                f"{resume_from} — an impossible history")
        if position == 0:
            if segment.get("parent_checkpoint") is not None \
                    or resume_from != 0:
                raise InfrastructureError(
                    "the first segment must start from scratch "
                    "(no parent checkpoint, resume point 0)")
        else:
            previous = segments[position - 1]
            if segment.get("parent_checkpoint") is None \
                    or segment["parent_checkpoint"] != \
                    previous.get("checkpoint_id"):
                raise InfrastructureError(
                    f"segment {segment['segment_id']!r} does not "
                    "resume from its predecessor's end checkpoint — "
                    "segment ordering/linkage broken")
            if resume_from != previous["checkpoint_consumed_groups"]:
                raise InfrastructureError(
                    f"segment {segment['segment_id']!r} resumes from "
                    f"consumed counter {resume_from}, but its parent "
                    f"checkpoint recorded "
                    f"{previous['checkpoint_consumed_groups']}")
        indices = sorted(g["global_group_index"]
                         for g in segment["groups"])
        if indices and (indices[0] != resume_from
                        or indices != list(range(indices[0],
                                                 indices[-1] + 1))):
            raise InfrastructureError(
                f"segment {segment['segment_id']!r} rows are not "
                f"contiguous from its resume point {resume_from}")
        for group in segment["groups"]:
            index = group["global_group_index"]
            if index >= cutoff:
                if status == "complete":
                    raise InfrastructureError(
                        f"complete segment {segment['segment_id']!r} "
                        f"carries row {index} beyond its own "
                        f"checkpoint cutoff {cutoff} — an impossible "
                        "history")
                excluded.append(group)
            else:
                trajectory.append(group)
    indices = [g["global_group_index"] for g in trajectory]
    seen = set()
    for index in indices:
        if index in seen:
            raise InfrastructureError(
                f"merged trajectory duplicates group {index}")
        seen.add(index)
    if seen and seen != set(range(min(seen), max(seen) + 1)):
        missing = sorted(set(range(min(seen), max(seen) + 1)) - seen)
        raise InfrastructureError(
            f"merged trajectory has missing groups {missing[:5]}"
            f"{'...' if len(missing) > 5 else ''}")
    if seen and min(seen) != 0:
        raise InfrastructureError(
            f"merged trajectory does not start at group 0 "
            f"(starts at {min(seen)})")
    return {"trajectory": trajectory,
            "excluded_aborted_evidence": excluded,
            "merged_groups": len(trajectory)}


# --- isolated evaluation RNG (208_s small item) -------------------------------------

@contextlib.contextmanager
def isolated_rng() -> Iterator[None]:
    """Snapshot and restore every RNG the training stack draws from,
    so a checkpoint evaluation cannot change subsequent rollout
    sampling. CUDA states are included when CUDA is present."""
    import numpy
    import torch
    python_state = random.getstate()
    numpy_state = numpy.random.get_state()
    torch_state = torch.get_rng_state()
    cuda_states = (torch.cuda.get_rng_state_all()
                   if torch.cuda.is_available() else None)
    try:
        yield
    finally:
        random.setstate(python_state)
        numpy.random.set_state(numpy_state)
        torch.set_rng_state(torch_state)
        if cuda_states is not None:
            torch.cuda.set_rng_state_all(cuda_states)


def capture_rng_state() -> dict[str, Any]:
    """The COMPLETE serializable RNG snapshot a checkpoint binds
    (214_s P1: the earlier version dropped python's version/gauss
    fields and numpy's position/Gaussian state, so two different
    states could hash identically). Restorable via
    `restore_rng_state` — capture → restore → draws are identical."""
    import numpy
    import torch
    python_version, python_internal, python_gauss = random.getstate()
    np_name, np_keys, np_pos, np_has_gauss, np_cached = \
        numpy.random.get_state()
    state: dict[str, Any] = {
        "python": {"version": python_version,
                   "internal_state": list(python_internal),
                   "gauss_next": python_gauss},
        "numpy": {"name": np_name, "keys": np_keys.tolist(),
                  "pos": int(np_pos), "has_gauss": int(np_has_gauss),
                  "cached_gaussian": float(np_cached)},
        "torch_cpu": torch.get_rng_state().tolist(),
        "torch_cuda": ([s.tolist() for s in
                        torch.cuda.get_rng_state_all()]
                       if torch.cuda.is_available() else None),
    }
    return state


def restore_rng_state(state: Mapping[str, Any]) -> None:
    """Exact inverse of `capture_rng_state`."""
    import numpy
    import torch
    python = state["python"]
    random.setstate((python["version"],
                     tuple(python["internal_state"]),
                     python["gauss_next"]))
    np_state = state["numpy"]
    numpy.random.set_state((np_state["name"],
                            numpy.array(np_state["keys"],
                                        dtype=numpy.uint32),
                            np_state["pos"], np_state["has_gauss"],
                            np_state["cached_gaussian"]))
    torch.set_rng_state(torch.tensor(state["torch_cpu"],
                                     dtype=torch.uint8))
    if state["torch_cuda"] is not None:
        if not torch.cuda.is_available():
            raise InfrastructureError(
                "checkpoint carries CUDA RNG state but CUDA is "
                "unavailable — wrong resume environment")
        torch.cuda.set_rng_state_all(
            [torch.tensor(s, dtype=torch.uint8)
             for s in state["torch_cuda"]])
