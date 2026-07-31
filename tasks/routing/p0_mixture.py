"""Unit B — the P0 training mixture (269_s-scoped: Q1 + hierarchical
Q2; formal Q3 unavailable). REV2 (271_s repairs).

Builds the ONE fixed, exact integer per-epoch schedule from the
LOCKED extension surface and the FROZEN Unit-A selection record:

- the former Q3-oriented Direction class is formally SUPERSEDED by
  Q2 COMPOSITE EXPOSURE (269_s §6): `math_code -> w3` and
  `fork_join -> w2` composite rows with BOUNDED imbalance — the
  fixed-worker payoffs on the composite rows are computed and
  DISCLOSED (273_s: 18:14 rows still give always-w2 a bounded edge;
  the balance limits, not eliminates, it); the `fork_join -> w2`
  renderer allocation is an EXPLICIT per-renderer quota (271_s B1);
- the five `code_atomic -> w3` rows are a DIRECT-SPECIALIST CONTROL
  class (271_s B4): no upstream unlocking step exists, so they are
  excluded from every Q2 gate and balance computation; their
  transfer confound is preregistered in the record;
- matched `goal_first` CONTROLS (tied rows) keep `goal_first` from
  globally implying worker 3; the reward-relevant conditional (over
  payoff-distinct rows only) is disclosed alongside the diluted one;
- BRIDGE (Q1) rows are quota-selected under the REGISTERED
  predicate — an accessible reward-1.0 family-correct route AND a
  reward-0.5 assignment of STRICTLY LOWER family correctness
  (271_s smaller item); Code-bearing rows additionally require tied
  reward-1 w2/w3 variants; payoff-distinct rows can never be
  Bridge; `math_atomic` and `math_code` are mass-heavy so the Q1
  gate has adequate prospective pass probability (271_s B2);
- ANCHOR is the fixed identity subset; fork_join latent 42 is
  SCREENED everywhere; lookups carry ZERO Bridge quota;
- the old direction-by-renderer balance gate is EXPLICITLY REPLACED
  by the Q2-aligned constraints (269_s §6);
- the Q1 projections use the TRUE Q1-counted rates (271_s B4) —
  rederived from the committed probe archive, frozen as literals,
  and test-verified against the archive — and the freeze carries a
  MEANINGFUL POSITIVE exposure criterion with per-cell prospective
  pass probabilities at the recommended Unit-C size (271_s B2);
- the consuming boundary AUTHENTICATES the supplied selection
  (expected record hash + body rehash) and guards against live
  config mutation (271_s B3).
"""
from __future__ import annotations

import hashlib
import json
import math
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
    # scope per 269_s sign-off: formal Q3 and renderer-independent
    # expertise routing OUT OF SCOPE for this P0
    "objectives": ("q1_family_routing", "q2_hierarchical_unlocking"),
    "extension_surface_lock_sha256":
        "ccb1c3e2db2422a82919292144c0bdecc21d2cc89cb7a3a2c69bec17a2ce6d1b",
    "selection_record_sha256":
        "c6c087757eb4673c42ad37121f9037ca57ce9488e65c4d339d78b37d07fbee34",
    "selection_evidence_path":
        "plans/conductor/evidence/support_extension_v1/selection.json",
    "selection_file_sha256":
        "e0bbb75d61aa0405c86a9a69a0e68957d5db995a389d1b34f353fe1dce546724",
    # projection basis: TRUE Q1-counted rates (271_s B4 — semantic
    # variation additionally requiring lower family correctness on
    # the 0.5 route), rederived from the committed probe archive and
    # frozen here as exact fractions; the archive files are
    # sha-bound and a regression re-derives these numbers
    "q1_counted_rates": {"code_atomic": [32, 72],
                         "fork_join": [8, 72],
                         "math_atomic": [2, 72],
                         "math_code": [2, 72]},
    "projection_basis_path":
        "plans/conductor/evidence/grouped_probe_v1/probe_report.json",
    "projection_basis_file_sha256":
        "3a001c99de1ccf15e3c6a828949ca3f285ee784c0ed1a0880358b73c742df35e",
    "q1_rates_evidence_path":
        "plans/conductor/evidence/grouped_probe_v1/actions.jsonl",
    "q1_rates_evidence_file_sha256":
        "44172e55ba4ae711bd526b6d48bca3ec40b258c70db9862eff0193586c1c4356",
    # per-epoch integer quotas (rows; one row = one G=8 group draw)
    "quotas": {
        # Q2 composite exposure (supersedes the Direction class)
        "q2_w3_math_code": {"observations": 7, "multiplicity": 2},
        # 271_s B1: EXPLICIT per-renderer quota, bound_var priority
        "q2_w2_fork_join": {"bound_var": 4, "goal_first": 14},
        # 271_s B4: direct-specialist control, NOT Q2
        "direct_specialist_control_code_atomic":
            {"observations": 5, "multiplicity": 1},
        # matched goal_first controls: tied rows, per Code cell
        "goal_first_controls_per_code_cell": 6,
        # Bridge (Q1): latents per cell x all 3 renderers; math cells
        # mass-heavy for prospective Q1 pass probability (271_s B2)
        "bridge_latents": {"code_atomic": 4, "fork_join": 4,
                           "math_atomic": 10, "math_code": 10},
        # Anchor: the fixed identity subset
        "anchor_latents": [0],
    },
    # Q2-aligned constraints (EXPLICIT supersession of the Q3
    # renderer-balance gate); balance is COMPOSITE-ONLY (271_s B4)
    "constraints": {
        "max_direction_row_ratio": 1.5,
        "max_p_w3_given_goal_first": 0.5,
        "min_q2_rows_per_direction": 12,
    },
    # 271_s B2: the frozen MEANINGFUL POSITIVE Q1 exposure criterion
    # and the prospective sizing it must pass at
    "q1_gate_criterion": {
        "min_counted_groups_per_cell": 2,
        "min_distinct_latents_among_counted": 2,
        "recommended_unit_c_epochs": 5,
        "min_prospective_pass_probability": 0.9,
        # 273_s blocking decision, resolved by EXPLICIT supersession
        # (never an implicit disappearance): the inherited >=2
        # renderer-strata requirement was Q3-deconfounding machinery;
        # the Q1 estimand (family routing) is renderer-independent,
        # every bridge latent enters with the COMPLETE renderer
        # crossing (structural equal-draw balance), and
        # renderer-stratified reporting is retained (269_s §5) so a
        # persistently silent stratum is reportable evidence. Gating
        # on per-renderer counted events would force either a budget
        # breach (6 epochs > the 1.0 GPU-h ceiling) or Bridge
        # over-weighting against 269_s §6; expected >=2-strata
        # occupancy at the math cells (~0.85) is DISCLOSED in the
        # projections.
        "renderer_representation": {
            "superseded": True,
            "replaced_by": "structural renderer crossing + "
                           "stratified reporting",
        },
    },
    "screened_latents": {"fork_join": [42]},  # diagnostic, never counted
    "shuffle_seed": 20260731,
    "lineage": {
        "parent_entry_sha256":
            "b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd",
        "outcome_informed": True,
        "motivating_evidence": "269_s §6 required Unit-B revision; "
                               "271_s repairs",
    },
}
CONFIG_SHA256 = content_sha256(MIXTURE_CONFIG)

_CLASS_PRECEDENCE = ("q2_composite", "direct_specialist_control",
                     "anchor", "goal_first_control", "bridge")


def tranche_freeze() -> dict[str, Any]:
    """Unit B is CPU-only (no GPU budget, no ledger launch); its
    freeze is the self-hashed design record consumed by the Unit-C
    freeze. Mirrors the live-config guard (273_s smaller item): a
    mutated config cannot produce a noncanonical freeze."""
    if content_sha256(MIXTURE_CONFIG) != CONFIG_SHA256:
        raise InfrastructureError(
            "MIXTURE_CONFIG was mutated after import — refusing to "
            "freeze a noncanonical config (273_s)")
    body = {
        "kind": "p0_mixture",
        "question": ("Unit B: the ONE fixed P0 training schedule — "
                     "does the frozen mixture give Q1 reward-varying "
                     "exposure in all four critical cells and "
                     "balanced downstream Q2 opportunities, under "
                     "the 269_s scope?"),
        "motivation": "269_s §6; 260_f signed design as amended; "
                      "271_s repairs",
        "config": MIXTURE_CONFIG,
        "budget_gpu_hours": 0.0,
    }
    return {**body, "freeze_sha256": content_sha256(body)}


# --- frozen inputs -------------------------------------------------------------

def validate_frozen_selection(record: Mapping[str, Any]) -> None:
    """271_s B3: the AUTHENTICATION boundary every consumer runs —
    expected record hash from the frozen config AND body rehash. A
    modified selection retaining the frozen pointer refuses here."""
    if not isinstance(record, Mapping) or record.get(
            "record_sha256") != MIXTURE_CONFIG[
            "selection_record_sha256"]:
        raise InfrastructureError(
            "selection record is not the frozen Unit-A selection")
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record["record_sha256"]:
        raise InfrastructureError(
            "selection record does not rehash (271_s B3)")


def load_frozen_selection() -> dict[str, Any]:
    config = MIXTURE_CONFIG
    raw = Path(config["selection_evidence_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != \
            config["selection_file_sha256"]:
        raise InfrastructureError(
            "selection evidence bytes are not the frozen ones")
    record = json.loads(raw.decode("utf-8"))
    validate_frozen_selection(record)
    return record


def load_projection_basis() -> dict[str, dict[str, float]]:
    """Per-cell checkpoint-zero rates: TRUE Q1-counted rates from the
    frozen literals (271_s B4; archive-rederived by regression) and
    zero-variance rates from the committed probe report. Measured on
    the ORIGINAL support; transport to extension rows is a DISCLOSED
    assumption."""
    config = MIXTURE_CONFIG
    raw = Path(config["projection_basis_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != \
            config["projection_basis_file_sha256"]:
        raise InfrastructureError(
            "projection basis bytes are not the frozen probe report")
    report = json.loads(raw.decode("utf-8"))
    basis = {}
    for cell, stats in report["by_cell"].items():
        zero_var = stats["zero_variance"]["any"]
        entry = {"p_zero_variance":
                 zero_var["count"] / zero_var["denominator"]}
        if cell in CRITICAL_CELLS:
            num, den = config["q1_counted_rates"][cell]
            entry["p_q1_counted"] = num / den
        basis[cell] = entry
    return basis


def q1_counted_rates_from_archive(loaded_original: Mapping[str, Any]
                                  ) -> dict[str, list[int]]:
    """Rederive the frozen `q1_counted_rates` from the committed
    probe trace: a group counts for Q1 iff it contains a reward-1.0
    FULLY family-correct completion AND a reward-0.5 completion of
    STRICTLY LOWER family correctness (271_s B4)."""
    config = MIXTURE_CONFIG
    raw = Path(config["q1_rates_evidence_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != \
            config["q1_rates_evidence_file_sha256"]:
        raise InfrastructureError(
            "probe trace bytes are not the frozen archive")
    meta = {obs["observation_id"]: obs
            for obs in loaded_original["observations"]}
    counted: dict[str, int] = {}
    total: dict[str, int] = {}
    for line in raw.decode("utf-8").splitlines():
        row = json.loads(line)
        cell = meta[row["observation_id"]]["cell_id"]
        total[cell] = total.get(cell, 0) + 1
        has_r1_fc = any(
            r == 1.0 and a is not None
            and _fc_fraction(cell, tuple(a)) == 1.0
            for r, a in zip(row["rewards"], row["assignments"]))
        has_half_lower = any(
            r == 0.5 and a is not None
            and _fc_fraction(cell, tuple(a)) < 1.0
            for r, a in zip(row["rewards"], row["assignments"]))
        if has_r1_fc and has_half_lower:
            counted[cell] = counted.get(cell, 0) + 1
    return {cell: [counted.get(cell, 0), total[cell]]
            for cell in CRITICAL_CELLS}


# --- the bridge predicate (260_f §1 + 271_s registered condition) ---------------

def _fc_fraction(cell: str, assignment: tuple[int, ...]) -> float:
    families = NODE_FAMILIES[cell]
    nodes = sorted(families)
    correct = sum(1 for n, w in zip(nodes, assignment)
                  if WORKER_FAMILIES.get(w) == families[n])
    return correct / len(nodes)


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
    """The REGISTERED Q1 bridge predicate: an accessible reward-1.0
    fully family-correct route AND a reward-0.5 assignment of
    STRICTLY LOWER family correctness (271_s smaller item — the
    lower-family-correctness condition is enforced, not assumed);
    Code-bearing rows additionally REQUIRE tied reward-1 w2/w3
    variants (260_f, no 'where available')."""
    has_r1_fc = any(p == 1.0 and _fc_fraction(cell, a) == 1.0
                    for a, p in rows.items())
    has_half_lower = any(p == 0.5 and _fc_fraction(cell, a) < 1.0
                         for a, p in rows.items())
    if not (has_r1_fc and has_half_lower):
        return False
    variants = _code_variants(cell)
    if variants is not None:
        w2v, w3v = variants
        if not (rows.get(w2v) == 1.0 and rows.get(w3v) == 1.0):
            return False
    return True


def _binomial_at_least(n: int, p: float, k: int) -> float:
    """P(X >= k) for X ~ Binomial(n, p), exact."""
    below = sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
                for i in range(k))
    return 1.0 - below


def _block_occupancy_at_least(blocks: int, draws_per_block: int,
                              p: float, k: int) -> float:
    """273_s: the probability that at least `k` of `blocks`
    independent latent blocks (each `draws_per_block` IID
    Bernoulli(p) group draws) contain >=1 counted group — the
    EXACT event the frozen criterion states (>=2 counted groups
    from >=2 DISTINCT latents == >=2 occupied latent blocks)."""
    q = 1.0 - (1.0 - p) ** draws_per_block
    return _binomial_at_least(blocks, q, k)


# --- the mixture builder -------------------------------------------------------

def build_mixture(loaded: Mapping[str, Any],
                  selection: Mapping[str, Any]) -> dict[str, Any]:
    """The ONE fixed per-epoch schedule: authenticated inputs,
    deterministic class assignment under the frozen precedence, exact
    integer multiplicities with exact-quota refusals, frozen shuffle,
    Q2-aligned constraint refusals, and prospective projections
    (true-Q1 rates, gate pass probabilities at the recommended
    Unit-C size)."""
    config = MIXTURE_CONFIG
    # 271_s B3: live-config guard — a mutated config cannot ride
    # under the import-time frozen hash
    if content_sha256(config) != CONFIG_SHA256:
        raise InfrastructureError(
            "MIXTURE_CONFIG was mutated after import — the live "
            "config no longer matches the frozen CONFIG_SHA256 "
            "(271_s B3)")
    quotas = config["quotas"]
    lock = loaded.get("lock", {})
    if lock.get("lock_sha256") != \
            config["extension_surface_lock_sha256"]:
        raise InfrastructureError(
            "mixture must build on the frozen extension lock")
    # 271_s B3: the consuming boundary authenticates the selection
    validate_frozen_selection(selection)
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

    # 1. Q2 composite (precedence first) — exact quotas enforced
    mc_pool = [oid for oid in sorted(
        owned.get("math_code|w3_favoured", [])) if not is_screened(oid)]
    if len(mc_pool) != quotas["q2_w3_math_code"]["observations"]:
        raise InfrastructureError(
            f"math_code w3 pool {len(mc_pool)} != the frozen quota "
            f"{quotas['q2_w3_math_code']['observations']} (271_s)")
    for oid in mc_pool:
        take(oid, "q2_composite",
             quotas["q2_w3_math_code"]["multiplicity"])
    # 271_s B1: fork_join w2 rows by EXPLICIT per-renderer quota,
    # ascending latent index within each renderer stratum
    fj_pool = [oid for oid in owned.get("fork_join|w2_favoured", [])
               if not is_screened(oid)]
    for renderer, want in quotas["q2_w2_fork_join"].items():
        stratum = sorted(
            (oid for oid in fj_pool
             if disclosure[oid]["renderer_id"] == renderer),
            key=lambda o: disclosure[o]["latent_index"])
        if len(stratum) < want:
            raise InfrastructureError(
                f"fork_join w2 {renderer} pool {len(stratum)} cannot "
                f"fill the frozen quota {want} (271_s B1)")
        for oid in stratum[:want]:
            take(oid, "q2_composite", 1)

    # 2. Direct-specialist control (271_s B4): code_atomic w3 rows —
    # no upstream unlocking step; excluded from every Q2 gate; the
    # transfer confound is preregistered below
    ca_pool = [oid for oid in sorted(
        owned.get("code_atomic|w3_favoured", []))
        if not is_screened(oid)]
    ca_quota = quotas["direct_specialist_control_code_atomic"]
    if len(ca_pool) != ca_quota["observations"]:
        raise InfrastructureError(
            f"code_atomic w3 pool {len(ca_pool)} != the frozen quota "
            f"{ca_quota['observations']} (271_s)")
    for oid in ca_pool:
        take(oid, "direct_specialist_control", ca_quota["multiplicity"])

    # 3. Anchor: the fixed identity subset
    for oid in sorted(meta):
        row = disclosure[oid]
        if row["latent_index"] in quotas["anchor_latents"] \
                and oid not in assigned and not is_screened(oid):
            take(oid, "anchor", 1)

    # 4. Matched goal_first controls — exact quota, underfill refuses
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
                f"{cell}: goal_first control pool {len(pool)} cannot "
                f"fill the frozen quota {per_cell_controls} (271_s)")
        for oid in pool[:per_cell_controls]:
            take(oid, "goal_first_control", 1)

    # 5. Bridge: quota-selected complete-renderer-crossed latents
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
            if any(disclosure[oid]["direction"] not in
                   ("tied", "no_pair") for oid in oids):
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

    screened = sorted(set(meta) - set(assigned))

    # --- the exact integer schedule + frozen shuffle -------------------
    rows = []
    for oid in sorted(assigned):
        rows.extend([oid] * multiplicity[oid])
    rng = random.Random(config["shuffle_seed"])
    rng.shuffle(rows)

    # --- Q2-aligned constraints (COMPOSITE-ONLY balance; refusals) -----
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
            f"{limits['max_direction_row_ratio']} — the bounded "
            "imbalance limit (269_s; 273_s wording)")
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
    # 271_s smaller item: the REWARD-RELEVANT conditional — over
    # payoff-distinct goal_first rows only (tied rows cannot penalize
    # a worker-3 shortcut)
    distinct_gf = [oid for oid in goal_first_rows
                   if disclosure[oid]["direction"]
                   in ("w2_favoured", "w3_favoured")]
    p_w3_gf_distinct = (
        sum(1 for oid in distinct_gf
            if disclosure[oid]["direction"] == "w3_favoured")
        / len(distinct_gf)) if distinct_gf else 0.0
    # 273_s: the Q2-COMPOSITE-ONLY goal_first conditional (excludes
    # the direct-specialist controls)
    q2_gf = [oid for oid in goal_first_rows
             if assigned.get(oid) == "q2_composite"
             and disclosure[oid]["direction"]
             in ("w2_favoured", "w3_favoured")]
    q2_gf_row_count = sum(multiplicity[oid] for oid in set(q2_gf))
    q2_gf_w3_rows = sum(multiplicity[oid] for oid in set(q2_gf)
                        if disclosure[oid]["direction"]
                        == "w3_favoured")
    p_w3_gf_q2 = q2_gf_w3_rows / q2_gf_row_count \
        if q2_gf_row_count else 0.0
    # 273_s: the fixed-worker payoffs over the composite rows — the
    # imbalance is BOUNDED and disclosed, not eliminated
    composite_rows = [oid for oid, cls in assigned.items()
                      if cls == "q2_composite"
                      for _ in range(multiplicity[oid])]
    constant_policy = {}
    for label, worker in (("always_w2", 2), ("always_w3", 3)):
        total_payoff = 0.0
        for oid in composite_rows:
            cell = disclosure[oid]["cell_id"]
            w2v, w3v = _code_variants(cell)
            variant = w2v if worker == 2 else w3v
            total_payoff += per_obs[oid][variant]
        constant_policy[label] = round(
            total_payoff / len(composite_rows), 5)
    for (cell, index) in screened_latents:
        for oid, row in disclosure.items():
            if row["cell_id"] == cell and row["latent_index"] == index \
                    and oid in assigned:
                raise InfrastructureError(
                    f"diagnostic latent {cell}:{index} entered the "
                    "schedule (269_s §6 item 6)")

    # --- prospective projections (true-Q1 rates; gate probabilities) ---
    basis = load_projection_basis()
    class_rows: dict[str, int] = {}
    for oid, cls in assigned.items():
        class_rows[cls] = class_rows.get(cls, 0) + multiplicity[oid]
    criterion = config["q1_gate_criterion"]
    epochs = criterion["recommended_unit_c_epochs"]
    q1_projection = {}
    bridge_latent_quota = quotas["bridge_latents"]
    for cell in CRITICAL_CELLS:
        bridge_rows = sum(
            multiplicity[oid] for oid, cls in assigned.items()
            if cls == "bridge" and disclosure[oid]["cell_id"] == cell)
        p = basis[cell]["p_q1_counted"]
        draws = bridge_rows * epochs
        latents = bridge_latent_quota[cell]
        draws_per_latent = len(RENDERER_IDS) * epochs
        if latents * draws_per_latent != draws:
            raise InfrastructureError(
                f"{cell}: bridge draws {draws} != latents x renderer "
                "crossing x epochs — the block model does not match "
                "the schedule")
        # 273_s: the statistic IS the frozen criterion — >=2 counted
        # groups from >=2 DISTINCT latents (latent-block occupancy),
        # enforced UNROUNDED
        pass_probability = _block_occupancy_at_least(
            latents, draws_per_latent, p,
            criterion["min_distinct_latents_among_counted"])
        renderer_occupancy = _block_occupancy_at_least(
            len(RENDERER_IDS), latents * epochs, p, 2)
        q1_projection[cell] = {
            "bridge_rows_per_epoch": bridge_rows,
            "p_group_q1_counted_ckpt0": round(p, 4),
            "expected_q1_counted_groups_per_epoch": round(
                bridge_rows * p, 2),
            "unit_c_draws_at_recommended_epochs": draws,
            "prospective_pass_probability": round(
                pass_probability, 4),
            # DISCLOSED, not gated (the supersession in the frozen
            # criterion): expected >=2 renderer-strata occupancy
            "renderer_two_strata_occupancy_disclosed": round(
                renderer_occupancy, 4),
        }
        if pass_probability < \
                criterion["min_prospective_pass_probability"]:
            raise InfrastructureError(
                f"{cell}: prospective Q1 gate pass probability "
                f"{pass_probability!r} < the frozen "
                f"{criterion['min_prospective_pass_probability']} — "
                "rebalance Bridge mass or Unit-C size (271_s B2, "
                "273_s block-occupancy statistic)")
    zero_variance_expected = round(sum(
        multiplicity[oid]
        * basis[disclosure[oid]["cell_id"]]["p_zero_variance"]
        for oid in assigned) / len(rows), 4)
    projections = {
        "basis": ("TRUE Q1-counted ckpt-0 per-cell rates (271_s B4), "
                  "frozen literals rederived from the committed probe "
                  "archive; zero-variance rates from the probe "
                  "report; transport to extension rows is a "
                  "disclosed assumption"),
        "epoch_rows": len(rows),
        "class_rows": class_rows,
        "q1": q1_projection,
        "q1_gate_criterion": dict(criterion),
        "q2_exposure_rows_per_epoch": {"w2_favoured": w2_rows,
                                       "w3_favoured": w3_rows},
        "p_w3_given_goal_first": round(p_w3_gf, 4),
        "p_w3_given_goal_first_payoff_distinct": round(
            p_w3_gf_distinct, 4),
        "p_w3_given_goal_first_q2_composite_only": round(
            p_w3_gf_q2, 4),
        # 273_s: BOUNDED imbalance, disclosed — a constant-worker
        # policy retains a small edge on the composite rows
        "constant_worker_payoffs_on_composite_rows": constant_policy,
        "expected_zero_variance_fraction": zero_variance_expected,
        "direct_specialist_control_note": (
            "the code_atomic w3 rows are a DIRECT-SPECIALIST CONTROL "
            "(271_s B4): no upstream unlocking step; excluded from "
            "every Q2 gate and balance; their transfer confound "
            "(atomic-row learning transferring to composites) is "
            "preregistered and reported separately"),
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
    the locked surface and the AUTHENTICATED frozen selection."""
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record.get("record_sha256"):
        raise InfrastructureError("mixture record does not rehash")
    rederived = build_mixture(loaded, selection)
    if json.loads(json.dumps(rederived)) != \
            json.loads(json.dumps(dict(record))):
        raise InfrastructureError(
            "mixture does not rederive from the locked surface and "
            "frozen selection")
