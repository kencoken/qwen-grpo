Changes requested, but Rev4 is close. The Rev3 blockers are materially fixed; two supported crash-path gaps remain before the GPU probe.

### Blocking

1. **Final cadence is committed too early.**
   At `p0_execution.py:2160–2170`, cadence 6123 is atomically committed before the training trace and `trainer_log_history.json` are sealed. A crash there makes resume choose finalize-only, but verification then fails permanently on the missing log.

   Make the final cadence record the last durable commit: seal/validate the training trace and log first, then perform the final checkpoint/evaluation and write its cadence record.

2. **A SIGKILL can leave an unparseable excluded tail.**
   Crash sanitation gzips the raw trace byte-for-byte, while the verifier parses every line before deciding whether it belongs to the checkpoint-authorized prefix. A truncated final JSON row in a post-checkpoint tail therefore poisons verification even though that tail is scientifically excluded.

   Preserve the complete gzip as evidence, but read and validate exactly the authorized prefix without parsing excluded tail bytes. Add a regression with a valid authorized prefix followed by a truncated JSON fragment.

### Lower-severity discrepancy

The “genuinely historical verification” repair is incomplete: `_expected_p0_identities()` still loads the current default freeze and current `plans/conductor/p0/p0_launch_freeze.json`, rather than the archived prelaunch copy. This should be corrected while the area is open, though it does not block the immediate GPU probe under the present unchanged artifacts.

### Confirmed closed

- Bundle inventory now derives from the authoritative filenames.
- Finalize sessions no longer alter trajectory boundaries.
- Complete killed-session artifacts are sanitized.
- Whole uncommitted cadence attempts are preserved.
- Session double-end accounting is rejected.
- Scheduler identity unwrapping is meaningful.
- Manifest-bound verification root is enforced.
- Freeze, identity, and evaluation pins correctly remain unchanged.
- `1040 passed` under warnings-as-errors; diff check clean.

I recommend one narrowly bounded Rev5 for the two crash windows and archived-freeze dependency, then proceed directly to the end-to-end reward-blind GPU lifecycle probe.