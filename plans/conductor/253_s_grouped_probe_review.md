## Verdict

Step 7—the execution and review of the Step-6-frozen grouped probe—is valid and should be accepted. Both live and committed archives independently verify `PASS`; the ledger, counters, adapter hashes, environment, and terminal inventory agree. No rerun is needed.

Before using [252_f](/private/tmp/review252/plans/conductor/252_f_grouped_probe_executed.md:63) as the P0 decision record, make a small erratum:

- Zero-variance is **380/432 = 87.96%**, not ~84%.
- There were **18 total** exact worker-2/worker-3 co-sampling groups: 15 tied and only **3 payoff-distinct**. Say “3 payoff-distinct contrasts,” not “3 exact contrasts.”
- All three payoff-distinct contrasts came from one `code_atomic / goal_first` observation—one latent, not three independent examples.
- Of the 72 support-matrix entries, 36 are structurally impossible. The informative statement is **22/36 admissible strata measured; 14 missing**.
- Restore the full pre-P0 sequence: prepare `routing_dev_val`, freeze the `routing_dev_cycle` cohort/rule, finalize `R_cycle`, then freeze P0. Probe trainer timing should not directly resize the cycle-evaluation reserve.

The underlying [probe report](/private/tmp/review252/plans/conductor/evidence/grouped_probe_v1/probe_report.json) is correct.

## What the Step-7 execution and review taught us

Formatting is not the bottleneck: parsing was 100% and validity 99.8%. Of 432 groups:

- 380 were zero-variance;
- 212 were stuck at all-0.5;
- 168 were saturated at all-1;
- 46 contained useful semantic 0.5-versus-1 variation;
- 6 contained only format-related variation.

The pooled reward of 0.721 therefore hides radically different states:

| Cell | Semantic groups | Zero-variance | C1 family routing | Interpretation |
|---|---:|---:|---:|---|
| `lookup_atomic` | 0/72 | 72/72 | 100% | Saturated |
| `lookup_math` | 0/72 | 72/72 | 100% | Saturated |
| `math_atomic` | 2/72 | 70/72 | 0.35% | Deep wrong-worker basin |
| `code_atomic` | 34/72 | 38/72 | 64.6% | Main immediate learning signal |
| `fork_join` | 8/72 | 64/72 | 51.4% | Sparse composition signal |
| `math_code` | 2/72 | 64/72 | 34.5% | Family routing gates specialist learning |

The most interesting result is genuinely hierarchical. On worker-3-favoured `math_code`, ModelAcc is 20/64: the model sometimes places worker 3 at the Code step. But C2 eligibility is 0/64 because it never simultaneously routes the Math step correctly. Thus the specialist choice is present, but cannot earn reward until family/topology learning unlocks the complete workflow.

That suggests an expected learning sequence:

1. Syntax remains stable.
2. C1 family routing improves—especially Math.
3. C2 eligibility begins rising on composite tasks.
4. Only then can worker-2/worker-3 differentiation and ScaleLift improve.
5. Reward variance may initially rise as the policy escapes all-0.5 basins, then fall again as it converges.

This is exactly the hierarchical training dynamic the toy experiment is meant to expose.

The current fine-grained model-selection evidence is nevertheless too confounded:

- worker-2 wins occur only in `code_atomic`/`fork_join`;
- worker-3 wins occur only in `math_code`;
- worker-3 wins occur only under `goal_first`;
- all three observed payoff-distinct direct contrasts came from one worker-2-favoured observation;
- ScaleLift is currently negative: −0.0062 overall.

A policy could therefore learn a cell/renderer lookup rather than semantic model selection. Without within-cell bidirectionality, the honest claim is “family routing plus task-class-conditioned model choice,” not adaptive per-instance specialist selection.

## Recommended P0 design

1. **Expand the structural training support first.**

   Use an outcome-conditioned but byte-reproducible search over additional `routing_dev` latents. Select at latent level with complete renderer crossing. Seek:

   - both winners within the same cell;
   - worker-3-favoured cases outside `goal_first`;
   - multiple independent latents per cell/direction;
   - balanced renderer support.

   Select using authenticated payoff surfaces, not which observations happened to produce lucky stochastic contrasts in this probe.

2. **Use a deliberately enriched fixed training mixture.**

   Include:

   - C1 bridge rows with observable semantic variation;
   - balanced worker-2/worker-3 direction rows;
   - a small all-cell anchor.

   Downweight the saturated lookup cells during training while retaining all cells. Keep evaluation on the frozen natural equal-cell mixture.

3. **Run the required zero-update sample on the exact candidate P0 cohort and mixture.**

   Before freezing P0, require evidence of:

   - semantic exposure in every cell whose learning is part of the P0 claim;
   - positive C2 eligibility on worker-3-favoured composites;
   - nonzero marginal support for both exact specialist alternatives;
   - payoff-distinct exposure in both directions across more than one latent.

   If this cannot be achieved, explicitly scope P0 as a C1/unlocking experiment rather than bidirectional C2 learning.

4. **Keep group size 8 initially.**

   A post-hoc conditional calculation predicts about 48.7 informative groups versus 52 observed, and 15 direct contrasts versus 18 observed. The main failure is therefore near-zero marginal probability for complete rewarding workflows—not pathological G8 batching. Increasing group size cannot rescue an action with probability zero.

   Consider G16 only if the exact-cohort sample shows both alternatives have nonzero probability but co-sampling remains insufficient. That would require the registered 4090 smoke and grouped reprobe.

5. **Size P0 from raw exposure counts, not an inherited update count.**

   At beta zero, the measured rate is 4.33 seconds/group: roughly 2.4 hours for 2,000 groups or 3.6 hours for 3,000. If retaining the intended `beta=1e-3`, run a short timing smoke because KL computation changes throughput.

   A reasonable design exercise is to target roughly:

   - order 100 semantic-gradient groups per critical C1 component;
   - 30–50 payoff-distinct contrasts per direction, if structurally achievable.

   Final counts, mixture weights, updates, and checkpoint cadence should come from the exact-cohort exposure sample.

6. **Preserve the key trajectories.**

   Report C1, C2 eligibility, C2 optimality, ModelAcc, ScaleLift, all-0.5 versus all-1 groups, entropy, and renderer-stratified behavior. Treat groups as repeated rollout draws and latents as the meaningful independent task unit.

Overall, the Step-7 execution and review of the Step-6-frozen probe did its job: it showed that compute and formatting are healthy, while the real difficulty is escaping a low-entropy routing prior and unlocking specialist reward through correct hierarchical composition. The next step is constrained P0 cohort/mixture design—not launching P0 directly.