# 261_f — Unit A: support-extension implementation + FREEZE (for review)

The signed 260_f design's Unit A, implemented as
`tasks/routing/extension_run.py` and frozen here BEFORE the GPU run.
`prepare_extension_launch` ran on the GPU host at reviewed bytes
(@742b97d); the prelaunch records are committed byte-for-byte under
`plans/conductor/routing_dev_extension_prelaunch/`. Full CPU suite:
**991 passed under `-W error`, TRUE exit 0** (9 new in the extension
battery).

## 1. What is implemented (the 259_s review list)

- **New extension runner** — a self-contained `support_extension`
  ledger launch kind with its OWN closed-schema launch manifest
  (`routing-dev-extension-launch-v1`): no first-probe rule, no
  comparator; binds the original Step-4 lock, the exact planned node
  counts, and the frozen budget. The ledger admission branch
  requires the manifest, its hash in the entry freeze, budget
  equality, and the manifest's own scientific-design identity
  (declaration/namespace/worker/request/cache/prefix/cap/original
  lock). The materializer gained validator/kind/manifest-key hooks
  (support defaults unchanged — the Step-4 path is byte-identical)
  and the persisted-launch loader dispatches on manifest kind, so
  extension surfaces lock and load through the SAME v3 surface-lock
  and fail-closed loader machinery.
- **Overlap gate BEFORE lock acceptance** (257_s B3):
  `verify_overlap_equality` — every original observation's payoff
  AND terminal value must be reproduced exactly (assignment by
  assignment, duplicates refused) between materialization and
  `build_surface_lock`. A divergent run ABORTS with measured cost
  and a content-hashed partial inventory, and NO lock is written
  (lifecycle regression proves it).
- **Immutable comparator** (257_s B3 / 259_s): `immutable_comparator`
  verifies the ORIGINAL `c_fixed_dev` record against the ORIGINAL
  Step-4 lock through the full 216_s F3 rederivation (a tampered or
  foreign record refuses; a call rooted in the extension surface
  refuses), then derives a ScaleLift-only consumer record with
  `reselected: false`. `select_c_fixed_dev` is never invoked on the
  extension surface — the end-to-end regression spies every
  rederivation call and requires the ORIGINAL lock on each.
- **Total selector** (260_f §2 + 258_f §4.1): per-observation
  direction from `derive_pair_entry` surface geometry; every latent
  globally assigned to AT MOST ONE direction bucket (majority of
  favoured renderings; tie → the direction of the favoured rendering
  first in frozen renderer order); renderer-induced reversals
  recorded as DIAGNOSTICS; buckets carry ALL qualifying latents in
  ascending index order (unselected payoff-distinct rows can only be
  Direction or Screened — never Bridge); dispositions per
  (cell × direction) at the frozen 3/2/<2 thresholds plus
  renderer-strata and non-`goal_first` constraints; the eligible
  common-cell set for Q3 PREDECLARED (both directions at ≥2
  latents); subtype/public-factor yield disclosure
  (cell / renderer / cell+renderer strata); and
  `verify_extension_selection` rederives the record byte-exactly
  from the locked surface (a curated bucket refuses even when
  rehashed).
- **Deadline enforcement**: the 1.0 GPU-h ceiling is enforced per
  observation inside the materialization loop, before any worker
  executes (regression: a past deadline refuses with zero worker
  calls and no payoffs written).
- **Exact cost derivation** (259_s): from the ledger-recorded Step-4
  basis (4,824 planned node executions, 0.0732 GPU-h): genuinely new
  indices 6–47 = **33,768 node executions ⇒ 0.5124 GPU-h
  expected**; full-regeneration bound = **38,592 ⇒ 0.5856 GPU-h**.
  Both counts rederive from the committed declaration and are bound
  in the manifest; the manifest refuses if expected cost exceeds the
  ceiling. (These equal the 257_s feasibility figures exactly.)

## 2. The 259_s test obligations, discharged

1. Overlap validation BEFORE locking:
   `test_extension_overlap_divergence_aborts_before_lock` (a healthy
   worker 3 diverging from the sabotaged original aborts at the gate;
   no `surface_lock.json` exists; the aborted closeout's partial
   inventory verifies).
2. Comparator selection unreachable:
   `test_extension_end_to_end` (spied rederivations all carry the
   original lock) + `test_extension_comparator_is_immutable`.
3. Original comparator verified against the ORIGINAL lock only:
   same tests (extension-rooted call refuses; tampered record
   refuses at the rehash).
4. Deadline enforced: `test_extension_deadline_enforced`.

Plus: admission-boundary negatives (manifest required, hash bound,
budget equality, outcome-blind declaration), overlap
payoff/terminal/missing-row refusals, selection tampering, and the
full end-to-end lifecycle on a prefix-7 extension of the prefix-6
fixture surface with reserve-present admission.

## 3. Frozen identities (FULL — the launch arguments)

- Config:
  `22de3e4e72c41c250b0298867956336552e239f7c6aa8a8ce5d790346dacdeef`
- Freeze:
  `03f740af3ced6dd7dfccef558b024de23f210e0717560a13b551cbeb435a993e`
- Extension-launch manifest (prepared at reviewed bytes):
  `70bfb448f11d958d7e46fa54a0903389dd95b4454d7ec91672e21715b62b7fcb`
- Declaration (864 observations, six-cell prefix 0–47):
  `dba1ccd511d53fb00391d13f459a9f5d03db5b1f91d9c5f4b0460d703627e260`
- Scientific design:
  `951e16b9b04fe83ca9f52dba1d60543b99985a293f3c43746e1607897cdd9bdd`
- Environment manifest:
  `6f3a898d783c725dbbaa77db647cbcf99819a439833beb333bda98da8d092fdc`
- Original Step-4 surface lock (overlap target, comparator root):
  `61c4e85a53683c9e2dbcbf15f60794935a76a86d979a69412a97f44ea9f2562b`
- Ledger head (= frozen lineage parent, anchor-enforced):
  `88c037a188c6c8f5aca21e7690ea288b76dd1f64eb53f6fc2647196d32cb0eeb`

Launch: `execute_extension(run_dir="runs/routing-dev/support-ext-v1",
expected_manifest_sha256=…70bfb448, expected_head_sha256=…88c037a1)`.
Budget 1.0 GPU-h (expected ≈0.51 with 0–5 as slw-cache hits);
`outcome_informed = true`, `cohort_selection = outcome_blind` (the
prefix is blind; the SELECTOR over it is outcome-conditioned and
disclosed). Envelope: 59.3539 GPU-h remaining, reserve 5.0
provisional intact — admissible (59.35 > 1.0 + 5.0).

## 4. Design bindings carried (260_f)

`c_fixed_dev` (worker 2) immutable; only ScaleLift consumes it —
C2/ModelAcc are surface-defined. Direction-disjoint latent buckets
(rev2 dual-direction rule superseded). Dispositions and the
predeclared Q3 common-cell set are Unit-A OUTPUTS consumed by the
Unit-B/C freezes; Bridge/Anchor construction, renderer-balanced
multiplicities, and the Q1 counted event live in the Unit-B freeze
(not here). Hamming-one neighbour preference remains DIAGNOSTIC
unless the Unit-B/C freeze makes it mandatory (the sign-off
clarification); the required Q1 condition is the family-correctness
difference.

## 5. Next

Reviewer pass on this freeze → GPU run `execute_extension` with the
§3 hashes → closeout + selection/disposition review (direction
yields disclosed by subtype; dropped strata recorded) → Unit-B
mixture freeze on the extension surface.
