"""371_f — the reward-blind P0 lifecycle probe (369_s/rev5
sign-off directive). PROBE SCALE: 2 trainer rows, max_steps = 2,
cadence [0, 1, 2]; evaluation over the FIRST SIX observations of
the ALREADY-EXPOSED smoke timing cohort (never the val cohort —
no outcome reveal before P0's real checkpoint zero). Reward-blind:
traces are sealed and no reward/semantic value is printed. No
ledger interaction; the real run roots are untouched.

Flow (the sign-off list): construction + FP32/key assertion →
scheduler lifecycle (`_prepare_training_objects`) → checkpoint
ZERO save + restoration → train() with the forced HF cadence
save at update 1 (bundle bound + verified) → post-train
scheduler identity AND state → interruption INJECTED BEFORE the
final cadence event (the realistic crash window) → session-2
one-step resume from the verified HF checkpoint → the final
cadence event from the RESUMED trainer → finalize-only
preconditions (complete cadence records + valid session chain;
the GPU-free finalize path itself is CPU-tested).

PREREGISTERED PASS CRITERIA: every stage prints PASS; total
probe cost <= 0.2 GPU-h; resumed counters == 2/2/2/16; resumed
scheduler last_epoch == 2; trainer ends at step 2 both sessions.
"""
import json
import os
import sys
import time

os.chdir("/home/ken/qwen-grpo")
sys.path.insert(0, "/home/ken/qwen-grpo")

from pathlib import Path

PROBE_ROOT = Path("runs/routing-dev/p0-lifecycle-probe-v1")


def main() -> None:
    from tasks.routing import checkpoint as ckpt
    from tasks.routing import dev_support, p0_execution, p0_smoke
    from tasks.routing.p0_contract import load_p0_science_contract
    from tasks.routing.p0_replay import (
        restore_extension_surface_if_absent,
    )
    from tasks.routing.p0_schedule import build_trainer_rows
    from tasks.routing.resume_validation import (
        _release_trainer,
        gpu_session_preflight,
        make_validation_reward,
        tensor_state_hashes,
        verify_hf_checkpoint_against_bundle,
    )
    from tasks.routing.unit_c2_sample import UNIT_C2_CONFIG

    started = time.monotonic()
    stages: dict[str, str] = {}
    if PROBE_ROOT.exists():
        raise SystemExit(f"{PROBE_ROOT} exists — probe runs once")
    run_dir = PROBE_ROOT
    (run_dir / "sealed").mkdir(parents=True)
    gpu_session_preflight()

    contract = load_p0_science_contract()
    rows = build_trainer_rows(contract, 1)[:2]
    loaded = dev_support.load_dev_surface(
        restore_extension_surface_if_absent(),
        expected_lock_sha256=UNIT_C2_CONFIG[
            "extension_surface_lock_sha256"])
    identity = p0_execution.load_p0_execution_identity(
        expected_sha256=p0_execution.P0_EXECUTION_IDENTITY_SHA256)
    sampling = identity["evaluation"]["sampling"]
    observations = p0_smoke.timing_cohort_observations()[:6]
    seeds = dict(p0_smoke.executed_seed_realization())
    eval_context = {
        "surface": loaded["surface"], "seeds": seeds,
        "observations": observations, "sampling": sampling}
    identities = {
        "routing_source_sha256": "ab" * 32,
        "environment_manifest_sha256": "cd" * 32,
        "config_sha256": p0_execution.P0_LAUNCH_FREEZE_SHA256,
        "surface_manifest_sha256":
            loaded["lock"]["manifest_sha256"],
        "worker_pool_fingerprint":
            loaded["lock"]["worker_pool_fingerprint"],
        "cache_identity": loaded["lock"]["cache_identity"],
        "seed": str(p0_execution.P0_TRAINING_SEED),
        "training_cohort_sha256": "12" * 32,
        "renderer_schedule_sha256": "34" * 32,
        "prompt_sha256": "56" * 32,
    }
    deadline = time.monotonic() + 3600.0

    # --- session 1: fresh --------------------------------------
    p0_execution._append_session_entry(run_dir, {
        "kind": "session_start", "session_index": 1,
        "mode": "fresh", "start_group_index": 0,
        "resume_update_index": None,
        "wall_start_utc": time.time()})
    accountant = ckpt.GroupAccountant()
    instrumentation = p0_smoke._EpochInstrumentation()
    trace1 = run_dir / "sealed" / "training_trace_s1.jsonl"
    base_reward = make_validation_reward(
        loaded["surface"], accountant, trace1, 8,
        start_group_index=0)
    reward = p0_smoke._make_smoke_reward(
        base_reward, instrumentation, deadline)
    context = {
        "run_dir": run_dir, "deadline": deadline,
        "accountant": accountant,
        "instrumentation": instrumentation,
        "identities": identities, "eval_context": eval_context,
        "last_checkpoint_sha256": None,
    }
    callback = p0_execution._make_p0_callback(context, [0, 1, 2])
    trainer = p0_execution._build_p0_trainer(
        rows, reward, run_dir, p0_execution.P0_TRAINING_SEED,
        max_steps=2, extra_callbacks=(callback,))
    context["trainer"] = trainer
    p0_smoke._strip_console_callbacks(trainer)
    p0_execution._cast_and_assert_lora(trainer)
    stages["construction_and_lora"] = "PASS"

    pre_opt, pre_sched = p0_execution._prepare_training_objects(
        trainer, 2)
    if trainer._created_lr_scheduler is not False:
        raise SystemExit("scheduler not marked user-provided")
    stages["training_objects_created"] = "PASS"

    # checkpoint ZERO save + restoration
    p0_execution._p0_cadence_event(context, 0, None)
    bundle0 = run_dir / "checkpoint_bundle_upd0"
    record0 = json.loads(
        (bundle0 / "checkpoint_record.json").read_text("utf-8"))
    ckpt.validate_resume(record0, identities, bundle_dir=bundle0)
    from safetensors.torch import load_file
    restored = load_file(str(bundle0 / "adapter.safetensors"))
    live = {k: v.detach().to("cpu")
            for k, v in trainer.model.state_dict().items()
            if "lora" in k}
    if tensor_state_hashes(restored) != tensor_state_hashes(live):
        raise SystemExit(
            "checkpoint-zero adapter does not restore to the "
            "live state")
    stages["checkpoint_zero_save_restore"] = "PASS"

    # train: the forced HF cadence save fires at update 1
    instrumentation.start_epoch()
    trainer.train()
    if int(trainer.state.global_step) != 2:
        raise SystemExit(
            f"trainer ended at {trainer.state.global_step} != 2")
    if p0_execution._unwrap_optimizer(trainer.optimizer) \
            is not p0_execution._unwrap_optimizer(pre_opt) \
            or p0_execution._unwrap_scheduler(
                trainer.lr_scheduler) \
            is not p0_execution._unwrap_scheduler(pre_sched):
        raise SystemExit("train() replaced optimizer/scheduler")
    sched_state = p0_execution._unwrap_scheduler(
        trainer.lr_scheduler).state_dict()
    if sched_state.get("last_epoch") != 2:
        raise SystemExit(
            f"scheduler last_epoch "
            f"{sched_state.get('last_epoch')} != 2")
    stages["scheduler_identity_and_state"] = "PASS"
    bundle1 = run_dir / "checkpoint_bundle_upd1"
    record1 = json.loads(
        (bundle1 / "checkpoint_record.json").read_text("utf-8"))
    hf1 = run_dir / "checkpoint-1"
    verify_hf_checkpoint_against_bundle(bundle1, hf1, record1)
    stages["forced_hf_cadence_save_verified"] = "PASS"

    # INTERRUPTION injected BEFORE the final cadence event — the
    # realistic crash window; seal + close session 1
    p0_execution._record_resumable_interruption(
        run_dir, 1, time.monotonic() - started,
        RuntimeError("probe-injected interruption"))
    stages["interruption_recorded_sealed"] = "PASS"
    holder = {"trainer": trainer}
    del trainer, context["trainer"]
    _release_trainer(holder)

    # --- session 2: the one-step resume ------------------------
    p0_execution._append_session_entry(run_dir, {
        "kind": "session_start", "session_index": 2,
        "mode": "resume", "start_group_index": 1,
        "resume_update_index": 1,
        "wall_start_utc": time.time()})
    session2_started = time.monotonic()
    accountant2 = ckpt.GroupAccountant.restore(
        record1["counters"])
    instrumentation2 = p0_smoke._EpochInstrumentation()
    trace2 = run_dir / "sealed" / "training_trace_s2.jsonl"
    base_reward2 = make_validation_reward(
        loaded["surface"], accountant2, trace2, 8,
        start_group_index=1)
    reward2 = p0_smoke._make_smoke_reward(
        base_reward2, instrumentation2, deadline)
    context2 = {
        "run_dir": run_dir, "deadline": deadline,
        "accountant": accountant2,
        "instrumentation": instrumentation2,
        "identities": identities, "eval_context": eval_context,
        "last_checkpoint_sha256": record1["checkpoint_sha256"],
    }
    callback2 = p0_execution._make_p0_callback(
        context2, [0, 1, 2], already_completed=(1,))
    trainer2 = p0_execution._build_p0_trainer(
        rows, reward2, run_dir, p0_execution.P0_TRAINING_SEED,
        max_steps=2, extra_callbacks=(callback2,))
    context2["trainer"] = trainer2
    p0_smoke._strip_console_callbacks(trainer2)
    p0_execution._cast_and_assert_lora(trainer2)
    p0_execution._prepare_training_objects(trainer2, 2)
    ckpt.validate_resume(record1, identities, bundle_dir=bundle1)
    verify_hf_checkpoint_against_bundle(bundle1, hf1, record1)
    instrumentation2.start_epoch()
    trainer2.train(resume_from_checkpoint=str(hf1))
    if int(trainer2.state.global_step) != 2:
        raise SystemExit(
            f"resume ended at {trainer2.state.global_step} != 2")
    if accountant2.counters() != {"generated_groups": 2,
                                  "consumed_groups": 2,
                                  "optimizer_updates": 2,
                                  "sampled_completions": 16}:
        raise SystemExit(
            f"resume counters diverge: {accountant2.counters()}")
    sched2 = p0_execution._unwrap_scheduler(
        trainer2.lr_scheduler).state_dict()
    if sched2.get("last_epoch") != 2:
        raise SystemExit(
            f"resumed scheduler last_epoch "
            f"{sched2.get('last_epoch')} != 2")
    # the FINAL cadence event from the RESUMED trainer
    p0_execution._p0_cadence_event(context2, 2, None)
    stages["one_step_resume_and_final_cadence"] = "PASS"

    # finalize-only preconditions: complete records, valid chain
    records = p0_execution._load_cadence_records(
        run_dir, [0, 1, 2])
    if set(records) != {"0", "1", "2"}:
        raise SystemExit(
            f"cadence records incomplete: {sorted(records)}")
    p0_execution._append_session_entry(run_dir, {
        "kind": "session_end", "session_index": 2,
        "elapsed_seconds": time.monotonic() - session2_started,
        "status": "interrupted"})
    state = p0_execution._session_state(run_dir)
    if state["unclosed_session_index"] is not None:
        raise SystemExit("session chain left unclosed")
    stages["finalize_preconditions"] = "PASS"

    p0_execution._sanitize_after_crash(run_dir)
    elapsed = time.monotonic() - started
    report = {
        "stages": stages,
        "elapsed_seconds": round(elapsed, 1),
        "gpu_hours": round(elapsed / 3600.0, 4),
        "cumulative_session_elapsed_seconds":
            round(state["cumulative_elapsed_seconds"], 1),
        "reward_blind": True,
        "cohort": "smoke timing cohort (already exposed), first 6",
    }
    (run_dir / "probe_report.json").write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    print("=== PROBE COMPLETE ===")
    print(json.dumps(report, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
