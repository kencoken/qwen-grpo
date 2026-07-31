# 272_f — Unit B REV2 (response to 271_s)

All four blocking findings and all three smaller corrections
repaired; identities regenerated. Full CPU suite: **999 passed
under `-W error`, TRUE exit 0**. Still CPU-only; built and verified
on the committed extension evidence.

## 1. B1 — the renderer allocation is the explicit frozen quota

`q2_w2_fork_join` is now an EXPLICIT per-renderer quota in the
config — `{bound_var: 4, goal_first: 14}` — selected ascending by
latent index within each stratum, with underfilled strata refusing.
(The rev1 bug: sorting by canonical renderer order put `goal_first`
first, yielding 18 goal_first / 0 bound_var.) The realized strata
are asserted exactly in tests: **4 bound_var + 14 goal_first**.

## 2. B2 — the Q1 exposure criterion is frozen and prospectively passed

The freeze now carries a MEANINGFUL POSITIVE criterion (no
consistency band that could accept zero): per critical cell, **≥2
Q1-counted groups from ≥2 distinct latents**, with a required
prospective pass probability **≥0.9** at the recommended Unit-C
size (**5 epochs = 785 rows ≈ 0.94 GPU-h**, inside the 1.0
ceiling). To meet it, `math_code` Bridge mass rose from 4 to **10
latents (30 rows/epoch)**. Exact-binomial pass probabilities are
computed in the record and ENFORCED as build-time refusals:

| Cell | Bridge rows/epoch | p(Q1-counted) | Draws @5 epochs | P(pass ≥2) |
|---|---:|---:|---:|---:|
| code_atomic | 12 | 0.4444 | 60 | 1.0000 |
| fork_join | 12 | 0.1111 | 60 | 0.9928 |
| math_atomic | 30 | 0.0278 | 150 | 0.9227 |
| math_code | 30 | 0.0278 | 150 | 0.9227 |

This is the final option-1 candidate (not a high-stop-rate B1/C1).

## 3. B3 — the consuming boundary authenticates everything

`build_mixture` itself now (a) refuses if the LIVE config's hash
differs from the import-time `CONFIG_SHA256` (a mutated config can
no longer ride under the frozen hash), and (b) authenticates the
supplied selection through `validate_frozen_selection` — expected
record hash from the frozen config AND body rehash. The reviewer's
reproduction (a modified selection retaining `c6c0877…`) now
refuses at the boundary; a re-hashed self-consistent forgery
refuses at the expected-record check; tampered evidence bytes still
refuse at the loader. All three are regressions, plus a live-config
mutation regression; the constraint logic itself is tested by
rebinding both the config and its hash.

## 4. B4 — the estimands are the registered ones

- **True Q1 rates**: the projections use the registered Q1-counted
  event (reward-1.0 fully family-correct completion AND a
  reward-0.5 completion of STRICTLY LOWER family correctness) —
  `code_atomic` 32/72, `fork_join` 8/72, `math_atomic` 2/72,
  `math_code` 2/72 — frozen as exact-fraction literals, sha-bound
  to the probe archive (`actions.jsonl` `44172e55…`), and
  REDERIVED from that archive by a regression.
- **The five `code_atomic→w3` rows are a DIRECT-SPECIALIST CONTROL
  class**: no upstream unlocking step, excluded from every Q2 gate
  and balance computation; the transfer confound is preregistered
  in the record. Composite-only Q2 balance is **18 w2 : 14 w3**
  (ratio 1.286 ≤ 1.5; both ≥ the 12 minimum).

## 5. Smaller corrections

- The reward-relevant conditional is disclosed alongside the
  diluted one: **P(w3-favoured | goal_first, payoff-distinct rows)
  = 0.576** (vs the diluted 0.224) — tied rows cannot penalize a
  worker-3 shortcut, and the record now says so with numbers.
- Exact configured quotas are ENFORCED: the `math_code` pool must
  be exactly 7, the control class exactly 5, `goal_first` control
  pools refuse underfill, and the fj strata refuse shortfall.
- `bridge_eligible` now enforces the registered
  lower-family-correctness condition on the 0.5 route (unit-tested
  with a crafted counterexample: 0.5 only on the family-correct
  route refuses).

## 6. The revised schedule (157 rows/epoch)

| Class | Rows |
|---|---:|
| Q2 composite (`math_code→w3` 7×2, `fork_join→w2` 4+14) | 32 |
| direct-specialist control (`code_atomic→w3`) | 5 |
| goal_first controls (6 per Code cell, tied) | 18 |
| Bridge (ca 4 / fj 4 / ma 10 / mc 10 latents × 3 renderers) | 84 |
| Anchor (latent 0 × 6 cells × 3 renderers) | 18 |

714 observations screened at zero multiplicity; latent 42 screened;
expected zero-variance fraction 0.851; frozen shuffle seed
unchanged.

## 7. Frozen identities (regenerated)

- Config:
  `71846d34060f3289aa2f6f1aea5d57657c3ae76d49605cabffc1e6ddb03d2d6e`
- Freeze:
  `4b67929f1aecc4f037ef3b87a460d0d36bded344479116855e32366fc37d81c4`
- Mixture record:
  `803433857ad1d0f667f7fdb10f4e10a0ccceb9460ff6c954c5b18d3bb6c5525a`
- Inputs unchanged: extension lock `ccb1c3e2…`; selection
  `c6c08775…` (file `e0bbb75d…`); probe report `3a001c99…`; probe
  trace `44172e55…`; lineage parent `b88eba02…`.

## 8. Next

Short changed-lines review (271_s closing) → pre-Unit-C
code-invalidation audit → Unit-C freeze (gates preregistered
against §2's frozen criterion and probabilities; validates mixture
record `80343385…` at 5 epochs) → Unit-C run → preregistered
decision → val/cycle/`R_cycle` → beta smoke → P0 freeze →
checkpoint-zero eval → P0.
