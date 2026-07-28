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
                loaded: Mapping[str, Any],
                c_fixed_record: Mapping[str, Any]) -> dict[str, Any]:
    """All per-group quantities for one completed group. Consumes the
    VERIFIED loaded-surface context (`load_dev_surface` result): the
    observation must be a member of the locked support, the comparator
    must rederive against that exact lock, and every reward is
    authenticated against the locked surface (216_s F3)."""
    from .dev_support import verify_c_fixed_for
    surface = loaded["surface"]
    membership = {obs["observation_id"]
                  for obs in loaded["observations"]}
    c_fixed_dev = verify_c_fixed_for(loaded, c_fixed_record)
    completions = group["completions"]
    if not completions:
        raise InfrastructureError("empty group")
    observation_id = group["observation_id"]
    if observation_id not in membership:
        raise InfrastructureError(
            f"{observation_id} is not an observation of the locked "
            "support — refusing to score a foreign group (216_s F3)")
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
        # 214_s/216_s reporting repairs: frequencies WITH denominators
        "worker_frequencies": {
            "counts": dict(sorted(worker_counts.items())),
            "denominator": sum(worker_counts.values())},
        "assignment_frequencies": {
            "counts": dict(sorted(assignment_counts.items())),
            "denominator": sum(assignment_counts.values())},
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


def _hierarchical_ratio(cells: Mapping[str, Mapping[str, Mapping[str,
                                                                 list]]],
                        numerator, denominator) -> dict[str, Any]:
    """Eligible-only hierarchical ratio (216_s F4): ratios per
    (latent, renderer) bucket with a nonzero denominator, renderer
    means within latent, latent means within cell, equal over the
    cells that HAVE eligible data — reported with the raw totals and
    the contributing cells."""
    total_num = 0.0
    total_den = 0
    cell_means = {}
    for cell, latents in cells.items():
        latent_means = []
        for renderers in latents.values():
            renderer_ratios = []
            for members in renderers.values():
                num = sum(numerator(g) for g in members)
                den = sum(denominator(g) for g in members)
                total_num += num
                total_den += den
                if den > 0:
                    renderer_ratios.append(num / den)
            if renderer_ratios:
                latent_means.append(sum(renderer_ratios)
                                    / len(renderer_ratios))
        if latent_means:
            cell_means[cell] = sum(latent_means) / len(latent_means)
    return {"value": (sum(cell_means.values()) / len(cell_means)
                      if cell_means else None),
            "numerator": total_num, "denominator": total_den,
            "cells": sorted(cell_means)}


def equal_cell_view(groups: list[Mapping[str, Any]]) -> dict[str, Any]:
    """The registered hierarchical weighting (130_s §6 / 214_s):
    average groups within (latent, renderer), renderers within latent,
    latents within cell, cells equally. 216_s F4: the population must
    BE the complete frozen crossing — all six cells and every latent's
    complete renderer set — and the eligible-only hierarchical
    ModelAcc and conditional-C2 views are reported with raw
    numerators/denominators."""
    from tasks.conductor.types import CELL_IDS, RENDERER_IDS
    cells: dict[str, dict[str, dict[str, list]]] = {}
    for g in groups:
        cells.setdefault(g["cell_id"], {}).setdefault(
            g["latent_program_id"], {}).setdefault(
            g["renderer_id"], []).append(g)
    if set(cells) != set(CELL_IDS):
        raise InfrastructureError(
            f"equal-cell view requires all six cells "
            f"{sorted(CELL_IDS)}; got {sorted(cells)} — a partial "
            "population is not the registered estimand (216_s F4)")
    for cell, latents in cells.items():
        for latent, renderers in latents.items():
            if set(renderers) != set(RENDERER_IDS):
                raise InfrastructureError(
                    f"{latent}: equal-cell view requires the complete "
                    f"renderer crossing {sorted(RENDERER_IDS)}; got "
                    f"{sorted(renderers)} (216_s F4)")
    out: dict[str, Any] = {}
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
    out["model_acc"] = _hierarchical_ratio(
        cells,
        lambda g: g["model_acc"][0] if g["model_acc"] else 0.0,
        lambda g: g["model_acc"][1] if g["model_acc"] else 0)
    out["c2_optimal_specialist"] = _hierarchical_ratio(
        cells,
        lambda g: g["c2_optimal"] if g["c2_optimal"] is not None else 0,
        lambda g: g["c2_eligible"] if g["c2_optimal"] is not None
        else 0)
    out["cells"] = sorted(cells)
    return out


def probe_report(groups: list[Mapping[str, Any]], *,
                 loaded: Mapping[str, Any],
                 bound_cohort: Mapping[str, Any],
                 frozen_rule: Mapping[str, Any]) -> dict[str, Any]:
    """THE report boundary (218_s F3): consumes the frozen bound
    cohort and rule and requires the groups to BE the frozen design —
    exact observation ids, exact multiplicity (groups per
    observation), and exact group size. An extra, missing, foreign or
    wrong-sized group refuses; only then does aggregation (incl. the
    equal-cell estimand) run."""
    from collections import Counter as _Counter

    from .charter import content_sha256
    from .cohorts import apply_probe_rule, validate_probe_rule
    rule = validate_probe_rule(frozen_rule)
    if not isinstance(bound_cohort, Mapping) \
            or bound_cohort.get("kind") != "routing-dev-probe-cohort-v1":
        raise InfrastructureError("not a probe-cohort binding record")
    body = {k: v for k, v in bound_cohort.items()
            if k != "cohort_sha256"}
    if content_sha256(body) != bound_cohort.get("cohort_sha256"):
        raise InfrastructureError(
            "probe-cohort binding record does not rehash")
    if bound_cohort["rule_sha256"] != frozen_rule["rule_sha256"]:
        raise InfrastructureError(
            "bound cohort was built from a different frozen rule")
    lock = loaded.get("lock")
    if not isinstance(lock, Mapping) \
            or bound_cohort["surface_lock_sha256"] != \
            lock.get("lock_sha256"):
        raise InfrastructureError(
            "bound cohort is not bound to this loaded surface's lock")
    # 220_s F3: the rule must be the one the surface was LAUNCHED
    # under, and the ordered observation ids are REDERIVED from the
    # rule + loaded declaration — a self-rehashed cohort record is
    # never trusted for the selection itself.
    if frozen_rule["rule_sha256"] != lock.get("probe_rule_sha256"):
        raise InfrastructureError(
            "this surface was launched under a different probe rule "
            "(220_s F3)")
    rederived = apply_probe_rule(frozen_rule, loaded["declaration"])
    if list(bound_cohort["observation_ids"]) != rederived:
        raise InfrastructureError(
            "bound cohort observation ids do not rederive from the "
            "launched rule and declaration (220_s F3)")
    expected = list(bound_cohort["observation_ids"])
    per_observation = rule["groups_per_observation"]
    counts = _Counter(g["observation_id"] for g in groups)
    if set(counts) - set(expected):
        raise InfrastructureError(
            f"report contains groups for observations outside the "
            f"bound cohort: {sorted(set(counts) - set(expected))[:3]}")
    wrong = {oid: counts.get(oid, 0) for oid in expected
             if counts.get(oid, 0) != per_observation}
    if wrong:
        raise InfrastructureError(
            f"group multiplicities do not match the frozen "
            f"{per_observation}/observation: "
            f"{dict(list(wrong.items())[:3])} (218_s F3)")
    bad_sizes = {g["observation_id"]: g["n"] for g in groups
                 if g["n"] != rule["group_size"]}
    if bad_sizes:
        raise InfrastructureError(
            f"group sizes differ from the frozen G="
            f"{rule['group_size']}: {dict(list(bad_sizes.items())[:3])}")
    report = aggregate_stratified(groups)
    report["design"] = {
        "rule_sha256": frozen_rule["rule_sha256"],
        "cohort_sha256": bound_cohort["cohort_sha256"],
        "surface_lock_sha256": lock["lock_sha256"],
        "observations": len(expected),
        "groups_per_observation": per_observation,
        "group_size": rule["group_size"],
    }
    return report


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
