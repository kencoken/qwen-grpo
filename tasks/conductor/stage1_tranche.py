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
    """CLUSTER-LEVEL two-point draws carried through all renderer rows
    (perfect renderer correlation, 145_s finding 4): the cluster-mean SD
    is exactly `sigma`, so a scenario declaring cluster-level sigma=0.75
    actually tests it — independent renderer rows would dilute it to
    sigma/sqrt(3)."""
    a, p_b = sv.two_point_distribution(delta, sigma)
    cluster_vals = np.where(rng.random(clusters) < p_b, 1.0, a)
    return np.repeat(cluster_vals[:, None], renderers, axis=1)


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


# --- deterministic equivalence set (production 10k replicates) ----------------

def run_deterministic_equivalence_set() -> dict[str, str]:
    """132_s §8.4D: production (10,000-replicate) inference is first run
    on a small frozen DETERMINISTIC equivalence set with analytically
    known decisions (constant data makes the bootstrap degenerate).
    Every decision must match exactly; the runner refuses to continue
    otherwise. Constant value ±0.10 is the null boundary: under the
    strict band (|theta| < 0.10; ±0.10 in the null), the degenerate
    interval [±0.10, ±0.10] satisfies the conclusive non-equivalence
    rule (LCB >= band, resp. UCB <= -band), so `fail` — correctly
    refusing equivalence — is the analytically required decision."""
    cases = {
        "inside_zero": (0.0, "pass"),
        "boundary_plus": (0.10, "fail"),
        "boundary_minus": (-0.10, "fail"),
        "outside_plus": (0.5, "fail"),
        "outside_minus": (-0.5, "fail"),
        "inside_edge": (0.099, "pass"),
    }
    results: dict[str, str] = {}
    for name, (value, expected) in cases.items():
        rows = [np.full((500, 3), value)]
        got = sv.sequential_equivalence_decision(
            rows, (100, 300, 500), 0.05 / 3,
            sv.COVERAGE_PRODUCTION_REPLICATES,
            seed=sv.scenario_seed(f"D-detset|{name}"))
        results[name] = got
        if got != expected:
            raise TrancheError(
                f"deterministic equivalence set: {name} decided {got!r},"
                f" expected {expected!r} — production inference is "
                "wrong; nothing else may run")
    return results


# --- agreement gate -------------------------------------------------------------

def _agreement_decision(family: str, rows: list[np.ndarray],
                        replicates: int, seed: int) -> str:
    if family == "stake_ordinary":
        return sv.sequential_stake_decision(rows, (100, 300, 500),
                                            0.05 / 9, replicates, seed)
    if family == "stake_fork":
        return sv.sequential_stake_decision(rows, (100, 200), 0.05 / 6,
                                            replicates, seed)
    if family == "equivalence":
        return sv.sequential_equivalence_decision(
            rows, (100, 300, 500), 0.05 / 3, replicates, seed)
    if family == "pilot_unequal":
        lcb, _ = sv.paired_cluster_bootstrap(rows, 0.05 / 2, replicates,
                                             seed)
        return "pass" if lcb > 0 else "not_pass"
    raise TrancheError(f"unknown agreement family {family!r}")


_AGREEMENT_FAMILIES = ("stake_ordinary", "equivalence", "pilot_unequal",
                       "stake_fork")


def run_agreement_gate() -> dict[str, int]:
    """The 2,000-vs-10,000 replicate decision-agreement check on 1,000
    separately frozen boundary datasets, REPRESENTING every
    reduced-replicate scenario family it authorizes (145_s finding 3):
    datasets cycle stake-ordinary / equivalence / pilot-unequal-cells /
    stake-fork, with boundary effect sizes cycling {0.08, 0.10, 0.12}
    (equivalence datasets sit at their own +/-0.10 band boundary)."""
    deltas = (0.08, 0.10, 0.12)
    agree = 0
    for i in range(sv.COVERAGE_AGREEMENT_DATASETS):
        family = _AGREEMENT_FAMILIES[i % 4]
        seed = sv.scenario_seed(f"D-agreement|{family}|{i}")
        rng = np.random.Generator(np.random.PCG64(seed))
        delta = deltas[(i // 4) % 3]
        if family == "stake_ordinary":
            rows = [_tp_rows(rng, delta, 0.5, 500)]
        elif family == "stake_fork":
            rows = [_tp_rows(rng, delta, 0.5, 200)]
        elif family == "equivalence":
            rows = [_tp_rows(rng, delta, 0.5, 500)]
        else:  # pilot_unequal: heterogeneous cells at a boundary shift
            sigmas = (0.25, 0.40, 0.50, 0.60, 0.75, 0.90)
            counts = (12, 12, 12, 12, 12, 6)
            rows = [_tp_rows(rng, delta / 2, sg, n)
                    for sg, n in zip(sigmas, counts)]
        d_small = _agreement_decision(
            family, rows, sv.COVERAGE_INNER_REPLICATES, seed ^ 0xA9)
        d_big = _agreement_decision(
            family, rows, sv.COVERAGE_PRODUCTION_REPLICATES, seed ^ 0xA9)
        agree += int(d_small == d_big)
    return {"agree_count": agree,
            "datasets": sv.COVERAGE_AGREEMENT_DATASETS}


def agreement_passes(artifact_block: Mapping[str, int]) -> bool:
    """145_s finding 3: the frozen criterion is the one-sided 95% Wilson
    LOWER BOUND >= 0.995 on exactly the 1,000 frozen datasets — 999/1000
    is the minimum passing count; 1/1 or any other sample size refuses."""
    agree = artifact_block.get("agree_count")
    datasets = artifact_block.get("datasets")
    if type(agree) is not int or type(datasets) is not int:
        raise TrancheError("malformed agreement block")
    if datasets != sv.COVERAGE_AGREEMENT_DATASETS:
        raise TrancheError(
            f"agreement gate requires exactly "
            f"{sv.COVERAGE_AGREEMENT_DATASETS} frozen datasets, got "
            f"{datasets}")
    if not 0 <= agree <= datasets:
        raise TrancheError("malformed agreement block")
    return sv.wilson_lower(agree, datasets) >= sv.COVERAGE_AGREEMENT_MIN


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
        results[scen["id"]] = run_d_battery_scenario(scen)
    return results


# --- content-addressed artifacts -----------------------------------------------------

_HEX64 = frozenset("0123456789abcdef")
_RESERVED_FIELDS = frozenset({"artifact", "tag",
                              "execution_manifest_sha256", "results",
                              "artifact_sha256"})

# Exact per-artifact row schemas (145_s finding 2): field sets, trial
# counts, and count identities are all enforced at load.
_ROW_SCHEMAS: dict[str, dict[str, Any]] = {
    "A": {"fields": frozenset({"pass_count", "fail_count",
                               "unresolved_count", "trials"}),
          "trials": sv.POWER_TRIALS,
          "identity": lambda r: (r["pass_count"] + r["fail_count"]
                                 + r["unresolved_count"] == r["trials"])},
    "C": {"fields": frozenset({"pass_count", "unresolved_count",
                               "trials"}),
          "trials": sv.PERSISTENCE_TRIALS,
          "identity": lambda r: (r["pass_count"] + r["unresolved_count"]
                                 <= r["trials"])},
    "D": {"fields": frozenset({"error_count", "trials"}),
          "trials": sv.COVERAGE_OUTER_TRIALS,
          "identity": lambda r: r["error_count"] <= r["trials"]},
    "B": {"fields": frozenset({"k2", "k3", "n"}),
          "trials": None,  # n checked against the replay contract
          "identity": lambda r: 0 <= r["k2"] + r["k3"] <= r["n"]},
}


def _check_hex64(value: Any, what: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or \
            not set(value) <= _HEX64:
        raise TrancheError(f"{what} must be 64 lowercase hex characters")
    return value


def finalize_artifact(name: str, execution_manifest_sha256: str,
                      results: Mapping[str, Mapping[str, int]],
                      extra: Mapping[str, Any] | None = None
                      ) -> dict[str, Any]:
    """Canonical, content-addressed tranche artifact. INTEGER sufficient
    statistics only (rates/bounds recomputed at load); the execution
    identity is validated; `extra` may not shadow reserved fields."""
    _check_hex64(execution_manifest_sha256, "execution_manifest_sha256")
    if name not in _ROW_SCHEMAS:
        raise TrancheError(f"unknown artifact name {name!r}")
    schema = _ROW_SCHEMAS[name]
    for key, row in results.items():
        if set(row) != schema["fields"]:
            raise TrancheError(
                f"artifact {name}: row {key!r} fields {sorted(row)} != "
                f"schema {sorted(schema['fields'])}")
        for field, value in row.items():
            if type(value) is not int:
                raise TrancheError(
                    f"artifact {name}: non-integer field "
                    f"{field!r}={value!r} at {key!r}")
    if extra and set(extra) & _RESERVED_FIELDS:
        raise TrancheError(
            f"extra fields {sorted(set(extra) & _RESERVED_FIELDS)} "
            "shadow reserved artifact fields")
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
                  expected_keys: frozenset[str],
                  execution_manifest_sha256: str | None = None,
                  b_n: int | None = None) -> dict[str, Any]:
    """Fail-closed reload: hash recompute, tag/name, exact key set,
    exact per-row schema with trial-count and count identities, and —
    when given — the ONE authoritative execution identity (145_s
    finding 2: the aggregate may never mix executions)."""
    body = {k: v for k, v in artifact.items() if k != "artifact_sha256"}
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if digest != artifact.get("artifact_sha256"):
        raise TrancheError(f"artifact {name}: content hash mismatch")
    if artifact.get("artifact") != name or \
            artifact.get("tag") != TRANCHE_ARTIFACT_TAG:
        raise TrancheError(f"artifact {name}: wrong name/tag")
    if execution_manifest_sha256 is not None and \
            artifact.get("execution_manifest_sha256") != \
            execution_manifest_sha256:
        raise TrancheError(
            f"artifact {name}: foreign execution identity — artifacts "
            "from different executions may not be aggregated")
    got = set(artifact["results"])
    if got != expected_keys:
        raise TrancheError(
            f"artifact {name}: key set mismatch "
            f"(missing {len(expected_keys - got)}, "
            f"extra {len(got - expected_keys)})")
    schema = _ROW_SCHEMAS[name]
    for key, row in artifact["results"].items():
        if set(row) != schema["fields"]:
            raise TrancheError(f"artifact {name}: row {key!r} has wrong "
                               "field set")
        for field, value in row.items():
            if type(value) is not int or value < 0:
                raise TrancheError(
                    f"artifact {name}: bad {field!r}={value!r} at "
                    f"{key!r}")
        expected_n = b_n if name == "B" else schema["trials"]
        n_field = "n" if name == "B" else "trials"
        if expected_n is not None and row[n_field] != expected_n:
            raise TrancheError(
                f"artifact {name}: {n_field}={row[n_field]} at {key!r} "
                f"!= frozen {expected_n}")
        if not schema["identity"](row):
            raise TrancheError(
                f"artifact {name}: impossible counts at {key!r}: "
                f"{dict(row)!r}")
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
    contributes; every input is a validated content-addressed artifact
    bound to ONE authoritative execution identity (the compatibility
    rule for B's GPU session is identity: same box, same
    stage1-environment-v2 manifest); Wilson bounds and B direction
    statuses are recomputed from integer counts, never trusted."""
    exec_sha = _check_hex64(
        a_artifact.get("execution_manifest_sha256"),
        "A execution_manifest_sha256")
    reg = expected_result_keys()
    a = load_artifact(a_artifact, "A",
                      reg["A_position"] | reg["A_router"], exec_sha)
    c = load_artifact(c_artifact, "C", reg["C"], exec_sha)
    d = load_artifact(d_artifact, "D", reg["D"], exec_sha)
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

    d_fail = []
    if not agreement_passes(d["agreement"]):
        d_fail.append("agreement")
    for scen in D_SCENARIOS:
        k, n = _checked_rate(d["results"][scen["id"]], "error_count",
                             scen["id"])
        ceiling = sv.coverage_alpha_ceiling(
            float(scen["allocated_alpha"]))
        if sv.wilson_upper(k, n) > ceiling:
            d_fail.append(scen["id"])

    # B: validated artifact; direction statuses RECOMPUTED from its
    # integer counts and embedded pre-sampling pair table — never
    # trusted from a summary (145_s finding 1). An empty or partial B
    # refuses inside load_b_artifact/summarize_replay.
    from .stage1_replay import load_b_artifact, summarize_replay
    b = load_b_artifact(b_artifact, exec_sha)
    summary = summarize_replay(b["results"], b["pair_table"],
                               b["obs_meta"])
    directions = summary["directions"]
    if set(directions) != {"2", "3"}:
        raise TrancheError("B summary must cover exactly directions "
                           "2 and 3")
    b_blockers = [u for u, block in sorted(directions.items())
                  if block["status"] == "not_demonstrated"]

    return {
        "A_positions_failing": a_fail,
        "A_router_failing": r_fail,
        "C_zero_persistence_failing": c_zero_fail,
        "C_power_failing": c_power_fail,
        "D_failing": d_fail,
        "B_directions_blocking": b_blockers,
        "B_directions_unknown": [
            u for u, block in sorted(directions.items())
            if block["status"] == "unknown"],
        "confirm_possible": not (a_fail or r_fail or c_zero_fail
                                 or c_power_fail or d_fail
                                 or b_blockers),
    }


# --- the one narrow tranche command (145_s finding 6) ---------------------------

TRANCHE_RUN_DIR = "runs/stage1-validation"
SCENARIO_ABORT_FACTOR = 4


def run_full_tranche(*, allow_dirty: bool = False) -> dict[str, Any]:
    """The single CPU-side tranche command, enforcing the frozen order:
    one environment manifest → deterministic equivalence set (must pass)
    → worst-case benchmark → A grids → C grid → agreement gate → D
    battery with the 4x-runtime abort per scenario → artifacts persisted
    to runs/stage1-validation/, reloaded and re-verified via
    load_artifact. Check B (GPU) runs separately under the same
    environment identity; aggregate_verdict joins all four."""
    import json
    import time
    from pathlib import Path

    from .stage1_manifest import build_stage1_env_manifest
    env = build_stage1_env_manifest(allow_dirty=allow_dirty)
    exec_sha = env["execution_manifest_sha256"]

    det = run_deterministic_equivalence_set()   # raises on any mismatch
    bench = sv.benchmark_worst_case()
    per_trial_budget = SCENARIO_ABORT_FACTOR * \
        bench["seconds_per_outer_trial"] * sv.COVERAGE_OUTER_TRIALS

    a_results = run_a_grids()
    c_results = run_c_grid()
    agreement = run_agreement_gate()
    if not agreement_passes(agreement):
        raise TrancheError(
            f"agreement gate failed ({agreement['agree_count']}/"
            f"{agreement['datasets']}); the reduced-replicate battery "
            "may not run")
    d_results: dict[str, dict[str, int]] = {}
    for scen in D_SCENARIOS:
        t0 = time.perf_counter()
        block = run_d_battery_scenario(scen)
        elapsed = time.perf_counter() - t0
        if elapsed > per_trial_budget:
            raise TrancheError(
                f"{scen['id']} took {elapsed:.0f}s > "
                f"{SCENARIO_ABORT_FACTOR}x the benchmarked projection "
                f"({per_trial_budget:.0f}s) — aborting per 144_f/147_f")
        d_results[scen["id"]] = block

    out_dir = Path(TRANCHE_RUN_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    reg = expected_result_keys()
    artifacts = {
        "A": finalize_artifact("A", exec_sha, a_results),
        "C": finalize_artifact("C", exec_sha, c_results),
        "D": finalize_artifact("D", exec_sha, d_results,
                               extra={"agreement": agreement}),
    }
    (out_dir / "env_manifest.json").write_text(
        json.dumps(env, indent=1), encoding="utf-8")
    for name, artifact in artifacts.items():
        path = out_dir / f"artifact_{name}.json"
        path.write_text(json.dumps(artifact, indent=1), encoding="utf-8")
        reloaded = json.loads(path.read_text(encoding="utf-8"))
        expected = (reg["A_position"] | reg["A_router"]
                    if name == "A" else reg[name])
        load_artifact(reloaded, name, expected, exec_sha)
    return {"execution_manifest_sha256": exec_sha,
            "deterministic_equivalence": det,
            "benchmark": bench, "agreement": agreement,
            "artifact_paths": {n: str(out_dir / f"artifact_{n}.json")
                               for n in artifacts}}


def run_d_battery_scenario(scen: Mapping[str, Any]) -> dict[str, int]:
    """One frozen coverage scenario at 5,000 outer trials."""
    errors = 0
    for t in range(sv.COVERAGE_OUTER_TRIALS):
        trial_seed = sv.scenario_seed(f"{scen['id']}|{t}")
        decision = scen["dgp"](trial_seed)
        errors += int(decision == scen["error_decision"])
    return {"error_count": errors, "trials": sv.COVERAGE_OUTER_TRIALS}
