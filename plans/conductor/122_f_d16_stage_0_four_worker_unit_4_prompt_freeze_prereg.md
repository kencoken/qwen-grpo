# Unit 4 rev2 — prompt-freeze preregistration (121_s lock sequence)

Registered by Ken's in-session direction (2026-07-23) adopting the
121_s findings and the reviewer's addendum on probe procedure,
counterbalancing and OOD framing. This document is committed BEFORE
any GPU execution of the demo check or the format probe.

## Corrections implemented (121_s findings 1 and 3)

- The smoke observation is `render.build_observation` — the canonical
  identity- and visibility-checked skeleton (`Resources available`,
  `(resource: …; previous results: …)` notation) — asserted
  byte-for-byte in tests. The four-id instruction lives in the system
  prompt only; the observation skeleton is untouched.
- The launch profile is authoritative: `loss_type` passed explicitly;
  `live_singleton` fails validation closed ("declaring an
  unimplemented mode is fabricated provenance"); the surface pin is
  read from the validated profile everywhere; the Conductor tokenizer
  is revision-pinned via an explicit `processing_class`.
- Pre-launch items: schedule indices on every trace row with online
  frozen-order enforcement in the reward callable; the summarizer
  refuses partial or reordered traces (exactly 288 completions in 36
  ordered groups); the four online metrics stream to W&B from the
  reward callable; surface-lookup and completion counts plus an
  aborted-status artifact persist even on failure; CUDA peak stats
  reset after the canary workers are released; the surface-pin check
  is hermetic (absence and mismatch each refuse with their own
  message).

## The preregistered demonstration candidate set

The reviewer's compact arrangement — every worker exactly twice, Code
order reversed across the Code-bearing demos:

| # | type (01_s) | action | gold | content |
|---|---|---|---|---|
| 1 | direct route | `[0]` | 27 | keyed-record lookup (R-3W6, Mesa.crates) |
| 2 | dependency chain | `[0, 1]` | 28 | lookup Harbor.flags=8 → `3*step_1+4` |
| 3 | independent→final | `[2, 3, 1]` | 19 | `at([8,3,5,9],2)=5`, `at([6,2,7],1)=2` → `step_1*step_2+9` |
| 4 | specialist→check | `[3, 2]` | 6 | `count_gt(stable_unique([7,1,7,5,2,5]),4)=2` → `at([4,9,6,3],step_1)=6` |

**Recorded interpretation:** "specialist→check" is a semantic role
pattern over the legal `[none, all]` chain, not a fourth v0 graph; the
executable check is a dependent read (the entry at the specialist's
count) — a transform of the first result, not a verification operator.

**Exchangeability statement (121_s standard):** both Code workers
execute both Code-bearing demos (the check runs assigned AND
Code-swapped variants, so 2 and 3 each execute every Code node in full
workflow context); this assignment is fixed here, before any probing;
no task-relevant feature — operation, index regime, wording, access
pattern or difficulty — is intentionally varied with worker id.

**OOD framing:** new synthetic problems, resources, entities and
payloads (no generator namespace or `worker_dev` content); the
endpoint-compatible task shapes and worker-tested `R-*` /
"zero-based index … requested resource" language are deliberately
reused — demonstrations establish legal capabilities, not linguistic
generalization.

## Demo-check procedure (bounded, preregistered)

- Verification through the exact canonical observation, the frozen
  `task_last` request contract, InstanceRegistry resource
  serialization and the whole-workflow four-worker executor
  (`execute_batch`), terminal-vs-gold.
- Six executions: four assigned + two Code-swapped variants.
- Budget counted in **unique rendered request bytes** (reported by the
  command from runtime telemetry), never cache-backed reruns.
- At most ONE batched repair round per failing demo type; repairs
  address executability only — never routing performance against the
  Stage-0 payoff surface, which the check does not load.
- Every failed candidate and adjustment is disclosed; a second failure
  of the same demo type returns to review.

## Reward-blind format probe (preregistered)

- One group of eight sampled completions per unique observation
  (18×8 = 144), smoke tokenizer/temperature/cap/seed (pinned-revision
  tokenizer, T=1.0, cap 128, seed 0).
- The probe process does not load the payoff surface and reports ONLY:
  valid JSON/schema rate and correct action-array-length rate, by
  topology. Worker choices are neither inspected nor reported.
- Catastrophic-stop rule: the existing ≥80% per-topology validity
  threshold. At most one schema-only repair; no tuning toward 100%.
- **Freeze immediately after a passing probe**: the `freeze` command
  records literal digests — system prompt, all 18 rendered
  observations, pinned chat-template bytes, launch profile, support
  declaration, executable commit — into a committed fixture that
  `run` verifies byte-for-byte, together with the named review record
  (`121_s` + its addendum). Then the canary and the reward-bearing
  smoke run exactly once.

## Recorded from 121_s verification

Positive evidence carried forward: single 0/0.5/1 reward and abort
path correct; no format reward; conversion correct; surface verifies;
36 groups over 18 updates realized under locked TRL; no payload or
model-identity leakage; trainer construction 7.62 s / 2.77 GiB
baseline / 29.9M trainable LoRA parameters. Also recorded: the
pre-existing `sentencepiece` teardown crash — all test bodies pass on
`picome` but the process exits 139; present at the unit-3 base, not a
unit-4 regression (not reproduced on the local box).
