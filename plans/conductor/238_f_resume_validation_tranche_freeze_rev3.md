# 238_f — Step-5 resume-validation tranche freeze REV3 (response to 237_s)

All six findings are repaired. No GPU work or ledger admission has
occurred. Full CPU suite: **970 passed under `-W error`, TRUE
process exit 0** (54 in the routing battery).

## 1. New frozen identities (supersede 236_f; FULL hashes per F4)

- Tranche: `routing-dev-resume-validation-v3`
- Config:
  `1c8d2a5df9ee8e05b5d9590d15ce72836312e140b1f2bafed36654fb0acbe578`
- Freeze:
  `1f7bd7764c48eba5439aac312b7510a6b1654916509bb0374971896464093f09`
- **Static execution-identity manifest** (F4 — NEW; prompt, routing
  source, config, cohort, renderer schedule, surface manifest +
  lock, pool fingerprint, cache identity, seed; everything in the
  run identity EXCEPT the live-built environment, which is attested
  separately):
  `82cd19675169b28d2740ec66d0ea965bbcf5753b9c7dcc78319d3ad55f0d787f`
- EXACT ceiling unchanged: 0.5 GPU-hours. Ledger head at launch:
  `264066e66d60ab8819ec5382122690ad73f798391eeafdeb6ba763ed17ac3f2b`

Launch signature (both reviewed hashes REQUIRED):
`execute_resume_validation(expected_freeze_sha256=…,
expected_identity_sha256=…, expected_head_sha256=…)` — a code,
prompt, cohort, or surface change after this review refuses at
launch (F4).

## 2. The findings, closed

1. **Bundle overwrite at update 6**: `on_save` writes ONLY at
   `state.global_step == checkpoint_at` and refuses a second write
   at the checkpoint step; the update-3/update-6 callback sequence
   is a CPU regression (save at 6 is a bundle no-op; duplicate at 3
   refuses). Gate 2 can no longer be self-defeated by the
   uninterrupted arm's second HF save.
2. **Single-GPU CUDA RNG**: the HF `rng_state.pth["cuda"]` single
   tensor is normalized to `[tensor.tolist()]` before comparison;
   python and numpy RNG states (which HF also restores) are now
   compared against the bundle sidecar too.
3. **The verifier rederives everything it advertises**: from the
   archive alone it now re-hashes both persisted final-state
   directories against `final_state_sha256`; binds
   `checkpoint_record_sha256` to the loaded bundle record;
   revalidates the bundle state files (hash + RNG cross-bind) and
   the consumed HF checkpoint
   (`verify_hf_checkpoint_against_bundle`); rederives gate 1/4 from
   the PERSISTED `checkpoint_zero_hashes.json` and the bundle
   adapter bytes (never two stored strings); rederives the A/B
   checkpoint-prefix and bundle equality; and compares FULL traces —
   `trace_sequence` now carries completions, parsed actions and
   semantic assignments everywhere (compare_runs included). A
   synthetic archive with missing bundle files or invented hashes
   refuses.
4. **The reviewed execution identity is bound** (§1): the static
   identity manifest is persisted into the run root and its hash is
   a required launch argument, checked BEFORE ledger admission;
   full 64-character hashes recorded above.
5. **NaN-safe exact comparison**: `compare_tensor_states` requires
   finite tensors on BOTH sides before differencing — NaN-vs-finite
   and NaN-vs-NaN both refuse (CPU regressions).
6. **Charter items**: `_final_state` cross-checks every trace
   observation id and global index against the frozen schedule
   prefix before deriving the next-sampler cursor (mismatch
   refuses); `gpu_session_preflight` (nvidia-smi free-VRAM ≥ the
   frozen 20,000 MiB floor — an ollama-resident model refuses) runs
   BEFORE admission and is persisted in the validation record.

## 3. Next

The 237_s changed-lines review of this rev3, then the GPU run:

```
execute_resume_validation(
  expected_freeze_sha256="1f7bd776…{full above}",
  expected_identity_sha256="82cd1967…{full above}",
  expected_head_sha256="264066e6…{full above}")
```

then the close-out record and the unchanged grouped-probe freeze
(step 6).
