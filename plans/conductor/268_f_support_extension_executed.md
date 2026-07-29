# 268_f — Unit A EXECUTED: extension surface locked; structural yield is MEASURED (and thin)

The approved rev4 ran 2026-07-29: **the complete 864-observation
six-cell prefix-0–47 surface materialized, the overlap gate against
the Step-4 lock passed (1,944 rows exact), the new lock is
accepted, and the canonical selector's yield is recorded — with
`eligible_common_cells_q3 = []`**: no cell can authorize the
bidirectional within-cell Q3 claim from this domain. That is the
dispositions discipline working as signed — recorded and scoped,
not widened.

## 1. The run (all ledger-recorded)

- Launch `68943a64…` against head `88c037a1…` (= the frozen lineage
  parent); manifest `bd8f90ca…` matched; environment attested.
- 29.7 min wall, **0.4934 GPU-h measured** (expected 0.5124; 0–5
  amortized via slw-cache hits). Complete closeout `b88eba02…` =
  the new LEDGER HEAD; chain verifies (13 entries). **Envelope:
  1.1395 consumed / 58.8605 remaining; reserve 5.0 intact.**
- Overlap gate BEFORE lock acceptance: all 1,944 original payoff +
  terminal rows reproduced exactly. New surface lock `ccb1c3e2…`;
  Step-4 lock untouched. Comparator `9220c2c7…` (frozen worker 2,
  `reselected: false`); selection `c6c08775…`.
- `verify_extension_outputs` re-derives PASS from the archive
  (in-run and again post-hoc); the evidence copy restores on a
  clean clone and loads under the new lock (864 observations).

## 2. Evidence

`plans/conductor/evidence/support_extension_v1/` (6.6 MB): run
record, selection (incl. the full 864-row public-factor
disclosure), comparator, direction disclosure, execute-time
environment, and the complete surface (payoffs, lock, manifests,
traces as byte-identical `gzip -n`). The 133 MB live root is
inventory-bound by the closeout.

## 3. MEASURED structural yield (the Unit-A outputs Unit B/C consume)

Dispositions (candidate domain 6–47; quotas ≥3 latents / ≥2
renderer strata / ≥1 non-`goal_first`):

| Bucket | Latents | Strata | Non-gf | Status |
|---|---|---|---|---|
| `code_atomic\|w2` | 0 | — | 0 | dropped_from_q3 |
| `code_atomic\|w3` | 5 | goal_first only | 0 | quota_constraints_unmet |
| `fork_join\|w2` | 3 (7, 8, 9) | bound_var + goal_first | 1 | **full_quota** |
| `fork_join\|w3` | 0 | — | 0 | dropped_from_q3 |
| `math_code\|w2` | 0 | — | 0 | dropped_from_q3 |
| `math_code\|w3` | 7 | goal_first only | 0 | quota_constraints_unmet |

- **`eligible_common_cells_q3 = []`** — the predeclared set is
  EMPTY. Under the signed disposition matrix, "bidirectional
  within-cell specialist learning" cannot be authorized from this
  candidate domain. The achievable Q3 form is at most a
  **direction-specific development result** (fork_join w2, the one
  full-quota bucket, with 22 further w2 latents in disclosed
  surplus).
- **Every w3-favoured candidate in the domain (12 latents across
  code_atomic + math_code) is `goal_first`-only** — zero
  non-`goal_first` w3 coverage anywhere. The renderer confound
  flagged in 253_s/257_s is now MEASURED, not suspected: any
  w3-direction training row is renderer-predictable.
- **One renderer reversal** (diagnostic, not bidirectional
  evidence): fork_join latent 42 — w2 under goal_first, w3 under
  bound_var; consumed by the w2 bucket per the frozen order.
- **Legacy disclosure** (Anchor material, never candidates):
  code_atomic w2 [5]; fork_join w2 [1, 5]; math_code w3 [2, 3].
- **Subtype association (the honest-claim control has real
  work):** code_atomic w3-favoured occurs ONLY under subtype
  `count` (5/5; the sole legacy w2 was `select`); fork_join
  w2-favoured is predominantly `code_first` (23 vs 6
  `lookup_first`); math_code w3 all under its single subtype. The
  `cell+renderer+subtype` control in the Unit-C analysis will
  determine how much of any learned behaviour is task-subtype
  routing (still orchestration, but the claim language must say
  so — 258_f gate 3).

## 4. Implications for the Unit-B freeze (recorded, not decided here)

Per the signed design the yield SCOPES the objectives; the Unit-B
freeze (separately reviewed) draws the consequences. What the
numbers permit: Q1 (bridge rows abundant — 387 tied Code-bearing
observations incl. 48/66 splits by subtype in fork_join); Q2
(unlocking: 7 w3-favoured math_code composite latents exist, all
goal_first); Q3 at most direction-specific (fork_join w2). What
they do not permit: the bidirectional within-cell claim (empty
common-cell set) and any renderer-deconfounded w3 claim (zero
non-goal_first w3 coverage). If the reviewer prefers widening the
candidate domain rather than scoping down, that is a NEW
outcome-informed extension with its own freeze — this run's
selection is immutable.

## 5. Next

Reviewer pass on this execution record and the selection/
disposition yield → Unit-B mixture freeze on the extension surface
(scoped per §4, binding the public-factor disclosure) → pre-C
invalidation audit → Unit C.
