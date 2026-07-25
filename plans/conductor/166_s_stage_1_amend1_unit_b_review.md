Unit B is close, but I would hold Unit C for one targeted repair. The affected suite passes 124 tests, and the core statistic, alpha split, coupled-prefix generation, stopping rules, hard-path gates, and 48/120 artifact validation look sound.

### Blocking sign-off

1. **C does not use its frozen seed registry.**  
   [`run_c_path()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_persistence.py:393) derives 10,000 unregistered `path_key|trial` seeds, while the bundle registers one exact seed per C path. Seed one `PCG64` from that registered path seed and draw trials sequentially. A formal all-48 runner should consume these seeds, enforce the exact registry and 30-minute deadline; keep arbitrary throwaway domains in a separate probe helper.

2. **Structural eligibility is inferred from observed data.**  
   [`look_decision()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_persistence.py:151) chooses the structural bound whenever all observed `K_c==3`. The sharper bound is valid only when full eligibility is guaranteed by the registered design. Pass an explicit structural flag; C sets it only for `eligibility=1.0`.

3. **The inversion used by D6–D8 lacks the required independent reference check.**  
   The scalar probe compares `G_L/G_U/denominator_L`, but not independently calculated `L_p/U_p`. Add a row-level inversion reference, compare endpoints at `rtol=0, atol=1e-12`, and test complete pass/fail/unresolved agreement. At the same time, make [`_membership()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_persistence.py:219) use the frozen 64-epsilon variance rule instead of unconditionally clamping every negative value.

4. **The claimed complete §4.6 look record remains incomplete.**  
   It lacks equal-cluster and renderer-conditioned descriptive values, plus an explicit implementation/version and inversion-rule binding. Compact C/D artifacts can remain unchanged, but the production reporting API needs richer renderer-level input—or this must be explicitly assigned and frozen before qualification.

These are local corrections; no statistical redesign is needed. After that repair, proceed to Unit C.