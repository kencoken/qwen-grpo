"""Step-5 GPU resume-validation tranche (211_f §11, 232_s sequence).

The infrastructure-acceptance run for the v1 checkpoint contract on
the REAL training stack: GRPOTrainer (NF4 + LoRA, the stage-0C
hyperparameter shape) training on the locked routing_dev support,
with checkpoints ONLY at the v1 boundary and a full
interrupted-vs-uninterrupted comparison.

Design (all literals frozen in RESUME_VALIDATION_CONFIG; the
tranche's lightweight freeze commits this config's hash and the
EXACT ceiling, 212_f reminder 2):

- 8 completions per optimizer step (per-device 2 × grad-accum 4) =
  exactly ONE group of G=8, generated at the start of each
  accumulation cycle (`steps_per_generation` = grad-accum default),
  so EVERY optimizer step is a v1 boundary and the HF `save_steps`
  checkpoint at update 3 satisfies `generated == consumed` by
  construction — the accountant still verifies it.
- 6 optimizer updates total over a deterministic 6-observation
  schedule (canonical order from the locked surface), few-shot
  system prompt + rendered user message — the same construction P0
  will use.
- Three runs: UNINTERRUPTED (0→6), INTERRUPTED (0→3, stop at the
  bundle), RESUME (fail-closed `validate_resume` + RNG restore +
  HF `resume_from_checkpoint`, 3→6). The §11 acceptance comparison:
  final adapter/optimizer/scheduler state under the FROZEN tolerance
  (0.0 — exact; deterministic algorithms requested; a nonzero
  difference is a reported finding, never a silent widening), next
  sampler identity, counters, and merged trace cardinality.
- Rewards authenticate against the locked surface (malformed → 0.0;
  a missing row is an infrastructure abort, never a reward), and
  every group appends a trace row (segment-local `actions.jsonl`)
  carrying its global group index for `merge_segments`.

Every run here is development data; the tranche is authorized by the
signed charter (212_f §1 item: GPU resume validation) and admitted
through the ledger at execution.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from tasks.conductor.types import InfrastructureError

from . import checkpoint as ckpt
from .charter import content_sha256
from .dev_support import load_dev_surface

# --- frozen tranche configuration (hashed into the lightweight freeze) --------

RESUME_VALIDATION_CONFIG: dict[str, Any] = {
    "tranche": "routing-dev-resume-validation-v1",
    # the Step-4 surface this trains on (231_f)
    "surface_lock_sha256": ("61c4e85a53683c9e2dbcbf15f60794935a76a"
                            "86d979a69412a97f44ea9f2562b"),
    "surface_dir": "runs/routing-dev/support-v1/surface",
    # model + finetuning shape (the stage-0C launch profile values)
    "model_id": "Qwen/Qwen2.5-3B-Instruct",
    "revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
    "quantization": {"load_in_4bit": True, "quant_type": "nf4",
                     "double_quant": True, "compute_dtype": "bfloat16"},
    "lora": {"r": 16, "alpha": 32, "dropout": 0.05,
             "targets": ["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"]},
    "grpo": {"beta": 1e-3, "group_size": 8, "temperature": 1.0,
             "per_device_batch": 2, "grad_accum": 4,
             "learning_rate": 1e-5, "warmup_steps": 0,
             "scheduler": "constant", "loss": "dapo",
             "optim": "adamw_torch", "bf16": True, "seed": 20260728},
    "policy_max_new_tokens": 128,
    "total_updates": 6,
    "checkpoint_at_update": 3,
    # §11 acceptance: the comparison tolerance, frozen BEFORE the test
    "comparison_tolerance": 0.0,
    # 212_f reminder 2: the tranche's EXACT operational ceiling
    "ceiling_gpu_hours": 0.5,
    "run_root": "runs/routing-dev/resume-validation-v1",
}

CONFIG_SHA256 = content_sha256(RESUME_VALIDATION_CONFIG)


def tranche_freeze() -> dict[str, Any]:
    """The 211_f §1 lightweight freeze for this tranche."""
    from .charter import lightweight_freeze
    return lightweight_freeze({
        "kind": "resume_validation",
        "question": ("Does the v1 checkpoint contract hold on the real "
                     "GRPOTrainer stack — boundary-only checkpoints, "
                     "exact counter/RNG/sampler restoration, and an "
                     "interrupted run indistinguishable from an "
                     "uninterrupted one?"),
        "motivation": "211_f §11 / §15 step 5; 232_s sequence item 2",
        "config": RESUME_VALIDATION_CONFIG,
        "budget_gpu_hours":
            RESUME_VALIDATION_CONFIG["ceiling_gpu_hours"],
    })


# --- dataset and reward (CPU-testable) ----------------------------------------

def load_locked_support(surface_dir: str | Path | None = None
                        ) -> dict[str, Any]:
    return load_dev_surface(
        surface_dir or RESUME_VALIDATION_CONFIG["surface_dir"],
        expected_lock_sha256=
        RESUME_VALIDATION_CONFIG["surface_lock_sha256"])


def training_schedule(loaded: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One row per optimizer update: the first `total_updates`
    observations in canonical (sorted observation-id) order. The
    schedule is part of the frozen identity."""
    from tasks.conductor import program
    from tasks.conductor.stage1 import prompt_fewshot
    from tasks.conductor.policy import policy_messages
    total = RESUME_VALIDATION_CONFIG["total_updates"]
    observations = sorted(loaded["observations"],
                          key=lambda obs: obs["observation_id"])
    if len(observations) < total:
        raise InfrastructureError(
            f"support has {len(observations)} observations; the "
            f"schedule needs {total}")
    system = prompt_fewshot()
    rows = []
    for obs in observations[:total]:
        # regenerate the instance for the rendered user message — the
        # loader's meta is identity-only
        from tasks.conductor.profiles import DEFAULT_PROFILE
        latent = program.generate_latent(
            obs["cell_id"], "routing_dev",
            int(obs["observation_id"].split(":")[2]),
            DEFAULT_PROFILE).latent
        inst = program.render_instance(
            latent, obs["renderer_id"],
            obs["observation_id"].split(":")[5])
        if inst["render_instance_id"] != obs["observation_id"]:
            raise InfrastructureError(
                f"regenerated instance {inst['render_instance_id']} != "
                f"scheduled {obs['observation_id']}")
        steps = [{"subtask": s["subtask"], "resource": s["resource"],
                  "access": s["access"]}
                 for s in program.workflow_steps(latent)]
        user = policy_messages(inst, steps)[1]
        assert user["role"] == "user"
        rows.append({
            "prompt": [{"role": "system", "content": system},
                       dict(user)],
            "observation_id": obs["observation_id"],
            "cell_id": obs["cell_id"],
            "num_steps": len(steps),
            "positions": json.dumps(
                latent["reference_program"]["positions"]),
        })
    return rows


def schedule_identities(rows: list[Mapping[str, Any]]) -> dict[str, str]:
    from tasks.conductor.stage1 import prompt_fewshot
    import hashlib
    return {
        "training_cohort_sha256": content_sha256(
            [row["observation_id"] for row in rows]),
        "renderer_schedule_sha256": content_sha256(
            [row["observation_id"].split(":")[4] for row in rows]),
        "prompt_sha256": hashlib.sha256(
            prompt_fewshot().encode("utf-8")).hexdigest(),
    }


def make_validation_reward(surface: Mapping[tuple[str, tuple[int, ...]],
                                            float],
                           accountant: ckpt.GroupAccountant,
                           trace_path: str | Path,
                           group_size: int,
                           start_group_index: int = 0
                           ) -> Callable[..., list[float]]:
    """Authenticated reward + group accounting + trace rows. One call
    per generation batch (= one group at this configuration)."""
    from tasks.conductor.grpo_task import positional_to_semantic
    from tasks.conductor.parser import ActionSchemaError, \
        parse_routing_action
    trace_path = Path(trace_path)
    state = {"group_index": start_group_index}

    def reward(completions: list[Any], *, observation_id: list[str],
               positions: list[str], num_steps: list[int],
               **_: Any) -> list[float]:
        if len(completions) % group_size != 0:
            raise InfrastructureError(
                f"batch of {len(completions)} is not whole groups of "
                f"{group_size}")
        if len(set(observation_id)) != len(completions) // group_size:
            raise InfrastructureError(
                "group/observation alignment broken — a group must be "
                "one observation")
        rewards = []
        for completion, oid, positions_json, steps in zip(
                completions, observation_id, positions, num_steps):
            text = completion if isinstance(completion, str) else \
                completion[0].get("content", "")
            try:
                action = parse_routing_action(text, steps)
            except ActionSchemaError:
                rewards.append(0.0)
                continue
            semantic = tuple(positional_to_semantic(
                action, json.loads(positions_json)))
            payoff = surface.get((oid, semantic))
            if payoff is None:
                raise InfrastructureError(
                    f"({oid}, {semantic}): no surface row — an "
                    "infrastructure abort, never a reward")
            rewards.append(float(payoff))
        groups = len(completions) // group_size
        accountant.record_generation(groups=groups,
                                     completions=len(completions))
        with trace_path.open("a", encoding="utf-8") as handle:
            for g in range(groups):
                handle.write(json.dumps({
                    "global_group_index": state["group_index"] + g,
                    "observation_id": observation_id[g * group_size],
                    "rewards": rewards[g * group_size:
                                       (g + 1) * group_size],
                }, sort_keys=True) + "\n")
        state["group_index"] += groups
        return rewards

    reward.state = state
    return reward


# --- comparison (CPU-testable) ------------------------------------------------

def compare_tensor_states(state_a: Mapping[str, Any],
                          state_b: Mapping[str, Any],
                          tolerance: float, label: str
                          ) -> None:
    """§11 acceptance 5: exact (or frozen-tolerance) agreement of
    tensor state dicts; a mismatch reports the worst key."""
    import torch
    keys_a, keys_b = set(state_a), set(state_b)
    if keys_a != keys_b:
        raise InfrastructureError(
            f"{label}: state keys differ "
            f"({sorted(keys_a ^ keys_b)[:3]}…)")
    worst_key, worst = None, 0.0
    for key in sorted(keys_a):
        a, b = state_a[key], state_b[key]
        if isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor):
            if a.shape != b.shape or a.dtype != b.dtype:
                raise InfrastructureError(
                    f"{label}: {key} shape/dtype mismatch")
            diff = (a.detach().float().cpu()
                    - b.detach().float().cpu()).abs().max().item() \
                if a.numel() else 0.0
        elif a == b:
            diff = 0.0
        else:
            raise InfrastructureError(
                f"{label}: non-tensor field {key} differs: "
                f"{a!r} != {b!r}")
        if diff > worst:
            worst_key, worst = key, diff
    if worst > tolerance:
        raise InfrastructureError(
            f"{label}: max abs diff {worst} at {worst_key} exceeds the "
            f"frozen tolerance {tolerance} (211_f §11.5)")


def _flatten_optimizer_state(state: Mapping[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for pid, buffers in state.get("state", {}).items():
        for name, value in buffers.items():
            flat[f"state.{pid}.{name}"] = value
    for i, group in enumerate(state.get("param_groups", [])):
        for name, value in group.items():
            if name != "params":
                flat[f"group.{i}.{name}"] = value
    return flat


def compare_runs(final_a: Mapping[str, Any], final_b: Mapping[str, Any]
                 ) -> dict[str, Any]:
    """The full §11.5 comparison between the uninterrupted final state
    and the interrupted+resumed final state. Both are the dicts
    produced by `_final_state`."""
    tolerance = RESUME_VALIDATION_CONFIG["comparison_tolerance"]
    compare_tensor_states(final_a["adapter"], final_b["adapter"],
                          tolerance, "adapter")
    compare_tensor_states(
        _flatten_optimizer_state(final_a["optimizer"]),
        _flatten_optimizer_state(final_b["optimizer"]),
        tolerance, "optimizer")
    if final_a["scheduler"] != final_b["scheduler"]:
        raise InfrastructureError("scheduler state differs")
    if final_a["next_sampler_identity"] != \
            final_b["next_sampler_identity"]:
        raise InfrastructureError(
            "next sampler/renderer identity differs (211_f §11.5)")
    if final_a["counters"] != final_b["counters"]:
        raise InfrastructureError(
            f"counters differ: {final_a['counters']} != "
            f"{final_b['counters']}")
    if final_a["trace_cardinality"] != final_b["trace_cardinality"]:
        raise InfrastructureError(
            f"merged trace cardinality differs: "
            f"{final_a['trace_cardinality']} != "
            f"{final_b['trace_cardinality']}")
    return {"tolerance": tolerance, "adapter_keys":
            len(final_a["adapter"]), "verdict": "PASS"}


# --- the GPU phases (exercised by the tranche run, not by CPU tests) ----------

def _identities(loaded: Mapping[str, Any],
                rows: list[Mapping[str, Any]],
                environment_manifest_sha256: str) -> dict[str, str]:
    from .charter import routing_execution_digest
    digest = routing_execution_digest(
        "tasks/routing/resume_validation.py")
    lock = loaded["lock"]
    return {
        "routing_source_sha256": digest["routing_source_sha256"],
        "environment_manifest_sha256": environment_manifest_sha256,
        "config_sha256": CONFIG_SHA256,
        "surface_manifest_sha256": lock["manifest_sha256"],
        "worker_pool_fingerprint": lock["worker_pool_fingerprint"],
        "cache_identity": lock["cache_identity"],
        "seed": str(RESUME_VALIDATION_CONFIG["grpo"]["seed"]),
        **schedule_identities(rows),
    }


def _build_trainer(rows, reward, run_dir: Path, max_steps: int,
                   save_at: int | None):
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer, BitsAndBytesConfig
    from trl import GRPOConfig, GRPOTrainer
    config = RESUME_VALIDATION_CONFIG
    grpo = config["grpo"]
    processing_class = AutoTokenizer.from_pretrained(
        config["model_id"], revision=config["revision"])
    args = GRPOConfig(
        output_dir=str(run_dir), run_name=run_dir.name,
        seed=grpo["seed"], num_generations=grpo["group_size"],
        max_completion_length=config["policy_max_new_tokens"],
        temperature=float(grpo["temperature"]),
        per_device_train_batch_size=grpo["per_device_batch"],
        gradient_accumulation_steps=grpo["grad_accum"],
        learning_rate=float(grpo["learning_rate"]),
        lr_scheduler_type=grpo["scheduler"],
        warmup_steps=grpo["warmup_steps"], beta=float(grpo["beta"]),
        max_steps=max_steps, loss_type=grpo["loss"],
        shuffle_dataset=False, eval_strategy="no",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        bf16=grpo["bf16"],
        model_init_kwargs={
            "torch_dtype": torch.bfloat16,
            "attn_implementation": "sdpa",
            "revision": config["revision"],
            "quantization_config": BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16)},
        optim=grpo["optim"], report_to="none", logging_steps=1,
        save_strategy=("steps" if save_at else "no"),
        save_steps=(save_at or 0),
        save_only_model=False)
    peft_config = LoraConfig(
        r=config["lora"]["r"], lora_alpha=config["lora"]["alpha"],
        lora_dropout=config["lora"]["dropout"],
        target_modules=list(config["lora"]["targets"]),
        task_type="CAUSAL_LM")
    return GRPOTrainer(
        model=config["model_id"], args=args,
        train_dataset=Dataset.from_list(list(rows)),
        processing_class=processing_class, reward_funcs=[reward],
        peft_config=peft_config)


def _adapter_state(trainer) -> dict[str, Any]:
    return {name: value.detach().clone()
            for name, value in trainer.model.state_dict().items()
            if "lora" in name}


def _final_state(trainer, accountant, trace_paths: list[Path],
                 rows) -> dict[str, Any]:
    consumed = accountant.consumed_groups
    next_row = (rows[consumed]["observation_id"]
                if consumed < len(rows) else "END")
    segments_rows = 0
    for path in trace_paths:
        segments_rows += sum(1 for _ in path.open())
    return {
        "adapter": _adapter_state(trainer),
        "optimizer": trainer.optimizer.state_dict(),
        "scheduler": trainer.lr_scheduler.state_dict(),
        "next_sampler_identity": next_row,
        "counters": {"generated_groups": accountant.generated_groups,
                     "consumed_groups": accountant.consumed_groups,
                     "optimizer_updates": accountant.optimizer_updates,
                     "sampled_completions":
                         accountant.sampled_completions},
        "trace_cardinality": segments_rows,
    }


class _BoundaryCallback:
    """Counts consumed groups at optimizer steps and writes the v1
    contract bundle at the checkpoint step."""

    def __init__(self, accountant, bundle_dir: Path | None,
                 identities: Mapping[str, str] | None,
                 run_id: str, segment_id: str,
                 groups_per_update: int) -> None:
        from transformers import TrainerCallback

        accountant_ref = accountant
        bundle_ref = bundle_dir
        callback_self = self

        class _Callback(TrainerCallback):
            def on_optimizer_step(self, args, state, control, **kw):
                accountant_ref.record_update(
                    consumed_groups=groups_per_update)

            def on_save(self, args, state, control, **kw):
                if bundle_ref is None:
                    return
                callback_self.write_bundle(kw["model"],
                                           kw.get("optimizer"),
                                           kw.get("lr_scheduler"),
                                           state)

        self.accountant = accountant
        self.bundle_dir = bundle_dir
        self.identities = dict(identities or {})
        self.run_id = run_id
        self.segment_id = segment_id
        self.callback = _Callback()
        self.record = None

    def write_bundle(self, model, optimizer, scheduler, state) -> None:
        import torch
        bundle = self.bundle_dir
        bundle.mkdir(parents=True, exist_ok=True)
        counters = self.accountant.authorize_checkpoint()
        adapter_path = bundle / \
            ckpt.CHECKPOINT_BUNDLE_FILENAMES["adapter"]
        from safetensors.torch import save_file
        save_file({k: v.detach().to("cpu").contiguous()
                   for k, v in model.state_dict().items()
                   if "lora" in k}, str(adapter_path))
        torch.save(optimizer.state_dict(),
                   bundle / ckpt.CHECKPOINT_BUNDLE_FILENAMES[
                       "optimizer"])
        torch.save(scheduler.state_dict(),
                   bundle / ckpt.CHECKPOINT_BUNDLE_FILENAMES[
                       "scheduler"])
        rng_state = ckpt.capture_rng_state()
        ckpt.persist_rng_state(bundle, rng_state)
        filenames = {name: ckpt.CHECKPOINT_BUNDLE_FILENAMES[name]
                     for name in ("adapter", "optimizer", "scheduler",
                                  "rng")}
        hashes = ckpt.hash_state_artifacts(bundle, filenames)
        self.record = ckpt.build_checkpoint_record(
            identities=self.identities, counters=counters,
            rng_state=rng_state, state_artifact_hashes=hashes,
            sampler_position={"next_global_group_index":
                              counters["consumed_groups"],
                              "hf_global_step": state.global_step},
            run_id=self.run_id, segment_id=self.segment_id,
            parent_checkpoint=None)
        (bundle / "checkpoint_record.json").write_text(
            json.dumps(self.record, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")


def execute_resume_validation(*, expected_head_sha256: str,
                              ledger_path: str | Path | None = None,
                              _environment_builder=None
                              ) -> dict[str, Any]:
    """The full Step-5 tranche: admit → uninterrupted run →
    interrupted run (bundle at update 3) → fail-closed resume →
    §11 comparison → closeout (aborted on any post-admission
    failure, with measured cost). Run only after the tranche freeze
    is committed and reviewed."""
    import gc

    import torch

    from .ledger import LEDGER_PATH, admit_and_append_launch, \
        append_ledger_entry
    ledger_path = ledger_path or LEDGER_PATH
    config = RESUME_VALIDATION_CONFIG
    frozen = tranche_freeze()
    if _environment_builder is None:
        from tasks.conductor.stage1_manifest import \
            build_stage1_env_manifest
        environment = build_stage1_env_manifest()
    else:
        environment = _environment_builder()
    from .dev_support import validate_environment_manifest_binding
    env_sha = validate_environment_manifest_binding(environment)
    loaded = load_locked_support()
    rows = training_schedule(loaded)
    identities = _identities(loaded, rows, env_sha)
    run_root = Path(config["run_root"])
    if run_root.exists():
        raise InfrastructureError(
            f"{run_root} exists; the tranche runs exactly once")

    entry = {
        "kind": "resume_validation",
        "question": frozen["question"],
        "motivating_evidence": "234_f freeze; 232_s sequence item 2",
        "freeze": {"freeze_sha256": frozen["freeze_sha256"],
                   "config_sha256": CONFIG_SHA256},
        "parent": None,
        "budget_allocated_gpu_hours": config["ceiling_gpu_hours"],
        "outcome_informed": False,
    }
    admitted = admit_and_append_launch(entry, expected_head_sha256,
                                       ledger_path)
    head = admitted["entry_sha256"]
    started = time.monotonic()
    deadline = started + config["ceiling_gpu_hours"] * 3600.0

    def _guard(phase: str) -> None:
        if time.monotonic() > deadline:
            raise InfrastructureError(
                f"ceiling reached before {phase} — aborting inside "
                "the frozen budget")

    def _release(trainer) -> None:
        del trainer
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    try:
        run_root.mkdir(parents=True)
        (run_root / "environment_manifest.json").write_text(
            json.dumps(environment, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        checkpoint_at = config["checkpoint_at_update"]
        total = config["total_updates"]

        # Phase A — uninterrupted 0 -> total (same save behavior so
        # the trajectories are structurally identical)
        _guard("uninterrupted run")
        trainer_a, accountant_a, trace_a, _ = run_training_segment(
            rows=rows, surface=loaded["surface"],
            run_dir=run_root / "uninterrupted", max_steps=total,
            save_at=checkpoint_at, identities=identities,
            run_id="resume-validation", segment_id="uninterrupted")
        final_a = _final_state(trainer_a, accountant_a, [trace_a],
                               rows)
        _release(trainer_a)

        # Phase B — interrupted 0 -> checkpoint_at, bundle written
        _guard("interrupted run")
        trainer_b, accountant_b, trace_b, boundary_b = \
            run_training_segment(
                rows=rows, surface=loaded["surface"],
                run_dir=run_root / "interrupted",
                max_steps=checkpoint_at, save_at=checkpoint_at,
                identities=identities, run_id="resume-validation",
                segment_id="interrupted")
        if boundary_b.record is None:
            raise InfrastructureError(
                "the interrupted run wrote no v1 bundle")
        _release(trainer_b)

        # Phase C — fail-closed resume from the bundle, then 3 -> 6
        _guard("resume run")
        bundle_dir = run_root / "interrupted" / "bundle"
        record = json.loads(
            (bundle_dir / "checkpoint_record.json").read_text("utf-8"))
        restored = ckpt.validate_resume(record, identities,
                                        bundle_dir=bundle_dir)
        accountant_c = ckpt.GroupAccountant.restore(
            restored["counters"])
        ckpt.restore_rng_state(restored["rng_state"])
        hf_checkpoint = run_root / "interrupted" / \
            f"checkpoint-{checkpoint_at}"
        trainer_c, accountant_c, trace_c, _ = run_training_segment(
            rows=rows, surface=loaded["surface"],
            run_dir=run_root / "resume", max_steps=total,
            save_at=None, identities=identities,
            run_id="resume-validation", segment_id="resume",
            resume_from=hf_checkpoint,
            start_group_index=restored["counters"]["consumed_groups"],
            accountant=accountant_c)
        final_c = _final_state(trainer_c, accountant_c,
                               [trace_b, trace_c], rows)
        _release(trainer_c)

        # §11 acceptance 3/4: merge the interrupted + resumed segments
        def _groups(path: Path) -> list[dict[str, Any]]:
            return [json.loads(line) for line in path.open()]
        merged = ckpt.merge_segments([
            {"segment_id": "interrupted", "run_id": "resume-validation",
             "config_sha256": CONFIG_SHA256, "status": "complete",
             "checkpoint_id": record["checkpoint_sha256"],
             "parent_checkpoint": None,
             "resume_from_consumed_groups": 0,
             "checkpoint_consumed_groups": checkpoint_at,
             "groups": _groups(trace_b)},
            {"segment_id": "resume", "run_id": "resume-validation",
             "config_sha256": CONFIG_SHA256, "status": "complete",
             "checkpoint_id": "final",
             "parent_checkpoint": record["checkpoint_sha256"],
             "resume_from_consumed_groups": checkpoint_at,
             "checkpoint_consumed_groups": total,
             "groups": _groups(trace_c)},
        ])
        comparison = compare_runs(final_a, final_c)
        validation = {
            "tranche": config["tranche"],
            "freeze_sha256": frozen["freeze_sha256"],
            "config_sha256": CONFIG_SHA256,
            "checkpoint_record_sha256": record["checkpoint_sha256"],
            "merged_groups": merged["merged_groups"],
            "comparison": comparison,
            "counters": final_c["counters"],
        }
        (run_root / "validation_record.json").write_text(
            json.dumps(validation, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    except BaseException as error:
        from .support_run import _hash_directory
        measured = round((time.monotonic() - started) / 3600.0, 4)
        append_ledger_entry(
            {"kind": "closeout", "question": frozen["question"],
             "motivating_evidence": "resume validation ABORTED",
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
             "outcome_informed": False,
             "outcome_pointer": str(run_root)},
            head, ledger_path)
        raise

    from .support_run import _hash_directory, _sha_file
    measured = round((time.monotonic() - started) / 3600.0, 4)
    closeout = append_ledger_entry(
        {"kind": "closeout", "question": frozen["question"],
         "motivating_evidence": "resume validation complete",
         "freeze": {
             "freeze_sha256": frozen["freeze_sha256"],
             "validation_record_file_sha256":
                 _sha_file(run_root / "validation_record.json"),
             "terminal_artifact_hashes": _hash_directory(run_root),
         },
         "parent": head, "budget_allocated_gpu_hours": 0.0,
         "budget_consumed_gpu_hours": measured,
         "closes_entry_sha256": head,
         "terminal_status": "complete",
         "outcome_informed": False,
         "outcome_pointer": str(run_root / "validation_record.json")},
        head, ledger_path)
    return {**validation, "measured_gpu_hours": measured,
            "launch_entry_sha256": head,
            "closeout_entry_sha256": closeout["entry_sha256"],
            "ledger_head": closeout["entry_sha256"]}


def run_training_segment(*, rows, surface, run_dir: Path,
                         max_steps: int, save_at: int | None,
                         identities, run_id: str, segment_id: str,
                         resume_from: Path | None = None,
                         start_group_index: int = 0,
                         accountant=None):
    """One training segment on the real stack. Returns (trainer,
    accountant, trace_path, boundary)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    accountant = accountant or ckpt.GroupAccountant()
    trace_path = run_dir / "actions.jsonl"
    group_size = RESUME_VALIDATION_CONFIG["grpo"]["group_size"]
    reward = make_validation_reward(surface, accountant, trace_path,
                                    group_size,
                                    start_group_index=start_group_index)
    boundary = _BoundaryCallback(
        accountant, (run_dir / "bundle") if save_at else None,
        identities, run_id, segment_id, groups_per_update=1)
    trainer = _build_trainer(rows, reward, run_dir, max_steps, save_at)
    trainer.add_callback(boundary.callback)
    if resume_from is not None:
        trainer.train(resume_from_checkpoint=str(resume_from))
    else:
        trainer.train()
    return trainer, accountant, trace_path, boundary
