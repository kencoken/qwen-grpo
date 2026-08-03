# 299_f — Unit C2 EXECUTED: all gates PASS; the frozen decision is Q1 + Q2 AUTHORIZED

The approved rev2 ran 2026-08-03: **every direct-Q1 cell passed the
empirical exposure gate, both Q2 cold-start directions passed on
their intended targets, the sizing derivation is live, and the
frozen four-branch matrix emits "Q1 + Q2 hierarchical-unlocking
authorized."** The 290_f wrap-up exit condition is met; the next
step is the 287_f contract-spine branch.

## 1. The run (all ledger-recorded)

- Launch `29690789…` against head `9f4661a8…` (= the frozen lineage
  parent); freeze `ae51bc57…`, identity `7b19aeb9…`, attested
  environment `372f958f…` all matched; `verify_c1_basis` ran FRESH
  pre-admission (and again post-C2 — the 294_s chain semantics hold
  with the new entries appended, completing the hard-gate triple).
- 785 groups / 6,280 completions, 60.9 min wall, **1.0142 GPU-h**
  (over the 0.98–1.0 point expectation; the 1.25 stop-bound margin
  was used exactly as intended). Zero-effective-update PROVEN over
  the two persisted 504-key maps; counters 785/785/785/6280;
  schedule exact. Complete closeout `2bf50c1e…` = the new LEDGER
  HEAD (17 entries verify). **Envelope: 3.1305 consumed / 56.8695
  remaining; reserve 5.0 intact.**
- `verify_unit_c2_run` rederives PASS in-run, post-hoc, and from
  the committed evidence copy alone
  (`plans/conductor/evidence/unit_c2_v1/`, 684 KB complete archive
  incl. the full 785-row trace). C1's archive and evidence remain
  untouched and still verify.

## 2. The measured gates

**Q1 (per direct-Q1 cell, ≥2 counted from ≥2 latents): ALL PASS —
60 counted groups total (C1: 42, with a dead cell).**

| Cell | Counted / draws | Latents | Renderers | vs B2 heuristic |
|---|---:|---|---|---|
| code_atomic | 13 / 30 | 8, 10 | all three | 16.0 proj. |
| fork_join | 34 / 195 | 24, 41, 43, 44, 46 | all three | 9.75 proj. |
| math_code | 13 / 195 | 7 latents | all three | 9.1 proj. |

The reallocation did its job: `fork_join` rose from 3 counted (C1)
to 34 across five latents; `math_code` from 7 to 13 across seven.
The disclosed heuristics were again only heuristics — under on
`code_atomic`, over on `fork_join` — which is exactly why they were
never validated projections.

**Q2 cold-start (per direction, intended target): PASS with
margin** — `fork_join→w2` 73 on-target selections across 14
latents; `math_code→w3` 108 across 7. Ckpt-0 composite detail:
fork_join 152 C2-eligible completions (8 optimal, 5 direct + 8
semantic contrast groups); math_code 15 eligible (0 optimal —
the asymmetric starting condition persists, disclosed).

**Sentinel (`math_atomic`, training-exposed): silent, as expected
at ckpt-0** — 15 groups, 0 worker-1 selections, 0 varying groups,
all firsts None. The block is in place for P0's unlocking
trajectory.

Zero-variance 0.8433 (C1: 0.8777 on the old mixture).

## 3. Sizing (derived and persisted; the P0-freeze input)

`derive_p0_size_v2` over the three sizing cells (sentinel
excluded): min cell = `code_atomic` (13 counted) → **39 epochs /
6,123 groups nominal**. At the C2-measured beta-0 rate
(≈4.65 s/group) that is ≈7.9 h of generation — plausibly WITHIN
the 10-hour operational ceiling for the first time (the C1-based
derivation was ~33 h), pending the beta-smoke wall rate and the
measured finalization reserve through the frozen cap formula. The
capped branch remains available and its semantics frozen; whether
it triggers is now an empirical question for the P0 freeze.

## 4. Wrap-up disposition (290_f exit condition)

C2 is ACCEPTED (direct-Q1 passed); the Q2 outcome sets the scope:
**Q1 + Q2 hierarchical-unlocking authorized** — the full permitted
scope under the signed matrix. The C2 closeout is the ledger head;
envelope and reserve reconciled; 289_f stands. **The Unit-C
wrap-up is COMPLETE.** Per the signed sequence, next is the 287_f
contract-spine cleanup on `conductor_spine` (with the 288_s
equivalence requirement: the spine must reproduce the legacy C2
schedule, classes, estimand counts, gates, and decision on the
frozen C2 inputs), then val/cycle/`R_cycle`, the beta smoke, and
the P0 freeze ON the spine.

## 5. Next

Reviewer pass on this execution record → the 287_f spine design
review → spine implementation on `conductor_spine` → merge → the
deferred pre-P0 units → P0.
