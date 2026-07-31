# 282_f — Unit C EXECUTED: machinery clean; the preregistered decision is STOP-AND-REVIEW

The approved rev4 ran 2026-07-31: **all execution gates passed, the
anchored verifier rederives PASS from the archive — and the frozen
Q1 gate FAILED in `math_atomic` (0 counted groups in 150 bridge
draws), so the preregistered decision is stop-and-review: no P0
launch.** That is the mechanical rule doing exactly what it was
frozen to do; nothing downstream is authorized by this document.

## 1. The run (all ledger-recorded)

- Launch `2314cfdd…` against head `b88eba02…` (= the frozen lineage
  parent); freeze `c90560dd…`, identity `6fa701a2…`, attested
  environment `372f958f…` all matched; preflight 24,079 MiB.
- 785 groups / 6,280 completions, 58.7 min wall, **0.9768 GPU-h**
  (under the 1.25 stop-bound; the 273_s margin was used — 0.944 was
  the point estimate). Zero-effective-update PROVEN over the two
  persisted 504-key maps; counters 785/785/785/6280; schedule
  exact. Complete closeout `9f4661a8…` = the new LEDGER HEAD (15
  entries verify). **Envelope: 2.1163 consumed / 57.8837 remaining;
  reserve 5.0 intact.**
- `verify_unit_c_run` rederives PASS in-run, post-hoc, and from the
  committed evidence copy alone
  (`plans/conductor/evidence/unit_c_v1/`, 664 KB — the complete
  archive including the full 785-row trace).

## 2. The preregistered evaluation (measured)

**Q1 gate (≥2 counted from ≥2 latents per critical cell):**

| Cell | Counted / draws | Latents | Renderers | Pass |
|---|---:|---|---|---|
| code_atomic | 32 / 60 | 8, 10, 11, 12 | all three | ✓ |
| fork_join | 3 / 60 | 22, 27 | goal_first | ✓ |
| **math_atomic** | **0 / 150** | — | — | **✗** |
| math_code | 7 / 150 | 11, 12, 16, 19 | all three | ✓ |

**Q2 cold-start gate (per direction, on-target): PASSED with
margin** — `fork_join→w2` 66 worker-2 selections across 10 latents;
`math_code→w3` 115 worker-3 selections across 7 latents. Notably,
ckpt-0 C2 eligibility on the composites is NOT zero (fork_join 142,
math_code 19 eligible completions; 2 optimal each; 2 direct + 2
semantic contrast groups per direction) — the Q2 starting condition
is better than the old-support measurement suggested. Zero-variance
0.8777 (projected 0.8508). Sizing: NOT DERIVABLE (a critical cell
has zero counted groups) — exactly as frozen.

## 3. What the math_atomic failure IS (the informative part)

All 150 `math_atomic` bridge draws — every latent, every renderer,
every subtype (T1/T2/T3) — were zero-variance at exactly reward
0.5: **1,200/1,200 valid completions, not one family-correct math
route sampled.** Under the frozen transport assumption (2/72 from
the original support) the probability of 0 in 150 draws is ≈1.5%,
so the more likely reading is that the TRANSPORT ASSUMPTION ITSELF
failed for `math_atomic`: the original support's two varying groups
came from its specific latents, and the checkpoint-zero
family-correct sampling rate on the NEW bridge latents is
effectively zero. The deep wrong-worker basin (ckpt-0 C1 0.35%) is
even deeper on the extension rows. This was a known risk, disclosed
in the Unit-B projections as a transport assumption; the frozen
gate converted it into a stop instead of letting P0 launch with an
unmeasurable Q1 cell.

## 4. What this run does NOT decide

Per the frozen rules: no P0 launch; the sizing rule is not
derivable; any mixture change is a NEW B/C iteration with new
identities; and the choice among the plausible responses —
rebalancing `math_atomic` Bridge mass (unlikely to help a 0/1,200
rate), a reviewed scope amendment (e.g. removing `math_atomic` from
the Q1-critical set, with the claim narrowed accordingly), or a
different curriculum device for the math basin — belongs to the
REVIEW, not to this record. The other three cells' measured rates
(code_atomic 6.4/epoch, math_code 1.4/epoch, fork_join 0.6/epoch)
and the passed Q2 gates are valid inputs to that decision.

## 5. Next

Reviewer pass on this execution record and the stop-and-review
disposition → the reviewed decision on the `math_atomic` branch
(scope amendment vs new B/C iteration vs curriculum change) →
whatever it authorizes.
