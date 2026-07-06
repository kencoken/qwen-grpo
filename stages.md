# Exploration roadmap: learning GRPO dynamics on a single RTX 4090

The goal is **intuition about GRPO training dynamics**, not benchmark numbers.
The organizing question after Stage 1: **how does reward density (task
difficulty) shape GRPO dynamics?** Datasets are instruments for that question,
not destinations.

Success criterion (unchanged since the original plan):

> *"I can predict how changing group size, temperature, reward shaping, and
> max length affects training."*

Working discipline, applied throughout:

- **Pre-register**: every run gets its prediction written in
  `experiment_log.md` *before* launch. Where predictions fail is where the
  learning is.
- **One hard change at a time**: a dataset move is secretly a verifier move +
  a distribution move + a length-regime move; sequence them.
- **Statistics**: full-set evals with fixed seeds (MATH500 at ~70% has ±~2%
  SE on all 500 — no 200-problem shortcuts there); two seeds before believing
  a headline claim.
- **GSM8K is retired as a research object but kept as the regression
  control**: rerun the E1 config after major trainer/code changes; if it
  degrades, the bug is ours, not the science.
- **Experiments per week is the real currency** on one GPU — prefer the
  instrument that iterates faster.

---

## Stage 0/1 — GSM8K: validate the pipeline ✅ (2026-07-05)

Complete; see `experiment_log.md` E0/E1. Headline: 86.5% → 92.0% held-out
after 300 steps on difficulty-filtered problems; observed zero-variance
groups, entropy-collapse pressure, and its endogenous self-stabilization.
Left behind: written predictions to test (Phase A) and the conclusion that
GSM8K has no headroom that isn't reliability-shaped.

## Phase A — close E1's open claims ✅ (2026-07-05/06; E2, E4, E5, E6)

Outcome, in one paragraph: the **sharpening story is confirmed** (E4: pass@64
unmoved, curves converge by k≈4, RL harvested ~half the majority-vote
headroom — gains are consistency, not capability). The **dynamics fine
structure did not survive replication** (E6: entropy recovery 1/3, end-KL
spread 4× across seeds; E1's "self-stabilization" retired as unconfirmed —
GSM8K compresses dynamics into too narrow a band to resolve such effects).
The **outcome story flipped** (E5: the "wasted compute" unfiltered run scored
93.0%, best of Phase A, against a pre-registered ≤89.5% bar; three registered
rival explanations — distribution match / guardrail / polishing — await
per-problem eval tooling). Empirical eval noise floor: seed-spread std ≈ 1pt,
treat single-run differences < 2pt as noise.

## Phase B — instrumentation ✅ (2026-07-05/06; E3)

vLLM offline generation (~10× on eval/filter passes), pass@k/maj@k doubling
curve in `eval.py`, periodic in-training eval, `analysis/windows.py`. E3
regression run certified the driver/torch/tooling stack; same-engine anchors
established (effect sizes are engine-dependent — only same-engine comparisons
count).

## Phase C — Countdown: the difficulty laboratory (~1–2 weeks; the core)

For the reward-density question, Countdown is the superior instrument, not a
detour: **difficulty is generative** (number count / target range dial initial
pass rate by construction — no estimation passes, no stale buckets, no
regression-to-the-mean like E1's filter), **data is infinite** (no prompt-set
overfitting confound, fresh eval problems with tight statistics), the
**verifier is trivial pure Python**, and a **3B/1.5B model with short
completions** iterates in minutes-to-an-hour per run (possibly vLLM-colocated
training). What it won't show — long CoT, realistic reasoning failures — is
Phase D's job.

- **C0**: Countdown task module in `data.py`/`rewards.py` + tests; calibrate
  the difficulty dial against initial pass rate on the chosen model.
- **C1 — the difficulty sweep** (the centerpiece): fixed config, five
  difficulty levels targeting ~90/70/50/30/10% initial pass rate. **Primary
  outcome: eval gain on a fixed held-out band** (Phase A's E5 showed
  mixed-group density does not predict outcome — the naive inverted-U in
  *dynamics* may not be an inverted-U in *gains*); secondary: reward slope,
  entropy trajectory, zero-variance fraction. Adjudicates the E5 rivals
  (distribution match / guardrail / polishing) with adequate power.
- **C2 — knobs at the sweet spot**: group size 4/8/16, temperature 0.7/1.0/1.2,
  `entropy_coef`, clip-higher (`epsilon_high`, the DAPO trick).
- **C3 — difficulty schedules**: curriculum, anti-curriculum, and *adaptive*
  (raise difficulty to hold pass rate ≈ 50% — home-made DAPO dynamic
  sampling; only clean on a generative task).
- **C4 (stretch) — learnability statistics pilot**: which group statistics
  (rollout disagreement, reward variance, trace diversity) predict
  per-problem improvement better than raw pass rate.

## Phase D — MATH: the transfer test (~1–2 weeks)

MATH's role is **external validity**: does the difficulty→dynamics map from
the lab predict the field? Train on MATH-train, evaluate on **MATH500
(eval-only — 500 problems is an evaluation set, never a training set)**.
Known-messy HF availability: use mirrors (`DigitalLearningGmbH/MATH-lighteval`
train, `HuggingFaceH4/MATH-500` eval).

- **D0 — the verifier project, first and separately**: `math_verify`-based
  equivalence checking (fractions, intervals, surds, π-expressions) with a
  proper test suite, built and tested offline before any training depends on
  it. Verifier false negatives don't add noise — they *teach* the model the
  buggy verifier's preferences.
- **D1 — baselines** (cheap post-Phase-B): full MATH500 greedy + maj@8;
  pass-rate estimation over a MATH-train sample → measured difficulty buckets.
- **D2 — one boring baseline run**: random MATH-train sample, 768–1024 token
  budget, `mask_truncated_completions` on, periodic eval. Watch
  `clipped_ratio` and whether completion length *grows* — the first new
  dynamic the previous phases couldn't show.
- **D3 — bucket runs** (easy/median/hard), each with a Phase-C-derived
  prediction pre-registered. Bucket caveat: membership is defined vs the
  initial policy and drifts as training sharpens the model — re-estimate or
  acknowledge.

## Phase E — code rewards, then toy Conductor

Deliberately unplanned in detail; Phases C/D should shape it. Sketch: code
execution rewards (rich partial credit: N tests passed, runtime/syntax
errors) on LiveCodeBench-easy, then the minimal Conductor (SFT on synthetic
workflow traces first — mandatory, cold GRPO would produce all-zero groups —
then tiny GRPO with parseability + correctness rewards, 1–2 local workers).

---

## Reference: hardware envelope (RTX 4090, 24 GB)

- 7B: QLoRA only. Training-time generation must be HF `generate` (a vLLM
  colocate copy is ~15 GB bf16 and TRL can't sync LoRA into a quantized
  engine). Measured E1 footprint: 12.5 GB peak, ~26 s/step at 512 tokens.
- 1.5B/3B: LoRA or full FT (1.5B comfortable; 3B needs adamw_8bit + grad
  ckpt and has no room for the KL reference copy → β=0). vLLM colocate fits →
  the fast-sweep vehicle for Phase C.
- Offline inference (eval/filter/bucketing): vLLM with bf16 7B fits fine —
  no training state on the GPU (Phase B unlock).
- NVIDIA driver 560 caps CUDA at 12.6: torch stays on the cu126 wheel index
  (pinned in pyproject.toml).
