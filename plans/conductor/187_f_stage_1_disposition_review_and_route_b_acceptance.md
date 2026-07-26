# 187_f — Review of 186_s, ledger verification, and Route B acceptance

Review of the reviewer's Stage-1 attempt-1 disposition and
routing-training development pivot (186_s @680b3a3). Verdict:
**accept, with five tightening items** for the follow-on plans (§4).
Ken has reviewed 186_s and this assessment and **chooses Route B**:
the attempt/global disposition is ACCEPTED and original-plan
attempt 2 is DECLINED (186_s §9 items 1–2, recorded here,
2026-07-26). Per 186_s §8 this choice is recorded BEFORE any B
diagnostic or development run exposes outcomes on the retained
support.

## 1. Ledger verification (186_s §3 — independently re-derived)

Read-only re-derivation from the immutable abort archive
`stage1_pre_ce1_amend1_9b5f1ab85f26` (manifest `114cf207…`) using
the frozen evaluators (`wilson_lower`/`wilson_upper`,
`coverage_alpha_ceiling`, `hard_path_acceptance`,
`d8_branch_support_ok`). Script disclosed below; verbatim output:

```
A: 12 gated cells, all LB >= 0.80: True, worst 0.98996 (A|fork_div3|0.15|0.5|10000)
C: hard-path passes: True | failures: []
D artifact content self-hash: 3afcd6727baebb5270c10eb92e579ca17e5af3a482085f13c8149163594f9683
D artifact file-byte sha256 : f0bd25c265ab3edc0661835fbd05e83e964ee638b07f13f2cc53e6e89c25b056
  D1_seq_null_ordinary_div3: 12/5000 UB=0.0038 ceiling=0.02167 -> INSIDE
  D2_seq_null_fork_div3: 15/5000 UB=0.0046 ceiling=0.02167 -> INSIDE
  D3_equiv_boundary_plus: 81/5000 UB=0.0194 ceiling=0.03125 -> INSIDE
  D4_equiv_boundary_minus: 101/5000 UB=0.0237 ceiling=0.03125 -> INSIDE
  D5_pilot_hetero_unequal: 157/5000 UB=0.0357 ceiling=0.03125 -> EXCEEDS
  D6_persist_const_theta10: 208/5000 UB=0.0465 ceiling=0.06250 -> INSIDE
  D7_persist_rowdispersed_theta10: 199/5000 UB=0.0446 ceiling=0.06250 -> INSIDE
  D8_persist_hybrid_theta01_fork: 0/5000 UB=0.0005 ceiling=0.06250 -> INSIDE
D8 branch support ok: True
P[K>=157 | n=5000, p=0.025] = 0.002879
```

Every 186_s §2/§3 number checks out, including the worst gated A
lower bound (0.98996), the binomial tail (0.0029), and the D
artifact hash — which is the artifact's CONTENT self-hash; the
archive manifest separately records the file-byte hash
(`f0bd25c2…`). Both identities are now pinned above.

Re-derivation recipe (complete):

```python
from scipy.stats import binom
from tasks.conductor import stage1_persistence as sp
from tasks.conductor import stage1_tranche as st
from tasks.conductor import stage1_validation as sv
root = ("plans/conductor/evidence/"
        "stage1_pre_ce1_amend1_9b5f1ab85f26/validation/")
# A: wilson_lower over the 12 gated cells (delta 0.15 / effect 0.10,
# sigma <= 0.50); C: sp.hard_path_acceptance(artifact["results"]);
# D: sv.wilson_upper vs sv.coverage_alpha_ceiling per st.D_SCENARIOS
# allocated alphas; branch support: st.d8_branch_support_ok;
# tail: binom.sf(156, 5000, 0.025).
```

## 2. Assessment of the disposition (186_s §§1–3)

Agreed in full:

- Separating the PHYSICAL abort (B unmeasured; no aggregate exists
  by construction) from the DESIGN failure (D5 exceeded its frozen
  ceiling; unit 3 stopped; amend-once consumed; no global C1/C2
  authorization) is the correct reading — cleaner than either
  fabricating an aggregate or treating D5 as unsettled pending B.
- The component ledger is the right vehicle: the apparatus produced
  real, scoped design evidence (A power validated with enormous
  margin; the amended persistence statistic calibrated in all three
  registered scenarios, including the row-dispersed case the v1
  envelope failed structurally; D8 branch support landing at
  2,782/257 against registered ≈2,700/≈245), and D5's failure is
  retained as evidence, localized to the small-sample heterogeneous
  unequal-cell percentile-bootstrap geometry.
- The D5 epistemics are calibrated correctly: the screen failed
  (`P[K≥157] ≈ 0.0029` under exact nominality); the method is not
  thereby shown catastrophically invalid (point estimate 3.14%,
  ~0.6pp above nominal). §6's guard — no replacement method may be
  selected because it reverses D5 — closes the garden path.

## 3. Route choice (186_s §8) — and a recorded change of position

185_f §4 recommended formal attempt 2 ("the wind-tunnel's product is
the calibration record"). **That recommendation is superseded**: the
186_s §8 counter-argument is correct. The CPU streams are
deterministic under registered seeds, so attempt 2 reproduces the D5
exceedance bit-for-bit; B cannot rescue a conjunctive failure; and
B's actual measurement arrives under Route B anyway, better scoped.
Route A would buy a formal aggregate whose decision is already
known, plus one real end-to-end exercise of the
finalize/success-archive machinery — which is test-covered
(`verify_finalized_run` and both archive modes have named tests) and
not worth a lock cycle by itself. The critical process constraint —
the fork is chosen BEFORE any diagnostic exposure forecloses clean
recovery — is honored by recording Route B now.

**Decision recorded: Route B. Original-plan attempt 2 declined. The
attempt-1 roots and archive remain immutable and are never resumed,
reused, or combined into the missing aggregate.**

## 4. Tightening items for the follow-on plans (accepted direction; scope guards)

1. **Ledger reproducibility — CLOSED HERE**: §1 above is the
   committed re-derivation record 186_s §3 referenced.
2. **Hash labeling — CLOSED HERE**: content self-hash vs file-byte
   hash both pinned in §1.
3. **Prompt-iteration scope (186_s §5)**: the development track may
   iterate CONDUCTOR prompts freely (logged); worker_dev
   prompt-editing remains CLOSED (103_s) — any worker-prompt work
   requires fresh worker instances. The launch plan must state this
   boundary explicitly.
4. **Namespace protections (186_s §5)**: the development-only
   namespace must not consume registered-but-unused populations —
   specifically policy_dev cohort B (24–47, registered never-reassign
   per 135_f) and the formal construction prefix. The launch plan
   names its cohorts and asserts disjointness.
5. **Smoke budget (186_s §4)**: the reward-blind GPU smoke carries
   an explicit completion budget in the repair plan (bounded-probe
   discipline), not "tiny".

## 5. Next actions (186_s §9, as now sequenced)

1. ✔ Route B chosen; disposition accepted; attempt 2 declined (this
   record).
2. Draft the narrow B repair-and-diagnostic plan (fix +
   real-`BatchEncoding` regression + budgeted reward-blind smoke +
   separately identified diagnostic root/tag/seed domain + the
   affirmative feasibility criterion if claim-bearing).
3. Draft the routing-training development-track launch plan (fixed
   initial budget, development namespace with §4 protections,
   traces, descriptive continuation rules; conductor-prompt-only
   iteration).
4. Use development observations to decide whether a claim-bearing
   confirmatory design is warranted; any such design uses fresh
   seeds and disjoint populations, excluding every development run.
