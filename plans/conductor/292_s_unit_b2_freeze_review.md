Verdict: the mixture design is correct, but I would not sign the Unit B2 freeze yet. Three narrow contract fixes remain.

### Blocking findings

1. **The C1 hard gate is optional in the actual workflow.**

   `tranche_freeze()` only authenticates the B2 config; it does not call `reverify_c1_archive()`. The regression test calls both functions separately, so successful freeze construction does not prove that the gate ran.

   Relatedly, `c1_rates_rederived()` authenticates only `exposure_report.json`. The configured sample-record and closeout hashes are unused. A corrupted sample record therefore leaves rate derivation successful even though the full archive verifier correctly rejects it.

   Add one authoritative C1-basis verifier which:

   - verifies the ledger chain and exact `9f4661a8…` head;
   - confirms the closeout binds the expected report, sample record and terminal inventory;
   - runs the untouched V1 archive verifier;
   - only then derives the heuristic rates.

   Invoke it at the B2 freeze boundary and again in C2 preflight.

2. **The Q1/Q2 outcome contract remains prose-only.**

   The config contains thresholds, but does not freeze:

   - the Bridge-only direct-Q1 population and counted-event definition;
   - the `q2_composite`-only Q2 population and exclusion of direct controls;
   - the decision matrix;
   - infrastructure abort as “no scientific outcome.”

   Add these as explicit configuration plus a small pure decision function, tested over Q1 failure, Q1+Q2, Q1-only, and infrastructure-abort branches.

3. **The documented frozen schedule identity is not mechanically pinned.**

   The exact `592f1e81…` record hash appears in the document, but no implementation boundary or regression asserts it. A later builder edit could produce a new self-consistent schedule under the unchanged config hash.

   Add an expected-record-hash constant or external freeze manifest, enforce `592f1e81…`, and assert both the hash and 157-row count.

### Sentinel correction before C2

`sentinel_block()` accepts `classes` but never uses it, so it currently includes every `math_atomic` row rather than the exact Anchor/sentinel population. The current schedule makes this harmless, but the shared P0 estimator would be vulnerable to contamination later. It also records group indices but not the group/update indices required by the signed plan.

Bind it to the frozen sentinel IDs or Anchor class and persist both first-group and first-update occurrences.

### What passed

- All documented config, freeze and mixture hashes reproduce.
- The 157-row mixture and 6/39/39 Bridge allocation are exact.
- All non-Bridge identities and multiplicities remain identical to V1.
- The C1 archive independently reverifies as `PASS`.
- V1 code remains untouched.
- The heuristic projections and three-cell sizing arithmetic are correct.
- Full suite: 1006 tests pass under warnings-as-errors; diff and worktree are clean.

These are boundary-enforcement defects, not a problem with the chosen mixture. After the targeted fixes, a narrow changed-lines review should be sufficient; another broad Unit B2 redesign or audit is unnecessary.