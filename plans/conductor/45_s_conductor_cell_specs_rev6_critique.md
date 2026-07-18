Rev6 correctly incorporates the previous feedback, but I would make four small exactness fixes before freezing it. The experimental design itself is ready; these are implementation-contract issues.

1. Complete the profile validator at [§1.14](/Users/ken/conductor_cell_specs_rev6.md:703):

   - Require `1 ≤ F_band.min ≤ F_band.max ≤ 10`; currently only the maximum is constrained. With `F=0`, target-field sampling is undefined.
   - State the ordinary invariant `band.min ≤ band.max`.
   - Explicitly require `code_atomic.value_band.min ≥ 1`, because `select` returns a band value directly.
   - Public artifact literals must be at most `999,999,999,999`, not merely nonnegative, because the grammar has a 12-digit limit.
   - Freeze either analytic profile bounds or a named pre-admission rejection ensuring every emitted reference execution stays within `|v| ≤ 10¹²`. Otherwise a tuned profile can store a valid-looking gold whose correct artifact deterministically produces `E_MAGNITUDE`.

2. Guarantee Lookup→Math intervention support at [line 1104](/Users/ken/conductor_cell_specs_rev6.md:1104). For minus tasks, `p≥2` and `q≥1` are insufficient. For example, with `value_band={1,2,3}`, `p=2`, `q=5`, the valid base value can be `n1=3`, but neither alternative produces a positive counterfactual.

   Define:

   ```text
   S⁻(p,q) = {x in value_band : p*x − q ≥ 1}
   ```

   Require `|S⁻(p,q)| ≥ 2` for every admitted `(p,q)`, then draw directly from `S⁻(p,q) \ {n1}`. This is clearer and safer than unbounded rejection-resampling.

3. Disambiguate “latent subtype.” The new statement at [line 584](/Users/ken/conductor_cell_specs_rev6.md:584) says calibration uses the full latent subtype, but the [qualification list](/Users/ken/conductor_cell_specs_rev6.md:780) omits `target_stratum` and includes renderer. Renderer is fully crossed, not a scheduler factor; treating it as subtype also makes the renderer-within-subtype leakage test degenerate.

   Define:

   ```text
   full_latent_stratum = joint categorical-factor assignment in the
   scheduler table, including target_stratum where applicable
   ```

   Rejection caps and leakage audits use that stratum. Qualification reports latent-stratum and renderer marginals separately.

4. Restore `expansion batch size` in the per-namespace declaration at [§1.13](/Users/ken/conductor_cell_specs_rev6.md:662). Rev5 froze maximum count, index order, expansion batch size, and stopping rule; the wording rewrite accidentally dropped the third item.

One useful non-blocking test is that a construction-inviable profile—such as a modulus-only domain whose candidates all fail the exclusion rules—reaches the resampling cap and returns a clean profile-screen failure, never an infrastructure exception.

After these patches, I would sign off Phase 1 on a targeted diff; no further scientific or cell-design review is needed.