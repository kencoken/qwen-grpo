"""P0 precursors, Unit T — the beta timing smoke (the SIGNED
precursors plan: 328_f §2 isolation; 328_f §3 + 330_f §2 the
frozen cadence and the executable measurement→cap-input mapping;
330_f §5 disclosure limits and abort/retry).

ONE bounded GPU run (<= 0.6 GPU-h) measuring the cap-formula
inputs under the REAL P0 training shape (the canonical profile:
beta 1e-3, lr 1e-5, 10-step `constant_with_warmup`) — which the
C2 zero-update run could not measure. The trained state is
DISCARDED after verification; disclosure before the P0 freeze is
TIMING/MEMORY/INFRASTRUCTURE ONLY (the record schema is closed —
no reward, routing, selection, or learning observable exists in
it); the semantic trace is retained hashed, uninspected until
after the P0 freeze.

This module carries the FROZEN design and every CPU-testable
boundary: the config and pins, the shape-matched
already-development-exposed timing cohort, the deterministic
measurement→cap-input mapping (`derive_cap_inputs`), the
non-binding worked launch projection, and the closed smoke-record
schema. The instrumented GPU runner (prepare/execute, mirroring
the two-phase pattern) is implemented against THESE boundaries
once the design is signed."""
from __future__ import annotations

import math
from typing import Any, Mapping

from tasks.conductor.types import (
    RENDERER_IDS,
    InfrastructureError,
)

from . import dev_support
from .charter import content_sha256
from .p0_launch import P0_RUNTIME_PROFILE_SHA256

SMOKE_RUN_ROOT = "runs/routing-dev/beta-smoke-v1"

SMOKE_CELLS = ("code_atomic", "fork_join", "lookup_atomic",
               "lookup_math", "math_atomic", "math_code")

# the frozen cadence (328_f §3; 330_f §2): checkpoint + evaluation
# every 4 epochs on the NOMINAL horizon plus the mandatory
# endpoints; persisted in BOTH epoch and optimizer-update units
# (157 groups/epoch x 1 group/update)
CADENCE_EPOCHS = (0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 39)
CADENCE_UPDATES = tuple(epoch * 157 for epoch in CADENCE_EPOCHS[:-1]
                        ) + (6123,)

SMOKE_CONFIG: dict[str, Any] = {
    "tranche": "routing-dev-beta-smoke-v1",
    "question": ("Unit T: the cap-formula inputs measured under "
                 "the REAL P0 training shape — whole-epoch wall, "
                 "the finalization components, and the scheduled "
                 "overhead at the frozen cadence"),
    "runtime_profile_sha256": P0_RUNTIME_PROFILE_SHA256,
    "training": {
        "shape": ("the canonical profile exactly: beta 1e-3, lr "
                  "1e-5, 10-step warmup as constant_with_warmup, "
                  "batch 2x4 = one 157-group epoch = 157 optimizer "
                  "updates, NF4 + fp32 LoRA, the pinned trainer "
                  "settings"),
        "schedule": ("ONE complete epoch of the pinned mixture "
                     "(135a72bf…) through the STRICT spine loader "
                     "build_trainer_rows(contract, 1), consumed "
                     "under the reviewed contract pin d47a63ff…"),
        "seed": 20260806,
        "seed_domain": "timing_smoke",
        "state": ("the trained adapter is VERIFIED to differ from "
                  "checkpoint zero (real updates happened — an "
                  "infrastructure fact) and then DISCARDED; "
                  "nothing from the smoke seeds P0"),
    },
    # 328_f §2: the timing-evaluation cohort is SHAPE-MATCHED and
    # ALREADY development-exposed — the locked routing_dev_val
    # cohort receives NO policy output before checkpoint zero
    "timing_cohort": {
        "namespace": "routing_dev",
        "cohort": {cell: [0, 1, 2, 3, 4] for cell in SMOKE_CELLS},
        "renderers": list(RENDERER_IDS),
        "visibility": "private",
        "source": ("the LOCKED extension surface (ccb1c3e2…) — "
                   "surfaces already materialized; no new "
                   "exposure"),
        "sampling": ("the frozen canonical sampling identity, so "
                     "the measured cost is the REAL evaluation "
                     "cost; outputs discarded unread"),
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
    # the instrumentation points (330_f §2; exact definitions the
    # runner must implement)
    "instrumentation": {
        "startup_seconds": ("process start (model + pool load) to "
                            "the FIRST optimizer update beginning"),
        "whole_epoch_seconds": ("first rollout start to the 157th "
                                "optimizer update end; NO "
                                "evaluation time included"),
        "per_group_generation_seconds": (
            "all 157 per-group rollout wall times; the WORST "
            "(maximum) feeds the finalization reserve"),
        "checkpoint_write_seconds": ("one adapter checkpoint "
                                     "save, wall"),
        "eval_pass_seconds": ("one 90-group generation pass on "
                              "the timing cohort under the frozen "
                              "sampling identity"),
        "trace_flush_archive_seconds": (
            "one-epoch trace flush + verification + "
            "deterministic-gzip archival, wall"),
        "per_epoch_trace_bytes": "the epoch's trace volume",
    },
    # the trace-volume scaling rule (329_s #2): the reserve prices
    # the NOMINAL 39-epoch volume
    "trace_scaling": {
        "rule": ("full_run_trace_seconds = ceil("
                 "trace_flush_archive_seconds x 39 x 1.2) — linear "
                 "in the nominal horizon with a frozen 1.2 "
                 "conservatism multiplier, rounded up to whole "
                 "seconds"),
        "nominal_epochs": 39,
        "conservatism_multiplier": 1.2,
    },
    "budget_gpu_hours": 0.6,
    "run_root": SMOKE_RUN_ROOT,
    "ledger_kind": "engineering_smoke",
    "disclosure": ("BEFORE the P0 freeze: the AUTOMATED "
                   "TIMING-ONLY projection (durations, memory, "
                   "infrastructure events, the derived cap inputs, "
                   "the worked NON-BINDING derive_launch_plan "
                   "projection). NO reward, routing, selection, or "
                   "learning observable. The semantic trace is "
                   "retained hashed, uninspected until after the "
                   "P0 freeze."),
    "predictions": {
        "whole_epoch_minutes": "12-16 (C2: 12.2 at beta 0)",
        "eval_pass_minutes": "~7 (90 groups x ~4.647 s/group)",
        "checkpoint_write": "seconds-scale",
        "derived_capacity_epochs": ("33-38 — the DISCLOSED "
                                    "under-target branch remains "
                                    "the expected P0 outcome "
                                    "(290_f)"),
        "warmup_ramp": ("the lr trajectory over the first 10 "
                        "updates matches constant_with_warmup"),
        "cost_gpu_hours": "0.35-0.45 within the 0.6 ceiling",
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
                                "T; 346_f Unit-Y closure"),
    },
}
SMOKE_CONFIG_SHA256 = \
    "cda554d2909568d477756e2d4c51f441083e66b1d9609de8b65910af3db9e62c"

# the measured field set the runner must produce — CLOSED: no
# semantic observable has a field to live in
MEASUREMENT_FIELDS = frozenset({
    "startup_seconds", "whole_epoch_seconds",
    "per_group_generation_seconds", "checkpoint_write_seconds",
    "checkpoint_zero_eval_seconds", "intermediate_eval_seconds",
    "final_eval_seconds", "trace_flush_archive_seconds",
    "per_epoch_trace_bytes", "peak_reserved_vram_mib",
    "warmup_lr_trajectory",
})


def _validated_config() -> dict[str, Any]:
    if content_sha256(SMOKE_CONFIG) != SMOKE_CONFIG_SHA256:
        raise InfrastructureError(
            "SMOKE_CONFIG was mutated after import")
    return SMOKE_CONFIG


def timing_cohort_observations() -> list[dict[str, Any]]:
    """The shape-matched, ALREADY-EXPOSED timing cohort — 90
    routing_dev observations whose surfaces live on the LOCKED
    extension surface (asserted by the membership check)."""
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


def _positive_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or value <= 0:
        raise InfrastructureError(
            f"{name} must be a finite positive number, got "
            f"{value!r}")
    return float(value)


def validate_measurements(measurements: Mapping[str, Any]
                          ) -> dict[str, Any]:
    """The CLOSED measurement record: exact field set; positive
    finite durations; 157 per-group times; an 11-point warmup lr
    trajectory (the first 10 updates + the plateau)."""
    if not isinstance(measurements, Mapping) \
            or set(measurements) != MEASUREMENT_FIELDS:
        raise InfrastructureError(
            "measurements do not match the closed field set — the "
            "smoke discloses timing/memory/infrastructure ONLY")
    for name in ("startup_seconds", "whole_epoch_seconds",
                 "checkpoint_write_seconds",
                 "checkpoint_zero_eval_seconds",
                 "intermediate_eval_seconds", "final_eval_seconds",
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
    trajectory = measurements["warmup_lr_trajectory"]
    if not isinstance(trajectory, (list, tuple)) \
            or len(trajectory) != 11:
        raise InfrastructureError(
            "warmup_lr_trajectory must carry updates 1..10 plus "
            "the plateau value")
    for value in trajectory:
        _positive_number("warmup_lr_trajectory[]", value)
    if list(trajectory) != sorted(trajectory) \
            or trajectory[-1] != trajectory[-2]:
        raise InfrastructureError(
            "warmup_lr_trajectory must ramp monotonically to the "
            "constant plateau (constant_with_warmup)")
    return dict(measurements)


def derive_cap_inputs(measurements: Mapping[str, Any]
                      ) -> dict[str, Any]:
    """The DETERMINISTIC 330_f §2 mapping — measurements in, the
    frozen cap formula's inputs out; every term named once, no
    double counting."""
    config = _validated_config()
    m = validate_measurements(measurements)
    intermediates = config["cadence"]["intermediate_evaluations"]
    scaling = config["trace_scaling"]
    full_run_trace_seconds = float(math.ceil(
        m["trace_flush_archive_seconds"]
        * scaling["nominal_epochs"]
        * scaling["conservatism_multiplier"]))
    overhead = (m["checkpoint_zero_eval_seconds"]
                + intermediates * (m["intermediate_eval_seconds"]
                                   + m["checkpoint_write_seconds"])
                + m["startup_seconds"])
    reserve = (max(m["per_group_generation_seconds"])
               + m["final_eval_seconds"]
               + m["checkpoint_write_seconds"]
               + full_run_trace_seconds)
    return {
        "measured_whole_epoch_seconds": m["whole_epoch_seconds"],
        "measured_finalization_reserve_seconds": round(reserve, 1),
        "frozen_non_rollout_overhead_seconds": round(overhead, 1),
        "cumulative_consumed_seconds": 0.0,
        "components": {
            "worst_rollout_batch_seconds":
                max(m["per_group_generation_seconds"]),
            "full_run_trace_seconds": full_run_trace_seconds,
            "intermediate_evaluations": intermediates,
        },
    }


def worked_launch_projection(measurements: Mapping[str, Any]
                             ) -> dict[str, Any]:
    """The NON-BINDING worked projection: `derive_launch_plan`
    over the derived inputs — the BINDING derivation happens at
    the P0LaunchFreeze with these persisted inputs (330_f §2)."""
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


def smoke_tranche_freeze() -> dict[str, Any]:
    """The preregistered Unit-T record the reviewer signs BEFORE
    any GPU launch."""
    config = _validated_config()
    observations = timing_cohort_observations()
    body = {
        "kind": "p0_beta_smoke_tranche",
        "question": config["question"],
        "motivation": "330_f-signed precursors plan Unit T",
        "config": config,
        "config_sha256": SMOKE_CONFIG_SHA256,
        "timing_cohort_observation_ids": [
            obs["observation_id"] for obs in observations],
        "observations_total": len(observations),
        "development_only": True,
    }
    body["freeze_sha256"] = content_sha256(body)
    return body
