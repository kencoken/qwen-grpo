# Cell specifications v0.5 — consolidation note (response to the rev4.2 review)

The rev4.2 review
([`41_s_conductor_cell_specs_rev4_2_errata_critique.md`](41_s_conductor_cell_specs_rev4_2_errata_critique.md))
approved the architecture and asked for six small contract corrections,
stating they "can be folded directly into the v0.5 consolidation without
another architectural revision." Accordingly, this round produces the
consolidated canonical file directly:

> **[`/conductor_cell_specs.md`](../../conductor_cell_specs.md) (repo root) —
> v0.5, the phase-1 sign-off artifact.**

v0.5 = 38_f (v0.4.1) + 40_f (v0.4.2 errata E1–E8) merged verbatim, with the
six corrections folded in (marked **[v0.5]** in the file):

| # | Correction | Where |
|---|---|---|
| 1 | Profile bands cell-scoped: `profile.cells.<cell>.<param>_band`, independent fields per cell, `derived_from` annotations for intentional default-copies (fork count branch ← code_atomic) | §1.14 |
| 2 | Resource-error precedence applied **globally across the AST** (collect all demands, then conditions 1→4 in order) — `a + step_9` is deterministic; mixed-demand and step-only fixtures added | §1.6, §4 |
| 3 | The §1.13 namespace parenthetical now states the two look schedules (ordinary 100/300/500; fork 100/200), matching §1.14 | §1.13 |
| 4 | Primary Stage-2 comparator renamed **signed deployable-assignment gap** — unclipped, may be negative (the policy conditions on observables and can beat the fixed mapping); malformed actions score 0 with schema-valid rate reported; not regret vs the best observation-conditional policy; `routing_regret` = legacy alias (new erratum 9) | §1.8, §6 |
| 5 | Smuggling token detector = restricted proxy (incomplete recall **and** possible false positives; bounds neither the true smuggling rate nor smuggling-free performance) — corrected in both §1.11 and §1.16 | §1.11, §1.16 |
| 6 | Shallow-predictor feature contract completed: one tree per cell; subtype one-hot in frozen scheduler order; numeric columns exactly `[p, q, t, k, i]`; missing = −1; strings (key/field/handle/entity) excluded as randomized nuisance; golden feature-matrix/prediction fixture | §1.11, §4 |
| + | Non-blocking CE1 addition: proposed and accepted `(N, F, N×F)` distributions in construction telemetry | §1.14 |

No cell, fixture, renderer string, or grammar production changed; fixture
arithmetic has been unchanged since v0.2 (five review rounds).

**Requested action**: formal phase-1 sign-off of root
`conductor_cell_specs.md` v0.5. On sign-off, phase 1 freezes; Stage-0A code
begins; the D16 system-prompt artifact remains the separate reviewed freeze
before the construction screen.
