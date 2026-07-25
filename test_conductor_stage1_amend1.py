"""Unit-A tests for the 158_s amend-once contract (160_f).

Covers the v1 evidence archive verifier (byte-exact, tamper-refusing),
the split seed domains and canonical registry, atomic run-root claims,
the execution-bundle manifest, the persistence branch contract
constants, amended registries, and old-artifact refusal. No frozen
simulation runs here.
"""

import json
import shutil

import pytest

from tasks.conductor import stage1, stage1_validation as sv
from tasks.conductor import stage1_amend1 as am
from tasks.conductor import stage1_tranche as st
from tasks.conductor.types import InfrastructureError

EXEC_SHA = "e" * 64


# --- §2: v1 evidence archive -----------------------------------------------------

def test_v1_evidence_archive_verifies():
    manifest_sha = am.verify_v1_evidence_archive()
    assert len(manifest_sha) == 64
    # deterministic across calls
    assert manifest_sha == am.verify_v1_evidence_archive()


def test_v1_evidence_archive_tamper_refuses(tmp_path):
    root = tmp_path / "archive"
    shutil.copytree(am.V1_EVIDENCE_DIR, root)
    # flip one byte in a frozen file
    p = root / "agreement.json"
    data = bytearray(p.read_bytes())
    data[-2] ^= 0x01
    p.write_bytes(bytes(data))
    with pytest.raises(InfrastructureError, match="sha256"):
        am.verify_v1_evidence_archive(root)
    # missing file refuses
    shutil.copytree(am.V1_EVIDENCE_DIR, tmp_path / "a2")
    (tmp_path / "a2" / "artifact_A.json").unlink()
    with pytest.raises(InfrastructureError, match="missing"):
        am.verify_v1_evidence_archive(tmp_path / "a2")
    # manifest disagreeing with bytes refuses
    shutil.copytree(am.V1_EVIDENCE_DIR, tmp_path / "a3")
    mp = tmp_path / "a3" / "evidence_manifest.json"
    m = json.loads(mp.read_text())
    m["files"]["benchmark.json"]["bytes"] += 1
    mp.write_text(json.dumps(m, sort_keys=True, indent=1))
    with pytest.raises(InfrastructureError, match="disagrees"):
        am.verify_v1_evidence_archive(tmp_path / "a3")


# --- §9.3: seed domains and registry ------------------------------------------------

def test_db_domain_reproduces_v1_scenario_seeds():
    # D and B seeds were never exposed; the retained domain must
    # reproduce the v1 derivation EXACTLY
    for key in ("D1_seq_null_ordinary_div3|0",
                "D5_pilot_hetero_unequal|4999",
                "B|obs|" + "p" * 64 + "|000"):
        assert am.seed(am.DB_SEED_DOMAIN, key) == sv.scenario_seed(key)


def test_ac_domain_differs_from_v1():
    for key in ("A|ordinary_div1|0.15|0.5|10000",
                am.c_path_key("fork", 0.60, 0.05, "cluster_correlated")):
        assert am.seed(am.AC_SEED_DOMAIN, key) != sv.scenario_seed(key)


def test_seed_registry_properties():
    reg = am.build_seed_registry()
    # completeness: 48 A + 24 router + 48 C paths + 8x5000 D
    assert len(reg) == 48 + 24 + 48 + 8 * 5_000
    assert all(0 <= v < 2 ** 64 for v in reg.values())
    # A/C entries use the fresh domain; D entries the retained one
    a_key = "A|ordinary_div1|0.15|0.5|10000"
    assert reg[a_key] == am.seed(am.AC_SEED_DOMAIN, a_key)
    assert reg[a_key] != sv.scenario_seed(a_key)
    d_key = "D3_equiv_boundary_plus|123"
    assert reg[d_key] == sv.scenario_seed(d_key)
    # digest deterministic
    assert am.seed_registry_digest(reg) == \
        am.seed_registry_digest(am.build_seed_registry())


def test_c_path_registry_cardinalities():
    assert len(am.c_path_cells()) == 48
    assert len(am.c_marginal_keys()) == 120
    key = am.c_path_key("ordinary", 0.65, 0.05, "cluster_correlated")
    assert key.endswith("|10000|coupled-path-v1")
    # look sizes are NOT in path keys
    assert "look" not in key
    assert any(k.endswith("|look500") for k in am.c_marginal_keys())
    # fork marginals use the AMENDED looks
    fork_marginals = {k for k in am.c_marginal_keys() if "|fork|" in k}
    assert all(k.endswith(("|look100", "|look500"))
               for k in fork_marginals)


def test_amended_d_registry():
    assert len(am.AMEND1_D_IDS) == 8
    assert "D7_persist_rowdispersed_theta10" in am.AMEND1_D_IDS
    assert "D8_persist_hybrid_theta01_fork" in am.AMEND1_D_IDS
    assert set(am.AMEND1_D_ALPHAS) == set(am.AMEND1_D_IDS)
    for d_id in ("D6_persist_const_theta10",
                 "D7_persist_rowdispersed_theta10",
                 "D8_persist_hybrid_theta01_fork"):
        assert am.AMEND1_D_ALPHAS[d_id] == pytest.approx(0.05)


# --- §4: persistence contract ---------------------------------------------------------

def test_persistence_tail_allocation():
    a, a_zero, a_ratio = am.persistence_tail_allocation("ordinary")
    assert a == pytest.approx(0.05 / 3)
    assert a_zero == a_ratio == pytest.approx(0.05 / 6)
    a, a_zero, a_ratio = am.persistence_tail_allocation("fork")
    assert a == pytest.approx(0.05 / 2)          # still two looks
    assert a_zero == a_ratio == pytest.approx(0.05 / 4)
    assert am.PERSISTENCE_BOUNDARY_R == 0.10
    assert am.PERSISTENCE_BRANCHES == ("zero", "positive")
    assert am.BISECTION_ITERATIONS == 80
    assert "p_hat_num" in am.PERSISTENCE_LOOK_FIELDS
    assert "branch" in am.PERSISTENCE_LOOK_FIELDS


# --- §9.2: run-root claims --------------------------------------------------------------

def test_claim_run_root_atomic_and_refusing(tmp_path, monkeypatch):
    root = tmp_path / "amend1-root"
    claimed = am.claim_run_root(root)
    assert claimed.is_dir()
    # ANY pre-existing path refuses — including the empty dir just made
    with pytest.raises(InfrastructureError, match="already exists"):
        am.claim_run_root(root)
    # an empty pre-existing directory refuses too
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(InfrastructureError, match="already exists"):
        am.claim_run_root(empty)


def test_frozen_root_literals():
    assert am.AMEND1_VALIDATION_RUN_ROOT == "runs/stage1-validation-amend1"
    assert am.AMEND1_REPLAY_RUN_ROOT == "runs/stage1-replay-amend1"
    assert am.ATTEMPT_ID == "stage1-pre-ce1-amend1-attempt-1"


# --- §9.1: execution bundle ---------------------------------------------------------------

def _bundle_fields():
    return {
        "amendment_prereg_sha256": "a" * 64,
        "lock_record_sha256": "b" * 64,
        "git_commit": "c" * 40,
        "source_digest": "d" * 64,
        "environment_manifest_sha256": "e" * 64,
        "v1_evidence_manifest_sha256": "f" * 64,
        "seed_registry_sha256": "1" * 64,
        "scenario_grid_sha256": "2" * 64,
        "b_support_sha256": "3" * 64,
        "prompt_sha256s": [stage1.PROMPT_FEWSHOT_SHA256,
                           stage1.PROMPT_SCHEMA_ONLY_SHA256],
        "artifact_tags": [am.AMEND1_VALIDATION_TAG,
                          am.AMEND1_REPLAY_TAG,
                          am.AMEND1_ARTIFACT_TAG],
        "run_roots": [am.AMEND1_VALIDATION_RUN_ROOT,
                      am.AMEND1_REPLAY_RUN_ROOT],
        "attempt_id": am.ATTEMPT_ID,
    }


def test_execution_bundle_roundtrip():
    bundle = am.build_execution_bundle(_bundle_fields())
    identity = am.validate_execution_bundle(bundle)
    assert identity == bundle["execution_bundle_sha256"]
    assert am.validate_execution_bundle(
        json.loads(json.dumps(bundle))) == identity


def test_execution_bundle_fail_closed():
    fields = _bundle_fields()
    missing = dict(fields)
    del missing["seed_registry_sha256"]
    with pytest.raises(InfrastructureError, match="missing"):
        am.build_execution_bundle(missing)
    wrong_attempt = dict(fields, attempt_id="attempt-2")
    with pytest.raises(InfrastructureError, match="attempt id"):
        am.build_execution_bundle(wrong_attempt)
    wrong_tags = dict(fields, artifact_tags=["v1"])
    with pytest.raises(InfrastructureError, match="tags"):
        am.build_execution_bundle(wrong_tags)
    bundle = am.build_execution_bundle(fields)
    tampered = dict(bundle, git_commit="x" * 40)
    with pytest.raises(InfrastructureError, match="hash mismatch"):
        am.validate_execution_bundle(tampered)


# --- §9: old-artifact refusal ----------------------------------------------------------------

def test_amend1_tag_refuses_v1_artifacts_and_vice_versa():
    row = {"pass_count": 5, "fail_count": 0, "unresolved_count": 9_995,
           "trials": 10_000}
    keys = frozenset({"k"})
    v1 = st.finalize_artifact("A", EXEC_SHA, {"k": row})
    amend1 = st.finalize_artifact("A", EXEC_SHA, {"k": row},
                                  tag=am.AMEND1_ARTIFACT_TAG)
    # each loads under its own tag
    st.load_artifact(v1, "A", keys, EXEC_SHA)
    st.load_artifact(amend1, "A", keys, EXEC_SHA,
                     tag=am.AMEND1_ARTIFACT_TAG)
    # and refuses under the other
    with pytest.raises(st.TrancheError, match="tag"):
        st.load_artifact(v1, "A", keys, EXEC_SHA,
                         tag=am.AMEND1_ARTIFACT_TAG)
    with pytest.raises(st.TrancheError, match="tag"):
        st.load_artifact(amend1, "A", keys, EXEC_SHA)


# --- fork-cap formula ripples (§5.1) -----------------------------------------------------------

def test_fork_cap_amended_everywhere():
    from tasks.conductor.program import NAMESPACE_CONFIG, namespace_cap
    assert stage1.FORK_LOOK_SCHEDULE == (100, 500)
    assert namespace_cap("qualification", "fork_join") == 500
    assert tuple(NAMESPACE_CONFIG["qualification"]["fork_join"]
                 ["look_schedule"]) == (100, 500)
    # two looks still: fork tail alpha unchanged
    assert sv.PERSISTENCE_LOOKS["fork"]["tail_alpha"] == \
        pytest.approx(0.05 / 2)
    assert sv.POSITION_SCENARIOS["fork_div3"]["schedule"] == (100, 500)
    # aggregate-router support unchanged: first 100 per cell
    assert stage1.AGGREGATE_ROUTER_SUPPORT_CLUSTERS == range(0, 100)
