## Verdict

**Not ready to launch yet.** Most previous findings are genuinely fixed, and the 4090 budget looks comfortable, but two deterministic runtime bugs would currently abort the tranche.

### Blocking findings

1. **The uninterrupted arm overwrites its checkpoint-3 bundle at update 6.**

   With `save_steps=3` and `max_steps=6`, Transformers saves at both updates 3 and 6. [`on_save()`](/private/tmp/review236/tasks/routing/resume_validation.py:574) writes the bundle unconditionally, always targeting `checkpoint-3`. Consequently, A’s bundle ends up containing update-6 state while B retains update-3 state; Gate 2 will necessarily fail.

   Only write when `state.global_step == checkpoint_at`, refuse a second write, and test the update-3/update-6 callback sequence.

2. **Single-GPU CUDA RNG validation will always fail.**

   On the frozen non-distributed runtime, HF stores `rng_state.pth["cuda"]` as one tensor. The sidecar stores `torch_cuda` as a list containing one tensor-state list. [The comparison](/private/tmp/review236/tasks/routing/resume_validation.py:697) iterates the HF tensor into scalar integers, producing the wrong shape.

   Normalize a single tensor to `[tensor.tolist()]`. Also compare Python and NumPy RNG states, since HF restores those too.

3. **The archive verifier does not yet independently rederive its advertised result.**

   [`verify_resume_validation()`](/private/tmp/review236/tasks/routing/resume_validation.py:818) currently does not:

   - verify `final_state_sha256`;
   - bind `checkpoint_record_sha256` to the loaded record;
   - revalidate the bundle files and consumed HF checkpoint;
   - independently derive Gate 4—it merely checks that two stored strings differ;
   - rederive A/B checkpoint-prefix equality or checkpoint-zero equality;
   - compare full completion/action/assignment traces.

   A synthetic archive with missing bundle state files and incorrect recorded hashes can still return `PASS`. Either strengthen the verifier to rederive these claims or narrow the freeze’s “archive-alone independent verification” claim. Given the project’s artifact-trust standard, I recommend strengthening it.

4. **The reviewed freeze still does not bind the reviewed execution identity.**

   The expected freeze hash covers configuration, question, motivation and budget. Prompt, source, cohort, renderer and environment identities are calculated after that check. A code or prompt change can therefore leave the reviewed hash unchanged.

   Persist and require one prelaunch-manifest hash covering the complete `_identities` result before ledger admission. Record full 64-character hashes in the freeze document rather than only `711c8204…`.

5. **Exact comparison accepts NaNs.**

   [`compare_tensor_states()`](/private/tmp/review236/tasks/routing/resume_validation.py:294) accepts NaN-versus-finite at tolerance zero because `NaN > worst` is false. I reproduced this on picome. Require finite tensors/differences before comparison.

6. **Two smaller charter requirements remain.**

   - Cross-check actual trace observation IDs against the frozen schedule prefix before deriving the next sampler identity.
   - Run and persist the charter-required Ollama/free-VRAM preflight before admission. Post-phase memory-release checking does not replace that session preflight.

### Verified as fixed

- Identical reseeding and six-update horizons across arms.
- Real update-4 fault with preserved/excluded tail.
- HF checkpoint content binding.
- CPU snapshots and actual trainer-reference release.
- Per-step deadline and `full_determinism=True`.
- Reward-variance and nonzero-update gates.
- Complete optimizer parameter-group comparison.
- Production clean-clone surface restoration.

Mechanical checks are clean: **966 tests passed under `-W error`**, `git diff --check` passes, hashes rederive, the ledger head is correct, and the Step‑5 run root remains absent.

These are localized repairs; Step 5 itself does not need redesign. After one fix commit, revised full hashes and a narrow changed-lines review, it should be ready to launch.