The most honest framing is:

> This is initially a wind-tunnel experiment for hierarchical GRPO, not evidence that a 3B model needs orchestration on natural Math or Code tasks.

It can establish that endpoint selection is learnable and objectively useful within the controlled environment. Whether orchestration remains useful when the Conductor sees everything is a separate, later experiment.

## What an instance should contain

Generate each example from executable semantics before producing language:

```text
Latent program
├── private resources
├── typed operation nodes
├── dependency edges
├── intermediate values
└── final integer answer
        ↓
Natural-language renderer
        ↓
Public prompt + opaque resource manifest
```

A stored instance should keep these logically separate:

```json
{
  "cell_id": "lookup_math",
  "renderer_id": "goal_first",
  "public_prompt": "...",
  "public_manifest": ["R-3T5"],
  "private_registry": {
    "R-3T5": {
      "kind": "integer_records",
      "payload": "..."
    }
  },
  "reference_program": "...",
  "gold_answer": 47,
  "generator_version": "v0.1",
  "seed": 18421
}
```

The public prompt and resource handle are visible to the Conductor. The resource payload is supplied only when a worker is called. The reference graph and intermediate values never enter execution.

Do not store a presumed gold worker in each instance. Worker assignments come from the empirically measured payoff surface.

# Concrete task examples

## 1. Atomic Lookup

Public prompt:

> Resource R-7K2 contains parcel records. Return the crate count recorded for Grove.

Private resource:

```text
R-7K2:
Aster.crates = 31
Cedar.crates = 17
Grove.crates = 39
Ivory.crates = 53
```

Latent semantics:

```text
lookup(R-7K2, "Grove", "crates") → 39
```

Tool-neutral reference subtask:

> Retrieve Grove’s crate count from the requested resource.

Worker artifact:

```text
<artifact>lookup(resource, "Grove", "crates")</artifact>
```

Gold answer: `39`.

Difficulty varies through record count, field count and distractors—not new semantics. A harder version could contain 20 records with five fields each.

## 2. Atomic Math

Public prompt:

> R-2P6 contains integers a, b, c and d. Evaluate `(a × b − c) ÷ d` exactly.

Private resource:

```text
R-2P6:
a = 83719
b = 43
c = 1
d = 6
```

Latent semantics:

```text
(83719 × 43 − 1) ÷ 6
= 3,599,916 ÷ 6
= 599,986
```

Worker artifact:

```text
<artifact>(a * b - c) / d</artifact>
```

Gold answer: `599986`.

The generator rejects examples unless division is exact and the result remains within the chosen bound.

The Conductor can understand that this is arithmetic, but it cannot calculate the result because it does not see the operands.

## 3. Atomic Code

Public prompt:

> From the integer sequence in R-8C3, remove later occurrences of repeated values, rotate the remaining sequence left by three positions, and count values greater than five.

Private resource:

```text
R-8C3:
[6, 1, 6, 9, 4, 1, 8, 3, 9, 2, 7, 4]
```

Latent semantics:

```text
stable_unique
→ [6, 1, 9, 4, 8, 3, 2, 7]

rotate_left(3)
→ [4, 8, 3, 2, 7, 6, 1, 9]

count_gt(5)
→ 4
```

Worker artifact:

```text
<artifact>
count_gt(rotate_left(stable_unique(resource), 3), 5)
</artifact>
```

Gold answer: `4`.

Reject cases where the transformation is trivial—for example, no duplicates, zero rotations, or a predicate count of zero or the full sequence length.

## 4. Lookup → Math

Public prompt:

> Retrieve Cedar’s units from R-3T5. Return three times that value minus four.

Private resource:

```text
R-3T5:
Aster.units = 31
Cedar.units = 17
Grove.units = 39
Ivory.units = 53
```

Latent program:

```text
n1 = lookup(R-3T5, "Cedar", "units") → 17
n2 = 3 × n1 − 4                     → 47
```

Reference subtasks:

```text
1. Retrieve Cedar’s units from the requested resource.
2. Multiply step_1 by three, then subtract four.
```

Artifacts:

```text
<artifact>lookup(resource, "Cedar", "units")</artifact>
<artifact>3 * step_1 - 4</artifact>
```

Gold answer: `47`.

For a counterfactual dependency test, replace `step_1=17` with `19`:

- corruption scoring retains the original target `47`;
- counterfactual-consistency scoring changes the target to `53`.

This determines whether the downstream step actually uses the intermediate.

## 5. Math → Code

Public prompt:

> R-6D1 contains integers a, b, c and m. Compute `(a × b + c) mod m`. Use the result as a zero-based index into R-9V4 and return the selected integer.

Private resources:

```text
R-6D1:
a = 982451653
b = 37
c = 7
m = 12

R-9V4:
[41, 7, 83, 22, 65, 14, 39, 90, 56, 11, 72, 28]
```

Latent program:

```text
n1 = (a × b + c) mod m → 8
n2 = R-9V4[8]           → 56
```

Artifacts:

```text
<artifact>(a * b + c) % m</artifact>
<artifact>at(resource, step_1)</artifact>
```

Gold answer: `56`.

Generation rejects instances unless the index is valid and counterfactual indices select different list values.

## 6. Fork/join: Lookup + Code → Math

Public prompt:

> Retrieve Cedar’s units from R-5A8. Separately, remove later duplicates from R-1J7, rotate it left by three positions, and count values greater than five. Return the product of the two results plus three.

Private resources:

```text
R-5A8:
Aster.units = 31
Cedar.units = 14
Grove.units = 39

R-1J7:
[6, 1, 6, 9, 4, 1, 8, 3, 9, 2, 7, 4]
```

Latent DAG:

```text
n1 = lookup(...)                                        → 14
n2 = count_gt(rotate_left(stable_unique(...), 3), 5)   → 4
n3 = n1 × n2 + 3                                       → 59
```

The first two nodes are independent and form one execution wave. The Math aggregator consumes both:

```text
<artifact>step_1 * step_2 + 3</artifact>
```

Useful branch counterfactuals:

```text
14 → 15 gives 15 × 4 + 3 = 63
4  → 3  gives 14 × 3 + 3 = 45
```

This is the first topology that teaches something beyond a linear chain.

# Mapping semantics to language

One latent Lookup→Math program can have several renderings:

**Resource first**

> Retrieve Cedar’s units from R-3T5. Return three times that value minus four.

**Goal first**

> Return the number obtained by subtracting four from three times Cedar’s units recorded in R-3T5.

**Bound variable**

> Let x be Cedar’s units in R-3T5. Output `3x−4`.

All three share:

- the same private payload;
- the same reference program;
- the same interventions;
- the same answer;
- the same acceptable workflow.

This separation is beneficial because it lets you:

- test language robustness without changing task semantics;
- hold out renderer families independently of operations;
- generate exact causal counterfactuals;
- debug the verifier without reasoning about prose;
- distinguish worker capability from renderer sensitivity;
- add semantic or counterfactual renderers later without rebuilding the environment.

It also prevents the renderer from accidentally determining the answer because it has no interface through which to read private values.

# Avoiding grammar shortcuts

There are two different notions of “shortcut.”

## Nuisance shortcuts

These should be eliminated:

- resource names such as `MATH_RESOURCE_1`;
- different output types for different endpoints;
- Math prompts always being shorter;
- Lookup always using staffing language;
- worker names appearing in task text;
- a fixed clause order per operation;
- resource IDs correlated with payload or split;
- answer ranges differing dramatically by cell.

Mitigations include:

- the same opaque handle format everywhere;
- integer outputs in every cell;
- renderer variants crossed with every cell;
- domain names and clause orders balanced across cells;
- the same words—“resource,” “result,” `step_1`—across directions;
- matched prompt-length and answer-range bands where practical;
- treating multiple renderings of one program as one statistical cluster;
- a nuisance-only classifier over renderer, domain, length, resource count and numeric formatting.

## Legitimate semantic cues

These should not be removed:

- “retrieve a field”;
- “multiply”;
- “zero-based index”;
- “remove duplicates.”

Understanding that multiplication is better handled by a Math endpoint is the behavior you want.

Consequently, transparent Stage 2 is still likely learnable by a lexical classifier. That is acceptable: its stated claim is only fixed endpoint selection in a typed environment. The deferred semantic/counterfactual renderer and shallow-router audit are required before claiming natural-language semantic orchestration.

# What if the 3B Conductor can solve Math and Code?

On visible inputs, it probably can solve many of them.

That gives three distinct levels of evidence:

### 1. Mechanism learnability

Can GRPO learn endpoint selection from terminal reward?

The private Stage 2 condition answers this cleanly. Concrete operands and lists are hidden, so the Conductor can recognize the required capability but cannot compute the answer itself.

### 2. Utility inside the controlled environment

Does composition actually outperform available one-call endpoints?

A composite cell is retained only if its deployable workflow oracle beats the best one-call whole-task endpoint by at least 20 points. Thus the study is not satisfied merely because routing can be memorized: the composed endpoints must deliver measurable value in that environment.

However, that value is partly constructed through private information and tool access.

### 3. Utility when orchestration is optional

Will the model delegate when it could solve directly?

The current private experiment does not answer this. A later visible condition needs an explicit action such as:

```text
SELF(answer)
```

or:

```text
RETURN(answer)
```

Without a direct action, the model is forced to call a worker and may express self-solving by embedding the answer or complete executable artifact in its subtask. That measures answer smuggling, not selective delegation.

So the initial experiment is not purely “can it produce orchestration syntax,” but neither does it establish natural-world delegation. It establishes:

> GRPO can or cannot learn a useful bundled-endpoint policy when endpoint choice and information flow objectively affect terminal payoff.

The endpoints are model-plus-tool bundles. It does not yet isolate the value of the specialist LLM from the value of its tool.

# How this maps to the Conductor paper

The transferable object is not the surface task. It is the payoff geometry.

Both systems contain:

- a trainable high-level policy;
- opaque endpoint identities;
- frozen heterogeneous workers;
- terminal workflow reward;
- multiple sampled workflows per prompt;
- group-relative advantages;
- no intermediate route supervision in the joint condition;
- interactions between worker selection and subtask wording;
- multi-call credit assignment.

The frontier paper obtains heterogeneity from differences among capable models. The toy deliberately creates it through models, tools and information access.

That means the toy can reproduce the optimization skeleton:

- learning fixed endpoint identities;
- strongest-worker collapse;
- failure when routing stakes are weak;
- format learning before correctness;
- sparse credit over multiple calls;
- routing learning before good subtask writing;
- sensitivity to demonstrations;
- redundant calls and over-orchestration.

It cannot establish that frontier-model heterogeneity will look the same, or that natural shared-context Math benefits from decomposition.

A sensible progression toward the paper is:

1. Hidden payloads, bundled tools: clean routing laboratory.
2. Visible payloads plus explicit `SELF`: selective delegation.
3. Equalized tools/access: isolate model specialization.
4. Semantic and counterfactual renderers: reduce template routing.
5. Stronger heterogeneous model/API endpoints.
6. Longer build–test–review–repair workflows.
7. Dynamic or recursive orchestration.

If the same routing collapse, credit-assignment and instruction-learning phenomena survive those relaxations, the analogy to the paper becomes much stronger.

# Expected learning dynamics

The reward naturally creates two phases:

```text
0.0 → 0.5: learn a structurally valid action
0.5 → 1.0: learn an action that actually succeeds
```

Because GRPO normalizes within each group of eight, an all-invalid, all-valid-wrong or all-correct group provides no learning signal. Expect the non-zero-variance-group fraction to rise during learning and then fall again as the policy either succeeds consistently or collapses.

## Stage 2: routing-only

This should be the cleanest learning curve.

Under approximately uniform initial routing, a group of eight contains one particular best assignment with probability roughly:

- atomic, three assignments: `1 − (2/3)^8 ≈ 96%`;
- two-step chain, nine assignments: `1 − (8/9)^8 ≈ 61%`;
- fork/join, 27 assignments: `1 − (26/27)^8 ≈ 26%`.

That predicts:

1. Routing-schema validity rises almost immediately.
2. Atomic routing learns first.
3. Two-step assignments learn later.
4. Fork/join is much noisier and may not learn at all with group size eight.
5. Endpoint entropy falls.
6. Zero-variance groups rise again at the final plateau.

The main failure is strongest-endpoint collapse: one generally good endpoint is selected everywhere before the model learns cell-conditional routing.

Track routing regret against the deployable payoff surface, not only exact route accuracy.

## Stage 3: decomposition-only

Expected progression:

1. Valid subtask schema.
2. Generic “solve the relevant part” prompts.
3. Endpoint-compatible local instructions.
4. Correct use of `step_1` and `step_2`.
5. A brittle wording plateau or genuine instruction improvement.

Likely failures:

- whole-problem passthrough;
- wording-lottery prompts;
- endpoint-artifact syntax leaking into subtasks;
- excessive Math verbosity and truncation;
- aggregators ignoring one predecessor;
- no improvement over generic prompts.

A Stage 3 null is plausible even if routing succeeds, matching the paper’s observation that a 3B model can learn selection before writing strong subtask instructions.

## Stage 4: joint learning

Likely phases:

1. Full workflow-format acquisition.
2. Valid-but-wrong `0.5` plateau.
3. Strongest-endpoint or one-step collapse.
4. Routing tendencies appear before good decomposition.
5. Atomic and Lookup→Math success first.
6. Math→Code and fork/join require much rarer coordinated rollouts.
7. Either stable useful workflows or premature entropy collapse.

Important joint failures include:

- always using the maximum number of calls;
- copying demonstration topology;
- repeated identical subtasks;
- resource shotgun attempts;
- final-worker aggregation bottlenecks;
- ignored dependencies;
- route and wording co-adapting into an uninterpretable local optimum.

## Most useful metrics

Beyond mean reward, track:

- frequencies of `0`, `0.5` and `1`;
- fraction of gradient-bearing groups;
- zero-variance groups;
- endpoint entropy by cell and position;
- full-assignment entropy;
- routing regret versus deployable oracle;
- worker artifact validity and tool success;
- success conditional on each prior node;
- dependency-corruption and counterfactual-consistency results;
- subtask lengths and truncations;
- answer-in-subtask telemetry;
- cache hit rate and worker latency;
- KL drift.

The main payoff of the project is therefore a mechanistic understanding of:

> when hierarchical GRPO has enough reward variation and endpoint advantage to learn routing, when textual instruction learning becomes the bottleneck, and how the two interfere when optimized jointly.

Those dynamics are the part most likely to transfer to a larger Conductor-style system—even if the absolute usefulness of these particular toy workers does not.