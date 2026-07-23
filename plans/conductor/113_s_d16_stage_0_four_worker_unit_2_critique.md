## Review outcome

Changes requested before Unit 3. The runtime execution itself looks healthy, and the recorded GPU smoke is behaviorally credible. The remaining blockers are provenance and acceptance-gate issues rather than model behavior.

### Blocking findings

1. **[P1] Runtime identity is not bound to the pool and request contract actually executed.**

   `FourWorkerRuntime(profile_b, pool_a, cache)` accepts independently configured objects. I reproduced a real pool using a 256-token cap while the runtime, cache, and trace fingerprints claimed a cap of 1.

   There is a second version of the same problem at the executor boundary: a trace writer for runtime A accepts calls from runtime B. The resulting trace recorded A’s `rtp` and `slw` even though B produced the completion. Likewise, a default `WorkflowItem` using the old v0 request contract can execute under a profile claiming `task_last`.

   The simplest correction is for the production builder to construct the pool and cache from one owned profile, then provide a runtime-bound execution method which preflights every item’s request contract. Test injection can remain private or explicitly marked as such.

   [pool_runtime.py](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-unit2/tasks/conductor/pool_runtime.py:391)

2. **[P1] The frozen profile accepts material treatment changes.**

   `validate_pool_profile` accepted all of these:

   - `max_new_tokens = 1`
   - NF4 compute dtype changed to `float16`
   - an invented Code tool version
   - an invented resource policy

   The latter two are particularly misleading because fingerprints record the invented declarations while the unchanged executor code actually runs.

   Require exact equality with the frozen 256-token singleton policy, `FROZEN_NF4_CONFIG`, `TOOL_VERSIONS`, and `RESOURCE_POLICY`. Add negative tests for each.

   [pool_runtime.py](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-unit2/tasks/conductor/pool_runtime.py:116)

3. **[P1] Device is missing from the execution and cache identity.**

   Device appears only in the descriptive logical-to-physical manifest. It is absent from `rtp`, `wv`, `slw`, and therefore the cache key. I reproduced a CPU-configured runtime returning a cached CUDA-produced result without generating; all three fingerprints were identical.

   Since the frozen physical key includes device, put the effective device in the bound execution profile and worker/cache fingerprints. Add a test proving cross-device reuse misses or is explicitly refused.

   [pool_runtime.py](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-unit2/tasks/conductor/pool_runtime.py:204)

4. **[P1] V2 traces do not yet satisfy the exact-request provenance contract.**

   Each row currently stores:

   - `record.request`, which is the worker user message—not the rendered chat request;
   - a hash supplied by the callback, without persisting or checking the corresponding rendered request;
   - no `binding_sha256`;
   - only the model/revision `weights_key`, rather than the complete physical key; and
   - no separate endpoint-family fingerprint required by §9.2.

   Moreover, worker identity is copied from the planned action rather than verified against the `CallRecord` that produced the completion. That is why the runtime-A/worker-B trace mismatch succeeds.

   Persist and validate `user_message`, exact `request_text`, its hash, `binding_sha256`, actual worker/runtime fingerprints, endpoint-family fingerprint, and complete physical key.

   [pool_runtime.py](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-unit2/tasks/conductor/pool_runtime.py:540)

5. **[P1] The smoke command does not enforce a cold first pass.**

   The recorded run happened to have zero first-pass hits, so its evidence is not invalidated. But the command opens any existing cache and only requires the second pass to be fully cached. A pre-populated cache could therefore pass without loading or parameter-checking either checkpoint.

   Require an empty cache or zero first-pass hits, all four workers to have cold executions, and `checkpoint_report` to show both physical models loaded before declaring success.

   [smoke.py](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-unit2/tasks/conductor/smoke.py:182)

### Non-blocking cleanups

- The smoke profile declares `fork_join: 0` while its support deliberately executes fork/join. Record a smoke-specific support declaration rather than letting the training mixture describe the diagnostic.
- `PoolTraceWriter.__exit__` marks `closed: true` even when execution raises. Add `complete|aborted` status so partial traces cannot resemble successful runs.
- The smoke reuses construction indices 0–1. Those lie within the already-consumed 0–29 D16 prefix, so no new construction identities were exposed. Document that fact; Unit 3 must use the registered `worker_dev` support.

### What passed

- 615 tests pass under warnings-as-errors.
- Agreement remains 16,665/16,665 over exactly 10,000 latents.
- Physical sharing is correct: workers 0–2 share one 1.5B object; worker 3 uses the 3B object.
- Worker-specific cache isolation and v1/v2 table separation are correct.
- Singleton generation, prompt-byte verification, and parameter-count checks are sound.
- The fresh RTX 4090 smoke produced 33 cold calls across workers 0–3, 33/33 warm hits, valid worker-3 execution, and 3.18 GiB peak reserved VRAM.

After the five P1s are fixed, rerun the focused tests and one genuinely cold GPU smoke. A targeted close-out review should then be enough; another broad Unit-2 audit should not be necessary.

---

## Resolution (2026-07-22)

All five P1 findings and all three cleanups implemented; full detail in
`114_f_d16_stage_0_four_worker_unit_2_response.md`. Headlines: pool and
cache are constructed from one owned profile with a runtime-bound
`execute_batch` (contract preflight, trace binding, producer-verified
CallRecords); the frozen 256-token singleton policy, NF4 config, tool
versions and resource policy are exact-equality validated; `device` is
in the profile and all fingerprints (cross-device cache reuse misses);
v2 trace rows persist user_message, verified rendered request bytes +
hash, binding_sha256, complete physical key, endpoint-family and
producer fingerprints; the smoke refuses a pre-existing cache and
requires cold executions from all four workers plus both checkpoints
loaded. Every reviewer reproduction is now a negative regression.
626 tests; agreement 16,665/16,665; cold GPU smoke re-recorded
(including a real firing of the pre-existing-cache refusal).
