# 165_f — Amend-once Unit B: the persistence statistic and C runner

Unit B of 158_s §10. CPU-only; **no frozen grid ran** — the only
executions were the two disclosed §5.4 probes (throwaway seeds,
statistical outputs discarded). Full CPU suite: **785 passed** under
`-W error` (31 new Unit-B tests covering the complete §5.2 required
list).

## 1. The amended statistic (`tasks/conductor/stage1_persistence.py`)

- **§4.5 positive branch**: integer sufficient statistics
  `(N, S_J, S_K, S_J², S_K², S_JK)`; the frozen float64 evaluation
  order for `S_D`, `S_D2`, `V_D`; the frozen tolerance clamp
  (`64·eps64·max(1,·,·)`, clamp only within `[-tol, 0)`, more negative
  or non-finite = infrastructure error); `s_D = 0` valid
  (`G_L = G_U = D̄`); Student-t at `df = N−1` via the frozen
  `scipy.stats.t.ppf`; the fail-closed Fieller denominator check
  (`denominator_L ≤ 0` → interval `[0,1]`, unresolved).
- **§4.4 zero branch**: trigger EXACTLY `J == 0`; structural
  full-eligibility simplification at the full `a_zero`; variable
  eligibility at `a_zero/2` with the Hoeffding floor; `L_Q ≤ 0` →
  unresolved; observed `K = 0` → unresolved (§4.1). Never a fail from
  `J = 0`.
- **§4.6 gate rule** with the complete per-branch serialization
  records (Unit-A frozen field sets; bounds as string decimals;
  decisions re-derivable).
- **§4.5 inversion**: membership `G_L(r) ≤ 0 ≤ G_U(r)` inverted over
  `[0,1]`; deterministic single-interval verification on the fixed
  1,001-point grid **augmented with p̂** — a genuine edge case our own
  tests caught: a perfectly homogeneous sample has `s_D(r) = 0` for
  every r, collapsing C to the single point `{p̂}` which a fixed grid
  misses; since `s_D = 0` is explicitly valid, the frozen rule is
  grid ∪ {p̂}, one contiguous run containing p̂, refuse otherwise.
  Outward bracket/bisection, exactly 80 float64 iterations, inclusive
  membership, conservative OUTER-bracket endpoints, 0/1 at reached
  boundaries.

## 2. Generators, runner, acceptance, artifacts

- **Prefix-valid coupled-path generators** for both frozen joint
  distributions: independently randomized incremental blocks meeting
  every cumulative eligibility target EXACTLY (cluster-correlated:
  `round(e·N_look)` full-eligibility clusters nested by look;
  row-dispersed: `round(e·m·N_look)` rows spread evenly with
  randomized remainders) — never a cap arrangement hoped to land on
  the floor, never independent looks.
- **`run_c_path`/`evaluate_path`**: §4.6 applied in look order; first
  terminal decision stops the operational path (early fail stops;
  unresolved at cap = non-pass); marginal decisions and
  zero/positive/denominator-unresolved branch counts recorded at every
  look from the same coupled prefixes. C-path counting skips the
  reporting inversion (decisions need only `(G_L, G_U)`); records that
  persist (qualification, D6–D8) compute it.
- **§5.3 hard-path acceptance evaluator** over the four hard cells
  (both distributions × both schedules at the floors): θ=0 must
  first-pass every trial; θ=0.05 Wilson LB ≥ 0.80 on first-pass-by-
  cap; θ=0.10 rows are non-gating disclosures.
- **Artifacts**: `build_c_artifact`/`load_amended_c_artifact` under
  the amend1 tag with the EXACT 48-path and 120-marginal key sets
  enforced at build and load (the 163_s closing requirement); the
  amended row schemas flow through the tranche loader via a
  `row_schema` override; a v1-tagged artifact refuses the amended
  loader.

## 3. §5.2 deterministic test list — all eleven

Support/point-estimand validation; branch trigger + alpha arithmetic
(`a_zero = a_ratio = a/2`, per schedule); the zero branch exactly at
θ=0 (structural and variable, against closed forms); cluster
permutation invariance; renderer rows travelling with their cluster
(moving one row between clusters changes `s_D` at equal J, K);
zero-eligible clusters retained in N; every maximum-cap draw meeting
every prefix target (both distributions × both schedules × all four
eligibilities); early pass/fail and cap-unresolved stopping on coupled
prefixes (deterministic early-pass at look 100 for structural θ=0;
deterministic early-fail; marginals at every look regardless);
sufficient statistics matching row-level computation; score decision
agreeing with the inverted interval at r = 0.10 (plus the degenerate
collapse case); and exact-key-set refusal for missing, duplicated, or
out-of-grid paths and marginals.

## 4. Disclosed §5.4 probes (items 1–2)

- **Reference agreement**: 200 fixed throwaway cases (N ∈ [10, 500),
  mixed schedules) — the optimized sufficient-statistic path and the
  plain-Python row-level reference agreed bit-for-bit on every
  trichotomy decision and within `atol = 1e-12, rtol = 0` on
  `(G_L, G_U, denominator_L)`. Zero disagreements.
- **Timing projection** (throwaway domain `throwaway-timing-v1`, no
  frozen prefix revealed, outputs discarded): ≈ 0.21 ms per path
  trial on the worst-shaped paths ⇒ the complete 48-path × 10,000
  registry projects to **≈ 1.7 minutes**, against the 30-minute §5.4
  abort budget. There is no inner bootstrap in C; the margin is ~18×.

## 5. Boundary

Deferred to Unit C: the D runner amendments (10,000 inner for D1–D5,
agreement-path removal, the D2 `(100,500)` literal, the reissued
D6–D8 exercising this statistic), the B C2/C1 decision matrix, and the
aggregate. Deferred to Unit D: the changed-lines review, the final
placeholder-free successor (which freezes the implementation literals
of §1: the augmented-grid rule, SciPy version, bisection/endpoint
conventions), and the separate lock. The full C benchmark and the
remaining §5.4 items (3–5) run at Unit D's pre-lock probe.
