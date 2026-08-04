"""P0 spine, Unit 5 — the P0LaunchFreeze schema and the FIRST REAL
CONSUMER (303_f §2/§9 step 5; 305_f §1/§5).

The `P0LaunchFreeze` (schema `p0-launch-freeze-v1`) carries: the
science-contract hash; the val/cycle/beta reviewed-output pins;
the ACTUAL epoch cap — the `derive_launch_plan` record persisted
VERBATIM (typed here, with a strict round-trip proof back to the
record); and the intrinsic runtime/seed identities plus the
COMMIT-INDEPENDENT attested-environment expectation. By the closed
schema it CANNOT carry an execution-manifest hash (an external
launch argument) nor any terminal output hash (closeouts only) —
the 305_f §1 identity graph is enforced by construction. The
INSTANCE is constructed only after the val/cycle/beta inputs exist
(post-merge); this unit freezes the schema, the builder, and the
consuming path.

`prepare_p0_dataset` is the first real consumer — DATASET
PREPARATION, never launch admission (321_s): every input flows
through a reviewed pin (the freeze under its externally reviewed
hash — REQUIRED, a self-hash is never authentication; the contract
under the reviewed pin), the launch plan is REDERIVED
(`require_launchable`), the runtime identity is BOUND to the
canonical `P0_RUNTIME_PROFILE` and the ACTUAL prompt
(`bind_runtime_identity`), the standing oracles run FRESH
(`verify_c2_equivalence` — which authenticates the complete replay
source — and `verify_appendix`), and the trainer dataset is built
by the STRICT schedule loader for exactly `launch_epochs` frozen
epochs. Launch admission itself (precursor artifacts resolved
under their pins; the execution-manifest EXTERNAL argument;
environment attestation; cadence/eval/telemetry identity) is
EXPLICITLY DEFERRED to the post-merge unit constructing the real
instance and its authenticated `P0ExecutionIdentity`.

`assemble_sentinel_trajectories` closes the deferred 305_f §4
obligation: the per-checkpoint sentinel blocks are assembled into
the `checkpoint_trajectory` / `evaluation_trajectory` structures
under the exact frozen index sets, the producer invariants, and
explicit infrastructure-abort handling."""
from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Mapping, Sequence

from tasks.conductor.types import InfrastructureError

from .charter import content_sha256
from .p0_cap import (
    REGISTERED_CAPACITY_INPUTS,
    _strict_equal,
    require_launchable,
)
from .p0_contract import load_p0_science_contract
from .p0_replay import P0_DIR
from .p0_schema import (
    P0ScienceContract,
    _require_finite,
    _require_hex64,
    _require_positive_int,
    contract_sha256,
)

SCHEMA_VERSION = "p0-launch-freeze-v1"
LAUNCH_FREEZE_PATH = P0_DIR / "p0_launch_freeze.json"

_LAUNCH_BRANCHES = ("disclosed_under_target", "no_extra_training")

# --- the canonical complete P0 runtime profile (321_s/323_s P1) ----------------
# The construction sections are the Step-5-validated literals
# (cross-checked against the hash-guarded C2 config at every
# binding). The training deltas are the SIGNED Stage-0 launch
# profile (13_f/106_s/120_f; implemented in
# grpo_smoke.STAGE0C_LAUNCH_PROFILE): beta 1e-3, lr 1e-5, 10-step
# warmup realized as `constant_with_warmup` (323_s: plain
# "constant" IGNORES warmup_steps). The 2x4 batch shape at one
# group per optimizer update is CONTROLLED by the 246_f
# resume-validation execution, which validated real optimizer
# updates in exactly that shape. The previously hard-coded trainer
# settings (shuffle, gradient checkpointing + kwargs, model dtype,
# attention implementation) are PINNED here (323_s). Checkpoint/
# evaluation cadence, eval decoding, and telemetry identity are
# NOT here — they are bound later through the authenticated
# P0ExecutionIdentity and remain explicitly deferred.
P0_RUNTIME_PROFILE: dict[str, Any] = {
    "kind": "p0-runtime-profile-v1",
    "model_id": "Qwen/Qwen2.5-3B-Instruct",
    "revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
    "quantization": {"load_in_4bit": True, "quant_type": "nf4",
                     "double_quant": True,
                     "compute_dtype": "bfloat16"},
    "lora": {"r": 16, "alpha": 32, "dropout": 0.05,
             "adapter_dtype": "float32",
             "targets": ["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"]},
    "grpo": {"beta": 1e-3, "group_size": 8, "temperature": 1.0,
             "per_device_batch": 2, "grad_accum": 4,
             "learning_rate": 1e-5, "warmup_steps": 10,
             "scheduler": "constant_with_warmup", "loss": "dapo",
             "optim": "adamw_torch", "bf16": True},
    "policy_max_new_tokens": 128,
    "full_determinism": True,
    "updates_per_group": 1,
    "worker_outcome_mode": "precomputed_surface",
    "trainer_settings": {
        "shuffle_dataset": False,
        "gradient_checkpointing": True,
        "gradient_checkpointing_kwargs": {"use_reentrant": False},
        "model_dtype": "bfloat16",
        "attn_implementation": "sdpa",
    },
    "lora_key_set": {
        "count": 504,
        "sorted_keys_sha256":
            "e44ecb9caf0be396aaaceae6802dbaab9209677103ba263c89"
            "ca9a7ea65f6215",
    },
}
P0_RUNTIME_PROFILE_SHA256 = \
    "202bc3773f9f4d4fa4ccc1842c17199aabd8d8f5c532bda7826c7af53fa08ceb"


def _validated_profile() -> dict[str, Any]:
    """The profile under BOTH its own pin and the validated
    construction: every construction section must equal the
    hash-guarded C2 config's section (the Step-5-validated
    literals), and the training deltas must be the signed launch
    profile."""
    from .unit_c2_sample import CONFIG_SHA256, UNIT_C2_CONFIG
    if content_sha256(P0_RUNTIME_PROFILE) \
            != P0_RUNTIME_PROFILE_SHA256:
        raise InfrastructureError(
            "P0_RUNTIME_PROFILE was mutated after import (321_s)")
    if content_sha256(UNIT_C2_CONFIG) != CONFIG_SHA256:
        raise InfrastructureError(
            "UNIT_C2_CONFIG was mutated after import")
    profile = P0_RUNTIME_PROFILE
    for key in ("model_id", "policy_max_new_tokens",
                "full_determinism"):
        source = "model_id" if key == "model_id" else key
        if profile[key] != UNIT_C2_CONFIG[source]:
            raise InfrastructureError(
                f"profile {key} diverges from the validated "
                "construction")
    if profile["revision"] != UNIT_C2_CONFIG["revision"] \
            or profile["quantization"] \
            != UNIT_C2_CONFIG["quantization"] \
            or profile["lora"] != UNIT_C2_CONFIG["lora"] \
            or profile["lora_key_set"] \
            != UNIT_C2_CONFIG["lora_key_set"]:
        raise InfrastructureError(
            "profile construction sections diverge from the "
            "validated (hash-guarded) C2 literals")
    c2_grpo = UNIT_C2_CONFIG["grpo"]
    for key in ("group_size", "temperature", "per_device_batch",
                "grad_accum", "loss", "optim", "bf16"):
        if profile["grpo"][key] != c2_grpo[key]:
            raise InfrastructureError(
                f"profile grpo.{key} diverges from the validated "
                "construction")
    # the training deltas are the SIGNED Stage-0 launch profile;
    # the scheduler is a delta by design (the C2 zero-update run
    # used plain constant with zero warmup) and must be the
    # warmup-implementing variant (323_s)
    if profile["grpo"]["beta"] != 1e-3 \
            or profile["grpo"]["learning_rate"] != 1e-5 \
            or profile["grpo"]["warmup_steps"] != 10 \
            or profile["grpo"]["scheduler"] \
            != "constant_with_warmup":
        raise InfrastructureError(
            "profile training deltas diverge from the signed "
            "launch profile (beta 1e-3, lr 1e-5, warmup 10, "
            "constant_with_warmup)")
    if profile["trainer_settings"] != {
            "shuffle_dataset": False,
            "gradient_checkpointing": True,
            "gradient_checkpointing_kwargs":
                {"use_reentrant": False},
            "model_dtype": "bfloat16",
            "attn_implementation": "sdpa"}:
        raise InfrastructureError(
            "profile trainer settings diverge from the signed "
            "hard-coded construction (323_s)")
    return profile


def _require_nonneg_number(value: Any, where: str) -> None:
    _require_finite(value, where)
    if value < 0:
        raise InfrastructureError(f"{where}: must be non-negative")


@dataclass(frozen=True)
class PrecursorOutputs:
    """The reviewed-output pins of the precursor freezes (303_f §2:
    'the launch freeze pins their reviewed outputs')."""
    routing_dev_val_lock_sha256: str
    cycle_record_sha256: str
    r_cycle_record_sha256: str
    beta_smoke_record_sha256: str

    def __post_init__(self) -> None:
        for field in fields(self):
            _require_hex64(getattr(self, field.name),
                           f"precursors.{field.name}")


@dataclass(frozen=True)
class CapInputs:
    """The registered capacity inputs, persisted verbatim."""
    operational_ceiling_seconds: float
    cumulative_consumed_seconds: float
    measured_finalization_reserve_seconds: float
    frozen_non_rollout_overhead_seconds: float
    measured_whole_epoch_seconds: float

    def __post_init__(self) -> None:
        if tuple(f.name for f in fields(self)) \
                != REGISTERED_CAPACITY_INPUTS:
            raise InfrastructureError(
                "CapInputs fields diverge from the registered "
                "tuple")
        for field in fields(self):
            _require_nonneg_number(getattr(self, field.name),
                                   f"cap inputs.{field.name}")
        if self.measured_whole_epoch_seconds <= 0 \
                or self.operational_ceiling_seconds <= 0:
            raise InfrastructureError(
                "whole-epoch and ceiling seconds must be positive")


@dataclass(frozen=True)
class LaunchPlan:
    """The 305_f §5 record, typed: every input and ALL THREE values
    (nominal/capacity/launch) with the closed launchable branch.
    The stop branch can NEVER be frozen — a freeze exists only for
    a launchable plan."""
    cap_rule_id: str
    inputs: CapInputs
    available_generation_seconds: float
    nominal_epochs: int
    capacity_epochs: int
    launch_epochs: int
    branch: str
    launchable: bool
    projected_q1_counted_by_cell: tuple[tuple[str, float], ...] | None
    target_q1_counted_groups_per_sizing_cell: int | None
    spare_epochs_not_trained: int | None

    def __post_init__(self) -> None:
        if self.cap_rule_id != "p0-cap-v1":
            raise InfrastructureError(
                f"unknown cap rule {self.cap_rule_id!r}")
        _require_finite(self.available_generation_seconds,
                        "plan.available_generation_seconds")
        _require_positive_int(self.nominal_epochs,
                              "plan.nominal_epochs")
        _require_positive_int(self.capacity_epochs,
                              "plan.capacity_epochs")
        _require_positive_int(self.launch_epochs,
                              "plan.launch_epochs")
        if self.launchable is not True:
            raise InfrastructureError(
                "a launch freeze exists only for a launchable plan "
                "(the stop branch is a reviewed-amendment decision)")
        if self.launch_epochs != min(self.nominal_epochs,
                                     self.capacity_epochs):
            raise InfrastructureError(
                "launch_epochs != min(nominal, capacity) (305_f §5)")
        if self.branch not in _LAUNCH_BRANCHES:
            raise InfrastructureError(
                f"branch {self.branch!r} is not a launchable branch")
        under = self.branch == "disclosed_under_target"
        if under:
            if self.projected_q1_counted_by_cell is None \
                    or self.target_q1_counted_groups_per_sizing_cell \
                    is None or self.spare_epochs_not_trained \
                    is not None:
                raise InfrastructureError(
                    "the under-target branch must carry its "
                    "quantified disclosure and no spare field")
            for cell, value in self.projected_q1_counted_by_cell:
                _require_nonneg_number(
                    value, f"plan.projected[{cell}]")
            _require_positive_int(
                self.target_q1_counted_groups_per_sizing_cell,
                "plan.target_q1_counted_groups_per_sizing_cell")
        else:
            if self.projected_q1_counted_by_cell is not None \
                    or self.target_q1_counted_groups_per_sizing_cell \
                    is not None or self.spare_epochs_not_trained \
                    is None:
                raise InfrastructureError(
                    "the spare-capacity branch must carry the spare "
                    "count and no under-target fields")
            if not isinstance(self.spare_epochs_not_trained, int) \
                    or isinstance(self.spare_epochs_not_trained,
                                  bool) \
                    or self.spare_epochs_not_trained < 0:
                raise InfrastructureError(
                    "plan.spare_epochs_not_trained must be a "
                    "non-negative non-boolean integer")

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "LaunchPlan":
        expected_keys = {
            "cap_rule_id", "inputs",
            "available_generation_seconds", "nominal_epochs",
            "capacity_epochs", "launch_epochs", "branch",
            "launchable"}
        optional = {"projected_q1_counted_by_cell",
                    "target_q1_counted_groups_per_sizing_cell",
                    "spare_epochs_not_trained"}
        if not isinstance(record, Mapping) \
                or not expected_keys <= set(record) \
                or not set(record) <= expected_keys | optional:
            raise InfrastructureError(
                "launch-plan record keys diverge from the "
                "registered shape")
        projected = record.get("projected_q1_counted_by_cell")
        return cls(
            cap_rule_id=record["cap_rule_id"],
            inputs=CapInputs(**record["inputs"]),
            available_generation_seconds=record[
                "available_generation_seconds"],
            nominal_epochs=record["nominal_epochs"],
            capacity_epochs=record["capacity_epochs"],
            launch_epochs=record["launch_epochs"],
            branch=record["branch"],
            launchable=record["launchable"],
            projected_q1_counted_by_cell=(
                tuple(sorted((str(k), v)
                             for k, v in projected.items()))
                if projected is not None else None),
            target_q1_counted_groups_per_sizing_cell=record.get(
                "target_q1_counted_groups_per_sizing_cell"),
            spare_epochs_not_trained=record.get(
                "spare_epochs_not_trained"))

    def to_record(self) -> dict[str, Any]:
        """The VERBATIM `derive_launch_plan` record (the 316_s/318_s
        admission boundary consumes exactly this shape)."""
        record: dict[str, Any] = {
            "cap_rule_id": self.cap_rule_id,
            "inputs": {name: getattr(self.inputs, name)
                       for name in REGISTERED_CAPACITY_INPUTS},
            "available_generation_seconds":
                self.available_generation_seconds,
            "nominal_epochs": self.nominal_epochs,
            "capacity_epochs": self.capacity_epochs,
            "launch_epochs": self.launch_epochs,
            "branch": self.branch,
            "launchable": self.launchable,
        }
        if self.branch == "disclosed_under_target":
            record["projected_q1_counted_by_cell"] = dict(
                self.projected_q1_counted_by_cell)
            record["target_q1_counted_groups_per_sizing_cell"] = \
                self.target_q1_counted_groups_per_sizing_cell
        else:
            record["spare_epochs_not_trained"] = \
                self.spare_epochs_not_trained
        return record


@dataclass(frozen=True)
class RuntimeIdentity:
    """The intrinsic runtime/seed fields plus the
    COMMIT-INDEPENDENT attested-environment expectation (305_f §1).
    The execution-manifest hash is NOT a field — it remains an
    external launch argument by the closed schema."""
    model_id: str
    model_revision: str
    quantization: str
    lora_adapter_dtype: str
    lora_key_set_sha256: str
    prompt_sha256: str
    runtime_profile_sha256: str
    group_size: int
    seed: int
    temperature: float
    learning_rate: float
    beta: float
    policy_max_new_tokens: int
    attested_environment_sha256: str

    def __post_init__(self) -> None:
        if not self.model_id or not isinstance(self.model_id, str):
            raise InfrastructureError("runtime.model_id required")
        if not isinstance(self.model_revision, str) \
                or len(self.model_revision) != 40 \
                or any(c not in "0123456789abcdef"
                       for c in self.model_revision):
            raise InfrastructureError(
                "runtime.model_revision must be a 40-hex commit")
        if self.quantization != "nf4" \
                or self.lora_adapter_dtype != "float32":
            raise InfrastructureError(
                "runtime quantization/adapter dtype outside the "
                "validated construction (nf4 + fp32 LoRA)")
        for name in ("lora_key_set_sha256", "prompt_sha256",
                     "runtime_profile_sha256",
                     "attested_environment_sha256"):
            _require_hex64(getattr(self, name), f"runtime.{name}")
        for name in ("group_size", "seed",
                     "policy_max_new_tokens"):
            _require_positive_int(getattr(self, name),
                                  f"runtime.{name}")
        for name in ("temperature", "learning_rate", "beta"):
            _require_finite(getattr(self, name), f"runtime.{name}")
        if self.temperature <= 0 or self.learning_rate <= 0 \
                or self.beta < 0:
            raise InfrastructureError(
                "P0 runs REAL training: temperature and "
                "learning_rate must be positive, beta non-negative")


def bind_runtime_identity(runtime: RuntimeIdentity) -> None:
    """321_s P1: the runtime identity must BIND to the canonical
    validated profile and to the ACTUAL prompt — a freeze declaring
    a different prompt, profile, or design hyperparameter is not an
    identity of this experiment. Run at every build AND at every
    preparation (a hand-crafted freeze file refuses here even
    though it loads structurally)."""
    import hashlib
    from tasks.conductor.stage1 import prompt_fewshot
    profile = _validated_profile()
    if runtime.runtime_profile_sha256 != P0_RUNTIME_PROFILE_SHA256:
        raise InfrastructureError(
            "runtime does not pin the canonical P0 runtime profile "
            "(321_s)")
    actual_prompt = hashlib.sha256(
        prompt_fewshot().encode("utf-8")).hexdigest()
    if runtime.prompt_sha256 != actual_prompt:
        raise InfrastructureError(
            "runtime.prompt_sha256 does not match the ACTUAL "
            "policy prompt — the freeze does not bind the "
            "execution it authorizes (321_s)")
    grpo = profile["grpo"]
    bindings = (
        ("model_id", runtime.model_id, profile["model_id"]),
        ("model_revision", runtime.model_revision,
         profile["revision"]),
        ("quantization", runtime.quantization,
         profile["quantization"]["quant_type"]),
        ("lora_adapter_dtype", runtime.lora_adapter_dtype,
         "float32"),
        ("lora_key_set_sha256", runtime.lora_key_set_sha256,
         profile["lora_key_set"]["sorted_keys_sha256"]),
        ("group_size", runtime.group_size, grpo["group_size"]),
        ("temperature", runtime.temperature, grpo["temperature"]),
        ("learning_rate", runtime.learning_rate,
         grpo["learning_rate"]),
        ("beta", runtime.beta, grpo["beta"]),
        ("policy_max_new_tokens", runtime.policy_max_new_tokens,
         profile["policy_max_new_tokens"]),
    )
    for name, declared, canonical in bindings:
        if declared != canonical:
            raise InfrastructureError(
                f"runtime.{name} = {declared!r} diverges from the "
                f"canonical profile value {canonical!r} (321_s — "
                "the design hyperparameters are frozen)")
    if profile["lora"]["adapter_dtype"] != "float32":
        raise InfrastructureError(
            "profile adapter dtype outside the validated "
            "construction")


@dataclass(frozen=True)
class P0LaunchFreeze:
    schema_version: str
    science_contract_sha256: str
    precursors: PrecursorOutputs
    launch_plan: LaunchPlan
    runtime: RuntimeIdentity

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise InfrastructureError(
                f"unknown launch-freeze schema "
                f"{self.schema_version!r}")
        _require_hex64(self.science_contract_sha256,
                       "science_contract_sha256")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, (PrecursorOutputs, CapInputs,
                          RuntimeIdentity)):
        return {f.name: getattr(value, f.name)
                for f in fields(value)}
    if isinstance(value, LaunchPlan):
        return value.to_record()
    return value


def canonical_freeze_json(freeze: P0LaunchFreeze) -> str:
    payload = {f.name: _to_jsonable(getattr(freeze, f.name))
               for f in fields(freeze)}
    return json.dumps(payload, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def freeze_sha256(freeze: P0LaunchFreeze) -> str:
    return content_sha256(json.loads(canonical_freeze_json(freeze)))


def build_p0_launch_freeze(*, plan_record: Mapping[str, Any],
                           precursors: Mapping[str, str],
                           runtime: Mapping[str, Any],
                           contract: P0ScienceContract | None = None
                           ) -> P0LaunchFreeze:
    """Constructed only after the val/cycle/beta inputs exist. The
    plan record is admitted through the Unit-4 boundary (REDERIVED
    under the authenticated contract; the stop branch refuses), and
    the typed plan must round-trip to the record VERBATIM."""
    contract = contract or load_p0_science_contract()
    require_launchable(contract, dict(plan_record))
    runtime_identity = RuntimeIdentity(**dict(runtime))
    bind_runtime_identity(runtime_identity)
    freeze = P0LaunchFreeze(
        schema_version=SCHEMA_VERSION,
        science_contract_sha256=contract_sha256(contract),
        precursors=PrecursorOutputs(**dict(precursors)),
        launch_plan=LaunchPlan.from_record(plan_record),
        runtime=runtime_identity)
    if not _strict_equal(freeze.launch_plan.to_record(),
                         dict(plan_record)):
        raise InfrastructureError(
            "the typed launch plan does not round-trip to the "
            "derive_launch_plan record VERBATIM (305_f §5)")
    return freeze


def save_launch_freeze(freeze: P0LaunchFreeze,
                       out_path: str | Path = LAUNCH_FREEZE_PATH
                       ) -> str:
    out_path = Path(out_path)
    if out_path.exists():
        raise InfrastructureError(
            f"{out_path} exists; the launch freeze is written "
            "exactly once")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(canonical_freeze_json(freeze))
    digest = content_sha256(payload)
    payload["freeze_sha256"] = digest
    out_path.write_text(
        json.dumps(payload, indent=1, sort_keys=True,
                   allow_nan=False) + "\n", encoding="utf-8")
    return digest


def load_p0_launch_freeze(path: str | Path,
                          expected_sha256: str) -> P0LaunchFreeze:
    """The strict closed loader. The externally reviewed hash is
    REQUIRED — a self-hash alone is never authentication (303_f
    §7); there is no default pin until a real instance is reviewed."""
    _require_hex64(expected_sha256, "expected_sha256")
    payload = json.loads(Path(path).read_text("utf-8"))
    if not isinstance(payload, dict):
        raise InfrastructureError("launch freeze must be an object")
    stored = payload.pop("freeze_sha256", None)
    if content_sha256(payload) != stored \
            or stored != expected_sha256:
        raise InfrastructureError(
            "launch freeze does not rehash to the externally "
            "reviewed value")
    expected_fields = {f.name for f in fields(P0LaunchFreeze)}
    if set(payload) != expected_fields:
        raise InfrastructureError(
            "launch-freeze fields diverge from the closed schema")
    for name, cls in (("precursors", PrecursorOutputs),
                      ("runtime", RuntimeIdentity)):
        section = payload[name]
        if not isinstance(section, dict) or set(section) \
                != {f.name for f in fields(cls)}:
            raise InfrastructureError(
                f"{name}: fields diverge from the closed schema")
    freeze = P0LaunchFreeze(
        schema_version=payload["schema_version"],
        science_contract_sha256=payload["science_contract_sha256"],
        precursors=PrecursorOutputs(**payload["precursors"]),
        launch_plan=LaunchPlan.from_record(payload["launch_plan"]),
        runtime=RuntimeIdentity(**payload["runtime"]))
    if freeze_sha256(freeze) != expected_sha256:
        raise InfrastructureError(
            "reconstructed launch freeze does not rehash to the "
            "reviewed value")
    return freeze


# --- the first real consumer: DATASET PREPARATION ------------------------------
# 321_s P1: this is dataset preparation, NOT launch admission.
# Launch admission is EXPLICITLY DEFERRED to the post-merge unit
# that constructs the real P0LaunchFreeze instance: the precursor
# artifacts must be resolved and verified under their pinned hashes
# (they do not exist yet), the execution manifest must arrive as
# the EXTERNAL launch argument (305_f §1) and bind against the
# freeze, the environment manifest must attest to the freeze's
# expectation, and cadence/eval-decoding/telemetry identity must be
# frozen. None of that can be genuinely enforced before those
# artifacts exist, so it is NOT marked complete anywhere.

LAUNCH_ADMISSION_OUTSTANDING = (
    "precursor artifacts (routing_dev_val lock, cycle, R_cycle, "
    "beta smoke) resolved and verified under their pinned hashes",
    "execution-manifest binding — the EXTERNAL launch argument "
    "(305_f §1) — against the freeze's runtime identity",
    "environment-manifest attestation against "
    "runtime.attested_environment_sha256",
    "checkpoint/evaluation cadence, evaluation decoding, and "
    "telemetry identity (bound through the authenticated "
    "P0ExecutionIdentity)",
)


def prepare_p0_dataset(freeze_path: str | Path,
                       expected_freeze_sha256: str,
                       evidence_dir: str | Path | None = None
                       ) -> dict[str, Any]:
    """DATASET PREPARATION (the first real consumer): freeze under
    its reviewed hash; contract under its reviewed pin; the launch
    plan REDERIVED; the runtime identity BOUND to the canonical
    profile and the ACTUAL prompt; the standing oracles run FRESH;
    the trainer dataset built by the strict schedule loader.
    Returns an explicit DEFERRED launch-admission block — this
    function never authorizes an execution."""
    from .p0_c2_equivalence import verify_c2_equivalence
    from .p0_schedule import build_trainer_rows, schedule_for_epochs
    from .p0_tables import verify_appendix
    freeze = load_p0_launch_freeze(freeze_path,
                                   expected_freeze_sha256)
    contract = load_p0_science_contract()
    if freeze.science_contract_sha256 != contract_sha256(contract):
        raise InfrastructureError(
            "the launch freeze pins a different science contract")
    plan = freeze.launch_plan.to_record()
    require_launchable(contract, plan)
    bind_runtime_identity(freeze.runtime)
    equivalence = verify_c2_equivalence(evidence_dir)
    appendix = verify_appendix()
    launch_epochs = freeze.launch_plan.launch_epochs
    schedule = schedule_for_epochs(contract, launch_epochs)
    rows = build_trainer_rows(contract, launch_epochs)
    if [row["observation_id"] for row in rows] != schedule:
        raise InfrastructureError(
            "trainer rows diverge from the frozen schedule")
    return {
        "freeze_sha256": expected_freeze_sha256,
        "science_contract_sha256":
            freeze.science_contract_sha256,
        "launch_epochs": launch_epochs,
        "groups_total": len(rows),
        "schedule": schedule,
        "trainer_rows": rows,
        "runtime": freeze.runtime,
        "gates": {
            "launch_plan": "REDERIVED",
            "runtime_binding": "BOUND",
            "c2_equivalence": equivalence["verdict"],
            "appendix": appendix["verdict"],
        },
        "launch_admission": {
            "status": "DEFERRED",
            "deferred_to": "the post-merge P0 launch-admission "
                           "unit (the real P0LaunchFreeze "
                           "instance and its authenticated "
                           "P0ExecutionIdentity)",
            "outstanding": LAUNCH_ADMISSION_OUTSTANDING,
        },
    }


# --- the deferred trajectory assembly (305_f §4) -------------------------------

_PER_CHECKPOINT_SENTINEL_FIELDS = (
    "cell", "training_exposed", "observation_ids",
    "group_denominator", "completion_denominator",
    "worker1_selections", "worker1_completions",
    "reward1_completions", "reward_varying_groups",
    "q1_counted_groups", "first_group_indices",
    "first_update_indices")


_SENTINEL_COUNTER_FIELDS = (
    "group_denominator", "completion_denominator",
    "worker1_selections", "worker1_completions",
    "reward1_completions", "reward_varying_groups",
    "q1_counted_groups")

# counter -> the firsts family that must be set iff the counter > 0
_COUNTER_FIRSTS = (
    ("worker1_selections", "worker1"),
    ("reward1_completions", "reward1"),
    ("reward_varying_groups", "varying"),
    ("q1_counted_groups", "q1_counted"))


def _validate_sentinel_block(name: str, index: int,
                             block: Mapping[str, Any],
                             contract: P0ScienceContract,
                             group_size: int,
                             updates_per_group: int
                             ) -> dict[str, Any]:
    """321_s/323_s P1: SEMANTIC validation of one per-checkpoint
    block — exposure, counters, denominators, bounds, the PRODUCER
    invariants (selections == completions; completion denominator
    == groups x the frozen group size; update index == group index
    x updates-per-group), and count/first-index consistency in
    both index spaces."""
    where = f"{name}[{index}]"
    if not isinstance(block, Mapping) or set(block) \
            != set(_PER_CHECKPOINT_SENTINEL_FIELDS):
        raise InfrastructureError(
            f"{where}: a sentinel block is not the COMPLETE "
            "per-checkpoint field set (305_f §4 — fields are never "
            "dropped)")
    if list(block["observation_ids"]) \
            != sorted(contract.scope.sentinel_observation_ids) \
            or block["cell"] != contract.scope.sentinel_cell:
        raise InfrastructureError(
            f"{where}: sentinel block population is not the "
            "contract's frozen sentinel")
    if block["training_exposed"] \
            is not contract.scope.sentinel_training_exposed:
        raise InfrastructureError(
            f"{where}: training_exposed diverges from the "
            "contract's sentinel exposure (321_s)")
    for field in _SENTINEL_COUNTER_FIELDS:
        value = block[field]
        if not isinstance(value, int) or isinstance(value, bool) \
                or value < 0:
            raise InfrastructureError(
                f"{where}.{field}: counters must be non-negative "
                "non-boolean integers (321_s)")
    if block["completion_denominator"] < block["group_denominator"]:
        raise InfrastructureError(
            f"{where}: completion denominator below the group "
            "denominator")
    for field in ("worker1_selections", "worker1_completions",
                  "reward1_completions"):
        if block[field] > block["completion_denominator"]:
            raise InfrastructureError(
                f"{where}.{field} exceeds the completion "
                "denominator (321_s — impossible count)")
    for field in ("reward_varying_groups", "q1_counted_groups"):
        if block[field] > block["group_denominator"]:
            raise InfrastructureError(
                f"{where}.{field} exceeds the group denominator "
                "(321_s — impossible count)")
    # 323_s: the PRODUCER invariants — states the block producer
    # cannot emit are not valid trajectories
    if block["worker1_selections"] != block["worker1_completions"]:
        raise InfrastructureError(
            f"{where}: worker-1 selections != completions — the "
            "producer emits them identically (323_s)")
    if block["completion_denominator"] \
            != block["group_denominator"] * group_size:
        raise InfrastructureError(
            f"{where}: completion denominator "
            f"{block['completion_denominator']} != groups x the "
            f"frozen group size G={group_size} (323_s)")
    if block["q1_counted_groups"] > block["reward_varying_groups"]:
        raise InfrastructureError(
            f"{where}: a Q1-counted group necessarily varies — "
            "counted cannot exceed varying")
    firsts_group = block["first_group_indices"]
    firsts_update = block["first_update_indices"]
    families = tuple(family for _, family in _COUNTER_FIRSTS)
    for label, mapping in (("first_group_indices", firsts_group),
                           ("first_update_indices", firsts_update)):
        if not isinstance(mapping, Mapping) \
                or set(mapping) != set(families):
            raise InfrastructureError(
                f"{where}.{label}: must carry exactly the four "
                "first-occurrence families")
        for family, value in mapping.items():
            if value is not None and (
                    not isinstance(value, int)
                    or isinstance(value, bool) or value < 0):
                raise InfrastructureError(
                    f"{where}.{label}[{family}]: a first index is "
                    "None or a non-negative non-boolean integer "
                    "(321_s)")
    for counter, family in _COUNTER_FIRSTS:
        set_group = firsts_group[family] is not None
        set_update = firsts_update[family] is not None
        if set_group is not set_update:
            raise InfrastructureError(
                f"{where}: {family} first indices disagree "
                "between the group and update spaces")
        if (block[counter] > 0) is not set_group:
            raise InfrastructureError(
                f"{where}: {counter} = {block[counter]} but the "
                f"{family} first index is "
                f"{'set' if set_group else 'None'} (321_s — "
                "count/index consistency)")
        if set_group and firsts_update[family] \
                != firsts_group[family] * updates_per_group:
            raise InfrastructureError(
                f"{where}: {family} first update index "
                f"{firsts_update[family]} != group index x "
                f"updates_per_group={updates_per_group} (323_s — "
                "the producer binds the two index spaces)")
    import copy as _copy
    return _copy.deepcopy(dict(block))


def _validate_expected_indices(name: str, expected: Sequence[int]
                               ) -> tuple[int, ...]:
    if not expected:
        raise InfrastructureError(
            f"{name}: the frozen expected index set is empty — "
            "checkpoint zero and the final checkpoint are "
            "mandatory (321_s)")
    previous = None
    for index in expected:
        if not isinstance(index, int) or isinstance(index, bool) \
                or index < 0:
            raise InfrastructureError(
                f"{name}: expected index {index!r} must be a "
                "non-negative non-boolean integer")
        if previous is not None and index <= previous:
            raise InfrastructureError(
                f"{name}: expected indices must be strictly "
                "increasing")
        previous = index
    if expected[0] != 0:
        raise InfrastructureError(
            f"{name}: the expected index set must begin at "
            "checkpoint zero (321_s)")
    if len(expected) < 2:
        raise InfrastructureError(
            f"{name}: checkpoint zero PLUS a positive final "
            "checkpoint are mandatory (323_s) — a single-element "
            "expected set has no final checkpoint")
    return tuple(expected)


def _validate_trajectory(name: str,
                         entries: Sequence[tuple[int,
                                                 Mapping[str, Any]]],
                         expected: tuple[int, ...],
                         status: str,
                         contract: P0ScienceContract,
                         group_size: int,
                         updates_per_group: int
                         ) -> tuple[tuple[int, dict[str, Any]], ...]:
    observed = [index for index, _ in entries]
    if status == "complete":
        if observed != list(expected):
            raise InfrastructureError(
                f"{name}: observed checkpoints {observed[:5]}... "
                f"!= the frozen expected set (empty or truncated "
                "trajectories are not complete; 321_s)")
    else:  # infrastructure_abort: EACH stream is a prefix (323_s;
        # possibly complete — the abort may fall between streams);
        # the assembly requires at least one STRICT prefix globally
        if len(observed) > len(expected) \
                or observed != list(expected)[:len(observed)]:
            raise InfrastructureError(
                f"{name}: an infrastructure-abort trajectory must "
                "be a PREFIX of the frozen expected set")
    validated = []
    for index, block in entries:
        validated.append((index, _validate_sentinel_block(
            name, index, block, contract, group_size,
            updates_per_group)))
    return tuple(validated)


def assemble_sentinel_trajectories(
        contract: P0ScienceContract,
        checkpoint_blocks: Sequence[tuple[int, Mapping[str, Any]]],
        evaluation_blocks: Sequence[tuple[int, Mapping[str, Any]]],
        *, expected_checkpoint_indices: Sequence[int],
        expected_evaluation_indices: Sequence[int],
        status: str = "complete") -> dict[str, Any]:
    """The P0 consumer's assembly of the two signed trajectories
    (321_s/323_s P1): the observed index sequences must EQUAL the
    frozen expected sets exactly (checkpoint zero PLUS a positive
    final checkpoint mandatory); every block must satisfy the
    PRODUCER invariants under the canonical profile's frozen group
    size and updates-per-group. An `infrastructure_abort` is
    handled EXPLICITLY: each stream a prefix of its expected set
    (possibly complete — the abort may fall between streams), at
    least one stream a STRICT prefix, with a disclosed truncation
    record. Blocks are DEEP-COPIED (mutation after assembly cannot
    reach the result). The expected sets themselves are bound
    later through the authenticated P0ExecutionIdentity — the home
    for the deferred cadence/evaluation/telemetry configuration."""
    if status not in ("complete", "infrastructure_abort"):
        raise InfrastructureError(
            f"unknown trajectory status {status!r}")
    profile = _validated_profile()
    group_size = profile["grpo"]["group_size"]
    updates_per_group = profile["updates_per_group"]
    expected_ckpt = _validate_expected_indices(
        "checkpoint_trajectory", expected_checkpoint_indices)
    expected_eval = _validate_expected_indices(
        "evaluation_trajectory", expected_evaluation_indices)
    result = {
        "status": status,
        "expected_checkpoint_indices": expected_ckpt,
        "expected_evaluation_indices": expected_eval,
        "checkpoint_trajectory": _validate_trajectory(
            "checkpoint_trajectory", checkpoint_blocks,
            expected_ckpt, status, contract, group_size,
            updates_per_group),
        "evaluation_trajectory": _validate_trajectory(
            "evaluation_trajectory", evaluation_blocks,
            expected_eval, status, contract, group_size,
            updates_per_group),
    }
    if status == "infrastructure_abort":
        if len(result["checkpoint_trajectory"]) \
                == len(expected_ckpt) \
                and len(result["evaluation_trajectory"]) \
                == len(expected_eval):
            raise InfrastructureError(
                "an infrastructure abort with BOTH streams "
                "complete is not an abort (323_s)")
        result["disclosed_truncation"] = {
            "checkpoints_observed":
                len(result["checkpoint_trajectory"]),
            "checkpoints_expected": len(expected_ckpt),
            "evaluations_observed":
                len(result["evaluation_trajectory"]),
            "evaluations_expected": len(expected_eval),
        }
    return result
