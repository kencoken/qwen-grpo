# Stage 0A PR review — `65dd32a`

**Pull request:** [kencoken/qwen-grpo#2](https://github.com/kencoken/qwen-grpo/pull/2)  
**Base:** `conductor@25c22ac4a4d7ef66d7ccd04fc178047279b45f4d`  
**Head:** `conductor_stage_0a@65dd32aee3a8c371923c47e0fc233bf4d454a8df`  
**Review scope:** closure of the findings reported against `95d99d8`, followed by a broader scientific-correctness and regression review against the frozen rev6 plan and rev8/v0.8 cell specification.

## Verdict

I recommend **Stage 0A sign-off** after the small remaining changes below.

The previously result-affecting findings are closed in the supported experimental workflow. I found no remaining issue that plausibly changes an estimand, gate population, phase boundary, identity, private-information boundary, or reproducible generated artifact.

The three remaining observations are local hardening and conformance improvements. They are worth resolving before Stage 1 relies on these interfaces, but none currently permits silent contamination through the normative Stage 0A workflow.

## Remaining changes

### [P3] Complete the latent-identity check in `draw_intervention()`

**Location:** `tasks/conductor/program.py:523-540`

The original, result-affecting problem is fixed: `draw_intervention()` now validates the supplied difficulty profile and rejects a profile whose digest differs from the latent's recorded `difficulty_profile_version`.

One subsidiary part of the earlier recommendation remains. The function still accepts:

- a latent whose `generator_version` is stale; and
- an otherwise valid latent whose `latent_program_id` has been replaced with the ID of another latent.

In a focused probe, changing only the latent ID changed the deterministic replacement from `45` to `99` without rejection.

This is not a Stage 0A scientific blocker because the frozen workflow persists rendered instances rather than raw latent dictionaries. The normative `validate_instance()` path regenerates the instance under the current generator and compares the complete regenerated record, while ordinary generation creates the version, ID, seed and contents together. Reaching the probe therefore requires bypassing the normative persisted-instance path and mutating an internal data object.

Nevertheless, the inexpensive hardening should be added before Stage 1 consumes this function:

1. require `latent["generator_version"] == GENERATOR_VERSION`; and
2. recompute and compare the canonical latent ID and seed from the latent's cell, namespace, index, generator version and difficulty-profile version.

Add focused tests for a stale generator version and a valid-but-different latent ID. This should remain a simple local validator; it does not require a new proof-marker type.

### [P3] Canonicalize redundant `InterventionReport` fields after validation

**Location:** `tasks/conductor/estimands.py:237-269`

`InterventionReport.__post_init__()` correctly recomputes all derived values from identity plus per-cluster sufficient statistics. Float-valued fields are compared with a `1e-9` tolerance, however, and the object then retains the caller-supplied values rather than the recomputed values.

For example, changing both occurrences of `base_accuracy` from `1.0` to `1.0000000005` in a persisted report is accepted, retained and emitted again by `to_json()`. The revived report is consequently not equal to the canonical report and can contain an accuracy slightly above one.

The numerical deviation is too small and too contrived to threaten the current experiment, but the behavior conflicts with the stated rule that the sufficient statistics are the source of truth.

After validating the redundant persisted values, overwrite every derived field with the recomputed value. Alternatively, exact comparison is reasonable because a Python JSON round-trip preserves these generated floats. Add a round-trip test which perturbs a redundant field within the current tolerance and verifies either rejection or canonicalization.

### [P3] Make `validate_instance()` consistently raise `LoadError`

**Location:** `tasks/conductor/program.py:1057-1080`

The frozen specification and function documentation say that a load-time mismatch produces `LoadError`. Malformed persisted inputs currently leak other exception types:

- missing fields produce `KeyError`;
- malformed identities or nonnumeric indices produce `ValueError`;
- invalid renderer values produce `ValueError`; and
- well-shaped but unknown generation identities can produce `GenerationError`.

All these cases fail closed, so no invalid instance is admitted and no scientific result is contaminated. The behavior is nevertheless awkward for the resumable Stage 1 loader and does not exactly implement the documented public boundary.

Validate the exact record shape and parse the canonical identity before regeneration, then translate artifact-shape, renderer and regeneration failures into `LoadError`. Add a small parameterized test covering the cases above.

## Closure of the previous findings

The substantive findings reported against `95d99d8` are correctly closed:

1. **Impossible sufficient statistics are rejected.** The implementation now enforces `n_total >= 1`, `corrupted + counterfactual <= followed`, and `followed_successes == counterfactual`, in addition to the ordinary per-count bounds.
2. **Executor-state coherence is enforced.** Mutated-terminal availability must agree with downstream-path success, and a successful base terminal cannot be marked ineligible.
3. **Frozen selection is verified at consumption.** `VerifiedFrozenSelections` has been removed. Each evaluation accepts the construction bundle and re-derives the construction argmax in the same call.
4. **Construction/qualification separation is preserved.** Selection primitives reject non-construction surfaces, while qualification evaluation can only score the construction-frozen candidates.
5. **Difficulty-profile mis-wiring is rejected.** A different valid profile can no longer silently change an intervention replacement or counterfactual target.
6. **All report construction paths validate identically.** Direct construction, `dataclasses.replace()` and `from_json()` all pass through the same sufficient-statistic derivation and consistency checks.
7. **Malformed numeric values fail closed.** Non-finite values, float or boolean counts, and inconsistent mappings are rejected.
8. **Public identifier validation is totalized.** The previously demonstrated unhashable-identifier cases now raise domain errors.
9. **The hot-path optimization is behavior-preserving.** Public intervention drawing validates the profile; generation uses the unchecked internal helper only after validating the profile once at entry.

I did not treat subclass-based overrides of verification methods as a finding. Such a bypass requires executing arbitrary in-process Python code and is not reachable by deserializing the supported artifacts. Trying to make ordinary Python objects cryptographically unforgeable would recreate the proof-marker complexity that the latest design correctly removed.

## Broader scientific review

No regression was found in the experiment's load-bearing semantics:

- Stage 1 intervention estimates remain full-sample eligible-set estimates, with equal-cluster estimates recorded separately.
- Every intervention quantity uses the same eligible denominator.
- Clusters with zero eligible observations remain in the population needed for the cluster bootstrap.
- Reports remain bound to one cell, split and directed edge.
- Frozen oracle, best-fixed, one-call and two-call selections remain construction-only.
- Qualification evaluation does not expose an argmax over qualification outcomes.
- Surface candidates remain observation-paired and cell/split-bound.
- The public/private rendering and worker-request boundaries are unchanged.
- Authoritative gate reporting remains fail-closed until the Stage 0B/1A population and execution-provenance artifacts exist.

The remaining construction-screen blockers recorded in `conductor_log.md`—the D16 review, fitted B1 models, real chat-template bytes, the population/execution manifest, and the CE1 bootstrap-degeneracy decision—are correctly left for their designated phases rather than being represented as completed Stage 0A functionality.

## Independent verification

Verification was performed against exact head `65dd32aee3a8c371923c47e0fc233bf4d454a8df`:

```text
454 passed in 1.68s
```

Warnings were treated as errors.

Reference/tool agreement:

```text
agreement: 16665/16665 node executions agree over 10000 latent programs
```

The run exercised all 13 declared operator-by-cell strata and covered exactly 10,000 latent programs.

The byte-stability generator wrote 58 request hashes and produced no diff. The verification worktree remained clean. GitHub reports the PR as cleanly mergeable; no GitHub check runs are currently configured for the head commit, so the independent Linux run is the operative test evidence.

## Recommended close-out for Stage 0A

After implementing the three local changes above:

1. Run the targeted new tests plus the complete suite with warnings as errors.
2. Re-run the 10,000-latent reference/tool agreement check.
3. Regenerate the byte-stability fixture and require no diff unless an intentional identity-affecting change was made.
4. Confirm the PR worktree and changed-lines whitespace check are clean.
5. Add one concise final close-out entry to `conductor_log.md`, recording the final commit and acceptance results.
6. Merge and treat Stage 0A as closed.

Do **not** follow these changes with another unrestricted adversarial audit of internal Python objects. Any further Stage 0A review should be limited to the final changed lines and the frozen acceptance commands. The next scientifically valuable review should happen against real Stage 0B/1 execution: worker/runtime fingerprints, real chat-template request bytes, cache keys, trace persistence, execution provenance and calibration integration.

After Stage 0A closes, changes to frozen generation, rendering, prompt, parser or tool behavior should be handled explicitly as versioned experiment changes. Once qualification data exists, such a change must retire the affected qualification set rather than being folded into an informal Stage 0A cleanup.
