# 322_f — Spine Unit 5 REV2 (response to 321_s)

Both P1s repaired. The repair follows the review's own scoping
rule: what can be genuinely bound NOW is bound and enforced; what
cannot exist before the precursor units land is EXPLICITLY
deferred — and no longer marked complete anywhere. Full suite:
**1023 passed under `-W error`, TRUE exit 0**. The appendix was
regenerated through the generator (12,665 bytes); the
contract/projection/mixture identities are untouched.

## 1. P1 — the freeze now binds the execution it authorizes (what is bindable)

**The canonical complete P0 runtime profile** —
`P0_RUNTIME_PROFILE` (`p0-runtime-profile-v1`), pinned at
`eae2e2fc…` and guarded at every binding:

- construction sections (model/revision, full NF4 quantization
  dict, full LoRA dict incl. all seven targets, batch 2×4 shape,
  optimizer/loss/scheduler, policy token cap, determinism,
  updates-per-group, worker-outcome mode, the 504-key LoRA
  key-set) are cross-checked field-by-field against the
  HASH-GUARDED C2 config — the profile structurally cannot drift
  from the Step-5-validated construction;
- the training deltas are the SIGNED house launch profile
  (13_f/106_s/120_f): **beta 1e-3** (the reviewer's finding — the
  schema no longer permits an arbitrary beta), lr 1e-5, 10-step
  warmup, constant schedule.

`RuntimeIdentity` gained `runtime_profile_sha256`;
`bind_runtime_identity` (run at EVERY build and EVERY
preparation) enforces: the profile pin; **`prompt_sha256` equal
to the ACTUAL recomputed policy prompt** (the reviewer's `00…00`
reproduction now refuses at build AND at preparation — a
regression hand-crafts the freeze file, confirms it loads
structurally, and confirms preparation refuses); and every scalar
(model, revision, quantization, dtype, key-set, group size,
temperature, lr, beta, token cap) equal to the canonical profile
value. The test fixture now carries beta 1e-3.

**What cannot be bound yet is explicitly deferred, not claimed**:
`prepare_p0_launch` is renamed **`prepare_p0_dataset`** — it is
dataset preparation, never launch admission. Its result carries
`launch_admission = {status: DEFERRED, outstanding: …}` naming
the four outstanding obligations verbatim: precursor artifacts
resolved and verified under their pinned hashes (they do not
exist yet); the execution-manifest binding as the EXTERNAL launch
argument (305_f §1); the environment-manifest attestation against
the freeze expectation; cadence/eval-decoding/telemetry identity.
The appendix matrix now has a dedicated **"Launch admission
(execution + precursor binding)" row marked DEFERRED** to the
post-merge unit constructing the real instance, and the consumer
row is retitled "Dataset preparation" with artifact "dataset
bundle (runtime; never an authorization)".

## 2. P1 — strict sentinel trajectory assembly

`assemble_sentinel_trajectories` now requires the **exact frozen
index sets** (`expected_checkpoint_indices` /
`expected_evaluation_indices`, keyword-only): validated as
strictly increasing non-boolean integers beginning at checkpoint
ZERO; a `complete` trajectory must equal the expected set exactly
— empty and truncated trajectories refuse (both reproductions are
regressions). **`infrastructure_abort` is handled explicitly and
separately**: the observed sequence must be a STRICT PREFIX of
the expected set, and the result carries a
`disclosed_truncation` record (observed vs expected counts) —
never silent. The expected sets themselves are frozen with the
real P0LaunchFreeze instance post-merge; the appendix trajectory
row says so explicitly.

**Semantic block validation** (every reproduction a regression):
`training_exposed` must equal the contract's sentinel exposure
(False refuses); all seven counters non-negative non-boolean
integers (negative and boolean refuse); completion denominator ≥
group denominator; worker/reward counters bounded by the
completion denominator (999 selections refuses); varying/counted
bounded by the group denominator; counted ≤ varying (a counted
group necessarily varies); first-index maps carry exactly the
four families, each value None or a non-negative non-boolean
integer (boolean refuses), group- and update-space Noneness in
agreement, update ≥ group; and **count/first-index consistency in
both directions** (a positive counter with a None first index
refuses; a zero counter with a set first index refuses). Blocks
are **deep-copied** — the regression mutates the source block
after assembly and confirms the result is unreachable.

## 3. Scope of change

`p0_launch.py` (profile + binding + rename + strict assembly),
`p0_tables.py` (matrix rows), the regenerated appendix, and
`test_routing_dev.py`. No frozen artifact touched; identities
unchanged; the equivalence oracle PASS 25/25.

## 4. Next

Sign-off on this rev2 → the MERGE GATE → post-merge:
routing_dev_val lock, cycle/R_cycle, beta smoke, the real
`P0LaunchFreeze` instance (its hash externally reviewed; launch
admission implemented THERE against existing artifacts) →
checkpoint-zero eval → P0 with sentinel tracking.
