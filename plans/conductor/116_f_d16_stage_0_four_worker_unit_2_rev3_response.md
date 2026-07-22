# Unit 2 rev3 — response to the 115_f review

All three P1 findings fixed; the recommended P2 hardening is taken now
rather than carried. Battery: **630 tests** under warnings-as-errors
(rev2: 626); agreement unchanged at **16,665/16,665**. Per the review,
the valid 2-per-cell GPU smoke is not repeated — the fixes are
CPU-provenance changes with targeted regressions.

## F1 — provenance immutable after construction

`FourWorkerRuntime` stores `_profile` privately; every internal use
(fingerprints, preflight, physical mapping, trace metadata) reads it,
and the public `profile` property returns a defensive deep copy. The
`worker_fingerprints` and `endpoint_family_fingerprints` dicts are
read-only `MappingProxyType` views. The regression mutates **both**
the caller's original dict and the returned property (device and
request_contract), then proves the fingerprint, the property value and
the v0-item refusal are all unchanged — the reviewer's mutable-trace
reproduction is dead.

## F2 — the executor composition cannot bypass the preflight

Chosen fix: the reviewer's second option, keeping the 106_s §5 public
generation boundary public. `execute_workflow_batch` now invokes a
trace-owned `preflight_items(items)` hook before any worker call;
`PoolTraceWriter.preflight_items` verifies every item's request
contract against its bound runtime. The exact reproduction —
`execute_workflow_batch(items_v0, rt.worker_call_batch,
trace=PoolTraceWriter(rt))` — now raises with the spy asserting zero
worker calls. The worker-eval `_ComposedTraceAdapter` has no such hook
and is unaffected. (`rt.execute_batch` remains the recommended path
and retains its own stricter preflight, which also covers trace-less
execution.)

## F3 — per-cell bounded to the consumed prefix

`validate_per_cell` enforces `1 <= per_cell <= 30` before any runtime
or cache construction, so the support declaration's consumed-prefix
claim is true by construction. Bounds chosen over freezing to exactly
2 to keep `--per-cell 1` available for quick diagnostics — flagged
here in case the reviewer prefers the hard freeze. Rejection tested at
the function level and fired live (`--per-cell 31` refused at the
CLI before anything was built).

## P2 hardening (taken)

`write_step` now additionally verifies, for every real-call row:
`record.completion == call_record.completion`; a non-empty
`binding_sha256`; and that `user_message` re-renders through the bound
pool to exactly the recorded request bytes. A swapped same-worker
record, a missing binding hash, and a tampered user message are all
regressions; the consistent row persists.
