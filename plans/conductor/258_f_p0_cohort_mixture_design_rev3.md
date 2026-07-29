# 258_f — Constrained P0 cohort/mixture design REV3 (response to 257_s)

All three result-affecting issues repaired, and the five
required-at-freeze items recorded as explicit gates. I reproduced
the 257_s B1 finding before repairing it: every one of the 108
Step-4 observations has payoff set exactly {0.5, 1.0}, so the rev2
"non-flat" Bridge predicate is degenerate (Anchor empty, 45/35/20
unconstructible). Architecture otherwise unchanged.

## 1. B1 — the mixture is schedule-based; the Bridge predicate is strengthened

The rev2 predicate-partition is REPLACED by schedule-based
selection with quotas (257_s):

- **Direction** — the matched selected direction rows from Unit A's
  selector (renderer-balanced multiplicities, §4).
- **Anchor** — a FIXED, all-cell, renderer-crossed identity subset:
  the outcome-blind lowest-index latents per cell (draft: indices
  {0, 1} × 6 cells × 3 renderers = 36 rows' worth of schedule
  mass), declared by identity, not by predicate. Saturated
  `lookup_*` cells live here at reduced multiplicity and keep
  saturation/forgetting observable.
- **Bridge** — QUOTA-SELECTED C1-isolating rows from the remainder,
  under the STRONGER predicate: an observation qualifies iff its
  authenticated surface offers (a) an accessible reward-1.0
  family-correct route AND (b) a reward-0.5 neighbouring
  assignment, and — for Code-bearing C1 bridges, where available —
  tied w2/w3 variants (so the C1 gradient is not confounded with a
  direction preference). Because this too may be common, Bridge
  membership is by frozen per-(cell × renderer) quota with
  ascending-index selection from the qualifying pool, not by
  predicate alone.
- **Screened-but-unused** — every remaining screened observation is
  DISCLOSED in the Unit-B freeze with zero multiplicity; nothing is
  silently dropped.

The exact integer schedule (multiplicities per class × cell ×
direction × renderer, frozen shuffle seed) carries over from rev2
unchanged; only the partition rule changed.

## 2. B2 — Q3 is a within-cell gate; the disposition matrix covers Q2 failure

- **Common-cell Q3:** after Unit A's closeout, the eligible
  common-cell set is PREDECLARED (cells whose Unit-A yield includes
  BOTH directions at ≥2 latents each). Q3's gate must then pass —
  both directions' raw-count requirements (≥10 payoff-distinct
  co-sampling groups, ≥2 latents, ≥2 renderer strata, ≥25 marginal
  samples per specialist) — **within the same predeclared cell**.
  Cross-cell pooling (w2 in `code_atomic` + w3 in `math_code`)
  can no longer authorize the bidirectional claim; a one-direction
  pass is labelled a **direction-specific development result**,
  never "bidirectional within-cell specialist learning".
- **Complete disposition matrix (Q2 branch added):**

  | Q1 | Q2 | Q3 | P0 scope |
  |---|---|---|---|
  | pass | pass | both, common cell | Q1+Q2+Q3 (full) |
  | pass | pass | one direction | Q1+Q2 + direction-specific result |
  | pass | pass | none | Q1+Q2 (unlocking experiment) |
  | pass | fail | — | **Q1-only** (family-routing experiment) or stop-and-review if Q1 alone cannot justify P0's budget |
  | fail | — | — | stop-and-review (no P0 launch on a failed Q1 gate) |

## 3. B3 — the honest support-extension and comparator contract

Rev2 §3's partial-materialization wording is WITHDRAWN (the
materializer processes every declared observation; the high-level
runner reselects `c_fixed_dev` — both confirmed in code by 257_s).
The contract is now:

- **Declare and process the complete new 864-observation 0–47
  surface** as a self-contained extension launch; indices 0–5 are
  permitted to resolve as **cache hits** (the slw-keyed worker
  cache), so their cost is amortized, not re-executed.
- **Overlap equality gate:** the new surface's 0–5 payoffs and
  terminal outputs must equal the old locked surface's, verified
  observation-by-observation against the Step-4 lock
  (`61c4e85a…`) before the new lock is accepted.
- **Persist the complete new surface + provenance** under its own
  lock; the Step-4 lock and evidence remain untouched.
- **Comparator selection is NEVER invoked** on the extension: the
  runner path that reselects `c_fixed_dev` is out of contract for
  Unit A. A new telemetry boundary (implemented at the Unit-A
  freeze) verifies the ORIGINAL `c_fixed_dev` record against the
  ORIGINAL Step-4 lock, extracts frozen worker 2, and applies it to
  expanded-surface ScaleLift without reselection.
- **Correction to rev2 §3:** only **ScaleLift** consumes
  `c_fixed_dev`; C2 and ModelAcc are surface-defined and never
  touch the comparator.

## 4. Explicit gates recorded for the coming freezes (257_s list)

1. **Unit A freezes a TOTAL selector:** frozen bucket ordering;
   overlap handling when one latent qualifies for multiple buckets
   (first-satisfying-bucket in the frozen order consumes it);
   subset/tie resolution by ascending latent index then renderer
   order; and a verifier that REDERIVES the selected observation
   IDs byte-exactly from the locked extension surface.
2. **Unit B REQUIRES renderer-balanced direction multiplicities**
   (a constraint the freeze must satisfy or refuse — not merely a
   recorded count).
3. **Direction-yield disclosure by observable subtype/public
   factors**, plus a `cell + renderer + subtype` control in the
   analysis. If subtype perfectly predicts the winner, the honest
   headline is **task-subtype routing** — still orchestration, but
   not finer instance-level adaptivity — and the P0 claim language
   is chosen accordingly at the gate decision.
4. **Pre-Unit-C code-invalidation audit** (the charter's): if the
   scheduling changes touch rollout sampling or grouping in any
   way, Unit C is promoted to a COMPLETE fresh grouped reprobe and
   becomes the SOLE P0 exposure source (the Step-6 probe then
   informs nothing quantitative in P0's sizing).
5. **Step-8/P0 freezes incorporate the complete charter contracts
   by reference:** final `R_cycle` authorization, isolated
   evaluation RNG, full telemetry block, optimizer/seed/provenance
   fields, and the ten-hour admission calculation.

## 5. Feasibility (257_s figures adopted)

- New indices 6–47: 33,768 planned node executions ≈ **0.51
  GPU-h** by Step-4 scaling; full-prefix regeneration bound:
  38,592 ≈ **0.59 GPU-h** (cache hits should keep the real cost
  near the lower figure).
- Unit C at ~500 groups: ≈ **0.60 GPU-h**.
- The 1.0 GPU-h ceilings on Units A and C stand. Budget table
  otherwise as rev2 §7 (val materialization ceiling at its freeze;
  `R_cycle` from the 231_f basis; envelope after Step 7: 59.3539
  GPU-h remaining).

## 6. Unchanged

The three registered questions (Q1/Q2/Q3) and their draft gate
constants; the reviewed lifecycle order; the six-cell prefix-48
shape; frozen `c_fixed_dev` intent (now with the §3 mechanism);
per-observation direction qualification, quotas, and dispositions
(rev2 §3); exact integer schedule + frozen shuffle seed; G=8
default; natural equal-cell evaluation untouched; checkpoint-zero
first; trajectory reporting with latents as the independent unit;
the 254_f §1 erratum to 252_f.

## 7. Next

Narrow mechanical review of this rev3 (257_s closing) → Unit-A
implementation + freeze (total selector, extension contract §3,
telemetry boundary, exact cost derivation; lineage on head
`88c037a1…`) → run → Unit B freeze → code-invalidation audit →
Unit C freeze + run → disposition per §2 → val/cycle/`R_cycle` →
timing smoke → P0 freeze → checkpoint-zero eval → P0.
