"""P0 spine, Unit 3 — the versioned, typed estimand rules (303_f §9
step 3; 305_f §3).

Every scientific quantity of P0 — and of the C2 replay equivalence
oracle — is computed by THESE functions, driven by the typed rule
objects of the frozen P0ScienceContract, never by the legacy report
builder. Ground-truth primitives are shared with the legacy path by
design (the frozen parser, the node/worker family tables, the
authenticated surface, the pair structure); the ESTIMAND layer —
the Q1 counted event, the four separated Q2 quantities, the
sentinel contract, the gates, sizing and the decision — lives here.

The four Q2 quantities (305_f §3), kept structurally distinct:

1. marginal target selection / cold-start authorization
   (`marginal_target_selection`, `evaluate_q2_cold_start_gate`) —
   counted over VALID completions regardless of upstream
   correctness; a marginal selection is NOT conditional support;
2. eligibility (`c2_eligible_completion`) — the c2-eligibility-v1
   rule (family-correct non-Code routing, Code choice within the
   specialist pool, malformed excluded);
3. conditional optimal-per-eligible (`conditional_choice`) — the P0
   learning estimand; a ZERO denominator is UNDEFINED (None), never
   0.0;
4. contrasts (`group_contrasts`) — direct (both family-correct
   variants drawn in one group) and semantic (reward levels 1 and
   0.5 co-present); a semantic contrast is NOT a Q1 counted event.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from tasks.conductor.stage1 import NODE_FAMILIES, WORKER_FAMILIES
from tasks.conductor.types import InfrastructureError

from .p0_schema import (
    ActiveScope,
    EligibilityRule,
    Q1CountedEvent,
    Q1Rule,
    Q2Rule,
    SizingRule,
)

ESTIMANDS_VERSION = "p0-estimands-v1"

REWARD_LADDER = (0.0, 0.5, 1.0)


def reward_level(value: float) -> float:
    """The frozen three-level ladder; anything else refuses."""
    if value not in REWARD_LADDER:
        raise InfrastructureError(
            f"reward {value!r} outside the frozen ladder "
            f"{REWARD_LADDER}")
    return float(value)


def family_correct_fraction(cell: str,
                            assignment: Sequence[int]) -> float:
    families = NODE_FAMILIES[cell]
    nodes = sorted(families)
    if len(assignment) != len(nodes):
        raise InfrastructureError(
            f"{cell}: assignment {assignment!r} has "
            f"{len(assignment)} workers; the cell has {len(nodes)} "
            "nodes")
    correct = sum(1 for node, worker in zip(nodes, assignment)
                  if WORKER_FAMILIES.get(worker) == families[node])
    return correct / len(nodes)


def code_node_index(cell: str) -> int | None:
    families = NODE_FAMILIES[cell]
    nodes = sorted(families)
    for i, node in enumerate(nodes):
        if families[node] == "code":
            return i
    return None


# --- Q1: the counted event -----------------------------------------------------

def q1_counted_event(event: Q1CountedEvent, cell: str,
                     rewards: Sequence[float],
                     assignments: Sequence[Sequence[int] | None]
                     ) -> bool:
    """The q1-counted-v1 event: a high-reward FULLY family-correct
    completion AND a low-reward completion of STRICTLY LOWER family
    correctness, valid completions only, within the SAME group. The
    rule's closed literals are operative — an unknown rule refuses
    rather than silently computing something else."""
    if event.rule_id != "q1-counted-v1" \
            or not event.valid_completions_only \
            or not event.same_group \
            or event.high_family_correctness != "full" \
            or event.low_family_correctness != "strictly_lower":
        raise InfrastructureError(
            f"unknown Q1 counted-event rule {event!r}")
    if len(rewards) != len(assignments):
        raise InfrastructureError(
            "rewards and assignments are not parallel")
    has_high = any(
        r == event.high_reward and a is not None
        and family_correct_fraction(cell, a) == 1.0
        for r, a in zip(rewards, assignments))
    has_low = any(
        r == event.low_reward and a is not None
        and family_correct_fraction(cell, a) < 1.0
        for r, a in zip(rewards, assignments))
    return has_high and has_low


def evaluate_q1_gate(q1: Q1Rule, cells: Sequence[str],
                     per_cell: Mapping[str, Mapping[str, Any]]
                     ) -> tuple[dict[str, Any], bool]:
    """The direct-Q1 gate over the measured per-cell state
    ({counted_groups, latents, renderers, bridge_draws})."""
    gate: dict[str, Any] = {}
    overall = True
    for cell in cells:
        entry = per_cell[cell]
        cell_pass = (
            entry["counted_groups"] >= q1.min_counted_groups_per_cell
            and len(entry["latents"])
            >= q1.min_distinct_latents_among_counted)
        overall = overall and cell_pass
        gate[cell] = {
            "bridge_draws": entry["bridge_draws"],
            "counted_groups": entry["counted_groups"],
            "distinct_latents": sorted(entry["latents"]),
            "renderers_observed": sorted(entry["renderers"]),
            "pass": cell_pass,
        }
    return gate, overall


# --- Q2: the four separated quantities -----------------------------------------

def c2_eligible_completion(rule: EligibilityRule, cell: str,
                           assignment: Sequence[int] | None) -> bool:
    """Quantity 2 — eligibility: every non-Code node routed
    family-correct AND every Code choice within the specialist pool;
    malformed completions are EXCLUDED (False), never dropped from
    the group."""
    if rule.rule_id != "c2-eligibility-v1" \
            or rule.non_code_routing != "family_correct" \
            or rule.malformed_completions != "excluded":
        raise InfrastructureError(
            f"unknown eligibility rule {rule!r}")
    if assignment is None:
        return False
    families = NODE_FAMILIES[cell]
    nodes = sorted(families)
    non_code_ok = all(
        WORKER_FAMILIES.get(w) == families[node]
        for node, w in zip(nodes, assignment)
        if families[node] != "code")
    code_choices = [w for node, w in zip(nodes, assignment)
                    if families[node] == "code"]
    return (bool(code_choices)
            and all(w in rule.code_worker_in for w in code_choices)
            and non_code_ok)


def c2_optimal_completion(rule: EligibilityRule, cell: str,
                          assignment: Sequence[int] | None,
                          pair_entry: Mapping[str, Any] | None
                          ) -> bool:
    """Optimality is defined WITHIN eligibility: an eligible
    completion whose assignment is the favoured family-correct
    variant of a distinct-payoff pair."""
    if not c2_eligible_completion(rule, cell, assignment):
        return False
    if pair_entry is None or pair_entry["direction"] is None:
        return False
    favoured = pair_entry[f"assignment_w{pair_entry['direction']}"]
    return list(assignment) == list(favoured)


def marginal_target_selection(cell: str,
                              assignment: Sequence[int] | None,
                              target_worker: int) -> bool:
    """Quantity 1 — the marginal selection event of the cold-start
    gate: the Code slot carries the target worker, counted over
    VALID completions regardless of upstream correctness (the
    contract's marginal gate structurally cannot become
    conditional)."""
    if assignment is None:
        return False
    index = code_node_index(cell)
    if index is None:
        return False
    return assignment[index] == target_worker


def conditional_choice(numerator: int,
                       denominator: int) -> float | None:
    """Quantity 3 — the conditional optimal-per-eligible estimand.
    A zero denominator is UNDEFINED (None), never 0.0 (305_f §3)."""
    if numerator < 0 or denominator < 0 \
            or numerator > denominator:
        raise InfrastructureError(
            f"conditional {numerator}/{denominator} is not a valid "
            "count pair")
    if denominator == 0:
        return None
    return numerator / denominator


def group_contrasts(rewards: Sequence[float],
                    assignments: Sequence[Sequence[int] | None],
                    pair_entry: Mapping[str, Any] | None
                    ) -> dict[str, bool]:
    """Quantity 4 — the contrasts. Semantic: reward levels 1 and 0.5
    co-present in the group (NOT the Q1 counted event — no
    family-correctness condition). Direct: both family-correct
    variants of the pair drawn in one group."""
    for value in rewards:
        reward_level(value)
    semantic = any(r == 0.5 for r in rewards) \
        and any(r == 1.0 for r in rewards)
    direct = False
    if pair_entry is not None:
        w2 = list(pair_entry["assignment_w2"])
        w3 = list(pair_entry["assignment_w3"])
        hits_w2 = sum(1 for a in assignments
                      if a is not None and list(a) == w2)
        hits_w3 = sum(1 for a in assignments
                      if a is not None and list(a) == w3)
        direct = hits_w2 > 0 and hits_w3 > 0
    return {"semantic_contrast": semantic,
            "direct_contrast": direct}


def evaluate_q2_cold_start_gate(q2: Q2Rule,
                                state: Mapping[str,
                                               Mapping[str, Any]]
                                ) -> dict[str, Any]:
    """The marginal cold-start gate over the measured per-direction
    state ({selections, latents})."""
    detail: dict[str, Any] = {}
    overall = True
    for direction, worker in q2.per_direction_targets:
        entry = state[direction]
        direction_pass = (
            entry["selections"] >= q2.marginal_min_target_selections
            and len(entry["latents"])
            >= q2.marginal_min_distinct_latents)
        overall = overall and direction_pass
        detail[direction] = {
            "target_worker": worker,
            "target_selections": entry["selections"],
            "distinct_latents": sorted(entry["latents"]),
            "pass": direction_pass,
        }
    return {
        "min_target_selections": q2.marginal_min_target_selections,
        "min_distinct_latents": q2.marginal_min_distinct_latents,
        "per_direction": detail,
        "pass": overall,
    }


# --- sizing + decision ---------------------------------------------------------

def derive_sizing(sizing: SizingRule, cells: Sequence[str],
                  counted_by_cell: Mapping[str, int], epochs: int,
                  cap_formula: Mapping[str, Any]
                  ) -> dict[str, Any]:
    """The mechanical integer sizing derivation over the sizing
    cells (sentinel excluded by construction — it is not in
    `cells`). The cap-formula prose is frozen config data passed in
    by the caller (a config echo, not a derived result)."""
    counts = {cell: counted_by_cell[cell] for cell in cells}
    minimum = min(counts.values())
    if minimum <= 0:
        return {"derivable": False,
                "sizing_cells": dict(counts),
                "reason": "a sizing cell has zero counted groups — "
                          "the direct-Q1 gate has already stopped "
                          "the run"}
    target = sizing.target_q1_counted_groups_per_sizing_cell
    derived_epochs = -(-(target * epochs) // minimum)
    return {
        "derivable": True,
        "sizing_cells": dict(counts),
        "min_counted_groups": minimum,
        "min_cell": min(cells, key=lambda c: counts[c]),
        "derived_epochs": derived_epochs,
        "derived_groups": derived_epochs * sizing.groups_per_epoch,
        "operational_ceiling_hours":
            sizing.operational_ceiling_hours,
        "cap_formula": dict(cap_formula),
    }


_DECISION_BRANCHES = frozenset({
    "q1_fail", "q1_pass_q2_pass", "q1_pass_q2_fail",
    "infrastructure_abort"})


def decide_outcome(matrix: Mapping[str, str], *, q1_pass: bool,
                   q2_pass: bool,
                   infrastructure_abort: bool = False) -> str:
    """The pure four-branch decision over the frozen matrix (the
    matrix strings are config data supplied by the caller)."""
    if set(matrix) != _DECISION_BRANCHES:
        raise InfrastructureError(
            f"decision matrix branches {sorted(matrix)} != the "
            f"frozen four")
    if infrastructure_abort:
        return matrix["infrastructure_abort"]
    if not q1_pass:
        return matrix["q1_fail"]
    if q2_pass:
        return matrix["q1_pass_q2_pass"]
    return matrix["q1_pass_q2_fail"]


# --- the sentinel contract (305_f §4) ------------------------------------------

def sentinel_checkpoint_block(scope: ActiveScope,
                              event: Q1CountedEvent,
                              trace_rows: Sequence[Mapping[str, Any]],
                              updates_per_group: int = 1
                              ) -> dict[str, Any]:
    """The complete per-checkpoint sentinel block: counts, BOTH raw
    denominators (groups AND completions), and both first-index
    families. Worker-1 events are the estimand — a [2]/[3]
    selection is different routing but is NOT Math unlocking. The
    population is BOUND to the contract's frozen sentinel ids; the
    trajectories of the contract's diagnostics spec are assembled by
    the consumer across checkpoints from these blocks."""
    ids = set(scope.sentinel_observation_ids)
    if not ids:
        raise InfrastructureError("empty sentinel population")
    for oid in ids:
        if not oid.startswith(scope.sentinel_cell + ":"):
            raise InfrastructureError(
                f"{oid}: sentinel id outside the contract's "
                f"sentinel cell {scope.sentinel_cell}")
    if not isinstance(updates_per_group, int) \
            or isinstance(updates_per_group, bool) \
            or updates_per_group <= 0:
        raise InfrastructureError(
            "updates_per_group must be a positive non-boolean "
            "integer")
    cell = scope.sentinel_cell
    firsts_group = {"worker1": None, "reward1": None,
                    "varying": None, "q1_counted": None}
    firsts_update = dict(firsts_group)
    block: dict[str, Any] = {
        "cell": cell,
        "training_exposed": scope.sentinel_training_exposed,
        "observation_ids": sorted(ids),
        "group_denominator": 0,
        "completion_denominator": 0,
        "worker1_selections": 0,
        "worker1_completions": 0,
        "reward1_completions": 0,
        "reward_varying_groups": 0,
        "q1_counted_groups": 0,
    }

    def _mark(family: str, index: int) -> None:
        if firsts_group[family] is None:
            firsts_group[family] = index
            firsts_update[family] = index * updates_per_group

    for row in trace_rows:
        oid = row["observation_id"]
        if oid not in ids:
            continue
        index = row["global_group_index"]
        rewards = list(row["rewards"])
        assignments = list(row["assignments"])
        block["group_denominator"] += 1
        block["completion_denominator"] += len(rewards)
        if len(set(rewards)) > 1:
            block["reward_varying_groups"] += 1
            _mark("varying", index)
        for reward, assignment in zip(rewards, assignments):
            if assignment is None:
                continue
            if 1 in assignment:
                block["worker1_selections"] += 1
                block["worker1_completions"] += 1
                _mark("worker1", index)
            if reward == 1.0:
                block["reward1_completions"] += 1
                _mark("reward1", index)
        if q1_counted_event(event, cell, rewards, assignments):
            block["q1_counted_groups"] += 1
            _mark("q1_counted", index)
    block["first_group_indices"] = firsts_group
    block["first_update_indices"] = firsts_update
    return block


def sentinel_legacy_view(block: Mapping[str, Any]) -> dict[str, Any]:
    """The exact field shape of the legacy C2 sentinel block, for
    the replay equivalence comparison against the frozen
    projection."""
    view = {
        "cell": block["cell"],
        "training_exposed": block["training_exposed"],
        "observation_ids": list(block["observation_ids"]),
        "groups": block["group_denominator"],
        "worker1_selections": block["worker1_selections"],
        "worker1_completions": block["worker1_completions"],
        "reward1_completions": block["reward1_completions"],
        "reward_varying_groups": block["reward_varying_groups"],
        "q1_counted_groups": block["q1_counted_groups"],
    }
    for family in ("worker1", "reward1", "varying", "q1_counted"):
        view[f"first_{family}_group_index"] = \
            block["first_group_indices"][family]
        view[f"first_{family}_update_index"] = \
            block["first_update_indices"][family]
    return view
