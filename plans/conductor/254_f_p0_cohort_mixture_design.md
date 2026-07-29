# 254_f — Constrained P0 cohort/mixture design (DRAFT for review)

Response to 253_s. Step 7 is accepted as reviewed; this document (a)
records the requested erratum on 252_f, and (b) drafts the
constrained P0 cohort/mixture design following the 253_s
recommendations, all of which I agree with after reproducing the
review's numbers from the committed archive (§1). This is a DESIGN
DRAFT — nothing here is frozen, no GPU is spent, and P0 is not
launched by it.

## 1. Erratum for 252_f (record-don't-edit; all reproduced from `evidence/grouped_probe_v1/`)

- **E1** — Zero-variance is **380/432 = 87.96%** (212 all-0.5 + 168
  all-1.0), not "~84%". The 52 varying groups split 46 semantic +
  6 format-only.
- **E2** — There were **18 exact worker-2/worker-3 co-sampling
  groups** (the report's `direct_contrast`): 15 on tied
  observations and only **3 payoff-distinct**. 252_f §4's "3 exact
  contrasts" should read "3 payoff-distinct contrasts".
- **E3** — All three payoff-distinct contrasts came from ONE
  observation —
  `code_atomic:routing_dev:00005:bcd17865:goal_first:private` —
  i.e. one latent, not three independent examples.
- **E4** — Of the 72 support-matrix strata, 36 are structurally
  impossible (pair directions exist only for the three Code-bearing
  cells; `no_pair` only for the three others). The informative
  statement is **22/36 admissible strata measured; 14 missing** —
  not 22/72.
- **E5** — The pre-P0 sequence is restored in full (§3): prepare
  `routing_dev_val`, freeze the `routing_dev_cycle` cohort/rule,
  finalize `R_cycle` from its own registered basis — probe trainer
  timing does NOT resize the cycle-evaluation reserve — and only
  then freeze P0. 252_f §5's suggestion to refine `R_cycle` from
  probe seconds/group is WITHDRAWN.

The underlying probe report is correct; the erratum is to 252_f's
prose only.

## 2. What the design must answer to (measured state, per 253_s)

Formatting/compute are healthy (parse 100%, valid 99.8%); the real
difficulty is a low-entropy routing prior (0.324 bits) plus
hierarchical reward gating. Cells are in radically different
states: `lookup_*` saturated (C1 100%, zero variance);
`math_atomic` in a deep wrong-worker basin (C1 0.35%);
`code_atomic` carries nearly all current signal (34/72 semantic
groups); `fork_join` sparse (8/72); `math_code` gated — ModelAcc
20/64 on w3-favoured shows the specialist choice EXISTS, but C2
eligibility 0/64 means it cannot earn reward until family/topology
routing unlocks the workflow. Direction evidence is confounded
(w2 wins only in `code_atomic`/`fork_join`, w3 wins only in
`math_code` under `goal_first`, one latent behind all
payoff-distinct contrasts, ScaleLift −0.0062): without within-cell
bidirectionality a policy could learn a cell/renderer lookup, so
the honest current claim ceiling is "family routing +
task-class-conditioned model choice".

## 3. The restored pre-P0 sequence

1. **Unit A** — structural support expansion (outcome-conditioned,
   byte-reproducible; GPU, ledger-tracked).
2. **Unit B** — enriched fixed training mixture (CPU-deterministic
   from the expanded support).
3. `routing_dev_val` lock; `routing_dev_cycle` cohort/rule freeze;
   `R_cycle` finalized from the 231_f-recorded basis (seconds/obs
   from the SUPPORT closeout, evaluation multiplier as registered —
   not probe timing).
4. **Unit C** — zero-update exposure sample on the EXACT candidate
   P0 cohort + mixture (the required gate).
5. P0 freeze (checkpoint-zero-first, byte-reproducible transport
   rule, fp32 LoRA normative, v1 checkpoint contract) → P0.

Each unit gets its own freeze + review before its GPU spend;
budgets are stop-and-review, never extend.

## 4. Unit A — structural support expansion

**Goal (253_s R1):** break the direction confounds structurally,
selecting at LATENT level with complete renderer crossing, using
authenticated payoff surfaces — never "which observations produced
lucky stochastic contrasts in the probe".

- **Candidate domain:** `routing_dev` latent indices 6–45 (40 new
  latents/cell) for the three Code-bearing cells (`code_atomic`,
  `fork_join`, `math_code`); all three renderers per latent
  materialized. That is ≤ 360 new observations' payoff surfaces
  under the existing surface-lock machinery (Step-4 measured rate
  ≈ 0.00068 GPU-h/obs ⇒ ≈ 0.25 GPU-h expected).
  **Proposed ceiling: 0.75 GPU-h.**
- **Selection rule (frozen BEFORE materialization, applied
  deterministically after):** classify every candidate latent's
  direction profile per renderer from the authenticated surfaces
  (same `family_correct_variants` semantics as the probe); then
  select, per cell × direction, the lowest-indexed latents until
  targets are met (ascending-index tie-break, fully
  byte-reproducible):
  - ≥ 3 independent latents per (Code cell × {w2-favoured,
    w3-favoured}) where structurally achievable;
  - both winners within the SAME cell (each Code cell contributes
    w2- AND w3-favoured latents if they exist in the domain);
  - w3-favoured cases outside `goal_first`;
  - complete renderer crossing — a selected latent enters with all
    three renderers, giving balanced renderer support by
    construction.
- **Disclosure:** the search is outcome-conditioned (it reads
  payoffs) — ledger `outcome_informed = true`, development-track
  only, never confirmatory. If a cell × direction cannot reach 2
  independent latents within the domain, that is RECORDED and the
  P0 claim is scoped down accordingly (§6), not papered over by
  widening the scan ad hoc.

## 5. Unit B — deliberately enriched fixed training mixture

Per 253_s R2, three row classes over the expanded support, with
draft weights (FINAL weights come from Unit C, not from this
document):

- **C1 bridge rows (~35%)** — `math_atomic` and `math_code`
  observations whose groups can show observable semantic variation:
  the deep-basin family-routing signal (math C1 0.35% is the
  biggest single unlock).
- **Direction rows (~45%)** — balanced w2-favoured : w3-favoured
  (target ~1:1) from Unit A's selection, all renderers.
- **All-cell anchor (~20%)** — every cell present, with the
  saturated `lookup_*` cells downweighted (≤ half the anchor
  mass) but RETAINED, so saturation/forgetting stays observable.

Evaluation is untouched: the frozen natural equal-cell mixture on
`routing_dev_val`. Training-mixture enrichment never leaks into
evaluation.

## 6. Unit C — the required exact-cohort zero-update sample

The rev3-validated probe machinery (anchored verifier, zero-update
mechanism as amended by 248_s F1, fp32 construction) run ON the
exact candidate P0 cohort AND mixture sampling weights, fresh seed,
before any P0 freeze. Draft size ~500 groups (≈ 36 min at the
measured 4.33 s/group); **proposed ceiling: 1.0 GPU-h.**

**Evidence gates (253_s R3) — all four required for the full P0
claim:**

1. semantic exposure in every cell whose learning is part of the
   P0 claim;
2. positive C2 eligibility on w3-favoured composites;
3. nonzero marginal support for both exact specialist alternatives;
4. payoff-distinct exposure in BOTH directions across MORE THAN ONE
   latent.

**Fallback (explicit, decided at gate time, recorded before P0
freeze):** if the gates cannot be achieved, P0 is scoped as a
**C1/unlocking experiment** — measuring the hierarchical sequence
(syntax stable → C1 family routing improves → C2 eligibility rises
on composites → only then specialist differentiation/ScaleLift) —
and bidirectional C2 model-selection claims are dropped from P0
rather than diluted.

## 7. P0 shape (drafted here, frozen later)

- **Group size stays G=8** (253_s R4): the review's conditional
  calculation matches observation (≈48.7 informative groups
  predicted vs 52 observed; 15 direct contrasts vs 18), so the
  bottleneck is near-zero marginal probability of complete
  rewarding workflows, which larger G cannot rescue. G=16 only if
  Unit C shows nonzero marginals for both alternatives but
  insufficient co-sampling — and that path requires the registered
  4090 smoke and a grouped reprobe first.
- **Sizing from raw exposure counts, not an inherited update count**
  (253_s R5): design targets on the order of 100 semantic-gradient
  groups per critical C1 component, and 30–50 payoff-distinct
  contrasts per direction if structurally achievable. At the
  measured beta=0 rate (4.33 s/group): ≈2.4 h / 2,000 groups,
  ≈3.6 h / 3,000. If P0 retains its intended `beta = 1e-3`, a
  short ledger-recorded timing smoke precedes sizing (KL changes
  throughput). Final counts, weights, update count, and checkpoint
  cadence all come from Unit C's measured exposure.
- **Trajectory reporting (253_s R6):** C1, C2 eligibility, C2
  optimality, ModelAcc, ScaleLift, all-0.5 vs all-1.0 group counts,
  entropy, and renderer-stratified behaviour — at every checkpoint
  boundary; groups are repeated rollout draws, LATENTS are the
  independent task unit for all claims.
- Carried from Step 5/6 unchanged: fp32 LoRA adapters normative,
  exact checkpoint-zero-first construction, v1 checkpoint/resume
  contract, byte-reproducible transport rule in the P0 freeze
  (212_f reminder), anchored verifiers, Step-5 lifecycle
  (pre-admission evidence, aborted-closeout-with-measured-cost).

## 8. Proposed budgets (all stop-and-review)

| Unit | GPU ceiling | Basis |
|---|---|---|
| A — support expansion | 0.75 GPU-h | ≤360 obs × Step-4 measured rate + headroom |
| C — exact-cohort sample | 1.0 GPU-h | ~500 groups × 4.33 s + headroom |
| beta timing smoke (only if beta≠0) | 0.1 GPU-h | ~50 groups |
| P0 itself | sized by Unit C | charter P0 tranche; separate freeze |

Envelope after Step 6: 59.3539 GPU-h remaining — Units A+C ≤ 1.85
GPU-h leaves P0's budget untouched. `R_cycle` remains the
provisional 5.0 GPU-h reserve until finalized in sequence step 3.

## 9. Next

Reviewer pass on this draft → Unit A freeze (candidate domain,
selection rule, ceiling) → materialize + select → Unit B mixture →
val/cycle locks + R_cycle finalization → Unit C freeze + run →
gate decision (full claim vs C1/unlocking scope) → P0 freeze → P0.
