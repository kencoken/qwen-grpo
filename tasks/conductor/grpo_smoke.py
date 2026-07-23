"""Stage-0C named launch profile and policy-dependent smoke — 106_s
§§10.1, 10.3 (unit 4).

The launch profile is the checked-in scientific configuration: every
setting below is explicit and validated — no repository default fills a
scientific setting, which is why this entry constructs its own
GRPOConfig rather than routing through train.py's CLI defaults. The
smoke runs the frozen schedule (18 updates, 36 prompt groups, each §9.4
observation exactly twice in declaration order; dataset order is the
schedule and trainer shuffling is disabled), with the real routing
parser and the sampled action determining reward. The trained model and
optimizer state are DISCARDED — this is an integration diagnostic; it
allocates no train/dev/test, construction or qualification namespace,
and nothing chosen from its output enters a later scientific run.

Preconditions enforced at launch: the pinned support surface verifies
through the fail-closed loader; the registered w2/w3 canary passes in
its exact direction (workers absent afterwards — pre-materialized
routing needs no resident worker, 106_s §10.4 mode 1).

GATE (106_s §10.2): the Conductor system prompt and demonstrations must
be reviewed and fingerprinted BEFORE the reward-bearing smoke runs; the
CLI refuses until the profile marks the prompt review recorded. Once
any smoke output is inspected, the prompt bytes are frozen — a later
change is a new launch profile.

Run:  uv run python -m tasks.conductor.grpo_smoke check   (CPU gates)
      uv run python -m tasks.conductor.grpo_smoke demo-check   (GPU)
      uv run python -m tasks.conductor.grpo_smoke run     (GPU smoke)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

from .grpo_task import (
    build_smoke_rows, make_conductor_reward, smoke_schedule,
    summarize_action_trace,
)
from .payoff_support import (
    DECLARATION_PATH, canonical_support_profile, load_support_surface,
    run_canary,
)
from .policy import DEMO_CODE_CHECKS, SYSTEM_CONDUCTOR, policy_prompt_sha256
from .types import InfrastructureError
from .workerpool import STAGE0_POOL_FINGERPRINT

# The unit-3 surface this smoke trains against (118_s: unit 4 pins the
# surface-manifest hash; the loader re-verifies everything else).
SURFACE_DIR = Path("runs/stage0-support")
SURFACE_MANIFEST_SHA256 = \
    "221a04d53403f14c537a3d43336eb6630ca6fe5682f5e3f8aa66f78ace679c23"

STAGE0C_LAUNCH_PROFILE: dict[str, Any] = {
    "profile_name": "stage0c-smoke-v1",
    # §10.1: the Conductor shares worker 3's frozen base checkpoint.
    "conductor_model": {
        "model_id": "Qwen/Qwen2.5-3B-Instruct",
        "revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
    },
    "quantization": {"load_in_4bit": "true", "quant_type": "nf4",
                     "double_quant": "true", "compute_dtype": "bfloat16"},
    "gradient_checkpointing": True,
    "lora": {"r": 16, "alpha": 32, "dropout": 0.05,
             "targets": ["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"]},
    "grpo": {
        "beta": "1e-3",
        "group_size": 8,
        "temperature": "1.0",
        "per_device_batch": 2,
        "grad_accum": 8,          # 2x8 = 16 completions = 2 groups/update
        "learning_rate": "1e-5",
        "warmup_steps": 10,
        "scheduler": "constant_with_warmup",
        "loss": "dapo",           # the repository's current GRPO loss
        "optim": "adamw_torch",
        "bf16": True,
        "seed": 0,
        "max_steps": 18,
    },
    "policy_max_new_tokens": 128,
    "worker_max_new_tokens": 256,
    "worker_generation_batch": 1,
    "workflow_max_steps": 3,
    "worker_outcome_mode": "precomputed_surface",
    "worker_pool_fingerprint": STAGE0_POOL_FINGERPRINT,
    "surface_manifest_sha256": SURFACE_MANIFEST_SHA256,
    "policy_system_prompt_sha256": policy_prompt_sha256(),
    "smoke": {"updates": 18, "prompt_groups": 36},
    "wandb_project": "qwen-grpo-conductor",
    "eval": {"n_eval": 0, "strategy": "no"},
    # §10.2 gate: flipped to the reviewing document's name once the
    # prompt bytes are reviewed and fingerprinted. The reward-bearing
    # smoke refuses to run while this is null.
    "policy_prompt_review": None,
}


def launch_profile_sha256() -> str:
    return hashlib.sha256(json.dumps(
        STAGE0C_LAUNCH_PROFILE, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_launch_profile() -> None:
    profile = STAGE0C_LAUNCH_PROFILE
    if profile["policy_system_prompt_sha256"] != policy_prompt_sha256():
        raise InfrastructureError(
            "launch profile prompt hash does not match the policy "
            "module bytes")
    if profile["grpo"]["per_device_batch"] * profile["grpo"]["grad_accum"] \
            != 2 * profile["grpo"]["group_size"]:
        raise InfrastructureError(
            "batch shape must give exactly two prompt groups per update")
    schedule = smoke_schedule()
    if len(schedule) != profile["smoke"]["prompt_groups"] \
            or profile["smoke"]["updates"] * 2 != len(schedule):
        raise InfrastructureError("smoke schedule does not match the "
                                  "declared update count")
    from collections import Counter
    if set(Counter(schedule).values()) != {2}:
        raise InfrastructureError(
            "every observation must appear exactly twice in the schedule")
    if profile["worker_outcome_mode"] not in ("precomputed_surface",
                                              "live_singleton"):
        raise InfrastructureError("unknown worker_outcome_mode")


def verify_surface_pin() -> dict:
    manifest_path = SURFACE_DIR / "manifest.json"
    actual = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if actual != SURFACE_MANIFEST_SHA256:
        raise InfrastructureError(
            f"surface manifest hash {actual[:16]}… does not match the "
            f"launch-profile pin {SURFACE_MANIFEST_SHA256[:16]}…")
    return load_support_surface(SURFACE_DIR)


def run_smoke() -> int:
    import os
    validate_launch_profile()
    profile = STAGE0C_LAUNCH_PROFILE
    if not profile["policy_prompt_review"]:
        raise InfrastructureError(
            "the Conductor prompt bytes have not been reviewed and "
            "fingerprinted (106_s §10.2); the reward-bearing smoke is "
            "gated until policy_prompt_review names the review record")
    surface = verify_surface_pin()

    # §10.3 pre-smoke canary: model-scale selection must reach the
    # reward path before any policy sampling. Workers are released
    # afterwards — pre-materialized routing keeps them absent.
    canary_profile = canonical_support_profile()
    canary_profile["cache_path"] = "runs/stage0c-canary/cache.sqlite"
    from .pool_runtime import build_pool_runtime
    rt = build_pool_runtime(canary_profile)
    try:
        canary = run_canary(rt)
    finally:
        rt.close()
    print(f"canary: {canary['rewards']} (expected direction confirmed)")

    profile_sha = launch_profile_sha256()
    run_name = (f"stage0c-smoke-{profile_sha[:8]}"
                f"-{SURFACE_MANIFEST_SHA256[:8]}")
    run_dir = Path("runs") / run_name
    if run_dir.exists():
        raise InfrastructureError(
            f"{run_dir} exists; the smoke never overwrites a recorded "
            "run")
    run_dir.mkdir(parents=True)
    trace_path = run_dir / "actions.jsonl"
    (run_dir / "launch_profile.json").write_text(
        json.dumps(STAGE0C_LAUNCH_PROFILE, indent=1, sort_keys=True)
        + "\n")

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import BitsAndBytesConfig
    from trl import GRPOConfig, GRPOTrainer

    os.environ["WANDB_PROJECT"] = profile["wandb_project"]
    grpo = profile["grpo"]
    dataset = Dataset.from_list(build_smoke_rows())
    reward = make_conductor_reward(surface, trace_path=trace_path)

    args = GRPOConfig(
        output_dir=str(run_dir),
        run_name=run_name,
        seed=grpo["seed"],
        num_generations=grpo["group_size"],
        max_completion_length=profile["policy_max_new_tokens"],
        temperature=float(grpo["temperature"]),
        per_device_train_batch_size=grpo["per_device_batch"],
        gradient_accumulation_steps=grpo["grad_accum"],
        learning_rate=float(grpo["learning_rate"]),
        lr_scheduler_type=grpo["scheduler"],
        warmup_steps=grpo["warmup_steps"],
        beta=float(grpo["beta"]),
        max_steps=grpo["max_steps"],
        # §10.1: the frozen schedule IS the dataset order.
        shuffle_dataset=False,
        # §10.1: periodic evaluation disabled; no dev/test namespace.
        eval_strategy="no",
        gradient_checkpointing=profile["gradient_checkpointing"],
        gradient_checkpointing_kwargs={"use_reentrant": False},
        bf16=grpo["bf16"],
        model_init_kwargs={
            "torch_dtype": torch.bfloat16,
            "attn_implementation": "sdpa",
            "revision": profile["conductor_model"]["revision"],
            "quantization_config": BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16),
        },
        optim=grpo["optim"],
        report_to="wandb",
        logging_steps=1,
        log_completions=True,
        num_completions_to_print=2,
        save_strategy="no",       # the model is discarded (§10.3)
    )
    peft_config = LoraConfig(
        r=profile["lora"]["r"], lora_alpha=profile["lora"]["alpha"],
        lora_dropout=profile["lora"]["dropout"],
        target_modules=list(profile["lora"]["targets"]),
        task_type="CAUSAL_LM")

    started = time.monotonic()
    trainer = GRPOTrainer(
        model=profile["conductor_model"]["model_id"], args=args,
        train_dataset=dataset,
        # §10.1: exactly ONE scalar task reward — no format_reward.
        reward_funcs=[reward],
        peft_config=peft_config)
    trainer.train()
    wall = time.monotonic() - started
    peak = (torch.cuda.max_memory_reserved()
            if torch.cuda.is_available() else 0)

    summary = summarize_action_trace(trace_path)
    summary.update({
        "wall_seconds": round(wall, 1),
        "peak_reserved_vram_gib": round(peak / 2 ** 30, 2),
        "launch_profile_sha256": profile_sha,
        "surface_manifest_sha256": SURFACE_MANIFEST_SHA256,
        "canary": canary,
        "declaration_sha256": hashlib.sha256(
            DECLARATION_PATH.read_bytes()).hexdigest(),
    })
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


def run_demo_check() -> int:
    """Non-reward-bearing §10.2 check: the matched Code-like demo steps
    execute successfully through BOTH real Code workers."""
    from . import contract, render
    from .pool_runtime import FourWorkerPool
    from .tools import Binding
    from .types import IntegerList
    profile = canonical_support_profile()
    pool = FourWorkerPool(profile)
    failures = []
    for check in DEMO_CODE_CHECKS:
        payload = check["payload"]
        resource_text = (f"{check['resource_handle']}: "
                         + " ".join(str(v) for v in payload))
        user = render.build_worker_request(
            "A buffer holds an integer sequence.",
            f"Return the value at zero-based index {check['index']} of "
            "the integer sequence in the requested resource.",
            resource_text=resource_text,
            contract=render.CONTRACT_TASK_LAST)
        binding = Binding(resources={
            check["resource_handle"]: IntegerList(tuple(payload))})
        for worker in (2, 3):
            request = pool.render_request(worker, user)
            gen = pool.generate_singleton(worker, request)
            result = contract.run_worker_output(2, gen.completion,
                                                binding)
            ok = (result.status == "success"
                  and result.value == check["expected"])
            print(f"demo {check['demo_index']} worker {worker}: "
                  f"{result.status} value={result.value} "
                  f"(expected {check['expected']}) "
                  f"{'OK' if ok else 'FAIL'}")
            if not ok:
                failures.append((check["demo_index"], worker))
    pool.close()
    if failures:
        print(f"FAIL: {failures}")
        return 1
    print("demo-check OK: both Code workers execute both matched demos")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="CPU gates: profile, schedule, pins")
    sub.add_parser("demo-check", help="GPU: matched Code demos execute "
                                      "through both workers")
    sub.add_parser("run", help="GPU: the 18-update reward-bearing smoke "
                               "(gated on the §10.2 prompt review)")
    args = ap.parse_args(argv)
    if args.command == "check":
        validate_launch_profile()
        surface = verify_surface_pin()
        print(f"launch profile OK (sha {launch_profile_sha256()[:16]}), "
              f"schedule {len(smoke_schedule())} groups, surface "
              f"{len(surface)} rows verified against pin "
              f"{SURFACE_MANIFEST_SHA256[:16]}")
        gate = STAGE0C_LAUNCH_PROFILE["policy_prompt_review"]
        print(f"§10.2 prompt review: "
              f"{gate or 'PENDING — reward-bearing smoke is gated'}")
        return 0
    if args.command == "demo-check":
        return run_demo_check()
    if args.command == "run":
        return run_smoke()
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
