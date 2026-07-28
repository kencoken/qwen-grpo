## Verdict

The execution is scientifically valid and no GPU rerun is needed. I found one archival blocker to formal close-out and one documentation typo. After those are fixed, proceed to Step 5.

## Findings

1. **The complete trace archive is not durably preserved.**
   [231_f](/private/tmp/review221/plans/conductor/231_f_support_materialization_execution_record.md:32) commits 15 of the 17 terminal files, leaving the trace manifest and `steps.jsonl` only in the ignored `runs/` tree on `picome`. Their hashes match the ledger, but a clean clone cannot reconstruct and fully verify the run. This conflicts with the charter’s complete-archive requirement.

   Commit the trace manifest and either the raw JSONL or a deterministic compressed copy with restoration instructions, then demonstrate clean reconstruction through `verify_terminal_outputs`. The 17 MB JSONL compresses to about 380 KB, so this is inexpensive and requires no ledger change.

2. **The admitted-launch identity is mislabeled.**
   [231_f](/private/tmp/review221/plans/conductor/231_f_support_materialization_execution_record.md:14) calls `6506f117…` the launch entry. The correct sequence is:

   - admitted launch: `f0d4651c…`
   - complete closeout: `6506f117…`
   - reserve/current ledger head: `264066e6…`

   The artifacts and ledger are correct; only the prose—and the commit message, if amended—are wrong.

Everything else verifies cleanly:

- Live terminal verification passes.
- Full suite: 961 tests pass under warnings-as-errors.
- `git diff --check` is clean.
- Ledger chain verifies with no open launches.
- All 4,824 planned trace rows are accounted for: 1,136 successes, 2,240 typed failures, and 1,448 expected dependency blocks.
- No infrastructure/world failures or token-cap events occurred.
- Cost and reserve calculations rederive exactly: 0.0732 GPU-hours consumed, 59.9268 remaining, provisional `R_cycle = 5` GPU-hours.

## What the results mean

The family-routing signal is excellent. Every observation has both 0.5 and 1.0 payoff assignments, and every reward-1 assignment is a family-correct workflow. There are no accidental successes from wrong-family routes. Thus there is a strong gradient for learning topology and worker-family selection.

Fine-grained Code-model selection is real but sparse:

- 6/54 Code-bearing rendered observations are direction-bearing.
- Worker 2 wins four; worker 3 wins two; 48 are ties.
- These represent only five independent latents.
- Five of six occur under `goal_first`; none under `resource_first`.
- Worker 2 wins only in `code_atomic`/`fork_join`; worker 3 only in `math_code`.
- There is no within-cell bidirectionality yet.

Consequently, this support currently looks more like **family routing plus coarse task/renderer-conditioned model choice** than rich per-instance model selection. That is still a legitimate toy analogue of selecting an appropriate model for a subtask, but it is narrower than the frontier-model adaptivity claim.

`c_fixed_dev = worker 2` is correct, but its natural-mixture advantage is small. On this support, oracle worker selection improves over fixed worker 2 by only `1/54 ≈ 1.85` percentage points within Code-bearing cells—or roughly `0.93` points across six equally weighted cells, conditional on otherwise perfect family routing.

## Impact on the plan

Do not change the frozen first probe. It remains outcome-blind and should use the bound 108 observations, four groups per observation, group size eight, and 3,456 completions.

Its relevant denominators are:

- 432 total groups;
- 216 Code-bearing groups;
- 24 groups on direction-bearing observations: 16 worker-2-favoured and 8 worker-3-favoured.

Those 24 are only opportunities: an exact direct contrast requires the policy to sample both specialist alternatives within the same group. Few or even zero such contrasts would be evidence of underexposure, not a failed experiment. The probe will primarily measure structured-action validity, family routing, semantic reward variance, and actual specialist co-sampling.

After the probe, direction-enriched P0 support now looks likely. That expansion should be explicitly outcome-conditioned, selected at latent level with full renderer crossing, and seek:

- more worker-3-favoured cases;
- non-`goal_first` cases;
- ideally both directions within the same cell.

Because the present probe leaves many cell × renderer × direction strata empty, the charter’s preferred exact-final-P0-cohort zero-update exposure sample will probably be safer than a reweighting argument. Natural-mixture evaluation must remain alongside any enriched curriculum.

Immediate sequence:

1. Archive the traces and correct the identity typo.
2. Prepare/review and freeze the Step-5 GPU resume-validation tranche with an exact ceiling.
3. Run and close out resume validation.
4. Freeze and run the unchanged grouped probe.
5. Use that measured exposure—not the surface counts alone—to design P0.