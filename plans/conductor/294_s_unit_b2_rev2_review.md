Verdict: Rev2 closes the original findings, but I would make two final narrow fixes before signing.

### Blocking

1. **C1 verification is cached and tied to the historical closeout remaining the current ledger head.**

   `_C1_BASIS_CACHE` means a later freeze/preflight can reuse an earlier result without rechecking evidence. I reproduced this: after warming the cache, making the underlying verifier fail still allowed `tranche_freeze()` to succeed.

   Separately, `verify_ledger_head(9f4661a8…)` will fail once C2 legitimately appends launch/closeout entries. A fresh-process C2 archive verification would then be unable to rebuild the B2 mixture.

   Fix by:

   - removing caching from mandatory boundaries;
   - validating `9f4661a8…` as the exact historical C1 closeout within a valid ledger chain;
   - checking the separately frozen current ledger head at each launch boundary.

   Add regressions for tampering after an earlier successful call and for a valid later ledger suffix.

2. **The sentinel population remains caller-selected.**

   `sentinel_block()` accepts any non-empty ID list. Passing a foreign `math_atomic` ID makes it a self-consistent sentinel population and can change the denominator and first-unlock trajectory.

   Have it derive IDs from the pinned mixture record, or compare against an exact frozen three-ID set. Merely passing the intended IDs from C2 is not structural binding.

### Closed correctly

- Report, sample-record and closeout provenance are now genuinely checked.
- The Q1/Q2 populations and four-way decision matrix are frozen appropriately for B2.
- The 157-row schedule and `135a72bf…` identity are mechanically pinned.
- The mixture remains exactly 6/39/39 with unchanged non-Bridge content.
- Infrastructure abort correctly has precedence and yields no scientific outcome.
- The current sentinel group/update mapping is correct because the frozen Unit-C path records one optimizer update per group.
- All regenerated hashes reproduce.
- Focused tests pass 4/4; the full 1006-test suite passes under warnings-as-errors; diff and worktree are clean.

For C2, the frozen population descriptions should become executable row predicates with cross-population tests, but that can properly land in the C2 implementation. After the two fixes above, a very narrow review should be enough to sign Unit B2.