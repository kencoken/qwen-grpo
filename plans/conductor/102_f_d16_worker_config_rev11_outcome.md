# 102_f — rev11 follow-up outcome: stop rule applied (101_f protocol)

**Executed 2026-07-22 at `3e2be63`,** clean worktree, both arms
admitted (bit-stable, within the cost gate), both full crossed runs
completed and strictly loaded. **Both arms miss the target; per the
101_f stop rule, no further prompt edits under that document.**

## Results

| configuration | total | Code endpoint |
|---|---:|---:|
| `generic_1p5b / task_last / rev10` (100_f anchor) | **887/900** | 257/270 |
| `generic_1p5b / task_last / rev11` | 878/900 | 248/270 |
| `coder_1p5b / task_last / rev11` (conditional arm) | 844/900 | 214/270 |

Guards: all 630 Lookup+Math records in the generic rev11 run are
byte-identical to the rev10 run (the amendment touched only Code, at
the byte level); Lookup and Math remain perfect in every arm.

## What rev11 taught

1. **The targeted rules worked on their targets**: 10 of the 13
   characterized rev10 failures are fixed; `math_code|goal_first` and
   `fork_join|bound_var` reached 30/30.
2. **But the added text induced 19 regressions** — dominantly the
   *return of handle substitution* (`stable_unique(R-4S5)` instead of
   `resource`), plus one invented function name and two new envelope
   slips. Mechanism: the three appended rules sit before the final
   identifier restatement and dilute exactly the recency that the
   rev3→rev4 history documented as load-bearing. Net −9.
3. **Conservation of failures at 1.5B**: prompt text added to fix the
   last ~13 cases displaces attention from rules holding down other
   modes. This is the properly-measured "model limit" signature 78_s
   asked for — not "the model cannot do the task" (887/900 says it
   mostly can), but "prompt additions now trade failure modes rather
   than removing them."
4. **The model-switch path at 1.5B is closed on full evidence**: the
   coder arm, predicted weaker by the 100_f paired prefix analysis,
   is weaker at full scale (844/900), with its composition mode
   catastrophic under `goal_first` (`fork_join` 1/30).

## State of the frontier

Best known configuration: **`generic_1p5b / task_last / rev10` at
887/900 (98.6%)** — Lookup 270/270, Math 360/360, Code 257/270 with a
13-case all-protocol-class residual. It fails the frozen 30/30 target
AND the §4.2 fallback floor (one stratum at 25/30 < 29/30), so **no
acceptance path exists under the frozen definitions** — the next step
is necessarily a new decision, not a rerun.

## Evidenced options for the next decision (Ken + reviewer)

- **(a) 3B escalation under `task_last` + rev10** — now a well-posed
  question for the first time: the contract blocker is resolved
  (Lookup/Math perfect), the 1.5B prompt frontier is demonstrated
  rather than assumed (this document), and the 1.5B model switch is
  closed. A bounded prereg: `{generic_3b, coder_3b}` × `task_last` ×
  rev10, the frozen machinery as-is, ~2 GPU-hours. The 92_s §8
  smallest-pool preference still applies if either reaches target.
- **(b) Amend the target** (accept 887/900-class performance with a
  characterized residual) — a design decision requiring the reviewer,
  with knock-on effects on the 1A parse gates.
- **(c) Stop D16 iteration here** and carry the characterized 98.6%
  configuration into the Stage-1A gates as-is.

Option (a) is the natural continuation of the frozen escalation logic;
(b)/(c) change definitions and belong to a design review.
