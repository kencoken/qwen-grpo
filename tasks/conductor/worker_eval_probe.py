"""P0/P1 generation-policy probes — recorded commands (plan 81_f §7).

P0 replays retained batch-sensitivity regressions: a frozen cohort
manifest lists the exact physical `model.generate` chunks (ordered case
references), and the probe drives `pool.generate` directly with the
original grouping, the reversed within-chunk order, or the scientific
singleton path. Differences between conditions are retained findings,
not tool failures.

P1 is the `singleton-v1` admissibility gate: one invocation = one fresh
process running the pre-registered sample in canonical or reversed
order; the `admit` subcommand takes two canonical-order runs and one
reversed-order run and admits only on exact generation-field equality
within the frozen cost gate (§7.3). If admission fails, stop and write
the §7.4 follow-up decision plan — do not fall back to the cache.

Run (each invocation is its own fresh process):

  uv run python -m tasks.conductor.worker_eval_probe p1 \
      --namespace worker_dev --per-cell 10 --order canonical --out r1.json
  uv run python -m tasks.conductor.worker_eval_probe p0 \
      --cohort chunks.json --condition reversed --out p0-rev.json
  uv run python -m tasks.conductor.worker_eval_probe compare a.json b.json
  uv run python -m tasks.conductor.worker_eval_probe admit r1.json r2.json r3.json
"""

from __future__ import annotations

import argparse
import copy
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
    node_cases_for_latent, singleton_call,
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
                      profile: Mapping[str, Any] | None = None
                      ) -> tuple[list[WorkerEvalCase], list[NodeLabel]]:
    latents = probe_latents(namespace, per_cell, profile)
    assert_probe_coverage(latents)
    cases: list[WorkerEvalCase] = []
    labels: list[NodeLabel] = []
    for latent in latents:
        latent_cases, latent_labels = node_cases_for_latent(
            latent, renderers, visibility)
        cases.extend(latent_cases)
        labels.extend(latent_labels)
    return cases, labels


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
    """One fresh-process singleton pass over the pre-registered sample,
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
                profile: Mapping[str, Any] | None = None
                ) -> tuple[str, list[list[tuple[WorkerEvalCase,
                                                NodeLabel]]]]:
    """Regenerate the cohort's cases from the frozen generator. Each chunk
    entry names one reference node; an optional pinned
    `user_message_sha256` must match the regenerated request exactly."""
    endpoint = cohort["endpoint"]
    if endpoint not in ENDPOINT_NAMES.values():
        raise ProfileError(f"unknown endpoint {endpoint!r}")
    chunks: list[list[tuple[WorkerEvalCase, NodeLabel]]] = []
    for chunk in cohort["chunks"]:
        resolved = []
        for entry in chunk:
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
            actual = hashlib.sha256(
                case.user_message.encode("utf-8")).hexdigest()
            if pinned is not None and pinned != actual:
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


def admit_singleton(runs: list[Mapping[str, Any]],
                    max_seconds: int = MAX_FULL_RUN_SECONDS,
                    max_vram_bytes: int = MAX_PEAK_VRAM_BYTES,
                    full_cases: int = 900) -> dict[str, Any]:
    """The §7.3 verdict over three fresh-process P1 outputs (canonical,
    canonical, reversed). Exact generation-field equality for every case
    plus the frozen cost gate, or FAIL — there is no partial credit."""
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
    for index in (1, 2):
        for diff in compare_records(runs[0]["cases"], runs[index]["cases"]):
            unequal = [field for field in diff["fields"]
                       if field in GENERATION_EQUALITY_FIELDS]
            if unequal:
                reasons.append(
                    f"run {index + 1} vs run 1: {diff['case_id']} "
                    f"differs on {unequal}")
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
        "projected_full_run_seconds": max(projected),
        "peak_vram_bytes": (max(vram)
                            if all(v is not None for v in vram) else None),
    }


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
    p1.add_argument("--namespace", required=True)
    p1.add_argument("--per-cell", type=int, default=10)
    p1.add_argument("--order", choices=["canonical", "reversed"],
                    default="canonical")
    p1.add_argument("--renderers", nargs="+", default=list(RENDERER_IDS))
    p1.add_argument("--visibility", default="private")
    p1.add_argument("--out", required=True)
    p1.add_argument("--device", default="cuda")

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
    adm.add_argument("--max-seconds", type=int,
                     default=MAX_FULL_RUN_SECONDS)
    adm.add_argument("--max-vram-gib", type=float, default=None)

    args = ap.parse_args(argv)

    if args.command == "p1":
        profile, pool, runtime = _build_real(args.device)
        cases, labels = build_probe_cases(
            args.namespace, args.per_cell, list(args.renderers),
            args.visibility)
        records, wall, vram = run_p1_cases(runtime, cases, labels,
                                           args.order)
        _write_output(args.out, _header(
            "p1", pool, profile, order=args.order,
            namespace=args.namespace, per_cell=args.per_cell,
            renderers=list(args.renderers), visibility=args.visibility,
            wall_seconds=wall, peak_vram_bytes=vram, cases=records))
        print(f"p1 {args.order}: {len(records)} cases in {wall:.1f}s, "
              f"peak VRAM {vram} B -> {args.out}")
        return 0

    if args.command == "p0":
        cohort = json.loads(Path(args.cohort).read_text(encoding="utf-8"))
        profile, pool, runtime = _build_real(args.device)
        endpoint, chunks = load_cohort(cohort)
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
        diffs = compare_records(left["cases"], right["cases"])
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
        verdict = admit_singleton(runs, max_seconds=args.max_seconds,
                                  max_vram_bytes=max_vram)
        print(json.dumps(verdict, indent=1, sort_keys=True))
        print("ADMIT singleton-v1" if verdict["admitted"]
              else "FAIL: singleton-v1 not admitted (see §7.4: stop and "
                   "write the follow-up decision plan)")
        return 0 if verdict["admitted"] else 1

    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
