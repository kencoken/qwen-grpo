# Experiment log

Living lab notebook. One entry per experiment: setup → results → findings →
follow-ups. Ideas that haven't been run yet live in the [backlog](#backlog)
at the bottom; when one is run, it moves up into a numbered entry.
W&B project: [`kencoken/qwen-grpo`](https://wandb.ai/kencoken/qwen-grpo).

---

## E8 — Countdown difficulty calibration (2026-07-07)

**Setup:** base Qwen2.5-3B-Instruct, k=8 @ temp 1.0, 200 fresh problems per
dial. Two dials: `num_numbers` (operands) and `max_number` (operand
magnitude — added after the first pass showed num_numbers alone was too
coarse and only spanned the hard end). W&B project `qwen-grpo-countdown`.

**Base pass rates:**

| num_numbers | max_number | pass@1 | pass@8 |
|---|---|---|---|
| 3 | 6 | 0.195 | 0.730 |
| 3 | 12 | 0.171 | 0.680 |
| 3 | 25 | 0.124 | 0.565 |
| 3 | 50 | 0.107 | 0.510 |
| 3 | 99 | 0.071 | 0.405 |
| 4 | 12 | 0.057 | 0.335 |
| 4 | 25 | 0.033 | 0.210 |
| 4 | 50 | 0.021 | 0.130 |
| 4 | 99 | 0.028 | 0.180 |
| 5 | 99 | 0.004 | 0.035 |
| 6 | 99 | 0.001 | 0.005 |

**Load-bearing finding: Countdown-on-3B has no elicitation regime.** Even the
trivial dial (3 numbers, magnitude ≤6) is only 19.5% pass@1 — the ceiling is
~20%. The planned 90/70/50/30/10% pass@1 ladder is unreachable. This is the
correct diagnosis, not a failure: Countdown is a **pure acquisition task**
(the base model is weak everywhere), which is exactly why it was chosen as
the contrast to GSM8K's elicitation regime (E4/E5).

**Consequence — measure difficulty by gradient-carrying fraction, not pass@1.**
For GRPO a group carries gradient iff its rollouts disagree; with all-correct
groups ~nonexistent here, that fraction ≈ **pass@8**. pass@8 spans a clean
monotone 73% → 3.5% across the dials — a strong spread in the reward-density
variable Phase C is actually about. The C1 ladder is therefore defined by
pass@8, and its central prediction changes: not an inverted-U (there is no
too-easy end) but a **monotone-or-plateau in eval gain that falls off as the
gradient-carrying fraction sparsifies** — with the Phase-A "easy data wins"
result having *no analog*, because the polishing mechanism (error-deletion on
mostly-correct groups) cannot operate where no group is mostly-correct.

**Chosen C1 levels** (pass@8 ≈ 2× step; D1 uses max 12 not 6 to avoid too
small a problem space → train/eval overlap):

| level | dial | pass@1 | pass@8 |
|---|---|---|---|
| D1 | (3, 12) | 0.171 | 0.68 |
| D2 | (3, 50) | 0.107 | 0.51 |
| D3 | (4, 12) | 0.057 | 0.34 |
| D4 | (4, 50) | 0.021 | 0.13 |
| D5 | (5, 99) | 0.004 | 0.035 |

Token budget: base completions well under 512 at every dial (format rate
0.55–0.83, no widespread truncation) → keep `max_completion_length=512`.

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

### Discussion

**Was the +5.5pt elicitation or overfitting?** Not overfitting in the
memorization sense: the gain is on held-out test problems and training was a
single epoch (nothing to memorize from). But it is the *cheap* kind of gain.
GRPO with group-relative rewards approximately trains toward the model's own
majority-vote answer, converting sampling inconsistency into greedy
reliability — pass@1 climbs toward where maj@8 already was, plus ~1pt of pure
format cleanup. The model didn't learn math it lacked; it stopped fumbling
math it knew. At an 86.5% baseline the task offers no other kind of headroom,
so "GSM8K is too easy" is correct in that precise sense. This matches the
RLVR-skeptic literature: RL raises pass@1 while base-model pass@k at large k
often stays equal or better — sampling efficiency moves, the capability
boundary doesn't. Testable: if base maj@8 ≈ trained pass@1 and pass@8 didn't
move, the sharpening story is confirmed (see backlog).

**Is Countdown "learning from scratch"?** No — and in a sense nothing in RLVR
is: the reward channel carries a few bits per rollout, far too narrow to
inject knowledge. GRPO can only redistribute probability over behaviors the
model can already emit (its occasional stumbled-into successes are what let
it bootstrap at all). The useful axis is not elicitation-vs-acquisition but
*behavioral distance*: GSM8K-on-instruct reinforces the model's typical
behavior (distance ≈ 0, reliability tuning); Countdown-on-base makes a
vanishingly-rare composition of pretrained components (propose → evaluate →
backtrack, with persistence) into the dominant strategy — elicitation at the
component level, genuinely new at the policy level. Even R1-Zero's "aha
moment" got this reinterpretation (Qwen2.5 base shows self-reflection at
step 0). For visibly reorganizing behavior rather than polishing it,
Countdown is the better instrument.

**What "overfitting" means in a GRPO run.** Held-out validation *does* exist
in RLVR — a held-out prompt set evaluated periodically (TRL: `eval_dataset`);
it's just expensive (every val point costs generation), so the curve is
sparse and train-time metrics fill the gaps. "Overfitting" then fragments
into four failure modes with different detectors:

1. **Prompt-set overfitting** — memorizing a small training prompt set. One
   epoch can't; a multi-epoch run over our 300 problems absolutely could.
   Only held-out prompts detect it.
2. **Verifier overfitting (reward hacking)** — policy exploits the reward
   function; train reward actively misleads. Detectors: reading sampled
   completions, unit-testing the verifier *before* training.
3. **Distributional collapse** — the policy "overfits to its own mode"
   (observed live in this run). Detectors: entropy, unique_answer_rate,
   frac_reward_zero_std, KL — these fire *before* any eval degrades.
4. **Capability forgetting** — better at the task, quietly worse elsewhere.
   Needs broader evals; KL is a crude proxy for distance traveled.

Caveat on naive train/val comparison: train correctness (~0.8 @ temp 1.0 on
deliberately-hard filtered problems) and val accuracy (92% greedy, unfiltered
test) measure different quantities under different distributions — train
reward is a property of the exploration distribution, not a preview of
deployment behavior.

---

## E2 — A2: KL split by group outcome (2026-07-05, analysis-only)

**Question** (pre-registered in the Phase-A backlog): is E1's late-run KL drop
(0.027 → 0.016) composition noise (driven by which problems were sampled) or
genuine relaxation of the sharpening? Discriminator: a drop confined to
zero-variance steps → composition; a drop present in mixed-outcome steps →
relaxation.

**Method:** `analysis/a2_kl_split.py` — E1 run history from the W&B API,
`kl`/`entropy` per 50-step window, split by `frac_reward_zero_std`
(uniform vs mixed groups). Zero GPU.

**Result:**

| steps | kl uniform | kl mixed | ent uniform | ent mixed | n uniform |
|---|---|---|---|---|---|
| 1–50 | 0.0066 | 0.0036 | 0.152 | 0.228 | 21 |
| 51–100 | 0.0111 | 0.0098 | 0.156 | 0.196 | 32 |
| 101–150 | 0.0227 | 0.0194 | 0.130 | 0.166 | 29 |
| 151–200 | 0.0239 | 0.0196 | 0.128 | 0.204 | 31 |
| 201–250 | 0.0279 | 0.0256 | 0.146 | 0.208 | 25 |
| 251–300 | **0.0147** | **0.0190** | 0.174 | 0.214 | 32 |

**Verdict: genuine relaxation, not composition noise.** The drop appears in
*both* strata — mixed-outcome steps fell 0.0256 → 0.0190 (−26%), so the
discriminator lands on relaxation. Two bonus observations:

1. Uniform steps carried *higher* KL than mixed steps in every window through
   step 250 — consistent with E1 finding 5's claim that sharpening (strongest
   on easy problems, whose groups go uniform) was the dominant component of
   measured KL.
2. The reversal is strongest exactly in that uniform stratum (−47%,
   0.0279 → 0.0147, ending *below* the mixed stratum): sharpening relaxed
   most where it had gone furthest. The entropy split agrees: uniform-step
   entropy troughs deeper (0.128 vs mixed's shallow dip) and recovers to its
   highest value in the final window.

**Caveats:** ~25–32 steps per cell, one seed; per-step KL is noisy
(0.005–0.08 range), so treat magnitudes as suggestive. The direction of the
verdict is consistent across both strata, which is what the discriminator
needed. A3's pure-easy control remains the causal test of the mechanism.

---

## E3 — Phase B certification + regression run (2026-07-05/06)

**What changed since E1:** NVIDIA driver 560→595 (CUDA 13.2), torch
2.12.1+cu126 → 2.11.0+cu130 (relaxed to honor vLLM 0.24.0's exact pin),
vLLM offline generation + pass@k/maj@k in `eval.py`, periodic in-training
eval in `train.py`. This run certifies the whole bundle before A1/A3.

**Certification battery (done):**

| check | result |
|---|---|
| base greedy, 200 (vLLM) | **88.5%** (HF/E1 measured 86.5% — engine shift, 4 problems) |
| E1 adapter greedy, 200 (vLLM) | **90.5%**, format 100% |
| pass@8 coherence (base, n=50, t=1.0) | pass@1 0.875 < maj@8 0.96 < pass@8 0.98 ✓ |

**Lesson locked in: effect sizes are engine-dependent** — the E1 gain reads
+5.5pt on HF generate and +2.0pt on vLLM (both engines agree on direction;
borderline generations flip). Standing policy: only same-engine comparisons
count; the vLLM anchors are now base 88.5% / E1-adapter 90.5%.
(Bonus pre-A1 signal, n=50 so indicative only: base maj@8 (0.96) ≥ trained
pass@1 (0.905–0.92) — consistent with the sharpening story.)

**Pre-registered expectations for the regression run** (`e1-repro-newstack`,
exact E1 config + seed, new stack, periodic eval on):

1. Not bit-identical to E1 (new kernels ⇒ different rollouts), but
   statistically equivalent training dynamics: reward curves same shape;
   entropy trough ~mid-run with late recovery; zero-variance fraction rising
   from ~40% toward ~60%; KL rising then relaxing late.
2. Periodic eval curve (new instrumentation) appears in W&B without errors
   and shows no divergence.
3. Final adapter greedy eval (vLLM, 200): within ±2.5% of the E1 adapter's
   same-engine 90.5%, and above the same-engine base 88.5%.
4. Format compliance ≥ 99.5%.
5. If the trough-and-recovery reproduces at the same training phase with the
   same seed on different kernels, that's partial A4 evidence for "dynamics,
   not data order".

**Result** (run [`upkp33jc`](https://wandb.ai/kencoken/qwen-grpo/runs/upkp33jc);
launch note: two false starts — an eval-batch divisibility crash, then
24-min evals at batch 4, fixed at batch 16 (~8 min); the skipped smoke test
would have caught the first one, lesson re-learned):

| expectation | verdict |
|---|---|
| 1. statistically equivalent dynamics | **partial** — see below |
| 2. periodic eval curve works | ✓ (6 evals, eval length dips then recovers) |
| 3. final greedy within ±2.5% of 90.5%, above 88.5% | ✓ **91.0%** |
| 4. format ≥ 99.5% | ✓ 100% |
| 5. same-phase trough = partial A4 evidence | ✓ for the trough |

Dynamics, per 50-step window (E1 → repro): correctness 0.77→0.89 vs
0.77→0.90 ✓; zero-var 42→64% vs 42→62% ✓; entropy trough at the *same phase*
(101–150: 0.145 vs 0.131) ✓; **but the late-run relaxation did not
reproduce** — repro entropy stays in the trough (0.149 final vs E1's
recovery to 0.188) and KL climbs monotonically to 0.032 (E1 relaxed
0.027→0.016). Completion length recovered late in *both* runs, now decoupled
from entropy.

**Verdict: stack and tooling certified** (endpoints, instrumentation, and
eval anchors all pass; A1/A3 unblocked) — **and E1 finding 4 is revised**:
the entropy *collapse* and its timing are robust across kernels; the
*self-stabilization/recovery* is not — it may be a stochastic excursion
rather than a systematic equilibrium (E2's KL-split showed E1's late drop
was real *within that run*, but not that it generalizes). A3 (pure-easy
control) and A4-style replication now carry the burden of settling whether
the frontier-dominated-gradient mechanism produces recovery reliably,
sometimes, or rarely.

---

## E4 — A1: pass@k / maj@k audit (2026-07-06, inference-only)

**Pre-registered:** (a) base maj@8 ≈ trained greedy pass@1 (0.905–0.910);
(b) trained pass@64 does not exceed base pass@64 (sharpening moves sampling
efficiency, not the capability boundary).

**Method:** k=64 samples at temp 1.0, 200 test problems, vLLM; pass@k via the
unbiased estimator, maj@k by plurality over the first k (`eval.py` doubling
curve). Three models: base, E1 adapter, repro adapter.

| k | base pass@k | E1 pass@k | repro pass@k | base maj@k | E1 maj@k | repro maj@k |
|---|---|---|---|---|---|---|
| 1 | 0.868 | 0.899 | 0.903 | — | — | — |
| 8 | 0.973 | 0.971 | 0.975 | 0.930 | 0.935 | 0.935 |
| 64 | **0.990** | **0.985** | **0.985** | 0.945 | 0.950 | 0.940 |

**Verdict:**

- **(b) confirmed cleanly.** Trained pass@64 ≤ base pass@64 (0.985 vs 0.990);
  the curves converge by k≈4. The capability boundary did not move (if
  anything a hair down, matching the RLVR-skeptic literature). The maj@k
  ceiling (~0.945) is also identical across all three models — training
  didn't change what the ensemble knows, only how often single samples hit it.
- **(a) qualitatively right, quantitatively undershot** — in the direction the
  n=50 preview hinted: base maj@8 (0.930) sits *above* trained greedy pass@1
  (0.905–0.910). RL harvested roughly **half** the majority-vote headroom
  (+2.0–2.5pt of the +4.5pt gap over base greedy).
- Sharpening seen directly at temp 1.0: base pays a 1.7pt sampling penalty
  (greedy 0.885 → sampled 0.868); the trained models pay ~0.5pt
  (0.910 → 0.903). Training mostly *removed the cost of sampling*.

**E1-discussion claim revised:** "trained pass@1 ≈ base maj@8" overstated it;
the accurate statement is *trained pass@1 closed about half the distance from
base pass@1 to base maj@8, with the pass@k boundary unmoved*. Mechanism
(consistency, not capability) stands. Also noteworthy: maj@k saturates by
k≈16 for all models — self-consistency has its own ceiling well below
pass@64, i.e. the ensemble *knows* answers it cannot *vote in*.

---

## E5 — A3: pure-easy control (2026-07-06)

**Setup:** repro config, `--dataset unfiltered` (first 300 GSM8K train
problems), seed 0, 300 steps. Run
[`n5vs16yt`](https://wandb.ai/kencoken/qwen-grpo/runs/n5vs16yt).

**Scoring the pre-registered predictions:**

| # | prediction | verdict |
|---|---|---|
| 1 | zero-var ~70–80% from step 1 | ✓ (64% first window, 76–86% after) |
| 2 | entropy declines, **no recovery**; KL slow | ✓ (0.185→0.140 monotone; KL 0.016 vs repro's 0.032) |
| 3 | eval gain ≤ +1pt (mostly wasted compute) | **✗ badly: 93.0%** — the *best* adapter yet (repro 91.0, E1 90.5) |

Dynamics (windows): corr 0.90→0.955, completion length *stable* (~182–191,
no shrink phase unlike the filtered runs' dip to ~153), smooth entropy
decline with no trough-and-recovery structure.

**What prediction 3 got wrong.** The "zero-variance ⇒ wasted compute ⇒ no
gain" chain treated all gradient-carrying groups as equal *signal*. Candidate
revision: signal **quality** differs by difficulty. In a mostly-correct group
the advantage isolates the single wrong rollout — low-noise "polishing"
toward the model's own reliable behavior. In a hard mixed group the advantage
reinforces rare successes, which may be lucky/atypical paths — higher-variance
signal. Since E4 showed the gains *are* consistency-polishing, easy data may
simply be the better consistency teacher per gradient-carrying step. The
~25% of A3 steps that carried gradient did more per step for eval than the
~50% in the filtered runs.

**Caveats, firmly:** one seed per condition; the A3-vs-repro gap (93.0 vs
91.0, n=200) is ~4 problems, near the noise floor for a *pairwise* claim —
but the pre-registered bar was ≤89.5%, and 93.0 clears that by well over
noise. Also two things changed at once relative to repro (difficulty AND
which problems), inherent to the design. **Implication for the program:**
mixed-group *density* is not a sufficient predictor of eval gain — this
sharpens Phase C1 (difficulty sweep with eval gain as primary outcome, not
just dynamics) and directly motivates the learnability-score line (C4).
The E1 finding-1 framing ("80% wasted compute") stands for *dynamics-per-step*
but not for *outcome* — revised accordingly.

**Discussion addendum (post-A4): three registered rival explanations for the
+4.5pt.** (1) **Distribution match** — you improve where you practice; the
test is ~80% easy problems, which only A3 trained on. Predicts filtered
adapters ≈ base on the easy slice (no harm, just no gain there). The
parsimony favorite. (2) **Guardrail** — filtered training actively *degrades*
easy-problem behavior because nothing in its training signal penalizes that;
easy data in the mix re-enters the gradient the moment a solid problem starts
failing. Predicts filtered adapters < base on the easy slice; probably needs
longer/stronger runs than 300-step LoRA to bite. (3) **Polishing** — a
7-of-8-correct group's advantage mostly *deletes the rare error* (small, safe
update on verified behavior) while a 1-of-8 group's mostly *amplifies a rare
success of unknown quality* (large, risky bet); per gradient-carrying step,
easy-mixed groups are better consistency teachers. Predicts A3's gains
concentrate on problems where base was right most-but-not-all of the time,
and an E4-style audit of the A3 adapter shows the same
boundary-unmoved/sampling-penalty-removed signature. All three require
per-problem eval outputs to test (see backlog).

---

## E6 — A4: re-seed replication, and the Phase-A dynamics reckoning (2026-07-06)

**Setup:** repro config, seed 1, filtered data. Run
[`s9orm4g2`](https://wandb.ai/kencoken/qwen-grpo/runs/s9orm4g2). Final greedy
eval **89.0%**, format 100%.

**Scoring the pre-registered predictions:**

| # | prediction | verdict |
|---|---|---|
| 1 | entropy trough mid-run (expect 3/3) | **✗ as stated** — A4 shows a noisy decline with a mid-run bump, no clean trough. What *is* 3/3: entropy declines ~0.20 → ~0.15 |
| 2 | recovery: measure it | **1/3** (E1 only). Combined with A3 (0/1 on easy data): the "self-stabilization" is best treated as a stochastic excursion, not a phenomenon |
| 3 | final eval within noise of repro's 91.0% | ✓ (89.0%, Δ2pt) — but barely above base (88.5%) |

KL adds the sharpest replication lesson: end-of-run KL across the three
same-config-different-kernel/seed runs is **0.016 / 0.032 / 0.062** — a 4×
spread. Fine KL trajectory structure carries almost no information at this
power; only coarse magnitude does.

**The Phase-A eval ledger** (greedy, vLLM, same 200 problems):

| run | data | eval | gain vs base |
|---|---|---|---|
| base | — | 88.5% | — |
| E1 adapter | filtered, seed 0 (old stack) | 90.5% | +2.0 |
| repro | filtered, seed 0 | 91.0% | +2.5 |
| A4 | filtered, seed 1 | 89.0% | +0.5 |
| A3 | **unfiltered**, seed 0 | **93.0%** | **+4.5** |

Three filtered runs give mean 90.2%, seed-spread std ≈ 1.0pt — our first
empirical **noise floor**: single-run endpoint differences under ~2pt are
not interpretable. A3 sits ~2.8σ above the filtered mean, so "easy data
matched or beat filtered data" survives the noise-floor test (n=1, confounds
noted in E5); "filtered beats base" barely survives it (mean +1.7pt).

**Standing revisions after Phase A** (supersedes E1 findings 4–5 and parts
of E3/E5 phrasing):

1. *Robust:* entropy declines ~25% in every run; zero-variance fraction is
   set by data difficulty (huge, unmistakable effect); completion length
   shrinks on filtered data, stays flat on easy data; GRPO gains on this
   task are consistency, not capability (E4, clean).
2. *Noise until proven otherwise:* entropy trough timing, late recovery,
   KL relaxation, and any single-run endpoint difference < 2pt. E1's
   self-stabilization mechanism story is retired as unconfirmed — the honest
   epitaph is that GSM8K-on-7B compresses all dynamics into too narrow a band
   for these effects to be resolved (the core argument for Phase C's
   difficulty dial, where dynamic range is constructed, not hoped for).
3. *Open, now with three registered rival explanations for A3's +4.5pt*
   (see E5 discussion): train/test distribution match (parsimony favorite),
   guardrail (easy data as self-activating anti-drift regularizer —
   distinguishable via filtered-adapter-vs-base on the easy slice),
   polishing (error-deletion vs success-amplification gradient quality —
   distinguishable via where gains concentrate). All three need per-problem
   eval outputs (tooling gap) and are properly answered by Phase C1/C4.

---

## E7 — rivals test battery (2026-07-06, inference-only)

**Question:** which of the three registered explanations for A3's +4.5pt
(E5 addendum) survives per-problem analysis — and which Phase-A endpoint
differences are statistically real at all?

**Method:** per-problem outcomes added to `eval.py` (`data/evals/*.json`);
battery of 7 vLLM evals on the same 200 test problems (base greedy, base k=8
for difficulty labels, four adapters greedy, A3 k=64); `analysis/e7_rivals.py`
computes paired McNemar tests, difficulty-slice accuracies (easy = base 8/8,
mid = 4–7/8, hard = 0–3/8), and the A3 pass@k signature.

**Pre-registered scoring rules** (written before the battery ran):

| rival | supported if |
|---|---|
| distribution match | filtered adapters ≈ base on the easy slice (no harm, no gain), A3 gains spread over easy+mid |
| guardrail | filtered adapters clearly *below* base on the easy slice (degradation) |
| polishing | A3 gains concentrate in the mid band (4–7/8), and A3 pass@64 ≈ 0.985–0.990 (boundary unmoved) |

Also recorded: McNemar p-values for A3-vs-each-filtered and each-adapter-vs-
base — the definitive word on Phase-A endpoint claims. A null result (all
rivals unsupported / differences insignificant) is a recordable outcome:
it would say A3's edge is seed noise, arbitrated later by C1 or a replicate.

**Results.** First, a methods finding: re-running the *same* greedy evals
shifted aggregates by ±1–2 problems vs the E6 ledger (base 0.890 vs 0.885,
repro 0.900 vs 0.910, A3 0.920 vs 0.930) — vLLM greedy is not
invocation-deterministic (batching/reduction order). Same-invocation
comparisons only; the noise floor grows again.

**McNemar: no Phase-A endpoint difference is statistically significant.**

| comparison | discordant (+/−) | p |
|---|---|---|
| E1 vs base | +9/−6 | 0.61 |
| repro vs base | +8/−6 | 0.79 |
| A4 vs base | +9/−10 | 1.00 |
| **A3 vs base** | **+9/−3** | **0.15** |
| A3 vs repro | +6/−2 | 0.29 |
| A3 vs A4 | +10/−3 | 0.09 |

With models agreeing on ~90% of problems, 200 of them leave ~12 discordant
pairs — hopelessly under-powered. **Even "GRPO improved on the base model"
is not established by any single Phase-A adapter at n=200.** E5's "falsified
badly" is tempered to "suggestive": A3-vs-base is the strongest signal in the
table but p=0.15. E6's "2.8σ" framing is superseded by these paired tests.

**Slices** (greedy accuracy; slice = base pass count over k=8 at t=1.0):

| slice | n | base | E1 | repro | A4 | A3 |
|---|---|---|---|---|---|---|
| easy 8/8 | 118 | 0.966 | 0.992 | 0.992 | 0.975 | 0.992 |
| mid 4–7/8 | 69 | 0.899 | 0.899 | 0.899 | 0.855 | **0.942** |
| hard 0–3/8 | 13 | 0.154 | 0.154 | 0.077 | 0.231 | 0.154 |

**Scoring the rivals** (each sub-claim individually under-powered; the
*pattern* is the evidence):

- **Guardrail: unsupported.** Filtered adapters sit *above* base on the easy
  slice (0.992 vs 0.966), not below — no degradation to guard against at
  300-step LoRA scale, as suspected.
- **Distribution match: partially contradicted.** Filtered adapters improved
  on the easy slice *despite never training on easy problems* — consistency
  gains generalize across difficulty; "you improve where you practice" is
  too crude.
- **Polishing: best supported.** A3's gains concentrate exactly in the mid
  band (0.899 → 0.942, while both seed-0 filtered adapters got *zero* there),
  and its pass@k signature matches the prediction: pass@64 0.985 vs base
  0.990 (boundary unmoved), sampled pass@1 0.868 → 0.903 (penalty removed).

**Verdict:** polishing wins the pattern-match; nothing wins significance.
The honest summary of Phase A's endpoint story: *GRPO on GSM8K produces
small consistency gains whose per-comparison significance is beyond a
200-problem eval's power; the easy-data run's edge is real-looking in
structure (mid-band concentration) but unproven in magnitude.* Follow-up
that would settle it at inference prices: full-test-set greedy evals
(1319 problems, ~20 min each on vLLM) → backlog; C1 remains the
adequately-powered instrument.

---

## Backlog

Roughly ordered by information-per-GPU-hour. Each Stage-2 run: change one
variable, encode it in the run name, add an entry above.

Organized by the phase plan in `stages.md` (A → E). Pre-registration rule:
write the prediction here before launching the run.

**Phase A — close E1's open claims:**
- ~~**A1 pass@k / maj@k audit**~~ → done, see E4: boundary unmoved (confirmed),
  RL captured ~half the majority-vote headroom.
- ~~**A2 KL-split analysis**~~ → done, see E2: genuine relaxation, present in
  both strata.
- ~~**A3 pure-easy control**~~ → done, see E5: dynamics predictions held,
  outcome prediction failed badly (93.0%, best adapter of Phase A).
- ~~**A4 re-seed replication**~~ → done, see E6: recovery 1/3 (retired as
  unconfirmed), KL end-values spread 4× across seeds, eval noise floor ≈
  2pt established.

**Phase-A follow-ups:**
- ~~Per-problem eval outputs~~ / ~~A3 pass@k audit~~ / ~~slice comparison~~
  → done, see E7 (polishing best-supported; nothing significant at n=200).
- **Full-test-set greedy evals** (1319 problems, ~20 min each on vLLM):
  6.5× the discordant pairs → the cheap way to give Phase-A endpoint claims
  real power. Candidate first task alongside Phase C0.
- **A3 seed replicate** (~3h training): optional overnight filler; C1
  answers the underlying question with proper power anyway.

**Phase B — instrumentation:**
- vLLM path for offline generation in `eval.py`/`filter_data.py` (training
  untouched; ~10× on bucketing/eval/pass@k passes).
- Periodic held-out eval during training (every ~50 steps → W&B) — the
  two-point before/after becomes a validation curve.
- pass@k / maj@k support in `eval.py`.
- GSM8K regression run (E1 config) to certify the changed tooling.

**Phase C — Countdown difficulty laboratory (3B/1.5B, fast sweeps):**
- C0: task module + tests; calibrate the difficulty dial vs initial pass rate.
- C1 **difficulty sweep** (centerpiece): five levels targeting ~90/70/50/30/10%
  initial pass; measure reward slope, entropy trajectory, zero-variance
  fraction, transfer. Prediction: inverted U, echoing E1.
- C2 knobs at the sweet spot: group size 4/8/16, temperature 0.7/1.0/1.2,
  `entropy_coef` > 0, clip-higher (`epsilon_high`, DAPO).
- C3 difficulty schedules: curriculum vs anti-curriculum vs adaptive (hold
  pass rate ≈ 50% — home-made DAPO dynamic sampling).
- C4 (stretch) learnability-statistics pilot: does rollout disagreement /
  trace diversity predict per-problem improvement better than pass rate?
- (fits here if wanted) **Deliberate prompt-set overfit** demo: many epochs
  over a small fixed problem set with periodic eval — train reward climbs
  while held-out stalls. Cheap on Countdown.

**Phase D — MATH transfer test:**
- D0 **verifier project first**: `math_verify` equivalence checking + test
  suite (fractions, intervals, surds, π), offline, before any training uses
  it. Data via mirrors: `DigitalLearningGmbH/MATH-lighteval` (train),
  `HuggingFaceH4/MATH-500` (eval-only, full 500, fixed seeds).
- D1 baselines: MATH500 greedy + maj@8; pass-rate buckets over MATH-train.
- D2 one boring baseline run: random sample, 768–1024 tokens,
  `mask_truncated_completions`, periodic eval; watch `clipped_ratio` and
  length *growth* — the first dynamic earlier phases can't show.
- D3 bucket runs (easy/median/hard) with Phase-C-derived pre-registered
  predictions; re-estimate buckets if drift matters.

**Unscheduled / opportunistic (slot in where a phase makes them cheap):**
- Base model R1-Zero style (7B base, raw-text prompt) — format emergence,
  which the instruct model can't show (E1 finding 2).
- Full-FT vs LoRA on 1.5B/3B (`use_lora false`) — test the "LoRA barely
  changes the dynamics" claim; natural fit alongside Phase C.
- β=0.04 real-leash arm; LoRA rank 8/16/32; reward shaping via
  `reward_weights`; SFT warm start (mandatory anyway for Phase E Conductor).
