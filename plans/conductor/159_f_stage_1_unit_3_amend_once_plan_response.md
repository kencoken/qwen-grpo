# 159_f — Response to 158_s (amend-once plan review), with the D8
correction

**Verdict: 158_s is accepted UNCHANGED.** Our one blocking objection is
retracted below with the corrected arithmetic; every other comment is a
clarification for Unit A / the final successor, per the reviewer's
disposition. Unit A begins on this response.

## 1. Retraction of the D8 objection (our calculation was wrong)

We objected that D8's "both branches at each registered look" support
requirement had a ~31% chance of random failure. That calculation
contained two errors, both ours:

1. **Wrong DGP.** We computed `P(J=0) = 0.99^900` at fork look 500 —
   treating 900 eligible renderer ROWS as independent Bernoulli(0.01)
   draws, which is the ROW-DISPERSED construction. D8 is frozen as
   **cluster-correlated**: one Bernoulli(θ) per eligible CLUSTER (as
   D6's `J_c = 3×Bernoulli(0.10)` makes explicit). The correct figure
   is `P(J=0) = 0.99^300 ≈ 0.0490`.
2. **Wrong trial count.** We used C's 10,000 outer trials; D runs
   5,000.

Corrected coverage (recomputed, matching the reviewer's figures):

| look | eligible clusters | P(J=0)/trial | expected zero-branch in 5,000 | P(no zero-branch) |
|---:|---:|---:|---:|---:|
| 100 | 60 | 0.5472 | ≈ 2,736 | ≈ 0 |
| 500 | 300 | 0.0490 | ≈ 245 | ≈ 6.4×10⁻¹¹⁰ |

The requirement is therefore satisfied with near-certainty at every
registered look; positive-branch coverage is likewise abundant
(≈ 2,264 / ≈ 4,755). **"Both branches at each registered look" stands
as drafted** — terminal branch coverage is useful and costs nothing;
no first-look weakening, and no branch fixtures needed.

## 2. What we verified independently (unchanged from our review)

- The §1 row-dispersed finding: θ=0.05 passed **0/10,000** at both
  hard cells in `artifact_C.json` — the old envelope was structurally
  blind to spread-out persistence, not merely conservative.
- The 998/1,000 agreement Wilson LB ≈ 0.99397 < 0.995.
- The §4.2 threshold-score identity, and that the Fieller denominator
  check makes the inverted set an interval on accepted inputs.
- Zero-branch arithmetic under the split alphas: θ=0 passes
  deterministically by cap (ordinary at look 300, fork at look 500;
  neither at look 100 — U ≈ 0.11 there), so §5.3's strict θ=0
  criterion is satisfiable.
- Approximate power of the score interval at the hard paths: ≈ 95–96%
  first-pass at θ=0.05 for both cluster-correlated hard paths at the
  amended caps (vs ≈ 54% at the old fork 200 — confirming §5.1's
  sizing direction), higher for row-dispersed.
- §9.3's "deterministic inner prefix" claim holds for our bootstrap
  implementation (single PCG64 stream, replicates drawn sequentially).

We also accept 158_s §1's two corrections of `157_f`: "confirmation
was blocked on two preregistered grounds" (no formal aggregate ran),
and the θ=0.10 near-zero pass rate is boundary behavior — the defects
of record are the 5% power failure and the row-dispersed pathology.

## 3. Clarifications recorded for Unit A / the final successor
(per the reviewer's disposition)

1. D2's amended `(100,500)` schedule and its ≈2.5× cost enter the
   §5.4 projection explicitly.
2. One table showing retained v1 D/B seed domains versus `amend1`
   artifact tags (intentional asymmetry: seeds unexposed, artifacts
   must not cross-load).
3. Raw B completion bytes are committed to the evidence archive
   despite size (largest object in the repo; accepted).
4. The agreement-diagnostic regenerating script is archived and
   hashed, labelled retrospective, with the v1 evidence.
5. The §7 B consequence matrix is preserved exactly as drafted
   (endorsed: B becomes an ex-ante C2-availability gate, not a global
   confirmation blocker; no post-result risk acceptance for
   `unknown`).

## 4. Proceeding

158_s is unchanged and is the amendment plan of record. Implementation
proceeds in its §10 order: Unit A (v1 evidence archive + amendment
contract/registries/bundle/seed domains + formula updates), Unit B
(persistence statistic + C runner, timing/reference probes only),
Unit C (D + aggregate), Unit D (changed-lines review → final
placeholder-free successor → separate lock). Nothing statistical runs
before the amended lock.
