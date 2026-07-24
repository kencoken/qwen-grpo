## Review verdict

Unit 2 is directionally sound, but I would not sign it off yet. Four provenance/phase-separation issues could plausibly contaminate formal results.

### Blocking findings

1. **[P1] Persisted manifests are not validated at consumption.**

   [`qualification_prefix()`](https://github.com/kencoken/qwen-grpo/blob/9eb08e5476715da9c64cbf6d88fbd43ce500ba90/tasks/conductor/stage1_manifest.py#L247-L256) trusts any mapping without checking its hash, schema, namespace, completeness, or regenerated identities.

   I reproduced:

   - a construction manifest being accepted as a qualification manifest and returning construction IDs;
   - a qualification ID being mutated after hashing and returned unchanged;
   - truncated support being accepted.

   Add one authoritative validator/loader that recomputes the hash and checks the exact phase, profile, source identity, cells, schedules, counts, IDs and lengths. Every public consumer should invoke it.

2. **[P1] The frozen difficulty profile and construction decisions are not enforced.**

   Both registrars accept any schema-valid profile, despite Unit 1 freezing only `dp-2bcb6373340a8a79`. A modified but valid profile was accepted as a formal population.

   Construction registration should permit only a preregistered candidate. Qualification registration should consume the construction-frozen profile and, ultimately, the frozen deployable/control artifact—not another free `profile` argument.

3. **[P1] `verify_rows()` is caller self-attestation rather than provenance verification.**

   [`verify_rows()`](https://github.com/kencoken/qwen-grpo/blob/9eb08e5476715da9c64cbf6d88fbd43ce500ba90/tasks/conductor/stage1_manifest.py#L264-L300) trusts a caller-supplied expected-key set. Consequently:

   - an arbitrary subset can be declared complete;
   - duplicate expected keys collapse through `set()`;
   - fabricated manifest/key pairs pass;
   - rows carry no environment, runtime, worker, endpoint or request identity.

   The environment manifest is currently a separate unhashed dictionary, so materially different execution conditions can still produce rows accepted under the same population hash.

   The simplest resolution is to derive structured expected row identities from a validated population/gate specification and require a content-addressed execution identity alongside the population identity. Existing runtime, worker-visible, pool and request fingerprints can be reused. If that join is intentionally deferred to Unit 4, the present helper should remain explicitly unavailable rather than claiming gate-report completeness.

4. **[P1] The registered support/count contract is incomplete.**

   [`_expected_cell_counts()`](https://github.com/kencoken/qwen-grpo/blob/9eb08e5476715da9c64cbf6d88fbd43ce500ba90/tasks/conductor/stage1_manifest.py#L130-L153) correctly records assignment, one-call, shortcut and some protocol totals, but omits support needed to protect later estimands:

   - full independent `(observation, node, logical worker)` execution rows;
   - intervention edge rows;
   - per-look denominator blocks;
   - per-selected-worker route counts once `d` is frozen;
   - named visible/control support.

   Planned logical support should be frozen now where deterministic. Outcome-dependent cache and physical-generation counts can be bound during materialization.

### Smaller corrections

- Require a non-empty look mapping and plain positive integers in `validate_qualification_looks()`; `100.0` currently validates.
- Either reject dirty trees for formal manifests or content-address their executable changes. `git_dirty: true` alone is not reproducible.
- Unit 1 states that infrastructure exception-to-code mapping lands in Unit 2, while Unit 2 explicitly adds no execution layer. Record its deferral to Unit 4 and ensure it exists before construction calls.

### Confirmed correct

The following pieces look good:

- formal construction cohort `30–129`;
- maximum qualification caps and immutable prefix concept;
- first-18 visible-slice placement;
- private renderer crossing;
- included count arithmetic;
- complete tracked `tasks/conductor/*.py` successor digest;
- worker-family and renderer authority cross-checks;
- queued `workerpool.py` citation correction.

Verification on `picome`:

- Focused Unit 1/2 regressions: **168 passed**
- CPU-compatible suite: **649 passed**
- Worker-evaluation suite: **79 passed**
- `git diff --check`: clean

The test processes still exit `139` after reporting completion, consistent with the recorded CUDA/NVML teardown issue; the new environment-manifest builder itself executed successfully.

After these focused fixes, I would close Unit 2 and proceed directly to Unit 3 without another broad audit.