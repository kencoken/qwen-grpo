## Verdict

The design is directionally strong, but I would not freeze Unit A yet. The Step‑7 interpretation is sound; the remaining issues concern executability and making Units A–C define one reproducible experiment.

### Blocking issues

1. **Unit B and Unit C are circular.**

   [Unit B says final weights come from Unit C](/private/tmp/review254/plans/conductor/254_f_p0_cohort_mixture_design.md:114), while Unit C claims to sample the exact candidate P0 mixture. Freeze the exact cohort, class membership, weights, and sampler before Unit C. Unit C may determine P0 duration and objective scope, but any cohort or weight change requires a new exact-mixture sample.

2. **The proposed Unit-A cohort cannot run through the existing API as written.**

   The current validator requires all six cells and complete renderer crossing, while the launch manifest requires per-cell prefixes and remains tied to the first-probe contract: [dev_support.py](/private/tmp/review254/tasks/routing/dev_support.py:59), [manifest validation](/private/tmp/review254/tasks/routing/dev_support.py:462). A Code-only `6–45` cohort is therefore currently rejected.

   The simplest resolution is a new, self-contained support-extension launch using the existing low-level surface machinery, with all six cells represented and prefix-shaped cohorts. A factor-balanced prefix such as `0–47`, while selecting new candidates from `6–47`, would also expand `math_atomic` for the C1 curriculum and avoid building composite partial locks. Crucially, the original `c_fixed_dev` must remain frozen and must not be reselected on this outcome-conditioned expansion.

3. **Renderer crossing is not the same as direction deconfounding.**

   A latent may be w3-favoured only under `goal_first` and tied under its other renderings. Including all three siblings balances renderer frequency, but all w3 labels can remain renderer-predictable.

   Unit A must define:

   - qualification from the per-renderer direction profile;
   - whether one latent can count for both directions;
   - quotas by cell × direction × renderer;
   - required non-`goal_first` coverage;
   - disposition at exactly two latents—the draft targets at least three but only scopes down below two.

   For the strongest objective, each direction should occur across multiple independent latents and multiple renderer strata within at least one common cell.

4. **Unit B is not yet a reproducible mixture.**

   The 35/45/20 classes overlap: a `math_code` observation can be bridge, direction, and anchor. Within-class cell, latent, renderer, tied-row and duplicate handling are unspecified.

   “Can show observable semantic variation” should be a deterministic predicate over authenticated payoff-surface geometry, not selection from lucky rollout groups. The bridge class should also retain the major measured C1 sources: tied `code_atomic` and `fork_join` rows produced 42 of the 46 semantic groups, whereas `math_atomic` and `math_code` produced only two each.

   Freeze an exact integer schedule or normalized sampler with mutually exclusive membership/precedence before Unit C.

5. **Unit-C gates need mechanical definitions.**

   “Positive” or “nonzero” currently allows one completion to authorize an objective. Freeze raw-count, denominator, latent and renderer requirements. Distinguish three development questions:

   - C1 family-routing learning;
   - hierarchical unlocking, where C1 improvement creates later C2 eligibility;
   - bidirectional within-cell specialist learning.

   A zero checkpoint-zero C2 count need not prevent the hierarchical-unlocking experiment—it may be its starting condition—but it cannot support a direct-C2-exposure interpretation. Any redesign after C is a new B/C iteration, not an in-place adjustment.

### Lifecycle and accounting corrections

The clean order is:

1. Unit A freeze/run/closeout.
2. Freeze the exact Unit B mixture.
3. Run Unit C and apply only its preregistered objective-scope/budget decision.
4. Freeze and materialize `routing_dev_val`; freeze the cycle cohort and checkpoint-selection rule; finalize `R_cycle`.
5. Run the `beta=1e-3` timing smoke.
6. Freeze P0 completely.
7. Run checkpoint-zero evaluation first, then training.

This should be recorded as the reviewed refinement of the charter sequence.

The Unit-A cost basis is understated: the proposed Code-cell expansion is about 27,360 planned node executions versus 4,824 previously, implying roughly 0.42 GPU-hours rather than 0.25. The 0.75-hour ceiling may still suffice, though a full six-cell prefix likely justifies 1.0 hour. The budget table must also include `routing_dev_val` materialization and reserve admission.

Finally, [“Envelope after Step 6”](/private/tmp/review254/plans/conductor/254_f_p0_cohort_mixture_design.md:197) should say “after Step 7—the execution/review of the Step‑6-frozen probe.”

### What should remain unchanged

The finite outcome-conditioned search, full disclosure, no ad-hoc widening, natural equal-cell evaluation, G=8 default, exact-mixture zero-update sample, beta timing smoke, checkpoint-zero-first execution, and C1→C2 trajectory reporting are all well judged.

So: **revise, then proceed to a separately reviewed Unit-A freeze. The architecture does not need restructuring.**