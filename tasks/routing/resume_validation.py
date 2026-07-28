"""Step-5 GPU resume-validation tranche (211_f §11; rev3 per 235_s/237_s).

The infrastructure-acceptance run for the v1 checkpoint contract on
the REAL training stack: GRPOTrainer (NF4 + LoRA, the stage-0C
hyperparameter shape) training on the locked routing_dev support,
with checkpoints ONLY at the v1 boundary, a deliberate
post-checkpoint FAULT, and a full interrupted-vs-uninterrupted
comparison persisted for independent re-verification.

The 235_s repairs, all frozen here:

- BOTH arms are the same launch configuration (`max_steps` =
  total_updates); the interrupted arm is stopped by FAULT INJECTION
  at `fault_at_update`, not by a shorter horizon. Every model
  construction is preceded by a full reseed, and the three arms must
  prove IDENTICAL checkpoint-zero adapter hashes (gate 1).
- The resumed run consumes the VALIDATED state: the v1 bundle binds
  every HF checkpoint file by content hash, and the resume path
  re-hashes them AND semantically verifies that the HF adapter /
  optimizer / scheduler / RNG equal the bundle's before
  `resume_from_checkpoint` is allowed to consume them.
- The fault leaves ≥1 post-checkpoint group: the aborted segment's
  tail must be preserved, appear in `excluded_aborted_evidence`, and
  stay out of the merged trajectory (§11.3, now actually exercised).
- The schedule is LONGER than the update budget, so the
  next-sampler comparison is a real cursor, never `END`; traces
  carry completions, parsed actions and semantic assignments; the
  optimizer comparison includes parameter-group membership; final
  states are PERSISTED and `verify_resume_validation` re-derives the
  comparison from the archive alone.
- Launch requires the externally reviewed freeze hash; the deadline
  is checked before every optimizer step; `full_determinism` is ON;
  phase teardown moves snapshots to CPU, drops every trainer
  reference, and VERIFIES allocated VRAM returns below the frozen
  floor before the next phase.

Acceptance gates (all mechanical, all persisted):
  1. identical checkpoint-zero adapter hashes across arms;
  2. identical interrupted/uninterrupted bundles and trace prefixes
     at the checkpoint;
  3. ≥1 reward-varying generated group;
  4. a nonzero checkpoint-zero → checkpoint adapter update;
  5. the §11.5 comparison at the FROZEN tolerance (0.0 — exact).
"""

from __future__ import annotations

import hashlib
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
    "tranche": "routing-dev-resume-validation-v3",
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
    # 235_s F4: the schedule EXCEEDS the update budget so the
    # next-sampler cursor is real, never END
    "schedule_length": 8,
    "total_updates": 6,
    "checkpoint_at_update": 3,
    # 235_s F1/F3: the interrupted arm runs the SAME horizon and is
    # stopped by an injected fault AFTER a post-checkpoint group
    "fault_at_update": 4,
    # 235_s F7: determinism is part of the frozen claim
    "full_determinism": True,
    # 235_s F6: allocated VRAM must return below this before the
    # next phase constructs a trainer
    "release_max_allocated_mib": 1024,
    # 237_s F6: the charter's session preflight — free VRAM required
    # BEFORE ledger admission (an ollama-resident model refuses here)
    "min_free_vram_mib": 20000,
    # §11 acceptance: the comparison tolerance, frozen BEFORE the test
    "comparison_tolerance": 0.0,
    # 212_f reminder 2: the tranche's EXACT operational ceiling
    "ceiling_gpu_hours": 0.5,
    "run_root": "runs/routing-dev/resume-validation-v3",
}

CONFIG_SHA256 = content_sha256(RESUME_VALIDATION_CONFIG)


def tranche_freeze() -> dict[str, Any]:
    """The 211_f §1 lightweight freeze for this tranche."""
    from .charter import lightweight_freeze
    return lightweight_freeze({
        "kind": "resume_validation",
        "question": ("Does the v1 checkpoint contract hold on the real "
                     "GRPOTrainer stack — boundary-only checkpoints, "
                     "exact counter/RNG/sampler restoration, aborted "
                     "tails preserved-but-excluded, and an interrupted "
                     "run indistinguishable from an uninterrupted "
                     "one?"),
        "motivation": ("211_f §11 / §15 step 5; 232_s sequence item 2; "
                       "235_s repairs"),
        "config": RESUME_VALIDATION_CONFIG,
        "budget_gpu_hours":
            RESUME_VALIDATION_CONFIG["ceiling_gpu_hours"],
    })


class InjectedFault(RuntimeError):
    """The deliberate 235_s F3 post-checkpoint interruption."""


# --- dataset and reward (CPU-testable) ----------------------------------------

def load_locked_support(surface_dir: str | Path | None = None
                        ) -> dict[str, Any]:
    return load_dev_surface(
        surface_dir or RESUME_VALIDATION_CONFIG["surface_dir"],
        expected_lock_sha256=
        RESUME_VALIDATION_CONFIG["surface_lock_sha256"])


def training_schedule(loaded: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One row per potential optimizer update: the first
    `schedule_length` observations in canonical (sorted
    observation-id) order — deliberately more rows than updates
    (235_s F4). The schedule is part of the frozen identity."""
    from tasks.conductor import program
    from tasks.conductor.policy import policy_messages
    from tasks.conductor.profiles import DEFAULT_PROFILE
    from tasks.conductor.stage1 import prompt_fewshot
    length = RESUME_VALIDATION_CONFIG["schedule_length"]
    observations = sorted(loaded["observations"],
                          key=lambda obs: obs["observation_id"])
    if len(observations) < length:
        raise InfrastructureError(
            f"support has {len(observations)} observations; the "
            f"schedule needs {length}")
    system = prompt_fewshot()
    rows = []
    for obs in observations[:length]:
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
    """Authenticated reward + group accounting + FULL trace rows
    (completions, parsed actions, semantic assignments, rewards —
    235_s F4). One call per generation batch (= one group here)."""
    from tasks.conductor.grpo_task import positional_to_semantic
    from tasks.conductor.parser import ActionSchemaError, \
        parse_routing_action
    trace_path = Path(trace_path)
    state = {"group_index": start_group_index}

    def reward(completions: list[Any], *, observation_id: list[str],
               positions: list[str], num_steps: list[int],
               **_: Any) -> list[float]:
        if len(completions) % group_size != 0 or not completions:
            raise InfrastructureError(
                f"batch of {len(completions)} is not whole groups of "
                f"{group_size}")
        if len(set(observation_id)) != len(completions) // group_size:
            raise InfrastructureError(
                "group/observation alignment broken — a group must be "
                "one observation")
        rewards, texts, actions, assignments = [], [], [], []
        for completion, oid, positions_json, steps in zip(
                completions, observation_id, positions, num_steps):
            text = completion if isinstance(completion, str) else \
                completion[0].get("content", "")
            texts.append(text)
            try:
                action = parse_routing_action(text, steps)
            except ActionSchemaError:
                actions.append(None)
                assignments.append(None)
                rewards.append(0.0)
                continue
            semantic = tuple(positional_to_semantic(
                action, json.loads(positions_json)))
            payoff = surface.get((oid, semantic))
            if payoff is None:
                raise InfrastructureError(
                    f"({oid}, {semantic}): no surface row — an "
                    "infrastructure abort, never a reward")
            actions.append(list(action))
            assignments.append(list(semantic))
            rewards.append(float(payoff))
        groups = len(completions) // group_size
        accountant.record_generation(groups=groups,
                                     completions=len(completions))
        with trace_path.open("a", encoding="utf-8") as handle:
            for g in range(groups):
                lo, hi = g * group_size, (g + 1) * group_size
                handle.write(json.dumps({
                    "global_group_index": state["group_index"] + g,
                    "observation_id": observation_id[lo],
                    "completions": texts[lo:hi],
                    "actions": actions[lo:hi],
                    "assignments": assignments[lo:hi],
                    "rewards": rewards[lo:hi],
                }, sort_keys=True) + "\n")
        state["group_index"] += groups
        return rewards

    reward.state = state
    return reward


def read_trace(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(line)
            for line in Path(path).read_text("utf-8").splitlines()]


# --- hashing + comparison (CPU-testable) --------------------------------------

def _normalize_adapter_key(key: str) -> str:
    """239_s F3: map both PEFT save grammars onto one name — strip
    the base-model prefix and the adapter-name segment."""
    name = key
    if name.startswith("base_model.model."):
        name = name[len("base_model.model."):]
    return name.replace(".default.", ".")


def tensor_state_hashes(state: Mapping[str, Any]) -> dict[str, str]:
    """Order-stable content hashes of a tensor state dict (the
    checkpoint-zero identity gate)."""
    import torch
    hashes = {}
    for key in sorted(state):
        value = state[key]
        if isinstance(value, torch.Tensor):
            # .float() first: bf16 has no numpy dtype, and the fp32
            # embedding is exact, so equality of hashes is equality
            # of tensors
            hashes[key] = hashlib.sha256(
                value.detach().float().cpu().contiguous()
                .numpy().tobytes()).hexdigest()
        else:
            hashes[key] = content_sha256(value)
    return hashes


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
            fa = a.detach().float().cpu()
            fb = b.detach().float().cpu()
            # 237_s F5: NaN vs finite silently passes `> worst` — an
            # exact comparison requires FINITE tensors
            if a.numel() and not (torch.isfinite(fa).all()
                                  and torch.isfinite(fb).all()):
                raise InfrastructureError(
                    f"{label}: {key} contains non-finite values — "
                    "exact comparison refuses (237_s F5)")
            diff = (fa - fb).abs().max().item() if a.numel() else 0.0
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
    """235_s F4: INCLUDES parameter-group membership."""
    flat: dict[str, Any] = {}
    for pid, buffers in state.get("state", {}).items():
        for name, value in buffers.items():
            flat[f"state.{pid}.{name}"] = value
    for i, group in enumerate(state.get("param_groups", [])):
        for name, value in group.items():
            flat[f"group.{i}.{name}"] = value      # incl. "params"
    return flat


def compare_runs(final_a: Mapping[str, Any], final_b: Mapping[str, Any]
                 ) -> dict[str, Any]:
    """The full §11.5 comparison between the uninterrupted final state
    and the interrupted+resumed final state: adapter, optimizer
    (with group membership), scheduler, the REAL next-sampler cursor,
    counters, and the full merged trace sequence (observation ids +
    rewards per group)."""
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
    if final_a["next_sampler_identity"] == "END":
        raise InfrastructureError(
            "next-sampler comparison degenerated to END — the "
            "schedule must exceed the update budget (235_s F4)")
    if final_a["counters"] != final_b["counters"]:
        raise InfrastructureError(
            f"counters differ: {final_a['counters']} != "
            f"{final_b['counters']}")
    if final_a["trace_sequence"] != final_b["trace_sequence"]:
        raise InfrastructureError(
            "merged trace sequences differ (observation ids/rewards)")
    if final_a["trace_cardinality"] != final_b["trace_cardinality"]:
        raise InfrastructureError(
            f"merged trace cardinality differs: "
            f"{final_a['trace_cardinality']} != "
            f"{final_b['trace_cardinality']}")
    return {"tolerance": tolerance,
            "adapter_keys": len(final_a["adapter"]),
            "trace_groups": final_a["trace_cardinality"],
            "verdict": "PASS"}


def trace_sequence(groups: list[Mapping[str, Any]]) -> list[list[Any]]:
    """237_s F3: the FULL row content — completions, parsed actions
    and semantic assignments, not just ids and rewards."""
    return [[g["global_group_index"], g["observation_id"],
             g["completions"], g["actions"], g["assignments"],
             g["rewards"]] for g in groups]

# --- the GPU phases (exercised by the tranche run, not by CPU tests) ----------

def _seed_everything() -> None:
    """235_s F1: a full reseed precedes EVERY model construction so
    all arms draw identical LoRA initializations."""
    import random

    import numpy
    import torch
    seed = RESUME_VALIDATION_CONFIG["grpo"]["seed"]
    random.seed(seed)
    numpy.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# 239_s F2: the expected-environment binding must survive the
# freeze commit itself, so it hashes the manifest body EXCLUDING the
# commit-dependent fields (the same documentation-only set the
# runtime attestation exempts, plus the dirty-diff fields).
ENV_BINDING_EXEMPT_FIELDS = frozenset({
    "git_commit", "git_tree", "git_dirty", "git_diff_sha256",
    "execution_manifest_sha256",
})


def attested_environment_sha256(env: Mapping[str, Any]) -> str:
    return content_sha256({k: v for k, v in env.items()
                           if k not in ENV_BINDING_EXEMPT_FIELDS})


def gpu_session_preflight() -> dict[str, Any]:
    """237_s F6: the charter's session preflight, BEFORE admission —
    free VRAM must clear the frozen floor (an ollama-resident model
    or stray process refuses here). Persisted into the validation
    record."""
    import subprocess
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.free,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True).stdout.strip()
    free_mib, total_mib = (int(x.strip()) for x in out.split(","))
    floor = RESUME_VALIDATION_CONFIG["min_free_vram_mib"]
    record = {"free_mib": free_mib, "total_mib": total_mib,
              "floor_mib": floor}
    if free_mib < floor:
        raise InfrastructureError(
            f"session preflight: {free_mib} MiB free < {floor} MiB "
            "floor — resolve (ollama?) before admission (237_s F6)")
    return record


def static_identity_manifest(loaded: Mapping[str, Any],
                             rows: list[Mapping[str, Any]]
                             ) -> dict[str, Any]:
    """237_s F4: the REVIEWED execution identity — everything in
    `_identities` except the run-time environment (which is
    live-built and attested separately). The freeze document records
    this manifest's hash in full; admission requires it to
    recompute."""
    from .charter import routing_execution_digest
    digest = routing_execution_digest(
        "tasks/routing/resume_validation.py")
    lock = loaded["lock"]
    manifest = {
        "kind": "routing-dev-resume-validation-identity-v1",
        "routing_source_sha256": digest["routing_source_sha256"],
        "config_sha256": CONFIG_SHA256,
        "surface_manifest_sha256": lock["manifest_sha256"],
        "surface_lock_sha256": lock["lock_sha256"],
        "worker_pool_fingerprint": lock["worker_pool_fingerprint"],
        "cache_identity": lock["cache_identity"],
        "seed": str(RESUME_VALIDATION_CONFIG["grpo"]["seed"]),
        **schedule_identities(rows),
    }
    manifest["manifest_sha256"] = content_sha256(manifest)
    return manifest


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


def _build_trainer(rows, reward, run_dir: Path, save_at: int | None,
                   extra_callbacks=()):
    """One launch configuration for EVERY arm (235_s F1):
    max_steps = total_updates always; interruption is a fault, not a
    shorter horizon."""
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer, BitsAndBytesConfig
    from trl import GRPOConfig, GRPOTrainer
    config = RESUME_VALIDATION_CONFIG
    grpo = config["grpo"]
    _seed_everything()
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
        max_steps=config["total_updates"], loss_type=grpo["loss"],
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
        optim=grpo["optim"], report_to="none", logging_steps=1,
        save_strategy=("steps" if save_at else "no"),
        save_steps=(save_at or 0),
        save_only_model=False)
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
    for callback in extra_callbacks:
        trainer.add_callback(callback)
    return trainer


def _adapter_state(trainer) -> dict[str, Any]:
    return {name: value.detach().clone()
            for name, value in trainer.model.state_dict().items()
            if "lora" in name}


def _cpu_state(value):
    import torch
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, Mapping):
        return {k: _cpu_state(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_cpu_state(v) for v in value]
    return value


def _release_trainer(holder: dict) -> None:
    """235_s F6: drop the CALLER-HELD references, collect, and VERIFY
    allocated VRAM returned below the frozen floor."""
    import gc

    import torch
    holder.clear()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        allocated_mib = torch.cuda.memory_allocated() / 2 ** 20
        floor = RESUME_VALIDATION_CONFIG["release_max_allocated_mib"]
        if allocated_mib > floor:
            raise InfrastructureError(
                f"VRAM did not release: {allocated_mib:.0f} MiB "
                f"allocated > the frozen floor {floor} MiB — refusing "
                "to construct the next phase (235_s F6)")


class _DeadlineCallback:
    """235_s F7: the frozen ceiling is enforced before EVERY
    optimizer step (= every generation cycle here)."""

    def __init__(self, deadline_monotonic: float) -> None:
        from transformers import TrainerCallback

        class _Callback(TrainerCallback):
            def on_step_begin(self, args, state, control, **kw):
                if time.monotonic() > deadline_monotonic:
                    raise InfrastructureError(
                        "tranche ceiling reached before the next "
                        "update — aborting inside the frozen budget")
        self.callback = _Callback()


class _FaultInjector:
    """235_s F1/F3: the interrupted arm is stopped by a deliberate
    fault AFTER at least one post-checkpoint group exists."""

    def __init__(self, fault_at_update: int) -> None:
        from transformers import TrainerCallback

        class _Callback(TrainerCallback):
            def on_step_end(self, args, state, control, **kw):
                if state.global_step >= fault_at_update:
                    raise InjectedFault(
                        f"injected fault after update "
                        f"{state.global_step}")
        self.callback = _Callback()


def _hf_checkpoint_hashes(hf_dir: Path) -> dict[str, str]:
    return {str(path.relative_to(hf_dir)):
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(hf_dir.rglob("*")) if path.is_file()}


class _BoundaryCallback:
    """Counts consumed groups at optimizer steps and writes the v1
    contract bundle at the checkpoint step — binding the HF
    checkpoint files it shadows (235_s F2)."""

    def __init__(self, accountant, bundle_dir: Path | None,
                 identities: Mapping[str, str] | None,
                 run_id: str, segment_id: str,
                 hf_output_dir: Path | None,
                 checkpoint_at: int | None) -> None:
        from transformers import TrainerCallback

        outer = self

        class _Callback(TrainerCallback):
            def on_optimizer_step(self, args, state, control, **kw):
                outer.accountant.record_update(consumed_groups=1)

            def on_save(self, args, state, control, **kw):
                if outer.bundle_dir is None:
                    return
                # 237_s F1: HF saves at EVERY save_steps multiple
                # (updates 3 AND 6 here) — the bundle is written at
                # the checkpoint step only, exactly once
                if state.global_step != outer.checkpoint_at:
                    return
                if outer.record is not None:
                    raise InfrastructureError(
                        "a second bundle write at the checkpoint "
                        "step — the v1 bundle is written exactly "
                        "once (237_s F1)")
                outer.write_bundle(kw["model"], kw.get("optimizer"),
                                   kw.get("lr_scheduler"), state)

        self.accountant = accountant
        self.bundle_dir = bundle_dir
        self.identities = dict(identities or {})
        self.run_id = run_id
        self.segment_id = segment_id
        self.hf_output_dir = hf_output_dir
        self.checkpoint_at = checkpoint_at
        self.callback = _Callback()
        self.record = None

    def write_bundle(self, model, optimizer, scheduler, state) -> None:
        import torch
        from safetensors.torch import save_file
        bundle = self.bundle_dir
        bundle.mkdir(parents=True, exist_ok=True)
        counters = self.accountant.authorize_checkpoint()
        save_file({k: v.detach().to("cpu").contiguous()
                   for k, v in model.state_dict().items()
                   if "lora" in k},
                  str(bundle /
                      ckpt.CHECKPOINT_BUNDLE_FILENAMES["adapter"]))
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
        hf_dir = self.hf_output_dir / \
            f"checkpoint-{self.checkpoint_at}"
        if not hf_dir.exists():
            raise InfrastructureError(
                f"{hf_dir} absent at on_save — the bundle cannot bind "
                "the HF checkpoint (235_s F2)")
        self.record = ckpt.build_checkpoint_record(
            identities=self.identities, counters=counters,
            rng_state=rng_state, state_artifact_hashes=hashes,
            sampler_position={
                "next_global_group_index": counters["consumed_groups"],
                "hf_global_step": state.global_step,
                "hf_checkpoint_dir": str(hf_dir),
                "hf_checkpoint_sha256": _hf_checkpoint_hashes(hf_dir),
            },
            run_id=self.run_id, segment_id=self.segment_id,
            parent_checkpoint=None)
        (bundle / "checkpoint_record.json").write_text(
            json.dumps(self.record, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")


def verify_hf_checkpoint_against_bundle(bundle_dir: str | Path,
                                        hf_dir: str | Path,
                                        record: Mapping[str, Any]
                                        ) -> None:
    """235_s F2: the resume may only consume an HF checkpoint whose
    every file re-hashes to the bundle's binding AND whose adapter /
    optimizer / scheduler / RNG semantically equal the validated
    bundle state."""
    import torch
    from safetensors.torch import load_file
    bundle_dir, hf_dir = Path(bundle_dir), Path(hf_dir)
    bound = record["sampler_position"]["hf_checkpoint_sha256"]
    actual = _hf_checkpoint_hashes(hf_dir)
    if actual != dict(bound):
        missing = sorted(set(bound) - set(actual))
        extra = sorted(set(actual) - set(bound))
        altered = sorted(k for k in set(bound) & set(actual)
                         if bound[k] != actual[k])
        raise InfrastructureError(
            f"HF checkpoint does not match the bundle binding: "
            f"missing {missing[:3]}, extra {extra[:3]}, altered "
            f"{altered[:3]} (235_s F2)")
    tolerance = RESUME_VALIDATION_CONFIG["comparison_tolerance"]
    bundle_adapter = load_file(
        str(bundle_dir / ckpt.CHECKPOINT_BUNDLE_FILENAMES["adapter"]))
    hf_adapter_path = hf_dir / "adapter_model.safetensors"
    # 239_s F3: the adapter file is REQUIRED — a missing file is a
    # malformed archive, never a skip
    if not hf_adapter_path.exists():
        raise InfrastructureError(
            "HF checkpoint lacks adapter_model.safetensors — refusing "
            "the malformed archive (239_s F3)")
    hf_adapter = load_file(str(hf_adapter_path))
    # 239_s F3: compare PER-TENSOR through NORMALIZED names (the PEFT
    # save format drops the adapter-name segment and may add the
    # base_model prefix) — never an unordered multiset
    normalized_bundle = {_normalize_adapter_key(k): v
                         for k, v in bundle_adapter.items()}
    normalized_hf = {_normalize_adapter_key(k): v
                     for k, v in hf_adapter.items()}
    if len(normalized_bundle) != len(bundle_adapter) \
            or len(normalized_hf) != len(hf_adapter):
        raise InfrastructureError(
            "adapter key normalization collided — the name grammars "
            "need review (239_s F3)")
    compare_tensor_states(normalized_bundle, normalized_hf,
                          tolerance, "hf-vs-bundle adapter")
    bundle_optimizer = torch.load(
        bundle_dir / ckpt.CHECKPOINT_BUNDLE_FILENAMES["optimizer"],
        weights_only=False)
    hf_optimizer = torch.load(hf_dir / "optimizer.pt",
                              weights_only=False)
    compare_tensor_states(_flatten_optimizer_state(bundle_optimizer),
                          _flatten_optimizer_state(hf_optimizer),
                          tolerance, "hf-vs-bundle optimizer")
    bundle_scheduler = torch.load(
        bundle_dir / ckpt.CHECKPOINT_BUNDLE_FILENAMES["scheduler"],
        weights_only=False)
    hf_scheduler = torch.load(hf_dir / "scheduler.pt",
                              weights_only=False)
    if bundle_scheduler != hf_scheduler:
        raise InfrastructureError(
            "HF scheduler state does not equal the validated bundle "
            "scheduler (235_s F2)")
    rng_json = json.loads(
        (bundle_dir / ckpt.CHECKPOINT_BUNDLE_FILENAMES["rng"])
        .read_text("utf-8"))
    hf_rng = torch.load(hf_dir / "rng_state.pth", weights_only=False)
    if hf_rng["cpu"].tolist() != rng_json["torch_cpu"]:
        raise InfrastructureError(
            "HF torch-CPU RNG state does not equal the validated "
            "bundle RNG (235_s F2)")
    if rng_json["torch_cuda"] is not None:
        # 237_s F2: on the frozen single-GPU runtime HF stores ONE
        # tensor, not a list — normalize before comparing; the stream
        # is REQUIRED when the bundle has it (239_s F3)
        hf_cuda = hf_rng.get("cuda")
        if hf_cuda is None:
            raise InfrastructureError(
                "HF rng_state.pth lacks the cuda stream (239_s F3)")
        if isinstance(hf_cuda, torch.Tensor):
            hf_cuda_lists = [hf_cuda.tolist()]
        elif hf_cuda is not None:
            hf_cuda_lists = [s.tolist() for s in hf_cuda]
        else:
            hf_cuda_lists = None
        if hf_cuda_lists != rng_json["torch_cuda"]:
            raise InfrastructureError(
                "HF CUDA RNG state does not equal the validated "
                "bundle RNG (235_s F2)")
    # 237_s F2 / 239_s F3: HF restores python and numpy RNG too —
    # ALL streams are REQUIRED, never conditionally skipped
    hf_python = hf_rng.get("python")
    bundle_python = rng_json["python"]
    if hf_python is None:
        raise InfrastructureError(
            "HF rng_state.pth lacks the python stream (239_s F3)")
    if True:
        version, internal, gauss = (hf_python[0],
                                    list(hf_python[1]),
                                    hf_python[2])
        if version != bundle_python["version"] \
                or internal != bundle_python["internal_state"] \
                or gauss != bundle_python["gauss_next"]:
            raise InfrastructureError(
                "HF python RNG state does not equal the validated "
                "bundle RNG (237_s F2)")
    hf_numpy = hf_rng.get("numpy")
    bundle_numpy = rng_json["numpy"]
    if hf_numpy is None:
        raise InfrastructureError(
            "HF rng_state.pth lacks the numpy stream (239_s F3)")
    if True:
        name, keys, pos, has_gauss, cached = hf_numpy
        keys_list = keys.tolist() if hasattr(keys, "tolist") \
            else list(keys)
        if name != bundle_numpy["name"] \
                or keys_list != bundle_numpy["keys"] \
                or int(pos) != bundle_numpy["pos"] \
                or int(has_gauss) != bundle_numpy["has_gauss"] \
                or float(cached) != bundle_numpy["cached_gaussian"]:
            raise InfrastructureError(
                "HF numpy RNG state does not equal the validated "
                "bundle RNG (237_s F2)")

def run_training_segment(*, rows, surface, run_dir: Path,
                         save_at: int | None, identities,
                         run_id: str, segment_id: str,
                         deadline_monotonic: float,
                         fault_at: int | None = None,
                         resume_from: Path | None = None,
                         start_group_index: int = 0,
                         accountant=None) -> dict[str, Any]:
    """One training segment on the real stack, returning CPU-side
    results only (235_s F6): the trainer is torn down and VRAM
    verified released before returning."""
    run_dir.mkdir(parents=True, exist_ok=True)
    accountant = accountant or ckpt.GroupAccountant()
    trace_path = run_dir / "actions.jsonl"
    group_size = RESUME_VALIDATION_CONFIG["grpo"]["group_size"]
    reward = make_validation_reward(surface, accountant, trace_path,
                                    group_size,
                                    start_group_index=start_group_index)
    boundary = _BoundaryCallback(
        accountant, (run_dir / "bundle") if save_at else None,
        identities, run_id, segment_id, hf_output_dir=run_dir,
        checkpoint_at=save_at)
    callbacks = [boundary.callback,
                 _DeadlineCallback(deadline_monotonic).callback]
    if fault_at is not None:
        callbacks.append(_FaultInjector(fault_at).callback)
    holder = {"trainer": _build_trainer(rows, reward, run_dir,
                                        save_at, callbacks)}
    trainer = holder["trainer"]
    checkpoint_zero = tensor_state_hashes(_adapter_state(trainer))
    faulted = False
    try:
        if resume_from is not None:
            trainer.train(resume_from_checkpoint=str(resume_from))
        else:
            trainer.train()
    except InjectedFault:
        faulted = True
        if fault_at is None:
            raise
    if fault_at is not None and not faulted:
        raise InfrastructureError(
            "the injected fault never fired — the interrupted arm "
            "completed (235_s F3)")
    final = {
        "adapter": _cpu_state(_adapter_state(trainer)),
        "optimizer": _cpu_state(trainer.optimizer.state_dict()),
        "scheduler": _cpu_state(trainer.lr_scheduler.state_dict()),
    }
    del trainer
    _release_trainer(holder)
    return {"final": final, "accountant": accountant,
            "trace_path": trace_path, "boundary": boundary,
            "checkpoint_zero": checkpoint_zero, "faulted": faulted}


def _final_state(final: Mapping[str, Any], accountant, rows,
                 merged_groups: list[Mapping[str, Any]]
                 ) -> dict[str, Any]:
    consumed = accountant.consumed_groups
    # 237_s F6: the actual trace observation ids must BE the frozen
    # schedule prefix before the next-sampler cursor means anything
    for i, group in enumerate(merged_groups):
        if group["observation_id"] != rows[i]["observation_id"] \
                or group["global_group_index"] != i:
            raise InfrastructureError(
                f"trace group {i} is "
                f"{group['observation_id']} (index "
                f"{group['global_group_index']}), not the frozen "
                f"schedule row {rows[i]['observation_id']} "
                "(237_s F6)")
    next_row = (rows[consumed]["observation_id"]
                if consumed < len(rows) else "END")
    return {
        **final,
        "next_sampler_identity": next_row,
        "counters": {"generated_groups": accountant.generated_groups,
                     "consumed_groups": accountant.consumed_groups,
                     "optimizer_updates": accountant.optimizer_updates,
                     "sampled_completions":
                         accountant.sampled_completions},
        "trace_sequence": trace_sequence(merged_groups),
        "trace_cardinality": len(merged_groups),
    }


def _persist_final(run_root: Path, name: str,
                   final: Mapping[str, Any]) -> dict[str, str]:
    """235_s F4: final states are persisted for the independent
    verifier."""
    import torch
    from safetensors.torch import save_file
    out = run_root / name
    out.mkdir(parents=True, exist_ok=True)
    save_file({k: v.contiguous() for k, v in final["adapter"].items()},
              str(out / "adapter.safetensors"))
    torch.save(final["optimizer"], out / "optimizer.pt")
    torch.save(final["scheduler"], out / "scheduler.pt")
    (out / "cursor.json").write_text(json.dumps({
        "next_sampler_identity": final["next_sampler_identity"],
        "counters": final["counters"],
        "trace_cardinality": final["trace_cardinality"],
        "trace_sequence": final["trace_sequence"],
    }, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {str(p.relative_to(out)):
            hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(out.iterdir())}


def _load_final(run_root: Path, name: str) -> dict[str, Any]:
    import torch
    from safetensors.torch import load_file
    out = run_root / name
    cursor = json.loads((out / "cursor.json").read_text("utf-8"))
    return {
        "adapter": load_file(str(out / "adapter.safetensors")),
        "optimizer": torch.load(out / "optimizer.pt",
                                weights_only=False),
        "scheduler": torch.load(out / "scheduler.pt",
                                weights_only=False),
        **cursor,
    }


def verify_resume_validation(run_root: str | Path) -> dict[str, Any]:
    """The independent verifier (235_s F4, strengthened per 237_s F3):
    from the archive ALONE it re-hashes the persisted final states,
    revalidates the bundle files and the consumed HF checkpoint,
    rederives checkpoint-zero/checkpoint equality gates from
    persisted hash maps and the bundle adapter, re-checks the A/B
    prefix equality, rederives the merge and the §11.5 comparison
    over FULL traces, and requires the persisted validation record to
    match everything exactly."""
    from .support_run import _sha_file
    run_root = Path(run_root)
    record = json.loads(
        (run_root / "validation_record.json").read_text("utf-8"))
    bundle_b = run_root / "interrupted" / "bundle"
    bundle_record = json.loads(
        (bundle_b / "checkpoint_record.json").read_text("utf-8"))
    body = {k: v for k, v in bundle_record.items()
            if k != "checkpoint_sha256"}
    if content_sha256(body) != bundle_record["checkpoint_sha256"]:
        raise InfrastructureError("bundle record does not rehash")
    if record["checkpoint_record_sha256"] != \
            bundle_record["checkpoint_sha256"]:
        raise InfrastructureError(
            "validation record is not bound to this bundle record "
            "(237_s F3)")
    # bundle state files re-hash against the record, and the RNG
    # artifact cross-binds
    filenames = {name: (ckpt.CHECKPOINT_BUNDLE_FILENAMES[name]
                        if bundle_record["state_artifact_sha256"]
                        .get(name) is not None else None)
                 for name in ckpt.REQUIRED_STATE_ARTIFACTS
                 + ckpt.OPTIONAL_STATE_ARTIFACTS}
    if ckpt.hash_state_artifacts(bundle_b, filenames) != \
            bundle_record["state_artifact_sha256"]:
        raise InfrastructureError(
            "bundle state files do not match the record (237_s F3)")
    rng_state = json.loads(
        (bundle_b / ckpt.CHECKPOINT_BUNDLE_FILENAMES["rng"])
        .read_text("utf-8"))
    if content_sha256(rng_state) != bundle_record["rng_state_sha256"]:
        raise InfrastructureError(
            "bundle RNG artifact does not cross-bind (237_s F3)")
    # the consumed HF checkpoint revalidates against the bundle
    hf_dir = Path(
        bundle_record["sampler_position"]["hf_checkpoint_dir"])
    if not hf_dir.is_absolute():
        candidate = run_root / "interrupted" / hf_dir.name
        hf_dir = candidate if candidate.exists() else hf_dir
    verify_hf_checkpoint_against_bundle(bundle_b, hf_dir,
                                        bundle_record)
    # persisted final states re-hash against the record
    for name, key in (("final_uninterrupted", "uninterrupted"),
                      ("final_resumed", "resumed")):
        out = run_root / name
        actual = {str(p.relative_to(out)): _sha_file(p)
                  for p in sorted(out.iterdir())}
        if actual != record["final_state_sha256"][key]:
            raise InfrastructureError(
                f"{name} files do not match final_state_sha256 "
                "(237_s F3)")
    checkpoint_at = RESUME_VALIDATION_CONFIG["checkpoint_at_update"]
    total = RESUME_VALIDATION_CONFIG["total_updates"]
    trace_a = read_trace(run_root / "uninterrupted" / "actions.jsonl")
    trace_b = read_trace(run_root / "interrupted" / "actions.jsonl")
    trace_c = read_trace(run_root / "resume" / "actions.jsonl")
    # A/B checkpoint-prefix equality and bundle equality rederive
    if trace_sequence(trace_a[:checkpoint_at]) != \
            trace_sequence(trace_b[:checkpoint_at]):
        raise InfrastructureError(
            "A/B pre-checkpoint traces differ (gate 2; 237_s F3)")
    bundle_a = run_root / "uninterrupted" / "bundle"
    for name in ("adapter", "optimizer", "scheduler", "rng"):
        filename = ckpt.CHECKPOINT_BUNDLE_FILENAMES[name]
        if _sha_file(bundle_a / filename) != \
                _sha_file(bundle_b / filename):
            raise InfrastructureError(
                f"A/B checkpoint {name} differs (gate 2; 237_s F3)")
    # 239_s F2: archived environment + preflight cross-check
    archived_env = json.loads(
        (run_root / "environment_manifest.json").read_text("utf-8"))
    from .dev_support import validate_env_self_hash
    if validate_env_self_hash(archived_env) != \
            record["environment_manifest_sha256"]:
        raise InfrastructureError(
            "archived environment does not match the record "
            "(239_s F2)")
    if attested_environment_sha256(archived_env) != \
            record["attested_environment_sha256"]:
        raise InfrastructureError(
            "archived environment does not match the reviewed "
            "attested binding (239_s F2)")
    preflight = json.loads(
        (run_root / "session_preflight.json").read_text("utf-8"))
    if content_sha256(preflight) != \
            record["session_preflight_sha256"] \
            or record["session_preflight"] != preflight:
        raise InfrastructureError(
            "archived session preflight does not match the record "
            "(239_s F2)")
    # 239_s F1: the identity manifest re-validates, and the schedule
    # list binds to its cohort identity
    identity_manifest = json.loads(
        (run_root / "identity_manifest.json").read_text("utf-8"))
    identity_body = {k: v for k, v in identity_manifest.items()
                     if k != "manifest_sha256"}
    if content_sha256(identity_body) != \
            identity_manifest["manifest_sha256"] \
            or identity_manifest["manifest_sha256"] != \
            record["identity_manifest_sha256"]:
        raise InfrastructureError(
            "archived identity manifest does not rehash or does not "
            "match the record (239_s F1)")
    if bundle_record["identities"]["config_sha256"] != CONFIG_SHA256 \
            or bundle_record["identities"]["training_cohort_sha256"] \
            != identity_manifest["training_cohort_sha256"]:
        raise InfrastructureError(
            "bundle identities do not match the archived identity "
            "manifest (239_s F1)")
    schedule = json.loads(
        (run_root / "schedule.json").read_text("utf-8"))
    if content_sha256(schedule) != \
            identity_manifest["training_cohort_sha256"]:
        raise InfrastructureError(
            "archived schedule does not hash to the identity "
            "manifest's cohort (239_s F1)")
    # 239_s F1: PER-ARM checkpoint-zero equality rederives
    zero_maps = json.loads(
        (run_root / "checkpoint_zero_hashes.json").read_text("utf-8"))
    if set(zero_maps) != {"uninterrupted", "interrupted", "resumed"}:
        raise InfrastructureError(
            "checkpoint-zero maps must cover all three arms "
            "(239_s F1)")
    if not (zero_maps["uninterrupted"] == zero_maps["interrupted"]
            == zero_maps["resumed"]):
        raise InfrastructureError(
            "checkpoint-zero adapters differ across arms — gate 1 "
            "fails on rederivation (239_s F1)")
    zero_map = zero_maps["interrupted"]
    if content_sha256(zero_map) != \
            record["checkpoint_zero_adapter_sha256"]:
        raise InfrastructureError(
            "checkpoint-zero hash map does not match the record "
            "(gate 1; 237_s F3)")
    from safetensors.torch import load_file
    bundle_adapter_hashes = tensor_state_hashes(load_file(
        str(bundle_b / ckpt.CHECKPOINT_BUNDLE_FILENAMES["adapter"])))
    if content_sha256(bundle_adapter_hashes) != \
            record["checkpoint_adapter_sha256"]:
        raise InfrastructureError(
            "bundle adapter does not rederive "
            "checkpoint_adapter_sha256 (237_s F3)")
    if record["checkpoint_zero_adapter_sha256"] == \
            record["checkpoint_adapter_sha256"]:
        raise InfrastructureError(
            "checkpoint-zero equals checkpoint adapter — gate 4 "
            "fails (zero-gradient trajectory)")
    merged = ckpt.merge_segments([
        {"segment_id": "interrupted", "run_id": "resume-validation",
         "config_sha256": CONFIG_SHA256, "status": "aborted",
         "checkpoint_id": bundle_record["checkpoint_sha256"],
         "parent_checkpoint": None,
         "resume_from_consumed_groups": 0,
         "checkpoint_consumed_groups": checkpoint_at,
         "groups": trace_b},
        {"segment_id": "resume", "run_id": "resume-validation",
         "config_sha256": CONFIG_SHA256, "status": "complete",
         "checkpoint_id": "final",
         "parent_checkpoint": bundle_record["checkpoint_sha256"],
         "resume_from_consumed_groups": checkpoint_at,
         "checkpoint_consumed_groups": total,
         "groups": trace_c},
    ])
    if len(merged["excluded_aborted_evidence"]) < 1:
        raise InfrastructureError(
            "no aborted tail was preserved — §11.3 untested")
    if merged["merged_groups"] != total:
        raise InfrastructureError(
            f"merged trajectory has {merged['merged_groups']} groups; "
            f"expected {total}")
    final_a = _load_final(run_root, "final_uninterrupted")
    final_c = _load_final(run_root, "final_resumed")
    comparison = compare_runs(final_a, final_c)
    # the persisted cursors must equal the FULL traces on disk
    if final_a["trace_sequence"] != trace_sequence(trace_a):
        raise InfrastructureError(
            "persisted uninterrupted cursor does not match its trace")
    if final_c["trace_sequence"] != trace_sequence(
            merged["trajectory"]):
        raise InfrastructureError(
            "persisted resumed cursor does not match the merged "
            "trajectory")
    # 239_s F1: counters, cardinality and the next cursor rederive
    # from the frozen config and the archived schedule — never taken
    # from arbitrary-but-equal cursor files
    group_size = RESUME_VALIDATION_CONFIG["grpo"]["group_size"]
    expected_counters = {
        "generated_groups": total, "consumed_groups": total,
        "optimizer_updates": total,
        "sampled_completions": total * group_size}
    for label, final in (("uninterrupted", final_a),
                         ("resumed", final_c)):
        if final["counters"] != expected_counters:
            raise InfrastructureError(
                f"{label} counters {final['counters']} != the "
                f"schedule-derived expectation {expected_counters} "
                "(239_s F1)")
        if final["trace_cardinality"] != total:
            raise InfrastructureError(
                f"{label} trace cardinality != {total} (239_s F1)")
        if final["next_sampler_identity"] != schedule[total]:
            raise InfrastructureError(
                f"{label} next cursor is not the schedule's row "
                f"{total} (239_s F1)")
    if record["counters"] != expected_counters:
        raise InfrastructureError(
            "validation record counters do not rederive (239_s F1)")
    for i, group in enumerate(trace_a):
        if group["observation_id"] != schedule[i]:
            raise InfrastructureError(
                f"uninterrupted trace group {i} is not schedule row "
                f"{i} (239_s F1)")
    for i, group in enumerate(merged["trajectory"]):
        if group["observation_id"] != schedule[i]:
            raise InfrastructureError(
                f"merged trace group {i} is not schedule row {i} "
                "(239_s F1)")
    varying = [g for g in trace_a if len(set(g["rewards"])) > 1]
    if not varying:
        raise InfrastructureError(
            "no reward-varying group — gate 3 fails (235_s)")
    rederived = {
        "comparison": comparison,
        "merged_groups": merged["merged_groups"],
        "excluded_tail_groups":
            [g["global_group_index"]
             for g in merged["excluded_aborted_evidence"]],
        "reward_varying_groups":
            [g["global_group_index"] for g in varying],
    }
    for key, value in rederived.items():
        if record.get(key) != value:
            raise InfrastructureError(
                f"validation record field {key} does not rederive: "
                f"{record.get(key)!r} != {value!r}")
    return {"verdict": "PASS", **rederived}


def execute_resume_validation(*, expected_freeze_sha256: str,
                              expected_identity_sha256: str,
                              expected_environment_sha256: str,
                              expected_head_sha256: str,
                              ledger_path: str | Path | None = None,
                              _environment_builder=None
                              ) -> dict[str, Any]:
    """The full Step-5 tranche. Requires the EXTERNALLY REVIEWED
    freeze hash (235_s F5) AND the reviewed static execution-identity
    manifest hash (237_s F4 — prompt/source/cohort/renderer/surface
    identities, so a code or prompt change after review refuses);
    runs the charter session preflight BEFORE admission (237_s F6);
    admits, runs the three arms, applies the gates, persists
    everything, verifies its own archive, and closes out (aborted
    with measured cost on any post-admission failure)."""
    from .ledger import LEDGER_PATH, admit_and_append_launch, \
        append_ledger_entry
    from .support_run import _hash_directory, _sha_file
    ledger_path = ledger_path or LEDGER_PATH
    config = RESUME_VALIDATION_CONFIG
    frozen = tranche_freeze()
    if frozen["freeze_sha256"] != expected_freeze_sha256:
        raise InfrastructureError(
            "the reconstructed freeze is not the externally reviewed "
            "one — the code or config moved after review (235_s F5)")
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
    identity_manifest = static_identity_manifest(loaded, rows)
    if identity_manifest["manifest_sha256"] != expected_identity_sha256:
        raise InfrastructureError(
            "the execution identity is not the reviewed one — "
            "prompt/source/cohort/renderer/surface identities moved "
            "after review (237_s F4)")
    # 239_s F2: the reviewed freeze also binds the environment (the
    # commit-independent attested body)
    if attested_environment_sha256(environment) != \
            expected_environment_sha256:
        raise InfrastructureError(
            "the live environment is not the reviewed one — "
            "uv.lock/torch/CUDA/GPU stack moved after review "
            "(239_s F2)")
    identities = _identities(loaded, rows, env_sha)
    preflight = gpu_session_preflight()
    preflight_sha = content_sha256(preflight)
    run_root = Path(config["run_root"])
    if run_root.exists():
        raise InfrastructureError(
            f"{run_root} exists; the tranche runs exactly once")
    # 239_s F2: the prelaunch evidence persists BEFORE admission, so
    # an admitted abort cannot lose it (the abort inventory covers it)
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

    entry = {
        "kind": "resume_validation",
        "question": frozen["question"],
        "motivating_evidence": "240_f rev4 freeze; 232_s item 2",
        "freeze": {"freeze_sha256": frozen["freeze_sha256"],
                   "config_sha256": CONFIG_SHA256,
                   "identity_manifest_sha256":
                       identity_manifest["manifest_sha256"],
                   # 239_s F2: environment + preflight bound at
                   # admission
                   "environment_manifest_sha256": env_sha,
                   "attested_environment_sha256":
                       expected_environment_sha256,
                   "session_preflight_sha256": preflight_sha},
        "parent": None,
        "budget_allocated_gpu_hours": config["ceiling_gpu_hours"],
        "outcome_informed": False,
    }
    admitted = admit_and_append_launch(entry, expected_head_sha256,
                                       ledger_path)
    head = admitted["entry_sha256"]
    started = time.monotonic()
    deadline = started + config["ceiling_gpu_hours"] * 3600.0

    try:
        # prelaunch evidence already persisted pre-admission
        checkpoint_at = config["checkpoint_at_update"]
        total = config["total_updates"]
        surface = loaded["surface"]

        # Phase A — uninterrupted (saves at 3 for structural identity)
        segment_a = run_training_segment(
            rows=rows, surface=surface,
            run_dir=run_root / "uninterrupted",
            save_at=checkpoint_at, identities=identities,
            run_id="resume-validation", segment_id="uninterrupted",
            deadline_monotonic=deadline)

        # Phase B — interrupted by the injected fault AFTER a
        # post-checkpoint group
        segment_b = run_training_segment(
            rows=rows, surface=surface,
            run_dir=run_root / "interrupted",
            save_at=checkpoint_at, identities=identities,
            run_id="resume-validation", segment_id="interrupted",
            deadline_monotonic=deadline,
            fault_at=config["fault_at_update"])
        if segment_b["boundary"].record is None:
            raise InfrastructureError(
                "the interrupted run wrote no v1 bundle")
        record = segment_b["boundary"].record

        # Gate 1 — identical checkpoint-zero adapters
        if segment_a["checkpoint_zero"] != segment_b["checkpoint_zero"]:
            raise InfrastructureError(
                "checkpoint-zero adapters differ between arms "
                "(gate 1; 235_s F1)")
        # Gate 2 — identical states + trace prefixes at checkpoint 3
        bundle_a = run_root / "uninterrupted" / "bundle"
        bundle_b = run_root / "interrupted" / "bundle"
        for name in ("adapter", "optimizer", "scheduler", "rng"):
            filename = ckpt.CHECKPOINT_BUNDLE_FILENAMES[name]
            if _sha_file(bundle_a / filename) != \
                    _sha_file(bundle_b / filename):
                raise InfrastructureError(
                    f"checkpoint-3 {name} differs between arms "
                    "(gate 2; 235_s)")
        trace_a_rows = read_trace(segment_a["trace_path"])
        trace_b_rows = read_trace(segment_b["trace_path"])
        if trace_sequence(trace_a_rows[:checkpoint_at]) != \
                trace_sequence(trace_b_rows[:checkpoint_at]):
            raise InfrastructureError(
                "pre-checkpoint traces differ between arms (gate 2)")
        # Gates 3 + 4
        varying = [g for g in trace_a_rows
                   if len(set(g["rewards"])) > 1]
        if not varying:
            raise InfrastructureError(
                "no reward-varying group — the optimizer was never "
                "meaningfully exercised (gate 3; 235_s)")
        checkpoint_adapter_hashes = tensor_state_hashes(
            __import__("safetensors.torch", fromlist=["load_file"])
            .load_file(str(bundle_b / ckpt.CHECKPOINT_BUNDLE_FILENAMES[
                "adapter"])))
        zero_sha = content_sha256(segment_b["checkpoint_zero"])
        checkpoint_sha = content_sha256(checkpoint_adapter_hashes)
        if zero_sha == checkpoint_sha:
            raise InfrastructureError(
                "checkpoint-3 adapter equals checkpoint-zero — a "
                "zero-gradient trajectory proves nothing (gate 4)")

        # Phase C — fail-closed resume from the VALIDATED state
        restored = ckpt.validate_resume(record, identities,
                                        bundle_dir=bundle_b)
        hf_checkpoint = Path(
            record["sampler_position"]["hf_checkpoint_dir"])
        verify_hf_checkpoint_against_bundle(bundle_b, hf_checkpoint,
                                            record)
        accountant_c = ckpt.GroupAccountant.restore(
            restored["counters"])
        ckpt.restore_rng_state(restored["rng_state"])
        segment_c = run_training_segment(
            rows=rows, surface=surface, run_dir=run_root / "resume",
            save_at=None, identities=identities,
            run_id="resume-validation", segment_id="resume",
            deadline_monotonic=deadline, resume_from=hf_checkpoint,
            start_group_index=restored["counters"]["consumed_groups"],
            accountant=accountant_c)
        if segment_c["checkpoint_zero"] != segment_a["checkpoint_zero"]:
            raise InfrastructureError(
                "checkpoint-zero adapters differ for the resumed arm "
                "(gate 1)")
        # 239_s F1: PER-ARM zero maps persist so the verifier can
        # rederive A/B/C equality itself
        (run_root / "checkpoint_zero_hashes.json").write_text(
            json.dumps({"uninterrupted": segment_a["checkpoint_zero"],
                        "interrupted": segment_b["checkpoint_zero"],
                        "resumed": segment_c["checkpoint_zero"]},
                       indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        trace_c_rows = read_trace(segment_c["trace_path"])

        # §11.3/4 — merge with the aborted tail excluded-but-preserved
        merged = ckpt.merge_segments([
            {"segment_id": "interrupted",
             "run_id": "resume-validation",
             "config_sha256": CONFIG_SHA256, "status": "aborted",
             "checkpoint_id": record["checkpoint_sha256"],
             "parent_checkpoint": None,
             "resume_from_consumed_groups": 0,
             "checkpoint_consumed_groups": checkpoint_at,
             "groups": trace_b_rows},
            {"segment_id": "resume", "run_id": "resume-validation",
             "config_sha256": CONFIG_SHA256, "status": "complete",
             "checkpoint_id": "final",
             "parent_checkpoint": record["checkpoint_sha256"],
             "resume_from_consumed_groups": checkpoint_at,
             "checkpoint_consumed_groups": total,
             "groups": trace_c_rows},
        ])
        if len(merged["excluded_aborted_evidence"]) < 1:
            raise InfrastructureError(
                "the fault produced no post-checkpoint tail — §11.3 "
                "is untested (235_s F3)")

        final_a = _final_state(segment_a["final"],
                               segment_a["accountant"], rows,
                               trace_a_rows)
        final_c = _final_state(segment_c["final"],
                               segment_c["accountant"], rows,
                               merged["trajectory"])
        comparison = compare_runs(final_a, final_c)
        hashes_a = _persist_final(run_root, "final_uninterrupted",
                                  final_a)
        hashes_c = _persist_final(run_root, "final_resumed", final_c)
        validation = {
            "tranche": config["tranche"],
            "freeze_sha256": frozen["freeze_sha256"],
            "config_sha256": CONFIG_SHA256,
            "checkpoint_record_sha256": record["checkpoint_sha256"],
            "checkpoint_zero_adapter_sha256": zero_sha,
            "checkpoint_adapter_sha256": checkpoint_sha,
            "merged_groups": merged["merged_groups"],
            "excluded_tail_groups":
                [g["global_group_index"]
                 for g in merged["excluded_aborted_evidence"]],
            "reward_varying_groups":
                [g["global_group_index"] for g in varying],
            "comparison": comparison,
            "counters": final_c["counters"],
            "final_state_sha256": {"uninterrupted": hashes_a,
                                   "resumed": hashes_c},
            "identity_manifest_sha256":
                identity_manifest["manifest_sha256"],
            "environment_manifest_sha256": env_sha,
            "attested_environment_sha256":
                expected_environment_sha256,
            "session_preflight": preflight,
            "session_preflight_sha256": preflight_sha,
        }
        (run_root / "validation_record.json").write_text(
            json.dumps(validation, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        # the archive must verify by itself before the closeout
        verify_resume_validation(run_root)
    except BaseException as error:
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
