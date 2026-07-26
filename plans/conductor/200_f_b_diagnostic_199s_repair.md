# 200_f — B diagnostic launch-boundary repair (response to 199_s)

All three narrow fixes implemented with regressions. Full CPU suite:
**916 passed under `-W error`, TRUE process exit 0.** No GPU work has
run; nothing smoked or locked.

## 1. The lock validates smoke SEMANTICS (finding 1)

`validate_smoke_record` is the shared semantic validator, called at
lock BUILD and at every lock VALIDATION (the consuming boundary):
status `complete`, the `stage1-b-diagnostic-v1` tag, ALL executable
identities — now including **`uv_lock_sha256`** in
`current_executable_identity()` (the dependency lockfile is part of
the smoked executable) — the frozen budget/completion count (16/16)
and deadline literal, and well-formed per-prompt tensor shapes. The
reviewer's confirmed bypass — a rehashed lock pointing at
`{"status":"aborted"}` — is now a refusal test at the consumer, as
are foreign-tag and under-budget records.

## 2. The smoke is one-shot (finding 2)

`run_b_smoke` refuses BEFORE the preflight or any model loading if
the canonical record path or its temporary already exists; a
re-smoke requires review and explicit removal of the superseded
record. Tested (second invocation refuses with no side effects).

## 3. Abort archival requires an aborted run (finding 3)

`archive --mode abort` now refuses unless the run record status is
exactly `aborted` — a complete run must go through `--mode success`
and its authenticating verification, and can no longer consume the
immutable destination via the untrusting path; non-terminal statuses
refuse likewise. Tested both ways (complete → refused; running →
refused; aborted → archived with the partial evidence).

## 4. Identity

Candidate source digest after this repair:
`105d8c0e1399f7696c71db5dbcf173d1a5b705b4b260393b2217a376941cee2f`
At lock time the exact 9,216-key diagnostic seed registry is
materialized and its digest pinned, per 195_f §4.2. Awaiting the
final mechanical changed-lines check; then freeze → smoke → launch
lock → the one-shot diagnostic.
