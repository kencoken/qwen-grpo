## Verdict

Unit V is **not ready for V2 launch**. V1’s cohort design is sound, but the execution path currently cannot complete, and the V3 lock does not yet authenticate the scientific state it claims to freeze.

### Blocking findings

1. **[P0] Ledger admission always rejects the validation launch.**
   `execute_val_run()` submits `support_materialization` with `val_launch_sha256`, while the ledger requires `support_launch_sha256` and the generic probe-bearing design schema. Renaming the key is insufficient because validation intentionally has no `probe_rule_sha256`. Add a dedicated validation-manifest admission path/kind.

2. **[P0] The surface cannot be locked after materialization.**
   The persisted-launch loader recognizes generic support and extension manifests only. A `routing-dev-val-launch-v1` manifest therefore fails the support manifest’s closed-schema check. Without fixing this, GPU work would finish and then abort during locking.

3. **[P1] The V3 lock accepts unauthenticated scientific state.**
   `build_val_lock()` copies claims from any `surface_lock.json`; the committed test deliberately succeeds with a stub lock. `load_val_lock()` checks only hashes and labels, so a rehashed record with `base_seed=999` also loads. It additionally fails to bind the post-run overlap gate.

   The builder should load and verify the complete surface first. The loader should rederive the cohort, evaluation identity and overlap result under a closed schema and authenticate the underlying surface bytes.

4. **[P1] CRN seed derivation differs from the frozen formula.**
   The implementation hashes only the first four digest bytes before modulo. The registered formula uses the complete SHA-256 integer modulo \(2^{31}\).

   For the first observation, slot 0:

   - Current implementation: `1583932182`
   - Frozen formula: `1176822329`

   Use the full digest and freeze both a known vector and the complete 720-seed schedule hash. Also restrict slots to `0..7`.

5. **[P1] Natural-mixture weights are described but not bound.**
   The lock stores prose rather than the canonical mixture identity and exact observation weights. Persist the canonical definition hash and ordered weights—currently `1/90` for every observation—and rederive them when loading.

6. **[P1] The 0.35 GPU-hour ceiling is not enforced.**
   A timer is started, but no deadline is passed to `materialize_dev_support()`. Use the existing per-observation deadline mechanism so an overrun produces an aborted closeout.

7. **[P1] Launch provenance needs completing.**
   Before launch:

   - make manifest validation closed-schema and recompute the source digest;
   - enforce the frozen C2 ledger parent;
   - bind the tranche-freeze hash to the launch manifest;
   - run a val-specific terminal verifier before successful closeout;
   - freeze the actual prepared manifest/environment/declaration hash in a narrow prelaunch review.

### Smaller conformance gaps

- The signed plan requested semantic/prompt checks across training, validation and cycle populations; the implementation currently checks validation against training only.
- “All namespaces” is tested against only `routing_dev` and `routing_dev_cycle`.
- The claimed complete evaluation identity should bind the full sampling options, not only temperature, token cap and group size.
- The abbreviated `135a72bf…` statement should become the full pinned training-mixture identity.

### What is sound

- Correct outcome-blind prefix: five latents per cell, six cells, all three renderers.
- Exactly 90 unique observations and 4,020 planned worker steps.
- Correct descriptive, paired latent-level framing.
- No policy outcome is generated before checkpoint zero.
- Current semantic and rendered-prompt intersections are genuinely zero.
- All 720 current seeds are collision-free.
- Hashes reproduce; worktree and diff checks are clean.
- Full suite passes: **1,026 tests under warnings-as-errors**.

The green suite currently misses the public V2 lifecycle and encodes the stub-lock defect. I recommend one consolidated repair followed by a CPU-fake end-to-end test covering:

`prepare → admit → materialize → surface lock → overlap gate → val lock → terminal verification → closeout`.

Then prepare the real reward-blind launch manifest and submit its exact hash for a narrow launch sign-off.