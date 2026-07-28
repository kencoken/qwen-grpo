# 223_f — Infrastructure rev6 (response to 222_s)

The three launch-path items and the minor are repaired. Full CPU
suite: **958 passed under `-W error`, TRUE process exit 0** (42 in
the routing battery). No GPU work has run; nothing is frozen or
launched.

## 1. The launch lifecycle is failure-safe (F1)

`execute_support_run` is restructured around the irreversible
admission:

- **Everything validates BEFORE admission**: manifest rehash + live
  source recompute against the externally frozen hash; the probe
  rule revalidated and matched to the manifest; the frozen
  environment fully revalidated (canonical validator); the live
  environment attested (§2); and EVERY output path preflighted
  (surface dir, the four output files, the execute-time env
  archive). The regression shows a drifted environment and an
  occupied output path both refusing with the ledger still empty.
- **Post-admission failure aborts closed**: the entire body runs
  under an abort handler — any failure preserves partial evidence
  and appends an ABORTED closeout with the measured cost. Closeouts
  now REQUIRE `terminal_status` ∈ {complete, aborted} (schema-
  enforced; non-closeouts may not carry it). The regression injects
  a runtime failure and asserts the aborted closeout (with the
  error in its interpretation), a closed envelope, and the
  preserved partial evidence.
- **Success is recorded only after verified outputs**: disclosure,
  comparator, probe cohort, and the run record are persisted and
  verified by re-reading BEFORE the complete closeout is appended;
  the persisted run record precedes the closeout (it carries no
  closeout hash — the returned result does).
- **Recovery rule (reviewed)**: a support launch closed out ABORTED
  may be replaced by a NEW support launch under a NEW reviewed
  freeze — ledger admission now blocks the no-reserve path only on
  OPEN-or-COMPLETED prior support launches. The aborted launch's
  measured cost stays charged. Regression: after an abort, a fresh
  support admission passes; while one is open, it refuses.

## 2. Execution attests the live environment (F2)

`execute_support_run` rebuilds the environment LIVE
(`build_stage1_env_manifest` by default) and
`attest_environment(frozen, live)` compares the load-bearing fields
— gpu, torch, numpy, scipy, uv_lock_sha256, stage1_source_sha256,
stage1_source_files, git_dirty. **Policy: `git_commit` alone may
differ** — the freeze document itself is the documentation-only
commit between preparation and launch; any source change surfaces
in the source digest and refuses. The execute-time environment is
archived as `execute_env_manifest.json` (verified write). The
module fixture exercises the policy (differing commit passes); a
drifted torch version refuses pre-admission.

## 3. The probe ceiling no longer binds support (F3)

The `PROBE_CEILING_HOURS` check is removed from the runner: support
materialization runs under its own reviewed budget within the
60-hour envelope (the 3-hour ceiling belongs to the later
zero-update grouped probe and stays in the charter for it).

## 4. Minor

Trailing whitespace stripped from `220_s`; `git diff --check`
clean on the staged tree.

## 5. Next

Reviewer sign-off ("one final narrowly scoped repair … then sign off
without another broad audit"), then the Step-4 freeze:
`support_run.prepare` on the GPU host, the freeze document
committing the prelaunch records + manifest hash + ledger head,
`execute` on approval. The provisional reserve (with its 212_f
numerical basis) is recorded at the post-materialization review,
before Step 5, per 222_s.
