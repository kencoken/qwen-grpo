# 198_f — B diagnostic repair (response to 197_s)

All four launch-relevant gaps and all four smaller fixes are
implemented with regressions. Full CPU suite: **916 passed under
`-W error`, TRUE process exit 0** (913 + 3 net new). No GPU work has
run; per 197_s the previous commit was neither smoked nor locked.

## 1. The launch lock is enforced at the consuming boundary (finding 1)

`run_b_diagnostic` now refuses to sample retained support unless a
committed launch-lock JSON exists and validates. The lock
(`build_launch_lock` → `plans/conductor/b_diagnostic_launch_lock.json`)
is self-hashed and binds: the PERSISTED smoke record's byte hash and
path; the four executable identities (`source_digest`,
`contract_sha256`, `generation_config_sha256`,
`model_revision`/`tokenizer_revision` via
`current_executable_identity()`); and the canonical seed-registry
digest. It can only be BUILT from a complete smoke record whose
identities equal the current executable (smoked == locked), and
`validate_launch_lock` re-derives the current identities at run time
(locked == launched), re-reads the smoke record bytes, and checks
the registry digest — a post-smoke executable change, a tampered
lock (even rehashed), or a modified smoke record all refuse
(tested). The smoke now PERSISTS its record atomically
(`b_diagnostic_smoke_record.json`, abort included) so the lock has
real bytes to bind.

## 2. Provenance claims are independently verified (finding 2)

`verify_b_diagnostic_evidence` now re-derives all three:
`stage1_source_sha256` must equal the VALIDATED environment
manifest's source identity; `generation_config_sha256` is recomputed
from the frozen kwargs; `chat_template_sha256` is recomputed from
the pinned loader's tokenizer (a loader without a chat template
refuses — fail closed). The reviewer's exact attack — change each
field and rehash the manifest — is now a three-way refusal test.

## 3. The report carries the signed outputs (finding 3)

Per-row: full reward-level frequencies (`reward_rate_0/0.5/1`) and
the complete sparse `assignment_rates` distribution. Report-level:
`support_composition` (18 observations; 3 pair observations of
which 2 distinct — 1 w2-favoured, 1 w3-favoured — and 1 tie in the
test fixture; the real support's 9/3/2/1/6 composition will print
itself) and explicit `populations` row/observation denominators.
Every aggregate metric now exposes the renderer→latent→cell
structure: `{"equal_cell": …, "per_cell": {…}}` via
`_aggregate_detail` (the equal-cell value equals the frozen
`sr._aggregate` by construction; pinned by test against `g8`).

## 4. Mid-block aborts preserve every completion (finding 4)

The driver's exception path atomically persists the CURRENT
in-memory raw map (temp + `os.replace`) before writing the aborted
record — the regression kills the generator 100 draws into a block
with no completed-block callback and asserts all 100 completions
land in `raw_completions_partial.json`.

## 5. Smaller fixes

- Non-UTF-8 completions count as non-parseable/reward-zero instead
  of aborting; raw persistence uses `ensure_ascii=True` so
  surrogate-bearing text round-trips (tested with a lone surrogate).
- Abort archives validate the run record's TERMINAL status and the
  present files: `run_status` and `files_present` travel in the
  evidence manifest, a non-terminal status is recorded as a
  validation error (abort) or refused (success) — tested.
- The smoke records `tokenizer_revision` and the per-prompt
  `prompt_input_ids_shapes` explicitly.
- The smoke loads ONLY the tokenizer (`_load_smoke_tokenizer`) —
  the retained-support surface is no longer touched by the synthetic
  smoke, so it runs on checkouts without `runs/stage0-support`.

## 6. Identity

Candidate source digest after this repair (input to the 195_f §3
step-3 freeze once the changed-lines review passes):
`84623e3c585e983db0a08223434c3e68c4ade27d1ba93ad42c1dc23912dae686`
Awaiting the narrow changed-lines review; then freeze → smoke →
launch lock → diagnostic.
