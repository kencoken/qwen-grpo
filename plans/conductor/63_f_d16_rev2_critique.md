# D16 rev2 critique — Code is converging; Math needs a different theory

Input: `62_f_d16_rev2.md`, traces in `runs/d16-rev2-eval/traces/`.

## Assessment of rev2

**Code** is responding to examples, not to rules: every failure mode we
have shown a worked example for has disappeared (envelope at rev1;
count-shape `resource` identifier at rev2 — all four successes are the
demonstrated shape), and every failure mode we have *not* demonstrated
persists (select-shape nesting, which the model actively garbles). This
is now a predictable pattern: this model class imitates worked examples
far more reliably than it obeys prose constraints. The remaining Code
errors are all example-coverage gaps, plus one contamination case
(pulling the join's `* 12` from the problem context into the step).

**Math** falsified rev2's central hypothesis. Removing the reasoning
foothold ("entire reply must be exactly the artifact") produced zero
change: the model writes a full LaTeX solution ending in `\boxed{}` on
every call. The template-injection hypothesis is also dead (rendered
bytes verified clean). What remains is that Qwen2.5-Math-1.5B-Instruct's
alignment is narrow and instruction-following weak: it treats *any*
arithmetic-shaped input as a problem to solve step by step. Instructing
it not to solve is fighting its training head-on.

## Ranked levers for rev3

1. **Math: reframe the role as translation, not restraint.** Instead of
   "solve but don't show working" (which still frames the task as
   solving), tell it the task IS a rewrite: "You translate tasks into
   calculator expressions. You never solve them." The subtask verb
   "Evaluate" invites solving; the system prompt should explicitly
   redefine it: "When the task says Evaluate, it means: write the
   expression the calculator should evaluate."
2. **Math: co-opt the boxed habit instead of suppressing it.** The model
   reliably ends with `\boxed{<answer>}`. Map the habit onto the
   contract: "Where you would normally write `\boxed{...}`, write
   `<artifact>...</artifact>` containing the unevaluated expression."
   This meets the model where its alignment already goes rather than
   demanding a behavior it never exhibits.
3. **Code: add the missing select-shape worked example** with the exact
   canonical nesting `at(rotate_left(stable_unique(resource), k), i)`
   (machine-verified via a third DEMONSTRATIONS entry), since example
   coverage is what demonstrably moves this endpoint.
4. **Code: scope discipline** — "Answer only the Task. Ignore any other
   arithmetic mentioned in the Problem." Targets the `* 12`
   contamination. And "no arithmetic operators — whitelist calls only"
   (the grammar has no `*`).
5. **Both: keep everything that works untouched** (Lookup prompt; Code
   count/step_k examples; Math step_k example).

## Escalation boundary (for the D16 review, if rev3 Math fails too)

If translation-framing + boxed-mapping still yields ~0% legal Math
artifacts, the honest conclusion is that no reasonable system prompt
makes this endpoint meet the <2% parse-failure gate, and the decision
leaves D16 scope: either (a) the Math endpoint model choice is revisited
(§1.6 endpoint change — a versioned experiment change needing review,
with Qwen2.5-1.5B-Instruct as the natural candidate given Lookup's 15/15
on the same base), or (b) Math-cell qualification is allowed to fail at
its gates, which is a legitimate experimental outcome the plan already
prices in. The D16 cycle's obligation is a documented best effort, not a
guaranteed pass; three revisions with a falsified-hypothesis trail is
approaching that bar but rev3's two untried levers come first.

## Risk note (unchanged)

Worked examples increasingly mirror the frozen reference-subtask
templates; construction-namespace tuning is the intended use, but the
D16 reviewer should weigh template overfit. Qualification data remains
untouched.
