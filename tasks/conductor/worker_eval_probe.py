"""P0/P1 generation-policy probes — recorded commands (plan 81_f §7).

P0 replays retained batch-sensitivity regressions: a frozen cohort
manifest lists the exact physical `model.generate` chunks (ordered case
references), and the probe drives `pool.generate` directly with the
original grouping, the reversed within-chunk order, or the scientific
singleton path. Differences between conditions are retained findings,
not tool failures.

P1 is the `singleton-v1` admissibility gate: one invocation = one fresh
process running the declared sample in canonical or reversed
order; the `admit` subcommand takes two canonical-order runs and one
reversed-order run and admits only on exact generation-field equality
within the frozen cost gate (§7.3). If admission fails, stop and write
the §7.4 follow-up decision plan — do not fall back to the cache.

The 92_s experiment commands (candidate = one registered model x
request-contract x Code-prompt configuration):

  uv run python -m tasks.conductor.worker_eval_probe p1 \
      --candidate coder_1p5b-current-rev9 --order canonical --out r1.json
  uv run python -m tasks.conductor.worker_eval_probe admit r1.json r2.json r3.json
  uv run python -m tasks.conductor.worker_eval_probe run \
      --candidate coder_1p5b-current-rev9 --run-dir runs/92s/...-full
  uv run python -m tasks.conductor.worker_eval_probe screen \
      --runs-dir runs/92s --tranche A --out screening.json
  uv run python -m tasks.conductor.worker_eval_probe reveal \
      --runs-dir runs/92s --screening screening.json --out reveal.json

P0 replay (each invocation is its own fresh process):

  uv run python -m tasks.conductor.worker_eval_probe p0 \
      --cohort tasks/conductor/fixtures/p0_rev9_code_cohort.json \
      --condition original --out p0-orig-1.json
  uv run python -m tasks.conductor.worker_eval_probe compare a.json b.json
"""

from __future__ import annotations

import argparse
import copy
import functools
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from . import contract, program
from .profiles import DEFAULT_PROFILE, ProfileError
from .runtime import (
    DEFAULT_RUNTIME_PROFILE, build_runtime, runtime_profile_fingerprint,
)
from .types import CELL_IDS, ENDPOINT_NAMES, RENDERER_IDS, \
    InfrastructureError
from .worker_eval import (
    ENDPOINT_SCHEDULE_VERSION, NodeLabel, NullCache, WorkerEvalCase,
    endpoint_schedule, environment_versions, git_provenance,
    node_cases_for_latent, resolve_request_contract, singleton_call,
)

PROBE_SCHEMA_VERSION = 1

# Frozen §7.3 cost gate — replaceable by a reviewer before the probe,
# never after inspecting P1 outcomes, and never with "acceptable latency".
MAX_FULL_RUN_SECONDS = 3600      # projected 900-case candidate run
MAX_PEAK_VRAM_BYTES = 22 * 2 ** 30

# §7.3: admit only on exact equality of these generated fields.
GENERATION_EQUALITY_FIELDS = ("completion", "finish_reason",
                              "generated_tokens",
                              "generation_hit_token_cap")
# `compare` additionally reports semantic drift between byte-different
# completions (§7.2: grammar result, executed value, node correctness).
COMPARE_FIELDS = GENERATION_EQUALITY_FIELDS + ("status", "value",
                                               "node_correct")

_ENDPOINT_ID = {name: eid for eid, name in ENDPOINT_NAMES.items()}


# --- sample construction and coverage (81_f §7.3) ----------------------------

def probe_latents(namespace: str, per_cell: int,
                  profile: Mapping[str, Any] | None = None) -> list[dict]:
    gen_profile = dict(profile) if profile is not None else DEFAULT_PROFILE
    return [program.generate_latent(cell, namespace, index,
                                    gen_profile).latent
            for cell in CELL_IDS for index in range(per_cell)]


def assert_probe_coverage(latents: list[Mapping[str, Any]]) -> None:
    """§7.3 pre-execution assertion: the sample covers every cell, node
    family and declared generator factor level."""
    cells = {latent["cell_id"] for latent in latents}
    if cells != set(CELL_IDS):
        raise InfrastructureError(
            f"sample misses cells {sorted(set(CELL_IDS) - cells)}")
    families = {family for latent in latents
                for family in endpoint_schedule(latent).values()}
    if families != set(ENDPOINT_NAMES.values()):
        raise InfrastructureError(
            f"sample misses node families "
            f"{sorted(set(ENDPOINT_NAMES.values()) - families)}")
    seen: dict[tuple[str, str], set[str]] = {}
    for latent in latents:
        for factor, level in latent["factor_assignment"].items():
            seen.setdefault((latent["cell_id"], factor), set()).add(level)
    for cell in cells:
        for factor, levels in program.CELL_FACTORS[cell]:
            missing = set(levels) - seen.get((cell, factor), set())
            if missing:
                raise InfrastructureError(
                    f"sample misses {cell}.{factor} levels "
                    f"{sorted(missing)}")


def build_probe_cases(namespace: str, per_cell: int,
                      renderers: list[str], visibility: str,
                      profile: Mapping[str, Any] | None = None,
                      request_contract_key: str = "worker-blocks-v0"
                      ) -> tuple[list[WorkerEvalCase], list[NodeLabel]]:
    latents = probe_latents(namespace, per_cell, profile)
    assert_probe_coverage(latents)
    cases: list[WorkerEvalCase] = []
    labels: list[NodeLabel] = []
    for latent in latents:
        latent_cases, latent_labels = node_cases_for_latent(
            latent, renderers, visibility, request_contract_key)
        cases.extend(latent_cases)
        labels.extend(latent_labels)
    return cases, labels


# --- 92_s candidate plans (§6.6, §6.9) ---------------------------------------

@functools.lru_cache(maxsize=8)
def _candidate_tokenizer(model_id: str, revision: str):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(model_id, revision=revision)


def _rendered_sha(model_id: str, revision: str, system_text: str,
                  user_message: str) -> str:
    tokenizer = _candidate_tokenizer(model_id, revision)
    text = tokenizer.apply_chat_template(
        [{"role": "system", "content": system_text},
         {"role": "user", "content": user_message}],
        tokenize=False, add_generation_prompt=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@functools.lru_cache(maxsize=32)
def candidate_p1_cases(cid: str) -> tuple[tuple[WorkerEvalCase, ...],
                                          tuple["NodeLabel", ...]]:
    """The candidate's exact 300-case P1 plan (worker_dev prefix under
    its request contract)."""
    from .candidates import candidate_config
    config = candidate_config(cid)
    cases, labels = build_probe_cases(
        WORKER_DEV_NAMESPACE, P1_PER_CELL, list(RENDERER_IDS), "private",
        request_contract_key=config["request_contract_key"])
    return tuple(cases), tuple(labels)


@functools.lru_cache(maxsize=32)
def candidate_full_cases(cid: str) -> tuple[tuple[WorkerEvalCase, ...],
                                            tuple["NodeLabel", ...]]:
    from .candidates import candidate_config
    config = candidate_config(cid)
    cases, labels = build_probe_cases(
        WORKER_DEV_NAMESPACE, 30, list(RENDERER_IDS), "private",
        request_contract_key=config["request_contract_key"])
    return tuple(cases), tuple(labels)


def _latent_index(case_id: str) -> int:
    # case_id = cell:namespace:index:hash:renderer:visibility:node
    return int(case_id.split(":")[2])


def assert_p1_nested_projection(cid: str) -> None:
    """92_s §6.9: the P1 case ids are exactly the first-10-latent
    projection of the full 30-latent plan, in plan order."""
    p1_ids = [case.case_id for case in candidate_p1_cases(cid)[0]]
    projected = [case.case_id for case in candidate_full_cases(cid)[0]
                 if _latent_index(case.case_id) < P1_PER_CELL]
    if p1_ids != projected:
        raise InfrastructureError(
            f"{cid}: P1 plan is not the nested first-10 projection of "
            "the full plan")


@functools.lru_cache(maxsize=32)
def candidate_plan_identity(cid: str) -> tuple[tuple[str, str, str, str],
                                               ...]:
    """(case_id, endpoint, user_sha, rendered request_sha) per P1 case —
    admission verifies runs against this, regenerated from the candidate
    registry (92_s §6.6): profile, prompt bundle, chat template and
    request contract, never a caller-provided label."""
    from .candidates import candidate_bundle, candidate_runtime_profile
    assert_p1_nested_projection(cid)
    profile = candidate_runtime_profile(cid)
    bundle = candidate_bundle(cid)
    cases, _ = candidate_p1_cases(cid)
    identity = []
    for case in cases:
        worker = profile["workers"][case.endpoint_name]
        identity.append((
            case.case_id, case.endpoint_name,
            hashlib.sha256(case.user_message.encode("utf-8")).hexdigest(),
            _rendered_sha(worker["model_id"], worker["revision"],
                          bundle.text(case.endpoint_name),
                          case.user_message)))
    return tuple(identity)


def sequence_hashes(case_ids: list[str]) -> dict[str, str]:
    """§6.9: canonical and exact-reversal order hashes for a plan."""
    canonical = hashlib.sha256(
        "\n".join(case_ids).encode("utf-8")).hexdigest()
    reversed_hash = hashlib.sha256(
        "\n".join(reversed(case_ids)).encode("utf-8")).hexdigest()
    return {"canonical": canonical, "reversed": reversed_hash}


# --- per-case records --------------------------------------------------------

def _case_record(case: WorkerEvalCase, label: NodeLabel, completion: str,
                 finish_reason: str, generated_tokens: int,
                 hit_cap: bool, request_sha256: str,
                 chunk_index: int | None,
                 chunk_slot: int | None) -> dict[str, Any]:
    result = contract.run_worker_output(
        _ENDPOINT_ID[case.endpoint_name], completion, case.binding())
    return {
        "case_id": case.case_id,
        "endpoint_name": case.endpoint_name,
        "chunk_index": chunk_index,
        "chunk_slot": chunk_slot,
        "user_message_sha256": hashlib.sha256(
            case.user_message.encode("utf-8")).hexdigest(),
        "request_sha256": request_sha256,
        "completion": completion,
        "completion_sha256": hashlib.sha256(
            completion.encode("utf-8")).hexdigest(),
        "finish_reason": finish_reason,
        "generated_tokens": generated_tokens,
        "generation_hit_token_cap": hit_cap,
        "status": result.status,
        "value": result.value,
        "rejection_code": result.rejection_code,
        "expected_value": label.expected_value,
        "node_correct": (result.status == "success"
                         and result.value == label.expected_value),
    }


def _vram_tracker():
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            return lambda: int(torch.cuda.max_memory_reserved())
    except ImportError:
        pass
    return lambda: None


def _header(probe: str, pool: Any, profile: Mapping[str, Any],
            **extra: Any) -> dict[str, Any]:
    endpoints = sorted(set(ENDPOINT_NAMES.values()))
    return {
        "probe": probe,
        "schema_version": PROBE_SCHEMA_VERSION,
        "generator_version": program.GENERATOR_VERSION,
        "endpoint_schedule_version": ENDPOINT_SCHEDULE_VERSION,
        "runtime_profile_fingerprint": runtime_profile_fingerprint(profile),
        "system_prompt_sha256": {
            name: hashlib.sha256(
                pool.system_prompt(name).encode("utf-8")).hexdigest()
            for name in endpoints},
        "chat_template_sha256": {name: pool.chat_template_sha(name)
                                 for name in endpoints},
        "git": git_provenance(),
        "environment": environment_versions(),
        # Fresh-process evidence (report-only, never an equality field).
        "process": {"pid": os.getpid(),
                    "started_utc": datetime.now(timezone.utc).isoformat()},
        **extra,
    }


# --- P1: singleton admissibility runs (81_f §7.3) ----------------------------

def run_p1_cases(runtime: Any, cases: list[WorkerEvalCase],
                 labels: list[NodeLabel], order: str
                 ) -> tuple[list[dict[str, Any]], float, int | None]:
    """One fresh-process singleton pass over the declared sample,
    through the exact runtime path the scientific evaluator uses."""
    if order not in ("canonical", "reversed"):
        raise ProfileError(f"unknown order {order!r}")
    label_by_id = {label.case_id: label for label in labels}
    ordered = list(cases) if order == "canonical" else list(reversed(cases))
    peak_vram = _vram_tracker()
    started = time.monotonic()
    records = []
    for case in ordered:
        record = singleton_call(runtime, case.endpoint_name,
                                case.user_message)
        records.append(_case_record(
            case, label_by_id[case.case_id], record.completion,
            record.finish_reason, record.generated_tokens,
            record.generation_hit_token_cap, record.request_sha256,
            chunk_index=None, chunk_slot=None))
    return records, time.monotonic() - started, peak_vram()


# --- P0: frozen physical-chunk replay (81_f §7.2) ----------------------------

def load_cohort(cohort: Mapping[str, Any],
                profile: Mapping[str, Any] | None = None,
                runtime_profile: Mapping[str, Any] | None = None
                ) -> tuple[str, list[list[tuple[WorkerEvalCase,
                                                NodeLabel]]]]:
    """Regenerate the cohort's cases from the frozen generator. Each chunk
    entry names one reference node and pins its `user_message_sha256`,
    which must match the regenerated request exactly. Chunk sizes must be
    executable as declared: a chunk larger than the endpoint microbatch
    would silently split inside `pool.generate` and the condition run
    would not be the physical batch the manifest claims (82_s finding 2)."""
    endpoint = cohort["endpoint"]
    if endpoint not in ENDPOINT_NAMES.values():
        raise ProfileError(f"unknown endpoint {endpoint!r}")
    microbatch = (dict(runtime_profile) if runtime_profile is not None
                  else DEFAULT_RUNTIME_PROFILE)["workers"][endpoint][
                      "microbatch"]
    seen_entries: set[tuple[str, int, str, str]] = set()
    chunks: list[list[tuple[WorkerEvalCase, NodeLabel]]] = []
    for chunk_index, chunk in enumerate(cohort["chunks"]):
        if not chunk:
            raise InfrastructureError(f"chunk {chunk_index} is empty")
        if len(chunk) > microbatch:
            raise InfrastructureError(
                f"chunk {chunk_index} has {len(chunk)} requests but the "
                f"{endpoint} microbatch is {microbatch}; pool.generate "
                "would split it and the replayed condition would not be "
                "the declared physical batch")
        resolved = []
        for entry in chunk:
            key = (entry["cell_id"], entry["latent_index"],
                   entry["renderer_id"], entry["node_id"])
            if key in seen_entries:
                raise InfrastructureError(f"duplicate cohort entry {key}")
            seen_entries.add(key)
            latent = program.generate_latent(
                entry["cell_id"], cohort["namespace"],
                entry["latent_index"],
                dict(profile) if profile is not None
                else DEFAULT_PROFILE).latent
            cases, labels = node_cases_for_latent(
                latent, [entry["renderer_id"]], cohort["visibility"])
            matches = [(case, label) for case, label in zip(cases, labels)
                       if label.node_id == entry["node_id"]]
            if len(matches) != 1:
                raise InfrastructureError(
                    f"cohort entry {entry} resolves to "
                    f"{len(matches)} cases")
            case, label = matches[0]
            if case.endpoint_name != endpoint:
                raise InfrastructureError(
                    f"{case.case_id} is scheduled on "
                    f"{case.endpoint_name!r}, cohort declares "
                    f"{endpoint!r}")
            pinned = entry.get("user_message_sha256")
            if pinned is None:
                raise InfrastructureError(
                    f"{case.case_id}: cohort entries must pin "
                    "user_message_sha256; an unpinned replay cannot show "
                    "it reproduced the retained requests")
            actual = hashlib.sha256(
                case.user_message.encode("utf-8")).hexdigest()
            if pinned != actual:
                raise InfrastructureError(
                    f"{case.case_id}: regenerated request does not match "
                    "the retained cohort request; the generator or "
                    "request contract has drifted")
            resolved.append((case, label))
        chunks.append(resolved)
    return endpoint, chunks


def run_p0_condition(pool: Any, runtime: Any, endpoint: str,
                     chunks: list[list[tuple[WorkerEvalCase, NodeLabel]]],
                     condition: str
                     ) -> tuple[list[dict[str, Any]], float, int | None]:
    """Execute the cohort under one condition. `original` and `reversed`
    drive `pool.generate` directly with the recorded physical chunks (the
    rejected dynamic-batching regime, §7.1); `singleton` uses the
    scientific runtime path for the same cases in flattened order."""
    peak_vram = _vram_tracker()
    started = time.monotonic()
    records: list[dict[str, Any]] = []
    if condition in ("original", "reversed"):
        for chunk_index, chunk in enumerate(chunks):
            ordered = list(chunk) if condition == "original" \
                else list(reversed(chunk))
            rendered = [pool.render_request(endpoint, case.user_message)
                        for case, _ in ordered]
            generations = pool.generate(endpoint, rendered)
            if len(generations) != len(ordered):
                raise InfrastructureError(
                    f"chunk {chunk_index}: {len(generations)} generations "
                    f"for {len(ordered)} requests")
            for slot, ((case, label), request, gen) in enumerate(
                    zip(ordered, rendered, generations)):
                records.append(_case_record(
                    case, label, gen.completion, gen.finish_reason,
                    gen.generated_tokens, gen.generation_hit_token_cap,
                    hashlib.sha256(request).hexdigest(),
                    chunk_index=chunk_index, chunk_slot=slot))
    elif condition == "singleton":
        for case, label in (pair for chunk in chunks for pair in chunk):
            record = singleton_call(runtime, case.endpoint_name,
                                    case.user_message)
            records.append(_case_record(
                case, label, record.completion, record.finish_reason,
                record.generated_tokens, record.generation_hit_token_cap,
                record.request_sha256, chunk_index=None, chunk_slot=None))
    else:
        raise ProfileError(f"unknown condition {condition!r}")
    return records, time.monotonic() - started, peak_vram()


# --- comparison and admission ------------------------------------------------

# Headers that must match before two probe outputs are comparable at
# all (84_s finding 2): P0 conditions run in separate invocations, so a
# prompt/model/template/code change between them must be refused as
# configuration drift, never misreported as batching evidence.
_P0_HELD_FIXED = ("probe", "schema_version", "cohort_sha256", "endpoint",
                  "generator_version", "endpoint_schedule_version",
                  "runtime_profile_fingerprint", "system_prompt_sha256",
                  "chat_template_sha256", "environment")


def compare_probe_outputs(left: Mapping[str, Any],
                          right: Mapping[str, Any]
                          ) -> list[dict[str, Any]]:
    """Whole-output comparison: refuse unless the probe-type-specific
    held-fixed headers, one clean shared commit, and per-case
    user-message/request hashes all match; only then report per-case
    outcome differences (which, for P0, are the retained evidence)."""
    if left.get("probe") != right.get("probe"):
        raise InfrastructureError(
            f"cannot compare {left.get('probe')!r} with "
            f"{right.get('probe')!r} outputs")
    if (left["process"]["pid"], left["process"].get("started_utc")) \
            == (right["process"]["pid"],
                right["process"].get("started_utc")):
        # 86_s: §7.2 compares two *executions*; one output compared with
        # itself would manufacture bit-stability evidence.
        raise InfrastructureError(
            "outputs share one process identity; comparison requires "
            "two separate executions")
    held = (_P0_HELD_FIXED if left["probe"] == "p0"
            else ("probe", "schema_version") + _P1_HELD_FIXED)
    mismatched = [field for field in held
                  if left.get(field) != right.get(field)]
    for side, run in (("left", left), ("right", right)):
        if run["git"]["dirty"]:
            mismatched.append(f"git.dirty ({side})")
    if left["git"]["commit"] != right["git"]["commit"]:
        mismatched.append("git.commit")
    if mismatched:
        raise InfrastructureError(
            f"outputs are not comparable; configuration differs on "
            f"{mismatched} — differences would not be generation "
            "evidence")
    left_by = {record["case_id"]: record for record in left["cases"]}
    right_by = {record["case_id"]: record for record in right["cases"]}
    drifted = sorted(
        case_id for case_id in set(left_by) & set(right_by)
        if (left_by[case_id]["user_message_sha256"],
            left_by[case_id]["request_sha256"])
        != (right_by[case_id]["user_message_sha256"],
            right_by[case_id]["request_sha256"]))
    if drifted:
        raise InfrastructureError(
            f"request bytes differ for {drifted[:5]}; the runs did not "
            "pose identical requests")
    return compare_records(left["cases"], right["cases"])


def compare_records(left: list[Mapping[str, Any]],
                    right: list[Mapping[str, Any]]
                    ) -> list[dict[str, Any]]:
    """Field-wise per-case differences (empty = exact agreement on the
    §7.2 comparison fields). Cases align by case_id, so condition order
    does not matter."""
    left_by_id = {record["case_id"]: record for record in left}
    right_by_id = {record["case_id"]: record for record in right}
    if len(left_by_id) != len(left) or len(right_by_id) != len(right):
        raise InfrastructureError("duplicate case_id in probe records")
    if set(left_by_id) != set(right_by_id):
        raise InfrastructureError(
            f"case sets differ: only-left "
            f"{sorted(set(left_by_id) - set(right_by_id))}, only-right "
            f"{sorted(set(right_by_id) - set(left_by_id))}")
    diffs = []
    for case_id in sorted(left_by_id):
        fields = {
            field: {"left": left_by_id[case_id][field],
                    "right": right_by_id[case_id][field]}
            for field in COMPARE_FIELDS
            if left_by_id[case_id][field] != right_by_id[case_id][field]}
        if fields:
            diffs.append({"case_id": case_id, "fields": fields})
    return diffs


# Candidate-identity fields that must match across the three P1 runs.
_P1_HELD_FIXED = ("namespace", "per_cell", "renderers", "visibility",
                  "generator_version", "endpoint_schedule_version",
                  "runtime_profile_fingerprint", "system_prompt_sha256",
                  "chat_template_sha256", "environment")

# The registered §7.3 P1 design (D1 erratum, 88_f): 10 latents per cell
# crossed with all renderers, private visibility — 300 node cases.
# Diagnostic runs with other shapes are legal probe invocations but
# never admissible.
P1_PER_CELL = 10
P1_CASES = 300

# The authoritative Gate-D namespace (88_f §3.3, ratified per 89_s):
# the public admit/confirm commands are hard-bound to it.
WORKER_DEV_NAMESPACE = "worker_dev"


@functools.lru_cache(maxsize=4)
def _p1_expected_plan(namespace: str
                      ) -> tuple[tuple[str, str, str], ...]:
    """(case_id, endpoint, user_message_sha256) in canonical plan order,
    regenerated from the frozen generator. 89_s blocking finding: the
    namespace *label* on a run is not evidence — admission must prove
    the runs posed exactly the declared plan."""
    cases, _ = build_probe_cases(namespace, P1_PER_CELL,
                                 list(RENDERER_IDS), "private")
    return tuple(
        (case.case_id, case.endpoint_name,
         hashlib.sha256(case.user_message.encode("utf-8")).hexdigest())
        for case in cases)


def admit_singleton(runs: list[Mapping[str, Any]],
                    expected_namespace: str,
                    max_seconds: int = MAX_FULL_RUN_SECONDS,
                    max_vram_bytes: int = MAX_PEAK_VRAM_BYTES,
                    full_cases: int = 900) -> dict[str, Any]:
    """The §7.3 verdict over three fresh-process P1 outputs (canonical,
    canonical, reversed). The runs must be the declared design against
    the declared namespace (82_s finding 1) — not merely mutually
    consistent — with exact generation-field equality for every case and
    the frozen cost gate. FAIL has no partial credit."""
    reasons: list[str] = []
    if len(runs) != 3:
        raise ProfileError("admission takes exactly three P1 runs")
    if any(run["probe"] != "p1" for run in runs):
        raise ProfileError("admission takes P1 outputs only")
    orders = [run["order"] for run in runs]
    if orders != ["canonical", "canonical", "reversed"]:
        reasons.append(f"run orders {orders} != "
                       "['canonical', 'canonical', 'reversed']")
    for field in _P1_HELD_FIXED:
        values = [run.get(field) for run in runs]
        if any(value != values[0] for value in values):
            reasons.append(f"held-fixed field {field!r} differs "
                           f"across runs: {values}")
    design = {"namespace": expected_namespace, "per_cell": P1_PER_CELL,
              "visibility": "private"}
    for field, expected in design.items():
        if runs[0].get(field) != expected:
            reasons.append(f"{field} {runs[0].get(field)!r} is not the "
                           f"declared {expected!r}")
    if sorted(runs[0].get("renderers", [])) != sorted(RENDERER_IDS):
        reasons.append(f"renderers {runs[0].get('renderers')} are not "
                       f"the full crossing {sorted(RENDERER_IDS)}")
    if len(runs[0]["cases"]) != P1_CASES:
        reasons.append(f"{len(runs[0]['cases'])} cases is not the "
                       f"declared {P1_CASES}-case design")
    commits = [run["git"]["commit"] for run in runs]
    if any(run["git"]["dirty"] for run in runs):
        reasons.append("a run came from a dirty worktree")
    if len(set(commits)) != 1:
        reasons.append(f"runs span commits {sorted(set(commits))}; "
                       "admission requires one clean commit")
    pids = [run["process"]["pid"] for run in runs]
    if len(set(pids)) != 3:
        reasons.append(f"process ids {pids} are not distinct; each run "
                       "must be a fresh process")
    # 89_s blocking finding: regenerate the declared plan and require
    # every run to match it — support, order, endpoint and request
    # identity. A relabelled namespace or candidate header proves
    # nothing. Candidate runs (92_s §6.6) additionally verify the
    # rendered request hashes, profile fingerprint, prompt hashes and
    # contract digest against the candidate registry.
    cids = {run.get("candidate") for run in runs}
    if len(cids) != 1:
        reasons.append(f"runs span candidates {sorted(map(str, cids))}")
    cid = next(iter(cids)) if len(cids) == 1 else None
    if cid is not None:
        from .candidates import (candidate_bundle, candidate_config,
                                 candidate_runtime_profile)
        config = candidate_config(cid)
        if expected_namespace != WORKER_DEV_NAMESPACE:
            reasons.append("candidate admission is defined only against "
                           f"{WORKER_DEV_NAMESPACE!r}")
        expected_rtp = runtime_profile_fingerprint(
            candidate_runtime_profile(cid))
        if runs[0].get("runtime_profile_fingerprint") != expected_rtp:
            reasons.append(f"runtime profile fingerprint is not "
                           f"{cid!r}'s registered profile")
        if runs[0].get("system_prompt_sha256") \
                != candidate_bundle(cid).sha256():
            reasons.append(f"prompt hashes are not {cid!r}'s registered "
                           "bundle")
        registered_contract = resolve_request_contract(
            config["request_contract_key"])
        if runs[0].get("request_contract", {}).get("digest") \
                != registered_contract["digest"]:
            reasons.append(f"request-contract digest is not {cid!r}'s "
                           "registered contract")
        plan4 = candidate_plan_identity(cid)
        canonical_ids = [case_id for case_id, _, _, _ in plan4]
        identity = {c: (e, u, r) for c, e, u, r in plan4}
        record_key = lambda record: (record["endpoint_name"],
                                     record["user_message_sha256"],
                                     record["request_sha256"])
    else:
        plan3 = _p1_expected_plan(expected_namespace)
        canonical_ids = [case_id for case_id, _, _ in plan3]
        identity = {c: (e, u) for c, e, u in plan3}
        record_key = lambda record: (record["endpoint_name"],
                                     record["user_message_sha256"])
    for index, run in enumerate(runs):
        sequence = [record["case_id"] for record in run["cases"]]
        expected_sequence = (canonical_ids if run["order"] == "canonical"
                             else list(reversed(canonical_ids)))
        if sequence != expected_sequence:
            reasons.append(
                f"run {index + 1}: case sequence is not the "
                f"{expected_namespace} plan in {run['order']} order")
            continue
        drifted = [record["case_id"] for record in run["cases"]
                   if record_key(record) != identity[record["case_id"]]]
        if drifted:
            reasons.append(
                f"run {index + 1}: endpoint/request identity differs "
                f"from the regenerated plan for {drifted[:3]}")
    for index in (1, 2):
        for diff in compare_records(runs[0]["cases"], runs[index]["cases"]):
            unequal = [field for field in diff["fields"]
                       if field in GENERATION_EQUALITY_FIELDS]
            if unequal:
                reasons.append(
                    f"run {index + 1} vs run 1: {diff['case_id']} "
                    f"differs on {unequal}")
        requests = [
            {record["case_id"]: record["request_sha256"]
             for record in run["cases"]} for run in (runs[0], runs[index])]
        if requests[0] != requests[1]:
            drifted = sorted(case for case in requests[0]
                             if requests[0].get(case)
                             != requests[1].get(case))
            reasons.append(f"run {index + 1} vs run 1: request bytes "
                           f"differ for {drifted[:5]} — the runs did not "
                           "pose identical requests")
    n_cases = len(runs[0]["cases"])
    projected = [run["wall_seconds"] * full_cases / n_cases
                 for run in runs]
    if max(projected) > max_seconds:
        reasons.append(
            f"projected {full_cases}-case run "
            f"{max(projected):.0f}s exceeds the frozen "
            f"{max_seconds}s gate")
    vram = [run["peak_vram_bytes"] for run in runs]
    if any(value is None for value in vram):
        reasons.append("peak_vram_bytes missing; the gate requires a "
                       "recorded measurement")
    elif max(vram) >= max_vram_bytes:
        reasons.append(
            f"peak reserved VRAM {max(vram)} B exceeds the frozen "
            f"{max_vram_bytes} B gate")
    return {
        "admitted": not reasons,
        "policy": "singleton-v1",
        "reasons": reasons,
        "cases": n_cases,
        "expected_namespace": expected_namespace,
        # The thresholds this verdict applied (82_s low-severity note).
        "max_seconds": max_seconds,
        "max_vram_bytes": max_vram_bytes,
        "projected_full_run_seconds": max(projected),
        "peak_vram_bytes": (max(vram)
                            if all(v is not None for v in vram) else None),
    }


# --- 92_s candidate runner (§6.7) and screening/reveal (§6.10) ---------------

class _TimedRuntime:
    """Delegating wrapper recording per-endpoint call counts and wall
    seconds for the §3 execution measurements."""

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime
        self.stats: dict[str, dict[str, float]] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._runtime, name)

    def worker_call_batch(self, endpoint_name: str,
                          user_messages: list) -> list:
        started = time.monotonic()
        records = self._runtime.worker_call_batch(endpoint_name,
                                                  user_messages)
        entry = self.stats.setdefault(endpoint_name,
                                      {"calls": 0, "seconds": 0.0})
        entry["calls"] += len(user_messages)
        entry["seconds"] += time.monotonic() - started
        return records


def _reserved_bytes() -> int:
    try:
        import torch
        if torch.cuda.is_available():
            return int(torch.cuda.memory_reserved())
    except ImportError:
        pass
    return 0


FULL_POPULATION = {"namespace": "worker_dev", "per_cell": 30,
                   "renderers": list(RENDERER_IDS),
                   "visibility": "private"}


def run_candidate(cid: str, mode: str, run_dir: str,
                  device: str = "cuda", pool: Any = None,
                  git_info: Mapping[str, Any] | None = None,
                  process_info: Mapping[str, Any] | None = None) -> Any:
    """One complete 92_s candidate evaluation artifact: the thin
    experiment command (§6.7), not an orchestration framework. An
    interrupted run stays on disk; restarts use a fresh run id/dir."""
    from .candidates import (candidate_bundle, candidate_config,
                             candidate_runtime_profile, physical_layout)
    from .worker_eval import (RunWriter, build_manifest, build_node_cases,
                              case_identities, run_composed_workflows,
                              run_node_cases, score_node_calls,
                              score_workflow_calls, summarize_worker_eval)
    config = candidate_config(cid)
    profile = candidate_runtime_profile(cid)
    bundle = candidate_bundle(cid)
    if pool is None:
        from .workers import WorkerPool
        pool = WorkerPool(profile, device=device)
    runtime = build_runtime(profile, pool=pool, cache=NullCache())
    contract_key = config["request_contract_key"]
    if mode == "isolated":
        cases, labels = build_node_cases(
            FULL_POPULATION, request_contract_key=contract_key)
        expected_calls, expected_scores = len(cases), len(labels)
    elif mode == "composed":
        expected_calls = 10 * 30 * len(RENDERER_IDS)  # steps per pass
        expected_scores = 6 * 30 * len(RENDERER_IDS)  # workflows
    else:
        raise ProfileError(f"unknown mode {mode!r}")
    manifest = build_manifest(
        runtime, bundle, run_id=Path(run_dir).name,
        purpose=f"92_s candidate {cid} ({mode})",
        population=FULL_POPULATION,
        endpoint_schedule_version=ENDPOINT_SCHEDULE_VERSION,
        candidate_label=cid, request_contract_key=contract_key,
        expected_calls=expected_calls, expected_scores=expected_scores,
        evaluation_mode=mode, physical_layout=physical_layout(profile),
        git_info=git_info, process_info=process_info)
    timed = _TimedRuntime(runtime)
    peak = _vram_tracker()
    started = time.monotonic()
    with RunWriter(run_dir, manifest) as writer:
        if mode == "isolated":
            rows = run_node_cases(timed, list(cases), writer,
                                  case_identities(list(labels)))
            scores = score_node_calls(rows, list(labels))
        else:
            rows, wlabels = run_composed_workflows(
                timed, FULL_POPULATION, writer,
                request_contract_key=contract_key)
            scores = score_workflow_calls(rows, wlabels)
        for row in scores:
            writer.write_score(row)
        writer.write_summary(summarize_worker_eval(manifest, rows, scores))
        writer.write_extra("measurements.json", {
            "wall_seconds": time.monotonic() - started,
            "idle_reserved_bytes": _reserved_bytes(),
            "peak_reserved_bytes": peak() or 0,
            "per_endpoint": timed.stats,
            "checkpoints": pool.checkpoint_report(),
        })
    return writer


def prefix_verdict(run: Mapping[str, Any], cid: str) -> bool:
    """§7 target_prefix_clean for a P1-admitted run: strict recompute —
    labels regenerated, tools re-run; stored semantic fields are never
    trusted (92_s §6.6)."""
    cases, labels = candidate_p1_cases(cid)
    by_id = {case.case_id: (case, label)
             for case, label in zip(cases, labels)}
    if len(run["cases"]) != P1_CASES:
        return False
    groups: dict[tuple, list[bool]] = {}
    for record in run["cases"]:
        if record["generation_hit_token_cap"]:
            return False
        case, label = by_id[record["case_id"]]
        result = contract.run_worker_output(
            _ENDPOINT_ID[case.endpoint_name], record["completion"],
            case.binding())
        groups.setdefault(
            (case.endpoint_name, label.cell_id, label.renderer_id),
            []).append(result.status == "success"
                       and result.value == label.expected_value)
    return all(len(outcomes) == P1_PER_CELL and all(outcomes)
               for outcomes in groups.values())


def screen_candidates(runs_dir: str | Path, tranche: str
                      ) -> dict[str, Any]:
    """§6.10 screening: expose only candidate id, admission/cost and the
    three-state prefix verdict; fix the full-run launch set (prefix-clean
    candidates plus one sentinel per contract) mechanically."""
    from .candidates import (REQUEST_CONTRACT_KEYS, arm_order,
                             sentinel_order)
    runs_dir = Path(runs_dir)
    table: dict[str, dict[str, Any]] = {}
    for cid in arm_order(tranche):
        paths = [runs_dir / f"{cid}.p1-{i}.json" for i in (1, 2, 3)]
        if not all(path.exists() for path in paths):
            table[cid] = {"status": "missing",
                          "target_prefix_clean": "NA"}
            continue
        runs = [json.loads(path.read_text(encoding="utf-8"))
                for path in paths]
        verdict = admit_singleton(runs, WORKER_DEV_NAMESPACE)
        table[cid] = {
            "status": "screened",
            "admitted": verdict["admitted"],
            "projected_full_run_seconds":
                verdict["projected_full_run_seconds"],
            "peak_vram_bytes": verdict["peak_vram_bytes"],
            "target_prefix_clean": (prefix_verdict(runs[0], cid)
                                    if verdict["admitted"] else "NA"),
        }
    launch = [cid for cid, entry in table.items()
              if entry.get("admitted")
              and entry["target_prefix_clean"] is True]
    sentinels = {}
    for contract_label in REQUEST_CONTRACT_KEYS:
        sentinels[contract_label] = next(
            (cid for cid in sentinel_order(contract_label, tranche)
             if table.get(cid, {}).get("admitted")), None)
        chosen = sentinels[contract_label]
        if chosen is not None and chosen not in launch:
            launch.append(chosen)
    return {"tranche": tranche, "candidates": table,
            "launch": launch, "sentinels": sentinels}


# §8 lexicographic selection orders (lower is better).
_CONTRACT_RANK = {"current": 0, "task_last": 1}
_PROMPT_RANK = {"rev9": 0, "code_local_v1": 1}


def reveal_tranche(runs_dir: str | Path,
                   screening: Mapping[str, Any]) -> dict[str, Any]:
    """§6.10 joint reveal: strict-load every launched full run, enforce
    unchanged-endpoint equality per contract, derive §4.1 target
    verdicts and apply the §8 mechanical selection."""
    from .candidates import (candidate_config, candidate_runtime_profile,
                             physical_layout)
    from .worker_eval import load_run
    runs_dir = Path(runs_dir)
    loaded = {cid: load_run(runs_dir / f"{cid}-full")
              for cid in screening["launch"]}
    # Unchanged-endpoint equality (§5): Lookup/Math generation fields are
    # byte-identical across arms sharing a contract.
    by_contract: dict[str, list[str]] = {}
    for cid in loaded:
        by_contract.setdefault(
            candidate_config(cid)["contract_label"], []).append(cid)
    for contract_label, cids in by_contract.items():
        reference: dict[str, tuple] = {}
        for cid in sorted(cids):
            for row in loaded[cid]["calls"]:
                if row["endpoint_name"] == "code":
                    continue
                key = row["case_id"]
                fields = (row["request_sha256"], row["completion"],
                          row["finish_reason"], row["generated_tokens"],
                          row["generation_hit_token_cap"])
                if key in reference and reference[key] != fields:
                    raise InfrastructureError(
                        f"unchanged endpoint call {key} differs across "
                        f"{contract_label!r} arms — reproducibility "
                        "stop (92_s §5)")
                reference.setdefault(key, fields)
    results = {}
    for cid, run in loaded.items():
        groups: dict[str, dict[str, int]] = {}
        for score in run["scores"]:
            key = "|".join((score["endpoint_name"], score["cell_id"],
                            score["renderer_id"]))
            entry = groups.setdefault(key, {"n": 0, "correct": 0})
            entry["n"] += 1
            entry["correct"] += int(score["node_correct"])
        outcomes = run["summary"]["isolated"]["outcomes"]
        target = (all(entry["n"] == 30 and entry["correct"] == 30
                      for entry in groups.values())
                  and outcomes["scheduled"] == outcomes["called"] == 900
                  and outcomes["envelope_failed"] == 0
                  and outcomes["grammar_failed"] == 0
                  and outcomes["token_cap"] == 0)
        results[cid] = {"groups": groups, "target": target}
    targets = sorted(
        (cid for cid, entry in results.items() if entry["target"]),
        key=lambda cid: (
            physical_layout(candidate_runtime_profile(cid))[
                "declared_parameter_sum"],
            physical_layout(candidate_runtime_profile(cid))[
                "unique_checkpoints"],
            _CONTRACT_RANK[candidate_config(cid)["contract_label"]],
            _PROMPT_RANK[candidate_config(cid)["code_prompt"]],
            cid))
    return {"tranche": screening["tranche"], "results": results,
            "selected": targets[0] if targets else None}


# --- command line ------------------------------------------------------------

def _write_output(path: str, payload: Mapping[str, Any]) -> None:
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, sort_keys=True)
        handle.write("\n")


def _build_real(device: str):
    from .prompts import resolve_prompts
    from .workers import WorkerPool
    profile = copy.deepcopy(DEFAULT_RUNTIME_PROFILE)
    pool = WorkerPool(profile, device=device, prompts=resolve_prompts())
    runtime = build_runtime(profile, pool=pool, cache=NullCache())
    return profile, pool, runtime


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("p1", help="one fresh-process singleton pass")
    p1.add_argument("--candidate", default=None,
                    help="registered 92_s candidate id; resolves the "
                         "exact profile, prompts and request contract")
    p1.add_argument("--namespace", default=None,
                    help="diagnostic mode only; ignored with --candidate")
    p1.add_argument("--per-cell", type=int, default=10)
    p1.add_argument("--order", choices=["canonical", "reversed"],
                    default="canonical")
    p1.add_argument("--renderers", nargs="+", default=list(RENDERER_IDS))
    p1.add_argument("--visibility", default="private")
    p1.add_argument("--out", required=True)
    p1.add_argument("--device", default="cuda")

    runp = sub.add_parser("run", help="92_s §6.7 candidate evaluation")
    runp.add_argument("--candidate", required=True)
    runp.add_argument("--mode", choices=["isolated", "composed"],
                      default="isolated")
    runp.add_argument("--run-dir", required=True)
    runp.add_argument("--device", default="cuda")

    scr = sub.add_parser("screen", help="92_s §6.10 P1 screening table + "
                                        "launch manifest")
    scr.add_argument("--runs-dir", required=True)
    scr.add_argument("--tranche", choices=["A", "B"], required=True)
    scr.add_argument("--out", required=True)

    rev = sub.add_parser("reveal", help="92_s §6.10 joint reveal after "
                                        "all launched full runs complete")
    rev.add_argument("--runs-dir", required=True)
    rev.add_argument("--screening", required=True)
    rev.add_argument("--out", required=True)

    p0 = sub.add_parser("p0", help="replay a frozen physical cohort")
    p0.add_argument("--cohort", required=True)
    p0.add_argument("--condition",
                    choices=["original", "reversed", "singleton"],
                    required=True)
    p0.add_argument("--out", required=True)
    p0.add_argument("--device", default="cuda")

    cmp_parser = sub.add_parser("compare",
                                help="field-wise diff of two outputs")
    cmp_parser.add_argument("left")
    cmp_parser.add_argument("right")

    adm = sub.add_parser("admit", help="§7.3 singleton-v1 verdict")
    adm.add_argument("runs", nargs=3)
    # Hard-bound to the registered worker_dev universe (88_f §3.3 as
    # amended per 89_s): the public Gate-D commands take no namespace
    # override; diagnostics against other namespaces use the Python
    # functions, whose output is never the Gate-D wording.
    adm.add_argument("--max-seconds", type=int,
                     default=MAX_FULL_RUN_SECONDS)
    adm.add_argument("--max-vram-gib", type=float, default=None)

    conf = sub.add_parser(
        "confirm", help="§7.4 full-run repeat confirmation for a "
                        "candidate (two evaluator run directories)")
    conf.add_argument("left")
    conf.add_argument("right")

    args = ap.parse_args(argv)

    if args.command == "p1":
        if args.candidate:
            from .candidates import (candidate_config,
                                     candidate_runtime_profile)
            from .workers import WorkerPool
            config = candidate_config(args.candidate)
            profile = candidate_runtime_profile(args.candidate)
            pool = WorkerPool(profile, device=args.device)
            runtime = build_runtime(profile, pool=pool, cache=NullCache())
            cases, labels = (list(part) for part in
                             candidate_p1_cases(args.candidate))
            extra = {
                "candidate": args.candidate,
                "request_contract": resolve_request_contract(
                    config["request_contract_key"]),
                "sequence_sha256": sequence_hashes(
                    [case.case_id for case in cases]),
                "namespace": WORKER_DEV_NAMESPACE,
                "per_cell": P1_PER_CELL,
                "renderers": list(RENDERER_IDS),
                "visibility": "private",
            }
        else:
            if not args.namespace:
                ap.error("p1 requires --candidate or --namespace")
            profile, pool, runtime = _build_real(args.device)
            cases, labels = build_probe_cases(
                args.namespace, args.per_cell, list(args.renderers),
                args.visibility)
            extra = {"namespace": args.namespace,
                     "per_cell": args.per_cell,
                     "renderers": list(args.renderers),
                     "visibility": args.visibility}
        records, wall, vram = run_p1_cases(runtime, cases, labels,
                                           args.order)
        _write_output(args.out, _header(
            "p1", pool, profile, order=args.order, wall_seconds=wall,
            peak_vram_bytes=vram, cases=records, **extra))
        print(f"p1 {args.order}: {len(records)} cases in {wall:.1f}s, "
              f"peak VRAM {vram} B -> {args.out}")
        return 0

    if args.command == "run":
        writer = run_candidate(args.candidate, args.mode, args.run_dir,
                               device=args.device)
        print(f"candidate {args.candidate} {args.mode} run complete -> "
              f"{args.run_dir} (manifest sha {writer.manifest_sha256})")
        return 0

    if args.command == "screen":
        screening = screen_candidates(args.runs_dir, args.tranche)
        _write_output(args.out, screening)
        digest = hashlib.sha256(
            Path(args.out).read_bytes()).hexdigest()
        for cid, entry in screening["candidates"].items():
            print(f"{cid}: admitted={entry.get('admitted')} "
                  f"prefix={entry.get('target_prefix_clean')}")
        print(f"launch: {screening['launch']}")
        print(f"sentinels: {screening['sentinels']}")
        print(f"screening manifest sha256 {digest} -> {args.out}")
        return 0

    if args.command == "reveal":
        screening = json.loads(
            Path(args.screening).read_text(encoding="utf-8"))
        outcome = reveal_tranche(args.runs_dir, screening)
        _write_output(args.out, outcome)
        for cid, entry in outcome["results"].items():
            print(f"{cid}: target={entry['target']}")
        print(f"selected: {outcome['selected']} -> {args.out}")
        return 0

    if args.command == "p0":
        cohort = json.loads(Path(args.cohort).read_text(encoding="utf-8"))
        profile, pool, runtime = _build_real(args.device)
        endpoint, chunks = load_cohort(cohort, runtime_profile=profile)
        records, wall, vram = run_p0_condition(pool, runtime, endpoint,
                                               chunks, args.condition)
        _write_output(args.out, _header(
            "p0", pool, profile, condition=args.condition,
            cohort_sha256=hashlib.sha256(
                Path(args.cohort).read_bytes()).hexdigest(),
            endpoint=endpoint, wall_seconds=wall, peak_vram_bytes=vram,
            cases=records))
        print(f"p0 {args.condition}: {len(records)} cases in {wall:.1f}s "
              f"-> {args.out}")
        return 0

    if args.command == "compare":
        left = json.loads(Path(args.left).read_text(encoding="utf-8"))
        right = json.loads(Path(args.right).read_text(encoding="utf-8"))
        try:
            diffs = compare_probe_outputs(left, right)
        except InfrastructureError as error:
            print(f"NOT COMPARABLE: {error}")
            return 2
        for diff in diffs:
            print(f"{diff['case_id']}:")
            for field, sides in sorted(diff["fields"].items()):
                print(f"  {field}: {sides['left']!r} != "
                      f"{sides['right']!r}")
        print(f"{len(diffs)} of {len(left['cases'])} cases differ")
        return 1 if diffs else 0

    if args.command == "admit":
        runs = [json.loads(Path(path).read_text(encoding="utf-8"))
                for path in args.runs]
        max_vram = (int(args.max_vram_gib * 2 ** 30)
                    if args.max_vram_gib is not None
                    else MAX_PEAK_VRAM_BYTES)
        verdict = admit_singleton(runs, WORKER_DEV_NAMESPACE,
                                  max_seconds=args.max_seconds,
                                  max_vram_bytes=max_vram)
        print(json.dumps(verdict, indent=1, sort_keys=True))
        print("ADMIT singleton-v1" if verdict["admitted"]
              else "FAIL: singleton-v1 not admitted (see §7.4: stop and "
                   "write the follow-up decision plan)")
        return 0 if verdict["admitted"] else 1

    if args.command == "confirm":
        from .worker_eval import confirm_repeat_run, load_run
        # The CLI always enforces the full §7.4 population against the
        # registered namespace; only the Python functions accept other
        # namespaces, for tests and diagnostics.
        verdict = confirm_repeat_run(load_run(args.left),
                                     load_run(args.right),
                                     WORKER_DEV_NAMESPACE)
        print(json.dumps(verdict, indent=1, sort_keys=True))
        print("CONFIRMED: repeat run is generation-identical"
              if verdict["confirmed"]
              else "FAIL: repeat run differs; the candidate result is "
                   "not confirmed (81_f §7.4)")
        return 0 if verdict["confirmed"] else 1

    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
