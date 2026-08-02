# 293_f — Unit B2 REV2 (response to 292_s)

All three boundary-enforcement fixes and the sentinel correction
applied; identities regenerated. Full suite: **1006 passed under
`-W error`, TRUE exit 0**.

## 1. B1 — one authoritative C1-basis verifier, run by the freeze

`verify_c1_basis()` is now THE single path to the heuristic rates:
it verifies the ledger chain at the exact frozen head `9f4661a8…`;
confirms the C1 closeout binds the expected report bytes
(`3e708f67…`), sample-record bytes (`7f52e420…` — now actually
checked), and a non-empty terminal inventory; runs the untouched V1
archive verifier; and only then derives and equality-checks the
rates. **`tranche_freeze()` invokes it** — a successful freeze now
PROVES the gate ran (memoized per process so repeated freezes don't
re-pay the archive verification). `c1_rates_rederived()` is a thin
alias of the authoritative path, and C2 preflight will call it
again pre-launch.

## 2. B2 — the outcome contract is frozen configuration + a pure function

`outcome_contract` in the frozen config now carries: the
bridge-only direct-Q1 population and the counted-event definition;
the q2_composite-only Q2 population with the direct-specialist
control excluded; the full decision matrix; and infrastructure
abort as "no scientific outcome" under the repair/relaunch
protocol. `decide_c2_outcome(q1_pass, q2_pass,
infrastructure_abort)` is the pure decision function over that
matrix, tested on all four branches (Q1 fail / Q1+Q2 / Q1-only /
abort).

## 3. B3 — the schedule identity is mechanically pinned

`EXPECTED_MIXTURE_V2_RECORD_SHA256` and `EXPECTED_EPOCH_ROWS = 157`
are module constants enforced in BOTH `build_mixture_v2` (the build
refuses if it does not produce the frozen identity) and
`verify_mixture_v2` (the pin is checked before any rederivation —
a rehashed self-consistent variant refuses at the pin, regression
included). A later builder edit can no longer produce a new
schedule under an unchanged config hash without a visible constant
change. The build is asserted to equal the pin in tests.

## 4. Sentinel correction

`sentinel_block(trace_rows, sentinel_observation_ids,
updates_per_group=1)` is now BOUND to the frozen sentinel ids (the
mixture's Anchor sentinel population): a non-Anchor `math_atomic`
row cannot contaminate it (regression), and an empty population
refuses. Both **first-group and first-update indices** are
persisted for every first-occurrence field (one group per optimizer
step ⇒ update = group; the parameter documents the mapping for any
future grouping).

## 5. Frozen identities (regenerated — the config gained the outcome contract)

- Config:
  `66d62b924a471c869dd77312b062399842eedd05325b3927c8cee542b0e6cfb5`
- Freeze (its construction now runs the C1-basis gate):
  `7f7d765cd4cfbe9820e2c7c6facfda39eb36d3436ff9c9fc284940db11732eef`
- Mixture record (PINNED):
  `135a72bf4deb77048371074636d88ffebf6bd07d1c00ae349b6fcee221975b3f`
- Inputs unchanged: extension lock `ccb1c3e2…`; selection
  `c6c08775…`; C1 evidence `3e708f67…`/`7f52e420…`/head
  `9f4661a8…`. V1 identities untouched (still asserted):
  `92f933e8…` / `69f73a58…`. The schedule CONTENT is unchanged from
  rev1 (157 rows, 6/39/39; the record hash moved only because the
  embedded config hash gained the outcome contract).

## 6. Next

Narrow changed-lines review (292_s closing) → C2 freeze (repeat
the trainer-path invalidation audit; `verify_c1_basis` again in
preflight; fresh seed; the PINNED schedule `135a72bf…` at 5 epochs;
`sentinel_block` + `decide_c2_outcome` consumed by the report) →
C2 run → decision per the frozen matrix → the 287_f spine branch.
