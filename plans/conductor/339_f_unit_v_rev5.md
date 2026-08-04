# 339_f — Unit V REV5 (response to 338_s)

Both terminal-boundary P1s repaired plus the nonblocking
cleanups. Full suite: **1030 passed under `-W error`, TRUE exit
0** (1029 + the late-abort/full-retry lifecycle test). The frozen
identities are UNCHANGED (config `73376e07…`, seed schedule
`7f5f6518…`, freeze `8ba9677f…`) — code-boundary changes only.

## 1. P1 — a genuine late abort is verifiable

The aborted branch of `verify_val_run` now permits
`val_lock.json` as HASHED PARTIAL EVIDENCE exactly under the
review's three conditions: `expected_val_lock_sha256 is None`;
the authenticated aborted closeout carries NO `val_lock_sha256`
(a closeout that authorizes one refuses); and the file is
reported as `unadmitted_val_lock_candidate` — never loaded, never
a consumable V3 lock (verifying the same archive UNDER the
candidate's own hash refuses, asserted in test).

The regression the review requested is committed and goes
further: the in-run verifier is forced to fail AFTER lock
creation → the run closes out aborted with the lock in the
partial hashes → the aborted archive VERIFIES (candidate flagged)
→ and then the **full CPU-fake identical-design attempt 2 runs
the complete lifecycle under the registered `…-r2` root** and
verifies complete — the abort→`-r2` filesystem retry is now a
committed regression (the 338_s nonblocking preference), with the
design hash asserted equal and the manifest hash asserted
distinct across attempts.

## 2. P1 — the three semantic fields are checked

- `run_record["surface_dir"]` now stores the ORIGINAL bound
  absolute surface path (resolved at execution), and the verifier
  requires it to equal `manifest["execution_root"]/surface` —
  archived copies stay portable (the binding is to the original
  root, not the copy's location). The forged-`surface_dir`
  reproduction refuses at the semantic record binding (regression
  asserts the message, not merely a byte mismatch).
- An aborted closeout must name THIS launch manifest
  (`freeze["val_launch_sha256"]`) — the reviewer's rehashed-chain
  reproduction is a regression built on a synthetic valid chain.
- Every closeout's semantic `parent` must equal the launch it
  closes (checked for aborted AND complete closeouts) — likewise
  regression-tested on a synthetic valid chain with a forged
  parent.

## 3. Nonblocking cleanups

- The `three_way_overlap_reports` docstring now states the
  actual contract (semantic intersections gated; prompt overlap
  disclosed).
- The full abort→`-r2` retry regression is committed (§1).

## 4. Next

Narrow changed-lines and mechanical review (per 338_s — no
further broad Unit V review) → the real prelaunch manifest on the
frozen C2 head under the registered root → the narrow launch
sign-off → the V2 GPU launch → V3 lock → Unit Y.
