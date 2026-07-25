Verdict: Unit C’s statistical core is sound, but I would make one bounded repair before Unit D. The remaining issues are execution-integrity gaps, not a reason to redesign the amendment.

### Blocking findings

1. **[P1] There is no executable amended B replay path.**
   [`run_replay()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_replay.py:584) still uses the legacy run root, environment hash, replay-manifest version and artifact tag, and never validates the common bundle or seed registry. The aggregate tests currently fabricate a legacy-tagged B artifact carrying the bundle hash. Implement a thin amended replay entry point using the amended root/tag, common bundle, finalized registry and authoritative support IDs; legacy artifacts must refuse.

2. **[P1] D is not actually consuming the registry it claims to bind.**
   [`run_d_battery_scenario()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_tranche.py:330) and the deterministic set derive seeds again instead of taking the registered values. Because bundle validation does not independently prove every registry value is canonical, D can execute different seeds from those named by its artifact. Consume the supplied registry directly, or rederive and compare the complete registry before execution. The amended B runner needs the same treatment.

3. **[P1] D branch telemetry is not exact-set validated.**
   [`aggregate_amend1_verdict()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_tranche.py:569) accepts missing D6/D7 rows and arbitrary extra schema-valid rows. Require exactly eight keys: D6/D7 at looks 100/300/500 and D8 at 100/500. The `partial_D_*` records for D6–D8 should also include their branch counts and execution/scenario identity.

4. **[P1] The successful file lifecycle cannot satisfy the frozen contract.**
   The runner writes `run_record_final.json`, which is absent from [`EXPECTED_RUN_FILES`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1.py:423), while never writing required `aggregate.json`. It also does not reload A/C/D after persistence. A small post-B finalizer should load and verify the persisted evidence, compute/persist the aggregate, update the existing `run_record.json`, and check both exact file sets.

5. **[P1] The combined and total deadlines are checked too late.**
   D6–D8’s 30-minute limit is checked only after each complete scenario, and the 12-hour limit only after all D rows. Pass the minimum remaining per-scenario, D6–D8 and total budget into the existing every-50-trial check, using a monotonic clock.

6. **[P1] `C2_preCE1_available` can be true on `scientific_stop`.**
   At [`stage1_tranche.py:628`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_tranche.py:628), availability depends only on B. It should require both-direction B support **and** scientific passage. A B-only diagnostic can be retained under a different name.

A smaller trust-boundary repair is also worthwhile: strengthen the [`C_marginal` identity](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1.py:259) with `denominator_unresolved <= unresolved_count` and `fail_count + denominator_unresolved <= positive_branch`.

### What passed review

- D1–D5 preserve their frozen DGPs and acceptance calculations.
- D2 correctly changes only the fork schedule to `(100, 500)`.
- D6–D8 implement the intended prefix coupling, structural/non-structural distinction, strict undercoverage definition, branch telemetry and Wilson ceiling.
- The B C2/C1 consequence matrix is correct apart from the availability flag above.
- The obsolete 2,000-replicate/agreement path is gone.
- Focused suite: **147 passed**.
- Syntax and changed-line checks are clean.

The full suite reached **883 passed**, but Python then reproducibly segfaulted during teardown in `sentencepiece`, yielding exit 139. That looks separate from the Unit C logic, but Unit D should not describe the suite as clean until it is isolated or resolved.

After this focused repair and a changed-lines regression review, proceeding to Unit D is appropriate.