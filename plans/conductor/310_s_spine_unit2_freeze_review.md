## Verdict

Unit 2’s scientific values are correct, but I recommend one narrow repair pass before Unit 3.

### P1 — `population_of()` bypasses the pinned-mixture boundary

`tasks/routing/p0_schedule.py:79` accepts any caller-provided mixture dictionary and trusts `class_assignment` without validating its hash or contract binding.

I changed one observation from `bridge` to `q2_composite`, retained the stale `record_sha256`, and `population_of()` returned the forged population. That could contaminate Unit 3 denominators and population-sensitive estimands.

Have it load the authenticated mixture internally, or validate the supplied object completely. Add a one-field population-substitution regression.

### P1 — C2-derived contract values are not mechanically cross-checked

`tasks/routing/p0_contract.py:83–126` correctly records Q1 `13/34/13`, Q2 `8/152`, `0/15`, `73/108`, target workers, 157 rows and 39 epochs—but these are literals. Construction loads the mixture only; it never checks them against the double-bound compatibility projection.

Consequently, the contract could pin projection A while carrying different baseline or sizing values B. Existing tests compare some values against matching literals rather than the authenticated projection.

Add one validation step during construction/freezing which compares the contract with `load_projection()` and the pinned mixture. This need not change the contract hash because all current values already agree.

### P2 — Repeated rows share mutable prompts

`tasks/routing/p0_schedule.py:147` shallow-copies cached rows. Duplicate observations therefore share the same nested `prompt` list; mutating one occurrence changes another. Dataset construction probably copies these, so this is nonblocking, but a deep copy is a cheap precaution.

I would not authenticate every pure schedule helper against `CONTRACT_SHA256`: variant contracts are deliberately supported for tests. Instead, retain the requirement that the eventual real consumer loads the reviewed contract through `load_p0_science_contract()`.

Positive verification:

- All current contract values and provenance pins are correct.
- All 785 generated trainer rows exactly equal the previous C2 preparation path.
- Legacy-builder disablement and surface-lock enforcement work.
- Contract semantic hash: `d47a63ff…`
- Contract file hash: `8b348b0f…`
- Full suite: **1,013 passed** under warnings-as-errors.
- Worktree and diff checks are clean.

After the two P1 repairs—and preferably the small aliasing fix—Unit 2 should be ready for sign-off.