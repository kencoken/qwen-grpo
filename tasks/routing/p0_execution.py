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


# --- the P0 execution runner (post-Unit-L; 361_f sign-off carry-forward) -------
# THE runner invariant: trainer inputs come ONLY from
# `admit_p0_execution`'s returned ADMITTED bundle — no path in
# this module (or anywhere) appends a `training_run` through the
# lower-level ledger helper.

# The EXECUTED evaluation-seed realization for P0 checkpoint
# evaluations: the smoke-priced shape (one slot-0 seed per
# observation, eight sampled sequences per call — the cap
# arithmetic priced EXACTLY this operation), realized under the
# val lock's CRN rule (domain p0_val_eval, base 20260804, NO
# checkpoint index — every checkpoint replays IDENTICAL draws).
P0_EVAL_REALIZATION_SHA256 = \
    "a8e9cf7322a008889414c68ce133bb50cd82fe960340d079b0f1a66fd7f2f802"

# Sentinel-block assembly is NOT performed in-run: the COMPLETE
# training trace and the per-checkpoint evaluation traces are the
# sealed evidence; the per-checkpoint sentinel blocks consumed by
# `assemble_sentinel_trajectories` are derived from that evidence
# by a deterministic CPU assembler in a follow-up reviewed unit
# BEFORE cycle synthesis. Registered as outstanding.
P0_RUNNER_OUTSTANDING = (
    "deterministic CPU sentinel-block assembly from the sealed "
    "training/evaluation traces (feeds "
    "assemble_sentinel_trajectories before cycle synthesis)",
    "resume entry point (a reviewed implementation under the "
    "ORIGINAL launch and its cumulative deadline — an abort "
    "leaves the launch terminally blocked until then)",
)


def _check_deadline(deadline: float, where: str) -> None:
    from .p0_smoke import _check_deadline as _impl
    _impl(deadline, where)


def p0_eval_seed_realization() -> list[tuple[str, int]]:
    """The frozen executed realization: 90 slot-0 seeds under the
    identity's CRN rule, in the val lock's canonical observation
    order, verified against the reviewed pin."""
    from .p0_val import seed_for_completion
    lock = _val_lock_for_identity()
    evaluation = lock["evaluation"]
    seeds = [(oid, seed_for_completion(
        oid, 0, domain=evaluation["domain"],
        base_seed=evaluation["base_seed"]))
        for oid in lock["ordered_observation_ids"]]
    if content_sha256([[oid, seed] for oid, seed in seeds]) \
            != P0_EVAL_REALIZATION_SHA256:
        raise InfrastructureError(
            "the executed evaluation-seed realization does not "
            "match its frozen pin")
    return seeds


def prepare_p0_launch(*, run_dir: str | Path = P0_RUN_ROOT,
                      _environment_builder=None) -> dict[str, Any]:
    """Phase 1 (CPU): persist the prelaunch inputs exactly once —
    the environment manifest, the execution manifest, and byte
    copies of the two reviewed artifacts. The manifest hash goes
    to the narrow prelaunch review."""
    from .p0_launch import LAUNCH_FREEZE_PATH
    from .support_run import _default_environment
    run_dir = Path(run_dir)
    prelaunch = run_dir / "prelaunch"
    if prelaunch.exists():
        raise InfrastructureError(
            f"{prelaunch} exists; a launch is prepared exactly "
            "once")
    environment = (_environment_builder or _default_environment)()
    manifest = build_p0_execution_manifest(
        environment_manifest=environment, execution_root=run_dir)
    prelaunch.mkdir(parents=True)
    for name, payload in (("env_manifest.json", environment),
                          ("p0_launch.json", manifest)):
        (prelaunch / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    for name, source in (
            ("launch_freeze.json", LAUNCH_FREEZE_PATH),
            ("execution_identity.json", EXECUTION_IDENTITY_PATH)):
        (prelaunch / name).write_bytes(Path(source).read_bytes())
    return manifest


def _p0_eval_pass(trainer, out_path: Path, deadline: float,
                  eval_context: dict[str, Any]) -> float:
    """One COMPLETE checkpoint evaluation: the smoke-priced shape
    (slot-0 seed, eight sequences) over the val cohort against
    the AUTHENTICATED val surface, inside `isolated_rng`, sealed
    inside the pass, deadline-checked at every observation."""
    import time as _time

    import torch
    from tasks.conductor import program
    from tasks.conductor.grpo_task import positional_to_semantic
    from tasks.conductor.parser import (
        ActionSchemaError,
        parse_routing_action,
    )
    from tasks.conductor.policy import policy_messages
    from tasks.conductor.stage1 import prompt_fewshot

    from .checkpoint import isolated_rng
    from .p0_smoke import _seal_file
    started = _time.monotonic()
    model = trainer.model
    tokenizer = trainer.processing_class
    surface = eval_context["surface"]
    seeds = eval_context["seeds"]
    observations = eval_context["observations"]
    sampling = eval_context["sampling"]
    system = prompt_fewshot()
    was_training = model.training
    model.eval()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with isolated_rng(), torch.no_grad(), \
            open(out_path, "w", encoding="utf-8") as trace:
        for obs in observations:
            _check_deadline(deadline, "P0 evaluation observation")
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
                **inputs, do_sample=True,
                temperature=float(sampling["temperature"]),
                top_p=float(sampling["top_p"]), top_k=0,
                num_return_sequences=sampling["group_size"],
                max_new_tokens=sampling["max_new_tokens"],
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
                    rewards.append(0.0)
                    continue
                semantic = tuple(positional_to_semantic(
                    parsed, positions))
                payoff = surface.get((oid, semantic))
                if payoff is None:
                    raise InfrastructureError(
                        f"({oid}, {semantic}): no val surface row "
                        "— an infrastructure abort, never a "
                        "reward")
                rewards.append(float(payoff))
            trace.write(json.dumps(
                {"observation_id": oid,
                 "completions": completions,
                 "rewards": rewards}, sort_keys=True) + "\n")
    _seal_file(out_path)
    if was_training:
        model.train()
    return _time.monotonic() - started


def _p0_checkpoint_and_eval(trainer, accountant, identities,
                            run_dir: Path, update_index: int,
                            deadline: float,
                            eval_context: dict[str, Any],
                            record_sink: dict[str, Any]) -> None:
    """One cadence event: the RETAINED v1 checkpoint bundle (the
    resume state — P0 never discards trained state) then the
    evaluation pass under the frozen realization."""
    from .p0_smoke import _save_and_verify_checkpoint_bundle
    _check_deadline(deadline, f"cadence update {update_index}")
    bundle_dir = run_dir / f"checkpoint_bundle_upd{update_index}"
    bundle_seconds, proof = _save_and_verify_checkpoint_bundle(
        trainer, accountant, identities, bundle_dir)
    eval_seconds = _p0_eval_pass(
        trainer,
        run_dir / "sealed" / f"eval_upd{update_index}.jsonl",
        deadline, eval_context)
    record_sink["checkpoints"][str(update_index)] = {
        "bundle_seconds": bundle_seconds,
        "eval_seconds": eval_seconds,
        "checkpoint_proof": proof,
    }
    record_sink["cadence_completed"].append(update_index)


def _make_p0_callback(accountant, instrumentation, deadline,
                      cadence_updates, on_cadence):
    """Lifecycle ordering exactly as reviewed for the smoke
    (352_s/355_s): deadline BEFORE the step, consumption at the
    optimizer, cadence events at step end when the optimizer
    count reaches an intermediate index."""
    from transformers import TrainerCallback

    intermediates = set(cadence_updates[1:-1])

    class _P0Callback(TrainerCallback):
        def on_step_begin(self, args, state, control, **kwargs):
            _check_deadline(deadline, "training step begin")

        def on_optimizer_step(self, args, state, control,
                              **kwargs):
            accountant.record_update(1)

        def on_step_end(self, args, state, control, **kwargs):
            scheduler = kwargs.get("lr_scheduler")
            lr = (scheduler.get_last_lr()[0]
                  if scheduler is not None else 0.0)
            instrumentation.on_update_end(lr)
            step = int(state.global_step)
            if step in intermediates:
                on_cadence(step)

    return _P0Callback()


def _sanitize_p0_abort(run_dir: Path) -> None:
    """The P0 abort rule: raw semantic traces are SEALED, but the
    checkpoint bundles are RETAINED — they are the resume state
    under the original launch (330_f §5; the resume entry point
    is a registered outstanding obligation). A failure here
    propagates: the launch stays OPEN and visibly blocked."""
    from .p0_smoke import _seal_file
    sealed = run_dir / "sealed"
    if sealed.exists():
        for raw in sorted(sealed.iterdir()):
            if raw.is_file() and not raw.name.endswith(".gz"):
                _seal_file(raw)


_P0_RECORD_KEYS = frozenset({
    "run", "p0_launch_manifest_sha256", "launch_freeze_sha256",
    "execution_identity_sha256", "launch_entry_sha256",
    "cadence_completed", "checkpoints", "whole_run_seconds",
    "sealed_sha256", "development_only"})


def verify_p0_run(run_dir: str | Path, *, ledger_path,
                  expected_head_sha256: str | None
                  ) -> dict[str, Any]:
    """The P0 terminal verifier, run before the success closeout
    and post-hoc: the chain-authenticated launch; the closed
    record schema; every sealed file `.gz` only and matching its
    recorded hash; a RETAINED checkpoint bundle for every
    completed cadence index; the environment cross-binding; the
    complete-closeout inventory when present."""
    from .ledger import verify_ledger_head
    from .support_run import _sha_file
    run_dir = Path(run_dir)
    chain = verify_ledger_head(expected_head_sha256, ledger_path)
    manifest = validate_p0_execution_manifest(json.loads(
        (run_dir / "prelaunch" / "p0_launch.json")
        .read_text("utf-8")), recompute=False)
    launches = [e for e in chain if e["kind"] == "training_run"
                and e["freeze"].get("p0_launch_manifest_sha256")
                == manifest["manifest_sha256"]]
    if len(launches) != 1:
        raise InfrastructureError(
            f"the verified chain holds {len(launches)} P0 "
            "launches binding this manifest — exactly one is "
            "required")
    launch = launches[0]
    frozen_env = json.loads(
        (run_dir / "prelaunch" / "env_manifest.json")
        .read_text("utf-8"))
    if dev_support.validate_environment_manifest_binding(
            frozen_env) != manifest["environment_manifest_sha256"]:
        raise InfrastructureError(
            "the prelaunch environment does not bind to the "
            "manifest")
    record = json.loads(
        (run_dir / "p0_record.json").read_text("utf-8"))
    if set(record) != _P0_RECORD_KEYS:
        raise InfrastructureError(
            "P0 record keys do not match the closed schema")
    if record["p0_launch_manifest_sha256"] \
            != manifest["manifest_sha256"] \
            or record["launch_freeze_sha256"] \
            != manifest["launch_freeze_sha256"] \
            or record["execution_identity_sha256"] \
            != manifest["execution_identity_sha256"] \
            or record["launch_entry_sha256"] \
            != launch["entry_sha256"] \
            or record["development_only"] is not True:
        raise InfrastructureError(
            "P0 record does not bind the authenticated launch")
    sealed = run_dir / "sealed"
    raw_left = [p for p in sealed.iterdir()
                if p.is_file() and not p.name.endswith(".gz")] \
        if sealed.exists() else []
    if raw_left:
        raise InfrastructureError(
            f"unsealed raw files remain: "
            f"{[p.name for p in raw_left][:3]}")
    for name, expected_sha in record["sealed_sha256"].items():
        if _sha_file(sealed / name) != expected_sha:
            raise InfrastructureError(
                f"sealed file {name} does not match the recorded "
                "hash")
    for update_index in record["cadence_completed"]:
        bundle = run_dir / f"checkpoint_bundle_upd{update_index}"
        if not (bundle / "checkpoint_record.json").exists():
            raise InfrastructureError(
                f"cadence update {update_index}: the RETAINED "
                "checkpoint bundle is missing")
        if str(update_index) not in record["checkpoints"]:
            raise InfrastructureError(
                f"cadence update {update_index} has no checkpoint "
                "record block")
    closeouts = [e for e in chain if e["kind"] == "closeout"
                 and e.get("closes_entry_sha256")
                 == launch["entry_sha256"]]
    if closeouts and closeouts[0].get(
            "terminal_status") == "complete":
        from .support_run import _hash_directory
        if closeouts[0]["freeze"].get("terminal_artifact_hashes") \
                != _hash_directory(run_dir):
            raise InfrastructureError(
                "terminal evidence does not match the closeout "
                "inventory")
    return {"verdict": "PASS",
            "launch_entry_sha256": launch["entry_sha256"]}


def execute_p0_run(*, run_dir: str | Path = P0_RUN_ROOT,
                   expected_manifest_sha256: str,
                   expected_head_sha256: str,
                   question: str, motivating_evidence: str,
                   ledger_path=None) -> dict[str, Any]:
    """Phase 2 (GPU): P0 itself. Admission through
    `admit_p0_execution` is the ONLY source of trainer inputs
    (the 361_f runner invariant). Checkpoint-zero evaluation is
    P0's FIRST execution under the already-frozen record (charter
    §7); training follows with NO configuration change; every
    cadence index gets a RETAINED v1 bundle + a CRN evaluation;
    the complete training trace is the sealed evidence; the
    cumulative deadline is enforced everywhere; abort seals and
    RETAINS (resume state)."""
    import time as _time

    from .ledger import LEDGER_PATH, append_ledger_entry
    from .p0_smoke import (
        _make_smoke_reward,
        _seal_file,
        _strip_console_callbacks,
    )
    from .p0_val import val_cohort_observations
    from .resume_validation import make_validation_reward
    from .support_run import (
        _default_environment,
        _hash_directory,
        _sha_file,
    )
    ledger_path = ledger_path or LEDGER_PATH
    run_dir = Path(run_dir)
    prelaunch = run_dir / "prelaunch"
    manifest = validate_p0_execution_manifest(json.loads(
        (prelaunch / "p0_launch.json").read_text("utf-8")))
    prepared_env = json.loads(
        (prelaunch / "env_manifest.json").read_text("utf-8"))
    outputs = [run_dir / "sealed", run_dir / "p0_record.json",
               run_dir / "execute_env_manifest.json"]
    for path in outputs:
        if path.exists():
            raise InfrastructureError(
                f"{path} exists — outputs are preflighted before "
                "admission")

    # THE runner invariant: admission is the only input source
    bundle = admit_p0_execution(
        execution_manifest=manifest,
        expected_manifest_sha256=expected_manifest_sha256,
        prepared_environment=prepared_env,
        expected_head_sha256=expected_head_sha256,
        question=question,
        motivating_evidence=motivating_evidence,
        run_dir=run_dir, ledger_path=ledger_path)
    head = bundle["launch_entry_sha256"]
    identity = bundle["execution_identity"]
    started = _time.monotonic()
    deadline = started + manifest["budget_gpu_hours"] * 3600.0

    try:
        from . import checkpoint as ckpt
        from . import p0_smoke
        from .p0_replay import restore_extension_surface_if_absent
        from .p0_val import VAL_RUN_ROOT
        from .unit_c2_sample import UNIT_C2_CONFIG
        _persist = p0_smoke._persist_verified
        _persist(run_dir / "execute_env_manifest.json",
                 _default_environment())
        sealed = run_dir / "sealed"
        sealed.mkdir(parents=True)

        # startup: surfaces, seeds, observations — all under pins
        training_surface = dev_support.load_dev_surface(
            restore_extension_surface_if_absent(),
            expected_lock_sha256=UNIT_C2_CONFIG[
                "extension_surface_lock_sha256"])
        val_lock = _val_lock_for_identity()
        val_surface = dev_support.load_dev_surface(
            Path(VAL_RUN_ROOT) / "surface",
            expected_lock_sha256=val_lock["surface_lock_sha256"])
        seeds = dict(p0_eval_seed_realization())
        observations = val_cohort_observations()
        if [o["observation_id"] for o in observations] \
                != list(val_lock["ordered_observation_ids"]):
            raise InfrastructureError(
                "val cohort order diverges from the lock")
        eval_context = {
            "surface": val_surface["surface"], "seeds": seeds,
            "observations": observations,
            "sampling": identity["evaluation"]["sampling"],
        }
        accountant = ckpt.GroupAccountant()
        instrumentation = p0_smoke._EpochInstrumentation()
        training_trace = sealed / "training_trace.jsonl"
        base_reward = make_validation_reward(
            training_surface["surface"], accountant,
            training_trace,
            group_size=identity["evaluation"]["sampling"][
                "group_size"])
        reward = _make_smoke_reward(base_reward, instrumentation,
                                    deadline)
        identities = {
            "routing_source_sha256":
                manifest["routing_source_sha256"],
            "environment_manifest_sha256":
                manifest["environment_manifest_sha256"],
            "config_sha256": manifest["launch_freeze_sha256"],
            "prompt_sha256":
                bundle["preparation"]["runtime"].prompt_sha256,
            "training_cohort_sha256": content_sha256(
                bundle["preparation"]["schedule"]),
            "renderer_schedule_sha256": content_sha256(
                [row["observation_id"]
                 for row in bundle["preparation"]["trainer_rows"]]),
            "surface_manifest_sha256": UNIT_C2_CONFIG[
                "extension_surface_lock_sha256"],
            "worker_pool_fingerprint": "precomputed_surface",
            "cache_identity":
                manifest["execution_identity_sha256"],
            "seed": str(bundle["preparation"]["runtime"].seed),
        }
        record_sink: dict[str, Any] = {
            "checkpoints": {}, "cadence_completed": []}
        cadence_updates = list(
            identity["cadence"]["update_indices"])

        trainer_holder: dict[str, Any] = {}

        def on_cadence(update_index: int) -> None:
            _p0_checkpoint_and_eval(
                trainer_holder["trainer"], accountant, identities,
                run_dir, update_index, deadline, eval_context,
                record_sink)

        callback = _make_p0_callback(
            accountant, instrumentation, deadline,
            cadence_updates, on_cadence)
        trainer = _build_p0_trainer(
            bundle["preparation"]["trainer_rows"], reward,
            run_dir, bundle["preparation"]["runtime"].seed,
            extra_callbacks=(callback,))
        trainer_holder["trainer"] = trainer
        _strip_console_callbacks(trainer)

        # checkpoint ZERO: P0's FIRST execution (charter §7)
        _p0_checkpoint_and_eval(trainer, accountant, identities,
                                run_dir, 0, deadline,
                                eval_context, record_sink)

        instrumentation.start_epoch()
        trainer.train()
        _check_deadline(deadline, "post-training boundary")

        # the FINAL cadence event at the last update index
        final_index = cadence_updates[-1]
        if int(trainer.state.global_step) != final_index:
            raise InfrastructureError(
                f"trainer ended at step {trainer.state.global_step}"
                f" != the frozen final update {final_index}")
        _p0_checkpoint_and_eval(trainer, accountant, identities,
                                run_dir, final_index, deadline,
                                eval_context, record_sink)
        if record_sink["cadence_completed"] != cadence_updates:
            raise InfrastructureError(
                "completed cadence diverges from the frozen index "
                "set")
        _seal_file(training_trace)
        log_path = sealed / "trainer_log_history.json"
        log_path.write_text(
            json.dumps(trainer.state.log_history, sort_keys=True),
            encoding="utf-8")
        _seal_file(log_path)
        sealed_hashes = {p.name: _sha_file(p)
                         for p in sorted(sealed.iterdir())}
        record = {
            "run": "routing-dev-p0-v1",
            "p0_launch_manifest_sha256":
                manifest["manifest_sha256"],
            "launch_freeze_sha256":
                manifest["launch_freeze_sha256"],
            "execution_identity_sha256":
                manifest["execution_identity_sha256"],
            "launch_entry_sha256": head,
            "cadence_completed": record_sink["cadence_completed"],
            "checkpoints": record_sink["checkpoints"],
            "whole_run_seconds": _time.monotonic() - started,
            "sealed_sha256": sealed_hashes,
            "development_only": True,
        }
        _persist(run_dir / "p0_record.json", record)
        verify_p0_run(run_dir, ledger_path=ledger_path,
                      expected_head_sha256=head)
    except BaseException as error:
        _sanitize_p0_abort(run_dir)
        measured = round((_time.monotonic() - started) / 3600.0, 4)
        append_ledger_entry(
            {"kind": "closeout", "question": question,
             "motivating_evidence": "P0 ABORTED",
             "freeze": {
                 "p0_launch_manifest_sha256":
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
    closeout = append_ledger_entry(
        {"kind": "closeout", "question": question,
         "motivating_evidence": "P0 COMPLETE (development-only)",
         "freeze": {
             "p0_record_file_sha256":
                 _sha_file(run_dir / "p0_record.json"),
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
         "outcome_pointer": str(run_dir / "p0_record.json")},
        head, ledger_path)
    verify_p0_run(run_dir, ledger_path=ledger_path,
                  expected_head_sha256=closeout["entry_sha256"])
    return {**record, "measured_gpu_hours": measured,
            "closeout_entry_sha256": closeout["entry_sha256"],
            "ledger_head": closeout["entry_sha256"]}


def _build_p0_trainer(rows, reward, run_dir: Path, seed: int,
                      extra_callbacks=()):
    """The canonical-profile construction for the FULL horizon:
    identical to the smoke's reviewed builder except max_steps =
    the frozen final update index and the P0 training seed."""
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
        max_steps=6123, loss_type=grpo["loss"],
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
    for callback in extra_callbacks:
        trainer.add_callback(callback)
    return trainer
