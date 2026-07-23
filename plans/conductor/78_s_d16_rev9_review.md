# D16 rev9 review — renderer crossing, semantic scoring, and runtime determinism

**Date:** 2026-07-21

**Review target:** `conductor_stage_0b_d16` at `1ef97e6084db5f6c41c9d660d00338324b9d68d2`

**Evidence reviewed:** `plans/conductor/60_f_d16_rev1.md` through
`77_f_d16_rev9_critique.md`, `conductor_log.md`, the frozen rev6 plan and rev8
cell specification, the Stage-0B runtime implementation, and the retained
`d16-rev*` execution traces.

## Verdict

Rev9 is a useful **candidate**, but D16 is not ready to freeze and the
construction screen should remain blocked.

The Lookup prompt is in good shape. The decision to replace
`Qwen2.5-Math-1.5B-Instruct` with the generic
`Qwen2.5-1.5B-Instruct` Math endpoint is well supported and should be
formally ratified. The Code endpoint remains unresolved, but the new evidence
does not point primarily to raw model size. Its dominant problems are:

1. interaction between the full public `Problem` and the assigned local
   `Task`;
2. severe sensitivity to the frozen renderer variants;
3. strict DSL compliance being conflated with semantic competence; and
4. generation and cache behavior depending on batch composition.

The next step should therefore be a bounded request-scope and model comparison
across all renderers, using a corrected node-level evaluator. Further
unstructured prompt wordsmithing on the existing `resource_first` smoke set
would not be informative.

## What the revision cycle did well

The cycle is a strong engineering and failure-analysis trail in several
respects:

- fixed construction instances made revision comparisons paired;
- hypotheses and negative results were retained rather than rewritten away;
- rev4's layout intervention, rev8's removal of the copyable guard example,
  and rev9's matched-regime example were reasonably focused;
- the Math investigation cleanly separated prompt content from endpoint-model
  behavior, and rev6 held the prompt fixed while changing the model;
- qualification namespaces were not inspected;
- demonstrations are machine-verified and prompt changes are reflected in the
  byte fixture; and
- the final run included a fresh index slice rather than reporting only on the
  repeatedly tuned prefix.

The principal problem is not that the iteration was careless. It is that the
workflow smoke and single-renderer sample were too narrow to support several of
the final scientific conclusions.

## Finding 1 — endpoint `success` is not subtask correctness

`tasks/conductor/smoke.py` increments endpoint success when
`WorkerResult.status == "success"`. That status means that an artifact parsed
and the endpoint tool executed; it does not mean that the emitted expression
produced the reference node value.

Independent replay of the rev9 confirmation trace against the generated
reference-node values gives:

| Endpoint / cell | Legal artifacts | Reference-node correct |
|---|---:|---:|
| Lookup, all called reference nodes | 90/90 | 90/90 |
| Math, all called reference nodes | 116/116 | 116/116 |
| Code — `code_atomic` | 29/30 | 29/30 |
| Code — `fork_join` | 26/30 | 26/30 |
| Code — `math_code` | 23/30 | **22/30** |
| **Code total** | **78/90** | **77/90** |

The omitted semantic failure is
`math_code:construction:00019:73c89c4b:resource_first:private`, whose second
step emitted:

```text
<artifact>at(rotate_left(stable_unique(resource), 2), step_1)</artifact>
```

The artifact is legal and executed, but returned 17 rather than the reference
value 64. It appears to blend the second and third Code demonstrations into an
unrelated `math_code` request. It is not addressed by the proposed
`step_1 <= 8` mitigation: this instance has `step_1 = 2`.

### Required change

Add a D16 evaluation path that reports, separately:

- envelope and grammar validity;
- tool execution;
- reference-node correctness;
- terminal workflow correctness;
- scheduled, called, and dependency-blocked denominators; and
- renderer, cell, node family, endpoint, and index strata.

The executor should remain reference-free. Reference-node values and golds
belong in a separate evaluator-generated summary artifact, not in the worker
execution path.

## Finding 2 — workflow smoke causes survivor-selected endpoint samples

The current smoke executes complete reference-routed workflows. A downstream
request is observed only when every required predecessor succeeds. This is why
the Code step of `math_code` was not exercised at all until the Math endpoint
was replaced at rev6.

Consequences include:

- endpoint denominators change when an upstream endpoint improves;
- revisions do not always compare the same downstream request population;
- one worker can conceal unsupported request shapes in another; and
- the final Math result is 116/116 among calls actually made, while four of 120
  scheduled `fork_join` Math calls were blocked by Code failures.

### Required change

Before freezing D16, independently issue every reference-node request with
gold predecessor values. Retain end-to-end reference-routed workflows as a
second test of composed behavior.

## Finding 3 — the omitted renderer crossing changes the conclusion

All nine prompt revisions evaluated only `resource_first`, but the frozen
distribution crosses each latent program with `resource_first`, `goal_first`,
and `bound_var`.

An independent construction-only crossing of the same 30 latents per cell
produced the following strict reference-node correctness for the current
`Qwen2.5-Coder-1.5B-Instruct` endpoint:

| Renderer | `code_atomic` | `math_code` | `fork_join` | Total |
|---|---:|---:|---:|---:|
| `resource_first` | 29/30 | 22/30 | 26/30 | 77/90 |
| `goal_first` | 29/30 | 30/30 | **1/30** | 60/90 |
| `bound_var` | 30/30 | 30/30 | **3/30** | 63/90 |

The alternative-renderer `fork_join` failures commonly attempted to solve or
compose the global Problem rather than translate the assigned Code branch, for
example:

```text
<artifact>count_gt(stable_unique(resource), 7) + grove_spools</artifact>
<artifact>count_gt(stable_unique(resource), 5) * maple_crates</artifact>
```

The renderer effect is not uniformly adverse: `math_code` improves to 30/30
under both alternative renderers. That further weakens the claim that its
large-index guard is a renderer-independent model limit.

The generic 1.5B alternative also fails the renderer crossing, but in a
different pattern:

| Renderer | `code_atomic` | `math_code` | `fork_join` | Total |
|---|---:|---:|---:|---:|
| `resource_first` | 30/30 | 30/30 | 26/30 | 86/90 |
| `goal_first` | 15/30 | **0/30** | 6/30 | 21/90 |
| `bound_var` | 22/30 | 30/30 | 29/30 | 81/90 |

On all 30 `goal_first` `math_code` calls, the generic model ignored the
provided `step_1` and reconstructed the global formula before indexing. This
is decisive evidence that the immediate problem is request scoping and
Problem/Task salience, not simply whether the endpoint has 1.5B or 3B
parameters.

It also creates a scientific risk for Stage 2: if endpoint payoffs change with
cosmetic renderer wording, GRPO can learn a renderer-specific routing shortcut
rather than stable semantic specialization.

## Finding 4 — the Code “model limit” is mostly a protocol limit

The current rev9 `resource_first` Code failures decompose as follows:

- four `fork_join` calls used the authorized `R-...` handle instead of the
  artificial interpreter alias `resource`;
- seven `math_code` calls emitted
  `at(resource, step_1 % length(resource))`;
- one `code_atomic` call had genuinely malformed nesting; and
- one `math_code` call was legal but semantically wrong through demonstration
  over-application.

The first eleven would be extensionally correct under a narrow analysis-only
normalization: the handle identifies the locally authorized payload, and the
modulo guard is a no-op because generation guarantees a valid index. Official
strict scores must not silently apply that normalization, but the diagnostic
distinguishes sequence reasoning from exact DSL obedience.

The defensible conclusion is therefore:

> Under rev9, Qwen2.5-Coder-1.5B has a brittle strict-DSL and local-task
> compliance boundary whose location depends on renderer and batching.

It is not yet defensible to call this a general Code-model capability limit.

For the same reason, narrowing `math_code` to `step_1 <= 8` should not be the
first remedy. It would fit the task distribution to a discovered interface
quirk, would not repair the low-index demonstration-copying failure, and could
hide rather than explain the learning environment's noise.

## Finding 5 — model size is not the governing variable

The same 90 `resource_first` Code requests were evaluated with the current
rev9 Code prompt and original two-wave batching:

| Model | Revision | Legal | Node-correct | Peak reserved VRAM |
|---|---|---:|---:|---:|
| Qwen2.5-Coder-1.5B-Instruct | `2e1fd397...` | 78/90 | 77/90 | 2.84 GiB |
| Qwen2.5-1.5B-Instruct | `989aa798...` | 86/90 | 86/90 | 2.84 GiB |
| Qwen2.5-3B-Instruct | `aa8e7253...` | 88/90 | 88/90 | 4.98 GiB |
| Qwen2.5-7B-Instruct | `a09a3545...` | 51/90 | 51/90 | 10.59 GiB |

These are diagnostics, not a selection experiment: the prompt was adaptively
tuned around the 1.5B Coder and only `resource_first` was used. They establish
that larger is not monotonically better and that a generic instruction-tuned
model can follow this synthetic contract better than a domain-specialized
checkpoint. The generic 1.5B renderer collapse above also shows why it should
not be adopted directly from the pooled `resource_first` result.

### Endpoint recommendation at this review

- **Lookup:** keep Qwen2.5-1.5B-Instruct.
- **Math:** ratify the switch to Qwen2.5-1.5B-Instruct.
- **Code:** leave unresolved until the request-scope experiment is complete;
  then compare Coder-1.5B, generic-1.5B, Coder-3B, and generic-3B under the
  identical crossed evaluation.

Choose the smallest model that satisfies semantic and protocol requirements in
the worst renderer/node stratum, not the model with the best pooled mean.

## Finding 6 — greedy NF4 generation depends on batch composition

The same 90 rev9 Code requests were regenerated under several schedules:

| Condition | Legal | Node-correct | Raw outputs changed from original |
|---|---:|---:|---:|
| Fresh original wave grouping, microbatch 16 | 78 | 77 | 0/90 |
| Second fresh original grouping, microbatch 16 | 78 | 77 | 0/90 |
| Microbatch 1 | 80 | 78 | 2/90 |
| Reversed request order within each wave, microbatch 16 | 79 | 78 | 1/90 |

The exact original grouping is bit-stable, but identical request bytes do not
define a unique raw completion independently of their batch companions and
order. The retained rev9 runs independently show the same issue: one identical
Math request under the same worker-visible fingerprint produced two equivalent
but byte-different artifacts when `--per-cell 15` and `--per-cell 30` changed
the batch population.

This falsifies the request-only determinism assumed by the completion cache.
The first batch in which a request is encountered can determine the cached
completion permanently; which siblings are already cached can itself change a
later miss batch. The observed differences happened to be small, but one of
the targeted Code probes changed semantic correctness.

### Required change

The simplest authoritative Stage-1 cache-population path is initially:

1. generate request-by-request (`microbatch = 1`);
2. repeat a sample in a fresh process and compare raw generations;
3. persist the resulting cache as an immutable, content-addressed artifact;
4. serve the fixed Stage-2 reference requests from that artifact; and
5. measure the real latency cost before deciding whether a canonical batching
   manifest is worth implementing.

For later live-subtask stages, either a validated batch-invariant backend or an
explicit canonical batching contract will be needed. Merely recording the
configured microbatch cap is insufficient because the dynamic cohort and order
also matter.

## Finding 7 — prompt and runtime provenance can disagree with execution

The runtime profile accepts any string as `prompts.d16_revision`, while the
real worker ignores that value and always renders the module-global current
prompt. A profile claiming `rev0` therefore validates while the worker executes
rev9. Request hashes protect individual cache rows from collision, but the
manifest and worker-visible provenance can describe behavior that did not run.

The runtime profile is also only shallow-copied. Mutating a nested caller-owned
worker setting after fingerprint construction can change generation behavior
while the stored fingerprint remains unchanged.

### Required change

- Use a revision-keyed prompt registry and reject unknown/mismatched revisions,
  or require equality with the sole current revision.
- Include actual per-endpoint system-prompt SHA-256 values in the
  worker-visible projection and trace manifest.
- Deep-copy and recursively freeze the runtime profile before building the
  pool or computing fingerprints.
- Add regression tests for stale prompt revision and caller mutation.

## Finding 8 — the current freeze surface is incomplete

Two contract items remain unresolved:

1. The canonical specification still names
   `Qwen2.5-Math-1.5B-Instruct`, while the runtime uses generic Instruct.
   Ratify the erratum, update the canonical specification/freeze record and
   stale worker documentation, and regenerate fingerprints and fixtures.
2. `SYSTEM_DIRECT` is part of D16 but remains at rev0 and untested because the
   direct baseline harness does not yet execute it. Either exercise and freeze
   it before the construction screen or split its status/revision from the
   three worker prompts explicitly.

The current prompt revision is correctly still marked `DRAFT`.

## Review of the mechanistic claims

The trail supports the narrower claims that demonstrations and prompt placement
materially affected these particular small models, and that
Math-Instruct's solve-and-box alignment was incompatible with the required
artifact contract in the tested regime.

The following final-cycle statements should be softened:

- “Math prompt content is irrelevant” becomes “none of three substantially
  different prompts overcame Math-Instruct on the 20 sampled requests.”
- “Examples > layout > prose” is a useful working hypothesis, not a cleanly
  identified ordering: several revisions changed examples, rules, contrasts,
  and placement together.
- “No overfit cliff” becomes “no large index-level collapse was observed on
  one 15-instance-per-cell holdout from the same generator under
  `resource_first`.”
- “No untried prompt lever remains” is false after the renderer crossing. The
  request-local scope and recency lever was not tested in the final layout;
  rev3's earlier “answer only the Task” instruction was removed before this
  failure surface was measured.

Zero observed failures also do not establish the Stage-1 `< 2%` rate by
themselves: D16 remains a construction diagnostic, and the registered
qualification gates must render the formal verdict.

## Recommended next D16 iteration

### A. Correct the measurement and runtime boundary first

Before evaluating rev10 candidates:

1. add node-level semantic evaluation with gold predecessors;
2. cross all three renderers;
3. use request-isolated authoritative cache population;
4. bind prompt hashes/revisions to execution; and
5. freeze runtime-profile ownership.

### B. Run a bounded request-scope experiment

Using fresh construction indices and otherwise identical prompts/models, compare:

1. **Current:** the frozen full `Problem` request contract.
2. **Task-last:** retain the full Problem, but place the local `Task` after
   Resource and Previous Results and end with an endpoint-neutral instruction
   such as:

   > Translate only the assigned Task. The Problem is background; do not
   > complete or combine other operations from it.

3. **Local diagnostic:** Task + authorized resource + previous results, without
   the global Problem.

The local diagnostic need not become the final design. It estimates the causal
cost of D10. The Task-last arm is the strongest candidate final contract: it
preserves the full Problem needed by the generic-subtask experiment while
applying the cycle's own recency lesson at the last instruction the model sees.

This changes the frozen §1.5 block order/final line and therefore requires an
explicit versioned specification erratum before qualification.

For `math_code`, a request-local statement that `step_1` has already been
validated as an in-range zero-based index is preferable to shrinking the data
band first.

### C. Repeat the model comparison only after scoping is fixed

Cross request-scope arm x renderer x node family for:

- Qwen2.5-Coder-1.5B-Instruct;
- Qwen2.5-1.5B-Instruct;
- Qwen2.5-Coder-3B-Instruct; and
- Qwen2.5-3B-Instruct.

Pre-register the selection rule and judge worst-stratum semantic correctness,
strict parse rate, truncation, and peak memory. Do not use the 7B result as a
reason to continue scaling; it already demonstrates non-monotonicity under
this interface.

### D. If syntax remains the dominant residue, test constrained decoding

The artifact languages are small deterministic grammars. Grammar-constrained
generation could enforce:

- one artifact envelope;
- the authorized `resource` alias;
- the function/operator whitelist; and
- argument shapes and order.

This would move the experiment away from fragile serialization and toward
model-plus-tool capability selection. It must be recorded as a versioned
endpoint/runtime change rather than applied as silent parser repair. A single
typed parser-feedback retry is a useful diagnostic alternative, but would turn
one logical endpoint call into a variable-cost internal workflow and needs its
own contract.

### E. Freeze, then proceed to the registered construction screen

After the bounded closure experiment:

1. select and freeze the three worker endpoints and prompt/request contract;
2. ratify the canonical specification errata;
3. exercise/freeze `SYSTEM_DIRECT` and freeze the B1 controls;
4. regenerate byte fixtures and execution fingerprints;
5. record the authoritative close-out command and commit; and only then
6. run the registered all-assignment payoff surface and Stage-1 construction
   gates.

Do not use the full cross-endpoint payoff matrix as another adaptive D16 prompt
tuning loop after freeze.

## RTX 4090 implications and scientific framing

There is no scientific requirement that every endpoint use the same parameter
count. The correct rule is to choose the smallest endpoint that is reliable
under the frozen contract and still leaves meaningful routing stakes.

Lookup and Math now use the identical generic 1.5B checkpoint, but
`WorkerPool` loads duplicate physical copies. Sharing model/tokenizer weights
by `(model_id, revision, quantization, device)` would recover substantial
headroom while preserving distinct logical endpoint prompts, tools, and
fingerprints. A shared 1.5B Lookup/Math model plus a distinct 3B Code model has
approximately the same total resident parameter count as three separately
loaded 1.5B models, before activation overhead; the real Stage-0C peak-memory
gate remains authoritative.

If all three logical endpoints ultimately share one 1.5B backbone, Stage 2 is
best described as **tool/prompt-gated endpoint routing**, not heterogeneous
frontier-model selection. That remains a valid and useful first orchestration
laboratory. Forcing superficial model heterogeneity before local-task behavior
is reliable would add confounding rather than bring the experiment meaningfully
closer to the Conductor paper. A distinct 3B Code endpoint is a natural later
relaxation once the clean routing baseline is established.

## Sign-off recommendation

**Request changes before D16 freeze.** Preserve rev9 and the `60_f`–`77_f`
trail as the prompt-development record. Implement the corrected evaluator and
runtime provenance/determinism fixes, then run one bounded crossed
request-scope/model closure cycle. If that produces stable intended-endpoint
behavior, freeze D16 and move review attention to the Stage-1 population,
controls, payoff surfaces, and calibration integration rather than reopening
unrestricted prompt iteration.
