# Toy Conductor — task preparation & context

*A self-contained briefing. Someone reading only this document should have
everything needed to draft a full plan for the toy-Conductor experiments. It
states context, objectives, constraints, reusable assets, and the open design
forks — it is **not** itself the plan.*

Date: 2026-07-14. Repo: `/home/ken/qwen-grpo`.

---

## 1. Where this sits — project context

This repo is a **learning-oriented GRPO study** on a single RTX 4090. The
success criterion has always been *intuition*, not benchmark scores:

> "I can predict how changing group size, temperature, reward shaping, and
> max length affects training."

Work so far (see `experiment_log.md`, entries E0–E10, and `concepts.md`):

- **Phase A/B (GSM8K, 7B QLoRA GRPO):** built and hardened the pipeline;
  learned the sharpening/elicitation dynamics, the pass@k picture, and a hard
  **statistics discipline** (single noisy runs mislead; need n=500 evals +
  ≥3 seeds; never read sub-noise wiggles).
- **Phase C (Countdown, acquisition task):** learned the two-phase
  learning→saturation dynamic and that the plateau is **gradient starvation
  from success** (as the model succeeds, groups go all-correct → zero
  variance → zero gradient). Concluded vanilla single-turn GRPO dynamics are
  largely mined.

The **toy Conductor is the original motivating goal** — the reason the GRPO
dynamics were studied in the first place. We are now pivoting straight to it.

### What the "Conductor" is (from prior planning; confirm specifics if repro'ing)

A paper (Qwen2.5-7B, GRPO, ~200 iterations, 4 questions × 64 rollouts,
2× H100 80GB) in which a **"conductor" model is trained with RL to emit a
*workflow* — a structured plan that decomposes a problem and delegates
sub-tasks to *worker* LLMs.** Workers execute; the final answer is checked.
Reward ≈ **parseable workflow + final-answer correctness.** The expensive part
is the online RL loop *plus worker calls* (~3 worker steps/workflow on
average → ~150k+ worker calls at paper scale). **Paper-scale reproduction is
explicitly out of scope** on a 4090; we build a *toy* version to learn the
dynamics of hierarchical/agentic RL, debugging locally.

*Caveat: the specific-paper details above come from earlier planning notes,
not a fresh read. A planner intending close reproduction should verify them;
for our toy/learning goal the exact paper numbers don't matter.*

---

## 2. What the toy Conductor task IS

The rollout, per training example, becomes **multi-step**:

1. **Conductor** (the 7B model being RL-trained) reads the problem and emits a
   **plan** in a fixed, parseable format (e.g. a short list of sub-tasks, each
   routed to a worker).
2. **Worker(s)** (model calls) execute each sub-task, producing intermediate
   results.
3. **Aggregation** combines worker outputs into a final answer (either a final
   conductor step, or a deterministic combiner).
4. **Verify** the final answer against ground truth (our existing verifiers).

**Reward is composite** — the first time in this project: e.g.
`+format` (plan parses / is well-formed) `+correctness` (final answer right),
possibly with intermediate shaping. Only the *conductor's* tokens receive
gradient; workers are treated as a (possibly frozen) environment.

### What is genuinely new here (vs everything in Phases A–C)

- **Multi-step rollout** with an external process (worker generation) *inside*
  the reward computation — the "online RL loop + worker calls" cost.
- **Composite / structured reward** — combining format, parseability, and
  final correctness (reward-shaping surface we've never exercised; also the
  canonical silent-failure spot — a lenient parser rewards garbage plans).
- **Orchestration logic** — parse plan → route to workers → aggregate. This is
  the core novelty and the thing only the Conductor can teach us.
- **Credit assignment** over a plan whose value depends on downstream worker
  outputs the conductor doesn't control.

*What is NOT new / already handled:* the worker "calls" are just LLM
generation, which the pipeline already does — there is **no code sandbox or
subprocess execution** here (a code-RL intermediate was considered and
rejected precisely because its sandbox infra is orthogonal to this).

---

## 3. Objectives (what we want to learn)

**Objective: learning the GRPO/worker *dynamics* of a hierarchical setting,
including whether GRPO can teach *orchestration* (decompose/plan) — but not
model *selection* (choosing the right model among many).** Orchestration is in
scope and is the headline outcome; selection is out of scope. This means a
**single worker** (§6 fork 2), and shapes the dataset (§7) and baseline
(§6 fork 5).

Primary (learning-oriented, in priority order):

1. **Can GRPO teach a model to orchestrate?** — the headline question. Does the
   conductor learn, via RL, to emit plans that (executed by the single worker)
   solve problems it wouldn't solve as well in one direct pass?
2. **The new dynamics *of* that learning:** how does a *composite* reward
   behave (does one component dominate / get hacked)? How does *multi-step*
   credit assignment play out? Does cold-start produce all-zero groups
   (forcing SFT)? — i.e. the mechanics of *how* (1) happens.
3. **Does hierarchy earn its keep — against a *compute-matched* baseline?**
   The honest test is not "beats one direct call" but "beats maj@N of the same
   model at equal inference budget" (see §6 fork 5). Going in, we accept a
   *null* result is plausible and still informative ("here's the
   compositionality gap we could/couldn't open, and why").

Explicit **non-goals:** the paper's scale/benchmark; learned model selection
(multiple heterogeneous workers); frontier/API workers; anything that doesn't
fit the 4090 dev loop.

---

## 4. Constraints

### Hardware / stack (fixed)

- **1× RTX 4090, 24 GB.** Everything must fit and run here for the dev loop.
- Python 3.12; **TRL 1.7.1** `GRPOTrainer`; torch 2.11.0+cu130 (driver 595,
  CUDA 13.2); vLLM 0.24.0; peft 0.19.1; bitsandbytes 0.49.2; wandb 0.28.0.
- Measured envelope: **7B QLoRA training ≈ 12.5 GB peak, ~26–46 s/step**
  (single-turn, group 8, 512 tokens). Base 7B bf16 inference ≈ 15 GB alone.
  Training-time generation uses **HF `generate`** (vLLM colocate does *not*
  fit alongside 7B QLoRA training).

### The binding constraints this creates

- **Memory: the conductor (7B QLoRA, training) and the worker must coexist.**
  Options a planner must weigh:
  - *Worker = the conductor's own base model with the LoRA adapter disabled* —
    **zero extra memory** (the base weights are already resident; this is how
    TRL computes the KL reference). Strong default for the 4090. Downside: no
    worker-capability diversity.
  - Small separate worker (Qwen 1.5B/3B) in bf16 (~3–6 GB) or 4-bit (~1–2 GB).
  - Reusing the *same* 7B as a second bf16 copy → **does not fit** alongside
    training. API workers → out of scope for the dev loop.
- **Throughput: worker calls multiply generation.** A group-8, 2-step-workflow
  training step ≈ 8 × (1 plan + ~2 worker calls) = ~24 generations vs 8 for
  single-turn. Expect **several× slower steps** than Phase C. Implications:
  keep group size small (4–8), workflows short (≤2 steps), completions short,
  datasets small (100–300 problems), and consider serving workers via a fast
  path (but mind memory).
- **Statistics discipline (carried over, non-negotiable):** any comparison
  needs n=500-scale evals + ≥3 seeds; trust training-side metrics over noisy
  eval; never read sub-noise wiggles. (We were fooled 3×; see E10.)

### Decisions already taken (treat as given)

- **Degenerate-first staging** to isolate bugs (see §7).
- **No code-RL intermediate** (sandbox infra orthogonal to this).
- **Reuse the existing codebase** rather than rebuild (see §5).
- **Underlying problems = GSM8K first** — trivial verifier, so orchestration
  is the *only* new variable.

---

## 5. Reusable assets (existing codebase)

- **`train.py`** — `Config` dataclass + TRL `GRPOTrainer` wiring; QLoRA/LoRA
  switches; periodic held-out eval; `WANDB_LOG_MODEL=false` needed to avoid an
  artifact-upload crash (see E10 saga). Reward funcs passed as a list →
  supports composite rewards natively; `reward_weights` in `GRPOConfig` shapes
  them.
- **`tasks/`** — a "task" = its data + verifier, behind a contract
  (`load_train`, `load_eval`, `correctness_reward`, `verify`, `canonical`);
  registry in `tasks/__init__.py`; growth rule "single file → package when it
  outgrows a sitting." A `conductor` task/package would slot in here.
  `tasks/gsm8k.py` gives the underlying problems + a trivial exact-match
  verifier to reuse.
- **`rewards.py`** — shared format/parse helpers (`<think>/<answer>` contract,
  answer extraction, normalization). A conductor plan-format verifier would
  live with the task and be **unit-tested first** (the repeatedly-paid lesson).
- **`eval.py`** — vLLM offline generation, pass@k/maj@k, per-problem JSONs
  (for paired stats). Would need a mode that runs the *full orchestration*
  (plan → workers → aggregate) to score the conductor end-to-end.
- **`filter_data.py`** — difficulty filtering (may matter for cold-start).
- **`analysis/windows.py`** — pulls the 50/80-step training-metric window
  tables from wandb (the low-noise signal we learned to trust).
- **`concepts.md`** — the gradient-sparsity / statistics mental models;
  **`experiment_log.md`** — full history E0–E10; **`stages.md`** — roadmap
  (Phase E = this task).
- Working wandb setup (project `qwen-grpo-countdown` for Phase C; a new
  project e.g. `qwen-grpo-conductor` is the pattern for a new phase). Note:
  train online with `WANDB_LOG_MODEL=false`; wandb model-artifact logging is
  the one thing that crashes runs.

---

## 6. Open design forks (for the planner to resolve)

1. **Cold-start: SFT warm-start vs zero-shot bootstrap.** The paper SFTs on
   synthetic workflow traces first, because a cold model rarely emits valid
   plans → all-zero groups → no gradient. But a 7B-Instruct followed our
   `<think>/<answer>` format zero-shot; it *may* follow a simple plan format
   often enough to bootstrap GRPO without SFT. **Recommended to try
   zero-shot bootstrap first** (fast), add SFT only if groups come up
   all-zero. Planner should design the cold-start check (measure fraction of
   parseable/nonzero-reward groups at step 0) and the SFT fallback (how to
   synthesize traces).
2. ~~**Worker model.**~~ **DECIDED (§3 objective lock): single worker.** Default
   = adapter-disabled base 7B (memory-free, capable; same trick TRL uses for
   the KL reference) — no extra model resident. A small separate worker
   (1.5B/3B) is an *optional* later variation, not part of v1. Multiple
   heterogeneous workers (the paper's routing goal) is out of scope.
3. **Plan / workflow format.** What exactly the conductor emits and how it's
   parsed — must be simple enough to bootstrap, strict enough to prevent
   reward hacking, and unit-testable. (e.g. a fenced list of sub-questions;
   or a small JSON schema.) Define the parser + its test suite up front.
4. **Aggregation.** Deterministic combiner vs a final conductor "synthesize"
   step (the latter adds another generation + more credit-assignment
   complexity).
5. **Evaluation — the compute-matched baseline is the crux.** Final accuracy
   alone is *not* enough: a conductor calling N workers spends N× the inference
   compute, so it must be compared against **maj@N of the same model at equal
   budget**, not against one direct call. Only that separates "orchestration
   works" from "we spent more compute." Also report conductor-direct and
   single-worker-direct for context. Held-out n=500-scale, ≥3 seeds (the
   statistics discipline).
6. ~~**Underlying task difficulty.**~~ **Resolved into criteria + candidates —
   see §7 Task selection.** (GSM8K is Stage-1-plumbing only; it is too easy /
   not decomposable-with-benefit for the real experiment.)
7. **Reward shape.** Weights on format vs correctness; whether to give
   intermediate credit; how to prevent the trivial-passthrough optimum.

---

## 7. Task selection (the pivotal design choice)

With the objective locked to *dynamics* and a *single* worker, the dataset is
what determines whether the experiment is meaningful. It is genuinely hard —
even the original paper drew review criticism for its task choices — so we go
in clear-eyed. **GSM8K is Stage-1-plumbing only**: Qwen-7B already solves ~86%
in one pass (no headroom) and its problems don't benefit from decomposition,
so it guarantees the trivial-passthrough optimum. The real task must satisfy
four criteria — the first two are yours, the last two are the *binding* ones:

- **(i) Naturally decomposable into *heterogeneous* parts** — sub-tasks of
  genuinely different kinds (e.g. lookup + arithmetic + comparison), so the
  conductor learns *what* to decompose, not just *that* it should.
- **(ii) Hard enough** that decomposition has a chance of beating a single
  simple call (real single-pass headroom).
- **(iii) Sub-parts solvable by the worker even when the whole isn't, and
  self-contained** — facts given in the prompt (or questions carefully
  selected). If single-pass failure is *ignorance*, isolating sub-questions
  can't rescue it — this is the parametric-recall trap in real multi-hop QA.
- **(iv) Single-pass failure must be *systematic*, not *variance*** — the
  deepest criterion, and the fair-baseline problem in disguise. Decomposition
  beats compute-matched **maj@N** only if the model fails the composed problem
  *consistently* (a compositionality gap: reliably wrong on the whole,
  reliably right on the parts) rather than *noisily* (which sampling already
  fixes). On "just harder math," failure is often variance → maj@N wins →
  orchestration looks pointless. This criterion is what makes hierarchy earn
  its keep, and is likely where the paper's tasks drew fire.

**Candidates:**

- **Synthetic self-contained compositional task** *(recommended v1)*: facts/
  rules given in-prompt; question requires chaining heterogeneous ops. Only
  option that lets us *dial* the compositionality gap directly (guarantees iv),
  removes the recall confound (iii), makes heterogeneity explicit (i), and
  fits our proven controllable-synthetic comfort zone (as Countdown did).
- **DROP** (discrete reasoning over a passage — extract/count/arithmetic/
  compare): the strongest *realistic* option — real, off-the-shelf,
  self-contained (facts in passage), heterogeneous, hard, verifiable (EM/F1).
  Good cross-check once the synthetic version shows orchestration helping.
- **Multi-hop QA with a compositionality gap** (Bamboogle-style; Press et al.
  2022): principled and literature-grounded, but hits (iii) hard (needs
  parametric recall → careful selection to avoid measuring ignorance), parts
  are homogeneous (all retrieval, weak on i), and Bamboogle is tiny (~125 Qs).
- **FinQA / TAT-QA** (numerical reasoning over tables+text): heterogeneous,
  hard, verifiable, self-contained — solid but domain-specific.

**Recommendation:** synthetic self-contained compositional task for v1; DROP
as the realistic cross-check later. And whatever the task, **the maj@N
compute-matched baseline is non-negotiable from day one** — it is the single
measurement separating "orchestration works" from "we spent more compute."

**Honest caveat:** even with a well-designed compositional task, decomposition
may *not* beat compute-matched maj@N on the 7B. That is an acceptable outcome:
the learning is "here is the compositionality gap we could/couldn't open, and
why" — genuine intuition about when hierarchy pays. We go in without needing a
win.

---

## 8. Staging (decided: degenerate-first)

Build and debug one new component at a time so any failure is attributable:

- **Stage 1 — plumbing (degenerate Conductor):** a *trivial fixed* plan → **1
  worker** solves the whole problem → verify, on GSM8K. No real decomposition
  yet. Purpose: build and debug the orchestration loop, the plan format +
  parser, the composite reward, and the end-to-end eval — with orchestration
  quality *not* yet a variable. Exit: the loop runs, rewards are sane, a smoke
  run trains without error, cold-start gradient exists (or SFT is added).
- **Stage 2 — real decomposition:** on the §7 task (not GSM8K), conductor emits
  a genuine ≤2-step plan; worker solves sub-tasks; aggregate. The core
  experiment: does GRPO improve the conductor's decomposition, and does it beat
  the **compute-matched maj@N baseline** (§6 fork 5)?
- **Stage 3 — variation:** a weaker/smaller separate worker, harder task, or
  reward-shaping variants — whichever the Stage-2 results make interesting.
  (Not multiple heterogeneous workers — that's the out-of-scope routing goal.)

---

## 9. Success criteria (what "working" looks like)

- **Stage 1:** the full plan→worker→aggregate→verify loop runs inside GRPO
  training without error; the composite reward is unit-tested and behaves;
  a smoke run shows nonzero, sane rewards and no all-zero-group starvation
  (or SFT resolves it).
- **Stage 2:** the conductor's held-out end-to-end accuracy **improves with
  training** (proper stats), and — the real bar — **beats compute-matched
  maj@N** of the same model, not just one direct call. A null vs maj@N is an
  acceptable, informative outcome (§7 caveat).
- **Overall (learning goal):** we can describe how composite-reward and
  multi-step-rollout GRPO behaves, and whether/when hierarchy helps — the
  agentic-RL analogue of the intuition we built for single-turn GRPO.

---

## 10. Risks & unknowns to plan around

- **Cold-start starvation** — conductor can't emit valid plans → all-zero
  groups → no learning. Mitigation: zero-shot-bootstrap check + SFT fallback.
- **Reward hacking / trivial passthrough** — the conductor learns to shove the
  whole problem to one worker (no real decomposition) because that maximizes
  reward. Watch for it; may need reward shaping or task selection.
- **Throughput** — worker calls may make steps too slow for a useful dev loop;
  may force smaller groups / shorter workflows / fewer problems, or a faster
  worker-serving path within the memory budget.
- **Composite-reward pathologies** — one component dominating; format reward
  saturating while correctness stalls (as seen single-turn).
- **Verifier/parser bugs** — a lenient plan parser silently rewards malformed
  plans (the canonical GRPO failure). Unit-test the parser before any GPU time.
- **Noise** — end-to-end eval is expensive (worker calls) *and* noisy; budget
  for n=500-scale evals + seeds, and resist reading single-run wiggles.
