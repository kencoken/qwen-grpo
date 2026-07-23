"""Stage-0 diagnostic payoff support — 106_s §9.4 (unit 3).

The fixed support is **identity-selected**: the first `worker_dev`
latent by frozen generator ordinal in each of the six cells, crossed
with the three private renderers — 18 observations chosen before any
outcome is seen, never by worker result. For every observation the
complete, context-aware `4^S` assignment-to-terminal-payoff surface is
materialized through the four-worker runtime, **including wrong-family
calls** (a well-formed world action scoring 0.5). Dependency blocking
and exact-request cache reuse reduce physical generations below the
naive 804-step bound; the runner records both planned step executions
and actual unique singleton calls rather than assuming the saving.

The support declaration (identities, assignment sets, pool and
worker-visible fingerprints) is a committed fixture written BEFORE the
new wrong-family calls run (106_s §9.4); materialization refuses a
runtime whose identity differs from the declaration, and the loader
fails closed on a missing, duplicated, foreign or wrong-profile payoff
row. This is a runtime fixture, not a population estimate.

Also here (106_s §§9.4-9.5): the separately registered worker-2 vs
worker-3 terminal-reward disagreement canary (deliberately selected
for disagreement, excluded from aggregate summaries — its latent
ordinal lies outside the ordinal-0 support), and the committed
sentinel set of retained 99_f/104_f requests that workers 2 and 3 must
reproduce bit-for-bit in fresh singleton processes. There is no
adaptive execution path in this module.

CLI:
  uv run python -m tasks.conductor.payoff_support declare
  uv run python -m tasks.conductor.payoff_support materialize --out DIR
  uv run python -m tasks.conductor.payoff_support verify --out DIR
  uv run python -m tasks.conductor.payoff_support canary
  uv run python -m tasks.conductor.payoff_support sentinels --order 23|32
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from . import executor, oracle, parser, program
from .executor import WorkflowItem
from .pool_runtime import (
    FOUR_WORKER_RUNTIME_PROFILE, FourWorkerPool, PoolTraceWriter,
    build_pool_runtime, pool_worker_visible_fingerprint,
)
from .profiles import DEFAULT_PROFILE
from .resources import InstanceRegistry
from .types import CELL_IDS, InfrastructureError
from .workerpool import STAGE0_POOL_FINGERPRINT, WORKER_IDS

SUPPORT_NAMESPACE = "worker_dev"
SUPPORT_ORDINAL = 0            # first latent by frozen generator ordinal
SUPPORT_RENDERERS = ("resource_first", "goal_first", "bound_var")
SUPPORT_VISIBILITY = "private"

SURFACE_SCHEMA_VERSION = 1
_MANIFEST_KEYS = frozenset({
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

FIXTURES = Path(__file__).parent / "fixtures"
DECLARATION_PATH = FIXTURES / "stage0_support.json"
CANARY_PATH = FIXTURES / "stage0_canary.json"
SENTINELS_PATH = FIXTURES / "stage0_sentinels.json"


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- observations ------------------------------------------------------------

def support_observations() -> list[dict[str, Any]]:
    """The 18 identity-selected observations, in frozen (cell, renderer)
    order. Rebuilt from the frozen generator on every call — the
    declaration verifies these, never the other way around."""
    observations = []
    for cell in CELL_IDS:
        latent = program.generate_latent(
            cell, SUPPORT_NAMESPACE, SUPPORT_ORDINAL, DEFAULT_PROFILE).latent
        positions = latent["reference_program"]["positions"]
        for renderer in SUPPORT_RENDERERS:
            inst = program.render_instance(latent, renderer,
                                           SUPPORT_VISIBILITY)
            observations.append({
                "observation_id": inst["render_instance_id"],
                "cell_id": cell,
                "renderer_id": renderer,
                "num_nodes": len(positions),
                "latent": latent,
                "instance": inst,
            })
    return observations


def _assignment_items(observation: Mapping[str, Any],
                      request_contract: str
                      ) -> list[tuple[tuple[int, ...], WorkflowItem]]:
    """Every 4^S assignment for one observation as an executable item.
    Assignments are stable-node-order tuples; positional conversion is
    the frozen semantic_to_positional mapping (106_s §6.1)."""
    inst = observation["instance"]
    latent = observation["latent"]
    registry = InstanceRegistry(inst["public_manifest"],
                                inst["private_registry"])
    steps = [{"subtask": s["subtask"], "resource": s["resource"],
              "access": s["access"]}
             for s in program.workflow_steps(latent)]
    positions = latent["reference_program"]["positions"]
    items = []
    for assignment in oracle.enumerate_assignments(
            observation["num_nodes"]):
        positional = oracle.semantic_to_positional(
            assignment, observation["cell_id"], positions)
        action = parser.routing_to_workflow(positional, steps)
        item_id = (observation["observation_id"]
                   + "#a" + "".join(str(w) for w in assignment))
        items.append((assignment, WorkflowItem(
            item_id=item_id, action=action,
            public_prompt=inst["public_prompt"], registry=registry,
            request_contract=request_contract)))
    return items


# --- declaration (committed before any wrong-family call runs) ---------------

def canonical_support_profile() -> dict[str, Any]:
    """The scientific identity the support binds: the frozen four-worker
    profile on the experiment device. Conductor-only keys (cache path,
    profile name, mixture) are outside the worker-visible fingerprint,
    so runs may place their caches freely."""
    return copy.deepcopy(FOUR_WORKER_RUNTIME_PROFILE)


def build_support_declaration(pool: Any) -> dict[str, Any]:
    """Identities + fingerprints, computed from a pool bound to the
    canonical profile. Recorded before materialization (106_s §9.4)."""
    profile = pool.profile
    chat_shas, system_shas = {}, {}
    for entry in profile["worker_pool"]:
        worker_id, name = entry["worker_id"], entry["name"]
        chat_shas[name] = pool.chat_template_sha(worker_id)
        system_shas[name] = hashlib.sha256(pool.system_prompt(
            worker_id).encode("utf-8")).hexdigest()
    observations = support_observations()
    planned = sum(len(oracle.enumerate_assignments(obs["num_nodes"]))
                  * obs["num_nodes"] for obs in observations)
    return {
        "support": "stage0-diagnostic-v1",
        "namespace": SUPPORT_NAMESPACE,
        "ordinal": SUPPORT_ORDINAL,
        "renderers": list(SUPPORT_RENDERERS),
        "visibility": SUPPORT_VISIBILITY,
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


def _verify_declaration_consistency(declaration: Mapping[str, Any],
                                    observations: list[dict[str, Any]]
                                    ) -> None:
    """118_s F3: verify the COMPLETE regenerated support description
    against the declaration — identities, cells, renderers, arities,
    assignment counts and the frozen selection constants — not only
    observation ids."""
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
        "namespace": SUPPORT_NAMESPACE,
        "ordinal": SUPPORT_ORDINAL,
        "renderers": list(SUPPORT_RENDERERS),
        "visibility": SUPPORT_VISIBILITY,
        "planned_step_executions": sum(
            obs["assignments"] * obs["num_nodes"]
            for obs in regenerated),
        "worker_ids": list(WORKER_IDS),
        "worker_pool_fingerprint": STAGE0_POOL_FINGERPRINT,
    }
    for key, expected in checks.items():
        if declaration.get(key) != expected:
            raise InfrastructureError(
                f"declaration field {key!r} does not match the "
                "regenerated support description; the generator or the "
                "declaration moved")


def load_declaration() -> dict[str, Any]:
    if not DECLARATION_PATH.exists():
        raise InfrastructureError(
            "support declaration is missing; generate and commit it "
            "with `payoff_support declare` before materialization")
    return json.loads(DECLARATION_PATH.read_text(encoding="utf-8"))


# --- materialization ---------------------------------------------------------

def materialize_support(rt: Any, out_dir: str | Path) -> dict[str, Any]:
    """Execute the complete declared surface through a runtime whose
    identity matches the committed declaration, with a v2 trace. The
    payoff of a schema-valid assignment is the frozen terminal ladder
    restricted to world outcomes: 1.0 correct, 0.5 otherwise."""
    declaration = load_declaration()
    if rt.worker_visible_fingerprint != \
            declaration["worker_visible_fingerprint"]:
        raise InfrastructureError(
            f"runtime worker-visible identity "
            f"{rt.worker_visible_fingerprint} does not match the "
            f"declared {declaration['worker_visible_fingerprint']}; "
            "the support binds one execution identity (106_s §9.4)")
    if rt.pool_fingerprint != declaration["worker_pool_fingerprint"]:
        raise InfrastructureError("runtime pool does not match the "
                                  "declared pool fingerprint")
    # 118_s F3: visibility is a Conductor-side condition outside the
    # worker-visible fingerprint, so it must be checked explicitly —
    # a "visible" runtime must not materialize the private support.
    if rt.profile["visibility_condition"] != declaration["visibility"]:
        raise InfrastructureError(
            f"runtime visibility "
            f"{rt.profile['visibility_condition']!r} does not match the "
            f"declared {declaration['visibility']!r} support")
    out_dir = Path(out_dir)
    payoff_path = out_dir / "payoffs.jsonl"
    manifest_path = out_dir / "manifest.json"
    if payoff_path.exists() or manifest_path.exists():
        raise InfrastructureError(
            f"{out_dir} already holds a materialized surface; refusing "
            "to overwrite a recorded artifact")
    out_dir.mkdir(parents=True, exist_ok=True)

    observations = support_observations()
    _verify_declaration_consistency(declaration, observations)

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
                assignment, item = record_pair
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
        "surface_schema_version": SURFACE_SCHEMA_VERSION,
        "support": declaration["support"],
        "declaration_sha256": _sha_file(DECLARATION_PATH),
        "worker_visible_fingerprint": rt.worker_visible_fingerprint,
        "runtime_profile_fingerprint": rt.runtime_profile_fingerprint,
        "worker_pool_fingerprint": rt.pool_fingerprint,
        "planned_step_executions":
            declaration["planned_step_executions"],
        "executed_step_records": executed_steps,
        # Records not served by the persistent cache (in-flight dedup
        # can fill several of these from one physical generation).
        "uncached_step_records": uncached_records,
        # Actual physical generations, counted at the pool.
        "unique_singleton_generations":
            getattr(rt.pool, "singleton_generations", 0)
            - generations_before,
        "cache_hits": cache_hits,
        "payoff_rows": len(rows),
        "wall_seconds": round(wall, 1),
        # 118_s F2: the surface binds its own artifacts by content.
        "payoffs_sha256": _sha_file(payoff_path),
        "trace_manifest_sha256": _sha_file(trace_dir / "manifest.json"),
        "trace_steps_sha256": _sha_file(trace_dir / "steps.jsonl"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=1,
                                        sort_keys=True) + "\n",
                             encoding="utf-8")
    return manifest


def _exact_int(value: Any) -> bool:
    return type(value) is int


def load_support_surface(out_dir: str | Path
                         ) -> dict[tuple[str, tuple[int, ...]], float]:
    """Fail-closed loader (106_s §9.5 as hardened by 118_s): the
    surface must be complete over every declared (observation,
    assignment) pair; every payoff is INDEPENDENTLY re-scored from the
    stored terminal value against the regenerated gold (a persisted
    payoff is never trusted); the manifest has an exact versioned
    schema binding the payoff and trace artifacts by content hash; the
    trace must be complete and carry the same execution identity. A
    missing, duplicated, foreign, mistyped, mis-scored or
    wrong-provenance row aborts."""
    out_dir = Path(out_dir)
    declaration = load_declaration()
    observations = support_observations()
    _verify_declaration_consistency(declaration, observations)
    golds = {obs["observation_id"]: obs["instance"]["gold_answer"]
             for obs in observations}

    manifest = json.loads((out_dir / "manifest.json").read_text(
        encoding="utf-8"))
    if set(manifest) != _MANIFEST_KEYS:
        raise InfrastructureError(
            f"surface manifest keys {sorted(manifest)} != the exact "
            f"schema {sorted(_MANIFEST_KEYS)}")
    if manifest["surface_schema_version"] != SURFACE_SCHEMA_VERSION:
        raise InfrastructureError(
            f"surface schema {manifest['surface_schema_version']!r} is "
            f"not {SURFACE_SCHEMA_VERSION}")
    if manifest["declaration_sha256"] != _sha_file(DECLARATION_PATH):
        raise InfrastructureError(
            "surface was materialized against a different support "
            "declaration; regenerate rather than reinterpret")
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
    # Accounting invariants over the recorded counts.
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
                raise InfrastructureError(
                    f"duplicate payoff row {key!r}")
            terminal = row["terminal_value"]
            if terminal is not None and not _exact_int(terminal):
                raise InfrastructureError(
                    f"terminal_value {terminal!r} is not an exact int")
            # 118_s F1: never trust a persisted payoff — re-score it
            # from the stored terminal outcome against the regenerated
            # gold answer.
            rescored = executor.score_terminal(
                terminal, golds[row["observation_id"]])
            if row["payoff"] != rescored:
                raise InfrastructureError(
                    f"row {key!r}: persisted payoff {row['payoff']!r} "
                    f"!= re-scored {rescored} from its terminal value")
            surface[key] = rescored
    missing = expected - set(surface)
    if missing:
        raise InfrastructureError(
            f"surface is incomplete: {len(missing)} declared rows "
            f"missing (e.g. {sorted(missing)[:3]})")
    return surface


# --- canary and sentinels ----------------------------------------------------

def run_canary(rt: Any) -> dict[str, Any]:
    """Execute the registered worker-2/worker-3 disagreement canary and
    require the terminal rewards to differ (106_s §10.3). Deterministic
    plumbing evidence that model-scale selection reaches the reward
    path — never an aggregate metric."""
    canary = json.loads(CANARY_PATH.read_text(encoding="utf-8"))
    latent = program.generate_latent(
        canary["cell_id"], canary["namespace"], canary["ordinal"],
        DEFAULT_PROFILE).latent
    inst = program.render_instance(latent, canary["renderer_id"],
                                   canary["visibility"])
    if inst["render_instance_id"] != canary["observation_id"]:
        raise InfrastructureError(
            "canary identity does not regenerate; the generator or the "
            "registered record moved")
    registry = InstanceRegistry(inst["public_manifest"],
                                inst["private_registry"])
    steps = [{"subtask": s["subtask"], "resource": s["resource"],
              "access": s["access"]}
             for s in program.workflow_steps(latent)]
    rewards = {}
    for worker in (2, 3):
        action = parser.routing_to_workflow([worker], steps)
        item = WorkflowItem(
            item_id=f"canary#w{worker}", action=action,
            public_prompt=inst["public_prompt"], registry=registry,
            request_contract=rt.profile["request_contract"])
        results, _ = rt.execute_batch([item])
        rewards[worker] = executor.score_terminal(
            results[0].terminal, inst["gold_answer"])
    # 118_s smaller finding: require exact agreement with the
    # registered direction, not merely a difference — a reversed
    # outcome would be a different (undiagnosed) phenomenon.
    expected_rewards = {
        worker: 1.0 if canary["expected"][f"worker_{worker}_correct"]
        else 0.5
        for worker in (2, 3)}
    outcome = {"rewards": {str(w): r for w, r in rewards.items()},
               "expected_rewards": {str(w): r for w, r
                                    in expected_rewards.items()},
               "differ": rewards[2] != rewards[3],
               "expected": canary["expected"]}
    if rewards != expected_rewards:
        raise InfrastructureError(
            f"canary rewards {rewards} do not match the registered "
            f"direction {expected_rewards}; model-scale selection is "
            "not reproducing the recorded disagreement")
    return outcome


def run_sentinels(pool: Any, order: str) -> dict[str, Any]:
    """Reproduce the committed retained 99_f/104_f requests bit-for-bit
    through fresh singleton generation, in the given worker order
    (`23` = worker 2 first, `32` = worker 3 first — the §9.5
    model-order stability check). Cache-free by construction: the pool
    is called directly."""
    sentinels = json.loads(SENTINELS_PATH.read_text(encoding="utf-8"))
    workers = [int(c) for c in order]
    if sorted(workers) != [2, 3]:
        raise InfrastructureError(f"order must be 23 or 32, got {order!r}")
    checked = 0
    for worker in workers:
        for entry in sentinels["cases"]:
            expected = entry[f"worker_{worker}"]
            request = pool.render_request(worker, entry["user_message"])
            actual_sha = hashlib.sha256(request).hexdigest()
            if actual_sha != entry["request_sha256"]:
                raise InfrastructureError(
                    f"{entry['case_id']}: rendered request "
                    f"{actual_sha[:16]}… != retained "
                    f"{entry['request_sha256'][:16]}…")
            gen = pool.generate_singleton(worker, request)
            for field in ("completion", "finish_reason",
                          "generated_tokens",
                          "generation_hit_token_cap"):
                if getattr(gen, field) != expected[field]:
                    raise InfrastructureError(
                        f"{entry['case_id']} worker {worker}: {field} "
                        f"differs from the retained artifact")
            checked += 1
    return {"order": order, "cases": len(sentinels["cases"]),
            "checks": checked}


# --- CLI ---------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("declare", help="write the committed support "
                                   "declaration (CPU; tokenizers only)")
    mat = sub.add_parser("materialize", help="execute the declared "
                                             "4^S surface (GPU)")
    mat.add_argument("--out", required=True)
    ver = sub.add_parser("verify", help="fail-closed surface load")
    ver.add_argument("--out", required=True)
    sub.add_parser("canary", help="run the w2/w3 disagreement canary")
    sen = sub.add_parser("sentinels", help="reproduce retained "
                                           "99_f/104_f requests")
    sen.add_argument("--order", default="23", choices=["23", "32"])
    args = ap.parse_args(argv)

    if args.command == "declare":
        pool = FourWorkerPool(canonical_support_profile())
        declaration = build_support_declaration(pool)
        with DECLARATION_PATH.open("x", encoding="utf-8") as handle:
            json.dump(declaration, handle, indent=1, sort_keys=True)
            handle.write("\n")
        print(f"declaration -> {DECLARATION_PATH} "
              f"(sha256 {_sha_file(DECLARATION_PATH)})")
        return 0

    if args.command in ("materialize", "canary"):
        profile = canonical_support_profile()
        profile["cache_path"] = str(
            Path(args.out if args.command == "materialize"
                 else "runs/stage0-canary") / "cache.sqlite")
        rt = build_pool_runtime(profile)
        try:
            if args.command == "materialize":
                manifest = materialize_support(rt, args.out)
                print(json.dumps(manifest, indent=1, sort_keys=True))
            else:
                print(json.dumps(run_canary(rt), indent=1))
        finally:
            rt.close()
        return 0

    if args.command == "verify":
        surface = load_support_surface(args.out)
        print(f"surface OK: {len(surface)} payoff rows, complete over "
              "the declared support")
        return 0

    if args.command == "sentinels":
        pool = FourWorkerPool(canonical_support_profile())
        outcome = run_sentinels(pool, args.order)
        pool.close()
        print(json.dumps(outcome, indent=1))
        return 0

    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
