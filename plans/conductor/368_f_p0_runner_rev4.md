# 368_f — P0 runner REV4 (response to 367_s): integration-path repairs

All four blocking findings and all four additional repairs, with
the reviewer's reproductions as regressions
(`test_p0_runner_rev4_regressions`). Full suite: **1040 passed
under `-W error`, TRUE exit 0** (1039 + the new regression). As
367_s confirms, **no pins change** — freeze `88c6635a…`,
identity `b5749eca…`, realization `a8e9cf73…` all stand;
evaluation semantics are untouched.

## 1. F1 — writer and verifier can no longer disagree

`_bundle_inventory()` DERIVES the expected file set from the
authoritative `CHECKPOINT_BUNDLE_FILENAMES`
(`adapter.safetensors`, `optimizer.pt`, `scheduler.pt`,
`rng_state.json`) plus `checkpoint_record.json` — the rev3
literal set with invented `*_state.*` names is gone. Regression:
the derived inventory equals the contract names and NOT the
rev3 spellings.

## 2. F2 — finalize sessions no longer poison the merge

Trajectory merge boundaries come from TRAINING sessions
(`fresh`/`resume`) ONLY; a `finalize` session is validated
separately — it must carry `start_group_index == -1` and NO
trace segment, and it never truncates the preceding segment's
authorized prefix. The sealed-inventory expectation likewise
counts only training-session segments.

## 3. F3 — SIGKILL recovery recovers the evidence

`_sanitize_after_crash` (IDEMPOTENT — already-sealed files
untouched) seals every raw file under `sealed/`, and
`_close_killed_session` invokes it before recording the inferred
end. The killed session's checkpoint-authorized training prefix
therefore enters the merge, the sealed inventory holds, and no
raw partial evaluation can be silently overwritten. Regression:
a killed session with raw training and evaluation files is
closed with both sealed; a second sanitation call is a no-op.

## 4. F4 — the WHOLE uncommitted attempt is excluded

`_exclude_uncommitted_attempt` moves the bundle directory, the
`checkpoint-<i>` HF checkpoint, and the raw/sealed evaluation
for every cadence index WITHOUT an atomic completion record into
session-scoped `excluded/` before the rerun — nothing at a fixed
path can be overwritten, and a second exclusion into the same
session scope refuses. Resume uses this for every pending index.

## 5. The additional repairs

- **The session loader IS the state machine**: contiguous start
  indices, closed per-kind schemas, exactly one start and at
  most one end per session — the reviewer's
  `start(1), end(1,100), end(1,0)` chain now REFUSES at load
  (regression), as do an end-without-start and a non-contiguous
  start.
- **Separate unwrapping**: `_unwrap_scheduler` follows ONLY
  `.scheduler` — a raw torch scheduler holds `.optimizer`, so
  the old shared unwrapper could land two DIFFERENT schedulers
  on the same optimizer and pass; the regression shows exactly
  that shape now distinguishing them. The GPU probe checks the
  real scheduler identity.
- **Elapsed covers terminal hashing**: the expensive
  `_hash_directory` over the full run root (including the ~GBs
  of HF checkpoints) happens INSIDE the measured window; after
  the session-end entry, only `sessions.jsonl` itself is
  re-hashed into the bound map (the closeout must bind the log
  including its end entry). The residual ledger append + final
  re-verification are structurally outside the recorded figure —
  a closeout cannot contain its own future — and are disclosed
  as such.
- **Genuinely historical verification**: `verify_p0_run` now
  enforces the manifest-bound execution root and verifies the
  ARCHIVED prelaunch freeze copy under the MANIFEST pin
  (`load_p0_launch_freeze` on the archived bytes) — the
  current-committed-copy byte comparison is gone, so evidence
  stays verifiable after the sentinel-assembler source commit.

## 6. Identities and next

No pin changes. Next, per 367_s: the **reward-blind GPU probe**
(trainer construction → the scheduler lifecycle → checkpoint-zero
save/restore → one training update → a forced HF cadence save
with bundle verification → an interruption → a one-step resume)
as a disclosed bounded probe, then the narrow prelaunch review of
the real manifest, then P0 on head `df4bf7ad…`.
