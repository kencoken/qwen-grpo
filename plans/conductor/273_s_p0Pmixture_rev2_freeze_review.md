## Verdict

Rev2 fixes the original findings correctly, but I would not sign it yet. One narrow gate-calculation defect and one inherited-requirement decision remain.

### Blocking: Q1 probability does not evaluate the frozen criterion

The criterion at [p0_mixture.py](/home/ken/qwen-grpo/tasks/routing/p0_mixture.py:119) requires two counted groups from at least two distinct latents. The calculation at [p0_mixture.py](/home/ken/qwen-grpo/tasks/routing/p0_mixture.py:545) only computes \(P(\text{at least two total successes})\); `min_distinct_latents_among_counted` is unused.

Under the same IID transport assumptions:

| Cell | Recorded | Correct ≥2-latent probability |
|---|---:|---:|
| `code_atomic` | 1.0000 | ≈1.0000 |
| `fork_join` | 0.9928 | ≈0.9826 |
| `math_atomic` | 0.9227 | ≈0.9085 |
| `math_code` | 0.9227 | ≈0.9085 |

The disposition remains above 0.9, but the frozen statistic and build-time refusal currently mean something different from the stated gate. Implement the latent-block occupancy probability, enforce the unrounded value, test exact figures, and regenerate identities.

### Blocking decision: renderer representation

The inherited Q1 gate also required at least two renderer strata. Rev2 silently omits that requirement.

For each math cell at five epochs:

- \(P(\ge2\text{ renderer strata}) \approx 0.8499\);
- \(P(\ge2\text{ latents and }\ge2\text{ renderers}) \approx 0.8394\).

Therefore the current mixture does not clear the 0.9 standard if renderer representation remains part of Q1. Before sign-off, either:

- retain it and rebalance the mixture/sample size; or
- explicitly supersede it with a scientific rationale.

It should not disappear implicitly.

### Scientific wording to tighten

Composite Q2 exposure is 18 worker-2-favoured versus 14 worker-3-favoured rows. Given the symmetric 1.0-versus-0.5 payoffs:

- always worker 2: 0.78125;
- always worker 3: 0.71875.

So “mixture imbalance cannot reward a constant-worker policy” is literally too strong. Either rebalance or describe this as bounded imbalance and disclose the fixed-worker advantage. Also report the Q2-only `goal_first` conditional—14 versus 14, exactly 0.5—alongside the current 0.576 figure that includes direct-specialist controls.

### Smaller item

Mirror the live-config guard in `tranche_freeze()`. Execution currently fails closed later, but the public freeze function can still produce a noncanonical self-hashed freeze after mutation.

### Verified as fixed

- Fork Q2 allocation is exactly 4 `bound_var` + 14 `goal_first`.
- Selection and live-config bypasses now refuse.
- True Q1 rates rederive correctly.
- `code_atomic→w3` is separated from Q2.
- Bridge predicate and exact quotas are enforced.
- Record `80343385…` and all documented identities rederive.
- Full suite: **999 passed** under warnings-as-errors.
- Diff check and worktree are clean.

One caution for Unit C: 785 groups project to approximately 0.944 GPU-hours, leaving only about 3.4 minutes beneath the ceiling. Its freeze should use a conservative runtime bound.

This needs only a narrow Rev3 and regenerated hashes; no broader redesign or Unit-A rerun is warranted.