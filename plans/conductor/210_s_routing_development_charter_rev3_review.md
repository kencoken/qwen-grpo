## Verdict

209_f closes almost all 208_s findings correctly, and the companion evidence itself is sound. I verified:

- all four bundled files match their recorded sizes and SHA-256 hashes;
- the companion self-hash reproduces;
- archive bindings match;
- the fail-closed loader reconstructs all 324 payoffs with `{0.5: 300, 1.0: 24}`;
- `git diff --check` is clean.

I would make one final targeted erratum before sign-off. Five narrow issues remain.

### 1. `c_fixed` does not exist

Section 7 invokes the “existing” construction-selected best-fixed-Code comparator for `ScaleLift`. Formal construction never ran, so no persisted `c_fixed` artifact exists in the repository.

Define a development comparator before the probe, for example:

- `c_fixed_dev ∈ {2,3}`;
- selected on the outcome-blind §4 support;
- maximize equal-weight family-correct terminal payoff across cells, latents, renderers and Code positions;
- tie to worker 2;
- persist both candidate scores, selection rule, source surface hashes and result.

C2 “optimal specialist” should mean the per-observation payoff winner, with ties reported separately. `ScaleLift` should use `c_fixed_dev`. Both remain development-only quantities.

### 2. The probe may not describe an enriched P0 cohort

The first probe uses an outcome-blind prefix, while P0 may subsequently select a direction-enriched cohort. B already showed large row/renderer variation, so probe rates cannot automatically be transported to unseen selected rows.

At the P0 boundary require either:

- projections only from probe-measured strata, with an explicit reweighting/transport rule; or preferably
- a small locally frozen zero-update exposure sample on the exact final P0 cohort and mixture.

Extend the existing group-size reprobe rule to material cohort/mixture changes.

### 3. Two authorization/order errors remain

The header authorizes “exactly three things,” but the required GPU resume-validation run is a separate locally frozen GPU tranche before the probe. Add it as a fourth authorization, or explicitly define it as an authorized infrastructure-acceptance subtranche with its own freeze and budget.

Also, §15 currently runs checkpoint-zero evaluation before freezing P0. Reverse that:

1. Freeze/materialize/lock `routing_dev_val`.
2. Freeze the complete P0 launch binding that lock and its evaluation configuration.
3. Run checkpoint zero as P0’s first execution.
4. Begin training without configuration changes.

Otherwise P0 is selected after observing its own baseline.

### 4. `R_cycle` needs corrected timing and scope

Support timing cannot finalize `R_cycle` until the exact cycle cohort size and evaluation rule are known. Either freeze those before sizing the reserve or maintain a conservative provisional reserve until they are frozen.

The admission formula should apply to ordinary pre-closure launches:

`remaining ≥ launch maximum + R_cycle`

When cycle closure begins, it must be allowed to consume the reserved `R_cycle`; otherwise the current wording double-counts the reserve and effectively requires about twice the closure budget.

### 5. Companion restore instructions are incomplete

The instructions restore only `runs/stage0-support`. On a clean checkout, the stated report command still fails because it expects the committed success archive under `runs/stage1-b-diagnostic/`.

Add instructions to copy the five files from:

`plans/conductor/evidence/stage1_b_diagnostic_973e8adc316e/`

into:

`runs/stage1-b-diagnostic/`

After doing that manually, the full verifier regenerates the committed report byte-identically. This is documentation-only; no evidence regeneration or B rerun is needed.

Once these items are corrected, I would sign the charter. No further broad design review should be necessary.