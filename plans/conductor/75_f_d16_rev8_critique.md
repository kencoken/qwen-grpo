# D16 rev8 critique — one matched-regime demo, then the verdict

Input: `74_f_d16_rev8.md`, traces in `runs/d16-rev8-eval/traces/`.

## Assessment

Rev8 was a controlled removal that produced the cycle's most valuable
negative result: the guard is endogenous, value-triggered (step_1 ≥ 10),
and instance-stable across three prompt treatments (spontaneous at rev6,
template-shaped at rev7, spontaneous again at rev8). This is exactly
the pre-registered model-limit signature from `73_f` — but with one
qualification: the demonstration set has never covered the triggering
regime. Declaring a model limit while the strongest known lever
(matched-regime worked example) sits untried would be premature.

## rev9 plan (single change)

Change the second Code demonstration's binding from `step_1 = 2` to
`step_1 = 10` (12-element demo list, expected value 7, machine-verified
like every demo), and add one assurance clause beside it: "step_1 is
always a valid zero-based index, even when it is large." Nothing else —
rev8's boundary flips (code_atomic idx 3, fork_join idx 6) confirm
every perturbation risks collateral movement, so the diff must stay
minimal to keep attribution clean.

## Decision rule (pre-registered, closing the loop on the instruction)

- **If rev9 clears the four large-index instances** (math_code ≥ 14/15)
  without new regressions: Code content iteration is DONE. Run the
  closing confirmation + consolidated summary; residual boundary noise
  (~1–2 calls/90) goes to the 1A gates.
- **If the guard persists under a matched-regime demonstration**: the
  model-limit hypothesis is accepted for this mode. The residue is
  4/45 code calls ≈ 2.2% concentrated in one cell (vs the 1A <2%
  per-endpoint parse gate measured over all on-contract calls — likely
  a near-miss composition), and the options pass out of D16 scope:
  accept and let the gate rule at qualification scale, or revisit the
  index-value distribution at the construction screen (step_1 values
  ≤ 9 would sidestep the trigger — a difficulty-profile decision, (S)
  bands are phase-2, not a prompt decision).
- Either way, this cycle ends with rev9 + confirmation: on the Lookup
  and Math fronts we are at 100%, and on Code we will have either
  ceiling or a characterized, bounded, gate-referred residual — the
  "exhausted or model-limit" terminus the instruction defines.
