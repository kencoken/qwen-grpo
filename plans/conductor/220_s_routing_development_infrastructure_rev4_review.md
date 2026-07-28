## Verdict

Not quite ready for Step-4 sign-off. Commit `31854be` is materially improved and the full suite passes—**960 tests under `-W error`**—but the remaining issues all sit on the actual freeze-to-execution boundary.

### Blocking findings

1. **The ledger admission and support execution are still independent.**
   [`admit_and_append_launch()`](/private/tmp/review219/tasks/routing/ledger.py:326) admits a ledger entry whose `freeze` can be any nonempty mapping. [`materialize_dev_support()`](/private/tmp/review219/tasks/routing/dev_support.py:231) never verifies that ledger entry or head.

   Consequently, the recorded and executed manifest or budget may differ, and materialization can run without admission. Require support entries to name the exact support-manifest hash and matching budget, then have materialization verify the recorded launch entry/current head. A single tracked Step-4 runner should own this sequence.

2. **Environment provenance is still partly caller-asserted and its archived bytes are unprotected.**
   [`validate_environment_manifest_binding()`](/private/tmp/review219/tasks/routing/dev_support.py:397) uses the canonical validator, but that validator checks shape, self-hash and current source—not whether the claimed git commit, GPU, lockfile or package versions match the live host. A canonical-shaped manifest with invented runtime values is accepted; the tests themselves use `git_commit="deadbeef"` and fake versions.

   More concretely, [`_load_persisted_launch(..., recompute=False)`](/private/tmp/review219/tasks/routing/dev_support.py:512) performs no validation of `env_manifest.json`. Replacing it with `{}` after surface locking still allowed the complete surface to load.

   The tracked runner should build the environment manifest live. The surface lock must bind its bytes, and historical loading must always verify body→manifest hash without requiring equality to the current source tree.

3. **The outcome-blind probe rule can still be replaced after materialization.**
   [`build_support_launch_manifest()`](/private/tmp/review219/tasks/routing/dev_support.py:410) accepts a generic reprobe rule and does not establish compatibility with the declaration. [`bind_probe_cohort()`](/private/tmp/review219/tasks/routing/cohorts.py:221) does not compare the supplied rule hash with `surface_lock["probe_rule_sha256"]`.

   I confirmed that a surface launched under one rule can subsequently bind a different rule. [`probe_report()`](/private/tmp/review219/tasks/routing/telemetry.py:474) then accepts that new self-consistent rule/cohort pair.

   Require the signed first-probe kind, apply it to the declaration before execution, compare its hash with the surface lock during binding and reporting, and rederive the exact ordered observation IDs rather than trusting a self-rehashed cohort record.

4. **The search cap uses the wrong unit.**
   [`build_support_launch_manifest()`](/private/tmp/review219/tasks/routing/dev_support.py:427) counts latent indices, whereas signed §4 defines the cap as rendered observations. Six latents crossed with three renderers produce 18 observations but currently pass `search_cap=6`. Count `len(declaration["observations"])` and ensure each cell’s declared indices form the frozen prefix.

5. **The actual tracked runner remains absent.**
   There is still no non-test CLI or entry point executing prepare → admit → materialize → lock → disclose/select/bind → closeout/reserve. `dev_support.py` is named as the driver in tests, but is not the actual caller. It is reasonable for this runner to land as part of Step 4, but it must exist and be reviewed before the freeze.

Correctly closed: same-entry ledger admission, required ledger head, finite-number handling, exact reserve rounding, aborted-segment coverage, and probe group-size/multiplicity checks.

Minor: `git diff --check` still reports trailing whitespace in `218_s`, despite `219_f` stating it is clean.

I recommend one final integration-focused repair—no further broad audit—then proceed to the Step-4 freeze.