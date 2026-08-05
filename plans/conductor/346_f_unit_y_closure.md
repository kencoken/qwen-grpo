# 346_f — Unit Y CLOSED: the final R_cycle reserve is APPENDED

Unit Y was signed at rev2 (the four pins recorded by the review:
config `843521a8…`, schedule `89076715…`, cycle record
`d617ab5f…`, reserve record `e13cf4d3…`). The real append has
been executed per the sign-off.

## 1. The append

- `record_final_r_cycle` executed on EXACTLY the frozen parent
  head `929e1724…` (the complete Unit-V closeout) — the
  lifecycle-bound boundary.
- **New ledger head (entry 20):
  `6fea9e3be1f2043d38c297e50bcce36b9d225ce741d61de3ed3a56054e8dba51`**
  — 20 entries verify.
- **The envelope now reports the FINAL reserve: 1.0 GPU-h**
  (status `final`), replacing the provisional 5.0 — P0 admission
  arithmetic (`remaining ≥ launch_max + R_cycle`) gains ≈4.0
  GPU-h of headroom. Remaining envelope: 56.8058 GPU-h.
- The ledger entry's freeze binds the cycle record, the reserve
  record (self + committed file hashes), and the registered
  support-closeout basis; the validator loaded both records
  through their rederiving strict loaders and checked the
  complete reserve projection at append time.

## 2. Test adjustment (disclosed)

The rev2 rehearsal test replayed the append on a full copy of
the real ledger; after the REAL append that copy's head is no
longer the frozen parent. The test now rehearses on a TRUNCATED
copy (the valid chain prefix ending at `929e1724…`), asserts the
rehearsed entry hash EQUALS the real appended entry
(`6fea9e3b…` — the append is deterministic), and asserts that any
further append refuses on both the copy and the real ledger
(exactly-once). Full suite: **1033 passed under `-W error`, TRUE
exit 0**.

## 3. Carry-forward for Unit L (registered)

Per the sign-off: P0 admission must CROSS-CHECK the persisted
final ledger entry against the pinned raw reserve record
(`e13cf4d3…`) and reject duplicates — generic ledger parsing
alone is never scientific authorization. This joins the
`admit_p0_execution` obligations of the signed 330_f §4
admission contract.

## 4. Next

Unit T rev1 (the beta timing smoke) — issued from the staged
draft with the post-Y state: head `6fea9e3b…`, final reserve
1.0, remaining 56.8058.
