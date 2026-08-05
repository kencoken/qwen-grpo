# 362_f — P0 execution runner (rev1): admission-only inputs, checkpoint-zero first, retained cadence checkpoints (for review)

The P0 runner, implemented in the SAME driver module the
manifest binds (`tasks/routing/p0_execution.py`). Full suite:
**1039 passed under `-W error`, TRUE exit 0**. One new frozen
pin (§3). **No GPU work; no prelaunch prepared** (the real
manifest is prepared only AFTER this review, since the runner
code moves the source identity). The Unit-L pins are untouched.

## 1. The 361_f carry-forwards, first

- **The runner invariant**: `execute_p0_run` obtains its trainer
  inputs ONLY from `admit_p0_execution`'s returned ADMITTED
  bundle (rows, schedule, runtime, identity); no path in the
  module appends a `training_run` through the lower-level
  helper.
- **Defense-in-depth adopted**: the ledger's P0 branch now
  invokes the closed manifest validator with `recompute=True` —
  the source digest is re-derived from the tree INSIDE ledger
  admission as well as at the admission boundary.

## 2. The run protocol

1. **Prepare** (`prepare_p0_launch`, exactly once): persists
   `prelaunch/{env_manifest, p0_launch, launch_freeze,
   execution_identity}.json` — the manifest hash goes to the
   narrow prelaunch review; the two reviewed artifacts are byte
   copies of the committed files.
2. **Admission** through `admit_p0_execution` (the external
   manifest re-validated from the persisted prelaunch bytes; the
   prepared environment authenticated; the resolved run root
   bound; the launch entry appended as admission's final act).
3. **Checkpoint ZERO is P0's FIRST execution** (charter §7): the
   v1 bundle at update 0 (GroupAccountant-authorized zero
   counters) then the checkpoint-zero evaluation — BEFORE
   `trainer.train()`.
4. **Training with NO configuration change**: the canonical
   profile literals, `max_steps = 6123`, the frozen P0 seed
   20260807, the established reward boundary
   (`make_validation_reward` on the C2-locked extension surface,
   wrapped by the reviewed deadline/instrumentation factory);
   deadline at every reward entry AND `on_step_begin`;
   consumption at `on_optimizer_step`; console reporters
   stripped.
5. **Cadence** at the identity's frozen intermediates
   {628, …, 5652} from the training callback, and the FINAL
   event at 6123 after `train()` returns (the trainer must end
   exactly there): each event = a **RETAINED** v1 checkpoint
   bundle (`checkpoint_bundle_upd<index>/`, restore-verified,
   proof recorded) + a CRN evaluation pass sealed inside the
   pass. The completed cadence must equal the frozen index set.
6. **Terminal**: training trace + trainer log sealed; the closed
   `p0_record.json` (10 keys); `verify_p0_run` BEFORE the
   success closeout and RE-RUN against the completed head;
   the complete closeout binds record/env/terminal hashes.

**Abort rule** (differs from the smoke DELIBERATELY): raw traces
are sealed, but checkpoint bundles are **RETAINED — they are the
resume state** under the original launch (330_f §5;
first-launch-only admission means an abort can never re-admit).
A sanitization failure propagates: the launch stays OPEN and
visibly blocked.

## 3. The evaluation identity — one consistency decision made explicit

The cap arithmetic priced each evaluation at the SMOKE's
measured operation, and the smoke's frozen executed shape was
**one slot-0 seed per observation with eight sampled sequences
per call**. The P0 checkpoint evaluation therefore freezes
EXACTLY that shape (any other realization would run an unpriced
operation), realized under the identity's CRN rule — domain
`p0_val_eval`, base 20260804, NO checkpoint index, so every
checkpoint replays IDENTICAL draws against the AUTHENTICATED val
surface (loaded under the val lock's surface pin `3698caa1…`).

The executed realization is itself frozen:

| pin | value |
|---|---|
| `P0_EVAL_REALIZATION_SHA256` (90 slot-0 seeds, lock order) | `a8e9cf7322a008889414c68ce133bb50cd82fe960340d079b0f1a66fd7f2f802` |

CRN continuity is test-asserted: slot 0 of the first observation
reproduces the V-reviewed pinned vector value `1176822329`.

## 4. Registered outstanding obligations (`P0_RUNNER_OUTSTANDING`)

1. **Sentinel-block assembly is NOT in-run**: the complete
   training trace and per-checkpoint evaluation traces are the
   sealed evidence; the per-checkpoint sentinel blocks consumed
   by `assemble_sentinel_trajectories` are derived by a
   deterministic CPU assembler in a follow-up REVIEWED unit
   before cycle synthesis (record-don't-edit: raw evidence
   first, derivation replayable).
2. **The resume entry point is deferred**: everything a resume
   needs is persisted (v1 bundles with counters, RNG, sampler
   position), but no resume path exists yet — an abort leaves
   the launch terminally blocked until a reviewed resume
   implementation. Fail-closed by construction.

## 5. CPU regressions

The frozen realization recomputes (forged pin refuses);
exactly-once prelaunch with the four-file inventory and
byte-identical artifact copies; callback ordering (deadline at
step begin, consumption cannot precede generation, cadence fires
ONLY at intermediates — 627 no, 628 yes, 6123 no); the abort
rule (raw sealed, bundles RETAINED); the closed record schema.

## 6. Budget expectation (from the signed closure)

39-epoch projected total **9.4029 h** against the 10.0 h manifest
budget (≈0.597 h headroom); envelope check at admission requires
remaining ≥ 10.0 + final R_cycle 1.0 (56.4941 available). The
run RETAINS ~11 checkpoint bundles (~tens of MB each, adapter +
optimizer state) — the cycle evaluation consumes checkpoint zero
and the final checkpoint per the frozen cycle record.

## 7. Next

Review of this runner → `prepare_p0_launch` on the signed tree →
narrow prelaunch review of the exact manifest hash → P0 launch
on head `df4bf7ad…` (~9.4 GPU-h) → timing + evidence closeout →
sentinel-block assembly unit → cycle evaluation → cycle
synthesis.
