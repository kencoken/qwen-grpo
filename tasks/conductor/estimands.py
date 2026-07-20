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

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from .types import VISIBILITY_CONDITIONS, InfrastructureError


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
    """§1.9 intervention estimates.

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

    **Confidence intervals** (Stage 1A): the cluster bootstrap resamples
    whole latent clusters *with replacement, paired across arms*, and
    recomputes this same full-sample statistic from the resampled raw rows
    each time. `cluster_weighted` is a diagnostic for reading the
    cluster structure, not the statistic the bootstrap resamples;
    `cluster_observation_counts` is carried so a resampler can reproduce
    per-cluster weights without re-reading the raw rows.
    """

    edge: tuple[str, str]
    n_total: int
    n_eligible: int
    intervention_ineligible: int
    eligibility_rate: float
    n_clusters: int
    base_accuracy: float
    corruption_accuracy: float
    corruption_drop: float
    old_answer_persistence: float
    counterfactual_consistency: float
    follow_through: float | None
    follow_through_rate: float
    cluster_weighted: Mapping[str, float]
    cluster_observation_counts: Mapping[str, int]

    def __deepcopy__(self, memo: dict) -> "InterventionReport":
        return self  # immutable; the mapping proxies are unpicklable

    def to_json(self) -> dict[str, Any]:
        """Explicit persistence form (Stage 1 is resumable);
        `dataclasses.asdict` cannot walk the mapping proxies."""
        return {
            "edge": list(self.edge),
            "n_total": self.n_total,
            "n_eligible": self.n_eligible,
            "intervention_ineligible": self.intervention_ineligible,
            "eligibility_rate": self.eligibility_rate,
            "n_clusters": self.n_clusters,
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


def intervention_report(outcomes: Sequence[EdgeOutcome]
                        ) -> InterventionReport:
    """Corruption, counterfactual consistency and persistence on one shared
    eligible set, with the eligibility rate attached."""
    if not outcomes:
        raise InfrastructureError("no intervention outcomes")
    edges = {o.edge for o in outcomes}
    if len(edges) != 1:
        raise InfrastructureError(f"outcomes span several edges: {edges}")
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

    # One denominator for every reported quantity.
    base = _group(eligible, lambda o: o.base_terminal == o.gold_answer)
    corrupted = _group(eligible, lambda o: o.mutated_terminal == o.gold_answer)
    counterfactual = _group(
        eligible, lambda o: o.mutated_terminal == o.counterfactual_gold)
    if not (set(base) == set(corrupted) == set(counterfactual)):
        raise InfrastructureError("paired estimates lost cluster alignment")
    for cluster in base:
        if not (len(base[cluster]) == len(corrupted[cluster])
                == len(counterfactual[cluster])):
            raise InfrastructureError(
                f"cluster {cluster}: unequal denominators across estimates")

    followed = [o for o in eligible if o.downstream_path_succeeded]
    follow_through = None
    follow_through_clustered = None
    if followed:
        followed_group = _group(
            followed, lambda o: o.mutated_terminal == o.counterfactual_gold)
        # The conditioned diagnostic uses the same weighting rule as the
        # primary estimate it is reported alongside.
        follow_through = _full_sample(followed_group)
        follow_through_clustered = _cluster_weighted(followed_group)

    base_accuracy = _full_sample(base)
    # Corruption accuracy and old-answer persistence are the same
    # comparison (mutated terminal vs the stored gold) read as two gates:
    # the drop from baseline, and the residual rate itself.
    corruption_accuracy = _full_sample(corrupted)
    clustered = {
        "base_accuracy": _cluster_weighted(base),
        "corruption_accuracy": _cluster_weighted(corrupted),
        "corruption_drop": _cluster_weighted(base) - _cluster_weighted(
            corrupted),
        "old_answer_persistence": _cluster_weighted(corrupted),
        "counterfactual_consistency": _cluster_weighted(counterfactual),
    }
    if follow_through_clustered is not None:
        clustered["follow_through"] = follow_through_clustered
    return InterventionReport(
        edge=next(iter(edges)),
        n_total=len(outcomes),
        n_eligible=len(eligible),
        intervention_ineligible=len(outcomes) - len(eligible),
        eligibility_rate=len(eligible) / len(outcomes),
        n_clusters=len(base),
        base_accuracy=base_accuracy,
        corruption_accuracy=corruption_accuracy,
        corruption_drop=base_accuracy - corruption_accuracy,
        old_answer_persistence=corruption_accuracy,
        counterfactual_consistency=_full_sample(counterfactual),
        follow_through=follow_through,
        follow_through_rate=len(followed) / len(eligible),
        cluster_weighted=MappingProxyType(clustered),
        cluster_observation_counts=MappingProxyType(
            {cluster: len(values) for cluster, values in base.items()}))


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
        # `type(...) is bool` rather than isinstance: 0/1 are valid ints
        # but would let `correct=2` through the same door.
        for field in ("public_numeric_collision", "correct",
                      "answer_in_subtask_detected"):
            value = getattr(outcome, field)
            if type(value) is not bool:
                raise InfrastructureError(
                    f"{field} must be a bool, got {value!r}")

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
