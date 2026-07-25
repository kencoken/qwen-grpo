"""§8.4 tranche runner — frozen grids, D registry, artifacts, verdict
(unit 3, completing the 141_f preregistration per 142_s).

Everything executable about the tranche lives here, frozen BEFORE any
output is revealed:

- exact grid enumerators and expected-key registries (48 A-position
  cells, 24 A-router cells, 120 C cells, 8 D scenarios, 1 B artifact);
- the frozen D scenario registry: DGPs, seeds, allocated operational
  alphas, truth, and error definitions;
- (amended per 158_s §6, Unit C: the agreement gate and the
  2,000-replicate approximation are DELETED — 10,000 production
  replicates are the only inner count; the v1 machinery lives in the
  archived worktree at da8424b);
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

from . import stage1_amend1 as am
from . import stage1_persistence as sp
from . import stage1_validation as sv
from .profiles import canonical_json
from .types import InfrastructureError

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


def stage1_fork_schedule() -> tuple[int, ...]:
    """The amended fork looks, read from the single source (158_s
    §5.1: (100, 500))."""
    from . import stage1
    return tuple(stage1.FORK_LOOK_SCHEDULE)


def _dgp_seq_null(schedule: tuple[int, ...], tail: float, cells: int,
                  sigma: float) -> Callable[[int], str]:
    def run(trial_seed: int) -> str:
        rng = np.random.Generator(np.random.PCG64(trial_seed))
        rows = [_tp_rows(rng, 0.0, sigma, schedule[-1])
                for _ in range(cells)]
        return sv.sequential_stake_decision(
            rows, schedule, tail, sv.COVERAGE_PRODUCTION_REPLICATES,
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
            rows, looks, tail, sv.COVERAGE_PRODUCTION_REPLICATES,
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
            rows, 0.05 / 2, sv.COVERAGE_PRODUCTION_REPLICATES,
            seed=trial_seed ^ 0x5EED)
        return "pass" if lcb > 0 else "not_pass"
    return run


def _amended_persistence_upper(record) -> float:
    """The reported ratio upper endpoint at one look (158_s §6): the
    zero-branch operational bound, or the inverted-interval upper for
    the positive branch; a denominator-unresolved look reports 1."""
    if record["branch"] == "zero":
        u = record["zero_U"]
        return float("inf") if u == "inf" else float(u)
    if record["denominator_check"] == "unresolved":
        return 1.0
    return float(record["pos_U_p"])


def _dgp_amended_persistence(schedule: str, eligibility: float,
                             theta: float, dist: str,
                             structural: bool) -> Callable[[int], Any]:
    """D6-D8 (158_s §6): one maximum-length prefix-valid vector per
    outer trial; every registered look evaluated with the AMENDED
    statistic (inversion included); error = UNDERCOVERAGE — the
    reported upper endpoint strictly below the true theta at ANY
    registered look (U_p == theta covers at the non-strict boundary).
    Returns (undercover: bool, branches: {look: branch-tag})."""
    looks = sv.PERSISTENCE_LOOKS[schedule]["looks"]

    def run(trial_seed: int):
        j, k = sp.generate_path(schedule, eligibility, theta, dist,
                                trial_seed)
        undercover = False
        branches: dict[int, str] = {}
        for look in looks:
            record = sp.look_decision(j[:look], k[:look], schedule,
                                      structural=structural)
            if record["branch"] == "zero":
                branches[look] = "zero"
            elif record["denominator_check"] == "unresolved":
                branches[look] = "denominator_unresolved"
            else:
                branches[look] = "positive"
            if _amended_persistence_upper(record) < theta:
                undercover = True
        return undercover, branches
    return run


D_SCENARIOS: tuple[dict[str, Any], ...] = (
    {"id": "D1_seq_null_ordinary_div3", "kind": "decision",
     "dgp": _dgp_seq_null((100, 300, 500), 0.05 / 9, 5, 0.75),
     "error_decision": "pass", "allocated_alpha": 3 * 0.05 / 9},
    # 158_s §5.1: schedule-based fork rows use the AMENDED (100, 500)
    {"id": "D2_seq_null_fork_div3", "kind": "decision",
     "dgp": _dgp_seq_null(stage1_fork_schedule(), 0.05 / 6, 1, 0.50),
     "error_decision": "pass", "allocated_alpha": 2 * 0.05 / 6},
    {"id": "D3_equiv_boundary_plus", "kind": "decision",
     "dgp": _dgp_equiv_boundary(+0.10),
     "error_decision": "pass", "allocated_alpha": 3 * 0.05 / 6},
    {"id": "D4_equiv_boundary_minus", "kind": "decision",
     "dgp": _dgp_equiv_boundary(-0.10),
     "error_decision": "pass", "allocated_alpha": 3 * 0.05 / 6},
    {"id": "D5_pilot_hetero_unequal", "kind": "decision",
     "dgp": _dgp_pilot_hetero(),
     "error_decision": "pass", "allocated_alpha": 0.05 / 2},
    # 158_s §6: reissued undercoverage rows on the AMENDED statistic
    {"id": "D6_persist_const_theta10", "kind": "persistence",
     "dgp": _dgp_amended_persistence("ordinary", 1.00, 0.10,
                                     "cluster_correlated",
                                     structural=True),
     "theta": 0.10, "allocated_alpha": 0.05},
    {"id": "D7_persist_rowdispersed_theta10", "kind": "persistence",
     "dgp": _dgp_amended_persistence("ordinary", 0.65, 0.10,
                                     "row_dispersed",
                                     structural=False),
     "theta": 0.10, "allocated_alpha": 0.05},
    {"id": "D8_persist_hybrid_theta01_fork", "kind": "persistence",
     "dgp": _dgp_amended_persistence("fork", 0.60, 0.01,
                                     "cluster_correlated",
                                     structural=False),
     "theta": 0.01, "allocated_alpha": 0.05,
     "requires_both_branches_each_look": True},
)
assert len(D_SCENARIOS) <= sv.COVERAGE_SCENARIO_CAP
assert len({sc["id"] for sc in D_SCENARIOS}) == len(D_SCENARIOS)
assert tuple(sc["id"] for sc in D_SCENARIOS) == am.AMEND1_D_IDS

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


def run_d_battery(deadline_seconds: float | None = None
                  ) -> tuple[dict[str, dict[str, int]],
                             dict[str, dict[str, int]]]:
    """All eight amended scenarios at 5,000 outer trials, 10,000
    production inner replicates where a bootstrap applies. There is NO
    agreement gate (158_s §6 — the reduced-replicate approximation is
    deleted). Returns (scenario rows, D6-D8 per-look branch rows)."""
    results: dict[str, dict[str, int]] = {}
    branch_rows: dict[str, dict[str, int]] = {}
    for scen in D_SCENARIOS:
        row, branches = run_d_battery_scenario(
            scen, deadline_seconds=deadline_seconds)
        results[scen["id"]] = row
        branch_rows.update(branches)
    return results, branch_rows


def run_d_battery_scenario(scen: Mapping[str, Any],
                           deadline_seconds: float | None = None
                           ) -> tuple[dict[str, int],
                                      dict[str, dict[str, int]]]:
    """One frozen scenario at 5,000 outer trials with the IN-LOOP
    deadline (checked every 50 trials; partial error count travels in
    the abort message). Persistence scenarios additionally return
    per-look branch rows (158_s §6)."""
    import time
    errors = 0
    branch_counts: dict[int, dict[str, int]] = {}
    started = time.perf_counter()
    for t in range(sv.COVERAGE_OUTER_TRIALS):
        if deadline_seconds is not None and t % 50 == 0 and \
                time.perf_counter() - started > deadline_seconds:
            raise TrancheError(
                f"{scen['id']} exceeded its {deadline_seconds:.0f}s "
                f"deadline at trial {t}/{sv.COVERAGE_OUTER_TRIALS} "
                f"(partial errors={errors}) — aborting per 158_s §5.4")
        trial_seed = sv.scenario_seed(f"{scen['id']}|{t}")
        if scen["kind"] == "decision":
            decision = scen["dgp"](trial_seed)
            errors += int(decision == scen["error_decision"])
        else:
            undercover, branches = scen["dgp"](trial_seed)
            errors += int(undercover)
            for look, tag in branches.items():
                row = branch_counts.setdefault(
                    look, {"zero_branch": 0, "positive_branch": 0,
                           "denominator_unresolved": 0})
                if tag == "zero":
                    row["zero_branch"] += 1
                elif tag == "denominator_unresolved":
                    row["positive_branch"] += 1
                    row["denominator_unresolved"] += 1
                else:
                    row["positive_branch"] += 1
    branch_rows = {
        f"{scen['id']}|look{look}": {**counts,
                                     "trials": sv.COVERAGE_OUTER_TRIALS}
        for look, counts in sorted(branch_counts.items())}
    return ({"error_count": errors,
             "trials": sv.COVERAGE_OUTER_TRIALS}, branch_rows)


def d8_branch_support_ok(branch_rows: Mapping[str, Mapping[str, int]]
                         ) -> bool:
    """158_s §6: D8 must reach BOTH branches at each registered look;
    otherwise the scenario is unsupported and D does not pass."""
    fork_looks = stage1_fork_schedule()
    for look in fork_looks:
        row = branch_rows.get(f"D8_persist_hybrid_theta01_fork"
                              f"|look{look}")
        if not row or row["zero_branch"] == 0 or \
                row["positive_branch"] == 0:
            return False
    return True


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
                      extra: Mapping[str, Any] | None = None,
                      tag: str = TRANCHE_ARTIFACT_TAG,
                      row_schema: Mapping[str, Any] | None = None
                      ) -> dict[str, Any]:
    """Canonical, content-addressed tranche artifact. INTEGER sufficient
    statistics only (rates/bounds recomputed at load); the execution
    identity is validated; `extra` may not shadow reserved fields."""
    _check_hex64(execution_manifest_sha256, "execution_manifest_sha256")
    if row_schema is not None:
        schema = row_schema           # amended schemas (158_s Unit B+)
    elif name in _ROW_SCHEMAS:
        schema = _ROW_SCHEMAS[name]
    else:
        raise TrancheError(f"unknown artifact name {name!r}")
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
        "artifact": name, "tag": tag,
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
                  b_n: int | None = None,
                  tag: str = TRANCHE_ARTIFACT_TAG,
                  row_schema: Mapping[str, Any] | None = None
                  ) -> dict[str, Any]:
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
            artifact.get("tag") != tag:
        raise TrancheError(
            f"artifact {name}: wrong name/tag (expected tag {tag!r}; "
            "a v1 artifact must refuse an amend1 loader and vice "
            "versa, 158_s §9)")
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
    schema = row_schema if row_schema is not None \
        else _ROW_SCHEMAS[name]
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


# --- the fail-closed amended verdict (158_s §§7, 12) ---------------------------

def _checked_rate(row: Mapping[str, Any], numerator: str,
                  key: str) -> tuple[int, int]:
    n = row.get("trials")
    k = row.get(numerator)
    if type(n) is not int or type(k) is not int or n <= 0 or \
            not 0 <= k <= n:
        raise TrancheError(f"malformed result at {key!r}: "
                           f"{numerator}={k!r}, trials={n!r}")
    return k, n


def aggregate_amend1_verdict(a_artifact: Mapping[str, Any],
                             c_artifact: Mapping[str, Any],
                             d_artifact: Mapping[str, Any],
                             b_evidence: Mapping[str, Any], *,
                             env_manifest: Mapping[str, Any],
                             bundle: Mapping[str, Any],
                             seed_registry: Mapping[str, int],
                             b_pinned_loader=None) -> dict[str, Any]:
    """The single fail-closed AMENDED tranche summary feeding the
    reviewed terminal decision (158_s §12 — never automated). Inputs
    bind to ONE execution-bundle identity (validated against the
    finalized registry); A keeps its v1 acceptance criteria under
    fresh seeds; C is judged by the §5.3 hard-path evaluator; D by the
    per-scenario Wilson ceilings plus the D8 branch-support rule; B by
    the §7 C2/C1 consequence matrix — B never blocks confirmation
    globally, it sets the claim state. There is NO agreement input."""
    exec_sha = am.validate_execution_bundle(bundle,
                                            seed_registry=seed_registry)
    from .stage1_manifest import validate_env_manifest
    env_sha = validate_env_manifest(env_manifest)
    if bundle.get("environment_manifest_sha256") != env_sha:
        raise TrancheError(
            "bundle does not bind this environment manifest")

    reg = expected_result_keys()
    a = load_artifact(a_artifact, "A",
                      reg["A_position"] | reg["A_router"], exec_sha,
                      tag=am.AMEND1_ARTIFACT_TAG)
    c = sp.load_amended_c_artifact(c_artifact, exec_sha)
    d = load_artifact(d_artifact, "D", frozenset(am.AMEND1_D_IDS),
                      exec_sha, tag=am.AMEND1_ARTIFACT_TAG)
    if "branch_counts" not in d:
        raise TrancheError("amended D artifact carries no "
                           "branch_counts block")
    am.validate_amend1_rows("D_branch", d["branch_counts"])

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

    c_verdict = sp.hard_path_acceptance(c["results"])

    d_fail = []
    for scen in D_SCENARIOS:
        k, n = _checked_rate(d["results"][scen["id"]], "error_count",
                             scen["id"])
        ceiling = sv.coverage_alpha_ceiling(
            float(scen["allocated_alpha"]))
        if sv.wilson_upper(k, n) > ceiling:
            d_fail.append(scen["id"])
    if not d8_branch_support_ok(d["branch_counts"]):
        d_fail.append("D8_branch_support")

    # B: full evidence verification, then the §7 consequence matrix —
    # malformed/unreproducible evidence raises (infrastructure abort);
    # not_demonstrated/unknown set the conservative C1-only state.
    from .stage1_replay import verify_replay_evidence
    for field in ("artifact", "replay_manifest",
                  "raw_completions_text"):
        if field not in b_evidence:
            raise TrancheError(f"B evidence bundle missing {field!r}")
    summary = verify_replay_evidence(
        b_evidence["artifact"], env_manifest=env_manifest,
        replay_manifest=b_evidence["replay_manifest"],
        raw_completions_text=b_evidence["raw_completions_text"],
        pinned_loader=b_pinned_loader,
        execution_identity=exec_sha)     # the bundle identity (§9.1)
    directions = summary["directions"]
    if set(directions) != {"2", "3"}:
        raise TrancheError("B summary must cover exactly directions "
                           "2 and 3")
    statuses = {u: directions[u]["status"] for u in ("2", "3")}
    for u, status in statuses.items():
        if status not in ("not_ruled_out", "not_demonstrated",
                          "unknown"):
            raise TrancheError(f"B direction {u}: bad status "
                               f"{status!r}")
    c2_available = all(v == "not_ruled_out" for v in statuses.values())

    scientific_pass = not (a_fail or r_fail
                           or not c_verdict["passes"] or d_fail)
    if scientific_pass and c2_available:
        decision = "confirm_c2_provisional"
    elif scientific_pass:
        decision = "confirm_c1_only"
    else:
        decision = "scientific_stop"

    return {
        "A_positions_failing": a_fail,
        "A_router_failing": r_fail,
        "C_hard_path_failures": c_verdict["failures"],
        "D_failing": d_fail,
        "B_direction_statuses": statuses,
        "C2_preCE1_available": c2_available,
        "decision": decision,
    }


# --- the one narrow amended tranche command (158_s §11) ---------------------------

SCENARIO_ABORT_FACTOR = 4
A_BUDGET_SECONDS = 30 * 60
D68_BUDGET_SECONDS = 30 * 60
TOTAL_BUDGET_SECONDS = 12 * 3600


def run_amend1_tranche(bundle: Mapping[str, Any],
                       seed_registry: Mapping[str, int], *,
                       allow_dirty: bool = False) -> dict[str, Any]:
    """The single CPU-side AMENDED tranche command in the frozen 158_s
    §11 order: v1 evidence archive verification → bundle/registry/
    environment validation → atomic run-root claim → deterministic
    equivalence set → the full-count worst-case benchmark and frozen
    budgets → fresh-seed A → amended C → all eight D scenarios →
    amend1 artifacts with staged persistence, wall times, and
    aborted-run records. B (GPU) runs separately under the same
    bundle; aggregate_amend1_verdict joins everything."""
    import json
    import time
    from pathlib import Path

    from .stage1_manifest import build_stage1_env_manifest

    am.verify_v1_evidence_archive()          # §11 step 1: entry gate
    exec_sha = am.validate_execution_bundle(
        bundle, seed_registry=seed_registry)
    env = build_stage1_env_manifest(allow_dirty=allow_dirty)
    if bundle.get("environment_manifest_sha256") != \
            env["execution_manifest_sha256"]:
        raise TrancheError("bundle does not bind the current "
                           "environment manifest")
    out_dir = am.claim_run_root(am.AMEND1_VALIDATION_RUN_ROOT)

    record: dict[str, Any] = {"status": "running", "stages": [],
                              "scenario_wall_seconds": {},
                              "started_unix": int(time.time())}

    def _persist(name: str, obj: Any) -> None:
        (out_dir / f"{name}.json").write_text(
            json.dumps(obj, indent=1), encoding="utf-8")
        record["stages"].append(name)
        (out_dir / "run_record.json").write_text(
            json.dumps(record, indent=1), encoding="utf-8")

    started = time.time()
    try:
        _persist("execution_bundle_manifest", dict(bundle))
        _persist("env_manifest", env)

        det = run_deterministic_equivalence_set()
        _persist("deterministic_equivalence", det)

        bench = sv.benchmark_worst_case()
        d_deadline = SCENARIO_ABORT_FACTOR * \
            bench["seconds_per_outer_trial"] * sv.COVERAGE_OUTER_TRIALS
        _persist("benchmark", {
            "seconds_per_outer_trial_x1e6":
                int(bench["seconds_per_outer_trial"] * 1e6),
            "d_scenario_deadline_seconds": int(d_deadline)})

        a_started = time.time()
        a_results: dict[str, dict[str, int]] = {}
        for scen, delta, sigma in a_position_cells():
            key = _a_key(scen, delta, sigma)
            out = sv.simulate_position_power(
                scen, delta, sigma, seed_override=seed_registry[key])
            a_results[key] = {"pass_count": out["pass_count"],
                              "fail_count": out["fail_count"],
                              "unresolved_count":
                                  out["unresolved_count"],
                              "trials": out["trials"]}
        for mix, effect, sigma in a_router_cells():
            key = _r_key(mix, effect, sigma)
            out = sv.simulate_router_power(
                mix, effect, sigma, seed_override=seed_registry[key])
            a_results[key] = {
                "pass_count": out["pass_count"], "fail_count": 0,
                "unresolved_count": out["trials"] - out["pass_count"],
                "trials": out["trials"]}
        if time.time() - a_started > A_BUDGET_SECONDS:
            raise TrancheError("A exceeded its 30-minute budget")
        a_art = finalize_artifact("A", exec_sha, a_results,
                                  tag=am.AMEND1_ARTIFACT_TAG)
        _persist("artifact_A", a_art)

        path_rows, marginal_rows = sp.run_amended_c(seed_registry)
        c_art = sp.build_c_artifact(exec_sha, path_rows, marginal_rows)
        _persist("artifact_C", c_art)

        d_results: dict[str, dict[str, int]] = {}
        d_branches: dict[str, dict[str, int]] = {}
        d68_started = None
        for scen in D_SCENARIOS:
            if scen["kind"] == "persistence" and d68_started is None:
                d68_started = time.time()
            t0 = time.perf_counter()
            try:
                row, branches = run_d_battery_scenario(
                    scen, deadline_seconds=d_deadline)
            finally:
                record["scenario_wall_seconds"][scen["id"]] = \
                    int(time.perf_counter() - t0)
            d_results[scen["id"]] = row
            d_branches.update(branches)
            _persist(f"partial_D_{scen['id']}", row)
            if scen["kind"] == "persistence" and \
                    time.time() - d68_started > D68_BUDGET_SECONDS:
                raise TrancheError("D6-D8 exceeded their combined "
                                   "30-minute budget")
        d_art = finalize_artifact(
            "D", exec_sha, d_results,
            extra={"branch_counts": {k: dict(v) for k, v
                                     in sorted(d_branches.items())}},
            tag=am.AMEND1_ARTIFACT_TAG)
        _persist("artifact_D", d_art)

        if time.time() - started > TOTAL_BUDGET_SECONDS:
            raise TrancheError("the amended CPU tranche exceeded 12h")
        record["status"] = "complete"
        record["total_wall_seconds"] = int(time.time()
                                           - record["started_unix"])
        _persist("run_record_final", record)
        return {"execution_bundle_sha256": exec_sha,
                "run_dir": str(out_dir), "record": record}
    except BaseException as error:
        record["status"] = "aborted"
        record["error"] = f"{type(error).__name__}: {error}"
        record["total_wall_seconds"] = int(time.time()
                                           - record["started_unix"])
        (out_dir / "run_record.json").write_text(
            json.dumps(record, indent=1), encoding="utf-8")
        raise
