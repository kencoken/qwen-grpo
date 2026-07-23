# 123_s — Stage-0 four-worker Unit 4 prompt-freeze preregistration critique

**Reviewed artifact:** `122_f_d16_stage_0_four_worker_unit_4_prompt_freeze_prereg.md`  
**Reviewed implementation:** through `9c910a7`  
**Scope:** GPU demo-check outcome, prompt-freeze readiness, and the scientific interpretation of the demonstrations

## 1. Verdict

The preregistered probe was executed with the intended discipline and produced a useful result. The current prompt must not be frozen unchanged because one demonstrated workflow is not executable under its assigned workers.

The appropriate response is one bounded correction pass, not another open-ended D16 prompt-tuning loop:

- retain the paper-like four-demonstration format for the Stage-0C integration smoke;
- replace the failing demonstrated assignment with an already-executed successful assignment;
- narrow the exchangeability claim to the genuinely matched Code example;
- record that the revised specialist example communicates a coarse worker-capability cue;
- correct the probe accounting and freeze-verification discrepancies described below.

After these changes, the final demo verification can be cache-backed, followed by the reward-blind format probe and immediate prompt freeze.

Stage 0 remains an integration experiment using demonstration-bootstrapped routing. It must not be interpreted as showing routing emerging from an uninformed initialization.

## 2. GPU probe outcome

The demo check exercised six workflows:

1. direct route with its assigned action;
2. dependency chain with its assigned action;
3. independent→final with its assigned Code ordering;
4. specialist→check with its assigned Code ordering;
5. independent→final with workers 2 and 3 swapped;
6. specialist→check with workers 2 and 3 swapped.

Five of the six workflows passed in both probe rounds.

| Workflow | Action | Round 0 | Round 1 |
|---|---:|---:|---:|
| direct | `[0]` | pass | pass |
| dependency | `[0,1]` | pass | pass |
| independent→final, assigned | `[2,3,1]` | pass | pass |
| independent→final, swapped | `[3,2,1]` | pass | pass |
| specialist→check, assigned | `[3,2]` | **fail** | **fail** |
| specialist→check, swapped | `[2,3]` | pass | pass |

The one permitted repair changed only the specialist Problem wording, from a goal-chained formulation to a resource-first imperative formulation. It did not change the steps, payloads, workers or gold answer.

Worker 3 nevertheless continued to incorporate downstream Problem operations into its assigned first node:

```text
Round 0:
at(count_gt(stable_unique(resource), 4), 3)

Round 1:
at(
    rotate_left(stable_unique(resource), 3),
    count_gt(stable_unique(resource), 4)
)
```

The repair budget was therefore correctly exhausted and execution stopped before:

- the reward-blind format probe;
- prompt freeze;
- the canary;
- any reward-bearing smoke output.

The full 673-test suite remained green under warnings-as-errors.

## 3. Interpretation of the failure

This is not evidence that worker 3 successfully solves the whole workflow. It is a recurrence of the previously characterized 3B task-scope failure.

Worker 3 sees the full Problem as background but receives only the resource and previous results authorized for its current node. It attempts to absorb the downstream goal into its local expression, but cannot execute the complete workflow correctly through that resource boundary.

The distinction is important:

- worker 3 has greater capacity to recognize and imitate the global composition;
- that capacity makes it less reliable at respecting the local Task boundary;
- worker 2 is less prone to this form of over-composition;
- worker 3 remains preferable on some other Code nodes.

This is legitimate endpoint heterogeneity. The endpoint treatment is the complete combination of:

```text
model checkpoint + system prompt + request contract + visible context
```

The appropriate scientific claim is therefore that the Conductor learns compatibility between workflow context and fixed model–prompt–contract endpoints. The result does not isolate intrinsic model capability independently of request design.

Neither another worker-prompt amendment nor an immediate switch to `local_only` is warranted:

- the frozen task-last contract already explicitly instructs the worker not to combine other Problem operations;
- the failure survived two materially different Problem formulations;
- prior D16 prompt additions traded one failure mode for another;
- changing request scope would invalidate worker fingerprints, cache identities, sentinels, the canary and the materialized payoff surface.

`local_only` remains a useful later mechanistic ablation.

## 4. Approved Stage-0 demonstration amendment

The revised demonstrated actions should be:

| Demonstration | Current | Revised |
|---|---:|---:|
| independent→final | `[2,3,1]` | `[3,2,1]` |
| specialist→check | `[3,2]` | `[2,3]` |

Both revised workflows have already passed through the exact runtime.

This arrangement preserves:

- every worker appearing exactly twice;
- reversed Code-worker order across the two demonstrations;
- all four workflow shapes required for the paper-like prompt;
- no additional worker-generation discovery.

The independent→final workflow establishes the matched legality result:

- workers 2 and 3 both execute both independent `at(...)` nodes successfully;
- both `[2,3,1]` and `[3,2,1]` succeed;
- assignment within that matched pair is not evidence of a capability difference.

The specialist→check workflow is different:

- `[2,3]` succeeds;
- `[3,2]` fails reproducibly;
- it is therefore an asymmetric successful capability example, not an exchangeability test.

The demo checker must be narrowed accordingly. It should cross-swap the explicitly matched independent→final example, but require only the demonstrated successful route for specialist→check. Requiring universal cross-executability would contradict the heterogeneity that motivates the four-worker pool.

This amendment does not remove `[3,2]` from the action space. `[3,2]` remains a legal action and may succeed in other workflow contexts. Only the false claim that it successfully executes this particular specialist chain is removed from the prompt.

## 5. Demonstration information and routing cues

The demonstrations communicate three different kinds of information:

1. **Format and topology**
   - the JSON action schema;
   - one action per step;
   - one-, two- and three-step action lengths.

2. **Broad worker-family compatibility**
   - worker 0 is demonstrated on Lookup;
   - worker 1 is demonstrated on Math;
   - workers 2 and 3 are demonstrated on Code.

3. **Conditional within-Code compatibility**
   - which of workers 2 and 3 is preferable for a particular operation, access pattern or full-Problem context.

The existing examples already disclose levels 1 and 2. Routing is therefore not learned from a tabula-rasa policy. The untrained model is conditioned in-context toward the broad task-family mapping before GRPO begins.

The revised specialist demonstration also communicates some information at level 3:

| Visible pattern | Demonstrated worker |
|---|---:|
| independent `at(...)` nodes | both 2 and 3 |
| scope-sensitive deduplication/count node with a downstream goal visible | 2 |
| dependent `at(resource, step_1)` node | 3 |

A policy could infer shortcuts such as:

```text
count/deduplicate → worker 2
dependent Code step → worker 3
```

This resembles part of the observed four-worker payoff geometry. It may therefore:

- improve cold-start routing;
- reduce the headroom available to GRPO;
- accelerate apparent learning through demonstration following;
- encourage an overly broad operation- or position-based shortcut.

This is not undisclosed data leakage: the example is synthetic and was selected using its own preregistered executability probe, not the Stage-0 payoff surface. It is nevertheless a disclosed capability prior, not merely a neutral format example.

The following framing is approved with that qualification:

> The demonstrations show workers succeeding on step types they can execute under the complete frozen request treatment. They establish executable endpoint compatibility, while also supplying a limited routing prior.

They must not be described as conveying format alone or as proving universal worker legality across every Code node.

## 6. Cross-check against the Conductor paper

The paper’s demonstrations are more than indicative schema illustrations.

The paper states that:

- the prompt contains examples of known successful coordination strategies;
- the examples are real Conductor completions selected from cold-start training runs;
- four examples are used in the main OOD condition;
- they are drawn from MedReason, DeepMath and Countdown rather than the training tasks;
- they are selected to vary workflow length and agent selection;
- they are intended both to improve initial formatting and to communicate useful agent compatibility information.

The paper’s rationale for using OOD examples is not to eliminate all routing information. It is to make directly copying a demonstrated solution strategy onto the training tasks less attractive while retaining a useful orchestration prior.

The documented examples should nevertheless not be interpreted as independently verified gold routing policies:

- the appendix shows the Conductor’s model IDs, subtasks and access lists;
- it does not show the complete downstream worker executions;
- it does not independently score each intermediate subtask;
- it does not establish that every selected model was necessary or optimal;
- it does not establish deterministic repeatability under swapped workers.

Their documented correctness is terminal and historical: they were selected from successful cold-start trajectories. Our exact deterministic workflow verification is a stronger requirement, which is appropriate for this controlled experiment.

The paper also reports a substantial no-few-shot ablation:

| Setting | MATH500 | MMLU | RLPR | LiveCodeBench |
|---|---:|---:|---:|---:|
| full few-shot prompt | 89.33 | 93.14 | 42.63 | 64.29 |
| without few-shot examples | 82.00 | 92.69 | 41.50 | 54.86 |

The main paper result is therefore demonstration-bootstrapped GRPO, not routing learned from a completely unconditioned initialization.

Retaining four successful demonstrations for Stage 0 is paper-consistent. The toy environment’s stable IDs and narrow task families make those demonstrations more directly reusable than the paper’s examples, so their effect must be measured rather than assumed negligible.

## 7. Prompt wording correction

The current system prompt states that:

```text
the step descriptions tell you what each step needs
```

This is incomplete because the measured worker-2-versus-worker-3 distinction can depend on the complete Problem wording, renderer and dependency context even when the local step description is unchanged.

Replace it with neutral wording such as:

```text
Workers differ in how they handle a step in the context of the full
request. Use the Problem, step description, resource/access annotations,
and previous-result pattern.
```

This does not reveal any worker mapping. It accurately describes the information on which the routing decision may depend.

## 8. Record-integrity corrections

### 8.1 Formal probe outcome

`122_f` contains the preregistration but not a formal outcome record. The results currently survive primarily in commit messages, code comments and the runtime cache.

The implementation response must persist:

- the complete round-by-round workflow matrix;
- both failed worker outputs;
- the repair that was attempted;
- confirmation that the repair budget was exhausted;
- confirmation that neither the payoff surface nor reward-bearing output was inspected.

### 8.2 Request accounting

The cumulative exposure across both rounds was:

- eight distinct rendered request hashes in each round;
- six hashes shared between rounds;
- **10 distinct rendered request hashes cumulatively**;
- **14 distinct `(worker fingerprint, request)` completions**.

The statement that the total budget was eight unique requests is therefore incorrect if interpreted cumulatively.

### 8.3 Short-circuiting

The current exchangeability language says that both Code workers execute every Code node in both Code-bearing demonstrations. That did not occur.

In the failing specialist `[3,2]` workflow:

- worker 3 failed at step 1;
- execution short-circuited;
- worker 2 did not execute step 2 in that assigned workflow.

The record must distinguish planned assignments from nodes that were actually reached.

### 8.4 Executable freeze verification

`compute_freeze_record()` records `executable_commit`, but `verify_freeze()` does not compare it. This conflicts with the preregistration’s statement that the executable commit is verified before launch.

Directly comparing the current Git commit would also create a self-reference problem once the freeze fixture itself is committed. Bind the freeze to a deterministic digest over the relevant executable source and configuration files instead, or equivalently to a source-tree digest that excludes the freeze fixture.

The consuming `run` path must fail closed if those bytes change.

## 9. Deferred Stage-2 demonstration decision

The Stage-0 prompt should retain the paper-like four-demonstration treatment. Stage 0 is an integration and cold-start diagnostic, and the resulting trained policy is discarded.

Before the Stage-2 prompt is frozen, explicitly choose and preregister the demonstration treatment.

At minimum:

1. Evaluate the frozen untrained few-shot policy.
2. Measure how much family routing and worker-2-versus-worker-3 selection it already obtains from the demonstrations.
3. If it is already near the deployable routing ceiling, make a schema-only/no-few-shot prompt the primary learning condition.
4. Otherwise retain the paper-like few-shot prompt as the primary condition and include a no-few-shot condition as an ablation.
5. Begin with one pilot seed per selected prompt treatment before committing headline seeds.

The most informative eventual comparison is:

| Policy | What it measures |
|---|---|
| untrained, no demonstrations | zero-shot routing prior |
| untrained, few-shot demonstrations | in-context demonstration effect |
| GRPO-trained, no demonstrations | routing learned primarily from reward |
| GRPO-trained, few-shot demonstrations | paper-like bootstrapped post-training |

Compute discipline may prevent running all four as full multi-seed conditions. The mandatory comparison is the trained few-shot policy against its own untrained few-shot baseline. A one-seed no-demonstration pilot is the preferred additional diagnostic.

This decision is deferred rather than silently settled by the Stage-0 prompt.

## 10. Acceptance sequence

Before Unit 4 prompt freeze:

1. Change independent→final to `[3,2,1]`.
2. Change specialist→check to `[2,3]`.
3. Cross-swap only the explicitly matched independent Code example.
4. Update the exchangeability and capability-cue documentation.
5. Correct the cumulative request accounting.
6. Persist the complete probe outcome.
7. Apply the neutral full-request-context prompt wording.
8. Make the executable source digest part of freeze verification.
9. Run the final demo verification from the existing cache, with no new worker generation expected.
10. Run the preregistered reward-blind format probe.
11. If it passes, freeze the prompt/profile/source bundle immediately.
12. Run the canary and the single reward-bearing Stage-0 smoke.

If the format probe fails its preregistered threshold, only the already-authorized schema-only repair is permitted. Worker routing, demonstrated capability choices and reward output must not be inspected or tuned during that repair.

## 11. Sign-off boundary

After the changes above, no further open-ended D16 worker-prompt or internal-object audit is recommended.

The next useful evidence should come from:

- the reward-blind format probe;
- the untrained policy’s selection distribution;
- the Stage-0 reward-bearing integration smoke;
- the later few-shot versus no-few-shot demonstration comparison.

The remaining scientific question is no longer whether all Code workers are interchangeable. They are demonstrably not. It is whether GRPO can learn the conditional routing policy over these fixed heterogeneous endpoints, and how much of that policy is supplied by prompt demonstrations rather than post-training.