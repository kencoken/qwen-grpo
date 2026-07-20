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

import itertools
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from .types import (
    CELL_NODES, ENDPOINT_IDS, RENDERER_IDS, parse_latent_program_id,
    parse_render_instance_id,
)

# Raw, unvalidated input shape.
RawSurface = Mapping[Any, Mapping[str, Mapping[str, float]]]

SELECTION_NAMESPACE = "construction"


class PayoffSurfaceError(ValueError):
    """A payoff surface is incomplete, unpaired, malformed, or is being
    used outside the phase its contract allows."""


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
        for endpoint in candidate:
            if type(endpoint) is not int or endpoint not in ENDPOINT_IDS:
                raise PayoffSurfaceError(
                    f"assignment {candidate!r} has a non-integer or "
                    f"out-of-range endpoint id")
    elif kind == "one_call":
        if type(candidate) is not int or candidate not in ENDPOINT_IDS:
            raise PayoffSurfaceError(
                f"one-call candidate {candidate!r} must be an int endpoint "
                f"id (bools and floats alias integer keys)")
    elif kind == "two_call":
        ok = (isinstance(candidate, tuple) and len(candidate) == 2
              and candidate[0] in TWO_CALL_ORIENTATIONS
              and isinstance(candidate[1], tuple) and len(candidate[1]) == 2
              and all(type(e) is int and e in ENDPOINT_IDS
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


@dataclass(frozen=True)
class PopulationManifest:
    """The registered calibration population, and (from Stage 0B) the
    execution provenance of the runs that produced it.

    Same-identity pairing across arms proves the arms agree with each
    other; it does not prove they are the *registered* population, nor that
    they were executed under one runtime profile. Supplying a manifest
    turns both into checked properties.

    The execution fields are `None` at Stage 0A because the artifacts they
    fingerprint (runtime profile, NF4 worker pool, frozen D16 prompts) do
    not exist until 0B/1A. `require_execution_provenance()` is the gate
    that must pass before any qualification result depends on a surface.
    """

    cell_id: str
    namespace: str
    clusters: tuple[str, ...]
    observations: Mapping[str, tuple[str, ...]]
    generator_version: str
    difficulty_profile_version: str
    runtime_profile_fingerprint: str | None = None
    endpoint_fingerprints: Mapping[str, str] | None = None
    prompt_revision: str | None = None

    def require_execution_provenance(self) -> None:
        missing = [name for name in ("runtime_profile_fingerprint",
                                     "endpoint_fingerprints",
                                     "prompt_revision")
                   if getattr(self, name) is None]
        if missing:
            raise PayoffSurfaceError(
                f"execution provenance is unrecorded ({', '.join(missing)}); "
                f"these are Stage-0B artifacts and must be bound before a "
                f"qualification gate depends on this population")


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
    manifest: PopulationManifest | None = None

    def __post_init__(self) -> None:
        if self.kind not in _SURFACE_KINDS:
            raise PayoffSurfaceError(f"unknown surface kind {self.kind!r}")
        if self.cell_id not in CELL_NODES:
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

        if self.manifest is not None:
            self._check_manifest(namespace, frozen_obs)

        # Re-freeze every nested collection: a caller keeping a reference
        # to the dictionaries it passed in must not be able to change a
        # validated surface afterwards.
        object.__setattr__(self, "candidates", tuple(expected))
        object.__setattr__(self, "clusters", tuple(self.clusters))
        object.__setattr__(self, "observations",
                           MappingProxyType(dict(frozen_obs)))
        object.__setattr__(self, "data", MappingProxyType(frozen_data))
        object.__setattr__(self, "namespace", namespace)

    def _check_manifest(self, namespace: str,
                        observations: Mapping[str, tuple[str, ...]]) -> None:
        manifest = self.manifest
        assert manifest is not None
        if manifest.cell_id != self.cell_id or manifest.namespace != namespace:
            raise PayoffSurfaceError(
                f"surface is {self.cell_id}/{namespace}, manifest registers "
                f"{manifest.cell_id}/{manifest.namespace}")
        if tuple(manifest.clusters) != tuple(self.clusters):
            raise PayoffSurfaceError(
                "surface clusters are not the registered population")
        for cluster in self.clusters:
            if tuple(manifest.observations.get(cluster, ())) != \
                    observations[cluster]:
                raise PayoffSurfaceError(
                    f"cluster {cluster}: observations are not the registered "
                    f"renderings")

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
            "entries": [
                {"candidate": _candidate_to_json(self.kind, candidate),
                 "outcomes": {cluster: dict(self.data[candidate][cluster])
                              for cluster in self.clusters}}
                for candidate in self.candidates],
        }

    @classmethod
    def from_json(cls, obj: Mapping[str, Any],
                  manifest: PopulationManifest | None = None
                  ) -> "ValidatedSurface":
        """Fail-closed deserialization.

        Persisted values are never coerced — `int(0.5)`, `int("1")` and
        `int(True)` would each manufacture a valid-looking binary
        observation out of malformed data — and duplicate candidate entries
        are rejected rather than silently collapsed last-write-wins, which
        is exactly what a resumed write-through artifact can contain.
        """
        if not isinstance(obj, Mapping):
            raise PayoffSurfaceError("surface JSON must be an object")
        if set(obj) != {"kind", "cell_id", "entries"}:
            raise PayoffSurfaceError(
                f"surface JSON keys must be exactly kind/cell_id/entries, "
                f"got {sorted(obj)}")
        kind, cell_id = obj["kind"], obj["cell_id"]
        if kind not in _SURFACE_KINDS:
            raise PayoffSurfaceError(f"unknown surface kind {kind!r}")
        if cell_id not in CELL_NODES:
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
        return _validate(raw, kind, cell_id, expected, manifest)


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
              candidates: Sequence[Any],
              manifest: PopulationManifest | None = None) -> ValidatedSurface:
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
                            observations=observations, data=raw,
                            manifest=manifest)


def validate_payoff_surface(raw: RawSurface, cell_id: str,
                            manifest: PopulationManifest | None = None
                            ) -> ValidatedSurface:
    """Validate a 3^S assignment surface for a named cell. `cell_id` is
    required: inferring S from the data cannot catch a surface built for
    the wrong cell."""
    if cell_id not in CELL_NODES:
        raise PayoffSurfaceError(f"unknown cell_id {cell_id!r}")
    return _validate(raw, "assignment", cell_id,
                     _expected_candidates("assignment", cell_id), manifest)


def validate_one_call_surface(raw: RawSurface, cell_id: str,
                              manifest: PopulationManifest | None = None
                              ) -> ValidatedSurface:
    """Best one-call whole-task control (§1.11 B5). Pair it with its
    assignment surface through a `CalibrationBundle` — that is what
    enforces the shared population."""
    if cell_id not in CELL_NODES:
        raise PayoffSurfaceError(f"unknown cell_id {cell_id!r}")
    return _validate(raw, "one_call", cell_id, list(ENDPOINT_IDS), manifest)


def validate_two_call_surface(raw: RawSurface, cell_id: str,
                              manifest: PopulationManifest | None = None
                              ) -> ValidatedSurface:
    """The 18-workflow contraction family (D12) — fork/join only."""
    if cell_id not in CELL_NODES:
        raise PayoffSurfaceError(f"unknown cell_id {cell_id!r}")
    return _validate(raw, "two_call", cell_id,
                     _expected_candidates("two_call", cell_id), manifest)


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
    endpoint-index tuple. Construction data only."""
    vs = _require_surface(surface, "assignment")
    _require_selection_phase(vs)
    return _argmax_in_tie_order(vs, vs.candidates)


def node_runner_up(surface: ValidatedSurface, deployable: tuple[int, ...],
                   node_index: int) -> tuple[int, ...]:
    """Best alternative endpoint at one node, all others fixed at the
    deployable assignment; ties → lowest endpoint index."""
    vs = _require_surface(surface, "assignment")
    _require_selection_phase(vs)
    _check_candidate("assignment", deployable, vs.cell_id)
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
    _require_selection_phase(vs)
    constants = [(e,) * vs.num_nodes for e in ENDPOINT_IDS]
    return _argmax_in_tie_order(vs, constants)


def uniform_random_accuracy(surface: ValidatedSurface) -> float:
    """§1.8 `random` control: the exact uniform mean over the enumerated
    3^S payoff surface (analytic, never Monte Carlo). Descriptive, so it is
    computable on any split."""
    vs = _require_surface(surface, "assignment")
    return sum(vs.accuracy(c) for c in vs.candidates) / len(vs.candidates)


def select_best_one_call(surface: ValidatedSurface) -> int:
    """Argmax over the 3 endpoints; tie → lowest index (§1.8)."""
    vs = _require_surface(surface, "one_call")
    _require_selection_phase(vs)
    return _argmax_in_tie_order(vs, vs.candidates)


def select_best_two_call(surface: ValidatedSurface
                         ) -> tuple[str, tuple[int, int]]:
    """Argmax over the 18-workflow family; tie → frozen order
    (lookup-first < code-first, then lexicographic endpoint tuple)."""
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
    random_accuracy: float
    best_one_call: int | None = None
    best_two_call: tuple[str, tuple[int, int]] | None = None

    def __post_init__(self) -> None:
        if self.namespace != SELECTION_NAMESPACE:
            raise PayoffSurfaceError(
                f"selections must come from {SELECTION_NAMESPACE} data")
        _check_candidate("assignment", self.deployable, self.cell_id)
        _check_candidate("assignment", self.best_fixed_assignment,
                         self.cell_id)
        for node, assignment in self.node_runner_ups.items():
            if node not in CELL_NODES[self.cell_id]:
                raise PayoffSurfaceError(f"unknown node {node!r}")
            _check_candidate("assignment", assignment, self.cell_id)
        if self.best_one_call is not None:
            _check_candidate("one_call", self.best_one_call, self.cell_id)
        if self.best_two_call is not None:
            _check_candidate("two_call", self.best_two_call, self.cell_id)
        object.__setattr__(self, "node_runner_ups",
                           MappingProxyType(dict(self.node_runner_ups)))

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
            "random_accuracy": self.random_accuracy,
            "best_one_call": self.best_one_call,
            "best_two_call": (None if self.best_two_call is None else
                              [self.best_two_call[0],
                               list(self.best_two_call[1])]),
        }

    @classmethod
    def from_json(cls, obj: Mapping[str, Any]) -> "FrozenSelections":
        if not isinstance(obj, Mapping):
            raise PayoffSurfaceError("selections JSON must be an object")
        required = {"cell_id", "namespace", "deployable",
                    "best_fixed_assignment", "node_runner_ups",
                    "random_accuracy", "best_one_call", "best_two_call"}
        if set(obj) != required:
            raise PayoffSurfaceError(
                f"selections JSON keys must be exactly {sorted(required)}")
        two_call = obj["best_two_call"]
        return cls(
            cell_id=obj["cell_id"], namespace=obj["namespace"],
            deployable=tuple(obj["deployable"]),
            best_fixed_assignment=tuple(obj["best_fixed_assignment"]),
            node_runner_ups={node: tuple(a) for node, a
                             in obj["node_runner_ups"].items()},
            random_accuracy=obj["random_accuracy"],
            best_one_call=obj["best_one_call"],
            best_two_call=(None if two_call is None
                           else (two_call[0], tuple(two_call[1]))))


@dataclass(frozen=True)
class CalibrationBundle:
    """Assignment surface plus its controls, proven to share one population.

    Stage-1 gates compare the deployable oracle against the best one-call
    and two-call controls. Those comparisons are only meaningful if every
    surface was scored on the *same* clusters and renderings — validating
    each surface in isolation cannot establish that.

    **Scope of that guarantee**: this is a same-identity structural check.
    It proves the arms agree with one another. Only a `PopulationManifest`
    on the surfaces proves they are the registered population, and only its
    execution fields (Stage 0B) prove the arms ran under one runtime
    profile, prompt revision, and endpoint set.
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
            random_accuracy=uniform_random_accuracy(self.assignment),
            best_one_call=(None if self.one_call is None
                           else select_best_one_call(self.one_call)),
            best_two_call=(None if self.two_call is None
                           else select_best_two_call(self.two_call)))

    # --- evaluation of frozen choices (no argmax) --------------------------

    def _check_frozen(self, frozen: FrozenSelections) -> FrozenSelections:
        if not isinstance(frozen, FrozenSelections):
            raise PayoffSurfaceError(
                "evaluation consumes a FrozenSelections artifact")
        if frozen.cell_id != self.cell_id:
            raise PayoffSurfaceError(
                f"selections are for {frozen.cell_id!r}, bundle for "
                f"{self.cell_id!r}")
        return frozen

    def deployable_accuracy(self, frozen: FrozenSelections) -> float:
        return self.assignment.accuracy(
            self._check_frozen(frozen).deployable)

    def best_fixed_accuracy(self, frozen: FrozenSelections) -> float:
        return self.assignment.accuracy(
            self._check_frozen(frozen).best_fixed_assignment)

    def one_call_accuracy(self, frozen: FrozenSelections) -> float:
        self._check_frozen(frozen)
        if self.one_call is None or frozen.best_one_call is None:
            raise PayoffSurfaceError("no one-call surface or selection")
        return self.one_call.accuracy(frozen.best_one_call)

    def two_call_accuracy(self, frozen: FrozenSelections) -> float:
        self._check_frozen(frozen)
        if self.two_call is None or frozen.best_two_call is None:
            raise PayoffSurfaceError("no two-call surface or selection")
        return self.two_call.accuracy(frozen.best_two_call)

    def deployable_vs_one_call(self, frozen: FrozenSelections) -> float:
        """Oracle advantage over the best single whole-task call, both
        chosen on construction data (the Stage-1A ≥ +20 point gate)."""
        return self.deployable_accuracy(frozen) - self.one_call_accuracy(frozen)

    def deployable_vs_two_call(self, frozen: FrozenSelections) -> float:
        return self.deployable_accuracy(frozen) - self.two_call_accuracy(frozen)


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
