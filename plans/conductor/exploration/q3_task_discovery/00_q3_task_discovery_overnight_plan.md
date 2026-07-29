# Q3 task-discovery overnight exploration plan

**Status:** development-only exploration  
**Branch:** create `conductor_q3_task_discovery` from the current post-Unit-A commit  
**Log root:** `plans/conductor/exploration/q3_task_discovery/`  
**Expected execution environment:** `picome`, RTX 4090  
**Timebox:** one overnight run  
**Scientific status:** adaptive discovery; no result from this branch is confirmatory or directly reusable as final evaluation evidence

## 1. Objective

Answer one bounded question:

> Can we construct, using the existing frozen generic 1.5B and generic 3B Code workers, a synthetic task distribution that produces substantial, publicly predictable, renderer-stable bidirectional model advantage within one common task cell?

The desired outcome is a candidate high-level task design suitable for clean reimplementation and formal validation in the main branch.

This exploration does not attempt to:

- train a Conductor;
- prove that GRPO learns Q3;
- establish population-level model-performance claims;
- search additional model checkpoints;
- train LoRA workers;
- optimize worker prompts;
- modify the existing formal experiment;
- produce final train, development or test data.

A null outcome means only:

> No suitable task was found for these workers within the tested task strategies, existing DSL and overnight budget.

It must not be described as proof that no suitable task can exist.

## 2. Existing evidence and hypothesis

Read the relevant project logs before implementation, especially:

- `78_s_d16_rev9_review.md`;
- `98_f_d16_worker_config_tranche_a_outcome.md`;
- `100_f_d16_worker_config_rev10_outcome.md`;
- `102_f_d16_worker_config_rev11_outcome.md`;
- `103_s_d16_worker_config_rev11_critique.md`;
- `104_f_d16_worker_config_3b_screen_prereg.md`;
- `105_f_d16_worker_config_3b_screen_outcome.md`;
- `106_s_stage_0_four_worker_orchestration_pivot.md`;
- `107_s_deferred_code_only_model_orchestration_design_note.md`;
- the latest Stage-1/Unit-A implementation and outcome documents;
- the current `conductor_log.md`;
- the frozen worker registry, prompts, request contract and runtime profiles.

The relevant historical evidence is:

| D16 development outcome | Cases |
|---|---:|
| both 1.5B and 3B correct | 235 |
| only 1.5B correct | 22 |
| only 3B correct | 13 |
| neither correct | 0 |

The generic 3B repaired all 13 characterized 1.5B residual cases but introduced new failures, principally:

- solving downstream/global operations rather than the assigned local Task;
- legal but semantically wrong threshold or binding values;
- prompt/context interactions.

The 1.5B was more locally disciplined but had more protocol-class limitations.

On the later fresh complete surface, model preference largely collapsed to a cell rule. The simple cell router reproduced 43/45 payoff-distinct choices, leaving only approximately 0.23 percentage points between the cell router and hindsight per-observation oracle. There was no eligible common cell with sufficiently supported, renderer-stable directions for Q3.

The prospective hypothesis for this exploration is:

> The 1.5B may be preferable when strict local scope and literal protocol execution are required, while the 3B may be preferable when the requested result genuinely requires deeper composition.

This is a hypothesis to test, not an assumption to encode into rewards.

## 3. Frozen worker treatment

Use the existing registered workers without modification:

- `w2`: generic Qwen2.5-1.5B-Instruct Code worker;
- `w3`: generic Qwen2.5-3B-Instruct Code worker.

Preserve the exact registered:

- model revisions;
- rev10 Code system-prompt bytes;
- `worker-blocks-task-last-v1` request contract;
- NF4 runtime;
- greedy decoding;
- token cap and stop rules;
- `singleton-v1` execution;
- Code parser, DSL and executor;
- resource authorization;
- private/public visibility behaviour;
- request and execution fingerprints.

Do not:

- edit the prompt;
- add task-specific demonstrations;
- use different prompts for the two models;
- change decoding;
- use grammar-constrained decoding;
- change precision;
- change request scope independently by model.

A common experimental task block may be added as required by the new task design, but it must be identical for both workers and recorded verbatim.

The frozen prompt is deliberate: it isolates task-distribution effects and preserves a checkpoint-only treatment. The historical prompt was developed primarily around the 1.5B worker, so a negative result must not silently be interpreted as proving that the 3B model lacks useful complementary capability under every prompt. Section 16 requires the final report to diagnose whether systematic prompt mismatch is a plausible explanation and, if so, recommend a separate bounded follow-up. Do not run that follow-up under this plan.

## 4. Branch and artifact discipline

At the start:

1. Confirm the current branch contains the latest Unit-A result.
2. Record the base commit and worktree status.
3. Create `conductor_q3_task_discovery`.
4. Create:

```text
plans/conductor/exploration/q3_task_discovery/
```

Suggested contents:

```text
00_q3_task_discovery_overnight_plan.md
01_setup_and_baseline.md
02_strategy_log.md
03_candidate_freeze.md
04_holdout_result.md
05_final_report.md
artifacts/
```

Raw completions may remain under a gitignored directory such as:

```text
runs/q3-task-discovery/
```

Commit compact scored rows, summaries, manifests and hashes. The final report must identify the raw run locations and SHA-256 hashes.

Every result row should preserve at least:

```text
strategy_id
strategy_revision
split / namespace
latent_id
paired_latent_id
semantic factors
renderer
target node / target scope
worker_id
request identity/hash
runtime identity
completion hash
parse status
semantic correctness
failure class
reference target
```

Do not silently overwrite results from an earlier strategy revision.

## 5. Implementation posture

Keep the implementation deliberately small and separate from production code where practical.

Prefer:

- a standalone experimental generator or script;
- reuse of current IR types, renderers, request builder and executor;
- existing legal DSL operations;
- exact independent scoring of the requested reference node;
- a few focused CPU tests proving generator/reference agreement.

Avoid:

- production-package refactoring;
- generalized frameworks for hypothetical future tasks;
- changing existing cell semantics;
- adding new DSL operations unless all existing strategies prove impossible;
- changes to the GRPO trainer.

If a shared-infrastructure correctness defect is discovered, record it and stop the affected run. Do not silently change formal experiment semantics on this branch.

## 6. Required baseline

Before testing new tasks, run a small known-support check demonstrating that the experimental harness:

- routes requests to the correct w2/w3 checkpoints;
- preserves frozen request identities;
- independently scores the intended node;
- reproduces expected existing behaviour on a small retained support;
- distinguishes parse/protocol failure from legal semantic error.

Record this in `01_setup_and_baseline.md`.

Do not spend time reproducing the complete historical surface.

## 7. Task-construction principles

The latent semantic program must be generated before language rendering.

For every task:

1. Generate a valid latent program from existing DSL semantics.
2. Select the intended target node or result.
3. Compute its exact reference artifact independently.
4. Render the semantic task through the selected renderer.
5. Send byte-equivalent semantic content to both workers.
6. Score only the intended target—not the complete global Problem unless that is the registered target.

Task selection must operate on complete strategies or semantic strata. Never retain individual instances because w2 and w3 happened to disagree.

Numeric values, resource payloads or exact examples must not be searched individually for disagreements.

## 8. Strategy sequence

The agent may refine implementation details after inspecting the existing IR, but should test the following strategies in order.

### Strategy 1 — paired intermediate versus terminal targets

Generate a type-valid multi-step program using existing operations, for example conceptually:

```text
n1 = stable_unique(resource)
n2 = rotate_left(n1, k)
n3 = at(n2, i)
```

Create paired observations from the same latent program:

- **intermediate-target condition:** return the DSL artifact for `n1` or `n2`; later operations remain visible but are not requested;
- **terminal-target condition:** return the artifact for the true terminal result.

The resource, constants, global plan and renderer should otherwise be matched.

This tests whether:

- 1.5B benefits from local target discipline;
- 3B benefits when full composition is genuinely required.

Use only type-valid combinations supported by the existing reference evaluator.

### Strategy 2 — relevant versus distracting global continuation

Create matched programs in which comparable downstream material is:

- genuinely required for the requested target; or
- visible but irrelevant to the requested target.

Match text length, operation vocabulary and renderer as closely as practical.

This isolates global-context relevance from simple task length or cell identity.

### Strategy 3 — composition and binding pressure

Cross a small number of structural factors:

- shallow versus deeper target expression;
- literal versus predecessor-derived argument;
- direct versus nested composition;
- local constant versus bound/predecessor value.

The same operation vocabulary should appear on both sides where possible.

The agent may try one additional task strategy if the first three reveal a clear, documented hypothesis. Any such adaptive strategy must be described before its worker results are run.

Do not drift into unrestricted template or prompt iteration.

## 9. Development funnel

### 9.1 Small strategy pilots

For each strategy, begin with approximately:

- 12–16 independent paired latents;
- two renderers;
- both workers;
- all relevant semantic conditions.

Compute results immediately.

Drop a strategy when it exhibits:

- strict or near-strict worker domination;
- almost universal both-correct outcomes;
- almost universal neither-correct outcomes;
- only renderer-dependent reversals;
- failures caused primarily by a broken reference/task implementation;
- no plausible public semantic rule for model preference.

### 9.2 Expanded development surface

Expand only promising strategies to approximately:

- 32–48 fresh latents;
- all three existing renderers;
- complete crossing of the retained semantic factors;
- both workers.

Do not filter the expanded support based on individual outcomes.

### 9.3 Candidate freeze and fresh holdout

Before running the final fresh batch:

1. Choose one strategy revision.
2. Record its generator parameters, factor support and predicted semantic routing rule in `03_candidate_freeze.md`.
3. Record the exact holdout namespace and latent count.
4. Do not alter the strategy after seeing holdout outcomes.

The holdout should contain:

- at least 48 fresh paired latents if time permits;
- all three renderers;
- fresh resource values and program parameters;
- at least one unused target-description wording family if feasible.

One additional strategy freeze/holdout is permitted after a failed first candidate, provided it uses a new namespace and the adaptivity is fully disclosed. Do not repeatedly tune against the same holdout.

## 10. Metrics

Report metrics both by rendered observation and by independent latent. Do not inflate support by treating three renderings of one latent as three independent discoveries.

For each strategy, semantic stratum and renderer, report:

```text
both correct
only w2 correct
only w3 correct
neither correct
w2 accuracy
w3 accuracy
parse/protocol failures by worker
legal semantic failures by worker
```

Compute:

1. best-fixed-worker accuracy;
2. uniform-random-worker expected accuracy;
3. predeclared semantic-router accuracy;
4. renderer-only-router accuracy;
5. simple text-length/template controls where cheap;
6. hindsight per-observation oracle accuracy, diagnostic only;
7. oracle minus best-fixed gap;
8. semantic router minus best-fixed gap;
9. proportion of oracle gain captured by the semantic router;
10. renderer-stable unique-win latents in each direction;
11. renderer reversals;
12. group-of-eight reward-diversity projection under initially balanced worker sampling.

A latent has a renderer-stable direction when the same worker is uniquely correct under at least two renderers and the opposite worker is not uniquely correct under another renderer. Also report the stricter all-three-renderer count.

Classify failure causes manually or programmatically into at least:

- parse/grammar;
- resource/identifier protocol;
- over-composition/wrong target;
- predecessor/binding;
- threshold/index/value;
- other legal semantic error.

## 11. Provisional decision rubric

These are development dispositions, not formal scientific gates.

### GREEN — strong candidate for principled integration

Prefer a design satisfying approximately:

- at least 10% independent-latent unique-win mass in each direction;
- both directions occur within the same task cell;
- both directions reproduce across all renderers, or are overwhelmingly renderer-stable;
- hindsight oracle exceeds best fixed by roughly 8–10 points or more;
- the frozen semantic router beats best fixed by roughly 5 points or more on fresh holdout;
- the semantic router captures most of the attainable oracle gain;
- renderer-only routing is materially worse;
- projected group-of-eight reward diversity is sufficient for GRPO;
- complementarity is not almost entirely malformed-output noise.

A GREEN result justifies formal task design in the main branch. It does not authorize copying the discovery data or claiming Q3 learning.

### AMBER — scientifically interesting but not ready

Examples:

- both directions exist but one is below roughly 5–10%;
- oracle headroom is only 4–8 points;
- direction is stable under two renderers but weak under the third;
- the semantic rule is plausible but not strong on holdout;
- most complementarity arises from protocol failure.

Document the design for review, but do not recommend immediate integration without deciding how to strengthen or reframe it.

### RED — no suitable task found

Examples:

- one worker dominates;
- direction is cell- or renderer-determined;
- only isolated latent-specific reversals occur;
- holdout removes the apparent crossing;
- best-fixed and semantic-router performance are effectively identical;
- reward diversity remains too sparse.

Stop rather than continuing arbitrary search.

## 12. Hard resource limits

Unless a clear reason is documented:

- no more than 2,000 new physical worker generations;
- no more than approximately 10 RTX 4090 GPU-hours;
- no more than four major task strategies;
- no more than two frozen holdout reveals;
- no GRPO training;
- no additional model checkpoints;
- no prompt revisions;
- no model-specific request treatment.

If time or GPU budget is exhausted, produce the final report from completed evidence.

## 13. Autonomous decision policy

The agent is authorized to:

- implement experimental generators;
- add focused tests;
- execute w2/w3 worker runs;
- inspect and classify results;
- discard unsuccessful complete strategies;
- refine semantic strategy designs within the caps;
- commit exploration code, logs and compact artifacts;
- push the exploration branch.

The agent should not pause for ordinary design choices. Pause only for:

- inability to identify the correct base commit or worker identities;
- a shared infrastructure defect that undermines scoring;
- a required change outside the declared task-design scope;
- a destructive or external action requiring user authority.

## 14. Prompt-mismatch diagnostic

The existing Code prompt was iterated primarily around 1.5B behaviour. The 3B worker was evaluated with rev10 and rev11 but never received an unrestricted model-specific prompt-development cycle. This is a legitimate limitation, but it must not be allowed to reopen prompt iteration inside this task-discovery run.

If all task strategies are RED, classify the evidence into one of the following:

1. **No task geometry under the common prompt:** domination, ceiling performance, sparse/idiosyncratic disagreement or non-predictable crossing remains after otherwise valid execution.
2. **Plausible systematic 3B prompt mismatch:** the new tasks consistently elicit a coherent, prompt-addressable 3B failure such as wrong scope interpretation or protocol misunderstanding, while other evidence indicates the desired semantic capability may be present.
3. **Indeterminate:** task design and prompt compatibility cannot be separated from the overnight evidence.

For category 2, recommend—but do not execute—a separate bounded follow-up with:

- one reviewed 3B-specific prompt revision;
- no model changes;
- fresh task namespaces;
- no reuse of revealed holdout support;
- an explicit treatment label of model-plus-prompt-configuration routing;
- no iterative prompt loop.

Do not recommend prompt work merely because the worker is less accurate. The report must identify the repeated failure mechanism that makes prompt mismatch plausible.

## 15. Termination conditions

Stop the overnight search when any of the following occurs:

- one strategy receives a GREEN result on its fresh holdout;
- the resource limits are reached;
- all planned strategies are RED and no clearly motivated fourth strategy remains;
- a shared infrastructure defect makes results uninterpretable;
- continued work would require prompt iteration, new models or new DSL semantics.

After termination, produce the final report rather than beginning another open-ended search.

## 16. Final deliverable

Write:

```text
plans/conductor/exploration/q3_task_discovery/05_final_report.md
```

It must contain:

1. base and final commit identities;
2. exact worker/runtime identities;
3. total physical calls, wall time and GPU time;
4. every strategy attempted, including failures;
5. representative task examples;
6. complete development and holdout matrices;
7. failure taxonomy;
8. shortcut and renderer analysis;
9. group-of-eight feasibility projection;
10. GREEN/AMBER/RED disposition;
11. limitations caused by adaptive discovery;
12. the Section 14 prompt-mismatch classification;
13. recommended next action.

For a GREEN result, additionally describe:

- the minimal semantic generator required;
- which existing IR operations can be reused;
- the intended semantics-to-language mapping;
- the proposed clean train/dev/test split;
- what must be independently reimplemented and reviewed in the main branch;
- which discovery artifacts must not be reused.

For a RED result, state precisely which strategies were tested and why each failed. Use the wording:

> No suitable Q3 task was found within the tested existing-DSL strategies and overnight search budget.

Do not claim impossibility. Explicitly state whether the result is best classified as no task geometry under the common prompt, plausible systematic 3B prompt mismatch, or indeterminate.

Commit and push the completed exploration branch, leaving the worktree clean.
