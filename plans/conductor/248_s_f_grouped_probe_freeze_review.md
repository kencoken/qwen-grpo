## Verdict

Not ready to lock or launch at `23e2057`. The cohort, schedule, compute envelope, and sampling design are sound; four narrow integrity/conformance repairs remain. No broad redesign is needed.

### Blocking findings

1. **[P1] The implementation contradicts the signed zero-update contract.**

   The charter requires “ZERO optimizer updates, zero model mutation” ([211_f §5](/private/tmp/review221/plans/conductor/211_f_routing_development_charter_rev4.md:222)). The implementation instead calls `trainer.train()` and requires 432 optimizer steps ([probe_run.py](/private/tmp/review221/tasks/routing/probe_run.py:490)).

   Learning rate zero plus identical adapter hashes proves zero parameter mutation, but optimizer/scheduler and RNG state still evolve.

   I recommend amending and re-freezing the contract as:

   > 432 real trainer optimizer-step calls at learning rate zero; zero effective parameter updates and exact checkpoint-zero adapter equality.

   This better serves the probe’s purpose—exercising P0’s real between-generation training path—than introducing a rollout-only special path. The document must stop describing this as the “unchanged” 211_f design.

2. **[P1] Report reconstruction does not authenticate what the policy actually selected.**

   [`groups_from_trace()`](/private/tmp/review221/tasks/routing/probe_run.py:234) only applies `json.loads()` to completion text, then trusts the persisted `action`, `assignment`, and `reward` fields.

   I reproduced a completion selecting worker 2 being reported as worker 3 with worker 3’s authenticated reward. That can corrupt worker frequencies, C1/C2, direct contrasts, and reward statistics while `verify_probe_run()` still passes.

   Reconstruction should:

   - parse each completion with `parse_routing_action`;
   - derive its semantic assignment through the frozen positional mapping;
   - derive reward from the locked surface;
   - require the stored action, assignment, and reward to match;
   - reject unequal parallel-array lengths rather than allowing `zip()` truncation.

3. **[P1] The archive verifier is not yet independent.**

   [`verify_probe_run()`](/private/tmp/review221/tasks/routing/probe_run.py:291) does not verify the archived environment, identity manifest, preflight, cohort, schedule, trace order, or global indices. Those are checked during live execution, but not at the persisted-artifact trust boundary.

   It should rehash and cross-bind:

   - environment and attested environment identity;
   - execution-identity manifest;
   - preflight values and acceptance semantics;
   - bound cohort and fully rederived 432-row schedule;
   - exact trace cardinality, order, observation IDs, and global indices;
   - record headers and frozen identities.

   The verifier currently also cannot independently prove zero mutation: only `checkpoint_zero_hashes.json` is persisted, while the final map remains in memory. Persist `checkpoint_final_hashes.json` and compare the two maps, not merely two digest strings copied into `probe_record.json`.

4. **[P1] One signed reporting category is absent.**

   The charter explicitly requires group-construction, cache, worker-execution, and infrastructure telemetry ([211_f §5](/private/tmp/review221/plans/conductor/211_f_routing_development_charter_rev4.md:239)). The scientific exposure report is comprehensive, but contains no explicit execution-telemetry block.

   Record the applicable counters and explicitly state that cache and live-worker calls are zero/not applicable because reward comes from the locked payoff surface. Include surface lookup counts, group-accounting counters, runtime/deadline information, and available infrastructure measurements.

### Smaller improvements

- Emit a complete cell × renderer × direction support matrix, including zero-denominator combinations. This will let the later P0 transport gate mechanically reject unmeasured strata.
- Require `expected_head_sha256` to equal the lineage parent frozen in `PROBE_CONFIG`, rather than relying on the launch command to pass the reviewed head.
- Add narrow regressions for semantic trace mismatch, unequal trace-array lengths, provenance/schedule tampering, final-map mismatch, and the success/abort verifier lifecycle.

### What is already correct

- All frozen hashes rederive exactly.
- Cohort and schedule are exactly 108 observations, 432 groups, and 3,456 completions.
- Direction support is 216 no-Code, 192 tied-Code, 16 worker-2-favoured, and 8 worker-3-favoured groups.
- The three-hour allocation is admissible, with ample 4090 VRAM and disk headroom.
- The Stage-5 backup exists and matches its recorded hash.
- The full suite passes: 979 tests under warnings-as-errors; diff-check is clean.
- No Step-6 run root exists, so these repairs remain fully pre-outcome and do not compromise the outcome-blind freeze.

After those focused repairs, a changed-lines review plus hash/test/ledger check should be sufficient to lock and launch.