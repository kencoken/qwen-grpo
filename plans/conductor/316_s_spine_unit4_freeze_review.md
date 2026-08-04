## Verdict

Unit 4’s arithmetic is correct, but it needs a bounded Rev2 before sign-off.

### P1 — `require_launchable()` accepts forged plans

`p0_cap.py:167` checks only truthy `launchable` and positive `launch_epochs`. It accepted:

- A capacity-zero `stop_reviewed_amendment` plan changed to launch one epoch.
- `launch_epochs=999` with capacity one and nominal 39.
- Boolean and NaN epoch values.

Have the boundary accept the authenticated contract, rederive the complete plan from its persisted inputs, compare it type-sensitively with the supplied record, then reject the genuine stop branch.

### P1 — The signed traceability matrix is missing

The required mapping—

`requirement → field → enforcement → regression → artifact`

—is absent from both `315_f` and the generated appendix. The appendix is currently a useful scientific summary, but not the merge-gated traceability table.

Add the matrix in Rev2. It should expose the complete sentinel/diagnostic obligations; the current sentinel section omits several first-occurrence fields and does not list raw denominators or checkpoint/evaluation trajectories deferred to Unit 5.

### P2 — Appendix verification is not byte-exact

`verify_appendix()` uses text reading, so a CRLF-rewritten file passes despite having different bytes. Compare raw UTF-8 bytes and add a CRLF regression. The current artifact is **6,822 bytes / 6,813 characters**, not the stated 6,814 bytes.

Positive verification:

- Registered cap arithmetic and all three branches are correct.
- Exact C2 replay remains 25/25.
- Full suite: **1,020 passed** under warnings-as-errors.
- Frozen identities and worktree remain clean.

These are local repairs; no Unit 4 redesign is needed.