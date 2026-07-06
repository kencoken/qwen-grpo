"""GRPO training: Config + TRL GRPOTrainer wiring. That's all this file is —
the algorithm lives in TRL, the verifier in rewards.py, the task in data.py.

The two standard runs (see stages.md):

  Stage 0 smoke (defaults):     uv run python train.py
  Stage 1 real run:             uv run python train.py \
      --model Qwen/Qwen2.5-7B-Instruct --load_in_4bit true \
      --max_completion_length 512 --max_steps 300 --n_train 512 \
      --dataset filtered --run_name stage1-7b-g8-t1.0

Every Config field is a --flag value override, so Stage-2 sweeps are shell
loops with run names that encode the variable being varied.
"""

import argparse
import os
from dataclasses import dataclass, fields

import torch
from peft import LoraConfig
from transformers import BitsAndBytesConfig
from trl import GRPOConfig, GRPOTrainer

from rewards import format_reward
from tasks.gsm8k import correctness_reward, load_eval, load_train


@dataclass
class Config:
    model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    dataset: str = "unfiltered"  # "filtered" needs filter_data.py output
    n_train: int = 64            # 512 for Stage 1
    run_name: str = "smoke-1.5b"
    seed: int = 0

    # --- memory strategy -----------------------------------------------------
    # 4-bit NF4 base + LoRA (= QLoRA) is what fits a 7B on 24 GB. use_lora=False
    # is full fine-tuning: fits 1.5B comfortably, 3B only with beta=0 (the
    # frozen reference for the KL metric is an extra full model copy; with LoRA
    # it's free — TRL just runs a forward pass with the adapter disabled).
    load_in_4bit: bool = False
    use_lora: bool = True
    lora_r: int = 16             # Stage-2 axis: 8 / 16 / 32

    # --- the GRPO knobs that Stage 2 is about ----------------------------------
    # Group size: advantages are computed *within* each group of rollouts for
    # the same prompt (reward minus group mean). Bigger groups = less noisy
    # advantage estimates, linearly more generation time.
    num_generations: int = 8
    # 2 x 4 = 8 = num_generations -> exactly one prompt's group per optimizer
    # step ("1 prompt per step" in the plan). The effective batch must be
    # divisible by num_generations or TRL refuses to start.
    per_device_batch: int = 2
    grad_accum: int = 4
    # (no prompt-length cap: TRL >=1.7 dropped max_prompt_length, and GSM8K
    # questions are short — system prompt + question is well under 300 tokens)
    max_completion_length: int = 256  # 512 for Stage 1; watch clipped_ratio
    # Rollout temperature: exploration knob. Too low -> rollouts agree with
    # each other -> zero within-group variance -> no gradient.
    temperature: float = 1.0
    # LoRA tolerates ~10x the learning rate of full fine-tuning (5e-7..1e-6).
    learning_rate: float = 1e-5
    # KL coefficient. 1e-3 = "gauge on, leash off": negligible penalty, but
    # TRL computes reference logprobs so the kl curve lands in W&B. Modern
    # practice (DAPO onward) uses 0 for verifiable rewards — the reward can't
    # be hacked like a learned RM, and reasoning training *wants* drift.
    # Costs ~10-15% step time. Set 0.04 for a real leash (Stage-2 arm).
    beta: float = 1e-3
    max_steps: int = 20          # 300 for Stage 1
    # Periodic held-out eval (TRL generates completions for n_eval test
    # problems every eval_steps and logs eval reward means). Caveat: this is
    # *sampled* accuracy at the training temperature — a relative validation
    # curve to catch divergence/overfitting mid-run; the headline greedy
    # number remains eval.py's job. Costs roughly 5-10% of run time.
    n_eval: int = 64
    eval_steps: int = 50


def parse_config():
    parser = argparse.ArgumentParser()
    for f in fields(Config):
        kind = (lambda s: s.lower() in ("1", "true", "yes")) if f.type == bool else f.type
        parser.add_argument(f"--{f.name}", type=kind, default=f.default)
    return Config(**vars(parser.parse_args()))


def main():
    cfg = parse_config()
    os.environ.setdefault("WANDB_PROJECT", "qwen-grpo")

    train_dataset = load_train(n=cfg.n_train, variant=cfg.dataset)
    eval_dataset = load_eval(n=cfg.n_eval)

    args = GRPOConfig(
        output_dir=f"runs/{cfg.run_name}",
        run_name=cfg.run_name,
        seed=cfg.seed,
        # generation
        num_generations=cfg.num_generations,
        max_completion_length=cfg.max_completion_length,
        temperature=cfg.temperature,
        # optimization (loss_type stays TRL's default, currently "dapo":
        # token-level normalization avoids naive GRPO's length bias)
        per_device_train_batch_size=cfg.per_device_batch,
        gradient_accumulation_steps=cfg.grad_accum,
        learning_rate=cfg.learning_rate,
        lr_scheduler_type="constant_with_warmup",
        warmup_steps=10,
        beta=cfg.beta,
        max_steps=cfg.max_steps,
        # periodic held-out eval (see Config note); 4 generations per eval
        # prompt halves the cost vs reusing the training group size. Eval is
        # generation-only (no optimizer/grad memory), so batch much wider
        # than training — at batch 4 an eval was 24 min on the 7B; at 16 it's
        # ~6-8. Must stay divisible by num_generations_eval.
        eval_strategy="steps",
        eval_steps=cfg.eval_steps,
        num_generations_eval=4,
        per_device_eval_batch_size=16,
        # memory: checkpoint activations; the model itself may be 4-bit (below).
        # Generation is HF generate — slow (~1.5-3 min/step on the 7B) but zero
        # extra weight copies. vLLM colocate would be ~5-10x faster generation
        # yet needs its own bf16 weight copy (~15 GB for 7B: doesn't fit next
        # to training state, and TRL can't sync LoRA into a quantized engine).
        # For 1.5B/3B Stage-2 sweeps it fits: use_vllm=True, vllm_mode="colocate".
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        bf16=True,
        model_init_kwargs={
            "torch_dtype": torch.bfloat16,
            "attn_implementation": "sdpa",
            **(
                {
                    "quantization_config": BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_compute_dtype=torch.bfloat16,
                    )
                }
                if cfg.load_in_4bit
                else {}
            ),
        },
        # full FT needs 8-bit optimizer states to fit (plain AdamW is 8
        # bytes/param in fp32); for LoRA the optimizer is tiny either way.
        optim="adamw_torch" if cfg.use_lora else "adamw_8bit",
        # logging: TRL logs per-reward-func means, completion lengths, kl,
        # entropy, clip ratios; rewards.py adds accuracy + unique_answer_rate.
        report_to="wandb",
        logging_steps=1,
        log_completions=True,
        num_completions_to_print=2,
        save_steps=50,
    )

    peft_config = (
        LoraConfig(
            r=cfg.lora_r,
            lora_alpha=cfg.lora_r * 2,
            lora_dropout=0.05,
            # all linear projections, not just q/v — standard for QLoRA since
            # the original paper found attention-only adapters underperform
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ],
            task_type="CAUSAL_LM",
        )
        if cfg.use_lora
        else None
    )

    trainer = GRPOTrainer(
        model=cfg.model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        # order matters only for reward_weights; both default to weight 1.0
        reward_funcs=[format_reward, correctness_reward],
        peft_config=peft_config,
    )
    trainer.train()
    trainer.save_model()  # LoRA: adapter only (a few MB) -> runs/<run_name>


if __name__ == "__main__":
    main()
