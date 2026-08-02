# 286_f — Unit-C wrap-up plan (for review): the route to a clean pre-P0 state

The plan for the remaining steps after the 283_s acceptance of Unit
C's STOP-AND-REVIEW, up to the point where the pre-P0 cleanup
(287_f) can begin on its own branch. Nothing here is a freeze;
each numbered unit below gets its own freeze + review in sequence.
This document iterates with the reviewer until approved.

## 1. 282_f erratum (record-forward; both corrections verified against the archive)

- **E1 — preflight figures.** 282_f §1 stated "preflight 24,079
  MiB". The authenticated archive records **23,687 MiB free /
  24,082 MiB total** (the 24,079 figure was the pre-launch
  `nvidia-smi` check, not the admitted preflight). Verified from
  `evidence/unit_c_v1/session_preflight.json`.
- **E2 — transport wording softened** to the 283_s formulation:
  282_f §3's "the transport assumption itself failed" overstates —
  the original evidence was two singleton successes which also
  failed to reproduce in Unit C. The defensible conclusion is:
  *"the homogeneous per-cell transport projection did not
  reproduce; the atomic-Math tail is too rare, heterogeneous or
  seed-unstable to support the frozen exposure guarantee."* The
  1.5% figure remains a plug-in diagnostic, not a calibrated
  p-value.
- **Recorded, and verified**: the 283_s strengthening of the
  finding — **all 1,320 `math_atomic` completions (165 groups:
  150 Bridge + 15 Anchor) selected exactly `[0]`**; the only
  distinct action observed. There is effectively no ckpt-0
  exploration of worker 1 on atomic Math under this prompt and
  sampling configuration; added multiplicity would buy identical
  zero-gradient groups.

## 2. Scope amendment (283_s recommended route, adopted)

- **Direct Q1 authorization: `code_atomic`, `fork_join`,
  `math_code`** (the three cells with measured nonzero counted
  rates).
- **Q2 unchanged in structure, honestly framed**: a SPARSE
  hierarchical-unlocking experiment with coarse cell-conditioned
  worker choice — not an already-demonstrated specialist-learning
  signal (each direction produced only two reward-bearing contrast
  groups; fork_join's Q1 positives were all `goal_first`; the w3
  signal stays renderer-confounded).
- **`math_atomic` becomes a delayed-unlocking / dead-basin
  SENTINEL**, not a direct-exposure requirement: its Anchor
  presence is retained so P0 can observe whether Math-node learning
  through `math_code` eventually causes atomic Math to begin
  varying and self-reinforcing. Explicitly NOT a pure held-out
  transfer test (the sentinel rows remain in the training
  schedule).

## 3. Unit B2 (one outcome-informed iteration — freeze + review)

- **Bridge reallocation of the 84 rows** away from the dead
  `math_atomic` block (283_s starting point): `code_atomic` 6 rows
  (2 complete-renderer-crossed latents), `fork_join` 39 rows (13
  latents), `math_code` 39 rows (13 latents). The locked support
  fills these quotas; selection stays canonical and
  OUTCOME-INDEPENDENT within the eligible pools (ascending-index
  within the frozen predicate pools — never the rows that happened
  to succeed in C1). Q2 composites, goal_first controls, the
  direct-specialist control, and Anchor are UNCHANGED.
- **Projection basis**: the C1-measured per-draw counted rates
  (ca 32/60, fj 3/60, mc 7/150) — an OUTCOME-INFORMED basis,
  disclosed as such (this is the sanctioned B2/C2 iteration; new
  identities throughout). Projected ≈3.2 / 2.0 / 1.8 counted
  groups per epoch, bringing the 100-group sizing target near the
  ten-hour P0 envelope (vs the ~33-hour C1 derivation).
- **Gates retained**: the frozen per-cell Q1 criterion (≥2 counted
  from ≥2 latents; prospective pass ≥0.9 at the recommended C2
  size) applied to the three Q1-direct cells; the per-direction Q2
  cold-start gate unchanged. `math_atomic` carries NO Q1 gate (it
  is a sentinel).
- **Process (284_s, adopted)**: the B2 freeze includes a
  traceability table (requirement → config field → enforcement →
  regression → artifact field), an explicit inherited/superseded
  list, and the stopping rule applies to its review.

## 4. Unit C2 (one fresh run — freeze + review + execute)

- Fresh seed, exact schedule, the same lifecycle and anchored
  verifier; **C1's root and evidence are preserved untouched**
  (never retried or overwritten; C2 gets its own run root and
  evidence directory).
- Same ceiling discipline (1.25 GPU-h stop-bound; expected ≈0.94).
- The preregistered decision rule as amended: Q1 gate over the
  three Q1-direct cells; per-direction Q2 gate; pass → the wrap-up
  is complete; fail → stop-and-review again (no third iteration
  without a reviewed re-design).

## 5. Definition of "good pre-P0 stage" (the exit condition)

Wrap-up is complete when: the erratum is recorded; the B2 freeze
and C2 execution have passed review; the C2 closeout is the ledger
head; and the envelope/reserve are reconciled. At that point the
cleanup (287_f) begins on its own branch. Deliberately DEFERRED to
after the cleanup merge (so they freeze against the contract
spine): `routing_dev_val` lock, cycle-holdout/`R_cycle`
finalization, the beta timing smoke, the P0 freeze (which executes
the frozen sizing + cap formula), checkpoint-zero eval, and P0
itself — with the P0 tracking obligations from 283_s (first
non-`[0]` atomic-Math action, first varying atomic-Math group, its
evaluation trajectory alongside C1/C2 unlocking).

## 6. Budget

B2 is CPU-only. C2 ≈1.0 GPU-h measured expectation against a 1.25
ceiling. Envelope after C1: 57.8837 remaining, reserve 5.0 intact —
admissible with ample margin. If C2 fails its gates, the fallback
exploration-isolation experiment (legal-action likelihoods +
bounded temperature probe, 283_s) would be a NEW reviewed design,
not part of this plan.

## 7. Sequence summary

1. This plan reviewed → approved.
2. Erratum recorded (this document, §1, stands as the record).
3. Unit B2 freeze → review → (repair ×1 if needed) → sign-off.
4. Unit C2 freeze → review → launch OK → GPU run → closeout +
   report review → pass.
5. → 287_f cleanup branch; merge; then the deferred pre-P0 units
   (§5) on the contract spine; then P0.
