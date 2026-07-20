"""Deployable oracle, controls, comparator — spec §1.8.

Assignments are tuples of endpoint indices in **stable node order
(n1, n2, n3)** — never positional order. Selection happens once, on
construction data, under cluster-weighted terminal accuracy; ties resolve
lexicographically; `positions` alone permutes a semantic assignment into
positional `worker_ids`.
"""

from __future__ import annotations

import itertools
import math
from typing import Any, Iterable, Sequence

from .types import CELL_NODES, ENDPOINT_IDS

# Payoff surface: {assignment tuple -> {cluster_id -> [terminal correctness]}}
PayoffSurface = dict[tuple[int, ...], dict[str, list[float]]]


class PayoffSurfaceError(ValueError):
    """A payoff surface is incomplete, unpaired, or malformed.

    Selection freezes the Stage-2 routing target, and calibration is
    resumable — so a partially loaded or interrupted surface must fail
    loudly rather than silently become the deployable assignment.
    """


def enumerate_assignments(num_nodes: int) -> list[tuple[int, ...]]:
    """The 3^S assignment set, lexicographic order."""
    return list(itertools.product(ENDPOINT_IDS, repeat=num_nodes))


def validate_payoff_surface(surface: PayoffSurface,
                            cell_id: str | None = None) -> int:
    """Require a complete, paired, well-formed surface; return S.

    Checks: the exact 3^S assignment set (for `cell_id`'s node count when
    given), legal endpoint ids and tuple lengths, identical non-empty
    cluster ids across assignments, identical non-empty observation counts
    within each cluster, and finite correctness values in [0, 1]. Raises
    PayoffSurfaceError — never `assert`, which vanishes under `python -O`.
    """
    if not isinstance(surface, dict) or not surface:
        raise PayoffSurfaceError("payoff surface is empty")
    lengths = {len(k) if isinstance(k, tuple) else None for k in surface}
    if lengths != {len(next(iter(surface)))} or None in lengths:
        raise PayoffSurfaceError("assignments must be tuples of one length")
    num_nodes = lengths.pop()
    if cell_id is not None:
        expected = len(CELL_NODES[cell_id])
        if num_nodes != expected:
            raise PayoffSurfaceError(
                f"{cell_id} has {expected} nodes, surface has {num_nodes}")
    for assignment in surface:
        for endpoint in assignment:
            if endpoint not in ENDPOINT_IDS or isinstance(endpoint, bool):
                raise PayoffSurfaceError(
                    f"illegal endpoint id in assignment {assignment}")
    complete = set(enumerate_assignments(num_nodes))
    if set(surface) != complete:
        missing = sorted(complete - set(surface))
        extra = sorted(set(surface) - complete)
        raise PayoffSurfaceError(
            f"surface is not the full 3^{num_nodes} enumeration "
            f"(missing {missing}, unexpected {extra})")

    reference_clusters: set[str] | None = None
    reference_counts: dict[str, int] | None = None
    for assignment in sorted(surface):
        outcomes = surface[assignment]
        if not isinstance(outcomes, dict) or not outcomes:
            raise PayoffSurfaceError(f"{assignment}: no cluster observations")
        counts = {}
        for cluster, values in outcomes.items():
            if not isinstance(values, (list, tuple)) or not values:
                raise PayoffSurfaceError(
                    f"{assignment}/{cluster}: empty observation list")
            for value in values:
                if isinstance(value, bool) or not isinstance(
                        value, (int, float)):
                    raise PayoffSurfaceError(
                        f"{assignment}/{cluster}: non-numeric correctness "
                        f"{value!r}")
                if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                    raise PayoffSurfaceError(
                        f"{assignment}/{cluster}: correctness {value!r} "
                        f"outside [0, 1]")
            counts[cluster] = len(values)
        if reference_clusters is None:
            reference_clusters, reference_counts = set(outcomes), counts
            continue
        if set(outcomes) != reference_clusters:
            raise PayoffSurfaceError(
                f"{assignment}: cluster support differs from the first "
                f"assignment (comparisons must be paired)")
        if counts != reference_counts:
            raise PayoffSurfaceError(
                f"{assignment}: per-cluster observation counts differ from "
                f"the first assignment (comparisons must be paired)")
    return num_nodes


def cluster_weighted_accuracy(outcomes: dict[str, list[float]]) -> float:
    """Mean over latent clusters of the within-cluster mean (§1.8)."""
    if not outcomes:
        raise PayoffSurfaceError("empty payoff cell")
    return sum(sum(v) / len(v) for v in outcomes.values()) / len(outcomes)


def _argmax_lex(candidates: Iterable[tuple[Any, float]]) -> Any:
    """Argmax by accuracy; ties resolve to the smallest key in iteration
    order, so callers pass candidates in the frozen tie order."""
    best_key, best_acc = None, None
    for key, acc in candidates:
        if best_acc is None or acc > best_acc:
            best_key, best_acc = key, acc
    return best_key


def select_deployable(surface: PayoffSurface,
                      cell_id: str | None = None) -> tuple[int, ...]:
    """Frozen executable selection rule: argmax of cluster-weighted terminal
    accuracy over the full enumeration; ties → lexicographically smallest
    endpoint-index tuple."""
    validate_payoff_surface(surface, cell_id)
    keys = sorted(surface)
    return _argmax_lex((k, cluster_weighted_accuracy(surface[k]))
                       for k in keys)


def node_runner_up(surface: PayoffSurface, deployable: tuple[int, ...],
                   node_index: int,
                   cell_id: str | None = None) -> tuple[int, ...]:
    """Best alternative endpoint at one node, all others fixed at the
    deployable assignment; ties → lowest endpoint index."""
    num_nodes = validate_payoff_surface(surface, cell_id)
    if not 0 <= node_index < num_nodes:
        raise PayoffSurfaceError(f"node_index {node_index} out of range")
    if len(deployable) != num_nodes or set(deployable) - set(ENDPOINT_IDS):
        raise PayoffSurfaceError(f"malformed assignment {deployable}")
    candidates = []
    for endpoint in ENDPOINT_IDS:
        if endpoint == deployable[node_index]:
            continue
        alt = deployable[:node_index] + (endpoint,) + deployable[node_index + 1:]
        candidates.append((alt, cluster_weighted_accuracy(surface[alt])))
    return _argmax_lex(candidates)


def best_fixed(surface: PayoffSurface,
               cell_id: str | None = None) -> tuple[int, ...]:
    """§1.8 control: best of the three constant assignments, same objective
    and tie rule (context-partitioning control, not selection)."""
    num_nodes = validate_payoff_surface(surface, cell_id)
    constants = [(e,) * num_nodes for e in ENDPOINT_IDS]
    return _argmax_lex((c, cluster_weighted_accuracy(surface[c]))
                       for c in constants)


def uniform_random_accuracy(surface: PayoffSurface,
                            cell_id: str | None = None) -> float:
    """§1.8 `random` control: the exact uniform mean over the enumerated
    3^S payoff surface (analytic, never Monte Carlo)."""
    validate_payoff_surface(surface, cell_id)
    accs = [cluster_weighted_accuracy(surface[k]) for k in sorted(surface)]
    return sum(accs) / len(accs)


def _validate_accuracy_domain(accuracy: dict, expected: Iterable,
                              label: str) -> None:
    expected = list(expected)
    if set(accuracy) != set(expected):
        raise PayoffSurfaceError(
            f"{label}: domain must be exactly the {len(expected)} enumerated "
            f"candidates")
    for key, value in accuracy.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise PayoffSurfaceError(
                f"{label}/{key}: accuracy {value!r} outside [0, 1]")


def select_best_one_call(accuracy_by_endpoint: dict[int, float]) -> int:
    """Argmax over the 3 endpoints; tie → lowest index (§1.8)."""
    _validate_accuracy_domain(accuracy_by_endpoint, ENDPOINT_IDS,
                              "best one-call")
    return _argmax_lex((e, accuracy_by_endpoint[e])
                       for e in sorted(accuracy_by_endpoint))


TWO_CALL_ORIENTATIONS = ("lookup_first", "code_first")  # frozen tie order


def enumerate_two_call_workflows() -> list[tuple[str, tuple[int, int]]]:
    """The 18-workflow contraction family (D12): orientation × endpoint
    pair, in the frozen tie order (lookup-first < code-first, then
    lexicographic endpoint tuple)."""
    return [(orientation, pair)
            for orientation in TWO_CALL_ORIENTATIONS
            for pair in itertools.product(ENDPOINT_IDS, repeat=2)]


def select_best_two_call(accuracy: dict[tuple[str, tuple[int, int]], float]
                         ) -> tuple[str, tuple[int, int]]:
    _validate_accuracy_domain(accuracy, enumerate_two_call_workflows(),
                              "best two-call")
    return _argmax_lex((wf, accuracy[wf])
                       for wf in enumerate_two_call_workflows())


def semantic_to_positional(assignment: Sequence[int], cell_id: str,
                           positions: Sequence[str]) -> list[int]:
    """Permute a stable-node-order assignment into positional worker_ids
    using `positions` alone (§1.8)."""
    nodes = CELL_NODES[cell_id]
    if len(assignment) != len(nodes) or sorted(positions) != sorted(nodes):
        raise ValueError("assignment/positions shape mismatch")
    index = {node: i for i, node in enumerate(nodes)}
    return [assignment[index[node]] for node in positions]


def signed_deployable_gap(deployable_correct: dict[str, list[float]],
                          policy_correct: dict[str, list[float]]) -> float:
    """§1.8 primary Stage-2 comparator, paired and cluster-weighted on the
    same examples; malformed policy actions enter as correctness 0 (callers
    encode that); unclipped, may be negative. `routing_regret` is a legacy
    alias for this quantity."""
    if not deployable_correct or set(deployable_correct) != set(policy_correct):
        raise PayoffSurfaceError("gap must be paired on identical clusters")
    for cluster in deployable_correct:
        if len(deployable_correct[cluster]) != len(policy_correct[cluster]):
            raise PayoffSurfaceError(f"cluster {cluster}: unpaired examples")
        for side in (deployable_correct[cluster], policy_correct[cluster]):
            if not side:
                raise PayoffSurfaceError(f"cluster {cluster}: no observations")
            for value in side:
                if isinstance(value, bool) or not isinstance(
                        value, (int, float)) or not math.isfinite(value) \
                        or not 0.0 <= value <= 1.0:
                    raise PayoffSurfaceError(
                        f"cluster {cluster}: correctness {value!r} outside "
                        f"[0, 1]")
    return (cluster_weighted_accuracy(deployable_correct)
            - cluster_weighted_accuracy(policy_correct))


routing_regret = signed_deployable_gap  # legacy metric name (§1.8, erratum 9)
