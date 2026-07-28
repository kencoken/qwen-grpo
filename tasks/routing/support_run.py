"""The tracked Step-4 support-materialization runner (220_s F5,
lifecycle-hardened per 222_s).

This module IS the driver the support-launch manifest names. The
lifecycle is failure-safe (222_s F1):

    prepare   → declaration, LIVE environment manifest, support-launch
                manifest, frozen probe rule — persisted once under
                `run_dir/prelaunch/`; the freeze document commits the
                manifest hash and the ledger head.
    execute   → 1. FULL pre-admission validation: manifest rehash +
                   live source recompute against the externally frozen
                   hash; probe rule revalidated and matched to the
                   manifest; frozen environment fully revalidated; the
                   LIVE environment rebuilt and ATTESTED against the
                   frozen snapshot (222_s F2 — `git_commit` alone may
                   differ, the documentation-only freeze-commit
                   policy; every other load-bearing field must match);
                   every output path preflighted.
                2. ADMIT (irreversible only after everything above).
                3. Post-admission work under an abort handler: any
                   failure preserves partial evidence and appends an
                   ABORTED closeout with the measured cost — the
                   launch is never left open.
                4. Outputs persisted AND verified by re-reading before
                   the successful closeout is recorded.

Recovery rule (222_s F1, reviewed): an initial support launch closed
out ABORTED may be replaced by a NEW support launch under a NEW
reviewed freeze (fresh `prepare`, fresh run_dir, fresh freeze
document); the ledger admits it because only open-or-completed
support launches block the no-reserve path. The aborted launch's
measured cost stays charged to the envelope.

The runtime and environment builders default to the real GPU stack;
`_runtime_factory` / `_environment_builder` are test-only injection
points, the established stage1 pattern.

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
from .cohorts import bind_probe_cohort, validate_probe_rule
from .ledger import LEDGER_PATH, admit_and_append_launch, \
    append_ledger_entry

DRIVER = "tasks/routing/support_run.py"
SUPPORT_CACHE_PATH = "runs/routing-dev/support-cache/cache.sqlite"

_PRELAUNCH_FILES = ("declaration.json", "env_manifest.json",
                    "support_launch.json", "probe_rule.json")
_OUTPUT_FILES = ("disclosure.json", "c_fixed_dev.json",
                 "probe_cohort.json", "run_record.json")

# 222_s F2: the load-bearing environment fields that must be IDENTICAL
# between the frozen prepare-time snapshot and the live execute-time
# environment. `git_commit` is deliberately absent: the freeze
# document itself is a documentation-only commit between preparation
# and launch. A source change shows up in stage1_source_sha256 and
# refuses.
ATTESTED_ENV_FIELDS = ("gpu", "torch", "numpy", "scipy",
                       "uv_lock_sha256", "stage1_source_sha256",
                       "stage1_source_files", "git_dirty")


def _default_runtime():
    from tasks.conductor.payoff_support import canonical_support_profile
    from tasks.conductor.pool_runtime import build_pool_runtime
    profile = canonical_support_profile()
    profile["cache_path"] = SUPPORT_CACHE_PATH
    return build_pool_runtime(profile)


def _default_environment() -> dict[str, Any]:
    from tasks.conductor.stage1_manifest import build_stage1_env_manifest
    return build_stage1_env_manifest()


def attest_environment(frozen: Mapping[str, Any],
                       live: Mapping[str, Any]) -> None:
    """222_s F2: the archived environment must describe the actual
    run. Every load-bearing field must match the live host; only
    git_commit may differ (the freeze commit)."""
    mismatches = [field for field in ATTESTED_ENV_FIELDS
                  if frozen.get(field) != live.get(field)]
    if mismatches:
        raise InfrastructureError(
            f"live environment differs from the frozen snapshot on "
            f"{mismatches} — the archived environment would not "
            "describe the actual run (222_s F2)")


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
    `run_dir/prelaunch/`, exactly once."""
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


def _persist_verified(path: Path, payload: Mapping[str, Any]) -> None:
    """222_s F1: outputs are written once and VERIFIED by re-reading
    before completion is recorded."""
    if path.exists():
        raise InfrastructureError(f"{path} exists; refusing to "
                                  "overwrite a recorded output")
    path.write_text(json.dumps(payload, indent=1, sort_keys=True)
                    + "\n", encoding="utf-8")
    if json.loads(path.read_text(encoding="utf-8")) != json.loads(
            json.dumps(payload)):
        raise InfrastructureError(
            f"{path} did not verify after writing")


def execute_support_run(*, run_dir: str | Path,
                        expected_manifest_sha256: str,
                        expected_head_sha256: str | None,
                        question: str, motivating_evidence: str,
                        ledger_path: str | Path = LEDGER_PATH,
                        _runtime_factory: Callable[[], Any]
                        | None = None,
                        _environment_builder:
                        Callable[[], dict[str, Any]] | None = None
                        ) -> dict[str, Any]:
    """Phase 2: fully validate BEFORE the irreversible admission; run
    under an abort handler AFTER it; verify outputs before recording
    success."""
    run_dir = Path(run_dir)
    prelaunch = _load_prelaunch(run_dir)
    declaration = prelaunch["declaration"]
    frozen_env = prelaunch["env_manifest"]
    manifest = prelaunch["support_launch"]
    frozen_rule = prelaunch["probe_rule"]

    # --- 1. FULL pre-admission validation (222_s F1) -------------------
    manifest = dev_support.validate_support_launch_manifest(
        manifest, declaration)
    if manifest["manifest_sha256"] != expected_manifest_sha256:
        raise InfrastructureError(
            "prepared support-launch manifest is not the externally "
            "frozen one")
    validate_probe_rule(frozen_rule)
    if frozen_rule["rule_sha256"] != manifest["probe_rule_sha256"]:
        raise InfrastructureError(
            "persisted probe rule does not match the manifest")
    if dev_support.validate_environment_manifest_binding(frozen_env) \
            != manifest["environment_manifest_sha256"]:
        raise InfrastructureError(
            "persisted environment manifest is not the one the "
            "manifest binds")
    live_env = (_environment_builder or _default_environment)()
    attest_environment(frozen_env, live_env)
    surface_dir = run_dir / "surface"
    output_paths = [run_dir / name for name in _OUTPUT_FILES]
    output_paths.append(run_dir / "execute_env_manifest.json")
    for path in [surface_dir, *output_paths]:
        if path.exists():
            raise InfrastructureError(
                f"{path} exists — outputs are preflighted before "
                "admission (222_s F1)")

    # --- 2. ADMIT (irreversible from here) -----------------------------
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
    started = time.monotonic()

    # --- 3. Post-admission work under the abort handler (222_s F1) -----
    try:
        _persist_verified(run_dir / "execute_env_manifest.json",
                          live_env)
        rt = (_runtime_factory or _default_runtime)()
        try:
            dev_support.materialize_dev_support(
                rt, declaration, surface_dir, launch_manifest=manifest,
                environment_manifest=frozen_env,
                expected_manifest_sha256=expected_manifest_sha256,
                ledger_path=ledger_path, expected_head_sha256=head)
        finally:
            rt.close()
        lock = dev_support.build_surface_lock(surface_dir)
        loaded = dev_support.load_dev_surface(
            surface_dir, expected_lock_sha256=lock["lock_sha256"])
        yields = dev_support.direction_yields(loaded["surface"],
                                              loaded["observations"])
        c_fixed = dev_support.select_c_fixed_dev(loaded)
        bound = bind_probe_cohort(frozen_rule, surface_dir,
                                  lock["lock_sha256"])
        record = {
            "run": "routing-dev-support-materialization-v1",
            "surface_dir": str(surface_dir),
            "support_launch_sha256": manifest["manifest_sha256"],
            "surface_lock_sha256": lock["lock_sha256"],
            "launch_entry_sha256": head,
            "direction_yields": yields["per_cell"],
            "c_fixed_dev_sha256": c_fixed["record_sha256"],
            "probe_cohort_sha256": bound["cohort_sha256"],
        }
        # 222_s F1: persist AND verify every output BEFORE recording
        # successful completion.
        for name, payload in (("disclosure.json", yields),
                              ("c_fixed_dev.json", c_fixed),
                              ("probe_cohort.json", bound),
                              ("run_record.json", record)):
            _persist_verified(run_dir / name, payload)
    except BaseException as error:
        measured = round((time.monotonic() - started) / 3600.0, 4)
        append_ledger_entry(
            {"kind": "closeout", "question": question,
             "motivating_evidence": "support run ABORTED",
             "freeze": {"support_launch_sha256":
                        manifest["manifest_sha256"]},
             "parent": head,
             "budget_allocated_gpu_hours": 0.0,
             "budget_consumed_gpu_hours": measured,
             "closes_entry_sha256": head,
             "terminal_status": "aborted",
             "interpretation": f"{type(error).__name__}: {error}",
             "outcome_informed": False,
             "outcome_pointer": str(run_dir)},
            head, ledger_path)
        raise

    # --- 4. SUCCESS closeout (only after verified outputs) -------------
    measured = round((time.monotonic() - started) / 3600.0, 4)
    closeout = append_ledger_entry(
        {"kind": "closeout", "question": question,
         "motivating_evidence": "measured support run cost",
         "freeze": {"surface_lock_sha256": lock["lock_sha256"]},
         "parent": head,
         "budget_allocated_gpu_hours": 0.0,
         "budget_consumed_gpu_hours": measured,
         "closes_entry_sha256": head,
         "terminal_status": "complete",
         "outcome_informed": False,
         "outcome_pointer": str(run_dir / "run_record.json")},
        head, ledger_path)
    return {**record, "measured_gpu_hours": measured,
            "c_fixed_dev": c_fixed, "probe_cohort": bound,
            "closeout_entry_sha256": closeout["entry_sha256"],
            "ledger_head": closeout["entry_sha256"]}


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
