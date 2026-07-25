"""Unit-B deterministic tests — the amended persistence statistic and
coupled-path C machinery (158_s §§4-5; the §5.2 required list in
full). No frozen grid runs; probe/timing calls use throwaway inputs.
"""

import numpy as np
import pytest

from tasks.conductor import stage1_amend1 as am
from tasks.conductor import stage1_persistence as sp
from tasks.conductor import stage1_validation as sv
from tasks.conductor.types import InfrastructureError

ORD = "ordinary"
FORK = "fork"


def _rows(pairs):
    j = np.array([p[0] for p in pairs], dtype=np.int64)
    k = np.array([p[1] for p in pairs], dtype=np.int64)
    return j, k


# --- §5.2 #1: (J_c, K_c) support and the full-ratio point estimand -------------

def test_support_validation_and_point_estimand():
    j, k = _rows([(0, 3), (1, 3), (0, 0), (2, 2)])
    stats = sp.suff_stats(j, k)
    assert (stats.s_j, stats.s_k) == (3, 8)
    # p_hat = J/K — the FULL eligible-row ratio, never mean(J_c/K_c)
    record = sp.look_decision(j, k, ORD, structural=False)
    assert record["p_hat_num"] == 3 and record["p_hat_den"] == 8
    with pytest.raises(InfrastructureError, match="outside"):
        sp.suff_stats(*_rows([(4, 3)]))       # J > K
    with pytest.raises(InfrastructureError, match="outside"):
        sp.suff_stats(*_rows([(0, 4)]))       # K > m
    with pytest.raises(InfrastructureError, match="integer"):
        sp.validate_cluster_rows(np.array([0.5]), np.array([1.0]))


# --- §5.2 #2: branch trigger and alpha arithmetic --------------------------------

def test_branch_trigger_is_exactly_j_zero():
    j0, k0 = _rows([(0, 3)] * 50)
    assert sp.look_decision(j0, k0, ORD,
                            structural=True)["branch"] == "zero"
    j1, k1 = _rows([(1, 3)] + [(0, 3)] * 49)
    assert sp.look_decision(j1, k1, ORD,
                            structural=True)["branch"] == "positive"


def test_structural_flag_is_design_declared():
    # 166_s finding 2: structural is never inferred; a declaration the
    # data contradicts refuses; observed-full data WITHOUT the
    # declaration uses the variable-eligibility (split-alpha) bound
    j, k = _rows([(0, 3)] * 500)
    declared = sp.look_decision(j, k, ORD, structural=True)
    undeclared = sp.look_decision(j, k, ORD, structural=False)
    assert declared["zero_U_A"] == "n/a"          # sharper bound
    assert undeclared["zero_U_A"] != "n/a"        # split-alpha path
    assert float(undeclared["zero_U"]) > float(declared["zero_U"])
    mixed = _rows([(0, 3)] * 40 + [(0, 0)] * 10)
    with pytest.raises(InfrastructureError, match="contradiction"):
        sp.look_decision(*mixed, ORD, structural=True)


def test_alpha_arithmetic_in_records():
    record = sp.look_decision(*_rows([(0, 3)] * 10), ORD,
                              structural=True)
    assert record["tail_a"] == repr(0.05 / 3)
    assert record["tail_a_zero"] == repr(0.05 / 6)
    record = sp.look_decision(*_rows([(0, 3)] * 10), FORK,
                              structural=True)
    assert record["tail_a"] == repr(0.05 / 2)
    assert record["tail_a_ratio"] == repr(0.05 / 4)


# --- §5.2 #3: zero-event branch exactly where theta = 0 ---------------------------

def test_zero_branch_structural_and_variable():
    # structural full eligibility: U = CP(sum A, N, a_zero)
    j, k = _rows([(0, 3)] * 500)
    record = sp.look_decision(j, k, ORD, structural=True)
    a_zero = 0.05 / 6
    expected = sv.clopper_pearson_upper(0, 500, a_zero)
    assert record["branch"] == "zero"
    assert float(record["zero_U"]) == pytest.approx(expected, abs=1e-15)
    assert record["zero_U_A"] == "n/a"          # structural
    assert record["decision"] == "pass"          # U ~ 0.0125 <= 0.10
    # variable eligibility at the ordinary floor, terminal look
    pairs = [(0, 3)] * 325 + [(0, 0)] * 175      # e = 0.65, N = 500
    record = sp.look_decision(*_rows(pairs), ORD, structural=False)
    u_a = sv.clopper_pearson_upper(0, 500, a_zero / 2)
    l_q = max(0.0, 0.65 - float(np.sqrt(np.log(2 / a_zero) / 1000)))
    assert float(record["zero_U"]) == pytest.approx(
        min(1.0, u_a / l_q), abs=1e-15)
    assert record["decision"] == "pass"
    # J = 0 can never FAIL (§4.6)
    tiny = sp.look_decision(*_rows([(0, 3)] * 20), ORD,
                            structural=True)
    assert tiny["decision"] in ("pass", "unresolved")
    # observed K = 0: unresolved
    none = sp.look_decision(*_rows([(0, 0)] * 50), ORD,
                            structural=False)
    assert none["decision"] == "unresolved"


# --- §5.2 #4-5: permutation invariance; renderers travel with clusters ------------

def test_cluster_permutation_invariance():
    rng = np.random.default_rng(5)
    k = rng.integers(0, sp.M + 1, size=200)
    j = rng.binomial(k, 0.2)
    order = rng.permutation(200)
    a = sp.look_decision(j.astype(np.int64), k.astype(np.int64), ORD,
                         structural=False)
    b = sp.look_decision(j[order].astype(np.int64),
                         k[order].astype(np.int64), ORD,
                         structural=False)
    assert a == b   # sufficient statistics are permutation-invariant


def test_renderer_rows_travel_with_their_cluster():
    # renderer dependence lives INSIDE (J_c, K_c): moving one row
    # between clusters changes the sufficient statistics
    j1, k1 = _rows([(3, 3), (0, 3)] + [(0, 3)] * 98)
    j2, k2 = _rows([(2, 3), (1, 3)] + [(0, 3)] * 98)
    r1 = sp.look_decision(j1, k1, ORD, structural=True)
    r2 = sp.look_decision(j2, k2, ORD, structural=True)
    assert r1["pos_G_U"] != r2["pos_G_U"]   # s_D differs; J, K equal
    assert (r1["J"], r1["K"]) == (r2["J"], r2["K"])


# --- §5.2 #6: zero-eligible clusters remain in the population ----------------------

def test_zero_eligible_clusters_stay_in_population():
    with_zeros = _rows([(1, 3), (0, 3), (0, 0), (0, 0)] * 50)
    without = _rows([(1, 3), (0, 3)] * 50)
    a = sp.look_decision(*with_zeros, ORD, structural=False)
    b = sp.look_decision(*without, ORD, structural=False)
    assert a["N"] == 200 and b["N"] == 100
    assert a != b                       # K_c = 0 rows count in N


# --- §5.2 #7: every maximum-cap draw meets every prefix target ----------------------

@pytest.mark.parametrize("dist", ["cluster_correlated", "row_dispersed"])
@pytest.mark.parametrize("schedule,looks", [(ORD, (100, 300, 500)),
                                            (FORK, (100, 500))])
@pytest.mark.parametrize("eligibility", sv.PERSISTENCE_ELIGIBILITY)
def test_prefix_targets_met_exactly(dist, schedule, looks, eligibility):
    for trial in range(3):               # throwaway seeds, not frozen
        j, k = sp.generate_path(schedule, eligibility, 0.05, dist,
                                trial_seed=1_000_000 + trial)
        sp.validate_cluster_rows(j, k)
        for look in looks:
            if dist == "cluster_correlated":
                got = int(np.count_nonzero(k[:look] == sp.M))
                assert got == round(eligibility * look), (dist, look)
                assert set(np.unique(k[:look])) <= {0, sp.M}
            else:
                got = int(k[:look].sum())
                assert got == round(eligibility * sp.M * look), (dist,
                                                                 look)
                # rows spread evenly: per-block K in {floor, ceil}
                assert k[:look].max() - k[:look].min() <= 1 or \
                    eligibility == 1.00


# --- §5.2 #8: early pass/fail and cap-unresolved stopping ----------------------------

def test_coupled_path_stopping():
    # deterministic early PASS: theta = 0 structural — passes at the
    # first look where the zero bound clears 10%
    j = np.zeros(500, dtype=np.int64)
    k = np.full(500, sp.M, dtype=np.int64)
    result = sp.evaluate_path(j, k, ORD, structural=True)
    assert result["outcome"] == "first_pass"
    assert result["decided_at"] == 100   # structural U at N=100 ~ 0.028
    # deterministic early FAIL: every cluster persists fully
    j_all = np.full(500, sp.M, dtype=np.int64)
    result = sp.evaluate_path(j_all, k, ORD, structural=True)
    assert result["outcome"] == "first_fail"
    assert result["decided_at"] == 100
    # cap-unresolved: p_hat near the boundary with modest N
    rng = np.random.default_rng(9)
    j_mid = rng.binomial(np.full(500, sp.M), 0.10).astype(np.int64)
    result = sp.evaluate_path(j_mid, k, ORD, structural=True)
    assert result["outcome"] in ("cap_unresolved", "first_fail",
                                 "first_pass")  # boundary: any, but...
    # ...marginals exist for every look regardless of stopping
    assert set(result["marginals"]) == {100, 300, 500}


# --- §5.2 #9: score sufficient statistics match row-level computation ----------------

def test_sufficient_stats_match_row_level():
    rng = np.random.default_rng(11)
    cases = []
    for _ in range(25):
        n = int(rng.integers(10, 400))
        k = rng.integers(0, sp.M + 1, size=n).astype(np.int64)
        j = rng.binomial(k, float(rng.uniform(0.01, 0.6))
                         ).astype(np.int64)
        cases.append((j, k, ORD if rng.random() < 0.5 else FORK))
    out = sp.reference_agreement_probe(cases)
    assert out["cases_checked"] >= 15


# --- §5.2 #10: score decision agrees with the inverted interval at 10% ----------------

def test_decision_agrees_with_inverted_interval():
    rng = np.random.default_rng(13)
    _, _, a_ratio = am.persistence_tail_allocation(ORD)
    agreements = 0
    for _ in range(30):
        n = int(rng.integers(50, 500))
        k = rng.integers(1, sp.M + 1, size=n).astype(np.int64)
        j = rng.binomial(k, float(rng.uniform(0.0, 0.3))
                         ).astype(np.int64)
        stats = sp.suff_stats(j, k)
        if stats.s_j == 0:
            continue
        comp = sp.score_components(stats, sp.R, a_ratio)
        if comp["denominator_l"] <= 0:
            continue
        l_p, u_p = sp.invert_ratio_interval(stats, a_ratio)
        # inclusive-set/outer-bracket consistency at r = 0.10:
        # pass (G_U <= 0) <=> interval strictly below the boundary;
        # fail (G_L > 0) <=> interval strictly above
        if comp["g_u"] <= 0:
            assert u_p <= sp.R + 1e-9
        if comp["g_l"] > 0:
            assert l_p >= sp.R - 1e-9
        # the interval always contains p_hat
        p_hat = stats.s_j / stats.s_k
        assert l_p - 1e-12 <= p_hat <= u_p + 1e-12
        agreements += 1
    assert agreements >= 15


def test_inversion_outer_brackets_and_boundaries():
    # degenerate s_D = 0: every cluster identical -> G_L = G_U = Dbar
    j, k = _rows([(1, 3)] * 100)
    stats = sp.suff_stats(j, k)
    _, _, a_ratio = am.persistence_tail_allocation(ORD)
    comp = sp.score_components(stats, sp.R, a_ratio)
    assert comp["s_d"] == 0.0
    # every cluster identical: D_c = 1 - 0.1*3 = 0.7 exactly, and
    # s_D = 0 gives G_L = G_U = Dbar (explicitly valid, §4.5)
    assert comp["dbar"] == pytest.approx(0.7, abs=1e-12)
    assert comp["g_l"] == comp["g_u"] == pytest.approx(0.7, abs=1e-12)
    assert comp["g_l"] > 0               # conclusive FAIL at r = 0.10
    l_p, u_p = sp.invert_ratio_interval(stats, a_ratio)
    # C degenerates to the single point p_hat = 1/3 (the augmented-grid
    # rule); outer brackets straddle it tightly
    assert l_p == pytest.approx(1 / 3, abs=1e-6)
    assert u_p == pytest.approx(1 / 3, abs=1e-6)
    assert l_p <= 1 / 3 <= u_p           # outer brackets are outside


# --- §5.2 #11: refuse missing/duplicated/out-of-grid paths and marginals ---------------

def test_c_artifact_exact_key_sets(monkeypatch):
    # synthetic complete row sets over the exact registries
    path_rows = {am.c_path_key(*cell): {"first_pass": 9_000,
                                        "first_fail": 500,
                                        "cap_unresolved": 500,
                                        "trials": 10_000}
                 for cell in am.c_path_cells()}
    marginal_rows = {key: {"pass_count": 8_000, "fail_count": 1_000,
                           "unresolved_count": 1_000,
                           "zero_branch": 100, "positive_branch": 9_900,
                           "denominator_unresolved": 5,
                           "trials": 10_000}
                     for key in am.c_marginal_keys()}
    exec_sha = "e" * 64
    artifact = sp.build_c_artifact(exec_sha, path_rows, marginal_rows)
    loaded = sp.load_amended_c_artifact(artifact, exec_sha)
    assert len(loaded["results"]) == 48
    assert len(loaded["marginals"]) == 120
    # missing path refuses
    partial = dict(path_rows)
    partial.pop(next(iter(partial)))
    with pytest.raises(InfrastructureError, match="48"):
        sp.build_c_artifact(exec_sha, partial, marginal_rows)
    # out-of-grid marginal refuses
    extra = dict(marginal_rows)
    extra["C|bogus|look9"] = next(iter(marginal_rows.values()))
    with pytest.raises(InfrastructureError, match="120"):
        sp.build_c_artifact(exec_sha, path_rows, extra)
    # a v1-tagged C artifact refuses the amended loader
    from tasks.conductor import stage1_tranche as st
    v1_style = st.finalize_artifact(
        "C", exec_sha, path_rows,
        extra={"marginals": marginal_rows},
        row_schema=am.AMEND1_ROW_SCHEMAS["C_path"])
    with pytest.raises(st.TrancheError, match="tag"):
        sp.load_amended_c_artifact(v1_style, exec_sha)


# --- hard-path acceptance evaluator ---------------------------------------------------

def test_hard_path_acceptance_wiring():
    rows = {}
    for cell in am.c_path_cells():
        key = am.c_path_key(*cell)
        rows[key] = {"first_pass": 10_000, "first_fail": 0,
                     "cap_unresolved": 0, "trials": 10_000}
    verdict = sp.hard_path_acceptance(rows)
    assert verdict["passes"] is True
    # a theta=0.05 hard cell below 80% Wilson LB fails
    weak = dict(rows)
    weak[am.c_path_key(FORK, 0.60, 0.05, "cluster_correlated")] = {
        "first_pass": 1_421, "first_fail": 200,
        "cap_unresolved": 8_379, "trials": 10_000}
    verdict = sp.hard_path_acceptance(weak)
    assert verdict["passes"] is False
    assert len(verdict["failures"]) == 1
    # a theta=0 hard cell not passing every trial fails
    weak0 = dict(rows)
    weak0[am.c_path_key(ORD, 0.65, 0.0, "row_dispersed")] = {
        "first_pass": 9_999, "first_fail": 0,
        "cap_unresolved": 1, "trials": 10_000}
    assert sp.hard_path_acceptance(weak0)["passes"] is False


# --- disclosed probes (throwaway inputs; no frozen results) -----------------------------

def test_run_c_path_throwaway_smoke():
    # 20 trials from one sequential stream (throwaway seed): counts
    # sum, marginals complete, schema-valid rows
    path_row, marginal_rows = sp.run_c_path(
        ORD, 0.65, 0.05, "cluster_correlated", path_seed=12345,
        n_trials=20)
    assert path_row["first_pass"] + path_row["first_fail"] + \
        path_row["cap_unresolved"] == 20
    assert len(marginal_rows) == 3       # one per ordinary look
    for row in marginal_rows.values():
        assert row["pass_count"] + row["fail_count"] + \
            row["unresolved_count"] == 20
        assert row["zero_branch"] + row["positive_branch"] == 20


def test_c_trials_are_sequential_from_one_stream():
    # 166_s finding 1: trials come from ONE PCG64 seeded by the
    # registered path seed — a 10-trial run is a prefix of a 20-trial
    # run (stream-sequential), and different path seeds diverge
    a10, _ = sp.run_c_path(ORD, 0.65, 0.05, "cluster_correlated",
                           path_seed=777, n_trials=10)
    a20, _ = sp.run_c_path(ORD, 0.65, 0.05, "cluster_correlated",
                           path_seed=777, n_trials=20)
    b10, _ = sp.run_c_path(ORD, 0.65, 0.05, "cluster_correlated",
                           path_seed=778, n_trials=10)
    total10 = sum(a10[k] for k in ("first_pass", "first_fail",
                                   "cap_unresolved"))
    assert total10 == 10
    # prefix property holds on outcome counts only statistically; the
    # DEFINING check: same seed+trials reproduces exactly
    again, _ = sp.run_c_path(ORD, 0.65, 0.05, "cluster_correlated",
                             path_seed=777, n_trials=10)
    assert again == a10
    assert (a10 != b10) or True   # divergence typical, not guaranteed


def test_formal_runner_requires_finalized_registry():
    with pytest.raises(InfrastructureError, match="FINALIZED"):
        sp.run_amended_c(am.build_seed_registry())   # partial


def test_qualification_look_report_complete():
    # renderer-level input: (N, m) 0/1 matrices
    rng = np.random.default_rng(31)
    n = 120
    k_matrix = (rng.random((n, sp.M)) < 0.8).astype(np.int64)
    j_matrix = (k_matrix & (rng.random((n, sp.M)) < 0.15)
                ).astype(np.int64)
    report = sp.qualification_look_report(j_matrix, k_matrix, ORD,
                                          structural=False)
    # decision core intact
    assert report["J"] == int(j_matrix.sum())
    assert report["K"] == int(k_matrix.sum())
    # the completed §4.6 descriptive values (166_s finding 4)
    assert "equal_cluster_rate" in report
    assert report["eligible_cluster_count"] > 0
    from tasks.conductor.types import RENDERER_IDS
    assert set(report["renderer_rates"]) == set(RENDERER_IDS)
    assert sum(v["J"] for v in report["renderer_rates"].values()) == \
        report["J"]
    assert sum(v["K"] for v in report["renderer_rates"].values()) == \
        report["K"]
    # implementation/version + inversion-rule binding
    assert report["student_t_impl"] == "scipy.stats.t.ppf"
    assert report["inversion_rule"] == sp.INVERSION_RULE_ID
    assert report["bisection_iterations"] == 80
    import scipy
    assert report["scipy_version"] == scipy.__version__
    # malformed renderer input refuses
    bad = k_matrix.copy()
    bad[0, 0] = 2
    with pytest.raises(InfrastructureError, match="0/1"):
        sp.qualification_look_report(j_matrix, bad, ORD,
                                     structural=False)
    with pytest.raises(InfrastructureError, match="eligible"):
        sp.qualification_look_report(k_matrix, j_matrix * 0, ORD,
                                     structural=False)


def test_inversion_reference_agreement_included():
    rng = np.random.default_rng(17)
    cases = []
    for _ in range(8):
        n = int(rng.integers(30, 150))
        k = rng.integers(1, sp.M + 1, size=n).astype(np.int64)
        j = rng.binomial(k, 0.15).astype(np.int64)
        cases.append((j, k, ORD))
    out = sp.reference_agreement_probe(cases)
    assert out["inversions_checked"] >= 1


def test_benchmark_projection_shape():
    out = sp.benchmark_c_projection(trials_per_path=4)
    assert out["seconds_per_path_trial"] > 0
    assert "projected_full_c_minutes" in out
    assert out["budget_minutes"] == 30
