# 270_f — Unit B: the P0 mixture, implemented + FROZEN (for review)

The 269_s-scoped Unit B, implemented as `tasks/routing/p0_mixture.py`
and frozen here. CPU-only (no GPU, no ledger launch); the frozen
schedule and its prospective projections are what the Unit-C freeze
preregisters against (269_s §7, option 1). Full CPU suite: **997
passed under `-W error`, TRUE exit 0**. Built and verified on the
COMMITTED extension evidence via the production restore path
(clean-clone valid).

## 1. Scope and wording (269_s §3 corrections adopted)

Objectives frozen as **Q1 family routing + Q2 hierarchical
unlocking and coarse, cell-correlated downstream model choice**.
Formal Q3 and renderer-independent expertise routing are OUT OF
SCOPE. Downstream documents now use the corrected language: formal
Q3 is unavailable; `fork_join→w2` is a one-sided descriptive
diagnostic (no positive specialist ScaleLift is available against
the frozen worker-2 comparator); and the w3 statement is "zero
assigned/eligible non-`goal_first` worker-3 coverage" (fork_join
latent 42's reversal stays diagnostic and is screened at
multiplicity zero — never reused to manufacture balance).

## 2. The ONE fixed per-epoch schedule (139 rows)

Deterministic class assignment under frozen precedence
(q2_composite → anchor → goal_first_control → bridge), exact
integer multiplicities, frozen shuffle seed 20260731:

| Class | Rows | Content |
|---|---:|---|
| **Q2 composite** (supersedes Direction) | 37 | `math_code→w3`: all 7 owned obs × mult 2 = 14; `code_atomic→w3`: all 5 × 1; `fork_join→w2`: 18 rows (all 4 bound_var + 14 goal_first, frozen renderer-then-index order) |
| **goal_first controls** | 18 | 6 tied goal_first rows per Code cell, ascending — so `goal_first` does not imply worker 3 |
| **Bridge (Q1)** | 66 | complete-renderer-crossed latents under the 260_f predicate: math_atomic 10 latents (the basin IS Q2's step-1 prerequisite), code_atomic/fork_join/math_code 4 each; payoff-distinct rows never Bridge; lookups ZERO Bridge quota |
| **Anchor** | 18 | the fixed identity subset: latent 0 × 6 cells × 3 renderers (lookups live here) |

732 observations are screened at zero multiplicity (disclosed
count in the record). One schedule for all of P0 — changing the
mixture after C1 improves would confound unlocking with exposure
(269_s §6 item 8), so no mid-training reweighting exists in the
design.

## 3. Q2-aligned constraints (the EXPLICIT gate supersession)

The Q3-designed complete-schedule direction-by-renderer balance
requirement is formally SUPERSEDED (269_s §6: replaced, not
silently relaxed) by machine-enforced refusals:

- per-direction Q2 rows ≥ 12; realized **w2 18 : w3 19** (ratio
  1.06 ≤ frozen 1.5) — mixture imbalance cannot reward a
  constant-worker policy;
- **P(w3-favoured | goal_first row) = 0.229 ≤ 0.5** across the
  whole schedule (the matched controls do their job; the actual w3
  advantage remains disclosed as renderer-confounded);
- latent 42 in the schedule → refuse; lookup Bridge quota → refuse;
  under-quota Bridge cells → refuse.

## 4. Prospective projections (the Unit-C preregistration basis)

From the committed Step-6 probe's ckpt-0 per-cell rates (file
sha-bound; transport from the original support to extension rows is
a DISCLOSED assumption):

| Cell | Bridge rows/epoch | P(semantic-varying) ckpt-0 | E[Q1-counted]/epoch |
|---|---:|---:|---:|
| code_atomic | 12 | 0.472 | 5.67 |
| fork_join | 12 | 0.111 | 1.33 |
| math_atomic | 30 | 0.028 | 0.83 |
| math_code | 12 | 0.028 | 0.33 |

Expected zero-variance fraction ≈ 0.846. Q2 exposure: 18 w2 / 19 w3
rows per epoch; ckpt-0 C2 eligibility on w3-favoured composites is
0/64 — the recorded Q2 STARTING CONDITION, never direct-C2
exposure.

**The tension this exposes, stated plainly:** at ckpt-0 rates a
~500-group Unit-C sample (~3.6 epochs) projects only ≈3.0
math_atomic and ≈1.2 math_code Q1-counted groups — the draft
"≥15 per cell" constant from 256_f is unreachable there and was
calibrated before these measurements. Per 269_s §7 (option 1), the
Unit-C freeze must set its gate constants AGAINST these
preregistered projections (e.g. exact-binomial consistency bands
around the projection plus latent/renderer-representation
requirements), not against the stale draft constant. That choice
belongs to the separately reviewed Unit-C freeze; the projections
here are its fixed, preregistered input.

## 5. Machinery + verification

`build_mixture(loaded, selection)` refuses unless the surface is
under the frozen extension lock `ccb1c3e2…` and the selection is
the frozen Unit-A record (file bytes sha-bound, record rehashes,
lock-bound); the Bridge predicate is the 260_f rev4 wording (tied
reward-1 w2/w3 variants REQUIRED for Code-bearing rows);
`verify_mixture` rehashes and rederives the record byte-exactly.
Tests build on the committed evidence via the production restore
path and cover: the exact 139-row schedule and class masses, the
constraint values, latent-42 screening, lookup/anchor/bridge class
laws, schedule-multiset integrity, the Q1-tension projection,
tampered-schedule and tampered-selection refusals, and a violated
Q2-minimum refusal.

## 6. Frozen identities

- Config:
  `05a1a41e2b3f72362636af7183ad03f501f011bf39dd46db21fbf016fb847559`
- Freeze:
  `17be032003cfeec5aad009df3b530599b117d90731aa58f6b31c5f7cefd763b2`
- Mixture record (deterministic from locked surface + frozen
  selection):
  `6d8fecbecd6fdd8b371fd5b7ad630fd77b17dad35077a10ec2b9c0b4d1224c59`
- Extension surface lock (input): `ccb1c3e2…` (unchanged)
- Selection record (input): `c6c08775…` / file `e0bbb75d…`
- Projection basis (input): probe report file `3a001c99…`
- Lineage parent: `b88eba02…` (the Unit-A closeout head)

## 7. Next

Reviewer pass on this freeze → pre-Unit-C code-invalidation audit
(full charter scope: rollout generation, sampling, grouping,
parsing, reward) → Unit-C freeze (gate constants preregistered
against §4's projections; validates THIS exact schedule, record
`6d8fecbe…`) → Unit-C run → preregistered scope/duration decision →
val/cycle/`R_cycle` → beta timing smoke → P0 freeze → checkpoint-
zero eval → P0.
