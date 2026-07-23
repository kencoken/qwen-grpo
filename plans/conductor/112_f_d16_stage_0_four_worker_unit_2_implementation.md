# Unit 2 — four-worker Stage-0B runtime (106_s §§9.1–9.3)

Battery: **615 tests** under warnings-as-errors (unit 1: 592);
agreement unchanged at **16,665/16,665**; recorded GPU smoke below.

## What was built

**`pool_runtime.py`** — the v2 runtime layer:

- **v2 profile (`FOUR_WORKER_RUNTIME_PROFILE`, schema_version 2)**
  embeds the ordered `WorkerSpec` entries as the authoritative pool
  declaration (106_s §5). `validate_pool_profile` re-derives them and
  compares against the frozen registry — a profile that omits,
  duplicates, relabels or retunes a worker fails closed before any
  tokenizer loads. The scientific `microbatch` is frozen at **1**
  (singleton-v1); a larger physical batch is rejected with the
  106_s §9.1 wording. `request_contract` must be the frozen
  `task_last`; `prompts.d16_revision` must equal the pool's declared
  bundle revision.
- **`FourWorkerPool`**: tokenizer/model objects keyed by the derived
  weights key (workers 0–2 share the generic-1.5B object, worker 3
  the generic-3B object); at construction the resolved bundle's
  per-family prompt bytes are hashed and verified against each spec's
  registered SHA (behavior, not label); at model load the measured
  NF4-unpacked parameter count is verified against the declared
  registry value — mismatch is a hard stop before any generation.
  `generate_singleton` takes exactly one request; there is
  deliberately no batched entry point on this pool.
- **`FourWorkerRuntime`**: the public boundary is
  `worker_call_batch(worker_id, user_messages)`; family resolution is
  internal to the pool. Cache key = worker-visible fingerprint +
  **selected-logical-worker execution fingerprint (`slw-…`)** +
  canonical rendered request. `slw` binds worker id and name, family,
  model revision, prompt and chat-template hashes, request contract,
  grammar/tool versions, quantization, decoding, caps and stopping —
  the complete §9.3 list the unit-1 static fingerprint deliberately
  deferred. Byte-identical in-flight requests are one singleton
  generation and one stored row (v1 dedup discipline retained).
  The runtime refuses a v1 `CompletionCache`.
- **`WorkerCompletionCache`** (in `cache.py`): a new table
  (`worker_completions`) and selector column (`selected_worker_fp`) —
  per §8.5, no v1 field name carries the new identity, and a v1 cache
  file's rows are never consulted. The v1 class is untouched for the
  retained D16 machinery.
- **`PoolTraceWriter`** — trace schema v2, deliberately not a
  `TraceWriter` subclass (the executor refuses that class, 110_f).
  The manifest binds the pool fingerprint, per-worker `slw`
  fingerprints and the re-derived logical-to-physical mapping; every
  step row carries worker id, stable name, endpoint family, weights
  key and `slw` fingerprint.
- Shared NF4 loading extracted (`load_nf4_checkpoint`,
  `measured_parameters` in `workers.py`) so quantization can never
  drift between the v1 endpoint pool and the four-worker pool.

**Smoke re-enabled** (was disabled fail-closed by 108_f F2): rebuilt
on the four-worker runtime — reference routing per cell, a `:w3`
variant of every workflow with a Code node, and one deliberate
wrong-family workflow (`:wf`) asserted to yield a typed 0.5 outcome;
two passes with the warm pass required to be fully cache-served and
byte-identical.

## Recorded smoke (RTX 4090, 2/cell)

```text
19 workflows, profile rtp-d5ec3ef128a3c32e, pool wp-197e286115f56e4a
physical: Qwen2.5-1.5B-Instruct@989aa798 <- [lookup_1p5b, math_1p5b, code_1p5b]
physical: Qwen2.5-3B-Instruct@aa8e7253  <- [code_3b]
pass 1: calls {lookup_1p5b: 8, math_1p5b: 13, code_1p5b: 6, code_3b: 6},
        cache hits 0, truncated 0, wall 10.5s
pass 1: statuses {success: 32, typed_failure: 1}; terminal 18/19
peak reserved VRAM: 3.18 GiB
pass 2: 33/33 cache hits, replay byte-identical
smoke OK
```

The single `typed_failure`/`E_PARSE` and the one non-1.0 terminal are
the deliberate `:wf` wrong-family item (scored 0.5, no abort — §6.2
exactly). Worker 3 executed 6/6 successfully through the real 3B
checkpoint, parameter-verified at load. Both physical objects resident
at 3.18 GiB peak — far under the 22 GiB gate.

## Test coverage added (23 new)

Profile fail-closed battery (omit/duplicate/relabel/re-revision/
microbatch≠1/wrong contract/wrong bundle/unknown field); w2/w3
byte-identical requests with **never-crossing cache rows** (each
worker's warm hit returns its own completion; one singleton generation
each, ever); shared-weights workers never share rows; in-flight dedup
= one generation; D11 sharing (wv equal across observation conditions,
rtp not); `slw` binds template and prompt hashes; v1/v2 caches are
disjoint tables; unknown worker id refused; executor end-to-end over
the runtime with worker 3 and a v2 trace (manifest pool binding,
per-step worker name/family/weights key/fingerprint); real-tokenizer
rendering matches the reviewed `pool_rendered_requests.json` fixture
byte-for-byte for all four workers; a bundle contradicting the
registry's prompt SHAs is refused at pool construction.

## Carry-forward disposition

The 110_f suggestion to retype the integer endpoint/tool boundary
(`contract.run_worker_output(endpoint: int, …)`) is **deferred with
rationale**: that signature is called throughout the frozen,
review-hardened worker-eval machinery (isolated scorer, probe, P0
replay, agreement) with family indices. The executor now resolves
workers through the registry before that boundary, and the smoke plus
e2e tests exercise it for all four workers; retyping it is a cosmetic
change with a wide blast radius into frozen code — proposed for unit 3
alongside the evaluation-support work if the reviewer still wants it.
