## Review verdict

Request one final narrow patch before merging `9f751bd`. The author has correctly closed most findings, but two supported API paths still permit scientifically misleading comparisons.

### Blocking findings

1. **[P1] A one-endpoint model comparison can still include unrelated endpoint drift.**

   [worker_eval.py:1381](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:1381) allows the complete `chat_template_sha256`, `tokenizer_facts` and `endpoint_fingerprints` mappings to differ. The one-endpoint check at [worker_eval.py:1472](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:1472) examines only model ID/revision fields.

   Reproduced: a Code model-ID change accompanied by unrelated Math chat-template drift was accepted:

   ```text
   ['chat_template_sha256.math',
    'runtime_profile.workers.code.model_id']
   ```

   The caller also never identifies the intended endpoint, so an intended Code comparison accidentally configured as a Math-only swap passes.

   Require an explicit endpoint—such as a `model_endpoint="code"` argument—and permit checkpoint, template, tokenizer and endpoint-fingerprint differences only for that endpoint. The global runtime/worker-visible fingerprints may still differ as consequences.

2. **[P1] The public §7.4 authority retains a test-only population override.**

   [worker_eval.py:1504](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/tasks/conductor/worker_eval.py:1504) accepts `per_cell`, and the test at [test_conductor_worker_eval.py:1212](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-worker-eval/test_conductor_worker_eval.py:1212) intentionally confirms two 30-call runs with `per_cell=1`.

   The CLI correctly provides no override, but this function is itself documented as the §7.4 confirmation authority and may be called directly by D16 integration code. Remove `per_cell` from the public function and fix it at 30. Tests can use the full fake-pool population or a clearly private helper.

   This does not require another proof-marker abstraction—just keep the scientific entry point fixed.

### Lower-severity recommendation

`compare_probe_outputs()` still accepts one P0 artifact compared with itself and reports zero differences. P0 is diagnostic rather than an admission gate, but §7.2 calls for two executions of the original grouping. Since process identity is already recorded, rejecting identical run/process identities would prevent an easy operator slip.

### Deferred gates

The response now accurately calls the population “declared,” not “registered.” The D1 `worker_dev` registration and exact retained P0 cohort hashes remain legitimate Tranche-D blockers, not merge defects.

However, the current commands can produce green output when passed `construction` as the declared namespace. Therefore, a successful command must not be interpreted as Gate-D completion until D1 and the retained cohort artifacts are frozen. Ideally, the later D1 integration should bind these commands to the authoritative namespace rather than leaving it as a post-hoc operator assertion.

### Correctly closed

The following fixes are sound:

- self-confirmation, wrong-size defaults, wrong namespace, split commits and noncanonical ordinals now fail on the CLI path;
- P0 refuses header, request-byte and commit drift with a distinct `NOT COMPARABLE` outcome;
- forged FROZEN claims are checked at construction and loading;
- revision-only prompt and template-only model comparisons fail;
- multi-endpoint checkpoint changes fail;
- request-contract comparison is disabled until it becomes executable;
- all three pairwise renderer flip counts are now recorded correctly.

### Verification

- Full suite: `547 passed` with warnings treated as errors.
- Reference/tool agreement: `16,665 / 16,665` over 10,000 latents.
- Diff formatting and worktree: clean.

After the two narrow corrections above, I would perform only a focused confirmation/comparator check and then merge. Another broad audit is not warranted.