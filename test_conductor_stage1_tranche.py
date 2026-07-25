"""Unit-3 tests for the tranche runner, D registry, artifacts, verdict,
and the executable B replay contract (142_s findings 1-4; revised per
145_s: 256 completions, not_ruled_out naming, strict schemas, execution
binding, corrected agreement criterion, cluster-level DGP variance).

Includes the 145_s-requested refusal probes: empty B, mixed manifests,
1/1 agreement, impossible counts, and incomplete replay outputs. No
frozen grid, coverage scenario, or GPU replay executes here.
"""

import json

import numpy as np
import pytest

from tasks.conductor import stage1, stage1_validation as sv
from tasks.conductor import stage1_amend1 as am_mod
from tasks.conductor import stage1_replay as sr
from tasks.conductor import stage1_tranche as st
from tasks.conductor.grpo_smoke import STAGE0C_LAUNCH_PROFILE
from tasks.conductor.types import InfrastructureError

FEW = sr.REPLAY_CONTRACT["prompt_fewshot_sha256"]
SO = sr.REPLAY_CONTRACT["prompt_schema_only_sha256"]

def _env_manifest(git_commit="t" * 40):
    import hashlib
    from tasks.conductor.profiles import canonical_json
    from tasks.conductor.stage1_manifest import (stage1_source_digest,
                                                 stage1_source_files)
    body = {"manifest": "stage1-environment-v2",
            "git_commit": git_commit,
            "git_dirty": 0, "uv_lock_sha256": "u" * 64,
            "stage1_source_sha256": stage1_source_digest(),
            "stage1_source_files": list(stage1_source_files()),
            "gpu": "test-gpu", "torch": "test",
            "numpy": "test", "scipy": "test"}
    sha = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    return {**body, "execution_manifest_sha256": sha}


ENV = _env_manifest()
EXEC_SHA = ENV["execution_manifest_sha256"]
_REGISTRY_A = am_mod.finalize_seed_registry(
    tuple(f"o{i:02d}" for i in range(18)))


def _support_rows():
    """18 synthetic support observations: 3 pair-bearing cells x 1 obs
    + 15 code-free fillers, positional order == sorted nodes."""
    rows = {}
    pair_cells = [("code_atomic", ["n1"]),
                  ("math_code", ["n1", "n2"]),
                  ("fork_join", ["n1", "n2", "n3"])]
    for idx, (cell, positions) in enumerate(pair_cells):
        oid = (f"{cell}:worker_dev:{idx:05d}:aaaaaaa{idx}:"
               "resource_first:private")
        rows[oid] = {"cell_id": cell, "num_steps": len(positions),
                     "positions": positions}
    for i in range(15):
        oid = (f"lookup_atomic:worker_dev:{i + 10:05d}:bbbbbb{i:02x}:"
               "goal_first:private")
        rows[oid] = {"cell_id": "lookup_atomic", "num_steps": 1,
                     "positions": ["n1"]}
    return rows


def _surface(rows):
    surface = {}
    payoffs = {"code_atomic": (0.5, 1.0),      # w3 direction
               "math_code": (1.0, 1.0),        # tie
               "fork_join": (1.0, 0.5)}        # w2 direction
    for oid, meta in rows.items():
        pair = sr.family_correct_variants(meta["cell_id"])
        if pair is None:
            continue
        w2, w3 = pair
        p2, p3 = payoffs[meta["cell_id"]]
        surface[(oid, tuple(w2))] = p2
        surface[(oid, tuple(w3))] = p3
    return surface


def _fill_raw_counts(rows, table, raw, counts, k2=30, k3=30):
    """Populate raw completions/counts that genuinely reparse: k2 w2
    assignments, k3 w3 assignments, the rest malformed (in the
    denominator). Shared by the evidence fixture and the amended
    replay driver probe."""
    for oid, m in sorted(rows.items()):
        pair = table.get(oid)
        for p in (FEW, SO):
            for i in range(sr.REPLAY_COMPLETIONS):
                if pair is not None and i < k2:
                    action = pair["assignment_w2"]
                elif pair is not None and i < k2 + k3:
                    action = pair["assignment_w3"]
                else:
                    raw[f"{oid}|{p}|{i:03d}"] = "malformed"
                    continue
                raw[f"{oid}|{p}|{i:03d}"] = json.dumps(
                    {"worker_ids": list(action)})
            if pair is not None:
                counts[f"{oid}|{p}"] = {"k2": k2, "k3": k3,
                                        "n": sr.REPLAY_COMPLETIONS}


def _b_evidence(k2=30, k3=30, exec_sha=None, tag=None):
    """A complete, self-consistent B evidence bundle whose raw
    completions genuinely reparse to the counts. `tag` defaults to the
    v1 artifact tag; amended-boundary fixtures pass the amend1 replay
    tag (169_s finding 1)."""
    import hashlib
    exec_sha = exec_sha or EXEC_SHA
    rows = _support_rows()
    surface = _surface(rows)
    cell_of = {o: m["cell_id"] for o, m in rows.items()}
    table = sr.pair_table_from_surface(surface, cell_of)
    meta = sr.observation_meta(rows)
    raw, counts = {}, {}
    _fill_raw_counts(rows, table, raw, counts, k2=k2, k3=k3)
    raw_text = json.dumps(dict(sorted(raw.items())), ensure_ascii=False)
    raw_sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    rr = {f"{o}|{p}": "a" * 64 for o in sorted(rows)
          for p in (FEW, SO)}
    manifest = sr.build_replay_manifest(exec_sha, rows, rr, table)
    artifact = st.finalize_artifact(
        "B", exec_sha, counts,
        extra={"pair_table": manifest["eligible_pairs"],
               "obs_meta": meta,
               "replay_manifest_sha256":
                   manifest["replay_manifest_sha256"],
               "raw_completions_sha256": raw_sha},
        **({"tag": tag} if tag is not None else {}))
    def loader():
        return surface, rows, rr
    return {"artifact": artifact, "replay_manifest": manifest,
            "raw_completions_text": raw_text, "loader": loader,
            "surface": surface, "support_rows": rows}



# --- exact grid registries ------------------------------------------------------

def test_registry_cardinalities():
    reg = st.expected_result_keys()
    assert len(st.a_position_cells()) == 48
    assert len(st.a_router_cells()) == 24
    assert len(st.c_cells()) == 120
    assert len(reg["A_position"]) == 48
    assert len(reg["A_router"]) == 24
    assert len(reg["C"]) == 120
    assert len(reg["D"]) == 8
    assert not (reg["A_position"] & reg["A_router"])


def test_d_registry_amended_shape():
    from tasks.conductor import stage1_amend1 as am
    ids = tuple(sc["id"] for sc in st.D_SCENARIOS)
    assert ids == am.AMEND1_D_IDS
    for sc in st.D_SCENARIOS:
        assert sc["kind"] in ("decision", "persistence")
        assert sc["allocated_alpha"] == pytest.approx(
            am.AMEND1_D_ALPHAS[sc["id"]])
        assert callable(sc["dgp"])
    # D2 uses the AMENDED fork schedule (158_s §5.1)
    assert st.stage1_fork_schedule() == (100, 500)
    # D8 carries the both-branches support requirement (158_s §6)
    d8 = next(sc for sc in st.D_SCENARIOS
              if sc["id"] == "D8_persist_hybrid_theta01_fork")
    assert d8["requires_both_branches_each_look"] is True
    assert d8["theta"] == pytest.approx(0.01)


def test_d_scenarios_execute_one_trial_each():
    for sc in st.D_SCENARIOS:
        out = sc["dgp"](123456789)
        if sc["kind"] == "decision":
            assert out in ("pass", "fail", "unresolved", "not_pass")
        else:
            undercover, branches = out
            assert isinstance(undercover, bool)
            assert branches and all(
                tag in ("zero", "positive", "denominator_unresolved")
                for tag in branches.values())


def test_no_agreement_machinery_remains():
    # 158_s §6: no reduced-replicate implementation remains
    for name in ("run_agreement_gate", "agreement_passes",
                 "_AGREEMENT_FAMILIES", "_BOOTSTRAP_SCENARIOS"):
        assert not hasattr(st, name)
    assert not hasattr(sv, "COVERAGE_INNER_REPLICATES")


def test_d8_branch_support_rule():
    good = {f"D8_persist_hybrid_theta01_fork|look{n}":
            {"zero_branch": 5, "positive_branch": 4_995,
             "denominator_unresolved": 0, "trials": 5_000}
            for n in (100, 500)}
    assert st.d8_branch_support_ok(good)
    bad = dict(good)
    bad["D8_persist_hybrid_theta01_fork|look500"] = {
        "zero_branch": 0, "positive_branch": 5_000,
        "denominator_unresolved": 0, "trials": 5_000}
    assert not st.d8_branch_support_ok(bad)
    assert not st.d8_branch_support_ok({})


def test_dgp_rows_have_cluster_level_variance():
    # 145_s finding 4: one cluster-level draw carried through all
    # renderer rows — perfect renderer correlation, cluster-mean SD =
    # sigma exactly (not sigma/sqrt(3))
    rng = np.random.default_rng(11)
    rows = st._tp_rows(rng, 0.15, 0.75, 4_000)
    assert np.array_equal(rows[:, 0], rows[:, 1])
    assert np.array_equal(rows[:, 0], rows[:, 2])
    assert rows.mean(axis=1).std(ddof=1) == pytest.approx(0.75,
                                                          abs=0.03)


def test_deterministic_equivalence_set_passes_production_inference():
    # the required deterministic 10,000-replicate equivalence check
    # (145_s finding 3): constant data, analytically known decisions,
    # exact match required — raises on any mismatch
    results = st.run_deterministic_equivalence_set()
    assert results == {
        "inside_zero": "pass", "boundary_plus": "fail",
        "boundary_minus": "fail", "outside_plus": "fail",
        "outside_minus": "fail", "inside_edge": "pass"}


# --- artifacts (145_s finding 2) --------------------------------------------------

def test_artifact_requires_valid_exec_identity_and_schema():
    with pytest.raises(st.TrancheError, match="64 lowercase hex"):
        st.finalize_artifact("A", "short", {})
    with pytest.raises(st.TrancheError, match="unknown artifact"):
        st.finalize_artifact("X", EXEC_SHA, {})
    # wrong field set for the artifact kind refuses at finalize
    with pytest.raises(st.TrancheError, match="fields"):
        st.finalize_artifact("A", EXEC_SHA,
                             {"k": {"pass_count": 1, "trials": 10}})
    # reserved-field shadowing refuses
    ok_row = {"pass_count": 1, "fail_count": 1, "unresolved_count": 8,
              "trials": 10}
    with pytest.raises(st.TrancheError, match="reserved"):
        st.finalize_artifact("A", EXEC_SHA, {"k": ok_row},
                             extra={"results": {}})


def _a_artifact(exec_sha=EXEC_SHA, tamper_key=None):
    reg = st.expected_result_keys()
    res = {}
    for key in reg["A_position"] | reg["A_router"]:
        res[key] = {"pass_count": 9_500, "fail_count": 0,
                    "unresolved_count": 500, "trials": 10_000}
    if tamper_key:
        res[tamper_key] = {"pass_count": 9_500, "fail_count": 100,
                           "unresolved_count": 500, "trials": 10_000}
    return st.finalize_artifact("A", exec_sha, res)


def test_load_rejects_impossible_counts_and_wrong_trials():
    key = next(iter(st.expected_result_keys()["A_position"]))
    bad = _a_artifact(tamper_key=key)  # counts sum to 10,100
    with pytest.raises(st.TrancheError, match="impossible counts"):
        st.load_artifact(bad, "A",
                         st.expected_result_keys()["A_position"]
                         | st.expected_result_keys()["A_router"],
                         EXEC_SHA)
    reg = st.expected_result_keys()
    res = {k: {"pass_count": 90, "fail_count": 0,
               "unresolved_count": 10, "trials": 100}  # wrong trials
           for k in reg["D"]}
    with pytest.raises(st.TrancheError):
        st.finalize_artifact("D", EXEC_SHA, res)  # wrong fields for D
    d_res = {k: {"error_count": 0, "trials": 100} for k in reg["D"]}
    art = st.finalize_artifact("D", EXEC_SHA, d_res)
    with pytest.raises(st.TrancheError, match="frozen"):
        st.load_artifact(art, "D", reg["D"], EXEC_SHA)


def test_load_rejects_mixed_executions():
    # 145_s probe: artifacts from different executions may not combine
    art = _a_artifact(exec_sha="f" * 64)
    reg = st.expected_result_keys()
    with pytest.raises(st.TrancheError, match="foreign execution"):
        st.load_artifact(art, "A",
                         reg["A_position"] | reg["A_router"], EXEC_SHA)


# --- fail-closed aggregate verdict -------------------------------------------------

def _amend1_bundle(registry=None):
    # 171_s finding 1: the aggregate binds B evidence to the support
    # implied by the registry's B keys, so the canonical fixture
    # registry is the one over the ACTUAL support ids (_REGISTRY_S)
    return am_mod.build_execution_bundle(
        _bundle_fields_amend1(),
        seed_registry=registry if registry is not None
        else _REGISTRY_S)


def _bundle_fields_amend1():
    from tasks.conductor.stage1_manifest import stage1_source_digest
    # git/source provenance must agree with the ENV fixture — the
    # 175_s cross-check refuses mismatches at every consumer
    return {
        "amendment_prereg_sha256": "a" * 64,
        "lock_record_sha256": "b" * 64,
        "git_commit": "t" * 40,
        "source_digest": stage1_source_digest(),
        "environment_manifest_sha256": ENV["execution_manifest_sha256"],
        "v1_evidence_manifest_sha256":
            am_mod.V1_EVIDENCE_MANIFEST_SHA256,
        "scenario_grid_sha256": am_mod.scenario_grid_digest(),
        "request_contract_sha256": am_mod.request_contract_digest(),
        "artifact_schema_sha256": am_mod.artifact_schema_digest(),
        "expected_file_set_sha256": am_mod.expected_file_set_digest(),
        "prompt_sha256s": [stage1.PROMPT_FEWSHOT_SHA256,
                           stage1.PROMPT_SCHEMA_ONLY_SHA256],
        "artifact_tags": [am_mod.AMEND1_VALIDATION_TAG,
                          am_mod.AMEND1_REPLAY_TAG,
                          am_mod.AMEND1_ARTIFACT_TAG],
        "run_roots": [am_mod.AMEND1_VALIDATION_RUN_ROOT,
                      am_mod.AMEND1_REPLAY_RUN_ROOT],
        "attempt_id": am_mod.ATTEMPT_ID,
    }


def _amend1_artifacts(c_pass=True, d_pass=True, b_k=30, registry=None):
    from tasks.conductor import stage1_persistence as sp_mod
    bundle = _amend1_bundle(registry)
    exec_sha = bundle["execution_bundle_sha256"]
    reg = st.expected_result_keys()
    a_res = {k: {"pass_count": 9_500, "fail_count": 0,
                 "unresolved_count": 500, "trials": 10_000}
             for k in reg["A_position"] | reg["A_router"]}
    a = st.finalize_artifact("A", exec_sha, a_res,
                             tag=am_mod.AMEND1_ARTIFACT_TAG)
    fp = 10_000 if c_pass else 1_421
    path_rows = {am_mod.c_path_key(*cell): {
        "first_pass": fp, "first_fail": 0,
        "cap_unresolved": 10_000 - fp, "trials": 10_000}
        for cell in am_mod.c_path_cells()}
    marginal_rows = {key: {"pass_count": fp, "fail_count": 0,
                           "unresolved_count": 10_000 - fp,
                           "zero_branch": 100,
                           "positive_branch": 9_900,
                           "denominator_unresolved": 0,
                           "trials": 10_000}
                     for key in am_mod.c_marginal_keys()}
    c = sp_mod.build_c_artifact(exec_sha, path_rows, marginal_rows)
    err = 0 if d_pass else 5_000
    d_res = {sc["id"]: {"error_count": err, "trials": 5_000}
             for sc in st.D_SCENARIOS}
    branch = {f"{sid}|look{n}": {"zero_branch": 100,
                                 "positive_branch": 4_900,
                                 "denominator_unresolved": 0,
                                 "trials": 5_000}
              for sid in ("D6_persist_const_theta10",
                          "D7_persist_rowdispersed_theta10",
                          "D8_persist_hybrid_theta01_fork")
              for n in ((100, 300, 500) if "fork" not in sid
                        else (100, 500))}
    d = st.finalize_artifact("D", exec_sha, d_res,
                             extra={"branch_counts": branch},
                             tag=am_mod.AMEND1_ARTIFACT_TAG)
    b = _b_evidence(k2=b_k, k3=b_k, exec_sha=exec_sha,
                    tag=am_mod.AMEND1_REPLAY_TAG)
    return bundle, a, c, d, b


def test_amend1_verdict_confirm_c2_provisional():
    bundle, a, c, d, b = _amend1_artifacts()
    v = st.aggregate_amend1_verdict(
        a, c, d, b, env_manifest=ENV, bundle=bundle,
        seed_registry=_REGISTRY_S, b_pinned_loader=b["loader"])
    assert v["decision"] == "confirm_c2_provisional"
    assert v["C2_preCE1_available"] is True
    assert v["B_supports_C2"] is True
    assert v["D_failing"] == []


def test_amend1_verdict_c1_only_on_not_demonstrated():
    # 158_s §7: B not_demonstrated does NOT block confirmation — it
    # freezes C2 unavailable and the C1-only branch continues
    bundle, a, c, d, _ = _amend1_artifacts()
    b = _b_evidence(k2=0, k3=0,
                    exec_sha=bundle["execution_bundle_sha256"],
                    tag=am_mod.AMEND1_REPLAY_TAG)
    v = st.aggregate_amend1_verdict(
        a, c, d, b, env_manifest=ENV, bundle=bundle,
        seed_registry=_REGISTRY_S, b_pinned_loader=b["loader"])
    assert v["decision"] == "confirm_c1_only"
    assert v["C2_preCE1_available"] is False
    assert v["B_supports_C2"] is False
    assert set(v["B_direction_statuses"].values()) == \
        {"not_demonstrated"}


def test_amend1_verdict_scientific_stop():
    bundle, a, c, d, b = _amend1_artifacts(c_pass=False)
    v = st.aggregate_amend1_verdict(
        a, c, d, b, env_manifest=ENV, bundle=bundle,
        seed_registry=_REGISTRY_S, b_pinned_loader=b["loader"])
    assert v["decision"] == "scientific_stop"
    assert v["C_hard_path_failures"]
    # 169_s finding 6: B support alone can never make C2 available on
    # a scientific stop — the diagnostic and the claim flag separate
    assert v["B_supports_C2"] is True
    assert v["C2_preCE1_available"] is False
    # D failures also stop scientifically
    bundle2, a2, c2, d2, b2 = _amend1_artifacts(d_pass=False)
    v2 = st.aggregate_amend1_verdict(
        a2, c2, d2, b2, env_manifest=ENV, bundle=bundle2,
        seed_registry=_REGISTRY_S, b_pinned_loader=b2["loader"])
    assert v2["decision"] == "scientific_stop"
    assert len(v2["D_failing"]) == 8


def test_amend1_verdict_infrastructure_abort():
    # malformed/unreproducible B evidence RAISES (infrastructure
    # abort), never a scientific decision
    bundle, a, c, d, b = _amend1_artifacts()
    raw = json.loads(b["raw_completions_text"])
    raw.pop(next(iter(raw)))
    tampered = dict(b, raw_completions_text=json.dumps(
        dict(sorted(raw.items())), ensure_ascii=False))
    with pytest.raises(InfrastructureError):
        st.aggregate_amend1_verdict(
            a, c, d, tampered, env_manifest=ENV, bundle=bundle,
            seed_registry=_REGISTRY_S, b_pinned_loader=b["loader"])
    # a bundle validated against the wrong registry refuses
    other = am_mod.finalize_seed_registry(
        [f"z{i:02d}" for i in range(18)])
    with pytest.raises(InfrastructureError):
        st.aggregate_amend1_verdict(
            a, c, d, b, env_manifest=ENV, bundle=bundle,
            seed_registry=other, b_pinned_loader=b["loader"])
    # D8 branch-support failure is a D (scientific) failure
    bundle3, a3, c3, d3raw, b3 = _amend1_artifacts()
    exec_sha = bundle3["execution_bundle_sha256"]
    d_res = {k: dict(v) for k, v in d3raw["results"].items()}
    branch = {k: dict(v) for k, v in d3raw["branch_counts"].items()}
    branch["D8_persist_hybrid_theta01_fork|look500"] = {
        "zero_branch": 0, "positive_branch": 5_000,
        "denominator_unresolved": 0, "trials": 5_000}
    d3 = st.finalize_artifact("D", exec_sha, d_res,
                              extra={"branch_counts": branch},
                              tag=am_mod.AMEND1_ARTIFACT_TAG)
    v3 = st.aggregate_amend1_verdict(
        a3, c3, d3, b3, env_manifest=ENV, bundle=bundle3,
        seed_registry=_REGISTRY_S, b_pinned_loader=b3["loader"])
    assert "D8_branch_support" in v3["D_failing"]
    assert v3["decision"] == "scientific_stop"


# --- B replay contract --------------------------------------------------------------

def test_replay_contract_256_and_launch_profile():
    model = STAGE0C_LAUNCH_PROFILE["conductor_model"]
    assert sr.REPLAY_CONTRACT["model_id"] == model["model_id"]
    assert sr.REPLAY_CONTRACT["revision"] == model["revision"]
    assert sr.REPLAY_CONTRACT["quantization"] == \
        STAGE0C_LAUNCH_PROFILE["quantization"]
    assert sr.REPLAY_COMPLETIONS == 256          # 145_s amendment
    assert sr.REPLAY_CONTRACT[
        "completions_per_observation_per_prompt"] == 256
    assert sr.REPLAY_CONTRACT["total_completions"] == 9_216
    assert sr.REPLAY_CONTRACT["generation_batch"] == 1


def test_completion_seed_range():
    assert sr.completion_seed("o", "p" * 64, 255) != \
        sr.completion_seed("o", "p" * 64, 254)
    with pytest.raises(ValueError):
        sr.completion_seed("o", "p" * 64, 256)


def test_family_correct_variants_per_cell():
    assert sr.family_correct_variants("lookup_atomic") is None
    assert sr.family_correct_variants("code_atomic") == ([2], [3])
    assert sr.family_correct_variants("math_code") == ([1, 2], [1, 3])
    assert sr.family_correct_variants("fork_join") == \
        ([0, 2, 1], [0, 3, 1])


def test_pair_table_from_surface_mapping():
    surface = {("o1", (2,)): 0.5, ("o1", (3,)): 1.0}
    table = sr.pair_table_from_surface(surface, {"o1": "code_atomic"})
    assert table["o1"]["direction"] == 3
    with pytest.raises(InfrastructureError, match="missing"):
        sr.pair_table_from_surface({("o1", (2,)): 0.5},
                                   {"o1": "code_atomic"})


def test_expected_completion_keys_9216():
    obs = [f"o{i:02d}" for i in range(18)]
    keys = sr.expected_completion_keys(obs)
    assert len(keys) == 9_216
    with pytest.raises(InfrastructureError, match="exactly 18"):
        sr.expected_completion_keys(obs[:17])


def test_summarize_replay_fail_closed_and_statuses():
    rows = _support_rows()
    surface = _surface(rows)
    table = sr.pair_table_from_surface(
        surface, {o: m["cell_id"] for o, m in rows.items()})
    meta = sr.observation_meta(rows)
    counts = {f"{o}|{p}": {"k2": 30, "k3": 28,
                           "n": sr.REPLAY_COMPLETIONS}
              for o in table for p in (FEW, SO)}
    out = sr.summarize_replay(counts, table, meta)
    assert out["comparisons"] == 4      # 2 distinct-payoff obs x 2
    assert out["directions"]["2"]["status"] == "not_ruled_out"
    assert out["directions"]["3"]["status"] == "not_ruled_out"
    # 145_s: not_ruled_out replaces "demonstrated" — an upper bound
    # above the floor does not demonstrate feasibility
    assert "demonstrated" not in {
        out["directions"]["2"]["status"],
        out["directions"]["3"]["status"]}
    # zero counts at 256: the branch is now reachable and BLOCKS
    low = {k: {"k2": 0, "k3": 0, "n": sr.REPLAY_COMPLETIONS}
           for k in counts}
    out_low = sr.summarize_replay(low, table, meta)
    assert out_low["directions"]["2"]["status"] == "not_demonstrated"
    assert out_low["directions"]["3"]["status"] == "not_demonstrated"
    # incomplete keys refuse (145_s probe)
    partial = dict(counts)
    partial.pop(next(iter(partial)))
    with pytest.raises(InfrastructureError, match="count keys"):
        sr.summarize_replay(partial, table, meta)
    # arbitrary n refuses
    bad_n = {k: {"k2": 0, "k3": 0, "n": 64} for k in counts}
    with pytest.raises(InfrastructureError, match="malformed"):
        sr.summarize_replay(bad_n, table, meta)
    # impossible counts refuse
    bad = dict(counts)
    bad[next(iter(bad))] = {"k2": 200, "k3": 100,
                            "n": sr.REPLAY_COMPLETIONS}
    with pytest.raises(InfrastructureError, match="malformed"):
        sr.summarize_replay(bad, table, meta)
    # missing meta refuses
    with pytest.raises(InfrastructureError, match="meta"):
        sr.summarize_replay(counts, table, {})


def test_summarize_uses_frozen_weighting_not_raw_average():
    # two same-direction observations in ONE cell must count as one
    # cell, not two raw observations: add a second fork renderer with
    # an extreme count and check the cell-equal aggregate differs from
    # the raw mean
    rows = _support_rows()
    surface = _surface(rows)
    table = sr.pair_table_from_surface(
        surface, {o: m["cell_id"] for o, m in rows.items()})
    fork_obs = next(o for o in table if o.startswith("fork_join"))
    second = fork_obs.replace("resource_first", "bound_var")
    table[second] = dict(table[fork_obs])
    meta = sr.observation_meta(list(table))
    counts = {}
    for o, row in table.items():
        for p in (FEW, SO):
            k = 60 if "bound_var" in o else 10
            counts[f"{o}|{p}"] = {"k2": k, "k3": k,
                                  "n": sr.REPLAY_COMPLETIONS}
    out = sr.summarize_replay(counts, table, meta)
    d2 = out["directions"]["2"]["per_prompt"][FEW]
    # renderer-mean within the single fork latent: g((10+60)/2/256-ish)
    # vs raw mean of two observations — the weighted value equals the
    # renderer-averaged value, strictly between the two obs values
    g_low = sr.g_direct_gradient(10 / 256, 10 / 256)
    g_high = sr.g_direct_gradient(60 / 256, 60 / 256)
    assert g_low < d2["g_point"] < g_high
    assert d2["g_point"] == pytest.approx((g_low + g_high) / 2,
                                          rel=1e-9)


def test_load_b_artifact_structural_fail_closed():
    b = _b_evidence()["artifact"]
    loaded = sr.load_b_artifact(json.loads(json.dumps(b)), EXEC_SHA)
    assert loaded["results"]
    with pytest.raises(st.TrancheError, match="foreign execution"):
        sr.load_b_artifact(b, "f" * 64)
    stripped = {k: v for k, v in b.items() if k != "obs_meta"}
    with pytest.raises(InfrastructureError, match="obs_meta"):
        sr.load_b_artifact(stripped, EXEC_SHA)
    stripped2 = {k: v for k, v in b.items()
                 if k != "raw_completions_sha256"}
    with pytest.raises(InfrastructureError, match="raw_completions"):
        sr.load_b_artifact(stripped2, EXEC_SHA)
    tampered = dict(b)
    key = next(iter(b["results"]))
    tampered["results"] = {**b["results"],
                           key: {"k2": 1, "k3": 1,
                                 "n": sr.REPLAY_COMPLETIONS}}
    with pytest.raises(st.TrancheError, match="hash mismatch"):
        sr.load_b_artifact(tampered, EXEC_SHA)


def test_replay_manifest_and_meta():
    rows = _support_rows()
    surface = _surface(rows)
    table = sr.pair_table_from_surface(
        surface, {o: m["cell_id"] for o, m in rows.items()})
    obs = sorted(table)
    rr = {f"{o}|{p}": "a" * 64 for o in obs for p in (FEW, SO)}
    m = sr.build_replay_manifest(EXEC_SHA, obs, rr, table)
    assert m["manifest"] == "stage1-replay-manifest-v2"
    assert m["contract"]["total_completions"] == 9_216
    with pytest.raises(InfrastructureError, match="rendered-request"):
        sr.build_replay_manifest(EXEC_SHA, obs,
                                 dict(list(rr.items())[:-1]), table)
    meta = sr.observation_meta(obs)
    assert meta[obs[0]]["cell_id"] == "code_atomic"
    assert meta[obs[0]]["renderer"] == "resource_first"


# --- 154_s: the abort boundary covers the ENTIRE post-`running` sequence ---

def _replay_probe_setup(tmp_path, monkeypatch):
    import tasks.conductor.stage1_manifest as sm
    monkeypatch.setattr(sr, "REPLAY_RUN_DIR",
                        str(tmp_path / "stage1-replay"))
    monkeypatch.setattr(sm, "build_stage1_env_manifest",
                        lambda allow_dirty=False: dict(ENV))
    b = _b_evidence()
    surface, rows, rr = b["loader"]()
    return {"surface": surface, "rows": rows, "messages": {},
            "rr_hashes": rr, "tokenizer": None}


def _read_record(tmp_path):
    return json.loads(
        (tmp_path / "stage1-replay" / "run_record.json").read_text(
            encoding="utf-8"))


def test_run_replay_model_load_failure_writes_aborted(tmp_path,
                                                      monkeypatch):
    inputs = _replay_probe_setup(tmp_path, monkeypatch)

    def boom():
        raise RuntimeError("CUDA out of memory (probe)")
    monkeypatch.setattr(sr, "_build_replay_model", boom)
    with pytest.raises(RuntimeError, match="probe"):
        sr.run_replay(_inputs=inputs)
    record = _read_record(tmp_path)
    assert record["status"] == "aborted"
    assert "RuntimeError" in record["error"]
    assert "wall_seconds" in record
    # the pre-model persistence survived the abort
    run_dir = tmp_path / "stage1-replay"
    assert (run_dir / "env_manifest.json").exists()
    assert (run_dir / "replay_manifest.json").exists()


# --- 169_s findings 1-6: amended execution-integrity probes ------------------------

_REGISTRY_S = am_mod.finalize_seed_registry(sorted(_support_rows()))


def test_amend1_verdict_refuses_foreign_support_registry():
    # 171_s finding 1: 170_f's aggregate fixtures demonstrated the
    # bypass — a bundle/registry over o00..o17 while B is scored over
    # different render-instance ids, and confirmation succeeded. The
    # same inputs must now refuse at CONSUMPTION.
    bundle, a, c, d, b = _amend1_artifacts(registry=_REGISTRY_A)
    with pytest.raises(InfrastructureError, match="support"):
        st.aggregate_amend1_verdict(
            a, c, d, b, env_manifest=ENV, bundle=bundle,
            seed_registry=_REGISTRY_A, b_pinned_loader=b["loader"])


def test_amend1_verdict_refuses_legacy_tagged_b():
    # 169_s finding 1: a legacy-tagged B artifact refuses at the
    # amended boundary even when it carries the bundle identity
    bundle, a, c, d, _ = _amend1_artifacts()
    legacy = _b_evidence(exec_sha=bundle["execution_bundle_sha256"])
    with pytest.raises(st.TrancheError, match="tag"):
        st.aggregate_amend1_verdict(
            a, c, d, legacy, env_manifest=ENV, bundle=bundle,
            seed_registry=_REGISTRY_S, b_pinned_loader=legacy["loader"])


def test_amend1_branch_telemetry_exact_set():
    # 169_s finding 3: exactly eight branch rows — D6/D7 at the
    # ordinary looks, D8 at the amended fork looks
    assert st.expected_branch_keys() == frozenset(
        [f"D6_persist_const_theta10|look{n}" for n in (100, 300, 500)]
        + [f"D7_persist_rowdispersed_theta10|look{n}"
           for n in (100, 300, 500)]
        + ["D8_persist_hybrid_theta01_fork|look100",
           "D8_persist_hybrid_theta01_fork|look500"])
    bundle, a, c, d0, b = _amend1_artifacts()
    exec_sha = bundle["execution_bundle_sha256"]
    d_res = {k: dict(v) for k, v in d0["results"].items()}
    branch = {k: dict(v) for k, v in d0["branch_counts"].items()}
    missing = dict(branch)
    missing.pop("D6_persist_const_theta10|look300")
    d_missing = st.finalize_artifact(
        "D", exec_sha, d_res, extra={"branch_counts": missing},
        tag=am_mod.AMEND1_ARTIFACT_TAG)
    with pytest.raises(st.TrancheError, match="exact per-look"):
        st.aggregate_amend1_verdict(
            a, c, d_missing, b, env_manifest=ENV, bundle=bundle,
            seed_registry=_REGISTRY_S, b_pinned_loader=b["loader"])
    extra = dict(branch)
    extra["D1_seq_null_ordinary_div3|look100"] = {
        "zero_branch": 0, "positive_branch": 5_000,
        "denominator_unresolved": 0, "trials": 5_000}
    d_extra = st.finalize_artifact(
        "D", exec_sha, d_res, extra={"branch_counts": extra},
        tag=am_mod.AMEND1_ARTIFACT_TAG)
    with pytest.raises(st.TrancheError, match="exact per-look"):
        st.aggregate_amend1_verdict(
            a, c, d_extra, b, env_manifest=ENV, bundle=bundle,
            seed_registry=_REGISTRY_S, b_pinned_loader=b["loader"])


def test_registered_seed_consumption():
    # 169_s finding 2: the formal D runner consumes the supplied
    # registry values directly; a missing key refuses, never derives
    seen = []
    scen = {"id": "Dx_probe", "kind": "decision",
            "dgp": lambda s: seen.append(s) or "fail",
            "error_decision": "pass", "allocated_alpha": 0.05}
    registry = {f"Dx_probe|{t}": t * 7 + 1
                for t in range(sv.COVERAGE_OUTER_TRIALS)}
    row, branches = st.run_d_battery_scenario(scen,
                                              seed_registry=registry)
    assert row == {"error_count": 0,
                   "trials": sv.COVERAGE_OUTER_TRIALS}
    assert branches == {}
    assert seen == [t * 7 + 1 for t in range(sv.COVERAGE_OUTER_TRIALS)]
    with pytest.raises(st.TrancheError, match="registered seed"):
        st.run_d_battery_scenario(scen, seed_registry={})
    with pytest.raises(st.TrancheError, match="registered seed"):
        st.run_deterministic_equivalence_set({})
    # the registered D/B-domain values ARE the v1 derivation (§9.3),
    # so direct consumption changes no frozen seed
    for key in am_mod.DETSET_KEYS:
        assert _REGISTRY_A[key] == sv.scenario_seed(key)


def test_d_scenario_deadline_minimum():
    # 169_s finding 5: the in-loop deadline is the MINIMUM remaining
    # per-scenario / D6-D8 / total budget
    assert st._d_scenario_deadline(100.0, 0.0, None) == 100.0
    assert st._d_scenario_deadline(
        1e9, st.TOTAL_BUDGET_SECONDS - 5.0, None) == pytest.approx(5.0)
    assert st._d_scenario_deadline(
        1e9, 0.0, st.D68_BUDGET_SECONDS - 3.0) == pytest.approx(3.0)
    with pytest.raises(st.TrancheError, match="remaining budget"):
        st._d_scenario_deadline(100.0, st.TOTAL_BUDGET_SECONDS + 1.0,
                                None)
    with pytest.raises(st.TrancheError, match="remaining budget"):
        st._d_scenario_deadline(100.0, 0.0,
                                float(st.D68_BUDGET_SECONDS))


def _write_amend1_run_dirs(tmp_path, bundle, a, c, d, b):
    """Materialize both run roots exactly as the amended runners leave
    them (pre-aggregate)."""
    val = tmp_path / "stage1-validation-amend1"
    rep = tmp_path / "stage1-replay-amend1"
    val.mkdir()
    rep.mkdir()

    def _w(dir_, name, obj):
        (dir_ / name).write_text(json.dumps(obj, indent=1),
                                 encoding="utf-8")
    _w(val, "execution_bundle_manifest.json", dict(bundle))
    _w(val, "env_manifest.json", ENV)
    _w(val, "deterministic_equivalence.json", {})
    _w(val, "benchmark.json", {})
    _w(val, "artifact_A.json", a)
    _w(val, "artifact_C.json", c)
    _w(val, "artifact_D.json", d)
    for scen in st.D_SCENARIOS:
        sid = scen["id"]
        partial = {"scenario": sid,
                   "execution_bundle_sha256":
                       bundle["execution_bundle_sha256"],
                   **d["results"][sid]}
        if scen["kind"] == "persistence":
            partial["branch_counts"] = {
                k: v for k, v in d["branch_counts"].items()
                if k.startswith(f"{sid}|")}
        _w(val, f"partial_D_{sid}.json", partial)
    _w(val, "run_record.json", {"status": "complete", "stages": []})
    _w(rep, "execution_bundle_manifest.json", dict(bundle))
    _w(rep, "env_manifest.json", ENV)
    _w(rep, "replay_manifest.json", b["replay_manifest"])
    (rep / "raw_completions.json").write_text(
        b["raw_completions_text"], encoding="utf-8")
    _w(rep, "artifact_B.json", b["artifact"])
    _w(rep, "run_record.json", {"status": "complete"})
    return val, rep


def test_finalize_amend1_run(tmp_path):
    # 169_s finding 4: the post-B finalizer computes/persists the
    # aggregate, updates run_record.json, and checks both exact sets
    bundle, a, c, d, b = _amend1_artifacts()
    val, rep = _write_amend1_run_dirs(tmp_path, bundle, a, c, d, b)
    v = st.finalize_amend1_run(bundle, _REGISTRY_S,
                               b_pinned_loader=b["loader"],
                               validation_dir=val, replay_dir=rep)
    assert v["decision"] == "confirm_c2_provisional"
    persisted = json.loads((val / "aggregate.json").read_text(
        encoding="utf-8"))
    assert persisted["decision"] == "confirm_c2_provisional"
    record = json.loads((val / "run_record.json").read_text(
        encoding="utf-8"))
    assert record["stages"] == ["aggregate"]
    assert record["aggregate_decision"] == "confirm_c2_provisional"
    # the completed lifecycle satisfies the frozen contract exactly
    am_mod.verify_run_file_set(val, am_mod.AMEND1_VALIDATION_RUN_ROOT)
    am_mod.verify_run_file_set(rep, am_mod.AMEND1_REPLAY_RUN_ROOT)
    # 171_s finding 2: a run finalizes ONCE — the second call refuses
    # at preflight rather than overwriting the aggregate
    with pytest.raises(st.TrancheError, match="already holds"):
        st.finalize_amend1_run(bundle, _REGISTRY_S,
                               b_pinned_loader=b["loader"],
                               validation_dir=val, replay_dir=rep)


def test_finalize_amend1_run_fail_closed(tmp_path):
    bundle, a, c, d, b = _amend1_artifacts()
    val, rep = _write_amend1_run_dirs(tmp_path, bundle, a, c, d, b)
    # an incomplete (aborted/running) run refuses to aggregate
    (rep / "run_record.json").write_text(
        json.dumps({"status": "aborted"}), encoding="utf-8")
    with pytest.raises(st.TrancheError, match="complete"):
        st.finalize_amend1_run(bundle, _REGISTRY_S,
                               b_pinned_loader=b["loader"],
                               validation_dir=val, replay_dir=rep)
    (rep / "run_record.json").write_text(
        json.dumps({"status": "complete"}), encoding="utf-8")
    # a foreign bundle manifest on disk refuses
    other_fields = dict(_bundle_fields_amend1(),
                        lock_record_sha256="e" * 64)
    other = am_mod.build_execution_bundle(other_fields,
                                          seed_registry=_REGISTRY_S)
    (val / "execution_bundle_manifest.json").write_text(
        json.dumps(dict(other), indent=1), encoding="utf-8")
    with pytest.raises(st.TrancheError, match="bundle"):
        st.finalize_amend1_run(bundle, _REGISTRY_S,
                               b_pinned_loader=b["loader"],
                               validation_dir=val, replay_dir=rep)
    (val / "execution_bundle_manifest.json").write_text(
        json.dumps(dict(bundle), indent=1), encoding="utf-8")
    # 171_s finding 2: a stray file refuses at PREFLIGHT — before any
    # mutation, so no apparently-successful aggregate is left behind
    (val / "stray.json").write_text("{}", encoding="utf-8")
    with pytest.raises(st.TrancheError, match="extra"):
        st.finalize_amend1_run(bundle, _REGISTRY_S,
                               b_pinned_loader=b["loader"],
                               validation_dir=val, replay_dir=rep)
    assert not (val / "aggregate.json").exists()
    (val / "stray.json").unlink()
    # a partial-D record that does not reconcile with artifact_D
    # refuses (tampered error count), still pre-mutation
    sid = "D1_seq_null_ordinary_div3"
    partial = json.loads((val / f"partial_D_{sid}.json").read_text(
        encoding="utf-8"))
    partial["error_count"] += 1
    (val / f"partial_D_{sid}.json").write_text(
        json.dumps(partial, indent=1), encoding="utf-8")
    with pytest.raises(st.TrancheError, match="reconcile"):
        st.finalize_amend1_run(bundle, _REGISTRY_S,
                               b_pinned_loader=b["loader"],
                               validation_dir=val, replay_dir=rep)
    assert not (val / "aggregate.json").exists()
    partial["error_count"] -= 1
    (val / f"partial_D_{sid}.json").write_text(
        json.dumps(partial, indent=1), encoding="utf-8")
    # a missing artifact refuses at preflight too
    (val / "artifact_D.json").unlink()
    with pytest.raises(st.TrancheError, match="missing"):
        st.finalize_amend1_run(bundle, _REGISTRY_S,
                               b_pinned_loader=b["loader"],
                               validation_dir=val, replay_dir=rep)


def _amend1_replay_setup(tmp_path, monkeypatch):
    import tasks.conductor.stage1_manifest as sm
    # bundle fields derive the live source digest (git) — build them
    # BEFORE leaving the repository working directory
    fields = _bundle_fields_amend1()
    bundle = am_mod.build_execution_bundle(fields,
                                           seed_registry=_REGISTRY_S)
    b = _b_evidence()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sm, "build_stage1_env_manifest",
                        lambda allow_dirty=False: dict(ENV))
    surface, rows, rr = b["loader"]()
    inputs = {"surface": surface, "rows": rows, "messages": {},
              "rr_hashes": rr, "tokenizer": None}
    return bundle, inputs, b, fields


def test_run_amend1_replay_success(tmp_path, monkeypatch):
    # 169_s finding 1: the amended B entry point — bundle identity,
    # amended root/tag, registered-seed consumption end-to-end
    from pathlib import Path
    repo_root = Path.cwd()
    bundle, inputs, b, _ = _amend1_replay_setup(tmp_path, monkeypatch)
    exec_sha = bundle["execution_bundle_sha256"]
    monkeypatch.setattr(sr, "_build_replay_model", lambda: None)
    seen = []

    def fake_generate(model, tok, rows, msgs, table, raw, counts, *,
                      seed_of):
        seen.append(seed_of(min(rows), FEW, 0))
        _fill_raw_counts(rows, table, raw, counts)
    monkeypatch.setattr(sr, "_generate", fake_generate)
    out = sr.run_amend1_replay(bundle, _REGISTRY_S, _inputs=inputs)
    assert out["execution_bundle_sha256"] == exec_sha
    # the seed consumed IS the registered value
    key = f"B|{min(inputs['rows'])}|{FEW}|0"
    assert seen == [_REGISTRY_S[key]]
    run_dir = tmp_path / "runs" / "stage1-replay-amend1"
    art = json.loads((run_dir / "artifact_B.json").read_text(
        encoding="utf-8"))
    assert art["tag"] == am_mod.AMEND1_REPLAY_TAG
    assert art["execution_manifest_sha256"] == exec_sha
    record = json.loads((run_dir / "run_record.json").read_text(
        encoding="utf-8"))
    assert record["status"] == "complete"
    assert record["execution_bundle_sha256"] == exec_sha
    am_mod.verify_run_file_set(run_dir, am_mod.AMEND1_REPLAY_RUN_ROOT)
    # a second invocation cannot reuse the claimed root
    with pytest.raises(InfrastructureError, match="already exists"):
        sr.run_amend1_replay(bundle, _REGISTRY_S, _inputs=inputs)
    # the produced evidence verifies at the amended boundary (back in
    # the repo root: env-manifest validation recomputes the source
    # digest via git)...
    monkeypatch.chdir(repo_root)
    manifest = json.loads((run_dir / "replay_manifest.json").read_text(
        encoding="utf-8"))
    raw_text = (run_dir / "raw_completions.json").read_text(
        encoding="utf-8")
    summary = sr.verify_replay_evidence(
        art, env_manifest=ENV, replay_manifest=manifest,
        raw_completions_text=raw_text, pinned_loader=b["loader"],
        execution_identity=exec_sha, seed_registry=_REGISTRY_S)
    assert set(summary["directions"]) == {"2", "3"}
    # ...refuses at the LEGACY boundary (tag/identity mismatch)...
    with pytest.raises(st.TrancheError, match="tag"):
        sr.verify_replay_evidence(
            art, env_manifest=ENV, replay_manifest=manifest,
            raw_completions_text=raw_text, pinned_loader=b["loader"])
    # ...refuses amended consumption WITHOUT the registry (171_s)...
    with pytest.raises(InfrastructureError, match="registry"):
        sr.verify_replay_evidence(
            art, env_manifest=ENV, replay_manifest=manifest,
            raw_completions_text=raw_text, pinned_loader=b["loader"],
            execution_identity=exec_sha)
    # ...and refuses a registry implying a DIFFERENT support (171_s
    # finding 1: the generation-time check repeats at consumption)
    with pytest.raises(InfrastructureError, match="support"):
        sr.verify_replay_evidence(
            art, env_manifest=ENV, replay_manifest=manifest,
            raw_completions_text=raw_text, pinned_loader=b["loader"],
            execution_identity=exec_sha, seed_registry=_REGISTRY_A)


def test_run_amend1_replay_aborts_and_refusals(tmp_path, monkeypatch):
    bundle, inputs, _, fields = _amend1_replay_setup(tmp_path,
                                                     monkeypatch)

    # registry/support mismatch refuses BEFORE claiming the root
    rows2 = dict(inputs["rows"])
    victim = min(rows2)
    rows2["zzz:worker_dev:99999:ffffffff:goal_first:private"] = \
        rows2.pop(victim)
    with pytest.raises(InfrastructureError, match="support ids"):
        sr.run_amend1_replay(bundle, _REGISTRY_S,
                             _inputs=dict(inputs, rows=rows2))
    assert not (tmp_path / "runs" / "stage1-replay-amend1").exists()

    # a model-construction failure aborts WITH the §9.4 pre-model
    # files and an aborted record in place
    def boom():
        raise RuntimeError("CUDA out of memory (probe)")
    monkeypatch.setattr(sr, "_build_replay_model", boom)
    with pytest.raises(RuntimeError, match="probe"):
        sr.run_amend1_replay(bundle, _REGISTRY_S, _inputs=inputs)
    run_dir = tmp_path / "runs" / "stage1-replay-amend1"
    record = json.loads((run_dir / "run_record.json").read_text(
        encoding="utf-8"))
    assert record["status"] == "aborted"
    assert "RuntimeError" in record["error"]
    for name in ("execution_bundle_manifest.json", "env_manifest.json",
                 "replay_manifest.json"):
        assert (run_dir / name).exists()

    # a NON-CANONICAL registry refuses even when the bundle was built
    # from it — the digest proves lock-equality, verify_registry_
    # canonical proves the values are the frozen derivation (169_s
    # finding 2)
    tampered = dict(_REGISTRY_S)
    tampered[next(iter(am_mod.DETSET_KEYS))] ^= 1
    evil_bundle = am_mod.build_execution_bundle(
        dict(fields), seed_registry=tampered)
    with pytest.raises(InfrastructureError, match="canonical"):
        sr.run_amend1_replay(evil_bundle, tampered, _inputs=inputs)


# --- 175_s findings 1-3: lock-readiness probes -------------------------------------

def test_frozen_deadline_literal_controls_and_sanity_band():
    # 175_s finding 1: the FROZEN literal is source, the deadline
    # derives from it, and the live-benchmark band is INCLUSIVE
    assert st.MEASURED_SECONDS_PER_OUTER_X1E6 == 951_551
    assert st.D_SCENARIO_DEADLINE_SECONDS == 19_031
    frozen = st.MEASURED_SECONDS_PER_OUTER_X1E6 / 1e6
    st.benchmark_sanity_check(frozen)
    st.benchmark_sanity_check(frozen / st.BENCHMARK_SANITY_FACTOR)
    st.benchmark_sanity_check(frozen * st.BENCHMARK_SANITY_FACTOR)
    with pytest.raises(st.TrancheError, match="sanity band"):
        st.benchmark_sanity_check(
            frozen / st.BENCHMARK_SANITY_FACTOR - 1e-9)
    with pytest.raises(st.TrancheError, match="sanity band"):
        st.benchmark_sanity_check(
            frozen * st.BENCHMARK_SANITY_FACTOR + 1e-6)


def test_bundle_env_provenance_cross_check():
    # 175_s finding 2: consumers refuse a bundle whose git/source
    # provenance disagrees with the VALIDATED environment manifest,
    # even though the bundle itself is format-valid and self-hashed
    fields = dict(_bundle_fields_amend1(), git_commit="u" * 40)
    bundle = am_mod.build_execution_bundle(fields,
                                           seed_registry=_REGISTRY_S)
    _, a, c, d, b = _amend1_artifacts()
    exec_sha = bundle["execution_bundle_sha256"]
    a2 = st.finalize_artifact("A", exec_sha,
                              {k: dict(v) for k, v
                               in a["results"].items()},
                              tag=am_mod.AMEND1_ARTIFACT_TAG)
    with pytest.raises(InfrastructureError, match="git_commit"):
        st.aggregate_amend1_verdict(
            a2, c, d, b, env_manifest=ENV, bundle=bundle,
            seed_registry=_REGISTRY_S, b_pinned_loader=b["loader"])
    with pytest.raises(InfrastructureError, match="source_digest"):
        am_mod.check_bundle_env_provenance(
            dict(_bundle_fields_amend1(), source_digest="d" * 64), ENV)


def test_build_lock_bundle_derives_everything(tmp_path, monkeypatch):
    # 175_s finding 2: the formal lock-time constructor derives every
    # provenance field from bytes/repository state — no caller-typed
    # hashes exist in its signature
    import hashlib
    import inspect
    import tasks.conductor.stage1_manifest as sm
    head = am_mod.current_git_commit()
    env = _env_manifest(git_commit=head)
    monkeypatch.setattr(sm, "build_stage1_env_manifest",
                        lambda allow_dirty=False: dict(env))
    prereg = tmp_path / "prereg.md"
    prereg.write_bytes(b"PREREG BYTES")
    lock = tmp_path / "lock.md"
    lock.write_bytes(b"LOCK BYTES")
    bundle, registry, env_out = am_mod.build_lock_bundle(
        prereg_path=prereg, lock_record_path=lock,
        _support_ids=sorted(_support_rows()))
    assert bundle["amendment_prereg_sha256"] == \
        hashlib.sha256(b"PREREG BYTES").hexdigest()
    assert bundle["lock_record_sha256"] == \
        hashlib.sha256(b"LOCK BYTES").hexdigest()
    assert bundle["git_commit"] == head
    assert bundle["source_digest"] == sm.stage1_source_digest()
    assert bundle["environment_manifest_sha256"] == \
        env["execution_manifest_sha256"]
    assert bundle["seed_registry_entries"] == 49_342
    am_mod.validate_execution_bundle(bundle, seed_registry=registry)
    params = inspect.signature(am_mod.build_lock_bundle).parameters
    assert "fields" not in params    # nothing caller-typed


def _production_context(tmp_path, monkeypatch):
    """A REAL derive-everything context: production support ids
    (178_s finding 1 — no injection), tmp reviewed documents, and an
    env manifest pinned to the actual HEAD."""
    import tasks.conductor.stage1_manifest as sm
    head = am_mod.current_git_commit()
    env = _env_manifest(git_commit=head)
    monkeypatch.setattr(sm, "build_stage1_env_manifest",
                        lambda allow_dirty=False: dict(env))
    prereg = tmp_path / "prereg.md"
    prereg.write_bytes(b"PREREG BYTES")
    lock = tmp_path / "lock.md"
    lock.write_bytes(b"LOCK BYTES")
    bundle, registry, _ = am_mod.build_lock_bundle(
        prereg_path=prereg, lock_record_path=lock)
    return bundle, registry, prereg, lock


def test_build_lock_bundle_production_default(tmp_path, monkeypatch):
    # 178_s finding 1: the PRODUCTION default derives the support
    # from payoff_support.support_observations — 18 unique ids (the
    # smoke-schedule rows would duplicate them and refuse)
    bundle, registry, _, _ = _production_context(tmp_path, monkeypatch)
    from tasks.conductor.payoff_support import support_observations
    ids = sorted(o["observation_id"] for o in support_observations())
    assert len(ids) == len(set(ids)) == 18
    assert am_mod._registry_support_ids(registry) == ids
    assert bundle["seed_registry_entries"] == 49_342
    am_mod.validate_execution_bundle(bundle, seed_registry=registry)


def test_persisted_context_and_cpu_first_order(tmp_path, monkeypatch):
    # 178_s finding 2: replay/finalize consume the CPU run's
    # PERSISTED bundle and refuse before a complete CPU root exists
    from tasks.conductor import stage1_amend1_run as sar
    bundle, registry, prereg, lock = _production_context(tmp_path,
                                                         monkeypatch)
    val = tmp_path / "val"
    # no CPU root at all -> CPU-first refusal
    val.mkdir()
    with pytest.raises(InfrastructureError, match="tranche first"):
        sar.persisted_context(validation_dir=val, prereg_path=prereg,
                              lock_record_path=lock)
    for name in am_mod.EXPECTED_RUN_FILES[
            am_mod.AMEND1_VALIDATION_RUN_ROOT]:
        if name != "aggregate.json":
            (val / name).write_text("{}", encoding="utf-8")
    (val / "execution_bundle_manifest.json").write_text(
        json.dumps(bundle), encoding="utf-8")
    # incomplete CPU record -> refusal BEFORE anything else runs
    (val / "run_record.json").write_text(
        json.dumps({"status": "running"}), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="complete"):
        sar.persisted_context(validation_dir=val, prereg_path=prereg,
                              lock_record_path=lock)
    (val / "run_record.json").write_text(
        json.dumps({"status": "complete"}), encoding="utf-8")
    context = sar.persisted_context(validation_dir=val,
                                    prereg_path=prereg,
                                    lock_record_path=lock)
    assert context["bundle"] == bundle
    assert am_mod.seed_registry_digest(context["seed_registry"]) == \
        bundle["seed_registry_sha256"]
    # authoritative provenance drift (lock record bytes changed after
    # the CPU run) refuses before the replay root would be claimed
    lock.write_bytes(b"LOCK BYTES CHANGED")
    with pytest.raises(InfrastructureError, match="authoritative"):
        sar.persisted_context(validation_dir=val, prereg_path=prereg,
                              lock_record_path=lock)


def test_archive_evidence_success_mode(tmp_path, monkeypatch):
    # 178_s finding 3: success mode validates provenance, both
    # completed roots, exact file sets and the finalized aggregate,
    # staging + atomic rename
    from pathlib import Path
    from tasks.conductor import stage1_amend1_run as sar
    bundle, registry, prereg, lock = _production_context(tmp_path,
                                                         monkeypatch)
    _, a, c, d, b = _amend1_artifacts()
    val, rep = _write_amend1_run_dirs(tmp_path, bundle, a, c, d, b)
    # missing aggregate -> success refuses on the exact file set
    with pytest.raises(InfrastructureError, match="missing"):
        sar.archive_evidence("success", validation_dir=val,
                             replay_dir=rep,
                             evidence_parent=tmp_path / "ev",
                             prereg_path=prereg,
                             lock_record_path=lock)
    (val / "aggregate.json").write_text("{}", encoding="utf-8")
    # an incomplete replay refuses
    (rep / "run_record.json").write_text(
        json.dumps({"status": "aborted"}), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="statuses"):
        sar.archive_evidence("success", validation_dir=val,
                             replay_dir=rep,
                             evidence_parent=tmp_path / "ev",
                             prereg_path=prereg,
                             lock_record_path=lock)
    (rep / "run_record.json").write_text(
        json.dumps({"status": "complete"}), encoding="utf-8")
    out = sar.archive_evidence("success", validation_dir=val,
                               replay_dir=rep,
                               evidence_parent=tmp_path / "ev",
                               prereg_path=prereg,
                               lock_record_path=lock)
    dest = Path(out["evidence_dir"])
    manifest = json.loads(
        (dest / "evidence_manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "success"
    assert manifest["validation_errors"] == []
    assert manifest["execution_bundle_sha256"] == \
        bundle["execution_bundle_sha256"]
    assert manifest["git_commit"] == bundle["git_commit"]
    # the frozen command list and the formal logs are recorded
    assert any("tranche" in cmd for cmd in manifest["commands"])
    assert "validation/run_record.json" in manifest["formal_logs"]
    assert out["files"] == len(list(val.iterdir())) + \
        len(list(rep.iterdir()))
    for rel, entry in manifest["files"].items():
        assert (dest / rel).stat().st_size == entry["bytes"]
    # no staging remnant; destination immutable
    assert not list((tmp_path / "ev").glob(".staging_*"))
    with pytest.raises(InfrastructureError, match="immutable"):
        sar.archive_evidence("success", validation_dir=val,
                             replay_dir=rep,
                             evidence_parent=tmp_path / "ev",
                             prereg_path=prereg,
                             lock_record_path=lock)


def test_archive_evidence_abort_mode(tmp_path):
    # 178_s finding 3: abort mode preserves partial bytes WITHOUT
    # trusting the bundle and records the validation errors
    from pathlib import Path
    from tasks.conductor import stage1_amend1_run as sar
    with pytest.raises(InfrastructureError, match="unknown archive"):
        sar.archive_evidence("partial", validation_dir=tmp_path)
    val = tmp_path / "val"
    val.mkdir()
    evil = {"manifest": "x", "execution_bundle_sha256": "f" * 64}
    (val / "execution_bundle_manifest.json").write_text(
        json.dumps(evil), encoding="utf-8")
    (val / "run_record.json").write_text(
        json.dumps({"status": "aborted", "error": "boom"}),
        encoding="utf-8")
    (val / "partial_D_D1_seq_null_ordinary_div3.json").write_text(
        "{}", encoding="utf-8")
    # success mode REFUSES this state...
    with pytest.raises(InfrastructureError, match="refused"):
        sar.archive_evidence("success", validation_dir=val,
                             replay_dir=tmp_path / "absent",
                             evidence_parent=tmp_path / "ev")
    # ...abort mode preserves it and records why it is not clean
    out = sar.archive_evidence("abort", validation_dir=val,
                               replay_dir=tmp_path / "absent",
                               evidence_parent=tmp_path / "ev")
    assert out["mode"] == "abort"
    assert any("self-hash" in e for e in out["validation_errors"])
    dest = Path(out["evidence_dir"])
    manifest = json.loads(
        (dest / "evidence_manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "abort"
    assert manifest["replay_status"] == "absent"
    assert manifest["validation_status"] == "aborted"
    assert manifest["validation_errors"]
    assert "validation/run_record.json" in manifest["formal_logs"]
    assert (dest / "validation" /
            "execution_bundle_manifest.json").exists()


def test_prelock_probe_recipe_and_lock_record_discovery(tmp_path,
                                                        monkeypatch):
    # 175_s finding 3: the committed §5.4 probe recipe is executable
    # (tiny parameters here; the formal record uses the defaults)
    from tasks.conductor import stage1_amend1_run as sar
    out = sar.run_prelock_probes(n_cases=12, trials_per_path=2,
                                 outer_trials=1)
    assert out["reference_agreement"]["cases_checked"] >= 1
    assert out["frozen_literal_x1e6"] == 951_551
    assert out["frozen_d_scenario_deadline_seconds"] == 19_031
    assert isinstance(out["measured_within_sanity_band"], bool)
    assert "cpu_tranche_worst_case_bound_hours" in out
    # the lock record is discovered from the repository and must be
    # unique
    monkeypatch.chdir(tmp_path)
    (tmp_path / "plans" / "conductor").mkdir(parents=True)
    with pytest.raises(InfrastructureError, match="exactly one"):
        sar.locate_lock_record()
    one = (tmp_path / "plans" / "conductor" /
           "199_f_stage_1_amend1_lock.md")
    one.write_text("lock", encoding="utf-8")
    assert sar.locate_lock_record() == one.relative_to(tmp_path)
    (tmp_path / "plans" / "conductor" /
     "200_f_stage_1_amend1_lock.md").write_text("x", encoding="utf-8")
    with pytest.raises(InfrastructureError, match="exactly one"):
        sar.locate_lock_record()


def test_run_replay_finalization_failure_writes_aborted(tmp_path,
                                                        monkeypatch):
    # post-generation failure: generation "succeeds" but produces
    # incomplete accounting — the finalization path must abort with a
    # record, not leave `running`
    inputs = _replay_probe_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(sr, "_build_replay_model", lambda: None)
    monkeypatch.setattr(
        sr, "_generate",
        lambda model, tok, rows, msgs, table, raw, counts: None)
    with pytest.raises(InfrastructureError, match="accounting"):
        sr.run_replay(_inputs=inputs)
    record = _read_record(tmp_path)
    assert record["status"] == "aborted"
    assert "accounting" in record["error"]
    assert "wall_seconds" in record
