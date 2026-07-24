## Lock verdict

**Not ready to lock yet.** Rev3 closes most previous findings correctly, but several changed-line issues can still alter or invalidate the frozen tranche.

### Blocking findings

1. **The replay executes different seeds from those preregistered.**

   `completion_seed()` freezes unsigned 64-bit seeds, but `run_replay()` applies `% 2**63`. This changes **4,541 of the 9,216** replay seeds. The pinned PyTorch build accepts the full unsigned range, so remove the modulus.

2. **The B execution path does not yet match its frozen model condition.**

   Compared with the Stage-2 loader, `run_replay()` omits explicit `torch_dtype=torch.bfloat16`, `task_type="CAUSAL_LM"` and the trainer’s k-bit preparation path. The “byte-identical Stage-2 sampling path” claim is also incompatible with the deliberately different singleton batching.

   Use the shared frozen model construction where possible, or run a reward-blind parity probe and describe B honestly as a separately frozen singleton replay regime.

3. **Persisted B evidence remains caller-attested.**

   `load_b_artifact()` does not:

   - load and validate the actual replay manifest;
   - verify the raw-completions file or even require its hash;
   - rederive the pair table and observation metadata from pinned support;
   - reparse the 9,216 completions and compare the resulting counts.

   A self-rehashed artifact can change every direction to `unknown` and thereby turn a blocking result into `confirm_possible=True`.

   Verification should happen at the consuming boundary using the environment manifest, replay manifest, raw completions and pinned surface. No proof-marker type is needed.

   Similarly, `aggregate_verdict()` currently proves only that all four artifacts contain the same 64-hex string—not that it is the hash of a valid `stage1-environment-v2` manifest.

4. **The agreement population still does not represent D1.**

   Its ordinary-stake datasets contain one σ=0.50 cell, whereas D1 contains five equally weighted σ=0.75 cells. Agreement for the former does not authorize 2,000 replicates for the latter. Use the actual D1 shape. Equivalence agreement should also alternate positive/negative boundaries or have an explicit sign-equivariance test.

5. **The runtime abort and failure record are not implemented as claimed.**

   Timing is checked only after all 5,000 trials finish, so it cannot interrupt an over-budget scenario. Moreover, nothing is persisted until every D scenario succeeds. An agreement failure or runtime abort therefore leaves no environment, A/C result, agreement outcome, timing or partial-D record.

   Add an in-loop deadline check, persist each stage boundary and an aborted/complete run record, record per-scenario wall times, and refuse overwriting an existing formal run directory. The replay directory has the same overwrite problem.

6. **The preregistration remains internally contradictory.**

   `147_f:203–204` still says “64-sample denominator,” while the operative value is 256. It also promises a per-completion seed table, but the manifest contains only the deterministic recipe. Either representation is fine, but the document must match the implementation. Reissue forward before lock.

### Smaller correction

`sequential_stake_decision()` computes its point estimate with ordinary `cell.mean()`. A single ineligible/NaN row makes the point NaN even when the bootstrap interval is finite and positive. Use the same eligible-cluster, equal-cell statistic as the bootstrap; an entirely zero-eligible cell should remain unresolved.

### What passed

- Focused Unit 3 suite: **68 passed**
- Full suite: **830 passed** with warnings treated as errors
- Diff formatting check: clean
- No frozen simulation or GPU replay was run

The 256/9,216 accounting, semantic action scoring, fixed denominator, structural Bonferroni population, hierarchical weighting, Wilson agreement threshold, cluster-level DGP variance and adverse equivalence handling are otherwise correctly implemented.

After these targeted fixes, only a mechanical verification of these exact points should be needed before locking—no further open-ended audit.