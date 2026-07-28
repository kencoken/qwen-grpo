## Verdict

Not ready to sign off yet. The original lifecycle and budget findings are substantially fixed, but three reachable workflow gaps remain.

### Blocking findings

1. **Live-environment attestation remains incomplete and unauthenticated.**

   [support_run.py:73](/private/tmp/review221/tasks/routing/support_run.py:73) omits active fields including Python, CUDA, Transformers, TRL, PEFT, bitsandbytes, datasets and `pyproject_sha256`. I confirmed that a canonical manifest with a changed Transformers version passes attestation.

   Compare the complete validated manifest body, excluding only explicitly allowed documentation-commit fields such as `git_commit`, `git_tree`, and the derived self-hash.

   Separately, `execute_env_manifest.json` is not bound by the surface lock, run record or closeout. It can be replaced after completion without `load_dev_surface()` noticing. Bind its hash into an authenticated terminal/surface artifact.

2. **An outcome-bearing abort can be retried under a changed design while still labelled outcome-blind.**

   The abort handler can run after the complete payoff surface or disclosure exists, but [ledger.py:388](/private/tmp/review221/tasks/routing/ledger.py:388) treats every aborted support launch as nonblocking. A replacement may therefore change the cohort, probe rule, worker configuration or request contract, while [support_run.py:232](/private/tmp/review221/tasks/routing/support_run.py:232) still records `outcome_informed=False`.

   The simplest conservative repair is to freeze a scientific-design identity and require every aborted-support retry to preserve it. Source/environment/budget may change for an infrastructure repair; declaration/cohort, probe rule, worker/request/cache identities may not. A changed scientific design would need an explicitly outcome-informed successor and could no longer authorize the nominal first probe.

   Also bind a content-hashed partial-artifact manifest into aborted closeouts. A mutable directory pointer is not sufficient preservation.

3. **A reserve can bypass successful Step-4 completion.**

   `append_ledger_entry()` currently accepts a provisional reserve on an empty ledger or while support remains open. The tests explicitly exercise both patterns. Once that reserve exists, subsequent admission no longer requires a successfully completed support run.

   The first provisional reserve should require:

   - a `terminal_status="complete"` support closeout;
   - no open launch;
   - binding to that support’s authenticated surface, terminal artifacts and measured timing.

### Minor

- `git diff --check` still reports trailing whitespace in `222_s`.
- The admission docstring still says no prior support is allowed, despite the new aborted-support exception.

### Verified closed

- Full pre-admission validation ordering
- Complete versus aborted closeouts
- Successful output persistence before closeout
- Measured abort accounting
- Removal of the erroneous three-hour support ceiling
- Manifest/budget/ledger linkage
- Frozen rule and exact cohort protections

Linux verification passed: **42 focused tests** and **958 total tests under warnings-as-errors**.

These are narrow fixes to the new execution/recovery path, not grounds for another broad audit. After them, I would sign off and proceed to the Step-4 freeze.