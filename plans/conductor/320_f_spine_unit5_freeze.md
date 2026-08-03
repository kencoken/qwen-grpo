# 320_f — Unit 4 LOCKED; Spine Unit 5: P0LaunchFreeze schema + the first real consumer (for review)

Unit 4 is locked at its signed rev3 state (§1). Unit 5 implements
303_f §9 step 5 within its registered boundary: the LAUNCH-FREEZE
SCHEMA, builder, and strict loader are frozen NOW; the INSTANCE is
constructed only after the val/cycle/beta inputs exist
(post-merge), exactly as the plan requires. Full suite: **1023
passed under `-W error`, TRUE exit 0** (1020 + three new tests).

## 1. Unit-4 locked identities (the signed pins)

- Code state: 319_f @f35fd33 (`p0_cap.py` with key-membership
  admission; `p0_tables.py` byte-exact gate).
- Committed appendix at Unit-4 sign-off: 11,187 bytes
  (regenerated THIS unit for the closed deferred rows — §4).
- Contract/projection/mixture identities unchanged throughout:
  `d47a63ff…`/`8b348b0f…`, `f1912078…`/`41f15c5d…`,
  `135a72bf…`/`b305d9c8…`.

## 2. `tasks/routing/p0_launch.py` — the P0LaunchFreeze schema

Schema `p0-launch-freeze-v1`, typed frozen dataclasses with
`__post_init__` validation (the p0_schema validators reused):

- `science_contract_sha256` — set from the loaded contract at
  build; admission requires equality with the reviewed-pin-loaded
  contract.
- `PrecursorOutputs` — the four reviewed-output pins
  (routing_dev_val lock, cycle, R_cycle, beta smoke), 64-hex
  validated (303_f §2: the launch freeze pins their reviewed
  outputs; the precursor units keep their own freezes).
- `LaunchPlan` — **the `derive_launch_plan` record persisted
  VERBATIM**, typed: the registered `CapInputs` (field order ==
  the registered tuple, enforced), all three values with
  `launch == min(nominal, capacity)` re-validated at
  construction, the closed launchable branches with
  branch-consistent optional fields (under-target must carry its
  quantified disclosure and no spare field; spare-capacity the
  reverse). **The stop branch is structurally UNFREEZABLE**
  (`launchable` must be True; `build_p0_launch_freeze` admits the
  record through `require_launchable` first). `to_record()` must
  round-trip `_strict_equal` to the input record — the verbatim
  proof is executed at every build.
- `RuntimeIdentity` — the intrinsic fields (model id, 40-hex
  revision, nf4 + fp32 LoRA enforced as the validated
  construction, LoRA key-set and prompt hashes, group size, seed,
  temperature, learning rate, beta, token cap) plus the
  COMMIT-INDEPENDENT `attested_environment_sha256` expectation.
  P0 runs REAL training: learning_rate must be positive.
- **Excluded by the closed schema** (305_f §1): the
  execution-manifest hash (an EXTERNAL launch argument) and every
  terminal output hash (closeouts only) — the loader refuses any
  extra field (regression: an injected `execution_manifest_sha256`
  refuses at the closed schema even with a recomputed self-hash).
- `save_launch_freeze` (writes once) /
  `load_p0_launch_freeze(path, expected_sha256)` — the reviewed
  hash is REQUIRED with no default constant: none exists until a
  real instance is reviewed (303_f §7).

## 3. The first real consumer + the trajectory assembly

`prepare_p0_launch(freeze_path, expected_freeze_sha256)`: freeze
under its reviewed hash → contract under `d47a63ff…` → contract
pin equality → the plan REDERIVED at admission
(`require_launchable`) → the standing oracles FRESH
(`verify_c2_equivalence`, which authenticates the complete replay
source, and `verify_appendix`) → the trainer dataset from the
STRICT schedule loader for exactly `launch_epochs` frozen epochs,
with the row/schedule identity re-checked. The integration test
runs it end-to-end on a genuine capacity-one freeze (157 rows;
counting wrappers prove both oracles were invoked exactly once; a
freeze pinning a different contract refuses at admission).

`assemble_sentinel_trajectories(contract, checkpoint_blocks,
evaluation_blocks)` closes the deferred 305_f §4 obligation:
strictly increasing non-boolean checkpoint indices, COMPLETE
per-checkpoint field sets (a dropped field refuses), and the
contract-bound sentinel population (a foreign population refuses).

## 4. Generated appendix updated

The matrix's two deferred rows now NAME their implemented
enforcement and regressions (`build_p0_launch_freeze` verbatim
persistence; `assemble_sentinel_trajectories`), a new "Launch
admission (the first real consumer)" row covers
`prepare_p0_launch`, and the sentinel section's trajectory rows
point at the assembly function. Regenerated through the generator:
**11,877 bytes**; the byte-exact gate passes; the test now asserts
NO dangling "DEFERRED to Unit 5" text remains.

## 5. Scope of change

New: `p0_launch.py`, three tests; the appendix regenerated; the
matrix rows updated in `p0_tables.py`. No frozen artifact touched;
all identities unchanged; the equivalence oracle PASS 25/25.

## 6. Next

Reviewer pass on this unit → the MERGE GATE (full suite green
under `-W error`; every committed archive reverifying; the
equivalence oracle; the traceability appendix reviewed; sign-off)
→ merge `conductor_spine` → `conductor_stage1` → the post-merge
sequence: `routing_dev_val` lock, cycle/`R_cycle`, beta smoke,
then the REAL `P0LaunchFreeze` instance (its hash externally
reviewed) → checkpoint-zero eval → P0 with sentinel tracking.
