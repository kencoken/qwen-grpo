Verdict: Rev3 fixes the substantive scientific path, but it is not quite ready for prelaunch. The remaining issues are bounded lifecycle repairs; no redesign or freeze change should be necessary.

### Remaining blockers

1. **`engineering_smoke` admission is still bypassable.**

   The ledger validates the manifest only when one is supplied:

   ```python
   if launch_kind == "engineering_smoke" and launch_manifest is not None:
   ```

   I reproduced successful admission of a manifestless smoke with fabricated hashes. Make the manifest mandatory and validate its kind, budget, smoke-freeze identity, actual parent, initial lineage and aborted-retry state. The existing smoke-freeze hash can serve as the retry design identity.

2. **Accounting and deadline checks occur at the wrong lifecycle point.**

   `accountant.record_update(1)` runs inside the reward function—before the optimizer has consumed the rollout. Likewise, the training deadline check at reward entry occurs after generation.

   Move consumption to `on_optimizer_step`, add the established deadline check at `on_step_begin`, and cross-check accountant counters, trainer global step and instrumentation all equal 157 before checkpointing.

3. **Checkpoint and terminal verification remain weaker than claimed.**

   “Restore verification” currently rehashes files twice but never calls the existing `checkpoint.validate_resume`. After deletion, `checkpoint_proof` is the only evidence, yet its nested schema and counters are not validated. The terminal verifier also permits omitted or extra sealed files and is not automatically rerun after the complete closeout is appended.

   Call the established resume validator before deletion; validate the exact proof and four-file sealed inventory; enforce the exact terminal inventory; then run `verify_smoke_run` again against the completed ledger head.

4. **Abort cleanup violates the same discard/sealing rules.**

   An abort during P5, P6 or terminal verification leaves `checkpoint_bundle/` on disk. Earlier aborts can also leave raw training/evaluation JSONL traces because sealing occurs only on successful completion.

   Before writing an aborted closeout, seal any partial semantic traces and discard all trained state; hash the sanitized terminal inventory. A cleanup failure should remain visibly blocked rather than authorizing a retry.

### Correctly closed

- Conversational completions now use the established reward boundary.
- The complete 157-group training trace drives the ×39 term.
- Evaluation traces are priced and sealed within their phases.
- Evaluation RNG is isolated and the executed 90-seed realization is pinned.
- Console reward/KL reporting is removed.
- Environment-to-manifest binding is restored.
- Successful runs discard trained state.
- Rev3 hashes rederive and the full suite passes: **1,034 tests under warnings-as-errors**.
- Branch and diff checks are clean.

One narrow Rev4 with direct regressions for manifestless admission, callback ordering, abort cleanup and terminal-proof mutation should be sufficient for sign-off.