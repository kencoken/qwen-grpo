"""Executable attempt-1 ledger verifier — 188_s sign-off blocker.

READ-ONLY re-derivation of the 186_s §3 component ledger from the
immutable abort archive `stage1_pre_ce1_amend1_9b5f1ab85f26`, through
the FROZEN loaders and evaluators. Verifies, in order:

1. the archive manifest's own SHA-256 against the pinned 185_f value,
   and every archived file against its manifest row (sha256 + bytes);
2. the persisted execution bundle's self-hash and cross-root
   equality;
3. A/C/D artifact identities and schemas via the frozen fail-closed
   loaders (exact key sets, amend1 tags, bundle binding, count
   identities);
4. the exact gated A rows (frozen grid enumeration + acceptance
   constants), the C §5.3 hard-path criteria, every D Wilson upper
   vs its frozen ceiling, and the D8 per-look branch counts;
5. the run statuses (validation complete / replay aborted), the
   ABSENCE of B completions and of any aggregate; and
6. the D5 binomial tail under exact nominality.

Run: `uv run python -m tasks.conductor.stage1_attempt1_ledger`
Exit 0 with the printed record iff every check passes; any
discrepancy raises. Writes nothing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scipy.stats import binom

from . import stage1_persistence as sp
from . import stage1_tranche as st
from . import stage1_validation as sv
from .profiles import canonical_json
from .types import InfrastructureError

ARCHIVE = Path("plans/conductor/evidence/"
               "stage1_pre_ce1_amend1_9b5f1ab85f26")
PINNED_MANIFEST_SHA = (
    "114cf207dd98e8578b814602e109a5261ce2ddf1454d5ace185dd388380d31c1")


def _fail(msg: str) -> None:
    raise InfrastructureError(f"attempt-1 ledger verification: {msg}")


def main() -> int:
    # --- 1. archive manifest + every consumed file ---------------------
    manifest_bytes = (ARCHIVE / "evidence_manifest.json").read_bytes()
    got_sha = hashlib.sha256(manifest_bytes).hexdigest()
    if got_sha != PINNED_MANIFEST_SHA:
        _fail(f"manifest sha {got_sha} != pinned {PINNED_MANIFEST_SHA}")
    manifest = json.loads(manifest_bytes)
    if manifest["mode"] != "abort":
        _fail("archive is not the abort-mode archive")
    for rel, entry in manifest["files"].items():
        data = (ARCHIVE / rel).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"] or \
                len(data) != entry["bytes"]:
            _fail(f"{rel} does not match its manifest row")
    print(f"1. archive manifest {got_sha[:12]}… verified; "
          f"{len(manifest['files'])} files match their rows")

    # --- 2. execution bundle self-hash + cross-root equality -----------
    val, rep = ARCHIVE / "validation", ARCHIVE / "replay"
    bundle = json.loads(
        (val / "execution_bundle_manifest.json").read_text("utf-8"))
    body = {k: v for k, v in bundle.items()
            if k != "execution_bundle_sha256"}
    exec_sha = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if exec_sha != bundle["execution_bundle_sha256"]:
        _fail("bundle fails its self-hash")
    if exec_sha != manifest["execution_bundle_sha256"]:
        _fail("bundle sha != manifest identity")
    rep_bundle = json.loads(
        (rep / "execution_bundle_manifest.json").read_text("utf-8"))
    if rep_bundle != bundle:
        _fail("run roots carry different bundles")
    print(f"2. execution bundle {exec_sha[:12]}… self-hash + "
          "cross-root equality verified")

    # --- 3. artifact identities/schemas via the frozen loaders ---------
    reg = st.expected_result_keys()
    a = st.load_artifact(
        json.loads((val / "artifact_A.json").read_text("utf-8")), "A",
        reg["A_position"] | reg["A_router"], exec_sha,
        tag="stage1-tranche-artifact-amend1-v1")
    c = sp.load_amended_c_artifact(
        json.loads((val / "artifact_C.json").read_text("utf-8")),
        exec_sha)
    d = st.load_artifact(
        json.loads((val / "artifact_D.json").read_text("utf-8")), "D",
        frozenset(s["id"] for s in st.D_SCENARIOS), exec_sha,
        tag="stage1-tranche-artifact-amend1-v1")
    from . import stage1_amend1 as am
    am.validate_amend1_rows("D_branch", d["branch_counts"])
    if set(d["branch_counts"]) != st.expected_branch_keys():
        _fail("D branch telemetry != the exact per-look key set")
    print("3. A/C/D reload through the frozen fail-closed loaders "
          "(exact keys, amend1 tags, bundle binding, schemas)")

    # --- 4a. exact gated A rows -----------------------------------------
    lbs = []
    for scen, delta, sigma in st.a_position_cells():
        if delta == sv.ACCEPT_DELTA and sigma <= sv.ACCEPT_SIGMA_MAX:
            row = a["results"][f"A|{scen}|{delta}|{sigma}|{sv.POWER_TRIALS}"]
            lbs.append((sv.wilson_lower(row["pass_count"],
                                        row["trials"]),
                        f"A|{scen}|{delta}|{sigma}"))
    for mix, effect, sigma in st.a_router_cells():
        if effect == sv.ROUTER_ACCEPT_EFFECT and \
                sigma <= sv.ACCEPT_SIGMA_MAX:
            row = a["results"][
                f"A-router|{mix}|{effect}|{sigma}|{sv.POWER_TRIALS}"]
            lbs.append((sv.wilson_lower(row["pass_count"],
                                        row["trials"]),
                        f"A-router|{mix}|{effect}|{sigma}"))
    lbs.sort()
    if len(lbs) != 12 or any(lb < sv.ACCEPT_PASS_WILSON_LB
                             for lb, _ in lbs):
        _fail(f"gated A rows: {len(lbs)} cells, "
              f"worst {lbs[0] if lbs else None}")
    print(f"4a. A: 12/12 gated cells >= {sv.ACCEPT_PASS_WILSON_LB}; "
          f"worst LB {lbs[0][0]:.5f} ({lbs[0][1]})")

    # --- 4b. C hard paths ------------------------------------------------
    c_verdict = sp.hard_path_acceptance(c["results"])
    if not c_verdict["passes"]:
        _fail(f"C hard paths: {c_verdict['failures']}")
    print("4b. C: hard-path criteria met "
          f"(failures: {c_verdict['failures']})")

    # --- 4c. D ceilings + D8 branch counts -------------------------------
    for scen in st.D_SCENARIOS:
        row = d["results"][scen["id"]]
        ub = sv.wilson_upper(row["error_count"], row["trials"])
        ceil = sv.coverage_alpha_ceiling(float(scen["allocated_alpha"]))
        state = "INSIDE" if ub <= ceil else "EXCEEDS"
        expected = "EXCEEDS" if scen["id"] == "D5_pilot_hetero_unequal" \
            else "INSIDE"
        if state != expected:
            _fail(f"{scen['id']}: {state}, ledger says {expected}")
        print(f"4c. {scen['id']}: {row['error_count']}/{row['trials']}"
              f" UB={ub:.4f} ceiling={ceil:.5f} -> {state}")
    for key in sorted(st.expected_branch_keys()):
        if key.startswith("D8"):
            print(f"4c. branch {key}: {dict(d['branch_counts'][key])}")
    if not st.d8_branch_support_ok(d["branch_counts"]):
        _fail("D8 branch support")
    print("4c. D8 branch support: ok")

    # --- 5. statuses, zero B completions, aggregate absence --------------
    val_rec = json.loads((val / "run_record.json").read_text("utf-8"))
    rep_rec = json.loads((rep / "run_record.json").read_text("utf-8"))
    if val_rec["status"] != "complete":
        _fail(f"validation status {val_rec['status']!r}")
    if rep_rec["status"] != "aborted" or rep_rec["wall_seconds"] > 5:
        _fail(f"replay record {rep_rec!r}")
    for absent in ("raw_completions.json", "artifact_B.json"):
        if (rep / absent).exists() or \
                f"replay/{absent}" in manifest["files"]:
            _fail(f"B output {absent} unexpectedly present")
    if (val / "aggregate.json").exists() or \
            "validation/aggregate.json" in manifest["files"]:
        _fail("aggregate unexpectedly present")
    print("5. statuses: validation=complete, replay=aborted "
          f"(wall {rep_rec['wall_seconds']}s, error "
          f"{rep_rec['error']!r}); zero B completions; no aggregate")

    # --- 6. D5 binomial tail ----------------------------------------------
    tail = float(binom.sf(156, 5000, 0.025))
    print(f"6. P[K>=157 | n=5000, p=0.025] = {tail:.6f}")

    print("ALL ATTEMPT-1 LEDGER CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
