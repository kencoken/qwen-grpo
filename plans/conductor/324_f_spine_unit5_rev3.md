# 324_f — Spine Unit 5 REV3 (response to 323_s)

Both points repaired plus the stale header. Full suite: **1023
passed under `-W error`, TRUE exit 0**. The appendix regenerated
through the generator (12,819 bytes); contract/projection/mixture
identities untouched.

## 1. The runtime profile now implements its declared warmup

- `scheduler` is now **`constant_with_warmup`** — the signed
  Stage-0 implementation (`grpo_smoke.STAGE0C_LAUNCH_PROFILE`)
  realized "10-step warmup, constant schedule" as exactly this
  variant; plain `"constant"` ignores `warmup_steps`, as the
  reviewer verified. `_validated_profile` moves the scheduler OUT
  of the C2 construction-equality set (the C2 zero-update run
  correctly used plain constant with zero warmup) and INTO the
  training-delta assertion (beta 1e-3, lr 1e-5, warmup 10,
  `constant_with_warmup`).
- The 2×4 batch shape at one group per optimizer update is now
  cited as CONTROLLED by the 246_f resume-validation execution
  (which validated real optimizer updates in exactly that shape) —
  in the profile comment.
- The previously hard-coded trainer settings are PINNED in a new
  `trainer_settings` section and asserted at every binding:
  `shuffle_dataset=False`, `gradient_checkpointing=True` with
  `{"use_reentrant": False}`, `model_dtype=bfloat16`,
  `attn_implementation=sdpa` — the exact literals of the signed
  trainer builders.
- New profile pin: **`202bc3773f9f4d4fa4ccc1842c17199aabd8d8f5c5`
  `32bda7826c7af53fa08ceb`** (kind unchanged; the profile was
  introduced in rev2 of THIS unit and amended pre-signature).

## 2. Sentinel assembly enforces the producer invariants

All four reproductions are permanent regressions:

- **selections == completions**: `worker1_selections` differing
  from `worker1_completions` refuses (the producer emits them
  identically);
- **the frozen group size**: `completion_denominator` must equal
  `group_denominator × G` with G=8 taken from the validated
  canonical profile — a block built from 7-completion groups
  refuses;
- **the two index spaces are bound**: for every set first index,
  `first_update_index == first_group_index × updates_per_group`
  (updates-per-group from the profile, = 1) — group 3 / update
  999 refuses;
- **checkpoint zero PLUS a positive final**: the expected sets
  must have length ≥ 2 beginning at 0 — `(0,)` refuses.

**Abort semantics corrected**: each stream must be a PREFIX of
its expected set (possibly complete — the abort may fall between
streams), and globally at least one stream must be a STRICT
prefix; both-streams-complete refuses as "not an abort". The
regression covers the reviewer's case: checkpoints complete +
evaluations truncated is now a valid disclosed abort, with the
truncation record showing 3/3 and 1/2.

The expected index sets remain deferred and are now named to
their binding home: **the authenticated `P0ExecutionIdentity`**
(also the home for the deferred cadence/evaluation/telemetry
configuration) — updated in the docstring and both appendix rows.

## 3. The stale module header

The `p0_launch.py` docstring now describes `prepare_p0_dataset`
(dataset preparation, never admission), the runtime binding, and
the explicit deferral to the post-merge `P0ExecutionIdentity`.

## 4. Scope of change

`p0_launch.py`, `p0_tables.py` (two matrix-row texts), the
regenerated appendix, `test_routing_dev.py`. No frozen artifact
touched; identities unchanged; the equivalence oracle PASS 25/25.

## 5. Next

Merge sign-off (per 323_s: this narrow rev3 should be sufficient)
→ the MERGE GATE → post-merge sequence.
