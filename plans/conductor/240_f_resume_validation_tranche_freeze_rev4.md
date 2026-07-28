# 240_f — Step-5 resume-validation tranche freeze REV4 (response to 239_s)

The three evidence-boundary blockers are repaired. No GPU work or
ledger admission has occurred. Full CPU suite: **972 passed under
`-W error`, TRUE process exit 0** (56 in the routing battery).

## 1. Frozen identities (FULL; supersede 238_f where changed)

- Config (unchanged — no frozen literal moved):
  `1c8d2a5df9ee8e05b5d9590d15ce72836312e140b1f2bafed36654fb0acbe578`
- Freeze (unchanged):
  `1f7bd7764c48eba5439aac312b7510a6b1654916509bb0374971896464093f09`
- **Static execution-identity manifest (CHANGED with the code — the
  property F4 demanded):**
  `6cd416ba0884baa2ae182ea8601ea9c560482fa7b2aaf62aa6fc62609e7ae96f`
- **Attested environment (NEW, 239_s F2 — the manifest body
  excluding the commit-dependent fields, so the freeze commit
  itself cannot change it):**
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head at launch:
  `264066e66d60ab8819ec5382122690ad73f798391eeafdeb6ba763ed17ac3f2b`

Launch signature — all FOUR reviewed hashes required:
`execute_resume_validation(expected_freeze_sha256,
expected_identity_sha256, expected_environment_sha256,
expected_head_sha256)`.

## 2. The findings, closed

1. **Gate 1 independently reproducible; the verifier rederives,
   never trusts**: PER-ARM checkpoint-zero maps persist
   (`checkpoint_zero_hashes.json` = uninterrupted / interrupted /
   resumed), and the exact scheduled observation-id list persists
   (`schedule.json`, hash-bound to the identity manifest's cohort).
   The verifier now derives A/B/C zero equality from the maps;
   counters, trace cardinality and the next cursor from the FROZEN
   config + archived schedule (never from arbitrary-but-equal
   cursor files); the schedule prefix over both trajectories; the
   bundle identities against the archived identity manifest; and
   requires the duplicated `validation_record` fields to match the
   rederivations.
2. **Environment and preflight bound at admission**: the launch
   entry's freeze carries `environment_manifest_sha256`,
   `attested_environment_sha256` (== the reviewed value), and
   `session_preflight_sha256`; the environment, identity manifest,
   preflight, and schedule persist BEFORE admission, so an admitted
   abort preserves them (they enter the aborted-closeout
   inventory). The reviewed freeze binds the environment through
   the attested hash above; a changed uv.lock/torch/CUDA/GPU
   refuses at launch (regression: the attested hash survives a
   `git_commit` change and moves on a torch change). The verifier
   cross-checks both archived manifests against the record.
3. **HF equivalence fail-closed**: `adapter_model.safetensors` is
   REQUIRED (a missing file refuses); adapter tensors compare
   PER-NAME through normalized keys (both PEFT grammars mapped to
   one name; a collision refuses; regression covers matching-under-
   different-grammar and changed-tensor refusal); python, numpy and
   — when the bundle has it — CUDA RNG streams are REQUIRED, never
   conditionally skipped.

## 3. Next

The 239_s changed-lines review, then the GPU run with the four
hashes of §1, its close-out record, and the unchanged grouped-probe
freeze (step 6).
