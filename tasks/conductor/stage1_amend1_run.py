"""Formal amended-run entry points — 158_s §11, 175_s finding 3,
hardened per 178_s findings 2-3.

Thin, didactic, reproducible-from-the-commit helpers; no framework:

- the CPU tranche creates THE canonical execution bundle (through the
  derive-everything constructor `build_lock_bundle`); replay and
  finalization CONSUME the persisted bundle from the CPU run root,
  verify it against current authoritative provenance, and require a
  complete CPU root BEFORE the replay root is claimed or any model
  loads (178_s finding 2 — CPU-first ordering is enforced here, not
  discovered at finalization);
- `main()` exposes the §11 commands verbatim: `probes` (pre-lock
  §5.4 suite, throwaway), `tranche` (CPU), `replay` (GPU B),
  `finalize` (post-B aggregate), and `archive --mode success|abort`;
- `archive_evidence()` has two EXPLICIT terminal modes (178_s
  finding 3): success validates authoritative provenance, both
  completed roots, exact file sets and the finalized aggregate;
  abort copies the partial bytes WITHOUT trusting their bundle and
  records every validation error in the manifest. Both modes stage
  the copy and atomically rename it into place, and both record the
  frozen command list and the structured run records as the formal
  logs;
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
    "180_f_stage_1_amend1_final_successor_prereg_rev3.md")
LOCK_RECORD_GLOB = "plans/conductor/*_f_stage_1_amend1_lock.md"
EVIDENCE_PARENT = Path("plans/conductor/evidence")
EVIDENCE_MANIFEST_KIND = "stage1-amend1-evidence-v1"
_HEX64 = frozenset("0123456789abcdef")

# the frozen §11 command list, recorded in every evidence manifest
FORMAL_COMMANDS = tuple(
    f"uv run python -m tasks.conductor.stage1_amend1_run {c}"
    for c in ("probes", "tranche", "replay", "finalize",
              "archive --mode success", "archive --mode abort"))


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
    """The TRANCHE execution context: bundle/registry/env from the
    derive-everything lock-time constructor. The CPU tranche is the
    only step that CREATES the canonical bundle; replay/finalize go
    through `persisted_context`. Paths default to the committed
    documents themselves."""
    bundle, registry, env = am.build_lock_bundle(
        prereg_path=prereg_path if prereg_path is not None
        else PREREG_PATH,
        lock_record_path=lock_record_path if lock_record_path
        is not None else locate_lock_record())
    return {"bundle": bundle, "seed_registry": registry, "env": env}


def persisted_context(*, validation_dir: Path | str | None = None,
                      prereg_path: Path | str | None = None,
                      lock_record_path: Path | str | None = None
                      ) -> dict[str, Any]:
    """The REPLAY/FINALIZE execution context (178_s finding 2):

    1. the CPU run root must exist, its run record must be
       `complete`, and it must hold exactly the pre-aggregate frozen
       file set — replay cannot start before the CPU tranche
       finished, and nothing runs twice;
    2. the PERSISTED bundle is loaded from that root and must EQUAL
       the bundle rebuilt from current authoritative provenance (the
       committed documents' bytes, clean HEAD, recomputed source
       digest, fresh validated environment manifest, canonical
       registry) — a moved HEAD or changed environment refuses HERE,
       before the replay root is claimed or any model loads.

    Returns the persisted bundle with the canonical registry."""
    val_dir = Path(validation_dir if validation_dir is not None
                   else am.AMEND1_VALIDATION_RUN_ROOT)
    bundle_path = val_dir / "execution_bundle_manifest.json"
    if not bundle_path.is_file():
        raise InfrastructureError(
            f"{val_dir} holds no execution bundle — run the CPU "
            "tranche first (178_s: CPU-first order)")
    persisted = json.loads(bundle_path.read_text(encoding="utf-8"))
    record = json.loads(
        (val_dir / "run_record.json").read_text(encoding="utf-8"))
    if record.get("status") != "complete":
        raise InfrastructureError(
            f"CPU tranche record status is {record.get('status')!r} "
            "— replay/finalize require a complete CPU root (178_s)")
    expected_pre = set(
        am.EXPECTED_RUN_FILES[am.AMEND1_VALIDATION_RUN_ROOT]) \
        - {"aggregate.json"}
    got = {p.name for p in val_dir.iterdir() if p.is_file()}
    if got != expected_pre:
        raise InfrastructureError(
            f"{val_dir}: pre-aggregate file set mismatch (missing "
            f"{sorted(expected_pre - got)}, extra "
            f"{sorted(got - expected_pre)})")
    rebuilt, registry, env = am.build_lock_bundle(
        prereg_path=prereg_path if prereg_path is not None
        else PREREG_PATH,
        lock_record_path=lock_record_path if lock_record_path
        is not None else locate_lock_record())
    if dict(persisted) != dict(rebuilt):
        raise InfrastructureError(
            "the persisted CPU-run bundle does not equal the bundle "
            "rebuilt from current authoritative provenance — the "
            "commit, documents, environment or registry moved since "
            "the CPU tranche (178_s finding 2)")
    return {"bundle": persisted, "seed_registry": registry,
            "env": env}


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


# --- byte-exact evidence archive (158_s §11 steps 11-12; 178_s finding 3) ------

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


def _bundle_self_hash_ok(bundle: Mapping[str, Any]) -> bool:
    body = {k: v for k, v in bundle.items()
            if k != "execution_bundle_sha256"}
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    return digest == bundle.get("execution_bundle_sha256")


def _run_status(dir_: Path) -> str:
    record = dir_ / "run_record.json"
    if not record.exists():
        return "absent"
    try:
        return json.loads(record.read_text(encoding="utf-8")).get(
            "status", "unknown")
    except ValueError:
        return "unreadable"


def archive_evidence(mode: str,
                     validation_dir: Path | str | None = None,
                     replay_dir: Path | str | None = None,
                     evidence_parent: Path | str | None = None,
                     prereg_path: Path | str | None = None,
                     lock_record_path: Path | str | None = None
                     ) -> dict[str, Any]:
    """Copy the exact immutable bytes of the run roots into
    `plans/conductor/evidence/stage1_pre_ce1_amend1_{first12}/` with
    a byte/length/SHA-256 manifest, the frozen command list, and the
    structured run records as the formal logs. Two EXPLICIT terminal
    modes (178_s finding 3):

    - `success`: the persisted bundle must pass its self-hash, equal
      the replay root's copy, AND equal the bundle rebuilt from
      current authoritative provenance; both run records must be
      `complete`; both roots must hold their EXACT frozen file sets
      (aggregate included) — anything less refuses;
    - `abort`: preserves whatever bytes exist WITHOUT trusting the
      bundle — every failed validation is RECORDED in the manifest's
      `validation_errors` instead of raising; the replay root may be
      absent.

    Both modes stage the copy under a temporary name, verify every
    archived byte against the sources and the manifest, then rename
    atomically into place — a failed copy never strands the
    immutable destination."""
    if mode not in ("success", "abort"):
        raise InfrastructureError(f"unknown archive mode {mode!r}")
    val_dir = Path(validation_dir if validation_dir is not None
                   else am.AMEND1_VALIDATION_RUN_ROOT)
    rep_dir = Path(replay_dir if replay_dir is not None
                   else am.AMEND1_REPLAY_RUN_ROOT)
    if not val_dir.is_dir():
        raise InfrastructureError(f"{val_dir} does not exist — "
                                  "nothing to archive")

    errors: list[str] = []
    bundle: Mapping[str, Any] | None = None
    bundle_path = val_dir / "execution_bundle_manifest.json"
    if bundle_path.is_file():
        try:
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        except ValueError as error:
            errors.append(f"validation bundle unreadable: {error}")
    else:
        errors.append("validation bundle manifest absent")
    if bundle is not None and not _bundle_self_hash_ok(bundle):
        errors.append("validation bundle fails its self-hash")
    if bundle is not None and rep_dir.is_dir() and \
            (rep_dir / "execution_bundle_manifest.json").is_file():
        try:
            rep_bundle = json.loads(
                (rep_dir / "execution_bundle_manifest.json").read_text(
                    encoding="utf-8"))
            if rep_bundle != bundle:
                errors.append("the two run roots carry different "
                              "execution bundles")
        except ValueError as error:
            errors.append(f"replay bundle unreadable: {error}")

    val_status = _run_status(val_dir)
    rep_status = _run_status(rep_dir) if rep_dir.is_dir() else "absent"

    if mode == "success":
        if errors:
            raise InfrastructureError(
                "success archive refused: " + "; ".join(errors))
        rebuilt, _, _ = am.build_lock_bundle(
            prereg_path=prereg_path if prereg_path is not None
            else PREREG_PATH,
            lock_record_path=lock_record_path if lock_record_path
            is not None else locate_lock_record())
        if dict(bundle) != dict(rebuilt):
            raise InfrastructureError(
                "success archive refused: persisted bundle != bundle "
                "rebuilt from current authoritative provenance")
        if val_status != "complete" or rep_status != "complete":
            raise InfrastructureError(
                f"success archive refused: run statuses "
                f"validation={val_status!r}, replay={rep_status!r}")
        am.verify_run_file_set(val_dir, am.AMEND1_VALIDATION_RUN_ROOT)
        am.verify_run_file_set(rep_dir, am.AMEND1_REPLAY_RUN_ROOT)
    else:
        # abort mode records, never trusts
        if val_status not in ("aborted", "complete"):
            errors.append(f"validation run status {val_status!r}")
        if rep_status not in ("aborted", "complete", "absent"):
            errors.append(f"replay run status {rep_status!r}")

    # destination identity: the claimed bundle hash when it is a
    # well-formed self-consistent value, else the byte hash of the
    # bundle file (abort mode only — success requires the real thing)
    claimed = (bundle or {}).get("execution_bundle_sha256")
    if isinstance(claimed, str) and len(claimed) == 64 and \
            set(claimed) <= _HEX64:
        first12, identity_basis = claimed[:12], "bundle_self_hash"
    else:
        raw = bundle_path.read_bytes() if bundle_path.is_file() \
            else b"missing-bundle"
        first12 = hashlib.sha256(raw).hexdigest()[:12]
        identity_basis = "bundle_file_bytes"

    parent = Path(evidence_parent if evidence_parent is not None
                  else EVIDENCE_PARENT)
    dest = parent / f"stage1_pre_ce1_amend1_{first12}"
    staging = parent / f".staging_stage1_pre_ce1_amend1_{first12}"
    if dest.exists():
        raise InfrastructureError(
            f"{dest} already exists — evidence archives are immutable")
    if staging.exists():
        raise InfrastructureError(
            f"{staging} already exists — remove the stale staging "
            "directory after investigating the failed copy")

    files: dict[str, dict[str, Any]] = {}
    _copy_and_hash(val_dir, staging / "validation", "validation",
                   files)
    if rep_dir.is_dir():
        _copy_and_hash(rep_dir, staging / "replay", "replay", files)

    manifest = {
        "manifest": EVIDENCE_MANIFEST_KIND,
        "mode": mode,
        "identity_basis": identity_basis,
        "execution_bundle_sha256": claimed if isinstance(claimed, str)
        else None,
        "validation_status": val_status,
        "replay_status": rep_status,
        "validation_errors": errors,
        "commands": list(FORMAL_COMMANDS),
        "formal_logs": [rel for rel in
                        ("validation/run_record.json",
                         "replay/run_record.json") if rel in files],
        "files": {k: files[k] for k in sorted(files)},
    }
    if mode == "success":
        manifest.update({
            "amendment_prereg_sha256":
                bundle["amendment_prereg_sha256"],
            "lock_record_sha256": bundle["lock_record_sha256"],
            "git_commit": bundle["git_commit"],
            "source_digest": bundle["source_digest"],
        })
    manifest_text = json.dumps(manifest, indent=1)
    (staging / "evidence_manifest.json").write_text(manifest_text,
                                                    encoding="utf-8")

    # verification pass over the STAGED copy, then the atomic rename
    for rel, entry in manifest["files"].items():
        prefix, name = rel.split("/", 1)
        src = (val_dir if prefix == "validation" else rep_dir) / name
        archived = (staging / prefix / name).read_bytes()
        if archived != src.read_bytes():
            raise InfrastructureError(
                f"archive verification failed: {rel} != source bytes")
        if hashlib.sha256(archived).hexdigest() != entry["sha256"] or \
                len(archived) != entry["bytes"]:
            raise InfrastructureError(
                f"archive verification failed: {rel} != manifest row")
    staging.rename(dest)
    manifest_sha = hashlib.sha256(
        manifest_text.encode("utf-8")).hexdigest()
    return {"evidence_dir": str(dest), "mode": mode,
            "evidence_manifest_sha256": manifest_sha,
            "validation_errors": errors,
            "files": len(manifest["files"])}


# --- CLI -----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Formal amended-tranche commands (158_s §11)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("probes", "tranche", "replay", "finalize"):
        sub.add_parser(name)
    archive = sub.add_parser("archive")
    archive.add_argument("--mode", required=True,
                         choices=("success", "abort"))
    args = parser.parse_args(argv)

    if args.command == "probes":
        print(json.dumps(run_prelock_probes(), indent=1))
        return 0
    if args.command == "archive":
        print(json.dumps(archive_evidence(args.mode), indent=1))
        return 0

    if args.command == "tranche":
        # the CPU tranche CREATES the canonical bundle (178_s)
        context = formal_context()
        from .stage1_tranche import run_amend1_tranche
        out = run_amend1_tranche(context["bundle"],
                                 context["seed_registry"])
    elif args.command == "replay":
        # replay CONSUMES the persisted bundle and requires the
        # complete CPU root before claiming anything (178_s)
        context = persisted_context()
        from .stage1_replay import run_amend1_replay
        out = run_amend1_replay(context["bundle"],
                                context["seed_registry"])
    else:
        context = persisted_context()
        from .stage1_tranche import finalize_amend1_run
        out = finalize_amend1_run(context["bundle"],
                                  context["seed_registry"])
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
