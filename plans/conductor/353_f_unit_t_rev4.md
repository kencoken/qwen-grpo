# 353_f — Unit T REV4 (response to 352_s): the bounded lifecycle repairs (for review)

All four remaining blockers repaired, with the four direct
regressions the review names (manifestless admission, callback
ordering, abort cleanup, terminal-proof mutation). Full suite:
**1035 passed under `-W error`, TRUE exit 0** (1034 + the new
regression). As the review anticipated, NO redesign or freeze
change was necessary — **every §6 identity of 351_f is
unchanged** (`SMOKE_CONFIG_SHA256 6e775b90…`,
`SMOKE_FREEZE_SHA256 d2d87971…`, seed schedule `cbfe5284…`,
executed realization `83faa184…`); the changes are code-only in
the ledger admission branch, the runner lifecycle, and the
terminal verifier.

## 1. Finding 1 — the manifest is MANDATORY at admission

The `engineering_smoke` branch in `ledger.py` now refuses
`launch_manifest is None` outright and, with a manifest supplied,
validates:

- the manifest **kind** is `routing-dev-beta-smoke-launch-v1`;
- the entry's freeze names the **exact manifest hash**;
- the admitted budget **equals** the manifest budget;
- the freeze carries the **signed smoke-freeze hash** the
  manifest binds;
- the entry's persisted parent is the **ACTUAL verified head**
  it is admitted on;
- the **first** launch is admitted only on the manifest's frozen
  `lineage_parent_sha256`;
- prior same-freeze attempts: **open → refuse; complete →
  refuse; aborted → retry allowed** — the smoke-freeze hash is
  the retry design identity, exactly as the review suggests.

Regression: the reviewer's reproduction — a manifestless smoke
entry with fabricated hashes — now refuses, as do a wrong-kind
manifest and a coherent manifest whose hash the entry does not
name.

## 2. Finding 2 — accounting and deadline at the correct lifecycle points

- `accountant.record_update` moved OUT of the reward function
  into `on_optimizer_step` — consumption is recorded when the
  optimizer consumes the rollout. The reward wrapper now does
  instrumentation timing + the established boundary ONLY.
- The deadline is checked at `on_step_begin` — BEFORE
  generation — in addition to every evaluation observation and
  phase boundary.
- Before P4 checkpointing, a **five-way cross-check** requires
  `accountant.optimizer_updates == generated_groups ==
  consumed_groups == trainer.state.global_step ==
  instrumentation.updates == 157`.

The callback is now built by a module-level factory
(`_make_update_callback`) so the ordering is directly
regression-tested: an expired deadline refuses at step BEGIN;
consumption **cannot precede generation** (the rev3 defect shape
is structurally refused by the accountant); consumption lands at
`on_optimizer_step`.

## 3. Finding 3 — checkpoint and terminal verification as claimed

- The ESTABLISHED `checkpoint.validate_resume` now runs against
  the bundle (record + identities + `bundle_dir` artifact
  re-hash) BEFORE the trained state is discarded.
- `_validate_checkpoint_proof` validates the surviving proof:
  the closed three-key schema, a 64-hex record hash, artifact
  hashes exactly spanning the required bundle manifest, and
  counters equal to the frozen one-epoch expectation
  (157/157/157/1256). Every mutation channel refuses
  (regressions).
- The sealed inventory is EXACT: on-disk files and the record's
  `sealed_sha256` keys must both equal the four-file set
  {training_trace, eval_ckpt0, eval_post,
  trainer_log_history}.gz — no omissions, no extras, nothing
  unsealed.
- The top-level terminal inventory is EXACT: the three prelaunch
  files, `execute_env_manifest.json`, `smoke_record.json`, and
  the four sealed files — nothing else.
- After the complete closeout is appended, **`verify_smoke_run`
  runs AGAIN against the completed ledger head**, exercising the
  closeout-inventory branch (terminal artifact hashes must match
  the closeout's bound map).

## 4. Finding 4 — abort cleanup obeys the discard/sealing rules

`_sanitize_for_abort` runs in the except handler BEFORE the
aborted closeout is written: any raw JSONL/JSON left under
`sealed/` is deterministically gzip-sealed, and
`_discard_trained_state` removes `checkpoint_bundle/` and any
trainer `checkpoint-*` directories. Only then does the aborted
closeout hash the SANITIZED inventory into
`partial_artifact_hashes`. A cleanup failure **propagates
without writing the closeout** — the launch stays OPEN, and an
open attempt refuses any new launch at admission (§1), so the
failure is visibly blocked rather than authorizing a retry.

Regression: an abort directory with a raw training trace, an
already-sealed eval file, the checkpoint bundle, and an HF
checkpoint dir is sanitized correctly (raw sealed, bundle and HF
dir deleted, sealed bytes untouched); a failing seal propagates.

## 5. Test-suite note

The generic ledger-boundary tests' `_entry()` helper had used
`engineering_smoke` as an arbitrary launch kind; with the
manifest now mandatory, those tests use `standalone_evaluation`
so they keep exercising the generic launch boundary. The
smoke-specific admission paths are covered by the new dedicated
regressions.

## 6. Identities (unchanged from 351_f §6)

| identity | hash |
|---|---|
| `SMOKE_CONFIG_SHA256` | `6e775b9079658799e8759a4d8d4bea969dd8bdd8c100016915c8ef6771a9cf41` |
| timing seed schedule | `cbfe528435882c0728eb79235e9303d85f403de2b7cf1a96cdae99328eb9992b` |
| executed seed realization (90 slot-0) | `83faa1843fc6c3350cb17ec1bfc69c3a2774f7fc60b65d0ef8ddbd38c84c79d0` |
| `SMOKE_FREEZE_SHA256` | `d2d87971765d40da9d2c8aebc29e014e2ca24e82f46a7afbf6c9b32231f75eb7` |

## 7. Next

Narrow review of this lifecycle repair → the prelaunch manifest
(prepared AFTER sign-off) → the narrow prelaunch sign-off → the
smoke launch on head `6fea9e3b…` → the timing-only projection →
Unit L.
