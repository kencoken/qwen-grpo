# Stage 0B worker-evaluation integrity — minimal implementation plan

**Status:** proposed; review before implementation

**Target branch:** `conductor_stage_0b_worker_eval_integrity`, based on
`conductor_stage_0b` at `365f2dd`

**Purpose:** Step 1 of the D16 close-out sequence

**Inputs reviewed:** frozen plan `plans/conductor/13_f_plan_rev6.md`, frozen cell
specification `conductor_cell_specs.md` /
`plans/conductor/48_f_conductor_cell_specs_rev8.md`, the Stage-0B runtime,
cache, executor, trace and smoke code, D16 logs `60_f`–`77_f`, and
`78_s_d16_rev9_review.md`.

## 1. Decision summary

Build one deliberately small worker-evaluation path, not a general experiment
framework.

It will:

1. bind every result to the actual worker request and runtime configuration;
2. evaluate every reference node independently with gold predecessor inputs;
3. keep normal composed-workflow evaluation as a separate diagnostic;
4. cross all three frozen renderers;
5. score intended-node correctness outside the executor;
6. write one manifest, raw call rows, score rows and a derived summary; and
7. run cache-disabled with physical batch size 1 if a bounded reproducibility
   and cost probe passes.

It will not implement a generalized arm type system, a new payoff-surface
wrapper, canonical-cohort caching, stochastic-endpoint inference, or a reusable
Stage-1 orchestration framework. If singleton execution fails the probe, stop
and write a separate design decision rather than growing this change until it
can represent every possible future execution policy.

This is the governing contract:

> Given a worker result, we can identify the exact request and execution
> configuration that produced it, independently score the intended reference
> node, compare it across renderers, and avoid silently conflating results
> produced under materially different execution conditions.

## 2. Concrete failures this must close

| D16 evidence | Required correction |
|---|---|
| `WorkerResult.status == "success"` counted a legal but wrong Code artifact as successful (`math_code`, construction index 19: observed 17, expected 64) | Report protocol/tool success separately from reference-node correctness |
| Downstream requests were called only after successful predecessors; four scheduled `fork_join` Math calls were blocked | Add isolated node evaluation with gold predecessor values; retain workflow evaluation separately |
| Code performance changed substantially across `resource_first`, `goal_first` and `bound_var` | Cross all three renderers and require exact paired support |
| Raw greedy NF4 output changed with request order, microbatch and cohort composition | Do not use the current dynamic-miss cache in worker evaluation; test a singleton execution policy before adopting it |
| A declared prompt revision could disagree with the module-global prompt actually rendered | Bind configuration to actual prompt bytes and hashes, not a label alone |
| The runtime shallow-copies its input profile | Own an immutable/deep-copied effective configuration before fingerprinting or execution |

The implementation should expose these effects. It should not decide whether
rev9, another prompt, a different Code model, or another request scope wins.

## 3. Scope and non-goals

### 3.1 In scope

- exact runtime and prompt provenance for worker evaluation;
- an explicit cache-disabled generation option;
- isolated reference-node request construction;
- strict external node scoring;
- composed reference-routed workflow diagnostics;
- complete renderer crossing;
- exact denominators and failure-stage telemetry;
- small, validated JSON/JSONL artifacts;
- a narrow run-comparison check; and
- CPU tests plus one recorded RTX-4090 acceptance run.

### 3.2 Out of scope

- prompt wording, prompt demonstrations, or rev10 design;
- endpoint/model selection;
- current versus task-last versus local-only request-scope selection;
- changing renderers, difficulty bands, operators, grammars or task data;
- grammar-constrained decoding or retries;
- semantic repair of officially invalid artifacts;
- full `3^S` payoff enumeration;
- interventions, bootstraps, confidence intervals or Stage-1 gates;
- a cache-v2 or canonical-cohort implementation;
- precomputing the Stage-2 training environment;
- implementing or selecting `SYSTEM_DIRECT`; and
- general reusable abstractions for later stages.

The existing frozen §1.10/D11 cache contract is not reinterpreted here. The
scientific worker-evaluation command bypasses the cache. Any later change to
cache identity or batching semantics requires its own reviewed plan/spec
erratum.

## 4. Scientific contracts

### 4.1 Keep execution and scoring separate

The existing executor remains reference-free. Do not add the reference graph,
current-node target, node-value map, or final gold to `WorkflowItem`,
`ExecutionResult`, `Runtime.worker_call_batch`, or the request sent to a worker.

The evaluator builds two in-memory objects:

```python
@dataclass(frozen=True)
class WorkerEvalCase:
    case_id: str
    observation_id: str
    endpoint_name: str
    user_message: str
    binding_payload: CanonicalBindingPayload
    binding_sha256: str

@dataclass(frozen=True)
class NodeLabel:
    case_id: str
    latent_program_id: str
    renderer_id: str
    cell_id: str
    node_id: str
    node_family: str
    position: int
    call_role: str
    predecessor_source: str
    expected_value: int
```

Only `WorkerEvalCase` reaches runtime generation and tool execution. `NodeLabel`
is joined afterward by exact `case_id`.

Gold predecessor values are legitimate ordinary inputs in isolated-node mode:
they appear in the same `Previous Results` block and `Binding.steps` channel
that produced predecessor values use in a real workflow. The expected value of
the node being tested never enters the executable case.

Required strip tests:

- deleting all labels leaves request bytes, completions and executed
  `WorkerResult`s unchanged;
- changing `expected_value` changes only the score; and
- the existing arbitrary-workflow strip test continues to pass.

### 4.2 Preserve authorization and privacy

An isolated case exposes exactly the normal step inputs:

- the public problem;
- the reference subtask for this node;
- at most its one authorized resource; and
- the permitted predecessor values.

It must not contain another registry entry, the current target, the reference
graph, or final gold. Canonicalize the binding into immutable tuples/bytes,
hash it, and reconstruct a fresh `Binding` only at tool execution. The current
`Binding` dataclass is only shallowly frozen because it contains dictionaries;
do not retain caller-owned dictionaries in a hashed case.

Raw call files contain worker-authorized private payloads and remain local
evaluator artifacts. They are never Conductor observations or training data.

### 4.3 Two evaluation modes, never pooled

#### Isolated node mode

For every registered latent, renderer and scheduled reference node:

1. validate/regenerate the latent and rendered instance;
2. derive `workflow_steps(latent)` in reference `positions` order;
3. recompute reference values with `program.evaluate_reference`;
4. build the ordinary request for this node;
5. use gold values for every permitted predecessor position;
6. expose only the node's authorized resource;
7. generate and strictly execute the completion; and
8. compare the returned integer with the separately held expected value.

For a valid isolated run:

```text
scheduled == called
dependency_blocked == 0
pre_call_world_failure == 0
```

Parse/tool failures are called outcomes and count as node-incorrect in the full
scheduled denominator. Any blocked or pre-call world-failure row invalidates
the run rather than becoming a worker-performance observation.

#### Composed workflow mode

Execute the existing reference-routed workflow normally, using produced
predecessor values and normal dependency propagation. This measures compounding
and terminal correctness.

Reconcile disjoint categories:

```text
scheduled_steps
  == called_steps
   + dependency_blocked_steps
   + pre_call_world_failure_steps
   + synthetic_steps
```

- `called` includes envelope, grammar, typed tool and wrong-value failures;
- `dependency_blocked` means no worker call after predecessor failure;
- `pre_call_world_failure` means no call because authorization/resource
  resolution failed;
- `synthetic` means an explicit pseudo-worker, not a model call; and
- unexpected infrastructure failures abort the run.

For a registered reference-routed D16 run, world failures and synthetic steps
must both be zero. Terminal correctness is over all scheduled workflows.
Conditional-on-called node correctness is diagnostic only.

### 4.4 On-contract calls are explicit data

Each node label carries `call_role`:

- `on_contract_reference`; or
- `off_contract_diagnostic`.

The role is derived from the declared logical endpoint/node-family schedule
before execution, never from success. D16 conformance and later endpoint
parse/truncation denominators use only `on_contract_reference`. A future
payoff-surface misroute must not silently enter those denominators.

This operator-aligned D16 schedule tests worker contracts. It is not a presumed
gold assignment and does not replace Stage 1's measured payoff surface.

### 4.5 Renderer crossing is exact and paired

For each declared `(latent_program_id, node_id, endpoint candidate)`, require
exactly one case for:

```text
resource_first, goal_first, bound_var
```

The three instances must validate as renderings of one latent program with the
same reference IR, private registry and expected values. Missing, duplicate or
extra renderer rows invalidate the run.

Report renderer marginals and paired correctness flips. Do not average away a
large renderer effect or treat three renderings as three independent latent
programs. Stage 0B reports descriptive point estimates only; cluster bootstrap
inference remains Stage 1 work.

### 4.6 Development population must be honest

D16 adaptively inspected construction indices 0–29, so those examples remain
useful development evidence but are not a fresh post-freeze construction
screen.

Do not move this adaptation silently into the existing `dev`, `test`, `train`
or `qualification` namespaces. Before the next candidate run, approve a narrow
specification erratum defining a dedicated `worker_dev`/`d16_dev` universe
(recommended), with its own seed identity, cap, deterministic order and
stopping rule.

Use indices 0–29 per cell from that dedicated universe, private visibility and
all three renderers. One full D16 semantic-endpoint pass then contains:

- 180 latent programs;
- 540 rendered observations; and
- 900 isolated node calls.

Separately, resolve the already consumed construction prefix before the formal
100-per-cell construction screen. Do not quietly use the inspected 30 or reduce
the screen to 70.

## 5. Minimal persisted artifacts

Write only four files per run:

```text
manifest.json
calls.jsonl
scores.jsonl
summary.json
```

### 5.1 `manifest.json`

The manifest contains:

- schema version, run ID, purpose and `running|complete|aborted` status;
- source commit and dirty-state/diff digest;
- exact population IDs, namespace/range, renderers and visibility;
- semantic endpoint-schedule version plus the exact ordered scheduled-row keys
  `(evaluation_mode, case_id, position)` and their SHA-256;
- generator and difficulty-profile versions;
- candidate display label plus request-contract key, canonical builder/config
  digest and status;
- a deep-copied canonical runtime profile;
- actual per-endpoint system-prompt text, SHA-256 and prompt status/revision;
- model and tokenizer IDs/revisions;
- actual chat-template hashes;
- NF4, dtype, decoding, EOS, padding and token-cap settings;
- seed policy and Torch/CUDA deterministic-backend flags;
- Torch, Transformers, bitsandbytes, CUDA/driver and GPU versions;
- parser, grammar, tool and resource-policy versions;
- generation policy (`singleton-v1` for scientific runs; an explicit frozen
  physical-batch manifest for P0);
- expected and written row counts; and
- SHA-256 of the three payload files.

The manifest does not hash itself. After close, print and record its full
SHA-256 in the run log. Retained GPU comparison runs require a clean committed
worktree; a dirty-state digest is diagnostic-only and cannot freeze a
candidate.

The runtime must deep-copy/own its configuration before resolving prompts,
templates or fingerprints. Caller mutation after `build_runtime` must change
neither behavior nor the manifest.

The writer refuses an existing run directory, writes payloads before the final
manifest, and marks exceptions `aborted`; an interrupted run cannot look
complete.

### 5.2 Prompt/configuration binding

Replace module-global prompt lookup during worker evaluation with an explicitly
resolved prompt mapping supplied to the pool/runtime. A named revision is valid
only if it resolves to the exact strings used.

Minimum behavior:

- actual prompt hashes enter the worker-visible/endpoint fingerprints and
  manifest;
- unknown revision or revision/content mismatch fails before generation;
- the pool renders from the resolved strings, not a second global lookup;
- draft candidate runs are allowed but visibly marked `DRAFT`; and
- a frozen run refuses a draft prompt bundle.

Bind the request contract the same way. A request-contract key resolves to the
exact block order, fixed boilerplate/final instruction, builder version and any
scope option. Store its canonical content/config digest in the manifest and
fail before generation if the key, builder or digest disagree. A label such as
`task_last` is not sufficient provenance by itself.

Keep worker-prompt status separate from `SYSTEM_DIRECT` status. This plan does
not implement the direct harness; the formal construction screen remains
blocked until the direct-prompt decision is closed or the frozen D16 contract is
explicitly amended.

### 5.3 `calls.jsonl`

One row per scheduled isolated call, or per scheduled workflow step. It contains
no expected node value or final gold.

Required fields:

- `run_id`, `case_id`, `observation_id` and workflow position;
- global schedule ordinal, validated against the manifest's ordered row plan;
- latent, cell, renderer and node identifiers for later joining;
- endpoint name and evaluation mode;
- predecessor source (`gold|produced|none`) and predecessor positions;
- call status (`called|dependency_blocked|pre_call_world_failure|synthetic`);
- exact canonical user message;
- exact rendered chat request as lossless UTF-8 text and SHA-256;
- canonical binding SHA-256;
- global generation ordinal for called rows;
- physical batch size and slot (both `1`/`0` in singleton mode);
- completion text and SHA-256;
- finish reason, generated-token count and cap flag;
- envelope parse outcome/error;
- endpoint grammar outcome/error;
- `WorkerResult` status, value, rejection code, `artifact_valid` and
  `tool_executed`; and
- cache source, which must be `disabled` for the proposed scientific run.

The row schema is status-conditional. Every scheduled row has its schedule
identity and status. Request, generation ordinal, batch, completion and backend
telemetry are required only for `called`; they are null for dependency-blocked,
pre-call-world-failure and synthetic rows (synthetic output remains in the
explicit pseudo-worker fields). The loader enforces these combinations.

`E_PARSE` is not enough to reconstruct failure stage: it can arise from
envelope ordering or endpoint grammar. Instrument/replay the existing envelope
parser and then the existing grammar/tool path, without changing acceptance.
Any replay is parse-only: the authoritative tool executes exactly once. The
staged record and terminal `WorkerResult` must agree.

For workflow rows, `(case_id, position)` is the call identity. For isolated
rows each `case_id` is one call. Separate determinism repetitions use separate
run IDs; there is no need for a hierarchy of generation/execution/score IDs.

### 5.4 `scores.jsonl`

Join calls to labels only after execution. A node score row contains:

- `run_id`, `case_id` and the call-file SHA-256;
- call role and strata;
- observed value or null;
- expected node value;
- strict `node_correct`; and
- scorer version.

A workflow score row contains the workflow case ID, terminal value, final gold,
`terminal_correct` and scorer version. Keep node and workflow row types
explicit; final gold is never an optional field on a node label.

The known rev9 `math_code` index-19 completion becomes a regression fixture. It
must be called, artifact-valid, tool-executed and protocol-successful, while
scoring `node_correct=false` (17 versus 64).

### 5.5 `summary.json`

This is derived, never source truth. Recompute it from calls and scores and
compare on load.

At minimum report:

- scheduled, called, blocked and pre-call-failure counts;
- token-cap, envelope, grammar, tool and protocol outcomes;
- strict node correctness;
- composed terminal correctness;
- endpoint × cell × node family × renderer strata;
- worst-renderer correctness;
- renderer max–min gap and paired flip rates; and
- conditional-on-called versus full-scheduled results where relevant.

Do not label `WorkerResult.status == "success"` as accuracy.

### 5.6 Loader rules

Strict loaders reject:

- a non-complete manifest;
- wrong schema, file hash or row count;
- missing, duplicate or extra planned scheduled-row keys;
- mixed run IDs or population identities;
- missing/duplicate renderer support;
- request or completion hash mismatch; and
- a summary that does not rederive exactly.

Persisted instances are validated by regeneration. No Stage-0B/D16 artifact can
emit a Stage-1 gate result.

On every load, independently regenerate each `NodeLabel` and workflow gold from
the manifest population and frozen generator/reference evaluator. Verify the
stored strata and expected values before recomputing correctness. File hashes
and an internally consistent summary are not allowed to bless a wrong target.

## 6. Minimal APIs and code changes

### 6.1 New `tasks/conductor/worker_eval.py`

Keep the new module single-purpose. Proposed public functions:

```python
build_node_cases(population, endpoint_schedule, request_contract) \
    -> tuple[cases, labels]
run_node_cases(runtime, cases, writer) -> call_rows
score_node_calls(call_rows, labels) -> score_rows
run_composed_workflows(
    runtime, population, endpoint_schedule, request_contract, writer
)
summarize_worker_eval(manifest, calls, scores) -> summary
compare_worker_eval_runs(left, right, allowed_difference) -> comparison
```

`allowed_difference` is a small enum (`prompt`, `model`, or
`request_contract`), not a generalized comparison language. The comparison
checks identical population/case/renderer support, singleton generation,
parser/tool versions, and all manifest fields that should be held fixed. It
prints the exact differing fields and refuses unexpected differences.

Use the existing request renderer, `contract.run_worker_output`, binding types
and reference evaluator. If the D16 semantic endpoint schedule or
reference-artifact helper is currently private to `agreement.py`, move only
that small shared helper to an appropriately named reference utility. Do not
call it an oracle assignment. Store assignments in stable semantic-node order
and derive action order through `reference_program.positions`; never treat
position order as the scientific assignment (`fork_join` code-first is the
regression case).

### 6.2 `tasks/conductor/runtime.py`

- deep-copy/own the effective profile;
- accept a resolved system-prompt mapping;
- include actual prompt hashes in existing fingerprints;
- expose cache-disabled calls;
- preserve one physical generation occurrence per planned evaluator case (do
  not apply the current duplicate-request miss deduplication);
- include the exact rendered request text/hash and batch-size metadata in
  `CallRecord`; and
- expose the resolved manifest fields listed in §5.1.

Avoid adding a new family of runtime, generation, endpoint and interpretation
snapshot classes. The canonical manifest plus the existing fingerprint scopes
is sufficient for this evaluator.

### 6.3 `tasks/conductor/workers.py`

- render from the resolved prompt mapping;
- report the actual tokenizer/template/EOS/padding facts used;
- add an explicit singleton generation method or enforce
  `physical_batch_size=1` in the evaluator path; and
- leave parsing, tools and scores outside the pool.

### 6.4 `tasks/conductor/executor.py`

Avoid a broad executor refactor. Extract one small reference-free helper for
constructing `(user_message, canonical binding)` from the public problem,
subtask, authorized resource and previous values, so isolated and composed
paths cannot drift.

The existing workflow trace identity `(item_id, position)` is sufficient.
Add only the call telemetry needed by §5.3; do not introduce new arm or proof
types.

### 6.5 `tasks/conductor/cache.py`

No cache-v2 work in this change. The scientific evaluator uses an explicit
disabled/no-op cache and asserts every row says `cache_source=disabled`.

Keep the existing cache for the Stage-0B mechanical smoke, clearly labelled as
such. The smoke's warm second pass demonstrates replay, not generation
determinism and not worker accuracy.

### 6.6 Tests

Add `test_conductor_worker_eval.py` and targeted changes to runtime/executor
tests. Avoid a broad new framework or generalized artifact library.

## 7. Generation-policy probe and gate

### 7.1 What is already rejected

Do not use this policy for scientific worker evaluation:

```text
dynamic cache misses
  -> batched in the current remaining order
  -> first completion stored under a request-only key
```

D16 already showed that identical request bytes can change with batch
companions/order. A fully cached second pass only reproduces the first writer.

### 7.2 P0 — retain the known regression

After this policy-neutral code is brought into the D16 branch, run cache
disabled on:

- the retained rev9 batch-sensitive Code requests;
- the identical Math request that changed between per-cell-15 and per-cell-30;
- the original grouping twice;
- reversed order; and
- singleton generation.

P0 retains a small diagnostic batched-probe path separate from the scientific
singleton runner. Its cohort manifest records each actual `model.generate`
chunk, ordered request hashes, slots and boundaries (including the rev9
16/16/13 split), not merely the larger logical wave. Original and reversed
conditions are reconstructed from those frozen physical manifests.

Compare completion bytes, finish reason, generated-token count, cap flag,
grammar result, executed value and strict node correctness. This is a recorded
regression, not a new prompt-selection sample.

### 7.3 P1 — singleton admissibility

Using the dedicated worker-development namespace, pre-register the first 10
latents per cell crossed with all renderers: 300 node cases. Assert the sample
covers every cell, node family and generator factor level before execution.

For every declared candidate configuration (reusing work only when prompt,
model/tokenizer/template, request bytes, backend and decoding configuration are
identical), run:

1. singleton, canonical case order, fresh process;
2. singleton, same order, second fresh process; and
3. singleton, reversed order, third fresh process.

Admit `singleton-v1` only if generated completion bytes, finish reason,
generated-token count and cap flag match exactly for every case. Wall time,
memory and timestamps are measurements, not equality fields.

The proposed cost gate is:

- projected full 900-case run ≤60 minutes per candidate;
- peak reserved VRAM <22 GiB.

Freeze these numeric limits before inspecting P1 outcomes. A reviewer may
replace them before the probe, but not with “acceptable latency.”

Do not extrapolate Stage-1 all-assignment cost from these 300 operator-aligned
calls: off-contract call counts, completion lengths and blocking differ. The
existing Stage-0C worst-case enumeration benchmark will set that later budget.

### 7.4 Fail closed

If singleton output is not bit-stable or exceeds the frozen cost gate:

1. do not fall back to the current cache;
2. do not quietly select one arbitrary materialized draw;
3. do not add canonical-cohort or stochastic machinery to this PR; and
4. write a short follow-up decision plan using the observed differences and
   timings.

This keeps the didactic implementation small. It also makes the scientific
limitation explicit rather than hiding batch dependence behind more elaborate
identifiers.

Admission applies only to the exact tested configuration and registered request
population. P1 is an early 300-case gate; before accepting a full candidate
result, execute the complete 900-case population twice in fresh processes in
the same canonical order and require the same exact generation-field equality.
A model, prompt, template, request-contract, quantization, library, driver,
hardware or generation-policy change reruns the relevant gate. It says nothing
about later Stage-3 free-form subtasks.

## 8. Implementation tranches

### Tranche A — provenance and singleton path

- own/deep-copy the runtime configuration;
- bind actual prompt text/hashes;
- add cache-disabled singleton generation;
- write/validate the minimal manifest and call rows.

**Gate A:** prompt revision/content mismatch fails; caller mutation cannot alter
behavior; exact request/completion hashes validate; existing CPU suite remains
green.

### Tranche B — isolated node scorer

- build isolated requests with gold predecessors;
- preserve authorization boundaries;
- write labels only to the scoring path;
- produce strict node scores and denominators.

**Gate B:** the legal-but-wrong rev9 fixture is detected; a downstream node is
called even after a scripted composed upstream failure; reference artifacts
score 100% across six cells × three renderers; target mutation does not change
execution.

### Tranche C — crossing, workflow diagnostic and comparison

- enforce complete renderer support;
- retain ordinary composed workflows;
- derive summaries;
- add the narrow two-run comparison check;
- document that construction and qualification gates remain unavailable.

**Gate C:** missing/duplicate cases or renderers fail; workflow denominators
reconcile; a hand-calculated paired-renderer fixture matches; unexpected
manifest differences block comparison.

### Tranche D — D16 GPU probe after integration

Merge A–C plus the probe command into `conductor_stage_0b`, bring it into the
D16 branch, then run P0/P1 on `picome` under the exact candidate configurations.

**Gate D:** either singleton is admitted with retained raw evidence and timing,
or work stops with the follow-up decision called for by §7.4.

No cache redesign is part of these tranches.

## 9. Acceptance battery

### 9.1 CPU/fake tests

1. Legal + tool-executed + wrong value gives protocol success but
   `node_correct=false`.
2. Isolated downstream calls use gold predecessors and are not survivor
   selected.
3. Gold and produced predecessor modes remain distinct in call metadata.
4. Exactly three renderer observations are required per latent/node/candidate.
5. Reference artifacts score every cell/renderer correctly.
6. Missing, duplicate, extra and mixed-run rows fail loading.
7. A changed expected value changes scores only.
8. Unauthorized resource and target sentinel values never enter requests or
   bindings.
9. Mutating source profile, prompt mapping, registry or binding dictionaries
   after construction does not change persisted cases/runtime behavior.
10. Unknown prompt revision and revision/content mismatch fail before calls.
11. Envelope-stage and grammar-stage `E_PARSE` cases are distinguished without
    changing terminal parser behavior.
12. Composed scheduled/called/blocked categories reconcile.
13. A code-first `fork_join` still maps the stable semantic node assignment
    through `positions` correctly.
14. Same request under two materially different manifests cannot be compared as
    if only an undeclared field changed.
15. Summary and file hashes rederive exactly; aborted runs are unusable.
16. The scientific evaluator cannot use the Stage-0B completion cache.
17. Existing executor strip, wave/sequential and D11 tool-reexecution tests pass.
18. Two planned cases with identical request bytes remain two singleton
    generation occurrences; evaluator execution never silently deduplicates
    them.
19. Score loading regenerates node/workflow targets independently and rejects a
    self-consistent file whose expected value or label strata were changed.

### 9.2 RTX-4090 acceptance

1. The dedicated worker-development plan contains exactly 180 latents, 540
   observations and 900 full-pass node cases.
2. P0 preserves raw difference evidence for the known Code and Math cases.
3. P1 runs for each distinct candidate configuration and records exact equality,
   wall time and peak VRAM.
4. Every declared candidate runs all three renderers; no `resource_first`
   pre-screen removes an arm.
5. Isolated `scheduled == called`; blocked/world failures are zero.
6. Composed workflow categories reconcile and survivor-selection deltas are
   reported.
7. Every call is cache-disabled and bound to the exact manifest/request.
8. There are zero missing, duplicate, extra or unscored cases.
9. Scores and summary replay from the persisted files in a fresh process.
10. Each accepted candidate's full 900-case result has a second fresh-process
    canonical-order run with exact completion/telemetry equality.

No worker-performance threshold is an infrastructure acceptance criterion.
Poor accuracy is a D16 prompt/model/request result, not an evaluator failure.

## 10. Decisions deliberately left open

### D1 — dedicated worker-development namespace

Approve the small namespace/population erratum before new adaptive D16 runs.
This implementation records and validates it but does not silently alter the
frozen generator.

### D2 — prompt mapping API

Use the smallest implementation that binds a name/status to exact strings:
either a checked mapping in `prompts.py` or a tiny content-addressed loader.
Acceptance is byte identity and fail-closed mismatch, not abstraction style.

### D3 — singleton policy

P1 decides it. Failure produces a separate plan; this branch does not need APIs
for canonical cohorts or stochastic replicates.

### D4 — consumed construction universe

Resolve it explicitly before Stage 1. This is separate from implementing the
worker evaluator.

### D5 — direct prompt

Exercise/freeze it before the construction screen, or explicitly amend D16 to
split worker and direct freeze surfaces. This evaluator does not choose the
prompt.

## 11. Definition of done and integration

The policy-neutral branch is ready to merge when Tranches A–C and all applicable
CPU tests pass, the cache-disabled P0/P1 command is present, and no D16 candidate
content or cache-policy redesign has entered the branch.

After merge:

1. bring the evaluator into `conductor_stage_0b_d16`;
2. approve and generate the dedicated worker-development population;
3. define every surviving candidate before the crossed run;
4. run P0/P1 and admit singleton or stop for a follow-up plan;
5. run every candidate cache-disabled across all renderers with isolated node
   scoring;
6. run composed workflows as the compounding check;
7. compare candidates only when population/support and held-fixed manifest
   fields match;
8. choose and freeze the remaining endpoint, prompt and request-scope decisions,
   including the pending Math-endpoint specification erratum;
9. only then decide the simplest cache/materialization policy actually required
   by Stage 1/2; and
10. resolve the construction/direct-prompt blockers before the formal
    construction screen.

The overall integrity step is successful when any result can be traced through
`manifest.json` and `calls.jsonl` to its exact request/configuration, rescored
from `scores.jsonl`, paired across all renderers, and reproduced without relying
on the current dynamic-miss cache. That is enough for the immediate scientific
question and keeps later integration work contingent on evidence rather than
anticipatory abstraction.
