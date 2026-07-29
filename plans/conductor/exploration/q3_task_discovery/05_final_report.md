# Q3 task-discovery final report

## Outcome

**Disposition: RED.**

> No suitable Q3 task was found within the tested existing-DSL strategies and overnight search budget.

This is a bounded null result, not an impossibility claim. The frozen 1.5B
Code worker was correct on every new-task observation. All nine pilot
disagreements favored w2, all were confined to `goal_first`, and none was
renderer-stable. Fixed w2 and the hindsight oracle both scored 100%.

No expansion, candidate freeze, holdout, prompt revision, model change, DSL
change, or GRPO training was run.

## Commit and execution identities

- Base branch: `conductor_stage1`.
- Base/latest Unit-A commit:
  `95cb618dca5eab2b93b151ffaccf575753ca4f33`.
- Pre-GPU harness freeze:
  `5d3e9227b04af4b0dce4292f1f6c1edd155b7468`.
- Final executed-evidence commit:
  `c1a456557fbf65c0a7349e6114c6eb743e88aad5`.
- Exploration branch: `conductor_q3_task_discovery`.

The pushed delivery tip is the commit containing this report. Its SHA is
reported by the final branch ref and handoff rather than embedded here,
because a commit cannot contain its own content-derived identity.

Exact treatment identity:

| Field | w2 | w3 |
|---|---|---|
| Worker | `2`, `code_1p5b` | `3`, `code_3b` |
| Model | `Qwen/Qwen2.5-1.5B-Instruct` | `Qwen/Qwen2.5-3B-Instruct` |
| Revision | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` | `aa8e72537993ba99e69dfaafa59ed015b17504d1` |
| Measured parameters | 1,543,714,304 | 3,085,938,688 |
| Selected-worker fingerprint | `slw-bfb9b10016770298` | `slw-247bf2139befbc03` |

Shared identities were:

- runtime `rtp-734994ee45569c1f`;
- pool `wp-197e286115f56e4a`;
- worker-visible configuration `wv-4e196a1c467d108b`;
- Code endpoint family `epf-d8f834da028432d3`;
- rev10 Code prompt SHA-256
  `9b08f3e6f4afad854484a13257d973e79e8664194f16cf44930644ab22e88aea`;
- chat-template SHA-256
  `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f`;
- request contract `worker-blocks-task-last-v1`, digest
  `8638fdad716e1e0c55b733298f8d0b4061af8dc5851ba0e6b8c99017642b5a7c`;
- parser/tool/grammar `cell-specs-v0.8`;
- NF4 double quantization with bfloat16 compute, greedy EOS decoding,
  256-token runtime cap, and `singleton-v1`.

The host was `picome`, NVIDIA GeForce RTX 4090, driver 595.84. Software
versions were Python 3.12.3, PyTorch 2.11.0+cu130, CUDA 13.0,
bitsandbytes 0.49.2, and transformers 5.13.0.

## Resource accounting and baseline

| Run | Cases | Physical calls | GPU seconds | Session wall seconds | Cache hits |
|---|---:|---:|---:|---:|---:|
| retained baseline | 4 | 8 | 4.816 | 7.957 | 0 |
| Strategy 1 pilot | 48 | 96 | 34.769 | 38.063 | 0 |
| Strategy 2 pilot | 48 | 96 | 42.482 | 45.779 | 0 |
| Strategy 3 pilot | 96 | 192 | 66.942 | 70.427 | 0 |
| **Total** | **196** | **392** | **149.009** | **162.225** | **0** |

The first run began at 2026-07-29 23:31:11 UTC and the last completed at
23:37:34 UTC, a 382.598-second elapsed interval including analysis between
runs. GPU use was 0.0414 hours. Limits used were 392/2,000 physical calls,
0.0414/10 GPU-hours, 3/4 major strategies, and 0/2 holdout reveals.

The four retained baseline directions all reproduced on eight cold physical
calls:

| Retained behavior | Actual |
|---|---|
| both correct | reproduced |
| w2 correct, w3 `E_PARSE` | reproduced |
| w3 correct, w2 `E_PARSE` | reproduced |
| w2 correct, w3 legal success at wrong value | reproduced |

Both checkpoints loaded and all baseline request identities matched their
pinned SHA-256 values. The independent verifier passed all four runs.

## Task construction and representative examples

The development-only cell was `code_scope_composition`. Each latent fixed an
integer-list resource and a typed semantic plan before rendering:
deduplicate, count above a threshold to bind `step_1`, rotate, then probe
direct or composed sequence positions. References were pairwise distinct,
computed independently, and checked against the unchanged parser/tool before
generation. w2 and w3 received byte-identical rendered requests.

Representative paired Tasks and legal references:

| Strategy/condition | Assigned Task | Reference artifact |
|---|---|---|
| S1 intermediate proxy | Return index `step_1` from the original resource. | `at(resource, step_1)` |
| S1 terminal | Deduplicate, rotate left by 1, then return index `step_1`. | `at(rotate_left(stable_unique(resource), 1), step_1)` |
| S2 relevant continuation | Deduplicate, rotate left by 9, then use `step_1`. | `at(rotate_left(stable_unique(resource), 9), step_1)` |
| S2 distracting continuation | Same visible plan, but use literal index 0. | `at(rotate_left(stable_unique(resource), 9), 0)` |
| S3 direct literal | Return original-resource index 5. | `at(resource, 5)` |
| S3 direct bound | Return original-resource index `step_1`. | `at(resource, step_1)` |
| S3 nested literal | Deduplicate, rotate left by 7, then use index 5. | `at(rotate_left(stable_unique(resource), 7), 5)` |
| S3 nested bound | Deduplicate, rotate left by 7, then use `step_1`. | `at(rotate_left(stable_unique(resource), 7), step_1)` |

The production scalar-only IR could not expose a sequence-valued
intermediate as a legal target. Strategy 1 therefore used the prospectively
declared scalar side probe as the closest existing-DSL proxy. This is a
material limitation, not an outcome-driven change.

## Complete development matrices

Rendered-observation totals by semantic condition:

| Strategy | Condition | Both | Only w2 | Only w3 | Neither | w2 acc. | w3 acc. |
|---|---|---:|---:|---:|---:|---:|---:|
| S1 | intermediate target | 24 | 0 | 0 | 0 | 100.0% | 100.0% |
| S1 | terminal target | 22 | 2 | 0 | 0 | 100.0% | 91.7% |
| S2 | distracting continuation | 24 | 0 | 0 | 0 | 100.0% | 100.0% |
| S2 | relevant continuation | 23 | 1 | 0 | 0 | 100.0% | 95.8% |
| S3 | direct literal | 21 | 3 | 0 | 0 | 100.0% | 87.5% |
| S3 | direct bound | 24 | 0 | 0 | 0 | 100.0% | 100.0% |
| S3 | nested literal | 24 | 0 | 0 | 0 | 100.0% | 100.0% |
| S3 | nested bound | 21 | 3 | 0 | 0 | 100.0% | 87.5% |
| **All pilots** | **all conditions** | **183** | **9** | **0** | **0** | **100.0%** | **95.3%** |

Complete renderer breakdown; each row has 12 rendered observations:

| Strategy | Condition | Renderer | Both | Only w2 | Only w3 | Neither | w2 acc. | w3 acc. | Incorrect-output class |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| S1 | intermediate | goal_first | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S1 | intermediate | bound_var | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S1 | terminal | goal_first | 10 | 2 | 0 | 0 | 100% | 83.3% | w3: 2 legal semantic |
| S1 | terminal | bound_var | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S2 | distracting | goal_first | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S2 | distracting | bound_var | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S2 | relevant | goal_first | 11 | 1 | 0 | 0 | 100% | 91.7% | w3: 1 legal semantic |
| S2 | relevant | bound_var | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S3 | direct literal | goal_first | 9 | 3 | 0 | 0 | 100% | 75.0% | w3: 3 parse/grammar |
| S3 | direct literal | bound_var | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S3 | direct bound | goal_first | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S3 | direct bound | bound_var | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S3 | nested literal | goal_first | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S3 | nested literal | bound_var | 12 | 0 | 0 | 0 | 100% | 100% | none |
| S3 | nested bound | goal_first | 9 | 3 | 0 | 0 | 100% | 75.0% | w3: 3 legal semantic |
| S3 | nested bound | bound_var | 12 | 0 | 0 | 0 | 100% | 100% | none |

No development expansion or holdout was run because no pilot had an oracle
gap or a w3-only direction. The complete holdout matrix is therefore:

| Candidate | Both | Only w2 | Only w3 | Neither |
|---|---:|---:|---:|---:|
| no candidate; no reveal | 0 | 0 | 0 | 0 |

## Independent-latent and renderer-stability analysis

Collapsing the two renderer replicas by strict majority produced 96
independent latent-target units:

| Outcome | Units | Mass |
|---|---:|---:|
| both correct | 87 | 90.625% |
| only w2 correct | 9 | 9.375% |
| only w3 correct | 0 | 0% |
| neither correct | 0 | 0% |

Every unique result appeared under only one of the two renderers. There were
zero renderer-stable unique-win targets for either worker, zero latents with
stable directions for both workers, and zero renderer reversals. The stricter
all-three-renderer count was not estimable because no strategy qualified for
the three-renderer expansion; no target had three renderer replicas.

## Routing, shortcut controls, and group-of-eight feasibility

Across all 192 pilot observations:

| Policy/diagnostic | Accuracy | Versus fixed w2 |
|---|---:|---:|
| fixed w2 | 100.000% | — |
| fixed w3 | 95.312% | -4.688 pp |
| uniform random worker, expected | 97.656% | -2.344 pp |
| prospective semantic router | 96.875% | -3.125 pp |
| hindsight per-observation oracle | 100.000% | 0 pp |

At the independent latent-target majority unit, fixed w2 and the oracle were
100%, while the prospective semantic router was 93.75%. The oracle-minus-
best-fixed gap was zero, so the fraction of oracle gain captured by the
semantic router is undefined rather than favorable.

The optimistic in-sample renderer-only and text-length controls both selected
w2 everywhere and reached 100%. All nine disagreements were `goal_first`;
all 96 `bound_var` observations were both-correct. Renderer presentation
therefore exposed a 3B fragility, not a public bidirectional specialization
rule.

Payoff-distinct rendered-observation rates and iid balanced group-of-eight
nonzero-diversity projections were:

| Strategy | Payoff-distinct rate | Projected nonzero diversity |
|---|---:|---:|
| S1 | 4.167% | 4.134% |
| S2 | 2.083% | 2.067% |
| S3 | 6.250% | 6.201% |
| all pilots | 4.688% | 4.651% |

All projected diversity was one-direction w2-only, renderer-local, and partly
malformed-output noise. It cannot support the intended Q3 routing mechanism.

## Failure taxonomy

New-task failures:

| Failure class | w2 | w3 |
|---|---:|---:|
| parse/grammar | 0 | 3 |
| resource/identifier protocol | 0 | 0 |
| over-composition/wrong target | 0 | 5 |
| predecessor/binding | 0 | 1 |
| threshold/index/value | 0 | 0 |
| other legal semantic error | 0 | 0 |

The retained baseline separately contained one w2 parse failure, one w3 parse
failure, and one w3 threshold/index/value error, all expected and reproduced.

Representative new-task errors show the renderer-local mechanism:

- for a terminal bound target, w3 substituted literal index `1` for
  `step_1`;
- for direct literal targets, w3 sometimes emitted nested `at(at(...))`
  expressions rejected by the grammar;
- for nested bound targets, w3 again literalized the predecessor, producing a
  legal artifact at the wrong target value.

## Strategy dispositions

1. **S1 `s1-v2`, intermediate side probe versus terminal target — RED.**
   w2 was 48/48, w3 was 46/48, there were no w3-only results, and both
   disagreements were goal-first-only.
2. **S2 `s2-v1`, relevant versus distracting continuation — RED.**
   w2 was 48/48, w3 was 47/48, and the sole disagreement was
   goal-first-only.
3. **S3 `s3-v1`, direct/nested × literal/bound crossing — RED.**
   w2 was 96/96, w3 was 90/96, all six disagreements were w2-only and
   goal-first-only, and three were parse failures.

No individual latent or numeric value was retained or discarded based on
outcome. Each complete strategy revision was scored and then dropped as a
unit.

## Artifact and raw-run index

Raw completions remain gitignored under `runs/q3-task-discovery/`. Compact
manifests, cases, latents, scored rows, and summaries are committed under
`plans/conductor/exploration/q3_task_discovery/artifacts/`.

| Run/raw location | Raw calls SHA-256 | Compact rows SHA-256 | Summary SHA-256 | Manifest-file SHA-256 |
|---|---|---|---|---|
| `runs/q3-task-discovery/00-baseline` | `bac8bbd0392421a19356ceed5618d1b6b817f53a60985e7b8a3791d14137083d` | `c7594df847eee8384048e1fb7397abe1965b18fc8f09f10e6376a706111fc576` | `741b6f4956778aa80e95577b224d5dbfb5fe78bd51cf19e6359dc6b1a092f6b1` | `11b6d885bd29b26abf19dae2bcc5f9ed41b6e2878480aa3cc9cdb7a1b3aef052` |
| `runs/q3-task-discovery/01-pilot-s1-v2` | `197a22031365ac2491ec4854966d736cad239ea2fc6109c0ccea632635ef2bcd` | `71f448d8c26fca5af486fd6ee11b59333fead9569bba974ea3cedae48bbff73d` | `88a7fee8919a81a851c2d171845e28d44e28981579949428a2aad455dc1d69a8` | `9eacd00cd2ec94c99a64325cbf4cfb50a71639142ded8c2f4637065b3afe42cb` |
| `runs/q3-task-discovery/02-pilot-s2-v1` | `aa21916898a534c25a0b315797a0366f484e20c6dcd4ff58c03168fb014949d0` | `5c6155211505f3dadd844c6094a3dafcde9dd7dfe009cf2f667a47d13d8ab045` | `38f19cdd5327a147adf3582212ebc5f7e06983e6e969a3df3f7dee738bf836c8` | `c060f7147e5af432b9a5856617bee67c58ab648daf2e78eb4dd8ec21097b01e6` |
| `runs/q3-task-discovery/03-pilot-s3-v1` | `1705094c4d23886400708784505458cf7e59523f34e418cd76b0b16b5ae0c6bd` | `892798d98c81094e8f7c2ad724b61c0d62fc2c196d9fcde5f4d516ae2f78564b` | `6431003e34d3fed1b94f60c81debd202ceb74eed8c86a43bdf9f4cb0624dd098` | `0f8291bec6589e1733fd72e54aeb46ffc3a9448f89200284c4f991b03cf2fb0f` |

## Adaptive-discovery limitations

- Strategy revisions and stopping decisions were adaptive development
  decisions, so none of these data is confirmatory evidence.
- Only the pilots were revealed. The absent three-renderer expansion means
  strict all-three stability was not estimated.
- Strategy 1 tested a scalar side-probe proxy, not a true sequence-valued
  intermediate, because the existing production IR cannot score the latter.
- The renderer set in pilots was `goal_first` and `bound_var`;
  `resource_first` was reserved for expansions that no strategy earned.
- The common rev10 prompt was developed primarily around 1.5B behavior.
- No discovery latent, resource value, completion, or namespace should be
  reused as future validation or holdout support.

## Prompt-mismatch classification

Classification: **No task geometry under the common prompt.**

The 3B failures were systematically concentrated in `goal_first` and often
involved binding/scope, so common-prompt compatibility remains a real
limitation. However, the evidence does not meet the plan's stronger
“plausible systematic 3B prompt mismatch” category: w3 never had a unique
win, w2 was perfect, and the 3B errors mixed legal wrong-target behavior with
grammar failures. There is no observed desired semantic advantage that a
prompt repair would recover. A 3B-specific prompt experiment is therefore
not recommended from this evidence alone.

## Final action

**RED — do not run GRPO. The present semantic task distribution does not
support w2/w3 specialization under the frozen production interface.**

The narrowest next step is to add, in a separate reviewed development design,
one typed sequence-valued target to the experimental Code IR and grammar.
Then rerun a fresh, common-prompt comparison of a true local sequence
intermediate against its composed scalar terminal target, using entirely new
namespaces and all three renderers. This adds exactly the semantic distinction
that Strategy 1 could only proxy; it does not authorize prompt iteration,
training, or reuse of the revealed support.
