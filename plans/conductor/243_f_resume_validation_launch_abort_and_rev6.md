# 243_f — Step-5 LAUNCH → ABORT (real finding), diagnosis, and freeze REV6

Ken authorized lock-and-launch (2026-07-28). The tranche launched
under the reviewed rev5 identities, ran all three arms on the GPU —
and **ABORTED at the final §11.5 comparison, exactly as designed**,
surfacing a real infrastructure defect the contract exists to catch.
Everything terminal is recorded; the fix is one line; the tranche
awaits a changed-lines pass on this rev6 before relaunch.

## 1. The launch and the abort (all ledger-recorded)

- Pre-admission validation passed: freeze `1f7bd776…`, identity
  `2f15ea86…`, attested environment `372f958f…` all matched; session
  preflight 24,079 MiB free ≥ 20,000; prelaunch evidence persisted;
  admitted as launch `36ac27c6…` against head `264066e6…`.
- Phase A (uninterrupted, 6 updates) and phase B (fault-injected at
  update 4, bundle at 3) completed; gates 1–4 passed (identical
  checkpoint-zero adapters; identical checkpoint-3 bundles and
  trace prefixes; reward-varying groups present — reward_std 0.23
  at update 1; nonzero adapter update). Phase C resumed through the
  fully validated bundle + HF checkpoint and completed updates 4–6.
- **The §11.5 comparison REFUSED**: adapter
  `…lora_A.default.weight` shape/dtype mismatch → ABORTED closeout
  `237d4c21…` with measured cost **0.0224 GPU-h** and the full
  partial-artifact inventory. Envelope: 0.0956 consumed, 59.90
  remaining, nothing open.

## 2. Diagnosis (ledger-recorded engineering smoke, 0.0076 GPU-h)

A lightweight-frozen smoke (launch + complete closeout in the
ledger; findings at
`runs/routing-dev/smoke-dtype-1/findings.json`) compared the live
LoRA state signatures of a fresh trainer vs a checkpoint-resumed
trainer: **all 504 LoRA tensors differ ONLY in dtype — fresh
construction initializes adapters in bfloat16 under the bf16 base,
while HF `resume_from_checkpoint` → PEFT `load_adapter` restores
them in float32.** The resumed run was computing its adapter math in
a different precision than the run it must be indistinguishable
from; the frozen exact tolerance refused correctly. (The persisted
bundle and HF adapter FILES are both bf16 and identical — the
divergence exists only in the live resumed model.)

## 3. The fix (rev6)

`_build_trainer` now pins every LoRA parameter to float32
immediately after construction — before the optimizer exists — so
the fresh-init and checkpoint-load paths land in ONE precision (the
standard k-bit fine-tuning setup; fp32 adapters over the NF4 base).
Both arms therefore train, save, and resume in fp32 adapters;
nothing else changes. The comparison mismatch message now states the
actual shapes/dtypes (the abort message had to be rediagnosed on the
GPU; regression added).

Full CPU suite: **975 passed under `-W error`, TRUE exit 0.**

## 4. Config change with this rev6

The tranche and run root move to `…-v4` (`routing-dev-resume-
validation-v4`, `runs/routing-dev/resume-validation-v4`): the
aborted v3 root is immutable evidence bound by the aborted
closeout's inventory, and the run root is a frozen config literal —
so the config and freeze hashes move with it.

## 5. REV6 identities (FULL — the relaunch arguments)

- Config:
  `0114eb3a0968424b195537b9d32d5e78f8fd0ba09989a713cdccba1580ddcc0e`
- Freeze:
  `010a0d47dc9309c835d9621149c8379d6be34fcc4ece2a18e82f443aee9d5752`
- Static execution-identity manifest:
  `49fe8b3a8ad5d43fdbca371689acfef966c20c2b8ace88e927376cc8bff7bdef`
- Attested environment (unchanged):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head at relaunch (the dtype-smoke's complete closeout):
  `943b9d7ce8c7ebcd908101489a8f0a866ccc575c8538f727d633415e918ca212`

## 6. Next

The 241_s-style changed-lines pass on this rev6 (the fix is one
cast plus one message; the launch path was already reviewed), then
relaunch with the §5 hashes, close-out, and the unchanged
grouped-probe freeze (step 6).
