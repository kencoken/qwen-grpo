## Verdict

Do not freeze `92_s` or begin `worker_dev` yet. The implementation is broadly on track and all 560 CPU tests pass, but several real workflow-integrity gaps could change which candidate is evaluated or selected.

### Blocking findings

1. **Screening accepts incomplete tranches.** Missing P1 triplets become `missing`, yet `screen` still emits a launch manifest; the test explicitly blesses screening with only one of eight arms. Screening must require the exact triggered candidate set. [worker_eval_probe.py:841](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:841) [test_conductor_worker_eval.py:1768](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/test_conductor_worker_eval.py:1768)

2. **Candidate identity can be misattributed.**

   - Candidate-less diagnostic P1 files can pass candidate screening.
   - Reveal trusts the filename/launch ID without checking the loaded manifest against that candidate. A valid generic-model run placed under a Coder filename was selected as the Coder candidate.

   Require embedded candidate equality and rederive the exact profile, prompts, contract, physical layout and request identities at both boundaries. [worker_eval_probe.py:609](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:609) [worker_eval_probe.py:888](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:888)

3. **The launch manifest is not a trusted artifact.** It records no P1 source hashes, and reveal accepts editable JSON without recomputing completeness, admissions, sentinels or launch membership. Use one strict loader that validates/rederives the screening result and a completion index mapping each candidate to its actual fresh run directory and manifest hash. This also resolves the current hard-coded `<cid>-full` restart problem.

4. **The frozen executable commit is not enforced across arms.** P1 checks only within each triplet; screening and reveal permit different clean commits across candidates, while the comparison code explicitly allows Git differences. Full candidate runs also omit `frozen_candidate=True`. This contradicts `92_s`’s no-documentation-exception rule. [worker_eval.py:1445](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval.py:1445)

5. **Tranche B cannot yet follow the preregistered state machine.** Reveal emits neither `viable`, `proven_non_target` nor `unaudited` contract states, and B screening consumes no validated A result. It therefore cannot enforce “no B after an A target” or select the eligible contract subset mechanically.

6. **The pre-run support freeze is incomplete.** The code regenerates plans, but there is no frozen pre-P1 artifact hashing the complete 300- and 900-case identities and rendered request digests. Screening also does not bind those hashes. This should be a compact support-digest registry, not a new elaborate type system.

7. **Model comparison is currently broken.** A real generic-versus-Coder comparison fails because `physical_layout.*` changes are not included in the model-scoped allowed differences. [worker_eval.py:1465](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval.py:1465)

8. **The disclosed §9 work must land before freeze/P1, not merely before reveal.** It is a `92_s §6.10` prerequisite and the experiment requires one executable commit. Reveal presently omits prefix/full paired contrasts, supported interactions, win/loss/tie counts and fallback status.

Physical provenance should also bind quantization and device as specified, and validate per-endpoint telemetry. The NF4 packed-parameter correction in `e50223f` itself looks correct and was sensibly verified on-device.

## `code_local_v1`

Approve after one narrow, hash-changing amendment. The current wording incorrectly implies that any whitelist call can produce `seq` and that every call has two arguments. Replace [prompts.py:328](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/prompts.py:328) with:

> The top-level call must be `count_gt(seq, n)` or `at(seq, n)`, where `seq` is `resource` or a nesting formed only with `stable_unique(seq)` and `rotate_left(seq, n)`, and `n` is a nonnegative integer or `step_k`, written exactly as given. In `count_gt`, `at`, and `rotate_left`, the FIRST argument is the sequence and the SECOND is the number; `stable_unique` takes only the sequence.

This is supported by the frozen grammar and the retained nesting failures; it introduces no answer leakage or model-specific trick.

Also correct `93_f`:

- Rev9 has two Code `Wrong:` contrasts, not three.
- Only the anti-guard exemplar was demonstrated to backfire. Describe positive-only prompting as the hypothesis being tested, not as proof that every negative exemplar is harmful.
- Say the prompt retains rev4’s rules/examples/final-restatement structure, rather than its exact “first sentence” layout.

Everything else in the prompt is supported and model-neutral. The current pre-amendment hash is `7aa430845b7ca12c06128725cfec91652ffed9f2a70a7e1a831111a4a96400a4`.

## Reveal interpretation

I approve procedural hiding; cryptographic hiding is unnecessary. The precise wording should be:

> Semantic material is retained in the run artifacts but is not surfaced or inspected until the reveal command.

“Summaries exist only via reveal” is inaccurate because each full RunWriter directory already contains `summary.json`. Procedural non-inspection is acceptable, but it does not replace the fail-closed launch, candidate-identity and artifact-hash checks above.

The P0 reconstruction looks correct: 90 calls in `[16,16,13,16,16,13]`. Run the four P0 replays and complete the fixes above before freezing. The uncached Coder-3B count may remain a first-use validation only if mismatch is explicitly a hard stop requiring a new preregistration—not an in-place post-freeze registry correction.