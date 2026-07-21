# D16 rev6 critique — Math is done pending scale; Code has one new front

Input: `70_f_d16_rev6.md`, traces in `runs/d16-rev6-eval/traces/`.
(Per instruction, the endpoint-model selection is taken as given here;
this critique addresses prompts only.)

## Assessment

**Math** needs no prompt work on this evidence: 57/57 legal *and*
correct at construction scale with the rev3 text unmodified. The right
posture is the one Lookup earned — freeze the text, verify at scale in
the closing confirmation run, and resist the temptation to "improve" a
100% endpoint (rev3 taught us what uninvited additions cost).

**Code** is now one cell from done. The two shapes with dedicated,
correctly-ordered examples are at ceiling (code_atomic 15/15). The two
remaining fronts are:

1. **math_code step 2 (0/15) — new, and the priority.** This is a core
   training-mixture cell, unlike fork_join. The failure decomposes as
   argument-order flip (majority) plus invented out-of-whitelist
   arithmetic (minority). Notably the existing second worked example
   shows this *exact* task phrasing with the correct
   `at(resource, step_1)` — imitation alone is failing for the first
   time. What differs between the demo and the failing requests: the
   live requests carry a two-handle Problem, a concrete
   `step_1 = <value>` line, and an operand-record handle as distractor.
   The English argument order ("the value at index i in s" → `at(i, s)`)
   is evidently a stronger prior than one example can override.
2. **fork_join (12/15) — diagnostic cell, lower stakes.** The prose
   extension bought one instance; three sticky handle-substituters
   remain.

## Ranked levers for rev7

1. **Argument-order contrast attached to the second example** (the
   pattern with a perfect record so far — every targeted wrong/right
   contrast has moved its failure mode): "Wrong: `at(step_1, resource)`
   — the sequence is always the FIRST argument of every whitelist call;
   the index or count comes second. Right: `at(resource, step_1)`."
2. **Anti-guard contrast in the same block**: "Wrong:
   `at(resource, step_1 % 8)` — use step_1 exactly as given; the
   whitelist has no arithmetic." (Folds the minority mode into the same
   example block rather than adding prose elsewhere.)
3. **A positional-form first sentence**: extend the existing first-
   sentence rule with "the first argument of every call is the sequence
   (resource or a nested call); the second is a number (an integer or
   step_k)". Rule-position discipline per rev4: first sentence + final
   line only.
4. **fork_join: hold.** No new lever this round — the remaining three
   are instance-sticky, the cell is diagnostic and behind admission
   gates, and stacking two structural experiments in one revision
   muddies attribution. If rev7 fixes math_code without disturbing
   fork_join, rev8 can try converting the two-handle prose into a true
   worked example as the last idea on that front.

## Exhaustion / model-limit watch (per the current instruction)

Not close to either for Code: rev7's levers are the cycle's
best-validated pattern applied to a brand-new failure mode, and the
model has responded to every such contrast so far. The genuine
model-limit candidate remains the sticky fork_join trio — three
instances that survive every prompt so far. If they survive a dedicated
worked example too (rev8), that residue (~2% of on-contract code calls
at mixture composition, concentrated in a deferred diagnostic cell) is
where I would draw the line and hand the remainder to the 1A gates.
