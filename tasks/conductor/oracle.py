"""Deployable oracle, controls, comparator — spec §1.8; plan contract 7.

Assignments are tuples of endpoint indices in **stable node order
(n1, n2, n3)** — never positional order.

Two contracts shape this module:

*Selection is a construction-time act.* The deployable assignment and the
controls are "selected per cell on construction data, frozen, never
reselected" (§1.8, plan contract 7). Re-maximizing on qualification data
would not merely make a point estimate optimistic — qualification uses
pre-registered sequential looks, so changing the candidate at each look
changes the hypothesis under test and voids the alpha-spending
interpretation. Every argmax here therefore refuses a non-construction
surface, and qualification consumes a persisted `FrozenSelections`
artifact that exposes no argmax at all.

*Payoff data is observation-keyed.*

    surface[candidate][cluster_id][observation_id] = correctness ∈ {0, 1}

Anonymous per-cluster lists could not prove two candidates were scored on
the *same* renderings. Cluster ids are `latent_program_id`s and observation
ids are `render_instance_id`s, so a surface is bound to its cell and split
by identity rather than by node arity (all three atomic cells have one
node).
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from .types import (
    CELL_NODES, RENDERER_IDS, parse_latent_program_id,
    parse_render_instance_id,
)
from .workerpool import STAGE0_POOL_FINGERPRINT, WORKER_IDS

# Raw, unvalidated input shape.
RawSurface = Mapping[Any, Mapping[str, Mapping[str, float]]]

SELECTION_NAMESPACE = "construction"

# Version tag on the source digest. It hashes canonical *surface-result
# content*, not experiment identity: two independent executions that
# produce identical payoff tables intentionally share a digest. Pair it
# with the deferred population and execution-manifest digests when those
# exist (see GATE_PROVENANCE_REQUIREMENT).
# "surfdig2" = the 106_s four-worker candidate domain; a persisted
# three-worker ("surfdig1") bundle can neither validate (incomplete
# 4^S support) nor match a digest, so old and new pools fail closed
# against each other rather than mixing.
SURFACE_DIGEST_SCHEMA = "surfdig2"


class PayoffSurfaceError(ValueError):
    """A payoff surface is incomplete, unpaired, malformed, or is being
    used outside the phase its contract allows."""


def enumerate_assignments(num_nodes: int) -> list[tuple[int, ...]]:
    """The 4^S worker-assignment set, lexicographic order (106_s §6.1)."""
    if num_nodes < 1:
        raise PayoffSurfaceError("a cell has at least one node")
    return list(itertools.product(WORKER_IDS, repeat=num_nodes))


TWO_CALL_ORIENTATIONS = ("lookup_first", "code_first")  # frozen tie order


def enumerate_two_call_workflows() -> list[tuple[str, tuple[int, int]]]:
    """The two-call contraction family (D12), regenerated mechanically
    from the four-worker registry (106_s §6.3): orientation × worker
    pair in the frozen tie order (lookup-first < code-first, then
    lexicographic worker tuple). Cardinality is asserted here — 32 is
    an acceptance expectation, never a second source of truth."""
    workflows = [(orientation, pair)
                 for orientation in TWO_CALL_ORIENTATIONS
                 for pair in itertools.product(WORKER_IDS, repeat=2)]
    assert len(workflows) == len(TWO_CALL_ORIENTATIONS) * len(WORKER_IDS) ** 2
    return workflows


_SURFACE_KINDS = ("assignment", "one_call", "two_call")

# The 18-workflow contraction family is defined only for the fork/join
# cell (D12); there is no two-call shortcut for a one- or two-step cell.
TWO_CALL_CELLS = ("fork_join",)


def _expected_candidates(kind: str, cell_id: str) -> list[Any]:
    if kind == "assignment":
        return enumerate_assignments(len(CELL_NODES[cell_id]))
    if kind == "one_call":
        return list(WORKER_IDS)
    if kind == "two_call":
        if cell_id not in TWO_CALL_CELLS:
            raise PayoffSurfaceError(
                f"the two-call shortcut family is not defined for {cell_id}")
        return enumerate_two_call_workflows()
    raise PayoffSurfaceError(f"unknown surface kind {kind!r}")


def _check_probability(value: Any, field_name: str) -> float:
    # `math.isfinite` raises OverflowError on an int too large to convert
    # to float, so the finiteness test must be guarded, not reached after a
    # bare `math.isfinite(value)`.
    bad = isinstance(value, bool) or not isinstance(value, (int, float))
    if not bad:
        try:
            bad = not math.isfinite(value) or not 0.0 <= value <= 1.0
        except OverflowError:
            bad = True
    if bad:
        raise PayoffSurfaceError(
            f"{field_name} must be a finite number in [0, 1], got {value!r}")
    return float(value)


def _int_list_from_json(value: Any, field_name: str) -> tuple[int, ...]:
    """Shape first: `tuple(...)` on a malformed value would either raise a
    raw TypeError or silently accept the wrong arity."""
    if not isinstance(value, (list, tuple)):
        raise PayoffSurfaceError(f"{field_name} must be a list of ints")
    for entry in value:
        if type(entry) is not int:
            raise PayoffSurfaceError(
                f"{field_name} contains a non-int entry {entry!r}")
    return tuple(value)


# --- candidate typing -------------------------------------------------------

def _check_candidate(kind: str, candidate: Any, cell_id: str) -> None:
    """Exact types. `False` and `0.0` hash and compare equal to `0`, so
    membership in the enumerated candidate set is not on its own enough."""
    if kind == "assignment":
        num_nodes = len(CELL_NODES[cell_id])
        if not isinstance(candidate, tuple):
            raise PayoffSurfaceError(
                f"assignment {candidate!r} must be a tuple of endpoint "
                f"indices")
        if len(candidate) != num_nodes:
            raise PayoffSurfaceError(
                f"assignment {candidate!r} must have {num_nodes} entries")
        for worker in candidate:
            if type(worker) is not int or worker not in WORKER_IDS:
                raise PayoffSurfaceError(
                    f"assignment {candidate!r} has a non-integer or "
                    f"out-of-range worker id")
    elif kind == "one_call":
        if type(candidate) is not int or candidate not in WORKER_IDS:
            raise PayoffSurfaceError(
                f"one-call candidate {candidate!r} must be an int worker "
                f"id (bools and floats alias integer keys)")
    elif kind == "two_call":
        ok = (isinstance(candidate, tuple) and len(candidate) == 2
              and candidate[0] in TWO_CALL_ORIENTATIONS
              and isinstance(candidate[1], tuple) and len(candidate[1]) == 2
              and all(type(e) is int and e in WORKER_IDS
                      for e in candidate[1]))
        if not ok:
            raise PayoffSurfaceError(
                f"two-call candidate {candidate!r} must be "
                f"(orientation, (endpoint, endpoint))")
    else:
        raise PayoffSurfaceError(f"unknown surface kind {kind!r}")


# --- population identity ----------------------------------------------------

def _check_cluster_belongs(cluster_id: Any, cell_id: str):
    """Cluster ids are `latent_program_id`s, which name their own cell and
    split — so a surface can be bound to its population by identity."""
    try:
        return parse_latent_program_id(cluster_id)
    except ValueError as exc:
        raise PayoffSurfaceError(
            f"cluster id {cluster_id!r} is not a latent_program_id: "
            f"{exc}") from exc


def _check_observation_belongs(observation_id: Any, cluster_id: str,
                               cell_id: str):
    try:
        render_id = parse_render_instance_id(observation_id)
    except ValueError as exc:
        raise PayoffSurfaceError(
            f"observation id {observation_id!r} is not a "
            f"render_instance_id: {exc}") from exc
    if render_id.latent_program_id != cluster_id:
        raise PayoffSurfaceError(
            f"observation {observation_id!r} is filed under cluster "
            f"{cluster_id!r} but names {render_id.latent_program_id!r}")
    return render_id


# --- deferred: the authoritative calibration provenance layer --------------
#
# Binding a surface to the *registered* population (namespace caps,
# deterministic prefixes, the pre-registered look schedule, three-renderer
# crossing, the scheduled visible slice) and to one *execution* environment
# (runtime-profile fingerprint, endpoint fingerprints, D16 prompt revision)
# is a Stage-1A `calibrate.py` responsibility built on Stage-0B artifacts.
# None of those fingerprints exist yet, and the population registration
# logic lives with the look schedules in calibration.
#
# A partial manifest here would be worse than none: it would read like a
# provenance check while establishing none of those properties. So Stage 0A
# ships the structural half only, and says so — see `CalibrationBundle` and
# the "Scope of the calibration guarantees" section of `conductor_log.md`.

GATE_PROVENANCE_REQUIREMENT = (
    "Stage-1A gate evaluation requires a canonical population manifest "
    "(registered clusters/renderings, generator and difficulty-profile "
    "versions) and execution provenance (runtime-profile fingerprint, "
    "endpoint fingerprints, D16 prompt revision). Those are Stage-0B/1A "
    "artifacts and are not implemented at Stage 0A; the helpers here are "
    "structural and descriptive only."
)


@dataclass(frozen=True)
class ValidatedSurface:
    """A complete, observation-paired payoff surface over a candidate set.

    Build these with `validate_*_surface`. `__post_init__` re-checks and
    **re-freezes** every nested collection, so neither a directly
    constructed instance nor a caller who keeps a reference to the backing
    dictionaries can change a validated surface. That is what makes the
    identity `__deepcopy__` sound.
    """

    kind: str                                   # assignment | one_call | two_call
    cell_id: str
    candidates: tuple[Any, ...]
    clusters: tuple[str, ...]
    observations: Mapping[str, tuple[str, ...]]  # cluster -> observation ids
    data: Mapping[Any, Mapping[str, Mapping[str, float]]]
    namespace: str = ""
    # 108_s finding 4: candidate ids are meaningless without the pool
    # that defines them; a surface generated under a different
    # four-worker pool (same cardinality, different models/prompts)
    # must fail closed rather than be silently reinterpreted.
    worker_pool: str = STAGE0_POOL_FINGERPRINT

    def __post_init__(self) -> None:
        if self.worker_pool != STAGE0_POOL_FINGERPRINT:
            raise PayoffSurfaceError(
                f"surface is bound to worker pool {self.worker_pool!r}; "
                f"this registry is {STAGE0_POOL_FINGERPRINT!r}")
        # Type before membership: an unhashable cell_id (a list, say) would
        # raise a raw TypeError from the `in` test.
        if not isinstance(self.kind, str) or self.kind not in _SURFACE_KINDS:
            raise PayoffSurfaceError(f"unknown surface kind {self.kind!r}")
        if not isinstance(self.cell_id, str) or self.cell_id not in CELL_NODES:
            raise PayoffSurfaceError(f"unknown cell_id {self.cell_id!r}")
        expected = _expected_candidates(self.kind, self.cell_id)
        for candidate in self.candidates:
            _check_candidate(self.kind, candidate, self.cell_id)
        if tuple(self.candidates) != tuple(expected):
            raise PayoffSurfaceError(
                f"{self.kind} surface candidates are not the frozen "
                f"enumeration for {self.cell_id}")
        if not isinstance(self.data, Mapping) or set(self.data) != set(expected):
            raise PayoffSurfaceError("surface data does not cover every "
                                     "candidate exactly once")
        if not self.clusters:
            raise PayoffSurfaceError("surface has no clusters")
        # Duplicate cluster entries would double-weight a cluster in
        # `accuracy()` while every set-based support check still passed.
        if len(set(self.clusters)) != len(self.clusters):
            raise PayoffSurfaceError("duplicate cluster ids in surface")
        if tuple(sorted(self.clusters)) != tuple(self.clusters):
            raise PayoffSurfaceError("clusters must be in canonical order")
        if not isinstance(self.observations, Mapping) \
                or set(self.observations) != set(self.clusters):
            raise PayoffSurfaceError("observation index does not match "
                                     "the cluster list")

        namespaces, frozen_obs = set(), {}
        for cluster in self.clusters:
            latent = _check_cluster_belongs(cluster, self.cell_id)
            if latent.cell_id != self.cell_id:
                raise PayoffSurfaceError(
                    f"cluster {cluster!r} belongs to cell "
                    f"{latent.cell_id!r}, not {self.cell_id!r}")
            namespaces.add(latent.namespace)
            observation_ids = tuple(self.observations[cluster])
            if not observation_ids:
                raise PayoffSurfaceError(f"cluster {cluster}: no observations")
            if len(set(observation_ids)) != len(observation_ids):
                raise PayoffSurfaceError(
                    f"cluster {cluster}: duplicate observation ids")
            if tuple(sorted(observation_ids)) != observation_ids:
                raise PayoffSurfaceError(
                    f"cluster {cluster}: observations must be in canonical "
                    f"order")
            for observation_id in observation_ids:
                render_id = _check_observation_belongs(observation_id,
                                                       cluster, self.cell_id)
                if render_id.latent.cell_id != self.cell_id:
                    raise PayoffSurfaceError(
                        f"observation {observation_id!r} belongs to cell "
                        f"{render_id.latent.cell_id!r}, not "
                        f"{self.cell_id!r}")
            frozen_obs[cluster] = observation_ids
        # A surface mixing splits is not a population: gates are defined
        # per split, and selection is construction-only.
        if len(namespaces) != 1:
            raise PayoffSurfaceError(
                f"surface mixes namespaces {sorted(namespaces)}; a payoff "
                f"surface covers exactly one split")
        namespace = namespaces.pop()
        if self.namespace and self.namespace != namespace:
            raise PayoffSurfaceError(
                f"surface namespace {self.namespace!r} disagrees with its "
                f"cluster ids ({namespace!r})")

        frozen_data: dict[Any, Mapping[str, Mapping[str, float]]] = {}
        for candidate in expected:
            outcomes = self.data[candidate]
            if not isinstance(outcomes, Mapping) \
                    or set(outcomes) != set(self.clusters):
                raise PayoffSurfaceError(
                    f"{candidate!r}: cluster support differs from the "
                    f"surface index")
            per_cluster: dict[str, Mapping[str, float]] = {}
            for cluster in self.clusters:
                values = outcomes[cluster]
                if not isinstance(values, Mapping) \
                        or tuple(sorted(values)) != frozen_obs[cluster]:
                    raise PayoffSurfaceError(
                        f"{candidate!r}/{cluster}: observation ids differ "
                        f"from the surface index")
                for observation_id, value in values.items():
                    if isinstance(value, bool) or value not in (0, 1):
                        raise PayoffSurfaceError(
                            f"{candidate!r}/{cluster}/{observation_id}: "
                            f"terminal correctness must be 0 or 1, got "
                            f"{value!r}")
                per_cluster[cluster] = MappingProxyType(
                    {o: float(values[o]) for o in frozen_obs[cluster]})
            frozen_data[candidate] = MappingProxyType(per_cluster)

        # Re-freeze every nested collection: a caller keeping a reference
        # to the dictionaries it passed in must not be able to change a
        # validated surface afterwards.
        object.__setattr__(self, "candidates", tuple(expected))
        object.__setattr__(self, "clusters", tuple(self.clusters))
        object.__setattr__(self, "observations",
                           MappingProxyType(dict(frozen_obs)))
        object.__setattr__(self, "data", MappingProxyType(frozen_data))
        object.__setattr__(self, "namespace", namespace)

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
        _check_candidate(self.kind, candidate, self.cell_id)
        if candidate not in self.data:
            raise PayoffSurfaceError(f"{candidate!r} is not in this surface")
        outcomes = self.data[candidate]
        return sum(
            sum(outcomes[cluster].values()) / len(outcomes[cluster])
            for cluster in self.clusters) / len(self.clusters)

    def full_sample_accuracy(self, candidate: Any) -> float:
        """Unweighted mean over every observation — reported as a
        diagnostic; §1.8 selection always uses `accuracy`."""
        _check_candidate(self.kind, candidate, self.cell_id)
        outcomes = self.data[candidate]
        values = [v for cluster in self.clusters
                  for v in outcomes[cluster].values()]
        return sum(values) / len(values)

    def __deepcopy__(self, memo: dict) -> "ValidatedSurface":
        return self  # every nested collection was re-frozen above

    def to_json(self) -> dict[str, Any]:
        """Explicit persistence form (Stage 1 is resumable). Candidates are
        tuples, not JSON object keys, so the surface serializes as a list
        of (candidate, outcomes) entries."""
        return {
            "kind": self.kind,
            "cell_id": self.cell_id,
            "worker_pool": self.worker_pool,
            "entries": [
                {"candidate": _candidate_to_json(self.kind, candidate),
                 "outcomes": {cluster: dict(self.data[candidate][cluster])
                              for cluster in self.clusters}}
                for candidate in self.candidates],
        }

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "ValidatedSurface":
        """Fail-closed deserialization.

        Persisted values are never coerced — `int(0.5)`, `int("1")` and
        `int(True)` would each manufacture a valid-looking binary
        observation out of malformed data — and duplicate candidate entries
        are rejected rather than silently collapsed last-write-wins, which
        is exactly what a resumed write-through artifact can contain.
        """
        if not isinstance(obj, Mapping):
            raise PayoffSurfaceError("surface JSON must be an object")
        if set(obj) != {"kind", "cell_id", "worker_pool", "entries"}:
            raise PayoffSurfaceError(
                f"surface JSON keys must be exactly kind/cell_id/"
                f"worker_pool/entries, got {sorted(obj)}")
        kind, cell_id = obj["kind"], obj["cell_id"]
        if obj["worker_pool"] != STAGE0_POOL_FINGERPRINT:
            raise PayoffSurfaceError(
                f"persisted surface is bound to worker pool "
                f"{obj['worker_pool']!r}; this registry is "
                f"{STAGE0_POOL_FINGERPRINT!r} — a surface from another "
                f"pool must be regenerated, never reinterpreted")
        # Type before membership: an unhashable value would raise a raw
        # TypeError from the `in` test.
        if not isinstance(kind, str) or kind not in _SURFACE_KINDS:
            raise PayoffSurfaceError(f"unknown surface kind {kind!r}")
        if not isinstance(cell_id, str) or cell_id not in CELL_NODES:
            raise PayoffSurfaceError(f"unknown cell_id {cell_id!r}")
        entries = obj["entries"]
        expected = _expected_candidates(kind, cell_id)
        if not isinstance(entries, list) or len(entries) != len(expected):
            raise PayoffSurfaceError(
                f"expected exactly {len(expected)} candidate entries, got "
                f"{len(entries) if isinstance(entries, list) else type(entries)}")

        raw: dict[Any, dict[str, dict[str, float]]] = {}
        for entry in entries:
            if not isinstance(entry, Mapping) \
                    or set(entry) != {"candidate", "outcomes"}:
                raise PayoffSurfaceError(
                    "each entry must have exactly candidate/outcomes")
            candidate = _candidate_from_json(kind, entry["candidate"])
            _check_candidate(kind, candidate, cell_id)
            if candidate in raw:
                raise PayoffSurfaceError(
                    f"duplicate candidate entry {candidate!r}: a resumed "
                    f"artifact must not collapse silently")
            outcomes = entry["outcomes"]
            if not isinstance(outcomes, Mapping):
                raise PayoffSurfaceError(f"{candidate!r}: outcomes must be "
                                         f"an object")
            per_cluster: dict[str, dict[str, float]] = {}
            for cluster, values in outcomes.items():
                if not isinstance(cluster, str):
                    raise PayoffSurfaceError(
                        f"cluster id {cluster!r} is not a str")
                if not isinstance(values, Mapping):
                    raise PayoffSurfaceError(
                        f"{candidate!r}/{cluster}: observations must be an "
                        f"object")
                # Values pass through unchanged; the binary validator in
                # __post_init__ is what accepts or rejects them.
                per_cluster[cluster] = dict(values)
            raw[candidate] = per_cluster
        return _validate(raw, kind, cell_id, expected)


def _candidate_to_json(kind: str, candidate: Any) -> Any:
    if kind == "assignment":
        return list(candidate)
    if kind == "one_call":
        return candidate
    return [candidate[0], list(candidate[1])]


def _candidate_from_json(kind: str, value: Any) -> Any:
    try:
        if kind == "assignment":
            if not isinstance(value, list):
                raise TypeError("assignment candidate must be a list")
            return tuple(value)
        if kind == "one_call":
            return value
        if not isinstance(value, list) or len(value) != 2 \
                or not isinstance(value[1], list):
            raise TypeError("two-call candidate must be [orientation, [e, e]]")
        return (value[0], tuple(value[1]))
    except TypeError as exc:
        raise PayoffSurfaceError(
            f"malformed persisted candidate {value!r}: {exc}") from exc


def _validate(raw: RawSurface, kind: str, cell_id: str,
              candidates: Sequence[Any]) -> ValidatedSurface:
    if not isinstance(raw, Mapping) or not raw:
        raise PayoffSurfaceError("payoff surface is empty")
    expected = list(candidates)
    try:
        present = set(raw)
    except TypeError as exc:  # unhashable keys
        raise PayoffSurfaceError(f"malformed candidate keys: {exc}") from exc
    for candidate in present:
        _check_candidate(kind, candidate, cell_id)
    missing = [c for c in expected if c not in present]
    unexpected = [c for c in present if c not in set(expected)]
    if missing or unexpected:
        raise PayoffSurfaceError(
            f"{kind} surface is not the full enumeration of "
            f"{len(expected)} candidates (missing {missing}, unexpected "
            f"{unexpected})")

    first = raw[expected[0]]
    if not isinstance(first, Mapping) or not first:
        raise PayoffSurfaceError(f"{expected[0]!r}: no cluster observations")
    for cluster in first:
        if not isinstance(cluster, str):
            raise PayoffSurfaceError(f"cluster id {cluster!r} is not a str")
    clusters = tuple(sorted(first))
    observations: dict[str, tuple[str, ...]] = {}
    for cluster in clusters:
        values = first[cluster]
        if not isinstance(values, Mapping) or not values:
            raise PayoffSurfaceError(
                f"{expected[0]!r}/{cluster}: observations must be a "
                f"non-empty {{observation_id: correctness}} mapping")
        for observation_id in values:
            if not isinstance(observation_id, str):
                raise PayoffSurfaceError(
                    f"observation id {observation_id!r} is not a str")
        observations[cluster] = tuple(sorted(values))
    return ValidatedSurface(kind=kind, cell_id=cell_id,
                            candidates=tuple(expected), clusters=clusters,
                            observations=observations, data=raw)


def validate_payoff_surface(raw: RawSurface, cell_id: str
                            ) -> ValidatedSurface:
    """Validate a 4^S assignment surface for a named cell. `cell_id` is
    required: inferring S from the data cannot catch a surface built for
    the wrong cell."""
    if not isinstance(cell_id, str) or cell_id not in CELL_NODES:
        raise PayoffSurfaceError(f"unknown cell_id {cell_id!r}")
    return _validate(raw, "assignment", cell_id,
                     _expected_candidates("assignment", cell_id))


def validate_one_call_surface(raw: RawSurface, cell_id: str
                              ) -> ValidatedSurface:
    """Best one-call whole-task control (§1.11 B5). Pair it with its
    assignment surface through a `CalibrationBundle` — that is what
    enforces the shared population."""
    if not isinstance(cell_id, str) or cell_id not in CELL_NODES:
        raise PayoffSurfaceError(f"unknown cell_id {cell_id!r}")
    return _validate(raw, "one_call", cell_id, list(WORKER_IDS))


def validate_two_call_surface(raw: RawSurface, cell_id: str
                              ) -> ValidatedSurface:
    """The registry-derived two-call contraction family (D12; 106_s
    §6.3) — fork/join only."""
    if not isinstance(cell_id, str) or cell_id not in CELL_NODES:
        raise PayoffSurfaceError(f"unknown cell_id {cell_id!r}")
    return _validate(raw, "two_call", cell_id,
                     _expected_candidates("two_call", cell_id))


def _require_surface(surface: Any, kind: str) -> ValidatedSurface:
    if not isinstance(surface, ValidatedSurface):
        raise PayoffSurfaceError(
            "selectors consume a ValidatedSurface; call the matching "
            "validate_*_surface constructor first")
    if surface.kind != kind:
        raise PayoffSurfaceError(
            f"expected a {kind} surface, got {surface.kind}")
    return surface


def _require_selection_phase(surface: ValidatedSurface) -> None:
    """§1.8 / plan contract 7: selection happens on construction data and
    is then frozen. Re-maximizing at a qualification look would change the
    hypothesis the pre-registered alpha spending is tested against."""
    if surface.namespace != SELECTION_NAMESPACE:
        raise PayoffSurfaceError(
            f"selection is {SELECTION_NAMESPACE}-only; this surface is "
            f"{surface.namespace!r}. Evaluate frozen selections instead of "
            f"reselecting (§1.8: 'frozen, never reselected').")


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
    worker-id tuple. Construction data only."""
    vs = _require_surface(surface, "assignment")
    _require_selection_phase(vs)
    return _argmax_in_tie_order(vs, vs.candidates)


def node_runner_up(surface: ValidatedSurface, deployable: tuple[int, ...],
                   node_index: int) -> tuple[int, ...]:
    """Best alternative worker at one node, all others fixed at the
    deployable assignment; ties → lowest worker id (106_s §6.3)."""
    vs = _require_surface(surface, "assignment")
    _require_selection_phase(vs)
    _check_candidate("assignment", deployable, vs.cell_id)
    if type(node_index) is not int or not 0 <= node_index < vs.num_nodes:
        raise PayoffSurfaceError(f"node_index {node_index!r} out of range")
    alternatives = [
        deployable[:node_index] + (worker,) + deployable[node_index + 1:]
        for worker in WORKER_IDS if worker != deployable[node_index]]
    return _argmax_in_tie_order(vs, alternatives)


def best_fixed(surface: ValidatedSurface) -> tuple[int, ...]:
    """§1.8 control: best of the constant assignments `(0,…,0)` through
    `(3,…,3)`, same objective and tie rule (context-partitioning
    control, not selection)."""
    vs = _require_surface(surface, "assignment")
    _require_selection_phase(vs)
    constants = [(w,) * vs.num_nodes for w in WORKER_IDS]
    return _argmax_in_tie_order(vs, constants)


def uniform_random_accuracy(surface: ValidatedSurface) -> float:
    """§1.8 `random` control: the exact uniform mean over the enumerated
    4^S payoff surface (analytic, never Monte Carlo). Descriptive, so it is
    computable on any split."""
    vs = _require_surface(surface, "assignment")
    return sum(vs.accuracy(c) for c in vs.candidates) / len(vs.candidates)


def select_best_one_call(surface: ValidatedSurface) -> int:
    """Argmax over the four workers; tie → lowest worker id (§1.8)."""
    vs = _require_surface(surface, "one_call")
    _require_selection_phase(vs)
    return _argmax_in_tie_order(vs, vs.candidates)


def select_best_two_call(surface: ValidatedSurface
                         ) -> tuple[str, tuple[int, int]]:
    """Argmax over the registry-derived two-call family; tie → frozen
    order (lookup-first < code-first, then lexicographic worker
    tuple)."""
    vs = _require_surface(surface, "two_call")
    _require_selection_phase(vs)
    return _argmax_in_tie_order(vs, vs.candidates)


# --- construction-frozen selections -----------------------------------------

@dataclass(frozen=True)
class FrozenSelections:
    """Every candidate chosen on construction data, recorded once.

    Qualification consumes this artifact and evaluates exactly these
    candidates. It deliberately exposes no argmax: that is the mechanical
    guarantee behind "never reselected on qualification results".
    """

    cell_id: str
    namespace: str
    deployable: tuple[int, ...]
    best_fixed_assignment: tuple[int, ...]
    node_runner_ups: Mapping[str, tuple[int, ...]]
    # Diagnostic, and named for the split it was computed on: the `random`
    # control is the exact uniform mean over *the surface being evaluated*,
    # so a construction value must never be mistaken for the qualification
    # control (use `CalibrationBundle.random_accuracy()` for that).
    construction_random_accuracy: float
    source_surface_digest: str
    best_one_call: int | None = None
    best_two_call: tuple[str, tuple[int, int]] | None = None
    worker_pool: str = STAGE0_POOL_FINGERPRINT

    def __post_init__(self) -> None:
        if self.worker_pool != STAGE0_POOL_FINGERPRINT:
            raise PayoffSurfaceError(
                f"selections are bound to worker pool "
                f"{self.worker_pool!r}; this registry is "
                f"{STAGE0_POOL_FINGERPRINT!r}")
        if not isinstance(self.cell_id, str) \
                or self.cell_id not in CELL_NODES:
            raise PayoffSurfaceError(f"unknown cell_id {self.cell_id!r}")
        if self.namespace != SELECTION_NAMESPACE:
            raise PayoffSurfaceError(
                f"selections must come from {SELECTION_NAMESPACE} data")
        _check_candidate("assignment", self.deployable, self.cell_id)
        _check_candidate("assignment", self.best_fixed_assignment,
                         self.cell_id)
        # `best_fixed` is the best *constant* assignment (§1.8): it is the
        # control that separates heterogeneous selection from the benefit
        # of making several context-partitioned calls, so a heterogeneous
        # tuple stored under that label would be a different quantity.
        if len(set(self.best_fixed_assignment)) != 1:
            raise PayoffSurfaceError(
                f"best_fixed_assignment {self.best_fixed_assignment} is not "
                f"constant")
        nodes = CELL_NODES[self.cell_id]
        if set(self.node_runner_ups) != set(nodes):
            raise PayoffSurfaceError(
                f"node_runner_ups must cover exactly {list(nodes)}, got "
                f"{sorted(self.node_runner_ups)}")
        for index, node in enumerate(nodes):
            assignment = self.node_runner_ups[node]
            _check_candidate("assignment", assignment, self.cell_id)
            # A runner-up differs from the deployable assignment at its own
            # node and nowhere else (§1.8).
            differing = [i for i, (a, b) in
                         enumerate(zip(assignment, self.deployable)) if a != b]
            if differing != [index]:
                raise PayoffSurfaceError(
                    f"runner-up for {node} must change exactly that node: "
                    f"{assignment} vs deployable {self.deployable}")
        if self.best_one_call is not None:
            _check_candidate("one_call", self.best_one_call, self.cell_id)
        if self.best_two_call is not None:
            if self.cell_id not in TWO_CALL_CELLS:
                raise PayoffSurfaceError(
                    f"the two-call family is not defined for {self.cell_id}")
            _check_candidate("two_call", self.best_two_call, self.cell_id)
        _check_probability(self.construction_random_accuracy,
                           "construction_random_accuracy")
        if not isinstance(self.source_surface_digest, str) \
                or not self.source_surface_digest:
            raise PayoffSurfaceError("source_surface_digest must be a non-empty "
                                     "string")
        object.__setattr__(self, "node_runner_ups",
                           MappingProxyType(dict(self.node_runner_ups)))

    def verify_against(self, construction: "CalibrationBundle") -> None:
        """Re-derive the selections from their source bundle; raise if they
        are not its argmax.

        The local invariants above cannot prove a stored candidate really
        *was* the argmax; this does, by recomputing it. The digest check
        first ensures we are comparing against the same construction
        surfaces the artifact was frozen from.

        Verification is done *at the consuming boundary* — every evaluation
        method takes the construction bundle and calls this in the same
        call. A returned "verified" object would only be evidence that
        wrapping happened, not that verification did, and nothing in Python
        makes such a wrapper truly unforgeable; requiring the source bundle
        at the point of use is the honest guarantee.
        """
        if not isinstance(construction, CalibrationBundle):
            raise PayoffSurfaceError("verify_against needs a CalibrationBundle")
        expected = construction.surface_digest()
        if expected != self.source_surface_digest:
            raise PayoffSurfaceError(
                f"selections were frozen from a different construction "
                f"population ({self.source_surface_digest} != {expected})")
        rederived = construction.freeze_selections()
        if rederived != self:
            raise PayoffSurfaceError(
                "selections do not match the argmax of their source bundle")

    def __deepcopy__(self, memo: dict) -> "FrozenSelections":
        return self

    def to_json(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "namespace": self.namespace,
            "deployable": list(self.deployable),
            "best_fixed_assignment": list(self.best_fixed_assignment),
            "node_runner_ups": {node: list(assignment) for node, assignment
                                in self.node_runner_ups.items()},
            "construction_random_accuracy": self.construction_random_accuracy,
            "source_surface_digest": self.source_surface_digest,
            "best_one_call": self.best_one_call,
            "best_two_call": (None if self.best_two_call is None else
                              [self.best_two_call[0],
                               list(self.best_two_call[1])]),
            "worker_pool": self.worker_pool,
        }

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "FrozenSelections":
        """Total shape validation before any conversion: an overlong
        `best_two_call` list must not be silently truncated by `tuple()`,
        and malformed values must not leak raw TypeError/IndexError."""
        if not isinstance(obj, Mapping):
            raise PayoffSurfaceError("selections JSON must be an object")
        required = {"cell_id", "namespace", "deployable",
                    "best_fixed_assignment", "node_runner_ups",
                    "construction_random_accuracy", "source_surface_digest",
                    "best_one_call", "best_two_call", "worker_pool"}
        if set(obj) != required:
            raise PayoffSurfaceError(
                f"selections JSON keys must be exactly {sorted(required)}, "
                f"got {sorted(obj) if isinstance(obj, Mapping) else obj!r}")
        deployable = _int_list_from_json(obj["deployable"], "deployable")
        best_fixed = _int_list_from_json(obj["best_fixed_assignment"],
                                         "best_fixed_assignment")
        runner_ups_json = obj["node_runner_ups"]
        if not isinstance(runner_ups_json, Mapping):
            raise PayoffSurfaceError("node_runner_ups must be an object")
        runner_ups = {}
        for node, assignment in runner_ups_json.items():
            if not isinstance(node, str):
                raise PayoffSurfaceError(f"node id {node!r} is not a str")
            runner_ups[node] = _int_list_from_json(
                assignment, f"node_runner_ups[{node}]")
        two_call_json = obj["best_two_call"]
        two_call = None
        if two_call_json is not None:
            if not isinstance(two_call_json, (list, tuple)) \
                    or len(two_call_json) != 2 \
                    or not isinstance(two_call_json[0], str):
                raise PayoffSurfaceError(
                    f"best_two_call must be [orientation, [e, e]], got "
                    f"{two_call_json!r}")
            pair = _int_list_from_json(two_call_json[1], "best_two_call pair")
            if len(pair) != 2:
                raise PayoffSurfaceError(
                    "best_two_call endpoint pair must have exactly 2 entries")
            two_call = (two_call_json[0], pair)
        return cls(
            cell_id=obj["cell_id"], namespace=obj["namespace"],
            deployable=deployable, best_fixed_assignment=best_fixed,
            node_runner_ups=runner_ups,
            construction_random_accuracy=obj["construction_random_accuracy"],
            source_surface_digest=obj["source_surface_digest"],
            best_one_call=obj["best_one_call"], best_two_call=two_call,
            worker_pool=obj["worker_pool"])


@dataclass(frozen=True)
class CalibrationBundle:
    """Assignment surface plus its controls, proven to share one population.

    Stage-1 gates compare the deployable oracle against the best one-call
    and two-call controls. Those comparisons are only meaningful if every
    surface was scored on the *same* clusters and renderings — validating
    each surface in isolation cannot establish that.

    **Scope of that guarantee — read before using a number from here.**
    This is a same-identity *structural* check: it proves the arms agree
    with one another. It does not prove they are the registered population,
    nor that they were executed under one runtime profile, prompt revision,
    and endpoint set. Those checks need the Stage-0B/1A artifacts described
    in `GATE_PROVENANCE_REQUIREMENT`, so every accuracy and difference this
    class returns is **descriptive**, and `gate_report()` refuses rather
    than dressing a provenance-free float as a Stage-1 gate result.
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
            if surface.namespace != self.assignment.namespace:
                raise PayoffSurfaceError(
                    f"{name} surface is {surface.namespace!r}, the "
                    f"assignment surface {self.assignment.namespace!r}")
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

    @property
    def namespace(self) -> str:
        return self.assignment.namespace

    def surface_digest(self) -> str:
        """Content address of this bundle's surfaces.

        Lets a revived `FrozenSelections` prove it came from *these*
        construction surfaces rather than a same-cell bundle from another
        experiment.
        """
        payload = {
            "assignment": self.assignment.to_json(),
            "one_call": (None if self.one_call is None
                         else self.one_call.to_json()),
            "two_call": (None if self.two_call is None
                         else self.two_call.to_json()),
        }
        encoded = json.dumps(payload, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")
        return f"{SURFACE_DIGEST_SCHEMA}-" + hashlib.sha256(encoded).hexdigest()[:32]

    def random_accuracy(self) -> float:
        """§1.8 `random` control on *this* bundle's data — the control is
        defined on the surface being evaluated, so qualification must use
        its own value, not the construction diagnostic."""
        return uniform_random_accuracy(self.assignment)

    def freeze_selections(self) -> FrozenSelections:
        """Select every downstream candidate, once, on construction data."""
        _require_selection_phase(self.assignment)
        deployable = select_deployable(self.assignment)
        runner_ups = {
            node: node_runner_up(self.assignment, deployable, index)
            for index, node in enumerate(CELL_NODES[self.cell_id])}
        return FrozenSelections(
            cell_id=self.cell_id,
            namespace=self.assignment.namespace,
            deployable=deployable,
            best_fixed_assignment=best_fixed(self.assignment),
            node_runner_ups=runner_ups,
            construction_random_accuracy=uniform_random_accuracy(
                self.assignment),
            source_surface_digest=self.surface_digest(),
            best_one_call=(None if self.one_call is None
                           else select_best_one_call(self.one_call)),
            best_two_call=(None if self.two_call is None
                           else select_best_two_call(self.two_call)))

    # --- evaluation of frozen choices (no argmax) --------------------------
    #
    # Evaluation takes the construction bundle and verifies the selections
    # against it in the same call. Verification is thus mechanically part
    # of consuming the artifact — not a wrappable marker a caller might
    # forget or forge (see FrozenSelections.verify_against).

    def _check_frozen(self, frozen: Any,
                      construction: "CalibrationBundle") -> FrozenSelections:
        if not isinstance(frozen, FrozenSelections):
            raise PayoffSurfaceError(
                "evaluation consumes a FrozenSelections artifact")
        if frozen.cell_id != self.cell_id:
            raise PayoffSurfaceError(
                f"selections are for {frozen.cell_id!r}, bundle for "
                f"{self.cell_id!r}")
        frozen.verify_against(construction)
        return frozen

    def deployable_accuracy(self, frozen: FrozenSelections,
                            construction: "CalibrationBundle") -> float:
        return self.assignment.accuracy(
            self._check_frozen(frozen, construction).deployable)

    def best_fixed_accuracy(self, frozen: FrozenSelections,
                            construction: "CalibrationBundle") -> float:
        return self.assignment.accuracy(
            self._check_frozen(frozen, construction).best_fixed_assignment)

    def one_call_accuracy(self, frozen: FrozenSelections,
                          construction: "CalibrationBundle") -> float:
        self._check_frozen(frozen, construction)
        if self.one_call is None or frozen.best_one_call is None:
            raise PayoffSurfaceError("no one-call surface or selection")
        return self.one_call.accuracy(frozen.best_one_call)

    def two_call_accuracy(self, frozen: FrozenSelections,
                          construction: "CalibrationBundle") -> float:
        self._check_frozen(frozen, construction)
        if self.two_call is None or frozen.best_two_call is None:
            raise PayoffSurfaceError("no two-call surface or selection")
        return self.two_call.accuracy(frozen.best_two_call)

    def descriptive_deployable_minus_one_call(
            self, frozen: FrozenSelections,
            construction: "CalibrationBundle") -> float:
        """Descriptive difference between the construction-frozen oracle
        and the construction-frozen one-call control on this bundle's data.

        Named descriptively on purpose: the Stage-1A "≥ +20 points" gate is
        this quantity *plus* a registered population, bound execution
        provenance, and a paired clustered interval. See `gate_report()`.
        """
        return (self.deployable_accuracy(frozen, construction)
                - self.one_call_accuracy(frozen, construction))

    def descriptive_deployable_minus_two_call(
            self, frozen: FrozenSelections,
            construction: "CalibrationBundle") -> float:
        return (self.deployable_accuracy(frozen, construction)
                - self.two_call_accuracy(frozen, construction))

    def gate_report(self, frozen: FrozenSelections,
                    construction: "CalibrationBundle") -> dict[str, float]:
        """Stage-1A gate evaluation — not available at Stage 0A.

        This exists so the missing capability is discoverable from the code
        rather than only from `conductor_log.md`: anything that reaches for
        a gate result fails loudly instead of silently accepting a
        descriptive number.
        """
        raise PayoffSurfaceError(GATE_PROVENANCE_REQUIREMENT)


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
    """§1.8 signed deployable-assignment gap: paired and cluster-weighted on
    the same examples; malformed policy actions enter as correctness 0
    (callers encode that); unclipped, may be negative. `routing_regret` is
    a legacy alias for this quantity.

    Both sides are observation-keyed so the pairing is checked by identity,
    not by count.

    **Scope**: this is a pure point estimator over self-declared mappings.
    §1.8 requires the schema-valid rate to be reported alongside it, and
    Stage 2 must wrap it in an authoritative report carrying that rate, the
    population, and the paired clustered interval — the float alone is not
    the comparator's result.
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
