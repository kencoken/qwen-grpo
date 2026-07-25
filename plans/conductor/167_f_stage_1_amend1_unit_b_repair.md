# 167_f — Unit-B repair (response to 166_s)

All four findings are implemented. Full CPU suite: **790 passed**
under `-W error` (36 Unit-B tests). No frozen grid ran; the reissued
disclosed probes used throwaway inputs only.

**1. C consumes its frozen seed registry.** `run_c_path` now takes
the REGISTERED path seed, seeds ONE `PCG64`, and draws all trials
sequentially from that stream (reproducibility of the same
seed+trial-count pinned by test); the unregistered `path_key|trial`
derivation is gone. The new formal runner `run_amended_c` requires the
FINALIZED registry, verifies each path's registered seed against the
frozen derivation, enforces the exact 48-key set, and applies the
30-minute §5.4 deadline. The throwaway timing probe derives its seeds
in a separate helper under the explicit throwaway domain and never
touches registered material.

**2. Structural eligibility is design-declared.** `look_decision` and
`evaluate_path` take an explicit `structural` flag; the sharper zero
bound is used ONLY when declared. Observed data contradicting a
structural declaration is an infrastructure error (tested); observed
all-full data WITHOUT the declaration uses the split-alpha variable
bound (tested: the undeclared bound is strictly looser). The C runner
sets `structural = (eligibility == 1.0)` — the registered design, not
the data.

**3. Independent inversion reference + the frozen tolerance rule in
the scan.** `scalar_reference_inversion` is a row-level
implementation sharing no code with the optimized path (two-pass
statistics per candidate r, the same grid∪{p̂} verification, the same
80-iteration outward bisection). `reference_agreement_probe` now
compares `(L_p, U_p)` at `rtol = 0, atol = 1e-12` alongside the bound
endpoints and the complete trichotomy: reissued over 119 fixed
throwaway positive-branch cases — 119/119 decisions bit-identical,
119/119 inversions within tolerance. `_membership` now applies the
64-eps refuse-vs-clamp rule instead of unconditional clamping — with
one measured, disclosed refinement: near r ≈ p̂ the variance is a
near-total cancellation of intermediates of order `S_J2 / 2rS_JK /
r²S_K2`, so the scan's tolerance magnitude set includes those summed
intermediates (measured on exact-zero-variance data: residuals
≈ 2×10⁻¹⁴ against a result-scale tolerance of 1.4×10⁻¹⁴ — the
result-scale set would refuse valid degenerate inputs). The r = 0.10
GATE keeps the §4.5 scalar rule verbatim (no cancellation arises
there). The scan-variant magnitude set is flagged for freezing as an
implementation literal in the Unit-D final successor.

**4. The complete §4.6 report exists and is assigned.**
`qualification_look_report` is the production reporting API: it takes
RENDERER-LEVEL `(N × m)` 0/1 eligibility/persistence matrices
(validated: 0/1, J ≤ K elementwise, renderer rows travel with their
cluster), produces the frozen decision record, and adds the §4.6
values the compact C/D counting rows omit — the equal-cluster
descriptive rate (the frozen secondary quantity, never replacing
p̂), per-renderer J/K under the authoritative renderer ids (sums
cross-checked against cluster totals by test) — plus the explicit
binding: `student_t_impl`, SciPy and NumPy versions,
`inversion_rule = grid1001-plus-phat-bisect80-outer-v1`, and the
bisection iteration count. Compact C/D artifacts are unchanged, as
permitted; qualification and D6–D8 records consume this API.

Reissued probes: reference agreement 119/119 (decisions, bounds, and
inversions); full-C timing projection ≈ 1.5 minutes against the
30-minute budget.

Proceeding to Unit C.
