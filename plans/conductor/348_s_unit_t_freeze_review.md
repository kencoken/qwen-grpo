Verdict: Unit T is directionally sound, but I would not sign or launch freeze `168728b9…` unchanged. One bounded revision should close it.

### Blocking findings

1. **The workload does not fit its stated budget.**

   Three ~7-minute evaluation passes plus the predicted 12–16-minute epoch already require 32.9–36.9 minutes. That excludes startup, checkpoint writing, trace handling and archival, yet the ceiling is 36 minutes and the prediction says 21–27 minutes.

   Either raise the reviewed ceiling—approximately 0.75 GPU-hours—or preferably run checkpoint-zero and post-epoch evaluations once each, then conservatively use their maximum for intermediate/final pricing.

2. **The timing intervals overlap and do not yet represent the real P0 operations.**

   `startup_seconds` ends at the first optimizer update, while `whole_epoch_seconds` begins at the first rollout. The first rollout is therefore counted twice; checkpoint-zero evaluation would also overlap startup if run in production order.

   Define disjoint intervals. Additionally:

   - Time a complete resumable checkpoint bundle, not only the adapter.
   - Time the complete evaluation path—generation, parsing/scoring, telemetry and sealed trace persistence—not generation alone.

3. **The validator does not prove the frozen training shape.**

   I reproduced acceptance of:

   - a completely flat learning rate;
   - a ramp to the wrong learning rate;
   - a 10-second epoch containing 157 five-second rollout timings.

   Freeze the LR sampling point and validate the exact `1e-5`, 10-update `constant_with_warmup` trajectory within a stated tolerance. Require the epoch wall time to contain all sequential group timings. Rev2 should also prove that the beta/reference-logprob path and 157 optimizer updates actually executed, without exposing semantic metrics.

4. **The purported freeze is not yet an executable identity boundary.**

   The runtime profile is pinned, but the science contract, 157-row mixture/order, actual prompt, extension surface and evaluation decoding/seed schedule remain prose, abbreviated hashes or dynamically loaded state. Persist the freeze, bind the complete hashes and ordered schedules, and require a strict loader/admission boundary before GPU execution.

   The timing-only disclosure also needs operational enforcement: disable W&B/reward logging and completion printing, capture/seal trainer logs and semantic traces, and expose only the generated timing projection.

### Minor issue

`round(..., 1)` can round cap inputs downward. Preserve exact values or conservatively round upward.

### What passed

- Unit Y closed correctly at `6fea9e3b…`; 20 ledger entries verify.
- The 90 timing observations are unique, development-only and on the authenticated extension surface.
- Cadence arithmetic is correct in epochs and update units.
- The closed measurement dictionary rejects additional semantic fields.
- Full suite: **1,034 passed under warnings-as-errors**.
- Branch is clean, aligned with the remote, and the diff check passes.

The deferred GPU runner is not itself a Rev1 defect. After correcting the frozen design above, Rev2 can implement the two-phase runner and prelaunch admission without reopening the overall Unit T approach.