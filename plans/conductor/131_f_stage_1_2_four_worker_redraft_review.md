# 131_f — Review of the 130_s Stage-1/2 four-worker redraft

**Verdict: directionally correct and close to signable.** The draft covers
all seven `127_f` Stage-1 prerequisites, resolves every `106_s` §15 deferral
it is obligated to resolve, keeps the §1.2 frozen contracts intact, and its
§1.1 amendment table upholds the no-silent-override discipline. This review
requests one substantive reconsideration (the confirmatory C2-compat
branch), one mandatory disclosure (the fork dependency of C2), three
pre-CE1 feasibility computations, and a set of smaller record and
completeness items. No code was changed for this review.

---

## 1. Scope and verification performed

Reviewed: `130_s_stage_1_2_four_worker_redraft.md` in full, against
`127_f` (prerequisites + carried evidence), `129_f` (dispositions, queued
items), `106_s` §§11–15 (cold-start arithmetic, carried controls, deferred
decisions), and `123_s` §9 (demonstration-treatment decision).

Independently recomputed, from the CE0 measured physical-generation units
(124 per fully crossed latent set; 12 atomic / 24 chain / 40 fork with
`12/12/16` renderer split):

| 130_s figure | recomputed | match |
|---|---:|---|
| six-cell train generations (one balanced renderer) | 4,132–4,136 | ✓ |
| six-cell dev (`dev_select`+`pilot_gate`) generations | 4,464 | ✓ |
| six-cell test generations (56 clusters/cell) | 6,944 | ✓ |
| five-cell totals (2,800 / 3,024 / 5,628) | same | ✓ |
| payoff rows 10,800 / 11,664 / 18,144 / 8,844 | same | ✓ |
| cold-start rows/generations 6,048 / 1,824 (six-cell), 1,440 / 864 (five-cell) | same | ✓ |
| minimum reward-bearing policy completions 3,456; format cohort A 288/240 | same | ✓ |
| update counts 300 / 250; snapshot counts 13 / 11; test passes 4,032 / 4,020 / 5,040 | same | ✓ |

The §13 compute plan is internally consistent and correctly refuses to
treat renderer crossing as de-duplication.

Prerequisite coverage (127_f items 1–7): manifests §4; parse-gate mapping
§§7.1–7.2; ≥64-group cold start §10.2 (72 ≥ 64); B1 §5.3, `SYSTEM_DIRECT`
§17, D4 §3.1, `math_code` band §5.2 (129_f item 6 carried normatively);
demonstration treatment §§10.1–10.3; stakes sufficiency §6 and
cached-vs-live §11.3; deferred notes §9.2/§2 (C4/C5). Complete.

Strengths worth naming: the §6.1 family-stake definition fixes the real
flaw in the old best-versus-runner-up rule (the other Code worker could
mask a strongly learnable family decision); the C1/C2 sibling framing is
honest; §7.2 is the right resolution of the two-imperfect-Code-workers
parse-gate question; the §8.3 rare-event Clopper–Pearson handling addresses
a genuine zero-event bootstrap failure.

---

## 2. Principal structural concern — C2 silently depends on fork

§9 requires qualified positions favouring **both** workers for task/node
model headroom. Core has exactly two C2 positions (`code_atomic n1`,
`math_code n2`), and every retained Stage-0 observation at both points the
same way: the canary (`code_atomic`, w2 0.5 / w3 1.0) and
`math_code × goal_first` both favour worker 3. The only measured worker-2
advantage lives in `fork_join` — the cell §9.1 makes optional.

On current evidence, **Core-only C2 headroom is likely unreachable by
construction**, and C2 rides entirely on fork passing all four of its
admission gates. The draft never states this. It must, because it changes
what REVIEW CHOICE 9 means: "fork optional" reads as a conservative
simplification but is effectively "C2 conditional on fork."

Requested change: either (a) state the dependency explicitly and set the
outcome expectation — the realistic branches are Core+fork-with-C2 or
C1-only — or (b) reconsider whether qualified-position bidirectionality is
the right definition of C2 headroom (noting `s` "uses both workers" already
encodes construction-level bidirectionality). We are content with (a); the
choice is the reviewer's, but it must be made in the open.

Compounding item: the §10.2 ≥10% direct model-gradient-group gate. On
fork, a direct model-gradient group requires two specific assignments out
of 64 to co-occur in a group of 8 with distinct payoff. Stage 0's own
smoke measured 2/36 such fork groups (5.6%) — below the gate. The
demonstration prior concentrates mass on family-correct actions, so the
true rate may be higher, but see §3 item (b): compute it before freezing a
gate that may be unachievable-by-construction for exactly the direction C2
needs. The branch algebra degrades coherently (C2 → C2-compat → C1), so
this is a disclosure-and-computation issue, not a design flaw.

---

## 3. Feasibility computations required before CE1 freeze

(a) **Power at the look caps.** Looks 100/300/500 (ordinary) and 100/200
(fork) are registered with no adequacy argument. After the §8.2 splits,
the scale-stake tail alpha is roughly `0.05/3 ÷ 2 families ÷ 2–3
positions` ≈ 0.002–0.004 one-sided. A short frozen power computation —
using construction point estimates, blind to qualification — must show a
true 10–15-point stake is detectable at the cap. One page, alongside the
coverage battery artifact.

(b) **Expected direct model-gradient-group rates per topology.** Compute
analytically from the measured Stage-0 selection distribution (the
recorded smoke) under both prompt candidates, per admitted direction,
before the 10% gate freezes. If the expected fork-direction rate is below
threshold under the measured prior, the gate is a predetermined outcome,
not a measurement.

(c) **The persistence envelope can be unresolvable when eligibility is
sparse.** With zero observed events in 500 clusters but eligibility near
10%, `min(1, m × U_CP(any_event) / L_CP(any_eligible))` evaluates to
roughly `3 × 0.01 / 0.08 ≈ 36%` — failing the ≤10% gate with zero
persistence events observed. If eligibility is structurally constant for
every gated cell, the envelope collapses to `U_CP(any_event)` ≈ 1% and is
fine. Verify against the planned eligibility fractions before freezing, or
specify the non-constant-eligibility handling differently.

---

## 4. Overly speculative machinery

1. **The confirmatory C2-compat branch — our one push-back on a
   recommended default.** The `s_compat` apparatus (renderer-stratified
   stakes, 6–9-way Bonferroni, `Delta_compat_fixed`, `ModelGO_compat`,
   stratified cold-start directions) exists to salvage a deliberately weak
   claim, and §8.2 pays for it by splitting the model-position alpha
   across semantic and compatibility families — **halving the alpha
   available to the primary semantic claim**. Recommendation: make
   C2-compat descriptive-only in v1 and spend full alpha on `s`. This
   simplifies §6.3, §8.2, §9, §10.3, §12.4, and §14.4 simultaneously. If
   the reviewer retains the confirmatory branch, the alpha cost to C2
   should be acknowledged as a priced trade, not a free option.
2. **The coverage-simulation battery (§8.3)** is the heaviest new
   machinery in the document — a multi-scenario Monte Carlo acceptance
   suite with a Wilson-bound miscoverage criterion — and it is not costed
   as its own §16 unit. Either budget it explicitly or trim it to the two
   genuinely nonstandard constructions: the cell-stratified equal-cell
   aggregate and the rare-event envelopes.
3. **`FORMAT_REPAIR_V1`** is mild YAGNI given the measured 144/144
   reward-blind format validity, but it is cheap and fail-closed; it can
   stand as drafted.

The §15 predictions and named failure modes are preregistration culture
working as intended, not speculation.

---

## 5. Smaller items

1. **123_s §9 is not explicitly disposed.** The claim-headroom priority
   rule is a defensible refinement of 123_s's "near-ceiling → schema-only
   primary" rule, but 123_s point 4 asked for a no-few-shot **ablation**
   when few-shot is primary; the draft defers all non-primary training to
   a later reviewed plan without citing what it overrides. Cite and
   dispose.
2. **Symmetric untrained descriptive pass.** §10.3 provides the untrained
   few-shot test pass only when schema-only wins. The mirror pass
   (untrained schema-only when few-shot wins) costs ~1,008 cached-surface
   greedy generations — essentially free — and completes the untrained row
   of the 123_s four-cell table in both branches. Add it.
3. **Queued `workerpool.py` citation fix.** 129_f queued the three stale
   `108_f` comment citations for exactly the moment §4 mandates: the
   successor source digest. Add the fix to §16 unit 2 (or the CE1 freeze
   checklist) so the new digest is not issued with stale citations.
4. **Silently settled `106_s` §15 items.** Keeping group size 8 (relevant
   given fork sparsity) and deferring the `local_only`/BF16/
   constrained-decoding ablations are both reasonable, but each §15 item
   should carry a one-line disposition rather than being settled by
   omission — the standard the draft applies everywhere else.
5. **Cold-start dead end.** If fork is admitted at qualification but its
   cold-start variance strata fail for **both** prompt treatments, §10.3
   rule 5 forces a full stop for a new launch-profile review — for a
   failure mode the draft itself predicts ("fork reward too sparse").
   A preregistered "drop fork, recompute the Core-only comparison"
   fallback, frozen now before any reward data, avoids a replan without
   creating a post-hoc branch choice. Put to the reviewer as an explicit
   choice.
6. **Notation.** §6.2 uses `w_scale(c,j,r)` in the compat definitions but
   defines only `w_scale(c,j)`; state the per-renderer-stratum winner
   explicitly.
7. **D4 balance test.** "Preserves the factorial balance rule" for indices
   30–129 is asserted; if latent generation does block arithmetic on the
   index, the +30 offset could shift block alignment. §5.1's
   "implemented and tested" must cover balance, not only range rejection.

---

## 6. Positions on the §17 review choices

| # | choice | position |
|---:|---|---|
| 1 | D4: 30–129, cap 130 | **sign**, with the §5.7 balance-test requirement |
| 2 | visible slice: first 18/cell | **sign** |
| 3 | profile discipline | **sign** |
| 4 | `math_code` full band, no silent ≤8 cap | **sign** — the retained low-index semantic failure justifies it |
| 5 | parse gate mapping | **sign** — correct resolution of the 106_s §15 deferral |
| 6 | retry/cascade taxonomy | **sign** |
| 7 | sequential inference | **sign conditional** on §3(a) power computation and §4.2 battery scoping/budgeting |
| 8 | scale materiality | **sign** |
| 9 | minimum cells, fork optional | **sign conditional** on the §2 explicit C2-dependency disclosure |
| 10 | scale-null branch: four-worker C1 path | **sign** |
| 11 | prompt selection by claim-headroom priority | **sign conditional** on §5.1 (123_s disposition) and §5.2 (symmetric untrained pass) |
| 12 | cold start: 72 groups + ≥10% direct-gradient | **sign conditional** on §3(b) analytic rate check and the §5.5 fork-drop rule decision |
| 13 | Stage-2 population formulas | **sign** — arithmetic verified §1 |
| 14 | training schedule/checkpoint rule | **sign** — the signed-gap criterion is equivalent to terminal-accuracy ordering on fixed `dev_select`, so the redundancy note is correct |
| 15 | pilot/continuation | **sign** |

Plus the one non-default recommendation: **demote C2-compat to
descriptive in v1** (§4.1).

---

## 7. Requested changes, consolidated

1. State the fork dependency of C2 and set outcome expectations (§2).
2. Decide C2-compat confirmatory vs. descriptive with the alpha cost
   priced; our recommendation is descriptive-only in v1 (§4.1).
3. Add the three pre-CE1 feasibility computations: look-cap power,
   direct-gradient-group rates from the measured Stage-0 distribution,
   persistence-envelope behavior at planned eligibility fractions (§3).
4. Budget or trim the coverage-simulation battery (§4.2).
5. Cite and dispose 123_s §9; add the symmetric untrained descriptive
   test pass in both prompt branches (§§5.1–5.2).
6. Add the queued `workerpool.py` citation fix to the unit issuing the
   successor source digest (§5.3).
7. Add one-line dispositions for the silently settled 106_s §15 items and
   a preregistered fork-drop rule for the cold-start dead end (§§5.4–5.5).
8. Minor: `w_scale(c,j,r)` notation; D4 balance-test scope (§§5.6–5.7).

Everything else — estimand definitions, manifest/retirement discipline,
the phase state machine, population formulas, checkpoint rule, and the
evaluation-path choice — we would sign as drafted. None of the requested
changes touches a frozen contract; all are amendments to the unfrozen
130_s draft before CE1.
