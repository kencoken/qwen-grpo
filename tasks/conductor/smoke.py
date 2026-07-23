"""Stage-0B recorded acceptance command: offline executor smoke on the
real NF4 pool (plan rev6, Stage 0B).

Run:  uv run python -m tasks.conductor.smoke --per-cell 2 --run-name <name>

Builds the real runtime from `DEFAULT_RUNTIME_PROFILE` (three NF4 1.5B
workers, SQLite write-through cache), executes the reference routing for a
few construction instances per cell through `execute_workflow_batch` with
JSONL traces, then re-executes the same batch and **fails unless every
second-pass call is a cache hit**. Reports per-endpoint telemetry and
descriptive accuracy (a smoke diagnostic, not a Stage-1 gate: no
registered population, no calibration manifest).
"""

from __future__ import annotations

import argparse
import copy
import sys
from collections import Counter
from pathlib import Path

from . import executor, parser, program
from .agreement import ENDPOINT_FOR_OP
from .cache import CompletionCache
from .executor import TraceWriter, WorkflowItem
from .profiles import DEFAULT_PROFILE
from .resources import InstanceRegistry
from .runtime import DEFAULT_RUNTIME_PROFILE, build_runtime
from .types import CELL_IDS, ENDPOINT_NAMES
from .workers import WorkerPool


def build_items(per_cell: int) -> tuple[list[WorkflowItem], dict[str, int]]:
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
            action = parser.routing_to_workflow(routing, steps)
            item_id = inst["render_instance_id"]
            items.append(WorkflowItem(item_id=item_id, action=action,
                                      public_prompt=inst["public_prompt"],
                                      registry=registry))
            golds[item_id] = inst["gold_answer"]
    return items, golds


def run_pass(rt, items, trace=None):
    stats = {"calls": Counter(), "cache_hits": 0, "truncated": 0,
             "records": []}

    def call(worker_id, requests):
        records = rt.worker_call_batch(ENDPOINT_NAMES[worker_id], requests)
        stats["calls"][ENDPOINT_NAMES[worker_id]] += len(records)
        stats["cache_hits"] += sum(r.cache_hit for r in records)
        stats["truncated"] += sum(r.generation_hit_token_cap
                                  for r in records)
        stats["records"].extend(records)
        return records

    results = executor.execute_workflow_batch(items, call, trace=trace)
    return results, stats


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--per-cell", type=int, default=2)
    argp.add_argument("--run-name", default="stage0b-smoke")
    argp.add_argument("--device", default="cuda")
    args = argp.parse_args()

    profile = copy.deepcopy(DEFAULT_RUNTIME_PROFILE)
    profile["cache_path"] = str(Path("runs") / args.run_name
                                / "cache.sqlite")
    pool = WorkerPool(profile, device=args.device)
    rt = build_runtime(profile, pool=pool,
                       cache=CompletionCache(profile["cache_path"]))
    items, golds = build_items(args.per_cell)
    print(f"{len(items)} workflows "
          f"({args.per_cell}/cell x {len(CELL_IDS)} cells), "
          f"profile {rt.runtime_profile_fingerprint}, "
          f"worker-visible {rt.worker_visible_fingerprint}")

    with TraceWriter(args.run_name, rt) as trace:
        results, stats = run_pass(rt, items, trace=trace)
    statuses = Counter()
    correct = 0
    for item, result in zip(items, results):
        for step in result.steps:
            statuses[step.result.status if step.result else
                     f"world:{step.world_failure}"] += 1
        correct += executor.score_terminal(result.terminal,
                                           golds[item.item_id]) == 1.0
    print(f"pass 1: calls {dict(stats['calls'])}, "
          f"cache hits {stats['cache_hits']}, "
          f"truncated {stats['truncated']}")
    print(f"pass 1: step statuses {dict(statuses)}; "
          f"terminal correct (descriptive) {correct}/{len(items)}")

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
    if stats2["cache_hits"] != total2:
        print("FAIL: second pass was not fully served by the cache")
        return 1
    if mismatched:
        print(f"FAIL: {mismatched} workflows replayed differently from cache")
        return 1
    print("smoke OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
