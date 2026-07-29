## Verdict

Rev3 is very close. The major architecture is now sound: full-prefix support, immutable `c_fixed_dev`, schedule-based mixture construction, common-cell Q3, Q2 failure handling, lifecycle order, and compute ceilings are all materially correct.

I would make three narrow corrections, then sign the design and stop iterating at the architecture level.

### 1. Q1 can still be contaminated by C2 variation

[Code-bearing Bridge rows require tied variants only “where available”](/private/tmp/review258/plans/conductor/258_f_p0_cohort_mixture_design_rev3.md:23). Consequently, an unselected payoff-distinct observation can enter Bridge, and a group varying only between workers 2 and 3 can count toward the inherited Q1 “semantic group” gate. That would authorize “family-routing exposure” using specialist-selection variation.

Fix:

- Require tied, reward-1 w2/w3 variants for every Code-bearing Bridge row.
- Send unselected payoff-distinct rows to Direction or Screened-but-unused—never Bridge.
- Define the Q1 counted event explicitly: the group must contain a reward-1 family-correct assignment and a reward-0.5 assignment with lower family correctness, preferably an otherwise-identical correct-family↔wrong-family neighbour.

Also impose direction/renderer balancing over the complete Unit-B schedule, not only the Direction class. The proposed Anchor already contains two known w2-favoured `fork_join` observations at latent 1; these are legitimate anchor rows, but their direction exposure must be included in the balance calculation.

### 2. The selector still contains a contradictory overlap rule

[Rev3 says the first matching bucket consumes a latent](/private/tmp/review258/plans/conductor/258_f_p0_cohort_mixture_design_rev3.md:92), while it carries Rev2’s direction qualification forward unchanged—even though Rev2 allowed one latent to count toward both directions under different renderers.

Choose one rule explicitly. I recommend:

> A latent is assigned globally to at most one direction bucket; Rev3 supersedes Rev2’s dual-direction counting rule.

That produces direction-disjoint latent sets. A renderer-induced winner reversal within the same latent should remain a useful diagnostic, but it is not the strongest evidence of semantic specialist selection—it primarily demonstrates renderer sensitivity.

The Unit-A freeze can then supply the exact bucket order and canonical subset verifier.

### 3. Complete two remaining mechanical clauses

- [The invalidation audit](/private/tmp/review258/plans/conductor/258_f_p0_cohort_mixture_design_rev3.md:107) currently names only sampling/grouping. Restore the complete charter scope: rollout generation, sampling, grouping, parsing, and reward. Repeat this audit at P0 freeze so a post-C repair cannot inherit C’s exposure evidence.
- Clarify whether Q1 “pass” in the [disposition matrix](/private/tmp/review258/plans/conductor/258_f_p0_cohort_mixture_design_rev3.md:53) means all four critical cells pass, superseding Rev2’s per-cell drops, or whether partial Q1 is allowed. The former is simpler. Also phrase Q2 failure as “maximum permissible scope becomes Q1-only; the P0 freeze decides whether its projected exposure justifies launch.”

### What is now correctly resolved

- The [complete 864-observation surface contract](/private/tmp/review258/plans/conductor/258_f_p0_cohort_mixture_design_rev3.md:63) is honest and implementable with a new runner.
- Old/new overlap equality is checked before lock acceptance.
- Comparator selection is excluded; only ScaleLift consumes frozen worker 2.
- Anchor and Bridge are quota-selected rather than an impossible predicate partition.
- Q3 requires both directions within the same predeclared cell.
- One-direction success is correctly labelled direction-specific.
- The approximately 0.51–0.59-hour Unit-A and 0.60-hour Unit-C projections support the one-hour ceilings.

At Unit A, require tests proving overlap validation occurs before locking, comparator selection is unreachable, the original comparator is verified against the original lock, and the deadline is enforced. The detailed Unit-B schedule, Unit-C runner, and final `R_cycle` implementation should block their respective freezes—not this design’s sign-off.

After the three narrow textual corrections above, I recommend signing and proceeding to Unit-A implementation/freeze.