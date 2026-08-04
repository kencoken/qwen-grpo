## Verdict

`287_f` is a sound architectural proposal, but it should not yet authorize implementation literally as written. It predates the final C2 result and leaves a few scientifically important boundaries ambiguous.

I would keep `287_f` as the rationale and produce one focused successor design. The spine should be smaller and more explicitly forward-only than the current four-component extraction suggests.

## Required changes for the successor

### 1. Keep the migration strictly P0-forward

There is a contradiction between:

- “one implementation consumed everywhere” and removal of the old guards; and
- preserving the C1/C2 modules and verifiers unchanged.

Do not retrofit `p0_mixture.py`, `p0_mixture_v2.py`, `unit_c_sample.py`, or `unit_c2_sample.py`. They remain the historical compatibility oracle. The new definitions become canonical only for P0-forward work.

There is also an important conceptual distinction in §2: `bridge_eligible` is not another implementation of the observed Q1-counted event. It is a surface-level schedule-eligibility predicate with an additional tied-worker condition. Keep these separately named:

- schedule feasibility: `bridge_eligible`;
- observed group estimand: `q1_counted`.

### 2. Split scientific design from the eventual run freeze

A single “constructed once” `P0Contract` cannot yet contain everything listed in §3. The beta smoke, finalization reserve, validation/cycle identities, operational epoch cap, and final runtime identity do not exist yet. “Expected artifact identities” can also create circular hashes.

Use two stages:

| Artifact | Contents | Frozen when |
|---|---|---|
| `P0ScienceContract` | Input pins, active scope, one-epoch schedule identity, estimands, gates, sizing/cap rules, required diagnostics | Spine implementation |
| `P0LaunchFreeze` | Science-contract hash, val/cycle evidence, beta/timing inputs, actual epoch cap, runtime/seed/environment identities | Immediately before P0 |

Terminal output hashes belong in the closeout, not either preregistration artifact.

The precursor val/cycle/beta units can retain their own small freezes; the final launch freeze simply pins their reviewed outputs.

### 3. Make C2 equivalence exact

“Every archive reverifies” is necessary but does not prove that P0 uses the experiment C2 authorized.

The successor should define a canonical scientific projection that the new spine independently rederives from the raw committed C2 trace, locked surface and comparator. It should exactly reproduce:

- the ordered 157-row epoch and 785-row C2 schedule;
- class assignments, multiplicities, populations and sentinel IDs;
- population draws: Anchor 75, Bridge 420, direct control 25, goal-first control 90, Q2 160, sentinel 15;
- complete Q1 counts, denominators, latent IDs, renderer coverage and gates;
- complete Q2 blocks, target-selection gate and sufficient statistics;
- direct control and full strata;
- sentinel counts and all first-occurrence fields;
- nominal sizing: 39 epochs / 6,123 groups;
- 662 zero-variance groups and 38 invalid completions;
- the exact authorization decision.

Exclude only identity fields expected to change under the new source. Add a few sensitivity regressions—row reorder, population substitution, and action alteration—to prove the comparison is meaningful.

This fixture is an outcome-informed migration oracle, not a new scientific gate or a source of additional design choices.

### 4. Do not build a general scheduler unnecessarily

The one-epoch schedule C2 authorized is already fixed as mixture `135a72bf…`. The simplest and strongest path is:

1. Materialize the complete legacy B2 mixture record once from its authenticated inputs.
2. Commit and bind both its file hash and self-hash.
3. Make `p0_schedule.py` a strict loader/validator for that artifact.
4. Let the later launch freeze specify how many complete epochs are executed.

A new general cohort-building framework would duplicate the reviewed B2 builder and create another opportunity for semantic drift.

Similarly, §2’s transport result justifies preserving heterogeneous diagnostics and avoiding homogeneous claims. It does not require a generic selectable per-latent/per-stratum rate engine. P0 sizing must remain the registered calculation over the three C2 cell counts and the exact existing cap formula.

### 5. Separate the Q2 quantities

“Q2 event/gate” is too broad. The spine must distinguish:

- checkpoint-zero marginal-support authorization;
- C2 eligibility;
- target-worker choice conditional on eligibility;
- optimal completions;
- direct contrast;
- semantic contrast.

The historical cold-start gate remains ≥8 target-worker selections from ≥2 latents among valid `q2_composite` completions, regardless of upstream correctness. It must not silently turn into the conditional P0 learning estimand.

### 6. Carry the final C2 scope and trajectory obligations

The machine-readable scope should encode:

- Q1-direct: `code_atomic`, `fork_join`, `math_code`;
- Q2: coarse, cell-correlated hierarchical unlocking;
- Q3: out of scope;
- `math_atomic`: training-exposed sentinel, not held out;
- sentinel excluded from Q1 gates, sizing, authorization and headline Q1 aggregates.

P0 reporting must retain raw numerators and denominators for the trajectory list in `301_f`, especially conditional Q2 eligibility/choice and the materially asymmetric fork-versus-math starting conditions.

### 7. Make immutability and authentication real

A frozen dataclass containing dictionaries and lists remains shallowly mutable. Use nested frozen dataclasses and tuples, canonical serialization, an explicit schema version, and a strict persisted loader. The consuming command must receive an externally reviewed expected hash; a self-hash alone is not authentication.

Historical supersession prose should live in the generated traceability appendix. Only active executable rules and identity-bearing provenance should affect the scientific contract hash.

### 8. Moderate the documentation claim

Generated numerical tables eliminate duplicated numbers, but they cannot make all prose/estimand divergence “structurally impossible.” Amend that to “mechanically detectable for generated numerical fields.” Independent invariants and human review remain necessary.

## Recommended implementation sequence

1. Freeze the schema, pinned-mixture artifact and exact C2 compatibility projection.
2. Implement `p0_contract.py` and the strict schedule loader.
3. Implement P0-forward estimands and prove exact C2 replay equivalence.
4. Add only the registered sizing/cap arithmetic and generated freeze tables.
5. Integrate the first real consumer, then construct the launch freeze after val/cycle/beta inputs exist.

Each unit should run the legacy C1 and C2 verifiers as well as its focused equivalence tests. Adding routing files will intentionally change the current source digest; historical identity remains established by the archived manifest and signed commit, not by regenerating the old manifest at the new HEAD.

With these amendments, I approve the contract-spine direction. I would issue the focused successor design and sign that before creating implementation commits.