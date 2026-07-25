# 179_f — Unit-D second repair (response to 178_s)

All three P1 integration blockers and the lower-severity
commands/logs gap are implemented; the successor is reissued as
**180_f** (rev3 — 177_f stands at reviewed bytes) with the
regenerated source identity. Full CPU suite: see §5. No formal
statistical run started; both amended run roots remain absent.

## 1. The real launch path works (finding 1)

`build_lock_bundle`'s production default now derives the support
from `payoff_support.support_observations()` — the 18
identity-selected observations, unique by construction (the
smoke-schedule rows duplicate each observation across the two prompt
schedules: 36 rows, 18 unique — exactly the refusal the reviewer
reproduced). Verified on this box: the production default builds the
registry with **49,342 entries and the PINNED digests unchanged**
(`seed_registry_sha256 = dbd8a12f…`, `b_support_sha256 =
5eb2ec57…`) — the earlier battery had deduplicated through a dict,
so no frozen value moves. A test now exercises the production
default with no injection
(`test_build_lock_bundle_production_default`).

## 2. Replay/finalize consume the persisted bundle; CPU-first enforced (finding 2)

The CPU tranche is the ONLY step that creates the canonical bundle.
`persisted_context()` is the replay/finalize context and enforces,
BEFORE the replay root is claimed or any model loads:

1. the CPU run root exists, its record is `complete`, and it holds
   exactly the pre-aggregate frozen file set (replay cannot start
   early, and nothing runs twice);
2. the persisted bundle EQUALS the bundle rebuilt from current
   authoritative provenance — committed document bytes, clean HEAD,
   recomputed source digest, fresh validated environment manifest,
   canonical registry — so a moved HEAD or changed environment
   identity refuses up front, not at finalization after 9,216 GPU
   completions.

The CLI wires `tranche` → `formal_context` (creates),
`replay`/`finalize` → `persisted_context` (consumes). Tested:
missing root, incomplete record, and post-run provenance drift all
refuse; the happy path returns the byte-identical persisted bundle.

## 3. Explicit archive modes (finding 3)

`archive_evidence(mode)` with `--mode success|abort` required on the
CLI:

- **success**: refuses unless the persisted bundle passes its
  self-hash, equals the replay root's copy AND the bundle rebuilt
  from current authoritative provenance; both run records
  `complete`; both roots hold their EXACT frozen file sets —
  including the finalized `aggregate.json`. CPU-complete/
  replay-absent is not archivable as success.
- **abort**: preserves whatever bytes exist WITHOUT trusting the
  bundle — self-hash failures, cross-root bundle disagreements,
  unreadable manifests and non-terminal statuses are RECORDED in the
  manifest's `validation_errors`, never raised; the replay root may
  be absent. The destination identity falls back from the claimed
  bundle hash to the bundle file's byte hash (`identity_basis`
  records which).
- **both modes**: the copy is staged under a dot-prefixed name,
  verified byte-for-byte against the sources and the manifest, then
  RENAMED atomically into place — a failed copy never strands the
  immutable destination (stale staging refuses loudly).

Lower-severity gap closed: every evidence manifest records the
frozen §11 command list (`commands`) and points at the structured
run records as the formal logs (`formal_logs`) — the plan's
"commands and logs" with no logging framework.

## 4. Changed lines

`stage1_amend1.py`: the support-source swap in `build_lock_bundle`
(two lines + docstring). `stage1_amend1_run.py`: `persisted_context`,
the two-mode `archive_evidence` (staging/rename, recorded errors,
commands/logs), CLI wiring, and the rev3 prereg path constant. Tests:
four new/rewritten (production default, CPU-first/persisted-bundle
ordering, success mode, abort mode). No statistic, grid, seed,
schema, threshold or budget changed; the registry/support/grid/
contract/schema/file-set digests are all UNCHANGED.

## 5. Regenerated identity and suite

Successor source digest (pinned in 180_f §1):
`460a0fe0e982d1ff5225afb8d91a96cfb8ee1bb4bd97f0108063ce430bdd1723`
Full CPU suite: **902 passed under `-W error`, TRUE process exit 0**
(899 + 4 new − 1 replaced). Ready for the narrow changed-lines
review and mechanical checks, then lock.
