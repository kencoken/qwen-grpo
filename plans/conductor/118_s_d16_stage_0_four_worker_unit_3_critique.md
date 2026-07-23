## Review outcome

Unit 3’s execution and reported GPU results are credible, but the persisted payoff surface is not yet safe to use as Unit 4’s training truth. Changes requested before proceeding.

### Blocking findings

1. **[P1] The loader trusts persisted payoff values instead of independently scoring them.**

   I changed a genuine row from:

   ```json
   {"payoff": 0.5, "terminal_value": null}
   ```

   to `payoff: 1.0`. The loader accepted all 324 rows. Unit 4 would therefore train on a fabricated success even though the stored terminal outcome says the workflow failed.

   The loader should regenerate observation→gold mappings and require:

   ```python
   payoff == score_terminal(terminal_value, regenerated_gold)
   ```

   Also strictly validate row fields and types; booleans and floats currently compare equal to integer worker IDs/payoffs in Python.

2. **[P1] The materialized surface is not adequately bound to its execution provenance.**

   The loader currently checks only the declaration hash and worker-visible fingerprint. I confirmed it still accepts:

   - an invented `worker_pool_fingerprint`;
   - an invented runtime fingerprint;
   - contradictory row/execution counts; and
   - in-range edits between `0.5` and `1.0`.

   A fabricated directory with no real trace can therefore look like a valid surface.

   A compact fix is sufficient:

   - versioned, exact manifest schema;
   - SHA-256 of `payoffs.jsonl`;
   - hashes of the trace manifest and steps;
   - exact pool/support identity checks;
   - trace `closed=true`, `status=complete`, and matching WV/pool/RTP;
   - expected row and step counts plus accounting invariants; and
   - Unit 4 pins the resulting surface-manifest hash.

3. **[P1] A visible runtime can materialize the declared private support.**

   Visibility is excluded from the worker-visible fingerprint, so a runtime declaring `visibility_condition="visible"` passes the current check even though the declaration and regenerated observations are private. Its trace then records a runtime profile inconsistent with the support it executed.

   Require the runtime’s visibility condition to equal the declaration and validate the complete regenerated support description—not only observation IDs.

### Smaller finding

`run_canary` records the expected direction but only checks that rewards differ. A reversed result would pass. Require exact agreement with the fixture: worker 2 → `0.5`, worker 3 → `1.0`.

### What is correct

Independent checks confirmed:

- 641 tests pass under warnings-as-errors.
- Agreement remains 16,665/16,665.
- Support is exactly six `worker_dev` ordinal-0 latents × three private renderers.
- All 324 assignments and 804 planned steps are present.
- Trace accounting reconciles: 804 rows, 560 real calls, 244 dependency-blocked steps, 124 unique physical generations/cache rows, and zero persistent-cache hits.
- Semantic-to-positional conversion is correct for the shuffled fork order.
- The canary reproduced worker 2 = 0.5 and worker 3 = 1.0.
- Both fresh-process model orders passed all 12 sentinel checks.
- No construction or qualification examples were consumed.

The current GPU outputs need not be discarded. The retained trace and payoffs can be passed through the stronger verifier, although a clean rematerialization is only about 48 seconds and may be simpler.

## Interpretation of the results

The result demonstrates genuine, useful model orchestration—not merely an artificially enlarged action space:

- `math_code × goal_first` requires worker 3.
- `fork_join × goal_first` and `fork_join × bound_var` require worker 2.
- Therefore, “always use the larger model” is wrong.
- The best fixed Code choice, worker 2, scores 17/18; context-conditioned scale selection reaches 18/18. Always choosing worker 3 scores 16/18.

That is the core phenomenon wanted from this toy experiment: identical requests sent to different checkpoints produce complementary outcomes, and selecting the checkpoint can improve reward.

The scope remains deliberately narrow:

- There are only six independent latent programs; the 18 observations are renderer crossings.
- All come from adaptively used `worker_dev`.
- The separating cues are strongly cell/renderer-conditioned.
- Family routing supplies most reward variation; only 3 of 9 Code-bearing observations distinguish worker scale.

Consequently, Unit 4 can test whether GRPO discovers and exploits the routing signal, but not whether routing generalizes semantically.

One numerical caution: `24/324 = 7.4%` is a row-weighted surface statistic, not the expected success rate of the equal-observation smoke schedule. Under uniform valid actions, averaging each observation equally gives roughly 19.8% success. Signal will nevertheless be sparse in the hard strata: a unique fork winner occupies `1/64` of valid actions, giving only about a 12% chance that a uniformly sampled group of eight contains it. Expect family routing to emerge before reliable small-versus-large selection, with substantial zero-variance noise in fork groups.

Compute-wise, Unit 3 is reassuring: 124 physical generations in 47.5 seconds and a roughly 3.6 MB artifact make pre-materialized routing very comfortable on the 4090. CE0 still needs full-command timing and final lifecycle memory measurement, since the 47.5-second timer excludes runtime/tokenizer construction and Unit 3 did not independently record peak VRAM.

After the three P1 integrity fixes and the exact canary check, I would sign off Unit 3 and proceed to Unit 4 without another broad audit.

---

## Resolution (2026-07-23)

All three P1s fixed plus the exact canary check; detail in
`119_f_d16_stage_0_four_worker_unit_3_response.md`. Headlines: the
loader independently re-scores every payoff from its stored terminal
value against the regenerated gold (the flipped-row reproduction now
aborts) with exact row typing; the surface manifest is a versioned
exact schema binding payoffs.jsonl and both trace files by content
hash, cross-checked against declaration, trace identity
(closed/complete/wv/pool/rtp) and the accounting invariants — all four
manifest reproductions are negative regressions; materialization
requires the runtime's visibility to equal the declaration and
verifies the complete regenerated support description; run_canary
requires the exact registered direction (a reversed disagreement
fails). The surface was cleanly rematerialized under the new schema
(identical execution: 560 records, 124 generations, 46.3s; canary
exact-pass). Unit-4 pin: surface manifest sha256
`221a04d53403f14c537a3d43336eb6630ca6fe5682f5e3f8aa66f78ace679c23`.
653 tests; agreement 16,665/16,665.
