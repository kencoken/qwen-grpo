# PR Review: Conductor Stage 0A — Follow-up

**Pull request:** [kencoken/qwen-grpo#2](https://github.com/kencoken/qwen-grpo/pull/2)

**Base:** `conductor@25c22ac4a4d7ef66d7ccd04fc178047279b45f4d`

**Head:** `conductor_stage_0a@c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2`

**Scope:** 31 changed files, 6,804 additions, 6 deletions, 3 commits

**Review status:** Changes requested before declaring Stage 0A complete

## Executive summary

This revision is a substantial improvement. Most findings from the preceding review have been addressed, the acceptance battery has expanded from 223 to 296 passing tests, and the reference-versus-tool agreement command now covers exactly 10,000 latent programs. The core architecture remains well designed.

Three scientific-validity issues should still block Stage 0A sign-off:

1. The payoff-surface representation cannot prove that assignments were evaluated on the same observation IDs, and cell identity remains optional.
2. Resource visibility is not structurally coupled to an instance's `visibility_condition`, allowing private-labelled observations to contain visible payloads.
3. The new intervention point estimates introduce equal-cluster weighting that does not clearly match the frozen full-sample eligible-set estimand.

There are also several smaller boundary gaps in direct-output parsing, profile workload validation, sensitivity-record validation, and the claimed immutable public-data boundary.

## Findings

### [P1] Key payoff outcomes by observation identity and require cell identity

**Locations:**

- [`tasks/conductor/oracle.py:18-19`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/oracle.py#L18-L19)
- [`tasks/conductor/oracle.py:36-103`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/oracle.py#L36-L103)
- [`tasks/conductor/oracle.py:123-211`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/oracle.py#L123-L211)

The validator now enforces a full `3^S` enumeration, identical cluster support, and identical per-cluster observation counts. That closes the obvious partial-surface case, but the underlying representation remains:

```python
surface[assignment][cluster_id] = [correctness, ...]
```

Because observations are anonymous list elements, validation cannot establish that every assignment was evaluated on the same renderer/example IDs. Assignment A could contain observations `o1, o2` and assignment B `o2, o3`; equal counts make this pass despite unpaired support. This preserves the original resumable or misassembled calibration risk.

There are related domain gaps:

- `cell_id` is optional, so `S` is inferred instead of checked against the intended cell.
- `{(): {"c": [1.0]}}` is accepted as a zero-node surface.
- Float endpoint IDs such as `(0.0,)` pass because they compare and hash equal to integers.
- A scalar key such as `0` raises raw `TypeError` rather than `PayoffSurfaceError`.
- A list-valued `deployable` can reach tuple concatenation and raise raw `TypeError` in `node_runner_up`.
- The one- and two-call selectors accept aggregate accuracies, so they cannot validate paired observation support or verify that the cluster-weighted objective was used.

Use an observation-keyed representation, for example:

```python
surface[assignment][cluster_id][observation_id] = correctness
```

Require `cell_id`, validate exact cluster and observation key equality across every assignment, and return a validated surface object consumed by all selectors. The aggregate one- and two-call controls should either consume the same kind of surface or require an explicitly validated aggregate type.

Per-observation terminal correctness should also be restricted to `{0, 1}` unless fractional observations are deliberately part of the contract. Merely accepting all values in `[0, 1]` makes it possible to feed the GRPO reward `0.5` into a terminal-accuracy surface accidentally.

### [P1] Bind resource disclosure to `visibility_condition`

**Locations:**

- [`tasks/conductor/program.py:951-982`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/program.py#L951-L982)
- [`tasks/conductor/render.py:269-286`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/render.py#L269-L286)
- [`test_conductor_estimands.py:287-311`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/test_conductor_estimands.py#L287-L311)

`render_instance` validates and stores `visibility_condition`, but `render_observation` does not receive or check it. Payload disclosure is independently controlled by whether the caller supplies `visible_payload_texts`.

Consequently, a `private` instance can be rendered with a `Resources:` block while retaining its `:private` identity and private scoring metadata. Conversely, a `visible` instance can omit its payload. The new observation test demonstrates the first inconsistency by creating a private instance and then passing its registry payloads to `render_observation`.

This can silently contaminate the private headline stratum. Add one canonical observation builder that accepts the instance and registry, derives disclosure exclusively from `instance["visibility_condition"]`, and rejects inconsistent inputs. A lower-level text formatter can remain internal if useful, but experimental code should have one safe construction path.

### [P1] Reconcile intervention weighting with the frozen estimand

**Locations:**

- [`conductor_cell_specs.md:475-498`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/conductor_cell_specs.md#L475-L498)
- [`tasks/conductor/estimands.py:68-78`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/estimands.py#L68-L78)
- [`tasks/conductor/estimands.py:137-161`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/estimands.py#L137-L161)

Section 1.9 names **full-sample eligible-set accuracy** as the primary metric, with clustering specified for comparisons and bootstrap uncertainty. `intervention_report` instead averages observations within each cluster and then weights every cluster equally.

For example, consider two eligible correct observations in cluster A and one eligible incorrect observation in cluster B:

- full eligible-set accuracy = `2 / 3`;
- implemented equal-cluster estimate = `(1 + 0) / 2 = 0.5`.

Eligibility can differ between renderer observations because base worker success can depend on the rendered prompt. This is therefore not limited to malformed data and can move Stage 1 gate values.

Either:

1. compute primary accuracies over all eligible rendered observations and use cluster resampling for uncertainty; or
2. explicitly amend and re-freeze the specification to state that latent clusters receive equal point-estimate weight.

The same decision should apply consistently to the conditioned follow-through estimate. It should be resolved before construction results are inspected.

### [P2] UTF-8 totalization missed the direct-answer path

**Location:** [`tasks/conductor/contract.py:94-103`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/contract.py#L94-L103)

Normal endpoint completions and policy actions now reject non-UTF-8-encodable strings correctly. Direct completions used by B1, B3, and B4 still bypass that completion-level check.

For example:

```python
completion = "reasoning " + chr(0xD800) + "\n42"
parse_answer_line(completion)  # returns 42
completion.encode("utf-8")    # raises UnicodeEncodeError
```

The result can therefore be accepted and later abort trace or cache encoding. Check `is_utf8_encodable(completion)` before scanning the answer line and return `None` when it fails.

Add focused regression tests for:

- an Arabic-Indic numeral in an artifact;
- a lone surrogate inside an artifact;
- a lone surrogate in a workflow string;
- a lone surrogate in direct-answer reasoning followed by a valid final integer.

The fixed normal paths currently lack explicit Unicode regression tests as well.

### [P2] Profile validation still permits unbounded work and allocation

**Locations:**

- [`tasks/conductor/profiles.py:152-154`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/profiles.py#L152-L154)
- [`tasks/conductor/profiles.py:245-269`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/profiles.py#L245-L269)
- [`tasks/conductor/program.py:228-244`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/program.py#L228-L244)
- [`tasks/conductor/program.py:490-510`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/program.py#L490-L510)
- [`tasks/conductor/program.py:629-640`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/program.py#L629-L640)

The new int64 checks prevent NumPy representability failures, but they do not bound computational cardinality. This profile still passes validation:

```python
profile["cells"]["code_atomic"]["L_band"] = [5, 1_000_000_000_000]
```

Generation can then attempt to allocate a list of size `L`. Similar full-range materialization occurs in `s_minus`, intervention replacement support, and T1's feasible-`c` calculation.

Introduce explicit list, payload, and support-cardinality limits consistent with the prompt and runtime budgets, or replace materialization with analytic support counts and deterministic index-based sampling. Invalid or computationally impossible profiles should fail quickly at profile load rather than hang or cause an OOM.

The derived public-index check should use the maximum attainable `U - 1`, namely `min(L_max, value_band_cardinality) - 1`, rather than `L_max - 1` alone.

### [P2] Sensitivity scoring permits replayed or internally inconsistent rows

**Location:** [`tasks/conductor/estimands.py:187-230`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/estimands.py#L187-L230)

`intervention_report` rejects duplicate `(cluster_id, observation_id)` records, but `sensitivity_scores` does not. A duplicated trace silently changes the cluster mean and `n_observations` while all same-population assertions continue to pass.

The scorer also permits renderer rows from one latent cluster to disagree about latent-level collision metadata. That can cause only part of a supposedly no-collision cluster to enter the headline population.

Before filtering, require unique `(cluster_id, observation_id)` identities and cluster-constant latent metadata such as `public_numeric_collision`. If expected renderer support is available, validate that support as well.

### [P2] The claimed immutable public boundary is only shallowly immutable

**Locations:**

- [`tasks/conductor/types.py:389-431`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/types.py#L389-L431)
- [`tasks/conductor/baselines.py:135-173`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/baselines.py#L135-L173)

`PublicParams` is documented as immutable, but its internal dictionary remains writable and `_cell_id` can be reassigned. Mutation can therefore change rendered bytes without changing the latent identity.

`PublicFeatureRecord.public_numeric_values` is also a mutable caller-supplied dictionary independent of `PublicParams`. Extra `p`, `q`, `t`, `k`, or `i` values can be injected into a supposedly sanitized control record, including values derived from private state.

Use genuinely immutable storage for `PublicParams`. Derive shallow-control numeric features directly from the validated public projection, or validate and freeze the exact subtype-specific numeric key/value set when constructing `PublicFeatureRecord`.

The ordinary generator path is currently safe, so this is not the same severity as the visibility issue, but it weakens the structural guarantee the revision claims to establish.

### [P3] Resource constructors accept ambiguous structures

**Locations:**

- [`tasks/conductor/resources.py:17-26`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/resources.py#L17-L26)
- [`tasks/conductor/types.py:118-149`](https://github.com/kencoken/qwen-grpo/blob/c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2/tasks/conductor/types.py#L118-L149)

`InstanceRegistry` compares sets, so a manifest containing the same handle twice is accepted. Payload rendering can consequently repeat a resource even though the registry contains one entry.

`IntegerRecord` accepts duplicate entity names, duplicate field names, and non-rectangular keyed grids. Lookup then becomes first-match-dependent rather than representing the specified ordered entities-by-fields grid.

Normative regeneration protects correctly validated generated instances, making this lower priority. Nevertheless, these constructors are runtime and load boundaries and should reject malformed structures directly. Check manifest cardinality before set comparison, and enforce entity uniqueness, field uniqueness, non-empty grids, and the common ordered field schema for keyed records.

## Findings resolved by this revision

The following parts of the preceding review are now substantively addressed:

- Normal endpoint completion parsing now handles Arabic-Indic digits and lone surrogates as typed failures.
- Policy action parsing rejects non-UTF-8-encodable completions and fields.
- Renderer and public-only control entry points normally require a `PublicParams` projection rather than the complete generator mapping.
- Latent indices reject negatives, booleans, and namespace overflow.
- Visibility labels are restricted to the frozen enum.
- Sampled bands are checked for int64 representability.
- `WorkerResult` enforces the status, value, rejection-code, and flag truth table.
- The shallow predictor is construction-only, requires one row per latent cluster, and consumes a sanitized record type.
- Majority-class and echo controls have deterministic, frozen tie and missing-subtype rules.
- Intervention eligibility, common denominators, eligibility-rate reporting, and the eligible-without-override abort path are implemented.
- Collision sensitivity, the true-zero no-op case, B4 request construction, direct-answer parsing, and semantic-to-positional mapping for all cells now have acceptance coverage.
- The agreement command distributes remainders, rejects incomplete requests, and asserts latent and stratum coverage.
- D16, fitted B1 models, and real chat-template bytes are explicitly recorded as construction-screen blockers.
- The provisional fixture is no longer described as the final cache-key fixture.

## Verification performed

All checks used exact head `c1b5ebe95fe05cf5c0c69c513aafb6e3f50bd4f2`:

- Full repository suite with warnings treated as errors: **296 passed**.
- Reference-versus-tool agreement: **16,665 / 16,665 node executions** over exactly **10,000 latent programs**.
- Agreement coverage included all **13 operator × cell strata**.
- The 58 byte-stability hashes regenerated with no fixture diff.
- The checkout remained clean after verification.
- GitHub reports the PR as mergeable against `conductor`.
- No commit-status checks are configured for the PR.

Targeted adversarial probes confirmed:

- Arabic-Indic artifact input now produces typed `E_PARSE`.
- A surrogate-bearing normal worker completion now produces typed `E_PARSE`.
- A surrogate-bearing workflow field now produces `ActionSchemaError`.
- A surrogate-bearing direct completion followed by `42` is still accepted as `42`.
- A scalar payoff key raises raw `TypeError`.
- A zero-node payoff surface is accepted.
- Float endpoint IDs are accepted and returned.
- A profile with `code_atomic.L_band = [5, 10^12]` passes validation.
- Duplicate sensitivity rows are counted more than once.
- Duplicate entities, fields, and non-rectangular keyed records are accepted.

## Explicit deferrals and non-findings

The following remain appropriately deferred and should not be treated as new defects in this PR:

- D16 is explicitly marked `DRAFT` and now clearly blocks the construction screen.
- Real chat-template/cache-key bytes belong to Stage 0B and are recorded as a blocker before relying on cache identity.
- Worker loading, NF4 configuration, batching, truncation telemetry, cache persistence, and trace writing belong to Stage 0B.
- Training integration and the policy-dependent smoke belong to Stage 0C.
- The fitted B1 models cannot be frozen until construction inputs exist, but their fitting rules must remain frozen and the fitted models must be recorded before construction accuracy is inspected.

## Recommendation

Request another revision before declaring Stage 0A complete.

At minimum, sign-off should require:

1. an observation-keyed, cell-bound validated payoff-surface contract;
2. a canonical observation builder that derives disclosure from `visibility_condition`;
3. an explicit resolution of the intervention point-estimate weighting rule; and
4. UTF-8 validation on the direct-answer path with focused regression tests.

The profile workload, sensitivity uniqueness, and immutable-boundary issues should also be inexpensive to close before the construction screen. The resource-schema hardening is lower priority but belongs naturally in the same boundary-validation pass.

Subject to those changes, the Stage 0A design and implementation are close to sign-off.
