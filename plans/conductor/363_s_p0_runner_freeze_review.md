Verdict: changes requested. `dd0b064` is a sound runner skeleton, but it is not safe to prepare the prelaunch manifest or launch P0 yet.

### Blocking findings

1. **[P0] Checkpoint zero deterministically aborts before evaluation.**

   `execute_p0_run()` saves a checkpoint before `trainer.train()`, but Transformers has not yet created `trainer.optimizer` or `trainer.lr_scheduler`. The reused saver immediately calls `.state_dict()` on both, raising `AttributeError`.

   Since admission is first-launch-only, this would consume the P0 attempt without producing the required checkpoint-zero evaluation. Explicitly create the optimizer and 6,123-step scheduler before checkpoint zero and prove `train()` reuses them.

2. **[P0] Evaluation does not execute the frozen RNG identity.**

   Unit L freezes 720 independent `(observation, completion_slot)` seeds. The runner instead uses only each observation’s slot-0 seed and generates eight completions from that RNG stream.

   The current 90-seed source pin cannot supersede the authenticated 720-seed identity. I recommend a narrow reviewed amendment to freeze the actual batched, per-observation seed rule: it matches the priced smoke operation and still provides common random numbers across checkpoints. Executing 720 separate generation calls would require remeasurement and cap review.

3. **[P0] Retained checkpoints are smoke-labelled and not validly resume-verified.**

   P0 reuses a helper that writes:

   - `run_id="beta-smoke-v1"`
   - `segment_id="smoke-epoch-1"`
   - `parent_checkpoint=None`
   - a smoke-specific sampler note

   The helper only rehashes freshly written files; P0 never calls `checkpoint.validate_resume()`.

   Implement a P0-specific saver with correct run/segment/parent lineage. At cadence update `i`, require trainer step, generated groups, consumed groups and optimizer updates all equal `i`, with `8i` completions. Validate every bundle immediately and again from disk during terminal verification.

4. **[P0] The abort path makes the promised resume impossible.**

   The sanitizer says an interrupted launch remains open for resume, but the catch-all `except BaseException` immediately appends a terminal `aborted` closeout. A later same-launch completion then refuses because the launch is already closed.

   Define separate lifecycle states:

   - resumable interruption: seal partial evidence, retain the last valid checkpoint, record cumulative elapsed time, but do not terminally close;
   - explicit terminal abort: close the launch and retire it.

   The resume entry point cannot safely remain deferred beyond launch. Sentinel assembly can remain a post-run unit.

5. **[P1] The terminal verifier can accept an impossible empty run.**

   I reproduced `verify_p0_run()` returning `PASS` for a record with empty cadence/checkpoint/sealed maps and negative runtime. It currently trusts the record’s declared collections.

   It should enforce:

   - the exact frozen eleven-point cadence;
   - exact checkpoint, evaluation-trace and sealed-file inventories;
   - valid nonnegative finite measurements;
   - exact 6,123-group training sequence and eight completions per group;
   - full checkpoint record/artifact/proof validation;
   - exact prelaunch freeze and identity copies;
   - prelaunch↔execution environment attestation;
   - exact terminal root inventory and lifecycle status.

6. **[P1] The ten-hour ceiling is not terminally enforced.**

   The final evaluation checks the deadline only before each observation. Its last generation, sealing, record persistence and verification can cross the ceiling and still close `complete`. A future resume would also currently receive a fresh ten hours.

   Persist cumulative launch time and check the deadline after every checkpoint/evaluation operation and immediately before successful closeout.

### Other conformance repairs

- Checkpoint identities currently duplicate the full observation-ID hash as the renderer-schedule hash and use placeholder worker/cache identities. Derive renderer, surface-manifest, worker-pool and cache fields from the admitted rows and authenticated surface lock.
- Restore the explicit FP32 LoRA cast and assert the frozen key set/dtypes.
- Consume every frozen evaluation sampling field, including `do_sample`, `top_k` and `repetition_penalty`.
- Run the existing ≥20 GiB free-VRAM preflight before irreversible ledger admission.
- Derive the final update count from the admitted execution identity rather than independently hardcoding `6123`.

### What is already sound

Admission ordering, the fixed horizon and cadence, isolated evaluation RNG, final-step/cadence assertions, trace sealing, and the intended checkpoint-zero-before-training design are all good foundations.

Mechanical checks are clean and all **1,039 tests pass under warnings-as-errors**. The present test only exercises CPU helpers, however; it never constructs the real trainer, saves checkpoint zero, or challenges the persisted verifier—which is why the immediate runtime failure escaped.

After the repairs, I recommend one tiny reward-blind GPU lifecycle check covering trainer construction → optimizer/scheduler initialization → checkpoint-zero save/restore → a minimal evaluation call. Then perform a narrow changed-lines review before preparing the real prelaunch manifest.