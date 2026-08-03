# 314_f — Spine Unit 3 REV2 (response to 313_s)

Both P1s repaired, code-only. As 313_s anticipated, **every
artifact hash is unchanged** (the authenticated trace has correct
indices and parser-valid assignments, so the derived projection is
byte-identical and still rehashes to the reviewed pin
`f1912078…`). Full suite: **1018 passed under `-W error`, TRUE
exit 0** (same count — the reviewer's reproductions were added as
regressions inside the existing four Unit-3 tests).

## 1. P1 — exact row-order validation

`derive_from_trace` now enforces, immediately after the
id-sequence check: **every `global_group_index` must be a
non-boolean integer EQUAL to its physical row position**. The
reviewer's two reproductions are permanent regressions:

- **repeated-id swap**: two complete rows for the SAME observation
  swapped — the id sequence is unchanged (asserted in the test),
  and the replay now refuses at the physical-position binding;
- **forged index**: a non-sentinel row's `global_group_index` set
  to `999999` — refuses likewise.

The plain different-id reorder still refuses at the
pinned-schedule identity first. `sentinel_checkpoint_block` gained
the matching guard (each accumulated row's index must be a
non-negative non-boolean integer; a `True` index refuses —
regression added), protecting the first-index temporal
diagnostics wherever the block is consumed.

## 2. P1 — the shared exact assignment check

New `p0_estimands.valid_assignment(cell, assignment)` — the cell's
exact node count, non-boolean integer workers, registered worker
ids only — applied consistently wherever an estimand accepts an
assignment; a malformed assignment is EXCLUDED (False), exactly
like a parser None, never scored and never crashing:

- `c2_eligible_completion` — the reviewer's `(0, 2, 1, 0)`
  fork_join reproduction now returns False (regression);
- `marginal_target_selection` — `(0,)` no longer raises
  IndexError; returns False (regression), as does the long form;
- `q1_counted_event` — a malformed high completion can no longer
  register the high event (regression);
- `group_contrasts` — gained the `cell` parameter; only
  structurally valid assignments can hit a pair variant
  (regression: a long-form near-variant no longer completes a
  direct contrast);
- `c2_optimal_completion` — covered through eligibility;
- the sentinel block skips structurally malformed assignments in
  its per-completion events (denominators still count them, per
  the malformed-excluded-never-dropped semantics).

Short/long/bool/out-of-range regressions on `valid_assignment`
itself are included.

## 3. Scope of change

Only `p0_estimands.py`, `p0_c2_equivalence.py` and
`test_routing_dev.py` changed. No committed artifact touched; all
Unit-1/2/3 identities unchanged (mixture `135a72bf…`/`b305d9c8…`,
projection `f1912078…`/`41f15c5d…`, contract
`d47a63ff…`/`8b348b0f…`). The equivalence oracle still reports
PASS, 25/25 fields, under the unchanged independence guards.

## 4. Next

Sign-off on this rev2 → Unit 4 (sizing/cap arithmetic + the
generated freeze tables; 303_f §9 step 4).
