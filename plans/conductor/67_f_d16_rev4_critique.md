# D16 rev4 critique — configuration is stable; spend rev5 on confirmation

Input: `66_f_d16_rev4.md`, traces in `runs/d16-rev4-eval/traces/`.

## Assessment

Rev4 confirmed the layout theory with a clean paired comparison: same
examples, same rules, different positions — 1/10 → 9/10. Combined state:
Lookup 15/15 (stable ×4), Code 9/10, Math 0/n with the cause localized
outside D16 scope. The prompt set has plausibly converged at the level
this evaluation size can resolve.

Two residual concerns:

1. **Sample size.** Per-revision Code evidence is 10 calls on 5 fixed
   instances; the rev2→rev3 "regression" and part of the rev4 "recovery"
   could contain noise, though the failure-mode *composition* shifts
   (nesting fixed, arithmetic gone, handle persisting on one specific
   instance) are qualitative and real. The <2% parse-failure gate at 1A
   will be judged on hundreds of qualification calls; the D16 review
   should see the frozen candidate at a less noisy construction count
   first.
2. **The residual Code failure is instance-sticky**: the same
   construction instance (`code_atomic` index 4, t=4) elicits the handle
   on every revision that fixes the others. Worth watching at scale —
   if handle-substitution concentrates on particular payload shapes,
   that is distribution information for the construction screen, not a
   prompt defect.

## Rev5 plan (final iteration of this cycle): confirmation, not content

Per `65_f` lever 3: **no prompt-text changes.** Re-run the paired
evaluation at `--per-cell 15` (~45 lookup, ~45+ math-eligible, ~30 code
calls) to give the D16 review stable per-endpoint rates for the frozen
candidate texts, and record the final evidence summary
(`68_f_d16_rev5.md`) consolidating all five revisions for the reviewer.
If the scaled run contradicts rev4 (Code compliance collapses), that is
a finding, and the cycle pauses with the contradiction documented rather
than patched — the pause point is the user's instruction either way.

## Standing items for the D16 review (final list)

- **Blocking question**: §1.6 Math endpoint model
  (Qwen2.5-Math-1.5B-Instruct cannot emit the envelope under any tested
  prompt; base Instruct scores 20/20 on the same requests — evidence in
  `64_f`). Endpoint swap = versioned experiment change; alternative =
  accept Math-cell qualification failure, which would gut four of six
  cells' reference paths.
- Judge template-overfit of the worked examples (they mirror the frozen
  reference-subtask phrasings; construction-only tuning is intended, but
  the reviewer should confirm this is acceptable for qualification).
- `SYSTEM_DIRECT` remains rev0 (unexercisable until the 1A baseline
  harness exists).
- Token cap 256 unchanged (runtime-profile decision; Math truncations
  are a symptom of the endpoint question, and legal artifacts from
  compliant endpoints run ~20–30 tokens).
