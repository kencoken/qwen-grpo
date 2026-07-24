"""Unit-3 tests for the tranche runner, D registry, artifacts, verdict,
and the executable B replay contract (142_s findings 1-4).

No frozen grid, coverage scenario, or GPU replay executes here: these
tests exercise registries, fail-closed loading/aggregation, and the
pure (CPU) replay functions with synthetic inputs.
"""

import json

import pytest

from tasks.conductor import stage1, stage1_validation as sv
from tasks.conductor import stage1_replay as sr
from tasks.conductor import stage1_tranche as st
from tasks.conductor.grpo_smoke import STAGE0C_LAUNCH_PROFILE
from tasks.conductor.types import InfrastructureError

EXEC_SHA = "e" * 64


# --- exact grid registries ------------------------------------------------------

def test_registry_cardinalities_match_142s():
    reg = st.expected_result_keys()
    assert len(st.a_position_cells()) == 48
    assert len(st.a_router_cells()) == 24          # 142_s correction
    assert len(st.c_cells()) == 120                # 142_s correction
    assert len(reg["A_position"]) == 48
    assert len(reg["A_router"]) == 24
    assert len(reg["C"]) == 120
    assert len(reg["D"]) == 8
    # disjoint, deterministic order, unique
    assert not (reg["A_position"] & reg["A_router"])
    assert st.a_position_cells() == st.a_position_cells()


def test_d_registry_frozen_shape():
    ids = [s["id"] for s in st.D_SCENARIOS]
    assert len(ids) == 8 <= sv.COVERAGE_SCENARIO_CAP
    assert ids == sorted(ids)  # D1..D8 frozen order
    for s in st.D_SCENARIOS:
        assert s["error_decision"] in ("pass", "undercover")
        assert 0 < s["allocated_alpha"] < 0.20
        assert callable(s["dgp"])
    # the plan's four required families are all present
    assert any("seq_null_ordinary" in i for i in ids)
    assert any("seq_null_fork" in i for i in ids)
    assert any("equiv_boundary_plus" in i for i in ids)
    assert any("equiv_boundary_minus" in i for i in ids)
    assert any("pilot" in i for i in ids)
    assert sum("persist" in i for i in ids) == 3


def test_d_scenarios_execute_one_trial_each():
    # one synthetic trial per scenario: machinery only, throwaway seed,
    # never a frozen outer-trial seed (those are scenario_seed(id|t))
    for s in st.D_SCENARIOS:
        decision = s["dgp"](123456789)
        assert decision in ("pass", "fail", "unresolved", "not_pass",
                            "cover", "undercover")


def test_agreement_gate_blocks_bootstrap_scenarios():
    bad = {"agree_count": 900, "datasets": 1000}
    with pytest.raises(st.TrancheError, match="agreement gate"):
        st.run_d_battery(bad)


# --- artifacts -----------------------------------------------------------------

def _tiny_artifact():
    return st.finalize_artifact(
        "X", EXEC_SHA, {"k1": {"pass_count": 5, "trials": 10}})


def test_artifact_roundtrip_and_hash():
    art = _tiny_artifact()
    assert len(art["artifact_sha256"]) == 64
    loaded = st.load_artifact(art, "X", frozenset({"k1"}))
    assert loaded["results"]["k1"]["pass_count"] == 5
    # json round-trip preserves identity (persisted artifacts)
    assert st.load_artifact(json.loads(json.dumps(art)), "X",
                            frozenset({"k1"}))


def test_artifact_rejects_floats_and_unknown_fields():
    with pytest.raises(st.TrancheError, match="non-integer"):
        st.finalize_artifact("X", EXEC_SHA,
                             {"k": {"pass_count": 0.5, "trials": 10}})
    with pytest.raises(st.TrancheError, match="non-integer"):
        st.finalize_artifact("X", EXEC_SHA,
                             {"k": {"pass_rate": 1, "trials": 10}})
    with pytest.raises(st.TrancheError, match="non-integer"):
        st.finalize_artifact("X", EXEC_SHA,
                             {"k": {"pass_count": True, "trials": 10}})


def test_artifact_load_fails_closed():
    art = _tiny_artifact()
    tampered = dict(art)
    tampered["results"] = {"k1": {"pass_count": 6, "trials": 10}}
    with pytest.raises(st.TrancheError, match="hash mismatch"):
        st.load_artifact(tampered, "X", frozenset({"k1"}))
    with pytest.raises(st.TrancheError, match="wrong name"):
        st.load_artifact(art, "Y", frozenset({"k1"}))
    with pytest.raises(st.TrancheError, match="key set"):
        st.load_artifact(art, "X", frozenset({"k1", "k2"}))
    with pytest.raises(st.TrancheError, match="key set"):
        st.load_artifact(art, "X", frozenset())


# --- fail-closed aggregate verdict -----------------------------------------------

def _full_artifacts(c_power_pass=True):
    """Complete synthetic artifacts over the exact registries."""
    reg = st.expected_result_keys()
    a_res = {}
    for key in reg["A_position"] | reg["A_router"]:
        a_res[key] = {"pass_count": 9_500, "fail_count": 0,
                      "unresolved_count": 500, "trials": 10_000}
    c_res = {}
    for key in reg["C"]:
        n = sv.PERSISTENCE_TRIALS
        parts = key.split("|")
        theta = float(parts[4])
        if theta == 0.0:
            k = n
        elif c_power_pass:
            k = 9_000
        else:
            k = 1_440  # the predicted fork failure region
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
    b = {"artifact_sha256": "b" * 64,
         "directions": {"2": {"status": "demonstrated"},
                        "3": {"status": "demonstrated"}}}
    return a, c, d, b


def test_aggregate_verdict_confirm_path():
    a, c, d, b = _full_artifacts(c_power_pass=True)
    v = st.aggregate_verdict(a, c, d, b)
    assert v["confirm_possible"] is True
    assert v["D_failing"] == []


def test_aggregate_verdict_c_failure_predicted_path():
    a, c, d, b = _full_artifacts(c_power_pass=False)
    v = st.aggregate_verdict(a, c, d, b)
    assert v["confirm_possible"] is False
    assert len(v["C_power_failing"]) == 2  # both hard-criterion cells


def test_aggregate_verdict_refuses_partial_or_tampered():
    a, c, d, b = _full_artifacts()
    # missing keys refuse (empty inputs can never pass — 142_s)
    partial_a = st.finalize_artifact(
        "A", EXEC_SHA, {"k1": {"pass_count": 5, "trials": 10}})
    with pytest.raises(st.TrancheError, match="key set"):
        st.aggregate_verdict(partial_a, c, d, b)
    # tampered content refuses on hash
    bad_c = dict(c)
    key = next(iter(bad_c["results"]))
    bad_c["results"] = {**bad_c["results"],
                        key: {"pass_count": 1, "unresolved_count": 0,
                              "trials": sv.PERSISTENCE_TRIALS}}
    with pytest.raises(st.TrancheError, match="hash mismatch"):
        st.aggregate_verdict(a, bad_c, d, b)
    # malformed B refuses
    with pytest.raises(st.TrancheError, match="missing"):
        st.aggregate_verdict(a, c, d, {"directions": {}})
    with pytest.raises(st.TrancheError, match="bad status"):
        st.aggregate_verdict(a, c, d, {
            "artifact_sha256": "b" * 64,
            "directions": {"2": {"status": "maybe"},
                           "3": {"status": "demonstrated"}}})


def test_aggregate_verdict_b_blocks_confirmation():
    a, c, d, _ = _full_artifacts()
    b = {"artifact_sha256": "b" * 64,
         "directions": {"2": {"status": "not_demonstrated"},
                        "3": {"status": "demonstrated"}}}
    v = st.aggregate_verdict(a, c, d, b)
    assert v["B_directions_blocking"] == ["2"]
    assert v["confirm_possible"] is False
    b_unknown = {"artifact_sha256": "b" * 64,
                 "directions": {"2": {"status": "unknown"},
                                "3": {"status": "demonstrated"}}}
    v2 = st.aggregate_verdict(a, c, d, b_unknown)
    # unknown is surfaced for the reviewed decision, not auto-blocking
    assert v2["B_directions_unknown"] == ["2"]
    assert v2["confirm_possible"] is True


def test_aggregate_verdict_d_agreement_failure():
    a, c, d, b = _full_artifacts()
    d_bad_res = {k: dict(v) for k, v in d["results"].items()}
    d_bad = st.finalize_artifact(
        "D", EXEC_SHA, d_bad_res,
        extra={"agreement": {"agree_count": 990, "datasets": 1_000}})
    v = st.aggregate_verdict(a, c, d_bad, b)
    assert "agreement" in v["D_failing"]
    assert v["confirm_possible"] is False


# --- B replay contract (CPU-pure parts) ----------------------------------------------

def test_replay_contract_matches_launch_profile():
    model = STAGE0C_LAUNCH_PROFILE["conductor_model"]
    assert sr.REPLAY_CONTRACT["model_id"] == model["model_id"]
    assert sr.REPLAY_CONTRACT["revision"] == model["revision"]
    assert sr.REPLAY_CONTRACT["quantization"] == \
        STAGE0C_LAUNCH_PROFILE["quantization"]
    assert sr.REPLAY_CONTRACT["sampling"]["max_new_tokens"] == \
        STAGE0C_LAUNCH_PROFILE["policy_max_new_tokens"]
    assert sr.REPLAY_CONTRACT["surface_manifest_sha256"] == \
        STAGE0C_LAUNCH_PROFILE["surface_manifest_sha256"]
    assert sr.REPLAY_CONTRACT["generation_batch"] == 1  # singleton
    assert sr.REPLAY_CONTRACT["prompt_fewshot_sha256"] == \
        stage1.PROMPT_FEWSHOT_SHA256
    assert sr.REPLAY_CONTRACT["prompt_schema_only_sha256"] == \
        stage1.PROMPT_SCHEMA_ONLY_SHA256
    assert sr.REPLAY_CONTRACT["total_completions"] == 2_304


def test_completion_seed_semantics():
    s1 = sr.completion_seed("obs1", "p" * 64, 0)
    s2 = sr.completion_seed("obs1", "p" * 64, 1)
    s3 = sr.completion_seed("obs2", "p" * 64, 0)
    assert len({s1, s2, s3}) == 3
    assert s1 == sr.completion_seed("obs1", "p" * 64, 0)
    with pytest.raises(ValueError):
        sr.completion_seed("obs1", "p" * 64, 64)


def test_family_correct_variants_per_cell():
    assert sr.family_correct_variants("lookup_atomic") is None
    assert sr.family_correct_variants("lookup_math") is None
    assert sr.family_correct_variants("code_atomic") == ([2], [3])
    assert sr.family_correct_variants("math_code") == ([1, 2], [1, 3])
    # fork nodes sorted n1(lookup) n2(code) n3(math)
    assert sr.family_correct_variants("fork_join") == \
        ([0, 2, 1], [0, 3, 1])


def _synthetic_surface():
    cell_of = {"o_code": "code_atomic", "o_mc": "math_code",
               "o_fork": "fork_join", "o_lm": "lookup_math"}
    rows = [
        {"observation_id": "o_code", "assignment": [2], "payoff": 0.5},
        {"observation_id": "o_code", "assignment": [3], "payoff": 1.0},
        {"observation_id": "o_mc", "assignment": [1, 2], "payoff": 1.0},
        {"observation_id": "o_mc", "assignment": [1, 3], "payoff": 1.0},
        {"observation_id": "o_fork", "assignment": [0, 2, 1],
         "payoff": 1.0},
        {"observation_id": "o_fork", "assignment": [0, 3, 1],
         "payoff": 0.5},
    ]
    return rows, cell_of


def test_eligible_pair_table():
    rows, cell_of = _synthetic_surface()
    table = sr.eligible_pair_table(rows, cell_of)
    assert set(table) == {"o_code", "o_mc", "o_fork"}  # no Code: absent
    assert table["o_code"]["direction"] == 3
    assert table["o_mc"]["distinct_payoff"] is False
    assert table["o_mc"]["direction"] is None
    assert table["o_fork"]["direction"] == 2
    # a missing variant row fails closed
    with pytest.raises(InfrastructureError, match="missing"):
        sr.eligible_pair_table(rows[:1], cell_of)


def test_g_direct_gradient_bounds():
    assert sr.g_direct_gradient(0.0, 0.5) == 0.0
    assert sr.g_direct_gradient(0.5, 0.5) == pytest.approx(
        1 - 2 * 0.5 ** 8, abs=1e-12)
    with pytest.raises(ValueError):
        sr.g_direct_gradient(0.7, 0.5)


def test_expected_completion_keys_accounting():
    obs = [f"o{i:02d}" for i in range(18)]
    keys = sr.expected_completion_keys(obs)
    assert len(keys) == 2_304
    with pytest.raises(InfrastructureError, match="exactly 18"):
        sr.expected_completion_keys(obs[:17])


def test_replay_manifest_fail_closed_and_hashed():
    rows, cell_of = _synthetic_surface()
    table = sr.eligible_pair_table(rows, cell_of)
    obs = sorted(cell_of)  # 4 obs — manifest checks rr-hash coverage
    rr = {f"{o}|{p}": "a" * 64 for o in obs
          for p in (sr.REPLAY_CONTRACT["prompt_fewshot_sha256"],
                    sr.REPLAY_CONTRACT["prompt_schema_only_sha256"])}
    m = sr.build_replay_manifest(EXEC_SHA, obs, rr, table)
    assert len(m["replay_manifest_sha256"]) == 64
    assert m["contract"]["contract"] == "stage1-replay-v1"
    with pytest.raises(InfrastructureError, match="rendered-request"):
        sr.build_replay_manifest(EXEC_SHA, obs,
                                 dict(list(rr.items())[:-1]), table)


def test_summarize_replay_directions():
    rows, cell_of = _synthetic_surface()
    table = sr.eligible_pair_table(rows, cell_of)
    few = sr.REPLAY_CONTRACT["prompt_fewshot_sha256"]
    so = sr.REPLAY_CONTRACT["prompt_schema_only_sha256"]
    counts = {}
    for o in table:
        for p, (k2, k3) in ((few, (20, 22)), (so, (6, 5))):
            counts[f"{o}|{p}"] = {"k2": k2, "k3": k3, "n": 64}
    out = sr.summarize_replay(counts, table)
    # both directions represented (o_fork -> u=2, o_code -> u=3)
    assert out["directions"]["2"]["status"] == "demonstrated"
    assert out["directions"]["3"]["status"] == "demonstrated"
    # PINNED DESIGN PROPERTY (143_f disclosure): at n=64 the frozen
    # conservative rule CANNOT produce not_demonstrated — even zero
    # observed hits leave a CP upper bound whose g-value exceeds the
    # 0.10 floor (g(u,u) ~ 56 u^2; U_CP(0,64,tail<=0.025) >= 0.056 =>
    # g >= 0.126). The rule errs toward not-blocking by construction.
    low = {k: {"k2": 0, "k3": 0, "n": 64} for k in counts}
    out_low = sr.summarize_replay(low, table)
    assert out_low["directions"]["2"]["status"] == "demonstrated"
    assert out_low["directions"]["3"]["status"] == "demonstrated"
    # the branch IS reachable at larger n (documenting the mechanism,
    # not a production path: the replay's n is frozen at 64)
    big = {k: {"k2": 0, "k3": 0, "n": 6_400} for k in counts}
    out_big = sr.summarize_replay(big, table)
    assert out_big["directions"]["2"]["status"] == "not_demonstrated"
    # malformed counts refuse
    bad = dict(counts)
    key = next(iter(bad))
    bad[key] = {"k2": 40, "k3": 40, "n": 64}
    with pytest.raises(InfrastructureError, match="malformed"):
        sr.summarize_replay(bad, table)
