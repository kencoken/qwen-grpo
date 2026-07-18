I would not freeze Phase 1 yet, but I would keep the six-cell design. The worked arithmetic is correct, the overall framing matches rev6, and most remaining problems are specification ambiguities—not a need for more task complexity.

The next revision should tighten the executable contract before generator code begins.

## Required before Phase 1 sign-off

1. Freeze exactly what the Conductor and workers observe

The spec defines payload rendering, but not the complete request assembled for a worker:

- Original public problem, if included
- Assigned subtask
- Authorized payload
- Predecessor names and/or values
- Endpoint system instructions
- Ordering and delimiters

This is scientifically consequential. It determines whether workers can solve the whole task, whether they can inline predecessor values, what interventions measure, and what belongs in the cache key.

The Conductor-side observation also needs definition. In particular, [fork branch order is randomized](/Users/ken/conductor_cell_specs.md:655), but every public renderer describes Lookup first and Code second. Unless the numbered reference subtasks are shown to the routing policy, a Code-first execution order is unobservable, producing irreducible label noise.

I would specify:

- Exactly what the Stage-2 policy sees
- Exactly what each worker sees
- How workflow positions map to semantic nodes
- A canonical, byte-stable worker request template

2. Repair the resource and reference-program schemas

There are two incompatible meanings of `integer_record`:

- [The global definition](/Users/ken/conductor_cell_specs.md:43) is `entity → field → int`.
- Hidden-Math examples require a flat namespace such as `a → 83719`.

For minimal complexity, retain two top-level resource kinds but make `integer_record` a tagged union:

```text
layout = keyed
payload = entity → field → int

layout = operands
payload = identifier → int
```

Then:

- Lookup dereferencing accepts only `keyed`.
- Math identifiers bind only against `operands`.
- A Math endpoint may still read a keyed record in context and emit a literal, preserving D1.
- N4’s entity/field balancing applies only to keyed records.
- Wrong layout dereferences yield a typed `E_RESOURCE_KIND`, never an exception.

The reference IR also needs explicit argument bindings. `deps=["n1"]` does not say which operand receives `n1`. Use typed literal/resource/node references and derive dependency edges from node references.

There is also a concrete operator mismatch: [`math_code` uses undefined `seq_select_by_step`](/Users/ken/conductor_cell_specs.md:623), while `prim_seq_select` means deduplicate, rotate and select. Add a separate `seq_at(xs, i)` primitive.

3. Add stable identity, split and visibility fields

The stored schema needs at least:

```text
latent_program_id
render_instance_id
split_id
visibility_condition
difficulty_profile_version
```

All renderings and private/visible variants of one latent program must remain in the same statistical cluster and split. “100 programs” should explicitly mean 100 latent clusters—not 100 rendered prompts.

Rev6 requires a paired visible qualification slice, but the cell spec currently defines only the private condition. Specify how visible payloads are appended, their order, and how visibility enters cache identity.

Use disjoint seed namespaces for construction, qualification, train and dev. Also define a stable labelled hash for interventions; `seed ⊕ edge_id` is not executable when `edge_id` is textual and must never rely on Python’s randomized `hash()`.

4. Make every baseline executable and deployable

[The baseline section](/Users/ken/conductor_cell_specs.md:246) is currently too informal for the gates it supports.

I would define:

- Public-only direct baseline: the 3B base Conductor returns a canonical integer without workers or payloads.
- Endpoint-without-resource: retain separately as a tool-rejection diagnostic.
- Visible direct baseline: the 3B receives the complete visible problem and all payloads. This diagnoses self-solving capability but, without `SELF`, still does not test learned delegation.
- Local-node baseline: downstream nodes also receive the required predecessor values.
- One-call endpoint baseline: all payloads appear in context; host binding is type-directed where exactly one compatible resource exists. Unsupported resources remain readable for mental/inlined reasoning.
- “Best one-call” means endpoint selected on construction data and frozen for qualification. Per-example hindsight maximum is diagnostic only.
- Generic subtask: freeze its exact wording now, because rev6 contains a reference-versus-generic Stage-3 gate.

The fork’s [“best two-call shortcut”](/Users/ken/conductor_cell_specs.md:728) is not defined. Either:

- Define the complete family of allowed two-call DAG contractions and enumerate them; or
- Define one named compressed two-call topology and stop calling it “best.”

Also report prompt tokens and tool access. If hierarchy wins because it partitions a long union context into shorter local contexts, that is still a valid systems result—but it should be identified as such.

5. Resolve intervention and caching semantics

[“Prompts unchanged”](/Users/ken/conductor_cell_specs.md:225) is ambiguous if predecessor values appear in worker context.

For v0, I recommend a clearly named mediator/wire intervention:

1. Replace the upstream value through a calibration-only override.
2. Replace it in both downstream context and tool binding.
3. Rerun the downstream worker.
4. Recompute counterfactual gold outside the executor.
5. Use a distinct cache identity.

Either cache raw model completions and re-execute tools against current bindings, or include every resource and predecessor binding in the key. Never cache an already executed `WorkerResult` without those bindings.

Report both:

- Full-workflow intervention accuracy
- Conditional follow-through among examples where the upstream step originally succeeded

Resource-level counterfactuals—mutating the original private payload and rerunning everything—would be stronger, but can remain deferred if the current test is accurately described as a mediator intervention.

6. Remove answer-irrelevant complexity from Code tasks

The [count pipeline’s rotation](/Users/ken/conductor_cell_specs.md:455) can never affect `count_gt`. A worker can ignore it and receive full reward. That is especially harmful for Stage 3, where incomplete instructions could look successful.

Use:

```text
count_gt(stable_unique(xs), t)
```

for count, and retain rotation only for select.

Add primitive-ablation rejection rules:

- Count: counting the original list must differ from counting the deduplicated list.
- Select: omitting deduplication must change the answer.
- Select: omitting rotation must change the answer.
- Modular tasks: ensure each advertised operand affects the result under plausible omission/replacement ablations.

This gives genuine complexity without adding more operators.

7. Replace the impossible nuisance-classifier gate

[The current audit](/Users/ken/conductor_cell_specs.md:263) says renderer, domain, prompt length and resource count must not predict cell. That cannot pass honestly:

- Resource count distinguishes the two composite cells.
- Operation vocabulary intentionally identifies endpoint demand.
- “Domain” is not defined.
- Prompt length naturally varies with semantic workload.

Rev6 explicitly permits transparent template routing at this stage. Therefore cell identity being predictable is not a defect.

Instead:

- Enforce exact balance for renderer IDs, handle characters, manifest ordering and split.
- Audit nuisance predictiveness conditional on topology/semantic operation.
- Report shallow lexical-router performance descriptively.
- Reserve a stronger anti-template gate for the deferred semantic renderer.

I would not add a second resource to Lookup→Math merely to balance resource count; that adds complexity to solve the wrong problem.

8. Specify distributions, not only ranges

The implementer still has to invent distributions for `N`, `F`, `L`, `p`, `q`, `k`, `t`, target position and so on.

Before generation, specify:

- Proposal distribution for every parameter
- Exact categorical balance for formula type, Code shape, sign, renderer and fork order
- Target-position strata
- Post-rejection distribution checks
- Rejection counts by rule
- A maximum acceptable rejection rate
- The frozen Phase-2 difficulty-profile hash

No individual instance should ever be retained or discarded based on worker performance. Only an entire difficulty profile or cell should pass or fail construction screening.

Qualification results should also be reported by latent subtype—T1/T2/T3, count/select, plus/minus, renderer—not only pooled by cell.

9. Complete failure and parser contracts

A rejected call cannot have `WorkerResult.value: Integer`. Define something like:

```text
status = success | typed_failure | dependency_blocked
value = int | null
rejection_code = code | null
```

Freeze propagation:

- A failed step blocks its descendants.
- Independent fork branches continue.
- A join is blocked if either branch fails.
- Typed failures yield 0.5.
- Only infrastructure failures abort.

Add uniform limits for all grammars:

- Artifact bytes
- AST nodes/depth
- Integer-literal digits
- Intermediate/result magnitude

Also define `%` with zero or negative moduli, negative-literal tokenization, associativity, and cases such as `a--5`. These must produce typed errors, not unexpected exceptions.

## Specific corrections

- The Lookup fixture labelled “minimum size” uses `N=4`, although the range begins at 3.
- Fork counterfactual generation requires `U ≥ 3`; at `U=2`, `[1,U−1] \ {n2}` is empty.
- Add a Code-first fork golden fixture and an explicit semantic-node-to-position map.
- The fork statement “Stage-2 use tests…” should be conditional because rev6 says fork admission to the training mixture is deferred.
- “Public-prompt-only accuracy ≈0” is too strong. Modular and count outputs have small support, so report majority and public-feature guessing baselines. Structural provenance—not nonzero accuracy—is the leakage test.
- D5’s claim that echo/coincidence can never score is false for Lookup and Code-select, whose correct answers necessarily occur in their payloads. Narrow the claim to the specific prohibited coincidences.
- Fully enumerate exact renderer strings. Phrases such as “select shape replaces…” and “or add” leave supposedly frozen templates partly implementation-defined.
- Rev6 shows `lookup(Q31, ...)`, while the cell spec uses `lookup(resource, ...)` and `R-7K2`. I prefer the cell-spec form, but the authoritative plan and demos must agree.
- Rev6 is named `rev6` but calls itself “v5”; give the signed-off contract one unambiguous version.
- Expand the acceptance suite to cover wrong resource kinds, every rejection code, future/unavailable `step_k`, failure propagation, both fork orders, cache isolation, split isolation and random valid ASTs. The 10k agreement run should be stratified by operator and cell.

## What I would leave unchanged

I would retain:

- The six-cell scope
- Integer-only outputs
- D1’s in-context plus host-side payload delivery
- Reference-free execution and separate scoring
- Empirically selected deployable oracles
- Pairwise-distinct lookup and selection values
- Cosmetic-renderer clustering
- Fork/join as diagnostic-only
- Construction screening followed by fresh qualification

I would also resist adding another task family or more steps now. If Lookup→Math or Math→Code fails the one-call advantage gate, first tune only the marked difficulty ranges—record size, list length and operand scale—and test on fresh data. Add semantic complexity only after the current harness demonstrates clean routing dynamics.

With the required contract fixes above, this becomes a strong implementation-ready specification for exactly the modest claim in rev6: learning fixed model-plus-tool endpoint selection in a transparent typed environment.