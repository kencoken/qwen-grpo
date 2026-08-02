"""Unit B2 — the P0 training mixture, VERSION 2 (290_f signed plan;
288_s constraints).

A VERSIONED path (288_s §1): the V1 modules (`p0_mixture`,
`unit_c_sample`) are retained UNCHANGED so the committed C1 archive
keeps verifying through its own code; `reverify_c1_archive` is the
HARD GATE run at the B2 freeze, immediately before the C2 launch,
and after the C2 implementation.

Changes vs V1 (the 283_s route as amended by 288_s/290_f):

- scope: direct Q1 = code_atomic / fork_join / math_code;
  `math_atomic` is a TRAINING-EXPOSED SENTINEL — zero Bridge quota,
  retained via its Anchor rows, mechanically excluded from the
  direct-Q1 gate, the sizing minimum, authorization, and headline
  aggregates (its estimand is the executable `sentinel_block`);
- Bridge reallocation: code_atomic 2 latents (6 rows), fork_join 13
  (39), math_code 13 (39) — canonical ascending selection,
  independent of C1 rollout outcomes within the already
  payoff-surface-informed eligible pools;
- the C1 rates are BOUND to the exact C1 evidence hashes and
  REDERIVED from the archive; they enter as disclosed,
  outcome-informed design HEURISTICS. The V1
  prospective-probability refusal is EXPLICITLY SUPERSEDED (C1
  demonstrated homogeneous per-cell transport unreliable); fresh C2
  is the empirical exposure gate;
- sizing population amended: cells = the three direct-Q1 cells,
  authenticated C2 measured rates, target 100/cell, sentinel
  excluded from the minimum; integer arithmetic and the
  finalization-aware cap formula unchanged in form.

Q2 composites, goal_first controls, the direct-specialist control,
and Anchor are UNCHANGED from the frozen V1 candidate."""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tasks.conductor.types import RENDERER_IDS, InfrastructureError

from .charter import content_sha256
from .p0_mixture import (
    _fc_fraction,
    bridge_eligible,
)

DIRECT_Q1_CELLS = ("code_atomic", "fork_join", "math_code")
SENTINEL_CELL = "math_atomic"
LOOKUP_CELLS = ("lookup_atomic", "lookup_math")

MIXTURE_V2_CONFIG: dict[str, Any] = {
    "tranche": "routing-dev-p0-mixture-v2",
    "objectives": ("q1_family_routing_direct",
                   "q2_hierarchical_unlocking",
                   "math_atomic_training_exposed_sentinel"),
    # the same frozen inputs as V1
    "extension_surface_lock_sha256":
        "ccb1c3e2db2422a82919292144c0bdecc21d2cc89cb7a3a2c69bec17a2ce6d1b",
    "selection_record_sha256":
        "c6c087757eb4673c42ad37121f9037ca57ce9488e65c4d339d78b37d07fbee34",
    "selection_evidence_path":
        "plans/conductor/evidence/support_extension_v1/selection.json",
    "selection_file_sha256":
        "e0bbb75d61aa0405c86a9a69a0e68957d5db995a389d1b34f353fe1dce546724",
    # 288_s §2: the C1 rates are heuristics BOUND to the exact C1
    # evidence; rederived from the archive, never called validated
    "c1_evidence": {
        "exposure_report_path":
            "plans/conductor/evidence/unit_c_v1/exposure_report.json",
        "exposure_report_file_sha256":
            "3e708f673f4d732c2bcf885c266aac44d7731f74f61b5173d4b0f0ba056ea449",
        "sample_record_file_sha256":
            "7f52e420869a369b8d9c24801d3cfac018766a7014d29ae8673c42aeefdd44f7",
        "closeout_entry_sha256":
            "9f4661a84e601299951f17370eb22d9aa52f970a717b80844684240c8c550996",
    },
    "c1_rate_heuristics": {"code_atomic": [32, 60],
                           "fork_join": [3, 60],
                           "math_code": [7, 150]},
    # 288_s §2 / 290_f §4: the V1 prospective-probability refusal is
    # EXPLICITLY SUPERSEDED — C1 demonstrated homogeneous per-cell
    # transport unreliable (and fork_join renderer-heterogeneous);
    # heuristic projections are DISCLOSED, never gated on; fresh C2
    # is the empirical exposure gate (>=2 counted from >=2 latents
    # per direct-Q1 cell, unchanged in strength).
    "prospective_probability_refusal": {
        "superseded": True,
        "replaced_by": "fresh C2 as the empirical exposure gate",
    },
    "quotas": {
        # UNCHANGED from V1
        "q2_w3_math_code": {"observations": 7, "multiplicity": 2},
        "q2_w2_fork_join": {"bound_var": 4, "goal_first": 14},
        "direct_specialist_control_code_atomic":
            {"observations": 5, "multiplicity": 1},
        "goal_first_controls_per_code_cell": 6,
        "anchor_latents": [0],
        # 283_s reallocation: sentinel gets ZERO bridge quota
        "bridge_latents": {"code_atomic": 2, "fork_join": 13,
                           "math_code": 13, "math_atomic": 0},
    },
    "constraints": {
        "max_direction_row_ratio": 1.5,
        "max_p_w3_given_goal_first": 0.5,
        "min_q2_rows_per_direction": 12,
    },
    # the C2 empirical gate (unchanged in strength; direct-Q1 only)
    "q1_gate_criterion": {
        "cells": list(DIRECT_Q1_CELLS),
        "min_counted_groups_per_cell": 2,
        "min_distinct_latents_among_counted": 2,
    },
    "q2_cold_start_gate": {
        "per_direction": {
            "math_code|w3_favoured": {"target_worker": 3},
            "fork_join|w2_favoured": {"target_worker": 2},
        },
        "min_target_selections": 8,
        "min_distinct_latents": 2,
    },
    # 288_s §3: the amended sizing population — sentinel EXCLUDED
    "p0_sizing_rule": {
        "sizing_cells": list(DIRECT_Q1_CELLS),
        "target_q1_counted_groups_per_sizing_cell": 100,
        "derivation": ("derived_epochs = ceil(target * c2_epochs / "
                       "min over SIZING cells of authenticated C2 "
                       "counted groups); derived_groups = "
                       "derived_epochs * 157"),
        "groups_per_epoch": 157,
        "operational_ceiling_hours": 10.0,
        "cap_formula": {
            "available_generation_seconds": (
                "operational_ceiling_seconds - "
                "cumulative_consumed_seconds - "
                "measured_finalization_reserve_seconds - "
                "frozen_non_rollout_overhead_seconds"),
            "capped_epochs": ("floor(available_generation_seconds / "
                              "measured_whole_epoch_seconds)"),
            "if_capped_epochs_leq_zero":
                "stop for a reviewed scope amendment",
            "capped_semantics": (
                "explicitly UNDER-TARGET: claims are based on "
                "achieved projected/observed exposure (capped_epochs "
                "x measured rate, DISCLOSED), never the nominal "
                "100-group target; per 290_f the capped branch is "
                "EXPECTED, not merely possible"),
            "inputs_from_smokes": [
                "measured_whole_epoch_seconds",
                "measured_finalization_reserve_seconds"],
        },
    },
    # 292_s B2: the frozen outcome contract (was prose-only)
    "outcome_contract": {
        "q1_population": "bridge-class draws only",
        "q1_counted_event": ("a reward-1.0 FULLY family-correct "
                             "completion AND a reward-0.5 completion "
                             "of STRICTLY LOWER family correctness "
                             "in the same group"),
        "q2_population": ("q2_composite rows only; the "
                          "direct_specialist_control class is "
                          "excluded from every Q2 statistic and "
                          "gate"),
        "decision_matrix": {
            "q1_fail": "stop-and-review (no P0 launch)",
            "q1_pass_q2_pass":
                "Q1 + Q2 hierarchical-unlocking authorized",
            "q1_pass_q2_fail": ("maximum permissible scope Q1-only; "
                                "the P0 freeze decides whether "
                                "launch remains worthwhile"),
            "infrastructure_abort": (
                "no scientific outcome; the repair/relaunch "
                "protocol applies; does NOT consume the "
                "no-third-scientific-iteration branch"),
        },
    },
    "screened_latents": {"fork_join": [42]},
    "shuffle_seed": 20260802,
    "lineage": {
        "parent_entry_sha256":
            "9f4661a84e601299951f17370eb22d9aa52f970a717b80844684240c8c550996",
        "outcome_informed": True,
        "motivating_evidence": "283_s route; 288_s constraints; "
                               "290_f signed plan (approved)",
    },
}
CONFIG_V2_SHA256 = content_sha256(MIXTURE_V2_CONFIG)
# 292_s B3: the FROZEN schedule identity — a later builder edit
# producing a new self-consistent schedule cannot ride under the
# unchanged config hash; set after the reviewed build, enforced in
# build_mixture_v2 AND verify_mixture_v2.
EXPECTED_MIXTURE_V2_RECORD_SHA256 = \
    "135a72bf4deb77048371074636d88ffebf6bd07d1c00ae349b6fcee221975b3f"
EXPECTED_EPOCH_ROWS = 157


_C1_BASIS_CACHE: dict[str, dict[str, list[int]]] = {}


def verify_c1_basis() -> dict[str, list[int]]:
    """292_s B1: THE authoritative C1-basis verifier — the single
    path to the heuristic rates. Verifies the ledger chain at the
    exact frozen head; confirms the C1 closeout binds the expected
    report and sample-record bytes and a non-empty terminal
    inventory; runs the untouched V1 archive verifier; only then
    derives the rates. Memoized per process (the archive
    verification is not free); invoked at the B2 freeze boundary
    and again in C2 preflight."""
    config = MIXTURE_V2_CONFIG["c1_evidence"]
    head = config["closeout_entry_sha256"]
    if head in _C1_BASIS_CACHE:
        return _C1_BASIS_CACHE[head]
    from .ledger import verify_ledger_head
    entries = verify_ledger_head(head)
    closeout = entries[-1]
    if closeout.get("entry_sha256") != head \
            or closeout.get("terminal_status") != "complete":
        raise InfrastructureError(
            "the frozen C1 closeout is not the verified ledger head")
    freeze = closeout.get("freeze", {})
    if freeze.get("exposure_report_file_sha256") != \
            config["exposure_report_file_sha256"] \
            or freeze.get("sample_record_file_sha256") != \
            config["sample_record_file_sha256"]:
        raise InfrastructureError(
            "the C1 closeout does not bind the frozen report/sample "
            "bytes (292_s B1)")
    if not freeze.get("terminal_artifact_hashes"):
        raise InfrastructureError(
            "the C1 closeout carries no terminal inventory")
    raw = Path(config["exposure_report_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != \
            config["exposure_report_file_sha256"]:
        raise InfrastructureError(
            "C1 exposure report bytes are not the closeout-bound ones")
    record_path = Path(config["exposure_report_path"]).parent \
        / "sample_record.json"
    if hashlib.sha256(record_path.read_bytes()).hexdigest() != \
            config["sample_record_file_sha256"]:
        raise InfrastructureError(
            "C1 sample-record bytes are not the closeout-bound ones "
            "(292_s B1)")
    if reverify_c1_archive()["verdict"] != "PASS":
        raise InfrastructureError("the C1 archive did not reverify")
    report = json.loads(raw.decode("utf-8"))
    rates = {cell: [report["q1_gate"][cell]["counted_groups"],
                    report["q1_gate"][cell]["bridge_draws"]]
             for cell in DIRECT_Q1_CELLS}
    if rates != MIXTURE_V2_CONFIG["c1_rate_heuristics"]:
        raise InfrastructureError(
            "frozen C1 rate heuristics do not rederive from the "
            "bound archive")
    _C1_BASIS_CACHE[head] = rates
    return rates


def decide_c2_outcome(*, q1_pass: bool, q2_pass: bool,
                      infrastructure_abort: bool = False) -> str:
    """292_s B2: the pure decision function over the frozen matrix."""
    matrix = MIXTURE_V2_CONFIG["outcome_contract"]["decision_matrix"]
    if infrastructure_abort:
        return matrix["infrastructure_abort"]
    if not q1_pass:
        return matrix["q1_fail"]
    if q2_pass:
        return matrix["q1_pass_q2_pass"]
    return matrix["q1_pass_q2_fail"]


def tranche_freeze() -> dict[str, Any]:
    if content_sha256(MIXTURE_V2_CONFIG) != CONFIG_V2_SHA256:
        raise InfrastructureError(
            "MIXTURE_V2_CONFIG was mutated after import")
    # 292_s B1: the freeze boundary RUNS the C1-basis gate — a
    # successful freeze proves the gate ran
    verify_c1_basis()
    body = {
        "kind": "p0_mixture_v2",
        "question": ("Unit B2: the ONE fixed P0 schedule under the "
                     "amended scope — does the reallocated mixture "
                     "deliver Q1 reward-varying exposure in the three "
                     "direct-Q1 cells (C2, the empirical gate) while "
                     "the math_atomic sentinel stays observable?"),
        "motivation": "290_f signed plan; 283_s route; 288_s "
                      "constraints",
        "config": MIXTURE_V2_CONFIG,
        "budget_gpu_hours": 0.0,
    }
    return {**body, "freeze_sha256": content_sha256(body)}


# --- the C1 hard gate (288_s §1) ------------------------------------------------

def reverify_c1_archive() -> dict[str, Any]:
    """The HARD GATE: the committed C1 archive must verify through
    the UNTOUCHED V1 path with its real frozen identities. Run at
    the B2 freeze, immediately before the C2 launch, and after the
    C2 implementation. If the canonical extension surface is absent
    (clean clone), it is reconstructed from the committed evidence
    via the production restore path first."""
    from . import unit_c_sample
    from .dev_support import load_dev_surface
    surface_dir = Path(
        unit_c_sample.UNIT_C_CONFIG["extension_surface_dir"])
    if not (surface_dir / "surface_lock.json").exists():
        from .support_run import restore_surface_evidence
        restore_surface_evidence(
            "plans/conductor/evidence/support_extension_v1/surface",
            surface_dir)
    # the restore (or the live root) must load under the frozen lock
    load_dev_surface(surface_dir, expected_lock_sha256=unit_c_sample
                     .UNIT_C_CONFIG["extension_surface_lock_sha256"])
    return unit_c_sample.verify_unit_c_run(
        "plans/conductor/evidence/unit_c_v1",
        "6fa701a29cbb7ae3de53d9f0ba8c22bdf8989fda6efa833febcade3a608daac8",
        "372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42")


# --- frozen inputs -------------------------------------------------------------

def validate_frozen_selection_v2(record: Mapping[str, Any]) -> None:
    if not isinstance(record, Mapping) or record.get(
            "record_sha256") != MIXTURE_V2_CONFIG[
            "selection_record_sha256"]:
        raise InfrastructureError(
            "selection record is not the frozen Unit-A selection")
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record["record_sha256"]:
        raise InfrastructureError("selection record does not rehash")


def load_frozen_selection_v2() -> dict[str, Any]:
    config = MIXTURE_V2_CONFIG
    raw = Path(config["selection_evidence_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != \
            config["selection_file_sha256"]:
        raise InfrastructureError(
            "selection evidence bytes are not the frozen ones")
    record = json.loads(raw.decode("utf-8"))
    validate_frozen_selection_v2(record)
    return record


def c1_rates_rederived() -> dict[str, list[int]]:
    """288_s §2 / 292_s B1: the ONLY rate path is the authoritative
    C1-basis verifier (ledger head + closeout bindings + V1 archive
    verification + rate equality)."""
    return verify_c1_basis()


# --- the B2 mixture builder ----------------------------------------------------

def build_mixture_v2(loaded: Mapping[str, Any],
                     selection: Mapping[str, Any]) -> dict[str, Any]:
    """The ONE fixed B2 per-epoch schedule. Identical class structure
    to the frozen V1 candidate except the Bridge reallocation and
    the sentinel declaration; the prospective-probability refusal is
    superseded (heuristic projections DISCLOSED, never gated)."""
    config = MIXTURE_V2_CONFIG
    if content_sha256(config) != CONFIG_V2_SHA256:
        raise InfrastructureError(
            "MIXTURE_V2_CONFIG was mutated after import")
    quotas = config["quotas"]
    lock = loaded.get("lock", {})
    if lock.get("lock_sha256") != \
            config["extension_surface_lock_sha256"]:
        raise InfrastructureError(
            "mixture must build on the frozen extension lock")
    validate_frozen_selection_v2(selection)
    if selection.get("extension_surface_lock_sha256") != \
            lock["lock_sha256"]:
        raise InfrastructureError(
            "selection record is not bound to this surface")
    disclosure = selection["public_factor_disclosure"]
    surface = loaded["surface"]
    per_obs: dict[str, dict[tuple[int, ...], float]] = {}
    for (oid, assignment), payoff in surface.items():
        per_obs.setdefault(oid, {})[assignment] = payoff
    meta = {obs["observation_id"]: obs
            for obs in loaded["observations"]}
    if set(disclosure) != set(meta):
        raise InfrastructureError(
            "selection disclosure does not cover the locked surface")

    screened_latents = {(cell, index)
                        for cell, indices in
                        config["screened_latents"].items()
                        for index in indices}

    def is_screened(oid: str) -> bool:
        row = disclosure[oid]
        return (row["cell_id"], row["latent_index"]) in screened_latents

    assigned: dict[str, str] = {}
    multiplicity: dict[str, int] = {}

    def take(oid: str, cls: str, mult: int) -> None:
        if oid in assigned:
            raise InfrastructureError(
                f"{oid} assigned twice ({assigned[oid]} then {cls})")
        assigned[oid] = cls
        multiplicity[oid] = mult

    owned: dict[str, list[str]] = {}
    for source in ("direction_buckets", "screened_surplus"):
        for bucket, members in selection[source].items():
            for member in members:
                owned.setdefault(bucket, []).extend(
                    member["observation_ids"])

    # 1. Q2 composite (UNCHANGED from V1)
    mc_pool = [oid for oid in sorted(
        owned.get("math_code|w3_favoured", []))
        if not is_screened(oid)]
    if len(mc_pool) != quotas["q2_w3_math_code"]["observations"]:
        raise InfrastructureError(
            f"math_code w3 pool {len(mc_pool)} != the frozen quota")
    for oid in mc_pool:
        take(oid, "q2_composite",
             quotas["q2_w3_math_code"]["multiplicity"])
    fj_pool = [oid for oid in owned.get("fork_join|w2_favoured", [])
               if not is_screened(oid)]
    for renderer, want in quotas["q2_w2_fork_join"].items():
        stratum = sorted(
            (oid for oid in fj_pool
             if disclosure[oid]["renderer_id"] == renderer),
            key=lambda o: disclosure[o]["latent_index"])
        if len(stratum) < want:
            raise InfrastructureError(
                f"fork_join w2 {renderer} pool cannot fill {want}")
        for oid in stratum[:want]:
            take(oid, "q2_composite", 1)

    # 2. direct-specialist control (UNCHANGED)
    ca_pool = [oid for oid in sorted(
        owned.get("code_atomic|w3_favoured", []))
        if not is_screened(oid)]
    ca_quota = quotas["direct_specialist_control_code_atomic"]
    if len(ca_pool) != ca_quota["observations"]:
        raise InfrastructureError(
            f"code_atomic w3 pool {len(ca_pool)} != the frozen quota")
    for oid in ca_pool:
        take(oid, "direct_specialist_control", ca_quota["multiplicity"])

    # 3. Anchor (UNCHANGED — the sentinel's rows live here)
    for oid in sorted(meta):
        row = disclosure[oid]
        if row["latent_index"] in quotas["anchor_latents"] \
                and oid not in assigned and not is_screened(oid):
            take(oid, "anchor", 1)

    # 4. goal_first controls (UNCHANGED)
    per_cell_controls = quotas["goal_first_controls_per_code_cell"]
    for cell in ("code_atomic", "fork_join", "math_code"):
        pool = sorted(
            (oid for oid, row in disclosure.items()
             if row["cell_id"] == cell
             and row["renderer_id"] == "goal_first"
             and row["direction"] == "tied"
             and oid not in assigned and not is_screened(oid)),
            key=lambda o: disclosure[o]["latent_index"])
        if len(pool) < per_cell_controls:
            raise InfrastructureError(
                f"{cell}: goal_first control pool cannot fill "
                f"{per_cell_controls}")
        for oid in pool[:per_cell_controls]:
            take(oid, "goal_first_control", 1)

    # 5. Bridge — the 283_s reallocation; canonical ascending
    # selection, independent of C1 rollout outcomes within the
    # already payoff-surface-informed eligible pools
    for cell, n_latents in quotas["bridge_latents"].items():
        if cell in LOOKUP_CELLS:
            raise InfrastructureError(
                "lookup cells carry ZERO bridge quota")
        if n_latents == 0:
            continue   # the sentinel: zero Bridge quota
        by_latent: dict[int, list[str]] = {}
        for oid, row in disclosure.items():
            if row["cell_id"] == cell:
                by_latent.setdefault(row["latent_index"], []).append(oid)
        chosen = 0
        for index in sorted(by_latent):
            if chosen >= n_latents:
                break
            oids = sorted(by_latent[index],
                          key=lambda o: RENDERER_IDS.index(
                              disclosure[o]["renderer_id"]))
            if len(oids) != len(RENDERER_IDS):
                continue
            if any(oid in assigned or is_screened(oid)
                   for oid in oids):
                continue
            if any(disclosure[oid]["direction"] not in
                   ("tied", "no_pair") for oid in oids):
                continue
            if not all(bridge_eligible(cell, per_obs[oid])
                       for oid in oids):
                continue
            for oid in oids:
                take(oid, "bridge", 1)
            chosen += 1
        if chosen < n_latents:
            raise InfrastructureError(
                f"{cell}: only {chosen} bridge latents available for "
                f"the frozen quota {n_latents}")

    screened = sorted(set(meta) - set(assigned))
    rows = []
    for oid in sorted(assigned):
        rows.extend([oid] * multiplicity[oid])
    rng = random.Random(config["shuffle_seed"])
    rng.shuffle(rows)

    # constraints (UNCHANGED from V1 rev3)
    limits = config["constraints"]
    w3_rows = sum(multiplicity[oid] for oid, cls in assigned.items()
                  if cls == "q2_composite"
                  and disclosure[oid]["direction"] == "w3_favoured")
    w2_rows = sum(multiplicity[oid] for oid, cls in assigned.items()
                  if cls == "q2_composite"
                  and disclosure[oid]["direction"] == "w2_favoured")
    if min(w2_rows, w3_rows) < limits["min_q2_rows_per_direction"]:
        raise InfrastructureError("Q2 direction exposure under minimum")
    ratio = max(w2_rows, w3_rows) / min(w2_rows, w3_rows)
    if ratio > limits["max_direction_row_ratio"]:
        raise InfrastructureError(
            f"Q2 direction row ratio {ratio:.2f} exceeds the bound")
    goal_first_rows = [oid for oid in rows
                       if disclosure[oid]["renderer_id"] == "goal_first"]
    w3_goal_first = sum(
        1 for oid in goal_first_rows
        if disclosure[oid]["direction"] == "w3_favoured")
    p_w3_gf = w3_goal_first / len(goal_first_rows) \
        if goal_first_rows else 0.0
    if p_w3_gf > limits["max_p_w3_given_goal_first"]:
        raise InfrastructureError(
            f"P(w3|goal_first) = {p_w3_gf:.3f} exceeds the bound")

    # heuristic projections (288_s §2: DISCLOSED, never gated —
    # the prospective-probability refusal is superseded)
    rates = c1_rates_rederived()
    heuristic = {}
    for cell in DIRECT_Q1_CELLS:
        bridge_rows = sum(
            multiplicity[oid] for oid, cls in assigned.items()
            if cls == "bridge" and disclosure[oid]["cell_id"] == cell)
        num, den = rates[cell]
        heuristic[cell] = {
            "bridge_rows_per_epoch": bridge_rows,
            "c1_rate_heuristic": [num, den],
            "heuristic_counted_per_epoch": round(
                bridge_rows * num / den, 2),
        }
    sentinel_rows = [oid for oid, cls in assigned.items()
                     if disclosure[oid]["cell_id"] == SENTINEL_CELL]
    record = {
        "kind": "routing-dev-p0-mixture-v2",
        "config_sha256": CONFIG_V2_SHA256,
        "extension_surface_lock_sha256": lock["lock_sha256"],
        "selection_record_sha256": selection["record_sha256"],
        "class_assignment": {oid: assigned[oid]
                             for oid in sorted(assigned)},
        "multiplicities": {oid: multiplicity[oid]
                           for oid in sorted(assigned)},
        "schedule_rows": rows,
        "screened_zero_multiplicity_count": len(screened),
        "sentinel": {
            "cell": SENTINEL_CELL,
            "training_exposed": True,
            "rows_per_epoch": len(sentinel_rows),
            "observation_ids": sorted(sentinel_rows),
            "excluded_from": ["direct_q1_gate", "sizing_minimum",
                              "authorization", "headline_q1"],
        },
        "heuristic_projections": {
            "basis": ("C1 measured rates, hash-bound and rederived; "
                      "outcome-informed design heuristics — NOT "
                      "validated projections (288_s §2); no "
                      "prospective-probability refusal (superseded)"),
            "per_cell": heuristic,
        },
        "q2_exposure_rows_per_epoch": {"w2_favoured": w2_rows,
                                       "w3_favoured": w3_rows},
        "p_w3_given_goal_first": round(p_w3_gf, 4),
    }
    record["record_sha256"] = content_sha256(record)
    if len(record["schedule_rows"]) != EXPECTED_EPOCH_ROWS:
        raise InfrastructureError(
            f"schedule has {len(record['schedule_rows'])} rows; the "
            f"frozen design needs {EXPECTED_EPOCH_ROWS} (292_s B3)")
    if record["record_sha256"] != EXPECTED_MIXTURE_V2_RECORD_SHA256:
        raise InfrastructureError(
            "the built mixture is not the FROZEN schedule identity "
            f"{EXPECTED_MIXTURE_V2_RECORD_SHA256[:16]}… (292_s B3)")
    return record


def verify_mixture_v2(loaded: Mapping[str, Any],
                      selection: Mapping[str, Any],
                      record: Mapping[str, Any]) -> None:
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record.get("record_sha256"):
        raise InfrastructureError("mixture record does not rehash")
    if record.get("record_sha256") != \
            EXPECTED_MIXTURE_V2_RECORD_SHA256:
        raise InfrastructureError(
            "record is not the frozen schedule identity (292_s B3)")
    rederived = build_mixture_v2(loaded, selection)
    if json.loads(json.dumps(rederived)) != \
            json.loads(json.dumps(dict(record))):
        raise InfrastructureError(
            "mixture does not rederive from the locked surface and "
            "frozen selection")


# --- the executable sentinel estimand (288_s §5 / 290_f §6) --------------------

def sentinel_block(trace_rows: list[Mapping[str, Any]],
                   sentinel_observation_ids: list[str],
                   updates_per_group: int = 1) -> dict[str, Any]:
    """The training-exposed-sentinel block: worker-1 events are the
    estimand ([2]/[3] is different but is not Math unlocking). ONE
    definition, consumed by the C2 report and every P0 checkpoint.
    292_s: bound to the FROZEN sentinel observation ids (the
    mixture's Anchor sentinel population — a later schedule with
    non-Anchor math_atomic rows cannot contaminate it), and both
    first-GROUP and first-UPDATE occurrences are persisted (one
    group per optimizer step => update = group * updates_per_group;
    the parameter documents the mapping for any future grouping)."""
    members = set(sentinel_observation_ids)
    if not members:
        raise InfrastructureError(
            "sentinel population is empty — bind the frozen "
            "sentinel observation ids (292_s)")
    block = {
        "cell": SENTINEL_CELL,
        "training_exposed": True,
        "observation_ids": sorted(members),
        "groups": 0,
        "worker1_selections": 0,
        "worker1_completions": 0,
        "reward1_completions": 0,
        "reward_varying_groups": 0,
        "q1_counted_groups": 0,
        "first_worker1_group_index": None,
        "first_worker1_update_index": None,
        "first_reward1_group_index": None,
        "first_reward1_update_index": None,
        "first_varying_group_index": None,
        "first_varying_update_index": None,
        "first_q1_counted_group_index": None,
        "first_q1_counted_update_index": None,
    }
    for row in trace_rows:
        oid = row["observation_id"]
        if oid not in members:
            continue
        index = row["global_group_index"]
        update = index * updates_per_group
        block["groups"] += 1
        rewards = list(row["rewards"])
        if len(set(rewards)) > 1:
            block["reward_varying_groups"] += 1
            if block["first_varying_group_index"] is None:
                block["first_varying_group_index"] = index
                block["first_varying_update_index"] = update
        has_r1_fc = False
        has_half_lower = False
        for reward, assignment in zip(row["rewards"],
                                      row["assignments"]):
            if assignment is None:
                continue
            if 1 in assignment:
                block["worker1_selections"] += 1
                block["worker1_completions"] += 1
                if block["first_worker1_group_index"] is None:
                    block["first_worker1_group_index"] = index
                    block["first_worker1_update_index"] = update
            if reward == 1.0:
                block["reward1_completions"] += 1
                if block["first_reward1_group_index"] is None:
                    block["first_reward1_group_index"] = index
                    block["first_reward1_update_index"] = update
                if _fc_fraction(SENTINEL_CELL,
                                tuple(assignment)) == 1.0:
                    has_r1_fc = True
            if reward == 0.5 and _fc_fraction(
                    SENTINEL_CELL, tuple(assignment)) < 1.0:
                has_half_lower = True
        if has_r1_fc and has_half_lower:
            block["q1_counted_groups"] += 1
            if block["first_q1_counted_group_index"] is None:
                block["first_q1_counted_group_index"] = index
                block["first_q1_counted_update_index"] = update
    return block


# --- the amended sizing (288_s §3) ---------------------------------------------

def derive_p0_size_v2(counted_by_cell: Mapping[str, int],
                      c2_epochs: int) -> dict[str, Any]:
    """The mechanical integer sizing derivation over the SIZING
    cells only (the sentinel is excluded from the minimum); the
    arithmetic and the cap formula are otherwise the frozen V1
    forms."""
    rule = MIXTURE_V2_CONFIG["p0_sizing_rule"]
    target = rule["target_q1_counted_groups_per_sizing_cell"]
    sizing = {cell: counted_by_cell[cell]
              for cell in rule["sizing_cells"]}
    minimum = min(sizing.values())
    if minimum <= 0:
        return {"derivable": False,
                "sizing_cells": dict(sizing),
                "reason": "a sizing cell has zero counted groups — "
                          "the direct-Q1 gate has already stopped "
                          "the run"}
    derived_epochs = -(-(target * c2_epochs) // minimum)
    derived_groups = derived_epochs * rule["groups_per_epoch"]
    return {
        "derivable": True,
        "sizing_cells": dict(sizing),
        "min_counted_groups": minimum,
        "min_cell": min(rule["sizing_cells"],
                        key=lambda c: sizing[c]),
        "derived_epochs": derived_epochs,
        "derived_groups": derived_groups,
        "operational_ceiling_hours":
            rule["operational_ceiling_hours"],
        "cap_formula": dict(rule["cap_formula"]),
    }


def derive_p0_cap_v2(*, cumulative_consumed_seconds: float,
                     measured_finalization_reserve_seconds: float,
                     frozen_non_rollout_overhead_seconds: float,
                     measured_whole_epoch_seconds: float
                     ) -> dict[str, Any]:
    """The frozen V1 cap formula, unchanged in form (290_f §4)."""
    rule = MIXTURE_V2_CONFIG["p0_sizing_rule"]
    if measured_whole_epoch_seconds <= 0:
        raise InfrastructureError(
            "measured whole-epoch duration must be positive")
    available = (rule["operational_ceiling_hours"] * 3600.0
                 - cumulative_consumed_seconds
                 - measured_finalization_reserve_seconds
                 - frozen_non_rollout_overhead_seconds)
    capped_epochs = int(math.floor(
        available / measured_whole_epoch_seconds)) \
        if available > 0 else 0
    return {
        "available_generation_seconds": round(available, 1),
        "capped_epochs": max(capped_epochs, 0),
        "stop_for_reviewed_amendment": capped_epochs <= 0,
        "capped_semantics":
            rule["cap_formula"]["capped_semantics"],
    }
