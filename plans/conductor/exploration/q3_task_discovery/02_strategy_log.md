# Strategy log

## Prospective implementation freeze before worker results

The experimental cell is `code_scope_composition`. Every latent is generated
before rendering and contains one integer-list resource plus a common semantic
plan:

1. keep first occurrences to form `u`;
2. count values of `u` above threshold `t` to form integer `j`;
3. rotate `u` left by `k` to form `v`;
4. define scalar probes `original[i]`, `original[j]`, `v[i]`, and `v[j]`.

The generator requires the five scalar reference values (including `j`) to be
pairwise distinct. This is an outcome-blind semantic construction constraint:
it makes wrong-target attribution unambiguous and never uses worker results.
Values and individual instances will not be searched for disagreements.

All conditions use only the existing Code whitelist:

```text
count_gt(stable_unique(resource), t)
at(resource, i)
at(resource, step_1)
at(rotate_left(stable_unique(resource), k), i)
at(rotate_left(stable_unique(resource), k), step_1)
```

The production task-last final instruction remains byte-for-byte:

> Translate only the assigned Task. The Problem is background; do not complete
> or combine other operations from it. Respond with exactly one
> `<artifact>...</artifact>` containing a single expression.

For each case, w2 and w3 receive the exact same Problem, Resource, Previous
results (when present), Task, and final instruction bytes.

### Renderer strata

The three existing renderer labels are reused locally without modifying the
production renderer:

- `resource_first`: introduces the resource, then the complete plan;
- `goal_first`: states terminal `v[j]` first, then the comparison probes;
- `bound_var`: introduces `u`, `j`, and `v` as bound variables.

Assigned Task text is invariant across renderer for a target condition. Thus a
renderer changes only the semantic plan's presentation, not the requested
artifact.

### Strategy 1 revision `s1-v2`

Paired targets from one latent:

- `intermediate_target`: request the local side probe `original[j]` via
  `at(resource, step_1)`;
- `terminal_target`: request `v[j]` via
  `at(rotate_left(stable_unique(resource), k), step_1)`.

Both arms receive the exact same `Previous results` block with gold `j`
authorized as `step_1`; only the assigned Task changes. The production
scalar-only IR cannot expose a sequence-valued intermediate as a legal target,
so `original[j]` is the closest public local-scope proxy. This limitation is
frozen prospectively rather than hidden after observing results.

Prospective semantic route: **w2 for intermediate, w3 for terminal**.

Pilot: 12 independent paired latents, `goal_first` and `bound_var`, canonical
wording, 96 planned physical calls before cache reuse.

### Strategy 2 revision `s2-v1`

Hold expression depth and visible plan vocabulary fixed while changing whether
the predecessor/global continuation is relevant:

- `relevant_continuation`: request `v[j]` using `step_1`;
- `distracting_continuation`: request matched `v[i]` using literal `i` while
  the supplied `step_1` and `v[j]` continuation remain visible but irrelevant.

Both arms include the Previous-results block. Prospective semantic route:
**w3 when the continuation/binding is relevant, w2 when it is distracting**.

Pilot: 12 independent paired latents, `goal_first` and `bound_var`, canonical
wording, 96 planned calls.

### Strategy 3 revision `s3-v1`

Complete 2 × 2 crossing:

| Condition | Composition | Argument |
|---|---|---|
| `direct_literal` | direct `resource` | literal `i` |
| `direct_bound` | direct `resource` | predecessor `step_1` |
| `nested_literal` | deduplicate + rotate | literal `i` |
| `nested_bound` | deduplicate + rotate | predecessor `step_1` |

All four arms include the same Previous-results block. Prospective route:
**w2 for literal arguments and w3 for predecessor-bound arguments**. The
direct/nested factor tests whether that binding rule survives composition.

Pilot: initially 12 independent paired latents, `goal_first` and `bound_var`,
canonical wording, 192 planned calls. The lower end of the plan's 12–16 range
keeps enough budget for a complete four-condition expansion and a frozen
two-stratum candidate holdout if this strategy is retained.

## Adaptive policy

Strategies run in order. A strategy is dropped as a complete revision for
domination, ceiling/floor behavior, renderer-only reversal, broken reference
logic, or absence of a public semantic route. No individual latent, numeric
value, renderer observation, or completion will be retained or discarded
because it disagrees.

An expanded surface or holdout will receive a fresh namespace. Before any
holdout call, `03_candidate_freeze.md` will record the chosen revision,
factor support, namespace, latent count, wording family and fixed routing
rule. At most one replacement freeze is allowed.

The baseline plus all three pilots costs at most 392 physical generations.
For Strategies 1 or 2, a 32-latent, three-renderer expansion costs 384 calls
and a 48-latent, three-renderer holdout costs 576 calls. For Strategy 3, the
32-latent factorial expansion costs 768 calls; before holdout reveal the
candidate freeze will select two complete semantic condition strata (never
individual cases) for a 576-call holdout. Thus even the most expensive
predeclared path costs 1,736 calls, below the hard 2,000-generation cap.

## Executed adaptive sequence

### Strategy 1 pilot — dropped

Run `01-pilot-s1-v2` executed all 96 planned calls from clean commit
`45d656107362c6a7df0d79a1dd0c2a3ec6704279`; all were physical cache
misses. Independent verification passed.

| Condition | Both | Only w2 | Only w3 | Neither | w2 acc. | w3 acc. |
|---|---:|---:|---:|---:|---:|---:|
| intermediate target | 24 | 0 | 0 | 0 | 100.0% | 100.0% |
| terminal target | 22 | 2 | 0 | 0 | 100.0% | 91.7% |
| overall | 46 | 2 | 0 | 0 | 100.0% | 95.8% |

Both terminal-only w2 wins occurred under `goal_first`; `bound_var` was
24/24 both-correct across the two conditions. There were no w3-only wins,
no renderer-stable unique-win targets in either direction, and no oracle gap
over fixed w2. The prospective semantic router scored 95.8%, 4.2 percentage
points below fixed w2. The two w3 failures were one
`over-composition/wrong target` and one `predecessor/binding`; w2 had no
failure.

**Decision:** drop revision `s1-v2` for ceiling behavior, absence of
bidirectional support, and renderer-local rather than renderer-stable
separation. No instance, value, or observation was filtered. Proceed to the
prospectively declared Strategy 2 pilot.

Frozen hashes:

- calls `197a22031365ac2491ec4854966d736cad239ea2fc6109c0ccea632635ef2bcd`;
- compact rows
  `71f448d8c26fca5af486fd6ee11b59333fead9569bba974ea3cedae48bbff73d`;
- summary
  `88a7fee8919a81a851c2d171845e28d44e28981579949428a2aad455dc1d69a8`;
- latents
  `bab429864350b5f812b60b9af901e419876d0e80478de11ae1120b6543e390df`;
- cases `fb4546dc5ad623a2808f8ee151b9834030bae002761ddd0ff666ec0bc2c43099`.

### Strategy 2 pilot — dropped

Run `02-pilot-s2-v1` executed all 96 planned calls from clean commit
`e36d57ee9c4aea8000c3ff03535255564e620200`; all were physical cache
misses. Independent verification passed.

| Condition | Both | Only w2 | Only w3 | Neither | w2 acc. | w3 acc. |
|---|---:|---:|---:|---:|---:|---:|
| distracting continuation | 24 | 0 | 0 | 0 | 100.0% | 100.0% |
| relevant continuation | 23 | 1 | 0 | 0 | 100.0% | 95.8% |
| overall | 47 | 1 | 0 | 0 | 100.0% | 97.9% |

The sole w2-only observation was a w3 `over-composition/wrong target`
failure under `goal_first`; every `bound_var` observation was both-correct.
There were no w3-only wins, no renderer-stable unique-win targets in either
direction, and no oracle gap over fixed w2. The prospective semantic router
scored 97.9%, 2.1 percentage points below fixed w2.

**Decision:** drop revision `s2-v1` for ceiling behavior and lack of
bidirectional, renderer-stable support. No instance, value, or observation
was filtered. Proceed to the prospectively declared Strategy 3 factorial
pilot.

Frozen hashes:

- calls `aa21916898a534c25a0b315797a0366f484e20c6dcd4ff58c03168fb014949d0`;
- compact rows
  `5c6155211505f3dadd844c6094a3dafcde9dd7dfe009cf2f667a47d13d8ab045`;
- summary
  `38f19cdd5327a147adf3582212ebc5f7e06983e6e969a3df3f7dee738bf836c8`;
- latents
  `7b282c35390a88c9a7b7577cfab3f85e17f7446ea170002243d7aa7a4034eb64`;
- cases `93ae7c543d4b62adb1a5dd299c3425274b4314777a1a7b33fea3ca07ed9f4d10`.
