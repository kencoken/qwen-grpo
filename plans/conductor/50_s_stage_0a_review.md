# PR Review: Conductor Stage 0A

**Pull request:** [kencoken/qwen-grpo#2](https://github.com/kencoken/qwen-grpo/pull/2)  
**Base:** `conductor@25c22ac4a4d7ef66d7ccd04fc178047279b45f4d`  
**Head:** `conductor_stage_0a@5aa2e124dbaf99d723c92e90cc3f0ad60498c588`  
**Scope:** 28 changed files, 5,286 additions, 6 deletions, 2 commits  
**Review status:** Changes requested before declaring Stage 0A complete

## Executive summary

This is a focused and substantial Stage 0A implementation. It provides all six cell generators, independent reference and tool evaluators, deterministic identities and scheduling, renderers, action parsing, a reference-free executor, intervention generation, oracle/control helpers, baseline request builders, and a broad CPU test suite. The overall architecture is well designed and closely follows the frozen specification.

Three issues should be treated as the most important changes:

1. Oracle selection must reject incomplete or unpaired payoff surfaces.
2. Arbitrary model output must never escape the typed-rejection boundary as an unexpected exception.
3. The public/private rendering boundary must be structural rather than relying on current renderer code not to access private fields.

Several remaining items are better understood as Stage 0A completion gaps rather than architectural problems. D16 is explicitly marked draft and should not block merging a clearly labelled "Stage 0A core", but it must block the construction screen and qualification-data generation.

## Findings

### [P1] Validate the complete payoff surface before oracle selection

**Location:** [`tasks/conductor/oracle.py:43-49`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/oracle.py#L43-L49)

`select_deployable` selects over whichever assignments are supplied. It does not require the complete \(3^S\) assignment set or verify that every assignment was evaluated on identical cluster and observation support. For example, the following returns `(2,)` rather than rejecting the surface:

```python
select_deployable({(2,): {"easy": [1.0]}})
```

This is dangerous in a resumable calibration workflow: an interrupted or partially loaded payoff surface could silently become the frozen Stage 2 routing target.

Add a shared validator used by all oracle/control selectors. It should require:

- the exact \(3^S\) assignment set for the relevant cell;
- legal endpoint IDs and tuple lengths;
- identical, non-empty cluster IDs across assignments;
- identical, non-empty observation counts within each cluster;
- finite, valid correctness values;
- explicit exceptions rather than `assert`, which disappears under optimized Python.

The same validation should cover `best_fixed`, exact-uniform random, runner-up selection, and the best-one-call control where applicable.

### [P1] Keep all model output inside typed failure boundaries

**Locations:**

- [`tasks/conductor/tools.py:71-73`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/tools.py#L71-L73)
- [`tasks/conductor/tools.py:332-336`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/tools.py#L332-L336)
- [`tasks/conductor/parser.py:72-99`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/parser.py#L72-L99)

The tokenizer uses Unicode-wide `str.isdigit()` and then assumes an ASCII digit regex matched. For an Arabic-Indic digit such as `١`, `m` is `None` and `m.group(0)` raises `AttributeError` instead of producing `E_PARSE`.

Lone Unicode surrogates produce a second exception class. An artifact containing `\ud800` raises `UnicodeEncodeError` during the byte-limit check, while workflow JSON containing the escaped form is accepted as a subtask and can later fail during request or cache encoding.

These strings originate in policy or worker completions, so they are untrusted model output. They must become `ActionSchemaError` or `ToolRejection("E_PARSE")`; they must not abort a rollout group or training update.

Recommended changes:

- use an ASCII digit check or guard the regex result;
- reject strings that cannot be encoded as UTF-8 at the action/artifact boundary;
- add focused regression tests for non-ASCII numerals and escaped lone surrogates.

### [P1] Make renderer privacy structural

**Locations:**

- [`tasks/conductor/program.py:634-665`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/program.py#L634-L665)
- [`tasks/conductor/program.py:759-788`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/program.py#L759-L788)
- [`tasks/conductor/program.py:927-946`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/program.py#L927-L946)

The generator stores private operands and private-derived values in `latent["params"]`, then passes that complete mapping to both subtask and public-prompt renderers. This contradicts the documented renderer contract that inputs contain handles and public parameters only.

Current renderer functions access only public keys, and a broad generated-data audit found no actual prompt leakage. Nevertheless, the frozen acceptance requirement is structural: private-value provenance must not be available to the renderer at all. The current output-scanning test would remain green if private values were supplied but happened not to be printed.

Split the data into an explicit public rendering record and private generator state, or introduce provenance-tagged parameter types with a mechanically enforced public projection. The test should assert the input boundary, in addition to scanning rendered output.

### [P2] Close the generation and profile domains

#### Latent indices

**Location:** [`tasks/conductor/program.py:861-875`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/program.py#L861-L875)

Only the upper namespace bound is checked. Negative indices generate IDs such as `lookup_atomic:construction:-0001:...`. Boolean indices are also accepted because `bool` subclasses `int`; `False` produces an instance whose display index is `00000` but whose seed was derived from the string `False`, so that instance fails its own normative regeneration.

Require a non-boolean built-in integer satisfying `0 <= latent_index < namespace_cap`.

#### Visibility labels

**Location:** [`tasks/conductor/program.py:941-955`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/program.py#L941-L955)

`VISIBILITY_CONDITIONS` is defined but not checked. `render_instance(..., "bogus")` creates an invalid stored instance, and `validate_instance` accepts it because it regenerates using the same invalid label. Reject anything outside `{private, visible}` before deriving the render-instance ID.

#### Derived public index limit

**Location:** [`tasks/conductor/profiles.py:223-233`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/profiles.py#L223-L233)

Profile validation checks the public `k` and `t` bands but does not bound the derived public index `i`. A profile whose attainable unique-list size permits a 13-digit `i` passes validation, despite the grammar's 12-digit literal limit. Validate the maximum attainable `U - 1`.

#### NumPy representability

**Locations:**

- [`tasks/conductor/profiles.py:118-126`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/profiles.py#L118-L126)
- [`tasks/conductor/program.py:576-577`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/program.py#L576-L577)

Arbitrarily large integer bands can pass validation and subsequently fail inside NumPy's integer sampler with `ValueError: high is out of bounds for int64`. Either validate every sampled band against the chosen sampler's representable range or provide an arbitrary-size integer sampler. Invalid profiles should fail at profile load, not during instance generation.

### [P2] Enforce the shallow control's construction-only contract

**Location:** [`tasks/conductor/baselines.py:140-155`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/baselines.py#L140-L155)

`fit_shallow_predictor` documents construction-only, one-row-per-latent-cluster fitting, but it checks only that all rows belong to the same cell. Qualification/test rows, duplicate latent IDs, empty input, or malformed public feature records can reach the fit.

Enforce:

- `namespace == "construction"` for every row;
- unique `latent_program_id` values;
- non-empty support;
- the required public feature fields;
- preferably a sanitized public-feature record rather than the complete latent object.

This prevents accidental qualification leakage into a control that is intended to diagnose public-prompt shortcuts.

### [P2] Complete the frozen Stage 0A acceptance hooks

These omissions belong to the Stage 0A acceptance contract rather than Stage 0B/0C:

1. **Intervention estimand:** existing tests cover successful positional overrides, but not base-execution eligibility, identical eligible denominators, eligibility-rate reporting, or the required eligible `override_applied == false` infrastructure abort.
2. **Collision sensitivity:** collision metadata exists, but there is no pure scorer/test proving that headline and detected-token-penalized results use identical clusters, observations, and weights, with only detected workflows recoded.
3. **No-op at true zero:** the only no-op test uses a fork case where zero is wrong. The required `math_code` case in which the true intermediate index is zero is absent.
4. **Semantic-to-positional coverage:** both fork orders are tested, but the specification requires coverage for all six cells.
5. **Smaller contract tests:** `render_observation`, B4 request construction, and direct-answer parsing lack dedicated tests.

B1's majority-class and public-parameter echo controls are also not implemented. They need not block a narrowly labelled core merge, but their exact fitting and selection rules must be frozen before construction results are inspected.

### [P3] Enforce the complete `WorkerResult` union

**Location:** [`tasks/conductor/types.py:265-277`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/types.py#L265-L277)

The dataclass accepts unknown status strings and treats `bool` as an integer success value. Consequently, `True` can compare equal to gold answer `1`. Some flag combinations that contradict the frozen truth table are also accepted.

Current internal constructors avoid these cases, so this is lower priority, but the class describes itself as invariant-enforcing and sits at pseudo-worker/custom-worker boundaries. Validate the status enum, exclude booleans, and enforce the exact flag row for each status/outcome class.

### [P3] Make the agreement command verify its requested coverage

**Location:** [`tasks/conductor/agreement.py:67-102`](https://github.com/kencoken/qwen-grpo/blob/conductor_stage_0a/tasks/conductor/agreement.py#L67-L102)

`cases // len(CELL_IDS)` drops remainders, so `--cases 10000` executes 9,996 latent programs rather than 10,000. Namespace caps can silently truncate it further, and `run(5)` checks zero nodes yet returns success.

Distribute the remainder or define the argument as cases per cell, reject impossible requests, and assert the achieved latent and operator × cell stratum coverage before returning success.

## Stage 0A conformance summary

| Area | Assessment |
|---|---|
| Six cell generators and independent reference evaluator | Implemented; default-profile audit passed |
| Endpoint grammars and tool evaluators | Happy paths and frozen error precedence covered; malformed Unicode boundary needs hardening |
| Routing and full-workflow schemas | Implemented and broadly tested |
| Reference-free executor and scorer split | Implemented; strip test passes |
| Deterministic identities, scheduler, renderers and interventions | Implemented; boundary validation and structural provenance need work |
| Oracle and controls | Happy-path formulas/tie rules implemented; surface validation is load-bearing and missing |
| B1-B6 request builders, pseudo-workers and shallow predictor | Mostly implemented; B1 controls and construction-only enforcement remain |
| D16 worker prompts and demonstrations | Explicitly draft; separate review/freeze still required |
| Cache, real worker pool, batching, truncation and traces | Correctly deferred to Stage 0B |
| Task registry, training integration and policy-dependent smoke | Correctly deferred to Stage 0C |
| Calibration, confidence intervals and qualification reporting | Correctly deferred to Stage 1A |

## Verification performed

All verification below used the unchanged PR head `5aa2e124dbaf99d723c92e90cc3f0ad60498c588`:

- full repository suite: **223 passed**;
- focused Conductor suite: **173 passed**;
- warnings-as-errors run: passed;
- reference-vs-tool agreement: **16,660/16,660 node executions agreed**;
- generated-data audit: **3,024 latents** across all six cells and all five namespaces, including ordinary prefixes and namespace boundaries;
- generated-data checks covered deterministic regeneration, normative validation, renderer invariance, namespace isolation, factor balance, reference/gold recomputation, literal limits, and prompt leakage;
- no actual prompt leaks or default-profile invariant failures were observed;
- bounded malformed-input fuzzing reproduced only the Unicode digit and surrogate exception classes described above;
- fixture regeneration produced no diff;
- repository diff check was clean;
- GitHub reports the PR as mergeable, with no configured commit-status checks.

One wording correction is appropriate: the recorded `--cases 10000` command currently covers 9,996 latent programs, even though all 16,660 resulting node executions agree.

## Explicit non-findings and deferrals

The following should not be treated as defects in this PR:

- The repository's existing CUDA/vLLM dependency graph and lack of cross-platform CI are outside the Stage 0A implementation.
- Cache isolation, backend truncation telemetry, NF4 worker loading, batched wave execution, trace persistence, and actual chat-template rendering are explicitly Stage 0B.
- Root task registration and training integration are explicitly Stage 0C.
- D16 is prominently marked `DRAFT`, so it is not a hidden omission.

The current byte fixture pins user-message bytes and a symbolic system identity for shortcut calls. That is consistent with the documented 0B deferral, but it should not be described or used as the final chat-template/cache-key fixture until Stage 0B replaces it.

## Recommendation

Request changes before treating this PR as the completed Stage 0A milestone.

At minimum, fix the oracle-surface validator, totalize the model-output parsing boundary, and establish the structural public/private renderer boundary before merge. The generation-domain checks are small and should be included in the same revision.

If the author prefers to merge this explicitly as **Stage 0A core**, the remaining pure acceptance helpers may be completed immediately afterward, but the following must still block the construction screen:

- all frozen intervention and collision-population acceptance hooks;
- B1 controls frozen before inspecting construction outcomes;
- separate D16 review and freeze against the real 1.5B workers;
- replacement of provisional request hashes with actual chat-template bytes during Stage 0B.
