Not quite ready for Unit B. Most repairs are correct, and 117 affected tests pass under warnings-as-errors, but one substantive blocker remains.

- **Execution-bundle provenance is still caller-asserted.** [`_check_bundle_semantics()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1.py:437) accepts arbitrary valid-looking provenance hashes. I confirmed it accepts both a fabricated evidence-manifest hash and the partial 40,126-entry seed-registry digest paired with a claimed count of 49,342. It also still lacks the preregistered request-contract, artifact-schema, and expected-file-set digests. The bundle boundary should derive or compare these against authoritative inputs, rather than checking format/count alone.

Two small fixes should accompany that:

- [`validate_env_manifest()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_manifest.py:171) must require the newly recorded NumPy and SciPy fields. Removing both and rehashing currently passes.
- The revised [diagnostic command](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/plans/conductor/evidence/stage1_pre_ce1_v1_ae26ba5d/agreement_diagnostic_script.py:16) still fails with `ModuleNotFoundError`; adding `PYTHONPATH=/tmp/v1-checkout` fixes it.

The archive authentication, finalized registry construction, real B seed material, branch schemas, and numerical constants are otherwise correctly repaired.

Recommendation: one final narrow repair commit, then proceed directly to Unit B. Unit B should enforce the exact 48/120 C key sets when its loaders land.