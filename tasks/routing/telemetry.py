"""Stratified group telemetry (211_f §7; 214_s P1: authenticate,
don't trust).

Input unit: one COMPLETED GROUP — the G completions sampled for one
observation — as
    {"observation_id", "completions": [
        {"parseable": bool, "valid": bool,
         "assignment": [semantic worker ids] | None,
         "reward": float}, ...]}

This boundary AUTHENTICATES its scientific inputs against the
lock-validated surface instead of trusting the caller:

- observation identity (cell, renderer, latent) is parsed from the
  observation id itself, never taken from caller metadata;
- a valid completion's reward MUST equal the authenticated surface
  payoff of its assignment; an invalid completion's reward MUST be 0;
- assignments are schema-checked (exact arity, workers in 0–3);
- the w2/w3 pair, its payoffs and its direction are DERIVED from the
  surface via the frozen `family_correct_variants`, never supplied;
- the comparator arrives as a rehashing `c_fixed_dev-v1` record.

The three contrast notions stay separate (211_f §5): FORMAT, SEMANTIC
(valid 0.5 vs 1), and the exact w2/w3 DIRECT contrast. C1 is
node-level family-correct routing; `ModelAcc` is the broader
full-denominator model-selection view (130_s §6.5: malformed and
wrong-family Code choices score 0 and stay in the denominator); C2 is
the conditional optimal-specialist view (non-Code nodes
family-correct AND Code ∈ {2,3}; tied observations reported, never
scored). ScaleLift collapses selected worker-2/3 Code positions to
`c_fixed_dev` (130_s §6.4; malformed contributes 0 to both members).
Every aggregate rate is `{count, denominator, rate}`, and the
hierarchical equal-cell view (renderer-within-latent,
latent-within-cell, equal cells) is reported alongside the pooled
strata (214_s reporting repairs).
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping

from tasks.conductor.stage1 import NODE_FAMILIES, WORKER_FAMILIES
from tasks.conductor.stage1_replay import family_correct_variants
from tasks.conductor.types import InfrastructureError, \
    parse_render_instance_id

from .dev_support import validate_c_fixed_record

REWARD_LEVELS = ("0", "0.5", "1")


def _reward_level(value: float) -> str:
    for level in REWARD_LEVELS:
        if value == float(level):
            return level
    raise InfrastructureError(
        f"reward {value!r} outside the frozen ladder {REWARD_LEVELS}")


def derive_pair_entry(observation_id: str, cell_id: str,
                      surface: Mapping[tuple[str, tuple[int, ...]],
                                       float]
                      ) -> dict[str, Any] | None:
    """The observation's family-correct w2/w3 variant pair, its
    payoffs and direction — derived from the authenticated surface,
    never caller-supplied (214_s P1). None for Code-free cells."""
    variants = family_correct_variants(cell_id)
    if variants is None:
        return None
    w2, w3 = variants
    payoffs = {}
    for label, assignment in (("w2", tuple(w2)), ("w3", tuple(w3))):
        key = (observation_id, assignment)
        if key not in surface:
            raise InfrastructureError(
                f"{key!r}: family-correct variant row missing from the "
                "surface")
        payoffs[label] = surface[key]
    direction = None
    if payoffs["w2"] != payoffs["w3"]:
        direction = 2 if payoffs["w2"] > payoffs["w3"] else 3
    return {"assignment_w2": list(w2), "assignment_w3": list(w3),
            "payoff_w2": payoffs["w2"], "payoff_w3": payoffs["w3"],
            "distinct_payoff": payoffs["w2"] != payoffs["w3"],
            "direction": direction}


def _validate_assignment(cell_id: str, assignment: Any) -> tuple[int, ...]:
    nodes = sorted(NODE_FAMILIES[cell_id])
    if not isinstance(assignment, (list, tuple)) \
            or len(assignment) != len(nodes) \
            or any(not isinstance(w, int) or isinstance(w, bool)
                   or not 0 <= w <= 3 for w in assignment):
        raise InfrastructureError(
            f"{cell_id}: assignment {assignment!r} violates the action "
            f"schema ({len(nodes)} workers in 0-3)")
    return tuple(assignment)


def _family_correct_fraction(cell_id: str,
                             assignment: tuple[int, ...]) -> float:
    families = NODE_FAMILIES[cell_id]
    nodes = sorted(families)
    correct = sum(
        1 for node, worker in zip(nodes, assignment)
        if WORKER_FAMILIES.get(worker) == families[node])
    return correct / len(nodes)


def _collapse_code(cell_id: str, assignment: tuple[int, ...],
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
                surface: Mapping[tuple[str, tuple[int, ...]], float],
                c_fixed_record: Mapping[str, Any]) -> dict[str, Any]:
    """All per-group quantities for one completed group, authenticated
    against the lock-validated surface."""
    c_fixed_dev = validate_c_fixed_record(c_fixed_record)
    completions = group["completions"]
    if not completions:
        raise InfrastructureError("empty group")
    observation_id = group["observation_id"]
    render_id = parse_render_instance_id(observation_id)
    cell = render_id.latent.cell_id
    renderer = render_id.renderer_id
    latent_program_id = render_id.latent_program_id
    pair_entry = derive_pair_entry(observation_id, cell, surface)
    direction = None
    if pair_entry is not None and pair_entry["distinct_payoff"]:
        direction = pair_entry["direction"]

    n = len(completions)
    parseable = valid = 0
    rewards: list[float] = []
    levels: Counter = Counter()
    assignments: Counter = Counter()
    worker_counts: Counter = Counter()
    c1_values: list[float] = []
    model_acc_values: list[float] = []   # distinct-pair obs only
    c2_eligible = 0
    c2_optimal = 0
    scale_lift_terms: list[float] = []
    for completion in completions:
        reward = float(completion["reward"])
        level = _reward_level(reward)
        rewards.append(reward)
        levels[level] += 1
        if completion.get("valid") and not completion.get("parseable"):
            raise InfrastructureError(
                "a valid completion that is not parseable is a "
                "contradiction")
        if completion.get("parseable"):
            parseable += 1
        if not completion.get("valid"):
            if reward != 0.0:
                raise InfrastructureError(
                    f"invalid completion carries reward {reward!r}; the "
                    "frozen ladder scores malformed actions 0 "
                    "(214_s P1)")
            # 130_s §6.5: malformed scores 0 in C1/ModelAcc and
            # contributes 0 to both ScaleLift members — never dropped.
            c1_values.append(0.0)
            if direction is not None:
                model_acc_values.append(0.0)
            scale_lift_terms.append(0.0)
            continue
        valid += 1
        assignment = _validate_assignment(cell,
                                          completion["assignment"])
        authenticated = surface.get((observation_id, assignment))
        if authenticated is None:
            raise InfrastructureError(
                f"({observation_id}, {assignment}): no authenticated "
                "surface row — the surface must cover the full 4^S "
                "space")
        if reward != authenticated:
            raise InfrastructureError(
                f"({observation_id}, {assignment}): reported reward "
                f"{reward!r} != authenticated payoff {authenticated!r} "
                "(214_s P1)")
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
            code_in_pool = bool(code_choices) and all(
                w in (2, 3) for w in code_choices)
            if direction is not None:
                # broader ModelAcc (130_s §6.5): the mean over eligible
                # Code SLOTS of 1[choice == target]; malformed scored 0
                # above; a wrong-family or wrong-specialist Code choice
                # scores 0 and stays in the denominator
                slot_scores = [
                    1.0 if w == direction else 0.0
                    for node, w in zip(nodes, assignment)
                    if families[node] == "code"]
                model_acc_values.append(
                    sum(slot_scores) / len(slot_scores))
            if non_code_ok and code_in_pool:
                c2_eligible += 1
                if direction is not None and assignment == tuple(
                        pair_entry[f"assignment_w{direction}"]):
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
        "renderer_id": renderer,
        "latent_program_id": latent_program_id,
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
        "model_acc": ((sum(model_acc_values), len(model_acc_values))
                      if direction is not None else None),
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

def _rate(count: int | float, denominator: int) -> dict[str, Any]:
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
    model_num = sum(g["model_acc"][0] for g in groups
                    if g["model_acc"] is not None)
    model_den = sum(g["model_acc"][1] for g in groups
                    if g["model_acc"] is not None)
    worker_counts: Counter = Counter()
    assignment_counts: Counter = Counter()
    for g in groups:
        for worker, count in g["worker_counts"].items():
            worker_counts[worker] += count
        for assignment, count in g["assignment_counts"].items():
            assignment_counts[assignment] += count
    concentrations = [g["max_assignment_concentration"] for g in groups
                      if g["max_assignment_concentration"] is not None]
    return {
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
        "c1_family_correct": _rate(
            sum(g["c1_mean"] * g["n"] for g in groups), completions),
        "model_acc": _rate(model_num, model_den),
        "c2_optimal_specialist": _rate(c2_num, c2_den),
        "c2_eligible_completions": _rate(
            sum(g["c2_eligible"] for g in groups), completions),
        "scale_lift": {
            "mean": (sum(g["scale_lift_mean"] * g["n"] for g in groups)
                     / completions),
            "denominator": completions},
        "routing_entropy_bits_mean": (
            sum(g["routing_entropy_bits"] for g in groups) / n_groups),
        # 214_s reporting repairs: raw frequencies + concentration
        "worker_frequencies": dict(sorted(worker_counts.items())),
        "assignment_frequencies": dict(sorted(
            assignment_counts.items())),
        "repeated_output_concentration_mean": (
            sum(concentrations) / len(concentrations)
            if concentrations else None),
    }


_EQUAL_CELL_METRICS = {
    "parse_rate": lambda g: g["parseable"] / g["n"],
    "valid_rate": lambda g: g["valid"] / g["n"],
    "mean_reward": lambda g: g["mean_reward"],
    "zero_variance_rate":
        lambda g: 1.0 if g["zero_variance_level"] is not None else 0.0,
    "format_contrast_rate": lambda g: 1.0 if g["format_contrast"]
        else 0.0,
    "semantic_contrast_rate": lambda g: 1.0 if g["semantic_contrast"]
        else 0.0,
    "direct_contrast_rate": lambda g: 1.0 if g["direct_contrast"]
        else 0.0,
    "c1_family_correct": lambda g: g["c1_mean"],
    "scale_lift": lambda g: g["scale_lift_mean"],
}


def equal_cell_view(groups: list[Mapping[str, Any]]) -> dict[str, Any]:
    """The registered hierarchical weighting (130_s §6 / 214_s):
    average groups within (latent, renderer), renderers within latent,
    latents within cell, cells equally."""
    cells: dict[str, dict[str, dict[str, list]]] = {}
    for g in groups:
        cells.setdefault(g["cell_id"], {}).setdefault(
            g["latent_program_id"], {}).setdefault(
            g["renderer_id"], []).append(g)
    out = {}
    for name, metric in _EQUAL_CELL_METRICS.items():
        cell_means = []
        for latents in cells.values():
            latent_means = []
            for renderers in latents.values():
                renderer_means = [
                    sum(metric(g) for g in members) / len(members)
                    for members in renderers.values()]
                latent_means.append(
                    sum(renderer_means) / len(renderer_means))
            cell_means.append(sum(latent_means) / len(latent_means))
        out[name] = sum(cell_means) / len(cell_means)
    out["cells"] = sorted(cells)
    return out


def aggregate_stratified(groups: list[Mapping[str, Any]]
                         ) -> dict[str, Any]:
    """Aggregates per cell, per renderer, per payoff direction (tied
    rows a separate stratum, never direction-bearing), per
    cell×renderer×direction, in total, and under the hierarchical
    equal-cell weighting. Input: `group_stats` outputs."""
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
    report: dict[str, Any] = {"total": _aggregate(list(groups)),
                              "equal_cell": equal_cell_view(
                                  list(groups))}
    for name, buckets in strata.items():
        report[name] = {key: _aggregate(members)
                        for key, members in sorted(buckets.items())}
    return report
