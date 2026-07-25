Not quite. The statistical repair is sound, but three integration issues still block locking.

1. **[P1] The real launch path fails before execution.**  
   [stage1_amend1.py](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1.py:763) builds the registry from 36 smoke-schedule rows rather than 18 unique observations. On picome I reproduced:

   ```text
   rows 36, unique observations 18
   InfrastructureError: B support must be exactly 18 observations, got 36
   ```

   The test bypasses this by injecting `_support_ids`. Use `support_observations()` directly—or otherwise derive a uniquely validated set—and add a test exercising the production default.

2. **[P1] Replay does not consume the CPU run’s persisted bundle or enforce CPU-first ordering.**  
   [stage1_amend1_run.py](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1_run.py:246) reconstructs the bundle independently for tranche, replay, and finalize. Consequently, replay can run before CPU completion or under changed environment identity, consume all 9,216 GPU completions, and only be rejected during finalization.

   The CPU tranche should create the canonical bundle. Replay should load that exact bundle, verify it against current authoritative provenance, and require a complete CPU root before claiming the replay root or loading the model. Finalization should consume the same persisted bundle.

3. **[P1] The archive command does not yet satisfy either terminal mode fully.**  
   [archive_evidence()](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1_run.py:140):

   - accepts incomplete or extra files without enforcing the successful exact-file-set/finalized-aggregate contract;
   - can archive CPU-complete/replay-absent state as though it were terminal;
   - refuses malformed or cross-bundle evidence, even though those are precisely infrastructure-abort states whose raw evidence must be preserved.

   Keep the fix simple: explicit success and abort modes. Success validates authoritative provenance, both completed roots, exact file sets, and aggregate. Abort copies the partial bytes without trusting their bundle and records the validation errors. Staging then atomically renaming the archive would prevent a failed copy from stranding its immutable destination.

One lower-severity discrepancy remains: the frozen plan says the archive includes commands and logs, but these are not recorded. A manifest command list plus treating the structured run records as the formal logs would be sufficient; no logging framework is needed.

Everything else checks out:

- 899 tests pass under warnings-as-errors.
- Focused Stage-1 suite: 163 passed.
- Source digest and lockfile hash recompute correctly.
- Frozen deadline control, sanity band, and cost projection are correct.
- No estimand, threshold, seed, or acceptance-rule regression found.

After these fixes, regenerate the source identity in `177_f`, run one narrow changed-lines review and the mechanical checks, then lock. Another open-ended audit should not be necessary.