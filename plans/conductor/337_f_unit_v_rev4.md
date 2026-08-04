# 337_f — Unit V REV4 (response to 336_s)

All four P1 boundaries repaired plus the smaller corrections.
Full suite: **1029 passed under `-W error`, TRUE exit 0**. The
frozen identities are UNCHANGED (`VAL_CONFIG` was not touched
this round: config `73376e07…`, seed schedule `7f5f6518…`, freeze
`8ba9677f…`); the changes are code boundaries and the manifest
contract (two new fields).

## 1. P1 — handle-INVARIANT latent normalization

The alpha mapping now derives from the **`public_manifest`
ORDER** (the semantic presentation order), and known handles are
replaced RECURSIVELY in keys and values **before** canonical
serialization — serialization order can no longer leak the
original spelling through sorted dict keys. An undeclared handle
in the semantic body refuses (the mapping would be unstable).

The reviewer's requested regression is in place: for EVERY frozen
multi-handle latent across the val AND cycle cohorts — including
the concrete `fork_join:…:00001:beaa828e:resource_first:private`
example — every handle is consistently renamed so the lexical
order REVERSES, and the semantic hash is asserted UNCHANGED. The
three-way semantic intersections remain 0 under the invariant
implementation (as the reviewer verified), and the disclosed
prompt-collision numbers are unaffected.

## 2. P1 — the ledger enforces the frozen initial parent

The manifest gains **`lineage_parent_sha256`** (rederived from
the frozen config by the validator; part of the closed schema; a
re-signed foreign value refuses in the parameterized set). The
ledger's `val_materialization` admission block now enforces: for
a FIRST launch, `entry["parent"]` must equal the manifest's
frozen initial parent (and, as before, the verified head) — the
reviewer's bypass reproduction is a regression: direct admission
of a val launch on a foreign head REFUSES; a manifest built for
the correct parent ADMITS; an identical-design retry ADMITS only
after an aborted closeout (positive regression added); a
changed-design retry refuses. `validate_entry` now also requires
`val_materialization` to declare `outcome_blind`.

## 3. P1 — `run_root` binds the executed directory

The manifest gains **`execution_root`** — the ACTUAL resolved
root, bound at preparation, OUTSIDE the scientific-design hash
(attempt identity; an aborted retry preserves the design).
`execute_val_run` compares the resolved directory to the bound
root, and enforces the registered ATTEMPT-ROOT rule: attempt 1
executes under the frozen `runs/routing-dev/val-surface-v1`;
attempt N under `…-rN`. The end-to-end fixture now runs under the
registered root name; a prepared launch under a non-registered
root refuses (regression). The in-run verifier enforces the root
binding; an archived COPY verifies post-hoc through its
closeout's byte-bound inventory (path equality is an in-run
property).

## 4. P1 — the verifier authenticates the ledger identities

`verify_val_run(run_dir, ledger_path=…, expected_head_sha256=…,
expected_val_lock_sha256=…)`: the launch and closeout are now
AUTHENTICATED from the verified chain — never caller-supplied.
Exactly one launch entry may bind the manifest; an unclosed
launch must be the chain tail (the in-run mode); the closeout is
located by `closes_entry_sha256`. Added checks: the prelaunch
environment's self-hash against the manifest binding;
`run_record["run"]` against the frozen tranche name;
`launch_entry_sha256` against the authenticated entry; and EVERY
duplicated closeout field cross-checked against recomputed
evidence (`terminal_artifact_hashes`, `surface_lock_sha256`,
`val_lock_sha256`, `val_lock_file_sha256`,
`run_record_file_sha256`, `execute_env_file_sha256`,
`rendered_observations`). Regressions: the forged
`run_record["run"]` refuses; a forged head authenticates nothing;
the aborted-run path verifies through the chain-authenticated
closeout.

## 5. Smaller corrections

- The stale `semantic_overlap_report` docstring is rewritten (the
  hard gate is semantic; prompt overlap is disclosed).
- The collision MEMBERSHIP is frozen and cell-stratified: the
  report (and therefore the lock) now carries
  `affected_candidate_ids` (the exact colliding val observations)
  and `affected_by_cell` — any repeated-vs-novel descriptive
  report uses this frozen membership, acknowledging the
  cell-confounded reuse.

## 6. Next

Changed-lines/test/hash review (per 336_s, a broad audit is not
warranted) → the real prelaunch manifest preparation on the
frozen C2 head under the registered root → the narrow launch
sign-off of its exact hashes → the V2 GPU launch → V3 lock →
Unit Y.
