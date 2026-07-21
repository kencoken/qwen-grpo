# D16 rev1 critique — what moved, what didn't, and the rev2 levers

Input: `60_f_d16_rev1.md`, traces in `runs/d16-rev1-eval/traces/`.

## Assessment of rev1

**What worked.** The worked-example + duplicated-envelope-contract
pattern fully repaired the Lookup endpoint (0/6 → 15/15 success, zero
truncation). The build-from-`DEMONSTRATIONS` construction is the right
mechanism: prompt examples are machine-verified by the existing 0A test,
and any prompt change moves `D16_REVISION`, the worker-visible
fingerprint, and every request hash by construction.

**What half-worked.** Code now always emits the envelope (`E_NO_ARTIFACT`
→ 0) — but substitutes the payload-header handle for the literal
identifier `resource` in 10/10 calls, *despite* an explicit prohibition
naming that exact mistake. A prohibition stated in prose loses to the
most salient token in the request (the `R-XXX:` header directly above
the sequence). rev1's error was relying on a negative rule without a
negative example.

**What didn't work.** Math is CoT-aligned strongly enough that a format
contract stated twice, a worked example, and a brevity allowance ("at
most one short sentence") produced zero behavior change in the artifact
dimension: 15/15 `E_NO_ARTIFACT`, step-by-step LaTeX regardless. Two
readings: (a) the "one short sentence of reasoning" allowance is a
foothold — once the model starts solving, its training pulls it through
a full solution and it never emits the envelope; (b) the demo subtask
("Evaluate … exactly") *invites* computing the value; the example never
shows that the evaluated number is the wrong output.

## Ranked levers for rev2

1. **Math: artifact-only reply.** Drop the reasoning allowance for Math
   specifically: "Your entire reply must be exactly the artifact —
   nothing before it, nothing after it." §1.6 permits text before the
   envelope; it does not require it, so instructing none is
   contract-clean. This removes the CoT foothold rather than trying to
   bound it.
2. **Math: contrastive wrong/right pair using the demo's own numbers.**
   Show explicitly that the evaluated value is wrong output:
   "Wrong: `599986`. Wrong: a step-by-step solution. Right:
   `<artifact>(a * b - c) / d</artifact>`." This is the missing negative
   example for the self-computation failure.
3. **Code: contrastive wrong/right pair naming the handle.** Same
   pattern: "Wrong: `count_gt(stable_unique(R-8C3), 5)` — `R-8C3` is a
   name the interpreter does not understand. Right:
   `count_gt(stable_unique(resource), 5)`." Plus the positive framing
   "the word `resource` is the only name the interpreter understands".
4. **Second worked example with `step_k` (Math and Code).** Composite
   cells route requests whose expressions must reference `step_1`
   (lookup_math step 2, math_code both steps, fork_join step 3); rev1
   demos only show resource-operand forms, and the rev1 Math traces
   ramble specifically about `step_1` values. Add one machine-verified
   demo per endpoint exercising `step_k` (requires `demo_binding` to
   carry a `steps` binding — small, test-covered extension).
5. **Hold the token cap at 256.** If lever 1 works, Math replies collapse
   to ~20 tokens and truncation disappears; raising the cap is a runtime
   -profile change, not a D16 change, and should not be spent while the
   failure is behavioral (currently expected shrink from 8/15 to 0).
6. **Watch for Lookup regression** (no changes planned to its prompt
   beyond structural parity with the others — keep the diff minimal).

Deliberately not pursued now: raising `max_new_tokens` (masks the
failure), few-shot as extra chat turns (violates the frozen §1.5
skeleton), changing the frozen ARTIFACT final line of the user message
(same reason), evaluating/revising `SYSTEM_DIRECT` (no execution path
until the 1A baseline harness).

## Risk note

Adding worked examples that mirror the reference-subtask phrasing tunes
prompts toward the construction distribution; that is what the
construction namespace is *for*, but the qualification samples must stay
untouched (nothing here reads them), and the D16 review should judge
whether the examples over-fit the six cells' template language.
