The Stage 0 architecture is solid, but I would not freeze the Stage 1 data design yet. Your intuition is right: the examples are too simple for studying decomposition—but adding a third trivial operation would mostly compound worker failures. The more important repair is making each dependency causally necessary and separating LLM capability from output-format compatibility.

## Highest-priority amendments

1. **Worker selection is currently confounded with selecting an output grammar.**

The plan deliberately “enforces heterogeneity via output interface” ([plan](/Users/ken/crystalline-sleeping-zephyr.md:31)). If Math, Code and Lookup emit mutually incompatible artifacts, a 20-point specialist advantage may simply mean that only one endpoint’s parser accepts the answer. Stage 2 then learns:

> percentage words → expression endpoint

rather than selecting an LLM based on empirical competence.

Use a common outer result contract for every worker:

```json
{
  "status": "ok",
  "value": {"type": "integer", "data": "17"},
  "artifact": {"kind": "arithmetic_expression", "data": "(43 - 7) / 3"}
}
```

Worker-specific artifacts and tools can remain internal, but report separately:

- outer-contract validity;
- artifact/tool validity;
- semantic answer correctness;
- final workflow correctness.

A particularly informative Stage 1 control would compare:

- one general model behind all three tool interfaces;
- three specialist models using a common answer interface;
- specialist models plus specialist interfaces.

That tells you whether heterogeneity comes from the LLM, the tool permission, or the parser.

2. **The shown decompositions are not causally necessary.**

In `LOOKUP → MATH`, every worker receives the original problem. The Math worker can read `2016` itself and calculate `504`, ignoring the Lookup result. Worse, the 3B Conductor can calculate the answer and issue “return 504” as its subtask.

For every composition family, add these Stage 1 interventions:

- correct dependency;
- dependency removed;
- dependency replaced with a valid value from another instance;
- upstream step skipped;
- direct 3B answer;
- “echo the value embedded in the subtask” worker.

Retain a composition only when the correct dependency materially outperforms the counterfactuals.

For the cleanest causal laboratory, I recommend opaque resource handles: the Conductor sees `ledger L-73`, but only the Lookup endpoint receives its contents. Keep a smaller visible-payload set as a paper-like transfer challenge. This is further from the paper’s information regime, but much better for learning what GRPO is doing.

3. **The CODE example already contains a semantic ambiguity/error.**

For `"marble"` ([data example](/Users/ken/data_generation.txt:18)):

- reversing gives `"elbram"`;
- zero-based even indices produce `"eba"`;
- one-based even positions produce `"lrm"`.

The stated `"ebm"` matches neither. This is important evidence that executing the gold graph through the same implementation does not validate the English rendering: generator and verifier can share the same mistake.

Add:

- explicit indexing language, such as “zero-based indices 0, 2, 4…”;
- hand-checked golden fixtures for every primitive and composition;
- an independent reference evaluator;
- metamorphic tests, such as reverse-twice restoring the input;
- manual review of every template × paraphrase before freezing it.

4. **Stage 1 calibrates a different environment from training.**

Stage 1 uses vLLM, while the live reward path proposes Transformers NF4 workers. Backend, quantization, batching and chat-template differences can change greedy outputs.

Either calibrate with the exact NF4 worker implementation or use vLLM only for screening, then rerun the decisive qualification set through the live backend. I would require approximately 98% per-example reward agreement and no worker-family cell shifting by more than two percentage points.

The cold-start gate should also use the Conductor generation backend used during training, or be explicitly replicated on both.

5. **The cache key is incorrect.**

The listed key omits the original problem ([plan](/Users/ken/crystalline-sleeping-zephyr.md:52)), even though workers receive it. Generic subtasks would therefore collide across different records or questions.

Hash the complete rendered worker request, including:

- original problem;
- subtask and authorized dependency results;
- model and tokenizer commit;
- complete chat template/system prompt;
- backend, quantization, decoding and stop settings;
- context/truncation policy.

SQLite is a safer exact cache than JSONL because it gives atomic writes and unique-key semantics. JSONL remains suitable for traces.

6. **The prompt demonstrates an illegal workflow.**

`workflow_max_steps=2` ([plan](/Users/ken/crystalline-sleeping-zephyr.md:71)) conflicts with the “independent→final” demonstration ([plan](/Users/ken/crystalline-sleeping-zephyr.md:95)), which requires two leaves plus an aggregator—three calls.

Either remove that demonstration or support three steps from the outset. Every few-shot example should execute successfully through the exact parser and worker runtime, not merely parse as JSON.

7. **Calibration selection is currently circular.**

Templates are tuned and retained using the same calibration outcomes later used to establish specialization. The current `calibration/dev/test` split also lacks an explicit Stage 2–4 training pool.

I would use:

- `construction`: freely inspected while designing templates;
- `qualification`: unseen templates used once for the Stage 1 gate;
- `train`: frozen Stage 2–4 distribution;
- `dev`: checkpoint/configuration selection;
- `test`: touched once.

If qualification causes a redesign, retire and version that qualification set. Also analyze paraphrases as clustered repeated measurements—not as five independent observations.

With only 10–12 templates total, template-level generalization claims will be weak regardless of how many numeric instances are sampled. Keep the operation vocabulary small, but add several independently authored renderers per operation and composition in each relevant split.

## Should three-step tasks return?

Yes—but as a targeted diagnostic first, not as an unconditional 10% mixture.

Under a rough independence approximation:

- 70% node accuracy gives about 49% two-step success;
- 70% node accuracy gives about 34% three-step success.

So another trivial step mainly reduces positive rewards. Three steps become useful when they introduce a genuinely new orchestration decision: parallel work, aggregation, dependency preservation or verification.

I recommend making the generator support three-node DAGs now and adding a Stage 1 challenge stratum of roughly 100–200 examples per topology:

| Tier | Purpose | Initial use |
|---|---|---|
| Atomic/easy two-step | Parser, executor and routing smoke | Stage 0 and early Stage 2 |
| Causally necessary two-step | Main routing/decomposition laboratory | Core Stage 1–4 candidate |
| Three-step linear | Dependency preservation | Stage 1 diagnostic |
| Two leaves → aggregator | Parallelism, access and aggregation | Stage 1 diagnostic |

A good fork/join example is:

```text
Task:
Retrieve Cedar's units from ledger L-18.
Count words ending in "s" in asset W-9.
Return units × count + 3.

Private Lookup payload:
Cedar.units = 14

Private Code payload:
["glass", "reed", "moss", "oak", "iris", "stone"]

Reference DAG:
n0 = lookup(...)                 # 14
n1 = code(count_suffix(...))     # 3
n2 = math(n0 * n1 + 3)           # 45
```

The first two calls form one parallel wave; the third aggregates. That teaches more than an arbitrary `LOOKUP → MATH → CODE` chain.

I would admit three-step tasks into Stage 2 at around 10% only if, on their own stratum:

- intended node accuracy is roughly 85% or better;
- oracle workflow success is at least 55–60%;
- oracle beats the best direct worker by at least 15 points;
- oracle beats the best two-call shortcut;
- removing or shuffling either dependency reduces success materially;
- cold-start samples contain successful and unsuccessful workflows rather than uniformly returning `0.5`.

## Important implementation gaps

The repository integration needs a little more structure than the plan currently allows:

- A module-level `reward_funcs` list cannot receive `workflow_max_steps`, model revisions, run name, cache path or token caps. Introduce a configured `TaskRuntime` or `build_runtime(config)` lifecycle with `close()`.
- The current [eval.py](https://github.com/kencoken/qwen-grpo/blob/conductor/eval.py) assumes raw `<answer>` completions. A workflow requires an execution-result object containing `parse_valid`, executed answer, correctness, trace ID, calls, latency and failure kind.
- Use a subprocess boundary between vLLM plan generation and worker execution; deleting a vLLM object in-process is not a reliable GPU cleanup boundary.
- Add a reproducible Stage 1 calibration command. No proposed file currently runs the matrix, paraphrase probe, oracle workflows, confidence intervals and gate report.
- Distinguish policy failures from infrastructure failures. A valid-but-wrong worker result can earn `0.5`; an OOM, corrupted cache or trace-write failure must abort the update rather than become training reward.
- Benchmark a forced-valid, cache-disabled worst case. An untrained Conductor may otherwise emit cheap malformed/one-step workflows and make the projected runtime look artificially good.
- Replace the fixed-plan GSM8K “training” smoke with two tests: a non-training executor smoke and a real one-step workflow smoke whose sampled Conductor output actually affects reward.
- Use an exact typed value layer. `normalize_number` is not safe for strings, identifiers such as `"0012"`, rationals or lists.
- Store run-local traces under `runs/<run_name>/…`, with a versioned manifest and stable example/template/sample IDs.

## Assessment of `risks.txt`

The existing risk assessment correctly identifies tool-as-output-evaluator, generator complexity, shared-contract changes and two-phase evaluation. But it underweights the risks most likely to invalidate the scientific conclusion:

- interface compatibility masquerading as LLM specialization;
- unused dependencies and Conductor answer-smuggling;
- calibration-selection bias;
- backend drift between calibration and training;
- shared generator/verifier bugs;
- insufficient template-level sample size;
- infrastructure failures becoming policy rewards;
- optimistic cached/short-workflow throughput measurements.

My recommendation is therefore: proceed with Stage 0 after fixing the runtime, cache, evaluation and demonstration contradictions; redesign and qualify the Stage 1 data before freezing it. Keep the current easy examples as a plumbing tier, add causally necessary two-step tasks as the main laboratory, and implement one carefully chosen three-node topology as a measured challenge rather than assuming that more steps automatically mean a better orchestration problem.