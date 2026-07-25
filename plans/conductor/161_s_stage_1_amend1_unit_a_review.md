Not quite ready for Unit B. The amended schedules, path counts, alpha allocations, archived v1 payloads, and atomic run-root handling all check out; the focused suite passed 185 tests under warnings-as-errors. However, four Unit A contract gaps remain.

### Blocking Unit A sign-off

1. **Execution bundles can be altered and self-rehashed.**  
   [`validate_execution_bundle()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1.py:308) checks the self-hash, manifest name, and attempt ID, but does not reapply the semantic checks used by the builder. I changed the frozen artifact tags, recomputed the hash, and validation accepted it. Loading must enforce the exact field set, frozen roots/tags, and authoritative contract/schema/file-set digests—not trust a self-consistent bundle.

2. **The v1 archive verifier does not authenticate the complete archive.**  
   [`verify_v1_evidence_archive()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1.py:211) accepts a modified `lock_commit` in the manifest and ignores a modified diagnostic script. Pin the known manifest hash or validate its complete identity and exact file set, and add the diagnostic script to the frozen hash table.

3. **The “canonical” seed registry is incomplete.**  
   [`build_seed_registry()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1.py:120) omits the 9,216 concrete B completion seeds and the formal deterministic D seeds, while its digest can already be placed into an execution bundle. The B seed test also checks a padded `|000` key rather than the real `|0` material. Provide an authoritative full-registry finalizer and refuse bundle construction from a partial registry.

4. **The advertised exact persistence/artifact schemas are not yet exact.**  
   [`PERSISTENCE_LOOK_FIELDS`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1.py:175) leaves the branch-specific bounds only in comments. Meanwhile, amended artifacts still use the v1 schemas in [`stage1_tranche.py`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_tranche.py:390). Freeze explicit zero/positive-branch schemas and the amended C/D sufficient-statistic schemas before Unit B starts producing them.

Before Unit B’s numerical probes, I would also add NumPy/SciPy versions to the environment manifest, promote the remaining numerical conventions to tested constants, and correct the archived diagnostic’s regeneration instructions—the script did not exist at the historical checkout named in its header.

Recommendation: make one narrow Unit A repair commit covering these items, briefly recheck it, then proceed to Unit B. No redesign of the amendment is needed.