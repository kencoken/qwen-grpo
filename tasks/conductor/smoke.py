"""Stage-0B recorded acceptance command: offline executor smoke on the
real four-worker NF4 pool (106_s §9.5; re-enabled by unit 2 after the
108_f finding-2 disablement).

Run:  uv run python -m tasks.conductor.smoke --per-cell 2 --run-name <name>

Builds the four-worker runtime from `FOUR_WORKER_RUNTIME_PROFILE`
(generic-1.5B shared by workers 0-2, generic-3B for worker 3, rev10
prompts, `task_last` contract, singleton-v1 generation, worker-keyed
SQLite cache), then executes through `execute_workflow_batch` with
pool-bound v2 traces:

- the reference routing for a few construction instances per cell
  (canonical family workers 0-2), covering atomic, chain and fork
  topologies;
- a worker-3 variant of every workflow with a Code node (`:w3` items),
  so both Code workers execute the same nodes;
- one deliberate wrong-family workflow (`:wf`), which must yield a
  typed 0.5 outcome, never an abort;

then re-executes the same batch and **fails unless every second-pass
call is a cache hit** and replays are byte-identical. Reports
per-worker telemetry, descriptive accuracy, wall time and peak
reserved VRAM (a smoke diagnostic, not a Stage-1 gate: no registered
population, no calibration manifest).
"""

from __future__ import annotations

import argparse
import copy
import sys
import time
from collections import Counter
from pathlib import Path

from . import executor, parser, program
from .agreement import ENDPOINT_FOR_OP
from .cache import WorkerCompletionCache
from .executor import WorkflowItem
from .pool_runtime import (
    FOUR_WORKER_RUNTIME_PROFILE, FourWorkerPool, FourWorkerRuntime,
    PoolTraceWriter,
)
from .profiles import DEFAULT_PROFILE
from .resources import InstanceRegistry
from .types import CELL_IDS
from .workerpool import WORKER_NAMES

WRONG_FAMILY_WORKER = 1  # deliberate math-family routing of a lookup node


def build_items(per_cell: int, request_contract: str
                ) -> tuple[list[WorkflowItem], dict[str, int]]:
    """Reference-routed items plus the §9.5 four-worker additions:
    a worker-3 variant for every workflow with a Code node, and one
    wrong-family workflow."""
    items, golds = [], {}
    for cell in CELL_IDS:
        for index in range(per_cell):
            latent = program.generate_latent(cell, "construction", index,
                                             DEFAULT_PROFILE).latent
            inst = program.render_instance(latent, "resource_first",
                                           "private")
            registry = InstanceRegistry(inst["public_manifest"],
                                        inst["private_registry"])
            steps = [{"subtask": s["subtask"], "resource": s["resource"],
                      "access": s["access"]}
                     for s in program.workflow_steps(latent)]
            nodes = {n["id"]: n for n in latent["reference_program"]["nodes"]}
            routing = [ENDPOINT_FOR_OP[nodes[node_id]["op"]]
                       for node_id in latent["reference_program"]["positions"]]
            item_id = inst["render_instance_id"]

            def add(suffix: str, worker_ids: list[int]) -> None:
                action = parser.routing_to_workflow(worker_ids, steps)
                items.append(WorkflowItem(
                    item_id=item_id + suffix, action=action,
                    public_prompt=inst["public_prompt"], registry=registry,
                    request_contract=request_contract))
                golds[item_id + suffix] = inst["gold_answer"]

            add("", routing)
            if 2 in routing:
                add(":w3", [3 if w == 2 else w for w in routing])
            if cell == "lookup_atomic" and index == 0:
                add(":wf", [WRONG_FAMILY_WORKER] * len(routing))
    return items, golds


def run_pass(rt: FourWorkerRuntime, items, trace=None):
    stats = {"calls": Counter(), "cache_hits": 0, "truncated": 0,
             "truncated_by_worker": Counter(), "records": []}

    def call(worker_id, requests):
        records = rt.worker_call_batch(worker_id, requests)
        name = WORKER_NAMES[worker_id]
        stats["calls"][name] += len(records)
        stats["cache_hits"] += sum(r.cache_hit for r in records)
        truncated = sum(r.generation_hit_token_cap for r in records)
        stats["truncated"] += truncated
        stats["truncated_by_worker"][name] += truncated
        stats["records"].extend(records)
        return records

    results = executor.execute_workflow_batch(items, call, trace=trace)
    return results, stats


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--per-cell", type=int, default=2)
    argp.add_argument("--run-name", default="stage0-4w-smoke")
    argp.add_argument("--device", default="cuda")
    args = argp.parse_args()

    profile = copy.deepcopy(FOUR_WORKER_RUNTIME_PROFILE)
    profile["cache_path"] = str(Path("runs") / args.run_name
                                / "cache.sqlite")
    pool = FourWorkerPool(profile, device=args.device)
    rt = FourWorkerRuntime(profile, pool,
                           WorkerCompletionCache(profile["cache_path"]))
    items, golds = build_items(args.per_cell, profile["request_contract"])
    print(f"{len(items)} workflows ({args.per_cell}/cell x "
          f"{len(CELL_IDS)} cells + :w3/:wf variants), "
          f"profile {rt.runtime_profile_fingerprint}, "
          f"pool {rt.pool_fingerprint}, "
          f"worker-visible {rt.worker_visible_fingerprint}")
    for entry in rt.logical_to_physical:
        print(f"physical: {entry['model_id']}@{entry['revision'][:12]} "
              f"<- {entry['workers']}")

    started = time.monotonic()
    with PoolTraceWriter(args.run_name, rt) as trace:
        results, stats = run_pass(rt, items, trace=trace)
    wall = time.monotonic() - started
    statuses = Counter()
    correct = 0
    per_worker: dict[str, Counter] = {name: Counter()
                                      for name in WORKER_NAMES.values()}
    wrong_family_ok = None
    for item, result in zip(items, results):
        for step in result.steps:
            statuses[step.result.status if step.result else
                     f"world:{step.world_failure}"] += 1
            if step.completion is None:
                continue  # pseudo-worker, world failure, or blocked
            wk = per_worker[WORKER_NAMES[step.worker_id]]
            wk["calls"] += 1
            assert step.result is not None
            wk["artifact_valid"] += step.result.artifact_valid
            wk["success"] += step.result.status == "success"
            if step.result.rejection_code:
                wk[step.result.rejection_code] += 1
        score = executor.score_terminal(result.terminal,
                                        golds[item.item_id])
        correct += score == 1.0
        if item.item_id.endswith(":wf"):
            # §9.5: typed wrong-family outcome, scored 0.5, no abort.
            wrong_family_ok = (score == 0.5 and all(
                s.result is not None and s.result.status == "typed_failure"
                for s in result.steps))
    print(f"pass 1: calls {dict(stats['calls'])}, "
          f"cache hits {stats['cache_hits']}, "
          f"truncated {stats['truncated']}, wall {wall:.1f}s")
    print(f"pass 1: step statuses {dict(statuses)}; "
          f"terminal correct (descriptive) {correct}/{len(items)}")
    for name, wk in per_worker.items():
        if wk["calls"]:
            detail = {code: n for code, n in wk.items()
                      if code not in ("calls", "artifact_valid", "success")}
            print(f"pass 1 [{name}]: calls {wk['calls']}, "
                  f"artifact_valid {wk['artifact_valid']}, "
                  f"success {wk['success']}, "
                  f"truncated {stats['truncated_by_worker'][name]}, "
                  f"rejections {detail}")
    if args.device.startswith("cuda"):
        import torch
        peak = torch.cuda.max_memory_reserved()
        print(f"peak reserved VRAM: {peak / 2**30:.2f} GiB")

    results2, stats2 = run_pass(rt, items)
    total2 = sum(stats2["calls"].values())
    print(f"pass 2: calls {dict(stats2['calls'])}, "
          f"cache hits {stats2['cache_hits']}/{total2}")
    mismatched = sum(
        1 for r1, r2 in zip(results, results2)
        if [s.completion for s in r1.steps] !=
           [s.completion for s in r2.steps])
    rt.close()

    trace_dir = Path("runs") / args.run_name / "traces"
    print(f"traces: {trace_dir / 'steps.jsonl'}")
    failures = []
    if stats2["cache_hits"] != total2:
        failures.append("second pass was not fully served by the cache")
    if mismatched:
        failures.append(f"{mismatched} workflows replayed differently")
    if wrong_family_ok is not True:
        failures.append("wrong-family workflow did not yield the typed "
                        "0.5 outcome")
    if not per_worker["code_3b"]["calls"]:
        failures.append("worker 3 made no calls")
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        return 1
    print("smoke OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
