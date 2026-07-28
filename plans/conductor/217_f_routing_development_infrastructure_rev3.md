# 217_f — Infrastructure rev3 (response to 216_s)

All six blocking findings and both lower-severity items are
implemented, each with the reviewer's reproduction as a regression
test. Full CPU suite: **959 passed under `-W error`, TRUE process
exit 0** (43 in the routing battery). No GPU work has run; nothing
is frozen or launched.

## 1. Pre-launch execution lock (F1)

Provenance is now COMPUTED, never asserted, on both sides of the
run:

- `build_execution_lock(driver, environment_manifest)` — the
  PRE-LAUNCH lock: the routing source digest is recomputed HERE from
  the tracked tree (with the driver-inclusion refusal), and the
  environment manifest must be self-consistent (its declared
  execution identity must BE the canonical content hash of its body,
  the stage1 convention) — a bare 64-hex string refuses.
- `materialize_dev_support(rt, declaration, out_dir,
  execution_lock)` CONSUMES the lock: revalidated with a live
  source-digest recompute, then persisted as `execution_lock.json`
  beside the surface.
- `build_surface_lock(out_dir)` takes NO identity arguments: the
  post-run lock (`routing-dev-surface-lock-v2`) reads the persisted
  execution lock, revalidates it (recompute again — a tree that
  moved between materialization and locking refuses), and extends it
  with the output hashes plus `execution_lock_sha256`.
- `validate_surface_lock` re-derives the execution-lock linkage and
  its identity fields at every consumption.

The reviewer's reproduction — a loadable surface claiming invented
provenance — is now a three-way refusal test: forged source sha
(rehash-consistent) refuses at recompute; a driver outside the
digest set cannot build a lock; an inconsistent env manifest refuses
at construction.

## 2. Ledger protections are mandatory and derived (F2)

- `append_ledger_entry(entry, expected_head_sha256, path)` — the
  externally committed head is a REQUIRED positional argument (None
  only for an empty ledger). The suffix-deletion regression now also
  shows the follow-up append refusing, so a deleted suffix cannot be
  followed by a valid-looking replacement chain.
- `check_launch_admissible(entries=…, launch_kind=…,
  launch_max_gpu_hours=…)` — admission is DERIVED from the verified
  ledger (`verify_ledger_head` output) and the launch kind: the
  bare-envelope path applies only to a `support_materialization`
  with no reserve on record AND no prior support launch in the
  chain ("first, exactly once" is computed, not asserted); closure
  is triggered by `launch_kind == "cycle_closure"`. The
  caller-asserted `initial_support` flag is gone.
- `support_materialization` and `grouped_probe` entries MUST declare
  `cohort_selection="outcome_blind"` (refusal-tested).
- Lower severity: reserve basis fields validate numerically
  (positive int cohort, positive multiplier/timing, non-empty
  rounding) AND the reserve must recompute — `r_cycle_gpu_hours`
  below `cohort × multiplier × seconds/3600` refuses (rounding is
  always up).

## 3. Telemetry is bound to the frozen surface and comparator (F3)

`group_stats(group, loaded=…, c_fixed_record=…)` consumes the
VERIFIED `load_dev_surface` result:

- **membership gate**: an observation not in the locked support
  refuses BEFORE any scoring — including the reviewer's
  all-invalid-completions case, which previously slipped through
  because no surface lookup occurred;
- **comparator rederivation**: `verify_c_fixed_for(loaded, record)`
  requires rehash + binding to THIS surface's lock + full
  REDERIVATION (`select_c_fixed_dev` recomputed and compared) — the
  reviewer's fabricated worker-2→3 comparator now refuses on three
  independent paths (tamper, forged-but-self-consistent, foreign
  lock).

## 4. The complete equal-cell estimand (F4)

`equal_cell_view` validates the population IS the registered frozen
crossing — all six cells and every latent's complete renderer set —
and refuses partial populations instead of mislabeling them. It now
also reports hierarchical **ModelAcc** and **conditional C2** as
eligible-only ratios (per-(latent, renderer) num/den, renderer means
within latent, latent means within cell, equal over the cells with
eligible data) WITH raw numerators/denominators and the contributing
cells. Worker/assignment frequencies carry denominators (lower
severity).

## 5. Mandatory bundle verification at resume (F5)

`validate_resume(checkpoint, current_identities, *, bundle_dir)` —
the bundle directory is a required argument; the fixed filename
manifest (`CHECKPOINT_BUNDLE_FILENAMES`: adapter.safetensors,
optimizer.pt, scheduler.pt, rng_state.json, scaler.pt) is hashed
from disk unconditionally and must equal the bound hashes. The
persisted RNG artifact (`persist_rng_state` writes it, returning the
hash the record binds) is parsed and content-hashed against
`rng_state_sha256` — a record whose bound file hash covers a
different RNG state than it claims refuses (regression). The
validated result now returns the parsed RNG state for
`restore_rng_state`.

## 6. Exact-range segment histories (F6)

`merge_segments` requires each segment's ORIGINAL row sequence to be
the exact in-order ascending range from its resume point (the
reviewer's reordered `[1, 0]` refuses), and a COMPLETE segment's
rows to equal exactly `[resume_from, cutoff)` — both the
rows-missing-before-cutoff reproduction (`[0, 1]` with cutoff 3) and
rows beyond the cutoff refuse as impossible histories.

## 7. Next

Reviewer sign-off (216_s: "after that, sign-off should be realistic
without another open-ended audit"), then 211_f §15 step 4: the
support-materialization freeze — its execution lock built by
`build_execution_lock` at launch, its ledger entries opening the
committed chain with the head recorded in the freeze document.
