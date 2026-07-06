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
- **A3 pure-easy control** (~3h run, `a3-easy-control`): repro config on
  *unfiltered* GSM8K, compute-matched. Pre-registered (post-E3 revision):
  (1) zero-variance fraction ~70–80% from step 1 (filter histogram: 77%
  all-pass); (2) entropy declines with **no recovery** and KL grows slowly
  (few gradient-carrying steps); (3) same-engine eval gain over base 88.5%
  is ≤ +1pt (vs repro's +2.5pt) — mostly wasted compute.
- **A4 re-seed replication** (~3h run, `a4-filtered-s1`, seed 1) — upgraded
  from contingent after E3: trough is 2/2, recovery 1/2; A4 gives n=3.
  Pre-registered: trough appears mid-run (expect 3/3); recovery explicitly
  *uncertain* (the point is to measure it); final eval within noise of
  repro's 91.0%.

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
