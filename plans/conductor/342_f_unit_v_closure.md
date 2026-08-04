# 342_f — Unit V CLOSED: the mechanical preservation commit (341_f sign-off conditions)

The 341_f execution sign-off approved the science and the
val-lock pin; this commit performs the required repository
closure. Full suite: **1031 passed under `-W error`, TRUE exit
0** (1030 + the clean-clone restoration gate). Worktree clean at
commit.

## 1. The five sign-off conditions, closed

1. **Ledger entries 18–19 committed unchanged** — the
   `val_materialization` launch (`5ef73f79…`) and its complete
   closeout (`929e1724…`, the head) enter the committed ledger in
   this commit, byte-identical to the working-tree entries the
   run produced (the chain verifies at the committed head).
2. **Evidence archived** under
   `plans/conductor/evidence/val_surface_v1/` (788 KB): the exact
   16-file terminal root, with `steps.jsonl` as a DETERMINISTIC
   gzip (`gzip -n -9` convention — mtime 0, no name, level 9 —
   matching the 233_f extension convention); every other file
   byte-identical.
3. **Clean-clone restoration proven**: `restore_val_evidence`
   reconstructs the 16-file root (deterministic gunzip) and the
   restored root passes `verify_val_run` — chain-authenticated,
   fresh overlap recomputation — under the COMMITTED ledger head
   `929e1724…` and the reviewed lock `2aecdf28…`. This is now a
   PERMANENT suite gate
   (`test_p0_val_evidence_restores_clean_clone`, pinning the
   pristine config against the test-fixture lineage patch).
4. **Consistent overlap reporting**: cycle↔training is
   **30 unique template collisions / 45 affected cycle
   observations** (the 341_f table showed only the unique count;
   the affected-side denominator is the 90-observation cycle
   cohort). Unchanged: val↔training 21/39; val↔cycle 15/30 —
   all against 90-observation candidate populations, semantic
   intersections 0 throughout.
5. **Clean worktree** at commit (verified before push).

## 2. The recorded external pin

`VAL_LOCK_SHA256 =
2aecdf28ad25cae10e494aa9fc1a95138a9feb5a29ab0636314b847987caf19d`
is now a CODE CONSTANT in `p0_val.py` (the approved
`routing_dev_val_lock_sha256` of the frozen `PrecursorOutputs`),
asserted by the clean-clone gate.

## 3. Standing obligation restated

The validation evidence remains DEVELOPMENT-ONLY and absent from
every training schedule; it must not be used to retune the P0
mixture, prompts, or workers (341_s sign-off note — binding).

## 4. Next

Unit Y rev1 (the cycle cohort record + the final `R_cycle`
reserve, replacing the provisional 5.0) — the staged draft gains
this unit's hashes (`2aecdf28…`, `929e1724…`, the measured
0.0637 GPU-h / 90-observation calibration) and enters review.
Then Unit T rev1 (the beta smoke) → Unit L → checkpoint-zero
eval → P0.
