The B diagnostic completed successfully and the results are credible. All 9,216 completions were reparsed and rescored, the provenance chain validated, and the committed report reproduces byte-for-byte. It gives us a useful cold-start picture for the routing-development stage.

| Prompt | Valid action | Mean reward | Predicted nonzero-variance groups | w2-favoured direct contrast | w3-favoured direct contrast |
|---|---:|---:|---:|---:|---:|
| Few-shot | 99.74% | 0.700 | 20.32% | 5.35% | 1.12% |
| Schema-only | 52.04% | 0.349 | 90.66% | 0% | 0.48% |

The direct-contrast columns are the predicted probability that a group of eight contains both relevant worker-2 and worker-3 actions.

### Main findings

1. **Few-shot should remain the P0 starting prompt.**

   Schema-only’s apparent abundance of gradient is misleading. Its JSON parse rate was 99.96%, but 2,210 actions failed the full schema:

   - 1,767 used quoted/string worker IDs;
   - 440 had the wrong number of actions;
   - only two were malformed JSON.

   Its reward variation is therefore mostly invalid `0` versus valid-but-wrong `0.5`. It would initially teach formatting, not model selection. The parser should remain strict.

2. **Few-shot is viable, but only barely supplies enough aggregate gradient.**

   Its predicted nonzero-variance rate is 20.32%, almost exactly the current 20% continuation floor. More importantly, the aggregate hides very different states:

   - `lookup_atomic`: essentially always correct and zero variance;
   - `lookup_math`: essentially always correct and zero variance;
   - `math_atomic`: essentially always **wrong** at reward `0.5`, also with almost no variance;
   - useful variation is concentrated in `code_atomic`, `fork_join`, and `math_code`.

   Consequently, mean reward could improve while some task families remain completely untouched.

3. **The actual worker-2 versus worker-3 learning signal is rare and initially reversed.**

   On w2-favoured observations, few-shot chooses worker 2 only 0.78% of the time and worker 3 33.6%. On the w3-favoured observation, it chooses worker 2 6.25% and worker 3 only 0.39%.

   This is scientifically interesting: the policy has strong, incorrect model preferences which GRPO could potentially reverse. But at group size eight, the direct corrective comparison appears in only:

   - about 1 in 19 w2-favoured groups;
   - about 1 in 89 w3-favoured groups.

   Once diluted across the full mixture, the latter may scarcely appear during P0.

4. **The few-shot prompt is strongly demo-shaped.**

   It produced only 32 distinct output strings across 4,608 samples. Several rows repeated one exact action all 256 times. Its dominant one-, two-, and three-step routes closely resemble the demonstrations.

   This makes the first training run particularly useful: we can observe whether GRPO moves beyond demonstration retrieval into payoff-sensitive routing.

5. **Renderer sensitivity is large.**

   For `code_atomic`, few-shot Code-worker selection varied from roughly 1% under `bound_var`, to 58% under `goal_first`, to 23% under `resource_first`. Similar changes occur for composite tasks.

   Renderer crossing and renderer-stratified telemetry are therefore load-bearing. A pooled reward gain could otherwise be a renderer shortcut.

6. **No direct-solution or runtime pathology surfaced.**

   Every completion began as a routing action; there was no systematic attempt to solve the underlying problem directly. There was one malformed suffix and one apparent 128-token runaway, but no general truncation problem. The repaired runtime also completed comfortably within budget.

### Changes I recommend before launching P0

The current [191_f development plan](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/plans/conductor/191_f_routing_training_development_track_launch_plan.md) should be revised using these priors:

- Run a zero-update probe through the **actual grouped rollout path** on fresh `routing_dev` observations. The B figures assume independent singleton draws and do not prove that real GRPO batches contain the same contrasts.
- Separate online variance into:

  - invalid versus valid-format variance;
  - valid `0.5` versus `1.0` semantic-routing variance;
  - direct worker-2 versus worker-3 contrast.

- Report these per cell, renderer, and payoff direction.
- Change the existing 5% co-sampling check from a pooled quantity to direction-stratified reporting. The w3 direction is already demonstrably below 5%.
- Treat co-sampling as an **early exposure diagnostic**, not a final success criterion. Successful convergence toward the favoured worker should eventually reduce co-sampling and reward variance.
- Track zero-variance groups by their reward level. “All reward 1” is convergence; “all reward 0.5” is a stuck policy.
- Ensure the P0 mixture contains enough direction-bearing Code observations in both directions. Keep natural-mixture holdout reporting separate from any contrast-enriched training slice.

I would retain group size eight for the initial baseline. If the actual grouped probe confirms insufficient exposure, group 16 raises the plug-in direct-contrast probabilities to approximately 11.5% and 3.8%; group 32 to roughly 21.6% and 10.2%. That should be a bounded configuration experiment because it costs approximately 2×/4× generation.

A useful later prompt candidate would be a minimally repaired schema prompt saying only that IDs must be JSON integers and there must be exactly one ID per listed step. That targets the observed formatting defect without injecting model-routing examples. I would not replace few-shot with it before observing P0.

### One evidence-closure item

The exact pinned Stage-0 payoff-surface files used by the verifier remain under an untracked `runs/` directory. Verification passes on the original `picome` checkout, but a clean checkout lacks those inputs. The original roughly 3 MB surface should be copied into the committed evidence archive with restore/path instructions.

That is evidence preservation only: it does not change the results or require another smoke, lock, or diagnostic run.

After that patch and a focused revision of 191_f, I recommend proceeding to P0. The most informative expected dynamic is now clear: stable syntax → generic worker-family routing → potentially sparse worker-2/worker-3 differentiation, with wrong deterministic basins and renderer shortcuts as the principal failure modes.