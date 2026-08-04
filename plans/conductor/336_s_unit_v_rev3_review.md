## Verdict

Rev3 is much closer, but I would **not sign off for launch yet**. Four localized P1 issues remain; three contradict explicit Rev3 closure claims.

### Findings

1. **[P1] Latent alpha-normalization is not actually handle-invariant.**

   `normalized_latent_semantics()` serializes the latent before replacing handles. Because JSON sorts mapping keys, the original handle spelling can change first-appearance order and therefore the hash.

   Concrete example: consistently renaming the two handles in `fork_join:routing_dev_val:00001:beaa828e:resource_first:private` changes its semantic hash despite identical semantics.

   Repair by deriving the mapping from `public_manifest` order, recursively replacing known handles in keys and values **before** canonical serialization. Add lexical-order-reversal tests across every frozen multi-handle latent.

   Encouragingly, a correct invariant implementation still gives zero semantic intersections for all three comparisons. This is a behavior-preserving repair.

2. **[P1] The authoritative ledger still accepts the wrong first parent.**

   `execute_val_run()` correctly checks the frozen C2 parent, but `admit_and_append_launch()` only checks that the supplied parent is the ledger’s current head.

   The new regression inadvertently proves the bypass: execution rejects `other_reserve`, after which direct ledger admission accepts a validation launch on that same foreign head.

   Bind the frozen initial parent into the validated launch contract and enforce it at ledger admission. Also require `val_materialization` to be outcome-blind there. Tests should cover:

   - wrong-parent direct admission refusing;
   - correct-parent direct admission succeeding;
   - identical-design retry succeeding only after an aborted closeout.

3. **[P1] `run_root` is recorded but not bound to the directory executed.**

   The manifest fixes `runs/routing-dev/val-surface-v1`, while `execute_val_run()` accepts any caller-provided directory. The committed end-to-end test succeeds under a temporary directory despite carrying the frozen root.

   This also leaves the registered retry without an honest filesystem path: the original directory cannot be reused, while a new directory works only because the root check is absent.

   Register a simple attempt-root rule, bind the actual execution root into the manifest, and compare resolved paths at preparation, execution and verification. Attempt identity can remain outside the scientific-design hash so an aborted retry preserves the design.

4. **[P1] The terminal verifier does not authenticate several claimed identities.**

   `verify_val_run()` accepts a caller-supplied closeout without verifying it against the ledger. I reproduced successful verification after:

   - changing `run_record["run"]` to `"forged-run"`;
   - falsifying the supplied closeout’s `surface_lock_sha256`, `rendered_observations`, and `run_record_file_sha256`.

   It also does not verify the prelaunch environment’s self-hash against the manifest, authenticate `launch_entry_sha256`, or validate several closeout fields.

   The verifier should consume a ledger path plus externally expected head, authenticate the launch/closeout entries, and cross-check every duplicated run-record and closeout field.

### Smaller corrections

- Update the stale `semantic_overlap_report()` docstring saying prompt intersections must be empty.
- If repeated-versus-novel prompt reporting is retained, freeze collision membership and stratify by cell: current prompt reuse is strongly cell-confounded.

### Confirmed closed

The amended overlap framing, frozen-cohort rederivation, configuration/source checks, runner-level retry guards, cumulative accounting, deadline handling, exact file inventory, mandatory surface authentication, and fresh overlap recomputation are otherwise sound.

Mechanical checks are clean:

- **1,029 tests passed** under warnings-as-errors.
- Focused Unit V tests: **6 passed**.
- Config, freeze and 720-seed identities rederive.
- Diff check clean.

This should be one final narrow Rev4. Once these four boundaries are repaired, a changed-lines/test/hash review should be sufficient; another broad Unit V audit would not be warranted.