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
The **outcome story flipped, then humbled** (E5: the "wasted compute"
unfiltered run scored 93.0%, best of Phase A; E7's paired McNemar tests then
showed *no* Phase-A endpoint difference is significant at n=200 — even
adapter-vs-base). E7's slice analysis leaves **polishing** as the
best-supported rival (A3's gains concentrate in the mid-difficulty band;
pass@k boundary unmoved), guardrail unsupported, distribution-match partially
contradicted (filtered adapters improved on easy problems they never trained
on). Noise-floor doctrine, final form: seed spread ±1pt, vLLM re-invocation
wobble ±1pt, and 200-problem evals lack power for <3pt claims — use
full-test-set evals (1319) for anything that matters.

## Phase B — instrumentation ✅ (2026-07-05/06; E3)

vLLM offline generation (~10× on eval/filter passes), pass@k/maj@k doubling
curve in `eval.py`, periodic in-training eval, `analysis/windows.py`. E3
regression run certified the driver/torch/tooling stack; same-engine anchors
established (effect sizes are engine-dependent — only same-engine comparisons
count).

## Phase C — Countdown gradient-density laboratory — WRAPPED (E8, E10)

**Status (2026-07-10): wrapped early, pivoted to Phase E.** C0 calibration
(E8) and a partial C1 + D1 convergence study (E10) delivered the core
learnings — most importantly the *methodological* ones (see below) — and the
vanilla single-turn GRPO dynamics vein hit diminishing returns. The C1 sweep
as designed was retired: comparing eval-gain vs g at a fixed 300-step budget
is confounded by convergence time (nothing converges that fast on an
acquisition task), so it couldn't cleanly test the hypothesis. **Robust
takeaways** carried forward: (1) two-phase learning→saturation; (2) the
plateau is *gradient starvation from success* (zero-variance fraction → 0.6);
(3) acquisition timescales ≫ elicitation; (4) a hard statistics discipline —
trust training-side metrics, never read sub-noise wiggles (n=48 eval ±3pt),
need n=500 + ≥3 seeds for any comparison. Parked (would need redesign to
run-to-convergence): C1 D4/D5, seeds, the knob sweeps (temperature is already
at the GRPO default 1.0, so exploratory not selection).

*Original Phase-C framing retained below for reference.*

The organizing variable is **gradient sparsity** — the fraction g of GRPO
groups that carry a nonzero gradient (see [`concepts.md`](concepts.md)).
Countdown is the instrument: **difficulty is generative** (num_numbers ×
max_number dial g by construction — no estimation passes, no stale buckets),
**data is infinite** (no prompt-set-overfitting confound, tight eval stats),
the **verifier is trivial pure Python**. Calibration (E8) showed Countdown is
a pure *acquisition* task with no elicitation regime — it shows the left arm
and gradient-rich peak of the g curve, the complement of GSM8K's right arm —
so **the 7B is used** (spans g 0.05→0.88, learning observable everywhere, and
holds the model fixed vs Phase A). Long CoT / realistic failures are Phase D's
job.

- **C0** ✅ (E8): `tasks/countdown.py` + tests; both difficulty dials; the
  7B g-ladder D1–D5 (g = 0.88 / 0.71 / 0.53 / 0.23 / 0.05).
- **C1 — the gradient-density sweep** (centerpiece): D1–D5 × 3 seeds, fixed
  config. **Primary outcome: eval gain** on fixed held-out sets (same-level +
  full-ladder transfer); secondary: entropy trajectory, zero-variance
  fraction, KL. Prediction (post-E8, *not* inverted-U — no elicitation end):
  gain highest at the gradient-rich levels, falling as g sparsifies; Phase A's
  easy-data advantage has no analog. Caveat: 1-prompt/update amplifies the
  cost of low g (concepts.md), so the sparse-end falloff is partly batch-size.
- **C2 — knobs at the best level**: group size 4/8/16, temperature, entropy
  bonus, clip-higher; **plus prompts-per-update × sparsity** (does a bigger
  batch rescue the sparse regime — separating task from batch-size effects).
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

## Phase E — toy Conductor (NEXT, pivoted here directly from C; E10)

Hierarchical agentic planning — the original motivating goal. A 7B
**conductor** emits a plan → local model **worker(s)** solve sub-tasks →
aggregate → verify; reward = parseable plan + final correctness (our first
*composite* reward, and first *multi-step* rollout). Code RL was considered
as an intermediate and **rejected**: its new infra (code sandbox) is
orthogonal to the Conductor, whose "workers" are just model calls we already
run — so it de-risks the wrong plumbing. The right on-ramp is **degenerate-
first**: (1) trivial fixed plan → 1 worker → verify on GSM8K (orchestration
is the only new variable); (2) real ≤2-step decomposition; (3) worker choice.
Open fork for the planning pass: zero-shot bootstrap (instruct emits
parseable plans; add SFT only if groups come up all-zero) vs the paper's
mandatory SFT warm-start. A full planning pass precedes any build.

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
