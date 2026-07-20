# PR Review: Conductor Stage 0A — Third Pass

**Pull request:** [kencoken/qwen-grpo#2](https://github.com/kencoken/qwen-grpo/pull/2)

**Base:** `conductor@25c22ac4a4d7ef66d7ccd04fc178047279b45f4d`

**Head:** `conductor_stage_0a@2363aa3971b76fb4ec8df60a324b305c10ad0005`

**Scope:** 32 changed files, 7,703 additions, 6 deletions, 4 commits

**Review status:** Changes requested before declaring Stage 0A complete

## Executive summary

This revision resolves most of the preceding review findings. In particular:

- The intervention estimator now follows the frozen §1.9 full-sample eligible-set definition. The example with two correct observations in one cluster and one incorrect observation in another correctly reports `2/3` as the primary estimate and `1/2` only as an equal-cluster diagnostic.
- Payoff surfaces are now keyed by observation identity and restrict terminal correctness to binary `{0, 1}` values.
- The direct-answer path is UTF-8-totalized.
- Agreement coverage is exact rather than silently dropping the remainder.
- Resource structures, profile domains, sensitivity replay handling, and public projections are materially better validated.

The two principal design choices in the revision are also sound in direction: using one typed surface representation for assignments and controls, and deriving public numeric features from `PublicParams`. Both still have incomplete boundary enforcement at their call sites.

Two issues should continue to block Stage 0A sign-off:

1. Observation disclosure is not bound to the complete instance identity or to the instance's actual payload data.
2. One- and two-call control surfaces are not required to use the assignment surface's population, despite the documented paired-support requirement.

Several P2 hardening issues should also be closed before the construction screen because they can create invalid calibration metrics, leak noncanonical features into B1, or make generation hang on a profile that passes validation.

## Findings

### [P1] Bind observation disclosure to instance identity and payload provenance

**Locations:**

- [`tasks/conductor/render.py:272-299`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/render.py#L272-L299)
- [`tasks/conductor/program.py:951-962`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/program.py#L951-L962)

`build_observation` derives disclosure from `instance["visibility_condition"]`, which closes the original independent `visible_payload_texts` switch. It does not, however, verify that this field agrees with `render_instance_id`. `observation_for` checks only `latent_program_id`.

Consequently, changing a private instance's `visibility_condition` to `visible` causes it to disclose resources while retaining a `render_instance_id` ending in `:private`. This directly contradicts the intended invariant that a private-labelled observation cannot carry a `Resources:` block.

There is a second provenance problem: the registry remains an independent argument. The only consistency check is equality of manifest handles. A newly constructed registry with the same handles but altered resource values is accepted, and those altered values are disclosed in the observation.

This is an ordinary accidental-wiring risk, not merely an adversarial mutation: handles can coincide across instances, while the payload data differ.

Recommended resolution:

- Verify the complete identity relation:

  ```text
  render_instance_id = latent_program_id + ":" + renderer_id + ":" + visibility_condition
  ```

- Construct the disclosure registry from the instance's own `private_registry`, or require exact payload identity rather than manifest equality if an external registry must remain an argument.
- Prefer a validated instance object at this boundary rather than an independently mutable dictionary and registry.
- Add regressions for private→visible mutation with a stale ID and for a same-manifest/different-payload registry.

### [P1] Validate assignment and control surfaces as one paired calibration population

**Locations:**

- [`tasks/conductor/oracle.py:105-177`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/oracle.py#L105-L177)
- [`tasks/conductor/oracle.py:196-220`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/oracle.py#L196-L220)

The observation-keyed representation now proves that every candidate *within one surface* uses identical cluster and observation support. That is a substantive fix.

The one- and two-call validators still receive only their own raw surface and a free `cell_id`. They therefore cannot enforce their documented requirement to use "the same observation support as the assignment surface."

The following all succeed:

- An assignment surface over one set of observations and a one-call surface for the same nominal cell over an entirely disjoint set.
- Relabelling a one-node `lookup_atomic` assignment surface as `math_atomic` or `code_atomic`, because only arity is checked.
- `validate_one_call_surface(..., "bogus")`.
- One-call endpoint keys such as `False` or `0.0`, which alias integer key `0` under Python equality and hashing.

The first case can invalidate the Stage 1 oracle-versus-one-call gate by comparing different populations. The cell-label cases mean the new surface is not yet genuinely cell-bound.

Recommended resolution:

- Introduce a jointly validated calibration bundle, or pass the validated assignment surface as the reference when validating control surfaces.
- Require identical `cell_id`, clusters, and observation IDs across assignment, one-call, and applicable two-call surfaces.
- Validate that canonical observation identities belong to the named cell and construction population.
- Validate exact control candidate types, using the same `type(x) is int` discipline already applied to assignment endpoint IDs.
- Restrict the two-call surface to the cell(s) for which that family is defined.

### [P2] Complete the public-only feature boundary on prediction paths

**Locations:**

- [`tasks/conductor/baselines.py:135-145`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/baselines.py#L135-L145)
- [`tasks/conductor/baselines.py:220-237`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/baselines.py#L220-L237)
- [`tasks/conductor/baselines.py:284-288`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/baselines.py#L284-L288)
- [`tasks/conductor/types.py:411-467`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/types.py#L411-L467)

Making `PublicFeatureRecord.public_numeric_values` a derived property is correct, and its construction-time cross-check detects drift in the normal training-row path.

The feature and prediction APIs still accept an independent caller-supplied numeric dictionary. A legitimate `lookup_math` `PublicParams` object combined with `{"p": 777777, "q": 888888}` produces a feature row containing those injected values. `echo_predict` has the same independent-input property.

Thus fitting is protected, but evaluation or prediction can still consume stale or private-derived values. The tests themselves continue to pass `latent["public_numeric_values"]` separately to `feature_row`, preserving the dual source of truth.

`PublicParams` also checks only the key set, not subtype-specific value types. It accepts, for example, `p=True` as a numeric feature and mutable objects such as a list-valued key. Mutating that list changes rendered bytes while the same `PublicParams` identity remains. Calling `__init__` again can also replace the backing mapping despite the documented immutability guarantee.

Recommended resolution:

- Remove `public_numeric_values` from `feature_row` and `shallow_predict`; derive it internally with `params.numeric_features()`.
- Make `echo_predict` consume canonical `PublicParams` or `PublicFeatureRecord` input.
- Validate subtype-specific scalar types and enums in `PublicParams` or expose only a guarded construction path.
- Make initialization one-shot and ensure all accepted values are deeply immutable.

### [P2] Totalize sensitivity-row validation before population filtering

**Location:** [`tasks/conductor/estimands.py:220-274`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/estimands.py#L220-L274)

The revision correctly rejects duplicate `(cluster_id, observation_id)` rows and cluster-inconsistent collision metadata. Other malformed persisted rows still pass:

- `correct=2` produces `headline=2.0`.
- `visibility_condition="Private"` is silently excluded instead of rejected.
- Integer `0`/`1` values are accepted for boolean fields.
- The same `observation_id` under two different clusters is accepted.

These cases can silently alter the headline population or produce impossible scores while appearing to be valid `WorkflowOutcome` objects.

Recommended resolution:

- Require exact `bool` types for `public_numeric_collision`, `correct`, and `answer_in_subtask_detected`.
- Require the frozen visibility enum.
- Validate non-empty string identifiers and bind each observation identity to exactly one cluster.
- If the expected renderer support is available, validate complete per-cluster support here as well.

### [P2] Replace T1 support enumeration with analytic sampling

**Locations:**

- [`tasks/conductor/profiles.py:26-33`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/profiles.py#L26-L33)
- [`tasks/conductor/profiles.py:246-264`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/profiles.py#L246-L264)
- [`tasks/conductor/program.py:629-640`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/program.py#L629-L640)
- [`tasks/conductor/program.py:885-931`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/program.py#L885-L931)

The workload caps prevent the previously identified trillion-element allocation. They still permit a one-million-element T1 feasible-set scan on each proposal, repeated up to the 1,000-attempt resampling cap.

This profile passes validation:

```python
a_band = [1_000_000, 1_000_000]
b_band = [99, 99]
c_band = [1, 1_000_000]
t1.d_band = [1_000_000_000, 1_000_000_000]
```

For every T1 proposal, `a * b mod d = 99_000_000`, which is outside the `c` band. Generation therefore enumerates one million candidates, rejects, and can repeat this roughly one thousand times for one latent—approximately one billion Python iterations after a profile has passed load-time validation.

The congruence support can be handled analytically:

1. Compute `r = (a * b) % d`.
2. Compute the first value at or above `c_min` congruent to `r mod d`.
3. Reject immediately if it exceeds `c_max`.
4. Derive the number of solutions arithmetically and sample an offset without materializing the support.

This removes both the pathological case and the ordinary million-element allocation.

### [P2] The validated-surface boundary remains bypassable and partly non-total

**Locations:**

- [`tasks/conductor/oracle.py:62-77`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/oracle.py#L62-L77)
- [`tasks/conductor/oracle.py:126-155`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/oracle.py#L126-L155)
- [`tasks/conductor/oracle.py:223-244`](https://github.com/kencoken/qwen-grpo/blob/2363aa3971b76fb4ec8df60a324b305c10ad0005/tasks/conductor/oracle.py#L223-L244)

Selectors now require a `ValidatedSurface`, but the dataclass constructor is public and performs no invariant validation. A directly constructed assignment surface containing only `(9,)` passes `_require_surface`, and `select_deployable` returns `(9,)`.

In addition, `_validate` sorts cluster keys before checking that they are strings. Mixed string/integer keys therefore raise raw `TypeError` rather than the promised `PayoffSurfaceError`.

Recommended resolution:

- Put full invariant checks in `ValidatedSurface.__post_init__`, or make it an internal product whose constructor cannot be used as an unchecked deserialization path.
- Validate cluster-key types before sorting.
- Add regressions for a forged validated object and heterogeneous malformed key types.

## Lower-priority follow-ups

These need not carry the same sign-off weight as the findings above, but should be resolved before their affected paths become operational:

1. **Normative IR resource validation:** `validate_reference_program` still compares manifest and registry sets without first rejecting duplicate or malformed manifest handles. The protections added to `InstanceRegistry` should also apply to the normative IR validator.
2. **Serialization contract:** `PublicParams`, `ValidatedSurface`, and `InterventionReport` contain mapping proxies. Ordinary `copy.deepcopy` and `dataclasses.asdict` fail for these objects. Stage 1 is explicitly resumable, so define and test an explicit JSON artifact representation rather than relying on generic dataclass serialization.
3. **Intervention-CI wording:** the full-sample correction is right. Cluster-bootstrap confidence intervals should resample paired latent clusters and recompute the full-sample statistic from raw rows. The equal-cluster value in `cluster_weighted` is a useful diagnostic, but it is not the primary bootstrap statistic.

## Verification

Independent verification was performed against exact head `2363aa3971b76fb4ec8df60a324b305c10ad0005`:

```text
pytest -q -W error
336 passed

python -m tasks.conductor.agreement --cases 10000
16665/16665 node executions agree over exactly 10000 latent programs
```

The byte-stability fixture regenerated with 58 hashes and no diff. The working tree remained clean after verification.

Targeted adversarial probes confirmed that the preceding review's principal cases—observation-key pairing within a surface, binary correctness, direct UTF-8 rejection, exact agreement coverage, and the full-sample intervention estimate—are fixed. The residual cases documented above were separately reproduced on the same commit.

The pull request is mechanically mergeable. No GitHub Actions workflow runs or commit-status checks are currently reported for this head.

## Recommendation

Do not reopen the intervention-weighting specification: the implementation now follows the signed-off text correctly.

Before Stage 0A sign-off, close the two P1 boundary problems and the three experiment-affecting P2 problems concerning public-only features, sensitivity-row validity, and T1 workload. The validated-surface hardening is small enough to include in the same patch. The remaining serialization and normative-IR items should be closed before Stage 1 persistence or construction data depends on those paths.
