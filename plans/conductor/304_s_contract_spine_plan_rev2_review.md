## Verdict

Rev2 closes the main architectural findings and is appropriately smaller. I would issue one narrow Rev3 before signing; no further broad redesign is needed.

The document-only commit is mechanically clean. Five precise clarifications remain because they can affect authentication, denominators, sentinel interpretation, or run length.

### 1. Make the identity dependency graph explicit

`P0LaunchFreeze` currently includes “runtime/seed/environment identities,” which could reintroduce a hash cycle if this means the execution-manifest or commit-dependent environment-manifest hash.

Freeze this order:

```text
authenticated inputs + C2 oracle
    → P0ScienceContract
    → P0LaunchFreeze
    → P0ExecutionIdentity / launch admission
    → closeout
```

The launch freeze may contain intrinsic runtime/model/prompt/worker fields, seed, and a commit-independent attested-environment expectation. The execution-manifest hash must remain an external launch argument; full environment and terminal hashes belong in admission/closeout.

### 2. Authenticate the complete C2 replay source

Section 3 needs more than trace + surface + comparator. Exact populations and strata also require the authenticated selection/disclosure and pinned mixture.

Unit 1 should require:

- verified ledger chain containing closeout `2bf50c1e…`;
- its complete terminal inventory, including actions `8e705317…`, report `03152f0e…`, schedule `c2687919…`, and sample record `cc42c16…`;
- reviewed identity/environment anchors;
- locked extension surface;
- frozen selection/public disclosure;
- frozen comparator;
- the newly materialized mixture artifact.

Verify the closeout inventory before replay. Include a clean-clone surface-restoration path rather than depending on an earlier test having populated `runs/`.

Also freeze the expected compatibility projection before implementing the new evaluator. The evaluator must not call `unit_c2_sample.build_exposure_report` or read the expected report; it should reparse completion text and independently rederive assignments/rewards from the locked surface.

### 3. Machine-encode the operative estimands

“Definitions by reference” and function names are insufficient. Add versioned rules and typed parameters for:

**Q1**

- Population: Bridge rows in the three direct-Q1 cells.
- Counted event: within one group, at least one valid reward-1.0 fully family-correct completion and at least one valid reward-0.5 completion with strictly lower family correctness.
- Historical gate: ≥2 counted groups from ≥2 latents per cell.
- Sizing basis: authenticated 13/34/13 counts over five C2 epochs.

Add a counterexample where generic semantic contrast is true but Q1-counted is false.

**Q2**

- Marginal authorization remains intended-worker selection among valid Q2 completions, regardless of upstream correctness.
- Eligibility requires correct non-Code routing and a Code worker in `{2,3}`.
- Conditional learning estimand:

```text
numerator   = C2-optimal completions
denominator = C2-eligible completions
```

Represent a zero denominator as undefined/`None`, never zero performance. The C2 baseline should reproduce fork `8/152` and math→code `0/15`, separately from marginal selections `73` and `108`.

A semantic counterexample should show that intended-worker selection with incorrect upstream routing counts for marginal support but not conditional success.

Use `p0_estimands.py` rather than the broader `estimands.py` name.

### 4. Restore the complete sentinel contract

Section 6 currently mentions only first occurrences. The signed requirement covers, at every P0 checkpoint/evaluation:

- worker-1 selections and completions;
- reward-1 completions;
- reward-varying groups;
- sentinel Q1-counted groups;
- raw group/completion denominators;
- the signed first group/update fields;
- checkpoint and evaluation trajectories.

Bind the exact three-observation sentinel population. Retain the regression that `[2]` or `[3]` is not Math unlocking merely because it differs from `[0]`.

### 5. Freeze nominal versus capacity epochs

State the launch calculation before observing beta timing:

```text
nominal_epochs  = 39
capacity_epochs = frozen_cap_formula(...)
launch_epochs   = min(nominal_epochs, capacity_epochs)
```

- `capacity_epochs <= 0`: stop for review.
- `0 < capacity_epochs < 39`: disclosed under-target branch.
- `capacity_epochs >= 39`: run 39; spare capacity does not authorize extra training.

Persist every cap input and all three values.

## Disposition

Everything else is satisfactorily closed: forward-only migration, legacy preservation, pinned schedule loading, deep immutability, external authentication, Q3 exclusion, removal of the generic rate engine, exact C2 parity coverage, source-digest handling, and moderated documentation claims.

After a short Rev3 containing these clauses, a narrow changed-lines review should be enough for signoff and Unit 1.