Not quite ready for Unit D. The scientific repairs are correct, but two execution-integrity blockers remain, and the test-suite claim in `170_f` is not reproducible.

### Remaining blockers

1. **[P1] B support is checked during generation, but not when persisted evidence is consumed.**

   [`run_amend1_replay()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_replay.py:791) correctly compares registry-implied support with authoritative support. However, [`verify_replay_evidence()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_replay.py:352) does not repeat that comparison.

   The current aggregate tests demonstrate the bypass: the bundle registry uses `o00…o17`, while B is scored over different render-instance IDs, yet confirmation succeeds. Pass the finalized registry/support digest into the amended verifier and require the exact support-ID match there. Aggregate fixtures should then use the matching registry.

2. **[P1] The persisted lifecycle is still not fully fail-closed.**

   In [`run_amend1_tranche()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_tranche.py:810), A/C/D are written but not reloaded before CPU completion and B authorization, contrary to the frozen persist/reload sequence.

   In [`finalize_amend1_run()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_tranche.py:902):

   - the replay environment is trusted from its claimed hash field rather than fully validated;
   - `partial_D_*` contents are not validated or reconciled with `artifact_D`;
   - exact file sets are checked only after writing `aggregate.json` and a confirmation decision. A stray file therefore raises while leaving an apparently successful aggregate and run record on disk.

   Preflight both roots before mutation, fully validate both environments, reconcile every partial D record, then write the aggregate/run record atomically and perform the final exact-set check.

### Test-suite discrepancy

On `picome`, in `/home/ken/qwen-grpo`, I ran the exact full-suite command twice:

- all **893 tests passed**;
- both processes then exited **139**;
- with fault diagnostics enabled, teardown reported a segmentation fault with `sentencepiece._sentencepiece`.

Several individual conductor test files also reproduce the nonzero exit. Therefore [`170_f` §8](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/plans/conductor/170_f_stage_1_amend1_unit_c_repair.md:105) is incorrect in describing this as macOS-specific and absent on the execution box. This must be resolved or explicitly carried as a Unit D entry blocker; a process that exits 139 is not a green formal test run.

### Confirmed closed

The amended B driver/tag/root, canonical seed consumption, exact eight-row D telemetry, in-loop deadlines, C2 availability semantics and strengthened C-marginal identities are all correct. The focused repair suite passes **54/54**.

After one final narrow lifecycle/support repair—and correcting the teardown record—we should proceed to Unit D. Also remove the trailing whitespace in `169_s`, since `git diff --check` currently fails on that document.