Verdict: Rev2 closes the original design findings, but it is not ready for prelaunch or GPU execution. The remaining work is a bounded runner repair, not another design revision.

### Blocking findings

1. **The training run currently fails on its first reward call.**

   `build_trainer_rows` uses conversational prompts, so TRL passes completions as message lists. The reward at `p0_smoke.py:1000` passes that list directly to `parse_routing_action`; I reproduced:

   ```text
   AttributeError: 'list' object has no attribute 'encode'
   ```

   Reuse or wrap the established `make_validation_reward` boundary, which normalizes `completion[0]["content"]`, validates group alignment, records full traces, and treats missing surface rows as infrastructure errors.

2. **The trace timing still measures the wrong operation.**

   No training completion trace is written. P6 compresses only the two evaluation JSONLs, calls that `per_epoch_trace_bytes`, and multiplies its sealing cost by 39. Trainer logs and terminal hash/verification time are excluded. Moreover, evaluation phases claim sealed persistence, but sealing occurs later in P6.

   Capture the complete 157-group training trace; seal each evaluation inside its evaluation phase; and time training-trace flush, archive, hash and round-trip verification separately before applying the ×39 rule.

3. **The checkpoint is neither the production v1 bundle nor discarded.**

   `_save_checkpoint_bundle` writes a PEFT directory plus one `training_state.pt`, omitting the established artifact manifest, counters, sampler position, checkpoint record and restore verification. It therefore does not price the real P0 checkpoint operation. The trained adapter is then retained indefinitely, contrary to the signed discard rule.

   Use the validated checkpoint contract, verify it, retain proof hashes/timing only, and delete the trained state before successful closeout.

4. **Timing-only disclosure and RNG isolation are not enforced.**

   - `disable_tqdm=True` causes Transformers to install `PrinterCallback`, which prints reward/KL/loss logs every 16 steps. `report_to="none"` only disables W&B.
   - Checkpoint-zero evaluation calls global `torch.manual_seed` 90 times without restoring state, so training starts from the last evaluation RNG state rather than the frozen training state.
   - The freeze authenticates 720 per-slot seeds, while execution uses only 90 slot-zero seeds.

   Remove/capture the printer callback, use the existing `isolated_rng` boundary, and freeze the seed realization actually executed.

5. **Budget and provenance boundaries remain incomplete.**

   - The deadline is checked only after all six phases, allowing substantial overspend. Check it within both evaluation loops, before each training generation step and between phases.
   - The persisted environment file is not cross-checked against the manifest’s environment hash.
   - `engineering_smoke` has no authoritative manifest-bound ledger-admission branch.
   - There is no terminal verifier before recording `complete`.

### Correctly repaired

- Two evaluation passes with conservative maximum pricing.
- The 0.75 GPU-hour reviewed ceiling.
- Disjoint top-level phase definitions.
- Exact warmup, update-count and epoch-consistency checks.
- Strict persisted freeze binding the contract, mixture, prompt, surface and runtime.
- Exact, non-rounded cap arithmetic.

Mechanical checks are clean and **1,034 tests pass under warnings-as-errors**, but the suite does not execute the new real reward path, which is why the immediate completion-shape failure escaped.

I would make one Rev3 runner repair, add focused regressions for these real paths, and only then prepare the prelaunch manifest—any code repair will change its source identity anyway.