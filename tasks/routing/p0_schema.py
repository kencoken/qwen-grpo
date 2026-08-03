"""P0 spine, Unit 1 — the P0ScienceContract SCHEMA (305_f-signed
design; 303_f §2/§7).

Types only: the contract INSTANCE is constructed in Unit 2. The
schema delivers what 302_s/304_s required of the container itself:

- deep immutability — nested frozen dataclasses and TUPLES
  throughout (no shallowly mutable dicts/lists anywhere in the
  hashed body);
- canonical serialization and an explicit `schema_version`;
- a STRICT persisted loader: closed field sets (unknown fields
  refuse), schema-version check, tuple reconstruction, and
  **external authentication — the loader takes an externally
  reviewed expected hash; a self-hash alone is never
  authentication** (304_s §7 via 302_s §7);
- the identity dependency graph of 305_f §1: this artifact carries
  input pins and RULES only — never terminal hashes, never
  commit-dependent environment or execution-manifest hashes.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from tasks.conductor.types import InfrastructureError

SCHEMA_VERSION = "p0-science-contract-v1"


@dataclass(frozen=True)
class InputPins:
    """Authenticated input identities (305_f §2). Content hashes and
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
    c2_projection_file_sha256: str


@dataclass(frozen=True)
class ActiveScope:
    """The 301_f/302_s §6 scope, machine-readable."""
    q1_direct_cells: tuple[str, ...]
    q2_description: str
    q3: str                      # always "out_of_scope" for this P0
    sentinel_cell: str
    sentinel_observation_ids: tuple[str, ...]
    sentinel_excluded_from: tuple[str, ...]
    sentinel_training_exposed: bool


@dataclass(frozen=True)
class Q1Rule:
    """The versioned Q1 rule (304_s §3)."""
    version: str
    population: str              # "bridge rows in the direct-Q1 cells"
    min_counted_groups_per_cell: int
    min_distinct_latents_among_counted: int
    sizing_counts: tuple[tuple[str, int], ...]   # authenticated C2 counts
    sizing_epochs: int           # the C2 epochs the counts came from


@dataclass(frozen=True)
class Q2Rule:
    """The versioned Q2 rules (304_s §3): the four quantities are
    DISTINCT; the marginal gate never becomes the conditional
    estimand."""
    version: str
    marginal_min_target_selections: int
    marginal_min_distinct_latents: int
    per_direction_targets: tuple[tuple[str, int], ...]
    conditional_estimand: str    # "optimal / eligible; zero denom = None"
    conditional_baselines: tuple[tuple[str, str], ...]  # direction -> "n/d"
    marginal_baselines: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class SizingRule:
    """The registered sizing + the 304_s §5 nominal/capacity split.
    RULES only — the beta-smoke numbers arrive in the LaunchFreeze."""
    target_q1_counted_groups_per_sizing_cell: int
    groups_per_epoch: int
    nominal_epochs: int
    operational_ceiling_hours: float
    launch_epochs_rule: str      # "min(nominal, capacity)"
    capacity_zero_rule: str      # "stop for a reviewed amendment"
    under_target_rule: str       # "disclosed under-target branch"
    spare_capacity_rule: str     # "never extra training"


@dataclass(frozen=True)
class RequiredDiagnostics:
    """The 301_f trajectory-retention list (raw numerators AND
    denominators)."""
    items: tuple[str, ...]


@dataclass(frozen=True)
class P0ScienceContract:
    schema_version: str
    input_pins: InputPins
    scope: ActiveScope
    q1: Q1Rule
    q2: Q2Rule
    sizing: SizingRule
    diagnostics: RequiredDiagnostics


_NESTED_TYPES = {
    "input_pins": InputPins,
    "scope": ActiveScope,
    "q1": Q1Rule,
    "q2": Q2Rule,
    "sizing": SizingRule,
    "diagnostics": RequiredDiagnostics,
}
_TUPLE_OF_PAIRS_FIELDS = {"sizing_counts", "per_direction_targets",
                          "conditional_baselines",
                          "marginal_baselines"}
_TUPLE_FIELDS = {"q1_direct_cells", "sentinel_observation_ids",
                 "sentinel_excluded_from", "items"}


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
    """The ONE canonical serialization (sorted keys, no whitespace
    variance)."""
    if contract.schema_version != SCHEMA_VERSION:
        raise InfrastructureError(
            f"contract schema {contract.schema_version!r} != "
            f"{SCHEMA_VERSION!r}")
    return json.dumps(_to_jsonable(contract), sort_keys=True,
                      separators=(",", ":"))


def contract_sha256(contract: P0ScienceContract) -> str:
    return hashlib.sha256(
        canonical_contract_json(contract).encode("utf-8")).hexdigest()


def save_contract(contract: P0ScienceContract,
                  path: str | Path) -> str:
    """Persist canonically; returns the contract hash (which the
    REVIEW records externally — saving does not authenticate)."""
    digest = contract_sha256(contract)
    Path(path).write_text(
        json.dumps(_to_jsonable(contract), sort_keys=True, indent=1)
        + "\n", encoding="utf-8")
    return digest


def _build_dataclass(cls, payload: Any, where: str):
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
        if f.name in _NESTED_TYPES and cls is P0ScienceContract:
            kwargs[f.name] = _build_dataclass(
                _NESTED_TYPES[f.name], value, f"{where}.{f.name}")
        elif f.name in _TUPLE_OF_PAIRS_FIELDS:
            if not isinstance(value, list) or any(
                    not isinstance(pair, list) or len(pair) != 2
                    for pair in value):
                raise InfrastructureError(
                    f"{where}.{f.name}: expected a list of pairs")
            kwargs[f.name] = tuple(
                (pair[0], pair[1]) for pair in value)
        elif f.name in _TUPLE_FIELDS:
            if not isinstance(value, list):
                raise InfrastructureError(
                    f"{where}.{f.name}: expected a list")
            kwargs[f.name] = tuple(value)
        else:
            kwargs[f.name] = value
    return cls(**kwargs)


def load_contract(path: str | Path,
                  expected_sha256: str) -> P0ScienceContract:
    """The STRICT loader: closed schema, version check, tuple
    reconstruction — and the EXTERNALLY REVIEWED expected hash is
    required and checked; a self-consistent file alone never
    authenticates (304_s §7)."""
    if not isinstance(expected_sha256, str) \
            or len(expected_sha256) != 64:
        raise InfrastructureError(
            "load_contract requires the externally reviewed expected "
            "hash — a self-hash alone is not authentication")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    contract = _build_dataclass(P0ScienceContract, payload,
                                "contract")
    if contract.schema_version != SCHEMA_VERSION:
        raise InfrastructureError(
            f"contract schema {contract.schema_version!r} != "
            f"{SCHEMA_VERSION!r}")
    digest = contract_sha256(contract)
    if digest != expected_sha256:
        raise InfrastructureError(
            "contract does not hash to the externally reviewed "
            "expected value")
    return contract
