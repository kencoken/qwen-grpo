"""Formal amended-run entry points — 158_s §11, 175_s finding 3.

Thin, didactic, reproducible-from-the-commit helpers; no framework:

- `formal_context()` builds the lock-time execution bundle through
  the derive-everything constructor (`build_lock_bundle`), locating
  the reviewed preregistration and the committed lock record inside
  the repository itself (the lock record is discovered by its frozen
  name pattern and must be unique);
- `main()` exposes the five §11 commands verbatim:
  `probes` (pre-lock §5.4 suite, throwaway), `tranche` (CPU),
  `replay` (GPU B), `finalize` (post-B aggregate), and `archive`
  (byte-exact evidence copy + manifest + verification — also used
  for aborted runs before any recovery decision);
- `run_prelock_probes()` is the committed construction recipe for
  the §5.4 probe suite (fixed seed, fixed case counts), so the
  173_f/176_f probe records regenerate from the commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

from . import stage1_amend1 as am
from .profiles import canonical_json
from .types import InfrastructureError

PREREG_PATH = Path(
    "plans/conductor/"
    "177_f_stage_1_amend1_final_successor_prereg_rev2.md")
LOCK_RECORD_GLOB = "plans/conductor/*_f_stage_1_amend1_lock.md"
EVIDENCE_PARENT = Path("plans/conductor/evidence")
EVIDENCE_MANIFEST_KIND = "stage1-amend1-evidence-v1"


def locate_lock_record() -> Path:
    """The committed lock record, discovered from the repository by
    its frozen name pattern — exactly one must exist."""
    matches = sorted(Path(".").glob(LOCK_RECORD_GLOB))
    if len(matches) != 1:
        raise InfrastructureError(
            f"expected exactly one lock record matching "
            f"{LOCK_RECORD_GLOB!r}, found {len(matches)}")
    return matches[0]


def formal_context(*, prereg_path: Path | str | None = None,
                   lock_record_path: Path | str | None = None
                   ) -> dict[str, Any]:
    """The formal execution context: bundle/registry/env from the
    derive-everything lock-time constructor. Paths default to the
    committed documents themselves."""
    bundle, registry, env = am.build_lock_bundle(
        prereg_path=prereg_path if prereg_path is not None
        else PREREG_PATH,
        lock_record_path=lock_record_path if lock_record_path
        is not None else locate_lock_record())
    return {"bundle": bundle, "seed_registry": registry, "env": env}


# --- the committed §5.4 probe recipe (pre-lock, throwaway) ---------------------

def run_prelock_probes(n_cases: int = 120, trials_per_path: int = 50,
                       outer_trials: int = 20,
                       seed: int = 20260725) -> dict[str, Any]:
    """The §5.4 probe suite exactly as run for 173_f/176_f: fixed
    seeded case construction (item 1), the C projection (item 2), the
    10,000-inner worst-case benchmark (item 3), and the auditable
    worst-case tranche projection (items 4-5) against the FROZEN
    deadline literal. Throwaway inputs only; statistical outputs
    discarded."""
    import numpy as np

    from . import stage1_persistence as sp
    from . import stage1_tranche as st
    from . import stage1_validation as sv

    rng = np.random.default_rng(seed)
    cases = []
    for _ in range(n_cases):
        n = int(rng.integers(20, 500))
        k = rng.integers(0, sp.M + 1, size=n).astype(np.int64)
        j = rng.binomial(k, float(rng.uniform(0.01, 0.5))
                         ).astype(np.int64)
        cases.append((j, k,
                      "ordinary" if rng.random() < 0.5 else "fork"))
    agreement = sp.reference_agreement_probe(cases)

    c_proj = sp.benchmark_c_projection(trials_per_path=trials_per_path)
    bench = sv.benchmark_worst_case(outer_trials=outer_trials)
    measured = bench["seconds_per_outer_trial"]

    frozen = st.MEASURED_SECONDS_PER_OUTER_X1E6 / 1e6
    # auditable worst-case projection (175_s): every D1-D5 scenario
    # bounded by the measured worst path; D6-D8/A/C by their frozen
    # 30-minute budgets
    d15_hours = 5 * measured * sv.COVERAGE_OUTER_TRIALS / 3600.0
    total_bound_hours = d15_hours + 3 * (30 / 60.0)
    return {
        "probe_seed": seed,
        "reference_agreement": agreement,
        "c_projection": c_proj,
        "worst_case_seconds_per_outer": measured,
        "worst_case_x1e6": int(measured * 1e6),
        "frozen_literal_x1e6": st.MEASURED_SECONDS_PER_OUTER_X1E6,
        "frozen_d_scenario_deadline_seconds":
            st.D_SCENARIO_DEADLINE_SECONDS,
        "measured_within_sanity_band": bool(
            frozen / st.BENCHMARK_SANITY_FACTOR <= measured
            <= frozen * st.BENCHMARK_SANITY_FACTOR),
        "d15_worst_case_hours": round(d15_hours, 2),
        "cpu_tranche_worst_case_bound_hours":
            round(total_bound_hours, 2),
        "within_12h": total_bound_hours <= 12.0,
        "c_within_30min": bool(c_proj["within_budget"]),
    }


# --- byte-exact evidence archive (158_s §11 steps 11-12) -----------------------

def _copy_and_hash(src_dir: Path, dest_dir: Path, prefix: str,
                   files: dict[str, dict[str, Any]]) -> None:
    dest_dir.mkdir(parents=True, exist_ok=False)
    for path in sorted(src_dir.iterdir()):
        if not path.is_file():
            raise InfrastructureError(
                f"{src_dir}: unexpected non-file entry {path.name!r}")
        data = path.read_bytes()
        (dest_dir / path.name).write_bytes(data)
        files[f"{prefix}/{path.name}"] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data)}


def archive_evidence(validation_dir: Path | str | None = None,
                     replay_dir: Path | str | None = None,
                     evidence_parent: Path | str | None = None
                     ) -> dict[str, Any]:
    """Copy the exact immutable bytes of BOTH run roots into
    `plans/conductor/evidence/stage1_pre_ce1_amend1_{first12}/`,
    write the byte/SHA-256 manifest, and verify the copy
    byte-for-byte against the run roots. Works for complete AND
    aborted runs (an infrastructure abort archives the partial
    evidence before any recovery decision); the run statuses travel
    in the manifest. Refuses a pre-existing destination."""
    val_dir = Path(validation_dir if validation_dir is not None
                   else am.AMEND1_VALIDATION_RUN_ROOT)
    rep_dir = Path(replay_dir if replay_dir is not None
                   else am.AMEND1_REPLAY_RUN_ROOT)

    bundle = json.loads(
        (val_dir / "execution_bundle_manifest.json").read_text(
            encoding="utf-8"))
    body = {k: v for k, v in bundle.items()
            if k != "execution_bundle_sha256"}
    bundle_sha = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if bundle_sha != bundle.get("execution_bundle_sha256"):
        raise InfrastructureError(
            "persisted execution bundle fails its self-hash")
    if rep_dir.exists():
        rep_bundle = json.loads(
            (rep_dir / "execution_bundle_manifest.json").read_text(
                encoding="utf-8"))
        if rep_bundle != bundle:
            raise InfrastructureError(
                "the two run roots carry different execution bundles")

    dest = Path(evidence_parent if evidence_parent is not None
                else EVIDENCE_PARENT) / \
        f"stage1_pre_ce1_amend1_{bundle_sha[:12]}"
    if dest.exists():
        raise InfrastructureError(
            f"{dest} already exists — evidence archives are immutable")

    files: dict[str, dict[str, Any]] = {}
    _copy_and_hash(val_dir, dest / "validation", "validation", files)
    if rep_dir.exists():
        _copy_and_hash(rep_dir, dest / "replay", "replay", files)

    def _status(dir_: Path) -> str:
        record = dir_ / "run_record.json"
        if not record.exists():
            return "absent"
        return json.loads(record.read_text(encoding="utf-8")).get(
            "status", "unknown")

    manifest = {
        "manifest": EVIDENCE_MANIFEST_KIND,
        "execution_bundle_sha256": bundle_sha,
        "amendment_prereg_sha256": bundle["amendment_prereg_sha256"],
        "lock_record_sha256": bundle["lock_record_sha256"],
        "git_commit": bundle["git_commit"],
        "source_digest": bundle["source_digest"],
        "validation_status": _status(val_dir),
        "replay_status": _status(rep_dir) if rep_dir.exists()
        else "absent",
        "files": {k: files[k] for k in sorted(files)},
    }
    manifest_text = json.dumps(manifest, indent=1)
    (dest / "evidence_manifest.json").write_text(manifest_text,
                                                 encoding="utf-8")

    # verification pass: every archived byte equals its source byte
    # and its manifest row
    for rel, entry in manifest["files"].items():
        prefix, name = rel.split("/", 1)
        src = (val_dir if prefix == "validation" else rep_dir) / name
        archived = (dest / prefix / name).read_bytes()
        if archived != src.read_bytes():
            raise InfrastructureError(
                f"archive verification failed: {rel} != source bytes")
        if hashlib.sha256(archived).hexdigest() != entry["sha256"] or \
                len(archived) != entry["bytes"]:
            raise InfrastructureError(
                f"archive verification failed: {rel} != manifest row")
    manifest_sha = hashlib.sha256(
        manifest_text.encode("utf-8")).hexdigest()
    return {"evidence_dir": str(dest),
            "evidence_manifest_sha256": manifest_sha,
            "files": len(manifest["files"])}


# --- CLI -----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Formal amended-tranche commands (158_s §11)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("probes", "tranche", "replay", "finalize", "archive"):
        sub.add_parser(name)
    args = parser.parse_args(argv)

    if args.command == "probes":
        print(json.dumps(run_prelock_probes(), indent=1))
        return 0
    if args.command == "archive":
        print(json.dumps(archive_evidence(), indent=1))
        return 0

    context = formal_context()
    bundle, registry = context["bundle"], context["seed_registry"]
    if args.command == "tranche":
        from .stage1_tranche import run_amend1_tranche
        out = run_amend1_tranche(bundle, registry)
    elif args.command == "replay":
        from .stage1_replay import run_amend1_replay
        out = run_amend1_replay(bundle, registry)
    else:
        from .stage1_tranche import finalize_amend1_run
        out = finalize_amend1_run(bundle, registry)
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
