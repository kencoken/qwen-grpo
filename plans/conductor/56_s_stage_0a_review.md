# PR Review: Conductor Stage 0A — Seventh Pass

**Pull request:** [kencoken/qwen-grpo#2](https://github.com/kencoken/qwen-grpo/pull/2)

**Base:** `conductor@25c22ac4a4d7ef66d7ccd04fc178047279b45f4d`

**Head:** `conductor_stage_0a@95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996`

**Functional update:** `cf6f7443850ac8c87c6ab34c2f04b542ce8ceaa6`

**Scope:** 36 changed files, 11,254 additions, 6 deletions, 9 commits

**Review status:** Changes requested before declaring Stage 0A complete

## Executive summary

This revision genuinely closes the previous review's principal findings:

- intervention reports are now confined to one cell, split, and directed edge;
- original and counterfactual targets are cluster-constant and must differ;
- generated interventions must name a legal edge and move the sink;
- report headline fields are derived from per-cluster statistics on the normal
  construction and deserialization paths;
- population-cluster and eligible-cluster counts are now distinguished; and
- the CE1 bootstrap-degeneracy decision is recorded as a construction-screen
  blocker.

The refactor is directionally sound, but the new compact report representation
still accepts combinations of sufficient statistics that no execution trace
could produce. The live row boundary likewise permits terminal, path-success,
and eligibility fields to contradict the executor. Those are blocker-class
issues because they can change eligibility, follow-through, causal consistency,
and the bootstrap population while yielding a well-formed report.

There are four lower-priority boundary issues: the new verified-selection type
is publicly forgeable, intervention generation is not bound to the latent's
difficulty profile, direct report construction bypasses `_derive`, and numeric
deserialization remains neither type-exact nor total.

## Findings

### [P1] Reject impossible combinations of per-cluster sufficient statistics

**Locations:**

- [`tasks/conductor/estimands.py:321-352`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/estimands.py#L321-L352)
- [`tasks/conductor/estimands.py:538-556`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/estimands.py#L538-L556)

`_derive()` validates every count independently, but does not validate the
relationships imposed by the definitions of those counts. The following
self-consistent serialized reports were accepted and round-tripped through
`InterventionReport.from_json()`:

```text
n_eligible = 1
corrupted = 1
counterfactual = 1
```

This is impossible because the original and counterfactual targets are now
required to differ: one terminal cannot equal both.

```text
counterfactual = 0
followed = 1
followed_successes = 1
```

This is also impossible because every followed success is, by definition, a
counterfactual success.

A third probe added a cluster whose seven sufficient-statistic counts were all
zero. It was accepted and increased `n_population_clusters`, thereby changing
the population from which the Stage-1 cluster bootstrap will resample despite
representing no observation.

At minimum, require for every cluster:

```text
n_total >= 1
corrupted + counterfactual <= n_eligible
followed_successes <= counterfactual
```

After the terminal/path invariant in the next finding is enforced, the
executor semantics permit the stronger and more useful constraints:

```text
followed_successes == counterfactual
corrupted + counterfactual <= followed
```

These checks belong in `_derive()`, because that function is the common live
and persisted report boundary. Add tests that construct the impossible tables
directly and through `from_json()`.

### [P1] Make terminal, path-success, and base-eligibility fields coherent

**Locations:**

- [`tasks/conductor/estimands.py:443-464`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/estimands.py#L443-L464)
- [`tasks/conductor/executor.py:40-43`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/executor.py#L40-L43)
- [`tasks/conductor/executor.py:64-70`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/executor.py#L64-L70)
- [`tasks/conductor/executor.py:114-118`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/executor.py#L114-L118)

The new row validator correctly rejects:

```text
downstream_path_succeeded = true
mutated_terminal = null
```

It still accepts the inverse contradiction:

```text
downstream_path_succeeded = false
mutated_terminal = counterfactual_gold
```

I reproduced a report in which this row counted as a counterfactual success in
the primary eligible-set estimate while being excluded from the follow-through
denominator. The result therefore reported counterfactual consistency `1.0`
but a follow-through rate of `0.5` solely because the persisted flag
contradicted the terminal.

The executor contract makes the relationship mechanical: `terminal` is
non-null only when the sink succeeds, and an `access="all"` sink is blocked
after any required prior step fails. For these workflows, require:

```text
(mutated_terminal is not None) == downstream_path_succeeded
```

The validator also accepts an ineligible row with a successful base terminal:

```text
eligible = false
base_terminal = gold_answer
```

A successful sink entails that its required parents succeeded, so this row
cannot be ineligible under §1.9's definition. Mixing it with one ordinary row
reduced the reported eligibility rate from `1.0` to `0.5`. Require:

```text
base_terminal is not None  =>  eligible
```

Several existing synthetic estimator tests use a non-null terminal to stand
for a failed downstream path. Those fixtures describe states the executor
cannot emit and should instead use `mutated_terminal=None`.

### [P2] Make `VerifiedFrozenSelections` constructible only by verification

**Locations:**

- [`tasks/conductor/oracle.py:711-736`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/oracle.py#L711-L736)
- [`tasks/conductor/oracle.py:807-829`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/oracle.py#L807-L829)
- [`tasks/conductor/oracle.py:936-951`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/oracle.py#L936-L951)

Introducing a distinct verified type is the right typestate design, but its
public constructor currently defeats the guarantee. `__post_init__()` checks
only that the payload is a locally valid `FrozenSelections` object.

I constructed a locally valid artifact whose deployable selection was not the
construction argmax. The intended path rejected it:

```python
forged.verify_against(construction_bundle)  # PayoffSurfaceError
```

Direct wrapping bypassed that check:

```python
verified = VerifiedFrozenSelections(forged)
qualification_bundle.deployable_accuracy(verified)  # accepted
```

The qualification helper returned accuracy `1.0` for forged assignment
`(2, 2)`, although the construction-frozen assignment was `(0, 0)`.

Make verified construction inaccessible except through a guarded factory, or
have the consuming operation take the construction bundle and perform
verification in the same call. A publicly constructible marker is evidence
that wrapping occurred, not that source verification occurred.

This is not yet an authoritative-gate bypass because `gate_report()` correctly
raises at Stage 0A, hence the P2 rather than P1 priority. The issue must be
closed before the type is relied on by Stage 1A.

### [P2] Bind intervention generation to the latent's difficulty profile

**Location:**

- [`tasks/conductor/program.py:523-559`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/program.py#L523-L559)

`draw_intervention()` derives its replacement support from the supplied
difficulty profile but never checks that this is the profile under which the
latent was generated.

Starting from one `lookup_math` latent, I used:

- the default valid profile, whose digest matched the latent; and
- a second valid profile with a wider `lookup_math.value_band` and a different
  digest.

For the same `(latent_program_id, n1 -> n2)`, the first call selected
replacement `45` and the second selected `87`. Both calls succeeded. Thus the
result is not actually one deterministic replacement per latent and edge when
the caller mis-wires a profile, and a resumed run can silently change its
counterfactual target.

Before deriving replacement support:

1. validate the supplied profile;
2. require `profile_version(profile) == latent["difficulty_profile_version"]`;
3. validate the applicable generator version or route through a shared
   load-time latent validator; and
4. fail with `GenerationError` or `LoadError` on mismatch.

### [P2] Enforce `_derive()` as the only `InterventionReport` constructor

**Location:**

- [`tasks/conductor/estimands.py:165-235`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/estimands.py#L165-L235)

The documentation says identity and sufficient statistics are the source of
truth and `_derive()` is the only constructor. The public dataclass initializer
does not enforce that contract: `__post_init__()` only freezes the mappings.

Direct construction accepted a report containing, among other contradictions:

```text
cell_id = "bogus"
n_total = -1
n_eligible = 99
eligibility_rate = NaN
corruption_accuracy = -3.0
follow_through_rate = 3.0
cluster_successes = {}
```

Likewise, `dataclasses.replace(valid_report, n_total=999)` creates an
inconsistent in-memory report which can be consumed or serialized; only a later
`from_json()` round-trip detects it.

If source-of-truth construction is intended to be mechanical, make the
initializer private/factory-only, or have construction recompute and validate
all derived fields. The latter requires avoiding recursive construction from
`_derive()`, for example by separating calculation from object creation.

### [P2] Complete exact and total numeric validation on persistence boundaries

**Locations:**

- [`tasks/conductor/estimands.py:262-304`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/estimands.py#L262-L304)
- [`tasks/conductor/oracle.py:101-106`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/oracle.py#L101-L106)
- [`tasks/conductor/oracle.py:513-540`](https://github.com/kencoken/qwen-grpo/blob/95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996/tasks/conductor/oracle.py#L513-L540)

`InterventionReport.from_json()` compares every redundant scalar through one
generic numeric expression:

```python
abs(value - expected) > 1e-9
```

Confirmed residual cases:

- `NaN` is accepted for redundant counts and rates because comparisons with
  NaN are false;
- `n_total=1.0` is accepted where the schema requires an integer count;
- sufficiently large integers in float-valued fields leak raw
  `OverflowError`; and
- boolean values in derived mappings can compare equal to numeric `0` or `1`.

Validate according to the derived field's schema before comparing:

- exact non-boolean integers for count fields;
- finite numeric values for rates and signed differences;
- exact mapping keys and finite, non-boolean mapping values; and
- conversion of malformed numeric input to `InfrastructureError` rather than
  raw arithmetic exceptions.

The same ordering problem exists in `_check_probability()`: `math.isfinite()`
can raise `OverflowError` on a sufficiently large integer before the range
check rejects it.

As a smaller part of the same totality sweep, the three public
`validate_*_surface(raw, cell_id)` functions still raise raw `TypeError` for an
unhashable `cell_id` such as `[]`. Apply the type-before-membership check already
used in `ValidatedSurface.__post_init__()` and `from_json()`.

## Confirmed fixes from the previous review

The following are now mechanically enforced on the relevant Stage-0A paths:

1. **One report population:** rows from different cells or namespaces cannot
   be pooled merely because their edge tuples coincide.
2. **Directed-edge identity:** one report carries one legal directed edge for
   its named cell, and that identity is persisted.
3. **Cluster-constant targets:** all renderings of one latent must carry the
   same original and counterfactual targets.
4. **Sink-changing interventions:** equal original and counterfactual targets
   are rejected, and `draw_intervention()` checks the recomputed sink.
5. **Ordinary persisted-field recomputation:** live and deserialized reports
   use the same `_derive()` path, and edits to the tested headline fields are
   detected.
6. **Explicit cluster counts:** `n_population_clusters` and
   `n_eligible_clusters` replace the ambiguous single count.
7. **CE1 acknowledgement:** handling of bootstrap replicates with zero
   eligible or zero followed observations is explicitly recorded for
   pre-registration before qualification data.

These are substantive improvements. In particular, the one-cell/split/edge
binding and the separation of identity/statistics from redundant report fields
are the correct foundations for the Stage-1A layer.

## Verification

Verification was performed against exact head
`95d99d83b9cbcaebb0ea60ee25aa6a7500c9c996`, with
`conductor@25c22ac4a4d7ef66d7ccd04fc178047279b45f4d` as the PR base.

### Automated suite

```text
440 passed in 1.65s
```

The suite was run on Linux with warnings treated as errors.

### Reference/tool agreement

```text
agreement: 16665/16665 node executions agree over 10000 latent programs
```

All declared operator-by-cell strata were exercised.

### Byte-stability fixture

```text
wrote 58 request hashes
```

Regenerating the fixture produced no diff.

### Repository and PR state

- The review worktree was clean after verification.
- The `ef23682..95d99d8` update passes `git diff --check`.
- The live PR targets `conductor`, reports head `95d99d8`, and is mergeable.
- GitHub reports no configured status checks or Actions runs for this head, so
  the Linux verification above is the operative test evidence.

## Recommendation

Do not sign off Stage 0A yet. The two P1 findings should be fixed before the
report artifact is treated as the source of truth for Stage 1A. The verified
selection, profile binding, constructor, and numeric-boundary findings should
also be resolved now while these interfaces are still being frozen; otherwise
they become easy-to-miss failure paths in the resumable calibration layer.

After those targeted changes, the remaining architecture appears close to
sign-off. No restructuring of the staged plan is indicated.
