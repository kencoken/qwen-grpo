## Verdict

Rev2 closes the original structural issues well, but I recommend one short Rev3 before sign-off. Two new/remaining defects can change the measured trajectory or epoch cap.

### Blocking findings

1. **Checkpoint-indexed seeds break the paired evaluation design.**

   Lines 148–153 derive validation seeds from the checkpoint index. That gives checkpoint zero and later checkpoints different random draws, contrary to the charter’s same-seed paired comparison.

   Derive seeds from:

   `evaluation domain + base seed + observation ID + completion slot`

   Do not include checkpoint index. The checkpoint belongs in provenance, not RNG derivation. Apply the same common-random-number rule to the two cycle checkpoints.

2. **The ten-hour cap still underprices execution.**

   The nominal cadence contains eleven evaluations:

   `{0, 4, …, 36, 39}` = checkpoint zero + nine intermediate + final.

   Lines 73–88 price only the nine intermediates and the final. Add checkpoint-zero’s approximately 420 seconds to `frozen_non_rollout_overhead_seconds`.

   The one-epoch smoke also cannot use its one-epoch trace flush/archive time directly as the final-run reserve. Scale or conservatively bound this for the nominal 39-epoch trace volume. The clean decomposition is:

   ```
   non-rollout overhead =
       checkpoint-zero evaluation
       + 9 × (intermediate evaluation + checkpoint write)
       + any one-time startup inside the ten-hour clock

   finalization reserve =
       worst rollout batch
       + final evaluation
       + final checkpoint write
       + full-run trace flush / verification / archival
   ```

   Persist cadence indices in the spine’s actual optimizer-update units, not only epoch labels: epoch four is update/group count 628, and nominal final is 6,123.

3. **The final `R_cycle` record still mixes two incompatible formulas.**

   Lines 15–25 describe an itemized component sum and then a ×2 multiplier. The current ledger validator instead computes:

   `cohort × multiplier × measured support seconds/observation`

   Mechanically, that is:

   `90 × 2 × 2.44 / 3600 = 0.122 h → ceil = 1 h`

   Meanwhile, surface materialization plus the two evaluations is already approximately `0.061 + 0.2325 = 0.2935 h` before verification/archive. Both happen to round to one hour, which could conceal the inconsistent basis.

   Freeze one exact recomputable rule. A simple option is:

   - implement the currently disabled validator-gated final-reserve path;
   - retain the registered rounded basis;
   - independently derive an itemized closure ceiling;
   - set the reserve to the rounded maximum of the two;
   - prove the complete cycle-closure maximum is ≤ the resulting reserve.

4. **Launch admission needs one explicit consuming boundary.**

   Unit L verifies precursors while constructing the freeze, but execution-time admission currently mentions only manifest and environment checks. Before checkpoint zero, one fail-closed operation should freshly:

   - load and verify all four raw precursor records under their freeze pins;
   - rederive every cap input from the timing record, cadence and ledger;
   - verify `P0ExecutionIdentity` under an externally reviewed hash and bind it to the reviewed launch freeze;
   - verify source/driver and environment identities;
   - run dataset preparation and standing gates;
   - enforce `remaining envelope ≥ P0 launch maximum + final R_cycle`.

   No trainer entry point should bypass this boundary.

### Small clarifications

- An engineering resume retains the existing launch freeze, epoch target and cadence while enforcing cumulative wall time. Only a genuinely new reviewed relaunch may rederive the cap.
- If cycle materialization partially reveals outcomes, allow only an exact design-preserving resume/retry. Otherwise retire that cohort and report cycle evaluation unavailable.
- Reviewers should receive an automated timing-only projection from Unit T; retain but do not inspect its semantic trace until after the P0 freeze.
- Normalize away namespace/identity-only fields in the semantic-overlap check, so an empty intersection is substantive rather than tautological.
- State explicitly that all P0, validation and cycle evidence remains development-only.

Everything else is now in good shape: the validation isolation, cadence concept, identity order, cycle closure rule, descriptive `n=5` framing, scope boundary and retry identities are resolved correctly. The commit is mechanically clean. After these bounded amendments, I would sign the plan and begin Unit V.