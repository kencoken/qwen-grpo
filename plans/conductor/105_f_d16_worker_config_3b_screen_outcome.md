# 105_f — outcome: the 104_f 3B prompt×model screen

**Verdict: ALL FOUR ARMS MISS the §4.1 target; the 104_f stop rule is
applied.** Best known configuration remains
`generic_1p5b / task_last / rev10` at **887/900**. The screen closes
the D16 model question in both directions: at 1.5B the coder variant
is worse (102_f), and at 3B *both* variants are worse — scale is
non-monotonic on this protocol.

Executable commit `cae75a5`; all runs under `runs/104f-3b-screen/`.

## Results

| arm | admitted | total | Code | LM guard (630) |
|---|---|---:|---:|---|
| `generic_3b-task_last-rev10` | ADMIT | 878/900 | 248/270 | byte-identical |
| `generic_3b-task_last-rev11` | ADMIT | 869/900 | 239/270 | byte-identical |
| `coder_3b-task_last-rev10` | ADMIT (attempt 2, see below) | 741/900 | 111/270 | byte-identical |
| `coder_3b-task_last-rev11` | ADMIT | 752/900 | 122/270 | byte-identical |
| *(best known, for reference)* `generic_1p5b-task_last-rev10` | — | **887/900** | **257/270** | reference run |

The preregistered guard held in every arm: all 4×630 Lookup/Math
records are byte-identical to the 99_f run, so every difference in
this table is attributable to the Code checkpoint swap alone (the F3
support digests already proved the request bytes identical).

## Finding 1 — scale solved exactly what it was asked to, then broke more

`generic_3b` fixed **all 13** characterized 1.5B-residual cases under
*both* prompts. But it introduced two new failure classes:

- **Global composition** (14 of rev10@3B's 22 Code failures,
  concentrated in `fork_join|goal_first`, 15/30): the model wraps its
  assigned step inside the downstream operations, e.g. its node's
  `count_gt(stable_unique(resource), 5)` becomes
  `at(rotate_left(count_gt(stable_unique(resource), 5), 18), 3)` — it
  solves the whole Problem instead of its Task. The 1.5B model did not
  *refrain* from this; it was *unable* to do it. Capability created
  the violation.
- **Legal-but-wrong-value** (5 rev10@3B / 7 rev11@3B): the first
  semantically-wrong-but-legal Code outputs in the entire D16 record
  (every 1.5B failure was protocol-class). Mostly threshold errors
  under `bound_var`. Consequence for the 103_s levers:
  grammar-constrained decoding can no longer be a complete fix at 3B.

## Finding 2 — the instruction-capacity hypothesis is refuted

rev11@3B (869) is *worse* than rev10@3B (878), and handle substitution
reappears under rev11 at 3B (15 cases). rev11's interference effect is
not a 1.5B capacity artifact — it reproduces at scale. (Per the 102_f
addendum this was already downgraded to a hypothesis; the screen now
rejects it.)

## Finding 3 — the coder prior is the anti-protocol prior

`coder_3b` fails ~150 Code cases per arm to **handle substitution**
(159 rev10 / 148 rev11): it writes the resource's literal name
(`stable_unique(R-4S5)`) where the DSL requires the word `resource` —
the professional-code convention of referencing variables by name,
applied where it is illegal. Whole strata collapse (`math_code`
`goal_first`/`resource_first` 0/30, `fork_join|goal_first` 0/30).
Coder-3B is worse than coder-1.5B (844), completing the pattern:
every coder variant underperforms its generic sibling at both scales.
Notably rev11 *helps* coder_3b (+11; `code_atomic|goal_first`
6/30 → 26/30) — the same amendment that hurts generic models, further
evidence that prompt effects are model-conditional, not additive.

## Admission incident (disclosed)

`coder_3b-task_last-rev10` attempt 1 was **refused** by the frozen
gate: P1 #1's wall (1867 s) included the one-time ~6 GiB checkpoint
download inside the measured window (P1 #2/#3: 97/95 s), projecting
5601 s > 3600 s. Following the P0 dirty-tree precedent: attempt-1
artifacts retained (`*.p1-{1,2,3}.json`, `admit.out`), and one fresh
triplet (`*.p1-r2-*.json`) ran under the **unchanged** frozen gate,
admitting at a projected ~300 s. The re-attempt decision used
wall-clock evidence only — no generation content was inspected before
it. Generation equality had already held across attempt 1's three
fresh processes; singleton-v1 is bit-stable on every 3B arm.
Flagged for reviewer ratification.

## Where this leaves D16

The frozen escalation logic is exhausted: model selection
(2 families × 2 scales), prompt revision (rev9→rev11 + code_local_v1),
and contract selection (current/task_last) have all been screened
under the frozen machinery, and **no arm reaches 30/30 or the §4.2
floor**. The failure surface is now fully characterized:

- 1.5B: protocol-class residual, prompt additions trade modes
  (interference).
- 3B generic: task-scope violations enabled by capability
  (composition) + first semantic errors.
- coder (both scales): prior-driven handle substitution.

Every dominant mode above is a **Problem-visibility failure** — the
worker misuses global context it does not need. This sharply
strengthens the 103_s `local_only` lever (send only Task, resource,
predecessors), which targets composition *and* handle-copying
directly. The other levers (BF16, grammar-constrained decoding — now
known partial, compressed replacement prompt) and the preserved
complementary-policies orchestration experiment remain as catalogued.

**Next decision (Ken + reviewer):** (a) preregister `local_only` as
the evidenced next probe; (b) amend the target / accept 887/900 with
its characterized residual into Stage-1A gates; (c) the orchestration
pivot (103_s §2) — its case is now "considerably stronger" by the
reviewer's own criterion, since the 3B screen failed to produce a
universal single worker. No further runs under 104_f.
