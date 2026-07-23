"""Stage-0C named launch profile, prompt-freeze machinery and
policy-dependent smoke — 106_s §§10.1–10.3 as corrected by 121_s.

The launch profile is authoritative over execution (121_s finding 3):
`loss_type` is passed explicitly, only `precomputed_surface` is
supported (anything else fails closed), the surface/pool pins are read
from the validated profile, and the tokenizer is revision-pinned via
an explicit `processing_class`. This entry constructs its own
`GRPOConfig` — no repository default fills a scientific setting.

Freeze discipline (121_s lock sequence): the demo-check executes the
four EXACT preregistered demonstration workflows through the real
runtime (both Code workers on every Code node, budget counted in
unique rendered request bytes); the reward-blind format probe samples
one group of eight per unique observation with the smoke tokenizer/
temperature/cap/seed, never loads the payoff surface, and reports only
schema validity and action-length rates by topology (>=80% per-topology
validity as the catastrophic-stop rule); a passing probe is followed
immediately by `freeze`, which records LITERAL digests (system prompt,
all 18 rendered observations, pinned chat-template bytes, launch
profile, executable commit) into a committed fixture. The
reward-bearing smoke refuses to run until the freeze fixture verifies
and `policy_prompt_review` names the review record.

Run:  uv run python -m tasks.conductor.grpo_smoke check        (CPU)
      uv run python -m tasks.conductor.grpo_smoke demo-check   (GPU)
      uv run python -m tasks.conductor.grpo_smoke format-probe (GPU)
      uv run python -m tasks.conductor.grpo_smoke freeze       (CPU)
      uv run python -m tasks.conductor.grpo_smoke run          (GPU)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

from . import parser
from .executor import WorkflowItem
from .grpo_task import (
    build_smoke_rows, make_conductor_reward, smoke_schedule,
    summarize_action_trace,
)
from .payoff_support import (
    DECLARATION_PATH, FIXTURES, canonical_support_profile,
    load_support_surface, run_canary,
)
from .policy import (
    CONDUCTOR_DEMOS, demo_registry, policy_prompt_sha256,
)
from .types import InfrastructureError
from .workerpool import STAGE0_POOL_FINGERPRINT

SURFACE_DIR = Path("runs/stage0-support")
FREEZE_PATH = FIXTURES / "stage0c_policy_freeze.json"

# 123_s §8.4: the freeze binds a deterministic digest over the
# executable source that produces the model-visible bundle and the
# smoke — not the live Git commit (self-referential once the fixture
# commits) and not the fixture itself.
SOURCE_DIGEST_FILES = (
    "tasks/conductor/policy.py",
    "tasks/conductor/render.py",
    "tasks/conductor/grpo_task.py",
    "tasks/conductor/grpo_smoke.py",
    "tasks/conductor/parser.py",
    "tasks/conductor/payoff_support.py",
    "tasks/conductor/workerpool.py",
    "tasks/conductor/prompts.py",
)


def executable_source_digest() -> str:
    digest = hashlib.sha256()
    for name in SOURCE_DIGEST_FILES:
        digest.update(name.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(Path(name).read_bytes())
        digest.update(b"\x00")
    return digest.hexdigest()

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
        "loss": "dapo",           # passed explicitly to GRPOConfig (121_s)
        "optim": "adamw_torch",
        "bf16": True,
        "seed": 0,
        "max_steps": 18,
    },
    "policy_max_new_tokens": 128,
    "worker_max_new_tokens": 256,
    "worker_generation_batch": 1,
    "workflow_max_steps": 3,
    # 121_s finding 3: only precomputed_surface is supported by this
    # smoke; any other declared mode fails validation closed.
    "worker_outcome_mode": "precomputed_surface",
    "worker_pool_fingerprint": STAGE0_POOL_FINGERPRINT,
    "surface_manifest_sha256":
        "221a04d53403f14c537a3d43336eb6630ca6fe5682f5e3f8aa66f78ace679c23",
    "policy_system_prompt_sha256": policy_prompt_sha256(),
    "smoke": {"updates": 18, "prompt_groups": 36},
    "wandb_project": "qwen-grpo-conductor",
    "eval": {"n_eval": 0, "strategy": "no"},
    # Set to the review record's name at freeze; the reward-bearing
    # smoke refuses while null (106_s §10.2).
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
    if profile["worker_outcome_mode"] != "precomputed_surface":
        raise InfrastructureError(
            f"worker_outcome_mode "
            f"{profile['worker_outcome_mode']!r} is not supported by "
            "this smoke: only precomputed_surface executes; declaring "
            "an unimplemented mode is fabricated provenance (121_s)")


def verify_surface_pin() -> dict:
    """The validated profile is the single authority for the pin
    (121_s finding 3)."""
    validate_launch_profile()
    pin = STAGE0C_LAUNCH_PROFILE["surface_manifest_sha256"]
    manifest_path = SURFACE_DIR / "manifest.json"
    if not manifest_path.exists():
        raise InfrastructureError(
            f"pinned surface {manifest_path} is absent; materialize it "
            "with payoff_support before the smoke")
    actual = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if actual != pin:
        raise InfrastructureError(
            f"surface manifest hash {actual[:16]}… does not match the "
            f"launch-profile pin {pin[:16]}…")
    return load_support_surface(SURFACE_DIR)


# --- demo-check: the exact preregistered workflows (121_s) -------------------

def demo_check_variants() -> list[tuple[str, dict, list[int]]]:
    """Every execution the check performs (123_s §4): each demo with
    its assigned ids; the Code-swapped variant ONLY for the explicitly
    matched independent→final pair. The specialist→check demo is an
    asymmetric capability example — requiring universal
    cross-executability there would contradict the heterogeneity that
    motivates the four-worker pool."""
    variants = []
    for demo in CONDUCTOR_DEMOS:
        variants.append((f"{demo['name']}:assigned", demo,
                         list(demo["worker_ids"])))
        if demo["name"] == "independent_final":
            swapped = [{2: 3, 3: 2}.get(w, w)
                       for w in demo["worker_ids"]]
            variants.append((f"{demo['name']}:code-swapped", demo,
                             swapped))
    return variants


def run_demo_check() -> int:
    from .pool_runtime import build_pool_runtime
    profile = canonical_support_profile()
    profile["cache_path"] = "runs/stage0c-demo-check/cache.sqlite"
    rt = build_pool_runtime(profile)
    unique_requests: set[str] = set()
    failures = []
    try:
        for label, demo, worker_ids in demo_check_variants():
            registry = demo_registry(demo)
            action = parser.routing_to_workflow(
                worker_ids, [dict(step) for step in demo["steps"]])
            item = WorkflowItem(
                item_id=f"demo:{label}", action=action,
                public_prompt=demo["problem"], registry=registry,
                request_contract=rt.profile["request_contract"])
            results, telemetry = rt.execute_batch([item])
            unique_requests.update(record.request_sha256
                                   for _, record in telemetry)
            terminal = results[0].terminal
            ok = terminal == demo["gold"]
            print(f"{label}: ids {worker_ids} -> terminal {terminal} "
                  f"(gold {demo['gold']}) {'OK' if ok else 'FAIL'}")
            if not ok:
                for step in results[0].steps:
                    status = (step.result.status if step.result
                              else f"world:{step.world_failure}")
                    print(f"    step {step.position} w{step.worker_id}: "
                          f"{status} {step.completion!r}"[:170])
                failures.append(label)
        generations = rt.pool.singleton_generations
    finally:
        rt.close()
    print(f"budget: {len(unique_requests)} unique rendered requests "
          f"this run; {generations} new singleton generations "
          "(cache-backed reruns are free)")
    if failures:
        print(f"FAIL: {failures}")
        return 1
    print("demo-check OK: all preregistered workflows execute, both "
          "Code workers on every Code node")
    return 0


# --- reward-blind format probe (121_s) ---------------------------------------

TOPOLOGY_BY_CELL = {"lookup_atomic": "atomic", "math_atomic": "atomic",
                    "code_atomic": "atomic", "lookup_math": "two_step",
                    "math_code": "two_step", "fork_join": "fork"}
FORMAT_PROBE_VALIDITY_FLOOR = 0.80  # the existing per-topology threshold


def run_format_probe() -> int:
    """One group of eight sampled completions per unique observation,
    smoke tokenizer/temperature/cap/seed. NEVER loads the payoff
    surface; reports ONLY schema validity and action-length rates by
    topology. >=80% per-topology validity is the catastrophic-stop
    rule; worker choices are neither inspected nor reported."""
    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig)

    validate_launch_profile()
    profile = STAGE0C_LAUNCH_PROFILE
    model_cfg = profile["conductor_model"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_cfg["model_id"], revision=model_cfg["revision"])
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        model_cfg["model_id"], revision=model_cfg["revision"],
        dtype=torch.bfloat16,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16),
        device_map="cuda").eval()
    torch.manual_seed(profile["grpo"]["seed"])

    rows = build_smoke_rows()
    unique: dict[str, dict] = {}
    for row in rows:
        unique.setdefault(row["observation_id"], row)
    stats: dict[str, dict[str, int]] = {}
    for observation_id, row in unique.items():
        topology = TOPOLOGY_BY_CELL[row["cell_id"]]
        bucket = stats.setdefault(topology, {"n": 0, "valid": 0,
                                             "right_length": 0})
        text = tokenizer.apply_chat_template(
            row["prompt"], tokenize=False, add_generation_prompt=True)
        batch = tokenizer([text] * profile["grpo"]["group_size"],
                          return_tensors="pt", padding=True,
                          add_special_tokens=False).to(model.device)
        with torch.no_grad():
            out = model.generate(
                **batch,
                max_new_tokens=profile["policy_max_new_tokens"],
                do_sample=True,
                temperature=float(profile["grpo"]["temperature"]),
                pad_token_id=tokenizer.pad_token_id)
        completions = tokenizer.batch_decode(
            out[:, batch["input_ids"].shape[1]:],
            skip_special_tokens=True)
        for completion in completions:
            bucket["n"] += 1
            try:
                parser.parse_routing_action(completion,
                                            row["num_steps"])
                bucket["valid"] += 1
                bucket["right_length"] += 1
            except parser.ActionSchemaError:
                try:
                    obj = json.loads(completion.strip())
                    ids = obj.get("worker_ids")
                    if isinstance(ids, list) \
                            and len(ids) == row["num_steps"]:
                        bucket["right_length"] += 1
                except (json.JSONDecodeError, AttributeError):
                    pass
    report = {
        topology: {
            "completions": bucket["n"],
            "valid_rate": round(bucket["valid"] / bucket["n"], 4),
            "right_length_rate": round(
                bucket["right_length"] / bucket["n"], 4),
        } for topology, bucket in sorted(stats.items())}
    print(json.dumps(report, indent=1, sort_keys=True))
    failed = {topology: values["valid_rate"]
              for topology, values in report.items()
              if values["valid_rate"] < FORMAT_PROBE_VALIDITY_FLOOR}
    if failed:
        print(f"CATASTROPHIC STOP: per-topology validity below "
              f"{FORMAT_PROBE_VALIDITY_FLOOR:.0%}: {failed} — at most "
              "one schema-only repair is permitted (121_s)")
        return 1
    print("format probe OK — freeze immediately (121_s)")
    return 0


# --- freeze: literal digests over the model-visible bundle -------------------

def compute_freeze_record(review_record: str | None = None
                          ) -> dict[str, Any]:
    from transformers import AutoTokenizer
    validate_launch_profile()
    model_cfg = STAGE0C_LAUNCH_PROFILE["conductor_model"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_cfg["model_id"], revision=model_cfg["revision"])
    rows = build_smoke_rows()
    unique: dict[str, str] = {}
    for row in rows:
        unique.setdefault(row["observation_id"],
                          row["prompt"][1]["content"])
    import subprocess
    commit = subprocess.run(["git", "rev-parse", "HEAD"],
                            capture_output=True, text=True,
                            check=True).stdout.strip()
    return {
        "freeze": "stage0c-policy-v1",
        "policy_system_prompt_sha256": policy_prompt_sha256(),
        "observation_sha256": {
            observation_id: hashlib.sha256(
                content.encode("utf-8")).hexdigest()
            for observation_id, content in sorted(unique.items())},
        "chat_template_sha256": hashlib.sha256(
            tokenizer.chat_template.encode("utf-8")).hexdigest(),
        "conductor_tokenizer":
            f"{model_cfg['model_id']}@{model_cfg['revision']}",
        "launch_profile_sha256": launch_profile_sha256(),
        "support_declaration_sha256": hashlib.sha256(
            DECLARATION_PATH.read_bytes()).hexdigest(),
        "executable_source_sha256": executable_source_digest(),
        "executable_commit_at_freeze": commit,  # informational
        "policy_prompt_review": review_record,
    }


def verify_freeze() -> dict[str, Any]:
    """Regenerate every digest and compare against the committed
    literal record — the freeze is bytes, not source introspection."""
    if not FREEZE_PATH.exists():
        raise InfrastructureError(
            "policy freeze fixture is absent; the prompt bundle is not "
            "frozen (121_s lock sequence)")
    frozen = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    current = compute_freeze_record(frozen.get("policy_prompt_review"))
    for key in ("policy_system_prompt_sha256", "observation_sha256",
                "chat_template_sha256", "conductor_tokenizer",
                "launch_profile_sha256", "support_declaration_sha256",
                "executable_source_sha256"):
        if frozen.get(key) != current[key]:
            raise InfrastructureError(
                f"frozen policy bundle field {key!r} does not match the "
                "current bytes — the prompt bundle moved after freeze; "
                "a change is a new launch profile (106_s §10.2)")
    if not frozen.get("policy_prompt_review"):
        raise InfrastructureError(
            "freeze fixture does not name the §10.2 review record")
    return frozen


# --- the reward-bearing smoke ------------------------------------------------

def run_smoke() -> int:
    import os
    validate_launch_profile()
    profile = STAGE0C_LAUNCH_PROFILE
    frozen = verify_freeze()
    if not profile["policy_prompt_review"] or \
            profile["policy_prompt_review"] != \
            frozen["policy_prompt_review"]:
        raise InfrastructureError(
            "launch profile policy_prompt_review does not name the "
            "frozen review record (106_s §10.2)")
    surface = verify_surface_pin()
    schedule = smoke_schedule()

    # §10.3 pre-smoke canary; workers are released afterwards and the
    # CUDA peak counter is reset so GRPO VRAM excludes them (121_s).
    from .pool_runtime import build_pool_runtime
    canary_profile = canonical_support_profile()
    canary_profile["cache_path"] = "runs/stage0c-canary/cache.sqlite"
    rt = build_pool_runtime(canary_profile)
    try:
        canary = run_canary(rt)
    finally:
        rt.close()
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    print(f"canary: {canary['rewards']} (registered direction)")

    profile_sha = launch_profile_sha256()
    run_name = (f"stage0c-smoke-{profile_sha[:8]}"
                f"-{profile['surface_manifest_sha256'][:8]}")
    run_dir = Path("runs") / run_name
    if run_dir.exists():
        raise InfrastructureError(
            f"{run_dir} exists; the smoke never overwrites a recorded "
            "run")
    run_dir.mkdir(parents=True)
    trace_path = run_dir / "actions.jsonl"
    (run_dir / "launch_profile.json").write_text(
        json.dumps(profile, indent=1, sort_keys=True) + "\n")
    (run_dir / "freeze_record.json").write_text(
        json.dumps(frozen, indent=1, sort_keys=True) + "\n")

    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer, BitsAndBytesConfig
    from trl import GRPOConfig, GRPOTrainer

    os.environ["WANDB_PROJECT"] = profile["wandb_project"]
    grpo = profile["grpo"]
    dataset = Dataset.from_list(build_smoke_rows())
    reward = make_conductor_reward(surface, trace_path=trace_path,
                                   schedule=schedule,
                                   group_size=grpo["group_size"])
    model_cfg = profile["conductor_model"]
    # 121_s finding 3: the tokenizer is revision-pinned explicitly.
    processing_class = AutoTokenizer.from_pretrained(
        model_cfg["model_id"], revision=model_cfg["revision"])

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
        loss_type=grpo["loss"],   # explicit, not TRL's default (121_s)
        shuffle_dataset=False,    # the frozen schedule IS the order
        eval_strategy="no",
        gradient_checkpointing=profile["gradient_checkpointing"],
        gradient_checkpointing_kwargs={"use_reentrant": False},
        bf16=grpo["bf16"],
        model_init_kwargs={
            "torch_dtype": torch.bfloat16,
            "attn_implementation": "sdpa",
            "revision": model_cfg["revision"],
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
    status = "complete"
    error_text = None
    try:
        trainer = GRPOTrainer(
            model=model_cfg["model_id"], args=args,
            train_dataset=dataset,
            processing_class=processing_class,
            # §10.1: exactly ONE scalar task reward — no format_reward.
            reward_funcs=[reward],
            peft_config=peft_config)
        trainer.train()
    except BaseException as error:
        status = "aborted"
        error_text = f"{type(error).__name__}: {error}"
        raise
    finally:
        wall = time.monotonic() - started
        peak = (torch.cuda.max_memory_reserved()
                if torch.cuda.is_available() else 0)
        record: dict[str, Any] = {
            "status": status,
            "error": error_text,
            "wall_seconds": round(wall, 1),
            "peak_reserved_vram_gib": round(peak / 2 ** 30, 2),
            "surface_lookups": reward.state["lookups"],
            "completions_recorded": reward.state["written"],
            "launch_profile_sha256": profile_sha,
            "surface_manifest_sha256":
                profile["surface_manifest_sha256"],
            "canary": canary,
        }
        if status == "complete":
            summary = summarize_action_trace(
                trace_path, expected_schedule=schedule,
                group_size=grpo["group_size"])
            record.update(summary)
        (run_dir / "summary.json").write_text(
            json.dumps(record, indent=1, sort_keys=True) + "\n")
        print(json.dumps(record, indent=1, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="CPU gates: profile, schedule, pins")
    sub.add_parser("demo-check", help="GPU: the exact preregistered "
                                      "demo workflows, both Code "
                                      "workers on every Code node")
    sub.add_parser("format-probe", help="GPU: reward-blind schema/"
                                        "length probe, 18x8")
    frz = sub.add_parser("freeze", help="record the literal policy "
                                        "bundle digests")
    frz.add_argument("--review-record", required=True)
    sub.add_parser("run", help="GPU: the reward-bearing smoke (frozen "
                               "bundle + review record required)")
    args = ap.parse_args(argv)
    if args.command == "check":
        validate_launch_profile()
        surface = verify_surface_pin()
        print(f"launch profile OK (sha {launch_profile_sha256()[:16]}), "
              f"schedule {len(smoke_schedule())} groups, surface "
              f"{len(surface)} rows verified against the profile pin")
        print(f"freeze: {'present' if FREEZE_PATH.exists() else 'ABSENT'}"
              f"; review: "
              f"{STAGE0C_LAUNCH_PROFILE['policy_prompt_review'] or 'PENDING'}")
        return 0
    if args.command == "demo-check":
        return run_demo_check()
    if args.command == "format-probe":
        return run_format_probe()
    if args.command == "freeze":
        record = compute_freeze_record(args.review_record)
        with FREEZE_PATH.open("x", encoding="utf-8") as handle:
            json.dump(record, handle, indent=1, sort_keys=True)
            handle.write("\n")
        print(f"frozen -> {FREEZE_PATH} (sha "
              f"{hashlib.sha256(FREEZE_PATH.read_bytes()).hexdigest()[:16]})")
        return 0
    if args.command == "run":
        return run_smoke()
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
