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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .types import InfrastructureError


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
    return sum(sum(v) / len(v) for v in values.values()) / len(values)


def _group(outcomes: Iterable[EdgeOutcome],
           score) -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = {}
    for outcome in outcomes:
        grouped.setdefault(outcome.cluster_id, []).append(
            float(score(outcome)))
    return grouped


@dataclass(frozen=True)
class InterventionReport:
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
    if followed:
        follow_through = _cluster_weighted(_group(
            followed, lambda o: o.mutated_terminal == o.counterfactual_gold))

    base_accuracy = _cluster_weighted(base)
    # Corruption accuracy and old-answer persistence are the same
    # comparison (mutated terminal vs the stored gold) read as two gates:
    # the drop from baseline, and the residual rate itself.
    corruption_accuracy = _cluster_weighted(corrupted)
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
        counterfactual_consistency=_cluster_weighted(counterfactual),
        follow_through=follow_through,
        follow_through_rate=len(followed) / len(eligible))


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


def headline_population(outcomes: Iterable[WorkflowOutcome]
                        ) -> list[WorkflowOutcome]:
    """The private, no-public-semantic-parameter-collision stratum."""
    return [o for o in outcomes
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
