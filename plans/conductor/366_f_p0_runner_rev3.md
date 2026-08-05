# 366_f — P0 runner REV3 (response to 365_s): the authenticated lifecycle (for review)

All three P0 blockers and all nine additional repairs
implemented. Full suite: **1039 passed under `-W error`, TRUE
exit 0**. **No pins changed** — the approved identity pin
`b5749eca…` and freeze pin `88c6635a…` stand; the repairs are
code-only in the runner/verifier (moving the future
routing-source and manifest hashes, as expected — no P0 manifest
is frozen).

## 1. F1 — the three deterministic failures

- `_persist_verified` now imports from its actual home
  (`support_run`) — the rev2 reference to a nonexistent
  `p0_smoke` symbol would have interrupted immediately after
  admission, exactly as the review says.
- `_cast_and_assert_lora` now asserts the C2 WAY:
  `content_sha256(sorted(keys))` over the state-dict LoRA key
  naming (the saved-map keys the frozen pin was computed from) —
  not `json.dumps` over parameter names.
- **The scheduler lifecycle is adapted to actual Trainer
  behavior**: `_prepare_training_objects` creates the optimizer
  through the Trainer API, creates the FULL-horizon scheduler,
  and marks it USER-PROVIDED (`_created_lr_scheduler = False`) —
  Transformers discards schedulers it created itself when
  `train()` begins, so the marking is what makes checkpoint zero
  capture the exact objects training uses. The post-train
  unwrapped-identity assertion remains as the runtime proof, and
  the GPU probe (§5) exercises it for real.

## 2. F2 — atomic cadence completion

A cadence point is complete ONLY when its ATOMIC record
(`cadence/upd<i>.json`, tmp+rename, write-once) exists — written
strictly AFTER the full 90-observation evaluation sealed and
validated. Resume derives its state from these records, NEVER
from bundle existence; a bundle whose evaluation never finished
is not a completed point, its partial sealed evaluation is moved
to `excluded/` (retained, hashed, never overwritten, never part
of the trajectory), and that index reruns completely. The
records carry the ACTUAL measured timings — the record blocks in
`p0_record.json` must EQUAL the persisted cadence records
(no 0.0 reconstruction; fabricated-evidence channel closed).

## 3. F3 — the authorized-prefix segment merge

Each session writes its own trace segment
(`training_trace_s<k>.jsonl`); the session log records each
session's `start_group_index`. The verifier merges the LEARNING
TRAJECTORY from each segment's checkpoint-authorized prefix —
`[start_k, start_{k+1})` — so a first segment reaching group 699
with a resume from checkpoint 628 contributes exactly groups
0–627; its 628–699 tail remains sealed EXCLUDED evidence
(schema-validated, index-continuous, not part of the
trajectory). The merged trajectory must be exactly the frozen
6,123-group schedule with eight completions per group.

## 4. The additional repairs

- **Hash-chained session log** (`sessions.jsonl`) replaces
  mutable `interruption.json`: append-only entries binding the
  previous entry's hash; every elapsed value validated finite
  and non-negative AT APPEND AND AT LOAD (NaN can never disable
  the deadline); a SIGKILL'd session (start without end) is
  closed at the next entry point with a CONSERVATIVE
  wall-clock-inferred elapsed. Regressions: tampered line
  refuses; NaN refuses; killed-session inference accumulates.
- **Independent identity re-derivation**: the verifier rebuilds
  all ten identity fields from the manifest, the freeze under
  its pin, the AUTHENTICATED training surface lock, and the
  frozen schedule — EVERY bundle must equal that expectation
  (nothing trusted from the first checkpoint).
- **Exact trace schemas**: every evaluation trace re-read (90
  observations in lock order, eight completions and eight finite
  rewards each); every training row validated
  (index/completions/actions/assignments/rewards).
- **Exact bundle inventories** (the five files, nothing else)
  and `verify_hf_checkpoint_against_bundle` for EVERY retained
  positive-index HF checkpoint, not only the resume choice.
- **Resume re-attests** the live environment (prepared-vs-live +
  the freeze's commit-independent expectation) and the bound run
  root on every entry.
- **Elapsed recomputed after persistence + verification**: the
  completion tail closes the session in the chained log AFTER
  `p0_record.json` is persisted and the open-state verification
  passes; the ceiling is enforced on the RECOMPUTED cumulative
  total, and the closeout consumes that total.
- **Historical environment self-validation** in the verifier
  (`validate_env_self_hash`) — evidence stays verifiable after
  the planned sentinel-assembler source commit.
- **Recoverable finalization**: `p0_record.json` is atomically
  replaceable, and `resume_p0_run` detects the
  all-cadence-complete state and finalizes WITHOUT the GPU
  (rebuild record from persisted cadence records → verify →
  close session → ceiling on recomputed total → closeout →
  re-verify).

## 5. Identities and next

No pin changes: identity `b5749eca…` (approved by 365_s), freeze
`88c6635a…`, realization `a8e9cf73…`.

Next, per the review's closing: the **expanded reward-blind GPU
probe** — trainer construction → optimizer/scheduler
initialization (the §1 lifecycle) → checkpoint-zero save/restore
→ ONE training update → a forced HF cadence save with bundle
verification → an interruption → a one-step resume — as a
disclosed bounded probe, then the narrow prelaunch review of the
real manifest, then P0 on head `df4bf7ad…`.
