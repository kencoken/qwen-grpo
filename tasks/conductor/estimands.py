"""Paired intervention estimand and collision-sensitivity scoring — spec
§1.9, §1.16.

Pure scoring over recorded executions: no runtime, no model calls. These
are the frozen 0A acceptance helpers that Stage 1A's calibration consumes.

Two invariants carry the causal claims and are enforced here rather than
documented:

- every reported intervention quantity is computed on the *identical*
  eligible edge-instance set, so corruption, counterfactual consistency and
  persistence share one denominator; and
- the eligibility rate travels with every gate, because these are
  conditional causal estimates and their conditioning fraction is part of
  the result.

**Weighting differs by section, deliberately.** §1.9 names *full-sample
(eligible-set) accuracy* as the primary intervention metric, with
clustering entering through paired comparisons and the cluster bootstrap.
§1.8's oracle objective is *cluster-weighted*, and §1.16's sensitivity pair
is specified on "the same cluster weights". Each estimator below follows
its own section, and `InterventionReport` carries the equal-cluster values
alongside the primary ones so a gate can never be read off the wrong rule.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from .types import (
    CELL_INTERVENTION_EDGES, CELL_NODES, NAMESPACES, VISIBILITY_CONDITIONS,
    InfrastructureError, parse_latent_program_id, parse_render_instance_id,
)


# --- §1.9 intervention estimand ---------------------------------------------

@dataclass(frozen=True)
class EdgeOutcome:
    """One (latent cluster, rendered observation, edge) record.

    `eligible` is decided once, from the *base* execution — every parent of
    the downstream node succeeded — never from the mutated run.
    """

    cluster_id: str            # latent_program_id
    observation_id: str        # render_instance_id
    edge: tuple[str, str]
    eligible: bool
    override_applied: bool
    gold_answer: int
    counterfactual_gold: int
    base_terminal: int | None
    mutated_terminal: int | None
    downstream_path_succeeded: bool


# Per-cluster sufficient statistics: enough to recompute every reported
# quantity under a cluster bootstrap, including eligibility and
# follow-through, and including clusters with no eligible observations.
_SUFFICIENT_STATISTIC_FIELDS = ("n_total", "n_eligible", "base", "corrupted",
                                "counterfactual", "followed",
                                "followed_successes")


def _require_rate(value: Any, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise InfrastructureError(
            f"{field} must be a finite rate in [0, 1], got {value!r}")


def _require_count(value: Any, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InfrastructureError(
            f"{field} must be a non-negative int, got {value!r}")


def _require_bool(value: Any, field: str) -> None:
    # `type(...) is bool`: 0/1 are valid ints and non-empty strings such as
    # "false" are truthy, either of which would silently read as True.
    if type(value) is not bool:
        raise InfrastructureError(f"{field} must be a bool, got {value!r}")


def _require_int(value: Any, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InfrastructureError(f"{field} must be an int, got {value!r}")


def _require_optional_int(value: Any, field: str) -> None:
    if value is None:
        return
    _require_int(value, field)


def _require_identity(cluster_id: Any, observation_id: Any,
                      visibility: str | None = None) -> None:
    """Persisted rows carry canonical ids; the metadata they encode must
    agree with the row's own fields.

    An observation naming cluster A and ending in `:visible`, filed under
    cluster B as `private`, would otherwise score normally inside the
    private headline population.
    """
    try:
        latent = parse_latent_program_id(cluster_id)
        render_id = parse_render_instance_id(observation_id)
    except ValueError as exc:
        raise InfrastructureError(f"malformed row identity: {exc}") from exc
    if render_id.latent_program_id != cluster_id:
        raise InfrastructureError(
            f"observation {observation_id!r} is filed under cluster "
            f"{cluster_id!r} but names {render_id.latent_program_id!r}")
    if visibility is not None and render_id.visibility_condition != visibility:
        raise InfrastructureError(
            f"observation {observation_id!r} encodes visibility "
            f"{render_id.visibility_condition!r}, row says {visibility!r}")
    return latent


def base_eligibility(reference_program: dict[str, Any], downstream: str,
                     base_steps: Sequence[Any]) -> bool:
    """Eligible iff every parent of `downstream` succeeded in the base run.

    `base_steps` are the executor's StepRecords in workflow-position order.
    """
    node = next((n for n in reference_program["nodes"]
                 if n["id"] == downstream), None)
    if node is None:
        raise InfrastructureError(f"unknown node {downstream!r}")
    positions = reference_program["positions"]
    parents = [ref["node"] for ref in node["args"].values() if "node" in ref]
    for parent in parents:
        record = base_steps[positions.index(parent)]
        result = getattr(record, "result", None)
        if result is None or result.status != "success":
            return False
    return True


def _cluster_weighted(values: dict[str, list[float]]) -> float:
    """Mean over clusters of the within-cluster mean (§1.8's convention)."""
    return sum(sum(v) / len(v) for v in values.values()) / len(values)


def _full_sample(values: dict[str, list[float]]) -> float:
    """Unweighted mean over every observation — §1.9's primary metric."""
    flat = [v for group in values.values() for v in group]
    return sum(flat) / len(flat)


def _group(outcomes: Iterable[EdgeOutcome],
           score) -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = {}
    for outcome in outcomes:
        grouped.setdefault(outcome.cluster_id, []).append(
            float(score(outcome)))
    return grouped


@dataclass(frozen=True)
class InterventionReport:
    """§1.9 intervention estimates for **one** (cell, split, edge).

    The headline fields are **full-sample eligible-set accuracies**, which
    §1.9 names as the primary metric. That differs deliberately from the
    §1.8 oracle objective, which is cluster-weighted: clustering enters
    §1.9 through *paired comparisons and the cluster bootstrap over latent
    programs*, not through the point estimate. The equal-cluster values are
    reported alongside in `cluster_weighted` for those paired comparisons,
    never as the gate value.

    Example of the difference: two eligible correct observations in cluster
    A and one eligible incorrect observation in cluster B give a full-sample
    accuracy of 2/3 but an equal-cluster estimate of 1/2. Eligibility can
    genuinely differ between renderings of one latent program, because base
    worker success depends on the rendered prompt, so the two can diverge on
    well-formed data.

    **Identity and per-cluster sufficient statistics are the source of
    truth**; every other field is derived from them by `_derive`, which is
    the only constructor used by both live computation and deserialization.
    Redundant headline values are still serialized for readability, and
    `from_json` recomputes and compares *all* of them, so a hand-edited
    artifact cannot load.

    **Scope**: this is a structural, descriptive point estimator. Binding
    the rows to the registered population and to one execution environment,
    and wrapping the estimate in the pre-registered sequential inference,
    are Stage-1A `calibrate.py` responsibilities (see
    `oracle.GATE_PROVENANCE_REQUIREMENT`). No number here is a Stage-1 gate
    result on its own.

    **Confidence intervals** (Stage 1A): the cluster bootstrap resamples
    whole latent clusters *with replacement, paired across arms*, and
    recomputes this same full-sample statistic from the resampled rows.
    `cluster_successes` carries what that needs, including clusters with
    zero eligible observations, since resampling draws from the original
    latent-program population.
    """

    cell_id: str
    namespace: str
    edge: tuple[str, str]
    cluster_successes: Mapping[str, Mapping[str, int]]
    n_total: int
    n_eligible: int
    intervention_ineligible: int
    eligibility_rate: float
    n_population_clusters: int
    n_eligible_clusters: int
    base_accuracy: float
    corruption_accuracy: float
    corruption_drop: float
    old_answer_persistence: float
    counterfactual_consistency: float
    follow_through: float | None
    follow_through_rate: float
    cluster_weighted: Mapping[str, float]
    cluster_observation_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "cluster_successes", MappingProxyType({
            cluster: MappingProxyType(dict(values))
            for cluster, values in self.cluster_successes.items()}))
        for name in ("cluster_weighted", "cluster_observation_counts"):
            object.__setattr__(self, name,
                               MappingProxyType(dict(getattr(self, name))))

    def __deepcopy__(self, memo: dict) -> "InterventionReport":
        return self  # every nested mapping is frozen above

    def to_json(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "namespace": self.namespace,
            "edge": list(self.edge),
            "cluster_successes": {cluster: dict(values) for cluster, values
                                  in self.cluster_successes.items()},
            "n_total": self.n_total,
            "n_eligible": self.n_eligible,
            "intervention_ineligible": self.intervention_ineligible,
            "eligibility_rate": self.eligibility_rate,
            "n_population_clusters": self.n_population_clusters,
            "n_eligible_clusters": self.n_eligible_clusters,
            "base_accuracy": self.base_accuracy,
            "corruption_accuracy": self.corruption_accuracy,
            "corruption_drop": self.corruption_drop,
            "old_answer_persistence": self.old_answer_persistence,
            "counterfactual_consistency": self.counterfactual_consistency,
            "follow_through": self.follow_through,
            "follow_through_rate": self.follow_through_rate,
            "cluster_weighted": dict(self.cluster_weighted),
            "cluster_observation_counts":
                dict(self.cluster_observation_counts),
        }

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "InterventionReport":
        """Rebuild from identity + statistics, then require every stored
        redundant field to equal its derived value."""
        if not isinstance(obj, Mapping):
            raise InfrastructureError("report JSON must be an object")
        expected_keys = {f.name for f in fields(cls)}
        if set(obj) != expected_keys:
            raise InfrastructureError(
                f"report JSON keys must be exactly {sorted(expected_keys)}, "
                f"got {sorted(obj)}")
        edge = obj["edge"]
        if not isinstance(edge, (list, tuple)) or len(edge) != 2 \
                or not all(isinstance(node, str) for node in edge):
            raise InfrastructureError(f"malformed edge {edge!r}")
        statistics = obj["cluster_successes"]
        if not isinstance(statistics, Mapping) or not statistics:
            raise InfrastructureError(
                "cluster_successes must be a non-empty object")
        derived = _derive(obj["cell_id"], obj["namespace"], tuple(edge),
                          statistics)
        stored = dict(obj)
        for name in ("cell_id", "namespace", "cluster_successes", "edge"):
            stored.pop(name)
        for name, value in stored.items():
            expected = getattr(derived, name)
            if isinstance(expected, Mapping):
                # Shape first: a null or list-valued mapping would raise a
                # raw TypeError/AttributeError, and a list would stay
                # mutable behind an object claiming to be frozen.
                if not isinstance(value, Mapping) or dict(value) != {
                        k: v for k, v in expected.items()}:
                    raise InfrastructureError(
                        f"{name} disagrees with the sufficient statistics")
            elif expected is None:
                if value is not None:
                    raise InfrastructureError(
                        f"{name} disagrees with the sufficient statistics")
            elif isinstance(value, bool) or not isinstance(
                    value, (int, float)) or abs(value - expected) > 1e-9:
                raise InfrastructureError(
                    f"{name} is {value!r}, derived {expected!r}")
        return derived


def _derive(cell_id: Any, namespace: Any, edge: tuple[str, str],
            statistics: Mapping[str, Mapping[str, int]]
            ) -> InterventionReport:
    """The single constructor: everything but identity and the per-cluster
    counts is a function of those counts, so consistency is a property of
    construction rather than a checklist."""
    if not isinstance(cell_id, str) or cell_id not in CELL_NODES:
        raise InfrastructureError(f"unknown cell_id {cell_id!r}")
    if not isinstance(namespace, str) or namespace not in NAMESPACES:
        raise InfrastructureError(f"unknown namespace {namespace!r}")
    if edge not in CELL_INTERVENTION_EDGES[cell_id]:
        raise InfrastructureError(
            f"edge {edge!r} is not a dependency edge of {cell_id}")

    counts: dict[str, dict[str, int]] = {}
    for cluster, values in statistics.items():
        if not isinstance(cluster, str):
            raise InfrastructureError(f"cluster id {cluster!r} is not a str")
        try:
            latent = parse_latent_program_id(cluster)
        except ValueError as exc:
            raise InfrastructureError(
                f"cluster id {cluster!r}: {exc}") from exc
        if latent.cell_id != cell_id or latent.namespace != namespace:
            raise InfrastructureError(
                f"cluster {cluster} is {latent.cell_id}/{latent.namespace}, "
                f"report is {cell_id}/{namespace}")
        if not isinstance(values, Mapping) \
                or set(values) != set(_SUFFICIENT_STATISTIC_FIELDS):
            raise InfrastructureError(
                f"cluster {cluster}: sufficient statistics must be exactly "
                f"{sorted(_SUFFICIENT_STATISTIC_FIELDS)}")
        for key, value in values.items():
            _require_count(value, f"{cluster}.{key}")
        if values["n_eligible"] > values["n_total"]:
            raise InfrastructureError(
                f"cluster {cluster}: n_eligible exceeds n_total")
        for key in ("base", "corrupted", "counterfactual"):
            if values[key] > values["n_eligible"]:
                raise InfrastructureError(
                    f"cluster {cluster}: {key} exceeds n_eligible")
        if values["followed_successes"] > values["followed"] \
                or values["followed"] > values["n_eligible"]:
            raise InfrastructureError(
                f"cluster {cluster}: inconsistent follow-through counts")
        counts[cluster] = dict(values)

    n_total = sum(v["n_total"] for v in counts.values())
    n_eligible = sum(v["n_eligible"] for v in counts.values())
    if not n_total:
        raise InfrastructureError("no intervention observations")
    if not n_eligible:
        raise InfrastructureError(
            "no eligible instances; intervention gates are undefined")
    eligible_clusters = [c for c, v in counts.items() if v["n_eligible"]]

    def full_sample(key: str) -> float:
        return sum(counts[c][key] for c in counts) / n_eligible

    def clustered(key: str) -> float:
        return sum(counts[c][key] / counts[c]["n_eligible"]
                   for c in eligible_clusters) / len(eligible_clusters)

    base_accuracy = full_sample("base")
    corruption_accuracy = full_sample("corrupted")
    counterfactual = full_sample("counterfactual")
    followed = sum(v["followed"] for v in counts.values())
    follow_through = (sum(v["followed_successes"] for v in counts.values())
                      / followed) if followed else None

    cluster_weighted = {
        "base_accuracy": clustered("base"),
        "corruption_accuracy": clustered("corrupted"),
        "corruption_drop": clustered("base") - clustered("corrupted"),
        "old_answer_persistence": clustered("corrupted"),
        "counterfactual_consistency": clustered("counterfactual"),
    }
    followed_clusters = [c for c, v in counts.items() if v["followed"]]
    if followed_clusters:
        cluster_weighted["follow_through"] = sum(
            counts[c]["followed_successes"] / counts[c]["followed"]
            for c in followed_clusters) / len(followed_clusters)

    return InterventionReport(
        cell_id=cell_id, namespace=namespace, edge=edge,
        cluster_successes=counts,
        n_total=n_total, n_eligible=n_eligible,
        intervention_ineligible=n_total - n_eligible,
        eligibility_rate=n_eligible / n_total,
        n_population_clusters=len(counts),
        n_eligible_clusters=len(eligible_clusters),
        base_accuracy=base_accuracy,
        corruption_accuracy=corruption_accuracy,
        corruption_drop=base_accuracy - corruption_accuracy,
        # The same comparison (mutated terminal vs the stored gold) read as
        # two gates: the drop from baseline, and the residual rate itself.
        old_answer_persistence=corruption_accuracy,
        counterfactual_consistency=counterfactual,
        follow_through=follow_through,
        follow_through_rate=followed / n_eligible,
        cluster_weighted=cluster_weighted,
        cluster_observation_counts={c: counts[c]["n_eligible"]
                                    for c in eligible_clusters})


def _validate_edge_rows(outcomes: Sequence[EdgeOutcome]) -> tuple[str, str]:
    """Total validation of persisted intervention rows; returns the single
    (cell_id, namespace) population they describe.

    Without it, string values such as `"false"` for `eligible`,
    `override_applied` and `downstream_path_succeeded` all read as true,
    reporting an eligibility rate and follow-through of 1.0.
    """
    populations, edges = set(), set()
    by_cluster: dict[str, list[EdgeOutcome]] = {}
    for outcome in outcomes:
        if not isinstance(outcome, EdgeOutcome):
            raise InfrastructureError(
                f"expected EdgeOutcome rows, got {type(outcome).__name__}")
        latent = _require_identity(outcome.cluster_id, outcome.observation_id)
        edge = outcome.edge
        if not isinstance(edge, tuple) or len(edge) != 2 \
                or not all(isinstance(node, str) for node in edge):
            raise InfrastructureError(
                f"edge {edge!r} must be a (u, v) tuple of node ids")
        # Direction and adjacency both matter: an intervention overrides a
        # parent and measures its child, so a reversed pair, a self-edge or
        # a fork sibling pair is not an intervention edge.
        legal = CELL_INTERVENTION_EDGES[latent.cell_id]
        if edge not in legal:
            raise InfrastructureError(
                f"edge {edge!r} is not a dependency edge of "
                f"{latent.cell_id}; legal edges are {list(legal)}")
        for name in ("eligible", "override_applied",
                     "downstream_path_succeeded"):
            _require_bool(getattr(outcome, name), name)
        # Golds are recorded by the generator and always present; only the
        # executed terminals can legitimately be absent (a failed run).
        for name in ("gold_answer", "counterfactual_gold"):
            _require_int(getattr(outcome, name), name)
        for name in ("base_terminal", "mutated_terminal"):
            _require_optional_int(getattr(outcome, name), name)
        # §3: the replacement provably changes the sink, so the mutated
        # target must differ from the original. Equal targets would count
        # one execution as both preserving the old answer and following
        # the counterfactual, making the diagnostic uninterpretable.
        if outcome.counterfactual_gold == outcome.gold_answer:
            raise InfrastructureError(
                f"{outcome.cluster_id}: counterfactual_gold equals "
                f"gold_answer; the replacement must change the sink")
        # A complete downstream path that produced no terminal is a
        # contradiction, and would enter the follow-through denominator as
        # a failure.
        if outcome.downstream_path_succeeded \
                and outcome.mutated_terminal is None:
            raise InfrastructureError(
                f"{outcome.observation_id}: downstream_path_succeeded with "
                f"no mutated terminal")
        populations.add((latent.cell_id, latent.namespace))
        edges.add(edge)
        by_cluster.setdefault(outcome.cluster_id, []).append(outcome)

    # Stage-1 intervention gates are per cell and edge; `lookup_math` and
    # `math_code` both define n1->n2, so a shared edge tuple is not enough
    # to prove one population.
    if len(populations) != 1:
        raise InfrastructureError(
            f"a report covers one (cell, split): got {sorted(populations)}")
    if len(edges) != 1:
        raise InfrastructureError(f"outcomes span several edges: {edges}")

    # One replacement is drawn per (latent_program_id, edge) and each
    # latent is rendered several ways, so both targets are cluster-level
    # constants.
    for cluster, rows in by_cluster.items():
        for name in ("gold_answer", "counterfactual_gold"):
            values = {getattr(row, name) for row in rows}
            if len(values) != 1:
                raise InfrastructureError(
                    f"cluster {cluster}: {name} differs between renderings "
                    f"({sorted(values)}); it is a latent-level constant")
    return populations.pop()


def intervention_report(outcomes: Sequence[EdgeOutcome]
                        ) -> InterventionReport:
    """Corruption, counterfactual consistency and persistence on one shared
    eligible set, with the eligibility rate attached."""
    if not outcomes:
        raise InfrastructureError("no intervention outcomes")
    # Before anything that hashes or compares the rows: a list-valued edge
    # would otherwise raise a raw TypeError instead of a domain error.
    cell_id, namespace = _validate_edge_rows(outcomes)
    edge = outcomes[0].edge
    seen = {(o.cluster_id, o.observation_id) for o in outcomes}
    if len(seen) != len(outcomes):
        raise InfrastructureError("duplicate (cluster, observation) records")

    eligible = [o for o in outcomes if o.eligible]
    for outcome in eligible:
        if not outcome.override_applied:
            # §1.9: never an ordinary observation — the harness failed to
            # apply an override it had decided was applicable.
            raise InfrastructureError(
                f"override_applied=false on eligible instance "
                f"{outcome.cluster_id}/{outcome.observation_id} "
                f"(infrastructure failure, abort)")
    if not eligible:
        raise InfrastructureError(
            "no eligible instances; intervention gates are undefined")
    followed = [o for o in eligible if o.downstream_path_succeeded]
    return _derive(cell_id, namespace, edge,
                   _sufficient_statistics(outcomes, eligible, followed))


def _sufficient_statistics(outcomes, eligible, followed
                           ) -> dict[str, dict[str, int]]:
    """Everything a cluster bootstrap needs, per cluster.

    Includes latent clusters with **zero** eligible observations: a
    bootstrap resamples the original latent-program population, so
    dropping them would silently change the eligibility rate it can
    reproduce.
    """
    def tally(rows, predicate=None) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in rows:
            if predicate is None or predicate(row):
                out[row.cluster_id] = out.get(row.cluster_id, 0) + 1
        return out

    totals = tally(outcomes)
    eligible_counts = tally(eligible)
    followed_counts = tally(followed)
    return {
        cluster: {
            "n_total": totals[cluster],
            "n_eligible": eligible_counts.get(cluster, 0),
            "base": tally(eligible, lambda r: r.base_terminal == r.gold_answer
                          ).get(cluster, 0),
            "corrupted": tally(
                eligible,
                lambda r: r.mutated_terminal == r.gold_answer).get(cluster, 0),
            "counterfactual": tally(
                eligible, lambda r: r.mutated_terminal == r.counterfactual_gold
            ).get(cluster, 0),
            "followed": followed_counts.get(cluster, 0),
            "followed_successes": tally(
                followed, lambda r: r.mutated_terminal == r.counterfactual_gold
            ).get(cluster, 0),
        }
        for cluster in sorted(totals)}


# --- §1.16 collision sensitivity --------------------------------------------

@dataclass(frozen=True)
class WorkflowOutcome:
    """One scored workflow, with the metadata the headline stratum needs."""

    cluster_id: str
    observation_id: str
    visibility_condition: str
    public_numeric_collision: bool
    correct: bool
    answer_in_subtask_detected: bool


@dataclass(frozen=True)
class SensitivityScores:
    headline: float
    penalized: float
    n_clusters: int
    n_observations: int
    detected_observations: int


def _validate_workflow_rows(outcomes: Sequence[WorkflowOutcome]) -> None:
    """Totally validate persisted rows before any population filtering.

    Filtering silently drops whatever it does not recognise, so a malformed
    row must fail here rather than quietly leaving or entering the headline
    population: `correct=2` would produce a headline above 1.0, and
    `visibility_condition="Private"` would be excluded as though it were a
    visible observation.
    """
    if not outcomes:
        raise InfrastructureError("no workflow outcomes")
    for outcome in outcomes:
        if not isinstance(outcome, WorkflowOutcome):
            raise InfrastructureError(
                f"expected WorkflowOutcome rows, got {type(outcome).__name__}")
        for field in ("cluster_id", "observation_id"):
            value = getattr(outcome, field)
            if not isinstance(value, str) or not value:
                raise InfrastructureError(
                    f"{field} must be a non-empty str, got {value!r}")
        if outcome.visibility_condition not in VISIBILITY_CONDITIONS:
            raise InfrastructureError(
                f"visibility_condition {outcome.visibility_condition!r} is "
                f"not one of {VISIBILITY_CONDITIONS}")
        for field in ("public_numeric_collision", "correct",
                      "answer_in_subtask_detected"):
            _require_bool(getattr(outcome, field), field)
        # The ids encode cluster and visibility; both must agree with the
        # row, or a misfiled visible rendering scores inside the private
        # headline population.
        _require_identity(outcome.cluster_id, outcome.observation_id,
                          outcome.visibility_condition)

    seen = {(o.cluster_id, o.observation_id) for o in outcomes}
    if len(seen) != len(outcomes):
        raise InfrastructureError(
            "duplicate (cluster_id, observation_id) rows: a replayed trace "
            "would change the cluster mean silently")
    # An observation belongs to exactly one latent cluster.
    owners: dict[str, set[str]] = {}
    for outcome in outcomes:
        owners.setdefault(outcome.observation_id, set()).add(outcome.cluster_id)
    shared = sorted(o for o, clusters in owners.items() if len(clusters) > 1)
    if shared:
        raise InfrastructureError(
            f"observation ids filed under more than one cluster: {shared}")
    by_cluster: dict[str, set] = {}
    for outcome in outcomes:
        by_cluster.setdefault(outcome.cluster_id, set()).add(
            outcome.public_numeric_collision)
    inconsistent = sorted(c for c, values in by_cluster.items()
                          if len(values) > 1)
    if inconsistent:
        raise InfrastructureError(
            f"collision metadata is latent-level but differs between "
            f"renderings of clusters {inconsistent}")


def headline_population(outcomes: Iterable[WorkflowOutcome]
                        ) -> list[WorkflowOutcome]:
    """The private, no-public-semantic-parameter-collision stratum."""
    rows = list(outcomes)
    _validate_workflow_rows(rows)
    return [o for o in rows
            if o.visibility_condition == "private"
            and not o.public_numeric_collision]


def sensitivity_scores(outcomes: Iterable[WorkflowOutcome]
                       ) -> SensitivityScores:
    """Headline and detected-token-penalized scores on *exactly* the same
    population: same clusters, same observations, same cluster weights —
    only workflows with a detected answer-in-subtask event are recoded as
    incorrect. Numerically ≤ the headline by construction.

    The detector is a restricted proxy with incomplete recall and possible
    false positives: the penalized score bounds neither the true smuggling
    rate nor genuinely smuggling-free performance.
    """
    population = headline_population(outcomes)
    if not population:
        raise InfrastructureError("headline population is empty")
    headline = _group(population, lambda o: o.correct)
    penalized = _group(
        population,
        lambda o: o.correct and not o.answer_in_subtask_detected)
    if set(headline) != set(penalized):
        raise InfrastructureError("sensitivity populations differ")
    for cluster in headline:
        if len(headline[cluster]) != len(penalized[cluster]):
            raise InfrastructureError(
                f"cluster {cluster}: sensitivity denominators differ")
    headline_score = _cluster_weighted(headline)
    penalized_score = _cluster_weighted(penalized)
    if penalized_score > headline_score:
        raise InfrastructureError(
            "penalized score exceeds headline — recoding is not monotone")
    return SensitivityScores(
        headline=headline_score,
        penalized=penalized_score,
        n_clusters=len(headline),
        n_observations=len(population),
        detected_observations=sum(1 for o in population
                                  if o.answer_in_subtask_detected))
