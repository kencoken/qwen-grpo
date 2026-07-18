This is very close. Rev2 resolves most previous blockers, and I would preserve the task design. I would still withhold Phase-1 sign-off until six remaining contract issues are corrected; none requires adding another task family.

## Remaining Phase-1 blockers

1. Reference IR still cannot reference private operand fields cleanly

The IR supports `lit`, `res`, and `node`, but [Math operands are represented as literal bindings](/Users/ken/conductor_cell_specs_rev2.md:638). That duplicates private values between the registry and graph, creating two possible sources of truth.

Add an explicit scalar reference, for example:

```json
{"operand": {"resource": "R-2P6", "name": "a"}}
```

Then reserve `lit` for public constants such as `p`, `q`, `k`, and `t`.

Also make the per-operation JSON schemas normative: required arguments, allowed reference types, extra-field rejection, unique nodes, acyclicity, valid references, topological positions, sink validity, and manifest/registry consistency.

Minor terminology correction: [`positions`](/Users/ken/conductor_cell_specs_rev2.md:138) is currently workflow-position → semantic-node, not semantic-node → workflow-position.

2. Renderer generation and categorical balancing contradict each other

The spec says every latent program is [fully crossed with all three renderers](/Users/ken/conductor_cell_specs_rev2.md:152), but later assigns renderer ID [round-robin over latent index](/Users/ken/conductor_cell_specs_rev2.md:492). Choose the fully crossed interpretation:

- Generate every latent program once.
- Render it in all three cosmetic forms.
- Keep those renderings in one cluster.
- Generate paired visible renderings only for the visible subset.
- Remove renderer from the latent-factor scheduler.

Naive round-robin also aliases equal-cardinality factors. For example, formula type, target-position third, and renderer all have three levels; assigning each as `index mod 3` creates perfect correlation despite balanced marginals.

Use a mixed-radix/full-factorial block scheduler with a seeded permutation. Because 100 is not divisible by three, replace “exactly balanced” with “counts differ by at most one,” or use compatible sample sizes. Test joint contingency tables, not just marginal counts.

3. Define the deployable fork oracle under branch reordering

Making branch order observable is now correct. But a single fixed worker vector cannot serve both orders:

```text
Lookup-first: [Lookup, Code, Math]
Code-first:   [Code, Lookup, Math]
```

The clean definition is a construction-selected semantic mapping:

```text
lookup_branch → selected endpoint
code_branch   → selected endpoint
join          → selected endpoint
```

The harness converts this to positional `worker_ids` through `positions`. Freeze this mapping on construction data.

Use semantic nodes consistently for:

- Stage-2 targets
- Runner-up substitutions
- Effective-routing-stakes gates
- Routing regret
- Best-fixed controls
- Cold-start calculations

This mapping may use observable branch identity/order, but not renderer ID, private values, qualification outcomes, or realized worker success.

4. The baseline section remains partly non-executable

Three corrections are needed in [§1.11](/Users/ken/conductor_cell_specs_rev2.md:407).

First, `GENERIC_SUBTASK` says “return a single integer,” while endpoint workers must emit a grammar-specific artifact. That could make the generic arm fail because of formatting conflict rather than instruction quality. Use something like:

> Complete the assigned step using the problem context, any provided resource, and any previous results.

Leave artifact formatting entirely to the fixed final instruction and endpoint system prompt.

Second, the fork’s 18 assignments define resource order and endpoint IDs, but not the contracted subtasks. Freeze both orientations:

- Lookup first:
  - Step 1 retrieves the requested value.
  - Step 2 performs the deduplicated count on its list, multiplies that count by `step_1`, and adds `q`.
- Code first:
  - Step 1 performs the deduplicated count.
  - Step 2 retrieves the requested record value, multiplies it by `step_1`, and adds `q`.

Without those exact strings, the `+15 versus best two-call` gate is implementation-dependent.

Third, B5 incorrectly says exactly one compatible resource always exists. Define:

- One compatible payload: bind it.
- Zero compatible payloads: bind none; in-context reading and literal Math expressions remain possible.
- More than one compatible payload: harness configuration error in v0.

Also freeze the exact multi-payload serialization rather than relying on the singular `Resource:` block.

5. Corruption and counterfactual tests should use the same mutation

The [intervention hash includes `kind`](/Users/ken/conductor_cell_specs_rev2.md:472), producing different replacements for corruption and counterfactual consistency. The intended experiment is cleaner if one mutated execution is scored twice:

- Against original gold for corruption/old-answer persistence.
- Against recomputed gold for counterfactual consistency.

Generate one replacement per `(latent_program_id, edge)` and remove scoring kind from the replacement seed. Retain kind only in result records.

Also restore rev6’s explicit `old-answer persistence ≤10%` metric. For conditional follow-through, require all non-intervened inputs to the affected downstream node to have succeeded—not merely the intervened upstream branch. This matters in fork/join.

6. The replacement nuisance audit remains underspecified

The original impossible classifier is gone, but [the new AUC gate](/Users/ken/conductor_cell_specs_rev2.md:350) can still fail for legitimate reasons. Within `math_atomic`, prompt length reveals T1/T2/T3, which legitimately predicts answer scale. Public `p`, `q`, `t`, or `i` can do the same.

The simplest robust approach is:

- Keep structural balance/invariance checks as gates.
- Restrict statistical leakage checks to randomized nuisance fields such as handles, entity names, field names, renderer, and split.
- Run within latent subtype.
- Treat prompt-length and shallow lexical models as descriptive diagnostics.

If retaining an AUC gate, define answer bins, classifier, cluster-aware train/test procedure, confidence interval, threshold, and conditioning variables.

## Important fixes before construction screening

These need not block the conceptual design, but should be settled before live payoff screening.

- B4 local capability should receive the same `Problem`, `Task`, `Resource`, and `Previous results` blocks as an endpoint worker; only the final answer protocol should differ.
- Rev6’s echo worker, no-op worker, and answer-in-subtask telemetry are still not defined, despite rev2 claiming all baseline arms are covered.
- Include the difficulty-profile fingerprint in generation identity. Otherwise changing an `(S)` profile can create different programs under the same `latent_program_id`.
- Freeze the PRNG algorithm/version, byte order for hash-to-integer conversion, canonical JSON rules for the profile hash, and preferably labelled substreams for semantic values, handles, and manifest order.
- Apply the 75% rejection cap by latent subtype, not just pooled cell. A pathological Code-select or modular subtype could otherwise be hidden by easier instances.
- Define exact train/dev/test counts or deterministic allocation before generating them.
- Store keyed records as ordered entry arrays, or include explicit order lists. JSON objects are not semantically ordered, while payload bytes and cache identity depend on record order.
- Finish the artifact-envelope parser contract: case sensitivity, attributes, nested/duplicate tags, `<value>` mixed with `<artifact>`, tag-like text in reasoning, trailing text, and truncation.
- The exact endpoint system prompts and demonstrations are not actually included—only future constant names. Either append them now or make them a separately reviewed 0A freeze artifact before construction screening.
- Rev2 says it supersedes v0.1 but still references metamorphic/provenance behavior “as v0.1.” Restate those tests so rev2 is genuinely self-contained.
- The errata section should say “proposed for approval,” not that the current review has already approved them.

## Public-number coincidences

Answers can still equal visible parameters such as `t`, `k`, `i`, `p`, or `q`. That becomes a potential answer-smuggling route in Stages 3–4.

I would not necessarily reject all such examples: observing this reward-hacking failure could be educational. Instead add a `public_numeric_collision` flag and pre-register:

- Collision frequency by cell/subtype
- Accuracy conditioned on collision versus non-collision
- Answer-in-subtask telemetry
- Non-collision performance as the cleaner Stage-3/4 result

If the goal is instead an uncontaminated headline instruction-learning result, add the rejection now because rejection-rule kinds freeze in Phase 1.

## Overall recommendation

Do not add another three-step cell. The existing fork is already the appropriate stress test, while the atomic cells mainly characterize endpoints. The real scientific decision remains whether Lookup→Math and Math→Code clear:

- The oracle-versus-one-call gap
- Effective routing stakes
- Counterfactual follow-through
- Cold-start reward variation

After the six blockers above are fixed, I would approve the Phase-1 freeze. The remaining work is contract closure, not task redesign.