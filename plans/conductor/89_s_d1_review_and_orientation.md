## Verdict

We are broadly on track, but I would not sign off D1 or begin P1 yet. The namespace implementation itself is sound; one Gate-D binding bug and one sequencing correction should be closed first.

## D1 review

What is correct:

- `worker_dev` is seed-disjoint from existing namespaces and capped at 30 latents per cell.
- Existing namespace outputs remain unchanged, so not bumping `GENERATOR_CODE_VERSION` is the right choice.
- I independently reproduced the declared population: 180 latents, 540 observations and 900 unique isolated cases.
- The 10-per-cell P1 prefix covers the declared cells, node families and factor levels.
- The permanent exclusion from construction, qualification, train, dev and test is scientifically appropriate.

### Blocking: P1 admission trusts the namespace label

[admit_singleton()](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:433) checks the top-level namespace and case count, then checks that the three runs agree with each other. It never proves that the cases are actually the `worker_dev` prefix.

I reproduced this:

- Generate three genuine 300-case `construction` P1 runs.
- Change only their top-level `namespace` fields to `worker_dev`.
- Admission returns `admitted=True` with no reasons.
- The retained first case still identifies itself as `lookup_atomic:construction:...`.

Before accepting Gate-D evidence, admission should regenerate the exact `worker_dev`, 10-per-cell, full-renderer/private plan and require every run to match:

- exact case-ID support;
- endpoint identity;
- user-message hash;
- canonical or reversed order as declared.

Add the construction-header-relabel repro as a regression test.

### Related: the Gate-D CLI is not authoritative

The `admit` and `confirm` commands still accept `--namespace` overrides at [worker_eval_probe.py:577](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:577) and [worker_eval_probe.py:589](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/tasks/conductor/worker_eval_probe.py:589). A successful diagnostic against another namespace prints the same `ADMIT` or `CONFIRMED` wording as Gate D.

That differs from the erratum’s stated contract that overrides remain available only at the function level. The simplest correction is:

- hard-bind the public `admit` and `confirm` commands to `worker_dev`;
- retain configurable Python functions for tests and diagnostics.

### Non-blocking observations

- Change the cap test from broad `pytest.raises(Exception)` to `GenerationError`, and cheaply parameterize the cap assertion over all six cells.
- The erratum should move from “proposed” to ratified only after the admission fix.
- On `picome`, pytest displayed `551 passed` under warnings-as-errors but then exited with code 139. The same teardown exit occurs at the pre-D1 parent commit, so it is not a D1 regression; ordinary evaluator and PyTorch imports exit normally. Track it separately and require actual P0/P1 commands to finish with both a valid artifact and exit code zero.

## High-level orientation

The project is in a much better position than at rev9:

- Tranches A–C are complete: independent node scoring, gold predecessors, full renderer crossing, exact request/runtime provenance, cache-disabled singleton execution and strict persisted-run comparison.
- D1 is implemented apart from the admission binding above.
- The rev1–9 results should now be treated as development history and P0 regression evidence, not as the final worker-selection evidence.
- Tranche-D GPU evidence has not yet begun: no pinned P0 cohort, P0 replay, P1 admission, corrected 900-case candidate runs or finalist confirmations exist yet.

So yes, we are on track—but “resuming D16 iteration” should now mean a bounded, preregistered scope/model experiment, not another open-ended prompt-revision loop.

## Sequencing correction

[Section 7 of 88_f](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/plans/conductor/88_f_d1_worker_dev_namespace_erratum.md:171) currently compares four Code models under the current request contract and tests request scope afterward.

That reverses the conclusion of [78_s](/Users/ken/Documents/Codex/2026-07-15/kencoken-qwen-grpo-https-github-com/review-stage-0b-d16/plans/conductor/78_s_d16_rev9_review.md:346). The existing evidence already shows model × renderer/request-salience interaction. Selecting the model first could select the model best adapted to a known-brittle contract and miss a rank reversal under task-last scope.

A bounded and economical design would be:

1. Start with `{current, task-last} × {Coder-1.5B, generic-1.5B}`.
2. If both models favor the same scope but neither is adequate, compare the two 3B models under that scope.
3. If scope rankings conflict across the 1.5B anchors, expand to the clean `2 scopes × 4 models` factorial rather than choosing a scope post hoc.
4. Keep local-only scope as a diagnostic, not a freeze-eligible contract.

The initial four arms cost roughly eight GPU-hours under the frozen worst-case timing gate, before finalist diagnostics and confirmation.

Also, the 30-index namespace cap does not itself prevent unlimited prompt/model iterations over those same examples. Freeze an explicit arm and escalation budget before inspecting P1 output.

## Recommended next steps

1. Fix P1 population binding and hard-bind the Gate-D CLI; ratify D1.
2. Construct and freeze the P0 cohort from the retained rev9 traces, including exact hashes, ordering and physical `16/16/13` chunks.
3. Run P0 twice in original grouping, then reversed and singleton. P0 preserves the batching evidence; it does not admit singleton.
4. Implement and version the exact `current` and `task-last` request contracts.
5. Before P1, freeze:

   - candidate arms and escalation rule;
   - exact model revisions, prompts, templates, quantization and token caps;
   - P1 and full-population support manifests;
   - ranking, adequacy and tie-break rules;
   - whether composed diagnostics run for every arm or finalists only.

6. Run P1 independently for every exact model/request configuration.
7. Run the corrected 900-case isolated crossing for every admitted arm.
8. Apply the preregistered selection rule, then repeat the full run for finalists and require exact confirmation.
9. Freeze Code model, request contract and prompts; ratify the Math endpoint and decide the `math_code` band without first narrowing it to fit observed failures.
10. Close D4 and `SYSTEM_DIRECT` before the formal construction screen.

The immediate worker position remains sensible: generic 1.5B for Lookup and provisionally Math; Code unresolved. There is no present reason to add 7B, retries, constrained decoding, parser normalization or more prompt prose until the scope/model comparison shows what residue remains.