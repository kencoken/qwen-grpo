## Verdict

Not ready yet, but only two narrowly scoped blockers remain.

1. **Complete terminal evidence is still not fully authenticated.**

   [verify_terminal_outputs()](/private/tmp/review221/tasks/routing/support_run.py:176) accepts:

   - a replaced `disclosure.json` containing `{}`;
   - modified surface payoffs while retaining the nominal lock field;
   - additional unbound result files.

   It also checks only that `rendered_observations` is positive, rather than matching the loaded authenticated population. Consequently, a synthetic complete closeout with invented hashes/count can still anchor a reserve.

   Minimal repair:

   - Bind an exact complete-run file-hash inventory, analogous to the aborted path.
   - Require exact on-disk equality.
   - Validate the surface through `validate_surface_lock()`/`load_dev_surface()`.
   - Cross-check `rendered_observations == len(loaded["observations"])`.
   - Have the reserve-append boundary consume this verified terminal run, not merely a shape-correct closeout.

2. **A premature `final` reserve remains possible.**

   [ledger.py:359](/private/tmp/review221/tasks/routing/ledger.py:359) accepts any truthy cycle-cohort and evaluation-rule strings. I confirmed that `"not-a-hash"` values authorize `status="final"`.

   Reject final reserves unconditionally for now. Enable them later only when the real cycle-cohort and evaluation-rule validators exist.

Correctly closed: canonical live-environment validation, design-preserving retries, exact aborted inventories, provisional timing arithmetic, and outcome-blind ordering.

Verification is clean: **45 focused tests**, **961 full tests under warnings-as-errors**, and `git diff --check` passes. After these two small changes, sign off.