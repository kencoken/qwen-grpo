Yes—the complementary failures materially change the interpretation. The evidence no longer looks like “1.5B cannot solve the Code tasks.” It looks like:

> No single 1.5B worker policy is reliably universal under the current prompt and request format, but the existing 1.5B policies collectively solve every Code case.

## Where we stand

Rev10 remains the best single configuration:

| Code policy | Correct |
|---|---:|
| A: generic-1.5B + rev10 | 257/270 |
| B: generic-1.5B + rev11 | 248/270 |
| C: Coder-1.5B + rev11 | 214/270 |
| A or B succeeds | 267/270 |
| A or C succeeds | 268/270 |
| A or B or C succeeds | **270/270** |

The union figures come from joining the retained case-level results. They are hindsight-oracle figures, not deployable accuracies, but there is no Code case all three workers miss.

Rev10’s Math change was an unusually clean success: its target group moved from 0/30 to 30/30, with Lookup and Code byte-identical. Rev11 then repaired 10 of rev10’s 13 Code failures but introduced 19 new ones. All the remaining errors across these policies are protocol/DSL failures; there are still no legal-but-semantically-wrong Code outputs. See the [rev10 outcome](</Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/plans/conductor/100_f_d16_worker_config_rev10_outcome.md>) and [rev11 outcome](</Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/plans/conductor/102_f_d16_worker_config_rev11_outcome.md>).

I would therefore soften two claims in `102_f`:

- “Conservation of failures” is a useful hypothesis, not yet a demonstrated law. Rev11 changed three rules together.
- The specific recency explanation is unproven: the final resource/envelope reminder remains the unchanged final suffix. The defensible conclusion is prompt interference or instruction-load pressure.

So the saturation hypothesis is now moderately strong, but narrowly defined:

> Generic-1.5B + NF4 + the full-Problem `task_last` request + unconstrained DSL generation appears near its practical single-prompt reliability frontier.

It is not a general reasoning-capacity ceiling. Indeed, perfect oracle coverage across the three 1.5B policies argues against that stronger interpretation.

## How interesting is the complementary routing?

Very—but the present perfect routing signal is partly renderer-dependent.

I calculated increasingly expressive static routers:

| Routing information | Score |
|---|---:|
| One best Code worker | 257/270 |
| Best worker per cell | 266/270 |
| Cell plus observable semantic subtype/fork order | 268/270 |
| Cell plus renderer | **270/270** |

Selecting the renderer-conditioned mapping using indices 0–14 and evaluating it on indices 15–29 gave 135/135. That suggests a stable effect within these templates, rather than a few accidental cases. But the prompts were developed using the full population, and both halves use the same three renderer grammars. It is not independent evidence that the routing rule generalizes.

This distinction matters:

- If the Conductor selects workers by genuine task structure—atomic sequence operation, predecessor-dependent indexing, fork composition—that is useful semantic orchestration.
- If it selects by phrases characteristic of `goal_first`, `bound_var`, or `resource_first`, it is learning a linguistic compatibility table. That is still a real form of agent selection, but it is much closer to the grammar shortcut we have tried to avoid.

The current frozen specification also has exactly three IDs corresponding to Lookup, Math and Code, with a \(3^S\) action space. It cannot simply treat A, B and C as additional workers. A flat pool such as `{Lookup, Math, A, B, C}` would require a deliberate specification amendment: \(5^S\) payoff surfaces, revised controls and cold-start analysis, and 125 rather than 27 assignments for three-node cells. See the [frozen cell specification](</Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/plans/conductor/48_f_conductor_cell_specs_rev8.md:210>).

The VRAM cost would be small: A and B share the same physical checkpoint, while C adds one Coder checkpoint. The experimental and cold-start complexity is the real cost.

A particularly attractive later extension is failure-aware routing. Running A first, then C and finally B only after a typed parse failure would solve the present 270 cases in 285 calls—about 1.056 calls per case. That uses genuine execution feedback rather than renderer wording and resembles recursive Conductor behaviour. It does, however, change the current one-shot Stage 2 into adaptive repair.

## Recommended next step

I would do two things, with different statuses.

### 1. Continue the core experiment with a bounded 3B screen

Run:

```text
Code model {generic-3B, Coder-3B}
× Code prompt {rev10, rev11}
× task_last
```

This respects the earlier decision to optimize model and prompt jointly. Rev11 at 3B is scientifically important: if the larger model retains its ten targeted repairs without the 19 regressions, that is substantially better evidence for an instruction-capacity explanation than merely observing that rev10 improves with scale.

Generic-3B should be prioritized; Coder-3B can be conditional if limiting compute. Keep Lookup and Math on generic-1.5B during this comparison so that Code scale is the only model change.

If generic-3B succeeds, then evaluate the deployment alternative where Lookup, Math and Code all use the shared generic-3B checkpoint. One shared 3B model has fewer unique parameters than resident 1.5B+3B checkpoints, but Lookup and Math must still be revalidated—larger models have not been monotonically better in these experiments.

This is comfortably within the 4090 budget. The frozen estimate for mixed 1.5B+3B was approximately 7.8 GiB, below the 22 GiB gate; actual 1.5B measurements have been smaller still.

### 2. Preserve A/B/C as a preregistered orchestration extension

Do not discard rev11 merely because it lost as a universal prompt. Freeze A, B and C as observed worker policies and formulate a separate pool experiment.

Its primary success condition should use renderer-invariant semantic routing. Renderer-conditioned and bag-of-words routers should be explicit controls. A genuinely new paraphrase or semantic renderer is needed before claiming that the perfect routing pattern generalizes beyond the three fixed grammars.

If semantic complementarity survives qualification, then expanding the worker pool becomes a justified scientific pivot. If only renderer-conditioned complementarity survives, I would retain it as a positive-control experiment in learned language-to-agent compatibility—not make it the headline orchestration result.

## Other remaining levers

If 3B does not cleanly solve Code, the best remaining probes are:

1. `local_only`: omit the global Problem and send only Task, authorized resource and predecessors. This directly tests the observed tendency to copy handles and recompute the global composition.
2. BF16 generic-1.5B: feasible on the 4090 and separates model size from NF4 numerical brittleness.
3. Typed grammar-constrained decoding: every rev10 failure is outside the legal language, making this a particularly principled way to remove serialization noise.
4. One compressed replacement prompt, not another additive amendment.

I would not lower the 30/30 target yet, and I would stop unrestricted prompt editing on the current `worker_dev` population.

My preferred course is therefore: run the bounded 3B prompt×model screen to close the original D16 question, while preserving the complementary 1.5B policies as a deliberately separate orchestration experiment. If 3B succeeds, you obtain a reliable core worker plus an interesting later study. If it fails, the case for making complementary worker selection part of the core experiment becomes considerably stronger.