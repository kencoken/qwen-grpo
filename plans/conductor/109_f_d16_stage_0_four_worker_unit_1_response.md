# Unit 1 rev2 — response to the 108_f review

All four blocking findings and all five smaller issues are implemented.
One claim from the rev1 unit is retracted below. Battery: **591 tests**
under warnings-as-errors; agreement unchanged at **16,665/16,665** over
exactly 10,000 latents; `byte_stability.json` byte-identical.

## F1 — worker 3 executes (fixed)

`executor._endpoint_id()` resolves the worker id through
`WORKER_TO_ENDPOINT_ID` at the artifact/tool boundary only — generation
batching stays keyed by worker. An unregistered id raises
`InfrastructureError` (the parser already bounds actions to the pool;
a directly constructed workflow must abort, never guess a family).
New regressions: worker 3 reaches the terminal on `code_atomic` and in
a composed `fork_join` workflow; wrong-family selection (workers 1 and
3 on a Lookup node) is a typed failure scoring 0.5, not an abort;
worker id 7 aborts.

## F2 — smoke disabled (fixed)

`run_pass` and `main` both raise immediately, naming the cause: the
historical `DEFAULT_RUNTIME_PROFILE` still carries the retired
Coder-1.5B Code checkpoint, rev9 prompts and the v0 contract, so any
partial binding would record new worker identities against the
historical execution configuration. The command re-enables only when
unit 2 binds it to the exact frozen pool. The historical recorded
smoke result stands in `conductor_log.md`.

## F3 — pool-bound fixture (fixed per the addendum); rev1 claim retracted

**Retraction:** the rev1 "worker-2/worker-3 byte-equality" evidence was
produced by routing both ids through the same legacy Code endpoint of
`DEFAULT_RUNTIME_PROFILE` — trivially true and evidentially empty.

`gen_chat_fixtures` is rewritten as the frozen-configuration fixture
(`fixtures/pool_rendered_requests.json`, 126 entries), per the 108_f
addendum:

- **worker-specific matrix** `cell × step × worker` — all four workers
  render every step (wrong-family renderings included: these are §9.4
  assignment-surface requests) — plus per-step user-message hashes and
  the registry-derived two-call family (64 call entries);
- rendered under **rev10 prompts + `worker-blocks-task-last-v1` + each
  worker's independently pinned tokenizer**, byte-matching the
  `WorkerPool.render_request` convention;
- provenance recorded alongside: pool fingerprint
  `wp-197e286115f56e4a`, prompt revision, contract key + digest
  `8638fdad…`, per-worker chat-template SHA and tokenizer pin;
- as predicted in the addendum: **every rendered-request hash differs
  from the legacy fixture** (task-last moves the Task block in every
  request; Math also changes for the rev10 amendment), while the four
  `chat_template:*` hashes all equal the shared Qwen2.5 template hash
  `cd8e9439…`;
- the acceptance test asserts worker-2/worker-3 hash equality across
  the whole matrix — now rendered through *independently pinned
  tokenizers*, this is the genuine §6.2 attribution guarantee;
- the legacy `chat_template_bytes.json` is deleted (history in git);
  `byte_stability.json` retained byte-identical, its generator
  docstring now stating the generator/semantic-vs-execution-contract
  distinction explicitly.

## F4 — pool-bound payoff identity (fixed)

`ValidatedSurface` and `FrozenSelections` now carry `worker_pool`,
verified against `STAGE0_POOL_FINGERPRINT` at construction and at
`from_json` (exact-key schemas, so a pool-free pre-108_f artifact
fails closed rather than defaulting). The fingerprint flows into
`surface_digest` through `to_json`, so a same-cardinality surface from
a different pool can neither validate nor reproduce a digest.
Traces: the reviewer's second option — `_trace_step` refuses to record
a worker outside 0–2 under trace schema v1, with the pool-bound schema
landing in unit 2 (consistent with the disabled smoke).

## Smaller issues (all fixed)

- `WORKER_NAMES` / `WORKER_TO_ENDPOINT` (+ new `WORKER_TO_ENDPOINT_ID`)
  are `MappingProxyType` views; tests assert in-place mutation raises.
- `physical_checkpoint_key()` → `weights_key()`; docstring states the
  complete physical key (quantization, device) composes at the runtime
  boundary.
- `worker_fingerprint()` → `worker_static_fingerprint()`; docstring
  states it is the static identity half only, with the full execution
  fingerprint composed in unit 2. (Hash inputs unchanged — the golden
  `wp-` value is unaffected.)
- `types.py` comment no longer claims endpoint indices equal worker
  ids.
- Full-workflow parser regression added: worker 3 accepted, worker 4
  rejected.

## Deltas a re-review should expect

- `pool_rendered_requests.json` is new (126 entries, provenance
  header); `chat_template_bytes.json` deleted.
- `surface_digest` values change once per this schema addition
  (`to_json` gained `worker_pool`); no persisted bundles existed.
- 591 tests (rev1: 583): +6 executor boundary regressions, +2 pool
  binding, +immutability/rename assertions folded into existing tests.
