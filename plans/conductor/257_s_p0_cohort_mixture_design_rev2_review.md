## Verdict

Rev2 is substantially better: the B→C circularity, lifecycle order, six-cell support shape, frozen comparator intent, renderer coverage, and mechanical Q1–Q3 thresholds are all improved.

I would not sign it yet. Three result-affecting issues remain.

### Blocking issues

1. **The Bridge predicate consumes the entire Anchor population.**

   [The predicate](/private/tmp/review256/plans/conductor/256_f_p0_cohort_mixture_design_rev2.md:122) defines every non-flat surface as Bridge. I checked it against the authenticated Step‑4 surface: all 108 observations—including every lookup observation—have exactly `{0.5, 1.0}` payoffs. Therefore, after Direction precedence, every remaining observation becomes Bridge and Anchor is empty. The proposed 45/35/20 mixture cannot be constructed.

   Prefer schedule-based selection:

   - Direction: matched selected direction rows.
   - Anchor: a fixed, all-cell, renderer-crossed identity subset.
   - Bridge: quota-selected C1-isolating rows from the remainder.
   - Screened-but-unused: disclosed rows with zero multiplicity.

   A stronger Bridge predicate would require an accessible reward-1 family-correct route and a reward-0.5 neighbour, with tied w2/w3 variants for Code-bearing C1 bridges where possible. But quotas are still needed because this may also be common.

2. **Q3 can still pass using different cells for the two directions.**

   Unit A correctly requires a [common cell](/private/tmp/review256/plans/conductor/256_f_p0_cohort_mixture_design_rev2.md:84), but [Unit C pools each direction across cells](/private/tmp/review256/plans/conductor/256_f_p0_cohort_mixture_design_rev2.md:157). Thus w2 exposure in `code_atomic` plus w3 exposure in `math_code` could pass while retaining the original cell shortcut.

   Predeclare the common Q3 cell or eligible common-cell set after Unit A. Both direction gates must pass within the same cell for “bidirectional within-cell specialist learning.” A one-direction pass should be labelled a direction-specific development result.

   The disposition matrix also lacks a Q2-failure branch: every listed outcome currently includes Q2. Add Q1-only or stop when Q2’s ≥8-completion gate fails.

3. **The support-extension execution contract remains internally inconsistent.**

   [Rev2 says](/private/tmp/review256/plans/conductor/256_f_p0_cohort_mixture_design_rev2.md:53) the lock covers prefix `0–47` but only indices `6–47` are materialized. The current materializer processes every declared observation, while the current high-level runner also reselects `c_fixed_dev`: [materializer](/private/tmp/review256/tasks/routing/dev_support.py:231), [runner](/private/tmp/review256/tasks/routing/support_run.py:393).

   The simplest honest contract is:

   - declare and process a complete new 864-observation `0–47` surface;
   - permit `0–5` to resolve as cache hits;
   - verify overlap payoff and terminal equality against the old locked surface;
   - persist the complete new surface and provenance;
   - never invoke comparator selection.

   Telemetry also currently rederives the comparator against the same expanded lock. It needs a boundary that verifies the original record against the original Step‑4 lock, extracts frozen worker 2, and applies that worker to expanded-surface ScaleLift without reselection. Only ScaleLift uses `c_fixed_dev`; C2 and ModelAcc remain surface-defined, so [line 67](/private/tmp/review256/plans/conductor/256_f_p0_cohort_mixture_design_rev2.md:65) should be corrected accordingly.

### Required at the relevant freezes

These do not require architectural redesign, but should become explicit gates:

- Unit A must freeze a total selector: bucket ordering, overlap handling when one latent qualifies multiple ways, subset/tie resolution, and a verifier that rederives the selected IDs.
- Unit B must require renderer-balanced direction multiplicities, not merely record renderer counts.
- Add direction-yield disclosure by observable subtype/public factors and a `cell + renderer + subtype` control. If subtype perfectly predicts the winner, the honest result is task-subtype routing—which is still orchestration—not finer instance-level adaptivity.
- Before Unit C, perform the charter’s code-invalidation audit. If scheduling changes touch rollout sampling/grouping, Unit C must be the complete fresh grouped reprobe and sole P0 exposure source.
- The later Step‑8/P0 freezes should incorporate the complete charter contracts by reference, including final `R_cycle` authorization, isolated evaluation RNG, full telemetry, optimizer/seed/provenance fields, and the ten-hour admission calculation.

### Feasibility

The revised ceilings look credible:

- 33,768 planned node executions for genuinely new indices `6–47`, approximately 0.51 GPU-hours by Step‑4 scaling;
- 38,592 if the entire prefix regenerates, approximately 0.59 hours;
- roughly 0.60 hours for 500 Unit-C groups.

So the one-hour ceilings are reasonable.

Once the Bridge partition, common-cell Q3 gate/Q2 disposition, and extension/comparator contract are corrected, the design should be ready for a narrow mechanical review and Unit-A implementation/freeze.