## Verdict

Almost, but **not yet ready to launch**. One narrow P1 remains; all other previous findings are closed.

### [P1] The verifier lacks an external root of trust

[`verify_probe_run()`](/private/tmp/review249/tasks/routing/probe_run.py:397) verifies that the archived manifests and record agree with each other, but not that they match the reviewed launch identities.

I reproduced coordinated relabelling:

- Changed the seed, prompt hash, routing-source hash, worker-pool identity, and cache identity.
- Rehashed the identity manifest and updated the record pointer.
- Separately changed GPU, Torch, lockfile, and source identity in the environment manifest, then rehashed it and updated both record hashes.
- `verify_probe_run()` still returned `PASS`.

The current regression only modifies the manifest without rehashing it, so it tests corruption rather than coherent misidentification.

Fix this by requiring either:

- `expected_identity_sha256` and `expected_environment_sha256` as verifier arguments, comparing them with both manifests and record fields; or
- the exact externally anchored ledger launch/closeout entry.

The first option is simplest. `execute_probe()` already has both reviewed hashes and can pass them into the verifier. Add regressions that rehash the altered manifests and update the record pointers.

### Nonblocking tightening

While touching the verifier, it would be cheap to validate the complete `execution_telemetry` schema: group accounting equals counters, embedded preflight equals the archived preflight, deadline equals 10,800 seconds, and timing/VRAM fields are finite and nonnegative. This is not a launch blocker.

### Confirmed closed

- The 432 zero-LR optimizer steps are now explicitly and prospectively amended as zero **effective parameter mutation**.
- Completion text is canonically reparsed; semantic assignments and rewards are independently rederived.
- Unequal trace arrays refuse.
- Both initial and final adapter hash maps are persisted and compared.
- Cohort, schedule, trace order, indices, preflight, support matrix, and ledger-head binding are validated.
- Execution telemetry is recorded.
- Revised hashes rederive exactly.
- Full suite: **982 passed under warnings-as-errors**.
- Diff-check and worktree are clean.
- No Step-6 run root exists; the repair remains pre-outcome.

After that single verifier repair, a narrow changed-lines and hash check should be enough to give the launch OK—no further broad audit is warranted.