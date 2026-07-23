Stage 0’s scientific GO stands, but the closure record needs a small erratum before being treated as fully authoritative. No GPU rerun is necessary.

Verified:

- `conductor_stage_0b_d16` is clean at `242f1c1`.
- All 674 tests pass under warnings-as-errors.
- The retained CE0 result and subordinate hashes reconcile.
- Complete materialization exercised all four logical workers evenly: 31 distinct requests each.
- No fresh qualification data were touched.
- The selected pre-materialized execution mode is comfortably feasible on the 4090.

## Record-only corrections

The following should be corrected in [127_f_stage_0_go_no_go_handoff.md](/private/tmp/stage0-closed/plans/conductor/127_f_stage_0_go_no_go_handoff.md:23), or explicitly superseded in the Stage 1/2 redraft:

1. **43.4 minutes is not a full Stage-2 first-seed estimate.** It prices the 18-observation diagnostic surface. A 100-latent-per-cell reference scale gives approximately:

   - 32,400 payoff rows;
   - 12,400 expected physical generations;
   - about 78 minutes of materialization;
   - about two hours including the projected training run.

   Even a deliberately pessimistic no-dedup extrapolation is about 9.1 hours, so the 12-hour gate still passes. The real estimate must be recomputed after the Stage-2 population and 300-update schedule are actually frozen.

2. **“Live worst case” did not exercise worker 3.** It used the family-reference route, for which Code always selects worker 2. Rename this the reference-route live benchmark. This does not undermine the selected mode: complete pre-materialization did exercise worker 3.

3. **17/18 means terminals reached, not 17 correct answers.** The identity of the `math_code × goal_first` failure comes from earlier evidence, not the persisted CE0 result.

4. **The automated `go` flag is partly declarative.** `no_infra_failures_as_reward` is hard-coded, and the sane-distribution gate is carried manually from the frozen smoke. Those facts are supported, but the record should distinguish computed CE0 gates from manually verified prior evidence.

5. Correct “every prediction hit” and “startup+loads 4.4 seconds.” The full command beat the 90–240 second prediction rather than falling inside it, and lazy model loading occurred inside the materialization timer.

6. Add the materialization-manifest SHA, `1e52c399…`, and carry the formal construction difficulty-band decision—especially `math_code`—as an explicit Stage-1 prerequisite.

I would describe Stage 0 as **GO with a record-only erratum**, not reopen it.