Unit 4 is valid and can proceed to Unit 5 after a small record-only close-out. I found no reason to rerun the smoke or reopen the frozen prompt.

The execution order was correct:

1. Demo amendment and review corrections committed.
2. Final demo check passed 5/5 from cache with zero new generations.
3. Reward-blind format probe passed 144/144.
4. Prompt/profile/source fixture frozen.
5. Canary ran in the expected direction.
6. The single reward-bearing smoke ran afterward.

The persisted trace independently reproduces every reported metric, and 674 tests pass under warnings-as-errors. The subsequent exit 139 is the already-recorded teardown problem, not a test failure or Unit 4 regression.

## Findings to close before Unit 5

### 1. The demonstration effect is over-attributed

[124_f](/private/tmp/unit4-latest/plans/conductor/124_f_d16_stage_0_four_worker_unit_4_prompt_freeze_response.md:138) and `conductor_log.md` say that 48.3% success confirms a substantial demonstration prior. That is not identified by this experiment.

The 48.3% aggregates rollouts across 18 updating GRPO steps, so it combines:

- the pretrained model’s existing routing ability;
- few-shot conditioning;
- learning during the smoke.

The trace reinforces this ambiguity:

| Trajectory portion | Full success | Mean reward |
|---|---:|---:|
| First 144 completions | 56/144 = 38.9% | 0.694 |
| Second 144 completions | 83/144 = 57.6% | 0.785 |

That is consistent with rapid learning contributing, although this ordered integration schedule is not a controlled learning-curve experiment.

Replace the causal claim with something like:

> The few-shot-conditioned pretrained policy, while being updated for 18 GRPO steps, achieved 48.3% rollout success. This is consistent with a strong routing initialization and/or rapid early adaptation; the contribution of demonstrations is not identified by this smoke.

The registered untrained few-shot and no-demonstration comparisons remain necessary.

### 2. The executable-source freeze is narrower than claimed

[`SOURCE_DIGEST_FILES`](/private/tmp/unit4-latest/tasks/conductor/grpo_smoke.py:65) omits relevant transitive dependencies, including `pool_runtime.py`, `executor.py`, several generator/resource modules, canary fixtures, and the dependency lockfile.

Consequently, `verify_freeze()` could pass after some materially relevant runtime bytes changed.

This does not invalidate the completed smoke:

- none of the omitted source files changed between freeze and execution;
- the canary and retained trace are coherent;
- the listed digest verifies today.

Because editing `grpo_smoke.py` now would itself move the frozen source, I would not retroactively change it or rerun Unit 4. Instead, add a committed provenance addendum recording:

- the exact source commit/tree;
- `pyproject.toml` and `uv.lock` hashes;
- relevant runtime/fixture hashes;
- that the eight-file digest is a partial smoke-source digest rather than the entire executable environment.

Unit 5 should use a complete source/environment manifest for its own preregistration.

### 3. Content-address the retained run

The result currently depends on ignored files under `runs/`. Add their hashes and sizes to `124_f` or a small committed manifest:

| Artifact | SHA-256 |
|---|---|
| `actions.jsonl` | `8477c3f62cdb7f0d58001fe5403e3cbae04ef5a3e641ecde0d77a61b96b3dca7` |
| `summary.json` | `b76420f2ba8821d6a213d3c417435ff53f8819877343055a7d67e2231a3702bc` |
| `launch_profile.json` | `79a833e46464e73d16d3d60c96db6e4f66e23e3a089b5e2afa256e75587414ed` |
| `freeze_record.json` | `6cf44e2d145b7a0b681e075e5939ea3ac01139bb71dabd75289d87c053e80457` |

Include the run directory and W&B run ID `3satfxr9`.

### 4. Record three frozen-source errata

Do not edit the frozen source merely for these, but record them:

- [`policy.py`](/private/tmp/unit4-latest/tasks/conductor/policy.py:51) still says `STATUS: DRAFT`.
- [`run_demo_check()`](/private/tmp/unit4-latest/tasks/conductor/grpo_smoke.py:248) and its CLI help still claim both Code workers execute “every Code node.” Only the matched independent pair is cross-swapped.
- [124_f’s short-circuit paragraph](/private/tmp/unit4-latest/plans/conductor/124_f_d16_stage_0_four_worker_unit_4_prompt_freeze_response.md:32) confusingly refers to worker-2 step-2 evidence from `[2,3]`; step 2 there is worker 3. No worker-2 execution of that specialist step is required.

## What the smoke actually established

The end-to-end integration result is strong:

- 287/288 valid actions;
- exact 0/0.5/1 reward path;
- zero infrastructure aborts represented as reward;
- all four worker IDs sampled;
- both Code workers sampled at Code positions;
- 139 fully correct workflows;
- exact canary direction;
- 14.43 GiB peak reserved VRAM;
- 153.2 seconds for 18 updates.

The trace also contains real within-Code scale contrast, but only in one direction:

- `fork_join × goal_first`: `[0,2,1]` earned 1.0 while `[0,3,1]` earned 0.5 in the same group.
- `fork_join × bound_var`: the same contrast occurred.
- The reverse-direction `math_code × goal_first` winner using worker 3 was never sampled alongside worker 2 under an otherwise-correct assignment.

Thus the sampled policy generated two genuine scale-selection advantage groups favouring worker 2. It did not demonstrate bidirectional model-scale learning, nor was there a final-policy evaluation.

Signal was sparse: only 8/36 groups had any reward variance, with 7 containing both a winner and a lower reward. This passes the explicitly modest Stage-0 smoke gate, but reinforces the need for the ≥64-group cold-start analysis before Stage 2.

## Unit 5 readiness

Proceed after the documentation/provenance addendum. Unit 5 still needs to preregister CE0 before any new GPU command and measure:

- full-command materialization time, including model/tokenizer loading;
- peak VRAM across the worker phase;
- physical calls and disk footprint;
- projected complete Stage-2 seed time;
- first-seed versus amortized additional-seed cost;
- the final Stage-0 go/no-go handoff.

The preliminary evidence strongly favours pre-materialized routing. If it passes the full CE0 gates, the plan explicitly says not to implement co-residency or adapter toggling merely for comparison.