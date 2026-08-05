# 371_f — Reward-blind P0 lifecycle probe: EXECUTED, all stages PASS

The rev5-sign-off-directed probe ran to completion on attempt 2.
**All eight stages PASS; 0.0168 GPU-h measured (preregistered
ceiling 0.2); every preregistered criterion met.** The console
was verified reward-blind (the only occurrence of "reward" in
the entire log is the report's own `"reward_blind": true`
field). No ledger interaction; the real run roots untouched;
ledger head unchanged at `df4bf7ad…` (22 entries) — so the
frozen `P0_LINEAGE_PARENT_SHA256` binds the ACTUAL post-probe
launch head, per the sign-off note.

## 1. The report (verbatim)

```json
{
 "cohort": "smoke timing cohort (already exposed), first 6",
 "cumulative_session_elapsed_seconds": 60.3,
 "elapsed_seconds": 60.6,
 "gpu_hours": 0.0168,
 "reward_blind": true,
 "stages": {
  "checkpoint_zero_save_restore": "PASS",
  "construction_and_lora": "PASS",
  "finalize_preconditions": "PASS",
  "forced_hf_cadence_save_verified": "PASS",
  "interruption_recorded_sealed": "PASS",
  "one_step_resume_and_final_cadence": "PASS",
  "scheduler_identity_and_state": "PASS",
  "training_objects_created": "PASS"
 }
}
```

Covered exactly the sign-off list: the scheduler lifecycle
(created via the Trainer API, marked user-provided, and PROVEN
identical after `train()` with `last_epoch == 2`); checkpoint
zero saved through the P0 saver and RESTORED (adapter tensor
hashes equal); the forced HF cadence save at update 1 with
`verify_hf_checkpoint_against_bundle` PASS; the interruption
injected BEFORE the final cadence event (the realistic crash
window), sealed and chained; the session-2 one-step resume from
the verified HF checkpoint (`resume_from_checkpoint`) reaching
step 2 with counters exactly 2/2/2/16 and performing the final
cadence event; and the finalize-only preconditions (complete
contiguous cadence records + a fully closed session chain).

## 2. Disclosures

- **Attempt 1 failed on a probe-SCRIPT defect** (committed as
  `695793d`): the final assertion called a nonexistent
  `GroupAccountant.counters()` method — every GPU stage through
  the one-step resume had already passed. Evidence archived at
  `runs/routing-dev/p0-lifecycle-probe-v1-failed-attempt1/`;
  attempt 2 ran the corrected script from a fresh root.
  Total probe GPU across both attempts ≈ 0.03 GPU-h.
- The HF save step writes a `README.md` (PEFT model card) into
  the trainer output directory. Harmless; in the real run it is
  simply part of the closeout's terminal hash map. Noted so the
  prelaunch reviewer is not surprised by it.
- Probe evidence retained (gitignored):
  `runs/routing-dev/p0-lifecycle-probe-v1/` — sealed traces,
  three validated bundles, the HF checkpoint, the session chain,
  and `probe_report.json`.

## 3. Next

Per the rev5 sign-off: directly to the narrow
real-manifest/prelaunch review (372_f) — no further open-ended
CPU audit.
