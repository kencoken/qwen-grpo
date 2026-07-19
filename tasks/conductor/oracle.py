"""Deployable oracle, controls, comparator — spec §1.8.

Assignments are tuples of endpoint indices in **stable node order
(n1, n2, n3)** — never positional order. Selection happens once, on
construction data, under cluster-weighted terminal accuracy; ties resolve
lexicographically; `positions` alone permutes a semantic assignment into
positional `worker_ids`.
"""

from __future__ import annotations

import itertools
from typing import Any, Iterable, Sequence

from .types import CELL_NODES, ENDPOINT_IDS

# Payoff surface: {assignment tuple -> {cluster_id -> [terminal correctness]}}
PayoffSurface = dict[tuple[int, ...], dict[str, list[float]]]


def enumerate_assignments(num_nodes: int) -> list[tuple[int, ...]]:
    """The 3^S assignment set, lexicographic order."""
    return list(itertools.product(ENDPOINT_IDS, repeat=num_nodes))


def cluster_weighted_accuracy(outcomes: dict[str, list[float]]) -> float:
    """Mean over latent clusters of the within-cluster mean (§1.8)."""
    if not outcomes:
        raise ValueError("empty payoff cell")
    return sum(sum(v) / len(v) for v in outcomes.values()) / len(outcomes)


def _argmax_lex(candidates: Iterable[tuple[Any, float]]) -> Any:
    """Argmax by accuracy; ties resolve to the smallest key in iteration
    order, so callers pass candidates in the frozen tie order."""
    best_key, best_acc = None, None
    for key, acc in candidates:
        if best_acc is None or acc > best_acc:
            best_key, best_acc = key, acc
    return best_key


def select_deployable(surface: PayoffSurface) -> tuple[int, ...]:
    """Frozen executable selection rule: argmax of cluster-weighted terminal
    accuracy over the full enumeration; ties → lexicographically smallest
    endpoint-index tuple."""
    keys = sorted(surface)
    return _argmax_lex((k, cluster_weighted_accuracy(surface[k]))
                       for k in keys)


def node_runner_up(surface: PayoffSurface, deployable: tuple[int, ...],
                   node_index: int) -> tuple[int, ...]:
    """Best alternative endpoint at one node, all others fixed at the
    deployable assignment; ties → lowest endpoint index."""
    candidates = []
    for endpoint in ENDPOINT_IDS:
        if endpoint == deployable[node_index]:
            continue
        alt = deployable[:node_index] + (endpoint,) + deployable[node_index + 1:]
        candidates.append((alt, cluster_weighted_accuracy(surface[alt])))
    return _argmax_lex(candidates)


def best_fixed(surface: PayoffSurface) -> tuple[int, ...]:
    """§1.8 control: best of the three constant assignments, same objective
    and tie rule (context-partitioning control, not selection)."""
    num_nodes = len(next(iter(surface)))
    constants = [(e,) * num_nodes for e in ENDPOINT_IDS]
    return _argmax_lex((c, cluster_weighted_accuracy(surface[c]))
                       for c in constants)


def uniform_random_accuracy(surface: PayoffSurface) -> float:
    """§1.8 `random` control: the exact uniform mean over the enumerated
    3^S payoff surface (analytic, never Monte Carlo)."""
    accs = [cluster_weighted_accuracy(surface[k]) for k in sorted(surface)]
    num_nodes = len(next(iter(surface)))
    assert len(accs) == 3 ** num_nodes, "surface must be the full enumeration"
    return sum(accs) / len(accs)


def select_best_one_call(accuracy_by_endpoint: dict[int, float]) -> int:
    """Argmax over the 3 endpoints; tie → lowest index (§1.8)."""
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
    if set(deployable_correct) != set(policy_correct):
        raise ValueError("gap must be paired on identical clusters")
    for cluster in deployable_correct:
        if len(deployable_correct[cluster]) != len(policy_correct[cluster]):
            raise ValueError(f"cluster {cluster}: unpaired examples")
    return (cluster_weighted_accuracy(deployable_correct)
            - cluster_weighted_accuracy(policy_correct))


routing_regret = signed_deployable_gap  # legacy metric name (§1.8, erratum 9)
