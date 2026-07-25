"""Amended persistence statistic and coupled-path C machinery — 158_s
§§4-5 (Unit B).

Implements, exactly as frozen by 158_s and the Unit-A contract:

- the branch-safe cluster-score/Fieller interval for the full
  eligible-row ratio (§4.2/§4.5): `D_c(r) = J_c - r K_c`, Student-t
  bounds on the mean score, a fail-closed Fieller denominator check,
  the optimized integer-sufficient-statistic evaluation in the frozen
  float64 order with the frozen tolerance clamps;
- the zero-event safeguard inside its preallocated `a_zero` budget
  (§4.4), triggered exactly by `J == 0`;
- the §4.6 gate rule and per-look serialization records;
- the reporting inversion over `r in [0, 1]` (§4.5): deterministic
  grid-contiguity verification (refuses rather than selecting a
  component), outward bracket/bisection with 80 float64 iterations,
  inclusive membership, conservative outer-bracket endpoints;
- prefix-valid coupled-path generators for both frozen joint
  distributions (§5.2): incremental randomized blocks meeting every
  cumulative eligibility target exactly, nested by look;
- the 48-path/120-marginal C runner (NOT executed in Unit B), its
  artifact build/load with EXACT key-set enforcement (163_s), and the
  §5.3 hard-path acceptance evaluator;
- the scalar row-level reference implementation and the disclosed
  timing/reference probes (§5.4 items 1-2).

Nothing in this module runs a frozen grid; the amended C executes only
after the final successor is locked.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
from scipy.stats import t as _student_t

from . import stage1_amend1 as am
from . import stage1_validation as sv
from .types import InfrastructureError

_EPS64 = float(np.finfo(np.float64).eps)
M = sv.PERSISTENCE_M                      # 3 renderer rows per cluster
R = am.PERSISTENCE_BOUNDARY_R             # 0.10


# --- sufficient statistics -------------------------------------------------------

@dataclass(frozen=True)
class SuffStats:
    """Integer sufficient statistics over N clusters (§4.5)."""
    n: int
    s_j: int
    s_k: int
    s_j2: int
    s_k2: int
    s_jk: int


def validate_cluster_rows(j_rows: np.ndarray, k_rows: np.ndarray) -> None:
    """§5.2: validate the (J_c, K_c) support — integers,
    0 <= J_c <= K_c <= m; zero-eligible clusters are legal and REMAIN
    in the population."""
    if j_rows.shape != k_rows.shape or j_rows.ndim != 1:
        raise InfrastructureError("J/K must be equal-length 1-D arrays")
    if not (np.issubdtype(j_rows.dtype, np.integer)
            and np.issubdtype(k_rows.dtype, np.integer)):
        raise InfrastructureError("J/K must be integer arrays")
    if np.any(k_rows < 0) or np.any(k_rows > M):
        raise InfrastructureError(f"K_c outside [0, {M}]")
    if np.any(j_rows < 0) or np.any(j_rows > k_rows):
        raise InfrastructureError("J_c outside [0, K_c]")


def suff_stats(j_rows: np.ndarray, k_rows: np.ndarray) -> SuffStats:
    validate_cluster_rows(j_rows, k_rows)
    j = j_rows.astype(np.int64)
    k = k_rows.astype(np.int64)
    return SuffStats(n=int(len(j)), s_j=int(j.sum()), s_k=int(k.sum()),
                     s_j2=int((j * j).sum()), s_k2=int((k * k).sum()),
                     s_jk=int((j * k).sum()))


def _clamped_variance(v: float, magnitude_a: float,
                      magnitude_b: float, what: str) -> float:
    """§4.5 tolerance clamp: tol = 64*eps64*max(1, |a|, |b|); clamp to
    zero only within [-tol, 0); more negative or non-finite is an
    infrastructure error."""
    tol = am.TOLERANCE_FACTOR * _EPS64 * max(1.0, abs(magnitude_a),
                                             abs(magnitude_b))
    if not np.isfinite(v):
        raise InfrastructureError(f"non-finite {what} variance")
    if v < -tol:
        raise InfrastructureError(
            f"{what} variance {v!r} below -tolerance {-tol!r}")
    return 0.0 if v < 0.0 else v


def score_components(stats: SuffStats, r: float,
                     a_ratio: float) -> dict[str, float]:
    """The §4.5 positive-branch computation in EXACTLY the frozen
    float64 evaluation order. Returns every intermediate the record
    serializes; decisions derive from (g_l, g_u, denominator_l)."""
    n = stats.n
    if n < 2:
        raise InfrastructureError("positive branch needs N >= 2")
    s_d = np.float64(stats.s_j) - np.float64(r) * np.float64(stats.s_k)
    s_d2 = (np.float64(stats.s_j2)
            - 2.0 * np.float64(r) * np.float64(stats.s_jk)
            + np.float64(r) * np.float64(r) * np.float64(stats.s_k2))
    v_d = s_d2 - s_d * s_d / np.float64(n)
    v_d = _clamped_variance(float(v_d), float(s_d2),
                            float(s_d * s_d / np.float64(n)), "score")
    s_d_sq = v_d / np.float64(n - 1)
    s_d_sd = float(np.sqrt(s_d_sq))
    dbar = float(s_d / np.float64(n))
    q = float(_student_t.ppf(1.0 - a_ratio, df=n - 1))
    v_k = (np.float64(stats.s_k2)
           - np.float64(stats.s_k) * np.float64(stats.s_k)
           / np.float64(n))
    v_k = _clamped_variance(float(v_k), float(stats.s_k2),
                            float(np.float64(stats.s_k) ** 2
                                  / np.float64(n)), "eligibility")
    s_k_sd = float(np.sqrt(v_k / np.float64(n - 1)))
    mean_k = float(np.float64(stats.s_k) / np.float64(n))
    denominator_l = mean_k - q * s_k_sd / float(np.sqrt(n))
    half = q * s_d_sd / float(np.sqrt(n))
    return {"dbar": dbar, "s_d": s_d_sd, "q": q, "mean_k": mean_k,
            "s_k": s_k_sd, "denominator_l": denominator_l,
            "g_l": dbar - half, "g_u": dbar + half}


def zero_branch_bound(n: int, sum_a: int, qbar: float, a_zero: float,
                      structural: bool) -> dict[str, Any]:
    """§4.4 zero-event branch inside the preallocated a_zero budget."""
    if structural:
        u = sv.clopper_pearson_upper(sum_a, n, a_zero)
        return {"U": u, "U_A": None, "L_Q": None, "resolved": True}
    u_a = sv.clopper_pearson_upper(sum_a, n, a_zero / 2.0)
    l_q = max(0.0, qbar - float(np.sqrt(np.log(2.0 / a_zero)
                                        / (2.0 * n))))
    if l_q <= 0.0:
        return {"U": float("inf"), "U_A": u_a, "L_Q": l_q,
                "resolved": False}
    return {"U": min(1.0, u_a / l_q), "U_A": u_a, "L_Q": l_q,
            "resolved": True}


def look_decision(j_rows: np.ndarray, k_rows: np.ndarray,
                  schedule: str, *,
                  with_inversion: bool = True) -> dict[str, Any]:
    """One registered look: branch selection (trigger EXACTLY J == 0),
    the §4.6 gate rule, and the full §4 serialization record with the
    frozen per-branch field sets."""
    stats = suff_stats(j_rows, k_rows)
    a, a_zero, a_ratio = am.persistence_tail_allocation(schedule)
    n = stats.n
    k_total, j_total = stats.s_k, stats.s_j
    sum_a = int(np.count_nonzero(j_rows > 0))
    structural = bool(np.all(k_rows == M))
    base = {
        "N": n, "m": M, "K": k_total, "J": j_total,
        "Qbar_num": k_total, "Qbar_den": M * n, "sum_A": sum_a,
        "p_hat_num": j_total, "p_hat_den": k_total,
        "tail_a": repr(a), "tail_a_zero": repr(a_zero),
        "tail_a_ratio": repr(a_ratio),
    }
    if k_total == 0:
        # observed K = 0: unresolved, cell cannot be admitted (§4.1)
        return {**base, "branch": "zero", "denominator_check": "n/a",
                "decision": "unresolved", "zero_U": "inf",
                "zero_U_A": "n/a", "zero_L_Q": "n/a"}
    if j_total == 0:
        qbar = k_total / (M * n)
        zb = zero_branch_bound(n, sum_a, qbar, a_zero, structural)
        decision = "pass" if (zb["resolved"] and zb["U"] <= R) \
            else "unresolved"                # never fail from J = 0
        return {**base, "branch": "zero", "denominator_check": "n/a",
                "decision": decision, "zero_U": repr(zb["U"]),
                "zero_U_A": "n/a" if zb["U_A"] is None
                            else repr(zb["U_A"]),
                "zero_L_Q": "n/a" if zb["L_Q"] is None
                            else repr(zb["L_Q"])}
    comp = score_components(stats, R, a_ratio)
    if comp["denominator_l"] <= 0.0:
        return {**base, "branch": "positive",
                "denominator_check": "unresolved",
                "decision": "unresolved",
                "pos_G_L": repr(comp["g_l"]),
                "pos_G_U": repr(comp["g_u"]),
                "pos_L_p": "0", "pos_U_p": "1"}
    if comp["g_u"] <= 0.0:
        decision = "pass"
    elif comp["g_l"] > 0.0:
        decision = "fail"
    else:
        decision = "unresolved"
    if with_inversion:
        l_p, u_p = invert_ratio_interval(stats, a_ratio)
        l_p_s, u_p_s = repr(l_p), repr(u_p)
    else:
        # C-path counting consumes decisions/branches only; the
        # reporting interval is computed where records persist
        # (qualification, D6-D8)
        l_p_s = u_p_s = "n/a"
    return {**base, "branch": "positive", "denominator_check": "ok",
            "decision": decision, "pos_G_L": repr(comp["g_l"]),
            "pos_G_U": repr(comp["g_u"]), "pos_L_p": l_p_s,
            "pos_U_p": u_p_s}


# --- §4.5 reporting inversion -------------------------------------------------------

_GRID = np.linspace(0.0, 1.0, 1_001)


def _membership(stats: SuffStats, r_values: np.ndarray,
                a_ratio: float) -> np.ndarray:
    """G_L(r) <= 0 <= G_U(r), vectorized over candidate r (inclusive
    membership). Equivalent to |Dbar(r)| <= q*s_D(r)/sqrt(N)."""
    n = np.float64(stats.n)
    r = r_values.astype(np.float64)
    s_d = np.float64(stats.s_j) - r * np.float64(stats.s_k)
    s_d2 = (np.float64(stats.s_j2) - 2.0 * r * np.float64(stats.s_jk)
            + r * r * np.float64(stats.s_k2))
    v_d = np.maximum(s_d2 - s_d * s_d / n, 0.0)
    s_sd = np.sqrt(v_d / (n - 1.0))
    q = float(_student_t.ppf(1.0 - a_ratio, df=stats.n - 1))
    dbar = s_d / n
    half = q * s_sd / np.sqrt(n)
    return np.abs(dbar) <= half


def invert_ratio_interval(stats: SuffStats,
                          a_ratio: float) -> tuple[float, float]:
    """The reporting interval [L_p, U_p] = the closure bounds of
    C = {r in [0,1]: G_L(r) <= 0 <= G_U(r)} (§4.5).

    Deterministic verification first: on the fixed 1,001-point grid,
    members must form ONE contiguous run containing p_hat — otherwise
    the implementation REFUSES rather than selecting a component. Then
    outward bracket/bisection from p_hat with exactly 80 float64
    iterations per side, inclusive membership, and conservative
    OUTER-bracket endpoints (0/1 where the set reaches the boundary)."""
    if stats.s_k <= 0:
        raise InfrastructureError("inversion requires K > 0")
    p_hat = stats.s_j / stats.s_k
    # The verification grid is AUGMENTED with p_hat: a perfectly
    # homogeneous sample has s_D(r) = 0 for every r, making C the
    # single point {p_hat}, which a fixed grid misses (s_D = 0 is
    # explicitly valid, 158_s §4.5). Contiguity is required on the
    # augmented, sorted grid and the run must contain p_hat.
    grid = np.sort(np.append(_GRID, np.float64(p_hat)))
    member = _membership(stats, grid, a_ratio)
    idx = np.flatnonzero(member)
    if len(idx) == 0:
        raise InfrastructureError(
            "inversion grid found no members — C must contain p_hat")
    runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    if len(runs) != 1:
        raise InfrastructureError(
            "membership set is not a single interval on the frozen "
            "grid — refusing rather than selecting a component (§4.5)")
    p_hat_idx = int(np.searchsorted(grid, np.float64(p_hat)))
    if not (idx[0] <= p_hat_idx <= idx[-1]):
        raise InfrastructureError(
            "the membership run does not contain p_hat — invariant "
            "violation")

    def is_member(r: float) -> bool:
        return bool(_membership(stats, np.array([r]), a_ratio)[0])

    if not is_member(p_hat):
        raise InfrastructureError("p_hat is not a member — invariant "
                                  "violation")

    def bisect(inside: float, outside: float) -> float:
        # returns the OUTER bracket end after 80 iterations
        for _ in range(am.BISECTION_ITERATIONS):
            mid = (inside + outside) / 2.0
            if is_member(mid):
                inside = mid
            else:
                outside = mid
        return outside

    l_p = 0.0 if is_member(0.0) else bisect(p_hat, 0.0)
    u_p = 1.0 if is_member(1.0) else bisect(p_hat, 1.0)
    return float(l_p), float(u_p)


# --- §5.2 prefix-valid coupled-path generators ---------------------------------------

def _nested_eligible_mask(rng: np.random.Generator,
                          looks: tuple[int, ...],
                          eligibility: float) -> np.ndarray:
    """Cluster-correlated eligibility: each look prefix has EXACTLY
    round(e * N_look) fully eligible clusters, built from independently
    randomized incremental blocks (never a cap arrangement hoped to
    land on the floor; never independent looks)."""
    cap = looks[-1]
    mask = np.zeros(cap, dtype=bool)
    prev_n, prev_e = 0, 0
    for look in looks:
        target = int(round(eligibility * look))
        block = np.arange(prev_n, look)
        need = target - prev_e
        if need < 0 or need > len(block):
            raise InfrastructureError("infeasible eligibility block")
        chosen = rng.permutation(block)[:need]
        mask[chosen] = True
        prev_n, prev_e = look, target
    return mask


def gen_cluster_correlated(rng: np.random.Generator,
                           looks: tuple[int, ...], eligibility: float,
                           theta: float) -> tuple[np.ndarray, np.ndarray]:
    """K_c = m on eligible clusters (0 otherwise); J_c = m with
    probability theta on eligible clusters — ONE Bernoulli per
    cluster."""
    mask = _nested_eligible_mask(rng, looks, eligibility)
    k = np.where(mask, M, 0).astype(np.int64)
    fire = rng.random(looks[-1]) < theta
    j = np.where(mask & fire, M, 0).astype(np.int64)
    return j, k


def gen_row_dispersed(rng: np.random.Generator, looks: tuple[int, ...],
                      eligibility: float, theta: float
                      ) -> tuple[np.ndarray, np.ndarray]:
    """Each look prefix has EXACTLY round(e * m * N_look) eligible rows
    distributed as evenly as possible over its incremental block's
    clusters (randomized remainder); J_c ~ Binomial(K_c, theta) —
    row-level persistence."""
    cap = looks[-1]
    k = np.zeros(cap, dtype=np.int64)
    prev_n, prev_rows = 0, 0
    for look in looks:
        target_rows = int(round(eligibility * M * look))
        block_n = look - prev_n
        need = target_rows - prev_rows
        if need < 0 or need > M * block_n:
            raise InfrastructureError("infeasible row block")
        base, extra = divmod(need, block_n)
        block_k = np.full(block_n, base, dtype=np.int64)
        bump = rng.permutation(block_n)[:extra]
        block_k[bump] += 1
        k[prev_n:look] = block_k
        prev_n, prev_rows = look, target_rows
    j = rng.binomial(k, theta).astype(np.int64)
    return j, k


def generate_path(schedule: str, eligibility: float, theta: float,
                  dist: str, trial_seed: int
                  ) -> tuple[np.ndarray, np.ndarray]:
    looks = sv.PERSISTENCE_LOOKS[schedule]["looks"]
    rng = np.random.Generator(np.random.PCG64(trial_seed))
    if dist == "cluster_correlated":
        return gen_cluster_correlated(rng, looks, eligibility, theta)
    if dist == "row_dispersed":
        return gen_row_dispersed(rng, looks, eligibility, theta)
    raise InfrastructureError(f"unknown distribution {dist!r}")


# --- coupled-path evaluation -----------------------------------------------------------

def evaluate_path(j: np.ndarray, k: np.ndarray, schedule: str
                  ) -> dict[str, Any]:
    """Apply §4.6 to the immutable prefixes in look order: first
    terminal decision stops the operational path (early fail stops;
    pass stops; unresolved expands; unresolved at cap = non-pass).
    Marginal decisions at every look are computed from the SAME coupled
    prefixes as telemetry."""
    looks = sv.PERSISTENCE_LOOKS[schedule]["looks"]
    marginals: dict[int, dict[str, Any]] = {}
    outcome, decided_at = "cap_unresolved", None
    for look in looks:
        record = look_decision(j[:look], k[:look], schedule,
                               with_inversion=False)
        marginals[look] = record
        if decided_at is None and record["decision"] == "pass":
            outcome, decided_at = "first_pass", look
        elif decided_at is None and record["decision"] == "fail":
            outcome, decided_at = "first_fail", look
    return {"outcome": outcome, "decided_at": decided_at,
            "marginals": marginals}


def run_c_path(schedule: str, eligibility: float, theta: float,
               dist: str, n_trials: int = am.C_OUTER_TRIALS,
               _seed_domain: str = am.AC_SEED_DOMAIN
               ) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    """One coupled path cell: n_trials fresh-seed maximum-cap paths
    under the FRESH A/C domain (§9.3), returning the C_path row and its
    per-look C_marginal rows (integer sufficient statistics only).
    `_seed_domain` exists ONLY for the throwaway timing probe — the
    frozen grid always runs under the default domain."""
    path_key = am.c_path_key(schedule, eligibility, theta, dist)
    looks = sv.PERSISTENCE_LOOKS[schedule]["looks"]
    counts = {"first_pass": 0, "first_fail": 0, "cap_unresolved": 0}
    marg = {look: {"pass_count": 0, "fail_count": 0,
                   "unresolved_count": 0, "zero_branch": 0,
                   "positive_branch": 0, "denominator_unresolved": 0}
            for look in looks}
    for trial in range(n_trials):
        # per-trial stream: frozen derivation over (path key, trial)
        trial_seed = am.seed(_seed_domain, f"{path_key}|{trial}")
        j, k = generate_path(schedule, eligibility, theta, dist,
                             trial_seed)
        result = evaluate_path(j, k, schedule)
        counts[result["outcome"]] += 1
        for look, record in result["marginals"].items():
            row = marg[look]
            if record["decision"] == "pass":
                row["pass_count"] += 1
            elif record["decision"] == "fail":
                row["fail_count"] += 1
            else:
                row["unresolved_count"] += 1
            if record["branch"] == "zero":
                row["zero_branch"] += 1
            else:
                row["positive_branch"] += 1
                if record["denominator_check"] == "unresolved":
                    row["denominator_unresolved"] += 1
    path_row = {**counts, "trials": n_trials}
    marginal_rows = {f"{path_key}|look{look}": {**marg[look],
                                                "trials": n_trials}
                     for look in looks}
    return path_row, marginal_rows


# --- §5.3 hard-path acceptance -----------------------------------------------------------

HARD_PATHS = (("ordinary", 0.65), ("fork", 0.60))


def hard_path_acceptance(path_rows: Mapping[str, Mapping[str, int]]
                         ) -> dict[str, Any]:
    """The frozen §5.3 criteria over completed path rows. theta=0.10
    rows are mandatory non-gating disclosures."""
    failures = []
    for schedule, eligibility in HARD_PATHS:
        for dist in ("cluster_correlated", "row_dispersed"):
            zero_key = am.c_path_key(schedule, eligibility, 0.0, dist)
            row = path_rows[zero_key]
            if row["first_pass"] != row["trials"]:
                failures.append(f"{zero_key}: theta=0 must first-pass "
                                "every trial")
            pow_key = am.c_path_key(schedule, eligibility, 0.05, dist)
            row = path_rows[pow_key]
            lb = sv.wilson_lower(row["first_pass"], row["trials"])
            if lb < 0.80:
                failures.append(
                    f"{pow_key}: Wilson LB {lb:.4f} < 0.80")
    return {"failures": failures, "passes": not failures}


# --- artifact build/load with exact key sets (163_s) ---------------------------------------

def build_c_artifact(execution_bundle_sha256: str,
                     path_rows: Mapping[str, Mapping[str, int]],
                     marginal_rows: Mapping[str, Mapping[str, int]]
                     ) -> dict[str, Any]:
    from .stage1_tranche import finalize_artifact
    am.validate_amend1_rows("C_path", path_rows)
    am.validate_amend1_rows("C_marginal", marginal_rows)
    expected_paths = {am.c_path_key(*cell) for cell in am.c_path_cells()}
    if set(path_rows) != expected_paths:
        raise InfrastructureError("C path rows != the exact 48-key set")
    if set(marginal_rows) != am.c_marginal_keys():
        raise InfrastructureError(
            "C marginal rows != the exact 120-key set")
    return finalize_artifact(
        "C", execution_bundle_sha256, path_rows,
        extra={"marginals": {k: dict(v)
                             for k, v in sorted(marginal_rows.items())}},
        tag=am.AMEND1_ARTIFACT_TAG,
        row_schema=am.AMEND1_ROW_SCHEMAS["C_path"])


def load_amended_c_artifact(artifact: Mapping[str, Any],
                            execution_bundle_sha256: str
                            ) -> dict[str, Any]:
    """Fail-closed amended-C loader: amend1 tag, exact 48-path key set
    via the tranche loader, then the exact 120-marginal key set and
    schema (163_s: enforced at the loader, not by convention)."""
    from .stage1_tranche import load_artifact
    expected_paths = frozenset(am.c_path_key(*cell)
                               for cell in am.c_path_cells())
    loaded = load_artifact(artifact, "C", expected_paths,
                           execution_bundle_sha256,
                           tag=am.AMEND1_ARTIFACT_TAG,
                           row_schema=am.AMEND1_ROW_SCHEMAS["C_path"])
    marginals = loaded.get("marginals")
    if marginals is None:
        raise InfrastructureError("amended C artifact carries no "
                                  "marginals block")
    if set(marginals) != am.c_marginal_keys():
        raise InfrastructureError(
            "C marginal key set != the exact 120-key registry")
    am.validate_amend1_rows("C_marginal", marginals)
    return loaded


# --- §5.4 items 1-2: scalar reference and disclosed probes -----------------------

def scalar_reference_bounds(j_rows: np.ndarray, k_rows: np.ndarray,
                            r: float, a_ratio: float
                            ) -> dict[str, float]:
    """Row-level reference implementation: plain-Python two-pass mean/
    sample-sd over per-cluster scores. The optimized sufficient-
    statistic path must agree bit-for-bit on decisions and within
    ENDPOINT_ATOL (rtol = 0) on endpoints."""
    validate_cluster_rows(j_rows, k_rows)
    n = len(j_rows)
    scores = [float(j_rows[c]) - r * float(k_rows[c])
              for c in range(n)]
    dbar = sum(scores) / n
    var = sum((x - dbar) ** 2 for x in scores) / (n - 1)
    s_d = var ** 0.5
    ks = [float(k) for k in k_rows]
    kbar = sum(ks) / n
    kvar = sum((x - kbar) ** 2 for x in ks) / (n - 1)
    q = float(_student_t.ppf(1.0 - a_ratio, df=n - 1))
    half = q * s_d / (n ** 0.5)
    return {"dbar": dbar, "g_l": dbar - half, "g_u": dbar + half,
            "denominator_l": kbar - q * (kvar ** 0.5) / (n ** 0.5)}


def _decision_from(g_l: float, g_u: float, denominator_l: float) -> str:
    if denominator_l <= 0.0:
        return "unresolved"
    if g_u <= 0.0:
        return "pass"
    if g_l > 0.0:
        return "fail"
    return "unresolved"


def reference_agreement_probe(cases: list[tuple[np.ndarray, np.ndarray,
                                                str]]
                              ) -> dict[str, Any]:
    """Disclosed §5.4 item-1 probe over fixed throwaway cases: the
    optimized and scalar implementations must agree bit-for-bit on the
    trichotomy decision and within ENDPOINT_ATOL on (G_L, G_U,
    denominator_L). Raises on any disagreement."""
    checked = 0
    for j_rows, k_rows, schedule in cases:
        _, _, a_ratio = am.persistence_tail_allocation(schedule)
        stats = suff_stats(j_rows, k_rows)
        if stats.s_j == 0 or stats.s_k == 0:
            continue                       # positive-branch probe only
        fast = score_components(stats, R, a_ratio)
        ref = scalar_reference_bounds(j_rows, k_rows, R, a_ratio)
        if _decision_from(fast["g_l"], fast["g_u"],
                          fast["denominator_l"]) != \
                _decision_from(ref["g_l"], ref["g_u"],
                               ref["denominator_l"]):
            raise InfrastructureError("scalar/optimized DECISION "
                                      "disagreement")
        for field in ("g_l", "g_u", "denominator_l"):
            if abs(fast[field] - ref[field]) > am.ENDPOINT_ATOL:
                raise InfrastructureError(
                    f"scalar/optimized endpoint {field} disagreement "
                    f"{fast[field]!r} vs {ref[field]!r}")
        checked += 1
    if checked == 0:
        raise InfrastructureError("probe had no positive-branch cases")
    return {"cases_checked": checked}


_THROWAWAY_DOMAIN = "throwaway-timing-v1"    # never a frozen result


def benchmark_c_projection(trials_per_path: int = 50) -> dict[str, Any]:
    """Disclosed §5.4 item-2 probe: a conservative THROWAWAY timing
    projection of the complete 48-path C registry. Statistical outputs
    are discarded; seeds come from a throwaway domain so no frozen
    prefix is revealed."""
    worst = [("ordinary", 0.65, 0.05, "row_dispersed"),
             ("ordinary", 1.00, 0.10, "cluster_correlated"),
             ("fork", 0.60, 0.05, "row_dispersed")]
    started = time.perf_counter()
    for schedule, e, theta, dist in worst:
        run_c_path(schedule, e, theta, dist,
                   n_trials=trials_per_path,
                   _seed_domain=_THROWAWAY_DOMAIN)
    elapsed = time.perf_counter() - started
    per_trial = elapsed / (len(worst) * trials_per_path)
    projected_minutes = per_trial * 48 * am.C_OUTER_TRIALS / 60.0
    return {"seconds_per_path_trial": per_trial,
            "projected_full_c_minutes": projected_minutes,
            "budget_minutes": 30,
            "within_budget": projected_minutes <= 30.0}
