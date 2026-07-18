# Conductor cell specifications — v0.4.2 errata (final phase-1 patch)

The short errata patch requested in
[`39_s_conductor_cell_specs_rev4_1_critique.md`](39_s_conductor_cell_specs_rev4_1_critique.md)
("I approve the architecture and cell design … After the six short
corrections above, I would formally sign off Phase 1").

**Scope**: this document amends
[`38_f_conductor_cell_specs_rev4_1.md`](38_f_conductor_cell_specs_rev4_1.md)
with exact replacement text; the phase-1 freeze content is **v0.4.1 as
amended here**. On sign-off, the two documents are consolidated into a
single frozen `conductor_cell_specs.md` (v0.5, verbatim merge, no new
content) at the repository root before any 0A code — so implementation
reads one canonical file. No cell, fixture, renderer string, or grammar
production changes below.

---

## E1. Resource checks are demand-driven (amends §1.6, resource-error ladder)

The ladder's preamble is replaced by:

> **Resource checks run only when the parsed AST requires a resource-bound
> symbol** (Lookup's `resource`, Code's `resource`, or a Math single-letter
> identifier). Evaluation order: envelope → grammar parse → collect required
> symbols → apply the ladder per required symbol → evaluate. An expression
> containing only literals and/or available `step_k` values **ignores the
> authorized resource set entirely and may succeed**, whatever resources are
> or are not authorized.

Ladder items 1–4 are unchanged and apply per required symbol; item 5 is
subsumed by the preamble and reads:

> 5. a literal-only (or literal + available `step_k`) Math expression
> requires no resource and may succeed with any binding set, including an
> empty or incompatible one.

Consequence made explicit for B5 (§1.11): a Math endpoint given only a
keyed record may read it in-context and emit a literal expression; no
`E_RESOURCE_KIND` fires unless the expression itself demands a binding.
An acceptance case is added to §4's grammar tests: literal-only Math
expression with (a) no authorized resource and (b) an incompatible
authorized resource — both succeed.

## E2. Two qualification look schedules (amends §1.14 and §3.6)

The sequential-inference paragraph of §1.14 is replaced by:

> **Sequential qualification inference (pre-registered)**: gate CIs use
> alpha spending across pre-registered look schedules — **ordinary cells:
> looks at 100, 300, 500 clusters/cell; fork/join: looks at 100, 200** —
> with a **separate pre-registered spending function for each schedule**,
> both fixed in CE1 before any qualification data, which also specifies
> **one- versus two-sided boundaries per gate**. Stopping semantics
> (frozen, per schedule): a conclusively failed gate stops as failure; all
> gates conclusively passing stops as pass; **unresolved at the respective
> cap means no admission**.

§3.6's "qualification slice 100–200 latent clusters if paired CIs are
decisive" is replaced by "qualification looks at 100 and 200 latent
clusters (§1.14 fork/join schedule)".

## E3. Best-fixed, random, and routing-regret controls (amends §1.8)

The following block is restored to §1.8 (rev6 requires these; the rev4.1
rewrite dropped them):

> **Controls (frozen definitions)**:
>
> - **`best_fixed`** — the construction-frozen best of the three constant
>   assignments `(0,…,0)`, `(1,…,1)`, `(2,…,2)`, selected under the same
>   cluster-weighted objective and tie rule (lowest endpoint index). This is
>   the control that distinguishes heterogeneous *selection* from the
>   benefit of simply making multiple context-partitioned calls.
> - **`random`** — the **exact uniform mean over the enumerated 3^S payoff
>   surface** (analytic, never Monte Carlo samples).
> - **Routing regret** (primary Stage-2 metric, per rev6/CE1) — the paired
>   cluster-weighted terminal-correctness difference between the frozen
>   deployable assignment and the policy's selected assignment **on the
>   same examples**.

## E4. Detected-token-penalized sensitivity score (amends §1.16)

The "conservative companion score" bullet is replaced by:

> **Detected-token-penalized sensitivity score**: a secondary scoring
> computed on **exactly the headline population** — the same private,
> no-public-semantic-parameter-collision clusters, the same renderer
> observations, the same cluster weights — in which every workflow with a
> detected answer-in-subtask event is recoded as incorrect. It is
> numerically ≤ the headline by construction, but it is **not a bound on
> genuinely smuggling-free accuracy**: undetected smuggling remains, and
> false-positive detections are possible. The token detector is a lower
> bound on smuggling events, not on smuggling-free performance.

## E5. Profile symbols replace inline band defaults (amends §1.14, §2.2)

All sampler bands are named profile symbols; the numerals given in this
spec are the **initial default-profile values**, stored in the difficulty
profile, never hard-coded in samplers:

> `c ∈ profile.c_band` (default [1, 20]); `dedup values ∈
> profile.dedup_value_band` (default [1, 9]); `select values ∈
> profile.select_value_band` (default [1, 99]); likewise `profile.a_band`,
> `profile.b_band`, `profile.d_band`, `profile.m_band`, `profile.L_band`,
> `profile.t_band`, `profile.k_band`, `profile.p_band`, `profile.q_band`,
> `profile.record_value_band`, `profile.N_band`, `profile.F_band`.

§2.2's sampler signatures **require** their band arguments (no Python
defaults):

```python
integer_record(N, F, value_band, layout)
integer_list_dedup(L, value_band)
integer_list_select(L, value_band)
```

The §3 parameter tables are read as the default profile's values for these
symbols (all already (S)-marked).

## E6. Intervention edge-label bytes and substream cleanup (amends §1.13, §4)

- **`edge_label` (frozen)**: the ASCII/UTF-8 string `"{u}->{v}"` over
  stable semantic node ids — e.g. `"n1->n3"` — exactly as already written
  in §3's intervention sections; no whitespace, lowercase node ids.
- The **unused per-instance `"intervention"` substream label is removed**
  from §1.13's substream list (intervention seeds derive from
  `h64("intervention" ␟ latent_program_id ␟ edge_label)`, not from a
  per-instance substream; the four remaining labels are `"values"`,
  `"names"`, `"handles"`, `"manifest"`).
- The **golden seed/ID fixture** (§4) additionally pins, for its fixture
  instance: the intervention seed bytes for one edge and the drawn
  replacement value.

## E7. Shallow-predictor configuration (freeze before construction; amends §1.11 B1)

Specified now rather than delegated:

> **Frozen shallow predictor**: scikit-learn `DecisionTreeClassifier`
> (library version pinned by the repository lockfile) with `max_depth=3`,
> `criterion="gini"`, `min_samples_leaf=5`, `random_state=0`; prediction
> ties resolve to the lowest class label. Features: latent subtype
> (one-hot) plus all public semantic parameters, with parameters absent in
> a subtype encoded as the sentinel −1. **One training row per latent
> cluster** (the canonical `resource_first` rendering — never three
> duplicated renderer rows). Fitted on construction data only, then frozen.
> **Parameter-echo predictors are evaluated only in subtypes where that
> parameter exists.**

## E8. Wording corrections (amends §1.6, §1.9)

- §1.6 envelope case 6 reads: "else: content **between the tags** is
  trimmed, parsed by the endpoint grammar."
- §1.9 reporting: **the intervention eligibility rate is reported alongside
  every intervention gate** (corruption, counterfactual consistency,
  old-answer persistence, follow-through) — these are conditional causal
  estimates and their conditioning fraction is part of the result.

---

## Acceptance-hook additions (amends §4)

- Literal-only Math expression succeeds with empty and with incompatible
  binding sets (E1).
- `best_fixed`, exact-uniform `random`, and routing-regret computations
  verified against a hand-enumerated toy payoff surface (E3).
- Sensitivity-score population identity: same clusters/observations/weights
  as the headline; only detected workflows recoded (E4).
- Samplers reject calls without explicit band arguments (E5).
- Golden fixture extended with intervention seed + replacement (E6).
- Shallow-predictor determinism: refitting on identical construction data
  reproduces identical predictions (E7).

## Status

| Item | Effect |
|---|---|
| E1–E6 | the reviewer's six formal freeze corrections |
| E7 | shallow-predictor freeze, required before construction |
| E8 | wording corrections |

Phase-1 content = **v0.4.1 (38_f) as amended by this document**; on
sign-off it is consolidated verbatim into the frozen root-level
`conductor_cell_specs.md` (v0.5) before any 0A code. The D16 system-prompt
artifact remains a separate reviewed freeze before the construction
screen, as 38_f states.
