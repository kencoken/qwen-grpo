# Unit 4 close-out — provenance addendum and errata (125_s)

Record-only close-out per the 125_s review: no frozen source is
edited, nothing reruns, and the completed smoke stands as recorded.

## 1. Scope note on the executable-source freeze (125_s finding 2)

The `executable_source_sha256` in `stage0c_policy_freeze.json` is a
**partial smoke-source digest** over eight files (`policy.py`,
`render.py`, `grpo_task.py`, `grpo_smoke.py`, `parser.py`,
`payoff_support.py`, `workerpool.py`, `prompts.py`) — it is NOT a
digest of the entire executable environment. Omitted but
execution-relevant: `pool_runtime.py`, `executor.py`, `workers.py`,
`cache.py`, `tools.py`, `contract.py`, the generator/resource modules
(whose observation-affecting behavior is, however, independently
pinned by the 18 literal observation hashes in the freeze), the canary
fixture, and the dependency lockfile (a TRL change would alter trainer
semantics under a passing freeze). None of the omitted bytes changed
between freeze and execution; the recorded run is valid. Unit 5's CE0
preregistration will carry a complete source/environment manifest.

## 2. Environment and source provenance at execution

| item | value |
|---|---|
| freeze commit | `65a5fbec89a7d48704fbe607d861211b32a93d6a` |
| execution/record commit | `5be9f7a8b7d86edbfcc22e2cbe8cdf928526484e` |
| tree at record commit | `1c695ec504b0010272032170931b343438f9ff5d` |
| `pyproject.toml` | `8e03a0bff80545abe45e06b0803490e971ab9ef49916ecadc3d19b71a1aa8c1b` |
| `uv.lock` | `f5486ec478b080aa79c6d0444478b019d2ce6262173a643fd1d6aa8f779e48c9` |
| `stage0_support.json` | `6df4c42b69f8480c9da01d60e664f618eec971d0f0cdd2aa90828cc7d39c4fff` |
| `stage0_canary.json` | `5ac8b52bc939a2417d48281a571ed6a55820a5759e44a6b8d1c536410b2224d1` |
| `stage0_sentinels.json` | `cd143e077968fd35e74ba373aff0ce2b1564eb673449161daf529b14a199d6a4` |
| `stage0c_policy_freeze.json` | `6cf44e2d145b7a0b681e075e5939ea3ac01139bb71dabd75289d87c053e80457` |
| surface manifest (pinned) | `221a04d53403f14c537a3d43336eb6630ca6fe5682f5e3f8aa66f78ace679c23` |

## 3. Content addresses of the retained run (125_s finding 3)

Run directory `runs/stage0c-smoke-0815c033-221a04d5`, W&B run
`3satfxr9` (project `qwen-grpo-conductor`). Hashes independently
verified to match the reviewer's own computation:

| artifact | SHA-256 | bytes |
|---|---|---:|
| `actions.jsonl` | `8477c3f62cdb7f0d58001fe5403e3cbae04ef5a3e641ecde0d77a61b96b3dca7` | 62,634 |
| `summary.json` | `b76420f2ba8821d6a213d3c417435ff53f8819877343055a7d67e2231a3702bc` | 1,176 |
| `launch_profile.json` | `79a833e46464e73d16d3d60c96db6e4f66e23e3a089b5e2afa256e75587414ed` | 1,494 |
| `freeze_record.json` | `6cf44e2d145b7a0b681e075e5939ea3ac01139bb71dabd75289d87c053e80457` | 3,202 |

(`freeze_record.json` is byte-identical to the committed fixture.)

## 4. Frozen-source errata (125_s finding 4 — recorded, not edited)

1. `policy.py` still carries `STATUS: DRAFT pending …` in its
   docstring; the bundle is in fact FROZEN as of `65a5fbe`. The line
   is stale; editing it would move the frozen source digest, so it
   stands as an erratum until any future launch profile.
2. `run_demo_check()`'s success message and CLI help still say both
   Code workers execute "every Code node"; since the 123_s narrowing,
   only the matched independent→final pair is cross-swapped. The
   printed claim is broader than the check performs.
3. The short-circuit paragraph originally written into `124_f`
   mislabeled the `[2,3]` step-2 worker; corrected in place in
   `124_f` (a plans document, not frozen source).

## 5. Attribution correction (125_s finding 1)

The claim that the smoke "confirms a substantial demonstration prior"
is retracted in `124_f` and the log. The identified statement: the
few-shot-conditioned pretrained policy, while being updated for 18
GRPO steps, achieved 48.3% rollout success — consistent with a strong
routing initialization and/or rapid early adaptation (first 144
completions: 38.9% success, mean reward 0.694; second 144: 57.6%,
0.785); the contribution of demonstrations is NOT identified by this
smoke. The registered untrained few-shot and no-demonstration
comparisons remain necessary (123_s §9).

## 6. Carried into the unit-5 handoff

The sampled trace contains genuine within-Code scale contrast in ONE
direction only (two `fork_join` groups where `[0,2,1]` earned 1.0
beside `[0,3,1]` at 0.5); the worker-3-favoring `math_code ×
goal_first` winner was never sampled alongside worker 2 under an
otherwise-correct assignment, and there was no final-policy
evaluation. Reward variance was sparse (8/36 groups) — passing the
modest Stage-0 gate while reinforcing the ≥64-group cold-start
analysis before Stage 2.
