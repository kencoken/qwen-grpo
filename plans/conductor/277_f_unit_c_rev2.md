# 277_f — Unit C REV2 (response to 276_s)

All three preregistration/reporting repairs applied before any
reward-bearing result is revealed; identities regenerated. Full CPU
suite: **1002 passed under `-W error`, TRUE exit 0**.

## 1. B1 — Q2 statistics on the q2_composite population only

The report now carries **per-direction Q2 blocks** computed over
q2_composite rows ONLY: draws, distinct latents, valid completions,
C2 eligibility AND optimality, ModelAcc numerator/denominator,
code-node worker selections (2/3/other), reward sums, and
direct/semantic contrast counts — `math_code→w3` and
`fork_join→w2` separately. The direct-specialist control is its own
block, excluded as required. The reviewer's reproduction is a
regression: an archive whose bridge rows carry specialist-selecting
family-correct completions while the q2 population has zero
eligibility now reports **q2 eligibility = 0** (bridge exposure
visible only in its own strata) — the population inversion cannot
recur.

## 2. B2 — Q2 authorized by a measurable gate (option a, chosen explicitly)

Schedule delivery is demoted to a VERIFIER INVARIANT (the report
raises on mismatch; it never authorizes). Q2 authorization now
comes from a frozen, MEASURABLE cold-start marginal-support gate:
**≥8 valid q2-composite completions selecting EACH specialist (w2
and w3) at the Code node** — echoing the signed "nonzero marginals
for both specialists" requirement at a scale the composite draws
make meaningful (1,280 completions). This gate CAN fail on a
completed run, so the signed Q2-fail → **maximum-Q1-only** branch
is reachable (and regression-tested: the uniform-worker archive
fails the gate and emits exactly that decision). Ckpt-0
C2-eligibility remains a REPORTED starting condition — zero
permitted, never a direct-C2-exposure claim.

## 3. B3 — the registered strata and the frozen sizing mapping

- **Strata with raw denominators**: every scheduled draw enters a
  `cell|renderer|subtype|class` stratum carrying draws, valid
  completions, zero-variance groups, Q1-counted groups (bridge),
  code-worker selections, and reward sums — the registered
  cell+renderer+subtype public-feature shortcut control, and the
  274_f supersession's reporting obligation, with denominators.
  Q2 metrics stratify by direction (the blocks) and appear in the
  strata by renderer/subtype; anchor coverage is a per-cell
  stability block (draws, rewards, zero-variance).
- **The deterministic sizing rule is FROZEN in the config** (no
  later free choice): P0 epochs =
  `ceil(100 / min over critical cells of measured Q1-counted groups
  per epoch)`; groups = epochs × 157; wall-rate from the beta=1e-3
  timing smoke; envelope admissibility checked at the P0 freeze
  with any budget cap DISCLOSED as a scope shortfall, never
  silently absorbed. The report carries
  `q1_counted_per_epoch_measured` (the rule's only measured input)
  and the rule itself.

## 4. Frozen identities (regenerated)

- Config:
  `5d6a6c6c64f38fbee3f63f80c4dac84130796be2c1c8e5413c9dbeda899d3a76`
- Freeze:
  `ac4558a8b72a3c41e667edb59b9053171fe53e35775c1d70b0752b988ed5d2ad`
- Static execution-identity manifest:
  `a8eafbd587e5278e8d3a093b83b7e1ffec075da5a09fa80ea902458e8e304a30`
- Attested environment (unchanged host):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head (unchanged anchor):
  `b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd`
- Inputs unchanged: mixture `0100df2b…`, extension lock
  `ccb1c3e2…`, comparator `9220c2c7…`; ceiling 1.25 GPU-h;
  seed 20260801.

Launch: `execute_unit_c(expected_freeze_sha256=…ac4558a8,
expected_identity_sha256=…a8eafbd5,
expected_environment_sha256=…372f958f,
expected_head_sha256=…b88eba02)`.

## 5. Next

Narrow changed-lines review (276_s closing) → GPU run with the §4
hashes → closeout + exposure-report review → the preregistered
decision → val/cycle/`R_cycle` → beta smoke → P0 freeze (sizing
rule executed there; audit repeated) → checkpoint-zero eval → P0.
