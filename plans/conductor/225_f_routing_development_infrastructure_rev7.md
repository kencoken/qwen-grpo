# 225_f — Infrastructure rev7 (response to 224_s)

The three workflow gaps and both minors are repaired. Full CPU
suite: **961 passed under `-W error`, TRUE process exit 0** (45 in
the routing battery). No GPU work has run; nothing is frozen or
launched.

## 1. Complete, authenticated attestation (F1)

- `attest_environment` now compares the COMPLETE validated manifest
  bodies — every field either manifest carries (python, cuda,
  transformers, trl, peft, bitsandbytes, datasets,
  pyproject_sha256, whatever the canonical builder emits) — with
  ONLY the documentation-commit fields exempt
  (`git_commit`, `git_tree`, and the derived self-hash). The
  reviewer's changed-transformers reproduction refuses, as does a
  field present on only one side.
- The SUCCESS closeout now binds the terminal artifact bytes:
  `run_record_file_sha256` and `execute_env_file_sha256` in its
  freeze — replacing `execute_env_manifest.json` (or the run
  record) after completion is detectable from the hash-chained
  ledger. `verify_terminal_outputs(run_dir, closeout)` is the
  re-verification boundary (regression: a swapped execute-env
  refuses).

## 2. Aborted retries preserve the scientific design (F2)

- `dev_support.scientific_design_sha256(manifest)` freezes the
  design identity: declaration/cohort hash, namespace,
  worker-visible/runtime-profile/pool fingerprints, request
  contract, cache identity, probe-rule hash, search cap.
  Source/environment/budget/driver are deliberately absent — an
  infrastructure repair may change them.
- Every support entry's freeze must carry the manifest's design
  hash, verified at admission. The no-reserve recovery path now
  requires every prior ABORTED support launch to share the NEW
  entry's design — a changed cohort, rule, worker, request, or
  cache identity refuses with the outcome-informed-successor
  message (regression: self-consistent changed-design manifest
  refuses; design-preserving retry passes; open launch still
  blocks). The admission docstring states the actual rule (minor).
- Aborted closeouts bind a CONTENT-HASHED partial-artifact manifest
  (`partial_artifact_hashes`: every file under the run root at
  abort time) — preservation by hash, not by a mutable directory
  pointer. `verify_terminal_outputs` re-verifies it (regression:
  altered partial evidence refuses).

## 3. Reserves require successful Step-4 completion (F3)

A `reserve_update` is now appendable only when the verified chain
contains a `terminal_status="complete"` support closeout and NO open
launch, and its freeze must BIND that support: the closeout's entry
hash, the closeout's authenticated `surface_lock_sha256`, and the
reserve's new required `measured_support_gpu_hours` equal to the
closeout's measured cost. Regressions: empty-ledger reserve,
unbound freeze, wrong surface lock, measured-cost mismatch, and
reserve-while-launch-open all refuse. The ledger tests now build the
honest chain (support → complete closeout → bound reserve →
launches).

## 4. Minors

`222_s` trailing whitespace stripped; the admission docstring
documents the aborted-support exception instead of denying it.

## 5. Next

Reviewer sign-off ("after them, I would sign off and proceed to the
Step-4 freeze"), then Step 4: `support_run.prepare` on the GPU host,
freeze document with prelaunch records + manifest hash + ledger
head, `execute` on approval; the provisional reserve is recorded at
the post-materialization review — now necessarily bound to the
completed support's surface and measured cost.
