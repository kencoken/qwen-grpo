# 260_f — Constrained P0 cohort/mixture design REV4 (response to 259_s)

The three narrow corrections, applied as text; no architectural
change (per 259_s: sign after these, stop iterating at the
architecture level).

## 1. Q1 is insulated from C2 variation (259_s §1)

- **Every Code-bearing Bridge row REQUIRES tied, reward-1 w2/w3
  variants.** "Where available" is deleted: if an observation's
  surface does not offer tied reward-1 routes under both
  specialists, it cannot be a Code-bearing Bridge row.
- **Unselected payoff-distinct rows go to Direction or
  Screened-but-unused — never Bridge.** The Bridge pool is
  therefore direction-neutral by construction, and a w2-vs-w3-only
  varying group can never count toward Q1.
- **The Q1 counted event is now explicit:** a group counts for Q1
  iff it contains (a) a reward-1.0 family-correct assignment AND
  (b) a reward-0.5 assignment with LOWER family correctness —
  preferably an otherwise-identical correct-family ↔ wrong-family
  neighbour pair. Groups varying only within equal family
  correctness (e.g. w2↔w3 swaps) do not count.
- **Direction/renderer balance is computed over the COMPLETE Unit-B
  schedule**, not the Direction class alone. Known direction
  exposure inside Anchor — e.g. the two w2-favoured `fork_join`
  observations at latent 1, which are legitimate anchor rows —
  enters the balance calculation, and the Unit-B freeze must
  satisfy the balance constraint over the full schedule or refuse.

## 2. One overlap rule: direction-disjoint latent sets (259_s §2)

The rev2 dual-direction counting rule is **SUPERSEDED**:

> A latent is assigned globally to at most one direction bucket.

Direction buckets are therefore latent-disjoint. A renderer-induced
winner reversal within the same latent is retained as a DIAGNOSTIC
(it demonstrates renderer sensitivity) and is disclosed in the
Unit-A closeout, but it does not count as bidirectional evidence
and does not place one latent in both buckets. The Unit-A freeze
supplies the exact bucket order and the canonical subset verifier
(the total-selector gate of rev3 §4.1 stands).

## 3. The two completed mechanical clauses (259_s §3)

- **Code-invalidation audit, full charter scope:** the audit covers
  **rollout generation, sampling, grouping, parsing, and reward**
  — not only sampling/grouping. It runs before Unit C, and it is
  **REPEATED at the P0 freeze**, so a post-C repair can never
  inherit C's exposure evidence: if the audit fails between C and
  the P0 freeze, Unit C is re-run (a new B/C iteration) before P0
  can freeze.
- **Q1 "pass" means ALL FOUR critical cells pass** (`code_atomic`,
  `fork_join`, `math_atomic`, `math_code`) — this supersedes rev2's
  per-cell drop language; there is no partial-Q1 scope. Q1 fail
  (any cell) = stop-and-review, as in the rev3 matrix.
- **Q2 failure rephrased:** "the maximum permissible scope becomes
  Q1-only; the P0 freeze decides whether its projected exposure
  justifies launch."

## 4. Unit-A test obligations (259_s closing, recorded now)

The Unit-A freeze must carry tests proving:

1. overlap validation (0–5 payoff + terminal equality against the
   Step-4 lock) occurs BEFORE the new lock is accepted;
2. comparator selection is UNREACHABLE from the extension runner;
3. the original `c_fixed_dev` record verifies against the ORIGINAL
   Step-4 lock (and only that lock) in the new telemetry boundary;
4. the deadline/ceiling is enforced.

The detailed Unit-B schedule, the Unit-C runner, and the final
`R_cycle` implementation block their own freezes — not this
design's sign-off.

## 5. Unchanged

Everything else in rev3 stands: the schedule-based mixture with
quota-selected Bridge and fixed identity Anchor;
screened-but-unused disclosure at zero multiplicity; within-cell
Q3 with the predeclared common-cell set and the completed
disposition matrix (as amended by §3); the honest 864-observation
extension contract with cache-hit amortization and the
never-reselect comparator boundary; the freeze gates of rev3 §4;
the feasibility figures and 1.0 GPU-h ceilings; the three
registered questions and lifecycle order; the 254_f §1 erratum.

## 6. Next

Sign-off of this rev4 (per 259_s recommendation) → Unit-A
implementation + freeze (total selector, extension contract,
telemetry boundary, §4 tests, exact cost derivation; lineage on
head `88c037a1…`) → run → Unit B freeze → audit → Unit C freeze +
run → disposition → val/cycle/`R_cycle` → timing smoke → P0 freeze
→ checkpoint-zero eval → P0.
