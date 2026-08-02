# 295_f — Unit B2 REV3 (response to 294_s)

Both final fixes applied. Code-only repairs: the frozen config did
not change, so **config, freeze, and the pinned mixture record are
UNCHANGED** (`66d62b92…` / `7f7d765c…` / `135a72bf…`). Full suite:
**1006 passed under `-W error`, TRUE exit 0**.

## 1. B1 — no cache; historical closeout within a valid chain

- **Caching removed from the mandatory boundary**: `verify_c1_basis`
  runs FRESH on every call. The reviewer's reproduction is a
  regression: after a successful (warm) call, making the underlying
  V1 verifier fail now makes both `verify_c1_basis()` and
  `tranche_freeze()` refuse.
- **Chain semantics fixed**: the verifier now verifies the ledger
  chain to its CURRENT head and requires the frozen `9f4661a8…`
  entry to appear EXACTLY ONCE in that valid chain as a complete
  closeout with the frozen report/sample-record bindings and a
  non-empty terminal inventory. Later legitimate C2 launch/closeout
  entries no longer break B2 rebuild/verification — a regression
  appends a valid suffix entry to a ledger copy and shows
  `verify_c1_basis` still passes. The LAUNCH-time head anchor
  remains the separate per-launch `expected_head` check (C2's
  admission binds its own frozen parent, as before).
- `verify_c1_basis` gained an explicit `ledger_path` parameter
  (default the real ledger) so the suffix regression exercises the
  real code path.

## 2. B2 — the sentinel population is structurally bound

`sentinel_block(trace_rows, mixture_record, updates_per_group=1)`
now derives its population FROM THE PINNED RECORD: the supplied
record's hash must equal `EXPECTED_MIXTURE_V2_RECORD_SHA256` AND
the record must rehash, and only then are its frozen sentinel ids
used. Caller-selected ID lists no longer exist in the API.
Regressions: a rehashed record with a foreign sentinel population
refuses at the pin; a record carrying the pinned hash over a
tampered body refuses at the rehash; foreign `math_atomic` rows in
the trace still contribute nothing.

## 3. Carried forward to C2 (294_s closing)

The frozen population descriptions become EXECUTABLE row predicates
with cross-population tests in the C2 implementation — recorded
here as a C2-freeze obligation.

## 4. Identities (unchanged — code-only repairs)

- Config:
  `66d62b924a471c869dd77312b062399842eedd05325b3927c8cee542b0e6cfb5`
- Freeze:
  `7f7d765cd4cfbe9820e2c7c6facfda39eb36d3436ff9c9fc284940db11732eef`
- Mixture record (pinned):
  `135a72bf4deb77048371074636d88ffebf6bd07d1c00ae349b6fcee221975b3f`
- V1 identities untouched: `92f933e8…` / `69f73a58…`.

## 5. Next

Very narrow review (294_s closing) → B2 sign-off → C2 freeze
(trainer-path audit repeat; `verify_c1_basis` in preflight; fresh
seed; the pinned schedule at 5 epochs; executable row predicates
with cross-population tests; `sentinel_block` +
`decide_c2_outcome` in the report) → C2 run → decision → spine.
