# 351_f — Unit T REV3 (response to 350_s): the bounded runner repair (for review)

All five blocking findings repaired with focused regressions on
the real paths. Full suite: **1034 passed under `-W error`, TRUE
exit 0**. New identities in §6 (the config and freeze changed;
the prelaunch manifest is prepared only AFTER this rev is signed,
per the 350_s closing note).

## 1. Finding 1 — the real reward path

The training reward is now the ESTABLISHED
`make_validation_reward` boundary (message-list normalization via
`completion[0]["content"]`, group/observation alignment
validation, the FULL 157-group training trace, missing surface
rows as infrastructure errors), wrapped only to add the deadline
check, the rollout-timing hook, and the GroupAccountant update
recording. Regression: the reviewer's reproduction shape — TRL
message-list completions — flows through the boundary and scores
correctly on CPU.

## 2. Finding 2 — the trace timing measures the real operation

- The COMPLETE 157-group training trace is captured (written
  incrementally by the reward boundary).
- Each evaluation pass SEALS ITS OWN trace INSIDE the timed
  phase (deterministic gzip within the window).
- P6 times, SEPARATELY, exactly the training-trace operations:
  flush + deterministic-gzip archive + hash + ROUND-TRIP
  verification — this and only this feeds the ×39 scaling;
  trainer-log sealing follows OUTSIDE that timer.
- `per_epoch_trace_bytes` is the training-trace volume.

## 3. Finding 3 — the production v1 checkpoint, verified then discarded

P4 now executes the VALIDATED checkpoint contract:
adapter safetensors + optimizer + scheduler + persisted RNG state
+ `hash_state_artifacts` + the `build_checkpoint_record` record
with GroupAccountant-AUTHORIZED counters (the accountant is fed
by the real reward/update path) and the sampler position. The
bundle is then RESTORE-VERIFIED (artifact hashes re-derived and
compared). The record retains PROOF ONLY (`checkpoint_proof`:
the checkpoint hash, artifact hashes, counters) and
`_discard_trained_state` DELETES the bundle and any trainer
checkpoint directories BEFORE the successful closeout — the
terminal verifier refuses if the trained state survives.

## 4. Finding 4 — disclosure and RNG, operationally enforced

- `_strip_console_callbacks` removes `PrinterCallback` AND
  `ProgressCallback` after construction (the reviewer is right
  that `disable_tqdm` alone INSTALLS PrinterCallback); log
  history is captured internally and sealed only. Regression on
  the stripping behaviour.
- Both evaluation passes run inside the existing `isolated_rng`
  boundary — the 90 `torch.manual_seed` calls can no longer
  perturb the training RNG stream.
- The EXECUTED seed realization is itself frozen: the 90
  per-observation slot-0 seeds carry their own pin
  (`TIMING_EXECUTED_SEEDS_SHA256`), bound into the freeze
  alongside the 720-entry identity schedule; execution consumes
  exactly `executed_seed_realization()` (a forged pin refuses —
  regression).

## 5. Finding 5 — budget and provenance boundaries

- The deadline is enforced at EVERY training reward entry, EVERY
  evaluation observation, and EVERY phase boundary
  (`_check_deadline`; regression on the helper).
- The persisted environment file is cross-checked against the
  manifest's environment hash at execution.
- The ledger gains an AUTHORITATIVE manifest-bound
  `engineering_smoke` admission branch (exact manifest hash,
  budget equality, the signed smoke-freeze binding), and the
  runner admits WITH its manifest.
- `verify_smoke_run` — the terminal verifier — runs BEFORE the
  success closeout and post-hoc: chain-authenticated launch, the
  record's closed schema, the projection RECOMPUTED from the
  validated measurements, environment cross-bindings, sealed
  files present as `.gz` only, the trained state ABSENT, and the
  complete-closeout inventory byte-for-byte.

## 6. New identities

| identity | hash |
|---|---|
| `SMOKE_CONFIG_SHA256` | `6e775b9079658799e8759a4d8d4bea969dd8bdd8c100016915c8ef6771a9cf41` |
| timing seed schedule (unchanged) | `cbfe5284…` |
| **executed seed realization (90 slot-0)** | `83faa1843fc6c3350cb17ec1bfc69c3a2774f7fc60b65d0ef8ddbd38c84c79d0` |
| **`SMOKE_FREEZE_SHA256`** (regenerated) | `d2d87971765d40da9d2c8aebc29e014e2ca24e82f46a7afbf6c9b32231f75eb7` |

## 7. Next

Narrow review of this runner repair (recording the §6 pins) →
the prelaunch manifest (prepared AFTER sign-off — the code
repairs changed the source identity, as the review anticipated)
→ the narrow prelaunch sign-off → the smoke launch on head
`6fea9e3b…` → the timing-only projection → Unit L.
