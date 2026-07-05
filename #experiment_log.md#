# Experiment log

Living lab notebook. One entry per experiment: setup → results → findings →
follow-ups. Ideas that haven't been run yet live in the [backlog](#backlog)
at the bottom; when one is run, it moves up into a numbered entry.
W&B project: [`kencoken/qwen-grpo`](https://wandb.ai/kencoken/qwen-grpo).

---

## E0 — pipeline smoke test (2026-07-05)

**Setup:** Qwen2.5-1.5B-Instruct, bf16 + LoRA r=16, 20 steps, 64 unfiltered
GSM8K problems, group size 8, max completion 256. W&B run
[`x5jcop1u`](https://wandb.ai/kencoken/qwen-grpo/runs/x5jcop1u).

**Result:** all Stage-0 exit criteria met — both reward curves logged
separately, `kl` curve present (β=1e-3 log-only), completions table, custom
`accuracy`/`unique_answer_rate` metrics, adapter saved. ~2 min wall clock,
~5.3 s/step, 9.1 GB peak.

**Findings:**
- The zero-variance-group phenomenon appeared unprompted at step 8: all 8
  rollouts produced the identical (correct) answer → `unique_answer_rate`
  0.125, loss ≈ 3e-7, grad_norm ≈ 7e-5 — an optimizer step contributing
  nothing. Motivated taking the difficulty filter seriously (see E1).
- `clipped_ratio` spiked to 0.75 on one step at the 256-token cap →
  confirmed 512 for the 7B run.

---

## E1 — Stage 1: 7B QLoRA on difficulty-filtered GSM8K (2026-07-05)

**Setup:** Qwen2.5-7B-Instruct, 4-bit NF4 QLoRA r=16/α=32 (all linear
projections), 300 steps × (8 rollouts of 1 prompt), temperature 1.0,
max completion 512, lr 1e-5 constant + 10-step warmup, β=1e-3 (log-only KL),
TRL loss default (`dapo`). Data: 300 difficulty-filtered GSM8K train problems
(one epoch). W&B run [`nfrzmbjv`](https://wandb.ai/kencoken/qwen-grpo/runs/nfrzmbjv).
Runtime 2h04m (~26 s/step), peak 12.5 GB VRAM.

**Difficulty filter** (`filter_data.py`: 4 rollouts @ temp 1.0 over the first
1500 train problems; kept pass rate strictly in (0,1) → `data/gsm8k_filtered.json`):

```
0/4:   39   all-fail: no gradient
1/4:   39   ┐
2/4:   62   ├ kept 300 (20%)
3/4:  199   ┘
4/4: 1161   all-pass: no gradient (77%)
```

**80% of unfiltered GSM8K would produce zero-gradient groups** for this model.
The filter pass cost ~25 min of GPU time.

**Result** (greedy, first 200 GSM8K test problems):

| | baseline | after 300 steps |
|---|---|---|
| accuracy | 0.865 | **0.920** |
| format compliance | 0.985 | 0.995 |

**+5.5pt held-out accuracy from one epoch over 300 problems.** Stage-1 exit
criterion was "format up, accuracy a bonus" — format had no headroom (see
finding 2), the accuracy bonus showed up instead.

### Findings

**1. The 4-rollout filter is a noisy difficulty estimate and skews easy.**
Two-thirds of kept problems showed 3/4 passes, and a problem with true pass
rate ~0.9 still shows ≤3/4 about a third of the time (regression to the
mean). Consequence: correctness reward was already ~0.7 at step 1 and ~44% of
early groups were all-correct. A better filter: 8 rollouts, keep a stricter
band (0.25–0.625), scan all 7.4k train problems (yield here suggests ~20%).

**2. Format reward was at ceiling from step 0 on the instruct model** (98.5%
baseline compliance → flat 0.2 curve). The classic "format improves first"
dynamic is invisible on an instruct 7B; observing format *emergence* needs
the base-model arm or Countdown.

**3. Entropy collapse pressure, observed live.** 50-step window averages:

| steps | entropy | unique_answer_rate | zero-var groups | mean len | kl |
|---|---|---|---|---|---|
| 1–50 | 0.196 | 0.29 | 42% | 182 | 0.005 |
| 51–100 | 0.170 | 0.21 | 64% | 162 | 0.011 |
| 101–150 | **0.145** | 0.21 | 58% | 166 | 0.021 |
| 151–200 | 0.157 | 0.23 | 62% | 160 | 0.022 |
| 201–250 | 0.177 | 0.25 | 50% | 148 | **0.027** |
| 251–300 | 0.188 | 0.20 | 64% | 169 | 0.016 |

Mechanism: on mostly-correct groups the winners are the *modal* completions,
so updates concentrate probability on already-likely tokens — temp-1.0
samples converge toward greedy decodes (`unique_answer_rate` pinned at its
0.125 floor on most late steps; lengths shrinking). This chokes the learning
signal: zero-variance groups climbed 42% → ~64%. Note the headline reward
curve hides all of this — the variance-family metrics are the ones to watch.

**4. …and self-stabilization: entropy troughs at ~step 130, then recovers.**
The sharpening force is self-extinguishing: it only acts while a group still
has disagreement, and its endpoint (uniform group) has zero gradient — its
own success mutes it. What remains in the gradient pool self-selects toward
frontier problems, where the rare correct rollout is an *atypical* sample, so
updates push probability into low-probability tokens — an entropy-*raising*
force. Net pressure flips sign once easy groups go quiet. Ruled out as
explanations: the KL leash (β=1e-3 is negligible) and LR decay (constant LR).
Since we ran one epoch (each problem seen once), the rising all-correct
fraction reflects *global* distributional sharpening transferring across
problems, not per-problem memorization.

**5. KL measurement subtlety: the late-run KL drop (0.027 → 0.016) is not
"moving back toward init".** The `kl` metric is per-token divergence averaged
over the tokens sampled *that step*, and distributional sharpening was its
dominant component — so when sharpening partially relaxed (finding 4), the
measured KL relaxed with it. Entropy-up and KL-down are largely two views of
the same relaxation. Residual caution: per-step KL also varies with which
problem was sampled, so some of the final-window drop is composition noise.
One seed, one epoch — findings 4–5 are the mechanistically-plausible reading,
not established fact; see backlog for the falsification runs.

---

## Backlog

Roughly ordered by information-per-GPU-hour. Each Stage-2 run: change one
variable, encode it in the run name, add an entry above.

**Directly falsify/confirm E1's dynamics story:**
- **Pure-easy control**: same config on *unfiltered* GSM8K. Prediction from
  finding 4: monotone entropy decline with no recovery (no hard-problem force
  to flip the sign), and a smaller eval gain.
- **Re-shuffle rerun** (new seed, same data): does the entropy trough-and-
  recovery appear at the same training phase (dynamics) or follow the data
  order (composition)?
- **Analysis-only**: split per-step `kl` by group outcome (zero-var vs mixed)
  in run `nfrzmbjv` to separate relaxation from composition noise.

**Fight the collapse (each vs the E1 baseline):**
- Temperature 0.7 vs 1.0 vs 1.2 — depth of the entropy trough vs final eval.
- `entropy_coef` > 0 (explicit entropy bonus).
- Clip-higher (`epsilon_high`, the DAPO trick): let unlikely-but-good tokens
  gain probability faster than the symmetric clip allows.

**Better data:**
- Stricter filter: 8 rollouts, keep 0.25–0.625 band, scan all 7.4k problems.
- MATH levels 3–5 + `math_verify` — raises headroom so the modal answer isn't
  already correct.

**Original Stage-2 grid (stages.md):** group size 4/8/16, LoRA rank 8/16/32,
reward shaping via `reward_weights`, max tokens 256/512, SFT warm start,
β=0.04 real-leash arm.

**Bigger arms:**
- Base model R1-Zero style (7B base, raw-text prompt) — format emergence,
  which the instruct model can't show (finding 2).
- Full-FT vs LoRA on 1.5B/3B (`use_lora false`) — test the "LoRA barely
  changes the dynamics" claim.
- Countdown on Qwen2.5-3B (+ vLLM colocate) — skill acquisition rather than
  elicitation; the fast-sweep vehicle.
