"""P0 spine, Unit 3 — the exact C2 replay equivalence oracle
(303_f §3/§9 step 3; 305_f §2).

`derive_c2_projection` rederives the canonical scientific
projection of the authorized C2 run from the RAW authenticated
trace: every completion text is re-parsed with the frozen parser,
its semantic assignment re-derived through the frozen positional
mapping, its reward re-derived from the locked surface, and every
estimand computed by the TYPED rules of `p0_estimands` under the
frozen P0ScienceContract.

Independence (305_f §2): the evaluator NEVER calls the legacy
`unit_c2_sample.build_exposure_report` and never reads the values
of the source `exposure_report.json` (its bytes are only hashed by
the Unit-1 authentication) nor the frozen expected projection —
`load_projection` is consumed only by the COMPARATOR,
`verify_c2_equivalence`. `derive_from_trace` is the PURE layer: it
performs no file access at all.

Disclosed config echoes: the cap-formula prose and the
decision-matrix strings enter the derived projection from the
hash-guarded `MIXTURE_V2_CONFIG` constant — they are frozen config
DATA reproduced verbatim, not measured results; every numerical
field is generated from the trace."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from tasks.conductor.types import InfrastructureError

from . import p0_estimands as est
from .charter import content_sha256
from .p0_contract import load_p0_science_contract
from .p0_replay import (
    C2_EVIDENCE_DIR,
    PROJECTION_SHA256,
    REPLAY_SOURCE,
    load_pinned_mixture,
    load_projection,
    restore_extension_surface_if_absent,
    verify_c2_replay_source,
)
from .p0_schema import P0ScienceContract


def _guarded_config_echoes() -> tuple[dict[str, Any],
                                      dict[str, str]]:
    """The two disclosed config echoes, taken only from the
    hash-guarded frozen constant."""
    from .p0_mixture_v2 import CONFIG_V2_SHA256, MIXTURE_V2_CONFIG
    if content_sha256(MIXTURE_V2_CONFIG) != CONFIG_V2_SHA256:
        raise InfrastructureError(
            "MIXTURE_V2_CONFIG was mutated after import — the "
            "config echoes are not trustworthy")
    return (dict(MIXTURE_V2_CONFIG["p0_sizing_rule"]["cap_formula"]),
            dict(MIXTURE_V2_CONFIG["outcome_contract"]
                 ["decision_matrix"]))


def derive_c2_projection(evidence_dir: str | Path | None = None
                         ) -> dict[str, Any]:
    """Authenticate the complete replay source (Unit 1), load every
    input through its reviewed pin, then hand the RAW trace to the
    pure derivation layer."""
    from .p0_mixture_v2 import load_frozen_selection_v2
    from .dev_support import load_dev_surface
    from .resume_validation import read_trace
    evidence = Path(evidence_dir or C2_EVIDENCE_DIR)
    verify_c2_replay_source(evidence_dir=evidence)
    contract = load_p0_science_contract()
    mixture = load_pinned_mixture(
        expected_file_sha256=contract.input_pins
        .pinned_mixture_file_sha256)
    if mixture["record_sha256"] != \
            contract.input_pins.pinned_mixture_record_sha256:
        raise InfrastructureError(
            "the pinned-mixture artifact does not match the "
            "contract's record pin")
    surface_dir = restore_extension_surface_if_absent()
    loaded = load_dev_surface(
        surface_dir,
        expected_lock_sha256=contract.input_pins
        .extension_surface_lock_sha256)
    selection = load_frozen_selection_v2()
    if selection["record_sha256"] != \
            contract.input_pins.selection_record_sha256:
        raise InfrastructureError(
            "the frozen selection is not the contract's pinned "
            "record")
    trace_rows = read_trace(evidence / "actions.jsonl")
    return derive_from_trace(
        trace_rows, contract=contract, mixture=mixture,
        loaded=loaded,
        disclosure=selection["public_factor_disclosure"])


def derive_from_trace(trace_rows: Sequence[Mapping[str, Any]], *,
                      contract: P0ScienceContract,
                      mixture: Mapping[str, Any],
                      loaded: Mapping[str, Any],
                      disclosure: Mapping[str, Mapping[str, Any]]
                      ) -> dict[str, Any]:
    """The PURE derivation layer: raw trace rows + authenticated
    inputs -> the canonical projection. No file access. Stored
    action/assignment/reward fields are cross-checked against the
    re-derivation and refuse on ANY disagreement — a corrupted
    redundant field is detected as corruption, never scored as an
    alternative result."""
    from tasks.conductor import program
    from tasks.conductor.grpo_task import positional_to_semantic
    from tasks.conductor.parser import (
        ActionSchemaError,
        parse_routing_action,
    )
    from tasks.conductor.profiles import DEFAULT_PROFILE
    from tasks.conductor.stage1 import NODE_FAMILIES
    from .telemetry import derive_pair_entry

    cap_formula, decision_matrix = _guarded_config_echoes()
    surface = loaded["surface"]
    membership = {obs["observation_id"]
                  for obs in loaded["observations"]}
    cells = contract.scope.q1_direct_cells
    event = contract.q1.event
    eligibility = contract.q2.eligibility
    groups_per_epoch = contract.sizing.groups_per_epoch

    # the schedule identity: the trace must be the pinned epoch,
    # verbatim, an exact whole number of times (row reorder or row
    # substitution refuses here)
    epoch_rows = list(mixture["schedule_rows"])
    if len(epoch_rows) != groups_per_epoch:
        raise InfrastructureError(
            f"the pinned epoch has {len(epoch_rows)} rows; the "
            f"contract requires {groups_per_epoch}")
    n = len(trace_rows)
    if n == 0 or n % groups_per_epoch != 0:
        raise InfrastructureError(
            f"{n} trace rows is not a whole number of "
            f"{groups_per_epoch}-row epochs")
    epochs = n // groups_per_epoch
    schedule_rows = epoch_rows * epochs
    if [row["observation_id"] for row in trace_rows] \
            != schedule_rows:
        raise InfrastructureError(
            "trace rows do not follow the pinned schedule — the "
            "replay refuses (reorder/substitution)")

    sentinel_ids = sorted(contract.scope.sentinel_observation_ids)
    population_by_observation = {
        oid: ("sentinel" if oid in set(sentinel_ids) else cls)
        for oid, cls in mixture["class_assignment"].items()}

    per_population: dict[str, int] = {}
    q1_by_cell = {cell: {"counted_groups": 0, "latents": set(),
                         "renderers": set(), "bridge_draws": 0}
                  for cell in cells}
    q2_blocks: dict[str, dict[str, Any]] = {}
    for direction, _worker in contract.q2.per_direction_targets:
        q2_blocks[direction] = {
            "draws": 0, "latents": set(), "valid_completions": 0,
            "c2_eligible_completions": 0,
            "c2_optimal_completions": 0,
            "model_acc_numerator": 0.0, "model_acc_denominator": 0,
            "code_worker_selections": {"2": 0, "3": 0, "other": 0},
            "reward_sum": 0.0, "direct_contrast_groups": 0,
            "semantic_contrast_groups": 0,
        }
    q2_gate_state = {direction: {"selections": 0, "latents": set()}
                     for direction, _ in
                     contract.q2.per_direction_targets}
    control_block = {"draws": 0, "c2_eligible_completions": 0,
                     "reward_sum": 0.0}
    strata: dict[str, dict[str, Any]] = {}
    zero_variance = 0
    valid_total = 0
    completion_total = 0
    group_size: int | None = None
    positions_cache: dict[str, list[str]] = {}
    pair_cache: dict[str, dict[str, Any] | None] = {}

    for row in trace_rows:
        oid = row["observation_id"]
        if oid not in membership:
            raise InfrastructureError(
                f"trace row names foreign observation {oid}")
        population = population_by_observation.get(oid)
        if population is None:
            raise InfrastructureError(
                f"{oid}: not a scheduled observation of the pinned "
                "mixture")
        arrays = (row["completions"], row["actions"],
                  row["assignments"], row["rewards"])
        lengths = {len(a) for a in arrays}
        if len(lengths) != 1:
            raise InfrastructureError(
                f"trace row {row.get('global_group_index')}: "
                "parallel arrays differ in length")
        if group_size is None:
            group_size = lengths.pop()
        elif lengths != {group_size}:
            raise InfrastructureError(
                "trace rows do not share one uniform group size")
        info = disclosure[oid]
        cell = info["cell_id"]
        if oid not in positions_cache:
            latent = program.generate_latent(
                cell, "routing_dev", int(oid.split(":")[2]),
                DEFAULT_PROFILE).latent
            positions_cache[oid] = \
                latent["reference_program"]["positions"]
        positions = positions_cache[oid]
        num_steps = len(positions)
        if oid not in pair_cache:
            pair_cache[oid] = derive_pair_entry(oid, cell, surface)
        pair = pair_cache[oid]
        direction = None
        if pair is not None and pair["distinct_payoff"]:
            direction = pair["direction"]

        # re-parse + re-derive every completion; stored fields must
        # agree exactly
        rewards: list[float] = []
        assignments: list[tuple[int, ...] | None] = []
        for text_, s_action, s_assignment, s_reward in zip(*arrays):
            completion_total += 1
            try:
                reparsed = parse_routing_action(text_, num_steps)
            except ActionSchemaError:
                reparsed = None
            if reparsed is None:
                if s_action is not None or s_assignment is not None \
                        or s_reward != 0.0:
                    raise InfrastructureError(
                        f"{oid}: stored action/assignment/reward "
                        "disagree with the re-parse (a malformed "
                        "completion recorded as valid)")
                rewards.append(0.0)
                assignments.append(None)
                continue
            semantic = tuple(positional_to_semantic(reparsed,
                                                    positions))
            payoff = surface.get((oid, semantic))
            if payoff is None:
                raise InfrastructureError(
                    f"({oid}, {semantic}): no surface row")
            if s_action != list(reparsed) \
                    or s_assignment != list(semantic) \
                    or s_reward != float(payoff):
                raise InfrastructureError(
                    f"{oid}: stored action/assignment/reward "
                    f"({s_action}/{s_assignment}/{s_reward}) do not "
                    f"match the re-derivation ({list(reparsed)}/"
                    f"{list(semantic)}/{float(payoff)}) — a "
                    "corrupted redundant field is not an "
                    "alternative result")
            est.reward_level(float(payoff))
            valid_total += 1
            rewards.append(float(payoff))
            assignments.append(semantic)

        per_population[population] = \
            per_population.get(population, 0) + 1
        is_zero_variance = len(set(rewards)) <= 1
        if is_zero_variance:
            zero_variance += 1
        counted = (population == "bridge" and cell in cells
                   and est.q1_counted_event(event, cell, rewards,
                                            assignments))
        contrasts = est.group_contrasts(rewards, assignments, pair)
        group_eligible = sum(
            1 for a in assignments
            if est.c2_eligible_completion(eligibility, cell, a))
        group_optimal = None
        if direction is not None:
            group_optimal = sum(
                1 for a in assignments
                if est.c2_optimal_completion(eligibility, cell, a,
                                             pair))
        model_acc = None
        if direction is not None:
            families = NODE_FAMILIES[cell]
            nodes = sorted(families)
            acc_values = []
            for assignment in assignments:
                if assignment is None:
                    acc_values.append(0.0)
                    continue
                slot_scores = [
                    1.0 if w == direction else 0.0
                    for node, w in zip(nodes, assignment)
                    if families[node] == "code"]
                acc_values.append(
                    sum(slot_scores) / len(slot_scores))
            model_acc = (sum(acc_values), len(acc_values))
        code_index = est.code_node_index(cell)

        stratum_key = (f"{cell}|{info['renderer_id']}"
                       f"|{info['subtype']}|{population}")
        stratum = strata.setdefault(stratum_key, {
            "draws": 0, "valid_completions": 0, "reward_sum": 0.0,
            "zero_variance_groups": 0, "q1_counted_groups": 0,
            "code_worker_selections": {"2": 0, "3": 0, "other": 0},
            "c2_eligible_completions": 0,
            "c2_optimal_completions": 0,
            "model_acc_numerator": 0.0, "model_acc_denominator": 0,
            "direct_contrast_groups": 0,
            "semantic_contrast_groups": 0,
            "latent_indices": []})
        stratum["draws"] += 1
        stratum["zero_variance_groups"] += \
            1 if is_zero_variance else 0
        stratum["q1_counted_groups"] += 1 if counted else 0
        if info["latent_index"] not in stratum["latent_indices"]:
            stratum["latent_indices"] = sorted(
                stratum["latent_indices"] + [info["latent_index"]])
        stratum["c2_eligible_completions"] += group_eligible
        if group_optimal is not None:
            stratum["c2_optimal_completions"] += group_optimal
        if model_acc is not None:
            num, den = model_acc
            stratum["model_acc_numerator"] = round(
                stratum["model_acc_numerator"] + num, 4)
            stratum["model_acc_denominator"] += den
        stratum["direct_contrast_groups"] += \
            1 if contrasts["direct_contrast"] else 0
        stratum["semantic_contrast_groups"] += \
            1 if contrasts["semantic_contrast"] else 0
        stratum["reward_sum"] = round(
            stratum["reward_sum"] + sum(rewards), 4)
        for assignment in assignments:
            if assignment is None:
                continue
            stratum["valid_completions"] += 1
            if code_index is not None:
                worker = assignment[code_index]
                bucket = str(worker) if worker in (2, 3) else "other"
                stratum["code_worker_selections"][bucket] += 1

        if population == "bridge" and cell in cells:
            entry = q1_by_cell[cell]
            entry["bridge_draws"] += 1
            if counted:
                entry["counted_groups"] += 1
                entry["latents"].add(info["latent_index"])
                entry["renderers"].add(info["renderer_id"])
        elif population == "q2_composite":
            key = f"{cell}|{info['direction']}"
            block = q2_blocks.get(key)
            if block is None:
                raise InfrastructureError(
                    f"{oid}: q2_composite row outside the scheduled "
                    f"directions ({key})")
            target_worker = dict(
                contract.q2.per_direction_targets)[key]
            block["draws"] += 1
            block["latents"].add(info["latent_index"])
            block["reward_sum"] = round(
                block["reward_sum"] + sum(rewards), 4)
            block["direct_contrast_groups"] += \
                1 if contrasts["direct_contrast"] else 0
            block["semantic_contrast_groups"] += \
                1 if contrasts["semantic_contrast"] else 0
            block["c2_eligible_completions"] += group_eligible
            if group_optimal is not None:
                block["c2_optimal_completions"] += group_optimal
            if model_acc is not None:
                num, den = model_acc
                block["model_acc_numerator"] = round(
                    block["model_acc_numerator"] + num, 4)
                block["model_acc_denominator"] += den
            for assignment in assignments:
                if assignment is None:
                    continue
                block["valid_completions"] += 1
                worker = assignment[code_index]
                bucket = str(worker) if worker in (2, 3) else "other"
                block["code_worker_selections"][bucket] += 1
                if est.marginal_target_selection(cell, assignment,
                                                 target_worker):
                    state = q2_gate_state[key]
                    state["selections"] += 1
                    state["latents"].add(info["latent_index"])
        elif population == "direct_specialist_control":
            control_block["draws"] += 1
            control_block["c2_eligible_completions"] += \
                group_eligible
            control_block["reward_sum"] = round(
                control_block["reward_sum"] + sum(rewards), 4)

    q1_gate, q1_pass = est.evaluate_q1_gate(contract.q1, cells,
                                            q1_by_cell)
    q2_gate = est.evaluate_q2_cold_start_gate(contract.q2,
                                              q2_gate_state)
    for block in q2_blocks.values():
        block["latents"] = sorted(block["latents"])
    counted_by_cell = {cell: q1_gate[cell]["counted_groups"]
                       for cell in cells}
    if q1_pass:
        sizing = est.derive_sizing(contract.sizing, cells,
                                   counted_by_cell, epochs,
                                   cap_formula)
    else:
        sizing = {"derivable": False,
                  "reason": "the direct-Q1 gate failed — sizing is "
                            "not derived on a stopped run"}
    sentinel = est.sentinel_legacy_view(
        est.sentinel_checkpoint_block(contract.scope, event,
                                      trace_rows))

    projection: dict[str, Any] = {
        "kind": "c2-compatibility-projection-v2",
        "source": {
            "closeout_entry_sha256":
                REPLAY_SOURCE["c2_closeout_entry_sha256"],
            "report_file_sha256":
                REPLAY_SOURCE["c2_report_file_sha256"],
            "schedule_file_sha256":
                REPLAY_SOURCE["c2_schedule_file_sha256"],
        },
        "epoch_rows": epoch_rows,
        "schedule_rows": schedule_rows,
        "mixture_record_sha256": mixture["record_sha256"],
        "class_assignment": dict(sorted(
            mixture["class_assignment"].items())),
        "multiplicities": dict(sorted(
            mixture["multiplicities"].items())),
        "sentinel_observation_ids": sentinel_ids,
        "population_by_observation": dict(sorted(
            population_by_observation.items())),
        "valid_completions": valid_total,
        "invalid_completions": completion_total - valid_total,
        "per_population_draws": dict(sorted(
            per_population.items())),
        "q1_gate": q1_gate,
        "q1_gate_pass_all_cells": q1_pass,
        "q1_counted_per_epoch_measured": {
            cell: round(counted_by_cell[cell] / epochs, 4)
            for cell in cells},
        "q2_blocks": q2_blocks,
        "q2_cold_start_gate": q2_gate,
        "direct_specialist_control": control_block,
        "sentinel_block": sentinel,
        "p0_size_derived": sizing,
        "strata": {key: dict(value)
                   for key, value in sorted(strata.items())},
        "zero_variance_groups": zero_variance,
        "zero_variance_fraction": round(zero_variance / n, 4),
        "preregistered_decision": est.decide_outcome(
            decision_matrix, q1_pass=q1_pass,
            q2_pass=q2_gate["pass"]),
    }
    projection["projection_sha256"] = content_sha256(
        {k: v for k, v in projection.items()
         if k != "projection_sha256"})
    return projection


def compare_projections(derived: Mapping[str, Any],
                        frozen: Mapping[str, Any]) -> list[str]:
    """The mechanical field-by-field comparison; returns the sorted
    names of every differing (or one-sided) top-level field."""
    sentinel_missing = object()
    return sorted(
        key for key in set(derived) | set(frozen)
        if derived.get(key, sentinel_missing)
        != frozen.get(key, sentinel_missing))


def verify_c2_equivalence(evidence_dir: str | Path | None = None
                          ) -> dict[str, Any]:
    """The oracle boundary: the raw-trace rederivation must equal
    the frozen expected projection EXACTLY, field for field, and
    rehash to the externally reviewed projection pin."""
    derived = derive_c2_projection(evidence_dir)
    frozen = load_projection()
    differing = compare_projections(derived, frozen)
    if differing:
        raise InfrastructureError(
            "the C2 replay does not reproduce the frozen "
            f"projection; differing fields: {differing}")
    if derived["projection_sha256"] != PROJECTION_SHA256:
        raise InfrastructureError(
            "the rederived projection does not carry the reviewed "
            "pin")
    return {"verdict": "PASS",
            "fields_compared": len(frozen),
            "projection_sha256": derived["projection_sha256"]}
