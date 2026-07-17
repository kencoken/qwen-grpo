Rev3 is close. It resolves the over-engineering problem and now has an appropriately narrow claim: Stage 1 certifies a routing harness, not semantic orchestration. I would approve the overall direction after one short specification pass.

The remaining problems are mostly unresolved contracts rather than architectural flaws.

## Must resolve before implementation

### 1. Stage 2 must vary only the worker ID

The workflow action currently includes `"resources": [...]` ([rev3](/Users/ken/crystalline-sleeping-zephyr-rev3.md:38)). If Stage 2 learns both worker and resource selection, it no longer isolates routing.

For routing-only Stage 2, provide:

- reference topology;
- reference subtasks;
- resource handles;
- predecessor access;
- number of calls.

Make only `worker_id` learnable. Resource selection and topology can become learnable in Stage 4.

The conclusion should then be:

> GRPO learns fixed endpoint selection on a transparent typed environment with hidden payloads.

That is more precise than the present “empirical worker/tool payoff mapping.”

### 2. Resource requests need hard operational limits

A list-valued resource field lets a policy request every resource in one call and bypass the intended DAG. The executor should impose task-independent rules:

- handles must belong to the current instance’s public manifest;
- at most one private resource per step in v0;
- no duplicate handles;
- fixed maximum calls and total resource requests;
- downstream aggregation uses predecessor values, not re-requested upstream resources.

For the v0 action space, explicitly permit only:

```text
[none]                 atomic
[none, all]            two-step chain
[none, none, all]      fork/join
```

Reject patterns such as `[none, all, none]`. Otherwise “wave batching by depth” is ambiguous.

The resource registry must also be instance-scoped: a handle from another example must never resolve accidentally.

### 3. Settle the worker/tool contract completely

The current protocol permits either `<value>` or `<artifact>` while saying the tool result is authoritative ([rev3](/Users/ken/crystalline-sleeping-zephyr-rev3.md:23)). There is no authoritative tool result when only `<value>` is emitted.

For the main endpoint-routing condition, I recommend:

- every tool-required endpoint emits exactly one `<artifact>…</artifact>`;
- the selected endpoint determines the available artifact grammar and tool;
- the host executes it and constructs the integer `WorkerResult`;
- duplicate, mixed or unexpected terminal tags are invalid;
- free `<value>` answers are reserved for an explicit answer-only control.

This makes the experiment unambiguously about model-plus-tool endpoints. If tools were equalized as well, it would instead test model selection; that can be a later factorial.

Also define that an invalid artifact or worker parse failure leaves a structurally valid workflow at reward `0.5`, not `0`.

### 4. Sampled execution must not consult the reference DAG

“Expected type comes from the workflow node” is risky because a sampled free-form step has no legitimate mapping to a reference node.

Since every v0 step returns an integer, make the execution contract globally integer-valued. The reference program should be used only for:

- dataset generation;
- final-answer verification;
- reference workflows and diagnostics.

A useful test is to delete all reference-node metadata after generation and confirm that an arbitrary sampled workflow still executes identically using only:

- public prompt and manifest;
- instance resource registry;
- sampled action;
- endpoint definitions;
- final answer.

### 5. Two data specifications are inconsistent

Private resources are restricted to keyed integer records and integer lists, but the operator set contains `suffix-count` ([rev3](/Users/ken/crystalline-sleeping-zephyr-rev3.md:49)). Replace this with an integer predicate such as `count_greater_than`.

Similarly, the hidden Math cells require a numeric resource type. Otherwise the operands must be public and the Conductor can solve them. A concrete Math resource could privately contain:

```text
a = 83719
b = 43
c = 1
```

while the public task says:

```text
Q41 contains integers a, b and c.
Evaluate (a × b − c) ÷ 6 exactly.
```

Whichever candidate worker is selected receives the same local payload in the primary condition.

Each of the six cells should get an executable specification before coding:

- parameter ranges;
- rejection rules;
- one hand-calculated example;
- intervention-generation rules;
- one-call shortcut baseline.

### 6. Restore exact qualification thresholds

Stage 1 says that passing cells expand from 100 to 500 examples, but “passing” is underspecified.

Use the 100-example run only for construction screening. Passing cells should then receive a fresh, frozen qualification sample. Suggested gates:

- artifact parse failure below 2%;
- truncation below 2%;
- best endpoint accuracy at least 75%;
- lower confidence bound on best-versus-runner-up payoff at least 20 points;
- two-step oracle success at least 65%;
- oracle at least 20 points above the best one-call whole-task endpoint;
- dependency-preserving execution at least 20 points above each intervention;
- reference subtasks at least 10 points above generic subtasks, although this gates Stage 3 rather than Stage 2.

Restore the cold-start numbers too, separately by topology:

- validity ≥80%;
- non-zero-variance groups ≥25%;
- groups containing both `1.0` and a lower reward ≥10%.

“≥64 groups” should mean enough groups within each reported stratum, not 64 divided thinly across six cells.

For fork/join:

- each leaf endpoint ≥80%;
- oracle workflow ≥60%;
- ≥15 points over the best two-call shortcut;
- corrupting either branch reduces correctness by ≥20 points.

### 7. Separate the three direct-solving baselines

The “direct 3B Conductor row” is ambiguous under private payloads. Record three different controls:

1. **Public-prompt-only direct model:** verifies that private information has not leaked.
2. **Local capability baseline:** 3B receives the same single-node payload and instruction as a worker.
3. **Best one-call whole-task baseline:** one model/endpoint receives the union of relevant payloads and attempts the complete composite task.

Only the third tells you whether hierarchy adds value. Direct failure with no access merely confirms the information partition.

The echo-worker test also becomes meaningful for answer-smuggling only when the Conductor can see or derive the answer.

### 8. Visible mode is a paired observation condition, not just a flag

Using the same latent program is excellent, but exposing payloads changes prompt length, content and available strategies. A private-trained policy evaluated on visible prompts is undergoing an OOD transfer test.

A causal visibility comparison requires either:

- separate matched policies trained on private versus visible prompts; or
- visibility randomized during training with an explicit indicator.

Bring a small visible qualification slice into Stage 1 so the direct and echo baselines are informative. The larger paired-policy experiment can remain deferred.

## Missing implementation machinery

Two pieces from rev2 have disappeared but are still necessary:

- A resumable `calibrate.py` or equivalent command to run Stage 1 and write per-example outcomes, payoff surfaces and gate reports.
- A versioned Conductor runtime configuration/profile. `workflow_max_steps` alone cannot communicate worker revisions, tools, visibility policy, token caps, resource rules, cell mixture, cache path and batch shape.

The Stage 1 workload will involve thousands of calls. An in-memory cache alone is fragile. Either retain SQLite now or make every result a resumable write-through artifact keyed by the complete request hash.

The worst-case benchmark should also include a per-worker inference microbatch cap. With two prompt groups × eight rollouts × two independent fork leaves, the first wave can contain 32 calls, potentially all routed to one worker.

## Reward table to add

Pre-register this explicitly:

| Outcome | Reward |
|---|---:|
| Malformed workflow/schema | 0.0 |
| Structurally valid but unknown resource, denied access, worker parse failure, invalid artifact, tool rejection or wrong answer | 0.5 |
| Correct executed terminal result | 1.0 |
| OOM, model failure, cache corruption, trace I/O failure | Abort update |

This prevents resource and tool failures from gradually being reclassified as format failures during implementation.

Dependency replacements must be constructed to change the reference sink. A random valid replacement may leave a modular, count or deduplication result unchanged, weakening the intervention through no model fault.

## High-level framing

The framing is now basically sound, with two refinements:

- The primary condition removes Conductor self-solving and authorization tautology, but still studies a **model-plus-tool endpoint**, not pure LLM specialization.
- The private condition is a partial-observability laboratory. It is not evidence that the same behavior will emerge when the Conductor sees everything.

For the six small cells, enumerate the complete worker-assignment payoff surface rather than estimating it from node-level margins:

- atomic: 3 assignments;
- two-step: 9 assignments;
- fork/join: 27 assignments.

That is cheap and gives exact oracle, best-fixed, random, shortcut and interaction effects. It will also reveal cases where a nominally weak upstream worker produces outputs that happen to work better with a particular downstream worker.

The “tool-demanding stratum” currently appears both in v0 and in the deferred list. I would remove it as a named v0 stratum. Let the 100-example pilot tune operand size, list length and distractor count within the existing cells; introduce a distinct hard stratum only after the vertical slice qualifies.

## Final assessment

Rev3 no longer needs another conceptual redesign. The remaining required pass is to lock:

1. what Stage 2 is allowed to vary;
2. resource budgets and legal topologies;
3. exactly one worker artifact protocol;
4. worker-specific versus shared tools;
5. reference-free execution;
6. fresh qualification sets and numeric gates;
7. direct/visible baseline definitions;
8. runtime configuration and calibration persistence.

Once those are written down, the plan is implementation-ready and its claims are appropriately scoped.