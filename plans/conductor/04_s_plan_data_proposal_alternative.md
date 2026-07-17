I would build a single shared “case-world” generator rather than separate LOOKUP, MATH and CODE datasets. Every task would come from an executable typed DAG; surface language would be rendered independently; workers would share one output format; and task schemas would be rejected empirically whenever shallow routing baselines succeeded.

Routing is inevitably a classification problem. The goal is not to eliminate classification, but to ensure the classification requires understanding the requested computation and dependencies—not recognizing “percentage,” “department,” or a worker-specific JSON grammar.

# Proposal: anti-shortcut typed workflows

## 1. Generate semantics before language

Each instance starts as a typed reference program:

```text
TaskInstance
├── resources: opaque private payloads
├── nodes:
│   ├── operation
│   ├── typed inputs: literals, resources, or earlier nodes
│   ├── output type
│   └── reference value
├── dependency graph
└── final typed answer
```

A node might look conceptually like:

```json
{
  "id": "n2",
  "operation": "numeric.combine",
  "inputs": [{"node": "n0"}, {"node": "n1"}],
  "output_type": "integer"
}
```

Use a small exact type system:

```text
Integer | Rational | Boolean | Text | Key | IntegerList
```

The program is evaluated by an independent reference evaluator before it is rendered into natural language.

I would call this a reference program, rather than a gold workflow. Other decompositions or workers may also succeed. After calibration, store the empirical payoff vector for every worker, not merely a presumed “correct worker.”

## 2. Put heterogeneity behind a common interface

All workers receive the same request shape and return the same result shape:

```json
{
  "status": "ok",
  "value": {
    "type": "integer",
    "data": "17"
  }
}
```

The Math worker can internally emit an expression and use a calculator. The Code worker can emit a sequence program. Those artifacts are useful telemetry, but they should not define whether the outer answer parses.

This separates:

- response-format compliance;
- internal artifact validity;
- tool execution success;
- semantic correctness.

Otherwise a “specialist advantage” may simply mean that only one worker’s private grammar was accepted.

## 3. Use private, opaque resources in the main causal environment

The Conductor sees resource handles such as `Q17`, but not their payloads. Resource names do not encode their type. The relevant worker receives the payload when selected.

A worker call receives:

- its assigned subtask;
- a neutral resource manifest;
- only the resource payloads it is authorized to inspect;
- canonical outputs from authorized predecessor steps.

It does not receive gold metadata, other resource payloads, or every previous worker’s raw reasoning.

This prevents the Conductor from solving the problem and asking a worker to echo the answer. It also makes dependency interventions meaningful.

This is deliberately access-gated heterogeneity. I would therefore also create a smaller `test_soft` distribution where all payloads are visible and all workers can attempt everything. Performance there tests whether routing transfers beyond hard access constraints.

## 4. Cross semantics and rendering independently

I would factor each rendering across several independent dimensions:

- domain: staffing, inventory, expeditions, laboratory, publishing;
- clause order: goal-first, resources-first, dependency-first;
- dependency language: named intermediate, pronoun, imperative sequence;
- operation description: explicit instruction, rule card, input-output demonstrations;
- answer type and prompt-length bucket.

Every domain and rendering family must be able to express every worker family and workflow topology. “Inventory” must not imply Lookup; “laboratory” must not imply Math.

Other counterbalancing rules:

- opaque resource handles are randomly generated;
- final answer types are balanced across routes;
- numeric ranges and prompt lengths are balanced;
- every task can contain records, numbers and sequences, including inert distractors;
- section ordering is randomized;
- family-exclusive formatting and headings are forbidden;
- matched counterfactual pairs remain in the same split.

Literal semantics such as “multiply” may remain. Recognizing multiplication as mathematical is legitimate routing. What should disappear are nuisance correlations such as “all Math prompts contain percentages and are shorter.”

## 5. Use three rendering levels

The same latent program can have three kinds of rendering.

### Transparent rendering

Explicit instructions such as “retrieve the value, then multiply it by three.”

Use for Stage 0 and early routing smoke tests.

### Semantic rendering

Describe operations through rule definitions or examples rather than family-specific verbs:

```text
Rule K maps triples as follows:

[2, 4, 1] → 7
[5, 3, 2] → 11
[4, 8, 3] → 13

Apply K to the triple stored in Q17.
```

The rule is `2a + b − c`, so this favors Math, but the prompt never says “equation” or “calculate.”

### Counterfactual rendering

Include the same domains, vocabulary, distractors and structure across different routes. Change only the semantic relationship that determines the operation.

This becomes the decisive anti-shortcut evaluation slice.

# Operator library

I would keep individual operations modest and make the composition meaningful.

| Capability | Initial operations |
|---|---|
| Relational | keyed retrieval, pointer following, unique filtered selection, computed-key retrieval |
| Numeric | affine rule, exact ratio, bounded modular rule, comparison/aggregation |
| Sequence | stable deduplication, indexed selection, rotation, predicate count, small state transition |

Importantly, some operations should be solvable by more than one worker. The capability matrix should show soft differences—not alternatives failing exclusively because of incompatible parsers.

# Example tasks

## 1. Matched atomic rule induction

These tasks use exactly the same grammar but require different semantic capabilities.

Math instance:

```text
Rule K maps triples:

[2, 4, 1] → 7
[5, 3, 2] → 11
[4, 8, 3] → 13

Apply K to [7, 2, 5].
```

Reference rule:

```text
K(a,b,c) = 2a + b − c
answer = 11
```

Code instance:

```text
Rule K maps triples:

[2, 4, 1] → 412
[5, 3, 2] → 325
[4, 8, 3] → 834

Apply K to [7, 2, 5].
```

Reference rule: rotate left once, then concatenate.

```text
[7,2,5] → [2,5,7] → 257
```

A word-level grammar classifier sees almost identical prompts. The route depends on interpreting the demonstrations.

## 2. Causal Lookup → Math

```text
Retrieve Cedar's units from Q31.
Return three times that value minus four.
```

Private payload visible only to the relational endpoint:

```text
Q31:
Cedar.units = 17
```

Reference program:

```text
n0 = lookup(Q31, "Cedar", "units")   # 17
n1 = 3 × n0 − 4                      # 47
```

The Conductor cannot embed `47` because it never sees `17`.

A less explicit rendering can define the numeric rule through examples rather than “three times.”

## 3. Code → Lookup with a computed key

```text
From the ordered values in Q41, retain only the first occurrence of each
value and select the item at zero-based index 2.

Use that result as the key in Q42 and return its recorded score.
```

Private resources:

```text
Q41 = ["M2", "K7", "M2", "R4", "K7"]

Q42:
M2.score = 11
K7.score = 19
R4.score = 23
```

Reference program:

```text
stable_unique(Q41) = ["M2", "K7", "R4"]
index 2 = "R4"
lookup(Q42, "R4", "score") = 23
```

This is more useful than merely reversing the usual worker order: the first operation produces the lookup key.

## 4. Math → Code

```text
Compute (47 − 7) ÷ 5.
Use the result as a zero-based index into Q52 and return that value.
```

Private resource:

```text
Q52 = [4, 9, 2, 7, 5, 8, 1, 6, 3, 0]
```

Reference program:

```text
n0 = 8
n1 = Q52[8] = 3
```

A counterfactual version can contain the same numbers and list but ask for a stored field, changing the route while preserving most surface features.

## 5. Three-step linear dependency

```text
Retrieve Cedar's shift from Q61.
Compute twice the shift plus one.
Rotate the text in Q62 left by that many characters.
```

Private resources:

```text
Q61: Cedar.shift = 3
Q62: "orchestration"
```

Reference program:

```text
3 → 7 → "rationorchest"
```

This tests whether a value remains intact across two dependency boundaries.

## 6. Three-node fork/join

```text
Retrieve Cedar's units from Q71.
Count the entries in Q72 that end with "s".
Return the product of those values plus three.
```

Private resources:

```text
Q71: Cedar.units = 14
Q72: ["glass", "reed", "moss", "oak", "iris", "stone"]
```

Reference DAG:

```text
n0 = lookup(...)                  # 14
n1 = count_suffix(...)            # 3
n2 = n0 × n1 + 3                  # 45
```

The first two calls are independent and can execute in one wave. This introduces parallel decomposition and aggregation without the reliability penalty of three sequential waves.

## 7. Stored-versus-derived matched pair

Create pairs using the same case, entities, numbers and language:

- In one member, the requested report value is explicitly stored: one relational call.
- In the other, only its components are stored and the report rule is supplied: relational → numeric.
- A decoy formula appears in the stored version.
- A decoy stored field appears in the derived version.

A router that reacts to “formula present” or “records present” fails; it must determine what the question actually requires.

# Generator acceptance tests

A task should not enter the frozen distribution merely because its gold program executes.

## Semantic correctness

- An independent reference evaluator and runtime tools agree on at least 10,000 generated cases per operator/composition.
- Every renderer skeleton has hand-checked fixtures at ordinary and boundary values.
- Every typed answer is canonical; no float-based normalization.
- Changing an unused distractor cannot change the answer.
- No intermediate or final answer accidentally appears in the public prompt.

## Causal necessity

For every dependency edge:

- remove the dependency;
- replace it with another valid same-type value;
- mutate it to several alternative values;
- skip the upstream worker.

At least two valid mutations should change the downstream or final answer. Empirically, correct dependencies should beat missing or shuffled dependencies by at least 20 percentage points.

## Capability structure

On unseen qualification templates:

- intended endpoint accuracy of at least roughly 75–85%;
- intended-versus-best-alternative margin of at least 20 points;
- at least a 10-point margin remaining under the common-interface control;
- oracle composition at least 15–20 points above the best fixed worker;
- direct Conductor and echo-worker baselines at least 15 points below the oracle.

Select or reject whole operator-renderer cells, not individual instances. Filtering individual examples based on which worker happened to solve them would create severe selection bias.

## Decomposition headroom

Before committing to Stage 3, compare oracle routing using:

- reference subtasks;
- generic “solve the relevant part” subtasks;
- missing dependency descriptions;
- noisy but valid subtasks.

Reference subtasks should beat generic subtasks by around 10 points. Otherwise the environment does not contain much instruction-learning headroom.

# Explicit shortcut audit

Before GRPO, train cheap CPU baselines:

- keyword/regex router;
- word and character TF–IDF logistic regression;
- nearest-template router;
- cheap-feature router using length, digit count, punctuation, answer type and resource count;
- template-copy decomposer.

Judge them by executing their workflows, not only by comparing route labels.

My proposed gate would be:

- best shallow router at least 10–15 terminal-accuracy points below the oracle on qualification;
- nuisance-only features no better than chance plus approximately five points;
- after joint training, the Conductor at least 10 points above all shallow routers on the matched-counterfactual and held-out-renderer slices.

If TF–IDF or nearest-template routing is within five points of the oracle, retain that distribution only as a routing-mechanics harness. Do not use it for claims about semantic orchestration.

# Split design

| Split | Purpose |
|---|---|
| `construction` | Freely inspected while changing operators and renderers |
| `qualification` | One-time unseen gate after construction |
| `train` | Frozen Stage 2–4 distribution |
| `dev` | Checkpoint and configuration selection |
| `test_render` | Entirely unseen structural renderers/domains |
| `test_compose` | Seen primitives in unseen orders or graph shapes |
| `test_soft` | Visible resources and weaker access gating |

Counterfactual pairs remain together in the same split. Five renderings of one latent program count as one statistical cluster, not five independent examples.

# Compute-conscious sizes

A reasonable first pass on the 4090:

- CPU generator stress: 10,000 programs per semantic schema;
- committed hand-audited fixtures: about 64;
- worker pilot: 100 atomic programs per capability × three workers × three surface forms;
- capability gate: 500 programs per capability, with only a 100-program subset rendered five ways;
- composition calibration: 100 per direction or topology, expanding marginal cells to 300;
- frozen train pool: approximately 2,048 programs;
- dev: 300;
- final test: 1,000, stratified across ordinary, unseen-renderer and unseen-composition slices;
- three-step probe: 100–200 per topology.

I would generate and calibrate three-node tasks immediately, but initially admit them to training only if oracle success is at least about 60% and cold-start reward diversity survives within that topology. The fork/join form is substantially more informative than adding a third easy sequential operation.

The core design choice is therefore:

> Make routing depend on recovering a latent operation and respecting information flow; make domain, wording, length, answer type and worker grammar useless as shortcuts; and prove that with shallow baselines before spending GRPO compute.

That would give you both a clean mechanics laboratory and a demanding held-out test of whether the learned policy is doing anything more than template classification.