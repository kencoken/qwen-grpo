# PR Review: Conductor Stage 0A — Fifth Pass

**Pull request:** [kencoken/qwen-grpo#2](https://github.com/kencoken/qwen-grpo/pull/2)

**Base:** `conductor@25c22ac4a4d7ef66d7ccd04fc178047279b45f4d`

**Head:** `conductor_stage_0a@fa63de6712c3f533d5ac1320a8ef07282d5513f4`

**Scope:** 34 changed files, 9,750 additions, 6 deletions, 6 commits

**Review status:** Changes requested before declaring Stage 0A complete

## Executive summary

The serious construction-versus-qualification regression from the previous
review is fixed. Every argmax now rejects non-construction surfaces, the
construction choices are captured in a separate `FrozenSelections` artifact,
and qualification evaluates those candidates without an argmax being reachable.
The B3/B5 instance-registry repair is also sound. Mixed-split surfaces, lossy
payoff deserialization, duplicate candidate entries, and mutable nested payoff
data are handled correctly.

The remaining issues are concentrated in the newly added persistence and
provenance layer. The current code separates selection from evaluation, but it
does not yet establish that:

1. construction selection used the registered population and one execution
   environment;
2. assignment and control arms share that execution provenance;
3. a revived `FrozenSelections` artifact really represents the labelled
   construction choices; or
4. persisted intervention reports are immutable and internally valid.

The log accurately records the canonical population/execution manifest as a
construction-screen blocker. That is a valid way to defer Stage-0B fields, but
the executable API is currently in an unsafe middle state: an empty or absent
manifest is accepted by methods described as Stage-1 gates, while the partial
`PopulationManifest` implementation claims stronger guarantees than it
actually establishes.

## Findings

### [P1] Make provenance a precondition of construction freeze and gate evaluation

**Locations:**

- [`tasks/conductor/oracle.py:518-548`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/oracle.py#L518-L548)
- [`tasks/conductor/oracle.py:743-767`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/oracle.py#L743-L767)
- [`tasks/conductor/oracle.py:777-834`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/oracle.py#L777-L834)
- [`tasks/conductor/oracle.py:372-445`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/oracle.py#L372-L445)

Every surface validator still accepts `manifest=None`. `freeze_selections()`
checks only that the assignment surface is in the construction namespace; it
does not require a population manifest or call
`require_execution_provenance()`. That method is not called by any production
path in this PR.

`CalibrationBundle` compares cell, namespace, clusters, and observation IDs,
but not the manifests attached to its arms. Assignment and one-call surfaces
with the same observation IDs but different generator versions, difficulty
profiles, runtime fingerprints, endpoint fingerprints, and prompt revisions
therefore bundle successfully. Both manifests can individually pass
`require_execution_provenance()`.

The evaluation boundary then checks only `FrozenSelections.cell_id`. Choices
from experiment A can be applied to same-cell qualification data from
experiment B. Surface JSON persistence also omits the manifest entirely; a
manifest-bound surface round-trips as manifestless and can still freeze or
evaluate normally.

This provenance is needed before **construction freeze**, not merely before a
qualification result is reported. Construction worker outcomes determine the
deployable assignment, node runner-ups, best-fixed assignment, and one-/two-call
controls. An inconsistent construction runtime becomes permanently embedded in
those choices.

Recommended resolution:

1. Distinguish a structural/descriptive bundle from an experiment-qualified
   bundle.
2. Require a canonical population manifest and complete execution provenance
   before `freeze_selections()`.
3. Compare the shared provenance fields across every assignment/control arm,
   while explicitly recording intentional request-family differences.
4. Persist a construction population/surface fingerprint in
   `FrozenSelections` and require compatible experiment identity at evaluation.
5. Make the future sequential qualification-gate object enforce the registered
   deterministic prefix, look schedule, paired CI, and alpha-spending state.

If this is deliberately deferred, keep the current methods explicitly
descriptive and provisional rather than describing their bare float return
values as Stage-1 gate results.

### [P1] `PopulationManifest` is self-declared, mutable, and insufficiently validated

**Locations:**

- [`tasks/conductor/oracle.py:157-192`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/oracle.py#L157-L192)
- [`tasks/conductor/oracle.py:308-337`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/oracle.py#L308-L337)
- [`conductor_cell_specs.md:649-652`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/conductor_cell_specs.md#L649-L652)
- [`conductor_cell_specs.md:779-814`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/conductor_cell_specs.md#L779-L814)

`PopulationManifest` has no `__post_init__`, validating constructor, persistence
form, or defensive freezing. `_check_manifest()` verifies only that the surface
matches the manifest's self-declared cell, namespace, clusters, and observation
IDs. It does not validate or use the declared generator or difficulty-profile
versions.

Confirmed accepted manifests include:

- one fabricated `deadbeef` construction cluster;
- one `resource_first` observation rather than the registered renderer support;
- bogus generator and difficulty-profile versions; and
- a qualification population containing only index 499 rather than a legal
  deterministic 100/300/500 prefix.

The class therefore does not yet establish namespace caps, exact prefix/look
sizes, three-renderer crossing, scheduled visible support, or deterministic ID
derivation. The unit test builds the manifest back from the surface being
checked, which is circular rather than a registration boundary.

`require_execution_provenance()` checks only whether fields are `None`, so the
following passes:

```text
runtime_profile_fingerprint = ""
endpoint_fingerprints       = {}
prompt_revision             = ""
```

The nested `observations` and `endpoint_fingerprints` mappings remain mutable.
Mutating them after surface validation changes the surface's claimed provenance,
even though `ValidatedSurface.__deepcopy__()` returns the original object on the
claim that every nested collection is immutable.

Either construct the manifest only through a canonical, profile-aware builder,
or defer/remove its authoritative claims until that builder exists. In either
case, deep-freeze all nested mappings and require non-empty, complete execution
fingerprints when provenance is declared bound.

### [P1] Validate the semantics and source of `FrozenSelections`

**Locations:**

- [`tasks/conductor/oracle.py:647-720`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/oracle.py#L647-L720)
- [`tasks/conductor/oracle.py:798-806`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/oracle.py#L798-L806)
- [`conductor_cell_specs.md:435-443`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/conductor_cell_specs.md#L435-L443)

The persisted artifact validates candidate shapes but not the scientific meaning
of its fields. This exact record is accepted for `lookup_math`:

```text
deployable             = (2, 2)
best_fixed_assignment  = (0, 1)
node_runner_ups         = {}
random_accuracy         = NaN
best_one_call           = 1
```

`best_fixed_accuracy()` will then evaluate the heterogeneous `(0, 1)` routing
assignment under the scientifically distinct **best-fixed** label. Other
accepted cases include runner-ups equal to the deployable, runner-ups changing
multiple nodes, missing runner-up nodes, and a two-call selection on a non-fork
cell.

At minimum, enforce:

- exact runner-up coverage for every cell node;
- exactly one changed endpoint at the named node;
- a constant best-fixed assignment;
- `best_two_call is None` outside the defined two-call cells; and
- finite numeric probabilities in `[0,1]` for any stored accuracy.

Those local checks cannot prove that a candidate was actually the argmax or
runner-up. Revival should therefore also verify the selections against the
source construction bundle or a content-addressed source artifact.

`random_accuracy` should not normally be frozen at all. The random control is
the exact uniform mean over the payoff surface being evaluated. The current
value is computed on construction data and can be mistaken for the qualification
control. Remove it, expose evaluation-surface random accuracy on the bundle, or
rename it explicitly to `construction_random_accuracy` as a diagnostic.

`FrozenSelections.from_json()` also needs total shape validation before
conversion. At present malformed values can leak raw `TypeError`,
`AttributeError`, or `IndexError`, and an overlong `best_two_call` list is
silently truncated.

### [P2] Make `InterventionReport` recursively immutable and validate its persisted form

**Locations:**

- [`tasks/conductor/estimands.py:140-235`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/estimands.py#L140-L235)
- [`tasks/conductor/estimands.py:336-358`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/estimands.py#L336-L358)

`__post_init__()` wraps only the outer `cluster_successes` mapping. The inner
dictionaries remain mutable:

```python
report.cluster_successes[cluster]["base"] = 999
```

This succeeds even though `__deepcopy__()` returns `self` on the assumption that
the object is immutable.

`from_json()` validates the top-level key set and edge shape, but accepts:

- string-valued counts;
- negative counts;
- rates and accuracies outside `[0,1]`;
- malformed per-cluster mappings; and
- headline values inconsistent with the purported sufficient statistics.

The new per-cluster statistics are sufficient for some eligible-set accuracy
recomputations, but not for every quantity the artifact claims to support. They
omit per-cluster total/ineligible counts, followed counts and followed successes,
and entirely omit latent clusters with zero eligible observations. Eligibility
and follow-through behaviour therefore cannot be reproduced under a bootstrap
over the original latent-program population.

Recommended resolution: either persist the raw paired `EdgeOutcome` rows and
derive reports from them, or recursively freeze and validate complete
per-cluster sufficient statistics, recomputing all redundant headline fields
at load time.

### [P2] Require actual directed intervention edges and non-null gold values

**Locations:**

- [`tasks/conductor/estimands.py:238-265`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/estimands.py#L238-L265)
- [`conductor_cell_specs.md:464-487`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/conductor_cell_specs.md#L464-L487)

The row validator requires both edge endpoints to be node IDs in the cell, but
does not require the ordered pair to be a real dependency edge. It accepts
reversed edges such as `("n2", "n1")`, self-edges, and sibling edges in
`fork_join`.

It also applies `_require_optional_int()` to `gold_answer` and
`counterfactual_gold`, although those fields are required integers. A probe with
the reversed edge and both gold values set to `None` produced an ordinary report
with zero base and counterfactual accuracy.

Introduce the fixed directed intervention-edge set:

```text
lookup_math: n1 -> n2
math_code:   n1 -> n2
fork_join:   n1 -> n3, n2 -> n3
atomic:      no edges
```

Require membership in that set, exact integer gold/counterfactual-gold values,
and optional integers only for execution terminals that can genuinely be absent.

### [P2] Finish totalizing the modified persistence and registry boundaries

**Locations:**

- [`tasks/conductor/oracle.py:390-445`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/oracle.py#L390-L445)
- [`tasks/conductor/oracle.py:700-720`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/oracle.py#L700-L720)
- [`tasks/conductor/resources.py:17-36`](https://github.com/kencoken/qwen-grpo/blob/fa63de6712c3f533d5ac1320a8ef07282d5513f4/tasks/conductor/resources.py#L17-L36)

The ordinary cases fixed in this commit are correct, but a few malformed JSON
shapes still escape through raw Python exceptions:

- an unhashable `ValidatedSurface` `cell_id` leaks `TypeError`;
- non-iterable or wrongly shaped frozen selections leak
  `TypeError`/`AttributeError`/`IndexError`; and
- a `null` or incomplete resource object in `InstanceRegistry` leaks
  `AttributeError` or `KeyError` from `resource_from_json()`.

Validate shapes before membership/index/conversion operations and translate
failures into the documented `PayoffSurfaceError` or `InfrastructureError` with
field context.

## Confirmed improvements

The following changes were independently reviewed and found sound:

- Every selection argmax rejects non-construction surfaces.
- Qualification evaluates the construction-frozen candidate without
  reselection.
- Mixed namespaces within a payoff surface are rejected.
- B3 and B5 derive both disclosed payloads and host-side bindings from the
  instance's own registry.
- Payoff-surface correctness remains exactly binary and observation-paired.
- Persisted correctness values are no longer coerced, and duplicate candidate
  entries are rejected.
- The nested payoff data owned by `ValidatedSurface` is defensively frozen.
- Persisted estimand rows are tied to their encoded cluster/visibility identity
  and exact primitive types on their ordinary path.
- The T1 analytic sampler and request bytes remain behaviour-preserving.

## Scope judgment

It is reasonable that real runtime, endpoint, and D16 prompt fingerprints do not
exist until Stage 0B. The earlier review explicitly allowed this work to be
deferred if the bundle was described honestly and the dependency recorded as a
construction/qualification blocker; `conductor_log.md` now does that.

There are therefore two acceptable approaches:

1. **Implement the authoritative path now:** canonical immutable population and
   execution manifests, cross-arm checks, content-addressed selection artifacts,
   and a separate qualification-look report.
2. **Keep Stage 0A minimal:** retain only explicitly structural/descriptive
   helpers, mark the partial manifest as non-authoritative or defer it entirely,
   and ensure no method currently presents a bare provenance-free float as a
   valid Stage-1 gate.

The `FrozenSelections`, intervention-row, and `InterventionReport` semantic and
immutability problems are Stage-0A persistence issues and should be fixed under
either approach.

## Verification

Independent verification was performed against exact head
`fa63de6712c3f533d5ac1320a8ef07282d5513f4` on the Linux environment:

```text
pytest -q -W error
380 passed in 1.65s

python -m tasks.conductor.agreement --cases 10000
16665/16665 node executions agree over exactly 10000 latent programs
```

The byte-stability generator wrote 58 request hashes and produced no diff. The
worktree remained clean. Targeted adversarial probes reproduced every finding
above.

GitHub reports the PR as cleanly mergeable into `conductor`. There are no GitHub
Actions workflow runs or commit-status checks for this head.

## Recommendation

Retain the construction-only argmax split, own-instance B3/B5 registry path,
payoff-surface hardening, and identity-validation work.

Before Stage 0A sign-off:

1. settle the authoritative-versus-deferred provenance API boundary;
2. make `FrozenSelections` source-bound and semantically valid;
3. make `InterventionReport` recursively immutable and validating;
4. validate actual directed intervention edges and required gold values; and
5. add adversarial tests for the exact accepted probes described above.

