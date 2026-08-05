## Verdict

Unit Y is directionally sound, but I would **not sign it or append the final reserve yet**. Four bounded, CPU-only repairs remain; none requires another GPU run, and `R_cycle` should remain 1.0 GPU-hour.

### Blocking findings

1. **[P1] The future cycle surface is not completely frozen or authenticated.**

   [`_val_execution_identities()`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage1/tasks/routing/p0_cycle.py#L222-L236) validates a self-consistent Unit-V declaration/manifest pair, but does not cross-check those identities against the val-lock-bound surface. A rehashed mixed archive with a changed worker fingerprint is accepted.

   The cycle record also omits parts of the exact declaration required by 328_f §5: generator/profile versions, exact 90-row/4,020-step geometry, worker IDs, prompt revision, and semantic/rendered-prompt schedule hashes. Observation IDs alone would not catch a generator semantic change made without a version bump.

   Freeze a cycle-specific declaration now, authenticate inherited execution fields against the Unit-V surface lock, and require exact regeneration before any future worker call.

2. **[P1] The one-reveal comparison lacks a closed reporting rule.**

   The record fixes checkpoints, sampling, weights and CRN seeds, but not which metrics, denominators and aggregations will be reported after reveal. That leaves avoidable post-reveal discretion.

   Bind the frozen `P0ScienceContract` (`d47a63ff…`) and a closed cycle-report schema covering paired checkpoint-zero/final comparisons, natural-mixture aggregation, malformed handling, Q1/Q2 denominators, and cell/renderer strata. If repeated-versus-novel prompt reporting is retained, freeze that membership now; otherwise explicitly omit it.

3. **[P1] The itemized reserve is not yet “exactly recomputable.”**

   [`_ITEMIZED_CLOSURE`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage1/tasks/routing/p0_cycle.py#L345-L356) hand-enters `0.0637` and `0.2325`; tests only compare those literals with themselves.

   Instead:

   - derive `0.0637` from Unit-V closeout `929e1724…`;
   - derive the inference rate from the authenticated C2 record: `3648 / 785 = 4.64713 s/group`;
   - compute the two-checkpoint cost mechanically;
   - retain `0.05` as a named frozen allowance;
   - add an explicit policy/checkpoint-loading and evaluator-startup allowance.

   The total should still round to 1.0 GPU-hour.

4. **[P1] The final-reserve append is not bound to the frozen lifecycle.**

   [`record_final_r_cycle()`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage1/tasks/routing/p0_cycle.py#L460-L516) accepts any currently verified head. It can append before the Unit-V closeout, after an intervening entry, or append a second final reserve.

   Require:

   - current head exactly equals the cycle record’s frozen parent `929e1724…`;
   - no existing final reserve;
   - the exact Unit-V closeout is present and complete.

### Cheap accompanying repair

The final ledger validator currently checks only the cycle hash and resulting `1.0`. It accepts an arbitrary `r_cycle_record_file_sha256` and different cohort/multiplier values that happen to round to the same reserve. Compare the file hash and the complete persisted reserve projection against the strictly loaded record.

### Confirmed sound

- 90 outcome-blind observations: six cells × five latents × three renderers.
- Equal `1/90` natural-mixture weights.
- 720 unique CRN seeds, with no checkpoint index and no collision with validation.
- Fixed checkpoint-zero/final rule, abort handling, one reveal and retirement.
- Overlap disclosures match Unit V.
- Registered and itemized calculations both currently ceil to 1.0 GPU-hour.
- Real ledger remains untouched at `929e1724…`.
- Full suite passes: **1,033 tests under warnings-as-errors**; worktree and diff check clean.

I recommend one consolidated Rev2, regeneration of both record hashes, and then a narrow changed-lines/arithmetic review before the real reserve append.