"""Unit B — the P0 training mixture (269_s-scoped: Q1 + hierarchical
Q2; formal Q3 unavailable).

Builds the ONE fixed, exact integer per-epoch schedule from the
LOCKED extension surface and the FROZEN Unit-A selection record:

- the former Q3-oriented Direction class is formally SUPERSEDED by
  Q2 COMPOSITE EXPOSURE (269_s §6): the owned direction rows give
  both scheduled downstream choices (`math_code -> w3`,
  `fork_join -> w2`) group-level exposure balanced so that mixture
  imbalance cannot reward an always-w2 or always-w3 policy;
- matched `goal_first` CONTROLS (tied rows) keep `goal_first` from
  globally implying worker 3, while the actual worker-3 advantage
  remains disclosed as renderer-confounded;
- BRIDGE (Q1) rows are quota-selected under the 260_f predicate
  (Code-bearing rows REQUIRE tied reward-1 w2/w3 variants;
  payoff-distinct rows can never be Bridge), math-heavy because the
  `math_atomic` family-routing basin is Q2's step-1 prerequisite;
- ANCHOR is the fixed identity subset (latent 0, all six cells, all
  renderers; lookups carry ZERO Bridge quota) for
  forgetting/stability visibility;
- fork_join latent 42 (the renderer-reversal diagnostic) is
  SCREENED everywhere at multiplicity zero, never counted;
- the old complete-schedule direction-by-renderer balance gate
  (Q3-designed) is EXPLICITLY REPLACED by the Q2-aligned constraints
  below (269_s §6 item — a reviewed supersession, not a silent
  relaxation);
- prospective GROUP-LEVEL PROJECTIONS (Q1-counted exposure,
  zero-variance fractions, per-direction Q2 exposure) derive from
  the committed Step-6 probe's checkpoint-zero per-cell rates —
  a disclosed transport assumption, no new GPU spend — so the
  Unit-C freeze can preregister its gates against them (269_s §7
  option 1: projections choose the candidate BEFORE the C run).
"""
from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tasks.conductor.stage1 import NODE_FAMILIES, WORKER_FAMILIES
from tasks.conductor.types import (
    CELL_IDS,
    RENDERER_IDS,
    InfrastructureError,
)

from .charter import content_sha256

CRITICAL_CELLS = ("code_atomic", "fork_join", "math_atomic",
                  "math_code")
LOOKUP_CELLS = ("lookup_atomic", "lookup_math")

MIXTURE_CONFIG: dict[str, Any] = {
    "tranche": "routing-dev-p0-mixture-v1",
    # scope per 269_s sign-off: Q1 family routing + Q2 hierarchical
    # unlocking and coarse, cell-correlated downstream model choice;
    # formal Q3 and renderer-independent expertise routing OUT OF
    # SCOPE for this P0
    "objectives": ("q1_family_routing", "q2_hierarchical_unlocking"),
    "extension_surface_lock_sha256":
        "ccb1c3e2db2422a82919292144c0bdecc21d2cc89cb7a3a2c69bec17a2ce6d1b",
    "selection_record_sha256":
        "c6c087757eb4673c42ad37121f9037ca57ce9488e65c4d339d78b37d07fbee34",
    "selection_evidence_path":
        "plans/conductor/evidence/support_extension_v1/selection.json",
    "selection_file_sha256":
        "e0bbb75d61aa0405c86a9a69a0e68957d5db995a389d1b34f353fe1dce546724",
    # projection basis: the committed Step-6 probe report (ckpt-0
    # per-cell rates on the ORIGINAL support — transport to new rows
    # is a disclosed assumption)
    "projection_basis_path":
        "plans/conductor/evidence/grouped_probe_v1/probe_report.json",
    "projection_basis_file_sha256":
        "3a001c99de1ccf15e3c6a828949ca3f285ee784c0ed1a0880358b73c742df35e",
    # per-epoch integer quotas (rows; one row = one G=8 group draw)
    "quotas": {
        # Q2 composite exposure (supersedes the Direction class)
        "q2_w3_math_code": {"observations": 7, "multiplicity": 2},
        "q2_w3_code_atomic": {"observations": 5, "multiplicity": 1},
        "q2_w2_fork_join": {"rows": 18},   # 4 bound_var + 14 goal_first, ascending
        # matched goal_first controls: tied rows, per Code cell
        "goal_first_controls_per_code_cell": 6,
        # Bridge (Q1): latents per cell x all 3 renderers
        "bridge_latents": {"code_atomic": 4, "fork_join": 4,
                           "math_atomic": 10, "math_code": 4},
        # Anchor: the fixed identity subset
        "anchor_latents": [0],
    },
    # Q2-aligned constraints (EXPLICIT supersession of the Q3
    # renderer-balance gate)
    "constraints": {
        "max_direction_row_ratio": 1.5,
        "max_p_w3_given_goal_first": 0.5,
        "min_q2_rows_per_direction": 12,
    },
    "screened_latents": {"fork_join": [42]},   # diagnostic, never counted
    "shuffle_seed": 20260731,
    "lineage": {
        "parent_entry_sha256":
            "b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd",
        "outcome_informed": True,
        "motivating_evidence": "269_s §6 required Unit-B revision",
    },
}
CONFIG_SHA256 = content_sha256(MIXTURE_CONFIG)

_CLASS_PRECEDENCE = ("q2_composite", "anchor", "goal_first_control",
                     "bridge")


def tranche_freeze() -> dict[str, Any]:
    """Unit B is CPU-only (no GPU budget, no ledger launch); its
    freeze is the self-hashed design record consumed by the Unit-C
    freeze."""
    body = {
        "kind": "p0_mixture",
        "question": ("Unit B: the ONE fixed P0 training schedule — "
                     "does the frozen mixture give Q1 reward-varying "
                     "exposure in all four critical cells and "
                     "balanced downstream Q2 opportunities, under "
                     "the 269_s scope?"),
        "motivation": "269_s §6; 260_f signed design as amended",
        "config": MIXTURE_CONFIG,
        "budget_gpu_hours": 0.0,
    }
    return {**body, "freeze_sha256": content_sha256(body)}


# --- frozen inputs -------------------------------------------------------------

def load_frozen_selection() -> dict[str, Any]:
    config = MIXTURE_CONFIG
    raw = Path(config["selection_evidence_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != \
            config["selection_file_sha256"]:
        raise InfrastructureError(
            "selection evidence bytes are not the frozen ones")
    record = json.loads(raw.decode("utf-8"))
    if record.get("record_sha256") != \
            config["selection_record_sha256"]:
        raise InfrastructureError(
            "selection record is not the frozen Unit-A selection")
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record["record_sha256"]:
        raise InfrastructureError("selection record does not rehash")
    return record


def load_projection_basis() -> dict[str, dict[str, float]]:
    """Per-cell checkpoint-zero rates from the committed Step-6 probe
    report: P(group semantically reward-varying) and P(group
    zero-variance). Measured on the ORIGINAL support; transport to
    extension rows is a DISCLOSED assumption."""
    config = MIXTURE_CONFIG
    raw = Path(config["projection_basis_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != \
            config["projection_basis_file_sha256"]:
        raise InfrastructureError(
            "projection basis bytes are not the frozen probe report")
    report = json.loads(raw.decode("utf-8"))
    basis = {}
    for cell, stats in report["by_cell"].items():
        semantic = stats["semantic_contrast"]
        zero_var = stats["zero_variance"]["any"]
        basis[cell] = {
            "p_semantic_varying":
                semantic["count"] / semantic["denominator"],
            "p_zero_variance":
                zero_var["count"] / zero_var["denominator"],
        }
    return basis


# --- the bridge predicate (260_f §1, rev4 wording) -----------------------------

def _family_correct(cell: str, assignment: tuple[int, ...]) -> bool:
    families = NODE_FAMILIES[cell]
    nodes = sorted(families)
    return all(WORKER_FAMILIES.get(w) == families[n]
               for n, w in zip(nodes, assignment))


def _code_variants(cell: str) -> tuple[tuple[int, ...],
                                       tuple[int, ...]] | None:
    families = NODE_FAMILIES[cell]
    nodes = sorted(families)
    if not any(f == "code" for f in families.values()):
        return None

    def variant(w: int) -> tuple[int, ...]:
        out = []
        for n in nodes:
            family = families[n]
            if family == "code":
                out.append(w)
            else:
                (member,) = [wid for wid, fam in
                             WORKER_FAMILIES.items() if fam == family]
                out.append(member)
        return tuple(out)

    return variant(2), variant(3)


def bridge_eligible(cell: str,
                    rows: Mapping[tuple[int, ...], float]) -> bool:
    """260_f: an accessible reward-1.0 family-correct route AND a
    reward-0.5 assignment; Code-bearing rows additionally REQUIRE
    tied reward-1 w2/w3 variants (no 'where available')."""
    has_r1_fc = any(p == 1.0 and _family_correct(cell, a)
                    for a, p in rows.items())
    has_half = any(p == 0.5 for p in rows.values())
    if not (has_r1_fc and has_half):
        return False
    variants = _code_variants(cell)
    if variants is not None:
        w2v, w3v = variants
        if not (rows.get(w2v) == 1.0 and rows.get(w3v) == 1.0):
            return False
    return True


# --- the mixture builder -------------------------------------------------------

def build_mixture(loaded: Mapping[str, Any],
                  selection: Mapping[str, Any]) -> dict[str, Any]:
    """The ONE fixed per-epoch schedule: deterministic class
    assignment under the frozen precedence, exact integer
    multiplicities, frozen shuffle, Q2-aligned constraint refusals,
    and prospective projections."""
    config = MIXTURE_CONFIG
    quotas = config["quotas"]
    lock = loaded.get("lock", {})
    if lock.get("lock_sha256") != \
            config["extension_surface_lock_sha256"]:
        raise InfrastructureError(
            "mixture must build on the frozen extension lock")
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

    # 1. Q2 composite (precedence first)
    owned: dict[str, list[str]] = {}
    for source in ("direction_buckets", "screened_surplus"):
        for bucket, members in selection[source].items():
            for member in members:
                owned.setdefault(bucket, []).extend(
                    member["observation_ids"])
    for oid in sorted(owned.get("math_code|w3_favoured", [])):
        if not is_screened(oid):
            take(oid, "q2_composite",
                 quotas["q2_w3_math_code"]["multiplicity"])
    for oid in sorted(owned.get("code_atomic|w3_favoured", [])):
        if not is_screened(oid):
            take(oid, "q2_composite",
                 quotas["q2_w3_code_atomic"]["multiplicity"])
    fj_pool = [oid for oid in owned.get("fork_join|w2_favoured", [])
               if not is_screened(oid)]
    # ascending (renderer order within latent): bound_var rows first
    # in frozen renderer order, then by latent index
    fj_sorted = sorted(
        fj_pool, key=lambda o: (RENDERER_IDS.index(
            disclosure[o]["renderer_id"]),
            disclosure[o]["latent_index"]))
    for oid in fj_sorted[:quotas["q2_w2_fork_join"]["rows"]]:
        take(oid, "q2_composite", 1)

    # 2. Anchor: the fixed identity subset
    for oid in sorted(meta):
        row = disclosure[oid]
        if row["latent_index"] in quotas["anchor_latents"] \
                and oid not in assigned and not is_screened(oid):
            take(oid, "anchor", 1)

    # 3. Matched goal_first controls: tied goal_first Code rows,
    # ascending latent index
    per_cell_controls = quotas["goal_first_controls_per_code_cell"]
    for cell in ("code_atomic", "fork_join", "math_code"):
        pool = sorted(
            (oid for oid, row in disclosure.items()
             if row["cell_id"] == cell
             and row["renderer_id"] == "goal_first"
             and row["direction"] == "tied"
             and oid not in assigned and not is_screened(oid)),
            key=lambda o: disclosure[o]["latent_index"])
        for oid in pool[:per_cell_controls]:
            take(oid, "goal_first_control", 1)

    # 4. Bridge: quota-selected latents whose COMPLETE renderer
    # crossing is bridge-eligible and unconsumed; payoff-distinct
    # rows can never be Bridge (260_f)
    for cell, n_latents in quotas["bridge_latents"].items():
        if cell in LOOKUP_CELLS:
            raise InfrastructureError(
                "lookup cells carry ZERO bridge quota (269_s)")
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
            if any(disclosure[oid]["direction"] != "tied"
                   and disclosure[oid]["direction"] != "no_pair"
                   for oid in oids):
                continue   # payoff-distinct rows never Bridge
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

    # everything else: screened at zero multiplicity (disclosed)
    screened = sorted(set(meta) - set(assigned))

    # --- the exact integer schedule + frozen shuffle -------------------
    rows = []
    for oid in sorted(assigned):
        rows.extend([oid] * multiplicity[oid])
    rng = random.Random(config["shuffle_seed"])
    rng.shuffle(rows)

    # --- Q2-aligned constraints (refusals) -----------------------------
    limits = config["constraints"]
    w3_rows = sum(multiplicity[oid] for oid, cls in assigned.items()
                  if cls == "q2_composite"
                  and disclosure[oid]["direction"] == "w3_favoured")
    w2_rows = sum(multiplicity[oid] for oid, cls in assigned.items()
                  if cls == "q2_composite"
                  and disclosure[oid]["direction"] == "w2_favoured")
    if min(w2_rows, w3_rows) < limits["min_q2_rows_per_direction"]:
        raise InfrastructureError(
            f"Q2 direction exposure {w2_rows}/{w3_rows} under the "
            f"frozen minimum {limits['min_q2_rows_per_direction']}")
    ratio = max(w2_rows, w3_rows) / min(w2_rows, w3_rows)
    if ratio > limits["max_direction_row_ratio"]:
        raise InfrastructureError(
            f"Q2 direction row ratio {ratio:.2f} exceeds the frozen "
            f"{limits['max_direction_row_ratio']} — mixture imbalance "
            "could reward a constant-worker policy (269_s)")
    goal_first_rows = [oid for oid in rows
                       if disclosure[oid]["renderer_id"] == "goal_first"]
    w3_goal_first = sum(
        1 for oid in goal_first_rows
        if disclosure[oid]["direction"] == "w3_favoured")
    p_w3_gf = w3_goal_first / len(goal_first_rows) \
        if goal_first_rows else 0.0
    if p_w3_gf > limits["max_p_w3_given_goal_first"]:
        raise InfrastructureError(
            f"P(w3-favoured | goal_first) = {p_w3_gf:.3f} exceeds "
            f"{limits['max_p_w3_given_goal_first']} — goal_first must "
            "not imply worker 3 (269_s §6 item 5)")
    for (cell, index) in screened_latents:
        for oid, row in disclosure.items():
            if row["cell_id"] == cell and row["latent_index"] == index \
                    and oid in assigned:
                raise InfrastructureError(
                    f"diagnostic latent {cell}:{index} entered the "
                    "schedule (269_s §6 item 6)")

    # --- prospective projections (group-level, ckpt-0 basis) -----------
    basis = load_projection_basis()
    class_rows: dict[str, int] = {}
    for oid, cls in assigned.items():
        class_rows[cls] = class_rows.get(cls, 0) + multiplicity[oid]
    q1_projection = {}
    for cell in CRITICAL_CELLS:
        bridge_rows = sum(
            multiplicity[oid] for oid, cls in assigned.items()
            if cls == "bridge" and disclosure[oid]["cell_id"] == cell)
        q1_projection[cell] = {
            "bridge_rows_per_epoch": bridge_rows,
            "p_group_semantic_varying_ckpt0":
                basis[cell]["p_semantic_varying"],
            "expected_q1_counted_groups_per_epoch": round(
                bridge_rows * basis[cell]["p_semantic_varying"], 2),
        }
    zero_variance_expected = round(sum(
        multiplicity[oid]
        * basis[disclosure[oid]["cell_id"]]["p_zero_variance"]
        for oid in assigned) / len(rows), 4)
    projections = {
        "basis": ("Step-6 probe ckpt-0 per-cell rates on the ORIGINAL "
                  "support; transport to extension rows is a disclosed "
                  "assumption"),
        "epoch_rows": len(rows),
        "class_rows": class_rows,
        "q1": q1_projection,
        "q2_exposure_rows_per_epoch": {"w2_favoured": w2_rows,
                                       "w3_favoured": w3_rows},
        "p_w3_given_goal_first": round(p_w3_gf, 4),
        "expected_zero_variance_fraction": zero_variance_expected,
        "q2_c2_eligibility_note": (
            "measured ckpt-0 C2 eligibility on w3-favoured composites "
            "is 0/64 (Step-6 probe) — the Q2 STARTING CONDITION; "
            "expected to rise with C1, never a direct-C2-exposure "
            "claim"),
    }

    record = {
        "kind": "routing-dev-p0-mixture-v1",
        "config_sha256": CONFIG_SHA256,
        "extension_surface_lock_sha256": lock["lock_sha256"],
        "selection_record_sha256": selection["record_sha256"],
        "class_assignment": {oid: assigned[oid]
                             for oid in sorted(assigned)},
        "multiplicities": {oid: multiplicity[oid]
                           for oid in sorted(assigned)},
        "schedule_rows": rows,
        "screened_zero_multiplicity_count": len(screened),
        "projections": projections,
        "superseded_gate_note": (
            "the complete-schedule direction-by-renderer balance "
            "requirement (Q3-designed) is EXPLICITLY SUPERSEDED by "
            "the constraints block (269_s §6)"),
    }
    record["record_sha256"] = content_sha256(record)
    return record


def verify_mixture(loaded: Mapping[str, Any],
                   selection: Mapping[str, Any],
                   record: Mapping[str, Any]) -> None:
    """The mixture verifier: rehash + byte-exact rederivation from
    the locked surface and frozen selection."""
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record.get("record_sha256"):
        raise InfrastructureError("mixture record does not rehash")
    rederived = build_mixture(loaded, selection)
    if json.loads(json.dumps(rederived)) != \
            json.loads(json.dumps(dict(record))):
        raise InfrastructureError(
            "mixture does not rederive from the locked surface and "
            "frozen selection")
