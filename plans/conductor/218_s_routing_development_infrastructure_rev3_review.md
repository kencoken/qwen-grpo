## Verdict

Changes still requested before Step 4. The full suite passes: **959 tests under `-W error`**.

### Step-4 blockers

1. **The prelaunch environment and execution identity remain forgeable.**
   [`validate_environment_manifest_binding()`](/private/tmp/review217/tasks/routing/dev_support.py:371) verifies only that an arbitrary mapping hashes to itself. I confirmed that a fictional environment manifest is accepted. Its bytes are not persisted, and the execution lock does not bind the declaration, cohort, runtime/pool/cache identity, probe rule, search cap or budget.

   Use the canonical Stage-1 environment builder/validator, persist `env_manifest.json`, and create one support-launch manifest binding all prelaunch inputs. Materialization should consume its externally frozen hash. The eventual tracked driver—not `dev_support.py` merely named as one—must be included.

2. **Launch admission still relies on caller discipline.**
   [`check_launch_admissible()`](/private/tmp/review217/tasks/routing/ledger.py:300) accepts a caller-provided `entries` list rather than verifying the persisted ledger and committed head itself. Passing `entries=[]` authorized “first support” repeatedly. Admission is also separate from the prospective entry and append, so the checked kind/budget need not be the recorded kind/budget.

   Make the consuming boundary take the ledger path, expected head and prospective launch entry, then verify, admit and append that same entry. Keep the 60-hour envelope fixed there.

   Non-finite values also fail open: both a `NaN` launch maximum and `NaN` reserve were accepted. Require `math.isfinite()` for every budget, timing, multiplier and reserve value.

### Required before their dependent tranches

3. **The headline aggregation is not bound to the frozen cohort.**
   [`equal_cell_view()`](/private/tmp/review217/tasks/routing/telemetry.py:422) checks six cells and renderer completeness only for latents that arrive. It cannot detect a wholly missing/extra latent, wrong groups-per-observation or wrong `G`. An extra authenticated group changed hierarchical ModelAcc from `1.0` to `0.9444` and was accepted.

   Before the grouped probe, add a report boundary consuming the frozen bound cohort and rule and requiring exact observation IDs, multiplicities and group size. The formulas themselves are now correct.

4. **Aborted segments may still omit checkpointed groups.**
   [`merge_segments()`](/private/tmp/review217/tasks/routing/checkpoint.py:391) enforces exact cutoff coverage only for complete segments. An aborted segment claiming cutoff 3 with rows `[0,1]` is accepted. Every segment must contain `[resume_from, cutoff)`; only the post-cutoff aborted tail is optional.

Minor: reserve rounding remains descriptive rather than exactly recomputed, and `git diff --check` reports trailing whitespace in `216_s`.

The comparator rederivation, observation membership, reward authentication, mandatory checkpoint-bundle verification, RNG cross-binding, and complete-segment repairs are correctly closed. One narrow repair round should be sufficient.