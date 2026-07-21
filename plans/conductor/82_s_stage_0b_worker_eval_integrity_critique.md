## Review verdict

Request changes before merging [PR #4](https://github.com/kencoken/qwen-grpo/pull/4). The evaluator’s core scientific structure is sound, and I found no regression in the existing Stage 0B execution path. However, several admission and provenance boundaries can currently certify runs that do not satisfy the plan.

Reviewed HEAD: `13491e7`.

### Blocking findings

1. **[P1] P1 can admit the wrong population or materially different requests.**

   [worker_eval_probe.py:308](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval_probe.py:308) and [worker_eval_probe.py:335](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval_probe.py:335)

   `admit_singleton()` does not require the registered namespace, 10 examples per cell, private visibility, all three renderers, 300 cases, distinct processes, a clean shared commit, or identical per-case request hashes.

   Reproduced:

   - A one-case, one-renderer, visible, wrong-namespace artifact was admitted.
   - Changing `request_sha256` across the three runs while leaving completions equal was still admitted.
   - The real CLI can produce a 100-case, one-renderer run that passes its coverage check.
   - There is no authoritative two-run, 900-case confirmation gate.

   Add one small P1 precondition validator covering the exact registered population, regenerated case set, process identity, source/config identity and request hashes. A separate minimal 900-case confirmation check is also needed.

2. **[P1] P0 does not establish that the recorded chunks were the physical model batches.**

   [worker_eval_probe.py:218](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval_probe.py:218), [worker_eval_probe.py:264](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval_probe.py:264), [workers.py:149](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/workers.py:149)

   Request hashes are optional, and an oversized “physical chunk” is accepted. A 17-request Code chunk is recorded as one chunk even though `WorkerPool.generate()` silently executes it as `16 + 1`.

   Require pinned request hashes, nonempty/unique chunks, and chunk sizes that exactly match the retained physical manifests. P0 comparisons should also validate cohort and execution headers before comparing results.

3. **[P1] Execution provenance can disagree with what actually ran.**

   [runtime.py:247](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/runtime.py:247), [worker_eval.py:84](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:84), [worker_eval.py:673](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:673)

   Two reproducible paths remain:

   - `Runtime.profile` is publicly mutable. Mutating it after construction changes the profile later written to the manifest while the cached fingerprint and pool behavior remain unchanged.
   - `singleton_call()` rejects cache hits, but not an enabled cold cache. A normal `CompletionCache` can miss, generate, store the completion, and produce a row labelled `cache_source="disabled"`.

   Keep the owned profile private/immutable—or at minimum rederive and verify its fingerprint when building and loading a manifest. Scientific calls should verify the no-op cache before generation, not infer that it was disabled from a cache miss.

4. **[P1] The persisted loader accepts impossible call states and relabelled endpoints.**

   [worker_eval.py:1162](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:1162) and [worker_eval.py:1198](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:1198)

   A rehashed isolated row can be changed to `dependency_blocked`, retain a successful value, and still load and score correct. A Lookup call can also be relabelled as Math and load successfully.

   For isolated runs, require every regenerated case to be `called` and compare endpoint, observation, mode, position, predecessor metadata, request and binding against the regenerated case. Apply the corresponding identity checks to composed rows and enforce the complete status-conditional schema.

5. **[P1] Candidate-arm identity remains label-driven and comparisons are too permissive.**

   [prompts.py:85](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/prompts.py:85), [worker_eval.py:102](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:102), [worker_eval.py:1238](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:1238)

   - A caller-created `PromptBundle` with arbitrary bytes can claim `revision="rev0"` and `status="FROZEN forged"` and be accepted as a frozen candidate if the pool renders those bytes.
   - Request-contract metadata is hashed, but not verified against the actual builder implementation or a frozen status.
   - `compare_worker_eval_runs(run, run, "prompt")` succeeds with no actual prompt difference.
   - Model comparisons permit the entire worker pool, caps and microbatch settings to change; arbitrary Git differences are always allowed.
   - One-renderer runs are accepted as complete and comparable because crossing is checked only against the renderer subset declared by the caller.

   Resolve frozen prompts through the authoritative registry, bind request contracts to an executable/versioned contract, require the declared dimension to differ in fact, and narrow comparison allowlists to the intended endpoint and field. Diagnostic renderer subsets can remain supported, but they must not be comparable or freezable as full D16 runs.

### Lower-severity discrepancies

- [worker_eval.py:188](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:188) stores the endpoint class as `node_family`, losing distinctions such as `seq_at`, `seq_count`, `modular` and `affine`. This weakens the intended worst-node-stratum analysis.
- The summary provides enough counts to derive renderer differences, but omits the specified max–min gap and pairwise flip counts/rates.
- The manifest omits the model generation-config EOS set actually used, the NVIDIA driver version, and the applied P1 thresholds.

### Verification

- Full suite: `535 passed` with warnings treated as errors.
- Reference/tool agreement: `16,665 / 16,665` node executions over exactly 10,000 latents.
- Diff formatting: clean.
- No legacy Stage 0B executor/cache regression found.

The corrections above are local validation and provenance fixes; they do not require a larger framework or cache redesign. After those changes, I would do one focused re-review of the affected boundaries and then merge rather than reopening the broader architecture.