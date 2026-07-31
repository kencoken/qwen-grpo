# 274_f — Unit B REV3 (response to 273_s)

The gate-calculation defect repaired, the renderer-representation
decision made EXPLICITLY, the wording tightened with the disclosed
numbers, and the freeze guard mirrored. Identities regenerated.
Full CPU suite: **999 passed under `-W error`, TRUE exit 0**.

## 1. Blocking — the statistic now IS the frozen criterion

`_block_occupancy_at_least` computes the latent-block occupancy
probability — ≥2 counted groups from ≥2 DISTINCT latents means ≥2
occupied latent blocks (each block = one bridge latent's
3-renderer × 5-epoch = 15 IID group draws). The build-time refusal
enforces the UNROUNDED value, the block model is cross-checked
against the schedule (draws == latents × renderer crossing ×
epochs, refusing on mismatch), and the exact figures are asserted
in tests with an independent in-test recomputation:

| Cell | Rev2 (wrong statistic) | Rev3 (≥2-latent occupancy) |
|---|---:|---:|
| code_atomic | 1.0000 | 1.0000 |
| fork_join | 0.9928 | **0.9826** |
| math_atomic | 0.9227 | **0.9085** |
| math_code | 0.9227 | **0.9085** |

All remain above the frozen 0.9 — the disposition stands, and the
number now measures the stated gate (matching the reviewer's
figures exactly).

## 2. Blocking decision — renderer representation EXPLICITLY superseded

Taken as an explicit supersession recorded in the frozen criterion
itself (never an implicit disappearance), with the rationale in the
config text: the ≥2-renderer-strata requirement was
Q3-deconfounding machinery; the Q1 estimand (family routing) is
renderer-independent; every bridge latent enters with the COMPLETE
renderer crossing (structural equal-draw balance); and
renderer-stratified reporting is retained per 269_s §5, so a
persistently silent stratum is reportable evidence rather than a
gate failure. Gating on per-renderer counted events would force
either a budget breach (6 epochs exceeds the 1.0 GPU-h ceiling —
see also §5) or Bridge over-weighting against 269_s §6. The
expected ≥2-strata occupancy is DISCLOSED per cell in the
projections (math cells ≈0.8499, fork_join 0.9747, code_atomic
1.0) — the reviewer's figures reproduced.

## 3. Wording — bounded imbalance, with the numbers

"Cannot reward a constant-worker policy" is corrected everywhere to
BOUNDED imbalance with the fixed-worker payoffs computed from the
composite rows and disclosed in the record:
`always_w2 = 0.78125`, `always_w3 = 0.71875` (the 18:14 rows leave
always-w2 a bounded 0.0625 edge — limited, not eliminated). The
Q2-COMPOSITE-ONLY `goal_first` conditional is now reported
alongside the other two: **exactly 0.5** (14:14, direct-specialist
controls excluded), vs 0.576 (all payoff-distinct gf rows) and
0.224 (diluted).

## 4. Smaller — the freeze mirrors the guard

`tranche_freeze()` refuses on a mutated live config exactly as
`build_mixture` does (regression added): a noncanonical self-hashed
freeze can no longer be produced after mutation.

## 5. Unit-C caution carried forward

The reviewer's runtime note is recorded for the Unit-C freeze: 785
groups project to ≈0.944 GPU-h — only ≈3.4 minutes under the 1.0
ceiling. The Unit-C freeze must use a conservative runtime bound
(its own decision; options include a slightly higher ceiling
admitted against the envelope or a per-group deadline with
margin — to be settled there, not here).

## 6. Frozen identities (regenerated)

- Config:
  `92f933e84d6c1c83f258437da30e352a79da7c3e01df87d3ffdf9f7ddc386bf8`
- Freeze:
  `182d278966741633285e8cb2313e3b29aeef84f1036adfe05bec2e249a5b9f1d`
- Mixture record:
  `0100df2bbb13447aa394d31ab87eb0dab1e0660e830186eee99028e30432bc01`
- Inputs unchanged: extension lock `ccb1c3e2…`; selection
  `c6c08775…`; probe report `3a001c99…`; probe trace `44172e55…`;
  lineage parent `b88eba02…`. Schedule unchanged from rev2
  (157 rows/epoch; the repairs changed the statistic, the
  disclosures, and the guard — not the schedule).

## 7. Next

Sign-off → pre-Unit-C code-invalidation audit → Unit-C freeze
(gates = the frozen criterion with the block-occupancy statistic;
validates mixture record `0100df2b…` at 5 epochs; conservative
runtime bound per §5) → Unit-C run → preregistered decision →
val/cycle/`R_cycle` → beta smoke → P0 freeze → checkpoint-zero
eval → P0.
