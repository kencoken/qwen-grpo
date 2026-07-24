"""Deterministic correctness tests for the §8.4 validation tranche
(132_s §8.4D's deterministic half; preregistered in 141_f).

These are exact-algebra and small-sample checks that run in CI. The
frozen 10,000-trial grids and the Monte-Carlo coverage battery execute
only after the 141_f preregistration is reviewed and the CPU budget is
approved; nothing here reveals a frozen-grid result.
"""

import numpy as np
import pytest
from scipy.stats import binom

from tasks.conductor import stage1, stage1_validation as sv


# --- two-point design distribution ---------------------------------------------

@pytest.mark.parametrize("delta", sv.POWER_DELTAS)
@pytest.mark.parametrize("sigma", sv.POWER_SIGMAS)
def test_two_point_moments_exact(delta, sigma):
    a, p_b = sv.two_point_distribution(delta, sigma)
    assert -1.0 <= a < 1.0
    mean = p_b * 1.0 + (1 - p_b) * a
    var = p_b * (1 - p_b) * (1.0 - a) ** 2
    assert mean == pytest.approx(delta, abs=1e-12)
    assert var ** 0.5 == pytest.approx(sigma, abs=1e-12)


def test_two_point_rejects_invalid_pairs():
    # a < -1 must reject, never clip (132_s §8.4A)
    with pytest.raises(ValueError, match="a="):
        sv.two_point_distribution(0.10, 1.05)
    with pytest.raises(ValueError):
        sv.two_point_distribution(-0.1, 0.5)
    with pytest.raises(ValueError):
        sv.two_point_distribution(0.10, 0.0)


def test_router_grid_pairs_all_valid():
    for effect in sv.ROUTER_EFFECTS:
        for sigma in sv.POWER_SIGMAS:
            sv.two_point_distribution(effect, sigma)


# --- exact interval helpers -------------------------------------------------------

def test_clopper_pearson_zero_count_closed_form():
    # U(0, n, alpha) = 1 - alpha^(1/n)
    for n, alpha in ((200, 0.0125), (500, 0.05 / 3 / 2), (36, 0.025)):
        assert sv.clopper_pearson_upper(0, n, alpha) == pytest.approx(
            1.0 - alpha ** (1.0 / n), rel=1e-9)
    assert sv.clopper_pearson_upper(5, 5, 0.05) == 1.0
    assert sv.clopper_pearson_lower(0, 10, 0.05) == 0.0


def test_clopper_pearson_inverts_binomial_tail():
    # P(X <= k | p = U) == alpha exactly (defining property)
    k, n, alpha = 3, 200, 0.0125
    u = sv.clopper_pearson_upper(k, n, alpha)
    assert binom.cdf(k, n, u) == pytest.approx(alpha, rel=1e-6)
    lo = sv.clopper_pearson_lower(k, n, alpha)
    assert binom.sf(k - 1, n, lo) == pytest.approx(alpha, rel=1e-6)


def test_clopper_pearson_monotone_in_k():
    us = [sv.clopper_pearson_upper(k, 100, 0.02) for k in range(0, 20)]
    assert us == sorted(us)


def test_wilson_bounds_one_sided():
    # frozen per 142_s: ONE-SIDED 95% (z = Phi^-1(0.95) ~ 1.645)
    from scipy.stats import norm
    z = norm.ppf(0.95)
    assert z == pytest.approx(1.6449, abs=1e-4)
    lb = sv.wilson_lower(50, 100)
    exact = (0.5 + z*z/200 - z*np.sqrt((0.25 + z*z/400)/100)) / \
        (1 + z*z/100)
    assert lb == pytest.approx(exact, abs=1e-12)
    assert sv.wilson_lower(0, 100) == 0.0
    assert sv.wilson_lower(100, 100) > 0.97
    assert sv.wilson_lower(80, 100) < sv.wilson_lower(90, 100)
    # upper mirrors lower
    assert sv.wilson_upper(50, 100) == pytest.approx(1 - lb, abs=1e-12)
    assert sv.wilson_upper(0, 100) < 0.03
    with pytest.raises(ValueError):
        sv.wilson_lower(5, 0)
    with pytest.raises(ValueError):
        sv.wilson_upper(11, 10)


def test_equivalence_decision_boundaries():
    # strict |theta| < 0.10: +/-0.10 belongs to the null (132_s §8.2)
    assert sv.equivalence_decision(-0.09, 0.09) == "pass"
    assert sv.equivalence_decision(-0.10, 0.05) == "inconclusive"
    assert sv.equivalence_decision(0.10, 0.20) == "fail"
    assert sv.equivalence_decision(-0.20, -0.10) == "fail"
    assert sv.equivalence_decision(-0.15, 0.05) == "inconclusive"
    with pytest.raises(ValueError):
        sv.equivalence_decision(0.2, 0.1)
    with pytest.raises(ValueError):
        sv.equivalence_decision(float("nan"), 0.1)


def test_adverse_replicate_constants():
    assert sv.ADVERSE_REPLICATE["lower_bound_gate"] == float("-inf")
    assert sv.ADVERSE_REPLICATE["upper_bound_gate"] == float("inf")
    assert sv.ADVERSE_REPLICATE["equivalence"] == (float("-inf"),
                                                   float("inf"))


def test_hoeffding_lower_formula():
    # exp(-2 N t^2) = a/2  =>  t = sqrt(log(2/a) / (2N))
    a, n = 0.05 / 3, 500
    t = (np.log(2.0 / a) / (2 * n)) ** 0.5
    assert sv.hoeffding_lower(0.65, n, a) == pytest.approx(0.65 - t)
    assert sv.hoeffding_lower(0.01, n, a) == 0.0  # floored at zero


# --- persistence-envelope algebra ---------------------------------------------------

def test_envelope_structural_simplification():
    # K_c = m guaranteed: L_Q = 1, U_A gets the FULL tail alpha
    b, resolved = sv.persistence_envelope(
        0, 500, 1.0, 0.05 / 3, structural_full_eligibility=True)
    assert resolved
    assert b == pytest.approx(sv.clopper_pearson_upper(0, 500, 0.05 / 3))


def test_envelope_unresolved_when_lq_zero():
    # sparse eligibility drives L_Q to 0: unresolved, never a zero-width
    # interval (132_s §8.3)
    b, resolved = sv.persistence_envelope(
        0, 500, 0.01, 0.05 / 3, structural_full_eligibility=False)
    assert not resolved
    assert b == float("inf")


def test_envelope_reproduces_132s_preliminary_geometry():
    # the frozen-formula pieces behind the 132_s §8.4C warning, exactly:
    # fork N=200, e=0.60, tail 0.025 -> L_Q ~ 0.495; zero events pass
    a = 0.05 / 2
    l_q = sv.hoeffding_lower(0.60, 200, a)
    assert l_q == pytest.approx(0.60 - (np.log(2 / a) / 400) ** 0.5,
                                abs=1e-12)
    b0, _ = sv.persistence_envelope(0, 200, 0.60, a,
                                    structural_full_eligibility=False)
    assert b0 <= 0.10  # zero-persistence criterion satisfiable
    # chain N=500, e=0.65, tail 0.05/3: zero events also pass
    b1, _ = sv.persistence_envelope(0, 500, 0.65, 0.05 / 3,
                                    structural_full_eligibility=False)
    assert b1 <= 0.10


# --- frozen grids and alpha arithmetic ------------------------------------------------

def test_position_scenarios_cover_the_alpha_matrix():
    s = sv.POSITION_SCENARIOS
    assert s["ordinary_div1"]["tail_alpha"] == pytest.approx(0.05 / 3)
    assert s["ordinary_div2"]["tail_alpha"] == pytest.approx(0.05 / 6)
    assert s["ordinary_div3"]["tail_alpha"] == pytest.approx(0.05 / 9)
    assert s["fork_div3"]["tail_alpha"] == pytest.approx(0.05 / 6)
    assert s["ordinary_div1"]["schedule"] == (100, 300, 500)
    assert s["fork_div3"]["schedule"] == (100, 200)
    # the model divisor is the fixed 3-position universe (132_s §8.2)
    assert stage1.MODEL_POSITION_ALPHA_DIVISOR == 3


def test_frozen_grid_constants():
    assert sv.POWER_DELTAS == (0.10, 0.15, 0.20)
    assert sv.POWER_SIGMAS == (0.25, 0.50, 0.75, 0.95)
    assert sv.POWER_TRIALS == 10_000
    assert sv.PERSISTENCE_ELIGIBILITY == (0.60, 0.65, 0.80, 1.00)
    assert sv.PERSISTENCE_THETAS == (0.0, 0.05, 0.10)
    assert sv.PERSISTENCE_M == 3
    assert sv.PERSISTENCE_FLOORS == {"fork": 0.60, "ordinary": 0.65}
    assert sv.ROUTER_EFFECTS == (0.05, 0.10, 0.15)
    assert sv.ROUTER_MIXTURES == {"core": 5, "core_fork": 6}
    assert sv.ROUTER_SUPPORT_PER_CELL == 100
    assert sv.COVERAGE_OUTER_TRIALS == 5_000
    assert sv.COVERAGE_INNER_REPLICATES == 2_000
    assert sv.COVERAGE_AGREEMENT_DATASETS == 1_000
    assert sv.COVERAGE_AGREEMENT_MIN == 0.995
    assert sv.COVERAGE_SCENARIO_CAP == 8


def test_coverage_alpha_ceiling():
    assert sv.coverage_alpha_ceiling(0.001) == pytest.approx(0.006)
    assert sv.coverage_alpha_ceiling(0.05) == pytest.approx(0.0625)


def test_scenario_seeds_deterministic_and_distinct():
    s1 = sv.scenario_seed("A|ordinary_div1|0.15|0.5|10000")
    s2 = sv.scenario_seed("A|ordinary_div1|0.15|0.5|10000")
    s3 = sv.scenario_seed("A|ordinary_div1|0.15|0.25|10000")
    assert s1 == s2 != s3
    assert 0 <= s1 < 2 ** 64


# --- small-sample behavioral sanity (non-frozen trial counts) ---------------------------

def test_position_sim_null_holds_designed_size():
    # delta = 0: a false pass needs LCB > 0, whose per-look probability
    # is <= the allocated tail alpha; Bonferroni across the 3 looks
    # bounds total type-I at 3 x 0.05/3 = 0.05. (The 10-point rule is a
    # materiality filter, not the size guarantee — at sigma = 0.5 and
    # N = 100 it sits near 2 SE, so it does not dominate.) 400 throwaway
    # trials sanity-check the machinery, never a frozen grid cell.
    out = sv.simulate_position_power("ordinary_div1", 0.0, 0.50,
                                     n_trials=400)
    assert out["pass_rate"] <= 0.05 + 0.02  # designed bound + MC slack


def test_position_sim_strong_effect_passes():
    out = sv.simulate_position_power("ordinary_div1", 0.20, 0.25,
                                     n_trials=400)
    assert out["pass_rate"] >= 0.99
    # bookkeeping is exact
    assert (out["pass_count"] + out["fail_count"]
            + out["unresolved_count"]) == 400
    assert sum(out["pass_by_look"].values()) == out["pass_count"]


def test_router_sim_null_size_and_power_direction():
    null = sv.simulate_router_power("core", 0.0 + 1e-9, 0.50,
                                    n_trials=400)
    assert null["pass_rate"] <= 0.06  # ~alpha with MC noise
    strong = sv.simulate_router_power("core", 0.15, 0.25, n_trials=400)
    assert strong["pass_rate"] >= 0.99


def test_persistence_sim_matches_exact_binomial():
    # cluster-correlated pass events are a deterministic function of
    # k ~ Bin(n_elig, theta): the sim must agree with the exact tail
    out = sv.simulate_persistence_envelope(
        "fork", 200, 0.60, 0.05, "cluster_correlated", n_trials=2_000)
    n_elig = 120
    tail = sv.PERSISTENCE_LOOKS["fork"]["tail_alpha"]
    l_q = sv.hoeffding_lower(0.60, 200, tail)
    k_star = -1
    for k in range(n_elig + 1):
        u = sv.clopper_pearson_upper(k, 200, tail / 2)
        if min(1.0, u / l_q) <= sv.PERSISTENCE_GATE:
            k_star = k
        else:
            break
    exact = float(binom.cdf(k_star, n_elig, 0.05))
    assert out["pass_rate"] == pytest.approx(exact, abs=0.03)


def test_persistence_zero_theta_always_passes_at_floors():
    for schedule, n in (("fork", 200), ("ordinary", 500)):
        out = sv.simulate_persistence_envelope(
            schedule, n, sv.PERSISTENCE_FLOORS[schedule], 0.0,
            "cluster_correlated", n_trials=200)
        assert out["pass_rate"] == 1.0


def test_row_dispersed_differs_from_cluster_correlated():
    cc = sv.simulate_persistence_envelope(
        "ordinary", 500, 0.65, 0.05, "cluster_correlated", n_trials=500)
    rd = sv.simulate_persistence_envelope(
        "ordinary", 500, 0.65, 0.05, "row_dispersed", n_trials=500)
    # same primary estimand, materially different cluster-any rates:
    # dispersing rows over more clusters raises P(A_c = 1) mass
    assert rd["pass_rate"] < cc["pass_rate"]


def test_bootstrap_renderer_coupling():
    # renderer rows travel WITH their cluster: permuting rows inside a
    # cluster changes nothing; moving a renderer row across clusters
    # changes the interval.
    rng = np.random.default_rng(3)
    cell = rng.normal(0.1, 0.4, size=(40, 3))
    base = sv.paired_cluster_bootstrap([cell], 0.05, 300, seed=7)
    permuted = cell[:, ::-1].copy()
    assert sv.paired_cluster_bootstrap([permuted], 0.05, 300,
                                       seed=7) == base
    crossed = cell.copy()
    crossed[0, 0], crossed[1, 0] = cell[1, 0], cell[0, 0]
    assert sv.paired_cluster_bootstrap([crossed], 0.05, 300,
                                       seed=7) != base
    # rejects renderer-collapsed input: rows must be matrices
    with pytest.raises(ValueError, match="matrix"):
        sv.paired_cluster_bootstrap([cell.mean(axis=1)], 0.05, 50,
                                    seed=1)


def test_bootstrap_unequal_cell_sizes_and_determinism():
    rng = np.random.default_rng(4)
    cells = [rng.normal(0.0, 0.5, size=(n, 3)) for n in (12, 6, 36)]
    a = sv.paired_cluster_bootstrap(cells, 0.05 / 2, 200, seed=7)
    b = sv.paired_cluster_bootstrap(cells, 0.05 / 2, 200, seed=7)
    c = sv.paired_cluster_bootstrap(cells, 0.05 / 2, 200, seed=8)
    assert a == b != c
    assert a[0] <= a[1]


def test_bootstrap_zero_cluster_cell_is_adverse():
    rng = np.random.default_rng(5)
    cells = [rng.normal(0.5, 0.1, size=(20, 3)),
             np.empty((0, 3))]
    lcb, ucb = sv.paired_cluster_bootstrap(cells, 0.05, 100, seed=1)
    assert lcb == float("-inf") and ucb == float("-inf")


def test_sequential_stake_decision_logic():
    # strong positive effect: pass; strong negative: conclusive fail;
    # near-zero spread: unresolved at cap — the complete trichotomy
    up = [np.full((200, 3), 0.4)]
    down = [np.full((200, 3), -0.4)]
    assert sv.sequential_stake_decision(up, (100, 200), 0.05 / 6, 100,
                                        seed=1) == "pass"
    assert sv.sequential_stake_decision(down, (100, 200), 0.05 / 6, 100,
                                        seed=1) == "fail"
    rng = np.random.default_rng(6)
    flat = [rng.normal(0.0, 0.001, size=(200, 3))]
    assert sv.sequential_stake_decision(flat, (100, 200), 0.05 / 6, 100,
                                        seed=1) == "unresolved"


def test_sequential_equivalence_decision_logic():
    rng = np.random.default_rng(7)
    inside = [rng.normal(0.0, 0.05, size=(200, 3))]
    outside = [rng.normal(0.5, 0.05, size=(200, 3))]
    assert sv.sequential_equivalence_decision(
        inside, (100, 200), 0.05 / 2, 100, seed=1) == "pass"
    assert sv.sequential_equivalence_decision(
        outside, (100, 200), 0.05 / 2, 100, seed=1) == "fail"
