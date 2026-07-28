"""The tracked Step-4 support-materialization runner (220_s F5).

This module IS the driver the support-launch manifest names: it owns
the whole sequence

    prepare  → the declaration, the LIVE environment manifest, and
               the support-launch manifest, persisted under the run
               root (the freeze document commits the manifest hash
               and the ledger head);
    execute  → admit-and-append the support launch (the recorded
               entry names the manifest and carries its budget),
               materialize under that admission, build the surface
               lock, load it back fail-closed, disclose the
               direction yields, select c_fixed_dev, bind the probe
               cohort, and close the launch out with the measured
               cost.

The runtime and environment builders default to the real GPU stack
(`build_pool_runtime` on the frozen four-worker profile,
`build_stage1_env_manifest`); `_runtime_factory` /
`_environment_builder` are test-only injection points, the
established stage1 pattern.

CLI:
  uv run python -m tasks.routing.support_run prepare --run-dir DIR ...
  uv run python -m tasks.routing.support_run execute --run-dir DIR ...
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from tasks.conductor.types import InfrastructureError

from . import dev_support
from .charter import PROBE_CEILING_HOURS
from .cohorts import bind_probe_cohort, validate_probe_rule
from .ledger import LEDGER_PATH, admit_and_append_launch, \
    append_ledger_entry

DRIVER = "tasks/routing/support_run.py"
SUPPORT_CACHE_PATH = "runs/routing-dev/support-cache/cache.sqlite"

_PRELAUNCH_FILES = ("declaration.json", "env_manifest.json",
                    "support_launch.json", "probe_rule.json")


def _default_runtime():
    from tasks.conductor.payoff_support import canonical_support_profile
    from tasks.conductor.pool_runtime import build_pool_runtime
    profile = canonical_support_profile()
    profile["cache_path"] = SUPPORT_CACHE_PATH
    return build_pool_runtime(profile)


def _default_environment() -> dict[str, Any]:
    from tasks.conductor.stage1_manifest import build_stage1_env_manifest
    return build_stage1_env_manifest()


def prepare_support_launch(*, run_dir: str | Path, tag: str,
                           cohort: Mapping[str, Any],
                           renderers, visibility: str,
                           frozen_probe_rule: Mapping[str, Any],
                           search_cap: int, budget_gpu_hours: float,
                           _runtime_factory: Callable[[], Any]
                           | None = None,
                           _environment_builder:
                           Callable[[], dict[str, Any]] | None = None
                           ) -> dict[str, Any]:
    """Phase 1: build and persist every prelaunch input under
    `run_dir/prelaunch/`. The LIVE environment manifest is built here
    (220_s F2 — never caller-asserted); the returned manifest hash is
    what the freeze document commits, together with the ledger head.
    """
    run_dir = Path(run_dir)
    prelaunch = run_dir / "prelaunch"
    if prelaunch.exists():
        raise InfrastructureError(
            f"{prelaunch} exists; a launch is prepared exactly once")
    validate_probe_rule(frozen_probe_rule)
    rt = (_runtime_factory or _default_runtime)()
    try:
        declaration = dev_support.build_dev_declaration(
            rt, tag=tag, namespace="routing_dev", cohort=cohort,
            renderers=renderers, visibility=visibility)
    finally:
        rt.close()
    environment = (_environment_builder or _default_environment)()
    manifest = dev_support.build_support_launch_manifest(
        declaration=declaration, frozen_probe_rule=frozen_probe_rule,
        search_cap=search_cap, budget_gpu_hours=budget_gpu_hours,
        driver=DRIVER, environment_manifest=environment)
    prelaunch.mkdir(parents=True)
    for name, payload in (("declaration.json", declaration),
                          ("env_manifest.json", environment),
                          ("support_launch.json", manifest),
                          ("probe_rule.json",
                           dict(frozen_probe_rule))):
        (prelaunch / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    return manifest


def _load_prelaunch(run_dir: Path) -> dict[str, Any]:
    prelaunch = run_dir / "prelaunch"
    out: dict[str, Any] = {}
    for name in _PRELAUNCH_FILES:
        path = prelaunch / name
        if not path.exists():
            raise InfrastructureError(
                f"{path} is missing — run `prepare` first")
        out[name.split(".")[0]] = json.loads(
            path.read_text(encoding="utf-8"))
    return out


def execute_support_run(*, run_dir: str | Path,
                        expected_manifest_sha256: str,
                        expected_head_sha256: str | None,
                        question: str, motivating_evidence: str,
                        ledger_path: str | Path = LEDGER_PATH,
                        _runtime_factory: Callable[[], Any]
                        | None = None) -> dict[str, Any]:
    """Phase 2: the admitted, recorded, measured run. The sequence is
    fixed; every boundary consumes the frozen identities persisted by
    `prepare` and the externally committed manifest hash + ledger
    head from the freeze document."""
    run_dir = Path(run_dir)
    prelaunch = _load_prelaunch(run_dir)
    declaration = prelaunch["declaration"]
    environment = prelaunch["env_manifest"]
    manifest = prelaunch["support_launch"]
    frozen_rule = prelaunch["probe_rule"]
    manifest = dev_support.validate_support_launch_manifest(
        manifest, declaration)
    if manifest["manifest_sha256"] != expected_manifest_sha256:
        raise InfrastructureError(
            "prepared support-launch manifest is not the externally "
            "frozen one")
    if frozen_rule["rule_sha256"] != manifest["probe_rule_sha256"]:
        raise InfrastructureError(
            "persisted probe rule does not match the manifest")
    if manifest["budget_gpu_hours"] > PROBE_CEILING_HOURS:
        raise InfrastructureError(
            f"support budget {manifest['budget_gpu_hours']} exceeds "
            f"the {PROBE_CEILING_HOURS} GPU-h tranche posture — "
            "revisit the freeze")

    # 1. ADMIT: the recorded entry names the manifest and its budget.
    entry = {
        "kind": "support_materialization",
        "question": question,
        "motivating_evidence": motivating_evidence,
        "freeze": {
            "support_launch_sha256": manifest["manifest_sha256"],
            "probe_rule_sha256": manifest["probe_rule_sha256"],
        },
        "parent": None,
        "budget_allocated_gpu_hours": manifest["budget_gpu_hours"],
        "outcome_informed": False,
        "cohort_selection": "outcome_blind",
    }
    admitted = admit_and_append_launch(entry, expected_head_sha256,
                                       ledger_path,
                                       launch_manifest=manifest)
    head = admitted["entry_sha256"]

    # 2. MATERIALIZE under the admission.
    started = time.monotonic()
    surface_dir = run_dir / "surface"
    rt = (_runtime_factory or _default_runtime)()
    try:
        dev_support.materialize_dev_support(
            rt, declaration, surface_dir, launch_manifest=manifest,
            environment_manifest=environment,
            expected_manifest_sha256=expected_manifest_sha256,
            ledger_path=ledger_path, expected_head_sha256=head)
    finally:
        rt.close()

    # 3. LOCK, reload fail-closed, disclose, select, bind.
    lock = dev_support.build_surface_lock(surface_dir)
    loaded = dev_support.load_dev_surface(
        surface_dir, expected_lock_sha256=lock["lock_sha256"])
    yields = dev_support.direction_yields(loaded["surface"],
                                          loaded["observations"])
    c_fixed = dev_support.select_c_fixed_dev(loaded)
    bound = bind_probe_cohort(frozen_rule, surface_dir,
                              lock["lock_sha256"])
    measured_hours = (time.monotonic() - started) / 3600.0

    # 4. CLOSE OUT with the measured cost.
    closeout = append_ledger_entry(
        {"kind": "closeout", "question": question,
         "motivating_evidence": "measured support run cost",
         "freeze": {"surface_lock_sha256": lock["lock_sha256"]},
         "parent": head,
         "budget_allocated_gpu_hours": 0.0,
         "budget_consumed_gpu_hours": round(measured_hours, 4),
         "closes_entry_sha256": head,
         "outcome_informed": False,
         "outcome_pointer": str(surface_dir)},
        head, ledger_path)

    record = {
        "run": "routing-dev-support-materialization-v1",
        "surface_dir": str(surface_dir),
        "support_launch_sha256": manifest["manifest_sha256"],
        "surface_lock_sha256": lock["lock_sha256"],
        "launch_entry_sha256": head,
        "closeout_entry_sha256": closeout["entry_sha256"],
        "ledger_head": closeout["entry_sha256"],
        "measured_gpu_hours": round(measured_hours, 4),
        "direction_yields": yields["per_cell"],
        "c_fixed_dev": c_fixed,
        "probe_cohort": bound,
    }
    for name, payload in (("disclosure.json", yields),
                          ("c_fixed_dev.json", c_fixed),
                          ("probe_cohort.json", bound),
                          ("run_record.json", record)):
        path = run_dir / name
        if path.exists():
            raise InfrastructureError(f"{path} exists; refusing to "
                                      "overwrite a recorded output")
        path.write_text(json.dumps(payload, indent=1, sort_keys=True)
                        + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--run-dir", required=True)
    prepare.add_argument("--config", required=True,
                         help="JSON file with tag/cohort/renderers/"
                         "visibility/probe rule/search cap/budget")
    execute = sub.add_parser("execute")
    execute.add_argument("--run-dir", required=True)
    execute.add_argument("--manifest-sha256", required=True)
    execute.add_argument("--ledger-head", required=True,
                         help="externally committed head, or the "
                         "literal 'empty'")
    execute.add_argument("--question", required=True)
    execute.add_argument("--evidence", required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        config = json.loads(Path(args.config).read_text("utf-8"))
        manifest = prepare_support_launch(
            run_dir=args.run_dir, tag=config["tag"],
            cohort=config["cohort"], renderers=config["renderers"],
            visibility=config["visibility"],
            frozen_probe_rule=config["frozen_probe_rule"],
            search_cap=config["search_cap"],
            budget_gpu_hours=config["budget_gpu_hours"])
        print(json.dumps(manifest, indent=1, sort_keys=True))
    else:
        head = (None if args.ledger_head == "empty"
                else args.ledger_head)
        record = execute_support_run(
            run_dir=args.run_dir,
            expected_manifest_sha256=args.manifest_sha256,
            expected_head_sha256=head, question=args.question,
            motivating_evidence=args.evidence)
        print(json.dumps(record, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
