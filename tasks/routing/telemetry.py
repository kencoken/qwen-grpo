"""Stratified group telemetry (211_f §7, 208_s F6, 210_s issue 1).

Input unit: one COMPLETED GROUP — the G completions sampled for one
observation — as
    {"observation_id", "completions": [
        {"parseable": bool, "valid": bool,
         "assignment": [semantic worker ids] | None,
         "reward": float}, ...]}
plus the observation's meta (cell, renderer, latent) and the pair
table / surface for the direction-bearing quantities.

The three contrast notions stay separate everywhere (211_f §5):
FORMAT (invalid vs valid), SEMANTIC (valid 0.5 vs 1), and the exact
w2/w3 DIRECT contrast — a group contains BOTH members of the
`family_correct_variants` pair. C1 is node-level family-correct
routing (malformed scores 0 and stays in the denominator, the 130_s
§6.5 rule); C2 is optimal-specialist selection CONDITIONAL on all
non-Code nodes family-correct AND the Code choice in {2,3}, where
"optimal" is the per-observation payoff winner and tied observations
are a separate stratum. ScaleLift collapses every selected worker-2/3
Code position to `c_fixed_dev` (both members of a malformed pair
contribute 0). Every aggregate rate is reported with its raw count
and denominator (206_s / 204_s).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping

from tasks.conductor.stage1 import NODE_FAMILIES, WORKER_FAMILIES
from tasks.conductor.types import InfrastructureError

REWARD_LEVELS = ("0", "0.5", "1")


def _reward_level(value: float) -> str:
    for level in REWARD_LEVELS:
        if value == float(level):
            return level
    raise InfrastructureError(
        f"reward {value!r} outside the frozen ladder {REWARD_LEVELS}")


def _family_correct_fraction(cell_id: str,
                             assignment: list[int] | tuple[int, ...]
                             ) -> float:
    families = NODE_FAMILIES[cell_id]
    nodes = sorted(families)
    if len(assignment) != len(nodes):
        raise InfrastructureError(
            f"{cell_id}: assignment arity {len(assignment)} != "
            f"{len(nodes)} nodes")
    correct = sum(
        1 for node, worker in zip(nodes, assignment)
        if WORKER_FAMILIES.get(worker) == families[node])
    return correct / len(nodes)


def _collapse_code(cell_id: str,
                   assignment: list[int] | tuple[int, ...],
                   c_fixed_dev: int) -> tuple[int, ...]:
    """The 130_s §6.4 collapse: every selected worker-2/3 at a Code
    node becomes c_fixed_dev; wrong-family selections and non-Code
    nodes are untouched."""
    families = NODE_FAMILIES[cell_id]
    nodes = sorted(families)
    return tuple(
        c_fixed_dev if families[node] == "code" and worker in (2, 3)
        else worker
        for node, worker in zip(nodes, assignment))


def group_stats(group: Mapping[str, Any], *,
                meta: Mapping[str, Any],
                pair_entry: Mapping[str, Any] | None,
                surface: Mapping[tuple[str, tuple[int, ...]], float],
                c_fixed_dev: int) -> dict[str, Any]:
    """All per-group quantities for one completed group. `pair_entry`
    is the observation's `eligible_pair_table` row (None for Code-free
    cells); `meta` carries cell_id / renderer_id / latent_program_id.
    """
    completions = group["completions"]
    if not completions:
        raise InfrastructureError("empty group")
    cell = meta["cell_id"]
    observation_id = group["observation_id"]
    n = len(completions)
    parseable = valid = 0
    rewards: list[float] = []
    levels = Counter()
    assignments: Counter = Counter()
    worker_counts: Counter = Counter()
    c1_values: list[float] = []
    c2_eligible = 0
    c2_optimal = 0
    scale_lift_terms: list[float] = []
    direction = None
    if pair_entry is not None and pair_entry["distinct_payoff"]:
        direction = pair_entry["direction"]
    for completion in completions:
        reward = float(completion["reward"])
        level = _reward_level(reward)
        rewards.append(reward)
        levels[level] += 1
        if completion.get("parseable"):
            parseable += 1
        if not completion.get("valid"):
            # 130_s §6.5: malformed scores 0 in C1 and contributes 0 to
            # both members of the ScaleLift pair — never dropped.
            c1_values.append(0.0)
            scale_lift_terms.append(0.0)
            continue
        valid += 1
        assignment = tuple(completion["assignment"])
        assignments[",".join(str(w) for w in assignment)] += 1
        for worker in assignment:
            worker_counts[worker] += 1
        c1_values.append(_family_correct_fraction(cell, assignment))
        collapsed = _collapse_code(cell, assignment, c_fixed_dev)
        if collapsed != assignment:
            key = (observation_id, collapsed)
            if key not in surface:
                raise InfrastructureError(
                    f"{key!r}: collapse row missing from the surface — "
                    "ScaleLift needs the complete 4^S space")
            scale_lift_terms.append(reward - surface[key])
        else:
            scale_lift_terms.append(0.0)
        if pair_entry is not None:
            families = NODE_FAMILIES[cell]
            nodes = sorted(families)
            non_code_ok = all(
                WORKER_FAMILIES.get(w) == families[node]
                for node, w in zip(nodes, assignment)
                if families[node] != "code")
            code_choices = [w for node, w in zip(nodes, assignment)
                            if families[node] == "code"]
            if non_code_ok and code_choices \
                    and all(w in (2, 3) for w in code_choices):
                c2_eligible += 1
                if direction is not None:
                    winner = tuple(
                        pair_entry[f"assignment_w{direction}"])
                    if assignment == winner:
                        c2_optimal += 1
    variant_hits = None
    if pair_entry is not None:
        w2 = ",".join(str(w) for w in pair_entry["assignment_w2"])
        w3 = ",".join(str(w) for w in pair_entry["assignment_w3"])
        variant_hits = {"w2": assignments.get(w2, 0),
                        "w3": assignments.get(w3, 0)}
    reward_set = set(rewards)
    zero_variance_level = (_reward_level(rewards[0])
                           if len(reward_set) == 1 else None)
    entropy = 0.0
    for count in assignments.values():
        p = count / valid if valid else 0.0
        if p > 0:
            entropy -= p * math.log2(p)
    return {
        "observation_id": observation_id,
        "cell_id": cell,
        "renderer_id": meta["renderer_id"],
        "direction": (f"w{direction}_favoured" if direction is not None
                      else ("tied" if pair_entry is not None
                            else "no_pair")),
        "n": n,
        "parseable": parseable,
        "valid": valid,
        "reward_levels": {level: levels.get(level, 0)
                          for level in REWARD_LEVELS},
        "mean_reward": sum(rewards) / n,
        "zero_variance_level": zero_variance_level,
        "format_contrast": valid > 0 and valid < n,
        "semantic_contrast": levels.get("0.5", 0) > 0
        and levels.get("1", 0) > 0,
        "direct_contrast": (variant_hits is not None
                            and variant_hits["w2"] > 0
                            and variant_hits["w3"] > 0),
        "variant_hits": variant_hits,
        "c1_mean": sum(c1_values) / n,
        "c2_eligible": c2_eligible,
        "c2_optimal": (c2_optimal if direction is not None else None),
        "scale_lift_mean": sum(scale_lift_terms) / n,
        "assignment_counts": dict(sorted(assignments.items())),
        "worker_counts": {str(w): worker_counts.get(w, 0)
                          for w in sorted(worker_counts)},
        "routing_entropy_bits": entropy,
        "max_assignment_concentration": (
            max(assignments.values()) / valid if valid else None),
    }


# --- stratified aggregation -----------------------------------------------------

def _rate(count: int, denominator: int) -> dict[str, Any]:
    """Every rate carries its raw count and denominator (206_s)."""
    return {"count": count, "denominator": denominator,
            "rate": (count / denominator) if denominator else None}


def _aggregate(groups: list[Mapping[str, Any]]) -> dict[str, Any]:
    n_groups = len(groups)
    completions = sum(g["n"] for g in groups)
    valid = sum(g["valid"] for g in groups)
    zero_var = {level: sum(1 for g in groups
                           if g["zero_variance_level"] == level)
                for level in REWARD_LEVELS}
    c2_den = sum(g["c2_eligible"] for g in groups
                 if g["c2_optimal"] is not None)
    c2_num = sum(g["c2_optimal"] for g in groups
                 if g["c2_optimal"] is not None)
    out = {
        "groups": n_groups,
        "completions": completions,
        "parse": _rate(sum(g["parseable"] for g in groups), completions),
        "valid": _rate(valid, completions),
        "reward_levels": {
            level: _rate(sum(g["reward_levels"][level] for g in groups),
                         completions)
            for level in REWARD_LEVELS},
        "mean_reward": (sum(g["mean_reward"] * g["n"] for g in groups)
                        / completions),
        "zero_variance": {
            "any": _rate(sum(zero_var.values()), n_groups),
            **{f"all_{level}": _rate(zero_var[level], n_groups)
               for level in REWARD_LEVELS}},
        "format_contrast": _rate(
            sum(1 for g in groups if g["format_contrast"]), n_groups),
        "semantic_contrast": _rate(
            sum(1 for g in groups if g["semantic_contrast"]), n_groups),
        "direct_contrast": _rate(
            sum(1 for g in groups if g["direct_contrast"]), n_groups),
        "c1_family_correct": {
            "mean": (sum(g["c1_mean"] * g["n"] for g in groups)
                     / completions),
            "denominator": completions},
        "c2_optimal_specialist": _rate(c2_num, c2_den),
        "c2_eligible_completions": _rate(
            sum(g["c2_eligible"] for g in groups), completions),
        "scale_lift": {
            "mean": (sum(g["scale_lift_mean"] * g["n"] for g in groups)
                     / completions),
            "denominator": completions},
        "routing_entropy_bits_mean": (
            sum(g["routing_entropy_bits"] for g in groups) / n_groups),
    }
    return out


def aggregate_stratified(groups: list[Mapping[str, Any]]
                         ) -> dict[str, Any]:
    """Aggregates per cell, per renderer, per payoff direction (tied
    rows a separate stratum, never direction-bearing), per
    cell×renderer×direction, and in total. Input: `group_stats`
    outputs."""
    if not groups:
        raise InfrastructureError("no groups to aggregate")
    strata: dict[str, dict[str, list]] = {
        "by_cell": {}, "by_renderer": {}, "by_direction": {},
        "by_cell_renderer_direction": {},
    }
    for g in groups:
        strata["by_cell"].setdefault(g["cell_id"], []).append(g)
        strata["by_renderer"].setdefault(g["renderer_id"], []).append(g)
        strata["by_direction"].setdefault(g["direction"], []).append(g)
        key = f"{g['cell_id']}|{g['renderer_id']}|{g['direction']}"
        strata["by_cell_renderer_direction"].setdefault(key, []).append(g)
    report: dict[str, Any] = {"total": _aggregate(list(groups))}
    for name, buckets in strata.items():
        report[name] = {key: _aggregate(members)
                        for key, members in sorted(buckets.items())}
    return report
