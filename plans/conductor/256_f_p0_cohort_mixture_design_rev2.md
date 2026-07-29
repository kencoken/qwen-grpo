# 256_f — Constrained P0 cohort/mixture design REV2 (response to 255_s)

All five blocking issues and both lifecycle/accounting corrections
adopted. The architecture is unchanged (per 255_s closing); what
changes is executability and the promotion of Units A–C into ONE
reproducible experiment with mechanically decidable gates. Still a
design document: nothing frozen, no GPU spent.

## 1. The three registered development questions

Everything below is organized so each gate serves exactly one of
(255_s B5):

- **Q1 — C1 family-routing learning** (incl. escaping the
  `math_atomic` basin and holding the saturated lookups).
- **Q2 — hierarchical unlocking**: C1/topology improvement creating
  later C2 eligibility on composites. A checkpoint-zero C2 count of
  ZERO does not block Q2 — it is Q2's starting condition — but it
  can never support a direct-C2-exposure interpretation.
- **Q3 — bidirectional within-cell specialist learning** (the full
  claim; separable per direction).

## 2. The reviewed lifecycle (refinement of the charter sequence)

Recorded as the reviewed refinement of 211_f's sequence (255_s):

1. **Unit A** freeze → run → closeout.
2. **Unit B**: freeze the EXACT mixture (cohort, class membership,
   integer schedule, sampler) — before Unit C, killing the B/C
   circularity (255_s B1). Unit C may determine only P0 duration
   and objective scope via its preregistered decision rule; ANY
   cohort or weight change afterward requires a fresh
   exact-mixture sample (a new B/C iteration, never an in-place
   adjustment).
3. **Unit C** run → apply the preregistered objective-scope/budget
   decision, nothing else.
4. Freeze + materialize `routing_dev_val`; freeze the
   `routing_dev_cycle` cohort AND the checkpoint-selection rule;
   finalize `R_cycle` from the registered 231_f basis.
5. `beta = 1e-3` timing smoke (ledger-recorded).
6. P0 freeze, complete (cohort, mixture, updates, cadence,
   transport rule byte-reproducible, fp32 LoRA, v1 contract).
7. Checkpoint-zero evaluation FIRST, then training.

## 3. Unit A rev2 — support extension as a six-cell prefix

**Resolution of 255_s B2** (confirmed against
`dev_support.validate_dev_cohort`: every development cohort must
cover all six cells, the complete renderer crossing, and
outcome-blind 0..k-1 prefixes — a Code-only 6–45 cohort is
rejected by the existing validator):

- **Cohort**: the factor-balanced six-cell prefix **0–47** (48
  latents × 6 cells × 3 renderers = 864 observations); a new,
  self-contained support-extension launch through the existing
  low-level surface machinery (declare/materialize under a new
  surface lock; no composite partial locks). Only the NEW
  observations (indices 6–47: 756) are materialized; 0–5 is the
  existing Step-4 support and must byte-match under the new lock's
  provenance.
- **Candidate selection domain**: 6–47. The prefix itself stays
  outcome-blind; the SELECTION over it (below) is
  outcome-conditioned and disclosed (`outcome_informed = true`).
- This also expands `math_atomic` for the Q1 curriculum (255_s).
- **`c_fixed_dev` stays frozen as selected in Step 4 (worker 2)**
  and is NOT reselected on this outcome-conditioned expansion; all
  C2/ModelAcc/ScaleLift metrics keep their frozen baseline.

**Direction qualification (255_s B3 — renderer crossing ≠
deconfounding).** Direction labels are per-OBSERVATION (per
renderer), derived from authenticated surface geometry exactly as
in the probe report:

- A latent qualifies for a direction IN a renderer stratum iff that
  rendered observation is payoff-distinct favoured for that worker.
- **One latent may count for both directions** (different
  renderings favouring different workers is genuine within-latent
  bidirectionality — the strongest evidence) but counts at most
  once per (direction × renderer stratum), and multi-latent
  requirements are always per direction.
- **Quotas (per Code cell × direction):** target ≥3 independent
  latents, spread over ≥2 renderer strata, with ≥1 latent whose
  favoured label holds under a NON-`goal_first` renderer.
- **Full-claim bar:** each direction occurs across multiple
  independent latents AND multiple renderer strata within at least
  one COMMON cell (so no cell/renderer lookup can mimic the claim).
- **Dispositions, fixed now:** ≥3 latents = full quota; exactly 2 =
  proceed at reduced power with explicit disclosure in the Unit-A
  closeout; <2 = that (cell × direction) is dropped from Q3's
  claim (recorded, never widened ad hoc).
- **Selection rule** frozen before materialization; deterministic
  (ascending latent index within each quota bucket); selection uses
  authenticated payoff surfaces only — never probe rollout luck.

**Cost basis (255_s correction).** The 254_f estimate is
WITHDRAWN as understated: it priced observations at the Step-4
average, but Code cells carry far larger 4^S assignment grids
(the reviewer's figure for the Code-only variant: ~27,360 planned
node executions vs 4,824 in Step 4 ⇒ ≈0.42 GPU-h). The six-cell
0–47 prefix adds the three cheap cells; the Unit-A freeze will
derive the expected cost exactly from per-cell node counts.
**Ceiling: 1.0 GPU-h** (255_s: a full six-cell prefix justifies
it).

## 4. Unit B rev2 — an exact, reproducible mixture

**Mutually exclusive classes with frozen precedence** (255_s B4):
every observation in the expanded support belongs to exactly ONE
class, assigned in this order:

1. **Direction** — observations payoff-distinct favoured for w2 or
   w3 (Unit A's selection), balanced w2:w3.
2. **Bridge** — remaining observations satisfying the deterministic
   semantic-variability predicate (below). This class RETAINS the
   major measured C1 sources: tied `code_atomic` and `fork_join`
   rows (42 of the probe's 46 semantic groups) alongside the
   `math_atomic`/`math_code` basin rows (2 each).
3. **Anchor** — everything else, including the saturated
   `lookup_*` cells (downweighted, retained for
   saturation/forgetting visibility).

**Semantic-variability predicate (deterministic, surface-geometry
only):** an observation is semantically variable iff its
authenticated payoff surface takes ≥2 distinct values over the
full assignment grid — i.e. not payoff-flat. No rollout data, no
probe luck, enters the predicate.

**Exact integer schedule:** Unit B freezes an integer row schedule
— exact counts per (class × cell × direction × renderer) stratum
per epoch, with duplicate handling explicit (an observation appears
in the schedule with an integer multiplicity; no sampling
distribution left implicit) and a frozen deterministic shuffle
seed. Draft mass remains ≈45% direction / ≈35% bridge / ≈20%
anchor (lookups ≤ half the anchor), realized as integers over the
actual Unit-A yield; the FROZEN schedule is what Unit C samples.
Evaluation stays the frozen natural equal-cell mixture on
`routing_dev_val`, untouched.

## 5. Unit C rev2 — mechanical gates

The rev3-validated zero-update machinery on the EXACT frozen Unit-B
schedule, fresh seed, ~500 groups; **ceiling 1.0 GPU-h**. Gate
constants below are the draft values; the separately reviewed
Unit-C freeze fixes them, and after the run they are decided
mechanically — no judgment calls, no in-place redesign (255_s B5).

- **Gate Q1 (per C1-critical cell — `code_atomic`, `fork_join`,
  `math_atomic`, `math_code`):** ≥15 reward-varying semantic groups,
  drawn from ≥2 distinct latents and ≥2 renderer strata. Any cell
  failing Q1's gate is dropped from the Q1 claim.
- **Gate Q2 (w3-favoured composites):** ≥8 completions placing the
  favoured specialist correctly at the specialist step (ModelAcc
  numerator) across ≥2 latents. C2 eligibility MAY be zero
  (starting condition); Q2 then reads as unlocking-only, and NO
  direct-C2-exposure interpretation is permitted anywhere
  downstream.
- **Gate Q3 (per direction, separately):** ≥10 payoff-distinct
  exact co-sampling groups, across ≥2 latents AND ≥2 renderer
  strata, AND marginal support — each specialist sampled ≥25 times
  at the decisive step within that direction's rows. A direction
  failing Q3 is dropped from the bidirectional claim; if both fail,
  P0 is scoped as a Q1+Q2 experiment.
- **Preregistered decision rule:** the gate outcomes select the P0
  objective scope (Q1+Q2+Q3-both / Q1+Q2+Q3-one-direction / Q1+Q2)
  and its duration per §6 sizing — nothing else. Any change to
  cohort, classes, schedule, or weights = a new B/C iteration.

## 6. P0 shape (unchanged from 254_f §7 except sizing inputs)

G=8 default (G=16 only via the registered 4090 smoke + grouped
reprobe, and only if Unit C shows nonzero marginals with
insufficient co-sampling); sizing from raw exposure counts (~100
semantic-gradient groups per critical C1 component; 30–50
payoff-distinct contrasts per claimed direction) using Unit C's
measured exposure and the beta-timing smoke; trajectory reporting
per 253_s R6 at every checkpoint (C1, C2 eligibility, C2
optimality, ModelAcc, ScaleLift, all-0.5 vs all-1.0, entropy,
renderer-stratified; latents = the independent unit);
checkpoint-zero evaluation first; fp32 LoRA normative; v1
checkpoint contract; byte-reproducible transport rule.

## 7. Budgets (all stop-and-review; envelope after STEP 7 — the execution/review of the Step-6-frozen probe: 59.3539 GPU-h remaining)

| Item | GPU ceiling | Basis |
|---|---|---|
| Unit A — six-cell prefix-48 extension | 1.0 GPU-h | exact per-cell node counts at the Unit-A freeze (Code-only variant ≈0.42; six-cell higher) |
| Unit C — exact-schedule sample | 1.0 GPU-h | ~500 groups × 4.33 s + headroom |
| `routing_dev_val` materialization | ceiling set at its freeze | same surface machinery; scale known after val cohort is fixed |
| beta=1e-3 timing smoke | 0.1 GPU-h | ~50 groups |
| `R_cycle` reserve admission | finalized at step 4 from the 231_f basis | replaces the provisional 5.0 GPU-h |
| P0 | sized by Unit C | separate complete freeze |

## 8. Unchanged by this revision (per 255_s)

Finite outcome-conditioned search with full disclosure and no
ad-hoc widening; natural equal-cell evaluation; G=8 default;
exact-mixture zero-update sample; beta timing smoke;
checkpoint-zero-first; C1→C2 trajectory reporting; the 254_f §1
erratum to 252_f stands as recorded.

## 9. Next

Reviewer pass on this rev2 → separately reviewed **Unit-A freeze**
(cohort prefix, selection rule with quotas/dispositions, exact cost
derivation, ceiling, lineage on head `88c037a1…`) → run → Unit B
freeze → Unit C freeze → run → preregistered gate decision → val +
cycle + `R_cycle` → timing smoke → P0 freeze → checkpoint-zero
eval → P0.
