Rev7 resolves all four substantive points from the previous review. One narrow contract contradiction remains around `R_MAGNITUDE`, plus two mechanical terminology replacements.

## Required correction: separate load validation from candidate rejection

The [profile-validation preamble](/Users/ken/conductor_cell_specs_rev7.md:726) says every listed rule rejects the profile at load. But [`R_MAGNITUDE`](/Users/ken/conductor_cell_specs_rev7.md:765) rejects individual generated candidates toward the 75% cap, while the [test list](/Users/ken/conductor_cell_specs_rev7.md:1375) again classifies it as a load-time invalid-profile failure.

Move it into a separate paragraph such as:

```text
Instance-level pre-admission rejection — not profile-load validation:

R_MAGNITUDE rejects a candidate toward its full_latent_stratum rejection
cap if exact, limit-aware evaluation of either:

1. the base reference execution; or
2. any deterministically drawn intervention/counterfactual reference execution

would exceed |v| ≤ 10^12 at any checked leaf, intermediate/operator
result, or terminal result.
```

Checking intervention paths matters. A base Lookup→Math instance can be magnitude-safe while its alternative `n1'` makes `p*n1' ± q` overflow. Similar cases exist for fork replacements and Math→Code’s alternative selected value.

Then separate the tests:

- Invalid-profile fixtures: expect rejection at load.
- `R_MAGNITUDE` fixtures: expect candidate rejection during generation.
- If every candidate is rejected, expect the existing clean profile-screen failure at the resampling cap.

## Two terminology replacements

Now that two subtype concepts are explicitly distinguished:

- At [line 700](/Users/ken/conductor_cell_specs_rev7.md:700), replace “whose subtype exceeds the cap” with “whose `full_latent_stratum` exceeds the cap.”
- At [line 877](/Users/ken/conductor_cell_specs_rev7.md:877), report collision rate by `cell × full_latent_stratum`, not bare `cell/subtype`.

Everything else passes: the profile predicates, `S⁻` intervention support, public-literal bounds, namespace batching, observable B1 features, latent-stratum definition, qualification reporting, and leakage conditioning are now consistent.

After this one magnitude-contract clarification and the two word replacements, I would sign off Phase 1.