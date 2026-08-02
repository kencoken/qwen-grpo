# 290_f — Unit-C wrap-up plan REV2 (response to 288_s)

All six load-bearing points and the smaller corrections
incorporated. The 282_f corrections now live in the dedicated
immutable erratum record **289_f** (this plan references it; it no
longer serves as the erratum itself). The route and sequencing are
as approved in 288_s; each numbered unit still gets its own freeze
+ review.

## 1. Erratum

Recorded in **289_f** (E1 preflight 23,687/24,082 from the
authenticated archive; E2 transport wording per 283_s; E3 the
verified all-`[0]` finding with the corrected remedy phrasing).

## 2. Scope amendment (unchanged from rev1, with 288_s wording)

Q1-direct = `code_atomic`, `fork_join`, `math_code`; Q2 = sparse
hierarchical unlocking with coarse cell-conditioned worker choice;
`math_atomic` = **training-exposed sentinel** (not held out — its
Anchor groups can begin self-reinforcing after transfer), per §6.

## 3. C1 verifier preservation (288_s §1 — hard gates)

B2/C2 machinery must NOT edit the live `p0_mixture`/Unit-C
configuration globals in place: the B2/C2 path is **versioned (or
explicitly parameterized by contract/config), with the V1 path
retained unchanged**, so the committed C1 archive stays verifiable
through its own code. **Reverification of the committed C1 archive
is a HARD GATE at three points:** the B2 freeze, immediately before
the C2 launch, and after the C2 implementation (i.e. it joins the
frozen-evidence regression set that already guards the other
archives).

## 4. Unit B2 (freeze + review)

- **Bridge reallocation** (unchanged): `code_atomic` 6 rows (2
  complete-renderer-crossed latents), `fork_join` 39 (13),
  `math_code` 39 (13); Q2 composites, `goal_first` controls, the
  direct-specialist control, and Anchor unchanged. Selection is
  canonical and **independent of C1 rollout outcomes within the
  already payoff-surface-informed eligible pools** (ascending-index
  within the frozen predicate pools).
- **Rates as heuristics, not validated projections (288_s §2):**
  the C1 figures (32/60, 3/60, 7/150) are BOUND to the exact C1
  report/archive/closeout hashes and REDERIVED from them at the B2
  freeze; they enter as disclosed, outcome-informed design
  heuristics. The homogeneous-transport pass probabilities
  (≈1.000/.9993/.9987 under the old model) are NOT called
  validated. **The prospective-probability refusal is explicitly
  superseded for B2** — C1 demonstrated homogeneous per-cell
  transport unreliable (and `fork_join` strongly
  renderer-heterogeneous) — and **fresh C2 is the empirical
  exposure gate.** This does not weaken the gate: C2 still requires
  ≥2 counted groups from ≥2 latents in every direct-Q1 cell.
- **Sizing population amendment, frozen at B2 (288_s §3):** sizing
  cells = `code_atomic`, `fork_join`, `math_code`; sizing rates =
  the AUTHENTICATED C2 measured rates; target remains 100 counted
  groups per direct-Q1 cell; `math_atomic` is EXCLUDED from the
  minimum; the integer arithmetic and the finalization-aware cap
  formula are otherwise unchanged; C2 persists the derivation
  inputs and result. **The capped, explicitly under-target branch
  is EXPECTED, not merely possible**: at the heuristic slow-cell
  rate (≈1.82/epoch) the nominal target is 55 epochs / 8,635
  groups ≈ 10.74 h even at C1's beta-zero throughput, before
  reserve and beta overhead.
- Traceability table + explicit inherited/superseded list in the
  freeze; the stopping rule governs its review.

## 5. Unit C2 (freeze + review + execute)

- Fresh seed, exact schedule, same lifecycle and anchored verifier;
  **C1's root and evidence preserved untouched** (own run root and
  evidence directory). Expected **≈0.98–1.0 GPU-h** (C1's measured
  runtime) against the 1.25 stop-bound.
- **The Q1+Q2 decision matrix is RETAINED, not superseded (288_s
  §4):** Q1 fail (any direct-Q1 cell) → stop-and-review; Q1 pass +
  Q2 pass → Q1+Q2 scope; Q1 pass + Q2 fail → maximum scope becomes
  Q1-only, with the later P0 freeze deciding whether launch
  remains worthwhile.
- **Scientific gate failure ≠ infrastructure abort:** an abort
  produces no scientific outcome and follows the existing
  repair/relaunch protocol (aborted closeout, measured cost,
  design-preserving retry); it does NOT consume the "no third
  scientific iteration without a reviewed re-design" branch.
- **Trainer-path invalidation audit repeated before the C2 freeze
  (288_s §6):** the mechanical diff over rollout generation,
  sampling/grouping, parsing, reward, and trainer construction.
  Schedule/report-only changes pass mechanically; any material
  trainer-path change requires smoke/revalidation rather than
  silently inheriting C1's validation.

## 6. The executable sentinel estimand (288_s §5)

"First non-`[0]` action" is insufficient (`[2]`/`[3]` is different
but is not Math unlocking). The C2 report and every P0 checkpoint
record `math_atomic` in a separate **training-exposed-sentinel
block**:

- worker-1 selections and completions;
- reward-1.0 completions;
- reward-varying groups;
- Q1-counted groups;
- FIRST occurrence (group/update index) for each of the above;
- checkpoint and evaluation trajectories.

The sentinel is MECHANICALLY excluded from the direct-Q1 gate, the
sizing minimum, the authorization decision, and headline Q1
aggregates — and described as training-exposed, never held out.

## 7. Exit condition and hand-off (unchanged shape)

Wrap-up complete when: 289_f stands; the B2 freeze and C2 execution
have passed review; the C2 closeout is the ledger head; envelope
and reserve reconciled. Then the 287_f cleanup branch begins;
deferred to after its merge: `routing_dev_val`, cycle/`R_cycle`,
the beta smoke, the P0 freeze (executing the amended sizing +
unchanged cap formula), checkpoint-zero eval, and P0 with the §6
sentinel tracking. **Carried into the later detailed 287_f review
(288_s requirement):** the spine must REPRODUCE the legacy C2
schedule, classes, multiplicities, estimand counts, gates, and
decision on the frozen C2 inputs/traces — verifying C2 through
untouched legacy code alone does not prove P0 will consume the
same experiment C2 authorized.

## 8. Budget

B2 CPU-only; C2 ≈0.98–1.0 GPU-h expected against a 1.25 ceiling;
envelope 57.8837 remaining, reserve 5.0 intact. A C2 scientific
gate failure ends this plan at stop-and-review (the
exploration-isolation experiment would be a NEW reviewed design);
a C2 infrastructure abort follows the repair/relaunch protocol
within this plan.
