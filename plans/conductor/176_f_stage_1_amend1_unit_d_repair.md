# 176_f — Unit-D repair (response to 175_s)

All three P1 lock-readiness blockers are implemented and all five
documentation corrections are incorporated into the reissued
successor **177_f** (rev2 — 174_f stands at reviewed bytes,
superseded forward per the 141_f→144_f discipline). Full CPU suite:
**899 passed under `-W error`, TRUE exit 0** (894 + 5 new probes).
No formal statistical run started; both amended run roots remain
absent.

## 1. The frozen deadline literal controls execution (finding 1)

`MEASURED_SECONDS_PER_OUTER_X1E6 = 951_551` and
`D_SCENARIO_DEADLINE_SECONDS = 19_031` are now SOURCE literals in
`stage1_tranche.py`; `run_amend1_tranche` uses the frozen deadline
for every D1–D5 scenario. The live benchmark is demoted to a
persisted sanity check: `benchmark_sanity_check` refuses a
measurement outside the INCLUSIVE band [literal/4, literal×4] as an
infrastructure abort. The persisted `benchmark.json` now records the
live measurement, the frozen literal, and the frozen deadline. Tests
pin the literal values and both inclusive boundaries.

## 2. Lock/bundle provenance is derived, never caller-typed (finding 2)

`build_lock_bundle(prereg_path, lock_record_path)` is the ONE formal
lock-time constructor. It derives: the preregistration hash from the
reviewed file's bytes; the lock-record hash from the committed lock
record's bytes; `git_commit` from clean HEAD; `source_digest` from
`stage1_source_digest()` recomputed at call time; the environment
manifest by building and validating it fresh; and the registry trio
from the AUTHORITATIVE support ids (`build_smoke_rows`), verified
canonical. Its signature admits no caller-typed provenance (asserted
by test). Additionally, every consumer that holds both the bundle
and a validated environment manifest — the tranche runner, the
replay driver, the aggregate, and the finalizer (per root) — now
cross-checks `git_commit` and `source_digest` against the manifest
(`check_bundle_env_provenance`; mismatches refuse, tested).

The circular §10 wording is corrected in 177_f §10 to the review's
sequence: (1) the lock record pins the reviewed preregistration and
executable state; (2) the lock record is committed; (3) the formal
constructor derives the lock-record byte hash and the clean HEAD
into the bundle at run time (the bundle exists only in the run
roots); (4) nothing is written back into the lock record.

## 3. Reproducible execution and evidence path (finding 3)

New tracked module `tasks/conductor/stage1_amend1_run.py` (now part
of the successor source digest):

- `formal_context()` — bundle/registry/env via `build_lock_bundle`,
  locating the reviewed preregistration (frozen path constant) and
  the committed lock record (unique-glob discovery: exactly one
  `plans/conductor/*_f_stage_1_amend1_lock.md` must exist);
- CLI: `uv run python -m tasks.conductor.stage1_amend1_run
  {probes|tranche|replay|finalize|archive}` — the §11 commands are
  now literally executable from the lock commit with no undefined
  objects;
- `archive_evidence()` — the concrete success/abort archive command:
  byte-copies BOTH run roots into
  `plans/conductor/evidence/stage1_pre_ce1_amend1_{first12(bundle_sha256)}/`
  (`validation/`, `replay/` subtrees), writes the byte/length/SHA-256
  manifest with the bundle/prereg/lock/commit identity block and run
  statuses, then verifies every archived byte against both the run
  roots and the manifest; refuses a pre-existing destination and any
  bundle self-hash or cross-root bundle disagreement (all tested).
  Aborted runs archive their partial file sets the same way;
- `run_prelock_probes()` — the COMMITTED §5.4 construction recipe
  (fixed seed 20260725, 120 cases, both schedules; C projection;
  10,000-inner worst-case benchmark; auditable worst-case tranche
  projection), so the 173_f probe record regenerates from the
  commit.

Fresh output of the committed recipe at full defaults (verbatim):

```json
{
 "probe_seed": 20260725,
 "reference_agreement": {"cases_checked": 120,
                         "inversions_checked": 120},
 "c_projection": {"seconds_per_path_trial": 0.00018814406047264735,
                  "projected_full_c_minutes": 1.5051524837811785,
                  "budget_minutes": 30, "within_budget": true},
 "worst_case_seconds_per_outer": 0.9437688527512365,
 "worst_case_x1e6": 943768,
 "frozen_literal_x1e6": 951551,
 "frozen_d_scenario_deadline_seconds": 19031,
 "measured_within_sanity_band": true,
 "d15_worst_case_hours": 6.55,
 "cpu_tranche_worst_case_bound_hours": 8.05,
 "within_12h": true,
 "c_within_30min": true
}
```

## 4. Documentation corrections (incorporated in 177_f; record-only for 173_f/174_f)

1. **8** gated A-position cells (4 scenarios × delta 0.15 × sigmas
   {0.25, 0.50}) plus **4** gated router cells (2 mixtures × effect
   0.10 × sigmas {0.25, 0.50}) — the v1 "12 gated cells" was their
   union; 174_f §8's "12 gated position cells" was wrong.
2. The ≈0.95 C-power prediction comes from 159_f's approximate
   amended-score calculation, NOT the v1 artifact (the v1
   row-dispersed envelope result was 0/10,000 — the failure the
   amendment exists to fix).
3. "Conservative by construction" softened: the design uses
   Bonferroni splits and t/CP/Hoeffding bounds INTENDED to be
   conservative, but not every component carries a finite-sample
   guarantee — establishing calibration is exactly what D6–D8 test.
4. Persistence wording fixed: qualification records carry
   renderer-level J/K via `qualification_look_report`; D6–D8
   ARTIFACTS persist integer scenario counts plus the eight
   branch-telemetry rows (per-look §4.6-style records are evaluated
   in memory, not persisted).
5. The unsupported "v1-measured relative scenario weights" is
   replaced by the auditable worst-case bound: five D1–D5 scenarios
   at the measured worst path = 5 × 0.9438 × 5,000 s ≈ **6.55 h**;
   adding the frozen 30-minute A/C/D6–D8 budgets bounds the CPU
   tranche at ≈ **8.05 h ≤ 12 h** (fresh-run numbers above; at the
   frozen literal: 5 × 0.951551 × 5,000 ≈ 6.61 h, bound ≈ 8.11 h).

## 5. Regenerated literals and changed lines

Adding the run module and the frozen literal changed the successor
source digest:
`d73cde71682fb87222c33e889b2cf77730ad338360a5226fea5919457296c461`
(pinned in 177_f §1; the registry, support, scenario-grid,
request-contract, artifact-schema and file-set digests are
UNCHANGED — no schema, grid, seed or contract moved). Changed lines
this repair: the two frozen literals + sanity check + runner wiring
(`stage1_tranche.py`), `check_bundle_env_provenance` +
`build_lock_bundle` (`stage1_amend1.py`), one cross-check line in
the replay driver, the new run module, and tests (5 new, fixtures
aligned to the provenance cross-check). Ready for the changed-lines
review, then lock.
