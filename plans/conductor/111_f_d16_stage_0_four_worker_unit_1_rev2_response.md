# Unit 1 rev2 follow-up — response to the 110_f trace finding

The one remaining blocker is implemented as recommended (the small
fail-closed patch now, not the deferred unit-2 alternative). Battery:
**592 tests** under warnings-as-errors; agreement unchanged at
**16,665/16,665** over exactly 10,000 latents.

## The fix

- **Preflight, before any worker call.** `execute_workflow_batch`
  refuses a legacy `TraceWriter` at entry — ahead of the duplicate-id
  check and ahead of any generation — so neither a complete nor a
  partial v1 trace of a new-pool execution can exist. This covers the
  full finding, not just worker 3: a workflow selecting only ids 0–2
  (worker 2 now meaning generic-1.5B/rev10/task-last, not the
  historical Coder-1.5B/rev9/v0) can no longer be persisted under the
  pool-free historical schema.
- **The superseded check is removed.** The rev2 post-execution
  worker-3 guard in `_trace_step` is deleted; `_trace_step` is plain
  again and unreachable with a live legacy writer.
- **Existing traces are historical artifacts only.** Nothing rewrites
  or reinterprets them; the `TraceWriter` file-format regressions
  (manifest fields, step rows, overwrite refusal) now drive
  `write_step` directly instead of going through the executor.

## New regressions

1. Executor level: a **worker-2** action with a v1 trace raises
   `InfrastructureError` and the worker callback is **never invoked**
   (spy asserts an empty call list) — exactly the requested test.
2. Runtime level: a **real `TraceWriter`** threaded through the
   executor raises, and `steps.jsonl` is asserted empty afterwards —
   no partial trace.

## One deliberate narrowing, flagged for the sign-off decision

The preflight gates on `isinstance(trace, TraceWriter)` rather than on
any non-None trace object. Reason: the retained worker-eval composed
path (106_s §9.4 path 1, "operator-aligned D16 diagnostics") threads
its `_ComposedTraceAdapter` through the same executor trace interface.
That adapter is not the v1 schema — its rows and run manifests carry
candidate model/prompt/contract identity and are verified by the
worker-eval loader — and a blanket refusal disables the retained
diagnostics machinery (three composed-mode regressions fail under it).
If a positive marker interface ("pool-aware trace") is preferred over
the isinstance gate, that fits naturally in the unit-2 trace-schema
work; happy to take it there.

## Carry-forwards

- **Taken now** (was non-blocking): explicit worker-2/worker-3
  equality assertions over the numeric two-call fixture rows —
  swapping worker 2 for worker 3 at either call position leaves that
  call's rendered hash unchanged, for both orientations and all
  partner workers.
- **Unit 2 as suggested:** replacing the remaining untyped integer
  endpoint/tool boundary with a family-typed boundary.

A short resolution note with the same content is appended to `110_f`
for the reviewer's re-check.
