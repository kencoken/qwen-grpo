## Verdict

Unit C is valid and should be closed as a genuine `STOP-AND-REVIEW`. The archive verifier passes, all 785 groups and 6,280 completions reconcile, the adapters remained unchanged, and the run stayed within budget. The current freeze does not authorize P0.

## What the result tells us

The aggregate Q1 projection was remarkably accurate, but its allocation across cells was not:

| Cell | Projected | Observed |
|---|---:|---:|
| `code_atomic` | 26.7 | 32 |
| `fork_join` | 6.7 | 3 |
| `math_atomic` | 4.2 | 0 |
| `math_code` | 4.2 | 7 |
| **Total** | **41.7** | **42** |

So this is not a lack-of-gradient problem globally. It is a cell-specific cold-start and transport failure.

The critical result is stronger than just `0/150` groups: all 1,320 `math_atomic` completions across Bridge and Anchor selected exactly `[0]`. There is effectively no checkpoint-zero exploration of worker 1 on atomic Math under this prompt and sampling configuration. Increasing `math_atomic` multiplicity would therefore mostly buy more identical zero-gradient groups.

Q2 remains viable, but should not be oversold:

- Both marginal-support gates passed comfortably.
- C2 eligibility was nonzero in both directions.
- However, each direction produced only two reward-bearing contrast groups.
- `fork_join`’s Q1-positive groups were all `goal_first`.
- The worker-3 signal remains renderer-confounded.

This supports a sparse hierarchical-unlocking experiment, not an already-demonstrated specialist-learning signal.

No training occurred, so nothing here says whether GRPO can learn, transfer into `math_atomic`, avoid collapse, or improve Q2.

## Two corrections to `282_f`

Before moving on:

- Replace the stated preflight `24,079 MiB`. The authenticated archive records `23,687 MiB` free and `24,082 MiB` total.
- Soften “the transport assumption itself failed for the new bridge latents.” The original evidence consisted of only two singleton successes, and those exact observations also failed to reproduce in Unit C. The defensible conclusion is:

  > The homogeneous per-cell transport projection did not reproduce; the atomic-Math tail is too rare, heterogeneous or seed-unstable to support the frozen exposure guarantee.

The quoted 1.5% calculation is useful as a plug-in diagnostic, but not a calibrated p-value.

## Recommended route

I recommend one outcome-informed Unit-B2/C2 iteration, rather than changing models, prompts or temperature before the first training run.

Amend the scope to:

- direct Q1 authorization: `code_atomic`, `fork_join`, `math_code`;
- Q2: hierarchical unlocking and coarse cell-conditioned worker choice;
- `math_atomic`: a delayed-unlocking/dead-basin sentinel, not a direct-exposure requirement.

Keep the small `math_atomic` Anchor presence so we can observe whether learning the Math node through `math_code` eventually causes atomic Math to begin varying and then self-reinforcing. Do not call this a pure held-out-transfer test.

Reallocate the 84 Bridge rows away from the currently dead `math_atomic` block. A defensible exposure-balanced starting point is:

- `code_atomic`: 6 rows — 2 complete-renderer-crossed latents;
- `fork_join`: 39 rows — 13 latents;
- `math_code`: 39 rows — 13 latents.

The locked support can fill those quotas. Selection should remain canonical and outcome-independent within the eligible pools—no choosing the rows that happened to succeed in Unit C. Preserve Q2 composites, controls and Anchor unchanged.

This projects roughly 3.2, 2.0 and 1.8 Q1-counted groups per epoch respectively, bringing a 100-group sizing target close to the ten-hour P0 envelope instead of the current approximately 33-hour derivation.

Then:

1. Freeze Unit B2 with new identities and the narrowed estimand.
2. Run one fresh-seed, exact-schedule Unit C2—do not retry or overwrite Unit C1.
3. Retain the existing per-cell Q1 and per-direction Q2 gates, applied to the amended scope.
4. If C2 passes, proceed with `routing_dev_val`, cycle-holdout/`R_cycle`, the beta timing smoke, and the final P0 freeze.
5. During P0, explicitly track the first non-`[0]` atomic-Math action, first varying atomic-Math group, and its evaluation trajectory alongside C1 and C2 unlocking.

If that P0 still leaves `math_atomic` immobile, the next experiment should isolate exploration: legal-action likelihoods followed by a bounded global-temperature probe. A direct Math demonstration is a later option, but it would change the capability prior substantially and require a complete new prompt profile and B/C validation.

This route gets us to actual training while preserving the most interesting failure mode Unit C uncovered.