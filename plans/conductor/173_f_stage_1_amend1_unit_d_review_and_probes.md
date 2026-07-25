# 173_f — Unit D part 1: changed-lines review, verification battery, §5.4 probes

Unit D of 158_s §10, first half: the review of every change against
the amendment, the pre-lock verification battery, and the complete
§5.4 probe suite. The final placeholder-free successor is issued
alongside as 174_f; the separate lock record follows sign-off of that
document (nothing statistical runs before the lock).

## 1. Changed-lines review (159_f @e9b09db → 172_f @9e54b6e)

Eight commits (160_f, 162_f, 164_f, 165_f, 167_f, 168_f, 170_f,
172_f), 15 files, ~3,800 insertions / ~600 deletions. Every
production diff was re-read this session against 158_s and the six
review rounds (161_s, 163_s, 166_s, 169_s, 171_s):

- `program.py` / `stage1.py` — exactly the §5.1 fork amendment:
  `FORK_LOOK_SCHEDULE = (100, 500)` and the qualification
  `fork_join` cap 200→500; two looks retained, so the 0.05/2 fork
  tail alpha is unchanged. No other constant moved.
- `stage1_manifest.py` — env manifest carries and REQUIRES
  numpy/scipy (161_s/163_s); nothing else changed.
- `stage1_validation.py` — `seed_override` threads registered
  fresh-domain seeds into the A simulators (default derivation
  unchanged for probes); `COVERAGE_INNER_REPLICATES` and both
  agreement constants deleted; `benchmark_worst_case` reissued as
  the §5.4 item-3 probe at 10,000 inner. The A/router/C-envelope
  statistics themselves are untouched.
- `stage1_amend1.py` (new) — the identity layer as reviewed through
  161_s/163_s/169_s/171_s: tags, split seed domains (DB domain
  reproduces v1 `scenario_seed` exactly — asserted), 49,342-entry
  finalized registry + `verify_registry_canonical`, execution
  bundle with derived-or-pinned provenance, atomic root claim,
  pinned v1 evidence verifier, persistence contract constants and
  row schemas (C_marginal identities strengthened per 171_s),
  `verify_run_file_set`.
- `stage1_persistence.py` (new) — the §4 statistic exactly as
  frozen: float64 sufficient-statistic order, 64-eps refuse-vs-
  clamp (scalar rule at the gate; scan-variant magnitude set in
  `_membership`), J==0 zero branch with design-declared structural
  flag, augmented-grid inversion, prefix-valid generators, the
  48/120 C runner consuming registered path seeds, §5.3 evaluator,
  scalar references sharing no code with the optimized path, §4.6
  production report with implementation/version binding.
- `stage1_tranche.py` — v1 agreement machinery deleted; amended
  D registry (D2 on the single schedule source; D6–D8 undercoverage
  on the amended statistic with branch telemetry and explicit
  `schedule` fields); registered-seed consumption via fail-closed
  lookups; the amended aggregate (bundle-bound identities, exact
  8-key branch set, §7 B matrix, `C2_preCE1_available` requires
  scientific passage); `run_amend1_tranche` (frozen order,
  min-remaining in-loop deadlines on the monotonic clock, staged
  persistence with reloads, abort records); `finalize_amend1_run`
  (preflight-before-mutation, full env validation, partial-D
  reconciliation, atomic writes, exact-set checks).
- `stage1_replay.py` — 256-completion contract unchanged;
  `run_amend1_replay` under the bundle identity with registered
  B seeds; `verify_replay_evidence` binds tag, bundle identity, and
  registry-implied support at consumption.
- `conftest.py` (new) — the sentencepiece exclusion (172_f §3);
  test-harness only, outside the successor source digest by
  construction (repo root, not `tasks/conductor/`).
- Test files — every reviewer-directed probe from the six rounds is
  a named test; the four §12 outcome paths, all refusal probes, and
  the 171_s bypass are asserted.

**Finding of the review: no defect.** Every changed line traces to a
numbered 158_s requirement or a numbered reviewer finding; no change
touches Stage-0 frozen sources (the eight SOURCE_DIGEST_FILES are
untouched — `workerpool.py`'s three comment citations were fixed
pre-amendment and are part of the reviewed v1 lineage).

## 2. Verification battery (158_s §10 Unit D items 1–4)

Script disclosed in the commit message directory note; all checks
executed on this box, exit 0:

1. **Tests**: full CPU suite under `-W error`: **894 passed, TRUE
   process exit 0** (unpiped; the deterministic §5.2/§8.4D sets run
   inside the suite).
2. **Frozen hashes re-derived from bytes**: few-shot prompt
   `fe9bba0d…`, schema-only prompt `9efe8998…` (derived by dropping
   the demo block, not retyped), SYSTEM_DIRECT `b7a7d2d2…`; pinned
   surface loads and hash-verifies (support declaration `6df4c42b…`,
   surface manifest `221a04d5…`, 18 support observations).
3. **Registries exact**: 48 A-position + 24 A-router cells; 48 C
   paths / 120 marginals; 8 D scenarios (ids == AMEND1_D_IDS); 8
   branch-telemetry keys; fork schedule (100, 500) from the single
   source; finalized seed registry = 49,342 entries, canonical
   (rederived and compared), DB-domain values == v1 `scenario_seed`,
   B keys == `completion_seed` material end-to-end.
4. **Artifact schemas / re-derivation / bundle binding**: enforced
   by the named tests cited in §1 (loaders recompute content hashes,
   re-derive rates from integer counts, and refuse foreign
   executions, wrong tags, inexact key sets, and impossible counts).
5. **v1 evidence archive**: verified byte-for-byte against the
   pinned manifest `b01b7060…`.
6. **Cost projection ≤ 12 h**: §3 below — ≈ 4.3 h.

## 3. §5.4 probe suite (throwaway inputs; timings/shapes/agreement only)

1. **Scalar/optimized reference agreement**: 120 fixed throwaway
   cases (seeded generator, both schedules, positive branch):
   **120/120 decisions bit-identical; 120/120 inversions and all
   endpoints within atol 1e-12 (rtol 0)** — both the bounds
   reference and the independent row-level inversion reference.
2. **C registry projection**: 0.189 ms/path-trial on the worst
   paths → complete 48-path × 10,000 C ≈ **1.51 min ≤ 30 min**.
3. **Actual 10,000-inner worst-case D benchmark**: **0.951551
   s/outer** (persisted literal `seconds_per_outer_trial_x1e6 =
   951551`; consistent with 168_f's 0.944 and the 145_s-era
   0.187 × 5). Frozen 4× rule at this measurement → 19,031 s per
   D1–D5 scenario.
4. **Complete amended CPU tranche projection**: D1 ≈ 79 min; D1–D5
   ≈ 3.7 h (v1-measured relative scenario weights); with D6–D8
   (< 30 min gate), A (≈ 1 min at 10k trials/cell), C (≈ 1.5 min):
   **≈ 4.3 h total**.
5. **Budget demonstration**: C ≤ 30 min ✓; complete CPU tranche
   ≤ 12 h ✓; abort rules preregistered in 174_f §6 (per-scenario 4×
   measured-at-run, D6–D8 combined 30 min and total 12 h enforced
   as min-remaining inside the every-50-trial check, A 30 min,
   C 30 min).

Statistical outputs of all probes discarded; no frozen seed touched
(throwaway domains only).

## 4. Deterministic sub-verification for the 174_f predictions

The θ=0 zero-branch decisions on exact nested-eligibility paths are
deterministic; computed by the implementation (not by hand):
ordinary e=0.65 → unresolved at look 100 (U=0.1101), PASS at look
300 (U=0.0327); fork e=0.60 → unresolved at 100 (U=0.1123), PASS at
500 (U=0.0191); structural e=1.00 → PASS at look 100 (U=0.0467).
These become exact registered predictions in 174_f §8.

## 5. Boundary

174_f is the final amendment preregistration with no placeholders.
The separate lock record (pinning 174_f's SHA-256, the lock commit,
and the execution-bundle fields completed at lock) is created only
after review sign-off and Ken's approval, matching the 153_f → 156_f
precedent. No formal statistical run occurs before that lock.
