## Review verdict

Request changes before merging `dec2863`. Most earlier findings are correctly closed, and I found no regression in the existing Stage 0B execution path. Three narrow correctness gaps remain in paths that will be used during D16.

### Blocking findings

1. **[P1] The §7.4 confirmation does not prove two fresh 900-case runs.**

   [worker_eval.py:1433](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:1433) accepts any two loaded runs. It does not require:

   - the complete 900-call isolated population;
   - private visibility and all renderers;
   - singleton generation or canonical order;
   - distinct processes or even distinct runs; or
   - the same clean commit—`git` is entirely allowed to differ.

   Reproduced directly:

   ```text
   confirm_repeat_run(run, run)
   -> {'confirmed': True, 'reasons': [], 'cases': 30}
   ```

   The new test currently codifies this incorrect behavior by expecting a 30-case confirmation at [test_conductor_worker_eval.py:1195](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/test_conductor_worker_eval.py:1195).

   Require the exact registered 900-case isolated population, singleton policy, canonical generation ordinals, two distinct recorded process identities, distinct run IDs and one clean commit. The approved cross-candidate Git policy should not implicitly apply to repeat confirmation.

2. **[P1] The P0 physical-chunk fix is correct, but its comparison boundary remains header-blind.**

   `load_cohort()` now correctly requires pins, nonempty unique chunks and sizes no larger than the physical microbatch. However, the CLI still compares only selected per-case outcomes at [worker_eval_probe.py:561](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval_probe.py:561). `compare_records()` ignores cohort SHA, runtime/prompt/template/environment headers and request hashes.

   Reproduced: changing `request_sha256` while leaving the completion and outcome unchanged still returned `[]`, meaning “no differences.”

   Because P0 conditions run in separate invocations, a prompt, model, template or code change between original and reversed runs could therefore be misreported as batching evidence. Add a whole-output P0 comparator that holds the cohort, endpoint, source, generator/schedule, runtime, prompts/templates and environment fixed, and requires matching user/request hashes.

3. **[P1] Candidate identity remains partly label-driven despite the response’s claim.**

   Three concrete bypasses remain around [worker_eval.py:722](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:722) and [worker_eval.py:1407](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:1407):

   - Omitting the optional `frozen_candidate=True` flag lets a hand-built bundle persist `status="FROZEN forged"`; the loader never rechecks the registry.
   - A prompt comparison succeeds when only `system_prompts.revision` changes and the actual prompt text/hashes are identical.
   - A “model” comparison succeeds on a chat-template-only change with no model ID or revision change. It also permits multiple endpoint checkpoints to change simultaneously.

   Make freeze grade intrinsic: any manifest claiming `FROZEN` should be registry-derived and downstream-verifiable. For comparisons, require actual prompt bytes to change for `prompt`, and an actual model ID/revision to change for `model`. If multi-endpoint model contrasts are intended, name them as such; otherwise require the endpoint explicitly.

   The `request_contract` comparison should remain disabled for now: the resolved contract metadata is currently discarded and does not configure `build_worker_call()`. A second metadata entry could therefore create a no-op “request-contract” arm.

### Lower-severity remaining discrepancy

The response says pairwise renderer flips can be derived from `by_renderer` plus aggregate `paired.flipped`, but that is not true. [worker_eval.py:995](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:995) records only whether any of the three renderers differed; it cannot identify which pair disagreed. The raw score rows preserve enough information, so this does not invalidate results, but adding three pairwise numerator/denominator counts would conform to §§4.5/5.5 without introducing floating-point summaries.

### Correctly closed

The following fixes are sound:

- cold real caches are rejected before generation;
- runtime-profile drift is checked at manifest construction and load;
- isolated endpoint/identity relabelling and impossible call states are rejected;
- P1 now checks shape, cross-run request equality, clean shared commit and distinct PIDs;
- P0 reconstructs executable physical chunks;
- full-renderer comparison checks, operator-level strata and best/worst renderer endpoints are present.

The declined runtime immutability, exhaustive conditional-schema and explicit model-EOS proposals are reasonable scope decisions. The differing-clean-commit policy is also documented as approved, although in practice I would use one commit across D16 arms unless a human has verified that the difference is documentation-only.

The dedicated `worker_dev` namespace, exact registered P1 case set and retained P0 cohort hashes remain legitimate Tranche-D blockers rather than merge defects—but the response should not yet describe P1 as checking a “registered” population.

### Verification

- Full suite: `543 passed` with warnings treated as errors.
- Reference/tool agreement: `16,665 / 16,665` over exactly 10,000 latents.
- Diff formatting: clean.
- No legacy executor/cache regression found.

After these targeted corrections, I would perform one focused review of the confirmation, P0 comparison and candidate-identity boundaries, then merge rather than reopen another broad audit.