## Verdict

Not quite ready for the merge gate. Rev2 closes the original two blockers, but two narrow result-affecting issues remain.

1. **The canonical runtime profile does not actually implement its declared warmup.**

   `scheduler="constant"` ignores `warmup_steps=10`; I verified the learning rate begins immediately at 1.0, whereas `constant_with_warmup` produces the intended ramp. The signed Stage-0 implementation used `constant_with_warmup`.

   Keeping `grad_accum=4` and one group/update is defensible because `246_f` later validates that as the P0 training shape, but that later evidence should be cited as controlling. The profile should also pin the material currently hard-coded trainer settings: shuffle behavior, gradient checkpointing/kwargs, model dtype and SDPA implementation.

2. **Sentinel assembly still accepts states its producer cannot emit.**

   I reproduced successful “complete” assembly with:

   - worker-1 selections differing from worker-1 completions;
   - seven completions for a frozen `G=8` group;
   - first group index 3 but first update index 999 despite one group/update;
   - expected trajectory `(0,)`, despite checkpoint zero plus a positive final checkpoint being mandatory.

   An infrastructure abort after completing one trajectory stream but before the other also refuses incorrectly. Each stream should be a prefix, with at least one strict prefix globally.

   Enforce the producer invariants, require zero plus a positive final index, and bind the expected sets later through the authenticated `P0ExecutionIdentity`. That is the natural home for the explicitly deferred cadence/evaluation/telemetry configuration.

The execution/precursor issue is now handled honestly: `prepare_p0_dataset()` cannot authorize training, and the appendix clearly retains launch admission as deferred. That scope is acceptable for this merge.

Mechanical checks are otherwise clean:

- **1,023 tests passed** under warnings-as-errors.
- C2 equivalence: **25/25 PASS**.
- Runtime-profile and appendix hashes pass.
- Prior forged-runtime and trajectory probes now fail.
- Worktree and diff checks are clean.

One final narrow Rev3 addressing the two points above—and updating the stale module header—should be sufficient for merge sign-off.