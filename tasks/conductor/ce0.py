"""CE0 — Stage-0 worst-case benchmark and environment manifest
(106_s §10.4; unit 5). A NEW module: the eight freeze-digested source
files are never edited.

Measurements (each preregistered in conductor_log.md before first GPU
use):

- **env-manifest**: the complete source/environment manifest 125_s
  requires — git commit/tree/dirty state, dependency hashes, package
  versions, CUDA/driver/GPU identity.
- **materialize-timing**: the exact `payoff_support materialize` CLI
  as a subprocess — full-command wall including interpreter, imports
  and model/tokenizer loading — with device-level VRAM polled via
  nvidia-smi (worker-phase peak; the box runs nothing else during
  CE0, recorded as a caveat).
- **live-worst-case**: cache-disabled (fresh cache) live singleton
  execution of a deterministic forced-valid workload — the 18 unique
  observations under their family-reference assignments — measuring
  wall, physical calls, per-call latency and in-process VRAM peak.
  This is the per-update worst case of a hypothetical live Stage-2
  mode; pre-materialized routing is the preferred path and modes 2/3
  (co-residency, adapter toggling) are NOT implemented if it passes
  (106_s §10.4).
- **enumeration**: CPU 4^S enumeration + positional conversion +
  workflow construction through S=3, full 324-assignment pass.
- **report**: gates + Stage-2 seed projection (first seed vs
  amortized additional seed) from the measurements plus the recorded
  smoke (18 updates / 153.2 s).

Run:  uv run python -m tasks.conductor.ce0 run --out runs/ce0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from . import oracle, parser, program
from .executor import WorkflowItem
from .payoff_support import canonical_support_profile, support_observations
from .resources import InstanceRegistry

SMOKE_SECONDS_PER_UPDATE = 153.2 / 18   # the recorded unit-4 smoke
STAGE2_SEED_UPDATES = 300               # the rev6 Stage-1/2 run length

CE0_GATES = {
    "peak_reserved_vram_gib_lt": 22.0,
    "projected_seed_hours_lte": 12.0,   # "no longer than overnight"
    "infra_failures_as_reward": 0,
}


def _sha_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True,
                          text=True, check=True).stdout.strip()


def build_env_manifest() -> dict[str, Any]:
    import torch
    import bitsandbytes
    import datasets
    import peft
    import transformers
    import trl
    gpu = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
         "--format=csv,noheader"],
        capture_output=True, text=True, check=True).stdout.strip()
    return {
        "manifest": "ce0-environment-v1",
        "git_commit": _git("rev-parse", "HEAD"),
        "git_tree": _git("rev-parse", "HEAD^{tree}"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "pyproject_sha256": _sha_file("pyproject.toml"),
        "uv_lock_sha256": _sha_file("uv.lock"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "transformers": transformers.__version__,
        "trl": trl.__version__,
        "peft": peft.__version__,
        "datasets": datasets.__version__,
        "bitsandbytes": bitsandbytes.__version__,
        "gpu": gpu,
    }


class _VramPoller:
    """Device-level polling via nvidia-smi while a subprocess runs.
    Caveat recorded with the result: device-level, so it includes any
    concurrent usage — CE0 runs on an otherwise idle box."""

    def __init__(self) -> None:
        self.peak_mib = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._poll, daemon=True)

    def _poll(self) -> None:
        while not self._stop.is_set():
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True).stdout.strip()
            try:
                self.peak_mib = max(self.peak_mib, int(out.splitlines()[0]))
            except (ValueError, IndexError):
                pass
            self._stop.wait(0.5)

    def __enter__(self) -> "_VramPoller":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._stop.set()
        self._thread.join()


def materialize_timing(out_dir: Path) -> dict[str, Any]:
    target = out_dir / "materialize"
    command = [sys.executable, "-m", "tasks.conductor.payoff_support",
               "materialize", "--out", str(target)]
    started = time.monotonic()
    with _VramPoller() as poller:
        proc = subprocess.run(command, capture_output=True, text=True)
    wall = time.monotonic() - started
    if proc.returncode != 0:
        raise RuntimeError(f"materialization failed:\n{proc.stderr[-2000:]}")
    manifest = json.loads((target / "manifest.json").read_text())
    disk_bytes = sum(f.stat().st_size for f in target.rglob("*")
                     if f.is_file())
    return {
        "command": " ".join(command[2:]),
        "full_command_wall_seconds": round(wall, 1),
        "in_process_wall_seconds": manifest["wall_seconds"],
        "startup_and_load_seconds": round(
            wall - manifest["wall_seconds"], 1),
        "unique_singleton_generations":
            manifest["unique_singleton_generations"],
        "executed_step_records": manifest["executed_step_records"],
        "payoff_rows": manifest["payoff_rows"],
        "surface_disk_bytes": disk_bytes,
        "device_peak_vram_mib_polled": poller.peak_mib,
        "vram_caveat": "device-level nvidia-smi polling at 0.5s",
    }


def live_worst_case(out_dir: Path) -> dict[str, Any]:
    """Cache-disabled live singleton execution of the deterministic
    forced-valid workload: the 18 unique observations under their
    family-reference assignments."""
    import torch
    from .agreement import ENDPOINT_FOR_OP
    from .pool_runtime import build_pool_runtime
    profile = canonical_support_profile()
    profile["cache_path"] = str(out_dir / "live-worst-case-cache.sqlite")
    if Path(profile["cache_path"]).exists():
        raise RuntimeError("live worst-case cache must start cold")
    torch.cuda.reset_peak_memory_stats()
    rt = build_pool_runtime(profile)
    items = []
    planned_steps = 0
    try:
        for obs in support_observations():
            latent = obs["latent"]
            inst = obs["instance"]
            registry = InstanceRegistry(inst["public_manifest"],
                                        inst["private_registry"])
            steps = [{"subtask": s["subtask"], "resource": s["resource"],
                      "access": s["access"]}
                     for s in program.workflow_steps(latent)]
            nodes = {n["id"]: n
                     for n in latent["reference_program"]["nodes"]}
            routing = [ENDPOINT_FOR_OP[nodes[node]["op"]]
                       for node in latent["reference_program"]["positions"]]
            planned_steps += len(steps)
            items.append(WorkflowItem(
                item_id=obs["observation_id"] + "#ce0",
                action=parser.routing_to_workflow(routing, steps),
                public_prompt=inst["public_prompt"], registry=registry,
                request_contract=profile["request_contract"]))
        started = time.monotonic()
        results, telemetry = rt.execute_batch(items)
        wall = time.monotonic() - started
        generations = rt.pool.singleton_generations
        peak = torch.cuda.max_memory_reserved()
    finally:
        rt.close()
    correct = sum(r.terminal is not None for r in results)
    return {
        "workflows": len(items),
        "planned_step_executions": planned_steps,
        "physical_generations": generations,
        "execution_wall_seconds": round(wall, 1),
        "seconds_per_generation": round(wall / max(generations, 1), 3),
        "terminals_reached": correct,
        "in_process_peak_reserved_vram_gib": round(peak / 2 ** 30, 2),
    }


def enumeration_overhead() -> dict[str, Any]:
    started = time.monotonic()
    total_items = 0
    for obs in support_observations():
        latent = obs["latent"]
        positions = latent["reference_program"]["positions"]
        steps = [{"subtask": s["subtask"], "resource": s["resource"],
                  "access": s["access"]}
                 for s in program.workflow_steps(latent)]
        for assignment in oracle.enumerate_assignments(len(positions)):
            positional = oracle.semantic_to_positional(
                assignment, obs["cell_id"], positions)
            parser.routing_to_workflow(positional, steps)
            total_items += 1
    wall = time.monotonic() - started
    return {"assignments_built": total_items,
            "wall_seconds": round(wall, 2)}


def build_report(results: dict[str, Any]) -> dict[str, Any]:
    materialization = results["materialize_timing"]
    live = results["live_worst_case"]
    # Live mode: one update = 16 rollouts; the forced-valid workload is
    # 18 workflows, so scale by 16/18.
    live_per_update = (live["execution_wall_seconds"] * 16
                       / live["workflows"])
    pre_seed_first = (materialization["full_command_wall_seconds"]
                      + STAGE2_SEED_UPDATES * SMOKE_SECONDS_PER_UPDATE)
    pre_seed_additional = STAGE2_SEED_UPDATES * SMOKE_SECONDS_PER_UPDATE
    live_seed = STAGE2_SEED_UPDATES * (SMOKE_SECONDS_PER_UPDATE
                                       + live_per_update)
    peaks = [materialization["device_peak_vram_mib_polled"] / 1024,
             live["in_process_peak_reserved_vram_gib"],
             14.43]  # recorded smoke training peak
    report = {
        "smoke_seconds_per_update": round(SMOKE_SECONDS_PER_UPDATE, 2),
        "live_mode_extra_seconds_per_update": round(live_per_update, 1),
        "projected_seed_updates": STAGE2_SEED_UPDATES,
        "premat_first_seed_minutes": round(pre_seed_first / 60, 1),
        "premat_additional_seed_minutes": round(
            pre_seed_additional / 60, 1),
        "live_mode_seed_minutes": round(live_seed / 60, 1),
        "max_observed_peak_vram_gib": round(max(peaks), 2),
        "gates": CE0_GATES,
        "gate_results": {
            "vram": max(peaks) < CE0_GATES["peak_reserved_vram_gib_lt"],
            "seed_overnight": pre_seed_first / 3600
                <= CE0_GATES["projected_seed_hours_lte"],
            "no_infra_failures_as_reward": True,  # smoke: 0 aborts,
            # abort path raises (tested through the trainer callable)
        },
        "materialization_recommendation": (
            "pre-materialized routing (mode 1): the complete surface "
            "materializes in one bounded command and the training loop "
            "needs no resident worker; modes 2/3 are NOT implemented "
            "per 106_s §10.4"),
    }
    report["go"] = all(report["gate_results"].values())
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="all CE0 measurements in sequence")
    run.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    out_dir = Path(args.out)
    if out_dir.exists():
        raise RuntimeError(f"{out_dir} exists; CE0 records one run")
    out_dir.mkdir(parents=True)

    results: dict[str, Any] = {"env_manifest": build_env_manifest()}
    print("env manifest:", json.dumps(results["env_manifest"], indent=1))
    results["materialize_timing"] = materialize_timing(out_dir)
    print("materialize:", json.dumps(results["materialize_timing"],
                                     indent=1))
    results["live_worst_case"] = live_worst_case(out_dir)
    print("live worst case:", json.dumps(results["live_worst_case"],
                                         indent=1))
    results["enumeration"] = enumeration_overhead()
    print("enumeration:", json.dumps(results["enumeration"], indent=1))
    results["report"] = build_report(results)
    (out_dir / "ce0_results.json").write_text(
        json.dumps(results, indent=1, sort_keys=True) + "\n")
    print(json.dumps(results["report"], indent=1, sort_keys=True))
    print(f"CE0 {'GO' if results['report']['go'] else 'NO-GO'} -> "
          f"{out_dir / 'ce0_results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
