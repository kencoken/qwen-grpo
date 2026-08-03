"""P0 spine, Unit 2 — the STRICT schedule loader (302_s §4; 303_f
§4).

`p0_schedule` is a loader/validator of the COMMITTED pinned-mixture
artifact — never a builder. It contains NO import of the legacy
builder (`build_mixture_v2`) anywhere in the module, and the tests
prove it operates with the legacy builder DISABLED and from a
clean-clone-restored surface (the 305_f approval reminders).

- `epoch_schedule(contract)` — the frozen 157-row epoch, validated
  against the contract pins (double-bound artifact: file hash AND
  self-hash from `input_pins`);
- `schedule_for_epochs(contract, epochs)` — N identical passes; the
  epoch count arrives from the LATER `P0LaunchFreeze`, never chosen
  here;
- `build_trainer_rows(contract, epochs, surface_dir=None)` — the
  trainer dataset rows regenerated from the LOCKED extension
  surface (restored clean-clone if absent), each regenerated
  instance identity-checked against its scheduled observation id."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tasks.conductor.types import InfrastructureError

from .p0_replay import (
    load_pinned_mixture,
    restore_extension_surface_if_absent,
)
from .p0_schema import P0ScienceContract


def _validated_mixture(contract: P0ScienceContract
                       ) -> dict[str, Any]:
    """Load the committed artifact under the CONTRACT's pins (both
    bindings)."""
    mixture = load_pinned_mixture(
        expected_file_sha256=contract.input_pins
        .pinned_mixture_file_sha256)
    if mixture["record_sha256"] != \
            contract.input_pins.pinned_mixture_record_sha256:
        raise InfrastructureError(
            "the pinned-mixture artifact does not match the "
            "contract's record pin")
    return mixture


def epoch_schedule(contract: P0ScienceContract) -> list[str]:
    """The frozen one-epoch schedule (157 observation ids in the
    frozen shuffled order), from the committed artifact only."""
    mixture = _validated_mixture(contract)
    rows = list(mixture["schedule_rows"])
    if len(rows) != contract.sizing.groups_per_epoch:
        raise InfrastructureError(
            f"the pinned epoch has {len(rows)} rows; the contract "
            f"requires {contract.sizing.groups_per_epoch}")
    return rows


def schedule_for_epochs(contract: P0ScienceContract,
                        epochs: int) -> list[str]:
    """N identical frozen passes. The epoch count is supplied by the
    P0LaunchFreeze (min(nominal, capacity)); this loader only bounds
    it."""
    if not isinstance(epochs, int) or isinstance(epochs, bool) \
            or epochs <= 0:
        raise InfrastructureError(
            "epochs must be a positive non-boolean integer")
    if epochs > contract.sizing.nominal_epochs:
        raise InfrastructureError(
            f"epochs {epochs} exceeds the contract's nominal "
            f"{contract.sizing.nominal_epochs} — spare capacity "
            "never authorizes extra training (304_s §5)")
    return epoch_schedule(contract) * epochs


def population_of(contract: P0ScienceContract,
                  mixture: dict[str, Any], oid: str) -> str:
    """The effective population map (sentinel override by the
    CONTRACT's frozen ids)."""
    if oid in set(contract.scope.sentinel_observation_ids):
        return "sentinel"
    cls = mixture["class_assignment"].get(oid)
    if cls is None:
        raise InfrastructureError(
            f"{oid}: not a scheduled observation of the pinned "
            "mixture")
    return cls


def build_trainer_rows(contract: P0ScienceContract, epochs: int,
                       surface_dir: str | Path | None = None
                       ) -> list[dict[str, Any]]:
    """The trainer dataset rows for `epochs` frozen passes,
    regenerated from the LOCKED extension surface — clean-clone
    capable (the surface is restored from committed evidence when
    absent), and every regenerated instance is identity-checked."""
    from tasks.conductor import program
    from tasks.conductor.policy import policy_messages
    from tasks.conductor.profiles import DEFAULT_PROFILE
    from tasks.conductor.stage1 import prompt_fewshot

    from .dev_support import load_dev_surface
    if surface_dir is None:
        surface_dir = restore_extension_surface_if_absent()
    loaded = load_dev_surface(
        surface_dir,
        expected_lock_sha256=contract.input_pins
        .extension_surface_lock_sha256)
    meta = {obs["observation_id"]: obs
            for obs in loaded["observations"]}
    schedule = schedule_for_epochs(contract, epochs)
    system = prompt_fewshot()
    per_oid_cache: dict[str, dict[str, Any]] = {}
    rows = []
    for oid in schedule:
        if oid not in per_oid_cache:
            obs = meta.get(oid)
            if obs is None:
                raise InfrastructureError(
                    f"{oid}: scheduled observation is not on the "
                    "locked surface")
            latent = program.generate_latent(
                obs["cell_id"], "routing_dev",
                int(oid.split(":")[2]), DEFAULT_PROFILE).latent
            inst = program.render_instance(
                latent, obs["renderer_id"], oid.split(":")[5])
            if inst["render_instance_id"] != oid:
                raise InfrastructureError(
                    f"regenerated instance != scheduled {oid}")
            steps = [{"subtask": s["subtask"],
                      "resource": s["resource"],
                      "access": s["access"]}
                     for s in program.workflow_steps(latent)]
            user = policy_messages(inst, steps)[1]
            per_oid_cache[oid] = {
                "prompt": [{"role": "system", "content": system},
                           dict(user)],
                "observation_id": oid,
                "cell_id": obs["cell_id"],
                "num_steps": len(steps),
                "positions": json.dumps(
                    latent["reference_program"]["positions"]),
            }
        rows.append(dict(per_oid_cache[oid]))
    return rows
