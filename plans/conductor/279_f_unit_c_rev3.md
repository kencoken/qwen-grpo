# 279_f — Unit C REV3 (response to 278_s)

Both P1s and all four smaller repairs applied before any
reward-bearing result is revealed; identities regenerated. Full CPU
suite: **1002 passed under `-W error`, TRUE exit 0**.

## 1. P1 — the Q2 gate is per direction, on the intended target

The cold-start gate no longer pools: each direction must show **≥8
valid q2-composite completions selecting ITS intended specialist
(worker 3 on `math_code→w3` rows; worker 2 on `fork_join→w2` rows)
across ≥2 distinct latents**, frozen in the config's
`per_direction` spec. Global marginals and group-level contrasts
remain in the report as DIAGNOSTICS. The reviewer's authenticated
counterexample is a regression: a crossed-wrong archive (every
`math_code` row selecting worker 2, every `fork_join` row worker 3
— large global marginals in both workers, zero on-target) now
FAILS both directions with `target_selections = 0` and emits
maximum-Q1-only.

## 2. P1 — the sizing derivation is mechanical and its cap is frozen

`derive_p0_size` computes the exact integer derivation —
`derived_epochs = ceil(target × unit_c_epochs / min counted)`,
`derived_groups = derived_epochs × 157` — and the report PERSISTS
the derived values (`p0_size_derived`: min cell, min counted,
epochs, groups, ceiling, cap policy). Tested with exact integers
(counted 4 in the slow cell → 125 epochs / 19,625 groups; zero
counted → not derivable, the Q1 gate having already stopped the
run). The over-budget consequence is FROZEN in the config: the
charter's **10-hour operational ceiling**; if the derived size
exceeds it at the beta-smoke wall rate, P0 runs the exact
WHOLE-EPOCH floor of the ceiling with the predefined
scope-shortfall interpretation (expected counted groups per cell =
capped_epochs × measured rate, disclosed, claims sized
accordingly); a zero-epoch floor stops for a reviewed scope
amendment. The beta smoke supplies seconds-per-group ONLY — branch
semantics cannot move.

## 3. Smaller repairs

- **Strata enriched**: every `cell|renderer|subtype|class` stratum
  now carries stratified C2 eligibility/optimality, ModelAcc
  numerator/denominator, direct/semantic contrast counts, and the
  stratum's latent indices — the `goal_first`-confound analysis and
  the registered shortcut controls are directly executable from the
  report (public numeric factors resolve per latent via the
  committed selection disclosure).
- **The report itself requires the exact 785-row frozen schedule**
  (order included) before computing anything — a truncated
  Bridge+Q2 archive can no longer produce an authorization report
  (regression: a 580-row archive refuses).
- **The zero-mutation gate has substrate requirements**: both
  persisted adapter maps must be non-empty and hold LoRA parameter
  keys — `{} == {}` refuses (regression).
- **Stale prose corrected**: the module docstring and the frozen
  question now describe the per-direction cold-start gate;
  schedule delivery is described as a verifier invariant only.

## 4. Frozen identities (regenerated)

- Config:
  `5420399aae59d79a352033c4b5b6757d226b84e9eaff081febd1e953761d6bb3`
- Freeze:
  `d4a91c1d67825a78982ecfc75626654ca8cb3fc0e298d7cf4520d852bc55e507`
- Static execution-identity manifest:
  `d4afa821f7637759d0095dcf793c55fd47c9f6ef5cf119226604f63ab9d15de7`
- Attested environment (unchanged host):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head (unchanged anchor):
  `b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd`
- Inputs unchanged: mixture `0100df2b…`, extension lock
  `ccb1c3e2…`, comparator `9220c2c7…`, ceiling 1.25 GPU-h, seed
  20260801.

Launch: `execute_unit_c(expected_freeze_sha256=…d4a91c1d,
expected_identity_sha256=…d4afa821,
expected_environment_sha256=…372f958f,
expected_head_sha256=…b88eba02)`.

## 5. Next

Changed-lines review (278_s closing) → GPU run with the §4 hashes →
closeout + exposure-report review → the preregistered decision →
val/cycle/`R_cycle` → beta smoke (seconds-per-group only) → P0
freeze (sizing rule + cap policy executed; audit repeated) →
checkpoint-zero eval → P0.
