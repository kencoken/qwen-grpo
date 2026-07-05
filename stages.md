# Exploration roadmap: learning GRPO dynamics on a single RTX 4090

The goal is **intuition about GRPO training dynamics**, not benchmark numbers.
Inspired by the Conductor paper (Qwen2.5-7B, 200 GRPO iterations, 4 questions ×
64 rollouts, 2× H100 — far beyond one 4090), the plan is to build a minimal,
fully-understood training loop and then vary one thing at a time.

Success criterion (unchanged from the original plan):

> *"I can predict how changing group size, temperature, reward shaping, and
> max length affects training."*

This document is the revised version of the original staging, after review.
Revisions and their reasons are marked **[revised]**.

---

## Stage 0 — plumbing (smoke test)

Prove the pipeline before spending real GPU-hours.

- **Verifier first**: `pytest test_rewards.py` green before any training.
  Reward bugs are the canonical silent GRPO failure — a regex that accepts
  malformed output *teaches the model malformed output*.
- **Run A**: Qwen2.5-**1.5B**-Instruct, bf16 + LoRA r=16, 20 optimizer steps,
  64 unfiltered GSM8K problems (~15 min).

**Exit criterion**: W&B shows both reward curves, the `kl` curve, and the
sample-completions table; no OOM. Format reward should tick up within ~20 steps.

## Stage 1 — first real run

**Run B**: Qwen2.5-**7B**-Instruct, 4-bit QLoRA r=16, group size 8,
1 prompt/step, max completion 512, 300 steps on 512 GSM8K problems (overnight;
generation-bound at ~1.5–3 min/step via HF `generate`).

Revisions vs. the original plan:

- **[revised] Difficulty-filtered data.** Qwen2.5-7B-Instruct already scores
  ~80–85% on GSM8K. GRPO's advantage is zero when all rollouts in a group score
  the same, so easy problems contribute no gradient. `filter_data.py` samples
  4 rollouts on ~1500 train problems and keeps ~512 with pass rate strictly
  between 0 and 1 — training signal concentrated where gradients exist.
- **[revised] KL logged, not penalized (β=1e-3).** Modern practice (DAPO
  onward) drops the KL penalty for verifiable-reward training: the reward
  can't be hacked the way a learned reward model can, and reasoning training
  *wants* distribution shift. But the KL curve is a drift gauge worth watching,
  and with LoRA the reference model is free (adapter-disabled forward pass).
  Tiny β keeps the gauge on with the leash off.
- **[revised] Held-out eval.** The original plan had none. `eval.py` runs
  greedy pass@1 on 200 GSM8K test problems before and after training.
- **No SFT warm start** (as originally planned, now with the reason explicit):
  an instruct model emits valid format often enough for nonzero group variance,
  and watching format emerge cold is half the point. SFT is a Stage-2 ablation
  and becomes *mandatory* in Stage 3.

Expected observations: format reward improves first; correctness is noisy;
`unique_answer_rate` collapsing toward 1/group_size signals mode collapse;
`completions/clipped_ratio` rising means answers are hitting the length limit.

**Exit criterion**: format compliance clearly up on held-out test; accuracy
movement is a bonus, not the bar.

## Stage 2 — dynamics experiments

One variable at a time, everything else frozen. Each run is a config override
plus a W&B run name that encodes the variable (`stage2-7b-g16-t1.0`).

Original grid:

| Axis | Values |
|---|---|
| group size (`num_generations`) | 4 vs 8 vs 16 |
| temperature | 0.7 vs 1.0 |
| LoRA rank | 8 vs 16 vs 32 |
| reward shaping (`reward_weights`) | binary vs partial credit |
| max completion tokens | 256 vs 512 |
| SFT warm start | no vs yes |

Added arms **[revised]**:

| Axis | Values | Why |
|---|---|---|
| KL penalty | β=1e-3 (log-only) vs 0.04 | does the leash change the dynamics? |
| base vs instruct | 7B base (R1-Zero style) vs 7B-Instruct | watch format emerge from nothing; Qwen2.5 base is known to cold-start well |
| full FT vs LoRA | 1.5B/3B, `use_lora` off vs on | test the "LoRA barely changes dynamics" claim |
| task | **Countdown on Qwen2.5-3B** | TinyZero-style skill *acquisition* (vs GSM8K's elicitation); unlimited synthetic data, tunable difficulty, fast sweeps |

Throughput unlock for the sweep phase: 1.5B/3B fit vLLM colocate
(`use_vllm=True, vllm_mode="colocate"`) → ~4–8× wall clock. The 7B QLoRA run
cannot use it (a second bf16 weight copy doesn't fit in 24 GB, and TRL can't
sync LoRA into a quantized engine).

Memory notes for full FT (weights + grads + adamw_8bit states, before
activations): 1.5B ≈ 9.5 GB (comfortable, KL ref copy fits), 3B ≈ 18.5 GB
(tight; no room for a ref copy → β must be 0), 7B — never on 24 GB.

## Stage 3 — mini-Conductor

Unchanged from the original plan:

1. **SFT first** on synthetic conductor traces (mandatory here: the model has
   ~zero prior probability of emitting valid workflow lists, so cold GRPO
   would produce all-zero groups).
2. Then tiny GRPO: reward = parseable workflow + final answer correctness.
3. 1–2 cheap local workers, 100–300 math/code problems, workflow ≤ 2 steps,
   4–8 rollouts. Debug locally before touching API frontier workers.

Dataset progression stays GSM8K → MATH500 subset (needs `math_verify` for
LaTeX answer equivalence) → LiveCodeBench-easy (execution rewards).
