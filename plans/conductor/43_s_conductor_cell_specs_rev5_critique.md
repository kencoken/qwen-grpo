Rev5 is scientifically coherent and incorporates the previous feedback correctly. I would approve it after two small contract corrections; neither requires redesigning the cells.

## 1. Define B1’s subtype as observable

The [shallow predictor contract](/Users/ken/conductor_cell_specs_rev5.md:560) currently says “latent subtype one-hot in frozen scheduler order.” But the scheduler includes `target_stratum`, which is hidden when resources are private. That would technically let a “public-only” baseline consume private generator metadata.

Freeze the levels explicitly:

```text
lookup_atomic: constant
math_atomic: T1 / T2 / T3
code_atomic: count / select
lookup_math: minus / plus
math_code: constant
fork_join: lookup_first / code_first
```

Explicitly exclude `target_stratum`, renderer, split, and other generator-only fields. The per-`(cell, subtype)` majority/echo control at line 541 should use the same definition.

This probably would not change results materially, but it closes a provenance leak in an important shortcut control.

## 2. Validate the structural domain of tunable profiles

The [profile schema](/Users/ken/conductor_cell_specs_rev5.md:654) currently validates field presence but not all the structural assumptions that the default ranges satisfy. Because every `(S)` range remains tunable, a Phase-2 profile could otherwise violate Phase-1 semantics without necessarily producing a clean rejected proposal.

At minimum, validation should encode:

- Keyed records: `N ≥ 3` for three non-empty target strata; `N ≤ 20`, `F ≤ 10` for the name pools; sufficient value-band cardinality for the largest admitted `N×F`.
- Math atomic: preserve the stated band guarantees `b ≥ 10`, `c ≥ 1`, `d ≥ 2`; require a valid positive modulus.
- Lookup→Math: preserve `p ≥ 2`, `q ≥ 1`.
- Dedup tasks: ensure `L ≥ 5` and enough possible distinct values to attain `U ≥ 3`.
- Math→Code: `L ≥ 2` for a non-empty intervention alternative set, and list-value cardinality at least the maximum permitted `L`.
- Public values inserted as grammar literals must be nonnegative.
- Value bands that directly determine terminal answers must preserve the global `gold ≥ 1` contract.
- Fork/join must preserve positive branch outputs and `q ≥ 1`.

Add invalid-profile tests alongside the existing [sampler tests](/Users/ken/conductor_cell_specs_rev5.md:1262). The general rule should be: every `requires`, “band-guaranteed,” grammar, intervention-support, and without-replacement assumption in the frozen specification is enforced by profile validation.

There is one associated inconsistency: the Lookup→Math and fork interventions still sample from hard-coded `[10,99]` at [line 1048](/Users/ken/conductor_cell_specs_rev5.md:1048) and [line 1192](/Users/ken/conductor_cell_specs_rev5.md:1192), even though their value bands are tunable. I recommend sampling from the respective cell’s frozen Phase-2 `value_band`, excluding the original value. Alternatively, `[10,99]` must become an explicitly non-tunable Phase-1 constant.

A minor wording cleanup at [line 633](/Users/ken/conductor_cell_specs_rev5.md:633) would also help: state that every namespace has its own predeclared maximum and stopping rule, while only `qualification` uses the 100/300/500 and 100/200 sequential-look schedules.

Everything else passes: payoff definitions, signed comparator, sequential inference, cell-scoped profiles, interventions, smuggling sensitivity, telemetry, and the global AST error procedure are now aligned. After the two corrections above, I would sign off Phase 1 without another full review; a targeted diff check is sufficient.