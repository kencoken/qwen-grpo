Rev4 is ready in principle. It resolves the previous architectural and scientific objections; I would sign off after a short final specification patch. Nothing below requires redesign.

## Remaining blockers

### 1. Define the routing-only output format

The action table correctly says only `worker_id` is learnable in Stage 0C and Stage 2 ([rev4](/Users/ken/crystalline-sleeping-zephyr-rev4.md:36)), but the parser otherwise expects full workflow JSON.

Use a stage-specific routing schema:

```json
{"worker_ids": [1, 2]}
```

The harness then combines those IDs with fixed subtasks, resources, topology and access. Extra fields should be rejected, not ignored. Otherwise GRPO assigns credit to tokens supposedly outside the routing action space.

Add an acceptance test establishing a bijection between routing completions and the enumerated 3/9/27 worker assignments.

### 2. Resolve the parser/reward contradiction

Legal access patterns are described as parser-rejected ([rev4](/Users/ken/crystalline-sleeping-zephyr-rev4.md:56)), while the reward table assigns an illegal access pattern `0.5` ([rev4](/Users/ken/crystalline-sleeping-zephyr-rev4.md:78)).

I recommend:

| Outcome | Reward |
|---|---:|
| Invalid JSON/schema, wrong field types, step-count violation, illegal topology/access pattern, duplicate resources, over-budget resource request | 0.0 |
| Schema-valid action with unknown handle, denied hard-control authorization, worker/artifact/tool rejection, wrong result | 0.5 |
| Correct executed result | 1.0 |
| Unexpected infrastructure exception | Abort |

Tools should return typed rejections for expected artifact errors. Unexpected exceptions must propagate rather than being caught as `0.5`.

### 3. Remove gold from the executor

The strip test currently lists the final answer among the executor inputs ([rev4](/Users/ken/crystalline-sleeping-zephyr-rev4.md:87)). Split execution and scoring:

```text
terminal_result = executor.execute(action, public_context, registry, endpoints)
reward = scorer.compare(terminal_result, gold_answer)
```

The executor should receive neither the reference graph nor the final answer. The strip test should execute without either, then test scoring independently.

### 4. Append or link the six executable cell specifications

The plan promises these specifications ([rev4](/Users/ken/crystalline-sleeping-zephyr-rev4.md:24)), but does not yet contain them. Because this is now the build specification, add an appendix or linked frozen file containing, for each cell:

- private resource schema;
- public instruction/formula;
- artifact grammar;
- predecessor variable names such as `step_1`;
- parameter ranges and rejection sampling;
- direct reference function;
- ordinary and boundary examples;
- valid counterfactual/intervention generation;
- one-call baseline prompt and payload.

Reference subtasks should be tool-neutral: describe the semantic operation without naming a worker or prescribing its endpoint-specific artifact syntax.

### 5. Define “oracle” and intervention semantics precisely

Full payoff enumeration is excellent, but distinguish:

- **Deployable cell oracle:** assignment selected on construction data, frozen, then evaluated on fresh qualification data.
- **Hindsight upper bound:** per-example maximum over realized assignments; diagnostic only.
- **Best fixed and random assignments.**

The Stage 1 gates and Stage 2 target should use the deployable oracle. A per-example hindsight oracle can exploit worker outcomes hidden from the policy.

Likewise, separate two intervention tests:

1. **Corruption:** mutate an intermediate but retain the original target; correctness should fall.
2. **Counterfactual consistency:** mutate the intermediate, recompute the reference sink, and test whether execution follows it to the new answer.

Missing/skip interventions often prove only that the tool rejects missing input. Valid replacements and counterfactual consistency provide stronger evidence of causal dependency use.

Fix the fork gate wording to:

> Baseline accuracy minus corrupted-branch accuracy ≥20 percentage points for each branch.

Use a paired lower confidence bound.

### 6. Complete the reproducibility path

The SQLite key should not be merely the rendered request hash. Use:

```text
runtime-profile fingerprint
+ selected-endpoint fingerprint
+ canonical rendered request
```

The fingerprint should cover model/tokenizer revisions, chat template, NF4 configuration, token cap, truncation policy, stopping rules, `do_sample=False`, artifact grammar, tool version and visibility/resource policy.

Also add explicitly:

- `calibrate.py` to the implementation stages and file inventory;
- its resumable per-call/per-example schema;
- a named Stage 0C launch profile fixing 3B QLoRA, `beta=0`, LoRA rank, policy limit, group size eight, two prompt groups, worker caps and worker microbatch cap.

The current repository defaults are not the intended experiment, so the checked-in profile is load-bearing.

## Gate refinements

The existing table is good, with three additions:

- Apply the `<2%` parse/truncation gate to each endpoint on its on-contract reference calls. Off-family artifact failures are legitimate low payoff, not endpoint-format failures.
- Make effective routing stakes a gate, not just a measurement. Require a minimum conditional payoff loss when each best endpoint is replaced while other choices remain fixed.
- Pre-register the visible-slice size. Private direct/echo results are leakage checks; visible results measure direct solving and answer smuggling.

Cosmetic variants of one latent program should be treated as one statistical cluster, using paired cluster-bootstrap intervals. Any generator, renderer, prompt, tool, parser or runtime-profile change after qualification should retire that qualification set.

## Compute check

Full payoff enumeration over 500 examples per cell is substantial. Even after factorizing and caching repeated upstream calls, it is on the order of tens of thousands of live worker generations.

Benchmark enumeration on the 100-example construction pass. For fork/join, 100–200 fresh qualification programs may be sufficient if paired confidence intervals are decisive; expand only marginal cells.

The 10k-per-cell tool agreement run should also be a separate recorded acceptance command, not part of ordinary `pytest`.

## Framing verdict

The claim table is now accurate, with one wording refinement:

- Stage 2 fork/join tests endpoint selection within a fixed parallel DAG.
- Constructing the fork/join topology is tested only when topology becomes learnable in Stage 4.

The overall progression is now defensible:

- Stage 2: fixed bundled-endpoint selection under hidden payloads;
- hard authorization: permission routing;
- Stage 3: instruction optimization;
- Stage 4: static joint workflow formulation under partial observability;
- paired visible policies: delegation versus self-solving.

Subject to the six specification fixes above, I consider rev4 implementation-ready.