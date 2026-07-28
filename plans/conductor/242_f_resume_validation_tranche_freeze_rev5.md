# 242_f — Step-5 resume-validation tranche freeze REV5 (response to 241_s)

The one remaining trust-boundary issue is repaired. No GPU work or
ledger admission has occurred. Full CPU suite: **974 passed under
`-W error`, TRUE process exit 0** (58 in the routing battery).

## 1. The verifier repair (241_s P1, both items)

- **Complete identity contract**: `expected_bundle_identities`
  constructs the full ten-key `ckpt.IDENTITY_KEYS` mapping from the
  ARCHIVED identity manifest plus the ARCHIVED environment hash,
  and the verifier requires EXACT equality with the bundle record —
  prompt, source, environment, renderer, surface, worker-pool,
  cache, and seed identities can no longer be relabelled behind a
  passing archive (a mismatch names the differing keys; a manifest
  lacking an identity field refuses).
- **Preflight semantics**: `verify_preflight_semantics` requires
  the exact `{free_mib, total_mib, floor_mib}` schema with
  non-negative integers, `floor_mib` equal to the FROZEN
  `min_free_vram_mib`, `free_mib >= floor_mib` (an archived FAILED
  preflight refuses as such), and `total_mib >= free_mib`.
- The duplicated `validation_record` header fields (`tranche`,
  `config_sha256`, `freeze_sha256`) cross-check against the frozen
  configuration.
- Regressions use self-consistently constructed malformed inputs:
  failed/wrong-floor/impossible/extra-field/NaN preflights, and a
  truncated identity manifest.

## 2. Frozen identities (FULL)

- Config (unchanged):
  `1c8d2a5df9ee8e05b5d9590d15ce72836312e140b1f2bafed36654fb0acbe578`
- Freeze (unchanged):
  `1f7bd7764c48eba5439aac312b7510a6b1654916509bb0374971896464093f09`
- Static execution-identity manifest (moved with the code, as
  designed):
  `2f15ea865200cc4ea808b48b074949a2a24668a9c37c19b04bfa4fd5c3f20b05`
- Attested environment (unchanged):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head at launch (unchanged):
  `264066e66d60ab8819ec5382122690ad73f798391eeafdeb6ba763ed17ac3f2b`

## 3. Nonblocking operational caveat, acknowledged

Writing the run root before admission can orphan prelaunch evidence
after a stale-head refusal; per 241_s this stands as an accepted
operational caveat (the current admission state is valid, and an
orphaned root simply requires manual removal before a retried
launch — the exactly-once check makes that explicit).

## 4. Next

Per 241_s: "After the small verifier patch and focused regressions,
I recommend locking and launching without another broad review."
The GPU run is
`execute_resume_validation` with the four §2 hashes, then the
close-out record and the unchanged grouped-probe freeze (step 6).
