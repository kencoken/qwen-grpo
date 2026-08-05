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
    "b5749ecac2e8e2444dd2ebb6193054fb721ea1686751ffd73d0c3938d80b1e1d"


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
                               "under IDENTICAL draws (common "
                               "random numbers; the checkpoint "
                               "index lives in provenance only, "
                               "330_f §1)",
            # 363_s F2: the EXECUTED batched realization is frozen
            # IN the authenticated identity — one slot-0 CRN seed
            # per observation seeds a single batched generation of
            # group_size sequences (the smoke-priced operation);
            # slots 1..7 of the 720-entry schedule are NOT
            # consumed by checkpoint evaluation
            "checkpoint_eval_realization": {
                "rule": "batched per-observation: torch.manual_"
                        "seed(slot-0 CRN seed) then ONE generate "
                        "call with num_return_sequences = "
                        "group_size — the operation the beta "
                        "smoke priced; identical draws at every "
                        "checkpoint",
                "realization_sha256": P0_EVAL_REALIZATION_SHA256,
            },
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


# --- the P0 execution runner (rev3, response to 365_s) -------------------------
# THE runner invariant (361_f): trainer inputs come ONLY from
# `admit_p0_execution`'s returned ADMITTED bundle. Lifecycle
# (363_s F4 / 365_s): a RESUMABLE INTERRUPTION seals partial
# evidence, retains every checkpoint, and leaves the launch OPEN;
# accounting lives in a HASH-CHAINED append-only session log
# (365_s: mutable interruption.json is gone — a SIGKILL'd session
# gets a conservative wall-clock-inferred end at the next
# session); cadence completion is an ATOMIC per-index record
# written only after the FULL evaluation validates (365_s F2);
# resume derives from those records, never from bundle existence;
# trace segments carry checkpoint-authorized prefixes and
# post-checkpoint tails are EXCLUDED evidence (365_s F3).

P0_RUN_ID = "routing-dev-p0-v1"

P0_EVAL_REALIZATION_SHA256 = \
    "a8e9cf7322a008889414c68ce133bb50cd82fe960340d079b0f1a66fd7f2f802"

P0_RUNNER_OUTSTANDING = (
    "deterministic CPU sentinel-block assembly from the sealed "
    "training/evaluation traces (feeds "
    "assemble_sentinel_trajectories before cycle synthesis)",
)


def _check_deadline(deadline: float, where: str) -> None:
    from .p0_smoke import _check_deadline as _impl
    _impl(deadline, where)


def _require_nonneg_finite(value: Any, where: str) -> None:
    import math
    if isinstance(value, bool) or not isinstance(
            value, (int, float)) or not math.isfinite(value) \
            or value < 0:
        raise InfrastructureError(
            f"{where}: must be a non-negative finite number, got "
            f"{value!r}")


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
    """Phase 1 (CPU): persist the prelaunch inputs exactly once."""
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


# --- the hash-chained session log (365_s: authenticated accounting) ------------

_SESSION_LOG = "sessions.jsonl"


def _append_session_entry(run_dir: Path,
                          entry: dict[str, Any]) -> dict[str, Any]:
    """Append-only, hash-chained: each entry binds the previous
    entry's hash; elapsed values are validated finite here (a NaN
    can never disable the deadline comparison)."""
    log_path = Path(run_dir) / _SESSION_LOG
    entries = _load_sessions(run_dir) if log_path.exists() else []
    prev = entries[-1]["entry_sha256"] if entries else None
    if "elapsed_seconds" in entry:
        _require_nonneg_finite(entry["elapsed_seconds"],
                               "session elapsed_seconds")
    body = {**entry, "prev_sha256": prev}
    body["entry_sha256"] = content_sha256(body)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(body, sort_keys=True) + "\n")
    return body


_SESSION_START_KEYS = frozenset({
    "kind", "session_index", "mode", "start_group_index",
    "resume_update_index", "wall_start_utc", "prev_sha256",
    "entry_sha256"})
_SESSION_END_KEYS = frozenset({
    "kind", "session_index", "elapsed_seconds", "status",
    "prev_sha256", "entry_sha256"})


def _load_sessions(run_dir: Path) -> list[dict[str, Any]]:
    """367_s: the loader IS the state machine — a valid hash
    chain is NOT enough. Contiguous start indices, closed
    per-kind schemas, exactly one start and AT MOST one end per
    session (an end must follow its start; a second end
    refuses)."""
    log_path = Path(run_dir) / _SESSION_LOG
    if not log_path.exists():
        return []
    entries = []
    prev = None
    started: set[int] = set()
    ended: set[int] = set()
    for line in log_path.read_text("utf-8").splitlines():
        entry = json.loads(line)
        body = {k: v for k, v in entry.items()
                if k != "entry_sha256"}
        if entry.get("prev_sha256") != prev \
                or content_sha256(body) != entry["entry_sha256"]:
            raise InfrastructureError(
                "session log chain is broken or rewritten (365_s)")
        kind = entry.get("kind")
        index = entry.get("session_index")
        if not isinstance(index, int) or isinstance(index, bool) \
                or index < 1:
            raise InfrastructureError(
                "session_index must be a positive int")
        if kind == "session_start":
            if set(entry) != set(_SESSION_START_KEYS):
                raise InfrastructureError(
                    "session_start schema is not closed (367_s)")
            if entry["mode"] not in ("fresh", "resume",
                                     "finalize"):
                raise InfrastructureError(
                    f"unknown session mode {entry['mode']!r}")
            if index != len(started) + 1:
                raise InfrastructureError(
                    f"session_start index {index} is not "
                    f"contiguous (expected {len(started) + 1})")
            started.add(index)
        elif kind in ("session_end", "session_end_inferred"):
            expected_keys = set(_SESSION_END_KEYS)
            if kind == "session_end":
                expected_keys = expected_keys | {"last_error"}
                if not (set(entry) == expected_keys
                        or set(entry)
                        == expected_keys - {"last_error"}):
                    raise InfrastructureError(
                        "session_end schema is not closed (367_s)")
            elif set(entry) != expected_keys:
                raise InfrastructureError(
                    "session_end_inferred schema is not closed")
            if index not in started:
                raise InfrastructureError(
                    f"session {index} ended without starting")
            if index in ended:
                raise InfrastructureError(
                    f"session {index} has a SECOND end — the "
                    "state machine refuses (367_s)")
            _require_nonneg_finite(entry["elapsed_seconds"],
                                   "session elapsed_seconds")
            ended.add(index)
        else:
            raise InfrastructureError(
                f"unknown session entry kind {kind!r}")
        prev = entry["entry_sha256"]
        entries.append(entry)
    return entries


def _session_state(run_dir: Path) -> dict[str, Any]:
    """Derived state: cumulative validated elapsed, the next
    session index, and whether the last session is unclosed (a
    SIGKILL/power loss — its conservative wall-clock end is
    appended by the CALLER before starting a new session)."""
    entries = _load_sessions(run_dir)
    ends = {e["session_index"]: e for e in entries
            if e["kind"] in ("session_end",
                             "session_end_inferred")}
    starts = {e["session_index"]: e for e in entries
              if e["kind"] == "session_start"}
    cumulative = sum(e["elapsed_seconds"] for e in ends.values())
    unclosed = sorted(set(starts) - set(ends))
    if len(unclosed) > 1:
        raise InfrastructureError(
            "more than one unclosed session — the log is "
            "incoherent")
    return {"entries": entries, "starts": starts, "ends": ends,
            "cumulative_elapsed_seconds": cumulative,
            "unclosed_session_index":
                unclosed[0] if unclosed else None,
            "next_session_index": len(starts) + 1}


def _sanitize_after_crash(run_dir: Path) -> None:
    """367_s F3: IDEMPOTENT crash sanitation — every raw file
    under sealed/ is deterministically sealed so the killed
    session's checkpoint-authorized training prefix enters the
    merge, the sealed inventory holds, and no raw partial
    evaluation can be silently overwritten. Safe to call
    repeatedly (already-sealed files are untouched)."""
    from .p0_smoke import _seal_file
    sealed = Path(run_dir) / "sealed"
    if sealed.exists():
        for raw in sorted(sealed.iterdir()):
            if raw.is_file() and not raw.name.endswith(".gz"):
                _seal_file(raw)


def _close_killed_session(run_dir: Path, state: dict[str, Any]
                          ) -> dict[str, Any]:
    """365_s/367_s F3: a session that recorded no end (SIGKILL,
    power loss) is closed with a CONSERVATIVE
    wall-clock-inferred elapsed, AND its evidence is sanitized
    (sealed) so resume can consume the authorized prefix."""
    import time as _time
    index = state["unclosed_session_index"]
    if index is None:
        return state
    _sanitize_after_crash(run_dir)
    start = state["starts"][index]
    inferred = _time.time() - float(start["wall_start_utc"])
    _require_nonneg_finite(inferred, "inferred session elapsed")
    _append_session_entry(run_dir, {
        "kind": "session_end_inferred", "session_index": index,
        "elapsed_seconds": inferred,
        "status": "killed_no_graceful_end"})
    return _session_state(run_dir)


# --- atomic per-cadence completion records (365_s F2) --------------------------

def _cadence_record_path(run_dir: Path, update_index: int) -> Path:
    return Path(run_dir) / "cadence" / f"upd{update_index}.json"


def _write_cadence_record(run_dir: Path,
                          record: dict[str, Any]) -> None:
    """ATOMIC (tmp + rename), written ONLY after the full
    evaluation validated — bundle existence NEVER implies a
    completed cadence point."""
    import os
    path = _cadence_record_path(run_dir, record["update_index"])
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise InfrastructureError(
            f"{path} exists — a cadence point completes exactly "
            "once")
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, indent=1, sort_keys=True)
                   + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load_cadence_records(run_dir: Path,
                          cadence: list[int]) -> dict[str, Any]:
    """The completed set is a CONTIGUOUS cadence prefix; each
    record carries its ACTUAL measured timings and proof (never
    reconstructed)."""
    records: dict[str, Any] = {}
    for update_index in cadence:
        path = _cadence_record_path(run_dir, update_index)
        if not path.exists():
            break
        record = json.loads(path.read_text("utf-8"))
        if set(record) != {"update_index", "bundle_seconds",
                           "eval_seconds", "checkpoint_proof",
                           "hf_checkpoint_dir"}:
            raise InfrastructureError(
                f"cadence record upd{update_index}: closed schema")
        _require_nonneg_finite(record["bundle_seconds"],
                               "cadence bundle_seconds")
        _require_nonneg_finite(record["eval_seconds"],
                               "cadence eval_seconds")
        if record["update_index"] != update_index:
            raise InfrastructureError(
                f"cadence record upd{update_index}: index "
                "mismatch")
        records[str(update_index)] = record
    for update_index in cadence[len(records):]:
        if _cadence_record_path(run_dir, update_index).exists():
            raise InfrastructureError(
                "cadence records are not a contiguous prefix")
    return records


def _p0_identities(manifest: Mapping[str, Any],
                   training_lock: Mapping[str, Any],
                   rows, seed: int) -> dict[str, str]:
    """Renderer/surface/worker/cache fields derive from the
    admitted rows and the AUTHENTICATED training surface lock."""
    from .resume_validation import schedule_identities
    return {
        "routing_source_sha256": manifest["routing_source_sha256"],
        "environment_manifest_sha256":
            manifest["environment_manifest_sha256"],
        "config_sha256": manifest["launch_freeze_sha256"],
        "surface_manifest_sha256": training_lock["manifest_sha256"],
        "worker_pool_fingerprint":
            training_lock["worker_pool_fingerprint"],
        "cache_identity": training_lock["cache_identity"],
        "seed": str(seed),
        **schedule_identities(list(rows)),
    }


def _cast_and_assert_lora(trainer) -> None:
    """The explicit FP32 LoRA cast; the frozen key set asserted
    the C2 WAY (365_s F1): `content_sha256(sorted(keys))` over
    the saved-map key naming (the state-dict LoRA keys)."""
    import torch

    from .p0_launch import _validated_profile
    profile = _validated_profile()
    for name, parameter in trainer.model.named_parameters():
        if "lora" in name:
            parameter.data = parameter.data.to(torch.float32)
    saved_keys = sorted(k for k in trainer.model.state_dict()
                        if "lora" in k)
    expected = profile["lora_key_set"]
    if len(saved_keys) != expected["count"] \
            or content_sha256(saved_keys) \
            != expected["sorted_keys_sha256"]:
        raise InfrastructureError(
            f"LoRA key set diverges from the frozen profile "
            f"({len(saved_keys)} keys)")
    for name, parameter in trainer.model.named_parameters():
        if "lora" in name and parameter.dtype is not torch.float32:
            raise InfrastructureError(
                f"{name}: LoRA parameter not FP32 after the cast")


def _prepare_training_objects(trainer, final_index: int) -> tuple:
    """365_s F1: Transformers DISCARDS a scheduler it created
    itself when `train()` begins (`_created_lr_scheduler=True`).
    The optimizer is created through the Trainer API; the
    FULL-horizon scheduler is then created and marked
    USER-PROVIDED so `train()` keeps it — checkpoint zero
    therefore captures the exact objects training uses, and the
    post-train reuse assertion proves it."""
    trainer.create_optimizer()
    trainer.create_scheduler(num_training_steps=final_index,
                             optimizer=trainer.optimizer)
    trainer._created_lr_scheduler = False
    return trainer.optimizer, trainer.lr_scheduler


def _unwrap_optimizer(obj):
    """Follow ONLY `.optimizer` wrapping (accelerate)."""
    inner = obj
    while hasattr(inner, "optimizer"):
        inner = inner.optimizer
    return inner


def _unwrap_scheduler(obj):
    """367_s: follow ONLY `.scheduler` wrapping — a raw torch
    scheduler HOLDS `.optimizer`, so following that attribute
    would land on the shared optimizer and let a REPLACED
    scheduler pass the identity assertion."""
    inner = obj
    while hasattr(inner, "scheduler"):
        inner = inner.scheduler
    return inner


def _save_p0_checkpoint_bundle(trainer, accountant, identities,
                               out_dir: Path, update_index: int,
                               parent_checkpoint: str | None,
                               hf_dir: Path | None
                               ) -> tuple[float, dict]:
    """The P0-specific v1 saver (363_s F3): correct lineage, the
    five-way counter cross-check, the HF binding, and an
    IMMEDIATE validate_resume from disk."""
    import time as _time

    import torch
    from safetensors.torch import save_file

    from . import checkpoint as ckpt
    from .resume_validation import _hf_checkpoint_hashes
    started = _time.monotonic()
    step = int(trainer.state.global_step)
    if not (step == update_index
            and accountant.generated_groups == update_index
            and accountant.consumed_groups == update_index
            and accountant.optimizer_updates == update_index
            and accountant.sampled_completions
            == 8 * update_index):
        raise InfrastructureError(
            f"cadence update {update_index}: counters diverge — "
            f"step {step}, accountant "
            f"{accountant.generated_groups}/"
            f"{accountant.consumed_groups}/"
            f"{accountant.optimizer_updates}/"
            f"{accountant.sampled_completions} (363_s F3)")
    out_dir.mkdir(parents=True, exist_ok=True)
    counters = accountant.authorize_checkpoint()
    save_file({k: v.detach().to("cpu").contiguous()
               for k, v in trainer.model.state_dict().items()
               if "lora" in k},
              str(out_dir /
                  ckpt.CHECKPOINT_BUNDLE_FILENAMES["adapter"]))
    torch.save(trainer.optimizer.state_dict(),
               out_dir / ckpt.CHECKPOINT_BUNDLE_FILENAMES[
                   "optimizer"])
    torch.save(trainer.lr_scheduler.state_dict(),
               out_dir / ckpt.CHECKPOINT_BUNDLE_FILENAMES[
                   "scheduler"])
    rng_state = ckpt.capture_rng_state()
    ckpt.persist_rng_state(out_dir, rng_state)
    filenames = {name: ckpt.CHECKPOINT_BUNDLE_FILENAMES[name]
                 for name in ("adapter", "optimizer",
                              "scheduler", "rng")}
    hashes = ckpt.hash_state_artifacts(out_dir, filenames)
    sampler_position: dict[str, Any] = {
        "next_global_group_index": counters["consumed_groups"],
        "hf_global_step": step,
        "hf_checkpoint_dir": str(hf_dir) if hf_dir else None,
    }
    if hf_dir is not None:
        sampler_position["hf_checkpoint_sha256"] = \
            _hf_checkpoint_hashes(hf_dir)
    record = ckpt.build_checkpoint_record(
        identities=identities, counters=counters,
        rng_state=rng_state, state_artifact_hashes=hashes,
        sampler_position=sampler_position,
        run_id=P0_RUN_ID, segment_id=f"upd{update_index}",
        parent_checkpoint=parent_checkpoint)
    (out_dir / "checkpoint_record.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    ckpt.validate_resume(record, identities, bundle_dir=out_dir)
    proof = {"checkpoint_sha256": record["checkpoint_sha256"],
             "state_artifact_sha256":
                 record["state_artifact_sha256"],
             "counters": counters}
    return _time.monotonic() - started, proof


def _p0_eval_pass(trainer, out_path: Path, deadline: float,
                  eval_context: dict[str, Any]) -> float:
    """One COMPLETE checkpoint evaluation under the frozen batched
    realization, sealed inside the pass; every frozen sampling
    field consumed."""
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
                **inputs, do_sample=bool(sampling["do_sample"]),
                temperature=float(sampling["temperature"]),
                top_p=float(sampling["top_p"]),
                top_k=(0 if sampling["top_k"] is None
                       else int(sampling["top_k"])),
                repetition_penalty=float(
                    sampling["repetition_penalty"]),
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


def _exclude_to(run_dir: Path, source: Path,
                session_index: int) -> None:
    """Move one path (file or directory) into session-scoped
    excluded evidence — retained, hashed into closeouts, never
    deleted, never overwritten."""
    if not source.exists():
        return
    excluded = run_dir / "excluded"
    excluded.mkdir(exist_ok=True)
    target = excluded / f"s{session_index}_{source.name}"
    if target.exists():
        raise InfrastructureError(
            f"{target} exists — excluded evidence is never "
            "overwritten")
    source.rename(target)


def _exclude_partial_evidence(run_dir: Path, name: str,
                              session_index: int) -> None:
    _exclude_to(run_dir, run_dir / "sealed" / name,
                session_index)


def _exclude_uncommitted_attempt(run_dir: Path,
                                 update_index: int,
                                 session_index: int) -> None:
    """367_s F4: an INCOMPLETE cadence attempt (bundle and/or HF
    checkpoint written, evaluation never completed) is excluded
    WHOLE — the bundle, the HF checkpoint, and the raw/sealed
    evaluation all move to session-scoped excluded evidence so a
    rerun can never overwrite retained artifacts."""
    for name in (f"eval_upd{update_index}.jsonl.gz",
                 f"eval_upd{update_index}.jsonl"):
        _exclude_to(run_dir, run_dir / "sealed" / name,
                    session_index)
    _exclude_to(run_dir,
                run_dir / f"checkpoint_bundle_upd{update_index}",
                session_index)
    _exclude_to(run_dir, run_dir / f"checkpoint-{update_index}",
                session_index)


def _p0_cadence_event(context: dict[str, Any],
                      update_index: int,
                      hf_dir: Path | None) -> None:
    """One cadence event: deadline BEFORE; the RETAINED bundle
    (validated immediately); the FULL evaluation; deadline AFTER
    each operation; then — and only then — the ATOMIC
    cadence-complete record (365_s F2)."""
    deadline = context["deadline"]
    run_dir = context["run_dir"]
    _check_deadline(deadline, f"cadence update {update_index}")
    bundle_seconds, proof = _save_p0_checkpoint_bundle(
        context["trainer"], context["accountant"],
        context["identities"],
        run_dir / f"checkpoint_bundle_upd{update_index}",
        update_index, context["last_checkpoint_sha256"], hf_dir)
    _check_deadline(deadline,
                    f"post-checkpoint update {update_index}")
    eval_seconds = _p0_eval_pass(
        context["trainer"],
        run_dir / "sealed" / f"eval_upd{update_index}.jsonl",
        deadline, context["eval_context"])
    _check_deadline(deadline,
                    f"post-evaluation update {update_index}")
    record = {
        "update_index": update_index,
        "bundle_seconds": bundle_seconds,
        "eval_seconds": eval_seconds,
        "checkpoint_proof": proof,
        "hf_checkpoint_dir": str(hf_dir) if hf_dir else None,
    }
    _write_cadence_record(run_dir, record)
    context["last_checkpoint_sha256"] = proof["checkpoint_sha256"]


def _make_p0_callback(context: dict[str, Any],
                      cadence_updates, already_completed=()):
    """Deadline BEFORE the step; consumption at the optimizer; at
    each REMAINING intermediate the callback requests an HF save
    and the cadence event fires at `on_save` (the 235_s F2
    binding)."""
    from transformers import TrainerCallback

    intermediates = set(cadence_updates[1:-1]) \
        - set(already_completed)

    class _P0Callback(TrainerCallback):
        def on_step_begin(self, args, state, control, **kwargs):
            _check_deadline(context["deadline"],
                            "training step begin")

        def on_optimizer_step(self, args, state, control,
                              **kwargs):
            context["accountant"].record_update(1)

        def on_step_end(self, args, state, control, **kwargs):
            scheduler = kwargs.get("lr_scheduler")
            lr = (scheduler.get_last_lr()[0]
                  if scheduler is not None else 0.0)
            context["instrumentation"].on_update_end(lr)
            if int(state.global_step) in intermediates:
                control.should_save = True
            return control

        def on_save(self, args, state, control, **kwargs):
            step = int(state.global_step)
            if step in intermediates:
                hf_dir = Path(args.output_dir) \
                    / f"checkpoint-{step}"
                if not hf_dir.exists():
                    raise InfrastructureError(
                        f"{hf_dir} absent at on_save (235_s F2)")
                _p0_cadence_event(context, step, hf_dir)

    return _P0Callback()


def _record_resumable_interruption(run_dir: Path,
                                   session_index: int,
                                   session_elapsed: float,
                                   error: BaseException) -> None:
    """A RESUMABLE interruption: partial evidence sealed, every
    checkpoint retained, the session closed in the HASH-CHAINED
    log — no ledger write, the launch stays OPEN."""
    from .p0_smoke import _seal_file
    sealed = run_dir / "sealed"
    if sealed.exists():
        for raw in sorted(sealed.iterdir()):
            if raw.is_file() and not raw.name.endswith(".gz"):
                _seal_file(raw)
    _append_session_entry(run_dir, {
        "kind": "session_end", "session_index": session_index,
        "elapsed_seconds": float(session_elapsed),
        "status": "interrupted",
        "last_error": f"{type(error).__name__}: {error}"})


def terminally_abort_p0(*, run_dir: str | Path = P0_RUN_ROOT,
                        question: str, reason: str,
                        ledger_path=None) -> dict[str, Any]:
    """The ONLY operation that closes an interrupted P0 launch
    aborted — explicit, binding the sanitized inventory and the
    validated CUMULATIVE consumed time from the session chain."""
    from .ledger import (
        LEDGER_PATH,
        append_ledger_entry,
        ledger_head,
        verify_ledger_head,
    )
    from .support_run import _hash_directory
    ledger_path = ledger_path or LEDGER_PATH
    run_dir = Path(run_dir)
    manifest = validate_p0_execution_manifest(json.loads(
        (run_dir / "prelaunch" / "p0_launch.json")
        .read_text("utf-8")), recompute=False)
    chain = verify_ledger_head(ledger_head(ledger_path),
                               ledger_path)
    launches = [e for e in chain if e["kind"] == "training_run"
                and e["freeze"].get("p0_launch_manifest_sha256")
                == manifest["manifest_sha256"]]
    if len(launches) != 1:
        raise InfrastructureError(
            "exactly one launch must bind this manifest")
    launch = launches[0]
    if any(e for e in chain if e["kind"] == "closeout"
           and e.get("closes_entry_sha256")
           == launch["entry_sha256"]):
        raise InfrastructureError(
            "this launch is already closed")
    state = _session_state(run_dir)
    state = _close_killed_session(run_dir, state)
    cumulative = state["cumulative_elapsed_seconds"]
    return append_ledger_entry(
        {"kind": "closeout", "question": question,
         "motivating_evidence": "P0 TERMINALLY ABORTED (explicit)",
         "freeze": {
             "p0_launch_manifest_sha256":
                 manifest["manifest_sha256"],
             "partial_artifact_hashes": _hash_directory(run_dir)},
         "parent": ledger_head(ledger_path),
         "budget_allocated_gpu_hours": 0.0,
         "budget_consumed_gpu_hours":
             round(cumulative / 3600.0, 4),
         "closes_entry_sha256": launch["entry_sha256"],
         "terminal_status": "aborted",
         "interpretation": reason,
         "outcome_informed": False,
         "outcome_pointer": str(run_dir)},
        ledger_head(ledger_path), ledger_path)


_P0_RECORD_KEYS = frozenset({
    "run", "p0_launch_manifest_sha256", "launch_freeze_sha256",
    "execution_identity_sha256", "launch_entry_sha256",
    "cadence_completed", "checkpoints", "whole_run_seconds",
    "sealed_sha256", "development_only"})

def _bundle_inventory() -> frozenset[str]:
    """367_s F1: the bundle inventory DERIVES from the
    authoritative checkpoint contract — the writer and the
    verifier can never disagree on filenames."""
    from . import checkpoint as ckpt
    return frozenset(
        {ckpt.CHECKPOINT_BUNDLE_FILENAMES[name]
         for name in ("adapter", "optimizer", "scheduler", "rng")}
        | {"checkpoint_record.json"})


def _read_authorized_prefix(segment_file: Path,
                            start_index: int,
                            authorized_end: int,
                            label: str) -> list[dict[str, Any]]:
    """369_s F2: read and validate EXACTLY the
    checkpoint-authorized prefix — excluded tail bytes are NEVER
    parsed (a SIGKILL can truncate a tail row mid-write; the
    complete gzip remains preserved evidence, but only the
    authorized rows are consumed)."""
    import gzip
    rows: list[dict[str, Any]] = []
    with gzip.open(segment_file, "rt",
                   encoding="utf-8") as handle:
        for offset, line in enumerate(handle):
            index = start_index + offset
            if index >= authorized_end:
                break
            group = json.loads(line)
            if group["global_group_index"] != index:
                raise InfrastructureError(
                    f"segment {label}: group index "
                    f"{group['global_group_index']} out of "
                    "sequence")
            if len(group["completions"]) != 8 \
                    or len(group["actions"]) != 8 \
                    or len(group["assignments"]) != 8 \
                    or len(group["rewards"]) != 8:
                raise InfrastructureError(
                    f"segment {label} group {index}: malformed "
                    "row (365_s)")
            rows.append(group)
    return rows


def _expected_p0_identities(manifest: Mapping[str, Any],
                            prelaunch: Path) -> dict[str, str]:
    """365_s: the verifier re-derives ALL TEN identity fields
    INDEPENDENTLY — from the manifest, the freeze under its pin,
    the AUTHENTICATED training surface lock, and the frozen
    schedule — and every bundle must match exactly."""
    from .p0_launch import prepare_p0_dataset
    from .p0_replay import restore_extension_surface_if_absent
    from .unit_c2_sample import UNIT_C2_CONFIG
    training_surface = dev_support.load_dev_surface(
        restore_extension_surface_if_absent(),
        expected_lock_sha256=UNIT_C2_CONFIG[
            "extension_surface_lock_sha256"])
    # 369_s: the ARCHIVED prelaunch copy under the MANIFEST pin —
    # never the current committed default (historical)
    freeze = load_real_launch_freeze(
        prelaunch / "launch_freeze.json")
    preparation = prepare_p0_dataset(
        prelaunch / "launch_freeze.json",
        manifest["launch_freeze_sha256"])
    return _p0_identities(manifest, training_surface["lock"],
                          preparation["trainer_rows"],
                          freeze.runtime.seed)


def verify_p0_run(run_dir: str | Path, *, ledger_path,
                  expected_head_sha256: str | None
                  ) -> dict[str, Any]:
    """The P0 terminal verifier (hardened per 363_s F5 + 365_s):
    trusts NOTHING declared. Chain-authenticated launch; exact
    frozen cadence from the loaded identity; every bundle
    re-validated from disk against INDEPENDENTLY re-derived
    identities, exact bundle inventories, the parent chain, and
    every bound HF checkpoint; exact sealed inventories; every
    evaluation trace re-read (90 observations in lock order,
    eight completions/rewards each); the training trajectory
    merged from the session log's AUTHORIZED segment prefixes
    (post-checkpoint tails excluded) and compared to the frozen
    schedule; HISTORICAL environment self-validation; the
    session-chain accounting within the ceiling; the lifecycle
    and closeout consistency."""
    import gzip

    from . import checkpoint as ckpt
    from .ledger import verify_ledger_head
    from .p0_contract import load_p0_science_contract as _load_c
    from .p0_schedule import schedule_for_epochs
    from .resume_validation import verify_hf_checkpoint_against_bundle
    from .support_run import _sha_file, attest_environment
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
    prelaunch = run_dir / "prelaunch"
    # 367_s: the manifest-bound execution root is enforced, and
    # the ARCHIVED prelaunch artifacts verify under the MANIFEST
    # pins (genuinely historical — never the current committed
    # copies)
    if str(run_dir.resolve()) != manifest["execution_root"]:
        raise InfrastructureError(
            "the run root diverges from the manifest's execution "
            "root (367_s)")
    from .p0_launch import load_p0_launch_freeze
    load_p0_launch_freeze(prelaunch / "launch_freeze.json",
                          manifest["launch_freeze_sha256"])
    # 365_s: HISTORICAL self-validation — evidence stays
    # verifiable after later source commits
    frozen_env = json.loads(
        (prelaunch / "env_manifest.json").read_text("utf-8"))
    if dev_support.validate_env_self_hash(frozen_env) \
            != manifest["environment_manifest_sha256"]:
        raise InfrastructureError(
            "the prelaunch environment does not bind to the "
            "manifest")
    execute_env_path = run_dir / "execute_env_manifest.json"
    if execute_env_path.exists():
        execute_env = json.loads(
            execute_env_path.read_text("utf-8"))
        dev_support.validate_env_self_hash(execute_env)
        attest_environment(frozen_env, execute_env)
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
            or record["run"] != P0_RUN_ID \
            or record["development_only"] is not True:
        raise InfrastructureError(
            "P0 record does not bind the authenticated launch")
    identity = load_p0_execution_identity(
        prelaunch / "execution_identity.json",
        expected_sha256=manifest["execution_identity_sha256"])
    cadence = list(identity["cadence"]["update_indices"])
    if record["cadence_completed"] != cadence:
        raise InfrastructureError(
            "cadence_completed is not the exact frozen "
            "eleven-point cadence (363_s F5)")
    if set(record["checkpoints"]) != {str(i) for i in cadence}:
        raise InfrastructureError(
            "checkpoint blocks do not cover exactly the frozen "
            "cadence")
    _require_nonneg_finite(record["whole_run_seconds"],
                           "whole_run_seconds")
    if record["whole_run_seconds"] > \
            manifest["budget_gpu_hours"] * 3600.0:
        raise InfrastructureError(
            "the recorded run time exceeds the ten-hour ceiling "
            "(363_s F6)")
    # the record's blocks must BE the persisted cadence records
    persisted = _load_cadence_records(run_dir, cadence)
    if set(persisted) != {str(i) for i in cadence}:
        raise InfrastructureError(
            "persisted cadence records do not cover the frozen "
            "cadence")
    # every bundle from disk against INDEPENDENT identities
    expected_identities = _expected_p0_identities(manifest,
                                                 prelaunch)
    parent = None
    for update_index in cadence:
        block = record["checkpoints"][str(update_index)]
        cadence_record = persisted[str(update_index)]
        if block != {"bundle_seconds":
                     cadence_record["bundle_seconds"],
                     "eval_seconds":
                     cadence_record["eval_seconds"],
                     "checkpoint_proof":
                     cadence_record["checkpoint_proof"]}:
            raise InfrastructureError(
                f"update {update_index}: record block diverges "
                "from the persisted cadence record (365_s)")
        bundle = run_dir / f"checkpoint_bundle_upd{update_index}"
        on_disk = {p.name for p in bundle.iterdir()
                   if p.is_file()}
        if on_disk != set(_bundle_inventory()):
            raise InfrastructureError(
                f"update {update_index}: bundle inventory is not "
                f"exact: {sorted(on_disk)[:6]} (365_s)")
        disk_record = json.loads(
            (bundle / "checkpoint_record.json")
            .read_text("utf-8"))
        proof = cadence_record["checkpoint_proof"]
        if set(proof) != {"checkpoint_sha256",
                          "state_artifact_sha256", "counters"}:
            raise InfrastructureError(
                f"update {update_index}: checkpoint proof schema")
        if disk_record["checkpoint_sha256"] \
                != proof["checkpoint_sha256"] \
                or disk_record["state_artifact_sha256"] \
                != proof["state_artifact_sha256"] \
                or disk_record["counters"] != proof["counters"]:
            raise InfrastructureError(
                f"update {update_index}: the disk record diverges "
                "from the recorded proof")
        expected_counters = {
            "generated_groups": update_index,
            "consumed_groups": update_index,
            "optimizer_updates": update_index,
            "sampled_completions": 8 * update_index}
        if dict(disk_record["counters"]) != expected_counters:
            raise InfrastructureError(
                f"update {update_index}: counters diverge from "
                "the cadence position (363_s F3)")
        if disk_record.get("parent_checkpoint") != parent \
                or disk_record.get("run_id") != P0_RUN_ID \
                or disk_record.get("segment_id") \
                != f"upd{update_index}":
            raise InfrastructureError(
                f"update {update_index}: run/segment/parent "
                "lineage diverges (363_s F3)")
        if dict(disk_record["identities"]) != expected_identities:
            raise InfrastructureError(
                f"update {update_index}: identities diverge from "
                "the independent re-derivation (365_s)")
        ckpt.validate_resume(disk_record, expected_identities,
                             bundle_dir=bundle)
        hf_dir = disk_record["sampler_position"][
            "hf_checkpoint_dir"]
        if hf_dir is not None:
            verify_hf_checkpoint_against_bundle(
                bundle, Path(hf_dir), disk_record)
        parent = disk_record["checkpoint_sha256"]
    # sessions: validated chain, all closed on a complete run
    sessions = _session_state(run_dir)
    starts = sessions["starts"]
    if not starts:
        raise InfrastructureError("no session records (365_s)")
    # EXACT sealed inventory
    sealed = run_dir / "sealed"
    on_disk = {p.name for p in sealed.iterdir() if p.is_file()}
    eval_files = {f"eval_upd{i}.jsonl.gz" for i in cadence}
    segment_names = {
        f"training_trace_s{k}.jsonl.gz" for k in starts
        if starts[k]["mode"] in ("fresh", "resume")}
    present_segments = {n for n in segment_names if n in on_disk}
    expected_sealed = eval_files | present_segments \
        | {"trainer_log_history.json.gz"}
    if on_disk != expected_sealed \
            or set(record["sealed_sha256"]) != expected_sealed \
            or not present_segments:
        raise InfrastructureError(
            "sealed inventory is not exactly the frozen set "
            "(363_s F5)")
    for name, expected_sha in record["sealed_sha256"].items():
        if _sha_file(sealed / name) != expected_sha:
            raise InfrastructureError(
                f"sealed file {name} does not match the recorded "
                "hash")
    # every evaluation trace re-read: 90 observations in lock
    # order, eight completions and eight finite rewards (365_s)
    lock_order = list(
        _val_lock_for_identity()["ordered_observation_ids"])
    for i in cadence:
        rows = []
        with gzip.open(sealed / f"eval_upd{i}.jsonl.gz", "rt",
                       encoding="utf-8") as handle:
            for line in handle:
                rows.append(json.loads(line))
        if [r["observation_id"] for r in rows] != lock_order:
            raise InfrastructureError(
                f"eval_upd{i}: observation order is not the lock "
                "order (365_s)")
        for r in rows:
            if len(r["completions"]) != 8 \
                    or len(r["rewards"]) != 8:
                raise InfrastructureError(
                    f"eval_upd{i}: not eight completions/rewards")
            for value in r["rewards"]:
                _require_nonneg_finite(value, "eval reward")
    # the training trajectory: AUTHORIZED segment prefixes merged
    # (post-checkpoint tails are excluded evidence, 365_s F3)
    contract = _load_c()
    freeze = load_real_launch_freeze(
        prelaunch / "launch_freeze.json")
    schedule = schedule_for_epochs(
        contract, freeze.launch_plan.launch_epochs)
    # 367_s F2: merge boundaries come from TRAINING sessions
    # (fresh/resume) ONLY; finalize sessions are validated
    # separately (no trace segment, start_group_index == -1)
    ordered_sessions = [k for k in sorted(starts)
                        if starts[k]["mode"] in ("fresh",
                                                 "resume")]
    for k in sorted(starts):
        if starts[k]["mode"] == "finalize":
            if starts[k]["start_group_index"] != -1 or (
                    sealed / f"training_trace_s{k}.jsonl.gz"
            ).exists():
                raise InfrastructureError(
                    f"finalize session {k} must carry no "
                    "training segment (367_s F2)")
    merged: list[dict[str, Any]] = []
    for position, k in enumerate(ordered_sessions):
        segment_file = sealed / f"training_trace_s{k}.jsonl.gz"
        if not segment_file.exists():
            continue
        start_index = int(starts[k]["start_group_index"])
        # the NEXT TRAINING session's resume point defines this
        # segment's checkpoint-authorized prefix (365_s F3)
        later = ordered_sessions[position + 1:]
        authorized_end = (int(starts[later[0]]
                              ["start_group_index"])
                          if later else len(schedule))
        merged.extend(_read_authorized_prefix(
            segment_file, start_index, authorized_end, f"s{k}"))
    if [g["global_group_index"] for g in merged] != \
            list(range(len(schedule))) or \
            [g["observation_id"] for g in merged] != schedule:
        raise InfrastructureError(
            f"the merged authorized trajectory ({len(merged)} "
            f"groups) is not the exact frozen "
            f"{len(schedule)}-group schedule (363_s F5/365_s F3)")
    # accounting within the ceiling; lifecycle consistency
    cumulative = sessions["cumulative_elapsed_seconds"]
    closeouts = [e for e in chain if e["kind"] == "closeout"
                 and e.get("closes_entry_sha256")
                 == launch["entry_sha256"]]
    if closeouts:
        status = closeouts[0].get("terminal_status")
        if status == "complete":
            if sessions["unclosed_session_index"] is not None:
                raise InfrastructureError(
                    "a complete run cannot carry an unclosed "
                    "session (365_s)")
            if cumulative > manifest["budget_gpu_hours"] * 3600.0:
                raise InfrastructureError(
                    "cumulative session time exceeds the ceiling "
                    "(363_s F6)")
            consumed = closeouts[0]["budget_consumed_gpu_hours"]
            _require_nonneg_finite(consumed, "closeout consumed")
            if consumed > manifest["budget_gpu_hours"] \
                    or record["whole_run_seconds"] \
                    > consumed * 3600.0 + 1.0:
                raise InfrastructureError(
                    "closeout consumed time is inconsistent with "
                    "the record (365_s)")
            from .support_run import _hash_directory
            if closeouts[0]["freeze"].get(
                    "terminal_artifact_hashes") \
                    != _hash_directory(run_dir):
                raise InfrastructureError(
                    "terminal evidence does not match the "
                    "closeout inventory")
    return {"verdict": "PASS",
            "launch_entry_sha256": launch["entry_sha256"],
            "lifecycle": (closeouts[0].get("terminal_status")
                          if closeouts else "open")}


def _persist_record_atomic(path: Path, payload: Mapping[str, Any]
                           ) -> None:
    """365_s: `p0_record.json` is atomically REPLACEABLE — a
    failure after it is written must remain finalizable."""
    import os
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True)
                   + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _finalize_p0_completion(*, run_dir: Path,
                            manifest: Mapping[str, Any],
                            cadence: list[int],
                            launch_entry_sha256: str,
                            session_index: int,
                            session_started_monotonic: float,
                            question: str,
                            ledger_path) -> dict[str, Any]:
    """The recoverable completion tail (365_s): rebuild the
    record from the PERSISTED cadence records + sealed hashes,
    verify OPEN, close the session in the chained log, recompute
    the CUMULATIVE total AFTER persistence and verification,
    enforce the ceiling, append the complete closeout, and
    re-verify against the completed head."""
    import time as _time

    from .ledger import append_ledger_entry, ledger_head
    from .support_run import _hash_directory, _sha_file
    sealed = run_dir / "sealed"
    persisted = _load_cadence_records(run_dir, cadence)
    if set(persisted) != {str(i) for i in cadence}:
        raise InfrastructureError(
            "finalization requires every cadence record")
    sealed_hashes = {p.name: _sha_file(p)
                     for p in sorted(sealed.iterdir())}
    prior = _session_state(run_dir)["cumulative_elapsed_seconds"]
    record = {
        "run": P0_RUN_ID,
        "p0_launch_manifest_sha256": manifest["manifest_sha256"],
        "launch_freeze_sha256": manifest["launch_freeze_sha256"],
        "execution_identity_sha256":
            manifest["execution_identity_sha256"],
        "launch_entry_sha256": launch_entry_sha256,
        "cadence_completed": list(cadence),
        "checkpoints": {
            key: {"bundle_seconds": value["bundle_seconds"],
                  "eval_seconds": value["eval_seconds"],
                  "checkpoint_proof": value["checkpoint_proof"]}
            for key, value in persisted.items()},
        "whole_run_seconds": prior
        + (_time.monotonic() - session_started_monotonic),
        "sealed_sha256": sealed_hashes,
        "development_only": True,
    }
    _persist_record_atomic(run_dir / "p0_record.json", record)
    verify_p0_run(run_dir, ledger_path=ledger_path,
                  expected_head_sha256=launch_entry_sha256)
    # 367_s: the EXPENSIVE terminal directory hashing happens
    # INSIDE the measured window; after the session closes, only
    # the session log itself is re-hashed (the closeout must bind
    # the log INCLUDING its end entry). The residual ledger
    # append + final re-verification are structurally outside the
    # recorded figure (a closeout cannot contain its own future)
    # and are disclosed as such.
    terminal_hashes = _hash_directory(run_dir)
    _append_session_entry(run_dir, {
        "kind": "session_end", "session_index": session_index,
        "elapsed_seconds":
            _time.monotonic() - session_started_monotonic,
        "status": "completed"})
    terminal_hashes[_SESSION_LOG] = _sha_file(
        run_dir / _SESSION_LOG)
    total_seconds = _session_state(run_dir)[
        "cumulative_elapsed_seconds"]
    if total_seconds > manifest["budget_gpu_hours"] * 3600.0:
        raise InfrastructureError(
            "cumulative run time crossed the ten-hour ceiling "
            "before closeout (363_s F6)")
    measured = round(total_seconds / 3600.0, 4)
    closeout = append_ledger_entry(
        {"kind": "closeout", "question": question,
         "motivating_evidence": "P0 COMPLETE (development-only)",
         "freeze": {
             "p0_record_file_sha256":
                 _sha_file(run_dir / "p0_record.json"),
             "execute_env_file_sha256":
                 _sha_file(run_dir / "execute_env_manifest.json"),
             "terminal_artifact_hashes": terminal_hashes,
         },
         "parent": ledger_head(ledger_path),
         "budget_allocated_gpu_hours": 0.0,
         "budget_consumed_gpu_hours": measured,
         "closes_entry_sha256": launch_entry_sha256,
         "terminal_status": "complete",
         "outcome_informed": False,
         "outcome_pointer": str(run_dir / "p0_record.json")},
        ledger_head(ledger_path), ledger_path)
    verify_p0_run(run_dir, ledger_path=ledger_path,
                  expected_head_sha256=closeout["entry_sha256"])
    return {**record, "measured_gpu_hours": measured,
            "closeout_entry_sha256": closeout["entry_sha256"],
            "ledger_head": closeout["entry_sha256"]}


def _p0_session(*, run_dir: Path, manifest: Mapping[str, Any],
                identity: Mapping[str, Any], rows,
                runtime_seed: int, deadline: float,
                resume_state: Mapping[str, Any] | None,
                question: str, ledger_path,
                launch_entry_sha256: str) -> dict[str, Any]:
    """The shared session core for fresh execution and resume."""
    import time as _time

    from . import checkpoint as ckpt
    from . import p0_smoke
    from .p0_replay import restore_extension_surface_if_absent
    from .p0_smoke import _make_smoke_reward, _seal_file, \
        _strip_console_callbacks
    from .p0_val import VAL_RUN_ROOT, val_cohort_observations
    from .resume_validation import make_validation_reward
    from .support_run import _default_environment, _persist_verified
    from .unit_c2_sample import UNIT_C2_CONFIG
    started = _time.monotonic()
    session_index = _session_state(run_dir)["next_session_index"]
    _append_session_entry(run_dir, {
        "kind": "session_start", "session_index": session_index,
        "mode": "fresh" if resume_state is None else "resume",
        "start_group_index":
            0 if resume_state is None
            else int(resume_state["start_group_index"]),
        "resume_update_index":
            None if resume_state is None
            else int(resume_state["resume_update_index"]),
        "wall_start_utc": __import__("time").time()})
    try:
        if not (run_dir / "execute_env_manifest.json").exists():
            _persist_verified(
                run_dir / "execute_env_manifest.json",
                _default_environment())
        sealed = run_dir / "sealed"
        sealed.mkdir(parents=True, exist_ok=True)

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
        cadence_updates = list(
            identity["cadence"]["update_indices"])
        final_index = cadence_updates[-1]
        realization = identity["evaluation"][
            "checkpoint_eval_realization"]
        if realization["realization_sha256"] \
                != P0_EVAL_REALIZATION_SHA256:
            raise InfrastructureError(
                "the identity's executed realization pin diverges")
        eval_context = {
            "surface": val_surface["surface"], "seeds": seeds,
            "observations": observations,
            "sampling": identity["evaluation"]["sampling"],
        }
        identities = _p0_identities(
            manifest, training_surface["lock"], rows,
            runtime_seed)

        if resume_state is None:
            accountant = ckpt.GroupAccountant()
            start_group_index = 0
            already_completed: tuple[int, ...] = ()
            last_sha = None
        else:
            accountant = ckpt.GroupAccountant.restore(
                resume_state["counters"])
            start_group_index = int(
                resume_state["start_group_index"])
            already_completed = tuple(
                resume_state["cadence_completed"])
            last_sha = resume_state["last_checkpoint_sha256"]
        trace_path = sealed \
            / f"training_trace_s{session_index}.jsonl"

        instrumentation = p0_smoke._EpochInstrumentation()
        base_reward = make_validation_reward(
            training_surface["surface"], accountant, trace_path,
            group_size=identity["evaluation"]["sampling"][
                "group_size"],
            start_group_index=start_group_index)
        reward = _make_smoke_reward(base_reward, instrumentation,
                                    deadline)
        context: dict[str, Any] = {
            "run_dir": run_dir, "deadline": deadline,
            "accountant": accountant,
            "instrumentation": instrumentation,
            "identities": identities,
            "eval_context": eval_context,
            "last_checkpoint_sha256": last_sha,
        }
        callback = _make_p0_callback(context, cadence_updates,
                                     already_completed)
        trainer = _build_p0_trainer(
            rows, reward, run_dir, runtime_seed,
            max_steps=final_index, extra_callbacks=(callback,))
        context["trainer"] = trainer
        _strip_console_callbacks(trainer)
        _cast_and_assert_lora(trainer)
        pre_optimizer, pre_scheduler = _prepare_training_objects(
            trainer, final_index)

        if resume_state is None:
            # checkpoint ZERO: P0's FIRST execution (charter §7)
            _p0_cadence_event(context, 0, None)
            instrumentation.start_epoch()
            trainer.train()
        else:
            instrumentation.start_epoch()
            trainer.train(resume_from_checkpoint=str(
                resume_state["hf_checkpoint_dir"]))
        if _unwrap_optimizer(trainer.optimizer) \
                is not _unwrap_optimizer(pre_optimizer) \
                or _unwrap_scheduler(trainer.lr_scheduler) \
                is not _unwrap_scheduler(pre_scheduler):
            raise InfrastructureError(
                "train() replaced the pre-created optimizer/"
                "scheduler — checkpoint zero did not capture the "
                "training objects (363_s F1)")
        _check_deadline(deadline, "post-training boundary")
        if int(trainer.state.global_step) != final_index:
            raise InfrastructureError(
                f"trainer ended at step {trainer.state.global_step}"
                f" != the frozen final update {final_index}")
        # 369_s F1: the training trace and the trainer log seal
        # FIRST — the final cadence record is the LAST durable
        # commit, so an all-records-complete state ALWAYS implies
        # sealed finalization inputs (finalize-only resume can
        # never fail on missing evidence)
        _seal_file(trace_path)
        log_name = "trainer_log_history.json"
        if (sealed / (log_name + ".gz")).exists():
            _exclude_partial_evidence(run_dir, log_name + ".gz",
                                      session_index)
        log_path = sealed / log_name
        log_path.write_text(
            json.dumps(trainer.state.log_history, sort_keys=True),
            encoding="utf-8")
        _seal_file(log_path)
        _p0_cadence_event(context, final_index, None)
    except BaseException as error:
        _record_resumable_interruption(
            run_dir, session_index,
            _time.monotonic() - started, error)
        raise
    return _finalize_p0_completion(
        run_dir=run_dir, manifest=manifest,
        cadence=list(identity["cadence"]["update_indices"]),
        launch_entry_sha256=launch_entry_sha256,
        session_index=session_index,
        session_started_monotonic=started,
        question=question, ledger_path=ledger_path)


def execute_p0_run(*, run_dir: str | Path = P0_RUN_ROOT,
                   expected_manifest_sha256: str,
                   expected_head_sha256: str,
                   question: str, motivating_evidence: str,
                   ledger_path=None) -> dict[str, Any]:
    """Phase 2 (GPU), FRESH launch: VRAM preflight → admission
    (the ONLY input source) → the shared session core."""
    from .ledger import LEDGER_PATH
    from .resume_validation import gpu_session_preflight
    ledger_path = ledger_path or LEDGER_PATH
    run_dir = Path(run_dir)
    prelaunch = run_dir / "prelaunch"
    manifest = validate_p0_execution_manifest(json.loads(
        (prelaunch / "p0_launch.json").read_text("utf-8")))
    prepared_env = json.loads(
        (prelaunch / "env_manifest.json").read_text("utf-8"))
    for path in (run_dir / "sealed", run_dir / "p0_record.json",
                 run_dir / "execute_env_manifest.json",
                 run_dir / _SESSION_LOG, run_dir / "cadence"):
        if path.exists():
            raise InfrastructureError(
                f"{path} exists — outputs are preflighted before "
                "admission")
    gpu_session_preflight()
    bundle = admit_p0_execution(
        execution_manifest=manifest,
        expected_manifest_sha256=expected_manifest_sha256,
        prepared_environment=prepared_env,
        expected_head_sha256=expected_head_sha256,
        question=question,
        motivating_evidence=motivating_evidence,
        run_dir=run_dir, ledger_path=ledger_path)
    import time as _time
    deadline = _time.monotonic() \
        + manifest["budget_gpu_hours"] * 3600.0
    return _p0_session(
        run_dir=run_dir, manifest=manifest,
        identity=bundle["execution_identity"],
        rows=bundle["preparation"]["trainer_rows"],
        runtime_seed=bundle["preparation"]["runtime"].seed,
        deadline=deadline, resume_state=None, question=question,
        ledger_path=ledger_path,
        launch_entry_sha256=bundle["launch_entry_sha256"])


def resume_p0_run(*, run_dir: str | Path = P0_RUN_ROOT,
                  expected_manifest_sha256: str,
                  question: str,
                  ledger_path=None) -> dict[str, Any]:
    """The resume entry point (363_s F4 / 365_s): the ORIGINAL
    launch must be OPEN (resume NEVER re-admits); accounting from
    the validated session chain (a killed session is closed with
    its conservative inferred elapsed); resume state from the
    ATOMIC cadence records — never bundle existence; the live
    environment and bound run root re-attested; superseded
    partial evaluations excluded; an all-cadence-complete state
    finalizes WITHOUT the GPU."""
    import time as _time

    from . import checkpoint as ckpt
    from .ledger import LEDGER_PATH, ledger_head, verify_ledger_head
    from .p0_launch import prepare_p0_dataset
    from .p0_replay import restore_extension_surface_if_absent
    from .resume_validation import (
        attested_environment_sha256,
        gpu_session_preflight,
        verify_hf_checkpoint_against_bundle,
    )
    from .support_run import _default_environment, attest_environment
    from .unit_c2_sample import UNIT_C2_CONFIG
    ledger_path = ledger_path or LEDGER_PATH
    run_dir = Path(run_dir)
    prelaunch = run_dir / "prelaunch"
    manifest = validate_p0_execution_manifest(json.loads(
        (prelaunch / "p0_launch.json").read_text("utf-8")))
    if manifest["manifest_sha256"] != expected_manifest_sha256:
        raise InfrastructureError(
            "the execution manifest does not match the externally "
            "supplied hash (360_s P1-2)")
    if str(run_dir.resolve()) != manifest["execution_root"]:
        raise InfrastructureError(
            "the resolved run root diverges from the manifest's "
            "execution root (365_s)")
    chain = verify_ledger_head(ledger_head(ledger_path),
                               ledger_path)
    launches = [e for e in chain if e["kind"] == "training_run"
                and e["freeze"].get("p0_launch_manifest_sha256")
                == manifest["manifest_sha256"]]
    if len(launches) != 1:
        raise InfrastructureError(
            "exactly one launch must bind this manifest")
    launch = launches[0]
    if any(e for e in chain if e["kind"] == "closeout"
           and e.get("closes_entry_sha256")
           == launch["entry_sha256"]):
        raise InfrastructureError(
            "this launch is CLOSED — resume applies only to an "
            "open interrupted launch (363_s F4)")
    # 365_s: live environment + run-root attestation on EVERY
    # resume
    freeze = load_real_launch_freeze(
        prelaunch / "launch_freeze.json")
    prepared_env = json.loads(
        (prelaunch / "env_manifest.json").read_text("utf-8"))
    live_env = _default_environment()
    dev_support.validate_environment_manifest_binding(live_env)
    attest_environment(prepared_env, live_env)
    if attested_environment_sha256(live_env) \
            != freeze.runtime.attested_environment_sha256:
        raise InfrastructureError(
            "the live environment does not attest to the freeze's "
            "commit-independent expectation (330_f §4.4)")
    # accounting from the validated chain; close a killed session
    state = _session_state(run_dir)
    state = _close_killed_session(run_dir, state)
    prior = state["cumulative_elapsed_seconds"]
    remaining = manifest["budget_gpu_hours"] * 3600.0 - prior
    if remaining <= 0:
        raise InfrastructureError(
            "the cumulative ten-hour ceiling is exhausted — only "
            "terminally_abort_p0 remains (363_s F6)")
    identity = load_p0_execution_identity(
        prelaunch / "execution_identity.json",
        expected_sha256=manifest["execution_identity_sha256"])
    cadence = list(identity["cadence"]["update_indices"])
    completed_records = _load_cadence_records(run_dir, cadence)
    completed = [i for i in cadence
                 if str(i) in completed_records]
    session_index = _session_state(run_dir)[
        "next_session_index"]
    if len(completed) == len(cadence):
        # 365_s: completion finalization is RECOVERABLE — no GPU
        started = _time.monotonic()
        _append_session_entry(run_dir, {
            "kind": "session_start",
            "session_index": session_index,
            "mode": "finalize", "start_group_index": -1,
            "resume_update_index": None,
            "wall_start_utc": _time.time()})
        return _finalize_p0_completion(
            run_dir=run_dir, manifest=manifest, cadence=cadence,
            launch_entry_sha256=launch["entry_sha256"],
            session_index=session_index,
            session_started_monotonic=started,
            question=question, ledger_path=ledger_path)
    gpu_session_preflight()
    positive_completed = [i for i in completed if i > 0
                          and completed_records[str(i)]
                          ["hf_checkpoint_dir"]]
    if not positive_completed:
        raise InfrastructureError(
            "no resumable positive-index cadence record exists — "
            "only terminally_abort_p0 remains (363_s F4)")
    resume_index = positive_completed[-1]
    resume_record_meta = completed_records[str(resume_index)]
    bundle_dir = run_dir / f"checkpoint_bundle_upd{resume_index}"
    disk_record = json.loads(
        (bundle_dir / "checkpoint_record.json").read_text("utf-8"))
    if disk_record["checkpoint_sha256"] != resume_record_meta[
            "checkpoint_proof"]["checkpoint_sha256"]:
        raise InfrastructureError(
            "the resume bundle diverges from its cadence record")
    training_surface = dev_support.load_dev_surface(
        restore_extension_surface_if_absent(),
        expected_lock_sha256=UNIT_C2_CONFIG[
            "extension_surface_lock_sha256"])
    preparation = prepare_p0_dataset(
        prelaunch / "launch_freeze.json",
        manifest["launch_freeze_sha256"])
    identities = _p0_identities(
        manifest, training_surface["lock"],
        preparation["trainer_rows"], freeze.runtime.seed)
    ckpt.validate_resume(disk_record, identities,
                         bundle_dir=bundle_dir)
    hf_dir = Path(resume_record_meta["hf_checkpoint_dir"])
    verify_hf_checkpoint_against_bundle(bundle_dir, hf_dir,
                                        disk_record)
    # 365_s F2 / 367_s F4: every UNCOMMITTED cadence attempt
    # (no atomic record) is excluded WHOLE — bundle, HF
    # checkpoint, and evaluation — so the rerun never overwrites
    # retained evidence
    for pending in cadence:
        if str(pending) not in completed_records:
            _exclude_uncommitted_attempt(run_dir, pending,
                                         session_index)
    deadline = _time.monotonic() + remaining
    resume_state = {
        "counters": disk_record["counters"],
        "start_group_index": disk_record["counters"][
            "consumed_groups"],
        "resume_update_index": resume_index,
        "cadence_completed": completed[:completed.index(
            resume_index) + 1],
        "last_checkpoint_sha256":
            disk_record["checkpoint_sha256"],
        "hf_checkpoint_dir": hf_dir,
    }
    return _p0_session(
        run_dir=run_dir, manifest=manifest, identity=identity,
        rows=preparation["trainer_rows"],
        runtime_seed=freeze.runtime.seed, deadline=deadline,
        resume_state=resume_state, question=question,
        ledger_path=ledger_path,
        launch_entry_sha256=launch["entry_sha256"])


def _build_p0_trainer(rows, reward, run_dir: Path, seed: int, *,
                      max_steps: int, extra_callbacks=()):
    """The canonical-profile construction for the FULL horizon
    (`max_steps` from the admitted execution identity)."""
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
        max_steps=max_steps, loss_type=grpo["loss"],
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
        save_strategy="no", save_total_limit=None,
        disable_tqdm=True)
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
