"""Unit C — the exact-schedule zero-update exposure sample (269_s §7,
option 1: the preregistered projections chose the candidate BEFORE
this run; Unit C VALIDATES the frozen Unit-B mixture, it does not
choose one).

The rev3-probe-validated machinery on the frozen Unit-B schedule:
5 identical passes over the frozen 157-row epoch = 785 groups /
6,280 completions through the REAL trainer loop at lr=0 / beta=0
(zero effective parameter updates, exact checkpoint-zero adapter
equality), on the LOCKED extension surface, scored through the
extension ScaleLift comparator boundary (never reselecting).

Preregistered evaluation (mechanical, no in-place redesign):

- **Q1 gate** (the frozen Unit-B criterion, block-occupancy form):
  per critical cell, >=2 Q1-counted groups (a reward-1.0 FULLY
  family-correct completion AND a reward-0.5 STRICTLY-lower-fc
  completion in the same group) among BRIDGE-class draws, spanning
  >=2 distinct latents. Any cell failing => stop-and-review (260_f
  disposition matrix as amended); renderer occupancy is REPORTED,
  not gated (274_f supersession).
- **Q2 exposure** is schedule-delivery + reporting: both scheduled
  composite directions must have delivered their exact draws
  (70 `math_code->w3`, 90 `fork_join->w2` at 5 epochs); observed
  ckpt-0 C2-eligible completions are REPORTED — zero is the
  recorded Q2 STARTING CONDITION (269_s §5), never a failure and
  never a direct-C2-exposure claim.
- Zero-variance fractions, per-class exposure, anchor coverage, and
  renderer/subtype-stratified yields are reported against the
  Unit-B projections.
- Any mixture change after this run is a NEW B/C iteration with new
  identities (269_s §7); the preregistered decision rule selects
  only the P0 scope and supplies measured rates to the P0 freeze.

Runtime bound (273_s caution): expected ≈0.944 GPU-h at the
measured 4.33 s/group; the frozen ceiling is a CONSERVATIVE 1.25
GPU-h stop-bound (admitted against the envelope; a ceiling is a
bound, not a target), enforced per optimizer step."""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tasks.conductor.types import RENDERER_IDS, InfrastructureError

from .charter import content_sha256, lightweight_freeze
from .p0_mixture import (
    CRITICAL_CELLS,
    MIXTURE_CONFIG,
    _fc_fraction,
    build_mixture,
    load_frozen_selection,
)
from .resume_validation import (
    attested_environment_sha256,
    make_validation_reward,
    read_trace,
    tensor_state_hashes,
)

UNIT_C_CONFIG: dict[str, Any] = {
    "tranche": "routing-dev-unit-c-exposure-v1",
    # the frozen Unit-B candidate (274_f rev3) — validated, never
    # chosen, by this run
    "mixture_record_sha256":
        "0100df2bbb13447aa394d31ab87eb0dab1e0660e830186eee99028e30432bc01",
    "mixture_config_sha256":
        "92f933e84d6c1c83f258437da30e352a79da7c3e01df87d3ffdf9f7ddc386bf8",
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
    # the exact P0 checkpoint-zero construction VALIDATED by Step 5
    # (identical literals to the Step-6 probe, fresh seed)
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
             "optim": "adamw_torch", "bf16": True, "seed": 20260801},
    "policy_max_new_tokens": 128,
    "zero_update_mechanism": ("785 real trainer optimizer-step calls "
                              "at learning_rate=0 and beta=0; zero "
                              "effective parameter updates; exact "
                              "checkpoint-zero adapter equality"),
    "full_determinism": True,
    "min_free_vram_mib": 20000,
    # 273_s caution: conservative stop-bound; expected ~0.944 GPU-h
    "ceiling_gpu_hours": 1.25,
    "run_root": "runs/routing-dev/unit-c-v1",
    # the preregistered decision rule: outcomes select the P0 scope
    # ONLY (plus measured rates as P0-freeze inputs)
    "decision_rule": {
        "q1_pass_all_cells": "Q1 authorized",
        "q1_fail_any_cell": "stop-and-review (no P0 launch)",
        "q2": ("authorized as the hierarchical-unlocking experiment "
               "iff the schedule delivered exactly; ckpt-0 "
               "C2-eligibility is the recorded starting condition, "
               "zero permitted"),
        "mixture_change": "a NEW B/C iteration with new identities",
    },
    "lineage": {
        "parent_entry_sha256":
            "b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd",
        "outcome_informed": True,
        "motivating_evidence": "274_f frozen mixture (signed); "
                               "269_s §7 option 1",
    },
}
CONFIG_SHA256 = content_sha256(UNIT_C_CONFIG)


def tranche_freeze() -> dict[str, Any]:
    if content_sha256(UNIT_C_CONFIG) != CONFIG_SHA256:
        raise InfrastructureError(
            "UNIT_C_CONFIG was mutated after import")
    return lightweight_freeze({
        "kind": "unit_c_exposure_sample",
        "question": ("Unit C: does the frozen Unit-B schedule "
                     "deliver, at checkpoint zero, the preregistered "
                     "Q1 reward-varying exposure in all four critical "
                     "cells and the exact scheduled Q2 composite "
                     "draws?"),
        "motivation": "269_s §7 option 1; 274_f frozen candidate",
        "config": UNIT_C_CONFIG,
        "budget_gpu_hours": UNIT_C_CONFIG["ceiling_gpu_hours"],
    })


# --- frozen inputs (CPU-testable) ----------------------------------------------

def load_locked_extension(surface_dir: str | Path | None = None
                          ) -> dict[str, Any]:
    from .dev_support import load_dev_surface
    return load_dev_surface(
        surface_dir or UNIT_C_CONFIG["extension_surface_dir"],
        expected_lock_sha256=UNIT_C_CONFIG[
            "extension_surface_lock_sha256"])


def frozen_mixture(loaded: Mapping[str, Any]) -> dict[str, Any]:
    """Rederive the mixture from the locked surface + authenticated
    selection and require it to BE the frozen Unit-B candidate."""
    if content_sha256(MIXTURE_CONFIG) != \
            UNIT_C_CONFIG["mixture_config_sha256"]:
        raise InfrastructureError(
            "the live mixture config is not the frozen Unit-B rev3 "
            "config")
    mixture = build_mixture(loaded, load_frozen_selection())
    if mixture["record_sha256"] != \
            UNIT_C_CONFIG["mixture_record_sha256"]:
        raise InfrastructureError(
            "rederived mixture is not the frozen Unit-B candidate")
    return mixture


def load_extension_comparator() -> dict[str, Any]:
    raw = Path(UNIT_C_CONFIG["extension_comparator_path"]).read_bytes()
    record = json.loads(raw.decode("utf-8"))
    if record.get("record_sha256") != \
            UNIT_C_CONFIG["extension_comparator_sha256"]:
        raise InfrastructureError(
            "extension comparator is not the frozen Unit-A record")
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record["record_sha256"]:
        raise InfrastructureError(
            "extension comparator does not rehash")
    return record


def unit_c_schedule(loaded: Mapping[str, Any],
                    mixture: Mapping[str, Any]
                    ) -> list[dict[str, Any]]:
    """One dataset row per GROUP: the frozen 157-row epoch order,
    repeated for the frozen epoch count (identical passes — the
    zero-update sample has no state between epochs)."""
    from tasks.conductor import program
    from tasks.conductor.policy import policy_messages
    from tasks.conductor.profiles import DEFAULT_PROFILE
    from tasks.conductor.stage1 import prompt_fewshot
    config = UNIT_C_CONFIG
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
    for epoch in range(config["epochs"]):
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
    digest = routing_execution_digest("tasks/routing/unit_c_sample.py")
    lock = loaded["lock"]
    manifest = {
        "kind": "routing-dev-unit-c-identity-v1",
        "routing_source_sha256": digest["routing_source_sha256"],
        "config_sha256": CONFIG_SHA256,
        "mixture_record_sha256": mixture["record_sha256"],
        "mixture_config_sha256":
            UNIT_C_CONFIG["mixture_config_sha256"],
        "extension_surface_lock_sha256": lock["lock_sha256"],
        "extension_comparator_sha256":
            UNIT_C_CONFIG["extension_comparator_sha256"],
        "prompt_sha256": hashlib.sha256(
            prompt_fewshot().encode("utf-8")).hexdigest(),
        "seed": str(UNIT_C_CONFIG["grpo"]["seed"]),
    }
    manifest["manifest_sha256"] = content_sha256(manifest)
    return manifest


# --- the exposure report (CPU-testable) ----------------------------------------

def q1_counted(cell: str, rewards: list, assignments: list) -> bool:
    """The registered Q1 event: a reward-1.0 FULLY family-correct
    completion AND a reward-0.5 completion of STRICTLY LOWER family
    correctness in the same group."""
    has_r1_fc = any(
        r == 1.0 and a is not None
        and _fc_fraction(cell, tuple(a)) == 1.0
        for r, a in zip(rewards, assignments))
    has_half_lower = any(
        r == 0.5 and a is not None
        and _fc_fraction(cell, tuple(a)) < 1.0
        for r, a in zip(rewards, assignments))
    return has_r1_fc and has_half_lower


def build_exposure_report(run_root: str | Path) -> dict[str, Any]:
    """The preregistered evaluation, rebuilt entirely from persisted
    trace rows against the locked surface, the frozen mixture, and
    the frozen selection disclosure."""
    from .probe_run import groups_from_trace
    run_root = Path(run_root)
    loaded = load_locked_extension()
    mixture = frozen_mixture(loaded)
    selection = load_frozen_selection()
    comparator = load_extension_comparator()
    disclosure = selection["public_factor_disclosure"]
    classes = mixture["class_assignment"]
    trace_rows = read_trace(run_root / "actions.jsonl")
    # authenticated group reconstruction (probe rev3 boundary; the
    # comparator flows through the extension-aware ScaleLift entry)
    groups = groups_from_trace(trace_rows, loaded, comparator)

    per_class: dict[str, int] = {}
    q1_by_cell: dict[str, dict[str, Any]] = {
        cell: {"counted_groups": 0, "latents": set(),
               "renderers": set(), "bridge_draws": 0}
        for cell in CRITICAL_CELLS}
    q2_draws = {"math_code|w3_favoured": 0, "fork_join|w2_favoured": 0}
    c2_eligible_completions = 0
    zero_variance = 0
    for row, group in zip(trace_rows, groups):
        oid = row["observation_id"]
        cls = classes.get(oid)
        if cls is None:
            raise InfrastructureError(
                f"{oid}: scheduled row is not in the frozen mixture")
        per_class[cls] = per_class.get(cls, 0) + 1
        cell = disclosure[oid]["cell_id"]
        rewards = [r for r in row["rewards"]]
        if len(set(rewards)) <= 1:
            zero_variance += 1
        if cls == "bridge" and cell in CRITICAL_CELLS:
            entry = q1_by_cell[cell]
            entry["bridge_draws"] += 1
            if q1_counted(cell, row["rewards"], row["assignments"]):
                entry["counted_groups"] += 1
                entry["latents"].add(disclosure[oid]["latent_index"])
                entry["renderers"].add(disclosure[oid]["renderer_id"])
        if cls == "q2_composite":
            key = f"{cell}|{disclosure[oid]['direction']}"
            if key in q2_draws:
                q2_draws[key] += 1
        if group["c2_eligible"] is not None:
            c2_eligible_completions += group["c2_eligible"]

    config = UNIT_C_CONFIG
    criterion_src = MIXTURE_CONFIG["q1_gate_criterion"]
    q1_gate: dict[str, Any] = {}
    q1_pass = True
    for cell in CRITICAL_CELLS:
        entry = q1_by_cell[cell]
        cell_pass = (
            entry["counted_groups"]
            >= criterion_src["min_counted_groups_per_cell"]
            and len(entry["latents"])
            >= criterion_src["min_distinct_latents_among_counted"])
        q1_pass = q1_pass and cell_pass
        q1_gate[cell] = {
            "bridge_draws": entry["bridge_draws"],
            "counted_groups": entry["counted_groups"],
            "distinct_latents": sorted(entry["latents"]),
            "renderers_observed": sorted(entry["renderers"]),
            "pass": cell_pass,
        }
    expected_q2 = {
        "math_code|w3_favoured": 14 * config["epochs"],
        "fork_join|w2_favoured": 18 * config["epochs"],
    }
    schedule_delivered = q2_draws == expected_q2
    report = {
        "design": {
            "config_sha256": CONFIG_SHA256,
            "mixture_record_sha256": mixture["record_sha256"],
            "extension_surface_lock_sha256":
                loaded["lock"]["lock_sha256"],
            "total_groups": config["total_groups"],
            "epochs": config["epochs"],
        },
        "per_class_draws": dict(sorted(per_class.items())),
        "q1_gate": q1_gate,
        "q1_gate_pass_all_cells": q1_pass,
        "q2_composite_draws": q2_draws,
        "q2_schedule_delivered_exactly": schedule_delivered,
        "ckpt0_c2_eligible_completions": c2_eligible_completions,
        "c2_note": ("ckpt-0 C2 eligibility is the recorded Q2 "
                    "STARTING CONDITION; zero is permitted and is "
                    "never a direct-C2-exposure claim (269_s §5)"),
        "zero_variance_groups": zero_variance,
        "zero_variance_fraction": round(
            zero_variance / len(groups), 4),
        "projected_zero_variance_fraction":
            mixture["projections"]["expected_zero_variance_fraction"],
        "preregistered_decision": (
            ("Q1 authorized; Q2 authorized as the hierarchical-"
             "unlocking experiment" if schedule_delivered else
             "schedule NOT delivered exactly — stop-and-review")
            if q1_pass else
            "Q1 gate failed — stop-and-review (no P0 launch)"),
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
    if preflight["floor_mib"] != UNIT_C_CONFIG["min_free_vram_mib"]:
        raise InfrastructureError(
            "preflight floor is not the frozen one")
    if preflight["free_mib"] < preflight["floor_mib"]:
        raise InfrastructureError(
            "the archived preflight FAILED (free < floor)")
    if preflight["total_mib"] < preflight["free_mib"]:
        raise InfrastructureError("preflight total < free")


def verify_unit_c_run(run_root: str | Path,
                      expected_identity_sha256: str,
                      expected_environment_sha256: str
                      ) -> dict[str, Any]:
    """The anchored independent archive verifier (probe rev3
    pattern): environment (self-hash + attested + REVIEWED anchor),
    identity manifest (rehash + anchor + frozen fields), preflight,
    the frozen mixture rederivation, exact trace cardinality/order,
    the zero-mutation gate over TWO PERSISTED maps, design counters,
    the telemetry schema, and the exact report rederivation."""
    from .dev_support import validate_env_self_hash
    run_root = Path(run_root)
    record = json.loads(
        (run_root / "sample_record.json").read_text("utf-8"))
    if record["config_sha256"] != CONFIG_SHA256 \
            or record["tranche"] != UNIT_C_CONFIG["tranche"] \
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
            or identity["manifest_sha256"] != expected_identity_sha256:
        raise InfrastructureError(
            "archived identity manifest does not rehash, bind, or "
            "match the REVIEWED identity")
    if identity["config_sha256"] != CONFIG_SHA256 \
            or identity["mixture_record_sha256"] != \
            UNIT_C_CONFIG["mixture_record_sha256"] \
            or identity["extension_surface_lock_sha256"] != \
            UNIT_C_CONFIG["extension_surface_lock_sha256"]:
        raise InfrastructureError(
            "identity manifest fields do not match the frozen "
            "configuration")
    preflight = json.loads(
        (run_root / "session_preflight.json").read_text("utf-8"))
    if content_sha256(preflight) != \
            record["session_preflight_sha256"] \
            or record["session_preflight"] != preflight:
        raise InfrastructureError(
            "archived preflight does not match the record")
    _verify_preflight(preflight)
    # the schedule must be the frozen mixture, five identical passes
    loaded = load_locked_extension()
    mixture = frozen_mixture(loaded)
    expected_schedule = list(mixture["schedule_rows"]) \
        * UNIT_C_CONFIG["epochs"]
    schedule = json.loads(
        (run_root / "schedule.json").read_text("utf-8"))
    if schedule != expected_schedule:
        raise InfrastructureError(
            "archived schedule does not rederive from the frozen "
            "mixture")
    trace_rows = read_trace(run_root / "actions.jsonl")
    total = UNIT_C_CONFIG["total_groups"]
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
    if zero_map != final_map:
        raise InfrastructureError(
            "zero-mutation gate FAILS on the persisted maps")
    if content_sha256(zero_map) != \
            record["checkpoint_zero_adapter_sha256"] \
            or content_sha256(final_map) != \
            record["final_adapter_sha256"]:
        raise InfrastructureError(
            "persisted hash maps do not match the record digests")
    group_size = UNIT_C_CONFIG["grpo"]["group_size"]
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
            UNIT_C_CONFIG["ceiling_gpu_hours"] * 3600.0:
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
    """The exact Step-5-validated checkpoint-zero construction (fp32
    adapters), with the frozen Unit-C zero-update hyperparameters —
    identical to the probe builder except the config source."""
    import random

    import numpy
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer, BitsAndBytesConfig
    from trl import GRPOConfig, GRPOTrainer
    config = UNIT_C_CONFIG
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
              "floor_mib": UNIT_C_CONFIG["min_free_vram_mib"]}
    if result["free_mib"] < result["floor_mib"]:
        raise InfrastructureError(
            f"session preflight FAILED: {result['free_mib']} MiB free "
            f"< the frozen floor {result['floor_mib']}")
    return result


def execute_unit_c(*, expected_freeze_sha256: str,
                   expected_identity_sha256: str,
                   expected_environment_sha256: str,
                   expected_head_sha256: str,
                   ledger_path: str | Path | None = None,
                   _environment_builder=None) -> dict[str, Any]:
    """The Unit-C run, in the validated Step-5/6 lifecycle shape."""
    from tasks.routing import checkpoint as ckpt

    from .ledger import LEDGER_PATH, admit_and_append_launch, \
        append_ledger_entry
    from .probe_run import _ConsumeCallback
    from .resume_validation import _DeadlineCallback, _release_trainer
    from .support_run import _hash_directory, _sha_file
    ledger_path = ledger_path or LEDGER_PATH
    config = UNIT_C_CONFIG
    frozen = tranche_freeze()
    if frozen["freeze_sha256"] != expected_freeze_sha256:
        raise InfrastructureError(
            "the reconstructed freeze is not the reviewed one")
    if expected_head_sha256 != \
            config["lineage"]["parent_entry_sha256"]:
        raise InfrastructureError(
            "expected_head_sha256 must equal the lineage parent "
            "frozen in UNIT_C_CONFIG")
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
    mixture = frozen_mixture(loaded)
    load_extension_comparator()
    rows = unit_c_schedule(loaded, mixture)
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
                "the sample MUTATED the model — zero-effective-update "
                "gate fails; this is an infrastructure abort")
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
        verify_unit_c_run(run_root, expected_identity_sha256,
                          expected_environment_sha256)
    except BaseException as error:
        measured = round((time.monotonic() - started) / 3600.0, 4)
        append_ledger_entry(
            {"kind": "closeout", "question": frozen["question"],
             "motivating_evidence": "Unit-C sample ABORTED",
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
         "motivating_evidence": "Unit-C sample complete",
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
