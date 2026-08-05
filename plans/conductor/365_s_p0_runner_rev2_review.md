Verdict: Rev2 is materially improved, but not ready for the GPU lifecycle probe or prelaunch.

### Blocking findings

1. **[P0] The fresh runner still has three deterministic failures.**

   - `p0_execution.py:1571` references `p0_smoke._persist_verified`, which does not exist. Execution interrupts immediately after admission.
   - `_cast_and_assert_lora()` uses ordinary `json.dumps()` rather than canonical `content_sha256()`. Against the real 504-key artifact, it computes `358a390f…`, not the frozen `e44ecb9…`.
   - Transformers 5.13 explicitly discards a pre-created scheduler when `train()` begins because `_created_lr_scheduler=True`. Consequently, checkpoint zero does not capture the scheduler training uses, and the reuse assertion at lines 1675–1681 will fail after all 6,123 updates. The lifecycle must be adapted to actual Trainer behavior, not just the assertion.

2. **[P0] A partial evaluation can be promoted to a completed cadence point.**

   The bundle is persisted before evaluation, while resume treats any bundle containing `checkpoint_record.json` as completed. An interruption halfway through evaluation therefore leaves:

   - a valid checkpoint bundle;
   - a partial sealed evaluation;
   - a resume path that skips that evaluation.

   The terminal verifier never opens evaluation traces, so the partial result can be accepted. Persist an atomic cadence-complete record only after the full 90-observation evaluation validates, and derive resume state from that record—not bundle existence.

3. **[P0] Ordinary between-cadence resume cannot produce a valid trajectory.**

   If the first segment reaches group 700 but the latest checkpoint is 628, its preserved trace contains groups 0–699. Resume writes groups 628–6122. The verifier concatenates both complete traces, producing duplicated groups 628–699 and rejecting the run.

   Reuse the established segment-merging contract: retain post-checkpoint tails as excluded evidence, while the learning trajectory includes only each segment’s checkpoint-authorized prefix.

### Additional required repairs

- Persist cadence timings/proofs as they complete. Reconstructing missing historical timings as `0.0` is fabricated evidence.
- Re-derive all ten checkpoint identities independently during verification; currently the first checkpoint’s prompt/cohort/renderer/surface/worker/cache/environment/seed fields are trusted.
- Validate exact evaluation trace schemas: 90 observations in lock order, eight completions and rewards each. Training traces should also validate group index, actions, assignments and rewards.
- Use exact bundle inventories and validate every retained positive-index HF checkpoint against its bundle—not only the checkpoint selected for resume.
- Attest the live environment and bound run root on every resume.
- Replace mutable, unauthenticated `interruption.json` accounting with validated, append-only or hash-chained session records. Currently `NaN` disables the deadline comparison, and a SIGKILL or power loss records no elapsed time at all.
- Recompute total elapsed time after final persistence and verification. Rev2 still measures before those operations.
- Use historical environment self-validation in `verify_p0_run`; the current-tree validator will make valid evidence unverifiable after the planned sentinel-assembler source commit.
- Make completion finalization recoverable: failures after `p0_record.json` is written currently cannot resume because the record is write-once.

### Correctly closed

The 90-seed batched evaluation amendment is clear and properly authenticated. I approve the new execution-identity pin:

`b5749ecac2e8e2444dd2ebb6193054fb721ea1686751ffd73d0c3938d80b1e1d`

The corrected P0 run/segment/parent labels, sampling-field consumption, checkpoint identity construction, VRAM preflight placement, derived final update count and per-cadence deadline checks are also sound.

All **1,039 tests pass under warnings-as-errors**, and diff hygiene is clean. However, no test enters `_p0_session`, the actual scheduler lifecycle, checkpoint persistence, or real resume.

After repair, expand the reward-blind GPU probe beyond checkpoint zero: include one update, a forced HF cadence save, bundle verification, interruption, and a one-step resume. That is the smallest probe that exercises Rev2’s genuinely risky new machinery.