Unit D is close, but I do **not** recommend locking yet. Three narrow lock-readiness blockers remain.

### Blocking findings

1. **[P1] The frozen D deadline literal does not control execution.**

   The successor freezes `951551 µs` and the resulting `19,031 s` deadline, but [`run_amend1_tranche()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_tranche.py:782) instead derives the deadline from whatever the live benchmark returns. The documented `[¼×, 4×]` sanity abort is also not implemented.

   Add the frozen literal to source, use it for the formal deadline, and treat the live benchmark only as a persisted sanity check with tested inclusive boundaries.

2. **[P1] Lock/bundle provenance remains caller-supplied.**

   [`build_execution_bundle()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1.py:633) accepts arbitrary correctly shaped preregistration hash, lock-record hash, source digest and Git commit. [`_check_bundle_semantics()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1.py:593) largely format-checks them; fabricated values can therefore pass.

   Add one formal lock-time constructor that derives:

   - the successor-preregistration hash from the reviewed file;
   - the lock-record hash from its actual bytes;
   - the current clean commit;
   - `stage1_source_digest()`;
   - the validated environment manifest;
   - the canonical registry and remaining derived fields.

   Consumers should cross-check Git/source provenance against the validated environment as well.

   Also correct the circular wording in [`174_f §10`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/plans/conductor/174_f_stage_1_amend1_final_successor_prereg.md:282): a lock record cannot contain its own full-file hash or the hash of the commit containing it. The correct sequence is:

   1. Lock record pins the reviewed preregistration/executable state.
   2. Commit the lock record.
   3. The formal constructor derives the lock-record byte hash and current clean HEAD into the bundle.
   4. Nothing is written back into the lock record.

3. **[P1] The formal execution and evidence path is not yet reproducible from the commit.**

   [`174_f §7`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/plans/conductor/174_f_stage_1_amend1_final_successor_prereg.md:210) calls undefined `bundle` and `seed_registry` objects “verbatim commands.” There is also no concrete success/abort archive command that copies both roots, creates the byte/length/SHA manifest, and verifies it.

   Likewise, [`173_f §3`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/plans/conductor/173_f_stage_1_amend1_unit_d_review_and_probes.md:99) reports 120 fixed probe cases but commits neither their construction recipe nor an executable probe/output record.

   A small didactic launch/archive helper and reproducible pre-lock probe script are sufficient; no framework is needed.

### Required documentation corrections

- There are **8**, not 12, gated A-position cells: 4 scenarios × one gated delta × two gated sigmas.
- The predicted C power near 0.95 came from an approximate amended-score calculation in `159_f`, not the old v1 artifact. The old row-dispersed v1 result was 0/10,000.
- Soften “D is conservative by construction”; not every t/Fieller/bootstrap component has a finite-sample conservatism guarantee.
- Qualification records carry renderer-level J/K; D6–D8 artifacts persist scenario counts and eight branch-telemetry rows, not full renderer records.
- “v1-measured relative scenario weights” is unsupported because v1 stopped before D. Either commit the throwaway per-scenario timing probe or use the auditable worst-case projection: five times the measured worst path is about 6.61 hours; adding the component budgets remains comfortably below 12 hours.

### Mechanical verification

Everything else checks out:

- **894 tests passed**, true exit 0.
- All stated source, lockfile, registry, support, scenario, request, schema and file-set hashes independently match.
- Numerical versions match.
- Worktree is clean.
- Both amended run roots remain absent.
- No formal statistical run has started.

After these focused corrections, regenerate the affected source/hash literals, perform one changed-lines review, and then lock.