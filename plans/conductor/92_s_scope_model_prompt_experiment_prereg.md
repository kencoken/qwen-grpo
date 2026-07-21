# Revised preregistration — D16 worker configuration experiment

**Status: DRAFT FOR FREEZE.** This document supersedes `91_f` once Ken
freezes it. No `worker_dev` P1 output, candidate output, or new GPU prompt
probe may be inspected before the prerequisites and exact identities below
are complete. Approval of this revision also closes the review of the D1
fixes in `90_f`; the amended `88_f` ratification must be recorded before the
first `worker_dev` invocation.

This revision makes four deliberate changes to `91_f`:

1. the selectable object is a complete worker configuration — model,
   request contract and prompt — rather than a model selected before prompt
   adequacy is known;
2. the primary target is full `30/30` semantic and protocol compliance in
   every endpoint cell × renderer group;
3. physical checkpoint sharing and measured RTX-4090 memory are part of the
   selection rule; and
4. the implementation and reveal rules are explicit enough that the
   decision can be applied mechanically.

## 1. Scientific scope and objective

This is an **adaptive development experiment on the finite `worker_dev`
population**. It selects a dependable toy-worker configuration; it does not
estimate population accuracy, emit a Stage-1 gate, or establish a true
failure rate below 2%. The later fresh construction and qualification
populations remain responsible for those claims.

The experimental unit is a latent program. Its renderer observations and
node calls are repeated measurements, not independent examples. Selection
uses exact finite-population counts; paired configuration contrasts are
descriptive.

The objectives are:

1. validate and freeze the already chosen Lookup and Math checkpoint,
   `Qwen/Qwen2.5-1.5B-Instruct`, under one shared request contract;
2. select the Code endpoint's model, request contract and Code system prompt;
3. prefer the smallest **physical** worker pool that achieves the target,
   subject to exact stability, latency and memory feasibility; and
4. stop with an explicit decision if the bounded search cannot achieve the
   target — never resume unrestricted prompt wordsmithing on `worker_dev`.

Lookup and Math prompts remain the registry-resolved rev9 texts in every
configuration. Only the Code prompt is a factor. `local_only`, 7B models,
retries, constrained decoding, parser normalization and difficulty-band
changes are outside this experiment.

## 2. Frozen factors and treatment identity

### 2.1 Code model checkpoints

The candidate registry contains these exact Hugging Face repositories and
revisions:

| key | repository | revision |
|---|---|---|
| `coder_1p5b` | `Qwen/Qwen2.5-Coder-1.5B-Instruct` | `2e1fd397ee46e1388853d2af2c993145b0f1098a` |
| `generic_1p5b` | `Qwen/Qwen2.5-1.5B-Instruct` | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| `coder_3b` | `Qwen/Qwen2.5-Coder-3B-Instruct` | `488639f1ff808d1d3d0ba301aef8c11461451ec5` |
| `generic_3b` | `Qwen/Qwen2.5-3B-Instruct` | `aa8e72537993ba99e69dfaafa59ed015b17504d1` |

Lookup and Math both use the exact `generic_1p5b` checkpoint above.

### 2.2 Shared request contracts

Both contracts are global: the same contract applies to Lookup, Math and
Code in an arm.

- **`current` / `worker-blocks-v0`:** the existing frozen order
  `Problem → Task → Resource(s) → Previous results → final line`, with the
  existing `ARTIFACT_FINAL_LINE` bytes.
- **`task_last` / `worker-blocks-task-last-v1`:**
  `Problem → Resource(s) → Previous results → Task → final line`, where the
  final line is exactly:

  ```text
  Translate only the assigned Task. The Problem is background; do not complete or combine other operations from it. Respond with exactly one <artifact>...</artifact> containing a single expression.
  ```

`task_last` is a bundled request-contract treatment: it changes block order
and the final instruction. Results must not be described as a pure recency
or scope effect. No `step_1` range hint or other task-specific sentence is
added to either contract.

Before freeze, both contracts receive checked registry keys, complete byte
fixtures and content digests. The digests, not the labels alone, enter every
candidate artifact.

### 2.3 Code prompt bundles

Two model-neutral Code prompt conditions are frozen **before any P1 run**:

1. **`rev9`:** the current registry-resolved rev9 bundle, byte-for-byte.
2. **`code_local_v1`:** one targeted Code-prompt revision derived only from
   the already retained rev1–9 evidence. It may address the known local-task,
   authorized-`resource`, exact-DSL and unnecessary-index-guard failures, but
   may not add a parser repair, retry, model-specific wording or hidden
   answer information.

`code_local_v1` must be written, reviewed, assigned a registry revision and
content hash before this document changes to `FROZEN`. Its Lookup and Math
texts are byte-identical to rev9. No third prompt and no edits to either
prompt are allowed after P1 begins. Failure of both prompt conditions across
all model arms in the last triggered tranche is a stop requiring a new
preregistration; failure in Tranche A alone follows the frozen 3B escalation
rule in §5.

### 2.4 Held-fixed runtime

All candidate configurations use one exact executable commit and hold fixed:

- Lookup/Math checkpoint and prompt bytes;
- tokenizer and chat-template revisions;
- NF4 (`nf4`, double quantization, BF16 compute);
- 256-token worker caps and greedy decoding;
- generator and difficulty profile;
- operator-aligned endpoint schedule;
- private visibility and all three renderers;
- cache-disabled `singleton-v1`; and
- endpoint grammar, tool and resource policy.

No documentation-only commit exception exists. Logs are written outside the
clean run worktree for the whole experiment and committed only after finalist
confirmation/composed execution or a terminal stop; they are not committed
between Tranches A and B.

## 3. Physical checkpoint sharing and RTX-4090 feasibility

Logical endpoints remain distinct even when their checkpoint is shared:
they retain different endpoint ids, prompts, tools and fingerprints. The
worker pool reuses model/tokenizer objects by the exact key

```text
(model_id, revision, quantization_config, device)
```

and renders the endpoint-specific system prompt at call time. Sharing is
implemented and tested before candidate P1 runs, then held fixed across the
matrix. It is never introduced between arms.

The prior single-model measurements give these planning estimates, not
acceptance values:

| Code choice | Physical worker checkpoints | rough peak sum |
|---|---|---:|
| generic 1.5B | one shared generic 1.5B | ~2.8 GiB |
| Coder 1.5B | shared generic 1.5B + Coder 1.5B | ~5.7 GiB |
| either 3B | shared generic 1.5B + Code 3B | ~7.8 GiB |
| current unshared baseline | generic 1.5B twice + Coder 1.5B | ~8.5 GiB |

CUDA context and allocator costs are not additive, so measurements rather
than the rough sums decide feasibility. The candidate runner extends the
ordinary RunWriter artifact with:

- a planned physical-layout manifest containing the exact unique checkpoint
  keys, revisions, parameter counts, quantization settings, devices and
  logical-endpoint-to-physical-worker mapping; and
- loader-validated execution measurements containing actual loaded keys,
  sharing status, idle resident VRAM, peak reserved VRAM, total wall time and
  per-endpoint latency.

Both are payload-hashed by the completed run manifest. The strict loader
re-derives the planned layout and frozen parameter counts from the candidate
registry, then refuses a planned/actual layout mismatch, missing measurement,
non-finite or negative measurement, or endpoint coverage mismatch. Selection
consumes only the loader-derived record, never an unvalidated console value.

Feasibility has two gates:

1. **Worker-only Gate D:** the existing P1 policy requires projected
   900-case time ≤3,600 seconds and peak reserved VRAM <22 GiB.
2. **Training-layout gate:** before the selected configuration becomes the
   Stage-0C launch profile, benchmark the real 3B QLoRA Conductor together
   with the chosen worker execution policy and require joint peak reserved
   VRAM <22 GiB. If Stage 2 uses immutable pre-materialized worker outcomes,
   record that worker models are intentionally absent during GRPO; live
   co-residency remains a later-stage gate.

The second gate is not inferred by adding individual peaks. Failure stops for
a memory-policy decision; it does not silently promote a runner-up.

## 4. Population, exact groups and success criteria

Every full candidate evaluation uses the fixed `worker_dev` population:
30 latents per cell, three private renderers, 180 latents, 540 observations
and 900 isolated node calls.

Primary groups are endpoint × cell × renderer, each with exactly 30 calls:

| endpoint | cells | groups | calls |
|---|---|---:|---:|
| Lookup | `lookup_atomic`, `lookup_math`, `fork_join` | 9 | 270 |
| Math | `math_atomic`, `lookup_math`, `math_code`, `fork_join` | 12 | 360 |
| Code | `code_atomic`, `math_code`, `fork_join` | 9 | 270 |

Operator-level cuts are reported diagnostically but are not pooled across
cells for selection. This prevents a strong `code_atomic` `seq_count` result
from hiding a weak `fork_join` `seq_count` result.

### 4.1 Target configuration

A configuration reaches the target only if:

- every applicable endpoint × cell × renderer group is exactly `30/30`
  `node_correct`;
- endpoint-wide envelope failures, grammar failures and token-cap hits are
  all zero;
- isolated `scheduled == called`, with no blocked or world-failure rows;
- the artifact loads and re-scores exactly; and
- P1 stability, time and memory gates pass.

Thus a selected target is 270/270 Lookup, 360/360 Math and 270/270 Code.
This is finite development compliance, not a confidence statement.

### 4.2 Recorded fallback floor

For decision support only, a **fully evaluated** configuration has a fallback
verdict recording whether it has:

- at least `29/30` in every endpoint × cell × renderer group;
- zero token-cap hits; and
- fewer than 2% endpoint-wide envelope-or-grammar failures — integer maxima
  5/270 for Lookup or Code and 7/360 for Math.

The fallback floor is **not automatic adequacy**. A prefix-pruned or
P1-non-admitted configuration is recorded as `fallback_not_evaluated`, not as
passing or failing this floor. If the bounded search finds no target
configuration, the experiment stops and presents the available full-run
fallback rows plus the separate P1 screening table for an explicit new
decision. Completing the fallback table would be a separately approved and
budgeted tranche; it does not happen automatically and the target is never
lowered after seeing results.

## 5. Candidate matrix and bounded adaptive sequence

The model-size ordering implements the objective “smallest physical pool
that reaches the target.” Both prompt conditions are evaluated before any
model of that size is selected, avoiding selection of a model under a prompt
that merely happened to suit it.

### Tranche A — complete 1.5B joint matrix

Run all eight configurations:

```text
Code model {coder_1p5b, generic_1p5b}
× request contract {current, task_last}
× Code prompt {rev9, code_local_v1}
```

Lookup and Math remain generic 1.5B with their rev9 prompts. All eight are
frozen before the first P1 invocation and revealed as one tranche.

If one or more target configurations survive, do not run 3B. Select among
the target configurations using §8.

### Tranche B — complete 3B joint matrix, conditional

Run Tranche B only if Tranche A has no target configuration. For every request
contract under which unchanged Lookup and Math are not **proven non-target**,
run:

```text
Code model {coder_3b, generic_3b}
× eligible request contract(s)
× Code prompt {rev9, code_local_v1}
```

This is at most eight further configurations and tests prompt × request
contract for each 3B model rather than importing a 1.5B-preferred contract.
If neither
request contract remains eligible because both have full, validated
Lookup/Math failures, stop before Tranche B: a Code-model change cannot repair
the shared-contract failure. An unaudited contract remains eligible; a
whole-candidate P1 failure may be caused by its 1.5B Code worker and cannot
prove that unchanged Lookup/Math fail under that contract.

If Tranche B has no target configuration, stop. New prompts, data bands,
decoding policies or models require a new preregistration and cannot consume
the remaining `worker_dev` universe opportunistically.

### Request-contract viability and unchanged-endpoint equality

For a fixed request contract, Lookup and Math have the same checkpoint,
prompt, cases and singleton policy in every Code-model/prompt arm. Their
generation fields must therefore be byte-identical across those arms.
A mismatch is a reproducibility stop, never a quantity to average.

A full, validated request-contract sentinel under which Lookup and Math reach
their target proves the contract viable. A full, validated Lookup/Math failure
proves it non-target and excludes it from later Code arms. If no 1.5B sentinel
can be completed, its state is `unaudited`, not `non-target`, and the contract
continues into Tranche B. The first completed full 3B arm then adjudicates it.
Fallback-floor status never makes a contract target-viable.

## 6. P0, implementation and freeze prerequisites

Complete these in order:

1. **Record D1 ratification.** P0 may proceed independently, but no
   `worker_dev` command runs before this entry exists.
2. **Freeze and replay the supported Code P0 cohort:** retain the rev9
   batch-sensitive Code requests with exact request hashes, ordering and every
   actual physical chunk (the recorded 16/16/13 grouping is per physical
   wave, not one larger logical batch). Replay original grouping twice,
   reversed-within-chunk order and singleton. Each command requires a valid
   artifact and exit code zero. P0 preserves historical batching evidence;
   it admits nothing.
3. **Retain the Math observation honestly as historical evidence.** The
   current P0 format admits each case once under one physical schedule, so it
   cannot represent the same target request inside both the per-cell-15 and
   per-cell-30 companion sets or compare those contexts as one cohort. Do not
   manufacture a replay by splitting it into incomparable cohorts. This
   experiment does not extend P0 solely for that diagnostic; the original
   request/completion/context records remain in the D16 log, and P1 tests the
   authoritative singleton policy. Any future Math context replay needs a
   small separately reviewed parent-cohort format with named schedules and an
   overlap-aligned comparator.
4. **Implement the lower-layer request contracts.** Contract selection must
   configure the actual renderer used by isolated and composed calls; a
   second metadata row without byte changes is forbidden.
5. **Implement the frozen candidate registry and physical sharing.** All
   Tranche-A and possible Tranche-B configurations exist in one clean commit.
6. **Make P1 candidate-aware.** `p1 --candidate <registered-id>` resolves the
   exact runtime profile, prompt bundle and request contract. Its output binds
   the candidate key and all content digests. Admission regenerates the exact
   candidate plan, including canonical rendered request hashes from the
   registered system prompt, tokenizer/chat template and user message — not a
   default plan or caller-provided label. Current/task-last and
   rev9/`code_local_v1` runs must fail cross-admission in tests. A strict P1
   loader independently regenerates labels and re-runs parsing/tools before
   deriving `target_prefix_clean`; it never trusts stored `expected_value` or
   `node_correct` fields.
7. **Add one thin candidate runner.** It writes complete RunWriter artifacts
   for isolated or composed mode. RunWriter intentionally refuses an existing
   directory: an interrupted or aborted invocation is retained and a
   permitted restart uses a fresh run id and directory; no partial run is
   resumed or overwritten. This is an experiment command, not a general
   orchestration framework.
8. **Re-enable narrow comparisons** only after request-contract comparison
   proves actual request-byte differences and refuses all undeclared
   differences. Prompt comparison must prove that only the Code prompt bytes
   and their derived Code/global fingerprints changed; Lookup and Math prompt
   hashes remain identical. The candidate registry must bind
   `runtime_profile.prompts.d16_revision` to the exact resolved PromptBundle,
   and profile↔bundle mismatch fails before execution.
9. **Generate and hash support plans before P1:** one 900-case full plan and
   one 300-case P1 projection per exact candidate. The P1 case ids must be an
   exact nested projection of the first 10 of the full plan's 30 latents in
   every cell; the loader proves that relationship. The P1 artifact freezes
   both the canonical sequence hash and the exact full-sequence reversal hash.
   Every invocation must match the applicable pre-run order hash.
10. **Implement one analysis/reveal command.** It strictly loads P1/full
    artifacts, independently re-scores them, validates unchanged-endpoint
    equality and writes a content-addressed screening/launch manifest. Before
    a tranche completes it exposes only candidate id, admission/cost and
    `target_prefix_clean ∈ {true, false, NA}`; `NA` is mandatory for
    non-admitted P1. It mechanically fixes the full-run launch set, including
    any sentinel, without exposing completions or per-case semantics. Raw P1
    and full outputs remain retained but hidden until every prescribed full
    run in that tranche completes. The joint reveal then releases frozen
    summaries, applies §8 and derives the supported §9 contrasts.
11. **Freeze this document and all content hashes.** No treatment identity,
    threshold, execution order or reveal rule changes afterward.

## 7. Execution, P1 screening and reveal discipline

For every candidate in a triggered tranche:

1. run P1 in three fresh processes: canonical, canonical, reversed;
2. require exact generation equality, valid artifacts, exit code zero and
   the frozen time/memory gates;
3. treat a valid P1 non-admission as candidate infeasibility — never rerun
   until a favorable draw and never fall back to the dynamic cache; and
4. retain raw outputs but expose only the admission/cost verdict and the
   automated three-state prefix verdict until the screening/launch manifest
   is frozen and every prescribed full run in the tranche is complete.

For a P1-admitted candidate, `target_prefix_clean=true` means all of the
following hold on the exact 300-case projection: exact planned support and
order; `scheduled == called == 300`; every endpoint × cell × renderer group
has its expected 10 calls and is `10/10 node_correct`; and envelope, grammar,
token-cap, blocked and world-failure counts are all zero. Any semantic or
protocol failure makes it `false`. A non-admitted or invalid P1 has verdict
`NA`, never `false`, because unstable or invalid generations are not semantic
evidence. These states and their supporting artifact hashes are derived by the
strict loader, not hand-entered.

The P1 prefix is the first 10 of the full 30 latents per cell. Once
singleton equality has been established, any semantic or protocol failure
in that prefix proves the candidate cannot achieve `30/30` on the full
population. Therefore:

- only P1-admitted candidates with a completely clean prefix proceed directly
  to a 900-case target run;
- prefix-failing candidates remain recorded in the screening table with
  fallback status `not_evaluated`, but do not receive an expensive full run
  during target search; and
- if no target is found after both tranches, any additional full runs needed
  to populate the fallback table require an explicit post-search decision,
  not an automatic extension.

Code prefix failures must not prevent the experiment from deciding whether a
shared request contract is viable for unchanged Lookup and Math. For each
request contract in Tranche A, designate a **contract sentinel** using the first
P1-admitted candidate in this frozen order:

```text
generic_1p5b/rev9
coder_1p5b/rev9
generic_1p5b/code_local_v1
coder_1p5b/code_local_v1
```

Run the sentinel's full 900-case artifact even if its Code prefix is not
clean; use only its full Lookup/Math groups to establish request-contract
viability.
The sentinel may simultaneously be an ordinary target run. If no candidate
in the fixed order admits, that contract is `unaudited` and continues into
Tranche B rather than being falsely rejected on a possibly Code-caused P1
failure. The first P1-admitted 3B candidate under it becomes its sentinel,
using the same frozen list above with `3b` substituted for `1p5b`. If no
candidate under that contract admits in the last triggered
tranche, that contract has no scientifically usable result; the overall
experiment stops if this leaves no viable candidate. Every later full arm
under an audited contract must reproduce the sentinel's unchanged Lookup/Math
generation fields exactly.

After all P1 invocations finish, the reveal command freezes the full-run launch
manifest using only admission and prefix states. All candidates named there
complete their 900-case isolated runs before raw P1 outputs or semantic
summaries are jointly revealed. Arm order is fixed in the candidate registry
using alternating model/request-contract/prompt order. A malformed or
non-zero-exit invocation is an infrastructure failure: record it and stop the
tranche rather than silently retrying. Candidate-level non-admission or a
valid dirty prefix is a preregistered elimination, not a global stop unless no
candidate remains. A semantically poor but valid run is an experimental
result.

## 8. Mechanical selection rule

Filter first to configurations satisfying the complete §4.1 target. If none
remain, follow the tranche transition or stop; do not rank an inadequate arm
as though it were adequate.

Among target configurations in the first successful model-size tranche,
choose lexicographically by:

1. lower exact sum of parameter counts across unique physical checkpoints;
2. fewer unique physical checkpoints;
3. `current` over `task_last`;
4. `rev9` over `code_local_v1`;
5. stable candidate id.

Measured peak VRAM and latency are feasibility gates and reported diagnostics,
not lexicographic rankers. This prevents allocator or timing noise from making
a two-checkpoint pool beat the structurally smaller shared pool. No unrounded
single-run timing measurement determines selection.

Because all surviving configurations are exactly correct on the finite
population, performance is not used to manufacture a distinction. A 3B
configuration cannot displace a target 1.5B configuration: the larger-model
tranche is never opened in that state.

## 9. Descriptive factorial outputs

Selection is mechanical, but the crossed design exists to teach us about the
interface. For evaluated configurations, define exact per-node-case outcomes

```text
Y[i, model, request_contract, prompt] ∈ {0, 1}
```

and report, overall and by endpoint × cell × renderer:

- paired **bundled request-contract** effects within a model and prompt;
- paired prompt effects within a model and request contract;
- model effects within a request contract and prompt;
- model × bundled-request-contract and model × prompt
  difference-in-differences; and
- paired win/loss/tie counts.

Because prefix screening deliberately creates missing 900-case arms, no
missing outcome is imputed and no complete full-population factorial is
promised. The common 300-case P1 projection supports paired prefix contrasts
only among P1-admitted candidates. Full-population effects are reported only
for executed pairs, and interactions only for complete executed rectangles on
identical support. Every table states its support and screening status. These
are bundled request-contract contrasts, never pure recency or scope effects.

These are finite-`worker_dev` descriptive contrasts. Renderers and nodes from
one latent are clustered views; do not report 900 independent-observation
standard errors. No bootstrap or interval is required for selection. If an
interval is added for exposition, it must resample latent ids as clusters and
remain explicitly non-gating.

## 10. Confirmation, composed diagnostic and worker-side freeze

Exactly one selected configuration advances:

1. its first complete 900-case isolated run is confirmation run 1;
2. run one fresh, same-commit 900-case repeat as run 2;
3. `confirm` must prove exact generation equality; mismatch stops and does
   not promote the runner-up; and
4. run one full composed-workflow diagnostic under the selected configuration.

The composed result is report-only for worker selection. Infrastructure
inconsistency stops; semantic compounding is recorded and carried into the
Stage-1 readiness assessment but does not trigger post-hoc runner-up
promotion.

The decision record contains:

- selected logical endpoints and physical checkpoint layout;
- model, request-contract and prompt ids plus full hashes;
- all target/fallback group counts and protocol telemetry for fully evaluated
  arms, plus `not_evaluated` statuses and exact prefix results for screened
  arms;
- P1, isolated confirmation, composed and VRAM/latency artifacts;
- descriptive factorial contrasts;
- ratification of the generic-1.5B Math endpoint;
- retention of the current `math_code` band; and
- the remaining Stage-0C memory condition.

This freezes the **worker-side D16 configuration surface** only. It is not a
claim that all of D16 or the construction screen is ready: D5/
`SYSTEM_DIRECT`, D4, B1 and the Stage-0C integration benchmark remain open as
listed in §12.

The `math_code` band is not selected from these outcomes. It remains
unchanged. Index-associated errors may be diagnosed, but any band amendment
requires its own preregistration and fresh evidence.

## 11. Compute planning envelope, invocation cap and stop conditions

At the frozen gates, one candidate is estimated to cost approximately:

- one GPU-hour for its three 300-case P1 runs; and
- one GPU-hour for its first 900-case run when selected by screening or as a
  contract sentinel.

Tranche A contains eight candidates; Tranche B contains at most eight more.
The preregistered invocation cap is therefore 16 candidate P1 triplets, at
most 16 first full runs (contract sentinels are candidates and are already
inside this cap), one finalist repeat and one finalist composed run. P0 and
model startup are additional. The matrix estimate is about 32 GPU-hours when
all 16 candidates receive both P1 and a first full run; plan for roughly
36–40 GPU-hours including P0, startup and finalist diagnostics. Prefix
elimination should reduce this substantially.

This is a planning envelope, not a guaranteed wall-clock ceiling: Gate D
limits P1's projected 900-case time, not the actual duration of a full or
composed run. Every actual duration is retained. Exceeding the projection is
reported and requires a cost-policy decision before another tranche; it does
not authorize an extra candidate, repeat or fallback-completion run. Any
post-search fallback completion is outside both the invocation cap and the
32-hour matrix estimate and requires a new budgeted preregistration.

The following are hard stops, not invitations to improvise:

- treatment bytes or support differ from their registered hashes;
- a real command exits non-zero or produces an invalid artifact;
- P1 non-admission leaves no viable candidate after applying the triggered
  tranche and unaudited-contract rules;
- unchanged Lookup/Math calls differ across Code-only arms;
- both shared request contracts are proven non-target for Lookup/Math on
  validated full evidence;
- no target configuration exists after the bounded tranches;
- finalist confirmation differs; or
- the selected physical layout later fails the exact Stage-0C memory gate.

Any subsequent prompt edit is a new exact configuration. Even if the model
and request contract remain administratively selected, it must rerun
candidate-specific P1, the full crossed evaluation and fresh confirmation
before D16 can be called frozen.

## 12. Boundaries after this experiment

This experiment does not discharge:

- D4, the consumed construction prefix;
- D5 / `SYSTEM_DIRECT`;
- B1 control fitting and freezing;
- the Stage-0C Conductor-plus-worker benchmark;
- construction or qualification gates; or
- the Stage-2 cache/materialization decision.

After the worker configuration and any required request-contract erratum are
frozen, close D5/`SYSTEM_DIRECT`, then D4, fit and freeze B1 controls without
inspection of construction accuracy, and pass the Stage-0C Conductor-plus-
worker/worst-case memory benchmark before the formal construction screen.
Decide the simplest Stage-2 materialization policy from the measured selected
configuration rather than assuming that all worker models must coexist with
the Conductor during routing-only GRPO.
