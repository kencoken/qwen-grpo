# 182_f — Unit-D third repair (response to 181_s)

Both archive-boundary P1s and all three small repairs are
implemented; the successor is reissued as **183_f** (rev4 — 180_f
stands at reviewed bytes) with the regenerated source identity. No
formal statistical run started; both amended run roots remain absent.

## 1. Success archival re-verifies the finalized evidence (finding 1)

`verify_finalized_run(bundle, seed_registry)` is the READ-ONLY
finalized-run verifier, extracted from `finalize_amend1_run` (which
now shares `_check_run_root_identity`, `_reconcile_partial_d`, and
`_load_run_evidence` with it — one code path for the gates). It:

- checks both roots' EXACT frozen file sets (aggregate included) and
  complete records;
- fully validates both environment manifests (recomputed hashes,
  bundle binding, provenance cross-check);
- RELOADS A/C/D, the B artifact, replay manifest and raw completions
  through every fail-closed gate;
- reconciles every partial-D record;
- RE-DERIVES the aggregate and requires exact equality with the
  persisted `aggregate.json`;
- requires the run record's `aggregate` stage and a matching
  `aggregate_decision`.

Success archival calls it after the provenance/self-hash/rebuilt-
bundle gates. The reviewer's demonstrated bypass is now the test:
the same foreign `{}` aggregate that previously archived is refused
at the verifier, the success path archives only a run genuinely
produced by `finalize_amend1_run`, and a finalized aggregate with a
flipped decision refuses (all in
`test_archive_evidence_success_mode`, rebuilt on real finalized
evidence over a derive-everything bundle).

## 2. Abort archival is total and never trusts a failed identity (finding 2)

- Decoded bundle and run-record objects are SHAPE-CHECKED: a `[]`
  bundle or `[]` record is recorded (`not a JSON object` /
  status `malformed`) and the bytes are preserved — no
  `AttributeError`, no lost evidence (tested).
- The claimed bundle hash names the destination ONLY when the
  self-hash actually passes (`identity_basis = "bundle_self_hash"`);
  otherwise the raw bundle-file byte hash is used as documented
  (`identity_basis = "bundle_file_bytes"`). The reviewer's
  reproduction — a self-hash-invalid bundle archived under
  `…_ffffffffffff` — is now a refusal test: the destination is named
  by the file-byte hash and the failure is recorded.

## 3. Small repairs

- `persisted_context` rejects subdirectories in its exact
  pre-aggregate check (tested).
- Archiving a replay root that exists WITHOUT its bundle manifest
  records `replay root exists but its bundle manifest is absent`
  (tested).
- 178_s trailing whitespace removed; `git diff --check` clean.

## 4. Changed lines and identity

`stage1_tranche.py`: the finalizer refactor into shared helpers +
`verify_finalized_run` (no behavioral change to
`finalize_amend1_run` itself). `stage1_amend1_run.py`: shape checks,
identity-basis rule, replay-bundle-absent recording, success-mode
verifier call, subdirectory rejection, rev4 prereg path constant.
Tests: success/abort archive tests rebuilt (real finalized evidence;
totality and identity probes), subdirectory probe. No statistic,
grid, seed, schema, threshold, deadline or projection changed; the
registry/support/grid/contract/schema/file-set digests are all
UNCHANGED.

Successor source digest (pinned in 183_f §1):
`d1bb6fc3be720ef0608e9eb55b65a6b7f908d5cfb2e6890bbae7c2d75898e4e5`
Full CPU suite: **902 passed under `-W error`, TRUE process exit 0.**
Ready for the mechanical hashes/tests/diff-check, then lock.
