# 345_f — Unit Y REV2 (response to 344_s)

All four P1s and the cheap accompanying repair applied, CPU-only;
both records REGENERATED under the amended config. `R_cycle`
remains **1.0 GPU-h**. Full suite: **1033 passed under `-W
error`, TRUE exit 0**. The real ledger remains untouched at
`929e1724…`.

## 1. New identities (both records regenerated pre-signature)

| record | hash |
|---|---|
| `CYCLE_CONFIG_SHA256` | `843521a836f63c78979ed8af053bcd1b2688b418639a398bf6e2637daecdb206` |
| cycle seed schedule | UNCHANGED `89076715…` |
| **`cycle_record_sha256`** | `d617ab5fbb609fc89c250e6a79627b2ed28e54603fa1fed2253d855a3abaccdc` |
| **`r_cycle_record_sha256`** | `e13cf4d3605393186499cab0490d5e2bc289c77841b146841d0f52258f422265` |

## 2. P1 — the future cycle surface is completely frozen and authenticated

- `_val_execution_identities` now reads the five identity fields
  from the **val-lock-bound SURFACE LOCK** (authentication chain:
  the reviewed pin `2aecdf28…` → the surface-lock self AND file
  hashes → the fields), with the prelaunch manifest required to
  AGREE — the rehashed-mixed-archive reproduction refuses on
  either side.
- The record gains the COMPLETE 328_f §5 declaration
  (`_cycle_declaration`): generator version + difficulty-profile
  version (uniformity asserted), the exact 90-row geometry with
  per-row arities and **4,020 planned step executions**, worker
  ids, the prompt revision (**rev10**, from the frozen pool
  profile constant — the authoritative in-code source, with the
  val declaration agreeing), and the **semantic and
  rendered-prompt SCHEDULE hashes** (alpha-normalized,
  handle-invariant, canonical order) — a generator semantic
  change without a version bump now breaks the rederivation.
- Exact regeneration before any worker call is bound into the
  materialization plan: synthesis must load through
  `load_cycle_record`, which regenerates cohort, declaration
  geometry, and both schedule hashes and refuses on ANY drift.

## 3. P1 — the closed one-reveal reporting rule

The record now carries `report_schema` (`cycle-report-v1`):
binds the frozen `P0ScienceContract` (`d47a63ff…`); estimands BY
REFERENCE to the frozen `p0_estimands` rules; PAIRED
checkpoint-zero-vs-final comparisons under common random numbers,
aggregated at latent level (descriptive only); the bound
natural-mixture weights and equal-cell view with cell × renderer
strata; the frozen malformed handling (scores 0, never dropped);
the closed metric list with explicit denominators (720
completions, 15 groups/cell, 90 groups); and
repeated-vs-novel-template reporting RETAINED with EXACTLY the
frozen membership — the 45 `cycle_vs_training`
`affected_candidate_ids` bound in the record's overlap
re-assertion, never recomputed post-reveal.

## 4. P1 — the itemized reserve is exactly recomputable

`_itemized_closure` DERIVES every measured item at build time:

- materialization **0.0637** = `budget_consumed_gpu_hours` of the
  verified Unit-V closeout `929e1724…` (from the chain, not a
  literal);
- inference **0.232357** = 2 × 90 × (3648 s / 785 groups =
  4.64713 s/group) / 3600 — the rate from the AUTHENTICATED C2
  sample record (file pin `cc42c16b…` verified before reading);
- `verification_traces_archival` **0.05** — a NAMED FROZEN
  allowance;
- `checkpoint_loading_evaluator_startup` **0.10** — the new NAMED
  FROZEN allowance (two checkpoint loads + evaluator startup).

Total **0.4461** → ceil **1.0** = max(basis 1.0, itemized 1.0) —
unchanged reserve, now recomputable. The tests assert the
derivations against their sources, not literals against
themselves.

## 5. P1 — the lifecycle-bound append + the ledger projection check

`record_final_r_cycle` now requires: the head EXACTLY equals the
cycle record's frozen parent (`929e1724…` — the complete Unit-V
closeout, verified present as the chain head); and NO final
reserve exists in the chain. Regressions: a foreign head refuses;
a second append after the first refuses. The ledger's final
branch additionally compares the freeze's
`r_cycle_record_file_sha256` against the COMMITTED file bytes and
the COMPLETE persisted reserve projection field-by-field against
the strictly loaded record — same-rounding lookalikes refuse
(344_s cheap repair).

## 6. Next

Narrow changed-lines/arithmetic review (per 344_s) → the REAL
`record_final_r_cycle` append on head `929e1724…` → Unit T rev1.
