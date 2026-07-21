"""Freeze the P0 cohort from a retained rev9 trace (92_s §6.2).

Reads a Stage-0B trace (`steps.jsonl`), takes every real Code-endpoint
call in file order, reconstructs the physical `model.generate` chunks
(wave = worker × position exactly as the executor batched them; chunks =
successive microbatch-sized groups within a wave), regenerates each
case from the frozen generator, verifies the retained request bytes
match the regeneration, and writes the pinned cohort manifest.

The output is id + hash only — no payloads — so it is committable as
the frozen evidence specification. The Math per-cell-15/30 observation
is deliberately NOT a cohort (92_s §6.3): it stays in the D16 log as
historical evidence.

Run:  uv run python -m tasks.conductor.gen_p0_cohort \
          --trace runs/d16-rev9-confirm/traces/steps.jsonl \
          --out tasks/conductor/fixtures/p0_rev9_code_cohort.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import program
from .profiles import DEFAULT_PROFILE
from .runtime import DEFAULT_RUNTIME_PROFILE
from .types import InfrastructureError
from .worker_eval_probe import load_cohort

CODE_WORKER_ID = 2


def build_cohort(trace_path: str | Path,
                 microbatch: int | None = None) -> dict:
    trace_path = Path(trace_path)
    steps = [json.loads(line)
             for line in trace_path.read_text(encoding="utf-8").splitlines()]
    if microbatch is None:
        microbatch = DEFAULT_RUNTIME_PROFILE["workers"]["code"]["microbatch"]
    code_calls = [step for step in steps
                  if step["worker_id"] == CODE_WORKER_ID
                  and step["completion"] is not None]
    if not code_calls:
        raise InfrastructureError(f"{trace_path}: no Code calls")

    # Reconstruct physical chunks: the executor gathered one wave per
    # (worker, position) in item order — which is the trace file order —
    # and the pool split each wave into successive microbatch groups.
    waves: dict[int, list[dict]] = {}
    for step in code_calls:
        waves.setdefault(step["position"], []).append(step)

    chunks = []
    chunk_sizes = []
    for position in sorted(waves):
        wave = waves[position]
        for start in range(0, len(wave), microbatch):
            chunk_steps = wave[start:start + microbatch]
            entries = []
            for step in chunk_steps:
                cell, namespace, index, _, renderer, visibility = \
                    step["item_id"].split(":")
                latent = program.generate_latent(
                    cell, namespace, int(index), DEFAULT_PROFILE).latent
                node_id = program.workflow_steps(latent)[
                    step["position"] - 1]["node"]
                pinned = hashlib.sha256(
                    step["request"].encode("utf-8")).hexdigest()
                entries.append({
                    "cell_id": cell, "latent_index": int(index),
                    "renderer_id": renderer, "node_id": node_id,
                    "user_message_sha256": pinned,
                })
            chunks.append(entries)
            chunk_sizes.append(len(entries))

    return {
        "schema_version": 1,
        "purpose": ("92_s §6.2 P0 cohort: the retained rev9 "
                    "batch-sensitive Code requests with their exact "
                    "physical generate chunks"),
        "endpoint": "code",
        "namespace": "construction",
        "visibility": "private",
        "microbatch": microbatch,
        "source_trace": str(trace_path),
        "source_trace_sha256": hashlib.sha256(
            trace_path.read_bytes()).hexdigest(),
        "chunk_sizes": chunk_sizes,
        "chunks": chunks,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    cohort = build_cohort(args.trace)
    # Fail-closed self-check: every pin must match the regenerated case
    # before the cohort is written (load_cohort verifies request bytes
    # and physical chunk sizes).
    load_cohort(cohort)
    out = Path(args.out)
    with out.open("x", encoding="utf-8") as handle:
        json.dump(cohort, handle, indent=1, sort_keys=True)
        handle.write("\n")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    total = sum(cohort["chunk_sizes"])
    print(f"{total} Code calls in chunks {cohort['chunk_sizes']} "
          f"-> {out} (sha256 {digest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
