# 156_f — Unit-3 tranche LOCK record

**The §8.4 design-validation tranche is LOCKED for execution.**

- Preregistration of record:
  `153_f_stage_1_unit_3_validation_tranche_prereg_rev5.md`, SHA-256
  `235acb78d9b875999ab90ca50a37e9fbe4c208fa2fa92a285c3229ec01748572`
  (lineage 141_f → 144_f → 147_f → 150_f → 153_f, every predecessor
  preserved at reviewed bytes).
- Reviewer approval: 154_s ("recommend locking immediately" after the
  single abort-boundary fix) + reviewer approval of the 155_f
  changed-lines fix, per Ken 2026-07-24.
- Ken's lock approval: 2026-07-24.
- Executable commit at lock: `75b852ff3bc3bd5671352451bfc60eae161b4370`
  (clean tree; this lock record is the only addition in the lock
  commit).
- Successor source digest at lock:
  `8034178f00d952e4f8952dc511a79ac8fc7e36fa58b46e523d47964a9cc4470b`
  (recomputed and bound inside the execution manifest at run time;
  fail-closed on drift).
- Pre-flight (this box, recorded): working tree clean; GPU idle
  (4 MiB/24564 MiB; no resident compute apps — ollama not holding
  VRAM); `runs/stage0-support` present for the surface pin;
  `runs/stage1-validation` and `runs/stage1-replay` absent
  (refuse-overwrite satisfied).

Execution now proceeds in the frozen 153_f §6 order, no further edits
of any kind until both runs complete (the shared execution identity
requires the identical environment manifest for the CPU tranche and
the GPU replay):

1. `run_full_tranche()` — deterministic equivalence set → worst-case
   benchmark → A grids → C grid → agreement gate → D battery under
   in-loop deadlines, staged persistence to `runs/stage1-validation/`.
2. `run_replay()` — the 9,216-completion singleton replay to
   `runs/stage1-replay/`.
3. `aggregate_verdict` over the four verified artifacts.
4. The tranche outcome document (next lineage number) carrying the
   verdict input for the single reviewed confirm/amend decision.

Registered predictions carried into execution (from 141_f, unchanged
through every revision): A and router acceptance PASS with margin
(worst gated cell ≈ 0.921); the C power criterion FAILS its 80%
Wilson criterion at both hard cells (fork ≈ 0.144 @ N=200/e=0.60,
chain ≈ 0.541 @ N=500/e=0.65) — the predicted tranche verdict is the
**amend-once branch on §8.4C power** before construction registration.
No prediction is registered for B beyond Stage 0's raw 2/36 warning.
