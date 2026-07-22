# Stage 0 four-worker model-orchestration pivot

**Status: FROZEN 2026-07-22 (Ken).** All five §0 decisions approved
in-session after a verification review (§1 overlap table 235/22/13/0,
§7 cascade 270/270 in 283 calls, §11 arithmetic, and §10.3 canary
existence all re-verified from the retained artifacts; no blocking
findings). Content hashes are recorded in the Freeze Record appended
at the end of this document; the status line and that record are the
only changes from the approved draft. It is a versioned amendment to
the remaining Stage 0 work; it does not rewrite the historical signed
documents or authorize construction, qualification, or Stage-2
training. Original draft status line for the record: DRAFT FOR
REVIEW; becomes normative only after Ken's sign-off and a targeted
review against the frozen plan and cell specification.

## 0. Review and freeze procedure

Sign-off is requested on five decisions:

1. the exact flat four-worker/two-checkpoint pool in §4;
2. `singleton-v1` as the scientific worker policy despite its throughput
   cost;
3. the four-worker oracle/control and schema erratum in §§6 and 8;
4. the identity-selected 18-observation Stage-0 replay support and separate
   disagreement canary; and
5. deferring adaptive cascade and retrospective router analysis to Stage 1,
   with pre-materialized outcomes the preferred Stage-0C path if CE0 passes.

After review findings are resolved, change the status to `FROZEN` and record
the approved commit plus SHA-256 hashes of this document and the existing
worker/prompt identities. Each new registry, replay-support and launch-profile
artifact is then reviewed and hashed before its first GPU use. No new payoff-
surface worker calls or reward-bearing Conductor smoke may run before the plan
freeze. Any later change to those treatment identities requires a versioned
amendment and new hashes.

## 1. Decision and motivation

The universal-Code-worker search stops. Stage 0 will instead finish around a
four-worker pool that exposes the complementary generic 1.5B and generic 3B
Code policies to the Conductor.

The decisive `worker_dev` result is:

| rev10 Code outcome | cases |
|---|---:|
| both generic-1.5B and generic-3B correct | 235 |
| only generic-1.5B correct | 22 |
| only generic-3B correct | 13 |
| neither correct | **0** |

The two Code workers use the same request contract, system prompt, chat
template, tool, grammar, decoding settings and singleton execution policy.
Only their model checkpoint differs. Their post-hoc oracle union is 270/270,
while either worker alone misses the frozen single-worker target. This is a
cleaner model-selection treatment than the earlier prompt-policy ensemble and
is directly aligned with the project's learning question: can GRPO learn that
the larger model is selectively, rather than universally, preferable?

This is **selection evidence**, not qualification evidence. The prompts were
developed on the complete `worker_dev` population, and the 270/270 union is a
hindsight diagnostic. Construction must establish the payoff surface and
select any deployable mapping; fresh qualification must test it without
reselection.

## 2. Corrections to the 3B outcome interpretation

The numerical results in `105_f` stand. The following narrower interpretation
governs this pivot:

1. The 3B screen closes the frozen Qwen2.5/NF4/`task_last`/rev10-rev11
   **single-worker matrix**. It does not establish that every possible
   3B-native prompt, precision or request scope is inferior.
2. The screen rejects the specific prediction that scale would absorb rev11's
   additive rules without regressions. It does not refute every practical
   instruction-capacity account: generic-3B repaired all 13 generic-1.5B
   rev10 failures before creating a different, disjoint failure surface.
3. The dominant generic-3B errors support prompt/context interaction, not the
   stronger claim that 1.5B was unable to solve the whole Problem. Several 3B
   outputs hybridize a local Task, a global-Problem constant and the system
   prompt's complex worked-example skeleton.
4. `local_only` would directly test global-Problem interference, but would not
   necessarily remove the `R-*` cue retained in the Resource block or the
   observed legal off-by-one errors. It is therefore an ablation, not an
   entailed fix.
5. The Coder checkpoints are retired from the core pool. Their handle-copying
   prior is incompatible with the present DSL at both tested scales.

The `coder_3b/rev10` post-download admission rerun is retained as a disclosed
steady-state cost measurement, not represented as strict first-attempt
admission. It has no bearing on the selected pool because no Coder checkpoint
is retained.

## 3. Scope and stopping boundary

This tranche covers:

- a targeted frozen-cell-specification erratum for four workers;
- the smallest Stage-0A compatibility patch required by that erratum;
- completion of the Stage-0B runtime for the exact pool;
- Stage-0C trainer integration, policy-dependent smoke and CE0 benchmark; and
- a go/no-go handoff containing the evidence needed to revise Stages 1–2.

One deliberate Stage-0C delta is explicit: the discarded routing smoke covers
all six cells and all three topology classes, rather than interpreting the
older “one-step routing schema” wording as an atomic-cell-only smoke. The
action remains routing-only; topology and subtasks remain reference-provided.

It does **not** cover:

- another Code prompt revision;
- Coder, 7B, `local_only`, BF16 or constrained-decoding selection arms;
- changing cells, generators, renderers, tools, resource privacy, reference
  subtasks, reward values or intervention semantics;
- construction or qualification data;
- fitting B1 controls, freezing `SYSTEM_DIRECT`, or resolving the consumed
  construction-prefix/D4 decision;
- Stage-2 GRPO beyond the discarded Stage-0C smoke; or
- revising Stages 3–4.

The implementation stops after CE0 and a Stage-0 go/no-go review. Later-stage
numeric gates are revised from measured four-worker evidence, not guessed now.

## 4. Exact worker pool

There are four **logical workers** backed by two **physical checkpoints**:

```text
generic_1p5b = Qwen/Qwen2.5-1.5B-Instruct@989aa7980e4cf806f80c7fef2b1adb7bc71aa306
generic_3b   = Qwen/Qwen2.5-3B-Instruct@aa8e72537993ba99e69dfaafa59ed015b17504d1
```

| worker id | stable name | endpoint family | physical checkpoint | resolved `rev10` endpoint prompt bytes |
|---:|---|---|---|---|
| 0 | `lookup_1p5b` | Lookup | `generic_1p5b` | inherited rev9 Lookup bytes |
| 1 | `math_1p5b` | Math | `generic_1p5b` | amended rev10 Math bytes |
| 2 | `code_1p5b` | Code | `generic_1p5b` | inherited rev9 Code bytes |
| 3 | `code_3b` | Code | `generic_3b` | inherited rev9 Code bytes |

`rev10` is one global `PromptBundle`, not three independently selectable
prompt labels. Its Lookup and Code components are byte-identical to rev9;
only Math was amended. The registry stores the bundle revision and each
resolved endpoint system-prompt SHA, so no mixed or nonexistent prompt
configuration can be assembled from the descriptive component names above.

All use:

- request contract `worker-blocks-task-last-v1`;
- private visibility for the primary condition;
- NF4 with double quantization and BF16 compute;
- greedy decoding, `do_sample=False`;
- `singleton-v1` authoritative generation: physical generation batch size is
  exactly 1 even when calls are collected and scheduled in waves;
- the currently registered endpoint token caps, stop rules, tokenizer/chat
  templates and tool versions, with scientific microbatch set to 1; and
- exact model/prompt/request fingerprints regenerated and appended to the
  implementation freeze record.

The names above are stable scientific identities. A worker identity is not an
endpoint-family alias and is not merely a model id.

## 5. Worker, endpoint and checkpoint are distinct concepts

The present implementation often treats the three endpoint indices as worker
ids. That equivalence ends here. The minimal normative worker record is:

```text
WorkerSpec:
  worker_id: int
  name: str
  endpoint_family: lookup | math | code
  model_id: str
  model_revision: str
  prompt_bundle_revision: str
  endpoint_system_prompt_sha256: str
  decoding/runtime fingerprint inputs
```

The corresponding minimal mappings are exact:

```text
WORKER_IDS = (0, 1, 2, 3)
WORKER_TO_ENDPOINT = {0: lookup, 1: math, 2: code, 3: code}
```

Endpoint-family constants remain three-valued and are never reused as the
four-worker action domain. Reference/tool agreement may choose the canonical
worker for a family, but that choice does not expand the 10k semantic battery
or turn worker 3 into a fourth tool.

The ordered `WorkerSpec` entries embedded in the named runtime profile are
the single authoritative representation. The registry is only their
immutable indexed view plus its content hash; it must not duplicate editable
model or prompt settings. Physical sharing is derived from the exact
`(model_id, model_revision, quantization_config, device)` key. Labels such as
`generic_1p5b` in the table are shorthand for the exact reference above,
never an independent claim that two workers share weights.

The separation has three consequences:

1. **Action selection is by worker.** The Conductor emits a worker id.
2. **Artifact parsing and tool execution are by endpoint family.** Workers 2
   and 3 share the Code grammar and interpreter.
3. **Loading is by derived physical checkpoint key.** Workers 0–2 share one
   resident model object, while worker 3 uses the generic-3B object. Any
   recorded logical-to-physical manifest is re-derived and compared rather
   than trusted as configuration.

The public generation boundary is
`worker_call_batch(worker_id, user_messages)` (executed as singleton chunks in
this profile); it resolves the family through the registry. Artifact parsing
and tool execution receive the resolved endpoint family. No public boundary
accepts an untyped integer and guesses whether it denotes a worker or an
endpoint.

No general plugin framework is required. One immutable four-entry registry,
used consistently by parser, executor, cache, traces and oracle code, is the
preferred didactic implementation.

## 6. Frozen action and execution deltas

### 6.1 Routing action

Stages 0C/2 use the same compact schema:

```json
{"worker_ids": [0, 3, 1]}
```

Rules:

- the array length is exactly the number of reference steps;
- entries are JSON integers in `{0, 1, 2, 3}`;
- duplicates remain permitted;
- extra fields and ids outside the pool are schema violations with reward 0;
- stable node order and `positions` conversion are unchanged; and
- the valid action set is the exact enumeration of `4^S` assignments.

Expected assignment counts are 4, 16 and 64 for one-, two- and three-step
cells. These counts replace 3, 9 and 27 everywhere that describes the active
four-worker experiment. Historical three-worker artifacts retain their own
schema/version and must never be silently reinterpreted.

### 6.2 Candidate execution

For a given reachable predecessor context, every selected worker receives the
same endpoint-neutral user-message blocks, node-local payload and predecessor
values. Endpoint family determines the system prompt, full chat rendering,
artifact parser and tool. Selecting an incompatible family is a well-formed
world action and normally yields a typed worker/tool failure and reward 0.5,
exactly as before.

Workers 2 and 3 must receive byte-identical rendered requests for the same
node. Their distinct results must be attributable only to their checkpoint
fingerprints.

### 6.3 Oracle and controls

The existing construction/qualification separation and cluster-weighted
objective remain unchanged. Generalize only the candidate set:

- full surface: `product(WORKER_IDS, repeat=S)`;
- tie-breaking: lexicographically smallest worker-id tuple;
- runner-up: best of the other three workers at the node with other nodes
  fixed;
- `best_fixed`: best of `(0,...,0)` through `(3,...,3)`;
- `random`: exact uniform mean over the `4^S` surface;
- best one-call: argmax over four workers;
- hindsight per-example maximum: diagnostic only; and
- frozen deployable mapping: may condition on `(cell_id, node_id)` only,
  exactly as in rev8. It does not condition on renderer, private values,
  qualification outcomes or realized success.

The learned policy may condition on its public observation and can therefore
legitimately outperform the fixed deployable mapping. The signed deployable
gap remains unclipped and may be negative.

The two-call shortcut family must be regenerated mechanically from the
four-worker registry rather than retaining the historical count of 18.
Orientation and lexicographic tie rules remain unchanged. It therefore has
`2 × 4 × 4 = 32` workflows. The implementation asserts that cardinality from
the constructor; 32 is an acceptance expectation, not a second hard-coded
source of truth.

### 6.4 No universal-worker acceptance requirement

D16's old requirement that one Code worker reach 270/270 is retired. Stage 0
accepts a reproducible worker pool and runtime, not a hindsight-perfect
worker. Stage 1 later decides whether the construction-frozen payoff surface
has sufficient qualification accuracy and effective stakes for learning.

The current 270/270 pairwise union motivates the pool but is not itself a
Stage-0 gate or a qualification claim.

## 7. Deferred adaptive cascade baseline

Retain the following explicitly non-policy baseline definition for the
Stage-1 revision; do not add an adaptive executor path during Stage 0:

1. execute `code_1p5b`;
2. if and only if its `WorkerResult` is a registered typed protocol/tool
   failure, execute `code_3b` on the identical request; and
3. use the second result; never retry a schema-valid executed result merely
   because it may be semantically wrong.

There is at most one retry. When implemented, both calls, fingerprints, costs
and cache events are traced. This baseline is not:

- a fifth worker;
- part of the one-shot assignment surface;
- reachable through the Stage-2 routing schema; or
- evidence that a one-call policy can predict the correct model.

On retained `worker_dev` evidence the narrower parser-triggered cascade scores
270/270 in 283 calls (1.048 calls per Code case). That is post-hoc motivation
only. Stage 1 must freeze the exact retry codes before implementation and
validate the baseline on fresh data. It later measures the accuracy/cost
trade-off between reactive failure recovery and learned one-shot selection.

## 8. Stage-0A compatibility patch

Stage 0A remains closed except for this versioned experiment change. Make the
smallest coherent patch:

1. add the immutable four-worker registry and pool fingerprint;
2. decouple worker id from endpoint family;
3. update compact-routing and full-workflow parsing plus full-assignment
   enumeration;
4. generalize oracle/control constructors to the registry rather than a
   hard-coded range of three;
5. bump every affected persisted contract: runtime profile/pool manifest,
   step-trace schema/manifest, payoff/calibration bundle, action-bearing
   artifact and diagnostic replay fixture. The raw JSON action envelope has
   no embedded version and remains unchanged. Rename/version the old
   selected-endpoint fingerprint field when it acquires selected-logical-
   worker semantics; do not leave a v1 field name carrying a new identity;
6. preserve historical trace/manifest identity and fail closed when a
   four-worker operation receives an old pool hash; no dual-version scientific
   payoff loader is required unless an actual persisted three-worker payoff
   bundle is identified; and
7. update only fixtures whose meaning genuinely contains the worker pool or
   routing action.

Required CPU regression tests:

- routing-action bijection for 4/16/64 assignments;
- ids 0–3 accepted and 4/negative/bool/non-integer ids rejected;
- deterministic lexicographic ties across four workers;
- `best_fixed`, `random`, runner-up, best-one-call and two-call controls derived
  from the same registry;
- both Code workers select the same parser/tool family;
- different worker fingerprints cannot share a result/cache identity;
- workers 0–2 share a physical checkpoint identity without sharing prompt
  identity;
- persisted three-worker and four-worker bundles cannot be mixed;
- existing generation, renderer, reference/tool agreement, privacy,
  interventions and serialization tests remain green; and
- the recorded reference-vs-tools result remains 16,665/16,665 node
  executions over exactly 10,000 latents, and the generator byte fixture is
  unchanged, because no task semantics changed.

Review is limited to these changed contracts and regressions. This amendment
does not trigger another open-ended adversarial audit of Stage-0A internals.

## 9. Stage-0B completion

### 9.1 Runtime and physical sharing

`build_runtime(profile)` resolves the exact four-entry registry. The loader:

- constructs one generic-1.5B model/tokenizer object for workers 0–2;
- constructs one generic-3B model/tokenizer object for worker 3;
- verifies registered revisions and parameter counts before use;
- exposes worker-specific rendering/generation over shared physical objects;
- records the logical-to-physical mapping in every manifest; and
- fails closed if a profile omits, duplicates or relabels a worker.

Keep scheduling simple: collect same-depth calls by logical worker within a
wave, but pass them through the frozen singleton generator one at a time;
share model objects at load time. A larger physical generation batch is a
different worker policy because D16 observed batch-composition sensitivity.
CE0 may measure it as a labelled diagnostic, but it cannot select it for the
scientific profile without a new preregistration and worker revalidation.

### 9.2 Executor

The executor collects and schedules same-depth calls by selected worker while
the pool executes singleton generations, and retains the reference-free
boundary. Traces add:

- `worker_id` and stable worker name;
- endpoint family;
- the re-derived physical checkpoint key; and
- worker and endpoint-family fingerprints.

The terminal/scorer split, reward ladder and unexpected-infrastructure-abort
semantics do not change.

### 9.3 Cache and provenance

The cache key retains the frozen three-part scope:

```text
worker-visible execution fingerprint
+ selected-logical-worker fingerprint
+ canonical rendered request
```

The selected-logical-worker fingerprint is the four-worker replacement for
the old selected-endpoint fingerprint. It includes worker id and stable name,
endpoint family, model revision, prompt and chat-template bytes, endpoint
grammar/tool versions, quantization, decoding, caps and stopping. The full
runtime-profile fingerprint continues to govern Conductor generations and
trace manifests; it does not replace the worker-visible cache scope.
Workers 2 and 3 have identical request hashes but necessarily different cache
keys. Workers 0–2 may share weights but necessarily differ by prompt and
endpoint family. Cache hits never cross those identities, while byte-identical
worker requests may still share across private/visible Conductor observation
conditions exactly as D11 requires.

Population/execution manifests bind the four-worker registry hash and its
logical-to-physical mapping. A three-worker manifest is not sufficient
provenance for a four-worker gate.

### 9.4 Evaluation paths

The worker-evaluation code must support two distinct schedules:

1. **operator-aligned D16 diagnostics**, retained for historical comparison;
2. **full assignment/payoff execution**, in which every registered worker is a
   valid candidate at every node and incompatibility is observed rather than
   filtered out.

Do not implement the full surface by pretending that worker 3 is a second
endpoint family. It is a second worker in the Code family.

Build one small, fixed diagnostic support from already retained `worker_dev`
identities; allocate no new generator namespace. Select the first latent by
the frozen generator ordinal in each cell and cross it with all three private
renderers: 18 observations selected by identity, never by worker outcome. The
support must contain the complete, context-aware `4^S` assignment-to-terminal-
payoff surface for every observation, including wrong-family calls. Underlying
call provenance remains keyed by the actual rendered request, including every
reachable predecessor context. The identities and current profile hash are
recorded before the new wrong-family calls run. This is a runtime fixture, not
a population estimate.

The naive no-dedup upper bound is 804 step executions:
`3×3×4 + 2×3×16×2 + 1×3×64×3`. Dependency blocking and exact-request cache
reuse may reduce physical generations, but the runner records both planned
step executions and actual unique singleton calls rather than assuming the
saving.

Separately register one already known worker-2/worker-3 terminal-reward
disagreement as a deterministic plumbing canary. It is deliberately selected
for disagreement and is therefore excluded from aggregate smoke reward,
variance and routing-stakes summaries unless it independently belongs to the
identity-based support.

The richer always-small/always-large, semantic-subtype, renderer-only,
bag-of-words and hindsight routing audit is deferred to the Stage-1 design.
Any later use of the retained D16 population is labelled post-hoc and
worker-dev-fitted, never “construction-frozen.”

### 9.5 Stage-0B acceptance

Stage 0B completes when:

- all CPU tests pass under warnings-as-errors;
- all four workers produce valid bound requests and traces;
- worker-2/worker-3 same-case request bytes are identical;
- a small committed sentinel set of retained `99_f`/`104_f` requests is
  reproduced bit-for-bit by workers 2 and 3 in fresh singleton processes;
- model-order and fresh-process singleton checks are stable;
- cold-cache then warm-cache replay proves worker-specific cache isolation;
- the fixed diagnostic support is complete over every valid assignment and a
  missing or wrong-profile payoff row aborts;
- the real-pool offline executor smoke exercises atomic, chain and fork cells;
- typed wrong-family outcomes do not abort the run;
- peak worker-only VRAM and latency are recorded; and
- no additional construction examples and no qualification examples have
  been touched.

The F3 runs admitted the mixed generic-1.5B/generic-3B layout below the 22-GiB
gate; `104_f` had conservatively estimated approximately 7.8 GiB. This
establishes provisional feasibility, but the exact final Stage-0B profile is
measured again after the registry/runtime change rather than inferred from a
D16 candidate run.

## 10. Stage-0C trainer integration

### 10.1 Named launch profile

Check in the experiment profile required by the signed plan:

- QLoRA Conductor on
  `Qwen/Qwen2.5-3B-Instruct@aa8e72537993ba99e69dfaafa59ed015b17504d1`,
  the same frozen base checkpoint used by worker 3;
- NF4 double quantization with BF16 compute and gradient checkpointing;
- LoRA rank 16, alpha 32, dropout 0.05 and targets `q_proj`, `k_proj`,
  `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`;
- beta `1e-3`, retained primarily to expose KL telemetry but acknowledged as
  a small nonzero contribution to the training objective;
- group size 8;
- rollout temperature 1.0;
- per-device batch 2 and gradient accumulation 8, giving two prompt groups
  per optimizer update;
- learning rate `1e-5`, ten-step warmup, constant schedule and the repository's
  current DAPO-normalized GRPO loss;
- `adamw_torch`, BF16 training and seed 0;
- policy completion cap 128 tokens;
- worker completion cap 256 tokens and physical generation batch size 1;
- four-worker registry and physical mapping;
- `workflow_max_steps=3`;
- explicit `worker_outcome_mode` in
  `{precomputed_surface, live_singleton}` (distinct from the raw-completion
  cache);
- W&B project `qwen-grpo-conductor`, and a run name containing the
  launch-profile and support-manifest hashes; and
- periodic evaluation disabled for this discarded diagnostic (`n_eval=0` /
  no eval strategy), so no dev/test namespace is invented.

The smoke schedule is frozen before launch: 18 updates and 36 prompt groups,
each of the 18 §9.4 observations used exactly twice in a recorded deterministic
order. This is approximately the signed 20-update smoke while giving every
cell and renderer equal support and guaranteeing nonzero atomic, two-step and
fork/join coverage. The named profile records an equal six-cell diagnostic
mixture and the support-manifest hash; stochastic resampling may not silently
replace the schedule.

No repository default may silently fill a scientific setting.

The Conductor registers exactly one scalar task reward implementing the
frozen `0 / 0.5 / 1.0` ladder. Do not add the repository's generic
`format_reward` as a second weighted reward: that would change the relative
advantages between malformed actions, world failures and correct executions.
Action parse rate is telemetry. The task registry may expose task-specific
`reward_funcs`; legacy tasks retain their existing format-plus-correctness
pair. Unit tests pin all three rewards and the infrastructure-abort path
through the actual trainer-facing callable.

### 10.2 Policy prompt and parser

The Stage-0C/2 observation skeleton is unchanged apart from listing four
opaque ids in demonstrations/instructions. The policy emits only
`{"worker_ids": [...]}`. It is not told model names, sizes, endpoint-family
labels or the small/large relationship.

The reference subtasks provide legitimate semantic information. Worker ids
remain fixed and opaque in v0; pool randomization remains a later relaxation.

Before the smoke, separately review and fingerprint the exact Conductor
system prompt and four executable out-of-domain demonstrations already
required by the signed plan. All four ids must occur in valid demonstrated
actions. Workers 2 and 3 should be shown on matched, non-`worker_dev` Code-like
steps that both execute successfully, so the examples establish that both are
legal Code candidates without encoding the retained renderer-conditioned
lookup table. Once any reward-bearing smoke output is inspected, these prompt
bytes are frozen; a later change is a new launch profile, not an in-place edit.

### 10.3 Policy-dependent smoke

Run the frozen 18 GRPO updates with the real routing parser and sampled action
determining reward. This model and its optimizer state are discarded;
the run is an integration diagnostic and does not consume a train/dev/test or
qualification claim.

The smoke reads the fixed Stage-0 diagnostic replay fixture from §9.4. It
allocates no `train`, `dev`, `test`, construction or qualification namespace.
Its retained `worker_dev` observations remain diagnostic-only and neither the
resulting policy nor any smoke-derived choice enters a later scientific run.

In `precomputed_surface` mode, the fixture is exactly the complete,
profile-bound
`4^S` support produced in §9.4. Every schema-valid sampled action therefore
has an outcome; a missing row, stale pool hash or partial surface is an
infrastructure abort, never reward 0 or 0.5. `live_singleton` uses the same
fixed identities and singleton policy.

Record at minimum:

- action-schema validity;
- reward frequencies 0/0.5/1;
- zero-variance-group fraction;
- groups containing both 1.0 and a lower reward;
- selection entropy and frequency per worker id;
- figures by atomic/two-step/fork topology;
- outcome-surface lookup counts and, in `live_singleton`, raw-completion cache
  hit/miss counts;
- wall time and peak VRAM; and
- infrastructure aborts.

Persist complete action, workflow and scoring traces. Keep the live dashboard
to action-parse rate, reward-level frequencies, zero-variance-group fraction
and worker-selection entropy; derive the remaining cuts from traces after the
run.

Before the sampled smoke, run otherwise-identical valid actions selecting
worker 2 and worker 3 on the separately registered canary and require the
terminal rewards to differ.
This deterministic check proves that model-scale selection reaches the reward
path; whether the sampled policy happens to choose both workers is measured,
not made a luck-dependent acceptance condition. No worker prompt, request
contract or task profile is tuned from this smoke.

### 10.4 Worst-case benchmark and CE0

Before any CE0 GPU command, append and freeze a `conductor_log.md` entry with
the executable commit, profile/support hashes, exact commands, predicted call
counts and the gates below. Results append to that entry; thresholds do not
move after launch.

Benchmark:

- forced-valid four-worker policy actions;
- cache-disabled live worker execution under the frozen physical batch size
  of 1;
- immutable pre-materialized outcomes as the likely Stage-2 routing path;
- `4^S` enumeration/composition overhead through `S=3`;
- Conductor plus both physical worker checkpoints when live co-residency is
  requested; and
- the simplest sequential-load alternative if co-residency is unnecessary or
  materially slower.

Because the Conductor and worker 3 share a base checkpoint, consider three
explicit deployment modes in this order and stop at the first simple mode
that satisfies the intended live/cached use case and CE0 gates:

1. **pre-materialized routing** — workers absent during GRPO; this is the
   simplest default if immutable complete surfaces are accepted;
2. **separate live objects** — one QLoRA Conductor object and an independent
   adapter-free worker-3 object, plus the shared 1.5B worker object; and
3. **single-object adapter toggling**, diagnostic only unless disabling and
   restoring LoRA reproduces the standalone worker-3 sentinel bytes exactly,
   leaves gradients and optimizer state untouched, and restores the Conductor
   adapter state after every call.

Do not implement modes 2 or 3 merely to complete a comparison if
pre-materialization passes. Do not assume that common checkpoint weights make
mode 3 safe or cheaper in practice. A failed sharing probe falls back to modes
1 or 2 rather than prompting custom model-lifecycle machinery.

Do not consume formal construction data merely to measure enumeration. Use
the same §9.4 diagnostic support; the actual construction pass remains Stage
1.

CE0 retains the signed gates:

- peak reserved VRAM below 22 GiB;
- projected Stage-2 seed no longer than overnight;
- no infrastructure failures represented as reward;
- a sane, non-degenerate sampled reward distribution; and
- a recorded worst-case throughput prediction including four-worker surface
  construction.

For this integration smoke, “sane, non-degenerate” means: every worker id
appears in at least one schema-valid action; workers 2 and 3 each appear at a
Code position; at least one sampled outcome earns 1.0; and at least one group
contains both 1.0 and a lower reward. Exact per-topology fractions remain
descriptive here and receive the signed ≥64-group cold-start treatment only
in Stage 1. Failure is a Stage-0 no-go requiring a reviewed launch-profile
decision, not an invitation to tune demonstrations against the same output.

Report one-time singleton payoff-materialization wall time, unique worker
calls and disk footprint separately from routing-only GRPO time per seed. Also
report time to the first completed seed and steady-state additional-seed time;
precomputation may be amortized but may not disappear from the 4090 feasibility
accounting.

The exact materialization policy is selected from measurement. Do not assume
that all physical workers must remain resident during routing-only GRPO if
outcomes are immutable and pre-materialized.

## 11. Cold-start expectations, not gates

Replacing three choices with four changes uniform-prior arithmetic. Under the
simplifying assumption of one suitable Lookup worker, one suitable Math worker
and two potentially suitable Code workers:

| topology | suitable-assignment upper-bound arithmetic | group-of-8 chance of at least one suitable assignment |
|---|---:|---:|
| Lookup/Math atomic | `1/4` | 90% |
| Code atomic | up to `2/4` | up to 99.6% |
| Lookup→Math | `1/16` | 40% |
| Math→Code | up to `2/16` | up to 66% |
| fork/join | up to `2/64` | up to 22% |

Using the observed Code overlap lowers the latter estimates slightly. These
are planning diagnostics only: pretrained routing priors, parser invalidity,
worker noise and demonstrations make the real distribution non-uniform.

Stage 0C measures the actual fractions. It does not rescue a weak result by
changing group size or demonstrations after inspection. Any intervention is a
new preregistered Stage-2 decision made after the go/no-go review.

## 12. Scientific controls carried forward

The later Stage-1/2 revision must include:

- best single worker and best single Code-scale policy;
- the construction-frozen best one-call whole-task baseline, which remains
  the control that speaks directly to hierarchy's value;
- exact-uniform four-worker routing;
- frequency-matched random routing;
- construction-frozen deployable assignment;
- shallow renderer/bag-of-words routing;
- semantic-subtype routing;
- hindsight oracle, diagnostic only;
- the parser-gated 1.5B-to-3B cascade with call cost;
- compute-matched best-of-N where applicable; and
- trained Conductor routing.

The pivot does not remove or redefine the frozen B1–B6 baseline family:
public-only direct plus its majority/public-parameter-echo/shallow controls,
endpoint without resource, visible direct, local-node capability, one-call
whole-task, and generic-subtask execution all carry forward. Echo/no-op
pseudo-workers and
answer-in-subtask telemetry also remain. Their Stage-1 fitting, the
`SYSTEM_DIRECT` freeze and any four-worker candidate-set generalization are
reviewed before construction; they are not Stage-0 implementation work.

Primary reporting separates:

1. endpoint-family selection (Lookup/Math/Code);
2. within-Code model-scale selection;
3. renderer sensitivity; and
4. terminal accuracy versus physical-call cost.

The v0 defensible claim remains modest: GRPO learns fixed worker selection in
a transparent typed environment. Renderer-conditioned routing is allowed as a
real language-to-worker compatibility effect, but renderer-only and shallow
controls must be reported. Generalization beyond fixed templates remains
deferred to an unseen paraphrase/semantic renderer.

## 13. Implementation order and review units

Implement in bounded commits/PR review units:

1. **Specification erratum and registry contract** — exact four workers,
   action/oracle/control deltas, schema versions and CPU fixtures.
2. **Stage-0B runtime** — shared physical loading, worker-specific execution,
   cache/provenance and offline smoke.
3. **Evaluation support** — complete four-worker diagnostic payoff path and
   retained-request sentinels; no adaptive execution path.
4. **Stage-0C integration** — task registration, reward path, named launch
   profile and policy-dependent smoke.
5. **CE0 benchmark and handoff** — measured memory/throughput, reward dynamics,
   materialization recommendation and go/no-go record.

Each unit receives a changed-lines/conformance review. Do not repeat the
open-ended Stage-0A internal-object audit. Any critical issue affecting
identity, phase separation, reward, privacy, reproducibility or the payoff
estimand remains in scope regardless of changed lines.

## 14. Stage-0 exit criteria

Stage 0 is complete only when:

- the targeted cell-specification erratum is signed and implemented;
- the exact four-worker registry and fingerprints are frozen, and D16 closes
  with these worker-side model, prompt and request-contract hashes recorded as
  the selected artifact rather than another development candidate;
- Stage-0A compatibility tests and the recorded agreement command pass;
- Stage-0B real-pool smoke, cache/provenance and trace checks pass;
- the deterministic worker-2-versus-worker-3 action pair changes terminal
  reward, sampled completions demonstrably drive the same scorer, and the
  sampled reward/selection distribution is recorded;
- CE0 memory, runtime and reward-distribution gates pass;
- no additional construction examples and no qualification examples have
  been touched;
- the unresolved Stage-1 prerequisites are enumerated rather than represented
  as complete (`SYSTEM_DIRECT` remains a Stage-1 prompt blocker; it is not
  part of the worker-side D16 freeze); and
- a handoff document records the exact executable commit, profile, artifacts,
  metrics and decision.

At that point stop. Revise Stage 1 and Stage 2 from the measured four-worker
surface and cold-start evidence. Do not begin construction, qualification or a
headline GRPO seed under this Stage-0 document.

## 15. Explicitly deferred decisions

The Stage-0 handoff, not this plan, informs:

- CE1 confidence intervals, sequential looks and qualification sample sizes;
- how the frozen `<2%` parse/truncation gate on on-contract calls maps to two
  intentionally imperfect Code workers: per logical worker, selected route,
  or a separately reported pool quantity. CE1 must decide this before
  construction/qualification outcomes; Stage 0 neither inherits nor relaxes
  it silently;
- whether every position has enough effective routing stakes to remain
  learnable;
- the exact Stage-2 cached-versus-live materialization policy;
- any group-size or curriculum intervention;
- D4, B1 and `SYSTEM_DIRECT` close-out;
- whether `local_only`, anonymous resources, BF16 or constrained decoding are
  later ablations;
- an unseen paraphrase/semantic-renderer tranche;
- recursive/failure-aware orchestration as a learned action; and
- Stages 3–4.

No result from the four-worker pivot retroactively changes the historical
three-worker D16 artifacts. They remain the evidence that motivated this
versioned model-orchestration design.

## Freeze Record (appended at freeze, 2026-07-22)

Recorded per §0 with Ken's approval of all five sign-off decisions.
Approved draft = this document at commit `08ae2a1`, sha256
`73f30391359abaa0f4ee426275f17d1e0338952c1f9ab02d05d34b716308f21d`
(the status line and this record are the only subsequent changes).

**Worker pool identities (§4):**

- `generic_1p5b` = `Qwen/Qwen2.5-1.5B-Instruct`
  `@989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, 1,543,714,304
  parameters (device-verified)
- `generic_3b` = `Qwen/Qwen2.5-3B-Instruct`
  `@aa8e72537993ba99e69dfaafa59ed015b17504d1`, 3,085,938,688
  parameters (device-verified in the 104_f runs)

**Prompt bundle `rev10`** (one global bundle; Lookup/Code bytes
inherited from rev9):

- lookup `b013c142be2ed48fea221196f80bdbc0b8fb459c83a73c62c42c03986f6f952f`
- math   `24c16a2115eceed072c0189692bf25799e59977f199829cc1f896e9da3b48787`
- code   `9b08f3e6f4afad854484a13257d973e79e8664194f16cf44930644ab22e88aea`

**Request contract:** `worker-blocks-task-last-v1` digest
`8638fdad716e1e0c55b733298f8d0b4061af8dc5851ba0e6b8c99017642b5a7c`
(all four workers).

**Chat template** (shared across all Qwen2.5 endpoints, the fact that
made the F3 screen a weights-only swap):
`cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f`.

**Support registry at freeze:** `support_digests.json`
`afa796aac5994841dbbb13e74cf699fae9b89517769fa513c19df3182e599899`
(23 candidates).

**Evidence base:** `runs/99f-rev10` (worker-2 policy),
`runs/104f-3b-screen` (worker-3 policy; guard: 630 Lookup/Math records
byte-identical across every arm and the 99_f run). Historical
three-worker D16 artifacts are unchanged by this freeze (§15).

Per §0, each new registry, replay-support and launch-profile artifact
is reviewed and hashed before its first GPU use; implementation
proceeds in the §13 review units.
