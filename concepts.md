# Concepts

A companion to [`experiment_log.md`](experiment_log.md). The log is
chronological — what we ran and found, in order. This file is the opposite:
the standing mental models that outlive any single run, refined as we learn.
Each experiment that sharpens one of these links back here.

---

## Gradient sparsity: the variable that governs whether GRPO learns

*Distilled from Phase A (E1–E7, GSM8K) and Phase C prep (E8, Countdown). This
is the single most useful lens we've found for predicting GRPO behaviour.*

### p — the per-problem success probability

Every problem has a hidden number `p`: the probability that **one** sampled
completion solves it, for a given model and temperature. It's a property of
*one problem*, not the dataset. "Natalia sold 48 clips…" might sit at p≈0.98
for a 7B; a hard combinatorics problem at p≈0.1.

So a dataset is not described by a single number — it's a **distribution of p
across its problems**. This is the thing that actually matters, and the thing
aggregate metrics blur.

We can't see p directly; we estimate it by sampling. 8 rollouts giving 3
successes → p̂ ≈ 0.375 (coarse per problem, stable once averaged over a few
hundred).

### Groups, advantages, and "carrying gradient"

One GRPO step on one problem: sample `k` rollouts (we use k=8), score each,
compute **advantage = reward − group-mean reward**, push up the
above-average rollouts and down the below-average ones.

The load-bearing fact: **if all k rollouts get the same reward, every
advantage is exactly zero** — all-correct and all-wrong groups produce *no
gradient*. A group only teaches the model something when its rollouts
**disagree**. With one problem per step, the fraction of groups that disagree
is literally the fraction of your optimizer steps that aren't no-ops — the
fraction of compute that isn't wasted.

### g(p) — the gradient-carrying probability

For a problem with success probability p, over k rollouts:

```
P(all correct) = p^k
P(all wrong)   = (1−p)^k
g(p) = P(mixed) = 1 − p^k − (1−p)^k
```

g(p) is a **bump: zero at p=0 and p=1, peaking at p=0.5.** For k=8:

| p    | 0.05 | 0.1  | 0.2  | 0.3  | 0.5  | 0.7  | 0.8  | 0.9  | 0.95 | 0.99 |
|------|------|------|------|------|------|------|------|------|------|------|
| g(p) | 0.34 | 0.57 | 0.83 | 0.94 | 0.99 | 0.94 | 0.83 | 0.57 | 0.34 | 0.08 |

Two things to read off it:

1. **The plateau is wide.** g stays above 0.8 across roughly p ∈ [0.2, 0.8].
   A problem the model solves "usually but not always" (p=0.7) still gives
   g=0.94 — 8 rollouts almost always include a failure. Being *good* at a
   problem doesn't kill its gradient.
2. **The cliffs are near the extremes.** g only crashes once p>0.9 (or
   p<0.1). A problem has to become *reliable* (p>0.9), not merely *likely*,
   before its groups start going uniform.

### Relationship to pass@1 / pass@8

Both pass metrics are **dataset averages** over the per-problem p's:

- **pass@1 = mean(p)** — average single-shot success (mastered capability).
- **pass@8 = mean(1 − (1−p)^8)** — fraction solvable within 8 tries (latent
  capability).
- **g = pass@8 − (fraction all-8-correct)** = mean of g(p). pass@8 removes
  the all-wrong collapse; subtracting all-8-correct removes the all-correct
  collapse; the mixed middle is what's left.

**Why pass@1 alone is the wrong difficulty axis.** Two datasets, identical
pass@1 = 0.5:

- *A:* every problem p=0.5 → pass@8=0.996, all-8-correct=0.004, **g=0.99**.
- *B:* half the problems p=1, half p=0 → pass@8=0.5, all-8-correct=0.5,
  **g=0** — every group is uniform, training does nothing.

Same average capability, opposite training behaviour. pass@1 can't see it;
g can. The **pass@1↔pass@8 gap** is the useful pair: it's the *inconsistency*
(can-sometimes minus can-reliably), and that gap is exactly GRPO's raw
material — a large gap at low pass@1 is the richest training regime.

### The two collapse modes live in different task types

g collapses two ways, and *which* way is a property of the task, not just its
difficulty:

- **Collapse from above (all-correct).** Needs problems at p>0.9. Only
  **elicitation** tasks supply these — things the model already does
  reliably. GSM8K-instruct has a big mass at p>0.95; those problems sit on
  the right cliff (g≈0.3), and as training *sharpens* the model it pushes
  more problems past p=0.9, so g falls over time. This is exactly E1's
  zero-variance fraction climbing 42%→64% — the model optimising itself out
  of its own gradient.
- **Collapse from below (all-wrong).** Needs problems at p<0.1. Only
  **acquisition** tasks at high difficulty supply these. Countdown even on a
  7B keeps the model *inconsistent* (E8: pass@1=0.49 at the easy dial, yet
  all-8-correct only 5.5%) — it can find a solution but not reliably, so
  almost nothing reaches p>0.9. Countdown *cannot* collapse from above; its
  only failure mode is the hard dials starving of successes.

**Consequence: no single task shows the whole g curve.** GSM8K is the right
cliff, Countdown is the left cliff plus the gradient-rich peak. To see both
arms you must cross tasks — which is why Phase A (GSM8K) and Phase C
(Countdown) are complementary rather than redundant, and why the same model
(7B) is used for both, so the difference is regime, not scale.

### Quantity is not quality

g measures whether a gradient exists, not whether it's *good*. A mixed group
can be a safe **error-deletion** update (p high, one failure to suppress —
low-noise, points at reliable behaviour) or a risky **success-amplification**
bet (p low, one lucky success to reinforce — the reinforced trajectory may
not generalise). Same g, different value. This quality axis is the open
question behind Phase A's "polishing" hypothesis (E5/E7); g is the quantity
axis we can dial cleanly. Both matter.

### Batch structure: three knobs, and how batch size interacts with g

Three independent knobs are easy to conflate:

1. **Group size k** (`num_generations`): rollouts *per prompt*. This is what
   sets g(p) and the quality of each problem's advantage estimate. Advantages
   are normalized *within* a group.
2. **Prompts per update**: distinct problems pooled into one gradient step.
   Averages the per-group gradients; does **not** change g (g is per-problem).
3. **Batch reuse** (`num_iterations`, PPO epochs): how many times each batch
   of rollouts is reused for updates. We use 1.

Our runs are **one prompt per update** (effective batch = per_device 2 ×
grad_accum 4 = 8 = one group of 8). Labs typically use many — DeepSeek-R1 used
4 prompts × 64 rollouts = 256 completions per iteration. On 24 GB we *can*
raise prompts-per-update via grad_accum (memory-cheap, sequential), but each
step then generates N groups before stepping, so wall-clock scales ~N×. More
memory/GPUs buys *speed* at large batch (parallel generation), not the
capability itself.

**Why this matters for g:** g's *definition* is untouched by prompts-per-
update, but the *cost of low g* depends on it entirely. At 1 prompt/update a
uniform group makes the whole step a no-op — at g=0.2, ~80% of steps do
nothing and the rest fire at random (high variance, slow, unstable). At N
prompts/update the step averages N groups: uniform ones contribute zero but
don't waste the step. So **larger prompt-batches partially rescue sparse-g
regimes** — not by creating gradient where there is none, but by keeping every
step productive. Consequence for our sweeps: sparse levels look *worse in our
1-prompt setup than they would in a large-batch lab*, so "learning falls off
as g sparsifies" is partly a property of our batch size, not only the task.
(Open experiment: fix g sparse, vary prompts-per-update, measure the rescue —
backlog C2.)

### Why this is the organizing variable for Phase C

The "difficulty sweet spot" people chase is just **the peak of g(p)**. So
Phase C's difficulty sweep is really a *reward-density* sweep: hold everything
fixed, vary the dial so g moves across its achievable range, and watch how
learning dynamics and eval gains respond. Measured in g (not pass@1), the
Countdown dials give a clean monotone ladder from the gradient-rich regime
(g≈0.88) down toward starvation (g≈0.1) — see E8 for the chosen levels.
