## Review verdict

Changes requested before Unit 1 sign-off. The implemented numerical choices are consistent with `132_s`, but three gaps should be closed.

### Blocking findings

1. **[P1] Fork intervention gates are not scoped to both edges.**

   [stage1.py:98](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/stage1.py:98) names corruption separately for `n1→n3` and `n2→n3`, but consistency and persistence appear only once. A consumer could therefore pool them or test one edge, whereas `132_s` requires all three diagnostics to pass independently on both edges.

   Encode the cross-product of:

   ```text
   {n1→n3, n2→n3}
   ×
   {corruption, counterfactual consistency, old-answer persistence}
   ```

   and test its cardinality against `CELL_INTERVENTION_EDGES`.

2. **[P1] The claimed protocol-denominator contract is not implemented.**

   [stage1.py:65](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/stage1.py:65) records gate names and C1/C2 positions, but not the §7.1 denominator that [133_f:36](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/plans/conductor/133_f_stage_1_unit_1_plan_freeze.md:36) says Unit 1 delivered:

   - on-contract `(cell, node, logical worker)` strata;
   - `3 × on-contract nodes` truncation rows per worker and latent;
   - `3 × S` selected-route rows per cell and latent;
   - `3 × selected nodes` rows per selected worker and latent.

   Unit 2 needs this mechanically to derive expected manifest counts. Add a small machine-readable strata/count contract and tests across all six cells and four workers.

3. **[P1] `133_f` relies on a format repair that does not exist, while Unit 3 lacks its two frozen prompts.**

   [133_f:16](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/plans/conductor/133_f_stage_1_unit_1_plan_freeze.md:16) says `FORMAT_REPAIR_V1` exists. Repository-wide search finds only comments; there is no implementation or frozen transformation. [policy.py:189](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/policy.py:189) also exposes only the few-shot prompt, not the schema-only candidate required by the §8.4B replay.

   Before Unit 3:

   - preserve and pin the existing few-shot bytes;
   - define and pin the exact schema-only bytes;
   - either implement and freeze `FORMAT_REPAIR_V1`, or correct `133_f` and explicitly freeze “no repair.”

   I recommend the simpler no-repair choice given the existing 144/144 format result.

### Lower-severity items

- [policy_dev_cohort()](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/program.py:140) accepts `True` and `1.0` as `format_a`. Add the same plain-integer guard used by `generate_latent`.
- [bootstrap_seed()](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/stage1.py:153) trusts callers to construct a canonical cell/look string. Provide a canonical builder or validate sorting, cells, looks, and the 64-character hexadecimal manifest digest.
- The shallow model router freezes feature groups but not categorical levels, one-hot order, or encoder configuration. Freeze those before construction reveal.
- The successor Unit 2 source digest must include [contract.py:94](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/contract.py:94); the historical Stage-0 digest does not bind the direct-answer parser used by B1/B3/B4.
- Pin the exact retry dictionary and complete gate-threshold mapping in tests, rather than only their shape.
- `133_f` calls `policy_dev` the “ninth namespace”; it is currently the seventh.

### Verification

- Plan commit and SHA-256 binding: correct.
- Stage-0 executable digest remains `688f7e06…cee8`.
- Focused Unit 1/program tests: 106 passed.
- CPU-compatible regression suite: 608 passed with warnings as errors.
- Previously excluded worker-evaluation tests: 79 passed separately in CPU-only mode.
- `git diff --check`: clean.

The D4 cohort, balance checks, profile selection, namespace isolation, visible slice, alpha constants, and Stage-2 population arithmetic all look correct. After the three blocking items are patched, Unit 1 should be ready to close and Unit 2 can begin.