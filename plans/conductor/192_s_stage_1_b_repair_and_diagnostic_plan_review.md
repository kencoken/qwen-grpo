The overall Route B design is good, but neither document is quite ready for execution sign-off. Let's focus on `190_f` for now and pause work on the development-track launch plan until we have completed the fixed B run.

## `190_f` — B repair and diagnostic

The proposed `BatchEncoding` repair is correct, and `256 × 18 × 2 = 9,216` is consistent. Four changes remain:

1. **Bind the complete request/execution contract** (`§4`, lines 99–106).

   The manifest should include the tokenizer revision, chat-template hash, per-observation×prompt rendered-request hashes, full quantization/adapter construction, decoding parameters, singleton batching/RNG semantics, parser and reward identities—not only model and prompt hashes. Reuse a diagnostic version of the existing `REPLAY_CONTRACT` and replay manifest.

2. **Authenticate the integer statistics from raw evidence** (`§4`, lines 115–146).

   The consuming verifier must enforce the exact 9,216 raw keys, reparse every completion, apply positional→semantic conversion, rescore it against the pinned surface, and require exact equality with every persisted assignment and reward count. Required count identities should include:

   - `parseable ≥ valid`;
   - sum of assignment counts = valid count;
   - sum of reward-level counts = 256;
   - malformed/invalid completions remain in the denominator with reward zero.

3. **Freeze the diagnostic estimands precisely** (`§4`, lines 129–146).

   Define `p2` and `p3` as frequencies of the two exact otherwise-identical family-correct assignments divided by all 256 draws—not generic worker marginals or conditional-on-valid rates. Compute nonlinear quantities per observation×prompt first, then aggregate renderer→latent→equal-cell. Report worker-2-favoured and worker-3-favoured directions separately.

4. **Add an implementation lock before the one-shot diagnostic** (`§5`, lines 152–162).

   After implementation and the reward-blind smoke, require a changed-lines review and clean-source lock before sampling retained support. The smoke should use the same repaired helper, model construction and generation kwargs as the diagnostic. Also restore the Ollama/free-VRAM preflight and enforce both deadlines inside the generation loop with a monotonic clock, preserving partial evidence on abort.

With those changes, I would sign `190_f`.

Recommended sequence:

1. Revise and sign `190_f`.
2. Implement, smoke, review/lock, and run B.
3. Use B only as descriptive prior information
4. Return to the development-track launch plan as the next step