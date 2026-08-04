## Verdict

Rev4 closes the scientific and normal-lifecycle blockers, but I would make **one final narrow repair before launch**. Two terminal-boundary issues remain.

### Findings

1. **[P1] A genuine late abort cannot be verified.**

   `execute_val_run()` writes `val_lock.json` before running the in-run verifier. If that verifier fails, the run is correctly closed as aborted with all partial files hashed—but the aborted verifier then rejects the archive solely because `val_lock.json` exists.

   Consequently, the tested early deadline abort works, while an abort after lock creation produces permanently unverifiable evidence.

   Simplest repair: permit `val_lock.json` as hashed partial evidence when:

   - `expected_val_lock_sha256 is None`;
   - the authenticated aborted closeout contains no authorized `val_lock_sha256`;
   - the file is explicitly treated as an unadmitted candidate, never a consumable V3 lock.

   Add a regression that forces failure after lock creation and then successfully verifies the aborted archive.

2. **[P1] Three authenticated semantic fields remain unchecked.**

   The verifier still accepts:

   - `run_record["surface_dir"]` inconsistent with `manifest["execution_root"]/surface`;
   - an aborted closeout whose `freeze["val_launch_sha256"]` names the wrong manifest;
   - a closeout whose semantic `parent` does not equal the launch it closes.

   I reproduced the first two with valid rehashed ledger chains: both returned `PASS`.

   These are small cross-checks. Store the original bound absolute surface path in the run record so archived copies remain portable, and verify the closeout’s semantic parent/direct predecessor and aborted manifest identity.

### Nonblocking cleanup

- Correct the remaining `three_way_overlap_reports()` docstring: only semantic intersections must be empty; prompt overlap is disclosed.
- Prefer committing the full abort→`-r2` filesystem regression. The current positive retry test is ledger-only and reuses one manifest, although an independent full CPU-fake retry completed successfully.

### Confirmed sound

- The former handle-renaming counterexample now hashes identically.
- Semantic overlaps remain zero; prompt collisions and exact memberships reproduce.
- Frozen-parent admission, actual execution-root binding, normal retry, deadline abort, complete verification and outcome-blind cohort enforcement work.
- **1,029 tests passed** under warnings-as-errors.
- Config, freeze and 720-seed hashes rederive unchanged.
- Diff and worktree checks are clean.

After these localized changes, a narrow changed-lines and mechanical review should be sufficient for sign-off; no further broad Unit V review is needed.