"""Deployable oracle, controls, comparator — spec §1.8.

Assignments are tuples of endpoint indices in **stable node order
(n1, n2, n3)** — never positional order. Selection happens once, on
construction data, under cluster-weighted terminal accuracy; ties resolve
lexicographically; `positions` alone permutes a semantic assignment into
positional `worker_ids`.

Payoff data is **observation-keyed**:

    surface[candidate][cluster_id][observation_id] = correctness ∈ {0, 1}

Anonymous per-cluster lists could not prove that two candidates were scored
on the *same* renderings — equal counts would admit `{o1, o2}` against
`{o2, o3}`. Since selection freezes the Stage-2 routing target and
calibration is resumable, every selector consumes a `ValidatedSurface`
built by one of the validating constructors below; a raw mapping is never
accepted.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from .types import CELL_NODES, ENDPOINT_IDS

# Raw, unvalidated input shape.
RawSurface = Mapping[Any, Mapping[str, Mapping[str, float]]]


class PayoffSurfaceError(ValueError):
    """A payoff surface is incomplete, unpaired, or malformed.

    Selection freezes the Stage-2 routing target, and calibration is
    resumable — so a partially loaded or misassembled surface must fail
    loudly rather than silently become the deployable assignment.
    """


def enumerate_assignments(num_nodes: int) -> list[tuple[int, ...]]:
    """The 3^S assignment set, lexicographic order."""
    if num_nodes < 1:
        raise PayoffSurfaceError("a cell has at least one node")
    return list(itertools.product(ENDPOINT_IDS, repeat=num_nodes))


TWO_CALL_ORIENTATIONS = ("lookup_first", "code_first")  # frozen tie order


def enumerate_two_call_workflows() -> list[tuple[str, tuple[int, int]]]:
    """The 18-workflow contraction family (D12): orientation × endpoint
    pair, in the frozen tie order (lookup-first < code-first, then
    lexicographic endpoint tuple)."""
    return [(orientation, pair)
            for orientation in TWO_CALL_ORIENTATIONS
            for pair in itertools.product(ENDPOINT_IDS, repeat=2)]


@dataclass(frozen=True)
class ValidatedSurface:
    """A complete, observation-paired payoff surface over a candidate set.

    `candidates` is the enumerated candidate list **in frozen tie order**,
    so argmax ties resolve by iteration order without re-deriving the rule
    at each call site.
    """

    kind: str                                   # assignment | one_call | two_call
    cell_id: str
    candidates: tuple[Any, ...]
    clusters: tuple[str, ...]
    observations: Mapping[str, tuple[str, ...]]  # cluster -> observation ids
    data: Mapping[Any, Mapping[str, Mapping[str, float]]]

    @property
    def num_nodes(self) -> int:
        if self.kind != "assignment":
            raise PayoffSurfaceError(f"{self.kind} surfaces have no node arity")
        return len(self.candidates[0])

    @property
    def n_observations(self) -> int:
        return sum(len(obs) for obs in self.observations.values())

    def accuracy(self, candidate: Any) -> float:
        """§1.8 objective: cluster-weighted terminal accuracy — the mean
        over latent clusters of the within-cluster mean."""
        outcomes = self.data[candidate]
        return sum(
            sum(outcomes[cluster].values()) / len(outcomes[cluster])
            for cluster in self.clusters) / len(self.clusters)

    def full_sample_accuracy(self, candidate: Any) -> float:
        """Unweighted mean over every observation — reported as a
        diagnostic; §1.8 selection always uses `accuracy`."""
        outcomes = self.data[candidate]
        values = [v for cluster in self.clusters
                  for v in outcomes[cluster].values()]
        return sum(values) / len(values)


def _validate(raw: RawSurface, kind: str, cell_id: str,
              candidates: Sequence[Any]) -> ValidatedSurface:
    if not isinstance(raw, Mapping) or not raw:
        raise PayoffSurfaceError("payoff surface is empty")
    expected = list(candidates)
    try:
        present = set(raw)
    except TypeError as exc:  # unhashable keys
        raise PayoffSurfaceError(f"malformed candidate keys: {exc}") from exc
    missing = [c for c in expected if c not in present]
    unexpected = [c for c in present if c not in set(expected)]
    if missing or unexpected:
        raise PayoffSurfaceError(
            f"{kind} surface is not the full enumeration of "
            f"{len(expected)} candidates (missing {missing}, unexpected "
            f"{unexpected})")

    reference_clusters: tuple[str, ...] | None = None
    reference_obs: dict[str, tuple[str, ...]] | None = None
    frozen: dict[Any, Mapping[str, Mapping[str, float]]] = {}

    for candidate in expected:
        outcomes = raw[candidate]
        if not isinstance(outcomes, Mapping) or not outcomes:
            raise PayoffSurfaceError(f"{candidate!r}: no cluster observations")
        clusters = tuple(sorted(outcomes))
        per_cluster: dict[str, Mapping[str, float]] = {}
        obs_ids: dict[str, tuple[str, ...]] = {}
        for cluster in clusters:
            if not isinstance(cluster, str):
                raise PayoffSurfaceError(f"cluster id {cluster!r} is not a str")
            values = outcomes[cluster]
            if not isinstance(values, Mapping) or not values:
                raise PayoffSurfaceError(
                    f"{candidate!r}/{cluster}: observations must be a "
                    f"non-empty {{observation_id: correctness}} mapping")
            for obs_id, value in values.items():
                if not isinstance(obs_id, str):
                    raise PayoffSurfaceError(
                        f"{candidate!r}/{cluster}: observation id "
                        f"{obs_id!r} is not a str")
                # Terminal correctness is binary. Accepting any value in
                # [0, 1] would let the 0.5 GRPO reward for a well-formed
                # world failure be averaged into a terminal-accuracy
                # surface.
                if isinstance(value, bool) or value not in (0, 1):
                    raise PayoffSurfaceError(
                        f"{candidate!r}/{cluster}/{obs_id}: terminal "
                        f"correctness must be 0 or 1, got {value!r}")
            obs_ids[cluster] = tuple(sorted(values))
            per_cluster[cluster] = MappingProxyType(
                {k: float(v) for k, v in values.items()})

        if reference_clusters is None:
            reference_clusters, reference_obs = clusters, obs_ids
        else:
            if clusters != reference_clusters:
                raise PayoffSurfaceError(
                    f"{candidate!r}: cluster support differs from the first "
                    f"candidate (comparisons must be paired)")
            if obs_ids != reference_obs:
                raise PayoffSurfaceError(
                    f"{candidate!r}: observation ids differ from the first "
                    f"candidate (comparisons must be paired on the same "
                    f"renderings)")
        frozen[candidate] = MappingProxyType(per_cluster)

    assert reference_clusters is not None and reference_obs is not None
    return ValidatedSurface(
        kind=kind, cell_id=cell_id, candidates=tuple(expected),
        clusters=reference_clusters,
        observations=MappingProxyType(dict(reference_obs)),
        data=MappingProxyType(frozen))


def _check_assignment(assignment: Any, num_nodes: int) -> None:
    if not isinstance(assignment, tuple):
        raise PayoffSurfaceError(
            f"assignment {assignment!r} must be a tuple of endpoint indices")
    if len(assignment) != num_nodes:
        raise PayoffSurfaceError(
            f"assignment {assignment!r} must have {num_nodes} entries")
    for endpoint in assignment:
        # `0.0` and `False` both compare and hash equal to 0, so an
        # identity check on the type is required, not membership alone.
        if type(endpoint) is not int or endpoint not in ENDPOINT_IDS:
            raise PayoffSurfaceError(
                f"assignment {assignment!r} has a non-integer or "
                f"out-of-range endpoint id")


def validate_payoff_surface(raw: RawSurface, cell_id: str) -> ValidatedSurface:
    """Validate a 3^S assignment surface for a named cell. `cell_id` is
    required: inferring S from the data cannot catch a surface built for
    the wrong cell."""
    if cell_id not in CELL_NODES:
        raise PayoffSurfaceError(f"unknown cell_id {cell_id!r}")
    num_nodes = len(CELL_NODES[cell_id])
    if isinstance(raw, Mapping):
        for candidate in raw:
            _check_assignment(candidate, num_nodes)
    return _validate(raw, "assignment", cell_id,
                     enumerate_assignments(num_nodes))


def validate_one_call_surface(raw: RawSurface, cell_id: str
                              ) -> ValidatedSurface:
    """Best one-call whole-task control (§1.11 B5): one candidate per
    endpoint, on the same observation support as the assignment surface."""
    return _validate(raw, "one_call", cell_id, list(ENDPOINT_IDS))


def validate_two_call_surface(raw: RawSurface, cell_id: str
                              ) -> ValidatedSurface:
    """The 18-workflow contraction family (D12)."""
    return _validate(raw, "two_call", cell_id, enumerate_two_call_workflows())


def _require_surface(surface: Any, kind: str) -> ValidatedSurface:
    if not isinstance(surface, ValidatedSurface):
        raise PayoffSurfaceError(
            "selectors consume a ValidatedSurface; call the matching "
            "validate_*_surface constructor first")
    if surface.kind != kind:
        raise PayoffSurfaceError(
            f"expected a {kind} surface, got {surface.kind}")
    return surface


def _argmax_in_tie_order(surface: ValidatedSurface,
                         candidates: Iterable[Any]) -> Any:
    """Argmax by cluster-weighted accuracy; ties resolve to the first
    candidate in the surface's frozen tie order."""
    best_key, best_acc = None, None
    for candidate in candidates:
        accuracy = surface.accuracy(candidate)
        if best_acc is None or accuracy > best_acc:
            best_key, best_acc = candidate, accuracy
    if best_key is None:
        raise PayoffSurfaceError("no candidates to select from")
    return best_key


def select_deployable(surface: ValidatedSurface) -> tuple[int, ...]:
    """Frozen executable selection rule: argmax of cluster-weighted terminal
    accuracy over the full enumeration; ties → lexicographically smallest
    endpoint-index tuple."""
    vs = _require_surface(surface, "assignment")
    return _argmax_in_tie_order(vs, vs.candidates)


def node_runner_up(surface: ValidatedSurface, deployable: tuple[int, ...],
                   node_index: int) -> tuple[int, ...]:
    """Best alternative endpoint at one node, all others fixed at the
    deployable assignment; ties → lowest endpoint index."""
    vs = _require_surface(surface, "assignment")
    _check_assignment(deployable, vs.num_nodes)
    if type(node_index) is not int or not 0 <= node_index < vs.num_nodes:
        raise PayoffSurfaceError(f"node_index {node_index!r} out of range")
    alternatives = [
        deployable[:node_index] + (endpoint,) + deployable[node_index + 1:]
        for endpoint in ENDPOINT_IDS if endpoint != deployable[node_index]]
    return _argmax_in_tie_order(vs, alternatives)


def best_fixed(surface: ValidatedSurface) -> tuple[int, ...]:
    """§1.8 control: best of the three constant assignments, same objective
    and tie rule (context-partitioning control, not selection)."""
    vs = _require_surface(surface, "assignment")
    constants = [(e,) * vs.num_nodes for e in ENDPOINT_IDS]
    return _argmax_in_tie_order(vs, constants)


def uniform_random_accuracy(surface: ValidatedSurface) -> float:
    """§1.8 `random` control: the exact uniform mean over the enumerated
    3^S payoff surface (analytic, never Monte Carlo)."""
    vs = _require_surface(surface, "assignment")
    return sum(vs.accuracy(c) for c in vs.candidates) / len(vs.candidates)


def select_best_one_call(surface: ValidatedSurface) -> int:
    """Argmax over the 3 endpoints; tie → lowest index (§1.8)."""
    vs = _require_surface(surface, "one_call")
    return _argmax_in_tie_order(vs, vs.candidates)


def select_best_two_call(surface: ValidatedSurface
                         ) -> tuple[str, tuple[int, int]]:
    """Argmax over the 18-workflow family; tie → frozen order
    (lookup-first < code-first, then lexicographic endpoint tuple)."""
    vs = _require_surface(surface, "two_call")
    return _argmax_in_tie_order(vs, vs.candidates)


def semantic_to_positional(assignment: Sequence[int], cell_id: str,
                           positions: Sequence[str]) -> list[int]:
    """Permute a stable-node-order assignment into positional worker_ids
    using `positions` alone (§1.8)."""
    nodes = CELL_NODES[cell_id]
    if len(assignment) != len(nodes) or sorted(positions) != sorted(nodes):
        raise ValueError("assignment/positions shape mismatch")
    index = {node: i for i, node in enumerate(nodes)}
    return [assignment[index[node]] for node in positions]


def signed_deployable_gap(deployable_correct: Mapping[str, Mapping[str, float]],
                          policy_correct: Mapping[str, Mapping[str, float]]
                          ) -> float:
    """§1.8 primary Stage-2 comparator, paired and cluster-weighted on the
    same examples; malformed policy actions enter as correctness 0 (callers
    encode that); unclipped, may be negative. `routing_regret` is a legacy
    alias for this quantity.

    Both sides are observation-keyed so the pairing is checked by identity,
    not by count.
    """
    if not deployable_correct or set(deployable_correct) != set(policy_correct):
        raise PayoffSurfaceError("gap must be paired on identical clusters")
    for cluster, deployable_obs in deployable_correct.items():
        policy_obs = policy_correct[cluster]
        if not isinstance(deployable_obs, Mapping) \
                or not isinstance(policy_obs, Mapping):
            raise PayoffSurfaceError(
                f"cluster {cluster}: observations must be "
                f"{{observation_id: correctness}} mappings")
        if not deployable_obs or set(deployable_obs) != set(policy_obs):
            raise PayoffSurfaceError(
                f"cluster {cluster}: unpaired observation ids")
        for side in (deployable_obs, policy_obs):
            for obs_id, value in side.items():
                if isinstance(value, bool) or value not in (0, 1):
                    raise PayoffSurfaceError(
                        f"cluster {cluster}/{obs_id}: terminal correctness "
                        f"must be 0 or 1, got {value!r}")

    def weighted(side: Mapping[str, Mapping[str, float]]) -> float:
        return sum(sum(obs.values()) / len(obs)
                   for obs in side.values()) / len(side)

    return weighted(deployable_correct) - weighted(policy_correct)


routing_regret = signed_deployable_gap  # legacy metric name (§1.8, erratum 9)
