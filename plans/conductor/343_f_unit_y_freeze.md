# 343_f — Unit Y (rev1): the cycle cohort record + the final R_cycle reserve (for review)

Issued from the staging draft after the Unit-V closure, per the
SIGNED precursors plan (328_f §1: R_cycle ≠ the P0 finalization
reserve; 330_f §1: CRN seeds; 330_f §3: one exact recomputable
reserve rule; 327_s #5 / 328_f §5: the cycle record's frozen
meaning). CPU-only; no GPU work; no surfaces (one-reveal at cycle
synthesis). Full suite: **1033 passed under `-W error`, TRUE exit
0** (1031 + two Unit-Y tests).

## 1. Identities (the pins for this review to record)

| record | hash |
|---|---|
| `CYCLE_CONFIG_SHA256` | `2b404642a06c0441246d5d634889d34e4fede99f48dcfb92bba9e65559d125d6` |
| cycle seed schedule (720 entries, unique) | `89076715ba7bef4d2a8077a75961f6aa4c6785ace98a8a1f48e736b8b26c16c7` |
| **`cycle_record_sha256`** (`plans/conductor/p0/cycle_record.json`) | `c1caf158cbac0ec8e1daf75a3b9330df1a1304d814053c036871ee7b9f76bb8f` |
| **`r_cycle_record_sha256`** (`plans/conductor/p0/r_cycle_reserve.json`) | `dd924326eb15695c417941009bcb0b31af9aeefabd7431687c3c3563ea5209a8` |

Lineage parent = the Unit-V closeout `929e1724…` (the current
verified head).

## 2. Y1 — the cycle cohort record (`tasks/routing/p0_cycle.py`)

- Namespace `routing_dev_cycle`; six cells × the DETERMINISTIC
  latent prefix 0–4 × all three renderers; **90 observations** in
  canonical order; the canonical natural-mixture weights (1/90,
  ordered pairs, rederived by the loader).
- **Evaluation identity**: domain `cycle_eval`; base seed
  **20260805** (distinct from val 20260804 — test-asserted with
  distinct seeds at matching coordinates); the SAME frozen CRN
  rule (full digest mod 2³¹, slots 0..7, NO checkpoint index —
  identical draws at BOTH cycle checkpoints); the canonical
  sampling identity; the frozen 720-entry seed schedule.
- **The checkpoint rule (`r-cycle-eval-v1`), closed literals**:
  evaluate EXACTLY checkpoint zero + the FINAL P0 checkpoint;
  P0 is DECLARED to close this development cycle; the
  terminally-closed-abort stand-in and the
  no-positive-checkpoint → UNDEFINED branch are frozen text; one
  reveal, then permanent retirement.
- **The full frozen declaration**: the partial-reveal rule; the
  materialization plan (a `cycle_closure` launch inside the final
  R_cycle, through the frozen §4 machinery); the EXECUTION
  IDENTITIES the surface will be materialized against — read from
  the AUTHENTICATED Unit-V evidence (the validated val-launch
  manifest: `wv-4e196a1c…`, `rtp-8510479a…`, the request contract
  and cache identity — the SAME frozen pool), which
  materialization at synthesis must reproduce.
- **Overlap re-assertion, never re-measurement**: the val lock's
  frozen numbers (authenticated under `2aecdf28…`) are bound into
  the record — val↔cycle 15/30; cycle↔training 30 unique / 45
  affected.
- Strict loader: external hash required; the record must
  REDERIVE from the frozen config and the authenticated evidence
  (a rehashed record with a different base seed refuses at the
  rederivation — regression).

## 3. Y2 — the final R_cycle reserve (330_f §3, both derivations persisted)

1. **The registered basis** (231_f retained, validator-gated):
   the Step-4 support closeout `6506f117…` (0.0732 GPU-h / 108
   rendered → **2.44 s/observation**, rederived exactly) × the
   REAL cohort 90 × multiplier 2.0 = 0.122 h → ceil = **1.0**.
2. **The itemized closure ceiling**: cycle-surface
   materialization **0.0637** (the MEASURED Unit-V cost for the
   identical 90-observation shape — the direct calibrator);
   two-checkpoint inference **0.2325** (2 × 90 groups ×
   4.65 s/group, C2-measured); verification/traces/archival
   **0.05** (margin; the Unit-V closure measured well under);
   total **0.3462** → ceil = **1.0**.

`R_cycle_final = max(1.0, 1.0) = 1.0 GPU-h` — the equal-rounding
coincidence EXPOSED by persisting both derivations (329_s); the
build refuses if the itemized total exceeds the reserve (the
closure-obligation proof, also a test).

**The ledger final-reserve path is now ENABLED with real
validators** (replacing the 228_s F2 unconditional refusal): a
`status: final` reserve must carry a whole-valued
`itemized_ceiling_gpu_hours` and recompute EXACTLY as
max(ceil(basis), itemized ceiling); its freeze must bind
`cycle_record_sha256` + `r_cycle_record_sha256` (+ file hash),
and the ledger LOADS both records through their rederiving
strict loaders — truthy strings still refuse. A provisional
reserve carrying an itemized field refuses; the old
provisional-boundary final refusal is retained (message updated).

**Rehearsed, not yet executed**: the test appends the final
reserve to a COPY of the REAL ledger — the envelope's reserve
becomes 1.0/final and the chain verifies — while the real ledger
is untouched (asserted). **The real append
(`record_final_r_cycle` on head `929e1724…`), which replaces the
provisional 5.0 and frees ≈4.0 GPU-h, executes only AFTER this
unit is signed.**

## 4. Disclosure

While pinning the support-closeout constant I initially
transcribed a full hash from a 12-character prefix — the
verified-chain lookup in `build_r_cycle_reserve_record` refused
it immediately ("the registered support closeout is not in the
verified chain"), and the true hash was substituted before any
artifact was frozen. Same failure mode as the Unit-1 disclosure;
same mechanical refusal caught it.

## 5. Tests

`test_p0_cycle_record` (cohort/order/seeds/schedule pin;
committed record loads + rederives; forged-seed rehash refuses;
identities == the authenticated manifest; overlap re-assertion;
write-once) and `test_p0_r_cycle_final_reserve` (both derivations
recompute; the max rule at the validator; whole-valued itemized
required for final and forbidden for provisional; the real-ledger
COPY rehearsal; missing-binding final refuses; the real ledger
untouched). Both pin the PRISTINE val config against the val
fixture's patched lineage (the recurring pattern).

## 6. Next

Reviewer pass (recording the §1 pins) → the REAL
`record_final_r_cycle` append on head `929e1724…` → Unit T rev1
(the beta smoke; its staged draft then gains the post-Y envelope
state) → Unit L → checkpoint-zero eval → P0.
