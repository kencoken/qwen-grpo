## Verdict

The plan has the right overall architecture, but I would request one revision before signing it or starting Unit V. The cohort design and V → Y → T → L progression are sound; the remaining issues concern reserve accounting, timing isolation, and launch identity.

### Blocking findings

1. **`R_cycle` and the P0 finalization reserve are conflated.**

   In lines 15–16, the existing 5 GPU-hours is called a “provisional finalization reserve.” It is actually the provisional cycle-end reserve, `R_cycle`, established by 231_f.

   Lines 98–100 then imply that the beta smoke’s finalization measurement replaces those 5 hours. It must not. These are separate quantities:

   - Unit Y must produce a numeric final `R_cycle`, covering cycle-surface materialization, selected-checkpoint inference, verification, traces and archival. It should bind the cycle record, retain the registered 231_f basis and rounding rule, and replace the provisional reserve in the ledger.
   - Unit T must separately measure the P0 run’s `measured_finalization_reserve_seconds`.

   The `r_cycle_record_sha256` should therefore identify a reserve record, not merely the checkpoint-selection rule.

2. **The timing smoke would touch `routing_dev_val` before checkpoint zero.**

   Lines 101–103 propose timing evaluation on the exact locked validation cohort. That would generate policy outputs on it before the required checkpoint-zero baseline and before the P0 launch freeze.

   Prefer a shape-matched, already-development-exposed `routing_dev` timing cohort. Alternatively, define a strictly reward-blind, semantically hidden timing operation with a distinct seed, but the disjoint cohort is cleaner.

   The one-epoch training smoke itself is reasonable, provided it has:

   - a dedicated seed, run root and execution identity;
   - only timing, memory and infrastructure results disclosed before P0;
   - no checkpoint or observed learning result reused in P0;
   - enough retained provenance to verify what ran.

3. **The cap and cadence calculation is not yet executable.**

   Lines 117–121 say cadence is “chosen” through `derive_launch_plan`, but that function does not choose cadence. It receives a precomputed `frozen_non_rollout_overhead_seconds`.

   The plan needs a deterministic mapping from measurements to:

   - `measured_whole_epoch_seconds`;
   - `measured_finalization_reserve_seconds`;
   - `frozen_non_rollout_overhead_seconds`;
   - P0-local `cumulative_consumed_seconds`, normally zero at a fresh launch—not the 3.1305-hour cycle spend.

   The finalization reserve must cover the charter’s worst-case rollout batch, final evaluation, checkpoint write, trace flush and archival. Scheduled intermediate evaluations/checkpoints belong in non-rollout overhead, without double counting.

   Freeze either a simple cadence rule before Unit T or a bounded, reviewed cost-only decision table. A particularly simple solution is to price a fixed nominal-horizon cadence conservatively, derive the epoch cap once, and trim out-of-horizon indices without reclaiming the reserved time.

4. **Unit L reverses the signed identity graph.**

   Lines 116–127 currently create `P0ExecutionIdentity` before `P0LaunchFreeze`. The frozen order is:

   `P0ScienceContract → P0LaunchFreeze → P0ExecutionIdentity/admission`

   Correct sequence:

   1. Resolve precursors and derive the launch plan.
   2. Build, persist and externally review the `P0LaunchFreeze`.
   3. Construct an authenticated `P0ExecutionIdentity` binding that reviewed freeze hash, exact cadence/index sets, evaluation configuration and telemetry schema.
   4. Perform admission using the external execution manifest and live environment attestation.

   The P0 training seed also needs to be frozen explicitly and kept distinct from validation, cycle and timing seeds.

5. **The cycle record needs a stronger frozen meaning.**

   Before deferring its surfaces, bind the exact cycle declaration: generator/profile identity, ordered observation IDs, renderers and weights, worker/prompt/request/surface identities, evaluation seed, checkpoint rule and future materialization plan. Existing declaration and verifier machinery should be sufficient.

   Also resolve “final P0 checkpoint”:

   - preferably declare that P0 closes this development cycle before any continuation or fork; or
   - define a structural lineage rule now.

   “Last complete checkpoint” should apply only after a terminally closed abort, not a resumable interruption. If no positive checkpoint exists, the zero-versus-final comparison should be undefined rather than evaluating checkpoint zero twice.

### Smaller clarifications

- Namespace-bearing IDs prove identity separation but not semantic separation. Add cheap zero-overlap checks for latent semantics and rendered policy prompts across training, validation and cycle populations.
- With five latents per cell, the effective cell-level sample size is five. That is acceptable for a cheap development monitor, but results should be described as paired, latent-level descriptive evidence—not completion-level precision.
- Bind exact ordered observations, batching, generation options and domain-separated seed derivation, rather than only one integer seed and three decoding fields.
- Define the normal abort/retry rule: partial materializations cannot be locked; identical-design retries receive new execution identities and cumulative accounting; material design changes require a reviewed successor.
- Restate at launch that P0 studies Q1 plus coarse, cell-correlated Q2 hierarchical unlocking; Q3 remains out of scope.

### What is already right

The six-cell outcome-blind prefixes, complete renderer crossing, natural-mixture weights, authenticated `4^S` surfaces, never-train validation separation, deferred one-reveal cycle surfaces, and fixed zero/final selection are all appropriate. The ceilings are plausible: Unit V is exactly 90 observations and 4,020 planned step executions, so its 0.35-hour ceiling has ample headroom. I also verified the stated ledger head, 17 entries and 3.1305 GPU-hours consumed.

After the above corrections, the precursor plan should be ready to sign and Unit V can begin.