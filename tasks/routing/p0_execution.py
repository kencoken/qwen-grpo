"""P0 precursors, Unit L — the REAL P0LaunchFreeze instance, the
authenticated P0ExecutionIdentity, and the fail-closed
`admit_p0_execution` boundary (330_f §4; 328_f §4 identity graph).

Order (328_f §4): the four precursor pins resolve to their
committed records and re-verify → the launch plan derives from the
CHAIN-AUTHENTICATED beta-smoke record through the frozen cap
formula → the P0LaunchFreeze instance is built and persisted
EXACTLY ONCE (plan rederived; runtime bound to the canonical
profile + the ACTUAL prompt; the P0 training seed frozen,
pairwise-distinct from every evaluation seed) → the
P0ExecutionIdentity BINDS the reviewed freeze hash, the exact
cadence in BOTH epoch labels and optimizer-update units
(checkpoint zero + final mandatory; out-of-horizon trimmed), the
evaluation configuration FROM the reviewed val lock (common random
numbers, NO checkpoint index), and the telemetry/trajectory
identity → `admit_p0_execution` runs BEFORE checkpoint zero and
no trainer entry point can bypass it (the trainer builder takes
its dataset and configuration ONLY from this boundary's returned
bundle).

Registered carry-forwards enforced here: the admission
cross-checks the PERSISTED final-reserve ledger entry against the
pinned reserve record and rejects duplicates (346_f); val evidence
never retunes P0 mixture/prompts/workers (the freeze consumes only
reviewed pins); the per-slot seed realization binds through the
val lock's frozen 720-entry schedule (342_f).

Development-only: all P0 evidence remains development-only — the
charter's confirmatory boundary is untouched."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from tasks.conductor.types import InfrastructureError

from . import dev_support
from .charter import content_sha256
from .p0_cap import _strict_equal, derive_launch_plan, require_launchable
from .p0_contract import load_p0_science_contract
from .p0_replay import P0_DIR, REPLAY_SOURCE

# --- the frozen Unit-L identities ----------------------------------------------

# The beta-smoke record, authenticated through the verified chain:
# the COMPLETE closeout (entry 22) binds the record file hash.
SMOKE_LAUNCH_ENTRY_SHA256 = \
    "4738b32b3e1cdd079235062f1587d4326adb030daf80c44eb0484aef470c0d90"
SMOKE_CLOSEOUT_SHA256 = \
    "df4bf7ad7c649a5b550b58673368811854c42493125f86a68e6abbf5ce91da56"
BETA_SMOKE_RECORD_SHA256 = \
    "a9d6f55b6300b97df03135beed4b82cb82ff5d555f7d1eee48688cf88a743b80"

# The four reviewed precursor pins (303_f §2: the launch freeze
# pins their reviewed outputs).
REAL_PRECURSORS = {
    "routing_dev_val_lock_sha256":
        "2aecdf28ad25cae10e494aa9fc1a95138a9feb5a29ab0636314b847987caf19d",
    "cycle_record_sha256":
        "d617ab5fbb609fc89c250e6a79627b2ed28e54603fa1fed2253d855a3abaccdc",
    "r_cycle_record_sha256":
        "e13cf4d3605393186499cab0490d5e2bc289c77841b146841d0f52258f422265",
    "beta_smoke_record_sha256": BETA_SMOKE_RECORD_SHA256,
}

# The P0 training seed, frozen HERE (328_f §4): pairwise-distinct
# by construction from the val evaluation seed (20260804), the
# cycle evaluation seed (20260805), and the timing-smoke seed
# (20260806) — asserted at every identity build.
P0_TRAINING_SEED = 20260807
_EVALUATION_SEEDS = (20260804, 20260805, 20260806)

# P0 execution constants: the launch is admitted ONLY on the
# beta-smoke closure head (a fresh launch; any resume/relaunch is
# a reviewed decision, 330_f §5), with the contract's operational
# ceiling as the launch budget.
P0_LINEAGE_PARENT_SHA256 = SMOKE_CLOSEOUT_SHA256
P0_RUN_ROOT = "runs/routing-dev/p0-v1"
P0_LAUNCH_KIND = "routing-dev-p0-launch-v1"
DRIVER = "tasks/routing/p0_execution.py"

EXECUTION_IDENTITY_SCHEMA = "p0-execution-identity-v1"
EXECUTION_IDENTITY_PATH = P0_DIR / "p0_execution_identity.json"

# The externally reviewed pins for the two persisted Unit-L
# artifacts (presented for review in the Unit-L freeze document;
# the strict loaders REQUIRE them — a self-hash is never
# authentication).
P0_LAUNCH_FREEZE_SHA256 = \
    "88c6635aadb2d0ca1c766efc937123b7ece427190cfe3ce3675ac8f269ebccfc"
P0_EXECUTION_IDENTITY_SHA256 = \
    "4c763cc9f21de2bfc05700b22b48529ed7f2e83ed68225a1ab115f4cdfa5a4ae"


# --- step 1: the chain-authenticated smoke record ------------------------------

def authenticate_smoke_record(ledger_path=None) -> dict[str, Any]:
    """The beta-smoke record under its pin AND through the verified
    chain: the record file bytes must hash to the reviewed pin, the
    committed ledger must verify, and the COMPLETE smoke closeout
    must bind exactly that file hash (never a floating file)."""
    from . import p0_smoke
    from .ledger import LEDGER_PATH, ledger_head, verify_ledger_head
    ledger_path = ledger_path or LEDGER_PATH
    record_path = Path(p0_smoke.SMOKE_RUN_ROOT) / "smoke_record.json"
    raw = record_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BETA_SMOKE_RECORD_SHA256:
        raise InfrastructureError(
            "the smoke record file does not hash to the reviewed "
            "beta_smoke_record pin")
    chain = verify_ledger_head(ledger_head(ledger_path), ledger_path)
    closeouts = [e for e in chain
                 if e["entry_sha256"] == SMOKE_CLOSEOUT_SHA256]
    if len(closeouts) != 1:
        raise InfrastructureError(
            "the registered smoke closeout is not in the verified "
            "chain")
    closeout = closeouts[0]
    if closeout["kind"] != "closeout" \
            or closeout.get("terminal_status") != "complete" \
            or closeout.get("closes_entry_sha256") \
            != SMOKE_LAUNCH_ENTRY_SHA256 \
            or closeout["freeze"].get("smoke_record_file_sha256") \
            != BETA_SMOKE_RECORD_SHA256:
        raise InfrastructureError(
            "the smoke closeout does not bind the pinned record "
            "file — the record is not chain-authenticated")
    record = json.loads(raw.decode("utf-8"))
    if record.get("smoke_freeze_sha256") \
            != p0_smoke.SMOKE_FREEZE_SHA256 \
            or record.get("launch_entry_sha256") \
            != SMOKE_LAUNCH_ENTRY_SHA256 \
            or record.get("development_only") is not True:
        raise InfrastructureError(
            "the smoke record does not bind the signed freeze and "
            "the authenticated launch")
    p0_smoke.validate_measurements(record["measurements"])
    return record


# --- step 2: the BINDING launch-plan derivation --------------------------------

def derive_real_launch_plan(contract=None,
                            ledger_path=None) -> dict[str, Any]:
    """The BINDING derivation (the smoke's worked projection was
    explicitly non-binding): every cap input REDERIVES from the
    authenticated timing record through the frozen 330_f §2
    mapping; `cumulative_consumed_seconds` is P0-LOCAL zero at a
    fresh launch. The result must ALSO equal the projection the
    smoke record persisted — a divergence means the record or the
    mapping changed after review."""
    from . import p0_smoke
    record = authenticate_smoke_record(ledger_path)
    inputs = p0_smoke.derive_cap_inputs(record["measurements"])
    if inputs["cumulative_consumed_seconds"] != 0.0:
        raise InfrastructureError(
            "a fresh P0 launch derives from P0-local zero consumed "
            "seconds (330_f §2)")
    contract = contract or load_p0_science_contract()
    plan = derive_launch_plan(
        contract,
        cumulative_consumed_seconds=inputs[
            "cumulative_consumed_seconds"],
        measured_finalization_reserve_seconds=inputs[
            "measured_finalization_reserve_seconds"],
        frozen_non_rollout_overhead_seconds=inputs[
            "frozen_non_rollout_overhead_seconds"],
        measured_whole_epoch_seconds=inputs[
            "measured_whole_epoch_seconds"])
    if not _strict_equal(plan, record["projection"]["plan"]):
        raise InfrastructureError(
            "the binding derivation diverges from the reviewed "
            "smoke projection — the record or the mapping moved "
            "after review")
    return plan


# --- step 3: the REAL P0LaunchFreeze instance ----------------------------------

def real_runtime_identity(environment: Mapping[str, Any]
                          | None = None) -> dict[str, Any]:
    """The runtime block of the real freeze: canonical profile
    values, the ACTUAL prompt, the frozen P0 training seed, and the
    COMMIT-INDEPENDENT attested environment — which must equal the
    C2-reviewed attestation (the same validated stack; a changed
    driver/torch/GPU refuses here, not at launch)."""
    from tasks.conductor.stage1 import prompt_fewshot

    from .p0_launch import P0_RUNTIME_PROFILE_SHA256, _validated_profile
    from .resume_validation import attested_environment_sha256
    from .support_run import _default_environment
    profile = _validated_profile()
    env = dict(environment) if environment is not None \
        else _default_environment()
    dev_support.validate_environment_manifest_binding(env)
    attested = attested_environment_sha256(env)
    if attested != REPLAY_SOURCE["attested_environment_sha256"]:
        raise InfrastructureError(
            "the commit-independent environment attestation "
            "diverges from the C2-reviewed stack — the freeze "
            "refuses to bind an unreviewed environment")
    if len(set(_EVALUATION_SEEDS + (P0_TRAINING_SEED,))) != 4:
        raise InfrastructureError(
            "the P0 training seed collides with an evaluation "
            "seed (328_f §4 pairwise distinctness)")
    grpo = profile["grpo"]
    return {
        "model_id": profile["model_id"],
        "model_revision": profile["revision"],
        "quantization": profile["quantization"]["quant_type"],
        "lora_adapter_dtype": profile["lora"]["adapter_dtype"],
        "lora_key_set_sha256":
            profile["lora_key_set"]["sorted_keys_sha256"],
        "prompt_sha256": hashlib.sha256(
            prompt_fewshot().encode("utf-8")).hexdigest(),
        "runtime_profile_sha256": P0_RUNTIME_PROFILE_SHA256,
        "group_size": grpo["group_size"],
        "seed": P0_TRAINING_SEED,
        "temperature": grpo["temperature"],
        "learning_rate": grpo["learning_rate"],
        "beta": grpo["beta"],
        "policy_max_new_tokens": profile["policy_max_new_tokens"],
        "attested_environment_sha256": attested,
    }


def freeze_real_p0_launch(out_path=None, *, ledger_path=None,
                          environment: Mapping[str, Any]
                          | None = None) -> str:
    """Build and persist the REAL P0LaunchFreeze EXACTLY ONCE
    (`save_launch_freeze` refuses an existing file). The plan is
    the binding derivation; the precursors are the four reviewed
    pins; the runtime binds the canonical profile, the ACTUAL
    prompt, and the frozen P0 seed. The returned hash goes to
    external review → `P0_LAUNCH_FREEZE_SHA256`."""
    from .p0_launch import (
        LAUNCH_FREEZE_PATH,
        build_p0_launch_freeze,
        save_launch_freeze,
    )
    target = Path(out_path or LAUNCH_FREEZE_PATH)
    if target.exists():
        raise InfrastructureError(
            f"{target} exists; the launch freeze is written "
            "exactly once")
    plan = derive_real_launch_plan(ledger_path=ledger_path)
    freeze = build_p0_launch_freeze(
        plan_record=plan, precursors=REAL_PRECURSORS,
        runtime=real_runtime_identity(environment))
    return save_launch_freeze(freeze,
                              out_path or LAUNCH_FREEZE_PATH)


def load_real_launch_freeze(path=None):
    """The committed real instance under its externally reviewed
    pin, with the REAL precursor pins re-asserted (a freeze built
    from other pins never loads as THE P0 freeze)."""
    from dataclasses import fields

    from .p0_launch import LAUNCH_FREEZE_PATH, load_p0_launch_freeze
    freeze = load_p0_launch_freeze(path or LAUNCH_FREEZE_PATH,
                                   P0_LAUNCH_FREEZE_SHA256)
    declared = {f.name: getattr(freeze.precursors, f.name)
                for f in fields(freeze.precursors)}
    if declared != REAL_PRECURSORS:
        raise InfrastructureError(
            "the loaded freeze does not pin the four reviewed "
            "precursor outputs")
    if freeze.runtime.seed != P0_TRAINING_SEED:
        raise InfrastructureError(
            "the loaded freeze does not carry the frozen P0 "
            "training seed")
    return freeze


# --- step 4: the cadence in both unit systems ----------------------------------

def derive_cadence(launch_epochs: int,
                   groups_per_epoch: int) -> dict[str, Any]:
    """330_f §2: epoch labels {0, 4, 8, …} on the launch horizon
    with checkpoint zero AND the final checkpoint MANDATORY;
    out-of-horizon labels trimmed; update indices = label ×
    groups/epoch (one group per optimizer update)."""
    if not isinstance(launch_epochs, int) or launch_epochs <= 0 \
            or not isinstance(groups_per_epoch, int) \
            or groups_per_epoch <= 0:
        raise InfrastructureError(
            "cadence requires positive integer epochs and "
            "groups/epoch")
    labels = [e for e in range(0, launch_epochs, 4)]
    if labels[-1] != launch_epochs:
        labels.append(launch_epochs)
    updates = [label * groups_per_epoch for label in labels]
    if labels[0] != 0 or labels[-1] != launch_epochs \
            or any(b <= a for a, b in zip(labels, labels[1:])):
        raise InfrastructureError(
            "cadence must be strictly increasing with mandatory "
            "checkpoint zero and final")
    return {"epoch_labels": labels, "update_indices": updates,
            "groups_per_epoch": groups_per_epoch,
            "rule": "every 4 epochs on the launch horizon; "
                    "checkpoint zero and final mandatory; "
                    "out-of-horizon trimmed (330_f §2)"}


# --- step 5: the authenticated P0ExecutionIdentity -----------------------------

def _val_lock_for_identity() -> dict[str, Any]:
    """The reviewed val lock under its pin WITH surface
    authentication — restoring the committed evidence if the run
    root is absent (the clean-clone path)."""
    from .p0_val import (
        VAL_LOCK_SHA256,
        VAL_RUN_ROOT,
        load_val_lock,
        restore_val_evidence,
    )
    run_root = Path(VAL_RUN_ROOT)
    if not (run_root / "val_lock.json").exists():
        restore_val_evidence()
    return load_val_lock(run_root / "val_lock.json",
                         VAL_LOCK_SHA256,
                         surface_dir=run_root / "surface")


def build_p0_execution_identity(*, launch_freeze_sha256: str
                                ) -> dict[str, Any]:
    """Constructed ONLY against the externally reviewed freeze hash
    (328_f §4 — the identity BINDS that hash). The evaluation block
    comes FROM the reviewed val lock (common random numbers, NO
    checkpoint index; the full 720-entry per-slot schedule pin);
    the cadence derives from the frozen rule over the freeze's
    launch epochs; the trajectory index sets (update units) are
    exactly the cadence; the telemetry identity is the closed
    sentinel-block schema."""
    from .p0_launch import (
        _PER_CHECKPOINT_SENTINEL_FIELDS,
        _SENTINEL_COUNTER_FIELDS,
        LAUNCH_FREEZE_PATH,
        load_p0_launch_freeze,
    )
    from .p0_schedule import schedule_for_epochs
    from .p0_val import VAL_SEED_SCHEDULE_SHA256, seed_schedule
    from .p0_schema import contract_sha256
    freeze = load_p0_launch_freeze(LAUNCH_FREEZE_PATH,
                                   launch_freeze_sha256)
    contract = load_p0_science_contract()
    if freeze.science_contract_sha256 != contract_sha256(contract):
        raise InfrastructureError(
            "the freeze pins a different science contract")
    groups_per_epoch = len(schedule_for_epochs(contract, 1))
    cadence = derive_cadence(freeze.launch_plan.launch_epochs,
                             groups_per_epoch)
    lock = _val_lock_for_identity()
    evaluation = dict(lock["evaluation"])
    if lock["seed_schedule_sha256"] != VAL_SEED_SCHEDULE_SHA256:
        raise InfrastructureError(
            "the val lock does not carry the frozen 720-entry "
            "seed schedule pin")
    recomputed = content_sha256(
        [[obs, slot, seed] for obs, slot, seed in seed_schedule()])
    if recomputed != VAL_SEED_SCHEDULE_SHA256:
        raise InfrastructureError(
            "the per-slot seed schedule does not recompute to the "
            "frozen pin (342_f realization binding)")
    if freeze.runtime.seed in (evaluation["base_seed"], 20260805,
                               20260806):
        raise InfrastructureError(
            "training seed collides with an evaluation seed")
    identity = {
        "schema_version": EXECUTION_IDENTITY_SCHEMA,
        "launch_freeze_sha256": launch_freeze_sha256,
        "science_contract_sha256": freeze.science_contract_sha256,
        "cadence": cadence,
        "evaluation": {
            "source": "routing_dev_val_lock",
            "val_lock_sha256":
                REAL_PRECURSORS["routing_dev_val_lock_sha256"],
            "domain": evaluation["domain"],
            "base_seed": evaluation["base_seed"],
            "seed_rule": evaluation["seed_rule"],
            "sampling": evaluation["sampling"],
            "seed_schedule_sha256": VAL_SEED_SCHEDULE_SHA256,
            "ordered_observation_ids_sha256": content_sha256(
                list(lock["ordered_observation_ids"])),
            "checkpoint_rule": "every cadence checkpoint evaluates "
                               "the full 90-observation cohort "
                               "under IDENTICAL per-slot seeds "
                               "(common random numbers; the "
                               "checkpoint index lives in "
                               "provenance only, 330_f §1)",
        },
        "telemetry": {
            "sentinel_fields":
                list(_PER_CHECKPOINT_SENTINEL_FIELDS),
            "counter_fields": list(_SENTINEL_COUNTER_FIELDS),
            "trajectory_index_sets": {
                "checkpoint_trajectory":
                    list(cadence["update_indices"]),
                "evaluation_trajectory":
                    list(cadence["update_indices"]),
            },
            "units": "optimizer updates (330_f §2)",
        },
        "training_seed": freeze.runtime.seed,
        "development_only": True,
    }
    return identity


def freeze_p0_execution_identity(*, launch_freeze_sha256: str,
                                 out_path=None) -> str:
    """Persist the identity EXACTLY ONCE; the returned hash goes to
    external review → `P0_EXECUTION_IDENTITY_SHA256`."""
    out_path = Path(out_path or EXECUTION_IDENTITY_PATH)
    if out_path.exists():
        raise InfrastructureError(
            f"{out_path} exists; the execution identity is written "
            "exactly once")
    identity = build_p0_execution_identity(
        launch_freeze_sha256=launch_freeze_sha256)
    digest = content_sha256(identity)
    payload = dict(identity)
    payload["record_sha256"] = digest
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=1, sort_keys=True,
                   allow_nan=False) + "\n", encoding="utf-8")
    return digest


def load_p0_execution_identity(path=None, *,
                               expected_sha256: str
                               ) -> dict[str, Any]:
    """The strict loader: the externally reviewed hash is REQUIRED,
    and the record must REDERIVE from the frozen constructors (a
    rehashed record carrying a different cadence, seed, or
    evaluation identity refuses at the rederivation — the freeze
    file itself must rehash to the recorded freeze pin)."""
    from .p0_schema import _require_hex64
    _require_hex64(expected_sha256, "expected_sha256")
    payload = json.loads(
        Path(path or EXECUTION_IDENTITY_PATH).read_text("utf-8"))
    body = {k: v for k, v in payload.items()
            if k != "record_sha256"}
    if content_sha256(body) != payload.get("record_sha256") \
            or payload["record_sha256"] != expected_sha256:
        raise InfrastructureError(
            "execution identity does not rehash to the externally "
            "reviewed value")
    rederived = build_p0_execution_identity(
        launch_freeze_sha256=body["launch_freeze_sha256"])
    if body != rederived:
        differing = sorted(
            k for k in set(body) | set(rederived)
            if body.get(k) != rederived.get(k))
        raise InfrastructureError(
            f"execution identity does not rederive from the frozen "
            f"constructors; differing fields: {differing}")
    return body


# --- step 6: the execution manifest (the EXTERNAL argument) --------------------

_P0_MANIFEST_KEYS = frozenset({
    "kind", "launch_freeze_sha256", "execution_identity_sha256",
    "science_contract_sha256", "budget_gpu_hours", "driver",
    "run_root", "execution_root", "lineage_parent_sha256",
    "routing_source_sha256", "environment_manifest_sha256"})


def build_p0_execution_manifest(*, environment_manifest:
                                Mapping[str, Any],
                                execution_root: str | Path
                                ) -> dict[str, Any]:
    """The execution manifest as the EXTERNAL launch argument
    (305_f §1): it binds the two reviewed Unit-L pins, the
    contract, the source digest, and the frozen launch constants —
    it is NEVER a field of the freeze (closed schema)."""
    from .charter import routing_execution_digest
    contract = load_p0_science_contract()
    digest = routing_execution_digest(DRIVER)
    manifest = {
        "kind": P0_LAUNCH_KIND,
        "launch_freeze_sha256": P0_LAUNCH_FREEZE_SHA256,
        "execution_identity_sha256": P0_EXECUTION_IDENTITY_SHA256,
        "science_contract_sha256":
            load_real_launch_freeze().science_contract_sha256,
        "budget_gpu_hours":
            float(contract.sizing.operational_ceiling_hours),
        "driver": DRIVER,
        "run_root": P0_RUN_ROOT,
        "execution_root": str(Path(execution_root).resolve()),
        "lineage_parent_sha256": P0_LINEAGE_PARENT_SHA256,
        "routing_source_sha256": digest["routing_source_sha256"],
        "environment_manifest_sha256":
            dev_support.validate_environment_manifest_binding(
                environment_manifest),
    }
    manifest["manifest_sha256"] = content_sha256(manifest)
    return manifest


def validate_p0_execution_manifest(manifest: Mapping[str, Any], *,
                                   recompute: bool = True
                                   ) -> dict[str, Any]:
    """Closed schema; every configuration-owned field REDERIVED
    from the frozen constants; the source digest recomputed from
    the tree when `recompute` is set."""
    from .charter import routing_execution_digest
    if not isinstance(manifest, Mapping) \
            or set(manifest) != _P0_MANIFEST_KEYS | \
            {"manifest_sha256"}:
        raise InfrastructureError(
            "P0 execution manifest keys do not match the closed "
            "schema")
    body = {k: v for k, v in manifest.items()
            if k != "manifest_sha256"}
    if content_sha256(body) != manifest["manifest_sha256"]:
        raise InfrastructureError(
            "P0 execution manifest does not rehash to its "
            "recorded value")
    contract = load_p0_science_contract()
    freeze = load_real_launch_freeze()
    expected = {
        "kind": P0_LAUNCH_KIND,
        "launch_freeze_sha256": P0_LAUNCH_FREEZE_SHA256,
        "execution_identity_sha256": P0_EXECUTION_IDENTITY_SHA256,
        "science_contract_sha256": freeze.science_contract_sha256,
        "budget_gpu_hours":
            float(contract.sizing.operational_ceiling_hours),
        "driver": DRIVER,
        "run_root": P0_RUN_ROOT,
        "lineage_parent_sha256": P0_LINEAGE_PARENT_SHA256,
    }
    for key, value in expected.items():
        if manifest[key] != value:
            raise InfrastructureError(
                f"P0 execution manifest {key} diverges from the "
                f"frozen configuration")
    if recompute:
        digest = routing_execution_digest(DRIVER)
        if manifest["routing_source_sha256"] \
                != digest["routing_source_sha256"]:
            raise InfrastructureError(
                "P0 execution manifest source digest diverges "
                "from the tree")
    return dict(manifest)


# --- step 7: the fail-closed admission boundary (330_f §4) ---------------------

def _cross_check_final_reserve(chain: list[dict[str, Any]]
                               ) -> dict[str, Any]:
    """346_f carry-forward, completed per 360_s P2-4: the
    PERSISTED final-reserve ledger entry must exist EXACTLY ONCE
    and must equal the pinned raw reserve record COMPLETELY — the
    full reserve projection AND the ledger freeze/file bindings —
    with the record loaded under the freeze's precursor pin."""
    from .p0_cycle import (
        R_CYCLE_RECORD_PATH,
        SUPPORT_SURFACE_LOCK_SHA256,
        load_r_cycle_reserve_record,
    )
    from .support_run import _sha_file
    record = load_r_cycle_reserve_record(
        expected_sha256=REAL_PRECURSORS["r_cycle_record_sha256"])
    finals = [e for e in chain if e["kind"] == "reserve_update"
              and isinstance(e.get("reserve"), dict)
              and e["reserve"].get("status") == "final"]
    if len(finals) != 1:
        raise InfrastructureError(
            f"the chain holds {len(finals)} final reserve entries "
            "— exactly one is required (346_f)")
    basis = record["registered_basis"]
    expected_reserve = {
        "status": "final",
        "r_cycle_gpu_hours": record["r_cycle_gpu_hours"],
        "assumed_cohort_size": basis["assumed_cohort_size"],
        "evaluation_multiplier": basis["evaluation_multiplier"],
        "measured_seconds_per_observation":
            basis["measured_seconds_per_observation"],
        "measured_support_gpu_hours":
            basis["measured_support_gpu_hours"],
        "itemized_ceiling_gpu_hours":
            record["itemized_closure_ceiling"]["ceiling_gpu_hours"],
        "rounding": "ceil_to_whole_gpu_hours",
    }
    if finals[0]["reserve"] != expected_reserve:
        raise InfrastructureError(
            "the persisted final reserve entry diverges from the "
            "pinned reserve record (346_f; 360_s P2-4 complete "
            "projection)")
    expected_freeze = {
        "support_closeout_sha256": basis["support_closeout_sha256"],
        "surface_lock_sha256": SUPPORT_SURFACE_LOCK_SHA256,
        "cycle_record_sha256": record["cycle_record_sha256"],
        "r_cycle_record_sha256": record["record_sha256"],
        "r_cycle_record_file_sha256":
            _sha_file(Path(R_CYCLE_RECORD_PATH)),
    }
    if finals[0]["freeze"] != expected_freeze:
        raise InfrastructureError(
            "the final reserve entry's freeze bindings diverge "
            "from the pinned record (360_s P2-4)")
    return {"entry_sha256": finals[0]["entry_sha256"],
            "r_cycle_gpu_hours":
                expected_reserve["r_cycle_gpu_hours"]}


def admit_p0_execution(*, execution_manifest: Mapping[str, Any],
                       expected_manifest_sha256: str,
                       prepared_environment: Mapping[str, Any],
                       expected_head_sha256: str,
                       question: str, motivating_evidence: str,
                       run_dir: str | Path = P0_RUN_ROOT,
                       ledger_path=None,
                       _live_environment: Mapping[str, Any]
                       | None = None) -> dict[str, Any]:
    """THE consuming operation (330_f §4): runs BEFORE checkpoint
    zero; no trainer entry point can bypass it — the trainer
    builder takes its dataset and configuration ONLY from this
    boundary's returned bundle. Fail-closed, in the frozen order:

    1. all FOUR precursor records verified under their pins;
    2. every cap input REDERIVED from the timing record and
       `require_launchable` re-run on the freeze's persisted plan;
    3. the P0ExecutionIdentity under its externally reviewed hash,
       BOUND to the reviewed freeze hash;
    4. source/driver identity + live environment attestation (the
       execution manifest as the EXTERNAL argument);
    5. dataset preparation and the standing gates
       (`prepare_p0_dataset`);
    6. the envelope inequality: remaining >= launch maximum +
       final R_cycle — with the 346_f final-reserve cross-check.

    The final act is the ledger admission itself (the launch entry
    appended atomically with its checks)."""
    from .ledger import (
        CYCLE_ENVELOPE_GPU_HOURS,
        LEDGER_PATH,
        admit_and_append_launch,
        envelope_state,
        ledger_head,
        verify_ledger_head,
    )
    from .p0_cycle import load_cycle_record
    from .p0_launch import LAUNCH_FREEZE_PATH, prepare_p0_dataset
    from .support_run import _default_environment, attest_environment
    ledger_path = ledger_path or LEDGER_PATH
    manifest = validate_p0_execution_manifest(execution_manifest)
    # 360_s P1-2: the manifest is EXTERNALLY authenticated — the
    # expected hash arrives as its own argument (a re-signed
    # manifest with a mutated root or environment refuses HERE,
    # never by its own self-hash)
    from .p0_schema import _require_hex64
    _require_hex64(expected_manifest_sha256,
                   "expected_manifest_sha256")
    if manifest["manifest_sha256"] != expected_manifest_sha256:
        raise InfrastructureError(
            "the execution manifest does not match the externally "
            "supplied hash (360_s P1-2)")
    # 360_s P1-2: the PREPARED environment artifact is
    # authenticated against the manifest's bound hash
    if dev_support.validate_environment_manifest_binding(
            dict(prepared_environment)) \
            != manifest["environment_manifest_sha256"]:
        raise InfrastructureError(
            "the prepared environment does not bind to the "
            "manifest (360_s P1-2)")
    # 360_s P1-2: the ACTUAL resolved run root must be the
    # manifest's execution root
    if str(Path(run_dir).resolve()) != manifest["execution_root"]:
        raise InfrastructureError(
            "the resolved run root diverges from the manifest's "
            "execution root (360_s P1-2)")

    # (1) the four precursors, fresh and fail-closed
    val_lock = _val_lock_for_identity()
    cycle_record = load_cycle_record()
    freeze = load_real_launch_freeze()
    if cycle_record["record_sha256"] \
            != REAL_PRECURSORS["cycle_record_sha256"]:
        raise InfrastructureError(
            "the cycle record pin diverges from the freeze's "
            "precursor pin")
    if val_lock["record_sha256"] \
            != REAL_PRECURSORS["routing_dev_val_lock_sha256"]:
        raise InfrastructureError(
            "the val lock pin diverges from the freeze's "
            "precursor pin")
    smoke_record = authenticate_smoke_record(ledger_path)

    # (2) the cap inputs rederived; the persisted plan re-admitted
    contract = load_p0_science_contract()
    derived = derive_real_launch_plan(contract,
                                      ledger_path=ledger_path)
    persisted = freeze.launch_plan.to_record()
    require_launchable(contract, persisted)
    if not _strict_equal(derived, persisted):
        raise InfrastructureError(
            "the freeze's persisted plan diverges from the fresh "
            "binding derivation (330_f §4.2)")

    # (3) the execution identity under its reviewed hash
    identity = load_p0_execution_identity(
        expected_sha256=manifest["execution_identity_sha256"])
    if identity["launch_freeze_sha256"] \
            != manifest["launch_freeze_sha256"]:
        raise InfrastructureError(
            "the execution identity does not bind the reviewed "
            "freeze hash (328_f §4)")

    # (4) live environment attestation: prepared vs live, and
    # live vs the freeze's commit-independent expectation
    from .resume_validation import attested_environment_sha256
    live_env = dict(_live_environment) if _live_environment \
        is not None else _default_environment()
    dev_support.validate_environment_manifest_binding(live_env)
    attest_environment(dict(prepared_environment), live_env)
    if attested_environment_sha256(live_env) \
            != freeze.runtime.attested_environment_sha256:
        raise InfrastructureError(
            "the live environment does not attest to the freeze's "
            "commit-independent expectation (330_f §4.4)")

    # (5) dataset preparation + the standing gates
    preparation = prepare_p0_dataset(LAUNCH_FREEZE_PATH,
                                     manifest["launch_freeze_sha256"])

    # (6) the envelope inequality with the final-reserve cross-check
    chain = verify_ledger_head(expected_head_sha256, ledger_path)
    if ledger_head(ledger_path) != expected_head_sha256:
        raise InfrastructureError(
            "the P0 launch head is not the committed ledger head")
    # 360_s P1-1: Unit-L admission is FIRST-LAUNCH-ONLY — ANY
    # prior same-freeze P0 attempt (open, aborted, or complete)
    # refuses; a resume stays under the ORIGINAL launch and its
    # cumulative deadline, and a relaunch requires a REVIEWED
    # successor identity (never a fresh allocation on the same
    # freeze with cumulative_consumed = 0)
    prior_p0 = [e for e in chain if e["kind"] == "training_run"
                and e["freeze"].get("launch_freeze_sha256")
                == manifest["launch_freeze_sha256"]]
    if prior_p0:
        raise InfrastructureError(
            "a prior P0 attempt exists under this launch freeze — "
            "Unit-L admission is first-launch-only (360_s P1-1)")
    reserve_check = _cross_check_final_reserve(chain)
    state = envelope_state(chain, CYCLE_ENVELOPE_GPU_HOURS)
    if state["reserve"] is None \
            or state["reserve"].get("status") != "final":
        raise InfrastructureError(
            "P0 admission requires the FINAL R_cycle reserve "
            "(330_f §4.6)")
    required = manifest["budget_gpu_hours"] \
        + reserve_check["r_cycle_gpu_hours"]
    if state["remaining_gpu_hours"] < required:
        raise InfrastructureError(
            f"envelope {state['remaining_gpu_hours']} < launch "
            f"maximum + final R_cycle = {required} (330_f §4.6)")

    entry = {
        "kind": "training_run",
        "question": question,
        "motivating_evidence": motivating_evidence,
        "freeze": {
            "p0_launch_manifest_sha256": manifest["manifest_sha256"],
            "launch_freeze_sha256":
                manifest["launch_freeze_sha256"],
            "execution_identity_sha256":
                manifest["execution_identity_sha256"],
        },
        "parent": expected_head_sha256,
        "budget_allocated_gpu_hours": manifest["budget_gpu_hours"],
        "outcome_informed": False,
    }
    admitted = admit_and_append_launch(entry, expected_head_sha256,
                                       ledger_path,
                                       launch_manifest=manifest)
    # 360_s P2-3: admission COMPLETED — the returned bundle
    # carries an explicit ADMITTED block (the dataset-preparation
    # DEFERRED marker described the pre-admission state)
    admission_block = {
        "status": "ADMITTED",
        "launch_entry_sha256": admitted["entry_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
        "launch_freeze_sha256": manifest["launch_freeze_sha256"],
        "execution_identity_sha256":
            manifest["execution_identity_sha256"],
    }
    preparation = dict(preparation)
    preparation["launch_admission"] = admission_block
    return {
        "launch_entry_sha256": admitted["entry_sha256"],
        "admission": admission_block,
        "manifest": manifest,
        "freeze_sha256": manifest["launch_freeze_sha256"],
        "execution_identity": identity,
        "preparation": preparation,
        "reserve_check": reserve_check,
        "development_only": True,
    }
