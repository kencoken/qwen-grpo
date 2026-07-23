# D16 rev7 critique — remove the copyable wrong code; one lever left

Input: `72_f_d16_rev7.md`, traces in `runs/d16-rev7-eval/traces/`.

## Assessment

Rev7 delivered the largest single-revision gain since rev1 (27/45 →
41/45) and closed both long-standing fronts (fork_join handles,
argument order). It also produced the cycle's cleanest negative result:
the anti-guard contrast *caused* its own failure mode — all four
residuals are verbatim copies of the "wrong" string. The sharpened rule
(contrasts work when the model's prior opposes the wrong form; they
backfire when the wrong form flatters the prior) is worth carrying into
any future prompt work on this project.

## Levers for rev8 (expected final content revision)

1. **Replace the copyable anti-guard exemplar with a non-copyable
   phrasing.** Keep the intent, remove the template: "The number
   argument is step_1 or an integer, written exactly as given — never
   wrap it in arithmetic; the whitelist has no operators." No code
   string on the wrong side; the correct form `at(resource, step_1)`
   already appears as the second example directly above.
2. **Nothing else.** Every other front is at ceiling on this data
   (lookup 45/45, math 60/60, code_atomic 15/15, fork_join 15/15).
   rev3 and rev7 both showed that each additional instruction carries
   regression risk; with one residual mode left, the minimal diff is
   the whole play.

## Exhaustion / model-limit watch

Neither exhaustion nor model-limit applies yet: rev8 is a
removal-of-harm edit with a specific mechanism behind it. If rev8
clears math_code (or leaves ≤1 failure), the content iteration is done
and the closing step is a confirmation run + consolidated summary for
the third-party reviewer. If the guard behavior *persists without its
template* — the model re-inventing `% length` spontaneously as at rev6
— that would be the first genuine model-limit candidate on the Code
side: a defensive prior stronger than instruction. Even then the
residue would sit at ~4/150 on-contract calls (≈2.7%), against the 1A
per-endpoint <2% parse gate — close enough that the gate, not further
prompting, should render the verdict on qualification data.
