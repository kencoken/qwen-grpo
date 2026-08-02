"""Unit C2 — the exact-schedule zero-update exposure sample on the
PINNED B2 mixture (295_f-signed; the one sanctioned fresh run).

Versioned alongside the untouched V1 (`unit_c_sample`), consuming
the B2 candidate `135a72bf…` through `p0_mixture_v2`:

- **preflight runs `verify_c1_basis()`** — the authoritative C1
  gate (fresh, uncached) — in addition to the environment/identity
  anchors; C1's root and evidence are never touched (C2 has its own
  run root and a fresh seed);
- **executable row predicates** (the 294_s obligation): the frozen
  population descriptions are small named functions with
  cross-population tests — every scheduled row belongs to exactly
  one population, the Q1 population is bridge-only, the Q2
  population excludes the direct-specialist control, the sentinel
  population is the pinned record's ids;
- the report consumes the SINGLE definitions from the B2 module:
  `sentinel_block` (pinned-record-bound), `decide_c2_outcome` (the
  frozen four-branch matrix), `derive_p0_size_v2` (sizing cells =
  the three direct-Q1 cells);
- gates: per direct-Q1 cell ≥2 counted from ≥2 latents; the
  per-direction Q2 cold-start gate on the intended target worker;
  the sentinel is mechanically excluded from gate, sizing,
  authorization, and headline aggregates;
- lifecycle, anchored verifier, zero-update contract (785 real
  optimizer steps at lr=0/beta=0; exact 504-key checkpoint-zero
  adapter equality), ceiling 1.25 GPU-h — the validated V1 shape
  with identical construction literals (fresh seed only)."""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tasks.conductor.types import InfrastructureError

from .charter import content_sha256, lightweight_freeze
from .p0_mixture_v2 import (
    DIRECT_Q1_CELLS,
    EXPECTED_MIXTURE_V2_RECORD_SHA256,
    MIXTURE_V2_CONFIG,
    SENTINEL_CELL,
    build_mixture_v2,
    decide_c2_outcome,
    derive_p0_size_v2,
    load_frozen_selection_v2,
    sentinel_block,
    verify_c1_basis,
)
from .resume_validation import (
    attested_environment_sha256,
    make_validation_reward,
    read_trace,
    tensor_state_hashes,
)

UNIT_C2_CONFIG: dict[str, Any] = {
    "tranche": "routing-dev-unit-c2-exposure-v1",
    # the PINNED B2 candidate — validated, never chosen, by this run
    "mixture_record_sha256": EXPECTED_MIXTURE_V2_RECORD_SHA256,
    "mixture_config_sha256":
        "66d62b924a471c869dd77312b062399842eedd05325b3927c8cee542b0e6cfb5",
    "extension_surface_lock_sha256":
        "ccb1c3e2db2422a82919292144c0bdecc21d2cc89cb7a3a2c69bec17a2ce6d1b",
    "extension_surface_dir": "runs/routing-dev/support-ext-v1/surface",
    "extension_comparator_path":
        "plans/conductor/evidence/support_extension_v1/comparator.json",
    "extension_comparator_sha256":
        "9220c2c7a7efe890c60e5abbdcc3b84eecbbb971e75fa69e313e6d61888e5f1f",
    "epochs": 5,
    "epoch_rows": 157,
    "total_groups": 785,
    # the exact Step-5-validated construction (identical literals to
    # C1/probe; FRESH seed)
    "model_id": "Qwen/Qwen2.5-3B-Instruct",
    "revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
    "quantization": {"load_in_4bit": True, "quant_type": "nf4",
                     "double_quant": True, "compute_dtype": "bfloat16"},
    "lora": {"r": 16, "alpha": 32, "dropout": 0.05,
             "adapter_dtype": "float32",
             "targets": ["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"]},
    "grpo": {"beta": 0.0, "group_size": 8, "temperature": 1.0,
             "per_device_batch": 2, "grad_accum": 4,
             "learning_rate": 0.0, "warmup_steps": 0,
             "scheduler": "constant", "loss": "dapo",
             "optim": "adamw_torch", "bf16": True, "seed": 20260803},
    "policy_max_new_tokens": 128,
    "zero_update_mechanism": ("785 real trainer optimizer-step calls "
                              "at learning_rate=0 and beta=0; zero "
                              "effective parameter updates; exact "
                              "checkpoint-zero adapter equality"),
    "full_determinism": True,
    "lora_key_set": {
        "count": 504,
        "sorted_keys_sha256":
            "e44ecb9caf0be396aaaceae6802dbaab9209677103ba263c89ca9a7ea65f6215",
    },
    "min_free_vram_mib": 20000,
    "ceiling_gpu_hours": 1.25,
    "run_root": "runs/routing-dev/unit-c2-v1",
    "lineage": {
        "parent_entry_sha256":
            "9f4661a84e601299951f17370eb22d9aa52f970a717b80844684240c8c550996",
        "outcome_informed": True,
        "motivating_evidence": "295_f-signed B2 (pinned 135a72bf…); "
                               "290_f wrap-up plan; 283_s route",
    },
}
CONFIG_SHA256 = content_sha256(UNIT_C2_CONFIG)


def tranche_freeze() -> dict[str, Any]:
    if content_sha256(UNIT_C2_CONFIG) != CONFIG_SHA256:
        raise InfrastructureError(
            "UNIT_C2_CONFIG was mutated after import")
    return lightweight_freeze({
        "kind": "unit_c2_exposure_sample",
        "question": ("Unit C2: at checkpoint zero on the PINNED B2 "
                     "schedule, is the Q1 reward-varying exposure "
                     "present in all three direct-Q1 cells, and does "
                     "each scheduled Q2 direction show cold-start "
                     "marginal support for its intended specialist?"),
        "motivation": "295_f-signed B2; 290_f matrix; 283_s route",
        "config": UNIT_C2_CONFIG,
        "budget_gpu_hours": UNIT_C2_CONFIG["ceiling_gpu_hours"],
    })


# --- frozen inputs (CPU-testable) ----------------------------------------------

def load_locked_extension(surface_dir: str | Path | None = None
                          ) -> dict[str, Any]:
    from .dev_support import load_dev_surface
    return load_dev_surface(
        surface_dir or UNIT_C2_CONFIG["extension_surface_dir"],
        expected_lock_sha256=UNIT_C2_CONFIG[
            "extension_surface_lock_sha256"])


def pinned_mixture(loaded: Mapping[str, Any]) -> dict[str, Any]:
    """Rederive the mixture and require it to BE the pinned B2
    candidate (the builder itself enforces the pin; this re-checks
    the config lineage)."""
    if content_sha256(MIXTURE_V2_CONFIG) != \
            UNIT_C2_CONFIG["mixture_config_sha256"]:
        raise InfrastructureError(
            "the live B2 config is not the frozen rev2/3 config")
    mixture = build_mixture_v2(loaded, load_frozen_selection_v2())
    if mixture["record_sha256"] != \
            UNIT_C2_CONFIG["mixture_record_sha256"]:
        raise InfrastructureError(
            "rederived mixture is not the pinned B2 candidate")
    return mixture


def load_extension_comparator() -> dict[str, Any]:
    raw = Path(
        UNIT_C2_CONFIG["extension_comparator_path"]).read_bytes()
    record = json.loads(raw.decode("utf-8"))
    if record.get("record_sha256") != \
            UNIT_C2_CONFIG["extension_comparator_sha256"]:
        raise InfrastructureError(
            "extension comparator is not the frozen Unit-A record")
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record["record_sha256"]:
        raise InfrastructureError(
            "extension comparator does not rehash")
    return record


# --- executable row predicates (the 294_s obligation) --------------------------

def row_population(mixture: Mapping[str, Any], oid: str) -> str:
    """The ONE population map: every scheduled row belongs to exactly
    one population; the sentinel population is the PINNED record's
    ids (its rows are anchor-class; membership is by frozen id)."""
    if oid in set(mixture["sentinel"]["observation_ids"]):
        return "sentinel"
    cls = mixture["class_assignment"].get(oid)
    if cls is None:
        raise InfrastructureError(
            f"{oid}: scheduled row is not in the pinned mixture")
    return cls


def is_q1_population(mixture: Mapping[str, Any], oid: str) -> bool:
    """Bridge-class draws only (the frozen outcome contract)."""
    return row_population(mixture, oid) == "bridge"


def is_q2_population(mixture: Mapping[str, Any], oid: str) -> bool:
    """q2_composite rows only; the direct-specialist control is
    excluded from every Q2 statistic and gate."""
    return row_population(mixture, oid) == "q2_composite"


def is_sentinel_population(mixture: Mapping[str, Any],
                           oid: str) -> bool:
    return row_population(mixture, oid) == "sentinel"


# --- schedule + identity (CPU-testable) ----------------------------------------

def unit_c2_schedule(loaded: Mapping[str, Any],
                     mixture: Mapping[str, Any]
                     ) -> list[dict[str, Any]]:
    """Five identical passes over the pinned 157-row epoch."""
    from tasks.conductor import program
    from tasks.conductor.policy import policy_messages
    from tasks.conductor.profiles import DEFAULT_PROFILE
    from tasks.conductor.stage1 import prompt_fewshot
    config = UNIT_C2_CONFIG
    meta = {obs["observation_id"]: obs
            for obs in loaded["observations"]}
    system = prompt_fewshot()
    epoch_rows = mixture["schedule_rows"]
    if len(epoch_rows) != config["epoch_rows"]:
        raise InfrastructureError(
            f"mixture epoch has {len(epoch_rows)} rows; the frozen "
            f"design needs {config['epoch_rows']}")
    per_oid_cache: dict[str, dict[str, Any]] = {}
    rows = []
    for _epoch in range(config["epochs"]):
        for oid in epoch_rows:
            if oid not in per_oid_cache:
                obs = meta[oid]
                latent = program.generate_latent(
                    obs["cell_id"], "routing_dev",
                    int(oid.split(":")[2]), DEFAULT_PROFILE).latent
                inst = program.render_instance(
                    latent, obs["renderer_id"], oid.split(":")[5])
                if inst["render_instance_id"] != oid:
                    raise InfrastructureError(
                        f"regenerated instance != scheduled {oid}")
                steps = [{"subtask": s["subtask"],
                          "resource": s["resource"],
                          "access": s["access"]}
                         for s in program.workflow_steps(latent)]
                user = policy_messages(inst, steps)[1]
                per_oid_cache[oid] = {
                    "prompt": [{"role": "system", "content": system},
                               dict(user)],
                    "observation_id": oid,
                    "cell_id": obs["cell_id"],
                    "num_steps": len(steps),
                    "positions": json.dumps(
                        latent["reference_program"]["positions"]),
                }
            rows.append(dict(per_oid_cache[oid]))
    if len(rows) != config["total_groups"]:
        raise InfrastructureError(
            f"schedule has {len(rows)} rows; the frozen design needs "
            f"{config['total_groups']}")
    return rows


def static_identity_manifest(loaded: Mapping[str, Any],
                             mixture: Mapping[str, Any]
                             ) -> dict[str, Any]:
    from tasks.conductor.stage1 import prompt_fewshot

    from .charter import routing_execution_digest
    digest = routing_execution_digest(
        "tasks/routing/unit_c2_sample.py")
    lock = loaded["lock"]
    manifest = {
        "kind": "routing-dev-unit-c2-identity-v1",
        "routing_source_sha256": digest["routing_source_sha256"],
        "config_sha256": CONFIG_SHA256,
        "mixture_record_sha256": mixture["record_sha256"],
        "mixture_config_sha256":
            UNIT_C2_CONFIG["mixture_config_sha256"],
        "extension_surface_lock_sha256": lock["lock_sha256"],
        "extension_comparator_sha256":
            UNIT_C2_CONFIG["extension_comparator_sha256"],
        "prompt_sha256": hashlib.sha256(
            prompt_fewshot().encode("utf-8")).hexdigest(),
        "seed": str(UNIT_C2_CONFIG["grpo"]["seed"]),
    }
    manifest["manifest_sha256"] = content_sha256(manifest)
    return manifest


# --- the exposure report (CPU-testable) ----------------------------------------

def q1_counted(cell: str, rewards: list, assignments: list) -> bool:
    from .p0_mixture import _fc_fraction
    has_r1_fc = any(
        r == 1.0 and a is not None
        and _fc_fraction(cell, tuple(a)) == 1.0
        for r, a in zip(rewards, assignments))
    has_half_lower = any(
        r == 0.5 and a is not None
        and _fc_fraction(cell, tuple(a)) < 1.0
        for r, a in zip(rewards, assignments))
    return has_r1_fc and has_half_lower


def _code_node_index(cell: str) -> int | None:
    from tasks.conductor.stage1 import NODE_FAMILIES
    families = NODE_FAMILIES[cell]
    nodes = sorted(families)
    for i, node in enumerate(nodes):
        if families[node] == "code":
            return i
    return None


def build_exposure_report(run_root: str | Path) -> dict[str, Any]:
    """The preregistered C2 evaluation over the executable
    populations; the decision comes from the frozen four-branch
    matrix via `decide_c2_outcome`."""
    from .probe_run import groups_from_trace
    run_root = Path(run_root)
    loaded = load_locked_extension()
    mixture = pinned_mixture(loaded)
    selection = load_frozen_selection_v2()
    comparator = load_extension_comparator()
    disclosure = selection["public_factor_disclosure"]
    config = UNIT_C2_CONFIG
    trace_rows = read_trace(run_root / "actions.jsonl")
    expected_schedule = list(mixture["schedule_rows"]) \
        * config["epochs"]
    if [row["observation_id"] for row in trace_rows] != \
            expected_schedule:
        raise InfrastructureError(
            "trace rows are not the exact pinned schedule — no "
            "report from a partial archive")
    groups = groups_from_trace(trace_rows, loaded, comparator)

    gate_config = MIXTURE_V2_CONFIG["q2_cold_start_gate"]
    criterion = MIXTURE_V2_CONFIG["q1_gate_criterion"]
    per_population: dict[str, int] = {}
    q1_by_cell = {cell: {"counted_groups": 0, "latents": set(),
                         "renderers": set(), "bridge_draws": 0}
                  for cell in DIRECT_Q1_CELLS}
    q2_blocks: dict[str, dict[str, Any]] = {}
    for key in gate_config["per_direction"]:
        q2_blocks[key] = {
            "draws": 0, "latents": set(), "valid_completions": 0,
            "c2_eligible_completions": 0,
            "c2_optimal_completions": 0,
            "model_acc_numerator": 0.0, "model_acc_denominator": 0,
            "code_worker_selections": {"2": 0, "3": 0, "other": 0},
            "reward_sum": 0.0, "direct_contrast_groups": 0,
            "semantic_contrast_groups": 0,
        }
    q2_gate_state = {key: {"selections": 0, "latents": set()}
                     for key in gate_config["per_direction"]}
    control_block = {"draws": 0, "c2_eligible_completions": 0,
                     "reward_sum": 0.0}
    strata: dict[str, dict[str, Any]] = {}
    zero_variance = 0

    for row, group in zip(trace_rows, groups):
        oid = row["observation_id"]
        population = row_population(mixture, oid)
        per_population[population] = \
            per_population.get(population, 0) + 1
        info = disclosure[oid]
        cell = info["cell_id"]
        rewards = list(row["rewards"])
        is_zero_variance = len(set(rewards)) <= 1
        if is_zero_variance:
            zero_variance += 1
        counted = (population == "bridge"
                   and cell in DIRECT_Q1_CELLS
                   and q1_counted(cell, row["rewards"],
                                  row["assignments"]))
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
        stratum["c2_eligible_completions"] += group["c2_eligible"]
        if group["c2_optimal"] is not None:
            stratum["c2_optimal_completions"] += group["c2_optimal"]
        if group["model_acc"] is not None:
            num, den = group["model_acc"]
            stratum["model_acc_numerator"] = round(
                stratum["model_acc_numerator"] + num, 4)
            stratum["model_acc_denominator"] += den
        stratum["direct_contrast_groups"] += \
            1 if group["direct_contrast"] else 0
        stratum["semantic_contrast_groups"] += \
            1 if group["semantic_contrast"] else 0
        stratum["reward_sum"] = round(
            stratum["reward_sum"] + sum(rewards), 4)
        code_index = _code_node_index(cell)
        for assignment in row["assignments"]:
            if assignment is None:
                continue
            stratum["valid_completions"] += 1
            if code_index is not None:
                worker = assignment[code_index]
                bucket = str(worker) if worker in (2, 3) else "other"
                stratum["code_worker_selections"][bucket] += 1

        if population == "bridge" and cell in DIRECT_Q1_CELLS:
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
            spec = gate_config["per_direction"][key]
            block["draws"] += 1
            block["latents"].add(info["latent_index"])
            block["reward_sum"] = round(
                block["reward_sum"] + sum(rewards), 4)
            block["direct_contrast_groups"] += \
                1 if group["direct_contrast"] else 0
            block["semantic_contrast_groups"] += \
                1 if group["semantic_contrast"] else 0
            block["c2_eligible_completions"] += group["c2_eligible"]
            if group["c2_optimal"] is not None:
                block["c2_optimal_completions"] += \
                    group["c2_optimal"]
            if group["model_acc"] is not None:
                num, den = group["model_acc"]
                block["model_acc_numerator"] = round(
                    block["model_acc_numerator"] + num, 4)
                block["model_acc_denominator"] += den
            for assignment in row["assignments"]:
                if assignment is None:
                    continue
                block["valid_completions"] += 1
                worker = assignment[code_index]
                bucket = str(worker) if worker in (2, 3) else "other"
                block["code_worker_selections"][bucket] += 1
                if worker == spec["target_worker"]:
                    state = q2_gate_state[key]
                    state["selections"] += 1
                    state["latents"].add(info["latent_index"])
        elif population == "direct_specialist_control":
            control_block["draws"] += 1
            control_block["c2_eligible_completions"] += \
                group["c2_eligible"]
            control_block["reward_sum"] = round(
                control_block["reward_sum"] + sum(rewards), 4)

    q1_gate: dict[str, Any] = {}
    q1_pass = True
    for cell in DIRECT_Q1_CELLS:
        entry = q1_by_cell[cell]
        cell_pass = (
            entry["counted_groups"]
            >= criterion["min_counted_groups_per_cell"]
            and len(entry["latents"])
            >= criterion["min_distinct_latents_among_counted"])
        q1_pass = q1_pass and cell_pass
        q1_gate[cell] = {
            "bridge_draws": entry["bridge_draws"],
            "counted_groups": entry["counted_groups"],
            "distinct_latents": sorted(entry["latents"]),
            "renderers_observed": sorted(entry["renderers"]),
            "pass": cell_pass,
        }
    q2_gate_detail = {}
    q2_pass = True
    for key, spec in gate_config["per_direction"].items():
        state = q2_gate_state[key]
        direction_pass = (
            state["selections"]
            >= gate_config["min_target_selections"]
            and len(state["latents"])
            >= gate_config["min_distinct_latents"])
        q2_pass = q2_pass and direction_pass
        q2_gate_detail[key] = {
            "target_worker": spec["target_worker"],
            "target_selections": state["selections"],
            "distinct_latents": sorted(state["latents"]),
            "pass": direction_pass,
        }
    for block in q2_blocks.values():
        block["latents"] = sorted(block["latents"])
    counted_by_cell = {cell: q1_gate[cell]["counted_groups"]
                       for cell in DIRECT_Q1_CELLS}
    sizing = derive_p0_size_v2(counted_by_cell, config["epochs"]) \
        if q1_pass else {
            "derivable": False,
            "reason": "the direct-Q1 gate failed — sizing is not "
                      "derived on a stopped run"}
    report = {
        "design": {
            "config_sha256": CONFIG_SHA256,
            "mixture_record_sha256": mixture["record_sha256"],
            "extension_surface_lock_sha256":
                loaded["lock"]["lock_sha256"],
            "total_groups": config["total_groups"],
            "epochs": config["epochs"],
        },
        "per_population_draws": dict(sorted(per_population.items())),
        "q1_gate": q1_gate,
        "q1_gate_pass_all_cells": q1_pass,
        "q1_counted_per_epoch_measured": {
            cell: round(counted_by_cell[cell] / config["epochs"], 4)
            for cell in DIRECT_Q1_CELLS},
        "q2_blocks": q2_blocks,
        "q2_cold_start_gate": {
            "min_target_selections":
                gate_config["min_target_selections"],
            "min_distinct_latents":
                gate_config["min_distinct_latents"],
            "per_direction": q2_gate_detail,
            "pass": q2_pass},
        "direct_specialist_control": control_block,
        "sentinel_block": sentinel_block(trace_rows, mixture),
        "p0_size_derived": sizing,
        "strata": {key: dict(value) for key, value in
                   sorted(strata.items())},
        "zero_variance_groups": zero_variance,
        "zero_variance_fraction": round(
            zero_variance / len(groups), 4),
        "preregistered_decision": decide_c2_outcome(
            q1_pass=q1_pass, q2_pass=q2_pass),
    }
    return report


# --- the anchored independent verifier -----------------------------------------

def _verify_preflight(preflight: Mapping[str, Any]) -> None:
    if set(preflight) != {"free_mib", "total_mib", "floor_mib"}:
        raise InfrastructureError("preflight schema is not exact")
    for field in ("free_mib", "total_mib", "floor_mib"):
        value = preflight[field]
        if not isinstance(value, int) or isinstance(value, bool) \
                or value < 0:
            raise InfrastructureError(
                f"preflight {field} must be a non-negative int")
    if preflight["floor_mib"] != UNIT_C2_CONFIG["min_free_vram_mib"]:
        raise InfrastructureError(
            "preflight floor is not the frozen one")
    if preflight["free_mib"] < preflight["floor_mib"]:
        raise InfrastructureError(
            "the archived preflight FAILED (free < floor)")
    if preflight["total_mib"] < preflight["free_mib"]:
        raise InfrastructureError("preflight total < free")


def verify_unit_c2_run(run_root: str | Path,
                       expected_identity_sha256: str,
                       expected_environment_sha256: str
                       ) -> dict[str, Any]:
    """The anchored independent archive verifier (the validated V1
    shape): environment/identity anchors, the pinned mixture
    rederivation, exact trace cardinality/order, the zero-mutation
    gate over the two persisted 504-key maps, design counters, the
    telemetry schema, and the exact report rederivation."""
    from .dev_support import validate_env_self_hash
    run_root = Path(run_root)
    record = json.loads(
        (run_root / "sample_record.json").read_text("utf-8"))
    if record["config_sha256"] != CONFIG_SHA256 \
            or record["tranche"] != UNIT_C2_CONFIG["tranche"] \
            or record["freeze_sha256"] != \
            tranche_freeze()["freeze_sha256"]:
        raise InfrastructureError(
            "sample record does not match the frozen configuration")
    archived_env = json.loads(
        (run_root / "environment_manifest.json").read_text("utf-8"))
    if validate_env_self_hash(archived_env) != \
            record["environment_manifest_sha256"]:
        raise InfrastructureError(
            "archived environment does not match the record")
    if attested_environment_sha256(archived_env) != \
            record["attested_environment_sha256"] \
            or record["attested_environment_sha256"] != \
            expected_environment_sha256:
        raise InfrastructureError(
            "archived environment is not the REVIEWED one")
    identity = json.loads(
        (run_root / "identity_manifest.json").read_text("utf-8"))
    body = {k: v for k, v in identity.items()
            if k != "manifest_sha256"}
    if content_sha256(body) != identity["manifest_sha256"] \
            or identity["manifest_sha256"] != \
            record["identity_manifest_sha256"] \
            or identity["manifest_sha256"] != \
            expected_identity_sha256:
        raise InfrastructureError(
            "archived identity manifest does not rehash, bind, or "
            "match the REVIEWED identity")
    if identity["config_sha256"] != CONFIG_SHA256 \
            or identity["mixture_record_sha256"] != \
            UNIT_C2_CONFIG["mixture_record_sha256"] \
            or identity["extension_surface_lock_sha256"] != \
            UNIT_C2_CONFIG["extension_surface_lock_sha256"]:
        raise InfrastructureError(
            "identity manifest fields do not match the frozen "
            "configuration")
    # 297_s: the sample record's mixture provenance must equal BOTH
    # the frozen config and the identity manifest — a closeout-bound
    # artifact cannot carry false provenance
    if record.get("mixture_record_sha256") != \
            UNIT_C2_CONFIG["mixture_record_sha256"] \
            or record.get("mixture_record_sha256") != \
            identity["mixture_record_sha256"]:
        raise InfrastructureError(
            "sample-record mixture provenance does not match the "
            "frozen config and identity (297_s)")
    preflight = json.loads(
        (run_root / "session_preflight.json").read_text("utf-8"))
    if content_sha256(preflight) != \
            record["session_preflight_sha256"] \
            or record["session_preflight"] != preflight:
        raise InfrastructureError(
            "archived preflight does not match the record")
    _verify_preflight(preflight)
    loaded = load_locked_extension()
    mixture = pinned_mixture(loaded)
    expected_schedule = list(mixture["schedule_rows"]) \
        * UNIT_C2_CONFIG["epochs"]
    schedule = json.loads(
        (run_root / "schedule.json").read_text("utf-8"))
    if schedule != expected_schedule:
        raise InfrastructureError(
            "archived schedule does not rederive from the pinned "
            "mixture")
    trace_rows = read_trace(run_root / "actions.jsonl")
    total = UNIT_C2_CONFIG["total_groups"]
    if len(trace_rows) != total:
        raise InfrastructureError(
            f"trace has {len(trace_rows)} groups; the design needs "
            f"{total}")
    for i, row in enumerate(trace_rows):
        if row["global_group_index"] != i \
                or row["observation_id"] != schedule[i]:
            raise InfrastructureError(
                f"trace row {i} violates the frozen schedule/order")
    zero_map = json.loads(
        (run_root / "checkpoint_zero_hashes.json").read_text("utf-8"))
    final_map = json.loads(
        (run_root / "checkpoint_final_hashes.json").read_text("utf-8"))
    key_set = UNIT_C2_CONFIG["lora_key_set"]
    for label, mapping in (("zero", zero_map), ("final", final_map)):
        if not mapping or any("lora" not in key for key in mapping):
            raise InfrastructureError(
                f"{label} adapter map is empty or holds non-LoRA "
                "keys — no substrate")
        if len(mapping) != key_set["count"] \
                or content_sha256(sorted(mapping)) != \
                key_set["sorted_keys_sha256"]:
            raise InfrastructureError(
                f"{label} adapter map keys are not the validated "
                f"{key_set['count']}-key LoRA set")
    if zero_map != final_map:
        raise InfrastructureError(
            "zero-mutation gate FAILS on the persisted maps")
    if content_sha256(zero_map) != \
            record["checkpoint_zero_adapter_sha256"] \
            or content_sha256(final_map) != \
            record["final_adapter_sha256"]:
        raise InfrastructureError(
            "persisted hash maps do not match the record digests")
    group_size = UNIT_C2_CONFIG["grpo"]["group_size"]
    expected_counters = {
        "generated_groups": total, "consumed_groups": total,
        "optimizer_updates": total,
        "sampled_completions": total * group_size}
    if record["counters"] != expected_counters:
        raise InfrastructureError(
            f"counters {record['counters']} != the design-derived "
            f"{expected_counters}")
    telemetry_block = record["execution_telemetry"]
    if set(telemetry_block) != {
            "group_accounting", "surface_reward_lookups",
            "live_worker_calls", "worker_cache", "wall_seconds",
            "deadline_seconds", "peak_reserved_vram_mib",
            "session_preflight"}:
        raise InfrastructureError(
            "execution-telemetry schema is not exact")
    valid_completions = sum(
        1 for row in trace_rows for action in row["actions"]
        if action is not None)
    if telemetry_block["surface_reward_lookups"] != valid_completions \
            or telemetry_block["live_worker_calls"] != 0 \
            or telemetry_block["group_accounting"] != \
            record["counters"] \
            or telemetry_block["session_preflight"] != preflight \
            or telemetry_block["deadline_seconds"] != \
            UNIT_C2_CONFIG["ceiling_gpu_hours"] * 3600.0:
        raise InfrastructureError(
            "execution telemetry does not rederive")
    rederived = build_exposure_report(run_root)
    persisted = json.loads(
        (run_root / "exposure_report.json").read_text("utf-8"))
    if persisted != json.loads(json.dumps(rederived)):
        raise InfrastructureError(
            "persisted exposure report does not rederive from the "
            "archived traces")
    return {"verdict": "PASS", "groups": total,
            "decision": persisted["preregistered_decision"]}


# --- the GPU run ---------------------------------------------------------------

def _build_sample_trainer(rows, reward, run_dir: Path,
                          extra_callbacks=()):
    """The exact Step-5-validated construction (identical literals to
    C1/probe; the frozen fresh seed)."""
    import random

    import numpy
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer, BitsAndBytesConfig
    from trl import GRPOConfig, GRPOTrainer
    config = UNIT_C2_CONFIG
    grpo = config["grpo"]
    seed = grpo["seed"]
    random.seed(seed)
    numpy.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    processing_class = AutoTokenizer.from_pretrained(
        config["model_id"], revision=config["revision"])
    args = GRPOConfig(
        output_dir=str(run_dir), run_name=run_dir.name,
        seed=seed, num_generations=grpo["group_size"],
        max_completion_length=config["policy_max_new_tokens"],
        temperature=float(grpo["temperature"]),
        per_device_train_batch_size=grpo["per_device_batch"],
        gradient_accumulation_steps=grpo["grad_accum"],
        learning_rate=float(grpo["learning_rate"]),
        lr_scheduler_type=grpo["scheduler"],
        warmup_steps=grpo["warmup_steps"], beta=float(grpo["beta"]),
        max_steps=config["total_groups"], loss_type=grpo["loss"],
        shuffle_dataset=False, eval_strategy="no",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        bf16=grpo["bf16"],
        full_determinism=config["full_determinism"],
        model_init_kwargs={
            "torch_dtype": torch.bfloat16,
            "attn_implementation": "sdpa",
            "revision": config["revision"],
            "quantization_config": BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16)},
        optim=grpo["optim"], report_to="none", logging_steps=16,
        save_strategy="no")
    peft_config = LoraConfig(
        r=config["lora"]["r"], lora_alpha=config["lora"]["alpha"],
        lora_dropout=config["lora"]["dropout"],
        target_modules=list(config["lora"]["targets"]),
        task_type="CAUSAL_LM")
    trainer = GRPOTrainer(
        model=config["model_id"], args=args,
        train_dataset=Dataset.from_list(list(rows)),
        processing_class=processing_class, reward_funcs=[reward],
        peft_config=peft_config)
    adapter_dtype = getattr(torch, config["lora"]["adapter_dtype"])
    if adapter_dtype is not torch.float32:
        raise InfrastructureError(
            "the validated construction is float32 adapters only")
    for name, parameter in trainer.model.named_parameters():
        if "lora" in name:
            parameter.data = parameter.data.to(adapter_dtype)
    for callback in extra_callbacks:
        trainer.add_callback(callback)
    return trainer


def _preflight() -> dict[str, int]:
    import torch
    free, total = torch.cuda.mem_get_info()
    result = {"free_mib": int(free // 2 ** 20),
              "total_mib": int(total // 2 ** 20),
              "floor_mib": UNIT_C2_CONFIG["min_free_vram_mib"]}
    if result["free_mib"] < result["floor_mib"]:
        raise InfrastructureError(
            f"session preflight FAILED: {result['free_mib']} MiB "
            f"free < the frozen floor {result['floor_mib']}")
    return result


def execute_unit_c2(*, expected_freeze_sha256: str,
                    expected_identity_sha256: str,
                    expected_environment_sha256: str,
                    expected_head_sha256: str,
                    ledger_path: str | Path | None = None,
                    _environment_builder=None) -> dict[str, Any]:
    """The C2 run, in the validated lifecycle shape. Preflight runs
    the AUTHORITATIVE C1-basis gate (fresh) before admission."""
    from tasks.routing import checkpoint as ckpt

    from .ledger import LEDGER_PATH, admit_and_append_launch, \
        append_ledger_entry
    from .probe_run import _ConsumeCallback
    from .resume_validation import _DeadlineCallback, _release_trainer
    from .support_run import _hash_directory, _sha_file
    ledger_path = ledger_path or LEDGER_PATH
    config = UNIT_C2_CONFIG
    frozen = tranche_freeze()
    if frozen["freeze_sha256"] != expected_freeze_sha256:
        raise InfrastructureError(
            "the reconstructed freeze is not the reviewed one")
    if expected_head_sha256 != \
            config["lineage"]["parent_entry_sha256"]:
        raise InfrastructureError(
            "expected_head_sha256 must equal the lineage parent "
            "frozen in UNIT_C2_CONFIG")
    # the AUTHORITATIVE C1-basis gate, fresh, pre-admission
    verify_c1_basis(ledger_path=ledger_path)
    if _environment_builder is None:
        from tasks.conductor.stage1_manifest import \
            build_stage1_env_manifest
        environment = build_stage1_env_manifest()
    else:
        environment = _environment_builder()
    from .dev_support import validate_environment_manifest_binding
    env_sha = validate_environment_manifest_binding(environment)
    if attested_environment_sha256(environment) != \
            expected_environment_sha256:
        raise InfrastructureError(
            "the live environment is not the reviewed one")
    loaded = load_locked_extension()
    mixture = pinned_mixture(loaded)
    load_extension_comparator()
    rows = unit_c2_schedule(loaded, mixture)
    identity_manifest = static_identity_manifest(loaded, mixture)
    if identity_manifest["manifest_sha256"] != \
            expected_identity_sha256:
        raise InfrastructureError(
            "the execution identity is not the reviewed one")
    preflight = _preflight()
    preflight_sha = content_sha256(preflight)
    run_root = Path(config["run_root"])
    if run_root.exists():
        raise InfrastructureError(
            f"{run_root} exists; the sample runs exactly once")
    run_root.mkdir(parents=True)
    for name, payload in (
            ("environment_manifest.json", environment),
            ("identity_manifest.json", identity_manifest),
            ("session_preflight.json", preflight),
            ("schedule.json",
             [row["observation_id"] for row in rows])):
        (run_root / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")

    lineage = config["lineage"]
    entry = {
        "kind": "standalone_evaluation",
        "question": frozen["question"],
        "motivating_evidence": lineage["motivating_evidence"],
        "freeze": {"freeze_sha256": frozen["freeze_sha256"],
                   "config_sha256": CONFIG_SHA256,
                   "identity_manifest_sha256":
                       identity_manifest["manifest_sha256"],
                   "environment_manifest_sha256": env_sha,
                   "attested_environment_sha256":
                       expected_environment_sha256,
                   "session_preflight_sha256": preflight_sha,
                   "mixture_record_sha256":
                       mixture["record_sha256"]},
        "parent": lineage["parent_entry_sha256"],
        "budget_allocated_gpu_hours": config["ceiling_gpu_hours"],
        "outcome_informed": lineage["outcome_informed"],
        "cohort_selection": "outcome_conditioned",
    }
    admitted = admit_and_append_launch(entry, expected_head_sha256,
                                       ledger_path)
    head = admitted["entry_sha256"]
    started = time.monotonic()
    deadline = started + config["ceiling_gpu_hours"] * 3600.0

    try:
        accountant = ckpt.GroupAccountant()
        trace_path = run_root / "actions.jsonl"
        reward = make_validation_reward(
            loaded["surface"], accountant, trace_path,
            config["grpo"]["group_size"])
        trainer = _build_sample_trainer(
            rows, reward, run_root / "trainer",
            [_DeadlineCallback(deadline).callback,
             _ConsumeCallback(accountant).callback])
        zero_map = tensor_state_hashes(
            {k: v for k, v in trainer.model.state_dict().items()
             if "lora" in k})
        (run_root / "checkpoint_zero_hashes.json").write_text(
            json.dumps(zero_map, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        trainer.train()
        final_map = tensor_state_hashes(
            {k: v for k, v in trainer.model.state_dict().items()
             if "lora" in k})
        (run_root / "checkpoint_final_hashes.json").write_text(
            json.dumps(final_map, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        import torch as _torch
        peak_reserved_mib = (
            round(_torch.cuda.max_memory_reserved() / 2 ** 20)
            if _torch.cuda.is_available() else 0)
        holder = {"trainer": trainer}
        del trainer
        _release_trainer(holder)
        if final_map != zero_map:
            raise InfrastructureError(
                "the sample MUTATED the model — zero-effective-"
                "update gate fails; this is an infrastructure abort")
        counters = accountant.authorize_checkpoint()
        total = config["total_groups"]
        expected_counters = {
            "generated_groups": total, "consumed_groups": total,
            "optimizer_updates": total,
            "sampled_completions":
                total * config["grpo"]["group_size"]}
        if counters != expected_counters:
            raise InfrastructureError(
                f"counters {counters} != the frozen design "
                f"{expected_counters}")
        trace_rows = read_trace(trace_path)
        for i, row in enumerate(trace_rows):
            if row["observation_id"] != rows[i]["observation_id"] \
                    or row["global_group_index"] != i:
                raise InfrastructureError(
                    f"trace group {i} does not match the frozen "
                    "schedule")
        report = build_exposure_report(run_root)
        valid_completions = sum(
            1 for row in trace_rows for action in row["actions"]
            if action is not None)
        execution_telemetry = {
            "group_accounting": dict(counters),
            "surface_reward_lookups": valid_completions,
            "live_worker_calls": 0,
            "worker_cache": ("not-applicable: rewards derive from "
                             "the locked payoff surface; no worker "
                             "executes during the sample"),
            "wall_seconds": round(time.monotonic() - started, 1),
            "deadline_seconds":
                config["ceiling_gpu_hours"] * 3600.0,
            "peak_reserved_vram_mib": peak_reserved_mib,
            "session_preflight": preflight,
        }
        record = {
            "tranche": config["tranche"],
            "freeze_sha256": frozen["freeze_sha256"],
            "config_sha256": CONFIG_SHA256,
            "identity_manifest_sha256":
                identity_manifest["manifest_sha256"],
            "environment_manifest_sha256": env_sha,
            "attested_environment_sha256":
                expected_environment_sha256,
            "session_preflight": preflight,
            "session_preflight_sha256": preflight_sha,
            "checkpoint_zero_adapter_sha256":
                content_sha256(zero_map),
            "final_adapter_sha256": content_sha256(final_map),
            "counters": counters,
            "mixture_record_sha256": mixture["record_sha256"],
            "execution_telemetry": execution_telemetry,
        }
        for name, payload in (("exposure_report.json", report),
                              ("sample_record.json", record)):
            (run_root / name).write_text(
                json.dumps(payload, indent=1, sort_keys=True) + "\n",
                encoding="utf-8")
        verify_unit_c2_run(run_root, expected_identity_sha256,
                           expected_environment_sha256)
    except BaseException as error:
        measured = round((time.monotonic() - started) / 3600.0, 4)
        append_ledger_entry(
            {"kind": "closeout", "question": frozen["question"],
             "motivating_evidence": "Unit-C2 sample ABORTED",
             "freeze": {"freeze_sha256": frozen["freeze_sha256"],
                        "partial_artifact_hashes": (
                            _hash_directory(run_root)
                            if run_root.exists() else
                            {"(nothing written)": "-"})},
             "parent": head, "budget_allocated_gpu_hours": 0.0,
             "budget_consumed_gpu_hours": measured,
             "closes_entry_sha256": head,
             "terminal_status": "aborted",
             "interpretation": f"{type(error).__name__}: {error}",
             "outcome_informed": True,
             "outcome_pointer": str(run_root)},
            head, ledger_path)
        raise

    measured = round((time.monotonic() - started) / 3600.0, 4)
    closeout = append_ledger_entry(
        {"kind": "closeout", "question": frozen["question"],
         "motivating_evidence": "Unit-C2 sample complete",
         "freeze": {
             "freeze_sha256": frozen["freeze_sha256"],
             "exposure_report_file_sha256":
                 _sha_file(run_root / "exposure_report.json"),
             "sample_record_file_sha256":
                 _sha_file(run_root / "sample_record.json"),
             "terminal_artifact_hashes": _hash_directory(run_root),
         },
         "parent": head, "budget_allocated_gpu_hours": 0.0,
         "budget_consumed_gpu_hours": measured,
         "closes_entry_sha256": head,
         "terminal_status": "complete",
         "outcome_informed": True,
         "outcome_pointer": str(run_root / "exposure_report.json")},
        head, ledger_path)
    return {"tranche": config["tranche"],
            "measured_gpu_hours": measured,
            "launch_entry_sha256": head,
            "closeout_entry_sha256": closeout["entry_sha256"],
            "ledger_head": closeout["entry_sha256"],
            "report": str(run_root / "exposure_report.json")}
