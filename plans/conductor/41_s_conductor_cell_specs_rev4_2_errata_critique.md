Rev4.2 is very close. The requested fixes are substantively correct, but a regular review found six small contract interactions to resolve before formal sign-off. None requires changing a cell, renderer, grammar, or experimental design.

## Required corrections

1. **Profile bands must be cell-scoped.**

[E5 currently defines global names](/Users/ken/conductor_cell_specs_rev4_2_errata.md:102), but the cells deliberately use different ranges:

- `math_atomic.a_band`: \(10^4–10^6\)
- `math_code.a_band`: \(10^8–10^9\)
- Math T2 `m_band`: 5–60
- `math_code.m = L`: 8–16

Use nested names such as:

```text
profile.cells.math_atomic.a_band
profile.cells.math_atomic.T2.m_band
profile.cells.math_code.a_band
profile.cells.math_code.L_band
```

Give every cell independent profile fields by default. Any intentional inheritance—such as fork’s count branch initially copying Code-count defaults—should be represented explicitly. This matters both to Phase-2 tuning and the profile hash.

2. **Resource-error precedence must be global across the AST.**

[E1 says to apply the ladder “per required symbol”](/Users/ken/conductor_cell_specs_rev4_2_errata.md:23). That makes an expression such as `a + step_9` ambiguous: iteration order could produce either `E_NO_RESOURCE` or `E_UNKNOWN_IDENT`.

Instead:

```text
Parse AST.
Collect all resource demands and all step references.
Apply global conditions 1→4 in order:
1. resource demanded, none authorized → E_NO_RESOURCE
2. resource demanded, none compatible → E_RESOURCE_KIND
3. operands bound, any required identifier absent → E_UNKNOWN_IDENT
4. any step reference unavailable → E_UNKNOWN_IDENT
Then evaluate.
```

Resource-free Math still ignores incompatible resources, as intended. Add mixed-demand and unavailable-step-only fixtures.

3. **E2 must also amend §1.13.**

The new [ordinary and fork schedules](/Users/ken/conductor_cell_specs_rev4_2_errata.md:45) are correct, but unchanged [rev4.1 §1.13](/Users/ken/conductor_cell_specs_rev4_1.md:574) still says every cell starts at 100, expands by 200, and caps near 500.

Replace that parenthetical with the same two schedules:

- ordinary: 100/300/500;
- fork: 100/200.

4. **“Routing regret” is actually a signed comparator gap.**

The [current definition](/Users/ken/conductor_cell_specs_rev4_2_errata.md:77) compares against a fixed `(cell_id,node_id)` assignment, while the learned policy can condition on observable subtype and task wording. The policy can therefore legitimately outperform the deployable assignment, producing a negative value.

Define:

```text
signed_deployable_gap =
    correctness(frozen deployable assignment)
  - correctness(policy assignment)
```

Also state:

- malformed policy actions receive policy terminal-correctness 0;
- schema-valid rate is reported alongside;
- the gap is not clipped and may be negative;
- it is not regret against the best observation-conditional policy.

You can retain `routing_regret` as a legacy metric name, but the scientific label should be “signed deployable-assignment gap.” The new `best_fixed` and exact-uniform `random` definitions themselves are good.

5. **The smuggling detector cannot be both false-positive-prone and a lower bound.**

[E4 correctly allows false positives](/Users/ken/conductor_cell_specs_rev4_2_errata.md:86), then calls detections a lower bound on smuggling events. Those statements conflict.

Use:

> The token detector is a restricted proxy with incomplete recall and possible false positives; neither the true smuggling-event rate nor genuinely smuggling-free performance is bounded.

Also amend the corresponding “lower bound” statement in rev4.1 §1.11, not only §1.16. The sensitivity-score population and recoding rule are now correct.

6. **Finish the shallow predictor’s feature contract.**

[E7 remains ambiguous](/Users/ken/conductor_cell_specs_rev4_2_errata.md:139) about whether the tree is global or per-cell and whether “all public semantic parameters” includes strings such as key, field, and sign. A scikit-learn tree cannot consume that mixed matrix directly.

The simplest scientifically appropriate freeze is:

- one classifier per cell;
- subtype one-hot in frozen scheduler order;
- numeric columns exactly `[p, q, t, k, i]`, in that order;
- missing numeric values encoded as −1;
- sign/template/branch order represented through subtype;
- keys, fields, handles, and entity names excluded as randomized nuisance variables.

Add a tiny golden feature-matrix/prediction fixture; “refitting is deterministic” alone would not catch an accidentally changed column order.

## Non-blocking CE1 addition

Add proposed and accepted `(N, F, N×F)` distributions to construction telemetry. Record workload is the primary distractor/context-size control and belongs beside `(m,residue)` and `(U,t,answer)`.

Everything else now composes correctly: demand-free Math, fork-specific alpha spending, best-fixed/random controls, paired smuggling population, explicit sampler arguments, intervention seed bytes, envelope wording, and eligibility reporting. The consolidation into one canonical v0.5 file is also the right approach.

After the six corrections above, I would sign off Phase 1. They can be folded directly into the v0.5 consolidation without another architectural revision.