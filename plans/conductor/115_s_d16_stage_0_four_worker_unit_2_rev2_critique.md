## Final review: changes requested

Commit `43575e5` is close, but I would fix three small issues before Unit 3.

### Blocking findings

1. **[P1] Runtime provenance remains mutable after construction.**

   `FourWorkerRuntime.profile` is a public mutable dictionary. After fingerprints and the pool are bound, changing `rt.profile["device"]` or `request_contract` changes later preflight and trace metadata without changing the pool or recorded fingerprint.

   I reproduced a trace whose embedded profile said CUDA while its unchanged fingerprint and executing pool represented CPU.

   Store a private `_profile`, use it internally, and expose only a defensive copy or read-only view. Test mutation of both the caller’s original profile and the returned property.

2. **[P1] The old public executor composition bypasses request-contract preflight.**

   The intended `rt.execute_batch(...)` path correctly rejects v0 items. But this still succeeds:

   ```python
   executor.execute_workflow_batch(
       items,
       rt.worker_call_batch,
       trace=PoolTraceWriter(rt),
   )
   ```

   I reproduced a v0 request completing successfully while the finished trace declared `worker-blocks-task-last-v1`.

   This is a realistic supported-API path, not adversarial object construction. Either make the low-level callback private, or have the executor invoke a trace/runtime-owned contract preflight before any calls.

3. **[P1] `--per-cell` can cross the consumed construction boundary.**

   The support declaration claims every index lies within the consumed construction prefix 0–29, but `--per-cell` is unrestricted. A value of 31 includes construction index 30 while recording the opposite claim.

   Prefer freezing this acceptance command to exactly `2`; alternatively enforce `1 <= per_cell <= 30`. Add a rejection test before runtime/cache construction.

### Recommended local hardening

The trace writer verifies worker/runtime fingerprints and the rendered-request hash, but it does not cross-check:

- `user_message` against the request re-rendered by the bound pool;
- `record.completion` against `call_record.completion`; or
- that a real call has a binding hash.

A swapped same-worker call record can therefore produce an internally inconsistent trace. This is not reachable through the current correct runtime ordering, so I would call it P2, but it is cheap and particularly useful before Unit 3’s larger batched execution.

### What is now correctly closed

- Exact frozen cap, NF4, tool, and resource settings are enforced.
- Pool/profile mismatch fails closed.
- Device participates in `rtp`, `wv`, `slw`, physical identity, and cache isolation.
- V2 traces contain exact request text/hash, binding, full physical key, and family/worker/runtime fingerprints.
- Aborted traces are distinguished from completed traces.
- Cold-cache acceptance and loaded-checkpoint verification work.

Independent verification:

- 626 tests passed under warnings-as-errors.
- Agreement remained 16,665/16,665.
- Fresh RTX 4090 smoke passed: 33 cold calls, 0 cold hits, 33/33 warm hits, both checkpoints loaded and parameter-verified, 3.18 GiB peak VRAM.
- Reusing the run name failed immediately on the existing cache.

After the three P1 fixes, targeted CPU regressions are sufficient; the valid 2-per-cell GPU smoke does not need repeating. Then I would sign off Unit 2 and move directly to Unit 3 without another broad audit.
---

## Resolution (2026-07-22)

All three P1s fixed, plus the P2 hardening taken now; detail in
`116_f_d16_stage_0_four_worker_unit_2_rev3_response.md`. Headlines:
`FourWorkerRuntime` stores a private `_profile` and exposes only a
defensive copy (both mutation directions tested; fingerprint views are
read-only proxies); the executor invokes a trace-owned
`preflight_items` before any worker call, so the reproduced
executor+callback+trace composition raises with zero calls made (the
§5 public generation boundary stays public); `--per-cell` is bounded
to 1..30 with a rejection before runtime/cache construction (live CLI
firing verified); and v2 trace writes now cross-check completion
against the producing record, require a binding hash on real calls,
and re-render the user message through the bound pool. 630 tests;
agreement 16,665/16,665; no GPU re-run needed per this review.
