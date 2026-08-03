## Verdict

Unit 1’s frozen artifacts contain the correct scientific values, but the unit is not ready for signoff. Four narrow repairs are required; no architectural redesign is needed.

### P1 — Replay verification accepts an incomplete archive

In `tasks/routing/p0_replay.py:167–172`, non-core inventory files are checked only if they exist. I deleted the identity/environment manifests, checkpoint maps, and preflight from a copied archive; `verify_c2_replay_source()` still returned `PASS`.

It also trusts identity/environment values asserted by `sample_record.json` without validating the actual manifests.

Required repair:

- Require every closeout-inventory member to exist and match its hash.
- Prefer exact file-set equality.
- Validate the identity-manifest self-hash and its binding to the reviewed/sample-record anchor.
- Validate the environment manifest and attested-environment cross-link.
- Run this complete check before any extraction or replay.

### P1 — Projection generation and loading are not authenticated boundaries

`extract_projection()` reads its source without calling `verify_c2_replay_source()`, and `freeze_projection()` calls it directly. A modified report therefore produces a modified projection while still stamping the frozen source hashes into its provenance.

Separately, `load_projection()` accepts any projection with a recomputed self-hash. It does not require the reviewed file hash `e30a6cb9…` or frozen projection hash `6a913547…`.

Required repair:

- Authenticate the complete source bundle inside the freeze/extraction boundary.
- Require an externally reviewed projection file hash and self-hash at loading.
- Add regressions for a tampered source report and a coherently rewritten projection.

The chronology itself is correct: no independent Unit-3 evaluator exists yet.

### P1 — The schema remains stringly typed

The central reason for this spine was to stop scientific meaning living in unconstrained strings, but the current schema still does that:

- `Q1Rule` cannot encode valid-only, same-group, reward-1/full-family-correct, and reward-0.5/strictly-lower semantics.
- `Q2Rule.conditional_estimand` is prose, while baselines such as `"8/152"` are strings.
- Eligibility and malformed-completion treatment are not represented structurally.
- `SizingRule` represents the cap/branch semantics as prose strings.
- `RequiredDiagnostics` is only a tuple of labels; the test exemplar includes merely `sentinel_first_occurrences`, omitting the signed sentinel counts, denominators and checkpoint/evaluation trajectories.
- The loader checks field names and container shapes but not primitive types or scientific invariants. I confirmed that a contract with `True` where an integer is expected authenticates and loads; non-finite floats are also possible.

Required repair:

- Use small closed rule identifiers plus typed operative fields.
- Represent conditional baselines as numeric numerator/denominator records.
- Add a closed sentinel diagnostic specification covering every signed field.
- Validate exact cell/direction sets, positive non-boolean integers, finite numbers, rule IDs, uniqueness and hash formats.
- Run validation from direct construction and loading; use `allow_nan=False`.
- Add the reviewed C2 identity/environment anchors to `InputPins`.

This should remain a small set of frozen dataclasses, not a framework.

### P1 — Exact mapping parity is absent from the projection

The signed compatibility list includes exact class assignments, multiplicities and effective population mapping. The projection contains only aggregate population draws and `mixture_record_sha256`; those maps exist in the separate mixture artifact but are not part of the comparison projection.

Either:

- add the exact maps—or canonical hashes plus sentinel override—to the projection; or
- explicitly define the oracle as the joined mixture-plus-report projection and compare those mappings mechanically.

The later population-substitution sensitivity test must alter this comparison.

### P2 — The mixture is not yet double-bound in code

`load_pinned_mixture()` enforces the semantic record hash but not the reviewed file hash `b305d9c8…`. Reformatting the JSON to different bytes still loads successfully. The file hash currently exists only in Markdown.

Enforce both hashes at the consuming boundary. The projection should receive the same treatment.

## Positive verification

- Both committed file hashes and self-hashes reproduce.
- The pinned mixture equals a fresh legacy B2 reconstruction.
- The projection’s Q1, Q2, sentinel, sizing, variance, validity and authorization values are correct.
- No new outcome-driven choice was introduced.
- Full suite: **1,011 passed** under warnings-as-errors.
- Worktree and diff checks are clean.

Repair these boundaries, regenerate the projection identities, and add the targeted regressions. A narrow changed-lines review should then be sufficient.