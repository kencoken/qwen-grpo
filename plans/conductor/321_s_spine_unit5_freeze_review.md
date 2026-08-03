## Verdict

Unit 5 needs one bounded repair pass before sign-off. Two P1 findings can affect the experiment’s identity or diagnostics.

### P1 — Launch admission does not bind the execution it authorizes

In `p0_launch.py:241–288` and `413–455`, the freeze records some runtime fields, but `prepare_p0_launch()` never verifies them against the execution that will run.

I reproduced a freeze declaring:

- `prompt_sha256 = 00…00`
- a fictional attested-environment hash;
- dummy precursor hashes.

It still returned `PASS` and generated 157 rows using the real prompt (`fe9bba0d…`).

This also conflicts with the signed design:

- No external execution-manifest/environment argument is admitted as required by `305_f §1`.
- The frozen design specifies `beta=1e-3`, but the schema permits any nonnegative beta and the test fixture uses `0.04`.
- Material settings are absent: complete quantization and LoRA configuration, batch/accumulation shape, optimizer/loss/scheduler/warmup, update and checkpoint cadence, evaluation RNG/decoding, determinism, worker-pool/request/cache/reward-surface identity, and telemetry/provenance.
- Val/cycle/`R_cycle`/beta-smoke hashes are only checked as hexadecimal strings; their artifacts and passing outcomes are never loaded or verified.

The simplest repair is a canonical complete P0 runtime profile plus hash, validated against the actual prompt, worker/runtime profile and external execution manifest at admission. Precursor artifacts must also be resolved under their pinned hashes. If those checks genuinely cannot exist until the precursor units land, this function should remain “dataset preparation” and launch admission must stay explicitly deferred—not be marked complete in the appendix.

### P1 — Sentinel trajectory assembly does not enforce valid or complete trajectories

In `p0_launch.py:469–517`, assembly accepts:

- empty or arbitrarily truncated trajectories;
- `training_exposed=False`;
- negative denominators;
- 999 selections against an impossible denominator;
- malformed/Boolean first-occurrence indices.

It also shallow-copies blocks, so nested data can be mutated after validation.

Require:

- exact frozen checkpoint and evaluation index sets, including checkpoint zero and the final checkpoint;
- semantic validation of counters, denominators, exposure, first-index maps and count/index consistency;
- immutable normalization or a deep copy;
- explicit separate handling for incomplete infrastructure-abort trajectories.

The generated appendix should retain these items as deferred until that enforcement is real.

### What is sound

- The Unit 4 JSON-order repair is correct.
- Cap persistence, rederivation and stop-branch exclusion are sound.
- Freeze hashing, closed-schema loading and contract binding work.
- The schedule is exactly `157 × launch_epochs`.
- Q1/Q2/Q3 interpretation remains correctly scoped.
- Full suite: **1,023 passed** under warnings-as-errors.
- C2 equivalence: **25/25 PASS**.
- Appendix: **11,877-byte PASS**.
- Worktree and diff checks are clean.

After these two focused repairs, I would expect Unit 5 to be ready for sign-off and the merge gate.