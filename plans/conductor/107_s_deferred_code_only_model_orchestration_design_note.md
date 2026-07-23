# Deferred design note — Code-only model and prompt orchestration

**Status: DEFERRED, NON-NORMATIVE DESIGN NOTE.** This document records a
possible follow-on experiment and the hypotheses already motivated by D16.
It is not a preregistration, does not amend `106_s`, and authorizes no model
screen, data generation, prompt iteration, qualification, or training run.
Exact treatments are deliberately left open until the mixed-environment
experiment has produced training-dynamics evidence.

## 1. Why record this now

The mixed Lookup/Math/Code environment is primarily a controlled experiment
in routing among model-plus-tool endpoints. Its strong tool-family
heterogeneity is useful for learning how GRPO behaves, but it permits the
critique that apparent “model orchestration” is mostly post-training for tool
selection.

D16 has exposed a cleaner nested treatment. Under `task_last` and the global
rev10 prompt bundle, the generic 1.5B and generic 3B Code workers share:

- the same public and private inputs;
- byte-identical rendered requests;
- the same Code system-prompt bytes;
- the same artifact grammar and Code interpreter;
- the same resource authorization;
- the same NF4, greedy decoding, caps, and singleton policy; and
- the same terminal scorer.

Only the model checkpoint changes. On the adaptively consumed `worker_dev`
population, their Code outcomes were:

| outcome | cases |
|---|---:|
| both correct | 235 |
| only generic 1.5B correct | 22 |
| only generic 3B correct | 13 |
| neither correct | 0 |

This is post-hoc development evidence, not a population estimate. It does,
however, motivate a future environment in which all selectable workers use
the same Code tool and the policy learns conditional model selection rather
than tool-family selection.

The idea is recorded now to prevent the later design from being reconstructed
solely around whichever dynamics look interesting after the mixed run. Its
exact implementation remains adaptive by design and must receive a new
preregistration before execution.

## 2. Intended scientific question

The narrow primary question would be:

> Can GRPO learn which frozen language model will most reliably translate a
> public natural-language Code task into one shared executable DSL, when
> request format, prompt, tool, grammar, authorization, and decoding are held
> fixed?

This is a stronger causal model-orchestration test than the endpoint-family
comparison. A successful result would still be modest: it could reflect
model-specific protocol compliance or language compatibility rather than
general reasoning specialization. That distinction must remain visible in
reporting.

The experiment would initially learn model identity only. It would not learn
topology, resource access, the Code grammar, or free-form subtask wording.

## 3. Why it should follow the mixed experiment

The mixed environment provides a more forgiving diagnostic setting because
Lookup/Math/Code advantages should be frequent and large. Complete it first
to establish that the training system can learn opaque endpoint identities
under terminal reward.

Before activating this note, the default evidence package should include:

1. the Stage-0C policy-dependent mixed-environment smoke;
2. Stage-1 construction and qualification of the mixed payoff surface; and
3. at least one mixed-environment Stage-2 signal seed or equivalently
   informative pilot, not only an inference benchmark.

The following observations should be carried forward:

- routing-schema validity and time to saturation;
- sampled support for every worker id;
- reward-level and zero-variance-group frequencies;
- group size and temperature adequacy;
- entropy decay and premature endpoint collapse;
- atomic versus two-step versus fork/join learning order;
- whether the policy explores both Code models;
- whether it collapses to the best fixed Code model;
- renderer and shallow-language sensitivity;
- the effect of demonstrations on initial worker frequencies;
- checkpoint-to-checkpoint stability and useful stopping rules; and
- measured payoff-materialization, storage, and per-seed 4090 costs.

These results may inform the later design. They do not count as independent
evidence for the code-only claim.

## 4. Hypotheses recorded before the mixed run

These are qualitative predictions, not frozen gates.

### H1 — Family routing will be learned before model routing

The mixed policy should acquire Lookup/Math/Code identity more easily than
the 1.5B/3B distinction because wrong-family failures are frequent and large.
Aggregate mixed-environment improvement may therefore occur without useful
within-Code selection.

### H2 — Best-fixed-Code collapse is the main mixed-environment risk

The 1.5B worker wins more retained disagreements than the 3B worker. A policy
may learn “Code means 1.5B” and stop exploring the rarer 3B-favouring region.
This would motivate a disagreement-enriched code-only laboratory rather than
count as evidence that model selection is unlearnable.

### H3 — A binary fixed-prompt task should be a strong positive control

With two Code workers and group size 8, both choices should ordinarily appear
within a group. If a publicly predictable disagreement surface exists, the
credit-assignment problem should be substantially easier than a multi-node
`4^S` workflow.

### H4 — Some complementarity will be renderer- or context-dependent

The retained errors cluster by renderer, block order, global context, and
task scope. A model router may first learn language-to-model compatibility.
Semantic, renderer-only, and bag-of-words controls will therefore be needed.

### H5 — Smaller models are not automatically useful workers

A model below 1.5B may avoid over-composition, but it may instead be strictly
dominated through parse failure. It should enter the pool only if it has a
reproducible unique-win region or if a separate cost-aware experiment makes
its lower inference cost relevant.

### H6 — Model-by-prompt interactions may be more learnable than free prompt
generation

D16 suggests that prompt amendments repair one failure surface while creating
another, with model-conditional effects. A finite prompt library may therefore
support useful joint model/prompt selection before the project attempts an
open natural-language action space.

## 5. Candidate experimental progression

The later preregistration should select the smallest useful prefix of this
progression. Later phases are not automatic consequences of earlier success.

### Phase A — Model discovery under one fixed prompt

Screen a small same-family scale ladder, provisionally including models around
0.5B, 1.5B, and 3B, under one exact Code prompt and request contract. The exact
repositories and revisions are not frozen here.

The discovery question is whether each candidate is nondominated on public,
repeatable task strata. Do not retain a model merely to create a larger pool.

### Phase B — One-step code-only model routing

Use the smallest nondominated pool, preferably beginning with the established
1.5B/3B pair. The harness supplies one fixed reference Code subtask and the
policy emits only a model/worker id. All worker-side conditions remain fixed.

This is the clean primary model-selection experiment.

### Phase C — Multi-step code-only routing

Only after Phase B learns, introduce predecessor-dependent or multi-node Code
tasks using existing legal semantics where possible. This tests multi-step
credit assignment without reintroducing different tool families.

The first tranche should not extend the DSL merely to manufacture a topology.
Any tool or grammar change requires its own review and agreement battery.

### Phase D — Discrete model-plus-prompt selection

Cross the retained models with a small, reviewed prompt-template library. The
policy emits a model id and a prompt-template id. Because the action space is
finite, the complete model×prompt payoff surface can be precomputed.

This tests configuration orchestration and model–prompt interaction while
retaining stable credit assignment and exact controls.

### Phase E — Compositional or free-language directives

First consider selecting a bounded set of prompt clauses. Free natural-
language directives should be attempted only if discrete prompt selection
shows material, qualification-stable stakes and a live-worker CE0 passes.

## 6. Data-construction principles

### 6.1 Discovery may characterize disagreement; final instances may not be
filtered individually

A new discovery-only namespace may evaluate a broad factorial generator
against all candidate models. It may identify regions in which model outcomes
differ.

Do not define the final dataset by retaining individual examples only when
the realized models disagree. That can elevate accidental hidden-value
failures into an apparently learnable routing problem.

Instead:

1. characterize disagreement by public generator factors;
2. select complete strata, templates, or parameter bands;
3. freeze their unconditional sampling rule; and
4. draw fresh construction, qualification, train, dev, and test instances
   from disjoint namespaces.

Any active-learning or adversarial proposal stage remains development data.

### 6.2 The winner must be predictable from public information

Oracle complementarity alone is insufficient. If model preference depends on
private resource values or idiosyncratic deterministic mistakes that cannot
be inferred from the public observation, no policy can learn the oracle.

For each proposed stratum, report:

- unique-win rates by model;
- both-correct and neither-correct rates;
- oracle minus best-fixed-model accuracy;
- within-stratum consistency;
- predictability from allowed public semantic factors;
- predictability from renderer and shallow lexical features alone; and
- transfer to held-out templates and fresh parameter values.

### 6.3 Keep laboratory and ecological distributions distinct

Two evaluation distributions are desirable:

1. **Routing laboratory:** deliberately increases the mass of publicly
   predictable disagreement strata so GRPO receives enough model-selection
   signal to study learning dynamics.
2. **Broad/ecological:** samples a wider frozen Code generator without
   disagreement balancing and measures how frequently orchestration is useful
   under that distribution.

Success in the laboratory establishes learnability, not natural prevalence.
Both distributions and their sampling weights must be reported.

### 6.4 Hold out language structure, not only values

Use fully crossed development renderers, then hold out at least one template
or semantic paraphrase family for evaluation. Instance-only splits would not
distinguish model routing from memorizing a renderer compatibility table.

## 7. Candidate public factors to investigate

The existing generator and D16 failures motivate, but do not freeze, the
following axes:

- atomic versus composed sequence expressions;
- expression nesting depth;
- literal parameters versus predecessor-derived parameters;
- local Task versus a larger Problem containing downstream operations;
- task-first, goal-first, resource-first, and bound-variable language;
- relevant versus irrelevant global constants;
- placement and salience of resource handles;
- required use of the literal identifier `resource`;
- direct versus indirect reference to `step_1`;
- threshold and index boundary regimes;
- distractor operations resembling prompt demonstrations; and
- clause order independent of the underlying operation.

Examples of desired regimes include:

- **scope discipline:** a local `count_gt(stable_unique(resource), t)` task
  embedded in a public Problem that describes later rotation or indexing;
- **predecessor binding:** a sequence operation whose legal index or rotation
  comes from `step_1`, rather than recomputing the public arithmetic;
- **identifier discipline:** a visible handle is present but the DSL requires
  the literal token `resource`;
- **nested translation:** a legal composition such as deduplicate → rotate →
  select, with depth varied independently of renderer; and
- **matched paraphrase:** identical semantics rendered with different clause
  order and binding language.

The discovery stage must determine which, if any, yield stable bidirectional
model advantages. The examples above are not assumed treatments.

## 8. Candidate-model admission principles

Every screened model must use the same:

- endpoint family and Code tool;
- system-prompt bytes for the fixed-prompt phase;
- canonical user-message blocks;
- resource authorization;
- artifact parser and rejection semantics;
- token cap, stop rules, and greedy decoding; and
- singleton execution policy.

A model should be retained only when its inclusion changes the attainable
payoff frontier on fresh discovery support. Useful evidence includes a stable
unique-win stratum, a meaningful oracle gain, and public predictability of
that gain.

A smaller model that is correct whenever a larger model is correct but never
uniquely correct is dominated under an accuracy-only reward. If lower call
cost is to make it selectable, define a separate cost-aware experiment with a
frozen cost measure, penalty, and accuracy floor. Do not silently add latency
to the existing `0 / 0.5 / 1` reward.

## 9. Required controls and reporting

At minimum, a code-only routing experiment should compare:

- best fixed model;
- exact-uniform model choice;
- frequency-matched random choice;
- construction-frozen semantic router;
- renderer-only router;
- shallow bag-of-words router;
- trained GRPO model router; and
- hindsight per-example oracle, diagnostic only.

Report separately:

1. terminal accuracy;
2. signed gap from the construction-frozen deployable router;
3. incremental gain over the best fixed model;
4. selection frequency and entropy by public stratum;
5. model-specific unique-win capture;
6. renderer/template generalization; and
7. calls, latency, and memory as descriptive costs.

A useful decisive control is a forced-family binary task in which the harness
has already fixed the Code endpoint family and the Conductor chooses only
between the 1.5B and 3B models. If the full mixed policy improves but this
control does not beat the best fixed Code model on qualification data, the
mixed result should be described as endpoint/tool routing rather than useful
model selection.

## 10. Prompt-learning ladder

“Learning prompts” can refer to materially different experiments. Keep them
separate.

| level | policy learns | execution implication |
|---|---|---|
| 1 | fixed prompt; model id only | finite model surface, precomputable |
| 2 | model id + prompt-template id | finite factorial surface, precomputable |
| 3 | model id + bounded prompt clauses | finite/compositional surface, often precomputable |
| 4 | model id + free-language directive | open action space, live worker calls |

For levels 2–3, prompt families might encode scope, identifier discipline,
predecessor use, or terse grammar-first translation. Their exact wording and
cardinality must be reviewed only after the fixed-prompt model-routing result.

For level 4:

- keep the immutable reference Task in a separate block;
- place learned text in a bounded directive slot that cannot alter resource
  authorization;
- keep the Conductor blind to private payloads and gold answers;
- retain answer-in-instruction and task-copy telemetry;
- cap directive length and reject extra action fields;
- compare against the exact reference and generic directives;
- keep every worker frozen; and
- treat renderer-specific “magic phrases” as compatibility effects, not
  decomposition skill.

Do not jointly post-train the worker models in the first prompt-learning
experiment. Moving workers would make the payoff surface non-stationary and
confound controller learning with worker improvement.

## 11. RTX 4090 feasibility framing

The finite routing and prompt-selection phases are expected to be the
straightforward cases:

- materialize each frozen model or model×prompt outcome once;
- unload workers before Conductor GRPO;
- train a 1.5B or 3B QLoRA Conductor against immutable payoff surfaces; and
- reuse those surfaces across seeds after provenance validation.

A 0.5B/1.5B/3B NF4 worker screen should be plausible on a 4090, but exact
co-residency, latency, and parameter counts must be measured rather than
assumed. Sequential loading is acceptable during one-time materialization.

Free-language directives cannot be exhaustively precomputed. With group size
8, two prompt groups per update, and 250 updates, the nominal upper bound is
approximately 4,000 live worker calls before cache reuse. Whether this is
acceptable depends on directive length, worker caps, co-residency, and
Conductor training time. It requires a separate CE0 measuring:

- worker-only and joint peak reserved VRAM;
- singleton calls per second by model;
- reward-function blocking time;
- cache reuse under generated directives;
- projected pilot and full-seed duration; and
- the simpler sequential/precomputed alternatives.

A 1.5B Conductor is a reasonable first free-directive pilot if the 3B
training layout is unnecessarily expensive; emitting a model id and short
directive need not require the larger policy. This is a future measured
choice, not a decision in this note.

## 12. Decisions intentionally left open

Do not freeze until the mixed evidence package exists:

- exact model repositories, revisions, and pool cardinality;
- whether the 0.5B candidate is nondominated;
- Code request scope and fixed prompt revision;
- discovery namespace name and size;
- generator factors and parameter bands;
- routing-laboratory mixture weights;
- broad/ecological distribution;
- template and semantic holdouts;
- quantitative admission and qualification gates;
- Conductor size and launch settings;
- group size, temperature, and curriculum;
- prompt-template text and cardinality;
- whether multi-step Code adds useful credit assignment;
- whether a cost-aware objective is worth a separate arm; and
- whether free-language prompt learning passes CE0.

## 13. Return-to-this-note checklist

After the first mixed training evidence is available:

1. summarize the transferable dynamics listed in §3;
2. state explicitly which design choices are being adapted from those results;
3. create a new, bounded discovery preregistration;
4. allocate fresh code-only discovery identities;
5. screen the smallest same-interface model set;
6. characterize public disagreement strata without instance filtering;
7. decide whether a learnable and practically meaningful payoff surface
   exists;
8. freeze the initial fixed-prompt code-only experiment;
9. protect fresh qualification before inspecting it; and
10. defer prompt learning again unless model-only routing succeeds.

If no qualification-stable, publicly predictable model complementarity is
found, close the code-only branch with that null result. Do not manufacture a
routing task by selecting isolated model mistakes.

## 14. Relationship to the main experiment

The two tracks answer different questions:

- **Mixed environment:** how GRPO learns opaque routing under strong,
  constructed model-plus-tool heterogeneity and multi-step terminal credit.
- **Code-only environment:** whether those lessons transfer when the tool and
  interface are equalized and only the frozen model policy changes.
- **Model-plus-prompt extension:** whether a controller can learn
  model-conditional instruction policies after model selection itself works.

The code-only track may ultimately provide the project's cleanest evidence
for model orchestration. It should not displace the mixed experiment before
the latter has supplied the training intuition and validated infrastructure
that make the harder follow-on interpretable.
