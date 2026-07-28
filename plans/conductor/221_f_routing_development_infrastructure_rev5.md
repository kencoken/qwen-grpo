# 221_f — Infrastructure rev5 (response to 220_s)

The integration-focused repair: all five findings and the minor item
are implemented, and the freeze-to-execution boundary now exists as
ONE tracked runner exercised end-to-end on CPU. Full CPU suite:
**956 passed under `-W error`, TRUE process exit 0** (40 in the
routing battery). No GPU work has run; nothing is frozen or
launched.

## 1. The tracked runner exists and owns the sequence (F5)

`tasks/routing/support_run.py` is the Step-4 driver the manifest
names (`DRIVER = "tasks/routing/support_run.py"`, inside the digest
set):

- `prepare_support_launch` — builds the declaration from the real
  runtime, builds the LIVE environment manifest
  (`build_stage1_env_manifest` by default; test-only injection
  hooks follow the stage1 pattern), builds the support-launch
  manifest, and persists all four prelaunch records under
  `run_dir/prelaunch/` exactly once. The returned manifest hash is
  what the freeze document commits, with the ledger head.
- `execute_support_run` — the fixed sequence: revalidate the
  prelaunch records against the externally frozen manifest hash →
  ADMIT the support launch (`admit_and_append_launch` with the
  manifest — the recorded entry names the manifest hash and carries
  its budget) → MATERIALIZE under that admission → surface lock →
  fail-closed reload → direction-yield disclosure → `c_fixed_dev`
  selection → probe-cohort binding → CLOSEOUT with the measured
  cost. Outputs persist once; a replay dies on the moved ledger
  head. CLI: `prepare` / `execute`.

The module-scoped test fixture runs this entire sequence on the CPU
fake pool with the real 6-prefix outcome-blind cohort (108
observations, 1,944 payoff rows) and asserts the resulting ledger
chain (admitted launch naming the manifest → closeout), envelope
accounting, and persisted outputs.

## 2. Admission and execution are linked (F1)

- A `support_materialization` entry is admissible ONLY with its
  launch manifest: the entry's freeze must name the exact
  `manifest_sha256` and the entry budget must equal the manifest
  budget (both refusal-tested).
- `materialize_dev_support` now takes `ledger_path` +
  `expected_head_sha256` and verifies the CURRENT ledger head is
  the admitted support entry naming exactly this manifest with this
  budget — the unadmitted-materialization and
  wrong-manifest-admission reproductions both refuse.

## 3. Environment provenance (F2)

- The runner builds the environment manifest LIVE — it is never a
  caller argument on the execution path.
- The surface lock binds the archived environment BYTES
  (`env_manifest_file_sha256`, recomputed at every validation), and
  `_load_persisted_launch` ALWAYS verifies the env manifest — full
  canonical validation in-session, `validate_env_self_hash`
  (body→hash binding without current-tree equality) on historical
  loads. The reviewer's `{}`-replacement reproduction refuses, and
  a canonical-shaped replacement with a valid self-hash dies on the
  byte binding.

## 4. The probe rule cannot be swapped (F3)

- `build_support_launch_manifest` requires the SIGNED first-probe
  kind and APPLIES the rule to the declaration before execution
  (a reprobe rule, or a rule the declaration cannot serve, refuses
  at the freeze).
- `bind_probe_cohort` requires the frozen rule's hash to equal the
  surface lock's `probe_rule_sha256` — the launched rule is the
  only bindable rule (post-materialization swap reproduction
  refuses).
- `probe_report` additionally REDERIVES the exact ordered
  observation ids from the rule + loaded declaration and requires
  the bound record to match — a self-rehashed cohort record with
  curated ids refuses.

## 5. Search cap in rendered observations (F4)

The cap counts `len(declaration["observations"])` (the signed §4
unit): the 6-latents × 3-renderers = 108-observations declaration
under `search_cap=107` refuses. Each cell's declared indices must
BE the outcome-blind prefix `0..k-1` (a curated subset refuses).

## 6. Minor

Trailing whitespace stripped from the committed `218_s`;
`git diff --check` clean this time.

## 7. Next

Reviewer sign-off ("one final integration-focused repair — no
further broad audit"), then the Step-4 freeze: run
`support_run.prepare_support_launch` on the GPU host with the real
runtime and environment, commit the prelaunch records + manifest
hash + ledger head in the freeze document, and on approval
`execute` — the ledger chain's first launch entry.
