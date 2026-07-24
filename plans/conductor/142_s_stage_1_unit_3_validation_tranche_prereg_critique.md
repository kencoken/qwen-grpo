## Sign-off verdict

Do not sign `141_f` for execution yet. The A/C statistical design is sound, but the preregistration is not presently complete or fail-closed.

### Approved design choices

I approve:

- the four A position scenarios and alpha divisors;
- the absorbing stopping interpretation: pass on point ≥0.10 and LCB >0, conclusively fail only on UCB <0, otherwise expand;
- equal-cell router weighting and variance calculation;
- the C persistence envelope, alpha split, two synthetic distributions and terminal hard cells;
- retaining the predicted C failure as a prediction rather than prematurely choosing its amendment;
- the CPU budget in principle—it remains comfortably below 12 hours.

### Blocking findings

1. **[P1] Check D is not actually preregistered or executable.**

   [`stage1_validation.py`](https://github.com/kencoken/qwen-grpo/blob/5c547868352ae2697a9f0fd9ce8d864491ccf766/tasks/conductor/stage1_validation.py#L304-L361) contains an eight-scenario cap, one LCB helper and a benchmark, but no exact scenario registry. This contradicts [`141_f` lines 185–188](https://github.com/kencoken/qwen-grpo/blob/5c547868352ae2697a9f0fd9ce8d864491ccf766/plans/conductor/141_f_stage_1_unit_3_validation_tranche_prereg.md#L185-L188), which says the composition exists in module constants.

   Missing machinery includes:

   - ordinary/fork sequential-null scenarios;
   - both ±0.10 equivalence boundaries;
   - unequal-cell-size pilot aggregation;
   - constant/variable eligibility cases;
   - undefined-replicate behavior;
   - the 5,000-outer coverage runner;
   - Wilson-upper evaluation;
   - the 2,000-versus-10,000 agreement gate.

   The exact ≤8 scenarios, DGPs, seeds, expected decisions and decision code must be frozen before any tranche output is revealed.

2. **[P1] Check B remains prose-only, so its source is not frozen.**

   The module explicitly defers B. There is no replay driver, candidate-specific prompt boundary, eligible-pair builder, scorer, manifest or tests.

   Before any GPU call, freeze:

   - literal model/tokenizer revisions and fresh-adapter or base-equivalent decision;
   - NF4, attention, token cap, stopping and every sampling parameter;
   - exact candidate-specific chat messages and rendered-request hashes;
   - batch size and RNG semantics—recording batching afterwards is too late;
   - the exact eligible w2/w3 table derived before sampling;
   - malformed/wrong-length/truncated outputs remaining in the 64-sample denominator;
   - full support/surface/parser/scorer/runtime identities;
   - complete 2,304-key output accounting.

   The cleanest batching choice is singleton generation with one seeded generator per `(observation, prompt, completion_index)`, especially given the earlier D16 batch-sensitivity evidence.

3. **[P1] Acceptance currently fails open.**

   [`evaluate_acceptance()`](https://github.com/kencoken/qwen-grpo/blob/5c547868352ae2697a9f0fd9ce8d864491ccf766/tasks/conductor/stage1_validation.py#L366-L410) returns:

   ```text
   confirm_possible = True
   ```

   for empty inputs. It also accepts partial grids, ignores duplicates and mandatory disclosures, trusts supplied Wilson summaries, allows NaNs to evade comparisons, and ignores B and D entirely.

   Add exact expected-key registries for:

   - 48 A-position cells;
   - 24 A-router cells;
   - 120 C cells;
   - the exact D registry;
   - one complete B artifact.

   Missing, duplicate, extra, malformed, non-finite or incorrectly sized results must refuse. The overall verdict must incorporate all four checks.

4. **[P1] There is no frozen runner or content-addressed result path.**

   Individual simulation functions accept arbitrary parameters, but nothing enumerates the exact grids, records their seeds and environment identity, writes canonical artifacts, reloads them, or verifies completeness. Implementing that after seeing A/C outcomes would defeat the source-freeze requirement.

   The 2,000-versus-10,000 agreement check must run and pass before the reduced-replicate D battery—not merely be grouped somewhere inside “D Monte Carlo.”

5. **[P1] The claimed deterministic D coverage is incomplete.**

   Current tests cover useful interval algebra, but not the plan’s required:

   - renderer-coupled cluster resampling;
   - unequal cell sizes;
   - equivalence decisions;
   - adverse undefined replicates;
   - complete sequential operational-error logic.

### Smaller corrections

- The router grid contains **24**, not 12, cells.
- The C grid contains **120**, not approximately 144, cells.
- Freeze Wilson as explicitly one-sided or two-sided. The implementation uses one-sided 95% (`z≈1.645`), while a test comment says `z=1.96`. I recommend explicitly retaining the one-sided implementation.
- Record full artifact hashes rather than abbreviated prefixes in the executable preregistration.

### Verification

- Deterministic Unit 1–3 tests: **122 passed**
- CPU-compatible suite: **695 passed**
- No frozen grid or GPU replay was executed.
- The full process still encounters the known post-pytest exit-139 teardown after reporting all tests passed.

The right next step is a focused preregistration-completion commit: exact D registry and runner, executable B replay contract, canonical artifact schemas, and one fail-closed A–D aggregator. After a changed-lines review of that commit, we should be able to sign and launch without another broad audit.