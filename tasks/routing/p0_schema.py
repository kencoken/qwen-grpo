"""P0 spine, Unit 1 REV2 — the P0ScienceContract SCHEMA (305_f;
307_s repairs).

Types only: the contract INSTANCE is constructed in Unit 2. 307_s
P1-3: scientific meaning lives in CLOSED RULE IDENTIFIERS plus
TYPED OPERATIVE FIELDS — not prose strings; every dataclass
validates its own invariants in `__post_init__`, so validation runs
from DIRECT CONSTRUCTION as well as loading; canonical
serialization uses `allow_nan=False`; the strict loader checks
primitive types, closed sets, finiteness, uniqueness, and hash
formats, and requires the EXTERNALLY reviewed expected hash."""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from tasks.conductor.types import InfrastructureError

SCHEMA_VERSION = "p0-science-contract-v2"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_DIRECT_Q1_CELLS = ("code_atomic", "fork_join", "math_code")
_Q2_DIRECTIONS = ("fork_join|w2_favoured", "math_code|w3_favoured")
_SENTINEL_EXCLUSIONS = ("direct_q1_gate", "sizing_minimum",
                        "authorization", "headline_q1")
# the signed sentinel diagnostic fields (304_s §4 complete contract)
_SENTINEL_FIELDS = (
    "worker1_selections", "worker1_completions",
    "reward1_completions", "reward_varying_groups",
    "q1_counted_groups", "group_denominator",
    "completion_denominator", "first_group_indices",
    "first_update_indices", "checkpoint_trajectory",
    "evaluation_trajectory",
)
_DIAGNOSTIC_VOCABULARY = (
    "q1_counted_by_cell", "q2_eligibility", "q2_optimality",
    "q2_choice_conditional_on_eligibility",
    "q2_marginal_target_selections",
    "direct_and_semantic_contrasts", "sentinel_block",
    "zero_variance_rate", "invalid_completion_rate",
)


def _require_hex64(value: Any, where: str) -> None:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise InfrastructureError(
            f"{where}: expected a 64-char lowercase hex hash")


def _require_positive_int(value: Any, where: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) \
            or value <= 0:
        raise InfrastructureError(
            f"{where}: expected a positive non-boolean integer")


def _require_nonneg_int(value: Any, where: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) \
            or value < 0:
        raise InfrastructureError(
            f"{where}: expected a non-negative non-boolean integer")


def _require_finite(value: Any, where: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value):
        raise InfrastructureError(
            f"{where}: expected a finite non-boolean number")


def _require_bool(value: Any, where: str) -> None:
    if not isinstance(value, bool):
        raise InfrastructureError(f"{where}: expected a bool")


def _require_rule_id(value: Any, allowed: str, where: str) -> None:
    if value != allowed:
        raise InfrastructureError(
            f"{where}: rule id must be {allowed!r}")


@dataclass(frozen=True)
class InputPins:
    """Authenticated input identities (305_f §2 + 307_s: the
    reviewed C2 identity/environment anchors included). Content and
    committed-file hashes only — nothing commit-dependent."""
    extension_surface_lock_sha256: str
    selection_record_sha256: str
    selection_file_sha256: str
    comparator_record_sha256: str
    pinned_mixture_record_sha256: str
    pinned_mixture_file_sha256: str
    c2_closeout_entry_sha256: str
    c2_actions_file_sha256: str
    c2_report_file_sha256: str
    c2_schedule_file_sha256: str
    c2_record_file_sha256: str
    c2_identity_manifest_sha256: str
    c2_attested_environment_sha256: str
    c2_projection_sha256: str
    c2_projection_file_sha256: str

    def __post_init__(self) -> None:
        for f in fields(self):
            _require_hex64(getattr(self, f.name),
                           f"input_pins.{f.name}")


@dataclass(frozen=True)
class ActiveScope:
    q1_direct_cells: tuple[str, ...]
    q2_description: str
    q3: str
    sentinel_cell: str
    sentinel_observation_ids: tuple[str, ...]
    sentinel_excluded_from: tuple[str, ...]
    sentinel_training_exposed: bool

    def __post_init__(self) -> None:
        if tuple(self.q1_direct_cells) != _DIRECT_Q1_CELLS:
            raise InfrastructureError(
                f"scope.q1_direct_cells must be exactly "
                f"{_DIRECT_Q1_CELLS}")
        if self.q3 != "out_of_scope":
            raise InfrastructureError(
                "scope.q3 must be 'out_of_scope' for this P0")
        if self.sentinel_cell != "math_atomic":
            raise InfrastructureError(
                "scope.sentinel_cell must be 'math_atomic'")
        if len(self.sentinel_observation_ids) != 3 or \
                len(set(self.sentinel_observation_ids)) != 3:
            raise InfrastructureError(
                "scope.sentinel_observation_ids must be exactly 3 "
                "distinct ids")
        if tuple(self.sentinel_excluded_from) != _SENTINEL_EXCLUSIONS:
            raise InfrastructureError(
                f"scope.sentinel_excluded_from must be exactly "
                f"{_SENTINEL_EXCLUSIONS}")
        _require_bool(self.sentinel_training_exposed,
                      "scope.sentinel_training_exposed")
        if self.sentinel_training_exposed is not True:
            raise InfrastructureError(
                "the sentinel is training-exposed by design")


@dataclass(frozen=True)
class Q1CountedEvent:
    """The Q1 counted event, structurally (307_s P1-3): within one
    group, ≥1 VALID completion at `high_reward` with FULL family
    correctness AND ≥1 VALID completion at `low_reward` with
    STRICTLY LOWER family correctness."""
    rule_id: str
    valid_completions_only: bool
    same_group: bool
    high_reward: float
    high_family_correctness: str     # closed: "full"
    low_reward: float
    low_family_correctness: str      # closed: "strictly_lower"

    def __post_init__(self) -> None:
        _require_rule_id(self.rule_id, "q1-counted-v1",
                         "q1.event.rule_id")
        _require_bool(self.valid_completions_only,
                      "q1.event.valid_completions_only")
        _require_bool(self.same_group, "q1.event.same_group")
        if not (self.valid_completions_only and self.same_group):
            raise InfrastructureError(
                "the Q1 event is valid-only and same-group by "
                "definition")
        _require_finite(self.high_reward, "q1.event.high_reward")
        _require_finite(self.low_reward, "q1.event.low_reward")
        if self.high_reward != 1.0 or self.low_reward != 0.5:
            raise InfrastructureError(
                "the registered Q1 rewards are 1.0 / 0.5")
        if self.high_family_correctness != "full" \
                or self.low_family_correctness != "strictly_lower":
            raise InfrastructureError(
                "the registered Q1 family-correctness conditions are "
                "full / strictly_lower")


@dataclass(frozen=True)
class Q1Rule:
    version: str
    population: str                  # closed: "bridge_rows"
    event: Q1CountedEvent
    min_counted_groups_per_cell: int
    min_distinct_latents_among_counted: int
    sizing_counts: tuple[tuple[str, int], ...]
    sizing_epochs: int

    def __post_init__(self) -> None:
        _require_rule_id(self.version, "q1-v2", "q1.version")
        if self.population != "bridge_rows":
            raise InfrastructureError(
                "q1.population must be 'bridge_rows'")
        _require_positive_int(self.min_counted_groups_per_cell,
                              "q1.min_counted_groups_per_cell")
        _require_positive_int(
            self.min_distinct_latents_among_counted,
            "q1.min_distinct_latents_among_counted")
        cells = tuple(cell for cell, _ in self.sizing_counts)
        if cells != _DIRECT_Q1_CELLS:
            raise InfrastructureError(
                f"q1.sizing_counts cells must be exactly "
                f"{_DIRECT_Q1_CELLS} in order")
        for cell, count in self.sizing_counts:
            _require_positive_int(count,
                                  f"q1.sizing_counts[{cell}]")
        _require_positive_int(self.sizing_epochs, "q1.sizing_epochs")


@dataclass(frozen=True)
class EligibilityRule:
    """C2 eligibility, structurally: correct non-Code routing and a
    Code worker in the specialist set; malformed completions are
    excluded from every denominator."""
    rule_id: str
    non_code_routing: str            # closed: "family_correct"
    code_worker_in: tuple[int, ...]
    malformed_completions: str       # closed: "excluded"

    def __post_init__(self) -> None:
        _require_rule_id(self.rule_id, "c2-eligibility-v1",
                         "q2.eligibility.rule_id")
        if self.non_code_routing != "family_correct":
            raise InfrastructureError(
                "eligibility requires family-correct non-Code "
                "routing")
        if tuple(self.code_worker_in) != (2, 3):
            raise InfrastructureError(
                "the specialist set is exactly (2, 3)")
        if self.malformed_completions != "excluded":
            raise InfrastructureError(
                "malformed completions are excluded from "
                "denominators")


@dataclass(frozen=True)
class ConditionalBaseline:
    direction: str
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if self.direction not in _Q2_DIRECTIONS:
            raise InfrastructureError(
                f"unknown Q2 direction {self.direction!r}")
        _require_nonneg_int(self.numerator,
                            f"baseline[{self.direction}].numerator")
        _require_nonneg_int(self.denominator,
                            f"baseline[{self.direction}].denominator")
        if self.numerator > self.denominator:
            raise InfrastructureError(
                f"baseline[{self.direction}]: numerator > "
                "denominator")


@dataclass(frozen=True)
class Q2Rule:
    """The four Q2 quantities, distinct and typed (304_s §3): the
    MARGINAL gate authorizes; the CONDITIONAL estimand (optimal /
    eligible, zero denominator undefined) is the learning quantity;
    eligibility is structural; baselines are numeric records."""
    version: str
    marginal_rule_id: str            # closed: "q2-marginal-v1"
    marginal_min_target_selections: int
    marginal_min_distinct_latents: int
    marginal_population: str         # closed: "valid_q2_composite"
    marginal_upstream_correctness_required: bool
    per_direction_targets: tuple[tuple[str, int], ...]
    eligibility: EligibilityRule
    conditional_rule_id: str         # closed: "q2-conditional-v1"
    conditional_numerator: str       # closed: "c2_optimal"
    conditional_denominator: str     # closed: "c2_eligible"
    conditional_zero_denominator: str  # closed: "undefined"
    conditional_baselines: tuple[ConditionalBaseline, ...]
    marginal_baselines: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        _require_rule_id(self.version, "q2-v2", "q2.version")
        _require_rule_id(self.marginal_rule_id, "q2-marginal-v1",
                         "q2.marginal_rule_id")
        _require_positive_int(self.marginal_min_target_selections,
                              "q2.marginal_min_target_selections")
        _require_positive_int(self.marginal_min_distinct_latents,
                              "q2.marginal_min_distinct_latents")
        if self.marginal_population != "valid_q2_composite":
            raise InfrastructureError(
                "the marginal population is valid q2_composite "
                "completions")
        _require_bool(self.marginal_upstream_correctness_required,
                      "q2.marginal_upstream_correctness_required")
        if self.marginal_upstream_correctness_required is not False:
            raise InfrastructureError(
                "the marginal gate is UNCONDITIONAL on upstream "
                "correctness by definition — it must never become "
                "the conditional estimand")
        directions = tuple(d for d, _ in self.per_direction_targets)
        if sorted(directions) != sorted(_Q2_DIRECTIONS):
            raise InfrastructureError(
                f"q2.per_direction_targets must cover exactly "
                f"{_Q2_DIRECTIONS}")
        for direction, worker in self.per_direction_targets:
            if worker not in (2, 3):
                raise InfrastructureError(
                    f"{direction}: target worker must be 2 or 3")
        _require_rule_id(self.conditional_rule_id,
                         "q2-conditional-v1",
                         "q2.conditional_rule_id")
        if self.conditional_numerator != "c2_optimal" \
                or self.conditional_denominator != "c2_eligible" \
                or self.conditional_zero_denominator != "undefined":
            raise InfrastructureError(
                "the conditional estimand is c2_optimal / "
                "c2_eligible with zero denominator UNDEFINED")
        baseline_dirs = tuple(b.direction
                              for b in self.conditional_baselines)
        if sorted(baseline_dirs) != sorted(_Q2_DIRECTIONS):
            raise InfrastructureError(
                "conditional baselines must cover exactly the Q2 "
                "directions")
        marginal_dirs = tuple(d for d, _ in self.marginal_baselines)
        if sorted(marginal_dirs) != sorted(_Q2_DIRECTIONS):
            raise InfrastructureError(
                "marginal baselines must cover exactly the Q2 "
                "directions")
        for direction, count in self.marginal_baselines:
            _require_positive_int(
                count, f"q2.marginal_baselines[{direction}]")


@dataclass(frozen=True)
class CapRule:
    """The 304_s §5 branch semantics, structurally closed."""
    rule_id: str                     # closed: "p0-cap-v1"
    launch_epochs: str               # closed: "min_nominal_capacity"
    capacity_inputs: tuple[str, ...]
    capacity_zero_action: str        # closed: "stop_reviewed_amendment"
    under_target_action: str         # closed: "disclosed_under_target"
    spare_capacity_action: str       # closed: "no_extra_training"

    def __post_init__(self) -> None:
        _require_rule_id(self.rule_id, "p0-cap-v1", "cap.rule_id")
        if self.launch_epochs != "min_nominal_capacity":
            raise InfrastructureError(
                "launch epochs = min(nominal, capacity), closed")
        expected_inputs = (
            "operational_ceiling_seconds",
            "cumulative_consumed_seconds",
            "measured_finalization_reserve_seconds",
            "frozen_non_rollout_overhead_seconds",
            "measured_whole_epoch_seconds")
        if tuple(self.capacity_inputs) != expected_inputs:
            raise InfrastructureError(
                f"cap.capacity_inputs must be exactly "
                f"{expected_inputs}")
        if self.capacity_zero_action != "stop_reviewed_amendment" \
                or self.under_target_action != \
                "disclosed_under_target" \
                or self.spare_capacity_action != "no_extra_training":
            raise InfrastructureError(
                "the cap branch actions are closed: "
                "stop_reviewed_amendment / disclosed_under_target / "
                "no_extra_training")


@dataclass(frozen=True)
class SizingRule:
    target_q1_counted_groups_per_sizing_cell: int
    groups_per_epoch: int
    nominal_epochs: int
    operational_ceiling_hours: float
    cap: CapRule

    def __post_init__(self) -> None:
        _require_positive_int(
            self.target_q1_counted_groups_per_sizing_cell,
            "sizing.target")
        _require_positive_int(self.groups_per_epoch,
                              "sizing.groups_per_epoch")
        _require_positive_int(self.nominal_epochs,
                              "sizing.nominal_epochs")
        _require_finite(self.operational_ceiling_hours,
                        "sizing.operational_ceiling_hours")
        if self.operational_ceiling_hours <= 0:
            raise InfrastructureError(
                "sizing.operational_ceiling_hours must be positive")


@dataclass(frozen=True)
class SentinelDiagnostics:
    """The COMPLETE signed sentinel specification (304_s §4): a
    closed field set — every field required at every P0
    checkpoint/evaluation."""
    fields_required: tuple[str, ...]

    def __post_init__(self) -> None:
        if tuple(self.fields_required) != _SENTINEL_FIELDS:
            raise InfrastructureError(
                f"sentinel diagnostics must require exactly "
                f"{_SENTINEL_FIELDS}")


@dataclass(frozen=True)
class RequiredDiagnostics:
    items: tuple[str, ...]
    sentinel: SentinelDiagnostics

    def __post_init__(self) -> None:
        if len(set(self.items)) != len(self.items):
            raise InfrastructureError(
                "diagnostics.items must be unique")
        unknown = set(self.items) - set(_DIAGNOSTIC_VOCABULARY)
        if unknown:
            raise InfrastructureError(
                f"unknown diagnostics {sorted(unknown)} — the "
                "vocabulary is closed")
        missing = set(_DIAGNOSTIC_VOCABULARY) - set(self.items)
        if missing:
            raise InfrastructureError(
                f"diagnostics.items missing {sorted(missing)} — the "
                "301_f list is complete, not a menu")


@dataclass(frozen=True)
class P0ScienceContract:
    schema_version: str
    input_pins: InputPins
    scope: ActiveScope
    q1: Q1Rule
    q2: Q2Rule
    sizing: SizingRule
    diagnostics: RequiredDiagnostics

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise InfrastructureError(
                f"contract schema {self.schema_version!r} != "
                f"{SCHEMA_VERSION!r}")


_NESTED = {
    "input_pins": InputPins, "scope": ActiveScope, "q1": Q1Rule,
    "q2": Q2Rule, "sizing": SizingRule,
    "diagnostics": RequiredDiagnostics,
}
_INNER = {
    "event": Q1CountedEvent, "eligibility": EligibilityRule,
    "cap": CapRule, "sentinel": SentinelDiagnostics,
}
_PAIR_TUPLES = {"sizing_counts", "per_direction_targets",
                "marginal_baselines"}
_PLAIN_TUPLES = {"q1_direct_cells", "sentinel_observation_ids",
                 "sentinel_excluded_from", "items", "code_worker_in",
                 "capacity_inputs", "fields_required"}


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return {f.name: _to_jsonable(getattr(value, f.name))
                for f in fields(value)}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise InfrastructureError(
        f"non-canonical value in contract: {type(value).__name__}")


def canonical_contract_json(contract: P0ScienceContract) -> str:
    return json.dumps(_to_jsonable(contract), sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def contract_sha256(contract: P0ScienceContract) -> str:
    return hashlib.sha256(
        canonical_contract_json(contract).encode("utf-8")).hexdigest()


def save_contract(contract: P0ScienceContract,
                  path: str | Path) -> str:
    digest = contract_sha256(contract)
    Path(path).write_text(
        json.dumps(_to_jsonable(contract), sort_keys=True, indent=1,
                   allow_nan=False) + "\n", encoding="utf-8")
    return digest


def _build(cls, payload: Any, where: str):
    if not isinstance(payload, dict):
        raise InfrastructureError(f"{where}: expected an object")
    field_names = {f.name for f in fields(cls)}
    unknown = set(payload) - field_names
    if unknown:
        raise InfrastructureError(
            f"{where}: unknown fields {sorted(unknown)} — the schema "
            "is closed")
    missing = field_names - set(payload)
    if missing:
        raise InfrastructureError(
            f"{where}: missing fields {sorted(missing)}")
    kwargs = {}
    for f in fields(cls):
        value = payload[f.name]
        if cls is P0ScienceContract and f.name in _NESTED:
            kwargs[f.name] = _build(_NESTED[f.name], value,
                                    f"{where}.{f.name}")
        elif f.name in _INNER:
            kwargs[f.name] = _build(_INNER[f.name], value,
                                    f"{where}.{f.name}")
        elif f.name == "conditional_baselines":
            if not isinstance(value, list):
                raise InfrastructureError(
                    f"{where}.{f.name}: expected a list")
            kwargs[f.name] = tuple(
                _build(ConditionalBaseline, item,
                       f"{where}.{f.name}[{i}]")
                for i, item in enumerate(value))
        elif f.name in _PAIR_TUPLES:
            if not isinstance(value, list) or any(
                    not isinstance(pair, list) or len(pair) != 2
                    for pair in value):
                raise InfrastructureError(
                    f"{where}.{f.name}: expected a list of pairs")
            kwargs[f.name] = tuple(
                (pair[0], pair[1]) for pair in value)
        elif f.name in _PLAIN_TUPLES:
            if not isinstance(value, list):
                raise InfrastructureError(
                    f"{where}.{f.name}: expected a list")
            kwargs[f.name] = tuple(value)
        else:
            kwargs[f.name] = value
    return cls(**kwargs)     # __post_init__ validates invariants


def load_contract(path: str | Path,
                  expected_sha256: str) -> P0ScienceContract:
    """The STRICT loader: closed schema, per-dataclass invariant
    validation (via construction), and the EXTERNALLY reviewed
    expected hash — required and checked."""
    if not isinstance(expected_sha256, str) \
            or not _HEX64.fullmatch(expected_sha256):
        raise InfrastructureError(
            "load_contract requires the externally reviewed expected "
            "hash — a self-hash alone is not authentication")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    contract = _build(P0ScienceContract, payload, "contract")
    digest = contract_sha256(contract)
    if digest != expected_sha256:
        raise InfrastructureError(
            "contract does not hash to the externally reviewed "
            "expected value")
    return contract
