# 184_f — Amended-tranche LOCK record

The separate lock record required by 158_s §10 Unit D, issued under
the non-circular sequence of 183_f §10: this record pins the
reviewed preregistration and executable state and is committed
FIRST; at run time `build_lock_bundle` derives THIS file's byte hash
and the clean HEAD (the commit containing this record) into the
execution bundle, which exists only in the run roots. Nothing is
ever written back into this record.

## Approvals

- Reviewer: 181_s repairs verified; mechanical lock gate passed in
  full (166 focused + 902 full-suite tests under `-W error`, clean
  worktree, source digest match, all frozen hashes match, both run
  roots absent, `git diff --check` clean after the final 181_s
  whitespace fix @2335872) — "you can lock without another review
  round."
- Ken approved the lock, 2026-07-25.

## Pinned preregistration (`amendment_prereg_sha256` source)

- Document of record:
  `plans/conductor/183_f_stage_1_amend1_final_successor_prereg_rev4.md`
  (rev4; supersedes 180_f → 177_f → 174_f, all preserved at
  reviewed bytes)
- SHA-256 of its committed bytes:
  `f1a3d19c6351c2aaad34bbd1437bd976b7e6fb80f27e0284499cea72ac2777c4`
- Introduced at commit `b492573`; final pre-lock tree state at
  `2335872` (documentation-only whitespace fix; source digest
  unaffected).

## Pinned executable state

- Successor source digest (`stage1_source_digest()`):
  `d1bb6fc3be720ef0608e9eb55b65a6b7f908d5cfb2e6890bbae7c2d75898e4e5`
- `uv.lock` SHA-256:
  `f5486ec478b080aa79c6d0444478b019d2ce6262173a643fd1d6aa8f779e48c9`
- Numerical stack: Python 3.12.3, NumPy 2.3.5, SciPy 1.18.0,
  torch 2.11.0+cu130.
- Full CPU suite at this state: 902 passed under `-W error`, TRUE
  process exit 0.
- Expected registry identity (re-derived, not trusted):
  `seed_registry_sha256 = dbd8a12f3269694c37f0083ca0793de531df42c775ca698848801240576a5eda`
  (49,342 entries), `b_support_sha256 =
  5eb2ec57db8ed7ea94fed1125e10e3a8baf8e9f07aafc10bc608cefb4ff4a439`.

## Frozen execution sequence (183_f §7 — verbatim)

From the commit containing this record, with a clean tree, on the
execution box (ollama VRAM checked before the GPU step):

1. `uv run python -m tasks.conductor.stage1_amend1_run tranche`
2. `uv run python -m tasks.conductor.stage1_amend1_run replay`
3. `uv run python -m tasks.conductor.stage1_amend1_run finalize`
4. `uv run python -m tasks.conductor.stage1_amend1_run archive --mode success`
   (an infrastructure abort instead archives with `--mode abort`
   before any recovery decision)
5. The reviewed §12 terminal decision, citing the archive manifest
   hash.

Thresholds, grids, seeds, budgets and the decision table of 183_f
never move after this lock. The single amend-once allowance (132_s
§8.4) is consumed; a scientific failure of this tranche is terminal
for unit 3.
