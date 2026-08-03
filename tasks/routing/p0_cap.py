"""P0 spine, Unit 4 — the REGISTERED sizing/cap arithmetic (303_f
§9 step 4; 305_f §5).

```
nominal_epochs  = contract.sizing.nominal_epochs   (C2-derived, 39)
capacity_epochs = frozen cap formula (beta smoke + reserve inputs)
launch_epochs   = min(nominal_epochs, capacity_epochs)
```

The closed branches (from the contract's CapRule):

- `capacity_epochs <= 0`  -> stop for a reviewed amendment;
- `0 < capacity < nominal` -> the DISCLOSED under-target branch
  (claims based on achieved projected exposure: capacity x the
  measured per-epoch counted rate, quantified here);
- `capacity >= nominal`    -> run exactly nominal; spare capacity
  NEVER authorizes extra training.

`derive_launch_plan` returns every cap input AND all three values
in one record — the exact content the later `P0LaunchFreeze`
(Unit 5, after val/cycle/beta inputs exist) must persist. The
arithmetic is the frozen V1 form; a parity test binds it to the
legacy `derive_p0_cap_v2` output on shared inputs."""
from __future__ import annotations

import math
from typing import Any

from tasks.conductor.types import InfrastructureError

from .p0_schema import P0ScienceContract

# the registered input names — must equal the contract CapRule's
# closed capacity_inputs tuple, checked at every derivation
REGISTERED_CAPACITY_INPUTS = (
    "operational_ceiling_seconds",
    "cumulative_consumed_seconds",
    "measured_finalization_reserve_seconds",
    "frozen_non_rollout_overhead_seconds",
    "measured_whole_epoch_seconds",
)


def _finite_number(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value):
        raise InfrastructureError(
            f"{name} must be a finite non-boolean number, got "
            f"{value!r}")
    return float(value)


def _validate_cap_rule(contract: P0ScienceContract) -> None:
    cap = contract.sizing.cap
    if cap.rule_id != "p0-cap-v1" \
            or cap.launch_epochs != "min_nominal_capacity" \
            or tuple(cap.capacity_inputs) \
            != REGISTERED_CAPACITY_INPUTS:
        raise InfrastructureError(
            f"unknown cap rule {cap!r} — the registered arithmetic "
            "refuses to compute an unregistered formula")


def derive_capacity(contract: P0ScienceContract, *,
                    cumulative_consumed_seconds: float,
                    measured_finalization_reserve_seconds: float,
                    frozen_non_rollout_overhead_seconds: float,
                    measured_whole_epoch_seconds: float
                    ) -> dict[str, Any]:
    """The frozen capacity formula over the registered inputs. The
    ceiling comes from the CONTRACT (never the caller); every other
    input arrives from measurements outside this module (beta smoke,
    ledger, reserve) and is validated, echoed, and persisted."""
    _validate_cap_rule(contract)
    consumed = _finite_number("cumulative_consumed_seconds",
                              cumulative_consumed_seconds)
    reserve = _finite_number(
        "measured_finalization_reserve_seconds",
        measured_finalization_reserve_seconds)
    overhead = _finite_number(
        "frozen_non_rollout_overhead_seconds",
        frozen_non_rollout_overhead_seconds)
    whole_epoch = _finite_number("measured_whole_epoch_seconds",
                                 measured_whole_epoch_seconds)
    if consumed < 0 or reserve < 0 or overhead < 0:
        raise InfrastructureError(
            "consumed/reserve/overhead seconds must be non-negative")
    if whole_epoch <= 0:
        raise InfrastructureError(
            "measured whole-epoch duration must be positive")
    ceiling = contract.sizing.operational_ceiling_hours * 3600.0
    inputs = {
        "operational_ceiling_seconds": ceiling,
        "cumulative_consumed_seconds": consumed,
        "measured_finalization_reserve_seconds": reserve,
        "frozen_non_rollout_overhead_seconds": overhead,
        "measured_whole_epoch_seconds": whole_epoch,
    }
    if tuple(inputs) != REGISTERED_CAPACITY_INPUTS:
        raise InfrastructureError(
            "capacity inputs diverge from the registered tuple")
    available = ceiling - consumed - reserve - overhead
    capacity = int(math.floor(available / whole_epoch)) \
        if available > 0 else 0
    return {
        "inputs": inputs,
        "available_generation_seconds": round(available, 1),
        "capacity_epochs": max(capacity, 0),
    }


def derive_launch_plan(contract: P0ScienceContract, *,
                       cumulative_consumed_seconds: float,
                       measured_finalization_reserve_seconds: float,
                       frozen_non_rollout_overhead_seconds: float,
                       measured_whole_epoch_seconds: float
                       ) -> dict[str, Any]:
    """The complete 305_f §5 record: every cap input and ALL THREE
    values (nominal/capacity/launch), the closed branch action, and
    the quantified under-target disclosure. The later
    `P0LaunchFreeze` persists this record verbatim."""
    _validate_cap_rule(contract)
    cap = contract.sizing.cap
    capacity_record = derive_capacity(
        contract,
        cumulative_consumed_seconds=cumulative_consumed_seconds,
        measured_finalization_reserve_seconds=
        measured_finalization_reserve_seconds,
        frozen_non_rollout_overhead_seconds=
        frozen_non_rollout_overhead_seconds,
        measured_whole_epoch_seconds=measured_whole_epoch_seconds)
    nominal = contract.sizing.nominal_epochs
    capacity = capacity_record["capacity_epochs"]
    launch = min(nominal, capacity)
    plan: dict[str, Any] = {
        "cap_rule_id": cap.rule_id,
        "inputs": capacity_record["inputs"],
        "available_generation_seconds":
            capacity_record["available_generation_seconds"],
        "nominal_epochs": nominal,
        "capacity_epochs": capacity,
        "launch_epochs": launch,
    }
    if capacity <= 0:
        plan["branch"] = cap.capacity_zero_action
        plan["launchable"] = False
    elif capacity < nominal:
        plan["branch"] = cap.under_target_action
        plan["launchable"] = True
        # the quantified disclosure: achieved projected exposure =
        # launch_epochs x the measured per-epoch counted rate
        plan["projected_q1_counted_by_cell"] = {
            cell: round(launch * count / contract.q1.sizing_epochs,
                        1)
            for cell, count in contract.q1.sizing_counts}
        plan["target_q1_counted_groups_per_sizing_cell"] = \
            contract.sizing \
            .target_q1_counted_groups_per_sizing_cell
    else:
        plan["branch"] = cap.spare_capacity_action
        plan["launchable"] = True
        # spare capacity is RECORDED and never trained
        plan["spare_epochs_not_trained"] = capacity - nominal
    return plan


def _strict_equal(a: Any, b: Any) -> bool:
    """Type-SENSITIVE deep equality (316_s P1): bool is never an
    int, int is never a float, NaN never equals anything."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return set(a) == set(b) \
            and all(_strict_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) \
            and all(_strict_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, float):
        return a == b and not math.isnan(a)
    return a == b


def require_launchable(contract: P0ScienceContract,
                       plan: dict[str, Any]) -> dict[str, Any]:
    """The consuming boundary for launch construction (316_s P1):
    the supplied plan is NEVER trusted — the complete plan is
    REDERIVED from its persisted inputs under the authenticated
    contract and compared type-sensitively; only then is the
    genuine stop branch rejected. A forged branch, epoch count, or
    boolean/NaN value refuses at the rederivation."""
    _validate_cap_rule(contract)
    if not isinstance(plan, dict) or not isinstance(
            plan.get("inputs"), dict) \
            or tuple(plan["inputs"]) != REGISTERED_CAPACITY_INPUTS:
        raise InfrastructureError(
            "the supplied plan does not carry the registered input "
            "record (316_s P1)")
    inputs = plan["inputs"]
    rederived = derive_launch_plan(
        contract,
        cumulative_consumed_seconds=inputs[
            "cumulative_consumed_seconds"],
        measured_finalization_reserve_seconds=inputs[
            "measured_finalization_reserve_seconds"],
        frozen_non_rollout_overhead_seconds=inputs[
            "frozen_non_rollout_overhead_seconds"],
        measured_whole_epoch_seconds=inputs[
            "measured_whole_epoch_seconds"])
    if not _strict_equal(rederived, plan):
        raise InfrastructureError(
            "the supplied launch plan does not rederive from its "
            "persisted inputs under the authenticated contract "
            "(316_s P1) — a forged plan is never launchable")
    if rederived["branch"] == \
            contract.sizing.cap.capacity_zero_action \
            or not rederived["launchable"] \
            or rederived["launch_epochs"] <= 0:
        raise InfrastructureError(
            "capacity_epochs <= 0: stop for a reviewed scope "
            "amendment (305_f §5) — no launch is derivable from "
            "this plan")
    return plan
