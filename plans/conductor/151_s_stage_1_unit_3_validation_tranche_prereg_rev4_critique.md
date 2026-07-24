## Mechanical verdict: not lockable yet

The major fixes pass, but the real replay path still has two blockers that synthetic tests missed.

### Blocking

1. **Real B evidence cannot be recounted.**

   `build_smoke_rows()` stores `positions` as JSON text, but `recount_from_raw()` passes that string directly to `positional_to_semantic()`. With a real Code row this fails with:

   ```text
   InfrastructureError: action length 1 != 6 steps
   ```

   Parse the stored JSON before recounting and add a test using actual `build_smoke_rows()` output.

2. **The replay verifier still does not authenticate the pinned inputs or requests.**

   `verify_replay_evidence()` rederives from caller-supplied `surface` and `support_rows`. It also does not compare the replay manifest’s observation IDs, eligible pairs or rendered-request hashes with authoritative regenerated values. A rehashed manifest with an altered request hash is accepted.

   At the consuming boundary, load the frozen support/surface internally, regenerate the complete expected replay manifest—including request hashes—and require exact equality.

3. **Zero eligibility still becomes `fail`, not `unresolved`.**

   `point_estimate()` correctly returns `None`, but the bootstrap supplies `UCB=-∞`, causing the subsequent conclusive-failure branch to fire. When the point is `None`, continue to the next look; unresolved at the cap must remain unresolved.

4. **Failure-path persistence remains incomplete.**

   - GPU run-directory exclusion occurs only after all 9,216 generations; move it and the environment/replay-manifest writes before model work, and write complete/aborted timing status.
   - A D deadline abort occurs before the current scenario’s wall time and partial result are persisted. Preserve both in the abort record.

5. **Rev4 still contains the withdrawn claim.**

   [150_f line 207] still says “byte-identical Stage-2 sampling path.” Replace it with the separately frozen singleton-regime wording. “One seeded generator” should likewise say that the global CPU/CUDA RNG is reset per singleton draw.

### Passed

- Full unsigned 64-bit replay seeds: correct
- Model construction parity and named singleton regime: correct
- Environment-manifest validation: correct
- Raw hashing, exact 9,216-key accounting and count recount machinery: present
- D1-shaped agreement and alternating equivalence signs: correct
- In-loop deadline: correct
- Focused tests: **71 passed**
- Full suite: **833 passed**
- Diff check: clean
- No frozen tranche or GPU replay was run

These are narrow fixes. After them, rerun the focused suite plus the real-row recount and changed-request-hash refusal probes; then we can lock without another broader review.