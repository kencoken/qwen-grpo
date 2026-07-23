## Review outcome

Changes requested. Unit 1 is not ready for sign-off yet. The enumeration and control changes are sound, but four issues could affect execution identity or persisted scientific meaning.

### Blocking findings

1. **[P1] Worker 3 parses successfully but cannot execute.**

   [executor.py:199](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/executor.py:199) passes `step.worker_id` directly to the three-valued endpoint/tool boundary. Worker 3 therefore reaches [tools.py:380](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/tools.py:380) and raises:

   ```text
   InfrastructureError: unknown endpoint 3
   ```

   Resolve worker ID → endpoint family before artifact parsing/tool execution. Add end-to-end tests proving workers 2 and 3 both execute the Code grammar/tool successfully, including a composed workflow.

2. **[P1] The interim smoke can silently run the wrong worker configuration.**

   [smoke.py:64](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/smoke.py:64) rejects worker 3 but executes workers 0–2 through the legacy runtime. That profile still contains:

   - Coder-1.5B for Code rather than the frozen generic-1.5B worker;
   - prompt revision rev9 rather than rev10;
   - `worker-blocks-v0` rather than the frozen task-last request contract.

   Thus worker 2 can be recorded as the new logical identity while actually executing the historical model and request configuration.

   Either disable the smoke completely until Unit 2 lands, or bind it to the exact four-worker profile now. Rejecting only worker 3 is not fail-closed.

3. **[P1] The chat fixture is generated from the historical profile, not the frozen pool.**

   [gen_chat_fixtures.py:97](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/gen_chat_fixtures.py:97) constructs `WorkerPool(DEFAULT_RUNTIME_PROFILE)`. Consequently:

   - every existing hash remained unchanged even though rev10 changed the Math system prompt;
   - the added worker-2/worker-3 equality is produced by routing both IDs through the same legacy Code endpoint;
   - the fixture is not evidence for the frozen rev10/task-last configuration.

   Generate a pool-bound fixture using the exact rev10 prompt and frozen chat-template/request contract. Existing semantic user-message hashes should remain unchanged, but rev10 Math rendered-request hashes should intentionally change.

4. **[P1] Persisted payoff identity is not bound to the worker pool.**

   [oracle.py:386](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/oracle.py:386) persists only kind, cell and outcomes. The digest at [oracle.py:885](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/oracle.py:885) similarly hashes only the surface content.

   `surfdig2` rejects historical three-worker surfaces by cardinality, but it cannot distinguish two materially different four-worker pools. A surface generated before a same-cardinality model/prompt change could be silently reinterpreted.

   Bind and verify `STAGE0_POOL_FINGERPRINT` in persisted surfaces/calibration identity. The trace schema also remains v1 and pool-free; either update it in this unit as [106_s §8](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/plans/conductor/106_s_stage_0_four_worker_orchestration_pivot.md:325) requires, or keep four-worker trace writing unavailable until Unit 2.

### Smaller issues to fix before Unit 2

- `WORKER_NAMES` and `WORKER_TO_ENDPOINT` are mutable dictionaries at [workerpool.py:83](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/workerpool.py:83). Mutation changes dispatch without changing the pool fingerprint. Use immutable views.
- `physical_checkpoint_key()` at [workerpool.py:48](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/workerpool.py:48) omits quantization and device. Rename it to a weights/checkpoint identity or construct the complete four-part physical key at the runtime boundary.
- `worker_fingerprint()` is described as cache identity but omits chat-template, request-contract, decoding, token-cap, tool and runtime inputs. Rename it as a static logical identity until Unit 2 composes the complete execution fingerprint.
- [types.py:349](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/types.py:349) still says endpoint indices equal worker IDs.
- Add the missing full-workflow parser regression for accepting worker 3 and rejecting worker 4.

### What is correct

- Exact 4/16/64 assignment enumeration.
- The mechanically derived 32 two-call workflows.
- Four-way `best_fixed`, uniform-random, runner-up and one-call controls.
- Lexicographic tie-breaking.
- Rev10 prompt hashes in the static registry.
- Existing semantic generation and oracle behavior.

Verification on `picome`:

- `583 passed` under warnings-as-errors.
- Reference/tool agreement: `16,665/16,665` node executions across exactly 10,000 latents.

These passing tests show no general regression, but they do not exercise the broken worker-3 execution boundary or the conflicting runtime identity. I recommend resolving the four blockers, adding the narrow regressions above, and then signing off Unit 1 without another open-ended audit.
---

## Addendum — reviewer response on F3 scope (2026-07-22)

You are correct. The frozen §4 configuration explicitly requires
`worker-blocks-task-last-v1` for all four workers. The fixture should
represent that complete frozen configuration, not merely substitute
rev10 prompts into the historical v0 request layout. Therefore:

- Every actual rendered-request hash should change from the legacy
  fixture, because every worker request has a Task block whose position
  and final instruction change under `task_last`.
- Math changes for two independent reasons: the task-last contract and
  the rev10 Math prompt.
- Lookup and Code change because of the task-last contract.
- The raw `chat_template:*` hashes should remain unchanged if the
  pinned tokenizers confirm the shared Qwen2.5 template.
- Worker 2 and worker 3 should have separate fixture keys whose request
  hashes are asserted equal after rendering through their independently
  pinned tokenizers.
- `byte_stability.json` should retain its existing hashes because it is
  the generator/semantic-rendering regression fixture, not the selected
  execution-contract fixture. Its documentation should make that
  distinction explicit.

I would also make the new chat fixture matrix worker-specific —
`cell × step × worker`, not `cell × step × endpoint family` — and
record the pool fingerprint, prompt revision, request-contract
key/digest, and tokenizer/chat-template hashes alongside it.

So I retract the "only Math should change" expectation from my
critique. That would apply only to a rev10-only regeneration under v0,
which is not the configuration frozen in §4. The proposed full
task-last regeneration is the correct implementation.
