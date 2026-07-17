Rev5 resolves the substantive architecture, action-space, leakage, cache, reward and framing issues. It is ready to begin Stage 0A, subject to two textual fixes and review of the first deliverable.

## Two remaining specification defects

### 1. `β=1e-3` is not “log-only”

In the current TRL path, nonzero `beta` contributes a real KL term to the loss. It may be deliberately tiny and used primarily as a drift gauge, but it is not observational only.

Either:

- keep `β=1e-3` and call it “a small nonzero KL regularizer used primarily as a drift gauge”; or
- set `β=0` and instrument KL separately if genuinely log-only behavior is required.

The current wording appears at [lines 9–11](/Users/ken/crystalline-sleeping-zephyr-rev5.md:9) and [lines 138–141](/Users/ken/crystalline-sleeping-zephyr-rev5.md:138).

### 2. Three CE1 gates remain incomplete or inconsistent

At [lines 194–205](/Users/ken/crystalline-sleeping-zephyr-rev5.md:194):

- **Effective routing stakes** has no numerical threshold.
- **Counterfactual consistency** has no quantitative pass rule.
- **Fork corruption** still says `≥ −20 pts`, contradicting the correct prose definition at line 128.

Suggested replacements:

```text
Effective routing stakes:
For every learnable composite position, replacing the deployable-best endpoint
with its runner-up while holding all other assignments fixed reduces terminal
accuracy by ≥10 points, with paired clustered 95% CI lower bound >0.
A position failing this gate is fixed rather than learned in Stage 2.
```

```text
Counterfactual consistency:
Accuracy on the recomputed sink is no more than 10 points below corresponding
unmutated accuracy, and persistence of the old answer is ≤10%.
```

```text
Fork corruption:
Baseline accuracy − corrupted-branch accuracy ≥20 points for each branch,
using a paired clustered confidence interval.
```

The exact thresholds can differ, but they must be numeric before CE1 begins.

## Cell-spec sign-off

Making `conductor_cell_specs.md` the first Stage 0A deliverable is the correct resolution. The plan is ready to start, but the actual generator cannot receive final scientific sign-off until that file exists and is reviewed.

Freeze in two phases:

1. Operator semantics, artifact grammars, public/private field boundaries and reference functions freeze when the cell-spec file is approved.
2. Difficulty ranges freeze after the 100-example construction screen and before generating fresh qualification data.

Do not select a new deployable oracle on qualification results; it must remain the assignment selected using construction data.

## Small clarifications worth adding

- Mark the union-payload one-call baseline explicitly as a harness-only exception to the one-resource-per-step policy.
- Put actual numeric policy and worker token caps in the checked-in launch profile.
- Pre-register sequential sampling: start at 100 qualification programs, expand in fixed batches only when confidence intervals are inconclusive, with a fixed maximum.
- Stage 2 fork/join correctly tests endpoint selection inside a fixed parallel DAG; topology construction remains a Stage 4 claim.

With those edits—and review of `conductor_cell_specs.md` before generator code—this is ready for implementation. No further high-level redesign is needed.