# Addressing review cycles

The volume of review cycles is primarily structural and methodological, not evidence that the author is generally weak. The author has repeatedly reproduced findings accurately, fixed them correctly, added regressions, and preserved evidence. A poor author would more often misunderstand or paper over the findings.

That said, a few authoring habits interact badly with the codebase's structure.

## Recurring patterns

| Pattern | Typical examples |
|---|---|
| Prose contract differs from executable contract | 4 `bound_var` rows promised but zero selected; distinct-latent gate recorded but unused |
| Generic metric reused for a narrower estimand | `semantic_contrast` presented as Q1-counted exposure |
| Aggregate tests miss important strata | 18:19 direction totals passed while renderer composition was wrong |
| Validation exists only on an optional path | Secure selection loader existed, but the public builder could bypass it |
| Hash describes something other than the live object | Mutable config generated a changed schedule under the old hash |
| Requirements silently disappear during revision | The inherited renderer gate vanished until explicitly discussed |
| Scientific classes and implementation classes drift | Atomic Code rows classified as hierarchical Q2 |
| Low empirical support is handled by weakening a gate | Consistency bands were proposed around an underexposed mixture |
| Corrections add more machinery to an already dense module | Schedule building, authentication, power calculations and reporting accumulate together |

These are not independent accidents. They have common causes.

## Structural causes

### 1. The effective specification is distributed across many Markdown revisions

To implement Unit B correctly, the author must mentally compose requirements from 256, 258, 260, 269, 271 and later amendments. Some clauses are inherited, some superseded, and some merely reworded.

That is why requirements such as renderer representation can disappear without anyone consciously deciding to remove them.

The documents are an excellent audit trail, but a poor active specification.

### 2. Scientific meaning is represented with untyped dictionaries and strings

Concepts such as:

- Q1-counted event;
- Q2 composite exposure;
- direct-specialist control;
- renderer requirement;
- construction versus qualification identity;

are mostly encoded through dictionary keys and conventions. The type system cannot distinguish "semantic contrast" from "Q1-counted contrast," or a direct Code row from a hierarchical Q2 row.

This makes scientifically different quantities look interchangeable in code.

### 3. The modules combine too many responsibilities

`p0_mixture.py` now handles:

- input authentication;
- schedule construction;
- class assignment;
- estimand definitions;
- power calculations;
- shortcut diagnostics;
- frozen identities;
- serialization and verification.

A change to one scientific decision therefore affects many identities and calculations. It also makes it easy for a test to confirm the final aggregate while missing an internal semantic mismatch.

### 4. Configuration is executable global state

Mutable global configuration plus import-time hashes has repeatedly created opportunities for identity drift. Tests also monkeypatch these globals, making "the frozen configuration" less absolute than the name suggests.

### 5. The preregistration posture makes every correction expensive

The project deliberately chose a registered-report style before any GRPO training:

- freeze the hypothesis;
- validate power;
- validate gates;
- authenticate every artifact;
- then permit execution.

That is scientifically admirable, but empirical behavior is still poorly known. Consequently, some "bugs" are really discoveries that the prospective design was unrealistic.

D5, persistence geometry, B cold-start behavior and the Q1 mixture sizing all fall partly into this category.

### 6. Reviews have remained open-ended

Each repair review has sometimes introduced a new conceptual dimension rather than only checking the previous findings. This has improved the experiment, but means there is no natural convergence rule.

Some of the cycle count therefore comes from the review process, not the implementation.

## Author-specific improvements

There are nevertheless habits the author could change:

- Convert every scientific claim into an executable invariant before writing "enforced," "exact" or "frozen."
- Test the complete stratum matrix, not only aggregate totals.
- Define the estimand function first, then use that same function for simulation, execution and reporting.
- Avoid solving every finding by adding another dictionary field or validation layer.
- Explicitly list which inherited requirements are retained or superseded in every new freeze.
- Include a traceability table in each implementation response:

| Requirement | Config field | Enforcement | Regression | Artifact field |
|---|---|---|---|---|

That table alone would have exposed several recent issues immediately.

## A useful restructuring

I would not rewrite the worker runtime, provenance system or existing evidence machinery now. The next failures are more likely to come from real Unit-C/P0 execution than from another broad refactor.

A small "contract spine" would be worthwhile before P0:

```text
P0Contract
├── authenticated input identities
├── exact schedule specification
├── active scientific objectives
├── estimand definitions
├── gate definitions
├── superseded requirements
└── expected artifact identities
```

Then separate the current module into four pure components:

```text
contract.py     Frozen active specification
estimands.py    Q1/Q2 event definitions
schedule.py     Deterministic cohort and mixture construction
design.py       Power/exposure calculations and acceptance checks
```

The important API would be conceptually:

```python
schedule = build_schedule(contract, surface, selection)
report = evaluate_design(contract, schedule, evidence)
verify_contract(contract, schedule, report)
```

Verification should remain at the consuming boundary; this should not become another hierarchy of "proof marker" types.

The Markdown freeze should be generated from, or mechanically checked against, the same contract. That removes duplicate numerical truths.

## Process changes that would reduce review cycles

For each future unit:

1. Design review: settle objectives, estimands and active requirements.
2. Author creates the machine-readable contract and traceability table.
3. Implementation review: code, tests and artifact identity.
4. One repair pass.
5. Changed-lines plus mechanical verification.
6. Sign off unless a remaining issue can plausibly change results, identity, privacy or phase separation.

Documentation wording and exotic malformed-object cases should not trigger another full round.

## Bottom line

The many cycles are approximately:

- one part genuinely difficult experimental design;
- one part intentionally strict preregistration;
- one part distributed specifications and weakly typed scientific concepts;
- one smaller part author habits;
- one part reviews continuing to broaden after each repair.

I would make a targeted contract/estimand restructuring, not a wholesale rewrite. More importantly, I would consolidate the active specification and impose a stopping rule on reviews. Those changes should materially reduce the cycle count without sacrificing the scientific discipline that has caught several real, result-changing errors.