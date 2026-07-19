"""10k-case reference-vs-tools agreement — the §4 recorded acceptance
command (not pytest).

For each case: generate a latent program, derive the reference artifact for
every node, execute it through the independent `tools.py` evaluators with
the node's authorized binding, and require exact agreement with the
reference node value. Stratified by operator × cell; the summary prints the
per-stratum counts.

Run:  uv run python -m tasks.conductor.agreement --cases 10000
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from . import program
from .contract import run_worker_output
from .profiles import DEFAULT_PROFILE
from .tools import Binding
from .types import CELL_IDS


def reference_artifact(latent: dict, node_id: str) -> str:
    """Render the node's reference computation in its endpoint grammar."""
    node = next(n for n in latent["reference_program"]["nodes"]
                if n["id"] == node_id)
    op, args = node["op"], node["args"]
    positions = latent["reference_program"]["positions"]

    def step_of(ref_node: str) -> str:
        return f"step_{1 + positions.index(ref_node)}"

    if op == "lookup":
        return (f'lookup(resource, "{args["key"]["lit"]}", '
                f'"{args["field"]["lit"]}")')
    if op == "affine":
        sign = args["sign"]["lit"]
        return (f"{args['p']['lit']} * {step_of(args['x']['node'])} "
                f"{sign} {args['q']['lit']}")
    if op == "mul_add":
        return "a * b + c"
    if op == "ratio":
        return "(a * b - c) / d"
    if op == "modular":
        return "(a * b + c) % m"
    if op == "product_affine":
        return (f"{step_of(args['x']['node'])} * "
                f"{step_of(args['y']['node'])} + {args['q']['lit']}")
    if op == "seq_count":
        return f"count_gt(stable_unique(resource), {args['t']['lit']})"
    if op == "seq_select":
        return (f"at(rotate_left(stable_unique(resource), "
                f"{args['k']['lit']}), {args['i']['lit']})")
    if op == "seq_at":
        return f"at(resource, {step_of(args['i']['node'])})"
    raise ValueError(op)


_ENDPOINT_FOR_OP = {"lookup": 0, "affine": 1, "mul_add": 1, "ratio": 1,
                    "modular": 1, "product_affine": 1, "seq_count": 2,
                    "seq_select": 2, "seq_at": 2}


def run(cases: int, namespace: str = "train") -> int:
    per_cell = cases // len(CELL_IDS)
    strata: Counter = Counter()
    mismatches = 0
    for cell in CELL_IDS:
        cap = program.namespace_cap(namespace, cell)
        for index in range(min(per_cell, cap)):
            latent = program.generate_latent(cell, namespace, index,
                                             DEFAULT_PROFILE).latent
            registry = program.registry_from_json(latent["private_registry"])
            positions = latent["reference_program"]["positions"]
            for node_id in positions:
                node = next(n for n in latent["reference_program"]["nodes"]
                            if n["id"] == node_id)
                handle = program.node_resource(latent["reference_program"],
                                               node_id)
                resources = {handle: registry[handle]} if handle else {}
                steps = {1 + positions.index(ref["node"]):
                         latent["node_values"][ref["node"]]
                         for ref in node["args"].values() if "node" in ref}
                completion = (f"<artifact>{reference_artifact(latent, node_id)}"
                              f"</artifact>")
                result = run_worker_output(
                    _ENDPOINT_FOR_OP[node["op"]], completion,
                    Binding(resources=resources, steps=steps))
                strata[(node["op"], cell)] += 1
                if result.status != "success" or \
                        result.value != latent["node_values"][node_id]:
                    mismatches += 1
                    print(f"MISMATCH {latent['latent_program_id']} "
                          f"{node_id}: {result}", file=sys.stderr)
    total = sum(strata.values())
    print(f"agreement: {total - mismatches}/{total} node executions agree")
    for (op, cell), count in sorted(strata.items()):
        print(f"  {op:15s} × {cell:15s}: {count}")
    return 1 if mismatches else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=10_000)
    ap.add_argument("--namespace", default="train")
    args = ap.parse_args()
    sys.exit(run(args.cases, args.namespace))


if __name__ == "__main__":
    main()
