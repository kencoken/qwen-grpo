## Verdict

Do not sign Unit B yet. It needs a narrow CPU-only repair and refreeze; Unit A does not need rerunning.

### Blocking findings

1. **The implemented renderer allocation contradicts the frozen plan.**

   [270_f](/home/ken/qwen-grpo/plans/conductor/270_f_p0_mixture_freeze.md:32) specifies `fork_join→w2` as four `bound_var` plus fourteen `goal_first` rows. The code sorts using canonical renderer order at [p0_mixture.py](/home/ken/qwen-grpo/tasks/routing/p0_mixture.py:293), producing eighteen `goal_first` and zero `bound_var` rows. Consequently, all 37 Q2 rows are `goal_first`.

   All four intended `bound_var` candidates exist. Encode the renderer quota/priority explicitly in the frozen config, assert exact strata in tests, and regenerate identities.

2. **The Bridge mass has not been prospectively justified.**

   In the exact first 500 schedule rows, `math_code` receives 45 Bridge draws. Using the frozen `2/72` transport rate:

   - expected Q1 events: 1.25;
   - probability of zero: 28.1%;
   - probability of at least two: 35.7%, before requiring distinct latents/renderers.

   [270_f](/home/ken/qwen-grpo/plans/conductor/270_f_p0_mixture_freeze.md:76) proposes consistency bands around this weak projection. Such a band could accept zero exposure, which does not satisfy the all-four-cell Q1 purpose required by [269_s](/home/ken/qwen-grpo/plans/conductor/269_s_support_extension_execution_review.md:184).

   Freeze a meaningful positive exposure/representation criterion now, then rebalance Bridge mass or Unit-C size to give it adequate prospective pass probability. Alternatively, explicitly label this B1/C1 with a high expected stop rate—not the final option-1 candidate.

3. **The builder/verifier does not authenticate its supplied selection.**

   [build_mixture](/home/ken/qwen-grpo/tasks/routing/p0_mixture.py:229) checks only the selection’s surface-lock pointer. A modified selection can retain `c6c087…`, produce a different schedule, and pass [verify_mixture](/home/ken/qwen-grpo/tasks/routing/p0_mixture.py:469).

   Move expected-record and body-rehash validation into the consuming boundary. The secure loader should not be optional.

   Relatedly, mutating `MIXTURE_CONFIG` changes the schedule while it still reports the import-time frozen config hash. Add a live-config hash guard.

4. **The projection and Q2 labels change the intended estimands.**

   - The Q1 projection uses generic `semantic_contrast` and labels it Q1-counted. True Q1 additionally requires lower family correctness on the reward-0.5 route. For `code_atomic`, the real rate is 32/72, not 34/72; the projection is 5.33 rather than 5.67.
   - Five `code_atomic→w3` rows are counted as `q2_composite`, despite having no upstream unlocking step. The reported Q2 balance is therefore 18:19, whereas composite-only exposure is 18:14—still within the 1.5 limit.

   Either remove the atomic rows or classify them as a direct-specialist control, exclude them from Q2 gates, and preregister the transfer confound.

### Smaller corrections

- Report reward-relevant goal-first direction counts as well as the diluted `P(w3-favoured | goal_first)=0.229`; tied rows do not penalize a worker-3 shortcut.
- Enforce exact configured quotas—some `observations` fields are currently unused and short control pools silently underfill.
- Make `bridge_eligible` enforce the registered lower-family-correctness condition. The current 66 selected Bridge rows happen to satisfy it.

### Mechanical result

The implementation otherwise rederives correctly:

- 139 schedule rows, 132 unique observations;
- class masses 37/18/18/66;
- documented config, freeze and mixture hashes match;
- latent 42 remains screened and lookup Bridge quota is zero;
- full warnings-as-errors suite: **997 passed**;
- diff check and worktree are clean.

After the four substantive repairs and regenerated hashes, this should be ready for a short changed-lines review rather than another architectural round.