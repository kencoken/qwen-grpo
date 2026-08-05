"""P0 precursors, Unit T — the beta timing smoke (the SIGNED
precursors plan: 328_f §2 isolation; 328_f §3 + 330_f §2 the
frozen cadence and the executable measurement→cap-input mapping;
330_f §5 disclosure limits and abort/retry; repaired per 348_s).

ONE bounded GPU run (<= 0.75 GPU-h) measuring the cap-formula
inputs under the REAL P0 training shape. The run is a sequence of
DISJOINT phases (348_s #2), in production order:

  P1 startup      — process start to READY (model + pool + data
                    loaded; before any rollout or evaluation)
  P2 ckpt-0 eval  — one COMPLETE evaluation pass (generation +
                    parse/score + telemetry + sealed trace)
  P3 epoch        — 157 rollout+update groups (the only training)
  P4 ckpt bundle  — one COMPLETE RESUMABLE checkpoint bundle
                    (adapter + optimizer + scheduler + RNG)
  P5 post eval    — the second complete evaluation pass
  P6 trace seal   — flush + verify + deterministic-gzip archival

Each phase is bounded by explicit markers; no interval overlaps
another. TWO evaluation passes are measured and the CONSERVATIVE
MAXIMUM prices every scheduled evaluation (348_s #1). The trained
state is DISCARDED after the adapter-changed verification.
Disclosure before the P0 freeze is TIMING/MEMORY/INFRASTRUCTURE
ONLY, operationally enforced (348_s #4): report_to none, no
completion printing, trainer logs and semantic traces SEALED
(persisted + hashed, never surfaced).

The freeze is a PERSISTED, strictly loaded identity boundary
(`plans/conductor/p0/beta_smoke_freeze.json`): full hashes for
the contract, the pinned mixture (record + file), the actual
prompt, the extension surface lock, the runtime profile, and the
frozen timing-evaluation seed schedule."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from tasks.conductor.types import (
    RENDERER_IDS,
    InfrastructureError,
)

from . import dev_support
from .charter import content_sha256
from .p0_launch import P0_RUNTIME_PROFILE_SHA256

SMOKE_RUN_ROOT = "runs/routing-dev/beta-smoke-v1"
SMOKE_FREEZE_PATH = Path("plans/conductor/p0/beta_smoke_freeze.json")

SMOKE_CELLS = ("code_atomic", "fork_join", "lookup_atomic",
               "lookup_math", "math_atomic", "math_code")

# the frozen cadence (328_f §3; 330_f §2), both unit systems
CADENCE_EPOCHS = (0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 39)
CADENCE_UPDATES = tuple(epoch * 157 for epoch in CADENCE_EPOCHS[:-1]
                        ) + (6123,)

# the P0 design learning rate and warmup (the canonical profile)
_PLATEAU_LR = 1e-5
_WARMUP_UPDATES = 10
_LR_REL_TOLERANCE = 1e-6

SMOKE_CONFIG: dict[str, Any] = {
    "tranche": "routing-dev-beta-smoke-v1",
    "question": ("Unit T: the cap-formula inputs measured under "
                 "the REAL P0 training shape — whole-epoch wall, "
                 "the finalization components, and the scheduled "
                 "overhead at the frozen cadence"),
    "runtime_profile_sha256": P0_RUNTIME_PROFILE_SHA256,
    "training": {
        "shape": ("the canonical profile exactly: beta 1e-3, lr "
                  "1e-5, 10-update warmup as constant_with_warmup, "
                  "batch 2x4 = one 157-group epoch = 157 optimizer "
                  "updates, NF4 + fp32 LoRA, the pinned trainer "
                  "settings"),
        "schedule": ("ONE complete epoch of the pinned mixture "
                     "through the STRICT spine loader "
                     "build_trainer_rows(contract, 1), consumed "
                     "under the reviewed contract pin"),
        "seed": 20260806,
        "seed_domain": "timing_smoke",
        "state": ("the trained adapter is VERIFIED to differ from "
                  "checkpoint zero (an infrastructure fact) and "
                  "then DISCARDED; nothing from the smoke seeds "
                  "P0"),
    },
    "timing_cohort": {
        "namespace": "routing_dev",
        "cohort": {cell: [0, 1, 2, 3, 4] for cell in SMOKE_CELLS},
        "renderers": list(RENDERER_IDS),
        "visibility": "private",
        "source": ("the LOCKED extension surface — surfaces "
                   "already materialized; no new exposure; the "
                   "locked routing_dev_val cohort receives NO "
                   "policy output before checkpoint zero"),
        "sampling": ("the frozen canonical sampling identity; "
                     "per-OBSERVATION seeding with the slot-0 CRN "
                     "seed, one 8-sequence batch (the operational "
                     "realization of the per-slot schedule is "
                     "bound at Unit L's P0ExecutionIdentity; the "
                     "smoke measures the identical cost shape); "
                     "outputs discarded unread"),
    },
    "cadence": {
        "rule": ("checkpoint + evaluation every 4 epochs on the "
                 "nominal horizon plus checkpoint zero "
                 "(evaluation-only) and the final epoch; after the "
                 "cap is derived ONCE, out-of-horizon indices are "
                 "TRIMMED (final := the capped epoch) WITHOUT "
                 "reclaiming reserved time"),
        "epochs": list(CADENCE_EPOCHS),
        "updates": list(CADENCE_UPDATES),
        "intermediate_evaluations": 9,
    },
    # 348_s #2: DISJOINT phase intervals, production order; every
    # boundary is an explicit marker
    "phases": {
        "P1_startup": ("process start to READY: model + pool + "
                       "strict-loader dataset + tokenizer loaded; "
                       "ends BEFORE the first evaluation or "
                       "rollout begins"),
        "P2_checkpoint_zero_eval": (
            "one COMPLETE evaluation pass: generation + "
            "parse/score against the locked surface + telemetry + "
            "sealed trace persistence"),
        "P3_epoch": ("the 157 rollout+update groups; first rollout "
                     "start to the 157th optimizer-update end; NO "
                     "evaluation time inside"),
        "P4_checkpoint_bundle": (
            "one COMPLETE RESUMABLE checkpoint bundle write: "
            "adapter + optimizer state + scheduler state + RNG "
            "states (the resume-validation bundle shape), wall"),
        "P5_post_epoch_eval": ("the second complete evaluation "
                               "pass, identical path to P2"),
        "P6_trace_seal": ("training + evaluation trace flush + "
                          "verification + deterministic-gzip "
                          "archival, wall; the per-epoch trace "
                          "volume is recorded"),
        "per_group_rollout_definition": (
            "group i's rollout wall = the reward-function entry "
            "time for group i minus the previous phase boundary "
            "(the (i-1)th optimizer-update end; the P3 start for "
            "i=1) — generation + prompt processing, measured "
            "inside P3; the WORST (maximum) feeds the "
            "finalization reserve"),
    },
    # 348_s #1: two measured passes; the conservative MAXIMUM
    # prices every scheduled evaluation
    "evaluation_pricing": ("eval_price_seconds = max(P2, P5); "
                           "used for checkpoint zero, all 9 "
                           "intermediates, AND the final "
                           "evaluation"),
    "trace_scaling": {
        "rule": ("full_run_trace_seconds = ceil("
                 "trace_flush_archive_seconds x 39 x 1.2) — linear "
                 "in the nominal horizon with a frozen 1.2 "
                 "conservatism multiplier, rounded up to whole "
                 "seconds"),
        "nominal_epochs": 39,
        "conservatism_multiplier": 1.2,
    },
    # 348_s #1: the ceiling covers the measured workload with
    # honest headroom (2 evals ~14 min + epoch 12-16 min + startup
    # + bundle + seal ~ 31-36 min predicted; the 0.75 ceiling
    # keeps an abort from a slow epoch out of the picture)
    "budget_gpu_hours": 0.75,
    "run_root": SMOKE_RUN_ROOT,
    "ledger_kind": "engineering_smoke",
    # 348_s #4: OPERATIONAL disclosure enforcement
    "disclosure_controls": {
        "report_to": "none",
        "completion_printing": "disabled — no completion text is "
                               "ever written to stdout/stderr",
        "trainer_logs": ("captured to sealed files inside the run "
                         "root, hashed into the closeout, never "
                         "surfaced before the P0 freeze"),
        "semantic_traces": ("persisted + hashed (sealed); "
                           "uninspected until after the P0 "
                           "freeze"),
        "surfaced_output": ("ONLY the closed timing record and "
                            "the derived cap-input projection"),
    },
    "predictions": {
        "whole_epoch_minutes": "12-16 (C2: 12.2 at beta 0)",
        "eval_pass_minutes": "~7 each (90 groups x ~4.647 "
                             "s/group)",
        "checkpoint_bundle_write": "seconds-scale",
        "derived_capacity_epochs": ("33-38 — the DISCLOSED "
                                    "under-target branch remains "
                                    "the expected P0 outcome "
                                    "(290_f)"),
        "warmup_ramp": ("lr at the end of update i equals "
                        "1e-5 x i/10 for i=1..10, then the 1e-5 "
                        "plateau (rel tol 1e-6)"),
        "cost_gpu_hours": "0.50-0.65 within the 0.75 ceiling",
    },
    "abort_retry": ("identical-design retries receive a new "
                    "execution identity and cumulative accounting; "
                    "a material change is a reviewed successor "
                    "(330_f §5)"),
    "development_only": True,
    "lineage": {
        "parent_entry_sha256":
            "6fea9e3be1f2043d38c297e50bcce36b9d225ce741d61de3ed3a5"
            "6054e8dba51",
        "outcome_informed": False,
        "motivating_evidence": ("330_f-signed precursors plan Unit "
                                "T; 346_f Unit-Y closure; 348_s"),
    },
}
SMOKE_CONFIG_SHA256 = \
    "70e4be03cc23b382404def3e3813c7696b4b5cfc34e9d6fa8f2b150470f3a110"

# the frozen timing-evaluation seed schedule (90 obs x slots 0..7,
# domain timing_smoke, base 20260806)
TIMING_SEED_SCHEDULE_SHA256 = \
    "cbfe528435882c0728eb79235e9303d85f403de2b7cf1a96cdae99328eb9992b"

# the externally reviewed freeze pin (set after the one-time
# freeze; recorded by the Unit-T review)
SMOKE_FREEZE_SHA256 = \
    "bd499f0376924cc2278df6c11f5a715ee98a6859a1dee4663cbd428fb08fb164"

# the CLOSED measured field set (348_s #3: the shape proofs are
# fields too — infrastructure counters, never semantic values)
MEASUREMENT_FIELDS = frozenset({
    "startup_seconds", "checkpoint_zero_eval_seconds",
    "whole_epoch_seconds", "per_group_generation_seconds",
    "checkpoint_bundle_write_seconds", "post_epoch_eval_seconds",
    "trace_flush_archive_seconds", "per_epoch_trace_bytes",
    "peak_reserved_vram_mib", "warmup_lr_trajectory",
    "optimizer_updates", "reference_kl_logged_events",
    "adapter_state_changed",
})


def _validated_config() -> dict[str, Any]:
    if content_sha256(SMOKE_CONFIG) != SMOKE_CONFIG_SHA256:
        raise InfrastructureError(
            "SMOKE_CONFIG was mutated after import")
    return SMOKE_CONFIG


def timing_cohort_observations() -> list[dict[str, Any]]:
    """The shape-matched, ALREADY-EXPOSED timing cohort — 90
    routing_dev observations whose surfaces live on the LOCKED
    extension surface (asserted)."""
    config = _validated_config()
    spec = config["timing_cohort"]
    observations = dev_support.dev_cohort_observations(
        spec["namespace"], spec["cohort"], spec["renderers"],
        spec["visibility"])
    from .p0_replay import restore_extension_surface_if_absent
    from .unit_c2_sample import UNIT_C2_CONFIG
    loaded = dev_support.load_dev_surface(
        restore_extension_surface_if_absent(),
        expected_lock_sha256=UNIT_C2_CONFIG[
            "extension_surface_lock_sha256"])
    members = {obs["observation_id"]
               for obs in loaded["observations"]}
    missing = [obs["observation_id"] for obs in observations
               if obs["observation_id"] not in members]
    if missing:
        raise InfrastructureError(
            f"timing cohort is not fully on the locked surface: "
            f"{missing[:3]}")
    return observations


def timing_seed_schedule() -> list[tuple[str, int, int]]:
    """The frozen 720-entry timing-evaluation seed schedule
    (domain `timing_smoke`, base 20260806), under its pin."""
    from .p0_val import seed_for_completion
    config = _validated_config()
    schedule = [
        (obs["observation_id"], slot,
         seed_for_completion(
             obs["observation_id"], slot,
             domain=config["training"]["seed_domain"],
             base_seed=config["training"]["seed"]))
        for obs in timing_cohort_observations()
        for slot in range(8)]
    digest = content_sha256([list(entry) for entry in schedule])
    if digest != TIMING_SEED_SCHEDULE_SHA256:
        raise InfrastructureError(
            "the derived timing seed schedule does not match the "
            "frozen pin")
    return schedule


def _positive_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or value <= 0:
        raise InfrastructureError(
            f"{name} must be a finite positive number, got "
            f"{value!r}")
    return float(value)


def validate_measurements(measurements: Mapping[str, Any]
                          ) -> dict[str, Any]:
    """The CLOSED measurement record with the 348_s #3 SHAPE
    PROOFS: the exact `constant_with_warmup` trajectory to the
    exact plateau within tolerance; the epoch wall containing all
    sequential group timings; 157 optimizer updates; the
    beta/reference path engaged; the adapter state changed —
    all infrastructure facts, no semantic value."""
    if not isinstance(measurements, Mapping) \
            or set(measurements) != MEASUREMENT_FIELDS:
        raise InfrastructureError(
            "measurements do not match the closed field set — the "
            "smoke discloses timing/memory/infrastructure ONLY")
    for name in ("startup_seconds", "checkpoint_zero_eval_seconds",
                 "whole_epoch_seconds",
                 "checkpoint_bundle_write_seconds",
                 "post_epoch_eval_seconds",
                 "trace_flush_archive_seconds"):
        _positive_number(name, measurements[name])
    per_group = measurements["per_group_generation_seconds"]
    if not isinstance(per_group, (list, tuple)) \
            or len(per_group) != 157:
        raise InfrastructureError(
            "per_group_generation_seconds must carry all 157 "
            "group rollout times")
    for value in per_group:
        _positive_number("per_group_generation_seconds[]", value)
    # 348_s #3: the epoch wall must CONTAIN the sequential groups
    if measurements["whole_epoch_seconds"] < sum(per_group):
        raise InfrastructureError(
            "whole_epoch_seconds is smaller than the sum of its "
            "sequential group timings (348_s #3)")
    volume = measurements["per_epoch_trace_bytes"]
    if not isinstance(volume, int) or isinstance(volume, bool) \
            or volume <= 0:
        raise InfrastructureError(
            "per_epoch_trace_bytes must be a positive integer")
    vram = measurements["peak_reserved_vram_mib"]
    if not isinstance(vram, int) or isinstance(vram, bool) \
            or vram <= 0:
        raise InfrastructureError(
            "peak_reserved_vram_mib must be a positive integer")
    # 348_s #3: the EXACT frozen trajectory — lr sampled at the
    # END of each of the first 10 updates, then the plateau
    trajectory = measurements["warmup_lr_trajectory"]
    if not isinstance(trajectory, (list, tuple)) \
            or len(trajectory) != _WARMUP_UPDATES + 1:
        raise InfrastructureError(
            "warmup_lr_trajectory must carry updates 1..10 plus "
            "the plateau value")
    for index, value in enumerate(trajectory):
        _positive_number("warmup_lr_trajectory[]", value)
        expected = (_PLATEAU_LR * (index + 1) / _WARMUP_UPDATES
                    if index < _WARMUP_UPDATES else _PLATEAU_LR)
        if abs(value - expected) > _LR_REL_TOLERANCE * expected:
            raise InfrastructureError(
                f"warmup_lr_trajectory[{index}] = {value!r} != "
                f"the frozen constant_with_warmup value "
                f"{expected!r} at lr {_PLATEAU_LR} (rel tol "
                f"{_LR_REL_TOLERANCE}; 348_s #3)")
    updates = measurements["optimizer_updates"]
    if updates != 157 or isinstance(updates, bool):
        raise InfrastructureError(
            f"optimizer_updates = {updates!r}; exactly 157 real "
            "updates must have executed (348_s #3)")
    kl_events = measurements["reference_kl_logged_events"]
    if not isinstance(kl_events, int) or isinstance(kl_events, bool) \
            or kl_events < 1:
        raise InfrastructureError(
            "reference_kl_logged_events must be >= 1 — the "
            "beta/reference-logprob path must have engaged "
            "(348_s #3; a COUNT of log events, never a value)")
    if measurements["adapter_state_changed"] is not True:
        raise InfrastructureError(
            "adapter_state_changed must be True — real updates "
            "must have moved the adapter off checkpoint zero "
            "(348_s #3)")
    return dict(measurements)


def derive_cap_inputs(measurements: Mapping[str, Any]
                      ) -> dict[str, Any]:
    """The DETERMINISTIC 330_f §2 mapping under the 348_s
    amendments: TWO measured evaluation passes, priced everywhere
    at their conservative MAXIMUM; EXACT values preserved (no
    downward rounding — the only rounding is the ceil inside the
    frozen trace-scaling rule)."""
    config = _validated_config()
    m = validate_measurements(measurements)
    intermediates = config["cadence"]["intermediate_evaluations"]
    scaling = config["trace_scaling"]
    eval_price = max(m["checkpoint_zero_eval_seconds"],
                     m["post_epoch_eval_seconds"])
    full_run_trace_seconds = float(math.ceil(
        m["trace_flush_archive_seconds"]
        * scaling["nominal_epochs"]
        * scaling["conservatism_multiplier"]))
    overhead = (eval_price
                + intermediates * (
                    eval_price
                    + m["checkpoint_bundle_write_seconds"])
                + m["startup_seconds"])
    reserve = (max(m["per_group_generation_seconds"])
               + eval_price
               + m["checkpoint_bundle_write_seconds"]
               + full_run_trace_seconds)
    return {
        "measured_whole_epoch_seconds": m["whole_epoch_seconds"],
        "measured_finalization_reserve_seconds": reserve,
        "frozen_non_rollout_overhead_seconds": overhead,
        "cumulative_consumed_seconds": 0.0,
        "components": {
            "eval_price_seconds": eval_price,
            "worst_rollout_batch_seconds":
                max(m["per_group_generation_seconds"]),
            "full_run_trace_seconds": full_run_trace_seconds,
            "intermediate_evaluations": intermediates,
        },
    }


def worked_launch_projection(measurements: Mapping[str, Any]
                             ) -> dict[str, Any]:
    """The NON-BINDING worked projection over the derived inputs —
    the BINDING derivation happens at the P0LaunchFreeze."""
    from .p0_cap import derive_launch_plan
    from .p0_contract import load_p0_science_contract
    inputs = derive_cap_inputs(measurements)
    plan = derive_launch_plan(
        load_p0_science_contract(),
        cumulative_consumed_seconds=inputs[
            "cumulative_consumed_seconds"],
        measured_finalization_reserve_seconds=inputs[
            "measured_finalization_reserve_seconds"],
        frozen_non_rollout_overhead_seconds=inputs[
            "frozen_non_rollout_overhead_seconds"],
        measured_whole_epoch_seconds=inputs[
            "measured_whole_epoch_seconds"])
    return {"binding": False,
            "note": ("the BINDING derivation happens at the "
                     "P0LaunchFreeze; this is the smoke record's "
                     "worked projection"),
            "cap_inputs": inputs, "plan": plan}


# --- the PERSISTED freeze: an executable identity boundary (348_s #4) ----------

def build_smoke_freeze() -> dict[str, Any]:
    """The complete identity boundary, FULL hashes only, built
    from the authoritative in-code sources and the authenticated
    artifacts — no prose stands in for a pin."""
    from tasks.conductor.stage1 import prompt_fewshot
    from .p0_contract import CONTRACT_SHA256
    from .p0_mixture_v2 import EXPECTED_MIXTURE_V2_RECORD_SHA256
    from .p0_replay import (
        PINNED_MIXTURE_FILE_SHA256,
        REPLAY_SOURCE,
    )
    config = _validated_config()
    observations = timing_cohort_observations()
    timing_seed_schedule()  # enforces the schedule pin
    record = {
        "kind": "p0_beta_smoke_freeze",
        "question": config["question"],
        "motivation": "330_f-signed precursors plan Unit T; 348_s",
        "config": config,
        "config_sha256": SMOKE_CONFIG_SHA256,
        # 348_s #4: FULL identity bindings
        "science_contract_sha256": CONTRACT_SHA256,
        "pinned_mixture_record_sha256":
            EXPECTED_MIXTURE_V2_RECORD_SHA256,
        "pinned_mixture_file_sha256": PINNED_MIXTURE_FILE_SHA256,
        "extension_surface_lock_sha256":
            REPLAY_SOURCE["extension_surface_lock_sha256"],
        "prompt_sha256": hashlib.sha256(
            prompt_fewshot().encode("utf-8")).hexdigest(),
        "runtime_profile_sha256": P0_RUNTIME_PROFILE_SHA256,
        "timing_seed_schedule_sha256": TIMING_SEED_SCHEDULE_SHA256,
        "timing_cohort_observation_ids": [
            obs["observation_id"] for obs in observations],
        "observations_total": len(observations),
        "development_only": True,
    }
    record["freeze_sha256"] = content_sha256(record)
    return record


def freeze_smoke_tranche(out_path: str | Path = SMOKE_FREEZE_PATH
                         ) -> dict[str, Any]:
    out_path = Path(out_path)
    if out_path.exists():
        raise InfrastructureError(
            f"{out_path} exists; the smoke freeze is written "
            "exactly once")
    record = build_smoke_freeze()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    return record


def load_smoke_freeze(path: str | Path = SMOKE_FREEZE_PATH,
                      expected_sha256: str | None = None
                      ) -> dict[str, Any]:
    """The strict loader/admission boundary (348_s #4): the
    externally reviewed hash; the record must REDERIVE completely
    from the frozen sources — GPU execution starts HERE or not at
    all."""
    expected = expected_sha256 or SMOKE_FREEZE_SHA256
    payload = json.loads(Path(path).read_text("utf-8"))
    body = {k: v for k, v in payload.items()
            if k != "freeze_sha256"}
    if content_sha256(body) != payload.get("freeze_sha256") \
            or payload["freeze_sha256"] != expected:
        raise InfrastructureError(
            "smoke freeze does not rehash to the externally "
            "reviewed value")
    if payload != build_smoke_freeze():
        raise InfrastructureError(
            "smoke freeze does not rederive from the frozen "
            "sources")
    return payload


# --- the two-phase instrumented runner (348_s: rev2 deliverable) ---------------

DRIVER = "tasks/routing/p0_smoke.py"

_SMOKE_LAUNCH_KEYS = frozenset({
    "kind", "smoke_freeze_sha256", "smoke_config_sha256",
    "science_contract_sha256", "runtime_profile_sha256",
    "budget_gpu_hours", "driver", "run_root", "execution_root",
    "lineage_parent_sha256", "routing_source_sha256",
    "environment_manifest_sha256",
})
SMOKE_LAUNCH_KIND = "routing-dev-beta-smoke-launch-v1"


def build_smoke_launch_manifest(*, environment_manifest:
                                Mapping[str, Any],
                                execution_root: str | Path
                                ) -> dict[str, Any]:
    from .charter import routing_execution_digest
    config = _validated_config()
    freeze = load_smoke_freeze()
    digest = routing_execution_digest(DRIVER)
    manifest = {
        "kind": SMOKE_LAUNCH_KIND,
        "smoke_freeze_sha256": freeze["freeze_sha256"],
        "smoke_config_sha256": SMOKE_CONFIG_SHA256,
        "science_contract_sha256":
            freeze["science_contract_sha256"],
        "runtime_profile_sha256": P0_RUNTIME_PROFILE_SHA256,
        "budget_gpu_hours": config["budget_gpu_hours"],
        "driver": DRIVER,
        "run_root": config["run_root"],
        "execution_root": str(Path(execution_root).resolve()),
        "lineage_parent_sha256":
            config["lineage"]["parent_entry_sha256"],
        "routing_source_sha256": digest["routing_source_sha256"],
        "environment_manifest_sha256":
            dev_support.validate_environment_manifest_binding(
                environment_manifest),
    }
    manifest["manifest_sha256"] = content_sha256(manifest)
    return manifest


def validate_smoke_launch_manifest(manifest: Mapping[str, Any], *,
                                   recompute: bool = True
                                   ) -> dict[str, Any]:
    """Closed schema; every configuration-owned field REDERIVED;
    the freeze loaded through its strict boundary; the source
    digest recomputed from the tree."""
    from .charter import routing_execution_digest
    if not isinstance(manifest, Mapping) \
            or set(manifest) != _SMOKE_LAUNCH_KEYS | \
            {"manifest_sha256"}:
        raise InfrastructureError(
            "smoke launch manifest keys do not match the closed "
            "schema")
    body = {k: v for k, v in manifest.items()
            if k != "manifest_sha256"}
    if content_sha256(body) != manifest["manifest_sha256"]:
        raise InfrastructureError(
            "smoke launch manifest does not rehash")
    config = _validated_config()
    freeze = load_smoke_freeze()
    for key, frozen_value in (
            ("kind", SMOKE_LAUNCH_KIND),
            ("smoke_freeze_sha256", freeze["freeze_sha256"]),
            ("smoke_config_sha256", SMOKE_CONFIG_SHA256),
            ("science_contract_sha256",
             freeze["science_contract_sha256"]),
            ("runtime_profile_sha256", P0_RUNTIME_PROFILE_SHA256),
            ("budget_gpu_hours", config["budget_gpu_hours"]),
            ("driver", DRIVER),
            ("run_root", config["run_root"]),
            ("lineage_parent_sha256",
             config["lineage"]["parent_entry_sha256"])):
        if manifest[key] != frozen_value:
            raise InfrastructureError(
                f"smoke launch manifest {key} = {manifest[key]!r} "
                f"diverges from the frozen value {frozen_value!r}")
    if recompute:
        digest = routing_execution_digest(DRIVER)
        if manifest["routing_source_sha256"] != \
                digest["routing_source_sha256"]:
            raise InfrastructureError(
                "smoke launch manifest source digest does not "
                "match the tree")
    return dict(manifest)


def prepare_smoke_launch(*, run_dir: str | Path = SMOKE_RUN_ROOT,
                         _environment_builder=None
                         ) -> dict[str, Any]:
    """Phase 1 (CPU): persist the prelaunch inputs exactly once;
    the prepared manifest hash goes to the narrow prelaunch
    review."""
    from .support_run import _default_environment
    run_dir = Path(run_dir)
    prelaunch = run_dir / "prelaunch"
    if prelaunch.exists():
        raise InfrastructureError(
            f"{prelaunch} exists; a launch is prepared exactly "
            "once")
    environment = (_environment_builder or _default_environment)()
    manifest = build_smoke_launch_manifest(
        environment_manifest=environment, execution_root=run_dir)
    prelaunch.mkdir(parents=True)
    for name, payload in (("env_manifest.json", environment),
                          ("smoke_launch.json", manifest),
                          ("smoke_freeze.json",
                           load_smoke_freeze())):
        (prelaunch / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    return manifest


class _EpochInstrumentation:
    """The P3 instrumentation (the frozen per-group rollout
    definition): reward-entry minus the previous phase boundary;
    lr sampled at the END of each update; update counting."""

    def __init__(self):
        import time as _time
        self._time = _time
        self.epoch_start = None
        self.last_boundary = None
        self.per_group_seconds: list[float] = []
        self.lr_trajectory: list[float] = []
        self.updates = 0

    def start_epoch(self):
        now = self._time.monotonic()
        self.epoch_start = now
        self.last_boundary = now

    def on_reward_entry(self):
        self.per_group_seconds.append(
            self._time.monotonic() - self.last_boundary)

    def on_update_end(self, learning_rate: float):
        self.updates += 1
        self.last_boundary = self._time.monotonic()
        if self.updates <= _WARMUP_UPDATES + 1:
            self.lr_trajectory.append(float(learning_rate))


def _timed_eval_pass(trainer, observations, loaded, seeds,
                     out_path: Path, label: str) -> float:
    """One COMPLETE evaluation pass (348_s #2): generation under
    the frozen sampling identity (per-observation slot-0 CRN
    seeding), parse/score against the locked surface, telemetry,
    and SEALED trace persistence — all inside the timed window."""
    import time as _time

    import torch
    from tasks.conductor import program
    from tasks.conductor.grpo_task import positional_to_semantic
    from tasks.conductor.parser import (
        ActionSchemaError,
        parse_routing_action,
    )
    from tasks.conductor.policy import policy_messages
    from tasks.conductor.profiles import DEFAULT_PROFILE
    from tasks.conductor.stage1 import prompt_fewshot
    started = _time.monotonic()
    model = trainer.model
    tokenizer = trainer.processing_class
    surface = loaded["surface"]
    system = prompt_fewshot()
    rows = []
    telemetry = {"groups": 0, "completions": 0, "valid": 0}
    was_training = model.training
    model.eval()
    with torch.no_grad():
        for obs in observations:
            oid = obs["observation_id"]
            latent = obs["latent"]
            steps = [{"subtask": s["subtask"],
                      "resource": s["resource"],
                      "access": s["access"]}
                     for s in program.workflow_steps(latent)]
            user = policy_messages(obs["instance"], steps)[1]
            prompt = tokenizer.apply_chat_template(
                [{"role": "system", "content": system},
                 dict(user)],
                tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(prompt, return_tensors="pt").to(
                model.device)
            torch.manual_seed(seeds[oid])
            generated = model.generate(
                **inputs, do_sample=True, temperature=1.0,
                top_p=1.0, top_k=0, num_return_sequences=8,
                max_new_tokens=128,
                pad_token_id=tokenizer.eos_token_id)
            positions = latent["reference_program"]["positions"]
            completions, rewards = [], []
            for sequence in generated:
                text = tokenizer.decode(
                    sequence[inputs["input_ids"].shape[1]:],
                    skip_special_tokens=True)
                completions.append(text)
                try:
                    parsed = parse_routing_action(
                        text, len(positions))
                except ActionSchemaError:
                    parsed = None
                if parsed is None:
                    rewards.append(0.0)
                    continue
                semantic = tuple(positional_to_semantic(
                    parsed, positions))
                payoff = surface.get((oid, semantic))
                if payoff is None:
                    rewards.append(0.0)
                    continue
                telemetry["valid"] += 1
                rewards.append(float(payoff))
            telemetry["groups"] += 1
            telemetry["completions"] += len(completions)
            rows.append({"observation_id": oid,
                         "completions": completions,
                         "rewards": rewards})
    if was_training:
        model.train()
    # SEALED: persisted inside the timed window, never surfaced
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True)
                  for row in rows) + "\n", encoding="utf-8")
    del rows  # discarded unread
    return _time.monotonic() - started


def _save_checkpoint_bundle(trainer, out_dir: Path) -> float:
    """P4: one COMPLETE RESUMABLE bundle — adapter + optimizer +
    scheduler + RNG states (the resume-validation bundle shape),
    timed."""
    import random
    import time as _time

    import numpy
    import torch
    started = _time.monotonic()
    out_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(str(out_dir / "adapter"))
    torch.save(
        {"optimizer": trainer.optimizer.state_dict(),
         "lr_scheduler": trainer.lr_scheduler.state_dict(),
         "torch_rng": torch.get_rng_state(),
         "cuda_rng": (torch.cuda.get_rng_state_all()
                      if torch.cuda.is_available() else None),
         "numpy_rng": numpy.random.get_state(),
         "python_rng": random.getstate()},
        out_dir / "training_state.pt")
    return _time.monotonic() - started


def _adapter_snapshot(trainer) -> dict[str, Any]:
    import hashlib as _hashlib
    digest = _hashlib.sha256()
    for name, parameter in sorted(
            trainer.model.named_parameters()):
        if "lora" in name:
            digest.update(name.encode("utf-8"))
            digest.update(parameter.data.detach().cpu().float()
                          .numpy().tobytes())
    return {"lora_state_sha256": digest.hexdigest()}


def _build_smoke_trainer(rows, reward, run_dir: Path,
                         extra_callbacks=()):
    """The canonical-profile construction: the C2-validated
    literals with the SIGNED training deltas (lr 1e-5, beta 1e-3,
    10-update constant_with_warmup) and the smoke seed; report_to
    none; logging captured by the caller into sealed files."""
    import random

    import numpy
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer, BitsAndBytesConfig
    from trl import GRPOConfig, GRPOTrainer

    from .p0_launch import _validated_profile
    profile = _validated_profile()
    grpo = profile["grpo"]
    seed = _validated_config()["training"]["seed"]
    random.seed(seed)
    numpy.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    processing_class = AutoTokenizer.from_pretrained(
        profile["model_id"], revision=profile["revision"])
    args = GRPOConfig(
        output_dir=str(run_dir), run_name=run_dir.name,
        seed=seed, num_generations=grpo["group_size"],
        max_completion_length=profile["policy_max_new_tokens"],
        temperature=float(grpo["temperature"]),
        per_device_train_batch_size=grpo["per_device_batch"],
        gradient_accumulation_steps=grpo["grad_accum"],
        learning_rate=float(grpo["learning_rate"]),
        lr_scheduler_type=grpo["scheduler"],
        warmup_steps=grpo["warmup_steps"],
        beta=float(grpo["beta"]),
        max_steps=157, loss_type=grpo["loss"],
        shuffle_dataset=False, eval_strategy="no",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        bf16=grpo["bf16"], full_determinism=True,
        model_init_kwargs={
            "torch_dtype": torch.bfloat16,
            "attn_implementation": "sdpa",
            "revision": profile["revision"],
            "quantization_config": BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16)},
        optim=grpo["optim"], report_to="none", logging_steps=16,
        save_strategy="no", disable_tqdm=True)
    peft_config = LoraConfig(
        r=profile["lora"]["r"],
        lora_alpha=profile["lora"]["alpha"],
        lora_dropout=profile["lora"]["dropout"],
        target_modules=list(profile["lora"]["targets"]),
        task_type="CAUSAL_LM")
    trainer = GRPOTrainer(
        model=profile["model_id"], args=args,
        train_dataset=Dataset.from_list(list(rows)),
        processing_class=processing_class, reward_funcs=[reward],
        peft_config=peft_config)
    for name, parameter in trainer.model.named_parameters():
        if "lora" in name:
            parameter.data = parameter.data.to(torch.float32)
    for callback in extra_callbacks:
        trainer.add_callback(callback)
    return trainer


def execute_smoke_run(*, run_dir: str | Path = SMOKE_RUN_ROOT,
                      expected_manifest_sha256: str,
                      expected_head_sha256: str | None,
                      question: str, motivating_evidence: str,
                      ledger_path=None) -> dict[str, Any]:
    """Phase 2 (GPU): the disjoint-phase instrumented run. Full
    validation before the irreversible admission (engineering_smoke
    on EXACTLY the frozen lineage parent for a first attempt;
    aborted identical-design retries per 330_f §5); the sealed
    outputs and the closed timing record; the closeout binds every
    terminal byte."""
    import time as _time

    from .ledger import (
        LEDGER_PATH,
        admit_and_append_launch,
        append_ledger_entry,
        verify_ledger_head,
    )
    from .support_run import (
        _default_environment,
        _hash_directory,
        _persist_verified,
        attest_environment,
    )
    config = _validated_config()
    ledger_path = ledger_path or LEDGER_PATH
    # lineage: first launch only from the frozen parent; retries
    # only after aborted-closed identical-design attempts
    chain = verify_ledger_head(expected_head_sha256, ledger_path)
    prior = [e for e in chain if e["kind"] == "engineering_smoke"
             and e["freeze"].get("smoke_freeze_sha256")
             == SMOKE_FREEZE_SHA256]
    if not prior and expected_head_sha256 != \
            config["lineage"]["parent_entry_sha256"]:
        raise InfrastructureError(
            "the FIRST smoke launch is admitted on the frozen "
            "lineage parent")
    closed = {e.get("closes_entry_sha256"): e for e in chain
              if e["kind"] == "closeout"}
    for attempt in prior:
        closeout = closed.get(attempt["entry_sha256"])
        if closeout is None:
            raise InfrastructureError(
                "a prior smoke attempt is OPEN — no new launch")
        if closeout.get("terminal_status") == "complete":
            raise InfrastructureError(
                "a completed smoke exists — never rerun")
    run_dir = Path(run_dir)
    prelaunch = run_dir / "prelaunch"
    frozen_env = json.loads(
        (prelaunch / "env_manifest.json").read_text("utf-8"))
    manifest = validate_smoke_launch_manifest(json.loads(
        (prelaunch / "smoke_launch.json").read_text("utf-8")))
    if manifest["manifest_sha256"] != expected_manifest_sha256:
        raise InfrastructureError(
            "prepared smoke manifest is not the externally frozen "
            "one")
    if str(run_dir.resolve()) != manifest["execution_root"]:
        raise InfrastructureError(
            "the execution directory is not the root the manifest "
            "binds")
    live_env = _default_environment()
    dev_support.validate_environment_manifest_binding(live_env)
    attest_environment(frozen_env, live_env)
    outputs = [run_dir / "sealed", run_dir / "smoke_record.json",
               run_dir / "execute_env_manifest.json"]
    for path in outputs:
        if path.exists():
            raise InfrastructureError(
                f"{path} exists — outputs are preflighted before "
                "admission")

    entry = {
        "kind": "engineering_smoke",
        "question": question,
        "motivating_evidence": motivating_evidence,
        "freeze": {
            "smoke_launch_sha256": manifest["manifest_sha256"],
            "smoke_freeze_sha256": SMOKE_FREEZE_SHA256,
            "smoke_config_sha256": SMOKE_CONFIG_SHA256,
        },
        "parent": expected_head_sha256,
        "budget_allocated_gpu_hours":
            manifest["budget_gpu_hours"],
        "outcome_informed": False,
    }
    admitted = admit_and_append_launch(entry, expected_head_sha256,
                                       ledger_path)
    head = admitted["entry_sha256"]
    started = _time.monotonic()
    deadline = started + manifest["budget_gpu_hours"] * 3600.0

    try:
        import torch

        from .p0_contract import load_p0_science_contract
        from .p0_replay import restore_extension_surface_if_absent
        from .p0_schedule import build_trainer_rows
        from .unit_c2_sample import UNIT_C2_CONFIG
        _persist_verified(run_dir / "execute_env_manifest.json",
                          live_env)
        sealed = run_dir / "sealed"
        sealed.mkdir(parents=True)

        # --- P1 startup: everything loaded, nothing sampled ------
        contract = load_p0_science_contract()
        rows = build_trainer_rows(contract, 1)
        loaded = dev_support.load_dev_surface(
            restore_extension_surface_if_absent(),
            expected_lock_sha256=UNIT_C2_CONFIG[
                "extension_surface_lock_sha256"])
        observations = timing_cohort_observations()
        seeds = {oid: seed for oid, slot, seed
                 in timing_seed_schedule() if slot == 0}
        instrumentation = _EpochInstrumentation()
        surface = loaded["surface"]

        def reward(completions=None, prompts=None, **kwargs):
            instrumentation.on_reward_entry()
            oids = kwargs["observation_id"]
            positions_json = kwargs["positions"]
            out = []
            from tasks.conductor.grpo_task import (
                positional_to_semantic,
            )
            from tasks.conductor.parser import (
                ActionSchemaError,
                parse_routing_action,
            )
            for text, oid, positions_s in zip(
                    completions, oids, positions_json):
                positions = json.loads(positions_s)
                try:
                    parsed = parse_routing_action(
                        text, len(positions))
                except ActionSchemaError:
                    out.append(0.0)
                    continue
                semantic = tuple(positional_to_semantic(
                    parsed, positions))
                out.append(float(surface.get((oid, semantic),
                                             0.0)))
            return out

        from transformers import TrainerCallback

        class _UpdateCallback(TrainerCallback):
            def on_step_end(self, args, state, control, **kwargs):
                scheduler = kwargs.get("lr_scheduler")
                lr = (scheduler.get_last_lr()[0]
                      if scheduler is not None else 0.0)
                instrumentation.on_update_end(lr)

        trainer = _build_smoke_trainer(
            rows, reward, run_dir,
            extra_callbacks=(_UpdateCallback(),))
        torch.cuda.reset_peak_memory_stats()
        baseline = _adapter_snapshot(trainer)
        startup_seconds = _time.monotonic() - started

        # --- P2 checkpoint-zero eval -----------------------------
        ckpt0_eval = _timed_eval_pass(
            trainer, observations, loaded, seeds,
            sealed / "eval_ckpt0.jsonl", "ckpt0")

        # --- P3 the epoch ----------------------------------------
        instrumentation.start_epoch()
        trainer.train()
        epoch_end = _time.monotonic()
        whole_epoch = epoch_end - instrumentation.epoch_start

        # --- P4 the resumable checkpoint bundle ------------------
        bundle_seconds = _save_checkpoint_bundle(
            trainer, run_dir / "checkpoint_bundle")

        # --- P5 the post-epoch eval ------------------------------
        post_eval = _timed_eval_pass(
            trainer, observations, loaded, seeds,
            sealed / "eval_post.jsonl", "post")

        # --- P6 trace seal ---------------------------------------
        import gzip
        seal_start = _time.monotonic()
        trace_files = sorted(sealed.glob("*.jsonl"))
        log_history = trainer.state.log_history
        (sealed / "trainer_log_history.json").write_text(
            json.dumps(log_history, sort_keys=True),
            encoding="utf-8")
        volume = 0
        for file in trace_files:
            data = file.read_bytes()
            volume += len(data)
            with open(str(file) + ".gz", "wb") as raw:
                with gzip.GzipFile(fileobj=raw, mode="wb",
                                   filename="", mtime=0,
                                   compresslevel=9) as handle:
                    handle.write(data)
            file.unlink()
        seal_seconds = _time.monotonic() - seal_start

        changed = _adapter_snapshot(trainer)
        kl_events = sum(1 for entry_ in log_history
                        if any("kl" in key for key in entry_))
        measurements = {
            "startup_seconds": startup_seconds,
            "checkpoint_zero_eval_seconds": ckpt0_eval,
            "whole_epoch_seconds": whole_epoch,
            "per_group_generation_seconds":
                list(instrumentation.per_group_seconds),
            "checkpoint_bundle_write_seconds": bundle_seconds,
            "post_epoch_eval_seconds": post_eval,
            "trace_flush_archive_seconds": seal_seconds,
            "per_epoch_trace_bytes": volume,
            "peak_reserved_vram_mib": int(
                torch.cuda.max_memory_reserved() // 2 ** 20),
            "warmup_lr_trajectory":
                list(instrumentation.lr_trajectory),
            "optimizer_updates": instrumentation.updates,
            "reference_kl_logged_events": kl_events,
            "adapter_state_changed":
                changed["lora_state_sha256"]
                != baseline["lora_state_sha256"],
        }
        projection = worked_launch_projection(measurements)
        record = {
            "run": config["tranche"],
            "smoke_launch_sha256": manifest["manifest_sha256"],
            "smoke_freeze_sha256": SMOKE_FREEZE_SHA256,
            "launch_entry_sha256": head,
            "measurements": validate_measurements(measurements),
            "projection": projection,
            "development_only": True,
        }
        _persist_verified(run_dir / "smoke_record.json", record)
        # the trained state is DISCARDED (the bundle stays as
        # timed evidence bytes; nothing loads it into P0)
        del trainer
        if _time.monotonic() > deadline:
            raise InfrastructureError(
                "the smoke finished past its budget deadline — "
                "the run aborts")
    except BaseException as error:
        measured = round((_time.monotonic() - started) / 3600.0, 4)
        append_ledger_entry(
            {"kind": "closeout", "question": question,
             "motivating_evidence": "smoke ABORTED",
             "freeze": {
                 "smoke_launch_sha256":
                     manifest["manifest_sha256"],
                 "partial_artifact_hashes":
                     _hash_directory(run_dir)},
             "parent": head,
             "budget_allocated_gpu_hours": 0.0,
             "budget_consumed_gpu_hours": measured,
             "closes_entry_sha256": head,
             "terminal_status": "aborted",
             "interpretation": f"{type(error).__name__}: {error}",
             "outcome_informed": False,
             "outcome_pointer": str(run_dir)},
            head, ledger_path)
        raise

    measured = round((_time.monotonic() - started) / 3600.0, 4)
    from .support_run import _sha_file
    closeout = append_ledger_entry(
        {"kind": "closeout", "question": question,
         "motivating_evidence": "measured beta-smoke cost",
         "freeze": {
             "smoke_record_file_sha256":
                 _sha_file(run_dir / "smoke_record.json"),
             "execute_env_file_sha256":
                 _sha_file(run_dir / "execute_env_manifest.json"),
             "terminal_artifact_hashes": _hash_directory(run_dir),
         },
         "parent": head,
         "budget_allocated_gpu_hours": 0.0,
         "budget_consumed_gpu_hours": measured,
         "closes_entry_sha256": head,
         "terminal_status": "complete",
         "outcome_informed": False,
         "outcome_pointer": str(run_dir / "smoke_record.json")},
        head, ledger_path)
    return {**record, "measured_gpu_hours": measured,
            "closeout_entry_sha256": closeout["entry_sha256"],
            "ledger_head": closeout["entry_sha256"]}
