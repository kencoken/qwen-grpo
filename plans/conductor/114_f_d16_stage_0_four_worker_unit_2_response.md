# Unit 2 rev2 — response to the 113_f review

All five P1 findings and all three cleanups are implemented. Battery:
**626 tests** under warnings-as-errors (rev1: 615); agreement unchanged
at **16,665/16,665**; a genuinely cold GPU smoke re-recorded below.

## F1 — execution identity bound to what actually executes

- **Production builder**: `build_pool_runtime(profile)` constructs the
  pool and cache from the one owned profile. The `FourWorkerRuntime`
  constructor (retained for test injection) now requires the pool to
  expose its owned profile and refuses on any byte difference — the
  reviewer's `FourWorkerRuntime(profile_b, pool_a, cache)` reproduction
  now raises before any fingerprint is computed.
- **Runtime-bound execution**: `FourWorkerRuntime.execute_batch(items,
  trace=None)` preflights every item's request contract against the
  profile (a default v0-contract `WorkflowItem` is refused with zero
  worker calls made), generates only through its own
  `worker_call_batch`, and accepts only a `PoolTraceWriter` bound to
  *this* runtime — the runtime-A/trace-B reproduction now raises.
- **Producer identity on records**: `CallRecord` gains
  `selected_worker_fp` and `runtime_fingerprint` (set only by the
  four-worker runtime; the v1 runtime leaves them None), which F4's
  trace verification consumes.

## F2 — frozen treatment settings admit no variation

`validate_pool_profile` now requires exact equality with the frozen
256-token singleton policy, `FROZEN_NF4_CONFIG`, the executable
`TOOL_VERSIONS`, and the implemented `RESOURCE_POLICY` — each refusal
names the drifted setting ("a declared version the executor does not
run is fabricated provenance"). All four reviewer reproductions
(`max_new_tokens=1`, float16 compute, invented tool version, invented
resource policy) are negative tests.

## F3 — device is execution and cache identity

`device` is now a top-level profile key: it flows into `rtp` (profile
hash), `wv` (it is not conductor-only), and `slw` (explicit field) —
and therefore the cache key. `FourWorkerPool` takes its device from
the profile rather than a construction argument. The reviewer's
reproduction is the new regression: a CPU-configured runtime sharing a
cache file with a CUDA-configured one *misses* and generates its own
completion; wv and slw both differ across devices.

## F4 — v2 trace rows carry verified exact-request provenance

Every real-call row now persists `user_message` (the worker user
message, correctly named), the exact rendered `request_text` and its
`request_sha256` (re-hashed and verified at write), `binding_sha256`,
the **complete physical key** (weights + quantization + device), the
§9.2 `endpoint_family_fp` (`epf-…`, also in the manifest), the
`selected_worker_fp` and the producing `runtime_profile_fingerprint`.
Worker identity is **verified against the `CallRecord` that produced
the completion**, not copied from the planned action: a record whose
producer fingerprint names another worker, another runtime, or
tampered request bytes raises at write. All three forgeries are
regressions; the genuine record passes.

## F5 — the smoke enforces a genuinely cold first pass

The command refuses a pre-existing cache file, fails on any first-pass
cache hit, requires cold executions from **all four** workers, and
requires `checkpoint_report` to show both physical models loaded (with
measured parameters printed) before declaring success. The refusal was
exercised for real: rerunning under the rev1 run name failed with
"cache already exists".

## Cleanups (all three)

- Smoke-specific support declaration written to
  `runs/<name>/support.json` (all six cells including fork/join, the
  variant list, and an explicit note that the profile `cell_mixture`
  is a training mixture, not this diagnostic's support).
- `PoolTraceWriter.__exit__` records `status: complete|aborted`; an
  exception-interrupted trace can no longer resemble a successful run
  (regression included).
- Documented in the smoke docstring: construction indices
  0..per_cell−1 lie inside the already-consumed 0–29 D16 prefix, so no
  new construction identities are exposed; unit 3 uses the registered
  `worker_dev` support.

## Re-recorded cold GPU smoke (RTX 4090, 2/cell)

```text
FAIL (as designed): cache runs/stage0-4w-smoke/cache.sqlite already
  exists; the smoke requires a cold first pass        <- rev1 run name
--- fresh run name ---
19 workflows, profile rtp-63b0558302760a61, pool wp-197e286115f56e4a
pass 1: calls {lookup_1p5b: 8, math_1p5b: 13, code_1p5b: 6, code_3b: 6},
        cache hits 0, truncated 0, wall 10.2s
pass 1: statuses {success: 32, typed_failure: 1}; terminal 18/19
peak reserved VRAM: 3.18 GiB
pass 2: 33/33 cache hits, replay byte-identical
checkpoint 1.5B@989aa798: loaded True, measured 1,543,714,304
checkpoint 3B@aa8e7253:  loaded True, measured 3,085,938,688
smoke OK
```

(The rtp/wv values differ from rev1 because `device` is now inside the
profile and the worker-visible projection — that is finding 3 doing
its job.)
