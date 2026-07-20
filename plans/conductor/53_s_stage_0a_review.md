# PR Review: Conductor Stage 0A — Fourth Pass

**Pull request:** [kencoken/qwen-grpo#2](https://github.com/kencoken/qwen-grpo/pull/2)

**Base:** `conductor@25c22ac4a4d7ef66d7ccd04fc178047279b45f4d`

**Head:** `conductor_stage_0a@61350652114beb23e456b2ef0cb39b64aa6cf532`

**Scope:** 33 changed files, 8,721 additions, 6 deletions, 5 commits

**Review status:** Changes requested before declaring Stage 0A complete

## Executive summary

This revision genuinely closes the fourteen concrete residual probes from the preceding review. The two advertised blocker fixes are substantially present:

- The canonical Conductor observation path now cross-checks the identity fields encoded by `render_instance_id` and derives visible payloads from the instance's own registry rather than an independently supplied registry.
- `CalibrationBundle` requires assignment and control surfaces to share their cell, clusters, and observation identities.

The public-feature, T1, sensitivity primitive-type, normative IR, and bootstrap-wording changes are also sound. The test and agreement claims were independently reproduced.

Three issues nevertheless remain blocking:

1. `CalibrationBundle` reselects the deployable assignment and controls on whichever population it is given. On qualification data this violates the construction-selected-and-frozen contract and can invalidate the sequential-look inference.
2. The new payoff-surface deserializer silently coerces invalid persisted values and silently overwrites duplicate candidate entries.
3. B3 and B5 retain the independently supplied registry path that was correctly removed from the Conductor observation builder.

The bundle also proves only that its arms contain the same self-declared IDs; it does not yet prove that those IDs are the registered construction/qualification population or that all arms were executed under the same runtime profile. That provenance requirement must be explicit before construction or qualification results depend on the bundle.

## Findings

### [P1] Separate construction selection from qualification evaluation

**Locations:**

- [`tasks/conductor/oracle.py:443-468`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/oracle.py#L443-L468)
- [`tasks/conductor/oracle.py:508-548`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/oracle.py#L508-L548)
- [`conductor_cell_specs.md:411-431`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/conductor_cell_specs.md#L411-L431)
- [`plans/conductor/13_f_plan_rev6.md:130-136`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/plans/conductor/13_f_plan_rev6.md#L130-L136)

The frozen contract is unambiguous: the deployable assignment and relevant controls are selected on construction data, frozen, and evaluated unchanged on fresh qualification data. They are never reselected using qualification outcomes.

`CalibrationBundle.deployable()`, `best_one_call()`, and `best_two_call()` instead perform `argmax` on the bundle's current surfaces. `deployable_vs_one_call()` and `deployable_vs_two_call()` immediately evaluate those newly selected choices. Nothing restricts the bundle to construction data: a qualification-only or test-only bundle is accepted.

An exact probe produced:

```text
construction-frozen assignment: (0, 0)
assignment selected by qualification bundle: (2, 2)
qualification bundle's reported gap: 1.0
qualification gap using the construction-frozen choices: 0.0
```

This is not only an optimistic point-estimate issue. Qualification uses pre-registered sequential looks at 100/300/500 clusters, or 100/200 for fork/join. Re-maximizing at every look changes the candidates and hence the tested hypothesis using qualification outcomes, invalidating the intended alpha-spending/CI interpretation.

The same construction-freeze requirement applies to:

- the deployable assignment;
- best one-call;
- best two-call;
- best-fixed; and
- each node runner-up used in effective-routing-stakes gates.

Recommended resolution:

1. Create an immutable, persisted `FrozenSelections` artifact from a construction bundle.
2. Record every construction-selected candidate needed downstream.
3. Make qualification APIs accept that artifact and evaluate those exact candidates without exposing any `argmax` operation.
4. Enforce the construction namespace at the selection boundary. Keep qualification evaluation as a distinct operation.

### [P1] Bind calibration surfaces to the registered population and execution profile

**Locations:**

- [`tasks/conductor/oracle.py:101-132`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/oracle.py#L101-L132)
- [`tasks/conductor/oracle.py:149-197`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/oracle.py#L149-L197)
- [`tasks/conductor/oracle.py:417-437`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/oracle.py#L417-L437)
- [`conductor_cell_specs.md:175-188`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/conductor_cell_specs.md#L175-L188)
- [`conductor_cell_specs.md:779-814`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/conductor_cell_specs.md#L779-L814)
- [`plans/conductor/13_f_plan_rev6.md:146-166`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/plans/conductor/13_f_plan_rev6.md#L146-L166)

The ID parsers correctly recover the cell, namespace, renderer, and visibility. Surface validation currently uses only the cell and the observation-to-cluster relationship. The bundle then requires exact equality of those self-declared IDs across arms.

Confirmed accepted cases include:

- a surface mixing construction and qualification clusters;
- a qualification-only or test-only surface reaching oracle selection;
- a surface with one fabricated `deadbeef` cluster and one renderer being treated as complete; and
- grammar-valid identities outside registered namespace caps.

The specification requires every latent to be rendered in all three forms, designated visible-slice pairings, deterministic namespace prefixes, and registered sequential-look sizes. A partial resumable artifact or cherry-picked support should not be able to freeze routing simply because every candidate contains the same truncated support.

There is also no execution provenance on a surface. Assignment and control surfaces produced under different model revisions, system prompts, token caps, tool versions, or request-family revisions can carry the same observation IDs and pass `CalibrationBundle`.

Before calibration results are used, require exact equality against a canonical population/execution manifest containing at least:

- cell and namespace/current qualification look;
- expected latent and render IDs, including renderer and visible-slice support;
- generator and difficulty-profile versions;
- runtime-profile fingerprint;
- worker/endpoint fingerprints; and
- request-family or prompt revision where it can differ by arm.

If this manifest is intentionally part of a later implementation tranche, `CalibrationBundle` should currently be described as a structural same-ID check, not as sufficient to make a Stage 1 gate valid. The manifest should then be added explicitly to the construction/qualification blockers in `conductor_log.md`.

### [P1] Make payoff-surface deserialization lossless and fail-closed

**Locations:**

- [`tasks/conductor/oracle.py:68-81`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/oracle.py#L68-L81)
- [`tasks/conductor/oracle.py:220-242`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/oracle.py#L220-L242)
- [`tasks/conductor/oracle.py:253-332`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/oracle.py#L253-L332)

`ValidatedSurface.from_json()` converts every persisted correctness value with `int(v)`. This silently maps malformed data into valid-looking binary observations:

```text
0.5  -> 0
1.9  -> 1
"1"  -> 1
True -> 1
```

This reopens the persisted `0.5` hazard that the binary-valued surface contract was designed to prevent—now by altering the observation rather than averaging it.

The deserializer also constructs its raw surface with a dictionary comprehension. Duplicate candidate entries are silently collapsed with last-write-wins behavior. Appending a second serialized entry for candidate `[0]` with different outcomes changes that candidate's accuracy without raising an error. This is particularly plausible in a resumed write-through artifact.

Assignment candidate `[false]` also aliases `(0,)` on this path because `_check_candidate_types` does not handle assignment candidates and `from_json()` bypasses `_check_assignment`.

Recommended resolution:

- Validate the exact top-level and entry schemas before constructing mappings.
- Require the exact expected number of candidate entries and reject duplicate canonical candidates.
- Preserve correctness values unchanged and let the binary validator reject invalid values—never coerce them.
- Apply the normal exact candidate-type validator for every kind, including assignments.
- Convert all malformed persistence inputs into `PayoffSurfaceError` rather than leaking raw exceptions.

### [P1] Derive B3 and B5 payloads from the instance's own registry

**Locations:**

- [`tasks/conductor/baselines.py:43-49`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/baselines.py#L43-L49)
- [`tasks/conductor/baselines.py:62-71`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/baselines.py#L62-L71)

The Conductor observation path now correctly removes the external registry argument. B3 visible-direct and B5 one-call request construction still accept an independent `InstanceRegistry`, checking neither payload equality nor instance identity.

A same-manifest registry containing an altered sentinel value produced:

```text
B3 foreign payload disclosed: True
B5 foreign payload disclosed: True
B5 host-side binding uses the foreign payload: True
```

This is load-bearing for B5 because oracle-versus-one-call is a cell-admission gate. A registry mis-wire can make the one-call control easier or harder and move the measured gap.

Construct the registry internally from `instance["public_manifest"]` and `instance["private_registry"]`, and apply the same identity validation used by the Conductor observation builder. If B4 remains deliberately lower-level, ensure its caller has an equivalent trace-level provenance assertion.

### [P2] Canonicalize and freeze directly constructed `ValidatedSurface` objects

**Locations:**

- [`tasks/conductor/oracle.py:135-218`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/oracle.py#L135-L218)

`ValidatedSurface.__post_init__` now rejects many forged objects, but it retains caller-owned `candidates`, `clusters`, `observations`, and nested `data` structures without defensive copying or freezing. `__deepcopy__` nevertheless returns `self` on the assumption that the object is immutable.

An exact probe constructed a valid surface from ordinary dictionaries, placed it in a `CalibrationBundle`, then mutated the original dictionary:

```text
selection before backing-dict mutation: (0,)
selection after backing-dict mutation:  (2,)
deepcopy(surface) is surface:            True
```

Duplicate entries in `clusters` are also accepted because support comparisons use sets, whereas `accuracy()` iterates the original tuple. Repeating cluster `c1` in `(c1, c1, c2)` can therefore double-weight it and change the selected endpoint. Candidate equality similarly allows `(False,)` to alias `(0,)` unless exact endpoint types are rechecked.

Either make direct construction inaccessible, or have `__post_init__`:

- validate exact candidate and cluster types;
- reject duplicate cluster entries;
- canonicalize ordering; and
- defensively reconstruct every nested collection using immutable tuples and mapping proxies.

Identity-deepcopy is correct only after every construction path establishes that immutability.

### [P2] Bind persisted estimand metadata to encoded identities

**Locations:**

- [`tasks/conductor/estimands.py:37-54`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/estimands.py#L37-L54)
- [`tasks/conductor/estimands.py:167-248`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/estimands.py#L167-L248)
- [`tasks/conductor/estimands.py:274-339`](https://github.com/kencoken/qwen-grpo/blob/61350652114beb23e456b2ef0cb39b64aa6cf532/tasks/conductor/estimands.py#L274-L339)

`WorkflowOutcome` validation now checks primitive types, the visibility enum, duplicate rows, and cluster-constant collision metadata. It does not parse the identities or require their encoded metadata to agree with the row.

A canonical observation ID that names cluster A and ends in `:visible`, filed under cluster B with `visibility_condition="private"`, is accepted into the private headline population and scores normally. The one-owner map only detects the same observation ID appearing under multiple clusters; it does not detect a single misfiled row.

`EdgeOutcome` has no equivalent total validation. A row with string values `"false"` for `eligible`, `override_applied`, and `downstream_path_succeeded` treats all three as true, producing eligibility and follow-through rates of `1.0`. A list-valued edge instead raises raw `TypeError` before a domain error.

Use a common persisted-row validator that:

- parses `cluster_id` and `observation_id`;
- requires the observation's latent ID to equal its cluster;
- requires encoded visibility to equal the row's visibility field where present;
- validates the edge as a two-string semantic-node tuple applicable to the cell;
- requires exact booleans; and
- requires gold/terminal values to be exact integers or `None`, excluding booleans.

## Lower-priority follow-ups

These should be resolved before their affected persistence paths become operational:

1. **`InterventionReport` round-trip:** it has `to_json()` but no validating `from_json()`. The test named as a round-trip checks only `json.dumps`. `InterventionReport(**json_obj)` leaves a list-valued edge and mutable dictionaries while `__deepcopy__` returns `self`.
2. **Manifest-validation totality:** `set(manifest)` runs before validating element types in both the normative IR and `InstanceRegistry` paths. A nested list or non-string handle can therefore produce raw `TypeError`; private observation construction also skips registry/manifest validation because it does not need payload disclosure.
3. **`PublicParams.from_json()` totality:** malformed schemas can expose raw `KeyError` or `TypeError`. Valid public parameters are now properly scalar, type-checked, and immutable, so this is a typed-boundary cleanup rather than a leakage issue.
4. **Bootstrap artifact wording:** cluster counts alone do not contain the per-cluster successes needed to reproduce the bootstrap. Persist raw paired rows or per-cluster sufficient statistics; the report can remain a derived summary.

## Confirmed improvements

The following changes were reviewed and found sound:

- A stale visibility mutation now disagrees with `render_instance_id` and is rejected by the canonical Conductor observation path.
- That path no longer accepts an independently supplied registry.
- Cluster and observation IDs are parsed and tied to the named cell.
- `CalibrationBundle` correctly establishes exact same-ID support across its assignment and control surfaces.
- Public-only feature extraction now has one source of truth; `feature_row`, `shallow_predict`, and `echo_predict` derive from `PublicParams`.
- Accepted `PublicParams` values are scalar and type-checked, initialization is one-shot, and identity-deepcopy is valid for those objects.
- Sensitivity primitive types and collision consistency are substantially better checked.
- The normative IR validator now rejects duplicate and malformed string handles on its ordinary path.
- The §1.9 full-sample estimator and paired-cluster bootstrap wording remain correct.
- T1's constructive congruence sampler is analytically correct and preserves the old ordered-support draw convention.

The exact fourteen previous probes are closed; the findings above arise from generalized persistence, phase-separation, and provenance probes.

## Verification

Independent verification was performed against exact head `61350652114beb23e456b2ef0cb39b64aa6cf532`:

```text
pytest -q -W error
359 passed in 1.60s

python -m tasks.conductor.agreement --cases 10000
16665/16665 node executions agree over exactly 10000 latent programs
```

The byte-stability generator wrote 58 hashes and produced no diff. The worktree remained clean.

The analytic T1 sampler was additionally compared against the original explicit enumeration over 500 independently seeded bands and RNG states:

```text
analytic_equivalence: 500/500
```

The pull request is mechanically mergeable. No GitHub Actions workflow runs or commit-status checks are currently reported for this head.

## Recommendation

The observation-identity, analytic-T1, public-feature, and primitive validation fixes should be retained.

Before Stage 0A sign-off:

1. separate construction selection from qualification evaluation using persisted frozen choices;
2. make payoff-surface persistence exact, duplicate-safe, and non-coercing;
3. bind B3/B5 payloads to their instance; and
4. make direct `ValidatedSurface` construction genuinely immutable or unavailable.

Before the construction screen or first qualification look, bind calibration artifacts to a canonical population and runtime manifest, and close the persisted estimand identity checks. Otherwise a clean same-ID bundle can still represent the wrong split, an incomplete/cherry-picked population, or arms run under different systems.
