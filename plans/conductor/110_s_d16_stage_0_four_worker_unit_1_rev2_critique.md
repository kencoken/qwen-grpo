Almost, but I would not formally sign off Unit 1 at `8082c02` yet. One narrow provenance blocker remains.

[executor.py:369](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/executor.py:369) rejects only worker 3 from the pool-free v1 trace schema. Workers 0–2 are also now new four-worker identities—especially worker 2, which now means generic-1.5B/rev10/task-last rather than historical Coder-1.5B/rev9/v0. A new-pool workflow that happens to select only IDs 0–2 can therefore still be persisted under the historical schema without a pool fingerprint.

The check also occurs after worker execution, so a later worker-3 step can leave a partial v1 trace before aborting.

Recommended final Unit‑1 fix:

- Preflight before any worker call and refuse all use of the legacy `TraceWriter` through the amended four-worker executor.
- Preserve existing traces only as historical artifacts.
- Add a regression showing that a worker-2 action cannot be written to v1 and that its worker callback is never invoked.

Alternatively, the pool-bound trace schema may be the first atomic Unit‑2 change, with no execution allowed beforehand. For clean unit closure, I prefer the small fail-closed patch now.

Everything else is correctly addressed:

- worker 3 executes through the Code tool;
- wrong-family routing remains a typed 0.5 outcome;
- the historical smoke is disabled;
- the rev10/task-last fixture is genuinely pool-bound;
- payoff surfaces and frozen selections bind the pool;
- registry views are immutable;
- partial weight/static fingerprints are named honestly.

Verification passed:

- 591 tests under warnings-as-errors;
- 16,665/16,665 agreement over 10,000 latents;
- clean diff check.

Two non-blocking Unit‑2 carry-forwards: replace the remaining untyped integer endpoint/tool boundary with a family-typed boundary, and add an explicit worker-2/worker-3 equality assertion for the numeric two-call fixture rows.

After the trace fix, I recommend immediate Unit‑1 sign-off and moving to Unit 2 without another broad audit.
---

## Resolution (2026-07-22, commit noted in log)

The trace preflight is implemented as recommended:

- `execute_workflow_batch` refuses the legacy `TraceWriter` at entry —
  before the duplicate-id check and before any worker call — so
  neither a complete nor a partial v1 trace of a new-pool execution
  (any worker id, including a 0–2-only workflow) can exist. The
  post-execution worker-3 check is removed as superseded.
- Existing v1 traces are untouched historical artifacts; the
  TraceWriter file-format regressions now drive `write_step` directly.
- New regressions: a worker-2 action with a v1 trace raises with the
  worker callback never invoked (executor level), and a real
  `TraceWriter` threaded through the executor raises with an empty
  `steps.jsonl` (runtime level).

**One deliberate narrowing, flagged for the sign-off decision:** the
preflight gates on `isinstance(trace, TraceWriter)`, not on any trace
object, because the retained worker-eval composed path (106_s §9.4
path 1) threads its `_ComposedTraceAdapter` through the same executor
interface. That adapter is not the v1 schema: its rows and run
manifests carry candidate model/prompt/contract identity and are
verified by the worker-eval loader. A blanket refusal would disable
the retained D16 diagnostics machinery (three composed-mode
regressions fail under it). If a positive marker interface is
preferred over the isinstance gate, that fits naturally in the unit-2
trace-schema work.

Also taken now (was a non-blocking carry-forward): the explicit
worker-2/worker-3 equality assertion over the numeric two-call fixture
rows. The family-typed endpoint/tool boundary remains a unit-2
carry-forward as suggested.

Battery: 592 tests under warnings-as-errors; agreement 16,665/16,665.
