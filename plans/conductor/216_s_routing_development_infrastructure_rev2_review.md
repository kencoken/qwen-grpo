Not ready to proceed yet. The repair is substantially better, and all **960 tests pass under warnings-as-errors**, but several reachable consuming-boundary defects remain.

## Blocking findings

1. **The surface lock is still post-execution and caller-asserted.**  
   [`materialize_dev_support()`](/tmp/qwen-grpo-ff8fce6-review.ciI7yF/tasks/routing/dev_support.py:231) consumes no prelaunch source/environment/driver lock. [`build_surface_lock()`](/tmp/qwen-grpo-ff8fce6-review.ciI7yF/tasks/routing/dev_support.py:350) subsequently accepts arbitrary 64-character hashes and any nonempty driver. I reproduced a loadable surface claiming invented provenance.  
   Add a prelaunch execution lock, consumed by materialization, then a post-run surface lock extending it with output hashes.

2. **Ledger protections remain optional.**  
   [`append_ledger_entry()`](/tmp/qwen-grpo-ff8fce6-review.ciI7yF/tasks/routing/ledger.py:194) allows omission of the externally committed head; suffix deletion can therefore be followed by a valid-looking replacement chain. [`check_launch_admissible()`](/tmp/qwen-grpo-ff8fce6-review.ciI7yF/tasks/routing/ledger.py:276) treats `initial_support=True` as a reusable caller assertion rather than deriving “first support launch, exactly once” from the verified ledger.  
   Require the expected head on every append and have admission consume verified ledger state and launch kind. Require `cohort_selection="outcome_blind"` for support/probe launches.

3. **Telemetry is not bound to the frozen surface and comparator.**  
   [`group_stats()`](/tmp/qwen-grpo-ff8fce6-review.ciI7yF/tasks/routing/telemetry.py:125) accepts a bare surface mapping and a self-hashed but otherwise forgeable comparator record. Switching a fabricated `c_fixed_dev` from worker 2 to 3 changed ScaleLift for the same trace. An unknown observation with all-invalid completions is also accepted because no surface lookup occurs.  
   Consume the verified loaded-surface context, rederive or fully verify `c_fixed_dev` against that exact lock, and require observation membership before scoring any completion.

4. **The registered headline estimand remains incomplete.**  
   [`equal_cell_view()`](/tmp/qwen-grpo-ff8fce6-review.ciI7yF/tasks/routing/telemetry.py:377) omits hierarchical ModelAcc and conditional C2, and labels partial populations “equal cell.” It should validate the complete frozen population and report eligible-only hierarchical numerators and denominators.

5. **Checkpoint artifact verification is optional.**  
   [`validate_resume()`](/tmp/qwen-grpo-ff8fce6-review.ciI7yF/tasks/routing/checkpoint.py:220) succeeds when disk hashes are omitted. Make artifact rehashing mandatory at the resume boundary, preferably by passing the bundle directory and fixed filename manifest. Also cross-bind the persisted RNG artifact to `rng_state_sha256`.

6. **Segment merging still accepts impossible histories.**  
   [`merge_segments()`](/tmp/qwen-grpo-ff8fce6-review.ciI7yF/tasks/routing/checkpoint.py:342) accepts reordered rows `[1,0]` and a complete segment with cutoff 3 containing only rows `[0,1]`. Require the original sequence to equal the exact range `[resume_from, cutoff)`.

Lower severity: reserve basis fields need numeric/recomputation validation, and worker/assignment “frequencies” need denominators rather than raw counts alone.

The runtime/request/cache binding, payoff authentication, pair-direction derivation, first-probe shape, closeout accounting, and RNG capture/restore are now correctly repaired. I recommend one narrow repair round covering the six items above; after that, sign-off should be realistic without another open-ended audit.