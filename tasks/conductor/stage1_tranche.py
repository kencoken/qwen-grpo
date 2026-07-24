"""§8.4 tranche runner — frozen grids, D registry, artifacts, verdict
(unit 3, completing the 141_f preregistration per 142_s).

Everything executable about the tranche lives here, frozen BEFORE any
output is revealed:

- exact grid enumerators and expected-key registries (48 A-position
  cells, 24 A-router cells, 120 C cells, 8 D scenarios, 1 B artifact);
- the frozen D scenario registry: DGPs, seeds, allocated operational
  alphas, truth, and error definitions;
- the agreement gate, which must run AND pass before the
  reduced-replicate battery;
- canonical, content-addressed artifacts holding INTEGER sufficient
  statistics only (every rate/bound is recomputed at load — floats are
  never persisted or hashed);
- one fail-closed A-D aggregator: missing, duplicate, extra, malformed,
  non-finite or wrong-size results refuse, and the overall verdict
  incorporates all four checks plus B.

The tranche runs only after 141_f (as completed here) is signed.
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Mapping

import numpy as np

from . import stage1_validation as sv
from .profiles import canonical_json

TRANCHE_ARTIFACT_TAG = "stage1-validation-v1"


class TrancheError(ValueError):
    """Fail-closed tranche registry/artifact/verdict error."""


# --- exact grid registries -----------------------------------------------------

def a_position_cells() -> tuple[tuple[str, float, float], ...]:
    """48 cells: 4 scenarios x 3 deltas x 4 sigmas, frozen order."""
    return tuple((scen, d, s)
                 for scen in sv.POSITION_SCENARIOS
                 for d in sv.POWER_DELTAS
                 for s in sv.POWER_SIGMAS)


def a_router_cells() -> tuple[tuple[str, float, float], ...]:
    """24 cells: 2 mixtures x 3 effects x 4 sigmas (0.75/0.95 are
    stress disclosures, gated cells are sigma <= 0.50)."""
    return tuple((mix, e, s)
                 for mix in sv.ROUTER_MIXTURES
                 for e in sv.ROUTER_EFFECTS
                 for s in sv.POWER_SIGMAS)


def c_cells() -> tuple[tuple[str, int, float, float, str], ...]:
    """120 cells: (ordinary looks 100/300/500 + fork looks 100/200) x
    4 eligibilities x 3 thetas x 2 distributions."""
    out = []
    for schedule, spec in sv.PERSISTENCE_LOOKS.items():
        for n in spec["looks"]:
            for e in sv.PERSISTENCE_ELIGIBILITY:
                for theta in sv.PERSISTENCE_THETAS:
                    for dist in ("cluster_correlated", "row_dispersed"):
                        out.append((schedule, n, e, theta, dist))
    return tuple(out)


def _a_key(scen: str, d: float, s: float) -> str:
    return f"A|{scen}|{d}|{s}|{sv.POWER_TRIALS}"


def _r_key(mix: str, e: float, s: float) -> str:
    return f"A-router|{mix}|{e}|{s}|{sv.POWER_TRIALS}"


def _c_key(schedule: str, n: int, e: float, theta: float,
           dist: str) -> str:
    return f"C|{schedule}|{n}|{e}|{theta}|{dist}|{sv.PERSISTENCE_TRIALS}"


def expected_result_keys() -> dict[str, frozenset[str]]:
    return {
        "A_position": frozenset(_a_key(*c) for c in a_position_cells()),
        "A_router": frozenset(_r_key(*c) for c in a_router_cells()),
        "C": frozenset(_c_key(*c) for c in c_cells()),
        "D": frozenset(s["id"] for s in D_SCENARIOS),
    }


# --- the frozen D scenario registry ------------------------------------------------

def _tp_rows(rng: np.random.Generator, delta: float, sigma: float,
             clusters: int, renderers: int = 3) -> np.ndarray:
    a, p_b = sv.two_point_distribution(delta, sigma)
    return np.where(rng.random((clusters, renderers)) < p_b, 1.0, a)


def _dgp_seq_null(schedule: tuple[int, ...], tail: float, cells: int,
                  sigma: float) -> Callable[[int], str]:
    def run(trial_seed: int) -> str:
        rng = np.random.Generator(np.random.PCG64(trial_seed))
        rows = [_tp_rows(rng, 0.0, sigma, schedule[-1])
                for _ in range(cells)]
        return sv.sequential_stake_decision(
            rows, schedule, tail, sv.COVERAGE_INNER_REPLICATES,
            seed=trial_seed ^ 0x5EED)
    return run


def _dgp_equiv_boundary(theta: float) -> Callable[[int], str]:
    looks, tail = (100, 300, 500), 0.05 / 3

    def run(trial_seed: int) -> str:
        rng = np.random.Generator(np.random.PCG64(trial_seed))
        rows = [_tp_rows(rng, abs(theta), 0.5, looks[-1])]
        if theta < 0:
            rows = [-r for r in rows]
        return sv.sequential_equivalence_decision(
            rows, looks, tail, sv.COVERAGE_INNER_REPLICATES,
            seed=trial_seed ^ 0x5EED)
    return run


def _dgp_pilot_hetero() -> Callable[[int], str]:
    # pilot aggregation: 6 heterogeneous cells at the null, UNEQUAL
    # cluster counts (one direction-starved cell), one-sided 0.05/2
    sigmas = (0.25, 0.40, 0.50, 0.60, 0.75, 0.90)
    counts = (12, 12, 12, 12, 12, 6)

    def run(trial_seed: int) -> str:
        rng = np.random.Generator(np.random.PCG64(trial_seed))
        rows = [_tp_rows(rng, 0.0, sg, n)
                for sg, n in zip(sigmas, counts)]
        lcb, _ = sv.paired_cluster_bootstrap(
            rows, 0.05 / 2, sv.COVERAGE_INNER_REPLICATES,
            seed=trial_seed ^ 0x5EED)
        return "pass" if lcb > 0 else "not_pass"
    return run


def _dgp_persistence(schedule: str, eligibility: float, theta: float
                     ) -> Callable[[int], str]:
    # exact CP/Hoeffding scenario — no bootstrap (132_s §8.4D); error is
    # UNDERCOVERAGE: the operational bound falling below the true row
    # rate at any registered look
    spec = sv.PERSISTENCE_LOOKS[schedule]
    looks, tail = spec["looks"], spec["tail_alpha"]
    structural = eligibility >= 1.0
    m = sv.PERSISTENCE_M

    def run(trial_seed: int) -> str:
        rng = np.random.Generator(np.random.PCG64(trial_seed))
        cap = looks[-1]
        n_elig_cap = int(round(eligibility * cap))
        eligible = np.zeros(cap, dtype=bool)
        eligible[rng.permutation(cap)[:n_elig_cap]] = True
        persists = rng.random((cap, m)) < theta
        for look in looks:
            k_any = int((eligible[:look]
                         & persists[:look].any(axis=1)).sum())
            mean_q = float(eligible[:look].mean())
            bound, resolved = sv.persistence_envelope(
                k_any, look, mean_q, tail,
                structural_full_eligibility=structural)
            if resolved and bound < theta:
                return "undercover"
        return "cover"
    return run


D_SCENARIOS: tuple[dict[str, Any], ...] = (
    {"id": "D1_seq_null_ordinary_div3",
     "dgp": _dgp_seq_null((100, 300, 500), 0.05 / 9, 5, 0.75),
     "error_decision": "pass", "allocated_alpha": 3 * 0.05 / 9},
    {"id": "D2_seq_null_fork_div3",
     "dgp": _dgp_seq_null((100, 200), 0.05 / 6, 1, 0.50),
     "error_decision": "pass", "allocated_alpha": 2 * 0.05 / 6},
    {"id": "D3_equiv_boundary_plus",
     "dgp": _dgp_equiv_boundary(+0.10),
     "error_decision": "pass", "allocated_alpha": 3 * 0.05 / 6},
    {"id": "D4_equiv_boundary_minus",
     "dgp": _dgp_equiv_boundary(-0.10),
     "error_decision": "pass", "allocated_alpha": 3 * 0.05 / 6},
    {"id": "D5_pilot_hetero_unequal",
     "dgp": _dgp_pilot_hetero(),
     "error_decision": "pass", "allocated_alpha": 0.05 / 2},
    {"id": "D6_persist_const_theta10",
     "dgp": _dgp_persistence("ordinary", 1.00, 0.10),
     "error_decision": "undercover", "allocated_alpha": 3 * 0.05 / 3},
    {"id": "D7_persist_var_nearzero",
     "dgp": _dgp_persistence("ordinary", 0.65, 0.01),
     "error_decision": "undercover", "allocated_alpha": 3 * 0.05 / 3},
    {"id": "D8_persist_var_zero_floor_fork",
     "dgp": _dgp_persistence("fork", 0.60, 0.0),
     "error_decision": "undercover", "allocated_alpha": 2 * 0.05 / 2},
)
assert len(D_SCENARIOS) <= sv.COVERAGE_SCENARIO_CAP
assert len({s["id"] for s in D_SCENARIOS}) == len(D_SCENARIOS)

# bootstrap-based scenarios must clear the agreement gate first
_BOOTSTRAP_SCENARIOS = ("D1_seq_null_ordinary_div3",
                        "D2_seq_null_fork_div3",
                        "D3_equiv_boundary_plus",
                        "D4_equiv_boundary_minus",
                        "D5_pilot_hetero_unequal")


# --- agreement gate -------------------------------------------------------------

def run_agreement_gate() -> dict[str, int]:
    """The 2,000-vs-10,000 replicate decision-agreement check on 1,000
    separately frozen boundary datasets. Runs and must pass BEFORE any
    reduced-replicate coverage scenario executes (142_s finding 4).
    Boundary deltas cycle {0.08, 0.10, 0.12} around the point rule."""
    deltas = (0.08, 0.10, 0.12)
    agree = 0
    for i in range(sv.COVERAGE_AGREEMENT_DATASETS):
        seed = sv.scenario_seed(f"D-agreement|{i}")
        rng = np.random.Generator(np.random.PCG64(seed))
        rows = [_tp_rows(rng, deltas[i % 3], 0.5, 500)]
        d_small = sv.sequential_stake_decision(
            rows, (100, 300, 500), 0.05 / 9,
            sv.COVERAGE_INNER_REPLICATES, seed=seed ^ 0xA9)
        d_big = sv.sequential_stake_decision(
            rows, (100, 300, 500), 0.05 / 9,
            sv.COVERAGE_PRODUCTION_REPLICATES, seed=seed ^ 0xA9)
        agree += int(d_small == d_big)
    return {"agree_count": agree,
            "datasets": sv.COVERAGE_AGREEMENT_DATASETS}


def agreement_passes(artifact_block: Mapping[str, int]) -> bool:
    return (artifact_block["agree_count"]
            / artifact_block["datasets"]) >= sv.COVERAGE_AGREEMENT_MIN


# --- runners (frozen order; integer sufficient statistics only) --------------------

def run_a_grids() -> dict[str, dict[str, int]]:
    results: dict[str, dict[str, int]] = {}
    for scen, d, s in a_position_cells():
        out = sv.simulate_position_power(scen, d, s)
        results[_a_key(scen, d, s)] = {
            "pass_count": out["pass_count"],
            "fail_count": out["fail_count"],
            "unresolved_count": out["unresolved_count"],
            "trials": out["trials"]}
    for mix, e, s in a_router_cells():
        out = sv.simulate_router_power(mix, e, s)
        results[_r_key(mix, e, s)] = {
            "pass_count": out["pass_count"], "fail_count": 0,
            "unresolved_count": out["trials"] - out["pass_count"],
            "trials": out["trials"]}
    return results


def run_c_grid() -> dict[str, dict[str, int]]:
    results: dict[str, dict[str, int]] = {}
    for schedule, n, e, theta, dist in c_cells():
        out = sv.simulate_persistence_envelope(schedule, n, e, theta,
                                               dist)
        results[_c_key(schedule, n, e, theta, dist)] = {
            "pass_count": out["pass_count"],
            "unresolved_count": out["unresolved_count"],
            "trials": out["trials"]}
    return results


def run_d_battery(agreement_block: Mapping[str, int]
                  ) -> dict[str, dict[str, int]]:
    """The 8-scenario coverage battery at 5,000 outer trials. Refuses
    to start a reduced-replicate (bootstrap) scenario unless the
    agreement gate already ran and passed."""
    results: dict[str, dict[str, int]] = {}
    gate_ok = agreement_passes(agreement_block)
    for scen in D_SCENARIOS:
        if scen["id"] in _BOOTSTRAP_SCENARIOS and not gate_ok:
            raise TrancheError(
                "agreement gate has not passed; reduced-replicate "
                f"scenario {scen['id']} may not run (142_s)")
        errors = 0
        for t in range(sv.COVERAGE_OUTER_TRIALS):
            trial_seed = sv.scenario_seed(f"{scen['id']}|{t}")
            decision = scen["dgp"](trial_seed)
            errors += int(decision == scen["error_decision"])
        results[scen["id"]] = {"error_count": errors,
                               "trials": sv.COVERAGE_OUTER_TRIALS}
    return results


# --- content-addressed artifacts -----------------------------------------------------

_INT_FIELDS = {"pass_count", "fail_count", "unresolved_count", "trials",
               "error_count", "agree_count", "datasets"}


def finalize_artifact(name: str, execution_manifest_sha256: str,
                      results: Mapping[str, Mapping[str, int]],
                      extra: Mapping[str, Any] | None = None
                      ) -> dict[str, Any]:
    """Canonical, content-addressed tranche artifact. INTEGER sufficient
    statistics only: any float refuses (rates and bounds are recomputed
    at load, never persisted)."""
    for key, row in results.items():
        for field, value in row.items():
            if field not in _INT_FIELDS or type(value) is not int:
                raise TrancheError(
                    f"artifact {name}: non-integer or unknown field "
                    f"{field!r}={value!r} at {key!r}")
    body: dict[str, Any] = {
        "artifact": name, "tag": TRANCHE_ARTIFACT_TAG,
        "execution_manifest_sha256": execution_manifest_sha256,
        "results": {k: dict(v) for k, v in sorted(results.items())},
    }
    if extra:
        body.update(extra)
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    out = dict(body)
    out["artifact_sha256"] = digest
    return out


def load_artifact(artifact: Mapping[str, Any], name: str,
                  expected_keys: frozenset[str]) -> dict[str, Any]:
    """Fail-closed reload: hash recompute, tag/name, exact key set."""
    body = {k: v for k, v in artifact.items() if k != "artifact_sha256"}
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if digest != artifact.get("artifact_sha256"):
        raise TrancheError(f"artifact {name}: content hash mismatch")
    if artifact.get("artifact") != name or \
            artifact.get("tag") != TRANCHE_ARTIFACT_TAG:
        raise TrancheError(f"artifact {name}: wrong name/tag")
    got = set(artifact["results"])
    if got != expected_keys:
        raise TrancheError(
            f"artifact {name}: key set mismatch "
            f"(missing {len(expected_keys - got)}, "
            f"extra {len(got - expected_keys)})")
    return dict(artifact)


# --- the fail-closed A-D + B verdict ---------------------------------------------------

def _checked_rate(row: Mapping[str, Any], numerator: str,
                  key: str) -> tuple[int, int]:
    n = row.get("trials")
    k = row.get(numerator)
    if type(n) is not int or type(k) is not int or n <= 0 or \
            not 0 <= k <= n:
        raise TrancheError(f"malformed result at {key!r}: "
                           f"{numerator}={k!r}, trials={n!r}")
    return k, n


def aggregate_verdict(a_artifact: Mapping[str, Any],
                      c_artifact: Mapping[str, Any],
                      d_artifact: Mapping[str, Any],
                      b_artifact: Mapping[str, Any]) -> dict[str, Any]:
    """The single fail-closed tranche summary feeding the reviewed
    confirm/amend decision (which is never automated). Every check
    contributes; every input is a validated content-addressed artifact;
    Wilson bounds are recomputed from integer counts, never trusted."""
    reg = expected_result_keys()
    a = load_artifact(a_artifact, "A",
                      reg["A_position"] | reg["A_router"])
    c = load_artifact(c_artifact, "C", reg["C"])
    d = load_artifact(d_artifact, "D", reg["D"])
    if "agreement" not in d:
        raise TrancheError("D artifact carries no agreement block")

    a_fail, r_fail = [], []
    for scen, delta, sigma in a_position_cells():
        key = _a_key(scen, delta, sigma)
        k, n = _checked_rate(a["results"][key], "pass_count", key)
        if delta == sv.ACCEPT_DELTA and sigma <= sv.ACCEPT_SIGMA_MAX \
                and sv.wilson_lower(k, n) < sv.ACCEPT_PASS_WILSON_LB:
            a_fail.append(key)
    for mix, effect, sigma in a_router_cells():
        key = _r_key(mix, effect, sigma)
        k, n = _checked_rate(a["results"][key], "pass_count", key)
        if effect == sv.ROUTER_ACCEPT_EFFECT and \
                sigma <= sv.ACCEPT_SIGMA_MAX and \
                sv.wilson_lower(k, n) < sv.ACCEPT_PASS_WILSON_LB:
            r_fail.append(key)

    c_zero_fail, c_power_fail = [], []
    for schedule, n_cl, e, theta, dist in c_cells():
        key = _c_key(schedule, n_cl, e, theta, dist)
        k, n = _checked_rate(c["results"][key], "pass_count", key)
        if dist != "cluster_correlated":
            continue
        terminal = sv.PERSISTENCE_LOOKS[schedule]["looks"][-1]
        if n_cl != terminal or e != sv.PERSISTENCE_FLOORS[schedule]:
            continue
        if theta == 0.0 and k < n:
            c_zero_fail.append(key)
        if theta == sv.PERSISTENCE_POWER_THETA and \
                sv.wilson_lower(k, n) < sv.PERSISTENCE_POWER_WILSON_LB:
            c_power_fail.append(key)

    agree = d["agreement"]
    if type(agree.get("agree_count")) is not int or \
            type(agree.get("datasets")) is not int or \
            agree["datasets"] <= 0 or \
            not 0 <= agree["agree_count"] <= agree["datasets"]:
        raise TrancheError("malformed agreement block")
    d_fail = []
    if not agreement_passes(agree):
        d_fail.append("agreement")
    for scen in D_SCENARIOS:
        k, n = _checked_rate(d["results"][scen["id"]], "error_count",
                             scen["id"])
        ceiling = sv.coverage_alpha_ceiling(
            float(scen["allocated_alpha"]))
        if sv.wilson_upper(k, n) > ceiling:
            d_fail.append(scen["id"])

    b = dict(b_artifact)
    for field in ("artifact_sha256", "directions"):
        if field not in b:
            raise TrancheError(f"B artifact missing {field!r}")
    b_blockers = []
    for direction, block in sorted(b["directions"].items()):
        status = block.get("status")
        if status not in ("demonstrated", "not_demonstrated", "unknown"):
            raise TrancheError(f"B direction {direction}: bad status "
                               f"{status!r}")
        if status == "not_demonstrated":
            b_blockers.append(direction)

    return {
        "A_positions_failing": a_fail,
        "A_router_failing": r_fail,
        "C_zero_persistence_failing": c_zero_fail,
        "C_power_failing": c_power_fail,
        "D_failing": d_fail,
        "B_directions_blocking": b_blockers,
        "B_directions_unknown": [
            k for k, v in sorted(b["directions"].items())
            if v.get("status") == "unknown"],
        "confirm_possible": not (a_fail or r_fail or c_zero_fail
                                 or c_power_fail or d_fail
                                 or b_blockers),
    }
