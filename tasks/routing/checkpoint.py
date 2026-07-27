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


def build_checkpoint_record(*, identities: Mapping[str, Any],
                            counters: Mapping[str, int],
                            rng_state: Mapping[str, Any],
                            sampler_position: Mapping[str, Any],
                            run_id: str, segment_id: str,
                            parent_checkpoint: str | None
                            ) -> dict[str, Any]:
    """The persisted contract record (the tensor state itself — adapter
    weights, optimizer, scheduler, scaler — travels beside it in the
    checkpoint directory; this record binds the identities and
    counters that make it resumable)."""
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
        "sampler_position": dict(sampler_position),
        "run_id": run_id,
        "segment_id": segment_id,
        "parent_checkpoint": parent_checkpoint,
    }
    record["checkpoint_sha256"] = content_sha256(record)
    return record


def validate_resume(checkpoint: Mapping[str, Any],
                    current_identities: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed: EVERY bound identity must match the resuming
    process exactly; the record must rehash. Returns the counters and
    sampler position to restore. A changed training parameter is a
    FORK, never a resume — it shows up here as an identity mismatch."""
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
    counters = checkpoint["counters"]
    if counters["generated_groups"] != counters["consumed_groups"]:
        raise InfrastructureError(
            "checkpoint violates the v1 boundary — refusing to resume "
            "from it")
    return {"counters": dict(counters),
            "sampler_position": dict(checkpoint["sampler_position"])}


# --- segment merging --------------------------------------------------------------

def merge_segments(segments: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Merge a launch's segments into one trajectory. Each segment:
    {"segment_id", "status": "complete"|"aborted",
     "checkpoint_consumed_groups": int  (the consumed counter of the
        checkpoint this segment ENDED at — for an aborted segment, the
        last VALID checkpoint before the abort),
     "groups": [{"global_group_index": int, ...}, ...]}.
    Post-checkpoint rows of an aborted segment are EXCLUDED from the
    trajectory but returned as preserved evidence; the merged
    trajectory must cover a contiguous, duplicate-free index range.
    """
    if not segments:
        raise InfrastructureError("no segments to merge")
    trajectory: list[Mapping[str, Any]] = []
    excluded: list[Mapping[str, Any]] = []
    for position, segment in enumerate(segments):
        status = segment.get("status")
        if status not in ("complete", "aborted"):
            raise InfrastructureError(
                f"segment {segment.get('segment_id')!r} has "
                f"non-terminal status {status!r}")
        if status == "aborted" and position != len(segments) - 1:
            # an aborted middle segment is exactly what an engineering
            # resume repairs; its tail rows never enter the trajectory
            pass
        cutoff = segment["checkpoint_consumed_groups"]
        if not isinstance(cutoff, int) or isinstance(cutoff, bool) \
                or cutoff < 0:
            raise InfrastructureError(
                f"bad checkpoint_consumed_groups {cutoff!r}")
        for group in segment["groups"]:
            index = group["global_group_index"]
            if status == "aborted" and index >= cutoff:
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
    """The serializable RNG snapshot a checkpoint binds (hashed into
    the record; the raw states travel in the checkpoint directory)."""
    import numpy
    import torch
    state: dict[str, Any] = {
        "python": list(map(str, random.getstate()[1])),
        "numpy": numpy.random.get_state()[1].tolist(),
        "torch_cpu": torch.get_rng_state().tolist(),
        "torch_cuda": ([s.tolist() for s in
                        torch.cuda.get_rng_state_all()]
                       if torch.cuda.is_available() else None),
    }
    return state
