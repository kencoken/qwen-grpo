"""P0 precursors, Unit Y — the cycle cohort record and the FINAL
R_cycle reserve (the SIGNED precursors plan 326_f/328_f/330_f:
328_f §1 R_cycle ≠ the P0 finalization reserve; 330_f §1 CRN
seeds; 330_f §3 one exact recomputable reserve rule; 327_s #5 /
328_f §5 the cycle record's frozen meaning).

Y1 — `cycle_record` (→ the `cycle_record_sha256` pin): the
one-reveal cycle-end holdout, bound BEFORE any surface exists:
the deterministic outcome-blind cohort (six cells × latent prefix
0–4 × three renderers, 90 observations), the canonical
natural-mixture weights, the COMPLETE evaluation identity (domain
`cycle_eval`, fresh base seed, the frozen CRN rule, the canonical
sampling options, the frozen 720-entry seed schedule), the FIXED
checkpoint rule (checkpoint zero + the FINAL P0 checkpoint; P0 is
declared to close this development cycle), the partial-reveal
rule, the future materialization plan, and the execution
identities it will be materialized against (read from the
AUTHENTICATED Unit-V evidence — the same frozen pool).

Y2 — the final `R_cycle` reserve (→ the `r_cycle_record_sha256`
pin): ONE exact recomputable rule — the registered validator-gated
basis (231_f retained: cohort × multiplier × measured support
seconds/observation, ceil to whole GPU-hours) AND an independent
itemized closure ceiling, BOTH persisted; the reserve is their
rounded maximum, and the complete closure obligation set is
proven to fit under it. `record_final_r_cycle` replaces the
provisional 5.0 in the ledger through the now-enabled
validator-gated final path — executed only AFTER this unit is
signed."""
from __future__ import annotations

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
from .p0_val import (
    VAL_EVIDENCE_DIR,
    VAL_LOCK_SHA256,
    seed_for_completion,
    validate_val_launch_manifest,
)
from .support_run import _sha_file

CYCLE_RECORD_PATH = Path("plans/conductor/p0/cycle_record.json")
R_CYCLE_RECORD_PATH = Path("plans/conductor/p0/r_cycle_reserve.json")

CYCLE_CELLS = ("code_atomic", "fork_join", "lookup_atomic",
               "lookup_math", "math_atomic", "math_code")

CYCLE_CONFIG: dict[str, Any] = {
    "record": "routing-dev-cycle-cohort-v1",
    "namespace": "routing_dev_cycle",
    # the outcome-blind DETERMINISTIC prefix — no selection function
    "cohort": {cell: [0, 1, 2, 3, 4] for cell in CYCLE_CELLS},
    "renderers": list(RENDERER_IDS),
    "visibility": "private",
    "natural_mixture": {
        "cells": "equal",
        "latent_clusters_within_cell": "equal",
        "renderers_within_latent": "equal",
        "definition": "the frozen 211_f natural-mixture definition "
                      "(charter.natural_mixture_weights); unchanged "
                      "across all within-cycle comparisons",
    },
    "evaluation": {
        "domain": "cycle_eval",
        "base_seed": 20260805,
        "seed_rule": ("int(sha256(domain || base_seed || "
                      "observation_id || completion_slot), 16) mod "
                      "2^31 over the COMPLETE digest; slots 0..7 "
                      "only; NO checkpoint index (common random "
                      "numbers ACROSS THE TWO CYCLE CHECKPOINTS, "
                      "330_f §1)"),
        "sampling": {"do_sample": True, "temperature": 1.0,
                     "top_p": 1.0, "top_k": None,
                     "repetition_penalty": 1.0,
                     "max_new_tokens": 128, "group_size": 8},
        "runtime_profile_sha256": P0_RUNTIME_PROFILE_SHA256,
        "batching": ("canonical (cell, latent index, renderer) "
                     "order; one 8-completion group per observation "
                     "per evaluated checkpoint"),
        "framing": ("paired latent-level DESCRIPTIVE evidence "
                    "(5 clusters per cell) — never completion-level "
                    "precision claims"),
    },
    "checkpoint_rule": {
        "rule_id": "r-cycle-eval-v1",
        "evaluate": ["checkpoint_zero", "final_checkpoint"],
        "selection": ("FIXED and outcome-blind — never best-of; "
                      "exactly two checkpoints, one reveal"),
        "final_definition": ("P0 CLOSES this development cycle: "
                             "cycle synthesis follows P0 directly; "
                             "no continuation or fork precedes it"),
        "terminally_closed_abort": (
            "after a TERMINALLY CLOSED abort (a closed-out "
            "infrastructure-abort closeout, never a resumable "
            "interruption), the last COMPLETE checkpoint stands in "
            "for the final checkpoint, disclosed as such"),
        "no_positive_checkpoint": (
            "if no positive-index checkpoint exists, the "
            "zero-vs-final comparison is UNDEFINED and recorded as "
            "such — checkpoint zero is never evaluated twice"),
        "one_reveal": ("surfaces are materialized only AT cycle "
                       "synthesis (a cycle_closure ledger launch "
                       "inside the final R_cycle), evaluated once, "
                       "archived, and the population permanently "
                       "retired"),
    },
    "partial_reveal_rule": (
        "if cycle-surface materialization partially reveals "
        "outcomes, only an EXACT design-preserving resume/retry is "
        "permitted; otherwise the cohort is retired and cycle "
        "evaluation is reported UNAVAILABLE — never re-selected "
        "(330_f §5)"),
    "materialization_plan": {
        "ledger_kind": "cycle_closure",
        "budget_source": "the final R_cycle reserve",
        "machinery": ("the frozen §4 machinery (dev declaration → "
                      "materialize_dev_support → surface lock), "
                      "validated against THIS record's cohort and "
                      "execution identities"),
    },
    "never_trained_on": (
        "structural — the P0 trainer consumes only the pinned "
        "mixture schedule (record_sha256 135a72bf4deb77048371074636"
        "d88ffebf6bd07d1c00ae349b6fcee221975b3f); routing_dev_cycle "
        "appears in no training schedule"),
    "development_only": True,
    "lineage": {
        "parent_entry_sha256":
            "929e172415845471f2fe613ef71a36eb57d47492cfa58c4e511e9"
            "5403a5ed11c",
        "outcome_informed": False,
        "motivating_evidence": ("330_f-signed precursors plan Unit "
                                "Y; 342_f Unit-V closure"),
    },
}
CYCLE_CONFIG_SHA256 = \
    "2b404642a06c0441246d5d634889d34e4fede99f48dcfb92bba9e65559d125d6"

# the frozen 720-entry cycle seed schedule (90 obs x slots 0..7)
CYCLE_SEED_SCHEDULE_SHA256 = \
    "89076715ba7bef4d2a8077a75961f6aa4c6785ace98a8a1f48e736b8b26c16c7"

# the externally reviewed record pins (set at the one-time freezes;
# recorded by the Unit-Y review)
CYCLE_RECORD_SHA256 = \
    "c1caf158cbac0ec8e1daf75a3b9330df1a1304d814053c036871ee7b9f76bb8f"
R_CYCLE_RECORD_SHA256 = \
    "dd924326eb15695c417941009bcb0b31af9aeefabd7431687c3c3563ea5209a8"


def _validated_config() -> dict[str, Any]:
    if content_sha256(CYCLE_CONFIG) != CYCLE_CONFIG_SHA256:
        raise InfrastructureError(
            "CYCLE_CONFIG was mutated after import")
    return CYCLE_CONFIG


# --- Y1: the cohort + record ---------------------------------------------------

def cycle_cohort_observations() -> list[dict[str, Any]]:
    """The cycle cohort regenerated from the frozen generator in
    canonical (cell, index, renderer) order — 90 observations."""
    config = _validated_config()
    return dev_support.dev_cohort_observations(
        config["namespace"], config["cohort"], config["renderers"],
        config["visibility"])


def cycle_seed_for_completion(observation_id: str,
                              completion_slot: int) -> int:
    """The cycle CRN seeds — the SAME frozen derivation, the cycle
    domain and base seed (identical draws at BOTH evaluated
    checkpoints)."""
    config = _validated_config()
    return seed_for_completion(
        observation_id, completion_slot,
        domain=config["evaluation"]["domain"],
        base_seed=config["evaluation"]["base_seed"])


def cycle_seed_schedule() -> list[tuple[str, int, int]]:
    config = _validated_config()
    group_size = config["evaluation"]["sampling"]["group_size"]
    schedule = [
        (obs["observation_id"], slot,
         cycle_seed_for_completion(obs["observation_id"], slot))
        for obs in cycle_cohort_observations()
        for slot in range(group_size)]
    digest = content_sha256([list(entry) for entry in schedule])
    if digest != CYCLE_SEED_SCHEDULE_SHA256:
        raise InfrastructureError(
            "the derived cycle seed schedule does not match the "
            "frozen schedule pin")
    return schedule


def _canonical_weights(observations: list[Mapping[str, Any]]
                       ) -> list[list[Any]]:
    from .charter import natural_mixture_weights
    weights = natural_mixture_weights(list(observations))
    return [[obs["observation_id"],
             weights[obs["observation_id"]]]
            for obs in observations]


_EXECUTION_IDENTITY_FIELDS = (
    "worker_visible_fingerprint", "runtime_profile_fingerprint",
    "worker_pool_fingerprint", "request_contract", "cache_identity")


def _val_execution_identities() -> dict[str, str]:
    """The worker/prompt/request identities the cycle surface will
    be materialized against — read from the AUTHENTICATED Unit-V
    evidence (the validated val-launch manifest binds the
    declaration that carries them; the same frozen pool)."""
    evidence = Path(VAL_EVIDENCE_DIR)
    declaration = json.loads(
        (evidence / "prelaunch" / "declaration.json")
        .read_text("utf-8"))
    manifest = validate_val_launch_manifest(
        json.loads((evidence / "prelaunch" / "val_launch.json")
                   .read_text("utf-8")),
        declaration, recompute=False)
    return {field: manifest[field]
            for field in _EXECUTION_IDENTITY_FIELDS}


def _val_lock_overlap() -> dict[str, Any]:
    """The Unit-V lock's bound three-way overlap result — the
    cycle record RE-ASSERTS the frozen numbers (never re-measures);
    the lock bytes authenticate under the externally reviewed
    pin."""
    payload = json.loads(
        (Path(VAL_EVIDENCE_DIR) / "val_lock.json")
        .read_text("utf-8"))
    body = {k: v for k, v in payload.items()
            if k != "record_sha256"}
    if content_sha256(body) != payload.get("record_sha256") \
            or payload["record_sha256"] != VAL_LOCK_SHA256:
        raise InfrastructureError(
            "the archived val lock does not authenticate under the "
            "reviewed pin")
    return {key: dict(payload["overlap_report"][key])
            for key in ("val_vs_cycle", "cycle_vs_training")}


def build_cycle_record() -> dict[str, Any]:
    """The Y1 record, built from the authoritative in-code sources
    and the authenticated Unit-V evidence — no hand
    transcription."""
    config = _validated_config()
    observations = cycle_cohort_observations()
    cycle_seed_schedule()  # enforces the schedule pin
    record = {
        "kind": config["record"],
        "cycle_config_sha256": CYCLE_CONFIG_SHA256,
        "namespace": config["namespace"],
        "cohort": config["cohort"],
        "renderers": config["renderers"],
        "visibility": config["visibility"],
        "natural_mixture": config["natural_mixture"],
        "natural_mixture_weights": _canonical_weights(observations),
        "evaluation": config["evaluation"],
        "seed_schedule_sha256": CYCLE_SEED_SCHEDULE_SHA256,
        "checkpoint_rule": config["checkpoint_rule"],
        "partial_reveal_rule": config["partial_reveal_rule"],
        "materialization_plan": config["materialization_plan"],
        "ordered_observation_ids": [obs["observation_id"]
                                    for obs in observations],
        "execution_identities": _val_execution_identities(),
        "overlap_reassertion": _val_lock_overlap(),
        "val_lock_sha256": VAL_LOCK_SHA256,
        "never_trained_on": config["never_trained_on"],
        "development_only": True,
        "lineage": config["lineage"],
    }
    record["record_sha256"] = content_sha256(record)
    return record


def freeze_cycle_record(out_path: str | Path = CYCLE_RECORD_PATH
                        ) -> dict[str, Any]:
    out_path = Path(out_path)
    if out_path.exists():
        raise InfrastructureError(
            f"{out_path} exists; the cycle record is frozen "
            "exactly once")
    record = build_cycle_record()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    return record


def load_cycle_record(path: str | Path = CYCLE_RECORD_PATH,
                      expected_sha256: str | None = None
                      ) -> dict[str, Any]:
    """The strict consuming loader: the externally reviewed hash;
    the record must REDERIVE from the frozen config and the
    authenticated Unit-V evidence (a rehashed record carrying a
    different seed, rule, or identity refuses here)."""
    expected = expected_sha256 or CYCLE_RECORD_SHA256
    payload = json.loads(Path(path).read_text("utf-8"))
    body = {k: v for k, v in payload.items()
            if k != "record_sha256"}
    if content_sha256(body) != payload.get("record_sha256") \
            or payload["record_sha256"] != expected:
        raise InfrastructureError(
            "cycle record does not rehash to the externally "
            "reviewed value")
    rederived = build_cycle_record()
    if payload != rederived:
        differing = sorted(
            k for k in set(payload) | set(rederived)
            if payload.get(k) != rederived.get(k))
        raise InfrastructureError(
            f"cycle record does not rederive from the frozen "
            f"sources; differing fields: {differing}")
    return payload


# --- Y2: the final R_cycle reserve ---------------------------------------------

# the registered basis (231_f, retained): the Step-4 support
# closeout the provisional reserve bound
SUPPORT_CLOSEOUT_SHA256 = \
    "6506f117180c9b2a2fafbd745ca9b19082b18e2c63d49a71e0a2dbce4da4c283"
SUPPORT_SURFACE_LOCK_SHA256 = \
    "61c4e85a53683c9e2dbcbf15f60794935a76a86d979a69412a97f44ea9f2562b"

R_CYCLE_FINAL_GPU_HOURS = 1.0

_ITEMIZED_CLOSURE = (
    ("cycle_surface_materialization", 0.0637,
     "the MEASURED Unit-V cost for the identical 90-observation "
     "shape (closeout 929e1724…, 342_f) — the direct calibrator"),
    ("two_checkpoint_inference", 0.2325,
     "2 checkpoints × 90 evaluation groups × 4.65 s/group (the "
     "C2-measured generation rate, 299_f)"),
    ("verification_traces_archival", 0.05,
     "conservative margin: terminal verification (~minutes CPU), "
     "trace flush, deterministic-gzip archival (the Unit-V "
     "closure measured well under this)"),
)


def build_r_cycle_reserve_record() -> dict[str, Any]:
    """The Y2 record: BOTH derivations persisted; the final
    reserve is their rounded maximum (330_f §3); the complete
    closure obligation set must fit under it."""
    from .ledger import LEDGER_PATH, ledger_head, verify_ledger_head
    entries = verify_ledger_head(ledger_head(), LEDGER_PATH)
    closeouts = [e for e in entries
                 if e["entry_sha256"] == SUPPORT_CLOSEOUT_SHA256]
    if len(closeouts) != 1 or closeouts[0].get(
            "terminal_status") != "complete":
        raise InfrastructureError(
            "the registered support closeout is not in the "
            "verified chain")
    support = closeouts[0]
    rendered = support["freeze"]["rendered_observations"]
    consumed = support["budget_consumed_gpu_hours"]
    seconds = consumed * 3600.0 / rendered
    cohort_size = len(load_cycle_record()["ordered_observation_ids"])
    implied = cohort_size * 2.0 * seconds / 3600.0
    basis_ceiling = float(math.ceil(implied))
    itemized_total = round(sum(hours for _, hours, _
                               in _ITEMIZED_CLOSURE), 4)
    itemized_ceiling = float(math.ceil(itemized_total))
    reserve = max(basis_ceiling, itemized_ceiling)
    if reserve != R_CYCLE_FINAL_GPU_HOURS:
        raise InfrastructureError(
            f"the derived final reserve {reserve} != the frozen "
            f"{R_CYCLE_FINAL_GPU_HOURS}")
    if itemized_total > reserve:
        raise InfrastructureError(
            "the itemized closure obligations exceed the reserve")
    record = {
        "kind": "routing-dev-r-cycle-final-v1",
        "cycle_record_sha256":
            load_cycle_record()["record_sha256"],
        "r_cycle_gpu_hours": reserve,
        "registered_basis": {
            "support_closeout_sha256": SUPPORT_CLOSEOUT_SHA256,
            "measured_support_gpu_hours": consumed,
            "rendered_observations": rendered,
            "measured_seconds_per_observation": seconds,
            "assumed_cohort_size": cohort_size,
            "evaluation_multiplier": 2.0,
            "implied_hours": round(implied, 6),
            "ceiling_gpu_hours": basis_ceiling,
            "rounding": "ceil_to_whole_gpu_hours",
        },
        "itemized_closure_ceiling": {
            "items": [{"obligation": name, "gpu_hours": hours,
                       "source": source}
                      for name, hours, source in _ITEMIZED_CLOSURE],
            "total_gpu_hours": itemized_total,
            "ceiling_gpu_hours": itemized_ceiling,
        },
        "rule": ("R_cycle_final = max(registered basis ceiling, "
                 "itemized closure ceiling) — both derivations "
                 "persisted (330_f §3); the coincidence of equal "
                 "roundings is exposed, not concealed (329_s)"),
        "replaces": ("the provisional 5.0 GPU-h reserve "
                     "(264066e6…, 231_f)"),
        "development_only": True,
    }
    record["record_sha256"] = content_sha256(record)
    return record


def freeze_r_cycle_reserve_record(
        out_path: str | Path = R_CYCLE_RECORD_PATH
        ) -> dict[str, Any]:
    out_path = Path(out_path)
    if out_path.exists():
        raise InfrastructureError(
            f"{out_path} exists; the reserve record is frozen "
            "exactly once")
    record = build_r_cycle_reserve_record()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    return record


def load_r_cycle_reserve_record(
        path: str | Path = R_CYCLE_RECORD_PATH,
        expected_sha256: str | None = None) -> dict[str, Any]:
    expected = expected_sha256 or R_CYCLE_RECORD_SHA256
    payload = json.loads(Path(path).read_text("utf-8"))
    body = {k: v for k, v in payload.items()
            if k != "record_sha256"}
    if content_sha256(body) != payload.get("record_sha256") \
            or payload["record_sha256"] != expected:
        raise InfrastructureError(
            "R_cycle reserve record does not rehash to the "
            "externally reviewed value")
    if payload != build_r_cycle_reserve_record():
        raise InfrastructureError(
            "R_cycle reserve record does not rederive from the "
            "frozen sources")
    return payload


def record_final_r_cycle(*, expected_head_sha256: str,
                         ledger_path: str | Path | None = None
                         ) -> dict[str, Any]:
    """THE final-reserve append boundary (executed only AFTER the
    Unit-Y sign-off): validates the committed cycle and reserve
    records under their reviewed pins, then appends the
    `status: final` reserve_update — replacing the provisional
    5.0 — through the ledger's validator-gated final path."""
    from .ledger import LEDGER_PATH, _append
    ledger_path = ledger_path or LEDGER_PATH
    cycle = load_cycle_record()
    reserve = load_r_cycle_reserve_record()
    if reserve["cycle_record_sha256"] != cycle["record_sha256"]:
        raise InfrastructureError(
            "the reserve record does not bind the committed cycle "
            "record")
    basis = reserve["registered_basis"]
    entry = {
        "kind": "reserve_update",
        "question": ("Unit Y: the FINAL R_cycle reserve — the "
                     "cycle cohort and its evaluation rule are "
                     "frozen; the reserve becomes the rounded "
                     "maximum of the registered basis and the "
                     "itemized closure ceiling"),
        "motivating_evidence": ("330_f-signed plan Unit Y; the "
                                "committed cycle and reserve "
                                "records"),
        "freeze": {
            "support_closeout_sha256":
                basis["support_closeout_sha256"],
            "surface_lock_sha256": SUPPORT_SURFACE_LOCK_SHA256,
            "cycle_record_sha256": cycle["record_sha256"],
            "r_cycle_record_sha256": reserve["record_sha256"],
            "r_cycle_record_file_sha256":
                _sha_file(Path(R_CYCLE_RECORD_PATH)),
        },
        "parent": expected_head_sha256,
        "budget_allocated_gpu_hours": 0.0,
        "outcome_informed": False,
        "reserve": {
            "status": "final",
            "r_cycle_gpu_hours": reserve["r_cycle_gpu_hours"],
            "assumed_cohort_size":
                basis["assumed_cohort_size"],
            "evaluation_multiplier":
                basis["evaluation_multiplier"],
            "measured_seconds_per_observation":
                basis["measured_seconds_per_observation"],
            "measured_support_gpu_hours":
                basis["measured_support_gpu_hours"],
            "itemized_ceiling_gpu_hours":
                reserve["itemized_closure_ceiling"][
                    "ceiling_gpu_hours"],
            "rounding": "ceil_to_whole_gpu_hours",
        },
    }
    return _append(entry, expected_head_sha256, ledger_path)
