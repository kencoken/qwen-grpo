# 364_f — P0 runner REV2 (response to 363_s): lifecycle, RNG identity, resume (for review)

All six blocking findings and the conformance repairs
implemented. Full suite: **1039 passed under `-W error`, TRUE
exit 0**. **One identity pin CHANGED by the requested amendment**
(§2); the launch-freeze pin is untouched. No GPU work; no
prelaunch prepared.

## 1. F1 — checkpoint zero captures REAL training objects

`trainer.create_optimizer_and_scheduler(num_training_steps =
final_index)` runs explicitly BEFORE checkpoint zero, and after
`train()` the session PROVES reuse: the unwrapped
optimizer/scheduler must be the SAME objects created before the
checkpoint (accelerate wrapping is unwrapped for the comparison);
divergence aborts the run. The recommended reward-blind GPU
lifecycle check (§7) will exercise this on the real stack before
any prelaunch.

## 2. F2 — the executed RNG identity is IN the authenticated identity

Adopted exactly as recommended: the identity's evaluation block
now freezes the **batched per-observation rule** explicitly —
`checkpoint_eval_realization`: one slot-0 CRN seed per
observation seeds a SINGLE batched generation of `group_size`
sequences (the smoke-priced operation; identical draws at every
checkpoint; slots 1..7 of the 720-entry schedule are NOT
consumed by checkpoint evaluation) — with the 90-seed
realization pin bound INSIDE the record. The artifact was
regenerated:

| artifact | pin |
|---|---|
| `P0_EXECUTION_IDENTITY_SHA256` (**NEW** — the narrow amendment) | `b5749ecac2e8e2444dd2ebb6193054fb721ea1686751ffd73d0c3938d80b1e1d` |
| `P0_LAUNCH_FREEZE_SHA256` (unchanged) | `88c6635aadb2d0ca1c766efc937123b7ece427190cfe3ce3675ac8f269ebccfc` |

The superseded pin `4c763cc9…` was never GPU-consumed. The
session refuses if the identity's realization pin diverges from
the module constant, and the eval pass consumes EVERY frozen
sampling field (`do_sample`, `top_k` — None realized as 0 —
`repetition_penalty`, temperature, top_p, group size, max new
tokens).

## 3. F3 — the P0-specific checkpoint saver

`_save_p0_checkpoint_bundle`: `run_id = "routing-dev-p0-v1"`,
`segment_id = "upd<i>"`, `parent_checkpoint` = the PREVIOUS
bundle's record hash (None only at update 0); the five-way
cross-check requires trainer step == generated == consumed ==
optimizer updates == `i` with `8i` completions BEFORE any bundle
exists; the sampler position binds the HF checkpoint (dir +
per-file hashes — the 235_s F2 pattern) when one exists; and
`checkpoint.validate_resume` runs IMMEDIATELY from disk after
every write. The terminal verifier re-validates EVERY bundle
from disk again, including the full parent chain and the
counters-at-cadence-position rule.

## 4. F4 — the lifecycle split, and resume is IMPLEMENTED

- **Resumable interruption** (the automatic path): partial
  evidence sealed, every checkpoint RETAINED, cumulative elapsed
  seconds and interruption count accumulated in
  `interruption.json` — **no ledger write; the launch stays
  OPEN** (regression: two interruptions accumulate 100 + 50 s).
- **`terminally_abort_p0`** is the ONLY operation that closes an
  interrupted launch aborted — explicit, binds the sanitized
  inventory and the CUMULATIVE consumed hours (regression: 9,000
  s → 2.5 GPU-h in the closeout; a second abort refuses).
- **`resume_p0_run` is implemented, not deferred**: it requires
  the ORIGINAL launch OPEN (resume NEVER re-admits —
  first-launch-only stands), the cumulative remaining budget
  positive, the last positive-index bundle validated via
  `checkpoint.validate_resume` AND its bound HF checkpoint
  verified via the 246_f-validated
  `verify_hf_checkpoint_against_bundle`, the accountant restored
  from the bundle counters, the reward boundary continued at
  `start_group_index = consumed`, and
  `trainer.train(resume_from_checkpoint=…)` under the CUMULATIVE
  deadline (`budget − prior elapsed`). Cadence intermediates
  already completed are skipped (regression on the callback's
  skip-list). Resume trace segments are separately sealed
  (`training_trace_r<k>.jsonl.gz`) and the verifier checks the
  MERGED sequence.
- Cadence bundles now bind HF checkpoints: at each intermediate
  the callback requests an HF save and the bundle is written at
  `on_save`, binding the `checkpoint-<step>` directory it
  shadows. HF checkpoints are all retained (bounded: ~11 ×
  ~200 MB).

## 5. F5 — the verifier trusts nothing declared

`verify_p0_run` now enforces: the EXACT frozen eleven-point
cadence from the loaded identity (never the record's
collections); checkpoint blocks covering exactly that set;
finite nonnegative measurements with the runtime within the
ceiling; EVERY bundle re-validated from disk (proof equality,
counters == cadence position, run/segment/parent lineage, the
identities binding the manifest, `validate_resume`); the EXACT
sealed inventory (per-cadence eval traces + trace segments +
trainer log, nothing else, `.gz` only); the merged training
trace re-read group by group — the observation sequence must BE
the frozen 6,123-group schedule with EIGHT completions per
group; BYTE-exact prelaunch copies of the two reviewed
artifacts; prelaunch↔execution environment attestation; and the
lifecycle/closeout consistency. Regressions: the reviewer's
empty-run record refuses at the cadence check; a negative
runtime refuses at the finiteness check.

## 6. F6 + conformance

- The deadline is checked BEFORE and AFTER every checkpoint and
  evaluation operation, at every reward entry and step begin,
  and the CUMULATIVE total is enforced immediately before the
  successful closeout; a resume receives only the REMAINING
  budget, and an exhausted budget leaves only the explicit
  terminal abort.
- Identities: renderer schedule from the admitted rows' renderer
  field (the established `schedule_identities`), surface
  manifest/worker pool/cache identity from the AUTHENTICATED
  training surface lock; no placeholders, no duplicated hashes.
- The explicit FP32 LoRA cast with the frozen key set asserted
  (count 504 + sorted-keys hash + post-cast dtype check).
- `gpu_session_preflight()` (the ≥20 GiB free-VRAM check) runs
  BEFORE the irreversible ledger admission, and before resume.
- The final update count derives from the admitted execution
  identity everywhere; `_build_p0_trainer` takes `max_steps` as
  an argument.

## 7. Next

Narrow changed-lines review of these repairs (recording the §2
pin) → **the tiny reward-blind GPU lifecycle check** the review
recommends (trainer construction → optimizer/scheduler
initialization → checkpoint-zero save/restore → a minimal
evaluation call; disclosed bounded probe, no science) → the real
prelaunch manifest → the narrow prelaunch review → P0 launch on
head `df4bf7ad…`.
