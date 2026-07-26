Not ready to lock yet. The core repair is correct, but four launch-relevant gaps remain:

1. **The diagnostic does not enforce the smoke/launch lock.** `run` can currently sample retained support immediately. Add one simple launch-lock JSON checked at the consuming boundary, binding the persisted smoke record, registry, and current executable/configuration identities.

2. **Three provenance claims are not independently verified.** I changed `stage1_source_sha256`, `chat_template_sha256`, and `generation_config_sha256`, recomputed the hashes, and the verifier still accepted all results.

3. **The report omits signed outputs.** It needs all-18 reward frequencies and action distributions, plus explicit population denominators/support composition and the promised renderer→latent→cell summaries.

4. **Mid-block aborts lose completions.** Only completed 256-draw blocks are flushed. The exception path should atomically persist the current in-memory raw map.

Also fix in the same pass:

- Treat non-UTF-8 text as non-parseable/reward-zero rather than aborting.
- Validate terminal status and present files in abort archives.
- Record tokenizer revision and tensor shapes explicitly in the smoke.
- Load only the tokenizer for the synthetic smoke; the current smoke unnecessarily requires the retained-support surface, which is presently absent in the picome checkout.

Mechanically, the implementation is otherwise healthy: **913 tests passed under warnings-as-errors**, `git diff --check` is clean, and the recorded source digest matches. The BatchEncoding repair, seed universe, scoring identities, formulas, raw recount, and success archive are correct.

After these focused repairs and regressions, run one narrow changed-lines review before freezing the candidate. Do not smoke or lock the current commit.