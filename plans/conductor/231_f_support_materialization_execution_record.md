# 231_f — Support materialization EXECUTED (Step 4 complete)

The frozen 230_f launch executed 2026-07-28 through the tracked
runner with zero deviations: prepare (@fab9dc4, clean tree) →
freeze commit @c7c5513 (the allowed documentation-only commit) →
execute — pre-admission validation incl. live-environment
attestation → ADMITTED (the ledger chain's first entry) →
materialized → locked → fail-closed reload → disclosure →
comparator → probe cohort → verified outputs → COMPLETE closeout →
bound provisional reserve. Every output is development data.

## 1. Identities and accounting

- Support-launch manifest `ea4c2806…` (= the 230_f freeze);
  admitted launch entry `6506f117…` naming it, budget 1.0 GPU-h,
  `cohort_selection = outcome_blind`, design identity carried.
- **Measured cost: 0.0732 GPU-h (4.4 min)** vs the 1.0 h ceiling —
  4,824 planned steps over 108 rendered observations
  (2.44 s/observation).
- Surface lock `61c4e85a…` (v3, extends the persisted launch
  manifest; payoffs `109669f8…`); complete closeout binds the run
  record, execute-time environment, and the EXACT 17-file terminal
  inventory; `verify_terminal_outputs` passed inside the reserve
  boundary (full fail-closed surface reload + comparator
  rederivation + population cross-check).
- Provisional reserve `264066e6…` (the current ledger head),
  recorded via `record_provisional_reserve` against the verified
  run: basis = 3,000 assumed observations × 2.0 multiplier ×
  2.44 s / 3600 = 4.07 h → **R_cycle = 5.0 GPU-h**
  (ceil_to_whole_gpu_hours). Envelope: 0.0732 consumed, 59.93
  remaining.
- Committed evidence:
  `plans/conductor/evidence/routing_dev_support_v1/` (run outputs +
  execute-time environment + surface lock/manifest/declaration/
  launch manifest/payoffs, 480 KB); the ledger
  `plans/conductor/routing_dev_ledger.md` (3 entries, head
  `264066e6…` — the externally committed head for the next append);
  traces remain local under `runs/routing-dev/support-v1/`,
  hash-bound by the lock and the terminal inventory.

## 2. Disclosure — direction yields (211_f §4 step 4, ALL screened)

Per cell over 18 rendered observations each (6 latents × 3
renderers):

| cell | w2_favoured | w3_favoured | tied | no_pair |
|---|---:|---:|---:|---:|
| code_atomic | 1 | 0 | 17 | 0 |
| fork_join | 3 | 0 | 15 | 0 |
| math_code | 0 | 2 | 16 | 0 |
| lookup_atomic / lookup_math / math_atomic | 0 | 0 | 0 | 18 each |

**6 of 54 Code-pair observations are direction-bearing (4
w2-favoured, 2 w3-favoured, 48 tied)** — a MUCH sparser direction
density than the 18-obs B support (3 of 9 pairs distinct). Both
directions ARE present in the outcome-blind 6-prefix, so the frozen
first probe (`0b616b88…`: G=8, 4 groups/observation → 432 groups,
3,456 completions) can measure real grouped exposure on both — but
the probe review should expect direction-bearing groups to be rare
(≈24 of 432 groups sit on direction-bearing observations before any
within-group co-sampling thinning), and the P0 cohort design will
likely need deliberate direction enrichment (211_f §6
outcome-conditioned adaptation) beyond this natural prefix.

- `c_fixed_dev` = **worker 2** (record `plans/conductor/evidence/
  routing_dev_support_v1/c_fixed_dev.json`): equal-weight
  family-correct payoff 0.9815 (w2) vs 0.9630 (w3), no tie —
  consistent with the B-support selection, now on lock-validated
  routing_dev surfaces.
- Probe cohort bound: `7f31bd09…` — the frozen rule applied
  verbatim, 108 observation ids, bound to lock `61c4e85a…`.

## 3. Boundary

Step 4 of 211_f §15 is complete: surfaces materialized and
authenticated under the freeze, screened rows disclosed, comparator
persisted, probe cohort bound, measured timing recorded, provisional
reserve set with its full numerical basis (212_f reminder 1
satisfied mechanically — the basis derives from the closeout).
Nothing here authorizes the probe run: next per §15 is step 5, the
GPU resume-validation tranche (its lightweight freeze must state an
EXACT ceiling, 212_f reminder 2), then the probe freeze (step 6)
consuming the bound cohort above.
