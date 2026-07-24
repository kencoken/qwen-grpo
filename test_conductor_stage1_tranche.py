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
from tasks.conductor import stage1_replay as sr
from tasks.conductor import stage1_tranche as st
from tasks.conductor.grpo_smoke import STAGE0C_LAUNCH_PROFILE
from tasks.conductor.types import InfrastructureError

EXEC_SHA = "e" * 64
FEW = sr.REPLAY_CONTRACT["prompt_fewshot_sha256"]
SO = sr.REPLAY_CONTRACT["prompt_schema_only_sha256"]


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


def test_d_registry_frozen_shape():
    ids = [s["id"] for s in st.D_SCENARIOS]
    assert len(ids) == 8 <= sv.COVERAGE_SCENARIO_CAP
    assert ids == sorted(ids)
    for s in st.D_SCENARIOS:
        assert s["error_decision"] in ("pass", "undercover")
        assert 0 < s["allocated_alpha"] < 0.20
        assert callable(s["dgp"])
    assert any("seq_null_ordinary" in i for i in ids)
    assert any("seq_null_fork" in i for i in ids)
    assert any("equiv_boundary_plus" in i for i in ids)
    assert any("equiv_boundary_minus" in i for i in ids)
    assert any("pilot" in i for i in ids)
    assert sum("persist" in i for i in ids) == 3


def test_d_scenarios_execute_one_trial_each():
    for s in st.D_SCENARIOS:
        decision = s["dgp"](123456789)
        assert decision in ("pass", "fail", "unresolved", "not_pass",
                            "cover", "undercover")


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


# --- agreement gate (145_s finding 3) -------------------------------------------

def test_agreement_criterion_wilson_999_of_1000():
    # the frozen criterion: one-sided 95% Wilson LB >= 0.995 on exactly
    # 1,000 datasets — 999/1000 is the minimum pass; 995/1000 fails
    assert st.agreement_passes({"agree_count": 1_000,
                                "datasets": 1_000})
    assert st.agreement_passes({"agree_count": 999, "datasets": 1_000})
    assert not st.agreement_passes({"agree_count": 998,
                                    "datasets": 1_000})
    assert not st.agreement_passes({"agree_count": 995,
                                    "datasets": 1_000})


def test_agreement_rejects_wrong_sample_sizes():
    with pytest.raises(st.TrancheError, match="exactly"):
        st.agreement_passes({"agree_count": 1, "datasets": 1})  # 1/1
    with pytest.raises(st.TrancheError, match="exactly"):
        st.agreement_passes({"agree_count": 500, "datasets": 500})
    with pytest.raises(st.TrancheError, match="malformed"):
        st.agreement_passes({"agree_count": 1_001, "datasets": 1_000})
    with pytest.raises(st.TrancheError, match="malformed"):
        st.agreement_passes({"agree_count": 999.0, "datasets": 1_000})


def test_agreement_families_cover_reduced_replicate_scenarios():
    # the gate's datasets must represent D1-D5 (stake ordinary/fork,
    # equivalence, pilot-unequal), not only ordinary stakes
    assert set(st._AGREEMENT_FAMILIES) == {
        "stake_ordinary", "stake_fork", "equivalence", "pilot_unequal"}
    # each family's decision function runs (tiny replicates, throwaway)
    rng = np.random.default_rng(12)
    assert st._agreement_decision(
        "stake_ordinary", [st._tp_rows(rng, 0.3, 0.3, 500)], 50, 1) \
        in ("pass", "fail", "unresolved")
    assert st._agreement_decision(
        "equivalence", [st._tp_rows(rng, 0.0, 0.3, 500)], 50, 1) \
        in ("pass", "fail", "unresolved")
    assert st._agreement_decision(
        "pilot_unequal", [st._tp_rows(rng, 0.0, 0.4, n)
                          for n in (12, 12, 6)], 50, 1) \
        in ("pass", "not_pass")


def test_agreement_gate_blocks_bootstrap_scenarios():
    bad = {"agree_count": 900, "datasets": 1_000}
    with pytest.raises(st.TrancheError, match="agreement gate"):
        st.run_d_battery(bad)


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

def _pair_table():
    return {
        "code_atomic:worker_dev:00000:aaaaaaaa:resource_first:private":
            {"cell_id": "code_atomic", "assignment_w2": [2],
             "assignment_w3": [3], "distinct_payoff": 1, "direction": 3},
        "fork_join:worker_dev:00000:bbbbbbbb:goal_first:private":
            {"cell_id": "fork_join", "assignment_w2": [0, 2, 1],
             "assignment_w3": [0, 3, 1], "distinct_payoff": 1,
             "direction": 2},
        "math_code:worker_dev:00000:cccccccc:bound_var:private":
            {"cell_id": "math_code", "assignment_w2": [1, 2],
             "assignment_w3": [1, 3], "distinct_payoff": 0,
             "direction": 0},
    }


def _obs_meta(table):
    meta = {}
    for obs in table:
        cell, _, _, _, renderer, _ = obs.split(":")
        meta[obs] = {"cell_id": cell,
                     "latent": ":".join(obs.split(":")[:4]),
                     "renderer": renderer}
    return meta


def _b_artifact(k2=30, k3=30, exec_sha=EXEC_SHA):
    table = _pair_table()
    counts = {f"{o}|{p}": {"k2": k2, "k3": k3,
                           "n": sr.REPLAY_COMPLETIONS}
              for o in table for p in (FEW, SO)}
    return st.finalize_artifact(
        "B", exec_sha, counts,
        extra={"pair_table": table, "obs_meta": _obs_meta(table),
               "replay_manifest_sha256": "d" * 64})


def _full_artifacts(c_power_pass=True, b_k=30):
    reg = st.expected_result_keys()
    a_res = {k: {"pass_count": 9_500, "fail_count": 0,
                 "unresolved_count": 500, "trials": 10_000}
             for k in reg["A_position"] | reg["A_router"]}
    c_res = {}
    for key in reg["C"]:
        theta = float(key.split("|")[4])
        n = sv.PERSISTENCE_TRIALS
        k = n if theta == 0.0 else (9_000 if c_power_pass else 1_440)
        c_res[key] = {"pass_count": k, "unresolved_count": 0,
                      "trials": n}
    d_res = {s["id"]: {"error_count": 0,
                       "trials": sv.COVERAGE_OUTER_TRIALS}
             for s in st.D_SCENARIOS}
    a = st.finalize_artifact("A", EXEC_SHA, a_res)
    c = st.finalize_artifact("C", EXEC_SHA, c_res)
    d = st.finalize_artifact(
        "D", EXEC_SHA, d_res,
        extra={"agreement": {"agree_count": 999, "datasets": 1_000}})
    return a, c, d, _b_artifact(k2=b_k, k3=b_k)


def test_aggregate_verdict_confirm_path():
    a, c, d, b = _full_artifacts()
    v = st.aggregate_verdict(a, c, d, b)
    assert v["confirm_possible"] is True
    assert v["D_failing"] == []
    assert v["B_directions_blocking"] == []


def test_aggregate_verdict_c_failure_predicted_path():
    a, c, d, b = _full_artifacts(c_power_pass=False)
    v = st.aggregate_verdict(a, c, d, b)
    assert v["confirm_possible"] is False
    assert len(v["C_power_failing"]) == 2


def test_aggregate_verdict_empty_b_refuses():
    # 145_s probe: even an empty directions mapping must refuse
    a, c, d, _ = _full_artifacts()
    with pytest.raises((st.TrancheError, InfrastructureError)):
        st.aggregate_verdict(a, c, d, {})
    empty_table = st.finalize_artifact(
        "B", EXEC_SHA, {},
        extra={"pair_table": {}, "obs_meta": {},
               "replay_manifest_sha256": "d" * 64})
    with pytest.raises(InfrastructureError, match="empty pair table"):
        st.aggregate_verdict(a, c, d, empty_table)


def test_aggregate_verdict_mixed_executions_refuse():
    a, c, d, _ = _full_artifacts()
    foreign_b = _b_artifact(exec_sha="f" * 64)
    with pytest.raises(st.TrancheError, match="foreign execution"):
        st.aggregate_verdict(a, c, d, foreign_b)


def test_aggregate_verdict_b_not_demonstrated_blocks():
    # at 256 the branch is REACHABLE: zero counts with O=4 comparisons
    # give U_CP(0;256) ~ 0.02 -> g ~ 0.02 < 0.10
    a, c, d, _ = _full_artifacts()
    b = _b_artifact(k2=0, k3=0)
    v = st.aggregate_verdict(a, c, d, b)
    assert v["B_directions_blocking"] == ["2", "3"]
    assert v["confirm_possible"] is False


def test_aggregate_verdict_d_agreement_failure():
    a, c, d, b = _full_artifacts()
    d_bad = st.finalize_artifact(
        "D", EXEC_SHA, {k: dict(v) for k, v in d["results"].items()},
        extra={"agreement": {"agree_count": 995, "datasets": 1_000}})
    v = st.aggregate_verdict(a, c, d_bad, b)
    assert "agreement" in v["D_failing"]
    assert v["confirm_possible"] is False


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
    table = _pair_table()
    meta = _obs_meta(table)
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
    table = _pair_table()
    table["fork_join:worker_dev:00000:bbbbbbbb:bound_var:private"] = \
        dict(table["fork_join:worker_dev:00000:bbbbbbbb:"
                   "goal_first:private"])
    meta = _obs_meta(table)
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


def test_load_b_artifact_fail_closed():
    b = _b_artifact()
    loaded = sr.load_b_artifact(json.loads(json.dumps(b)), EXEC_SHA)
    assert loaded["results"]
    with pytest.raises(st.TrancheError, match="foreign execution"):
        sr.load_b_artifact(b, "f" * 64)
    stripped = {k: v for k, v in b.items() if k != "obs_meta"}
    with pytest.raises(InfrastructureError, match="obs_meta"):
        sr.load_b_artifact(stripped, EXEC_SHA)
    tampered = dict(b)
    key = next(iter(b["results"]))
    tampered["results"] = {**b["results"],
                           key: {"k2": 1, "k3": 1,
                                 "n": sr.REPLAY_COMPLETIONS}}
    with pytest.raises(st.TrancheError, match="hash mismatch"):
        sr.load_b_artifact(tampered, EXEC_SHA)


def test_replay_manifest_and_meta():
    table = _pair_table()
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
