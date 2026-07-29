## Verdict

Unit A is **not ready to launch**. The infrastructure is mechanically sound, but four contract discrepancies could change cohort membership, Q3 eligibility, or ScaleLift semantics.

### Blocking findings

1. **[P1] The selector includes legacy indices `0–5` and implements a different selection rule.**

   [`extension_run.py`](/home/ken/qwen-grpo/tasks/routing/extension_run.py:418) processes all `0–47` latents, despite the signed candidate domain being `6–47`. A probe against the locked Step-4 surface selected legacy latents:

   - `code_atomic|w2`: `[5]`
   - `fork_join|w2`: `[1, 5]`
   - `math_code|w3`: `[2, 3]`

   These can incorrectly satisfy quotas and move intended Anchor observations into Direction.

   The implementation also assigns by renderer majority and retains all qualifying latents, whereas the signed design specifies ordered, first-satisfying assignment and a canonical quota-bounded subset.

   Filter selection to `6–47`, retain `0–5` only in the complete yield/Anchor disclosure, and either implement the signed canonical selector or explicitly amend and review the majority/all-members rule.

2. **[P1] Q3 common-cell eligibility bypasses the renderer constraints.**

   [`extension_run.py`](/home/ken/qwen-grpo/tasks/routing/extension_run.py:483) calculates dispositions correctly, but `eligible_common_cells_q3` at line 504 uses only raw bucket sizes. A direction marked `quota_constraints_unmet` can therefore still authorize a Q3 common cell.

   Derive eligibility from acceptable disposition states. Also enumerate all three Code cells × both directions so zero-yield cells receive explicit dropped dispositions.

3. **[P1] The required subtype/public-factor disclosure is absent.**

   [`extension_run.py`](/home/ken/qwen-grpo/tasks/routing/extension_run.py:511) reports only cell, renderer, and cell×renderer. It does not report observable subtype/public factors or cell×renderer×subtype—the analysis needed to detect simple public-subtype routing.

   Reuse the existing safe public projection and test that all 864 observations enter the disclosure.

4. **[P1] The immutable comparator artifact has no working ScaleLift consumer.**

   [`immutable_comparator`](/home/ken/qwen-grpo/tasks/routing/extension_run.py:359) creates a new extension record, but [`telemetry.group_stats`](/home/ken/qwen-grpo/tasks/routing/telemetry.py:123) accepts only the original `c_fixed_dev-v1` record. A focused probe fails with:

   ```text
   InfrastructureError: not a c_fixed_dev-v1 record
   ```

   Implement and integration-test the actual extension-aware ScaleLift boundary: verify the extension lock, reverify the source comparator against the original lock, extract worker 2, and compute ScaleLift without invoking selection on the extension.

### Smaller operational issues

- `python -m tasks.routing.extension_run` silently exits because no execute/verify CLI exists. Add a frozen-hash-bound launch and verification command, or document an equally reproducible supported entry point.
- A fully cache-served reviewed retry currently fails because zero live generations are rejected. This is worth fixing before the first expensive run.
- The reviewed run root is descriptive rather than identity-bound. Binding it would prevent copied prelaunch artifacts being executed under a different lifecycle root.

### What verified cleanly

- `991 passed` under warnings-as-errors.
- Clean diff and matching committed/live prelaunch bytes.
- Exactly 864 observations, 38,592 total and 33,768 new node executions.
- Expected new cost `0.5124 GPU-h`, within the 1-hour ceiling.
- Overlap payoff/terminal equality runs before lock acceptance.
- Original `c_fixed_dev` verification is rooted in the Step-4 lock, with extension reselection unreachable.
- Ledger admission, environment/source binding, and success/abort artifact inventories are sound.

These fixes alter reviewed source bytes, so regenerate the prelaunch manifest and update `261_f` before launching.