# 281_f — Unit C REV4 (response to 280_s)

The final sizing correction and the exact adapter-key binding
applied; identities regenerated. Full CPU suite: **1002 passed
under `-W error`, TRUE exit 0**.

## 1. P1 — the cap charges everything the charter charges

The frozen `cap_formula` now allocates generation time from what
REMAINS of the ten-hour operational ceiling, never the whole of it:

```
available_generation_seconds =
    operational_ceiling_seconds
    − cumulative_consumed_seconds          (engineering resumes etc.)
    − measured_finalization_reserve_seconds
    − frozen_non_rollout_overhead_seconds  (eval/checkpoint/trace/archive)

capped_epochs = floor(available_generation_seconds
                      / measured_whole_epoch_seconds)
```

`capped_epochs ≤ 0` → stop for a reviewed scope amendment. The
capped run is EXPLICITLY UNDER-TARGET: claims are based on achieved
projected/observed exposure (capped_epochs × measured rate,
disclosed), never the nominal 100-group target. The formula is
executable (`derive_p0_cap`) and integer-tested (a worked example
with consumed/reserve/overhead deductions → 52 epochs; an
exhausted ceiling → capped 0, stop=True). The later smokes supply
`measured_whole_epoch_seconds` and
`measured_finalization_reserve_seconds` as NUMBERS ONLY — the
formula and branch semantics are frozen here.

## 2. P2 — the complete LoRA key set is bound

The config freezes the validated construction's adapter key set —
**504 keys, sorted-key-set digest `e44ecb9c…`** (reproduced exactly
from the committed Step-6 checkpoint-zero map via
`content_sha256(sorted keys)`, regression-checked against that
evidence). The verifier requires BOTH persisted maps to carry
exactly this key set (count + digest) before the zero-mutation
comparison: `{}`, a one-key `lora` map, and any partial/foreign
set all refuse ("not the validated 504-key LoRA set"). The
lifecycle test now builds its synthetic maps over the real 504
keys, and the final-map-mismatch tamper mutates a VALUE within the
full key set so it exercises the equality gate itself.

## 3. Frozen identities (regenerated)

- Config:
  `69f73a5811922bea3ef6d04a891817bec13e30729b1741f4500f2f1f2bb02d59`
- Freeze:
  `c90560ddecc271a41affc13cc0b4c0598b0178063c05d301a45ceb5def7052f1`
- Static execution-identity manifest:
  `6fa701a29cbb7ae3de53d9f0ba8c22bdf8989fda6efa833febcade3a608daac8`
- Attested environment (unchanged host):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head (unchanged anchor):
  `b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd`
- Inputs unchanged: mixture `0100df2b…`, extension lock
  `ccb1c3e2…`, comparator `9220c2c7…`, ceiling 1.25 GPU-h, seed
  20260801.

Launch: `execute_unit_c(expected_freeze_sha256=…c90560dd,
expected_identity_sha256=…6fa701a2,
expected_environment_sha256=…372f958f,
expected_head_sha256=…b88eba02)`.

## 4. Next

Mechanical hash/test check (280_s closing) → launch OK → GPU run
with the §3 hashes → closeout + exposure-report review → the
preregistered decision → val/cycle/`R_cycle` → beta smoke → P0
freeze (sizing + cap formula executed; audit repeated) →
checkpoint-zero eval → P0.
