## Verdict

One final narrow repair is needed before freezing Step 4. The scientific retry issue is closed, but two consuming-boundary problems remain.

### Blocking

1. **The provisional reserve’s timing basis is still caller-asserted.**

   [ledger.py:324](/private/tmp/review221/tasks/routing/ledger.py:324) verifies the total support cost, but never derives `measured_seconds_per_observation` from that cost and the authenticated observation count.

   I confirmed that a **1.5-hour support run paired with 0.1 seconds per observation is accepted**, producing an arbitrarily undersized reserve.

   Persist the measured duration and rendered-observation denominator in the completed closeout, then require the reserve’s per-observation value to rederive exactly. Also reject `status="final"` at this stage; final reserve authorization must wait for the cycle cohort and evaluation-rule identities.

2. **Terminal verification proves file hashes, not valid terminal evidence.**

   The all-field environment comparison is fixed, but the live manifest is never canonical/self-hash validated. An invalid live `execution_manifest_sha256` is accepted.

   Likewise, [verify_terminal_outputs()](/private/tmp/review221/tasks/routing/support_run.py:176) accepts `{}` as both `run_record.json` and `execute_env_manifest.json` when their raw hashes match. It does not require or verify the disclosure, comparator, probe cohort or surface identity. Aborted verification similarly permits an empty artifact map.

   Use a closed, status-specific terminal-artifact manifest:

   - Complete: exact required output set, surface lock, live environment, disclosure, comparator, cohort and run record.
   - Aborted: non-empty exact partial-file inventory.
   - Parse and validate the live environment and cross-check the run-record identities, rather than checking bytes alone.
   - Require this canonical terminal binding before a reserve can reference the closeout.

### Correctly closed

- Complete environment field comparison
- Design-preserving abort retries
- Outcome-blind first-probe protection
- Content-hashed partial evidence on the real runner path
- Completed-support/no-open-launch reserve ordering
- Terminal success/abort lifecycle
- Mechanical cleanup

Verification is otherwise clean: **45 focused tests**, **961 total tests under warnings-as-errors**, and `git diff --check` passes.

These are directly in the newly changed trust boundaries, not another broad audit. After this small terminal-manifest and reserve-derivation repair, I would sign off.