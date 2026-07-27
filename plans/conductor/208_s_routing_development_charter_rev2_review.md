## Verdict

207_f closes nearly all findings from 206_s correctly. The support-materialization tranche, stable natural-mixture definition, checkpoint-zero baseline, C1/C2 telemetry, strict probe-to-P0 binding, deadline handling and provenance rules are all substantially improved.

I would make one final narrow erratum before sign-off. No further broad redesign is needed.

## Remaining findings

1. **Checkpointing still permits an unsafe boundary.**

   Section 11 allows a checkpoint between generation and its consuming update “without recording which.” Recording the identity is insufficient: the current GRPOTrainer does not checkpoint its buffered rollout inputs and will regenerate them after resume.

   For the simple v1 contract, require checkpoints only after the optimizer has consumed the complete generation buffer. Otherwise the full completions, token IDs, masks, log-probabilities, rewards and buffer cursor would need persistence.

   The interrupted/uninterrupted test should also compare:

   - final adapter, optimizer and scheduler state—exactly or under a frozen tolerance;
   - next sampler/renderer identity;
   - counters and merged trace cardinality.

   Because §15 currently runs this test after the grouped probe, state that any resulting fix touching rollout generation, sampling, grouping, parsing or reward code invalidates and reruns the probe. Alternatively, move the GPU resume test before the probe.

2. **Evaluation payoff surfaces remain absent from the P0 lifecycle.**

   Section 4 now correctly handles `routing_dev`, but checkpoint-zero and later evaluation require authenticated surfaces for `routing_dev_val`.

   Add a mandatory pre-P0 sequence:

   - outcome-blind freeze of the exact `routing_dev_val` cohort, renderer schedule, weights and evaluation seeds;
   - complete surface materialization and authentication;
   - lock binding the resulting cohort and surface hashes;
   - checkpoint-zero evaluation;
   - then training.

   For `routing_dev_cycle`, freeze its cohort and checkpoint-selection/evaluation rule before P0, but preferably materialize its surfaces only at cycle synthesis. That preserves the one-reveal discipline. Then archive and permanently retire it.

   This does not block the presently authorized support/probe tranches because P0 remains unauthorized, but it should appear explicitly in the charter’s full order.

3. **Reserve cycle-end evaluation budget.**

   The 60-hour envelope can presently be exhausted before the cycle holdout is materialized and evaluated. Once support timing is known, reserve a measured `R_cycle` for:

   - cycle-surface materialization;
   - selected-checkpoint inference;
   - verification, traces and archival.

   A new launch should require:

   `remaining budget ≥ launch maximum + R_cycle`.

4. **Make outcome-blind probe selection mechanically auditable.**

   Freeze the exact grouped-probe prefix length/selection rule before worker execution—not merely the larger candidate prefix and search cap. After materialization, only surface hashes should be filled in; observed direction yields must not influence the first probe cohort.

5. **Move projected P0 counts to the P0 proposal.**

   Section 5 asks the probe report to project informative-group counts under the proposed P0 budget, but that budget is chosen only after reviewing the probe. The probe should report authenticated rates, counts and denominators. The later P0 freeze should calculate projected counts using those results.

6. **Tighten the C2 denominator.**

   Define C2 as optimal specialist selection conditional on:

   - all non-Code nodes being family-correct; and
   - the Code choice being in `{2,3}`.

   Wrong-family Code choices remain incorrect rather than disappearing from the broader `ModelAcc` denominator. “Incremental lift” should use the existing best-fixed-Code `ScaleLift` comparison, not generic checkpoint-to-checkpoint reward lift.

## Small lifecycle clarifications

- An aborted/incomplete grouped probe cannot be reported as the completed exposure estimate. Partial evidence may motivate a separately frozen continuation.
- Evaluation must use isolated RNG state—or save and restore training RNG—so checkpoint evaluations do not change subsequent rollout sampling.
- Ensure the execution digest includes the actual training driver, not only `tasks/conductor/*.py`.
- The companion B payoff-surface bundle is still absent. Under 207_f’s own §15, it remains a prerequisite to final sign-off.

With these targeted corrections and the companion bundle committed, I would sign the charter for infrastructure, support materialization and the group-eight zero-update probe. The overall design is now on solid footing.