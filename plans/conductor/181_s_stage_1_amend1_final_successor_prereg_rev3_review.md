Not ready to lock yet. The production launch and CPU-first bundle flow are fixed, but the archive boundary still has two defects.

1. **[P1] Success archival accepts invalid finalized evidence.**
   [archive_evidence()](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/tasks/conductor/stage1_amend1_run.py:297) checks provenance, statuses, and filenames, but never reloads the artifacts or re-derives the verdict. The new test explicitly writes `aggregate.json` as `{}`—alongside foreign environment/artifact fixtures—and successfully archives it at [test_conductor_stage1_tranche.py:1176](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage1/test_conductor_stage1_tranche.py:1176).

   Extract a read-only finalized-run verifier from `finalize_amend1_run` and call it before success archival. It should:

   - validate both environment manifests;
   - reload A/C/D/B and raw B evidence;
   - reconcile partial-D records;
   - re-derive the aggregate;
   - require exact equality with `aggregate.json`;
   - require the run-record `aggregate` stage and matching `aggregate_decision`.

2. **[P1] Abort archival is not yet total and can trust an invalid identity.**

   - A bundle containing valid JSON of the wrong shape, such as `[]`, raises `AttributeError` instead of preserving the aborted evidence.
   - A self-hash-invalid bundle with a 64-hex claimed hash is still archived under that claim and labelled `identity_basis="bundle_self_hash"`. I reproduced it being placed under `..._ffffffffffff` despite recording a self-hash failure.

   Shape-check decoded bundle/run-record objects. Only use the claimed bundle identity when the self-hash actually passes; otherwise use the raw bundle-file hash as documented.

Small repairs to include in the same patch:

- Reject subdirectories in `persisted_context`’s “exact” pre-aggregate check.
- Record a missing replay bundle when an already-created replay root is archived as aborted.
- Remove three trailing-whitespace findings in `178_s`; `git diff --check` currently fails.

Everything else is clean:

- Production support is now exactly 18 unique observations.
- Registry remains 49,342 entries with unchanged pinned digests.
- Replay/finalize consume the persisted CPU bundle and enforce CPU-first ordering.
- Source and dependency hashes match `180_f`.
- Focused changed-lines suite passed 42/42 under warnings-as-errors.
- No estimand, threshold, seed, DGP, deadline, or projection changed.

After this single archive-focused repair, regenerate the source digest in `180_f`, run mechanical hashes/tests/diff-check, and lock. No broader review round should be necessary.