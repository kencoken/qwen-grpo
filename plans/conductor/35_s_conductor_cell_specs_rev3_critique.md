Rev3 resolves the earlier design blockers in substance. I support the flag-and-stratify decision for public-number coincidences, and I would not add another cell. I would still make one small rev4 before Phase-1 sign-off because four executable contradictions remain.

## Phase-1 blockers

1. `math_atomic` T3 is invalid under the normative IR

The [`affine` schema](/Users/ken/34_f_conductor_cell_specs_rev3.md:124) requires:

```text
x = node
p, q = public literals
```

But T3 is `a × b + c`, where all three arguments are private operand references and there is no predecessor node.

The cleanest fix is a separate IR operation:

```text
mul_add:
  a, b, c = operand references
  semantics = a*b+c
```

It can reuse the same underlying arithmetic helper; the distinction is primarily for validation and provenance. Alternatively, define two explicitly permitted `affine` signatures, but do not simply allow arbitrary mixtures of node/literal/operand references.

Also require all operand references for one node to point to the same operand record, preserving the one-resource-per-step rule.

2. The factorial scheduler cannot currently guarantee its stated crossing

[`seed_material`](/Users/ken/34_f_conductor_cell_specs_rev3.md:520) includes `latent_index`, and `factor_perm` is derived from that per-instance seed. But the [scheduler](/Users/ken/34_f_conductor_cell_specs_rev3.md:554) requires one shared permutation for an entire factorial block.

Define:

```text
B = product of factor cardinalities
block_index = latent_index // B
offset = latent_index % B

block_seed = hash(
  project, generator version, profile, namespace,
  cell, "factor_perm", block_index
)

assignment = permutation(cartesian_product, block_seed)[offset]
```

Freeze factor order, level order, and partial-block behavior. Add a golden fixture with expected assignments from a known seed.

If marginal balance must also differ by at most one at every sequential prefix, an arbitrary joint permutation does not guarantee that; use a balanced-prefix ordering or weaken that claim.

3. The semantic-oracle contract omits two cells and partly contradicts itself

[The oracle table](/Users/ken/34_f_conductor_cell_specs_rev3.md:387) omits `math_atomic` and `code_atomic`. It also uses informal keys such as `lookup_branch` and says the mapping may condition on branch order, despite the intended oracle being order-invariant.

Use stable node IDs for all six cells:

```text
lookup_atomic: n1
math_atomic:   n1
code_atomic:   n1
lookup_math:   n1, n2
math_code:     n1, n2
fork_join:     n1=lookup, n2=code, n3=join
```

The full mapping is selected jointly on construction performance and frozen. `positions` alone permutes it into positional worker IDs. It should not condition on execution order. If any subtype conditioning is allowed, enumerate the exact allowed fields now.

Add deterministic tie-breaking for oracle and runner-up selection.

4. Collision tracking is terminal-only, so the “clean” workflow stratum is not actually clean

[`public_numeric_collision`](/Users/ken/34_f_conductor_cell_specs_rev3.md:612) only checks whether the final answer equals a public number. In composed tasks, an intermediate can be copied from a public number and still produce a non-collision final answer. Examples include:

- Lookup→Math: lookup value equals public `q`.
- Fork: Code count equals public `t`.
- Fork: lookup value equals public `q`.

A learned subtask can smuggle that intermediate, after which the downstream calculation produces the correct final answer. The current [answer-in-subtask telemetry](/Users/ken/34_f_conductor_cell_specs_rev3.md:495) also checks only the final gold and would miss this.

Replace the single flag with something like:

```text
public_numeric_values:
  parameter name → value

public_numeric_collision_nodes:
  node_id → matching public parameter names

public_numeric_collision:
  any node has a match

sink_public_numeric_collision:
  sink alone has a match
```

Derive public values from provenance-tagged semantic parameters, not by scanning rendered text; that avoids ambiguity from handle digits and typography.

For Stage 3, compare each subtask with its corresponding node value. For Stage 4, conservatively flag any reference-node value appearing in any authored subtask. Keep all of this as scorer/calibration-only metadata, invisible to the policy, workers, and normal executor.

The flag-not-reject choice is then sound. The private, no-node-collision stratum should be the clean headline, with its sample size reported.

## Important corrections before construction screening

- The no-op pseudo-worker is not a guaranteed floor. It returns zero, but `math_code` explicitly permits the correct intermediate index to be zero. Either make no-op an unconditional typed failure or retain zero and acknowledge/report its occasional correct workflows.
- Predeclared final namespace counts conflict with rev6’s sequential qualification rule. Predeclare the maximum, immutable latent-index order, batch sizes, and stopping rule; generate the maximum pool upfront or evaluate deterministic prefixes.
- “Target stratum for record cells” should mean keyed-record cells only. Define thirds explicitly, for example with `array_split`, and say the target entity is uniform within its scheduled stratum and the field is uniform. Remove the competing claim of globally uniform target position.
- Add two modular-error exclusions:
  - `(a + b + c) mod m != gold` — multiplication-to-addition error.
  - `(a*b - c) mod m != gold` — sign-flip error.
  
  Existing checks establish operand relevance but do not prevent these common wrong programs from receiving full reward.
- Define intervention behavior when the intervened upstream call fails. Record `override_applied`; conditional follow-through should require the intervened parent and every other required parent to have succeeded. Freeze denominators for full-sample and conditional metrics.
- Scope B2 to resource-requiring nodes; removing a nonexistent Resource block from a join step changes nothing.
- Freeze the public-feature guessing baseline: fit/select it using construction data only, then freeze it for qualification.
- Add `SYSTEM_DIRECT` to the separately reviewed prompt artifact for B1/B3/B4.

## Truncation and telemetry

[`E_TRUNCATED`](/Users/ken/34_f_conductor_cell_specs_rev3.md:291) currently means “open artifact tag without a close.” That does not prove backend truncation, while a genuine token-cap truncation may contain no artifact tag at all.

Record backend truncation independently from envelope syntax:

```text
generation_hit_token_cap: bool
finish_reason
envelope_error
```

Either rename the syntactic error to `E_UNCLOSED_ARTIFACT`, or retain `E_TRUNCATED` but do not use it alone for rev6’s truncation-rate gate.

Also freeze:

- Error precedence when multiple envelope errors apply.
- `artifact_valid` and `tool_executed` values for envelope failure, grammar failure, semantic tool rejection, success, and dependency blocking.

## Smaller contract cleanups

- The B5 zero-compatible case should distinguish no authorized resource from an incompatible authorized resource: Lookup/Code dereferencing the wrong kind should produce `E_RESOURCE_KIND`, not `E_NO_RESOURCE`.
- Define whether raw worker completions are intentionally shared across private/visible conditions. Worker requests are declared identical, while the cache section claims distinct keys.
- Specify UTF-8 for seed strings, the difficulty-profile digest length, and canonical integer-token boundaries for Echo telemetry.
- Make full instance validation normative: recompute IDs, profile hash, public prompt, gold, collision metadata, graph/resource shape, rejection invariants, and renderer identity.
- Name the independent evaluator used by random valid-AST fuzzing; the primitive reference functions alone do not evaluate arbitrary expression ASTs.
- Add tests for all 18 shortcut requests, the T3 IR fix, exact scheduler assignments, all six oracle mappings, intervention ineligibility, node-level collisions, no-op at true index zero, and backend truncation.

## Recommendation

I support D15—flagging rather than rejecting public-number coincidences—once it is node-level and analysis-only. After the four Phase-1 blockers above are patched, I would approve the specification. The remaining changes are local contract fixes; the experiment design itself is ready.