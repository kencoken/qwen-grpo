## Verdict

**Do not start Step 5 from commit `94b6556` yet.** The freeze and core accounting logic are sound, but the current run would not cleanly test whether checkpoint/resume reproduces uninterrupted training.

No GPU work or ledger admission has occurred, so correcting this now has no budget or evidence consequence.

### Blocking findings

1. **The uninterrupted and interrupted arms can start from different LoRA weights.**
   Seeding occurs inside trainer initialization, after the PEFT adapter has been created. Because A trains before B is constructed, B can receive a different random `lora_A` initialization. I reproduced this mechanism independently. Additionally, A uses `max_steps=6`, while B uses `max_steps=3`, so they are not the same launch configuration. See [_build_trainer and phase construction](/private/tmp/review221/tasks/routing/resume_validation.py:339).

   Both arms should load one shared checkpoint-zero adapter—or reseed before every model construction—and prove identical initial hashes. Both should use `max_steps=6`, with B stopped by fault injection rather than a different horizon.

2. **The validated bundle is not the checkpoint actually resumed.**
   The custom bundle is validated, but training resumes from the separate HF `checkpoint-3` directory. The bundle’s adapter, optimizer and scheduler are not loaded, while its restored RNG is consumed before HF loads its own unbound RNG state. See [resume path](/private/tmp/review221/tasks/routing/resume_validation.py:586).

   Either resume from the validated bundle or content-bind and semantically verify every HF checkpoint file that the trainer actually consumes.

3. **The required aborted-tail case is not exercised.**
   B stops cleanly at update 3 and is marked complete. There is no post-checkpoint work to preserve and exclude, so §11.3 is currently untested. See [segment merge](/private/tmp/review221/tasks/routing/resume_validation.py:611).

   B should checkpoint at 3, continue far enough to produce at least one post-checkpoint group, then deliberately abort. The raw tail must remain archived, appear in `excluded_aborted_evidence`, and not enter the six-group merged trajectory.

4. **The final comparison is incomplete and cannot be independently reverified.**

   - The sampler comparison always obtains `END`, because the schedule has exactly six entries for six updates.
   - Optimizer comparison omits parameter-group membership.
   - Traces contain observation IDs and rewards, but not completions, parsed actions or semantic assignments.
   - Final A/C states are compared only in memory and are not persisted.
   - There is no verifier that reloads the archive and rederives `validation_record.json`.

   Use a schedule longer than six entries, compare the actual trace sequence and next cursor, include the complete optimizer state, and persist sufficient final state for an independent verifier.

5. **The launch does not consume the reviewed freeze identity.**
   `execute_resume_validation()` accepts a ledger-head hash and then recomputes the freeze from whichever code/config exists at execution time. It never requires the reviewed `539ccc2c…` hash. See [execution admission](/private/tmp/review221/tasks/routing/resume_validation.py:488).

   Require the exact externally reviewed freeze hash at launch.

6. **The GPU lifecycle is unsafe for a 4090.**
   `_release(trainer)` deletes only its local reference; `trainer_a` and `trainer_b` remain live. The captured comparison states also retain GPU tensors. Later phases could therefore load multiple 3B trainers concurrently. See [_release](/private/tmp/review221/tasks/routing/resume_validation.py:544).

   Move snapshots to CPU, delete the caller-held trainer/model references, collect garbage and verify VRAM returns before constructing the next phase.

7. **The ceiling and determinism claims are not implemented as frozen.**

   - The 0.5-hour deadline is checked only between entire `trainer.train()` calls, not before each generation/update.
   - `full_determinism` remains false despite the claim that deterministic algorithms are requested.

   Both matter when interpreting an exact-tolerance comparison.

8. **The claimed test result is currently not reproducible.**
   The full Linux run produced **964 passed, 1 failed**, rather than 965 passing. [The failing test](/private/tmp/review221/test_routing_dev.py:1602) leaves `trace.open()` unclosed, producing a `ResourceWarning` under `-W error`.

### Additional acceptance gates

The revised tranche should also require:

- identical checkpoint-zero hashes;
- identical A/B states and traces at checkpoint 3;
- at least one reward-varying generated group;
- a nonzero checkpoint-zero → checkpoint-3 adapter update.

Without the final two checks, a zero-gradient trajectory could make resume appear exact without meaningfully exercising optimizer restoration.

The committed Stage-4 surface also cannot currently be restored by the production path in a clean clone; that reconstruction exists only in a test helper. This is nonblocking for the present picome launch if its retained, verified `runs/` directory is made an explicit prerequisite, but it is a portability gap.

### What is already correct

The freeze hashes rederive, reward authentication is sound, the installed TRL configuration does produce one G=8 group per optimizer update, checkpoint boundary authorization is meaningful, and the generated/consumed accounting is directionally correct.

I recommend fixing the items above, issuing a revised freeze with new source/config/freeze hashes, rerunning the warnings-as-errors suite, and then doing one narrow changed-lines review. The broader Step‑5 design does not need reconsideration.