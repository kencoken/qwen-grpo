# Toy Conductor training plan

## Decision

Build a controlled “typed micro-workflow” environment in which tasks compose retrieval, mathematical reasoning, and code/string transformation. Train a 3B Conductor first, then repeat the decisive configuration with a 7B QLoRA model.

The main experiment will jointly learn decomposition and worker selection, but only after separate routing-only and decomposition-only experiments make the failure modes attributable.

This modifies the earlier [`conductor_task_prep.md`](https://github.com/kencoken/qwen-grpo/blob/main/conductor_task_prep.md) proposal in three important ways:

- Heterogeneous selection is part of the main experiment, not postponed indefinitely.
- A single-worker setup becomes a causal ablation.
- Few-shot workflow examples are the default cold start; SFT is only a measured fallback.

## What the papers imply

The [Conductor paper](https://arxiv.org/abs/2512.04388) trains a Qwen2.5-7B model for 200 updates using four questions × 64 workflows per update, up to five worker calls per workflow, terminal `0 / 0.5 / 1.0` reward, and no KL penalty. That is 51,200 generated workflows and probably around 150,000 worker calls. The current v5 appendix reports **2× H100 80GB**, not H200.

Several details are especially relevant:

- Its “pure RL” setup includes four curated successful workflow demonstrations. Removing them materially reduces performance.
- The 3B ablation learns similar broad routing patterns but writes weaker subtask instructions. This supports using 3B to study selection dynamics and 7B only for confirmation.
- Forcing every selected worker to be GPT-5 removes almost none of the AIME result, but loses roughly four to five points on BigCodeBench and GPQA. Math therefore mostly tests repeated prompting/refinement, while coding and science better expose actual heterogeneity.
- Fine-grained access lists did not help. Binary “no previous outputs” versus “all previous outputs” is enough for v1.
- The [OpenReview discussion](https://openreview.net/forum?id=U23A2BUKYt) leaves task suitability, compute-matched best-of-N controls, and causal worker-specialization evidence genuinely unresolved.

The [Fugu report](https://arxiv.org/abs/2606.21228) strengthens the case for build→audit→repair and specialist-insertion workflows. It also reports tasks where the simpler router beats Fugu-Ultra, so the toy environment must contain cases where one call is sufficient. Another valuable finding is that sharing all current worker histories caused anchoring and redundant-agent collapse; access should be explicit and isolated.

## The primary environment

Each problem is generated from a hidden typed program whose nodes belong to three families:

- `LOOKUP`: extract a fact from a self-contained passage, record set, or small table.
- `MATH`: arithmetic, algebra, comparison, or formula evaluation.
- `CODE`: trace or apply a restricted Python-like/string/list transformation.

The final answer is an exactly verifiable number, string, or label. The generator retains the gold operation graph, worker assignment, intermediate values, and final answer, but the joint RL reward uses only format and terminal correctness.

Example compositions include:

- lookup → mathematics;
- mathematics → code transformation;
- code trace → mathematics;
- lookup → code → mathematics;
- two independent leaves → final comparison.

Use the following training mixture:

- 40% atomic, optimally requiring one worker;
- 50% two-step compositions;
- 10% three-step compositions.

Balance the direction and worker ordering of the composite tasks. Atomic cases teach selective delegation and expose over-orchestration.

## Worker pool

Use three frozen 1.5B agents:

- [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) with a lookup tool;
- [Qwen2.5-Math-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Math-1.5B-Instruct) with an exact calculator;
- [Qwen2.5-Coder-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct) with a restricted expression/string executor.

Load workers frozen and 4-bit. Their tools operate on CPU and expose only narrow typed operations—no general code sandbox in the primary experiment.

Before training, empirically build a worker capability matrix over at least 500 atomic examples per family. Do not assume model names imply useful specialization. Retain task templates only when:

- the intended agent succeeds at least 70% of the time;
- it leads the alternatives by at least 25 percentage points;
- the oracle composed workflow succeeds at least 70%;
- direct use of the best single worker leaves meaningful headroom.

If the capability gap is insufficient, first tighten tool permissions and task construction. Only then consider lightweight specialist SFT adapters.

## Workflow interface

The Conductor emits:

```text
<think>...</think>
<workflow>
{"steps": [
  {"worker_id": 1, "subtask": "...", "access": []},
  {"worker_id": 2, "subtask": "...", "access": ["all"]}
]}
</workflow>
```

Rules:

- One to three steps.
- Strict JSON with valid worker IDs.
- Access is only `[]` or `["all"]`.
- The first step must use `[]`.
- Every worker receives the original problem and its assigned subtask.
- `["all"]` additionally supplies earlier subtask/output pairs.
- Workers never receive another worker’s private history.
- The final worker’s answer is the system answer; there is no extra Conductor synthesis call.
- Worker IDs are opaque and fixed during the main experiment.
- The Conductor cannot select itself in v1.

Malformed workflows are rejected without retry. Parser strictness must be adversarially unit-tested before any GPU run.

## Experimental progression

| Stage | What is learned | Purpose |
|---|---|---|
| 0. Harness | Nothing | Validate parser, context isolation, tools, execution, rewards, memory and timing. Use GSM8K only as a forced-one-worker regression smoke test. |
| 1. Capability calibration | Nothing | Measure the actual worker × subtask success matrix and tune task difficulty. |
| 2. Routing-only | Worker IDs | Supply gold subtasks and topology; use cached worker outcomes. Establish whether GRPO can learn empirical capability priors. |
| 3. Decomposition-only | Subtask wording | Fix oracle workers and topology. Compare learned instructions with generic “solve this” prompts. |
| 4. Joint Conductor | Steps, instructions, workers, access | Main 3B experiment on the full mixed task distribution. |
| 5. Causal ablations | — | Separate routing, prompting, topology, cost and worker-noise effects. |
| 6. 7B confirmation | Same as Stage 4 | Test whether the observed mechanism survives at the paper’s model scale. |
| 7. External validity | — | Apply the learned lessons to tiny build–test–debug tasks. |

Stages 2–4 should start from the same base checkpoint rather than continuing one adapter through changing action spaces. This makes their learning curves genuinely comparable.

## GRPO configuration

For the main 3B run:

- Conductor: Qwen2.5-3B-Instruct, NF4 QLoRA, rank 16, all linear projections.
- Conductor sampling temperature: 1.0.
- Worker temperature: 0 for the core study; 0.2 as a later reward-noise arm.
- Group size: 8.
- Effective batch: two prompt groups per optimizer update.
- Conductor completion limit: 512 tokens.
- Worker completion limit: 256 tokens.
- Joint training: 250 updates, checkpoints every 50.
- Learning rate: `1e-5`, ten-step warmup, existing constant schedule.
- KL coefficient: 0.
- Retain the repository’s currently validated DAPO-normalized GRPO loss initially; test paper-like normalization only after orchestration works.
- Run three seeds for all headline 3B comparisons.

Benchmark the full online rollout before committing to 250 updates. Target no more than roughly 12–16 hours per seed. If slower, shorten worker outputs and reduce to one prompt group per update before reducing group size.

## Cold start and reward

Seed the system prompt with four successful out-of-domain workflows covering:

- a one-step direct route;
- a two-step dependency chain;
- independent work followed by aggregation;
- a specialist followed by verification.

Before training, sample 32 prompts × 8 workflows. Proceed directly to GRPO if:

- at least 80% parse correctly;
- at least 25% of groups contain more than one reward level;
- terminal success is neither effectively zero nor saturated.

If format remains the blocker after one prompt revision, perform one epoch of SFT over 256–512 oracle workflow traces and rerun the gate. If workflows parse but all fail, fix task difficulty or worker competence rather than using format SFT.

Core reward:

- `0.0`: invalid workflow;
- `0.5`: valid workflow, wrong final answer;
- `1.0`: correct final answer.

Do not add intermediate route or decomposition rewards to the main joint run: terminal credit assignment is one of the phenomena being studied. Gold routes are for diagnostics.

A later selective-delegation arm can add at most `0.05` for using fewer calls, preserving the ordering `correct > valid-wrong > invalid`.

## Evaluation and baselines

Use at least 1,000 fixed held-out tasks, stratified by atomic/two-step/three-step structure, with paired per-problem outputs.

Required baselines:

- each worker directly;
- best single worker;
- prompted but untrained Conductor;
- oracle decomposition and oracle routing;
- oracle decomposition with random routing;
- learned workflow forced to use the best worker everywhere;
- learned worker sequence with generic subtasks;
- fixed hand-written workflow;
- best-of-N/self-consistency using the same number of worker calls;
- full trained heterogeneous Conductor.

Report total worker calls, generated tokens, wall-clock latency, and parallel critical-path latency separately.

The main positive result requires three things:

1. Joint training improves held-out composite accuracy over the untrained Conductor.
2. The heterogeneous workflow beats the same workflow forced through the best single worker.
3. Compute-matched best-of-N does not explain the improvement.

A null result on the third criterion remains scientifically useful: it means the chosen hierarchy did not outperform ordinary inference-time scaling at this model size.

## Training-dynamics instrumentation

Log these per checkpoint and by task type:

- format and parser success;
- frequencies of rewards 0, 0.5 and 1;
- reward standard deviation and zero-variance-group fraction;
- worker-selection entropy and worker × operation confusion matrix;
- workflow length and access topology;
- success conditional on correct routing;
- redundant worker calls;
- subtask and output lengths;
- direct-answer leakage in Conductor subtasks;
- worker token count, latency and tool usage;
- template similarity to the few-shot demonstrations.

Replay fixed workflows with counterfactual worker substitutions and removed access edges. These interventions distinguish genuine specialization from correlations in final reward.

## Failure modes to expect

- **Format-first plateau:** format reward saturates while correctness remains flat.
- **All-zero/all-equal groups:** no GRPO gradient despite substantial computation.
- **Strongest-worker collapse:** one generally capable model receives every subtask.
- **Weak-worker contamination:** exploration repeatedly places a weak model in the final role.
- **Trivial passthrough:** every subtask merely asks a worker to solve the original problem.
- **Self-solving leakage:** the Conductor embeds the answer in its instructions.
- **Redundant decomposition:** workers repeat rather than specialize.
- **First-worker anchoring:** later agents copy an early mistake.
- **Aggregator bottleneck:** correct intermediate results are lost in the final step.
- **Over-orchestration:** composite-looking workflows are used on atomic cases.
- **Worker-noise illusion:** apparent policy improvement disappears when workflows are replayed deterministically.
- **Worker-ID memorization:** routing fails when the pool is permuted.

Each should be treated as an experimental result with a pre-registered prediction, not merely as an implementation bug.

## 7B confirmation

Repeat only the decisive joint configuration using the existing 7B QLoRA setup. Keep the workers, task distribution, reward, group size and evaluation set unchanged.

One 7B run can establish qualitative mechanism transfer. Any numerical 7B improvement claim still requires three seeds; otherwise label it explicitly as a scaling sanity check.

If three 1.5B workers do not coexist safely with the measured 12.5GB 7B training footprint, replace the general retrieval agent with a deterministic lookup worker while retaining the Math and Coder LLM agents.

## After the primary experiment

The first external-validity task should be tiny build–test–debug problems:

- planner interprets requirements;
- coder implements;
- tests execute deterministically;
- reviewer identifies a concrete failure;
- coder repairs.

Only after that should you attempt AutoResearch-lite. It introduces stopping, experiment selection, persistent state and long-horizon credit simultaneously—too many new variables for the first hierarchical GRPO study.

## Amendments / clarifications following review (2026-07-16, revised after external review)

Adopted after checking the plan against the literature PDFs, the repository’s Phase A–C lessons, and an external review of the first round of amendments. The staged structure stands; these amend rather than restructure.

Framing and literature corrections:

- Own that heterogeneity is by construction (tool-gated 1.5B specialists, calibration-fitted task set). This is an orchestration laboratory: success means “GRPO learns routing where routing objectively matters”, not a miniature of the paper’s frontier-model claim.
- Fixed opaque ordinal worker IDs are the paper’s *base* setup (“Model 0, Model 1 …”), not a departure. The correct delta statement: v1 omits the adaptive-pool and recursive fine-tuning extensions.
- The paper reports 1e-6 AdamW with cosine scheduling but does not disclose whether training was full-parameter or parameter-efficient. State the delta as: repository 1e-5 LoRA versus the paper’s undisclosed adaptation method at 1e-6 with cosine scheduling.
- Both previously unlocated Fugu attributions are confirmed: the build→audit→repair pattern (Section 4.4, GPT builds, Opus enumerates concrete risks, repairs follow) and ordinary Fugu above Fugu-Ultra on SciCode (60.1 vs 58.7), τ³ Banking (21.7 vs 20.6) and Long Context Reasoning (74.7 vs 73.3). The latter is evidence that the more elaborate system is not universally better — not a causal demonstration that extra orchestration caused the losses.

Scope and compute discipline:

- Tranche-gating: commit now only through the Stage 2 gate, with explicit go/no-go gates before Stages 3–4 (numeric gates below).
- Pilot-then-seeds, tightened: either one disposable pilot (freeze everything, then three fresh seeds) or count the pilot as seed one only if no substantive setting, task filter, reward or stopping rule changes afterwards. Replicate decisive negatives as well as promising positives.
- Stages 2–4 all run on the same full task mixture, varying only what is learnable, so stage deltas are attributable. Note: Stage 2 (oracle subtasks) and Stage 3 (oracle workers) differ in both action space and privileged information — their curves diagnose whether each subproblem is learnable and must not be read as an additive decomposition of the joint score.
- Pre-registered: a Stage 3 null at 3B is expected-possible (the paper’s 3B ablation writes weaker subtask instructions) and promotes Stage 3 to 7B before any “GRPO can’t learn decomposition” conclusion.
- v1 trims, with the scope change stated plainly: dropping the 10% three-step tier means v1 studies selective delegation, two-stage decomposition and worker assignment — **not** learned parallel/tree topology (with only atomic and two-step chains, `["all"]` is usually the obvious access choice). Three-step parallel→aggregate tasks return in Stage 5. First-pass baselines are the decision-relevant eight: untrained Conductor, best single worker, **random routing (uniform and frequency-matched)**, oracle–oracle, forced-best-worker, generic subtasks, compute-matched best-of-N, trained Conductor. Random routing is the cheapest Stage 2 control — without it, beating the best single worker does not establish that routing learned the capability matrix. The remaining baselines return in Stage 5.

Feasibility requirements (treated as gates, not promises):

- Batched wave-execution of worker calls inside the reward function: all same-depth subtasks across the group, batched per worker. Verified in TRL 1.7.1 source: reward functions are invoked once per generation batch (`per_device_train_batch_size × steps_per_generation`), so group-wide depth-wise batching is achievable in-reward with the generation batch configured to span the update’s prompt groups. The serial alternative costs roughly 12–20 hours per seed in worker time alone; batched, roughly 6–9 hours. These estimates remain unverified until the full reward path is benchmarked.
- The most important Stage 0 feasibility test: produce a real GRPO completion batch; parse every plan; batch first-wave calls by worker; run second-wave calls after dependencies resolve; confirm peak memory, cache behaviour and calls per hour. If the trainer prevents this batching, reconsider the reward-function-only architecture before implementing the rest.
- Memoization is exact-key only: model revision + quantization config + worker system prompt + subtask + dependency context + decoding settings + tool version. No semantic/near-duplicate caching — it would silently alter the environment and could reward one paraphrase with another paraphrase’s output. Measure the exact-cache hit rate rather than assuming savings (gold subtasks in Stage 2 should hit often; free-form Stage 4 instructions may not).
- Evaluation path: generate Conductor plans via vLLM with the LoRA adapter served, then execute workers in per-model batched passes — roughly 30–45 minutes per 1,000-task evaluation, to be confirmed at Stage 0.

Generator and environment integrity:

- Three generator splits, not two: calibration templates (capability matrix construction), dev templates (checkpoint and configuration selection), untouched test templates (headline result). Hold out both surface templates and some operation compositions, otherwise the Conductor may learn “equation-shaped prompt → Math worker” without any subtask understanding.
- Wording-sensitivity probe in Stage 1, with refined interpretation: paraphrase gold subtasks five ways and measure worker success. Stable specialist advantage across paraphrases → semantic routing is learnable; large within-worker paraphrase variance → Stage 3 measures prompt optimisation (“wording-lottery mining”); specialist advantage disappearing under paraphrase → the constructed specialization is too brittle. Gate on the specialization advantage surviving paraphrase; record the variance as an outcome, since learned instruction wording is itself part of the paper’s claimed capability.
- Worker-side failure telemetry from Stage 1 onward: parse failures and truncations, each per worker. The Math-1.5B worker’s long-chain-of-thought habit makes truncation-before-answer likely; require terse structured answers first, and raise only its cap if truncation stays above threshold.

Stage gates (numeric):

- Stage 1 → 2: each specialist retains ≥ 20-point advantage on its intended operation across held-out paraphrases; worker parse failure and truncation each < 2%; oracle two-step workflows materially beat the best direct worker; the full training smoke stays below a conservative 22 GB peak; measured throughput projects to an acceptable overnight seed.
- Cold start: ≥ 80% valid workflows; ≥ 10% of prompt groups contain both a 1.0 outcome and a lower outcome; ≥ 25% of groups non-zero-variance. The group-level 1.0 criterion matters more than a global correct count because GRPO’s signal is group-relative.
- Stage 2 → 3: routing-only beats uniform and frequency-matched random routing on held-out templates; improves by a pre-registered margin over the untrained router (e.g. ten assignment-accuracy points); survives the cached-versus-live check (~20 live-worker updates) without material score change.
- Stage 3 → 4: learned subtasks separate from generic subtasks on dev. If Stage 3 is null: inspect paraphrase sensitivity, truncation and oracle-worker headroom; run Stage 3 with the 7B Conductor; then either proceed to a 7B joint experiment or consciously redefine Stage 4 as a routing-dominant study.

Instrumentation and selection:

- Traces are the source of truth, W&B for learning dynamics. Complete workflow traces are logged as JSONL, and all post-experiment analysis, claims and debugging run off them — anything not logged live is recoverable from them. W&B metrics are the live window: monitoring runs, catching failure modes mid-flight, and watching learning dynamics unfold; log whatever is useful for that. Complex derived diagnostics (e.g. confusion matrices, counterfactual replay) are offline analysis over traces. Claims come from traces plus proper statistics.
- Checkpoint selection rule: headline numbers come from the best-on-dev checkpoint (dev templates, evaluated every ~25 updates in Stage 4); the test templates are touched once, after selection.

Codebase: implement in this repository as a `tasks/conductor/` package (generator, workers, tools, parser, executor, with the task contract re-exported); worker execution lives inside the reward function. Aim to keep `train.py` thin rather than literally unchanged — expect modest additions for worker model IDs and per-worker token caps, cache and trace locations, eager/lazy worker loading, generation batching, executor shutdown/memory cleanup, and a conductor-specific evaluation mode. Revisit a repository split only if a custom rollout loop becomes necessary or Stage 7’s build–test–debug sandbox lands.
