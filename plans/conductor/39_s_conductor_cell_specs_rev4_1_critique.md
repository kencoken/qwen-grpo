Rev4.1 closes the major rev4 findings correctly. I approve the architecture and cell design, but would make one final, short errata patch before marking Phase 1 formally frozen. No further cell or distribution redesign is warranted.

## Remaining freeze items

1. **Resource precedence still conflicts with literal-only Math.**

The spec permits Math to read an incompatible keyed record and [emit a literal](/Users/ken/conductor_cell_specs_rev4_1.md:61), but ladder item 2 would currently return `E_RESOURCE_KIND` whenever only incompatible resources are authorized.

Clarify that resource checks run only when the parsed AST requires a resource-bound symbol. A Math expression containing only literals and/or available `step_k` values ignores authorized resource kinds and may succeed. This matters directly to B5’s intended in-context capability.

2. **Fork’s qualification schedule contradicts the general schedule.**

[Section 1.14 specifies 100/300/500](/Users/ken/conductor_cell_specs_rev4_1.md:619), while [fork/join still specifies 100–200](/Users/ken/conductor_cell_specs_rev4_1.md:1015).

The natural resolution is:

- ordinary cells: looks at 100, 300, 500;
- fork/join: looks at 100, 200;
- separate pre-registered alpha spending for the two schedules;
- unresolved at the respective cap means no admission.

CE1 should specify one- versus two-sided boundaries for each gate.

3. **Restore best-fixed, random, and routing-regret controls.**

The rewritten [oracle section](/Users/ken/conductor_cell_specs_rev4_1.md:409) accidentally drops controls required by rev6 and present in rev4.

Define:

- `best_fixed`: construction-frozen best of `(0,…,0)`, `(1,…,1)`, `(2,…,2)`, under the same cluster-weighted objective and tie rule;
- `random`: exact uniform mean over the enumerated \(3^S\) payoff surface, not Monte Carlo samples;
- routing regret: paired cluster-weighted terminal-correctness difference between the frozen deployable assignment and the policy’s selected assignment on the same examples.

Best-fixed is particularly important: it distinguishes heterogeneous selection from the benefit of simply making multiple context-partitioned calls.

4. **Correct the interpretation and denominator of the smuggling sensitivity score.**

The [companion score](/Users/ken/conductor_cell_specs_rev4_1.md:685) must use exactly the same private, no-public-semantic-parameter-collision clusters, renderer observations, and cluster weights as the headline; only detected workflows are recoded as incorrect.

Call it a “detected-token-penalized sensitivity score.” It is numerically no greater than the headline, but it is not a bound on genuinely smuggling-free accuracy: undetected smuggling remains, while false-positive detections are also possible.

5. **Remove the remaining hard-coded sampler defaults.**

[Section 1.14 says no `(S)` band is hard-coded](/Users/ken/conductor_cell_specs_rev4_1.md:582), but then uses `[1,20]`, `[1,9]`, and `[1,99]`, and §2.2 retains Python-style defaults.

Use profile symbols instead:

```text
c ∈ profile.c_band
dedup values ∈ profile.dedup_value_band
select values ∈ profile.select_value_band
```

The current numbers can be labelled initial/default-profile values. Sampler functions should require the band argument rather than supply a default.

6. **Freeze intervention edge-label bytes.**

The [intervention seed](/Users/ken/conductor_cell_specs_rev4_1.md:563) hashes an undefined `edge_label`. Define it, for example, as UTF-8/ASCII `"{u}->{v}"`, with stable semantic node IDs, and add the seed and replacement to the golden fixture. The unused `"intervention"` per-instance substream label should either be removed or assigned a purpose.

## Freeze before construction, but not a cell-design blocker

The [shallow predictor](/Users/ken/conductor_cell_specs_rev4_1.md:496) says its configuration is fixed without supplying it. Either specify the implementation now or explicitly delegate it to CE1 before construction. Freeze:

- library/version and classifier;
- `max_depth=3`, criterion and minimum-leaf settings;
- seed and class-tie rule;
- subtype and missing-parameter encoding;
- one training row per latent cluster, rather than three duplicated renderer rows.

Parameter-echo predictors should only be evaluated in subtypes where that parameter exists.

Two very small wording improvements are also worthwhile:

- restore “content **between the tags** is trimmed” at [line 287](/Users/ken/conductor_cell_specs_rev4_1.md:287);
- report intervention eligibility rate alongside every intervention gate, since those are conditional causal estimates.

Everything else is now closed: seed derivation, routing IDs, B2’s two channels, node-to-position interventions, paired denominators, cache sharing and metadata, pseudo-workers, IR typing, collision reporting, truncation semantics, and the acceptance fixtures.

After the six short corrections above, I would formally sign off Phase 1. Construction should still wait for the separate D16 system-prompt freeze, as the document correctly states.