# Where we landed — synthesis

A synthesis of the two responses to the pre-implementation questions (concrete data examples; what the experiment actually tests given a 3B Conductor that could self-solve; the mapping to the Conductor paper; expected learning dynamics): my response and the reviewer's [`conductor_plan_v5_where_we_landed.md`](conductor_plan_v5_where_we_landed.md). Where the two differ, this document records the adopted position.

## Canonical framing

> This is a wind-tunnel experiment for hierarchical GRPO, not evidence that a 3B model needs orchestration on natural Math or Code tasks.

A wind tunnel is the right metaphor: controlled conditions, real physics. The optimization dynamics transfer; the particular workers do not need to matter.

## Data examples (merged view)

The two sets of examples agree on anatomy (typed latent program → private resources → rendered public prompt → tagged worker artifacts → executor → scorer). Adopted extensions from the review:

- **Stored-instance schema** with logical separation: `cell_id`, `renderer_id`, `public_prompt`, `public_manifest`, `private_registry`, `reference_program`, `gold_answer`, `generator_version`, `seed`. **No presumed gold worker is stored** — worker assignments come from the empirically measured payoff surface.
- **Atomic cells are one worker call, not one primitive**: the atomic Code cell composes ops inside a single artifact (`count_gt(rotate_left(stable_unique(resource), 3), 5)`), so the artifact grammar supports nesting (whitelist interpreter stays small).
- **Per-cell rejection rules are part of the spec**: e.g. Code rejects duplicate-free inputs, zero rotations, degenerate counts; Math rejects inexact division and out-of-bound results; Math→Code rejects invalid indices and counterfactual indices that select unchanged values.
- **Renderer variants** of one latent program (resource-first / goal-first / bound-variable) share payload, program, interventions, answer — and count as one statistical cluster. The factoring's key structural property: the renderer has no interface through which to read private values, so it cannot determine the answer even by accident.
- **Shortcut taxonomy**: nuisance cues (typed handle names, per-cell output types, length/domain/clause-order correlations, worker names in text) are eliminated by construction and checked by a nuisance-only classifier; legitimate semantic cues ("multiply", "retrieve a field", "zero-based index") are the intended routing signal and stay. Transparent Stage 2 is expected to be lexically routable; that is acceptable for its stated claim (fixed endpoint selection), and anything stronger awaits the semantic/counterfactual renderers plus the shallow-router audit.

## What the experiment actually tests

Three distinct levels of evidence:

1. **Mechanism learnability** — can GRPO learn endpoint selection from terminal reward? The private Stage 2 condition answers this cleanly: the Conductor can recognize the required capability but cannot compute the answer.
2. **Utility inside the controlled environment** — composition must beat the best one-call whole-task endpoint by ≥20 points for a cell to qualify, so routable-but-pointless composition cannot satisfy the study. This utility is partly constructed (private information, tool access) and is claimed only as such.
3. **Utility when orchestration is optional** — not answered by the private condition. The deferred visible experiment requires an explicit `SELF(answer)` action: without it, a Conductor that wants to self-solve can only express that by smuggling the answer into a subtask, and the experiment would measure answer smuggling while claiming to measure delegation.

The pre-registrable claim: *GRPO can (or cannot) learn a useful bundled-endpoint policy when endpoint choice and information flow objectively affect terminal payoff.* Endpoints are model-plus-tool bundles; isolating LLM specialization from tool access is a later factorial.

The design agrees with the observation that a 3B Conductor could solve much of the Math and Code itself — privacy converts that from a confound into the control.

## Mapping to the Conductor paper

**The transferable object is not the surface task; it is the payoff geometry**: a trainable high-level policy, opaque endpoint identities, frozen heterogeneous workers, terminal workflow reward, group-relative advantages, multi-call credit assignment, routing–wording interaction. The toy reproduces the optimization skeleton (endpoint-identity learning, strongest-worker collapse, weak-stakes failure, format-before-correctness, routing-before-instruction-writing, demonstration sensitivity) while manufacturing the heterogeneity the paper gets free from frontier models. The paper's own 3B ablation licenses this: selection learning is precisely the component that survives at small scale.

**Relaxation ladder toward the paper** (each step relaxes one constructed constraint; if the same phenomena survive, the analogy strengthens stepwise):

1. Hidden payloads, bundled tools — the clean routing laboratory (this project).
2. Visible payloads + explicit `SELF` — selective delegation vs self-solving.
3. Equalized tools/access — isolate model specialization.
4. Semantic and counterfactual renderers — reduce template routing.
5. Stronger heterogeneous model/API endpoints.
6. Longer build–test–review–repair workflows.
7. Dynamic or recursive orchestration.

## Expected learning dynamics

Two-tier reward creates two phases: 0.0→0.5 (structurally valid action; fast, format-like) and 0.5→1.0 (successful action; the experiment). The gradient-bearing-group fraction should **rise then fall** — rising as outcomes diversify, falling as the policy saturates or collapses.

**Cold-start routing arithmetic** (uniform-routing prior; the few-shot demos will bias this — the ≥64-group cold-start measurement checks it): probability a group of 8 contains the best assignment ≈ 96% (atomic, 3 assignments), ≈ 61% (two-step, 9), ≈ **26% (fork/join, 27)**. Predictions: routing-schema validity saturates immediately; atomic routing learns first; two-step later; **fork/join may not learn at group size 8 at all** — and if it stalls for this reason, the predicted (not rescue) intervention is batch structure: more prompt groups per update. Primary Stage-2 metric: **routing regret vs the deployable payoff surface**, not exact-route accuracy. Main failure mode: strongest-endpoint collapse before cell-conditional routing.

**Stage 3** progression: valid schema → generic prompts → endpoint-compatible instructions → correct `step_i` usage → brittle wording plateau or genuine improvement. Failures: whole-problem passthrough, wording-lottery prompts, endpoint-artifact syntax leaking into subtasks, Math verbosity/truncation, aggregators ignoring a predecessor. **A Stage-3 null at 3B is expected-plausible even with successful routing** (the paper's 3B writes weaker instructions).

**Stage 4** phases: format acquisition → valid-but-wrong 0.5 plateau → strongest-endpoint/one-step collapse → routing before decomposition → atomic and Lookup→Math first → rarer coordinated rollouts for Math→Code and fork/join → stable workflows or premature entropy collapse. Watch: maximum-calls habits, demonstration-topology copying, repeated identical subtasks, resource shotgunning, aggregation bottlenecks, route–wording co-adaptation into uninterpretable local optima.

**Additional observables**: entropy *localization* (with format mostly forced, watch where in the completion entropy lives — the decision tokens — not just its scalar); the Stage-2 vs Stage-4 action-space-size comparison (~12-token vs ~200-token completions, same environment) as the cleanest generic-GRPO sample-efficiency lesson available; expected gradient availability computable *in advance* from the enumerated payoff surfaces (predicted-vs-realized g).

**The project's payoff, in one sentence** (carried into the conductor log's header): *when does hierarchical GRPO have enough reward variation and endpoint advantage to learn routing, when does textual instruction learning become the bottleneck, and how do the two interfere when optimized jointly.* Those dynamics are what transfer — even if the absolute usefulness of these toy workers never does.
