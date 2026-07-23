Unit 4 is close, but I would not lock the current prompt or launch the reward-bearing smoke yet. This is the right point to perform the prompt freeze, after one focused correction pass.

### Blocking prompt-freeze findings

1. **The policy input is not fully frozen or using the canonical observation boundary.**

   [`build_smoke_rows()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-unit2/tasks/conductor/grpo_task.py:45) uses a new hand-written renderer rather than the existing identity- and visibility-checked [`render.build_observation()`](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-unit2/tasks/conductor/render.py:318). This changes the supposedly unchanged skeleton and omits `Resources available` and canonical access notation.

   The recorded hash is also calculated dynamically from only `SYSTEM_CONDUCTOR`. It excludes:

   - the 18 rendered user observations;
   - the tokenizer/chat-template bytes;
   - the observation-rendering code.

   Editing the source before import automatically updates both sides of the current validation. Use a literal reviewed digest over the complete model-visible prompt bundle.

2. **The four demonstrations do not yet satisfy the inherited demonstration contract.**

   All four are atomic, whereas the signed plan called for demonstrations covering one-step routing, dependency, independent→final, and specialist→verification workflows. As written, the 3B model is never shown a two- or three-element action, potentially confounding routing learning with action-length acquisition.

   The Lookup example is not currently executable: it conflates `B-11` as resource handle and badge/key, and defines no legal entity, field, or payload.

   The Code demo checker also substitutes a shortened Problem and noncanonical resource serialization. My exact canonical probes found:

   - both Code workers solve both Code examples;
   - the Math example succeeds with value `269`;
   - the Lookup example cannot currently be instantiated as specified.

   The Code examples should additionally be counterbalanced: index `2`/“buffer” currently implies worker 2 while index `0`/“log” implies worker 3, introducing an arbitrary scale-routing cue.

3. **The named profile is not yet authoritative over execution.**

   - It records `loss="dapo"` but never passes `loss_type` to `GRPOConfig`; the current behavior merely matches TRL 1.7.1’s default.
   - `live_singleton` passes validation but still executes the precomputed-surface path.
   - The stored surface and pool hashes are not the values actually consulted everywhere; separate module constants remain authoritative.
   - The model revision pins the weights, but because no explicit `processing_class` is passed, TRL loads the tokenizer/processor separately without that revision.

   For this smoke, the simplest resolution is to support only `precomputed_surface`, fail closed on everything else, and construct the trainer directly from the validated profile—including an explicitly revision-pinned processor.

### Before the reward-bearing smoke

The following are non-prompt issues but should land before launch:

- Add a schedule index to traces and require exactly 288 completions, 36 groups of eight, and the frozen observation order. The current summarizer accepts even a one-row trace as a complete group.
- Wire the four required online metrics: parse rate, reward-level frequencies, zero-variance-group fraction, and worker-selection entropy.
- Persist explicit surface-lookup and infrastructure-abort counts, including a failure-status artifact if training aborts.
- Reset CUDA peak-memory statistics after releasing the canary workers. Otherwise reported GRPO VRAM includes the earlier worker-model peak.
- Make the surface-pin test hermetic. A clean checkout currently gives 667 passes and one failure because the test expects the untracked materialized surface.
- Record the pre-existing `sentencepiece` teardown crash: all 668 test bodies pass on `picome`, but the process exits 139. The same occurs at the Unit 3 base, so it is not a Unit 4 regression.

### Positive evidence

The core integration is sound:

- the single `0/0.5/1` reward and missing-row infrastructure abort are correct;
- no generic format reward was added;
- positional-to-semantic assignment conversion is correct;
- the 324-row payoff surface verifies against its pin;
- locked TRL realizes the intended 36 groups over 18 optimizer updates;
- no private payload or model-size/name leakage was found;
- non-reward trainer construction on the 4090 succeeded in 7.62 seconds, with 2.77 GiB reserved baseline and 29.9M trainable LoRA parameters. Full generation/backprop VRAM remains for CE0.

### Recommended lock sequence

1. Restore the canonical observation renderer.
2. Replace the demonstrations with four executable, topology-covering OOD workflows, with balanced worker-2/worker-3 cues.
3. Make the demo command execute all four exact workflows through the real runtime.
4. Optionally run one preregistered reward-blind format probe across the 18 observations, reporting only JSON validity and correct array length.
5. Freeze literal hashes for the system text, all rendered observations, pinned chat-template bytes, launch profile, support manifest, and executable commit.
6. Set the review record and run the canary followed by the reward-bearing smoke exactly once.
