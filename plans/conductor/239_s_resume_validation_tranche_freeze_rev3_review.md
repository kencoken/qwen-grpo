## Verdict

**One more narrow repair is needed before launch.** The live GPU/resume path now looks credible; the remaining problems are with the evidence and provenance contract rather than likely runtime failure.

### Remaining blockers

1. **Gate 1 is still not independently reproducible.**

   Only B’s checkpoint-zero map is persisted in [`checkpoint_zero_hashes.json`](/private/tmp/review238/tasks/routing/resume_validation.py:1221). The verifier therefore cannot rederive that A, B and C all started identically.

   It also accepts arbitrary-but-equal non-`END` cursors, counters and cardinalities because it never rederives them from the schedule and traces or checks `validation_record["counters"]`.

   Persist per-arm zero maps plus the exact scheduled observation-ID list. The verifier should derive:

   - A/B/C zero-state equality;
   - trace cardinality and expected counters;
   - schedule prefix and next cursor;
   - corresponding duplicated fields in `validation_record.json`.

2. **Environment and preflight evidence are not bound at admission.**

   The static identity deliberately excludes the environment. A changed `uv.lock`, Torch/CUDA stack or GPU can therefore retain the reviewed static identity hash. The environment and VRAM preflight are computed before admission, but [the launch entry](/private/tmp/review238/tasks/routing/resume_validation.py:1137) binds neither. The preflight is persisted only in the successful terminal record, so an admitted abort loses that evidence.

   Bind the environment-manifest hash and preflight record/hash into the launch entry, persist them immediately, and have the verifier cross-check both archived manifests. Ideally the reviewed freeze should also carry the expected environment hash.

3. **HF equivalence remains fail-open for malformed archives.**

   [`verify_hf_checkpoint_against_bundle()`](/private/tmp/review238/tasks/routing/resume_validation.py:706):

   - silently skips adapter comparison when `adapter_model.safetensors` is absent;
   - compares adapter tensors as an unordered hash multiset;
   - checks Python and NumPy RNG only when those fields happen to exist.

   Require the expected adapter file and all four RNG streams, and compare adapter tensors through normalized names rather than an unordered multiset.

A synthetic archive with valid state/HF hashes but deliberately incorrect identities, counters and preflight still returns `PASS`, so this is reachable through the public verifier rather than merely internal-object hardening.

### Confirmed fixed

- Update-6 no longer overwrites the update-3 bundle.
- Single-GPU CUDA RNG normalization works.
- Full Python/NumPy/Torch RNG equality works for the real checkpoint shape.
- NaN and infinity contamination refuses.
- Full completions/actions/assignments are compared.
- Live trace-to-schedule checking works.
- Current 4090 preflight passes: **24,079 / 24,564 MiB free**.
- All hashes rederive; ledger head and unused run root are correct.
- **970 tests pass under `-W error`**; diff check and worktree are clean.

The tranche itself needs no redesign. After these evidence-boundary fixes and focused regressions, a narrow changed-lines review should be enough to lock and run Step 5.