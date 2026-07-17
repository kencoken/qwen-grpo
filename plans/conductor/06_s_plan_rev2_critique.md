The revision is scientifically much stronger, but the other reviewer’s concern is valid: it has become an experimental platform rather than an “ugly-and-small” Stage 0–1 implementation. Incrementally populating the data does not fully control complexity if all fourteen modules, seven split roles, dual evaluators, renderer tiers, audits and interface factorials are built before the first routing run.

I would preserve the conceptual design but stage the implementation itself much more aggressively.

## Overall verdict

Keep these parts:

- typed reference programs;
- common executor-level worker results;
- explicit resource and dependency isolation;
- runtime lifecycle and infrastructure-failure separation;
- qualification on the live worker backend;
- causal dependency interventions;
- policy-dependent GRPO smoke;
- cell-level rather than instance-level selection.

Trim or defer:

- generic support for six output types;
- a second extensible DAG evaluator;
- rule induction;
- semantic and counterfactual renderer engines;
- the complete ML shortcut-audit suite;
- specialist/general-model factorial;
- three-step linear workflows;
- `test_soft` as a separate data-generation system;
- possibly persistent caching and subprocess evaluation until the first Stage 2 run requires them.

The statement “adopt the architecture wholesale, populate incrementally” ([revision](/Users/ken/crystalline-sleeping-zephyr-rev2.md:9)) should become:

> Preserve extension points for the full architecture, but implement only one end-to-end vertical slice before adding another abstraction.

## A smaller v0

I would initially support only integer-valued workflows:

- public step/final outputs: `Integer`;
- private resources: keyed integer records and integer lists;
- exact fractions allowed internally only when they resolve to integers;
- no Boolean, Rational, free Text or generic IntegerList outputs yet.

Start with five cells:

1. Atomic Lookup.
2. Atomic Math.
3. Atomic Code.
4. Lookup → Math.
5. Math → Code.

Then add one fork/join diagnostic:

6. Lookup + Code → Math.

Use one transparent renderer with two manually authored cosmetic variations. Defer rule induction until this environment produces a routing learning curve.

This still tests:

- selective delegation on atomic cases;
- different endpoint orderings;
- typed intermediate transport;
- terminal credit assignment;
- wave batching and aggregation through the fork/join cell.

It avoids building a general workflow language before knowing whether the basic training signal exists.

## The worker JSON question

I would not ask the 1.5B workers to produce JSON at all.

Short JSON might work at temperature zero, but a strict `<2%` failure rate should not be assumed—especially for Math-1.5B, which may emit reasoning, Markdown fences or malformed quoting. More importantly, frozen-worker JSON compliance is not the phenomenon you are trying to study. It would introduce exogenous reward noise for no scientific benefit.

Separate the model’s textual output from the executor’s structured result.

A worker emits a minimal tagged artifact:

```text
<value>28</value>
```

or:

```text
<artifact>(3 * v0) - 4</artifact>
```

or:

```text
<artifact>select_at(Q42, v0)</artifact>
```

The host wrapper parses or executes it and constructs:

```python
WorkerResult(
    status="ok",
    value=IntegerValue(47),
    artifact_valid=True,
    tool_executed=True,
)
```

Allow reasoning outside the tag and extract exactly the final complete tag. The expected type is already known from the workflow node, so the model does not need to serialize it.

Keep JSON for the 3B Conductor workflow because variable-length steps, worker IDs, resources and dependencies justify it—and Conductor format learning is part of the experiment.

One unresolved choice in the revision should also be settled now:

- If workers return final values directly, you are studying model competence.
- If workers emit artifacts that tools execute, you are studying model-plus-tool endpoints.

For the initial toy, I recommend the second. Make the executed tool result authoritative for correctness. A free-form claimed answer should not override it.

## Yes, the Conductor may directly solve MATH and CODE

This is not merely possible; it is quite plausible.

The Conductor is a 3B model while the frozen workers are 1.5B. Although Math-1.5B and Coder-1.5B have specialist training and tools, the 3B Conductor can probably solve many of the proposed algebra, percentage, indexing and short sequence transformations itself.

It could then emit:

```text
Ask Worker 2 to return 47.
```

If Worker 2 echoes `47`, terminal reward cannot distinguish this from genuine decomposition.

In that condition, the experiment would principally test whether GRPO learns to:

- produce a valid hierarchical action string;
- compute answers inside the policy;
- transport those answers through a worker;
- select any endpoint capable of echoing them.

That is a real training dynamic, but it is not evidence of division of labour or heterogeneous worker selection.

The capability matrix therefore needs another row:

> untrained 3B Conductor answering directly, without workers.

Run this per atomic and composition cell. Also include:

- an echo worker that returns values embedded in the subtask;
- a no-op generic worker;
- answer-in-subtask telemetry;
- dependency removal and replacement;
- transplanting a learned subtask onto a matched instance.

If the direct Conductor or echo worker approaches oracle workflow accuracy, that cell does not establish orchestration.

## Is a private environment a hack?

Private state is not inherently a hack. It is a causal intervention: it removes the self-solving strategy so you can study routing and dependency learning in isolation.

But the current formulation couples two separate ideas:

1. hiding values from the Conductor;
2. giving each value exclusively to one particular worker.

The first controls self-solving. The second can make the desired route tautological.

If only the Lookup worker is permitted to see `Q17`, then a Lookup advantage says little about model competence. The experiment is learning an access-control matrix.

I recommend separating visibility from authorization.

| Condition | Conductor visibility | Candidate-worker visibility | What it tests |
|---|---|---|---|
| Primary causal condition | Payload hidden | Every candidate for that node receives the same local payload | Empirical model/tool selection without Conductor self-solving |
| Hard-routing control | Payload hidden | Only one endpoint is authorized | Permission and tool routing |
| Visible condition | Payload visible | Shared | Self-solving, answer smuggling and paper-like external validity |

“Every candidate receives the same local payload” does not mean every worker sees the whole problem. For a particular node, whichever worker is selected receives:

- the explicitly requested resource;
- the assigned subtask;
- authorized predecessor values.

This preserves causal decomposition while allowing a fair comparison between workers.

The workflow action should explicitly request resources:

```json
{
  "worker_id": 2,
  "resources": ["Q17"],
  "access": [],
  "subtask": "Retrieve Rowan's crate count."
}
```

The executor must reveal resources based solely on this sampled action—not by consulting the reference DAG and silently supplying what the intended step needed.

I would also make the visible condition a paired execution mode over the same latent programs, rather than a separate `test_soft` distribution. That isolates visibility cleanly:

```text
same program + same rendering + private payload
same program + same rendering + visible payload
```

A failure after changing visibility then has a precise interpretation.

## What the stages would actually establish

| Experiment | Defensible conclusion |
|---|---|
| Stage 2, hidden Conductor and equalized worker observations | GRPO can learn an empirical worker/tool payoff mapping from terminal reward |
| Stage 2, worker-exclusive resources | GRPO can learn fixed permission and endpoint routing |
| Stage 3 | GRPO can improve subtask instructions, but only if reference subtasks beat generic prompts |
| Stage 4, private condition | GRPO can jointly route and formulate static workflows under partial observability |
| Paired visible condition | Whether the learned policy delegates when it could self-solve, and whether answer smuggling emerges |
| Fork/join | Whether it can construct and execute a fixed parallel DAG—not dynamic or output-conditional adaptation |

This is still a valuable progression. It just needs careful naming. The private condition is the clean mechanics laboratory; the visible condition is the bridge toward the Conductor paper’s more natural setting.

## Tasks that reduce direct solving without privacy

Private resources are not the only option. You can also construct visible tasks where the worker’s tool creates a genuine capability advantage:

- exact arithmetic over several large integers;
- modular expressions where transcription is easy but mental execution is unreliable;
- transformations over 50–100 sequence elements;
- randomly generated per-instance sequence programs;
- computed-key lookups into large distractor-heavy tables.

The Conductor can recognize and describe the computation but is unlikely to execute it reliably. This is closer to natural delegation.

The gate remains empirical:

- direct Conductor at least 15–20 points below the best composed workflow;
- correct worker endpoint materially above alternatives;
- tool result authoritative;
- generic/echo baselines substantially below reference workflows.

I would include a small public-but-tool-demanding stratum alongside private resources. That lets you distinguish:

- delegation because information was unavailable;
- delegation because a specialist/tool was genuinely more capable.

## Specific revisions to the plan

A few concrete corrections are also needed.

1. **Integer canonicalization**

The comment `"0012" ≠ 12` ([revision](/Users/ken/crystalline-sleeping-zephyr-rev2.md:19)) is only true when the first value is Text or Key. For Integer, either reject `"0012"` as a noncanonical wire form or canonicalize it to `12`.

2. **Resource privacy claim**

The statement that private resources mean “single workers cannot solve alone” ([revision](/Users/ken/crystalline-sleeping-zephyr-rev2.md:67)) is too broad—atomic tasks are intentionally single-worker—and it conflates information hiding with exclusive permissions.

3. **No-answer-in-prompt invariant**

Literal substring absence ([revision](/Users/ken/crystalline-sleeping-zephyr-rev2.md:109)) will produce false failures with small integers. Test provenance instead: renderers must never read private payloads or derived node values. Chance textual collisions are harmless.

4. **Worker protocol timing**

Stage 0 depends on `contract.py`, prompts and runtime, but JSON versus tagged output is not selected until the Stage 1 pilot ([revision](/Users/ken/crystalline-sleeping-zephyr-rev2.md:132)). Select the tagged protocol now.

5. **Cross-backend agreement**

Because decisive results are rerun on live NF4 Transformers, 98% per-example agreement with vLLM should be diagnostic, not a hard gate. Require that screening does not change the cell-level conclusion.

6. **Transparent data versus shortcut audit**

TF–IDF may route transparent tasks well because their words communicate legitimate operations. That should not block routing-only Stage 2. Separate two decisions:

- harness-ready for Stage 2;
- semantically demanding enough for Stage 3–4 claims.

The semantic/counterfactual renderer and full shortcut audit should gate the latter.

7. **Cold-start sample**

With 32 groups, the 10% success-diversity criterion is only four groups. Treat it as a smoke or increase to at least 64 groups and report it separately by atomic, two-step and fork/join strata.

8. **Independent evaluator**

Do not build two general DAG interpreters. Use one tiny direct reference function per primitive, separate runtime tool code, hand-calculated fixtures and metamorphic tests. This gives useful independence without doubling the framework.

## Recommended staging

### Stage 0A: minimal environment

- Integer outputs only.
- Three atomic and two causal two-step cells.
- Two transparent renderings.
- Tagged worker artifacts.
- Direct reference functions, fixtures and dependency tests.
- Mock executor and action-controlled resource disclosure.

### Stage 0B: runtime

- Real worker pool.
- Wave batching.
- Runtime lifecycle and trace schema.
- In-memory cache initially; SQLite only if resumability is immediately useful.
- Offline executor smoke.

### Stage 0C: trainer integration

- Genuine policy-dependent workflow smoke.
- Forced-valid, cache-disabled throughput benchmark.
- Mocked infrastructure-failure tests—do not deliberately corrupt the live CUDA process with a real OOM.

### Stage 1A: minimum qualification

- 100 examples per cell on the live backend;
- expand passing cells to 500;
- worker and direct-Conductor capability matrix;
- dependency remove/replace/mutate;
- generic and echo baselines;
- stratified cold-start gate;
- random/fixed routing controls.

### Only after that passes

- fork/join;
- semantic/rule-induction renderer;
- full shallow-router audit;
- specialist-versus-general factorial;
- paired visible condition;
- persistent caching and full evaluation integration.

The revised plan’s central scientific ideas are worth keeping. The key correction is to stop treating all of them as prerequisites for the first routing-only experiment. A clean private-resource vertical slice can answer whether GRPO learns hierarchical endpoint routing; a paired visible condition can then answer the much more interesting question of whether it still orchestrates when the Conductor itself is capable of solving the task.