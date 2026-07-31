## Verdict

Rev2 closes the original population-inversion bug, but is not ready to launch. Two result-affecting issues remain; both fit a narrow Rev3.

### P1 — Q2 support is pooled across directions

The gate at [`unit_c_sample.py:492`](/home/ken/qwen-grpo/tasks/routing/unit_c_sample.py:492) aggregates worker selections across both Q2 populations.

I reproduced an authenticated counterexample:

- every `math_code → w3` row selected worker 2: 560 selections;
- every `fork_join → w2` row selected worker 3: 720 selections;
- ModelAcc: **0/1,280**;
- direct and semantic contrasts: **zero in both directions**;
- nevertheless, the Q2 gate passed and authorized Q1+Q2.

Gate separately on the intended target:

- `math_code → w3`: at least 8 worker-3 selections across at least 2 latents;
- `fork_join → w2`: at least 8 worker-2 selections across at least 2 latents.

Keep global marginals and group-level contrasts as diagnostics. Add the crossed-wrong regression.

### P1 — The sizing rule still leaves the capped duration discretionary

[`p0_sizing_rule`](/home/ken/qwen-grpo/tasks/routing/unit_c_sample.py:139) stores its formula as prose and defers an unspecified cap. The report emits rates and the rule, but not the mechanically derived epochs/groups.

At the projected slow-cell rate, it requests approximately:

- 121 epochs;
- 18,997 groups;
- about 23 hours at the existing beta-zero rate;

which exceeds the charter’s ten-hour P0 operational ceiling. Therefore the cap branch is likely, not hypothetical.

Before outcomes are revealed:

1. Implement and test an integer derivation such as
   `ceil(100 × Unit-C epochs / minimum counted groups)`.
2. Persist the derived epochs and groups in the report.
3. Freeze the over-budget consequence:
   - exact derived size if admissible; otherwise
   - either stop for a reviewed scope amendment, or apply an exact whole-epoch ten-hour cap with a predefined scope-shortfall interpretation.

The later beta timing smoke may supply seconds per group; it should not determine the branch semantics.

### Smaller repairs to include in Rev3

- The renderer/subtype strata have valid denominators, but omit stratified C2 eligibility/optimality, ModelAcc, and direct/semantic contrasts. Add these to support the known `goal_first`-confound analysis. Retaining latent IDs/public numeric factors would also make the registered shortcut controls directly executable.
- Make `build_exposure_report()` itself require the exact 785-row frozen schedule. Currently a truncated 580-row Bridge+Q2 archive can produce an authorization report, although the outer verifier would later abort it.
- Require non-empty/expected LoRA hash-map keys so `{}` → `{}` cannot satisfy zero-mutation verification.
- Update the stale module prose and frozen question, which still describe Q2 as schedule-delivery authorization.

### Verified

- The old 1,080-Bridge-completion contamination is fixed.
- Q2 statistics are now composite-only and direction-separated.
- The Q2-fail → Q1-only branch is reachable.
- Exact schedule remains 785 groups / 6,280 completions.
- Config, freeze and identity hashes reproduce.
- Full suite: **1,002 passed** under warnings-as-errors.
- Worktree and diff checks are clean.

After this narrow Rev3 and regenerated identities, Unit C should need only a changed-lines review before launch.