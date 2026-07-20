# PR Review: Conductor Stage 0A — Sixth Pass

**Pull request:** [kencoken/qwen-grpo#2](https://github.com/kencoken/qwen-grpo/pull/2)

**Base:** `conductor@25c22ac4a4d7ef66d7ccd04fc178047279b45f4d`

**Head:** `conductor_stage_0a@ef2368218f7c216c738b17c22267d95ea43df028`

**Scope:** 35 changed files, 10,561 additions, 6 deletions, 7 commits

**Review status:** Changes requested before declaring Stage 0A complete

## Executive summary

The main scope decision is now sound. Removing the partial
`PopulationManifest` is cleaner than retaining an object whose name implied
guarantees it could not establish. `CalibrationBundle` now describes its values
as structural/descriptive, the difference methods are named accordingly, and
`gate_report()` fails closed until the Stage-0B/1A authoritative provenance
layer exists.

The frozen-selection semantics, random-control interpretation, directed-edge
typing, sufficient statistics, nested immutability on the ordinary report path,
and malformed-resource handling are all materially improved.

The remaining blocker-class issues are concentrated in intervention reporting:

1. one report can pool rows from different cells or splits;
2. the causal targets are not required to be constant per latent or to change
   the sink; and
3. the persisted report validator recomputes only three of many redundant
   fields, so a hand-edited gate result can still load successfully.

There are also residual lower-priority problems around optional
frozen-selection verification, JSON totality, and the intervention constructor
not enforcing the centralized edge table.

## Findings

### [P1] Require one cell and namespace per intervention report

**Locations:**

- [`tasks/conductor/estimands.py:315-348`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/estimands.py#L315-L348)
- [`tasks/conductor/estimands.py:351-365`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/estimands.py#L351-L365)

`_validate_edge_rows()` parses each row's latent identity and checks its edge
against that row's own cell. `intervention_report()` then checks only that the
edge tuple is shared across rows. It does not require a shared cell or namespace.

Because `lookup_math` and `math_code` both define `n1 -> n2`, this ordinary
report was accepted:

```text
lookup_math:construction:* / n1 -> n2
math_code:construction:*   / n1 -> n2
```

A second probe mixed `lookup_math:construction` and
`lookup_math:qualification` and was also accepted.

Stage-1 intervention gates are per cell and edge. Pooling either of these
populations silently changes the admission statistic while producing an
apparently well-formed report.

Recommended resolution:

1. Have row validation return each parsed `(cell_id, namespace)` identity.
2. Require exactly one `(cell_id, namespace, edge)` across the report.
3. Persist `cell_id` and `namespace` explicitly in `InterventionReport`.
4. On deserialization, parse the per-cluster IDs and require them to agree with
   those header fields.

Exact prefix/look registration remains correctly deferred to Stage 1A; this
finding concerns only the structural no-mixing invariant that Stage 0A can
enforce now.

### [P1] Enforce the causal-target invariants across renderings

**Locations:**

- [`tasks/conductor/estimands.py:315-348`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/estimands.py#L315-L348)
- [`conductor_cell_specs.md:464-487`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/conductor_cell_specs.md#L464-L487)

The new validator correctly requires exact integer original and counterfactual
golds. It does not yet enforce their semantic relationships.

The specification draws one deterministic replacement per
`(latent_program_id, edge)`, and each latent is rendered several ways.
Consequently every rendering in one cluster must carry the same:

- original `gold_answer`; and
- `counterfactual_gold` produced by that replacement.

The replacement rules are also specified to provably change the sink, so these
two values must differ.

Confirmed accepted cases:

```text
same latent, rendering 1: gold=10, counterfactual=20
same latent, rendering 2: gold=11, counterfactual=21

unchanged intervention: gold=10, counterfactual=10
```

The unchanged-target case reported:

```text
old_answer_persistence      = 1.0
counterfactual_consistency  = 1.0
```

That makes the causal diagnostic uninterpretable: the mutated execution is
simultaneously counted as preserving the old answer and following the
counterfactual.

Group rows by latent cluster and require cluster-constant targets plus
`counterfactual_gold != gold_answer`. Later, the authoritative calibration
layer should additionally bind those targets to the generated intervention
record.

The row contract also accepts:

```text
downstream_path_succeeded = true
mutated_terminal          = null
```

This row enters the conditioned follow-through denominator as a failed answer,
although the flag claims that the complete downstream path executed
successfully. Require path success and terminal availability to agree.

### [P1] Derive or validate every persisted `InterventionReport` field

**Locations:**

- [`tasks/conductor/estimands.py:165-312`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/estimands.py#L165-L312)
- [`tasks/conductor/estimands.py:419-468`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/estimands.py#L419-L468)
- [`conductor_log.md:177-180`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/conductor_log.md#L177-L180)

`InterventionReport._validate()` now checks primitive ranges and recomputes:

- `base_accuracy`;
- `corruption_accuracy`; and
- `counterfactual_consistency`.

It does not reconcile most of the remaining redundant state. Starting from a
valid serialized report, the following hand edits were accepted together:

```text
edge                       = reversed n2 -> n1
eligibility_rate           = 0.123
follow_through_rate         = 0.123
old_answer_persistence      = 0.123
corruption_drop             = 0.123
n_clusters                  = 999
cluster_weighted            = {"bogus": NaN}
cluster_observation_counts  = {"bogus": 999}
```

This directly contradicts the log's statement that the report “recomputes its
redundant headline fields at load.” It also means persisted values used for
reporting or later gate decisions remain forgeable while passing the declared
validator.

The most robust resolution is to make identity plus per-cluster sufficient
statistics the persisted source of truth and derive the remainder. If redundant
headline fields remain serialized for readability, compare every one against
its derived value:

- `n_total`, `n_eligible`, and `intervention_ineligible`;
- eligibility rate;
- population and eligible-cluster counts;
- base, corruption, and counterfactual accuracies;
- corruption drop and old-answer persistence;
- follow-through and its rate;
- exact `cluster_weighted` keys and values; and
- `cluster_observation_counts`.

The validator should also parse cluster IDs, establish the single
cell/namespace population, and validate edge direction against that cell.

`n_clusters` is now ambiguous: it is computed as the number of clusters with at
least one eligible observation, while `cluster_successes` correctly includes
zero-eligible clusters from the original bootstrap population. Prefer explicit
`n_population_clusters` and `n_eligible_clusters` fields.

### [P2] Make frozen-selection source verification part of the consuming boundary

**Locations:**

- [`tasks/conductor/oracle.py:629-719`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/oracle.py#L629-L719)
- [`tasks/conductor/oracle.py:847-863`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/oracle.py#L847-L863)
- [`tasks/conductor/oracle.py:892-922`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/oracle.py#L892-L922)

`verify_against()` correctly checks the content digest and re-derives every
selection when it is called. The evaluation methods do not require that call.
`_check_frozen()` checks only the artifact type and cell.

A locally valid artifact with:

```text
source_fingerprint = "cb-unverified-other"
```

was accepted and evaluated against a qualification bundle without source
verification.

This is not currently an authoritative-gate bypass because `gate_report()`
correctly raises. It does mean, however, that the persisted artifact is not
mechanically source-bound as its documentation suggests. A side-effect-free
method that a caller may or may not invoke provides no evidence to the consuming
operation that verification occurred.

Possible resolutions:

- require the construction bundle in `FrozenSelections.from_json()` and verify
  before returning;
- return a distinct `VerifiedFrozenSelections` type that evaluation accepts; or
- require source verification within every later operational loader/gate.

The stored value is also a digest of canonical **surface-result content**, not
experiment identity. Two independent executions producing identical payoff
tables intentionally receive the same digest. Rename it to
`source_surface_digest`, add a digest schema/domain version, and later pair it
with the deferred population and execution-manifest digests.

### [P2] Complete total validation at the modified JSON boundaries

**Locations:**

- [`tasks/conductor/oracle.py:376-433`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/oracle.py#L376-L433)
- [`tasks/conductor/oracle.py:740-787`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/oracle.py#L740-L787)
- [`tasks/conductor/estimands.py:214-312`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/estimands.py#L214-L312)

Several malformed persisted values still escape through raw Python exceptions:

```text
ValidatedSurface.from_json(... cell_id=[])
    -> TypeError: unhashable type: 'list'

FrozenSelections.from_json(... cell_id=[])
    -> TypeError: unhashable type: 'list'

InterventionReport.from_json(... cluster_weighted=null)
    -> TypeError

InterventionReport.from_json(... cluster_successes=null)
    -> AttributeError
```

The surface test added in this commit checks direct `ValidatedSurface`
construction, but `from_json()` performs its own dictionary-membership test
before reaching that constructor. The frozen-selection constructor has the same
ordering issue.

The report also accepts list-valued `cluster_weighted`,
`cluster_observation_counts`, or `corruption_drop` values. Such values remain
mutable even though `InterventionReport.__deepcopy__()` returns `self` on the
claim that the report is recursively immutable.

Validate all shapes and scalar types before membership checks or defensive
freezing, and consistently translate failures into `PayoffSurfaceError` or
`InfrastructureError` with field context.

### [P2] Enforce the legal directed edge in `draw_intervention()`

**Locations:**

- [`tasks/conductor/program.py:493-546`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/program.py#L493-L546)
- [`tasks/conductor/types.py:369-379`](https://github.com/kencoken/qwen-grpo/blob/ef2368218f7c216c738b17c22267d95ea43df028/tasks/conductor/types.py#L369-L379)

Moving the edge table to `types.py` gives generation and analysis one source of
truth, but `draw_intervention()` does not actually consult it. It chooses
replacement support using `u` and returns whichever `(u, v)` the caller passed.

This probe succeeds:

```text
cell = lookup_math
edge = (n1, n1)
```

Ordinary generation currently iterates the legal table, and later row validation
rejects the bad edge, so the main generated-data path is safe. The public
constructor should nevertheless fail closed rather than emit an invalid
intervention record.

Check `(u, v)` against `CELL_INTERVENTION_EDGES[cell_id]` before drawing and
assert that the recomputed counterfactual sink differs from the stored original
sink.

## Scope consistency follow-ups

These are not additional Stage-0A blockers, but should be kept explicit:

1. `intervention_report()` should be described as a structural/descriptive
   estimator until the Stage-1A population/execution manifest and sequential
   inference wrapper exist, just as `CalibrationBundle` now is.
2. `signed_deployable_gap()` remains documented as the primary Stage-2
   comparator while accepting arbitrary self-declared mappings and not coupling
   the result to the required schema-valid rate. Stage 2 should wrap this pure
   point estimator in an authoritative report rather than treating the float as
   the complete result.
3. CE1 should pre-register how cluster-bootstrap replicates with zero eligible
   observations—or zero followed observations for the secondary diagnostic—are
   handled.

## Confirmed improvements

The following changes were independently reviewed and found sound:

- The misleading partial `PopulationManifest` has been removed.
- `GATE_PROVENANCE_REQUIREMENT` documents the missing authoritative layer in
  code.
- `gate_report()` fails closed.
- Oracle/control differences are explicitly named as descriptive.
- Frozen best-fixed assignments must be constant.
- Runner-ups cover every node and change exactly that node.
- Two-call choices are restricted to the fork/join family.
- Stored construction random accuracy is clearly named, while
  `CalibrationBundle.random_accuracy()` computes the control on the evaluated
  surface.
- Source-surface hashing is canonical and explicit re-derivation works when
  invoked.
- Raw intervention rows require real directed dependency edges and exact,
  non-null integer gold types.
- Bootstrap statistics now contain total, eligible, base, corrupted,
  counterfactual, followed, and followed-success counts.
- Zero-eligible clusters are retained for whole-cluster resampling.
- Ordinary nested per-cluster report statistics are recursively immutable.
- Malformed resource objects are translated into contextual
  `InfrastructureError`s.

## Verification

Independent verification was performed against exact head
`ef2368218f7c216c738b17c22267d95ea43df028` on the Linux environment:

```text
pytest -q -W error
416 passed in 1.65s

python -m tasks.conductor.agreement --cases 10000
16665/16665 node executions agree over exactly 10000 latent programs
```

The byte-stability generator wrote 58 request hashes and produced no diff. The
worktree remained clean. Targeted adversarial probes reproduced every finding
above.

The base commit is an ancestor of the head, so the PR is mechanically
fast-forwardable. GitHub's API was still reporting mergeability as
`unknown` at review time. No GitHub Actions runs or commit-status checks are
reported for this head.

`git diff --check fa63de6..ef23682` reports only one non-blocking mechanical
issue: an extra blank line at the end of
`plans/conductor/54_s_stage_0a_review.md`.

## Recommendation

Retain the structural/authoritative scope separation, fail-closed gate stub,
selection-semantic validation, random-control fix, shared directed-edge table,
complete bootstrap counts, and malformed-resource handling.

Before Stage 0A sign-off:

1. require one cell/namespace per intervention report;
2. enforce cluster-constant and sink-changing counterfactual targets;
3. derive or comprehensively validate every persisted report field;
4. make revived-selection verification mechanically visible to consumers;
5. finish totalizing the JSON boundaries; and
6. validate legal edges inside the intervention constructor itself.
