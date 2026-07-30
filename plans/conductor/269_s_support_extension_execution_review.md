# 269_s — Unit-A execution review: accept closeout; scope P0 to Q1 + hierarchical Q2

## Verdict

Accept Unit A as complete. The extension run is valid, reproducible and
within its frozen compute envelope. It produced the intended decision:
the support is strong enough to proceed with Q1 and a deliberately scoped
Q2 hierarchical-unlocking experiment, but it does not authorize formal
Q3 bidirectional within-cell specialist routing.

There is no reason to rerun or widen Unit A. The immutable selection and
its negative Q3 result should be carried into Unit B. The separate bounded
Q3 task-discovery experiment strengthens that disposition: further
ecological search for Q3 examples should stop for this frozen worker
pair/interface.

## 1. Execution and artifact integrity

The committed evidence supports the closeout recorded in `268_f`:

- 864 observations, 15,552 payoff rows and 38,592 trace steps were
  materialized;
- all 1,944 overlap rows reproduced exactly before the extension lock was
  accepted;
- surface lock
  `ccb1c3e2db2422a82919292144c0bdecc21d2cc89cb7a3a2c69bec17a2ce6d1b`;
- frozen selection
  `c6c087757eb4673c42ad37121f9037ca57ce9488e65c4d339d78b37d07fbee34`;
- comparator
  `9220c2c7a7efe890c60e5abbdcc3b84eecbbb971e75fa69e313e6d61888e5f1f`
  remains worker 2 and reports no reselection;
- the portable evidence archive restores, the selection re-derives and
  the public verifier passes;
- measured cost was 0.4934 GPU-hours, below the 1.0 GPU-hour ceiling; and
- closeout/ledger head
  `b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd`
  verifies with the reserve intact.

I found no execution, provenance, overlap, selector or budget defect that
blocks acceptance.

## 2. What Unit A measured

For candidate latents 6–47, the frozen selector found:

| Direction bucket | Selected support | Disposition |
|---|---:|---|
| `code_atomic -> w3` | 5 latents, `goal_first` only | quota constraints unmet |
| `fork_join -> w2` | 3 selected latents across `goal_first` and `bound_var`, plus 22 surplus latents | full quota |
| `math_code -> w3` | 7 latents, `goal_first` only | quota constraints unmet |
| the three opposite directions | 0 latents | dropped from Q3 |

Accordingly, `eligible_common_cells_q3 = []`. This is not merely a thin
sample of formal Q3: under the registered criterion, formal Q3 has no
eligible cell.

The Q1 bridge surface is nevertheless strong. The full-predicate counts
are:

| Critical cell | Eligible Bridge observations |
|---|---:|
| `code_atomic` | 138 |
| `fork_join` | 114 |
| `math_atomic` | 144 |
| `math_code` | 135 |

The three Code-bearing cells contribute 387 tied reward-1 worker-2/worker-3
observations. Unit C must still show that the frozen schedule turns this
structural availability into group-level Q1 reward variation in all four
critical cells.

The retained owned Direction set—selected rows plus disclosed surplus—is
cell-perfect on 38/38 observations:

- `code_atomic -> w3`;
- `fork_join -> w2`; and
- `math_code -> w3`.

Across all 45 payoff-distinct observations, the cell-only rule is correct
on 43/45; adding renderer and subtype reaches 44/45. On the natural
equal-cell surface across the three Code-bearing cells, fixed worker 2
scores 0.9826, the trivial cell router 0.9977 and the hindsight oracle
1.0000. Only 0.23 percentage points remain beyond the cell router.

Those figures support an honest description of the available mechanism:
coarse cell/task-conditioned model choice under hierarchical credit
assignment. They do not support instance-adaptive specialist selection,
and “task-subtype routing” is unnecessarily strong as the primary
description because subtype is not needed to solve the retained cohort.
The renderer/subtype controls should still be retained to quantify
shortcut use.

## 3. Two wording corrections to `268_f`

These do not alter the archive or require a rerun, but the downstream
documents should use the more precise language:

1. Replace “Q3 at most direction-specific” with:

   > Formal Q3 is unavailable. `fork_join -> w2` remains a one-sided
   > descriptive diagnostic, not a Q3 claim.

   This is especially important because the frozen fixed comparator is
   worker 2: `fork_join -> w2` has no positive specialist ScaleLift
   available against that comparator. Positive specialist ScaleLift can
   occur only on the worker-3-favoured rows, which are renderer-confounded.

2. Replace “zero non-`goal_first` w3 coverage anywhere” with:

   > There is zero assigned/eligible non-`goal_first` worker-3 coverage.

   Fork-join latent 42 contains a diagnostic renderer reversal—worker 2
   under `goal_first`, worker 3 under `bound_var`—but the frozen selector
   assigns the latent to the worker-2 bucket. It must remain diagnostic
   rather than being reused to manufacture balance.

## 4. The bounded Q3 task-discovery result

The separate `conductor_q3_task_discovery` exploration tested the most
plausible remaining ecological recovery route without changing workers.
Models, the rev10 prompt, request contract, runtime, parser, grammar and
decoding were frozen; only synthetic task semantics and rendering varied.
Three prospectively specified strategies were evaluated over 192
observations after known-support complementarity was reproduced.

The result was a bounded negative:

- worker 2: 100%;
- worker 3: 95.3%;
- all nine disagreements favoured worker 2;
- every disagreement occurred under `goal_first`;
- none was renderer-stable;
- fixed worker 2 equalled the hindsight oracle; and
- the proposed semantic routers performed worse.

Because the known-support control reproduced first, this is not best
explained by a broken harness or scorer. Close further ecological Q3 task
search for this frozen worker pair/interface. Preserve its evidence under
`plans/conductor/exploration/q3_task_discovery/` on the exploration branch;
there is no need to merge its exploratory implementation into the main
lineage.

Q3 may be revisited later only through a separately framed experiment—for
example deliberately constructed worker heterogeneity, materially
different models/interfaces, or an explicit mechanism study. That would
be new work, not an extension of the present P0 claim.

## 5. Q2 remains viable and should retain both Code workers

The Q3 disposition does not remove the downstream worker choice from P0.
Q2 asks whether hierarchical learning unlocks it:

1. family/topology routing improves;
2. the downstream Code decision becomes reward-eligible; and
3. a coarse rule such as `math_code -> w3` and `fork_join -> w2` can then
   be reinforced.

The seven worker-3-favoured `math_code` latents provide real downstream
opportunities, while `fork_join -> w2` supplies the opposite scheduled
choice. Their cell correlation and the worker-3 renderer confound limit
the claim, but do not make the hierarchical-credit question empty.

The principal Q2 measurements should therefore be:

- C1 family/topology accuracy;
- C2 eligibility;
- Code-worker accuracy conditional on C2 eligibility;
- the temporal ordering of C1 improvement, eligibility, then conditional
  worker accuracy;
- ScaleLift, reported with the comparator asymmetry above; and
- cell-, renderer-, subtype- and latent-blocked public-feature controls.

## 6. Required Unit-B mixture revision

Do **not** mechanically shrink the former approximately 45% Direction
allocation merely because formal Q3 is gone. Q1 is expected to be the
earlier/easier acquisition. A Bridge-heavy fixed schedule could spend
later updates repeatedly teaching an already-solved distinction while
starving the policy of downstream opportunities once C1 unlocks.

Instead, formally supersede the old Q3-oriented Direction class with
deliberate **Q2 composite exposure**:

1. determine the minimum Bridge mass projected to satisfy the Q1
   reward-variation gate in every critical cell;
2. retain enough Anchor mass to measure forgetting and stability;
3. allocate most remaining mass to downstream Q2 rows;
4. give both `math_code -> w3` and `fork_join -> w2` enough group-level
   exposure that mixture imbalance does not reward an always-worker-2 or
   always-worker-3 policy;
5. add matched `goal_first` controls—using fork/tied rows where
   appropriate—so `goal_first` does not globally imply worker 3, while
   still disclosing that the actual worker-3 advantage is
   renderer-confounded;
6. keep latent 42 diagnostic/screened and do not count it twice;
7. retain lookup cells as Anchor/screened support with zero Bridge quota;
   and
8. use one fixed P0 schedule. Changing the mixture after C1 improves
   would confound hierarchical unlocking with increased Q2 exposure.

The resulting Q2 mass may remain in roughly the same order as the former
45%, but its value must come from group-level exposure and zero-variance
projections, not inheritance from the abandoned Q3 objective.

The previous complete-schedule direction-by-renderer balance requirement
was designed for Q3, no longer matches the authorized objective and may be
infeasible on the selected support. Unit B must explicitly replace it with
constraints aligned to Q2; it must not silently relax the old gate.

## 7. Unit-C authorization and iteration rule

Unit C must validate the exact Unit-B candidate schedule, including:

- Q1-counted reward-varying exposure in all four critical cells;
- downstream/C2-eligible exposure;
- conditional worker-choice opportunities in both scheduled Q2
  directions;
- predicted zero-variance-group fractions;
- Anchor/stability exposure; and
- the public-feature shortcut controls.

It must not both choose a new mixture from its outcomes and authorize that
same mixture. Either:

- preregistered projections choose the candidate before the Unit-C run;
  or
- use an explicit B1/C1 -> B2/C2 loop with new identities.

Any mixture change creates a new B/C iteration. Only the final, unchanged
candidate that passes Unit C may authorize P0.

## Sign-off and next step

Unit A should now be closed. Proceed to Unit B with the headline scope:

> Q1 family routing plus Q2 hierarchical unlocking and coarse,
> cell-correlated downstream model choice.

Formal Q3 and renderer-independent expertise routing are out of scope for
this P0. Freeze the revised schedule only after its Bridge, Anchor and Q2
composite masses have been justified by prospective group-level
projections; then run Unit C on that exact schedule.
