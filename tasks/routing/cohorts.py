"""Cohort builders: the frozen probe-selection rule (211_f §4 step 1,
210_s issue 4 — mechanically auditable outcome-blindness).

A probe rule is a CLOSED schema frozen before any worker executes: it
may reference only identity coordinates (cell, latent index, renderer,
visibility) — there is no field that could carry a payoff, a direction
yield, or any other outcome, so outcome-blindness is enforced by the
schema rather than promised. `apply_probe_rule` is a deterministic
function of (rule, declaration) alone: after materialization only the
surface hashes are added, via `bind_probe_cohort`, which refuses any
change to the selection itself.
"""

from __future__ import annotations

from typing import Any, Mapping

from tasks.conductor.types import (
    CELL_IDS, RENDERER_IDS, VISIBILITY_CONDITIONS, InfrastructureError,
)

from .charter import DEV_NAMESPACES, content_sha256

PROBE_RULE_KIND = "routing-dev-probe-selection-v1"

# The complete, closed schema. Nothing here can name an outcome.
_PROBE_RULE_KEYS = frozenset({
    "kind", "namespace", "prefix_length_per_cell", "renderers",
    "visibility", "group_size", "groups_per_observation",
})


def freeze_probe_rule(*, namespace: str, prefix_length_per_cell: int,
                      renderers: tuple[str, ...] | list[str],
                      visibility: str, group_size: int,
                      groups_per_observation: int) -> dict[str, Any]:
    """Content-hash the exact probe cohort rule BEFORE worker
    execution: the first `prefix_length_per_cell` latent indices of
    every cell (the outcome-blind, factor-balanced prefix), crossed
    with the declared renderers. The rule IS the selection function;
    there are no free choices left after this freeze."""
    if namespace not in DEV_NAMESPACES:
        raise InfrastructureError(
            f"{namespace!r} is not a development namespace")
    if not isinstance(prefix_length_per_cell, int) \
            or isinstance(prefix_length_per_cell, bool) \
            or prefix_length_per_cell < 1:
        raise InfrastructureError(
            f"prefix_length_per_cell must be a positive int, got "
            f"{prefix_length_per_cell!r}")
    if not renderers or len(set(renderers)) != len(renderers) \
            or any(r not in RENDERER_IDS for r in renderers):
        raise InfrastructureError(
            f"renderers {renderers!r} must be distinct members of "
            f"{RENDERER_IDS}")
    if visibility not in VISIBILITY_CONDITIONS:
        raise InfrastructureError(f"unknown visibility {visibility!r}")
    for name, value in (("group_size", group_size),
                        ("groups_per_observation",
                         groups_per_observation)):
        if not isinstance(value, int) or isinstance(value, bool) \
                or value < 1:
            raise InfrastructureError(
                f"{name} must be a positive int, got {value!r}")
    rule = {
        "kind": PROBE_RULE_KIND,
        "namespace": namespace,
        "prefix_length_per_cell": prefix_length_per_cell,
        "renderers": list(renderers),
        "visibility": visibility,
        "group_size": group_size,
        "groups_per_observation": groups_per_observation,
    }
    return {"rule": rule, "rule_sha256": content_sha256(rule)}


def validate_probe_rule(frozen: Mapping[str, Any]) -> dict[str, Any]:
    """The rule must be exactly the closed schema and must rehash —
    an extra key (however named) is a refusal, because the schema is
    the outcome-blindness guarantee."""
    rule = frozen.get("rule")
    if not isinstance(rule, Mapping):
        raise InfrastructureError("frozen probe rule carries no rule")
    if set(rule) != _PROBE_RULE_KEYS:
        raise InfrastructureError(
            f"probe rule keys {sorted(rule)} != the closed schema "
            f"{sorted(_PROBE_RULE_KEYS)} — outcome-blindness is "
            "enforced by the schema")
    if rule["kind"] != PROBE_RULE_KIND:
        raise InfrastructureError(f"unknown rule kind {rule['kind']!r}")
    if frozen.get("rule_sha256") != content_sha256(dict(rule)):
        raise InfrastructureError(
            "probe rule does not rehash to its frozen rule_sha256")
    # Re-validate the field contents through the freezer.
    rebuilt = freeze_probe_rule(
        namespace=rule["namespace"],
        prefix_length_per_cell=rule["prefix_length_per_cell"],
        renderers=rule["renderers"], visibility=rule["visibility"],
        group_size=rule["group_size"],
        groups_per_observation=rule["groups_per_observation"])
    if rebuilt["rule_sha256"] != frozen["rule_sha256"]:
        raise InfrastructureError("probe rule fields do not revalidate")
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
                      declaration: Mapping[str, Any],
                      surface_hashes: Mapping[str, str]
                      ) -> dict[str, Any]:
    """211_f §4 step 6: the frozen rule applied verbatim, bound to the
    exact surface hashes. ONLY the hashes are new information here —
    the selection is regenerated from the rule, never edited."""
    observation_ids = apply_probe_rule(frozen, declaration)
    record = {
        "kind": "routing-dev-probe-cohort-v1",
        "rule_sha256": frozen["rule_sha256"],
        "observation_ids": observation_ids,
        "surface_hashes": dict(sorted(surface_hashes.items())),
    }
    record["cohort_sha256"] = content_sha256(record)
    return record
