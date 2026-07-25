"""Pre-CE1 design-validation tranche — 132_s §8.4 (unit 3).

Implements checks A (look-cap power), C (persistence-envelope
feasibility), and the Monte-Carlo half of D (coverage battery framework);
check B (the direct-gradient GPU replay) has its support, prompts, seeds,
and manifest requirements frozen in the 141_f preregistration and is
driven separately after that preregistration is reviewed.

Discipline (132_s §8.4): the scenario grids, seeds, and acceptance
criteria below are FROZEN by 141_f before any frozen run executes; the
tranche's single reviewed outcome either confirms the current design or
amends it once in a new reviewed plan before construction registration.
This module never inspects formal construction or qualification outcomes
— its only inputs are frozen formulas, synthetic sensitivity cases, and
(for B, elsewhere) retained Stage-0 records.

Everything here is a *design approximation* battery, not the production
bootstrap: check A uses the exact two-point design distribution and the
allocated-alpha normal-approximation interval that 132_s §8.4A
specifies; production inference remains the §8.3 cluster bootstrap.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Mapping

import numpy as np
from scipy.stats import beta as _beta
from scipy.stats import norm as _norm

from . import stage1

# --- frozen seed derivation ---------------------------------------------------

_TRANCHE_TAG = "stage1-validation-v1"


def scenario_seed(scenario_id: str) -> int:
    """First 8 bytes (big-endian) of SHA-256 over the ␟-joined
    (tag, scenario_id) — same convention as stage1.bootstrap_seed."""
    material = "\x1f".join([_TRANCHE_TAG, scenario_id])
    return int.from_bytes(
        hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


def _rng(scenario_id: str) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(scenario_seed(scenario_id)))


# --- shared exact helpers -------------------------------------------------------

def clopper_pearson_upper(k: int, n: int, alpha: float) -> float:
    """One-sided exact upper bound: P(X <= k | p = U) = alpha."""
    if not 0 <= k <= n:
        raise ValueError(f"k={k} outside [0, {n}]")
    if k == n:
        return 1.0
    return float(_beta.ppf(1.0 - alpha, k + 1, n - k))


def clopper_pearson_lower(k: int, n: int, alpha: float) -> float:
    """One-sided exact lower bound: P(X >= k | p = L) = alpha."""
    if not 0 <= k <= n:
        raise ValueError(f"k={k} outside [0, {n}]")
    if k == 0:
        return 0.0
    return float(_beta.ppf(alpha, k, n - k + 1))


def _wilson(k: int, n: int, confidence: float) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= k <= n:
        raise ValueError(f"k={k} outside [0, {n}]")
    z = float(_norm.ppf(confidence))
    phat = k / n
    denom = 1.0 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * ((phat * (1 - phat) + z * z / (4 * n)) / n) ** 0.5
    return (max(0.0, (centre - margin) / denom),
            min(1.0, (centre + margin) / denom))


def wilson_lower(k: int, n: int, confidence: float = 0.95) -> float:
    """ONE-SIDED 95% Wilson score lower bound (z = Phi^-1(0.95) ~ 1.645;
    frozen per 142_s: the §8.4 pass-probability and agreement criteria
    are one-sided claims)."""
    return _wilson(k, n, confidence)[0]


def wilson_upper(k: int, n: int, confidence: float = 0.95) -> float:
    """ONE-SIDED 95% Wilson score upper bound — the §8.4D
    operational-error ceiling comparator."""
    return _wilson(k, n, confidence)[1]


def equivalence_decision(lcb: float, ucb: float,
                         band: float = 0.10) -> str:
    """§8.2 strict-equivalence trichotomy: |theta| < band. Pass only when
    the full interval lies strictly inside (-band, band); fail when it
    lies wholly outside; otherwise inconclusive. theta = +/-band belongs
    to the null."""
    if np.isnan(lcb) or np.isnan(ucb) or lcb > ucb:
        raise ValueError(f"malformed interval [{lcb}, {ucb}]")
    # adverse-widened endpoints (-inf/+inf) fall through to inconclusive
    if lcb > -band and ucb < band:
        return "pass"
    if lcb >= band or ucb <= -band:
        return "fail"
    return "inconclusive"


# §8.3 undefined-replicate rules: a replicate with zero eligible
# observations receives the gate-adverse extreme and is counted, never
# redrawn.
ADVERSE_REPLICATE = {"lower_bound_gate": float("-inf"),
                     "upper_bound_gate": float("inf"),
                     "equivalence": (float("-inf"), float("inf"))}


def hoeffding_lower(mean_q: float, n: int, tail_alpha: float) -> float:
    """132_s §8.3 L_Q: distribution-free lower bound at alpha/2 when the
    caller has split tail alpha `a` equally (log(2/a) form)."""
    return max(0.0, mean_q - (np.log(2.0 / tail_alpha) / (2 * n)) ** 0.5)


def persistence_envelope(k_any_event: int, n_clusters: int,
                         mean_q: float, tail_alpha: float, *,
                         structural_full_eligibility: bool
                         ) -> tuple[float, bool]:
    """The §8.3 operational upper bound. Returns (bound, resolved):
    unresolved (L_Q = 0) is reported as (inf, False) — never replaced by
    a zero-width interval."""
    if structural_full_eligibility:
        u_a = clopper_pearson_upper(k_any_event, n_clusters, tail_alpha)
        return u_a, True
    u_a = clopper_pearson_upper(k_any_event, n_clusters, tail_alpha / 2.0)
    l_q = hoeffding_lower(mean_q, n_clusters, tail_alpha)
    if l_q <= 0.0:
        return float("inf"), False
    return min(1.0, u_a / l_q), True


# --- A. look-cap power ----------------------------------------------------------

def two_point_distribution(delta: float, sigma: float
                           ) -> tuple[float, float]:
    """132_s §8.4A bounded design distribution: D in {a, 1} with
    E[D] = delta, SD(D) = sigma. Rejects an invalid pair rather than
    clipping it."""
    if not 0.0 <= delta < 1.0:
        raise ValueError(f"delta {delta} outside [0, 1)")
    if sigma <= 0.0:
        raise ValueError(f"sigma {sigma} must be positive")
    a = delta - sigma * sigma / (1.0 - delta)
    if a < -1.0:
        raise ValueError(f"invalid (delta={delta}, sigma={sigma}): "
                         f"a={a:.4f} < -1")
    p_b = (delta - a) / (1.0 - a)
    if not 0.0 < p_b < 1.0:
        raise ValueError(f"invalid (delta={delta}, sigma={sigma}): "
                         f"P(D=1)={p_b:.4f}")
    return a, p_b


# The frozen §8.4A grids. Position scenarios are the distinct
# (schedule, alpha-divisor) combinations the §8.2 rules produce:
# family gates divide the one-look tail alpha by positions-in-cell
# (1 atomic, 2 chain, 3 fork); model gates always divide by the fixed
# 3-position universe on their cell's schedule.
POSITION_SCENARIOS: dict[str, dict[str, Any]] = {
    "ordinary_div1": {"schedule": stage1.ORDINARY_LOOK_SCHEDULE,
                      "tail_alpha": 0.05 / 3 / 1},
    "ordinary_div2": {"schedule": stage1.ORDINARY_LOOK_SCHEDULE,
                      "tail_alpha": 0.05 / 3 / 2},
    "ordinary_div3": {"schedule": stage1.ORDINARY_LOOK_SCHEDULE,
                      "tail_alpha": 0.05 / 3 / 3},
    "fork_div3": {"schedule": stage1.FORK_LOOK_SCHEDULE,
                  "tail_alpha": 0.05 / 2 / 3},
}
POWER_DELTAS = (0.10, 0.15, 0.20)
POWER_SIGMAS = (0.25, 0.50, 0.75, 0.95)
POWER_TRIALS = 10_000
POINT_MATERIALITY = 0.10          # the >=10-point stake rule
ACCEPT_DELTA = 0.15               # acceptance evaluated here...
ACCEPT_SIGMA_MAX = 0.50           # ...for sigma <= 0.50
ACCEPT_PASS_WILSON_LB = 0.80

ROUTER_EFFECTS = (0.05, 0.10, 0.15)
ROUTER_ACCEPT_EFFECT = 0.10
ROUTER_ALPHA = stage1.AGGREGATE_ROUTER_ALPHA          # 0.025 one-sided
ROUTER_SUPPORT_PER_CELL = 100                          # fixed first-100
ROUTER_MIXTURES = {"core": 5, "core_fork": 6}


def simulate_position_power(scenario: str, delta: float, sigma: float,
                            n_trials: int = POWER_TRIALS,
                            seed_override: int | None = None
                            ) -> dict[str, Any]:
    """One (scenario, delta, sigma) grid cell: draw one maximum-length
    iid vector per trial, evaluate immutable prefixes at each registered
    look with the allocated-alpha normal-approximation interval and
    sample SE, and apply the frozen stopping + point-materiality rules.

    Pass at a look: point >= 0.10 AND LCB > 0. Conclusive fail at a
    look: UCB < 0. Otherwise expand; unresolved at the cap is
    not-passed. `ever_pass` is the pass-by-cap probability."""
    spec = POSITION_SCENARIOS[scenario]
    schedule, tail_alpha = spec["schedule"], spec["tail_alpha"]
    a, p_b = two_point_distribution(delta, sigma)
    z = float(_norm.ppf(1.0 - tail_alpha))
    cap = schedule[-1]
    # amended runs supply the REGISTERED fresh-domain seed (158_s
    # §9.3); the default derivation remains the v1 domain for probes
    if seed_override is not None:
        rng = np.random.Generator(np.random.PCG64(seed_override))
    else:
        rng = _rng(f"A|{scenario}|{delta}|{sigma}|{n_trials}")
    draws = np.where(rng.random((n_trials, cap)) < p_b, 1.0, a)
    passed = np.zeros(n_trials, dtype=bool)
    failed = np.zeros(n_trials, dtype=bool)
    pass_look = np.full(n_trials, -1)
    for look in schedule:
        prefix = draws[:, :look]
        mean = prefix.mean(axis=1)
        se = prefix.std(axis=1, ddof=1) / np.sqrt(look)
        live = ~passed & ~failed
        now_pass = live & (mean >= POINT_MATERIALITY) & (mean - z * se > 0)
        now_fail = live & (mean + z * se < 0)
        pass_look[now_pass] = look
        passed |= now_pass
        failed |= now_fail
    k = int(passed.sum())
    return {
        "scenario": scenario, "delta": delta, "sigma": sigma,
        "tail_alpha": tail_alpha, "trials": n_trials,
        "pass_count": k, "pass_rate": k / n_trials,
        "pass_wilson_lb": wilson_lower(k, n_trials),
        "fail_count": int(failed.sum()),
        "unresolved_count": int((~passed & ~failed).sum()),
        "pass_by_look": {str(look): int((pass_look == look).sum())
                         for look in schedule},
    }


def simulate_router_power(mixture: str, effect: float, sigma: float,
                          n_trials: int = POWER_TRIALS,
                          seed_override: int | None = None
                          ) -> dict[str, Any]:
    """One aggregate-router grid cell: the fixed first-100-per-cell
    support with equal-cell weighting (never pooled as one N), a single
    terminal test at one-sided 0.025, pass iff LCB > 0. No
    point-materiality rule applies to Delta_router (132_s §9)."""
    n_cells = ROUTER_MIXTURES[mixture]
    a, p_b = two_point_distribution(effect, sigma)
    z = float(_norm.ppf(1.0 - ROUTER_ALPHA))
    if seed_override is not None:
        rng = np.random.Generator(np.random.PCG64(seed_override))
    else:
        rng = _rng(f"A-router|{mixture}|{effect}|{sigma}|{n_trials}")
    draws = np.where(
        rng.random((n_trials, n_cells, ROUTER_SUPPORT_PER_CELL)) < p_b,
        1.0, a)
    cell_means = draws.mean(axis=2)
    cell_vars = draws.var(axis=2, ddof=1)
    agg = cell_means.mean(axis=1)
    se = np.sqrt(cell_vars.sum(axis=1) / ROUTER_SUPPORT_PER_CELL) / n_cells
    k = int((agg - z * se > 0).sum())
    return {
        "mixture": mixture, "effect": effect, "sigma": sigma,
        "trials": n_trials, "pass_count": k, "pass_rate": k / n_trials,
        "pass_wilson_lb": wilson_lower(k, n_trials),
    }


# --- C. persistence-envelope feasibility -----------------------------------------

# The frozen §8.4C grid. m = 3: renderer-crossed rows per latent cluster
# for one directed edge (the persistence gate is per edge and never
# pools edges, 7.1).
PERSISTENCE_M = 3
PERSISTENCE_ELIGIBILITY = (0.60, 0.65, 0.80, 1.00)
PERSISTENCE_THETAS = (0.0, 0.05, 0.10)
PERSISTENCE_TRIALS = 10_000
PERSISTENCE_GATE = stage1.GATE_THRESHOLDS["old_answer_persistence_ucb_max"]
# (schedule id, N at each registered look, terminal tail alpha)
PERSISTENCE_LOOKS = {
    "ordinary": {"looks": stage1.ORDINARY_LOOK_SCHEDULE,
                 "tail_alpha": 0.05 / 3},
    "fork": {"looks": stage1.FORK_LOOK_SCHEDULE,
             "tail_alpha": 0.05 / 2},
}
# hard criteria (132_s §8.4C) at the relevant terminal caps
PERSISTENCE_FLOORS = {"fork": 0.60, "ordinary": 0.65}
PERSISTENCE_POWER_THETA = 0.05
PERSISTENCE_POWER_WILSON_LB = 0.80


def simulate_persistence_envelope(schedule: str, n_clusters: int,
                                  eligibility: float, theta: float,
                                  dist: str,
                                  n_trials: int = PERSISTENCE_TRIALS
                                  ) -> dict[str, Any]:
    """One §8.4C grid cell under one of the two frozen joint
    distributions for (K_c, J_c). Frozen seeds randomize which clusters
    receive each state; the statistic depends on the counts. Both
    constructions target primary estimand E[J]/E[K] = theta."""
    if dist not in ("cluster_correlated", "row_dispersed"):
        raise ValueError(f"unknown distribution {dist!r}")
    tail_alpha = PERSISTENCE_LOOKS[schedule]["tail_alpha"]
    structural = eligibility >= 1.0
    rng = _rng(f"C|{schedule}|{n_clusters}|{eligibility}|{theta}|{dist}"
               f"|{n_trials}")
    m = PERSISTENCE_M
    if dist == "cluster_correlated":
        n_elig = int(round(eligibility * n_clusters))
        mean_q = n_elig / n_clusters
        # J_c = K_c with probability theta on eligible clusters
        k_any = rng.binomial(n_elig, theta, size=n_trials)
    else:
        total_rows = int(round(eligibility * n_clusters * m))
        base, extra = divmod(total_rows, n_clusters)
        k_rows = np.full(n_clusters, base)
        k_rows[:extra] += 1
        mean_q = total_rows / (n_clusters * m)
        # every eligible row persists independently with prob theta;
        # A_c = 1[J_c > 0]; clusters with K_c = 0 can never fire
        p_any = 1.0 - (1.0 - theta) ** k_rows
        k_any = (rng.random((n_trials, n_clusters))
                 < p_any[None, :]).sum(axis=1)
    bounds = np.empty(n_trials)
    resolved = np.empty(n_trials, dtype=bool)
    for i, k in enumerate(k_any):
        bounds[i], resolved[i] = persistence_envelope(
            int(k), n_clusters, mean_q, tail_alpha,
            structural_full_eligibility=structural)
    # non-strict upper-bound gate: pass iff bound <= 10% (and resolved)
    passes = resolved & (bounds <= PERSISTENCE_GATE)
    k_pass = int(passes.sum())
    return {
        "schedule": schedule, "n_clusters": n_clusters,
        "eligibility": eligibility, "theta": theta, "dist": dist,
        "trials": n_trials, "tail_alpha": tail_alpha,
        "pass_count": k_pass, "pass_rate": k_pass / n_trials,
        "pass_wilson_lb": wilson_lower(k_pass, n_trials),
        "unresolved_count": int((~resolved).sum()),
        "median_bound": float(np.median(
            np.where(np.isfinite(bounds), bounds, 1.0))),
    }


# --- D. coverage battery primitives ------------------------------------------------

COVERAGE_OUTER_TRIALS = 5_000
# 158_s §6 (amend-once, Unit C): 10,000 production replicates are the
# ONLY bootstrap inner count; the 2,000-replicate approximation and
# its agreement authorization are removed together. The v1 constants
# and gate live in the archived worktree (da8424b) only.
COVERAGE_PRODUCTION_REPLICATES = stage1.BOOTSTRAP_REPLICATES  # 10,000
COVERAGE_SCENARIO_CAP = 8


def coverage_alpha_ceiling(allocated_operational_alpha: float) -> float:
    """132_s §8.4D acceptance ceiling on the 95% Wilson upper bound of
    the operational error rate."""
    return allocated_operational_alpha + max(
        0.005, 0.25 * allocated_operational_alpha)


_GATE_KINDS = ("lower_bound", "upper_bound", "equivalence")


def paired_cluster_bootstrap(rows_by_cell: list[np.ndarray],
                             tail_alpha: float, replicates: int,
                             seed: int, gate: str = "lower_bound"
                             ) -> tuple[float, float]:
    """The production §8.3 construction in miniature, for the coverage
    battery: independently resample N_c latent ids WITHIN each cell,
    CARRYING every renderer row of a resampled cluster (rows are
    (clusters, renderers) matrices — renderer-coupled by construction),
    collapse renderer-within-cluster, equal-cell average, percentile
    endpoints via linear quantiles at tail_alpha and 1 - tail_alpha.

    Eligibility: NaN entries are ineligible rows. A cluster whose rows
    are all ineligible stays in the sampling population (§8.3) but
    carries no eligible observations; a REPLICATE with zero eligible
    observations overall is undefined and receives the gate-adverse
    extreme (145_s finding 5): -inf for a lower-bound gate, +inf for an
    upper-bound gate, and the adverse endpoint ON EACH SIDE for
    equivalence (the replicate enters the lower endpoint as -inf and
    the upper endpoint as +inf)."""
    if gate not in _GATE_KINDS:
        raise ValueError(f"unknown gate kind {gate!r}")
    rng = np.random.Generator(np.random.PCG64(seed))
    cluster_means = []
    for cell in rows_by_cell:
        if cell.ndim != 2:
            raise ValueError("each cell must be a (clusters, renderers) "
                             "matrix — renderer rows travel with their "
                             "cluster")
        if cell.shape[0]:
            finite = ~np.isnan(cell)
            counts = finite.sum(axis=1)
            sums = np.where(finite, cell, 0.0).sum(axis=1)
            means = np.where(counts > 0,
                             sums / np.maximum(counts, 1), np.nan)
        else:
            means = np.empty(0)
        cluster_means.append(means)
    values = np.empty(replicates)
    adverse = np.zeros(replicates, dtype=bool)
    for r in range(replicates):
        cell_vals = []
        for means in cluster_means:
            n = len(means)
            if n == 0:
                cell_vals = None
                break
            picked = means[rng.integers(0, n, size=n)]
            eligible = picked[~np.isnan(picked)]
            if len(eligible) == 0:
                cell_vals = None
                break
            cell_vals.append(eligible.mean())
        if cell_vals is None:
            adverse[r] = True
            values[r] = 0.0  # placeholder; replaced per endpoint below
        else:
            values[r] = float(np.mean(cell_vals))
    if gate == "lower_bound":
        lo_vals = np.where(adverse, -np.inf, values)
        hi_vals = lo_vals
    elif gate == "upper_bound":
        lo_vals = np.where(adverse, np.inf, values)
        hi_vals = lo_vals
    else:  # equivalence: adverse endpoint on each side
        lo_vals = np.where(adverse, -np.inf, values)
        hi_vals = np.where(adverse, np.inf, values)
    return (_linear_quantile(lo_vals, tail_alpha),
            _linear_quantile(hi_vals, 1.0 - tail_alpha))


def _linear_quantile(values: np.ndarray, q: float) -> float:
    """numpy.quantile(method='linear') semantics, extended so an
    adverse +/-inf replicate propagates to the endpoint instead of
    producing NaN during interpolation (§8.3: adverse replicates are
    counted, never redrawn)."""
    s = np.sort(values)
    h = (len(s) - 1) * q
    lo, hi = int(np.floor(h)), int(np.ceil(h))
    a, b = float(s[lo]), float(s[hi])
    if not np.isfinite(a):
        return a
    if not np.isfinite(b):
        return b if h > lo else a
    return a + (h - lo) * (b - a)


def sequential_stake_decision(rows_by_cell: list[np.ndarray],
                              looks: tuple[int, ...], tail_alpha: float,
                              replicates: int, seed: int,
                              point_min: float = POINT_MATERIALITY
                              ) -> str:
    """The production stake trichotomy over registered looks, using the
    bootstrap intervals on immutable cluster prefixes: pass on
    (point >= point_min AND LCB > 0); conclusive fail on UCB < 0; else
    expand; unresolved at cap. Look k uses seed+k (frozen)."""
    for k, look in enumerate(looks):
        prefix = [cell[:min(look, cell.shape[0])]
                  for cell in rows_by_cell]
        point = point_estimate(prefix)
        if point is None:
            # zero eligible observations at this look: undefined — the
            # adverse bootstrap endpoints must not fire either branch
            # (151_s finding 3); expand, and unresolved at cap stays
            # unresolved
            continue
        lcb, ucb = paired_cluster_bootstrap(prefix, tail_alpha,
                                            replicates, seed + k)
        if point >= point_min and lcb > 0:
            return "pass"
        if ucb < 0:
            return "fail"
    return "unresolved"


def point_estimate(rows_by_cell: list[np.ndarray]) -> float | None:
    """The SAME eligible-cluster, equal-cell statistic the bootstrap
    resamples (148_s smaller correction): NaN rows are ineligible;
    cluster value = mean of its eligible rows; cell value = mean over
    clusters with eligible rows; equal-cell mean. None when any cell
    has zero eligible observations — the gate stays unresolved rather
    than a NaN point silently comparing false."""
    cell_vals = []
    for cell in rows_by_cell:
        if cell.shape[0] == 0:
            return None
        finite = ~np.isnan(cell)
        counts = finite.sum(axis=1)
        if not counts.any():
            return None
        sums = np.where(finite, cell, 0.0).sum(axis=1)
        means = sums[counts > 0] / counts[counts > 0]
        cell_vals.append(float(means.mean()))
    return float(np.mean(cell_vals))


def sequential_equivalence_decision(rows_by_cell: list[np.ndarray],
                                    looks: tuple[int, ...],
                                    look_tail_alpha: float,
                                    replicates: int, seed: int,
                                    band: float = 0.10) -> str:
    """§8.2 equivalence over registered looks: the two-sided interval
    splits the one-look tail alpha across both tails."""
    for k, look in enumerate(looks):
        prefix = [cell[:min(look, cell.shape[0])]
                  for cell in rows_by_cell]
        lcb, ucb = paired_cluster_bootstrap(prefix, look_tail_alpha / 2.0,
                                            replicates, seed + k,
                                            gate="equivalence")
        decision = equivalence_decision(lcb, ucb, band)
        if decision != "inconclusive":
            return decision
    return "unresolved"


def benchmark_worst_case(outer_trials: int = 20) -> dict[str, Any]:
    """The §5.4 item-3 timing probe (NON-frozen throwaway seed,
    statistical output discarded): the ACTUAL worst-case D path — the
    ordinary 3-look sequential null at 5 cells x 500 clusters x 3
    renderers with the full 10,000 production inner replicates per
    look. The measured per-outer literal feeds the frozen D1-D5
    deadlines (4 x measured x 5,000)."""
    rng = np.random.Generator(np.random.PCG64(0xDEADBEEF))  # throwaway
    cells = [rng.normal(0.0, 0.5, size=(500, 3)) for _ in range(5)]
    t0 = time.perf_counter()
    for i in range(outer_trials):
        sequential_stake_decision(cells, (100, 300, 500), 0.05 / 9,
                                  COVERAGE_PRODUCTION_REPLICATES, seed=i)
    elapsed = time.perf_counter() - t0
    per_trial = elapsed / outer_trials
    return {
        "outer_trials_timed": outer_trials,
        "seconds_per_outer_trial": per_trial,
        "projected_one_scenario_hours":
            per_trial * COVERAGE_OUTER_TRIALS / 3600.0,
        "projected_full_battery_hours":
            per_trial * COVERAGE_OUTER_TRIALS * COVERAGE_SCENARIO_CAP
            / 3600.0,
    }
