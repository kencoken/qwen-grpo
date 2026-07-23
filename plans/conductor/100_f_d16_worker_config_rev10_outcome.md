# 100_f — rev10 follow-up outcome (99_f protocol)

**Executed 2026-07-22 at the follow-up's executable commit `6b87a6c`,**
clean worktree, every command artifact + exit 0. P1: three fresh
processes, **ADMITTED** (bit-stable, within the cost gate). Full
900-case crossed run completed and strictly loaded.

## Preregistered evaluation

| endpoint | Tranche A `task_last` sentinel (rev9) | rev10 |
|---|---:|---:|
| Lookup | 270/270 | 270/270 (byte-identical) |
| Math | 330/360 (**0/30** on `math_code`×`bound_var`) | **360/360** |
| Code | 257/270 | 257/270 (byte-identical) |
| **total** | 857/900 | **887/900** |

1. **The treatment worked completely.** `math|math_code|bound_var`:
   0/30 → **30/30**. Every Math group is now perfect (360/360) with
   zero Math protocol failures. No Math stratum regressed.
2. **The regression guard held exactly.** All 540 Lookup and Code
   generation records are **byte-identical** to the Tranche A sentinel
   — the amendment provably touched only what it targeted, at the byte
   level, courtesy of admitted singleton generation.
3. **The §4.1 target is NOT reached**, so per the 99_f one-revision
   stop rule this follow-up stops here — no further prompt edits under
   this document. The entire remaining distance is the pre-existing
   Code residual (13/270, unchanged bytes from Tranche A).

## The remaining gap, characterized

All 13 Code failures are **protocol-class** (11 `E_PARSE`,
2 `E_NO_ARTIFACT`); zero are legal-but-wrong. Three legible modes:

- **`math_code`×`goal_first` (5)**: `at(resource, (a * b + c) % m)` —
  the model computes the Math step itself instead of using `step_1`
  (arithmetic is outside the Code whitelist → `E_PARSE`). The 78_s
  local-task violation, surviving at 5/30 under `task_last` (down from
  30/30-scale collapse under `current`).
- **`code_atomic`×`goal_first` (4) + `fork_join`×`resource_first`
  (2)**: invented nesting `…stable_unique(at(resource, k))…` —
  `at` returns an integer, not a sequence.
- **`fork_join`×`bound_var` (2)**: malformed envelope
  (`<count_gt(…)</count_gt>` — tag confusion, `E_NO_ARTIFACT`).

## Consequences for the next decision (Ken + reviewer)

- **The 98_f shared-contract blocker is resolved.** With rev10 Math,
  the `task_last` contract has perfect unchanged Lookup/Math — the
  contract is viable in `92_s` §5 terms; the residual question is
  Code-endpoint-only.
- **Math and Lookup are at their endpoint targets** under
  `generic_1p5b` / `task_last` / rev10 — candidates for ratification
  in the eventual decision record.
- The natural next preregistration is a bounded Code follow-up under
  the now-viable anchor: a rev11 Code amendment targeting the three
  identified modes, and/or re-crossing `coder_1p5b` vs `generic_1p5b`
  under `task_last` + rev10-Math (Tranche A's model contrasts were
  measured under the rev9 Math confound). 887/900 with a fully
  characterized, protocol-class-only residual is the starting position.
