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
    # any manifest edit now fails the PINNED manifest hash first
    with pytest.raises(InfrastructureError, match="pinned"):
        am.verify_v1_evidence_archive(tmp_path / "a3")
    # 161_s finding 2 reproductions: a modified lock_commit and a
    # modified diagnostic script must both refuse
    shutil.copytree(am.V1_EVIDENCE_DIR, tmp_path / "a4")
    mp4 = tmp_path / "a4" / "evidence_manifest.json"
    m4 = json.loads(mp4.read_text())
    m4["lock_commit"] = "f" * 40
    mp4.write_text(json.dumps(m4, sort_keys=True, indent=1))
    with pytest.raises(InfrastructureError, match="pinned"):
        am.verify_v1_evidence_archive(tmp_path / "a4")
    shutil.copytree(am.V1_EVIDENCE_DIR, tmp_path / "a5")
    sp = tmp_path / "a5" / "agreement_diagnostic_script.py"
    sp.write_text(sp.read_text() + "\n# tampered\n")
    with pytest.raises(InfrastructureError, match="sha256"):
        am.verify_v1_evidence_archive(tmp_path / "a5")


# --- §9.3: seed domains and registry ------------------------------------------------

def test_db_domain_reproduces_v1_scenario_seeds():
    # D and B seeds were never exposed; the retained domain must
    # reproduce the v1 derivation EXACTLY — using the REAL key
    # material: raw unpadded completion indices (161_s finding 3)
    from tasks.conductor import stage1_replay as sr
    for key in ("D1_seq_null_ordinary_div3|0",
                "D5_pilot_hetero_unequal|4999",
                "D-detset|boundary_plus",
                f"B|obs|{'p' * 64}|0",
                f"B|obs|{'p' * 64}|255"):
        assert am.seed(am.DB_SEED_DOMAIN, key) == sv.scenario_seed(key)
    # and equality with the actual replay derivation end-to-end
    assert am.seed(am.DB_SEED_DOMAIN, f"B|obs1|{'p' * 64}|7") == \
        sr.completion_seed("obs1", "p" * 64, 7)


def test_ac_domain_differs_from_v1():
    for key in ("A|ordinary_div1|0.15|0.5|10000",
                am.c_path_key("fork", 0.60, 0.05, "cluster_correlated")):
        assert am.seed(am.AC_SEED_DOMAIN, key) != sv.scenario_seed(key)


def test_seed_registry_properties():
    reg = am.build_seed_registry()
    # components: 48 A + 24 router + 48 C paths + 8x5000 D + 6 det-set
    assert len(reg) == 48 + 24 + 48 + 8 * 5_000 + 6
    assert "D-detset|inside_zero" in reg
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


def test_finalized_registry_is_the_only_bundle_input():
    from tasks.conductor import stage1_replay as sr
    obs = [f"o{i:02d}" for i in range(18)]
    full = am.finalize_seed_registry(obs)
    assert len(full) == am.FULL_SEED_REGISTRY_ENTRIES == 49_342
    # the B entries use EXACTLY completion_seed's material
    key = f"B|o03|{stage1.PROMPT_FEWSHOT_SHA256}|42"
    assert full[key] == sr.completion_seed(
        "o03", stage1.PROMPT_FEWSHOT_SHA256, 42)
    # wrong support size refuses
    with pytest.raises(InfrastructureError, match="18"):
        am.finalize_seed_registry(obs[:17])
    # a bundle refuses a partial registry count
    fields = _bundle_fields()
    fields["seed_registry_entries"] = len(am.build_seed_registry())
    with pytest.raises(InfrastructureError, match="FINALIZED"):
        am.build_execution_bundle(fields)


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
    # 161_s finding 4: branch bounds are explicit schema, not comments
    assert "zero_U" in am.PERSISTENCE_ZERO_BRANCH_FIELDS
    assert "zero_U_A" in am.PERSISTENCE_ZERO_BRANCH_FIELDS
    assert "zero_L_Q" in am.PERSISTENCE_ZERO_BRANCH_FIELDS
    for f in ("pos_G_L", "pos_G_U", "pos_L_p", "pos_U_p"):
        assert f in am.PERSISTENCE_POSITIVE_BRANCH_FIELDS
    assert am.FLOAT_DTYPE == "float64"
    assert am.TOLERANCE_FACTOR == 64
    assert am.STUDENT_T_IMPL == "scipy.stats.t.ppf"
    assert am.ENDPOINT_RTOL == 0.0


def test_amend1_row_schemas_fail_closed():
    ok_path = {"k": {"first_pass": 9_000, "first_fail": 500,
                     "cap_unresolved": 500, "trials": 10_000}}
    am.validate_amend1_rows("C_path", ok_path)
    bad_sum = {"k": {"first_pass": 9_000, "first_fail": 600,
                     "cap_unresolved": 500, "trials": 10_000}}
    with pytest.raises(InfrastructureError, match="impossible"):
        am.validate_amend1_rows("C_path", bad_sum)
    ok_marg = {"k": {"pass_count": 8_000, "fail_count": 1_000,
                     "unresolved_count": 1_000, "zero_branch": 100,
                     "positive_branch": 9_900,
                     "denominator_unresolved": 5, "trials": 10_000}}
    am.validate_amend1_rows("C_marginal", ok_marg)
    bad_branch = {"k": dict(ok_marg["k"], zero_branch=200)}
    with pytest.raises(InfrastructureError, match="impossible"):
        am.validate_amend1_rows("C_marginal", bad_branch)
    bad_denom = {"k": dict(ok_marg["k"], zero_branch=9_900,
                           positive_branch=100,
                           denominator_unresolved=500)}
    with pytest.raises(InfrastructureError, match="impossible"):
        am.validate_amend1_rows("C_marginal", bad_denom)
    ok_dbr = {"k": {"zero_branch": 2_736, "positive_branch": 2_264,
                    "denominator_unresolved": 3, "trials": 5_000}}
    am.validate_amend1_rows("D_branch", ok_dbr)
    with pytest.raises(InfrastructureError, match="fields"):
        am.validate_amend1_rows("C_path", ok_marg)
    with pytest.raises(InfrastructureError, match="unknown"):
        am.validate_amend1_rows("bogus", {})


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
        "seed_registry_entries": am.FULL_SEED_REGISTRY_ENTRIES,
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


def test_execution_bundle_self_rehash_attack_refuses():
    # 161_s finding 1 reproduction: change frozen literals, RECOMPUTE
    # the self-hash — validation must still refuse on semantics
    import hashlib as _h
    from tasks.conductor.profiles import canonical_json
    bundle = am.build_execution_bundle(_bundle_fields())

    def rehash(body):
        body = dict(body)
        body.pop("execution_bundle_sha256", None)
        body["execution_bundle_sha256"] = _h.sha256(
            canonical_json(body).encode("utf-8")).hexdigest()
        return body

    evil_tags = rehash(dict(bundle, artifact_tags=["v1-tag"]))
    with pytest.raises(InfrastructureError, match="tags"):
        am.validate_execution_bundle(evil_tags)
    evil_roots = rehash(dict(bundle, run_roots=["runs/other"]))
    with pytest.raises(InfrastructureError, match="roots"):
        am.validate_execution_bundle(evil_roots)
    evil_prompt = rehash(dict(bundle, prompt_sha256s=["a" * 64]))
    with pytest.raises(InfrastructureError, match="prompt"):
        am.validate_execution_bundle(evil_prompt)
    evil_extra = rehash(dict(bundle, smuggled="x"))
    with pytest.raises(InfrastructureError, match="field set"):
        am.validate_execution_bundle(evil_extra)
    evil_count = rehash(dict(bundle, seed_registry_entries=42))
    with pytest.raises(InfrastructureError, match="FINALIZED"):
        am.validate_execution_bundle(evil_count)


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
