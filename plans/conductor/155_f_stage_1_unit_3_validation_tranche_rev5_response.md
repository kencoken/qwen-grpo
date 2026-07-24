# 155_f — Response to 154_s (the single abort-boundary blocker)

**The blocker is fixed.** `run_replay` now wraps the ENTIRE
post-`running` sequence — `_build_replay_model()` (factored to module
level exactly so the probes can substitute a failing loader), the
generation loop, accounting, raw-completions persistence, artifact
finalization, write, and the reload verification — in one abort
handler: any failure anywhere in that span rewrites `run_record.json`
as `aborted` with wall time and the error, and `complete` is written
only after the reloaded artifact re-validates. `run_record.json` can no
longer be left permanently `running` by a model-load OOM or a
finalization failure.

Both requested probes are named tests, exercising the real
`run_replay` body via the test-only `_inputs` injection point (the
shared authoritative loader `_load_replay_inputs_full` is now the
single input path for driver and verifier):

- **model-load failure**: `_build_replay_model` raising (a CUDA-OOM
  stand-in) → `aborted` record with the error and wall time, with the
  pre-model `env_manifest.json` and `replay_manifest.json` intact on
  disk;
- **post-generation finalization failure**: generation returning
  incomplete accounting → the finalization path aborts with an
  `aborted` record naming the accounting failure, never `running`.

Non-blocking cleanups, both taken as directed (in place, per the
review's explicit invitation): the duplicated rev-4 sentence and the
extra EOF blank line in `153_f` are removed, and `run_full_tranche`'s
run record now also carries `total_wall_seconds` (complete and aborted
paths both).

Focused unit-3 tests: 74; full CPU suite: **735 passed** under
`-W error`. No frozen tranche or GPU replay executed.

Per 154_s: after this changed-lines/test review, lock — no further
open-ended audit. On lock, execution proceeds in the frozen 153_f §6
order: `run_full_tranche()` (deterministic set → benchmark → A → C →
agreement → D under in-loop deadlines, staged persistence throughout)
→ `run_replay()` on the GPU (~50 min; ollama VRAM check first) →
`aggregate_verdict` over the four verified artifacts → the single
reviewed confirm/amend decision, predicted since 141_f to be the
amend-once branch on §8.4C power.
