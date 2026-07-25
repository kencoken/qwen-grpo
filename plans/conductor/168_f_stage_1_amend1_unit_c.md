# 168_f — Amend-once Unit C: D, the aggregate, and the B matrix

Unit C of 158_s §10. CPU-only; no frozen scenario ran (the only
execution was the disclosed §5.4 item-3 timing probe on throwaway
seeds). Full CPU suite: **782 passed** under `-W error`. All four §10
outcome paths are named tests.

## 1. The reduced-replicate implementation is gone (§6)

`run_agreement_gate`, `agreement_passes`, the agreement dataset
families, `_BOOTSTRAP_SCENARIOS`, and `COVERAGE_INNER_REPLICATES` are
DELETED from the codebase (asserted by test; the v1 machinery lives in
the archived worktree at `da8424b`). Every bootstrap-based D scenario
now uses `COVERAGE_PRODUCTION_REPLICATES = 10,000` — the only inner
count. The deterministic equivalence set remains the entry gate,
unchanged.

## 2. The amended D registry

- **D1–D5**: unchanged DGP meanings and v1 per-trial seeds (never
  exposed), at 10,000 inner; **D2 uses the amended fork looks
  (100, 500)** read from the single schedule source.
- **D6–D8 reissued per the §6 table**, exercising the Unit-B
  statistic end-to-end: one maximum-length prefix-valid vector per
  outer trial; every registered look evaluated with the amended
  interval (inversion included); error = UNDERCOVERAGE — the reported
  upper endpoint (`zero_U`, or `pos_U_p`, or 1 on a
  denominator-unresolved look) strictly below the true θ at any look;
  `U_p == θ` covers at the non-strict boundary. D6: structural
  cluster-correlated θ=0.10; D7: row-dispersed e=0.65 θ=0.10; D8:
  fork cluster-correlated e=0.60 θ=0.01 with the both-branches-at-
  each-look support rule (`d8_branch_support_ok`; per-look
  zero/positive/denominator-unresolved counts persisted as `D_branch`
  rows in the artifact and schema-validated). Ceilings: Wilson UB ≤
  0.0625 for D6–D8; D1–D5 keep their inherited scenario ceilings.

## 3. The amended aggregate and the §7 B matrix

`aggregate_amend1_verdict(A, C, D, B_evidence; env, bundle,
registry)`: validates the execution BUNDLE against the finalized
registry and requires every artifact — including B, via a new
explicit `execution_identity` parameter on `verify_replay_evidence` —
to bind the bundle's self-hash (158_s §9.1; the env manifest is still
fully validated and bound inside the bundle). A keeps its v1
acceptance criteria under fresh seeds; C is judged by the §5.3
hard-path evaluator over the exact 48/120 artifact; D by the ceilings
plus D8 branch support. **B never blocks confirmation globally**: the
§7 matrix is implemented in the decision table —

| verified B statuses | decision |
|---|---|
| both `not_ruled_out` | `confirm_c2_provisional` |
| any `not_demonstrated` or `unknown` | `confirm_c1_only`, `C2_preCE1_available = false` |
| malformed / unreproducible / foreign identity | raises (infrastructure abort) |
| any A/C/D scientific failure | `scientific_stop` (no second amendment) |

All four §12 outcome paths are tested: confirm-C2-provisional,
C1-only on `not_demonstrated` (verified continuing, not blocking),
scientific stop (C hard-path failure; total D failure; D8
branch-support failure), and infrastructure abort (tampered raw
completions; wrong finalized registry).

## 4. The amended runner (§11)

`run_amend1_tranche(bundle, seed_registry)`: v1 evidence archive
verification (entry gate) → bundle/registry/environment validation
(bundle must bind the current environment manifest) → atomic claim of
`runs/stage1-validation-amend1/` → deterministic equivalence set →
the full-count worst-case benchmark with the frozen budgets (A ≤ 30
min; C ≤ 30 min inside `run_amended_c`; per-D1–D5 in-loop deadlines
at 4× the measured per-outer literal; D6–D8 combined ≤ 30 min; total
≤ 12 h) → fresh-seed A (registered seeds via the new
`seed_override`) → amended C through `run_amended_c` → all eight D
scenarios with per-scenario wall times (recorded in a `finally`) →
amend1-tagged artifacts, staged persistence, and aborted-run records
throughout.

## 5. Disclosed §5.4 item-3 benchmark (throwaway, outputs discarded)

The ACTUAL worst-case D path at 10,000 inner replicates:
**0.944 s per outer trial** (consistent with the 145_s-era 0.187 s at
2,000 × 5). D1 projects to ≈ 79 minutes; the frozen 4× deadline
literal at this measurement would be ≈ 18,885 s; rough D1–D5 total
≈ 2.2 h; with D6–D8 (< 30 min gate), A (≈ 0.2 min) and C (≈ 1.5 min)
the complete amended CPU tranche projects to **≈ 2.5–3 h** against
the 12-hour gate. The binding per-outer literal is persisted by the
actual pre-lock benchmark at Unit D and copied verbatim into the
final successor/lock.

## 6. Boundary

Unit D remains: the changed-lines review, the final placeholder-free
successor (freezing the implementation literals flagged in 165_f/
167_f — the augmented-grid inversion rule, the scan-variant tolerance
magnitude set, SciPy/NumPy versions, the measured deadline literal —
plus the complete §5.4 probe suite run pre-lock), and the separate
lock record. Nothing statistical runs before that lock.
