"""Cohort builders: the frozen probe-selection rules (211_f §4 step 1,
210_s issue 4, 214_s P1).

A probe rule is a CLOSED schema frozen before any worker executes: it
may reference only identity coordinates (cell, latent index, renderer,
visibility) — there is no field that could carry a payoff, a direction
yield, or any other outcome, so outcome-blindness is enforced by the
schema rather than promised.

Two distinct builders (214_s): `freeze_first_probe_rule` produces the
SIGNED first probe and enforces its authorized shape — `routing_dev`,
group size 8, the full renderer crossing, and a factor-balanced prefix
(the generator's factor blocks have sizes 1, 2, 3 and 6, so the common
factor-balanced prefix length must be divisible by 6). The generic
`freeze_reprobe_rule` is for later, separately frozen reprobes and
keeps its parameters free within the development namespaces.

`bind_probe_cohort` consumes a surface DIRECTORY under its externally
frozen surface lock — never caller-supplied hashes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from tasks.conductor.types import (
    CELL_IDS, RENDERER_IDS, VISIBILITY_CONDITIONS, InfrastructureError,
)

from .charter import DEV_NAMESPACES, content_sha256
from .dev_support import validate_surface_lock

FIRST_PROBE_RULE_KIND = "routing-dev-first-probe-v1"
REPROBE_RULE_KIND = "routing-dev-reprobe-v1"

# 211_f §5: the signed first probe's fixed shape.
FIRST_PROBE_NAMESPACE = "routing_dev"
FIRST_PROBE_GROUP_SIZE = 8
# The generator's frozen factor-block sizes; a factor-balanced prefix
# must be a multiple of their least common multiple.
FACTOR_BLOCK_SIZES = (1, 2, 3, 6)
FACTOR_BALANCED_MULTIPLE = 6

# The complete, closed schema. Nothing here can name an outcome.
_PROBE_RULE_KEYS = frozenset({
    "kind", "namespace", "prefix_length_per_cell", "renderers",
    "visibility", "group_size", "groups_per_observation",
})


def _validate_common_fields(rule: Mapping[str, Any]) -> None:
    if rule["namespace"] not in DEV_NAMESPACES:
        raise InfrastructureError(
            f"{rule['namespace']!r} is not a development namespace")
    prefix = rule["prefix_length_per_cell"]
    if not isinstance(prefix, int) or isinstance(prefix, bool) \
            or prefix < 1:
        raise InfrastructureError(
            f"prefix_length_per_cell must be a positive int, got "
            f"{prefix!r}")
    renderers = rule["renderers"]
    if not renderers or len(set(renderers)) != len(renderers) \
            or any(r not in RENDERER_IDS for r in renderers):
        raise InfrastructureError(
            f"renderers {renderers!r} must be distinct members of "
            f"{RENDERER_IDS}")
    if rule["visibility"] not in VISIBILITY_CONDITIONS:
        raise InfrastructureError(
            f"unknown visibility {rule['visibility']!r}")
    for name in ("group_size", "groups_per_observation"):
        value = rule[name]
        if not isinstance(value, int) or isinstance(value, bool) \
                or value < 1:
            raise InfrastructureError(
                f"{name} must be a positive int, got {value!r}")


def _validate_first_probe_shape(rule: Mapping[str, Any]) -> None:
    """The signed 211_f §5 first probe, enforced (214_s P1)."""
    if rule["namespace"] != FIRST_PROBE_NAMESPACE:
        raise InfrastructureError(
            f"the first probe runs on {FIRST_PROBE_NAMESPACE!r}, not "
            f"{rule['namespace']!r} (211_f §5)")
    if rule["group_size"] != FIRST_PROBE_GROUP_SIZE:
        raise InfrastructureError(
            f"the first probe uses group size "
            f"{FIRST_PROBE_GROUP_SIZE}, not {rule['group_size']} "
            "(211_f §5)")
    if list(rule["renderers"]) != list(RENDERER_IDS):
        raise InfrastructureError(
            "the first probe crosses ALL renderers in canonical order "
            f"{RENDERER_IDS} (211_f §5)")
    if rule["prefix_length_per_cell"] % FACTOR_BALANCED_MULTIPLE != 0:
        raise InfrastructureError(
            f"a factor-balanced prefix must be divisible by "
            f"{FACTOR_BALANCED_MULTIPLE} (factor blocks "
            f"{FACTOR_BLOCK_SIZES}); got "
            f"{rule['prefix_length_per_cell']}")


def _freeze(kind: str, *, namespace: str, prefix_length_per_cell: int,
            renderers, visibility: str, group_size: int,
            groups_per_observation: int) -> dict[str, Any]:
    rule = {
        "kind": kind,
        "namespace": namespace,
        "prefix_length_per_cell": prefix_length_per_cell,
        "renderers": list(renderers),
        "visibility": visibility,
        "group_size": group_size,
        "groups_per_observation": groups_per_observation,
    }
    _validate_common_fields(rule)
    if kind == FIRST_PROBE_RULE_KIND:
        _validate_first_probe_shape(rule)
    return {"rule": rule, "rule_sha256": content_sha256(rule)}


def freeze_first_probe_rule(*, prefix_length_per_cell: int,
                            groups_per_observation: int,
                            visibility: str = "private"
                            ) -> dict[str, Any]:
    """The SIGNED first probe: routing_dev, group 8, full renderer
    crossing, factor-balanced prefix — anything else refuses."""
    return _freeze(FIRST_PROBE_RULE_KIND,
                   namespace=FIRST_PROBE_NAMESPACE,
                   prefix_length_per_cell=prefix_length_per_cell,
                   renderers=RENDERER_IDS, visibility=visibility,
                   group_size=FIRST_PROBE_GROUP_SIZE,
                   groups_per_observation=groups_per_observation)


def freeze_reprobe_rule(*, namespace: str, prefix_length_per_cell: int,
                        renderers, visibility: str, group_size: int,
                        groups_per_observation: int) -> dict[str, Any]:
    """A later, separately frozen reprobe (group-size or cohort
    changes per 211_f §§5, 9). Still outcome-blind by schema."""
    return _freeze(REPROBE_RULE_KIND, namespace=namespace,
                   prefix_length_per_cell=prefix_length_per_cell,
                   renderers=renderers, visibility=visibility,
                   group_size=group_size,
                   groups_per_observation=groups_per_observation)


def validate_probe_rule(frozen: Mapping[str, Any]) -> dict[str, Any]:
    """The rule must be exactly the closed schema, rehash, and satisfy
    its kind's shape — an extra key (however named) is a refusal,
    because the schema is the outcome-blindness guarantee."""
    rule = frozen.get("rule")
    if not isinstance(rule, Mapping):
        raise InfrastructureError("frozen probe rule carries no rule")
    if set(rule) != _PROBE_RULE_KEYS:
        raise InfrastructureError(
            f"probe rule keys {sorted(rule)} != the closed schema "
            f"{sorted(_PROBE_RULE_KEYS)} — outcome-blindness is "
            "enforced by the schema")
    if rule["kind"] not in (FIRST_PROBE_RULE_KIND, REPROBE_RULE_KIND):
        raise InfrastructureError(f"unknown rule kind {rule['kind']!r}")
    if frozen.get("rule_sha256") != content_sha256(dict(rule)):
        raise InfrastructureError(
            "probe rule does not rehash to its frozen rule_sha256")
    _validate_common_fields(rule)
    if rule["kind"] == FIRST_PROBE_RULE_KIND:
        _validate_first_probe_shape(rule)
    return dict(rule)


def probe_cohort_spec(frozen: Mapping[str, Any]) -> dict[str, Any]:
    """The rule applied: the exact per-cell index lists and renderer
    crossing the probe will use — a pure function of the rule, so the
    reviewer can regenerate the selection from the frozen bytes."""
    rule = validate_probe_rule(frozen)
    prefix = list(range(rule["prefix_length_per_cell"]))
    return {
        "namespace": rule["namespace"],
        "cohort": {cell: list(prefix) for cell in CELL_IDS},
        "renderers": list(rule["renderers"]),
        "visibility": rule["visibility"],
    }


def apply_probe_rule(frozen: Mapping[str, Any],
                     declaration: Mapping[str, Any]) -> list[str]:
    """Select the probe observation ids from a materialized-support
    declaration. Fail-closed: the declaration must contain EVERY
    observation the rule selects (the search cap must not have
    under-covered the prefix), and the selection uses identity fields
    only."""
    spec = probe_cohort_spec(frozen)
    if declaration["namespace"] != spec["namespace"]:
        raise InfrastructureError(
            f"declaration namespace {declaration['namespace']!r} != "
            f"rule namespace {spec['namespace']!r}")
    if declaration["visibility"] != spec["visibility"]:
        raise InfrastructureError(
            "declaration visibility does not match the rule")
    declared = {(obs["cell_id"], obs["renderer_id"],
                 obs["observation_id"]) for obs in
                declaration["observations"]}
    by_identity = {}
    for cell_id, renderer_id, observation_id in declared:
        parts = observation_id.split(":")
        index = int(parts[2])
        by_identity[(cell_id, index, renderer_id)] = observation_id
    selected = []
    for cell in sorted(spec["cohort"]):
        for index in spec["cohort"][cell]:
            for renderer in spec["renderers"]:
                key = (cell, index, renderer)
                if key not in by_identity:
                    raise InfrastructureError(
                        f"rule selects {key} but the materialized "
                        "declaration does not contain it — the support "
                        "under-covers the frozen prefix")
                selected.append(by_identity[key])
    return selected


def bind_probe_cohort(frozen: Mapping[str, Any],
                      surface_dir: str | Path,
                      expected_lock_sha256: str) -> dict[str, Any]:
    """211_f §4 step 6: the frozen rule applied verbatim to the
    LOCK-VALIDATED surface directory (214_s P1 — no caller-supplied
    hashes). ONLY the lock identity is new information here — the
    selection is regenerated from the rule, never edited."""
    surface_dir = Path(surface_dir)
    lock = validate_surface_lock(surface_dir, expected_lock_sha256)
    # 220_s F3: the ONLY bindable rule is the one the surface was
    # LAUNCHED under — the lock carries its hash.
    if frozen["rule_sha256"] != lock["probe_rule_sha256"]:
        raise InfrastructureError(
            "this surface was launched under a different probe rule — "
            "a post-materialization rule swap refuses (220_s F3)")
    declaration = json.loads(
        (surface_dir / "declaration.json").read_text(encoding="utf-8"))
    observation_ids = apply_probe_rule(frozen, declaration)
    record = {
        "kind": "routing-dev-probe-cohort-v1",
        "rule_sha256": frozen["rule_sha256"],
        "observation_ids": observation_ids,
        "surface_lock_sha256": lock["lock_sha256"],
        "payoffs_sha256": lock["payoffs_sha256"],
    }
    record["cohort_sha256"] = content_sha256(record)
    return record
