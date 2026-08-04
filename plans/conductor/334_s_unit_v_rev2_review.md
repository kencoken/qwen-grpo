## Verdict

Rev2 is substantially improved, but I would **not sign off or prepare the GPU launch yet**. The original execution blockers are closed, but four material issues remain.

### Findings

1. **[P1] The prompt-overlap gate is still not substantively normalized.**

   `semantic_overlap_report()` compares raw prompts. Opaque resource handles such as `R-8V9` are identity-only aliases, but are not canonicalized.

   Replacing each observation’s handles consistently with `R0`, `R1`, etc. produces:

   - Validation ↔ training: **21 unique prompt collisions**, affecting 39/90 validation observations.
   - Validation ↔ cycle: **15 collisions**, affecting 30/90 observations.
   - Cycle ↔ training: **30 collisions**.
   - Alpha-normalized latent-semantic overlap remains zero throughout.

   Thus the current reported zero is largely due to random handle names and does not satisfy the substantive-normalization requirement in `330_f`.

   My preferred disposition is not to select a special collision-free cohort, because that would compromise the natural-mixture design. Instead, amend the framing before materialization:

   - hard requirement: alpha-normalized latent/resource semantics are disjoint;
   - disclose alpha-normalized prompt overlap;
   - describe validation as testing held-out latent/resource instances, not template-disjoint prompts;
   - optionally report repeated-prompt versus novel-prompt results descriptively.

2. **[P1] Manifest validation does not independently enforce the frozen launch.**

   I reproduced `validate_val_launch_manifest()` accepting correctly re-signed changes to:

   - `budget_gpu_hours`;
   - `search_cap`;
   - `support`;
   - `driver`;
   - the declaration/cohort.

   The source check recomputes using constant `DRIVER` without requiring `manifest["driver"] == DRIVER`.

   Extract the builder’s cohort checks into a shared validator, rederive every configuration-owned field, bind/enforce `run_root`, and add parameterized re-signing tests.

3. **[P1] Frozen lineage and registered retry semantics are not implemented correctly.**

   The first-attempt check can be bypassed with `lineage_parent_sha256=None`; the end-to-end test uses that bypass. Conversely, after an actual abort, the ledger head is no longer the original C2 head, so the default path cannot perform the signed identical-design retry.

   The ledger also permits a changed-design retry or another launch following completion. The launch entry still records `"parent": None`.

   The boundary should enforce:

   - first launch only from the frozen C2 head;
   - retry only after an aborted-closed validation attempt;
   - identical `scientific_design_sha256`;
   - no retry after an open or completed attempt;
   - cumulative envelope accounting;
   - actual lineage parent persisted in the entry.

4. **[P1] The terminal verifier does not yet authenticate the terminal archive.**

   `verify_val_run()` still returns `PASS` after deleting `execute_env_manifest.json` or adding an unbound file. It ignores several run-record identities and compares the persisted overlap report back to the same claim rather than recomputing it. `load_val_lock()` also permits callers to omit the surface entirely.

   Mirror the established terminal-verifier pattern:

   - exact complete/aborted inventory;
   - execution-environment validation;
   - reviewed launch-manifest and admission cross-bindings;
   - mandatory authenticated surface at the scientific consuming boundary;
   - exact run-record and overlap schemas;
   - fresh three-way overlap recomputation;
   - aborted-run/no-lock verification.

### Smaller correction

The deadline is now passed into materialization, closing the original defect. Add a post-materialization deadline check and an abort regression test, because the final observation can currently finish after the ceiling and still close successfully.

### Confirmed closed

- Dedicated validation admission works.
- Val manifests now pass through surface locking/loading.
- The full-digest CRN formula, known vector and 720-seed pin are correct.
- Canonical natural-mixture weights are persisted and rederived.
- The genuine CPU-fake success lifecycle runs end to end.
- All namespace identities are checked.
- Hashes reproduce and the worktree is clean.
- **1,028 tests pass under warnings-as-errors; 5 focused Unit V tests pass.**

These are localized repairs. After one consolidated Rev3, a narrow changed-lines review should be sufficient before preparing the real prelaunch manifest.