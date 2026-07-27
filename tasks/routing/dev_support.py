"""Development-namespace payoff surfaces (211_f §4).

The Stage-0 `payoff_support` machinery is frozen (SOURCE_DIGEST_FILES),
so this module re-implements the declaration → materialization →
fail-closed reload lifecycle PARAMETERIZED by cohort, importing the
frozen executable pieces (assignment enumeration, workflow items,
terminal scoring, trace writer) rather than copying them. Differences
from the Stage-0 support, all deliberate:

- the cohort (namespace, per-cell latent indices, renderers,
  visibility) is an argument, frozen per tranche — not module
  constants; the declaration is persisted INSIDE the surface directory
  and hash-bound by the manifest (the tranche freeze commits it too);
- disclosure is a first-class product: `direction_yields` reports
  every materialized row's direction so nothing screened is silent
  (211_f §4 step 4);
- `select_c_fixed_dev` (210_s issue 1) is selected here, on the
  outcome-blind support, and persisted with both candidate scores.

Every surface this module produces is development data permanently.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping

from tasks.conductor import executor, oracle, program
from tasks.conductor.payoff_support import (
    _assignment_items, _exact_int, _sha_file,
)
from tasks.conductor.pool_runtime import PoolTraceWriter
from tasks.conductor.profiles import DEFAULT_PROFILE
from tasks.conductor.stage1 import NODE_FAMILIES, WORKER_FAMILIES
from tasks.conductor.stage1_replay import eligible_pair_table
from tasks.conductor.types import CELL_IDS, InfrastructureError
from tasks.conductor.workerpool import STAGE0_POOL_FINGERPRINT, WORKER_IDS

from .charter import DEV_NAMESPACES, content_sha256

DEV_SURFACE_SCHEMA_VERSION = 1
_DEV_MANIFEST_KEYS = frozenset({
    "surface_schema_version", "support", "declaration_sha256",
    "worker_visible_fingerprint", "runtime_profile_fingerprint",
    "worker_pool_fingerprint", "planned_step_executions",
    "executed_step_records", "uncached_step_records",
    "unique_singleton_generations", "cache_hits", "payoff_rows",
    "wall_seconds", "payoffs_sha256", "trace_manifest_sha256",
    "trace_steps_sha256",
})
_ROW_KEYS = frozenset({"observation_id", "assignment", "payoff",
                       "terminal_value", "step_statuses"})


# --- cohorts and observations -------------------------------------------------

def validate_dev_cohort(namespace: str,
                        cohort: Mapping[str, Any],
                        renderers: tuple[str, ...] | list[str],
                        visibility: str) -> None:
    """A development cohort spec is exact: a dev namespace, per-cell
    duplicate-free integer index lists inside the namespace cap, known
    renderers, one visibility condition."""
    from tasks.conductor.program import namespace_cap
    from tasks.conductor.types import RENDERER_IDS, VISIBILITY_CONDITIONS
    if namespace not in DEV_NAMESPACES:
        raise InfrastructureError(
            f"{namespace!r} is not a development namespace "
            f"{DEV_NAMESPACES}")
    if not cohort:
        raise InfrastructureError("empty development cohort")
    for cell, indices in cohort.items():
        if cell not in CELL_IDS:
            raise InfrastructureError(f"unknown cell {cell!r}")
        if not indices or not isinstance(indices, (list, tuple)):
            raise InfrastructureError(f"{cell}: empty index list")
        seen = set()
        cap = namespace_cap(namespace, cell)
        for idx in indices:
            if not isinstance(idx, int) or isinstance(idx, bool):
                raise InfrastructureError(
                    f"{cell}: non-integer latent index {idx!r}")
            if not 0 <= idx < cap:
                raise InfrastructureError(
                    f"{cell}: index {idx} outside [0, {cap})")
            if idx in seen:
                raise InfrastructureError(
                    f"{cell}: duplicate latent index {idx}")
            seen.add(idx)
    if not renderers:
        raise InfrastructureError("cohort declares no renderers")
    if len(set(renderers)) != len(renderers) \
            or any(r not in RENDERER_IDS for r in renderers):
        raise InfrastructureError(
            f"renderers {renderers!r} must be distinct members of "
            f"{RENDERER_IDS}")
    if visibility not in VISIBILITY_CONDITIONS:
        raise InfrastructureError(f"unknown visibility {visibility!r}")


def dev_cohort_observations(namespace: str,
                            cohort: Mapping[str, Any],
                            renderers: tuple[str, ...] | list[str],
                            visibility: str) -> list[dict[str, Any]]:
    """Regenerate the cohort's observations from the frozen generator in
    canonical (cell, index, renderer) order — the declaration verifies
    these, never the other way around."""
    validate_dev_cohort(namespace, cohort, renderers, visibility)
    observations = []
    for cell in sorted(cohort):
        for index in sorted(cohort[cell]):
            latent = program.generate_latent(
                cell, namespace, index, DEFAULT_PROFILE).latent
            positions = latent["reference_program"]["positions"]
            for renderer in renderers:
                inst = program.render_instance(latent, renderer,
                                               visibility)
                observations.append({
                    "observation_id": inst["render_instance_id"],
                    "cell_id": cell,
                    "renderer_id": renderer,
                    "latent_program_id": latent["latent_program_id"],
                    "num_nodes": len(positions),
                    "latent": latent,
                    "instance": inst,
                })
    return observations


# --- declaration ---------------------------------------------------------------

def build_dev_declaration(pool: Any, *, tag: str, namespace: str,
                          cohort: Mapping[str, Any],
                          renderers: tuple[str, ...] | list[str],
                          visibility: str) -> dict[str, Any]:
    """Identities + fingerprints + the exact cohort spec, computed from
    a pool bound to the frozen profile, BEFORE materialization. The
    tranche freeze commits this record; materialization persists it
    beside the surface and binds it by content hash."""
    import hashlib
    profile = pool.profile
    from tasks.conductor.pool_runtime import (
        pool_worker_visible_fingerprint,
    )
    chat_shas, system_shas = {}, {}
    for entry in profile["worker_pool"]:
        worker_id, name = entry["worker_id"], entry["name"]
        chat_shas[name] = pool.chat_template_sha(worker_id)
        system_shas[name] = hashlib.sha256(pool.system_prompt(
            worker_id).encode("utf-8")).hexdigest()
    observations = dev_cohort_observations(namespace, cohort, renderers,
                                           visibility)
    planned = sum(len(oracle.enumerate_assignments(obs["num_nodes"]))
                  * obs["num_nodes"] for obs in observations)
    return {
        "support": tag,
        "namespace": namespace,
        "cohort": {cell: sorted(cohort[cell]) for cell in sorted(cohort)},
        "renderers": list(renderers),
        "visibility": visibility,
        "observations": [
            {"observation_id": obs["observation_id"],
             "cell_id": obs["cell_id"],
             "renderer_id": obs["renderer_id"],
             "num_nodes": obs["num_nodes"],
             "assignments": len(oracle.enumerate_assignments(
                 obs["num_nodes"]))}
            for obs in observations],
        "planned_step_executions": planned,
        "worker_ids": list(WORKER_IDS),
        "worker_pool_fingerprint": STAGE0_POOL_FINGERPRINT,
        "worker_visible_fingerprint": pool_worker_visible_fingerprint(
            profile, chat_shas, system_shas),
        "request_contract": profile["request_contract"],
        "prompt_revision": profile["prompts"]["d16_revision"],
        "device": profile["device"],
    }


def _verify_dev_declaration(declaration: Mapping[str, Any],
                            observations: list[dict[str, Any]]) -> None:
    """Verify the COMPLETE regenerated cohort description against the
    declaration — identities, cells, renderers, arities, assignment
    counts and the cohort spec itself."""
    regenerated = [
        {"observation_id": obs["observation_id"],
         "cell_id": obs["cell_id"],
         "renderer_id": obs["renderer_id"],
         "num_nodes": obs["num_nodes"],
         "assignments": len(oracle.enumerate_assignments(
             obs["num_nodes"]))}
        for obs in observations]
    checks = {
        "observations": regenerated,
        "planned_step_executions": sum(
            obs["assignments"] * obs["num_nodes"]
            for obs in regenerated),
        "worker_ids": list(WORKER_IDS),
        "worker_pool_fingerprint": STAGE0_POOL_FINGERPRINT,
    }
    for key, expected in checks.items():
        if declaration.get(key) != expected:
            raise InfrastructureError(
                f"dev declaration field {key!r} does not match the "
                "regenerated cohort description; the generator or the "
                "declaration moved")


# --- materialization -----------------------------------------------------------

def materialize_dev_support(rt: Any, declaration: Mapping[str, Any],
                            out_dir: str | Path) -> dict[str, Any]:
    """Execute the complete declared 4^S surface through a runtime whose
    identity matches the declaration, with a v2 trace. Mirrors the
    frozen Stage-0 materializer; the declaration is an argument and is
    persisted beside the surface."""
    for key, expected in (
            ("worker_visible_fingerprint", rt.worker_visible_fingerprint),
            ("worker_pool_fingerprint", rt.pool_fingerprint)):
        if declaration[key] != expected:
            raise InfrastructureError(
                f"runtime {key} {expected} does not match the declared "
                f"{declaration[key]}; the support binds one execution "
                "identity")
    if rt.profile["visibility_condition"] != declaration["visibility"]:
        raise InfrastructureError(
            f"runtime visibility {rt.profile['visibility_condition']!r} "
            f"does not match the declared {declaration['visibility']!r}")
    out_dir = Path(out_dir)
    payoff_path = out_dir / "payoffs.jsonl"
    manifest_path = out_dir / "manifest.json"
    declaration_path = out_dir / "declaration.json"
    if payoff_path.exists() or manifest_path.exists() \
            or declaration_path.exists():
        raise InfrastructureError(
            f"{out_dir} already holds a materialized surface; refusing "
            "to overwrite a recorded artifact")
    out_dir.mkdir(parents=True, exist_ok=True)

    observations = dev_cohort_observations(
        declaration["namespace"], declaration["cohort"],
        declaration["renderers"], declaration["visibility"])
    _verify_dev_declaration(declaration, observations)
    declaration_path.write_text(
        json.dumps(declaration, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")

    started = time.monotonic()
    generations_before = getattr(rt.pool, "singleton_generations", 0)
    executed_steps = 0
    uncached_records = 0
    cache_hits = 0
    rows = []
    with PoolTraceWriter("traces", rt, base_dir=out_dir) as trace:
        for obs in observations:
            gold = obs["instance"]["gold_answer"]
            pairs = _assignment_items(
                obs, rt.profile["request_contract"])
            results, telemetry = rt.execute_batch(
                [item for _, item in pairs], trace=trace)
            for record_pair, result in zip(pairs, results):
                assignment, _item = record_pair
                payoff = executor.score_terminal(result.terminal, gold)
                executed_steps += sum(
                    1 for step in result.steps
                    if step.completion is not None)
                rows.append({
                    "observation_id": obs["observation_id"],
                    "assignment": list(assignment),
                    "payoff": payoff,
                    "terminal_value": result.terminal,
                    "step_statuses": [
                        step.result.status if step.result
                        else f"world:{step.world_failure}"
                        for step in result.steps],
                })
            uncached_records += sum(
                1 for _, record in telemetry if not record.cache_hit)
            cache_hits += sum(
                1 for _, record in telemetry if record.cache_hit)
    wall = time.monotonic() - started

    with payoff_path.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    trace_dir = out_dir / "traces" / "traces"
    manifest = {
        "surface_schema_version": DEV_SURFACE_SCHEMA_VERSION,
        "support": declaration["support"],
        "declaration_sha256": _sha_file(declaration_path),
        "worker_visible_fingerprint": rt.worker_visible_fingerprint,
        "runtime_profile_fingerprint": rt.runtime_profile_fingerprint,
        "worker_pool_fingerprint": rt.pool_fingerprint,
        "planned_step_executions":
            declaration["planned_step_executions"],
        "executed_step_records": executed_steps,
        "uncached_step_records": uncached_records,
        "unique_singleton_generations":
            getattr(rt.pool, "singleton_generations", 0)
            - generations_before,
        "cache_hits": cache_hits,
        "payoff_rows": len(rows),
        "wall_seconds": round(wall, 1),
        "payoffs_sha256": _sha_file(payoff_path),
        "trace_manifest_sha256": _sha_file(trace_dir / "manifest.json"),
        "trace_steps_sha256": _sha_file(trace_dir / "steps.jsonl"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=1,
                                        sort_keys=True) + "\n",
                             encoding="utf-8")
    return manifest


# --- fail-closed loader ----------------------------------------------------------

def load_dev_surface(out_dir: str | Path) -> dict[str, Any]:
    """Mirror of the frozen Stage-0 loader for a persisted development
    declaration: complete coverage over the declared 4^S space, every
    payoff independently re-scored from its stored terminal value
    against the regenerated gold, artifacts bound by content hash,
    trace complete with the same execution identity. Returns
    {"surface", "declaration", "observations", "manifest"}."""
    out_dir = Path(out_dir)
    declaration_path = out_dir / "declaration.json"
    if not declaration_path.exists():
        raise InfrastructureError(
            f"{out_dir} holds no declaration.json — not a development "
            "surface directory")
    declaration = json.loads(declaration_path.read_text(encoding="utf-8"))
    observations = dev_cohort_observations(
        declaration["namespace"], declaration["cohort"],
        declaration["renderers"], declaration["visibility"])
    _verify_dev_declaration(declaration, observations)
    golds = {obs["observation_id"]: obs["instance"]["gold_answer"]
             for obs in observations}

    manifest = json.loads((out_dir / "manifest.json").read_text(
        encoding="utf-8"))
    if set(manifest) != _DEV_MANIFEST_KEYS:
        raise InfrastructureError(
            f"surface manifest keys {sorted(manifest)} != the exact "
            f"schema {sorted(_DEV_MANIFEST_KEYS)}")
    if manifest["surface_schema_version"] != DEV_SURFACE_SCHEMA_VERSION:
        raise InfrastructureError(
            f"surface schema {manifest['surface_schema_version']!r} is "
            f"not {DEV_SURFACE_SCHEMA_VERSION}")
    if manifest["declaration_sha256"] != _sha_file(declaration_path):
        raise InfrastructureError(
            "surface was materialized against a different declaration; "
            "regenerate rather than reinterpret")
    if manifest["support"] != declaration["support"]:
        raise InfrastructureError(
            "manifest support tag does not match the declaration")
    for key in ("worker_visible_fingerprint", "worker_pool_fingerprint"):
        if manifest[key] != declaration[key]:
            raise InfrastructureError(
                f"surface manifest {key} does not match the declaration")
    if manifest["payoffs_sha256"] != _sha_file(out_dir / "payoffs.jsonl"):
        raise InfrastructureError(
            "payoffs.jsonl does not match the manifest content hash")
    trace_dir = out_dir / "traces" / "traces"
    for name, claimed in (("manifest.json",
                           manifest["trace_manifest_sha256"]),
                          ("steps.jsonl", manifest["trace_steps_sha256"])):
        if _sha_file(trace_dir / name) != claimed:
            raise InfrastructureError(
                f"trace {name} does not match the manifest content hash")
    trace_manifest = json.loads(
        (trace_dir / "manifest.json").read_text(encoding="utf-8"))
    if not trace_manifest.get("closed") \
            or trace_manifest.get("status") != "complete":
        raise InfrastructureError(
            "surface trace is not a complete closed run")
    for surface_key, trace_key in (
            ("worker_visible_fingerprint", "worker_visible_fingerprint"),
            ("worker_pool_fingerprint", "worker_pool_fingerprint"),
            ("runtime_profile_fingerprint",
             "runtime_profile_fingerprint")):
        if manifest[surface_key] != trace_manifest[trace_key]:
            raise InfrastructureError(
                f"trace {trace_key} does not match the surface manifest")
    if trace_manifest["steps_written"] != \
            declaration["planned_step_executions"]:
        raise InfrastructureError(
            f"trace holds {trace_manifest['steps_written']} step rows; "
            f"the declared plan is "
            f"{declaration['planned_step_executions']}")
    if not (0 < manifest["unique_singleton_generations"]
            <= manifest["uncached_step_records"]
            <= manifest["executed_step_records"]
            <= declaration["planned_step_executions"]):
        raise InfrastructureError(
            "surface accounting invariants do not hold")
    if manifest["uncached_step_records"] + manifest["cache_hits"] != \
            manifest["executed_step_records"]:
        raise InfrastructureError(
            "cache accounting does not reconcile with executed records")

    expected: set[tuple[str, tuple[int, ...]]] = set()
    for obs in declaration["observations"]:
        for assignment in oracle.enumerate_assignments(obs["num_nodes"]):
            expected.add((obs["observation_id"], assignment))
    if manifest["payoff_rows"] != len(expected):
        raise InfrastructureError(
            f"manifest declares {manifest['payoff_rows']} payoff rows; "
            f"the declared support requires {len(expected)}")
    surface: dict[tuple[str, tuple[int, ...]], float] = {}
    with (out_dir / "payoffs.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if not isinstance(row, dict) or set(row) != _ROW_KEYS:
                raise InfrastructureError(
                    f"payoff row keys must be exactly {sorted(_ROW_KEYS)}")
            if not isinstance(row["observation_id"], str) \
                    or not isinstance(row["assignment"], list) \
                    or not all(_exact_int(w) for w in row["assignment"]):
                raise InfrastructureError(
                    "payoff row identity fields are mistyped (bools and "
                    "floats alias integer ids)")
            key = (row["observation_id"], tuple(row["assignment"]))
            if key not in expected:
                raise InfrastructureError(
                    f"payoff row {key!r} is not in the declared support")
            if key in surface:
                raise InfrastructureError(f"duplicate payoff row {key!r}")
            terminal = row["terminal_value"]
            if terminal is not None and not _exact_int(terminal):
                raise InfrastructureError(
                    f"terminal_value {terminal!r} is not an exact int")
            rescored = executor.score_terminal(
                terminal, golds[row["observation_id"]])
            if row["payoff"] != rescored:
                raise InfrastructureError(
                    f"row {key!r}: persisted payoff {row['payoff']!r} != "
                    f"re-scored {rescored} from its terminal value")
            surface[key] = rescored
    missing = expected - set(surface)
    if missing:
        raise InfrastructureError(
            f"surface is incomplete: {len(missing)} declared rows "
            f"missing (e.g. {sorted(missing)[:3]})")
    meta = [{key: obs[key] for key in
             ("observation_id", "cell_id", "renderer_id",
              "latent_program_id", "num_nodes")}
            for obs in observations]
    return {"surface": surface, "declaration": declaration,
            "observations": meta, "manifest": manifest}


# --- disclosure: direction yields (211_f §4 step 4) ---------------------------

def direction_yields(surface: Mapping[tuple[str, tuple[int, ...]], float],
                     observations: list[Mapping[str, Any]]
                     ) -> dict[str, Any]:
    """Every materialized observation's payoff direction, disclosed —
    per cell and in total. Code-free cells are 'no_pair'. Uses the
    frozen family-correct variant-pair table."""
    cell_of = {obs["observation_id"]: obs["cell_id"]
               for obs in observations}
    surface_rows = [{"observation_id": oid, "assignment": list(a),
                     "payoff": p}
                    for (oid, a), p in surface.items()]
    table = eligible_pair_table(surface_rows, cell_of)
    per_observation: dict[str, str] = {}
    for oid in sorted(cell_of):
        if oid not in table:
            per_observation[oid] = "no_pair"
            continue
        entry = table[oid]
        if not entry["distinct_payoff"]:
            per_observation[oid] = "tied"
        else:
            per_observation[oid] = f"w{entry['direction']}_favoured"
    yields: dict[str, dict[str, int]] = {}
    for oid, direction in per_observation.items():
        cell = cell_of[oid]
        bucket = yields.setdefault(cell, {
            "w2_favoured": 0, "w3_favoured": 0, "tied": 0, "no_pair": 0})
        bucket[direction] += 1
    return {"per_observation": per_observation, "per_cell": yields,
            "pair_table": {oid: {k: v for k, v in entry.items()}
                           for oid, entry in table.items()}}


# --- c_fixed_dev (210_s issue 1) ----------------------------------------------

def select_c_fixed_dev(surface: Mapping[tuple[str, tuple[int, ...]], float],
                       observations: list[Mapping[str, Any]],
                       surface_hashes: Mapping[str, str]
                       ) -> dict[str, Any]:
    """The development best-fixed-Code comparator: for each candidate
    w ∈ {2, 3}, the equal-weight family-correct terminal payoff —
    renderer-within-latent, latent-within-cell, equal weights over the
    Code-bearing cells — of the assignment that is family-correct at
    every non-Code node with the (unique) Code node fixed to w.
    Tie → worker 2. Persisted with both candidate scores, the rule,
    and the source surface hashes; development-only forever."""
    code_cells: dict[str, dict[str, dict[str, dict[int, float]]]] = {}
    for obs in observations:
        cell = obs["cell_id"]
        families = NODE_FAMILIES[cell]
        code_nodes = [n for n, f in sorted(families.items())
                      if f == "code"]
        if not code_nodes:
            continue
        if len(code_nodes) != 1:
            raise InfrastructureError(
                f"{cell}: multiple Code nodes — the collapse is not "
                "unique; the contract must be revisited")
        payoffs: dict[int, float] = {}
        for w in (2, 3):
            assignment = []
            for node in sorted(families):
                family = families[node]
                if family == "code":
                    assignment.append(w)
                else:
                    (member,) = [wid for wid, fam in
                                 WORKER_FAMILIES.items() if fam == family]
                    assignment.append(member)
            key = (obs["observation_id"], tuple(assignment))
            if key not in surface:
                raise InfrastructureError(
                    f"{key!r}: family-correct variant row missing from "
                    "the surface")
            payoffs[w] = surface[key]
        code_cells.setdefault(cell, {}).setdefault(
            obs["latent_program_id"], {})[obs["observation_id"]] = payoffs
    if not code_cells:
        raise InfrastructureError(
            "no Code-bearing observations — c_fixed_dev is undefined")
    scores: dict[int, float] = {}
    for w in (2, 3):
        cell_means = []
        for latents in code_cells.values():
            latent_means = []
            for members in latents.values():
                latent_means.append(
                    sum(p[w] for p in members.values()) / len(members))
            cell_means.append(sum(latent_means) / len(latent_means))
        scores[w] = sum(cell_means) / len(cell_means)
    tie = scores[2] == scores[3]
    selected = 2 if scores[2] >= scores[3] else 3
    record = {
        "comparator": "c_fixed_dev-v1",
        "rule": ("argmax over w in {2,3} of equal-weight family-correct "
                 "terminal payoff, renderer-within-latent, "
                 "latent-within-cell, equal Code-bearing cell weights; "
                 "tie -> worker 2 (211_f section 4)"),
        "candidate_scores": {"2": scores[2], "3": scores[3]},
        "tie": tie,
        "c_fixed_dev": selected,
        "code_bearing_cells": sorted(code_cells),
        "surface_hashes": dict(sorted(surface_hashes.items())),
        "development_only": True,
    }
    record["record_sha256"] = content_sha256(record)
    return record
