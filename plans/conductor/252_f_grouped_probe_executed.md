# 252_f — Step 6 EXECUTED: the grouped probe ran clean; exposure is MEASURED

The signed-off rev3 probe ran 2026-07-29 on the frozen design: **432
groups / 3,456 completions through the real trainer loop, zero
effective parameter updates PROVEN (persisted checkpoint-zero and
final adapter maps are equal), all gates passed, and the anchored
`verify_probe_run` rederives PASS** — in-run before the closeout,
again post-hoc from the live root, and a third time from the
committed evidence copy alone.

## 1. The run (all ledger-recorded)

- Launch `0eca0fcb…` against head `1a8d41fd…` (= the frozen lineage
  parent; the rev3 anchor makes any other head unlaunchable);
  freeze `88fee921…`, identity `2155a8bf…`, attested environment
  `372f958f…` all matched; preflight 24,079 MiB free (floor 20,000).
- 432 optimizer steps at lr=0/beta=0, ~4.0 s/step, wall 31.2 min;
  peak reserved VRAM 6,088 MiB; deadline 10,800 s never approached.
- Zero-effective-update gate: `checkpoint_final_hashes.json` ==
  `checkpoint_zero_hashes.json` (both persisted). Counters exactly
  432/432/432/3456. Every trace row matches the frozen schedule
  (bound cohort order × 4). Telemetry: 3,449 surface reward lookups
  (= valid completions), zero live worker calls.
- **Measured cost 0.5192 GPU-h** (well under the 3.0 ceiling);
  complete closeout `88c037a1…` = the new LEDGER HEAD, binding the
  report/record file hashes and the exact terminal inventory. Chain
  verifies: 11 entries. **Envelope: 0.6461 consumed / 59.3539
  remaining, nothing open.**

## 2. Evidence

The complete archive is small and is committed VERBATIM:
`plans/conductor/evidence/grouped_probe_v1/` (508 KB — full
per-group trace `actions.jsonl`, both adapter hash maps,
environment/identity/preflight/schedule/cohort manifests, report,
record). `verify_probe_run(evidence_dir, identity, environment)`
rederives PASS from this copy alone; the live root
`runs/routing-dev/probe-v1` is inventory-bound by the closeout.

## 3. MEASURED exposure (the registered measurement, 211_f §5 denominators)

Health: parse 3,456/3,456 (100%); valid 3,449/3,456 (99.80%); mean
reward 0.721; C1 family-correct 58.49%; mean routing entropy 0.324
bits (the untrained checkpoint-zero policy is highly concentrated).

Direction-conditioned exposure — denominators are the registered
432 / 216 Code-bearing / 24 direction-bearing (16 w2-fav, 8 w3-fav):

- **no_pair (216 groups)**: direct contrasts 0 (structurally);
  reward-varying groups only 2/216 — 214/216 groups are
  zero-variance (144 all-1.0, 70 all-0.5).
- **tied Code (192 groups)**: direct w2-vs-w3 contrasts 15/192
  (7.8%); semantic contrasts 40/192; 148/192 zero-variance.
- **w2-favoured (16 groups)**: direct contrasts **3/16** (18.8%);
  semantic 4/16; ModelAcc 21.1%; C2 optimal-specialist 32.8%.
- **w3-favoured (8 groups)**: direct contrasts **0/8**; semantic
  0/8; ModelAcc 31.3%; 6/8 groups all-0.5 zero-variance.

Support matrix: **22 of 72 cell × renderer × direction strata have
any measured exposure; 50 are zero** — committed in the report so
the P0 transport gate can mechanically reject unmeasured strata.

## 4. Reading (discipline: opportunities, not thresholds)

The registered discipline holds: few or zero exact contrasts is
**underexposure evidence, not failure**. The headline measurement
for P0 design is that the untrained policy delivers exact
w2-vs-w3 contrasts in only **3 of 432 groups** (all in w2-favoured
strata; the w3-favoured direction got ZERO in 8 opportunities), and
~84% of all groups are reward-zero-variance, i.e. produce no GRPO
gradient signal at all. Combined with the Step-4 disclosure (only
6/54 Code-pair observations direction-bearing), natural exposure
under the untrained policy is far too sparse for P0 to measure
direction-learning as-is — exactly the case the charter anticipated:
**P0 must be designed around outcome-conditioned direction
enrichment and an exact-cohort exposure sample, not natural-mixture
reweighting.** These are development observations; nothing here is
confirmatory.

## 5. Next (211_f §15 sequence)

Reviewer pass on this execution record and report → P0 designed
from THIS measured exposure (checkpoint-zero-first, transport rule
byte-reproducible, fp32 LoRA normative) → routing_dev_val lock → P0
freeze → P0. The R_cycle reserve basis can now also be refined with
the probe's measured seconds/group if the reviewer wants it.
