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

from .types import (
    CELL_NODES, ENDPOINT_IDS, parse_latent_program_id,
    parse_render_instance_id,
)

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


_SURFACE_KINDS = ("assignment", "one_call", "two_call")


def _candidate_to_json(kind: str, candidate: Any) -> Any:
    if kind == "assignment":
        return list(candidate)
    if kind == "one_call":
        return candidate
    return [candidate[0], list(candidate[1])]


def _candidate_from_json(kind: str, value: Any) -> Any:
    if kind == "assignment":
        return tuple(value)
    if kind == "one_call":
        return value
    return (value[0], tuple(value[1]))

# The 18-workflow contraction family is defined only for the fork/join
# cell (D12); there is no two-call shortcut for a one- or two-step cell.
TWO_CALL_CELLS = ("fork_join",)


def _expected_candidates(kind: str, cell_id: str) -> list[Any]:
    if kind == "assignment":
        return enumerate_assignments(len(CELL_NODES[cell_id]))
    if kind == "one_call":
        return list(ENDPOINT_IDS)
    if kind == "two_call":
        if cell_id not in TWO_CALL_CELLS:
            raise PayoffSurfaceError(
                f"the two-call shortcut family is not defined for {cell_id}")
        return enumerate_two_call_workflows()
    raise PayoffSurfaceError(f"unknown surface kind {kind!r}")


def _check_cluster_belongs(cluster_id: Any, cell_id: str) -> None:
    """Cluster ids are `latent_program_id`s, which name their own cell —
    so a surface can be bound to its cell by identity rather than by node
    arity alone (the three atomic cells all have one node)."""
    try:
        latent = parse_latent_program_id(cluster_id)
    except ValueError as exc:
        raise PayoffSurfaceError(
            f"cluster id {cluster_id!r} is not a latent_program_id: "
            f"{exc}") from exc
    if latent.cell_id != cell_id:
        raise PayoffSurfaceError(
            f"cluster {cluster_id!r} belongs to cell {latent.cell_id!r}, "
            f"not {cell_id!r}")


def _check_observation_belongs(observation_id: Any, cluster_id: str,
                               cell_id: str) -> None:
    try:
        render_id = parse_render_instance_id(observation_id)
    except ValueError as exc:
        raise PayoffSurfaceError(
            f"observation id {observation_id!r} is not a "
            f"render_instance_id: {exc}") from exc
    if render_id.latent.cell_id != cell_id:
        raise PayoffSurfaceError(
            f"observation {observation_id!r} belongs to cell "
            f"{render_id.latent.cell_id!r}, not {cell_id!r}")
    if render_id.latent_program_id != cluster_id:
        raise PayoffSurfaceError(
            f"observation {observation_id!r} is filed under cluster "
            f"{cluster_id!r} but names {render_id.latent_program_id!r}")


@dataclass(frozen=True)
class ValidatedSurface:
    """A complete, observation-paired payoff surface over a candidate set.

    `candidates` is the enumerated candidate list **in frozen tie order**,
    so argmax ties resolve by iteration order without re-deriving the rule
    at each call site.

    Build these with `validate_*_surface`. The invariants are re-checked in
    `__post_init__` so that a directly constructed instance — including one
    revived by a deserializer — cannot smuggle an unvalidated surface past
    the selectors.
    """

    kind: str                                   # assignment | one_call | two_call
    cell_id: str
    candidates: tuple[Any, ...]
    clusters: tuple[str, ...]
    observations: Mapping[str, tuple[str, ...]]  # cluster -> observation ids
    data: Mapping[Any, Mapping[str, Mapping[str, float]]]

    def __post_init__(self) -> None:
        if self.kind not in _SURFACE_KINDS:
            raise PayoffSurfaceError(f"unknown surface kind {self.kind!r}")
        if self.cell_id not in CELL_NODES:
            raise PayoffSurfaceError(f"unknown cell_id {self.cell_id!r}")
        expected = _expected_candidates(self.kind, self.cell_id)
        if tuple(self.candidates) != tuple(expected):
            raise PayoffSurfaceError(
                f"{self.kind} surface candidates are not the frozen "
                f"enumeration for {self.cell_id}")
        if set(self.data) != set(expected):
            raise PayoffSurfaceError("surface data does not cover every "
                                     "candidate exactly once")
        if not self.clusters:
            raise PayoffSurfaceError("surface has no clusters")
        if set(self.observations) != set(self.clusters):
            raise PayoffSurfaceError("observation index does not match "
                                     "the cluster list")
        for cluster in self.clusters:
            _check_cluster_belongs(cluster, self.cell_id)
            if not self.observations[cluster]:
                raise PayoffSurfaceError(f"cluster {cluster}: no observations")
            for observation_id in self.observations[cluster]:
                _check_observation_belongs(observation_id, cluster,
                                           self.cell_id)
        for candidate in expected:
            outcomes = self.data[candidate]
            if set(outcomes) != set(self.clusters):
                raise PayoffSurfaceError(
                    f"{candidate!r}: cluster support differs from the "
                    f"surface index")
            for cluster in self.clusters:
                values = outcomes[cluster]
                if tuple(sorted(values)) != tuple(self.observations[cluster]):
                    raise PayoffSurfaceError(
                        f"{candidate!r}/{cluster}: observation ids differ "
                        f"from the surface index")
                for observation_id, value in values.items():
                    if isinstance(value, bool) or value not in (0, 1):
                        raise PayoffSurfaceError(
                            f"{candidate!r}/{cluster}/{observation_id}: "
                            f"terminal correctness must be 0 or 1")

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

    def __deepcopy__(self, memo: dict) -> "ValidatedSurface":
        return self  # immutable; the mapping proxies are unpicklable

    def to_json(self) -> dict[str, Any]:
        """Explicit persistence form (Stage 1 is resumable). Candidates are
        not JSON object keys — they are tuples — so the surface serializes
        as a list of (candidate, outcomes) entries."""
        return {
            "kind": self.kind,
            "cell_id": self.cell_id,
            "entries": [
                {"candidate": _candidate_to_json(self.kind, candidate),
                 "outcomes": {cluster: dict(self.data[candidate][cluster])
                              for cluster in self.clusters}}
                for candidate in self.candidates],
        }

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "ValidatedSurface":
        kind, cell_id = obj["kind"], obj["cell_id"]
        raw = {_candidate_from_json(kind, entry["candidate"]):
               {cluster: {o: int(v) for o, v in values.items()}
                for cluster, values in entry["outcomes"].items()}
               for entry in obj["entries"]}
        return _validate(raw, kind, cell_id,
                         _expected_candidates(kind, cell_id))

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
    # Key equality alone is not identity: `False` and `0.0` hash and
    # compare equal to `0`, so an endpoint key of the wrong type would
    # satisfy the enumeration check above.
    _check_candidate_types(kind, raw)

    reference_clusters: tuple[str, ...] | None = None
    reference_obs: dict[str, tuple[str, ...]] | None = None
    frozen: dict[Any, Mapping[str, Mapping[str, float]]] = {}

    for candidate in expected:
        outcomes = raw[candidate]
        if not isinstance(outcomes, Mapping) or not outcomes:
            raise PayoffSurfaceError(f"{candidate!r}: no cluster observations")
        # Type-check keys before sorting: heterogeneous keys would raise a
        # raw TypeError from sorted() instead of PayoffSurfaceError.
        for cluster in outcomes:
            if not isinstance(cluster, str):
                raise PayoffSurfaceError(f"cluster id {cluster!r} is not a str")
        clusters = tuple(sorted(outcomes))
        per_cluster: dict[str, Mapping[str, float]] = {}
        obs_ids: dict[str, tuple[str, ...]] = {}
        for cluster in clusters:
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


def _check_candidate_types(kind: str, raw: Mapping) -> None:
    for candidate in raw:
        if kind == "one_call":
            if type(candidate) is not int:
                raise PayoffSurfaceError(
                    f"one-call candidate {candidate!r} must be an int "
                    f"endpoint id (bools and floats alias integer keys)")
        elif kind == "two_call":
            if (not isinstance(candidate, tuple) or len(candidate) != 2
                    or not isinstance(candidate[0], str)
                    or not isinstance(candidate[1], tuple)
                    or len(candidate[1]) != 2
                    or any(type(e) is not int for e in candidate[1])):
                raise PayoffSurfaceError(
                    f"two-call candidate {candidate!r} must be "
                    f"(orientation, (endpoint, endpoint))")


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
    endpoint. Pair it with its assignment surface through a
    `CalibrationBundle` — that is what enforces the shared population."""
    if cell_id not in CELL_NODES:
        raise PayoffSurfaceError(f"unknown cell_id {cell_id!r}")
    return _validate(raw, "one_call", cell_id, list(ENDPOINT_IDS))


def validate_two_call_surface(raw: RawSurface, cell_id: str
                              ) -> ValidatedSurface:
    """The 18-workflow contraction family (D12) — fork/join only."""
    if cell_id not in CELL_NODES:
        raise PayoffSurfaceError(f"unknown cell_id {cell_id!r}")
    return _validate(raw, "two_call", cell_id,
                     _expected_candidates("two_call", cell_id))


@dataclass(frozen=True)
class CalibrationBundle:
    """Assignment surface plus its controls, proven to share one population.

    Stage-1 gates compare the deployable oracle against the best one-call
    and two-call controls. Those comparisons are only meaningful if every
    surface was scored on the *same* clusters and renderings — validating
    each surface in isolation cannot establish that, so the comparison is
    only ever taken from a bundle.
    """

    assignment: ValidatedSurface
    one_call: ValidatedSurface | None = None
    two_call: ValidatedSurface | None = None

    def __post_init__(self) -> None:
        _require_surface(self.assignment, "assignment")
        for name, surface, kind in (("one_call", self.one_call, "one_call"),
                                    ("two_call", self.two_call, "two_call")):
            if surface is None:
                continue
            _require_surface(surface, kind)
            if surface.cell_id != self.assignment.cell_id:
                raise PayoffSurfaceError(
                    f"{name} surface is for cell {surface.cell_id!r}, the "
                    f"assignment surface for {self.assignment.cell_id!r}")
            if surface.clusters != self.assignment.clusters:
                raise PayoffSurfaceError(
                    f"{name} surface uses different clusters from the "
                    f"assignment surface (gates would compare populations)")
            for cluster in self.assignment.clusters:
                if surface.observations[cluster] != \
                        self.assignment.observations[cluster]:
                    raise PayoffSurfaceError(
                        f"{name} surface/{cluster}: different observation "
                        f"ids from the assignment surface")

    @property
    def cell_id(self) -> str:
        return self.assignment.cell_id

    def deployable(self) -> tuple[int, ...]:
        return select_deployable(self.assignment)

    def best_one_call(self) -> int:
        if self.one_call is None:
            raise PayoffSurfaceError("bundle has no one-call surface")
        return select_best_one_call(self.one_call)

    def best_two_call(self) -> tuple[str, tuple[int, int]]:
        if self.two_call is None:
            raise PayoffSurfaceError("bundle has no two-call surface")
        return select_best_two_call(self.two_call)

    def deployable_vs_one_call(self) -> float:
        """Oracle advantage over the best single whole-task call, on the
        shared population (the Stage-1A ≥ +20 point gate)."""
        return (self.assignment.accuracy(self.deployable())
                - self.one_call.accuracy(self.best_one_call())
                if self.one_call is not None
                else _no_control("one-call"))

    def deployable_vs_two_call(self) -> float:
        return (self.assignment.accuracy(self.deployable())
                - self.two_call.accuracy(self.best_two_call())
                if self.two_call is not None
                else _no_control("two-call"))


def _no_control(name: str) -> float:
    raise PayoffSurfaceError(f"bundle has no {name} surface")


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
