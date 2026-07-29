"""Unit A — the support-extension runner (260_f, signed design).

A NEW, self-contained support-extension launch (257_s B3): the
complete six-cell factor-balanced prefix 0..47 is declared and
processed through the existing low-level surface machinery under its
OWN launch-manifest kind (never the first-probe contract), with

- indices 0..5 permitted to resolve as slw-keyed cache hits;
- an OVERLAP EQUALITY GATE — the new surface's 0..5 payoffs and
  terminal values must equal the original Step-4 locked surface,
  observation by observation, BEFORE the new lock is accepted;
- comparator selection NEVER invoked: the immutable-comparator
  boundary verifies the ORIGINAL `c_fixed_dev` record against the
  ORIGINAL Step-4 lock, extracts frozen worker 2, and derives an
  extension-scoped consumer record without reselection (only
  ScaleLift consumes it; C2/ModelAcc are surface-defined);
- the ceiling enforced per observation during materialization;
- a TOTAL selector (259_s/260_f): every latent globally assigned to
  at most one direction bucket, deterministic ordering, recorded
  dispositions, renderer/subtype yield disclosure, and a verifier
  that rederives the selection byte-exactly from the locked surface.

The materialization cohort is the outcome-blind prefix; the SELECTOR
over it is outcome-conditioned and the launch is recorded
`outcome_informed = true` (development track only)."""
from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from tasks.conductor.types import (
    CELL_IDS,
    RENDERER_IDS,
    InfrastructureError,
)

from . import dev_support
from .charter import content_sha256, lightweight_freeze
from .ledger import (
    LEDGER_PATH,
    admit_and_append_launch,
    append_ledger_entry,
)
from .support_run import (
    _default_environment,
    _default_runtime,
    _hash_directory,
    _persist_verified,
    _sha_file,
    attest_environment,
)

DRIVER = "tasks/routing/extension_run.py"

EXTENSION_CONFIG: dict[str, Any] = {
    "tranche": "routing-dev-support-extension-v1",
    "namespace": "routing_dev",
    # 257_s B3 / 259_s: the factor-balanced six-cell outcome-blind
    # prefix; only 6..47 is genuinely new — 0..5 must byte-match the
    # Step-4 support through the overlap gate below.
    "prefix_k": 48,
    "original_prefix_k": 6,
    "renderers": list(RENDERER_IDS),
    "visibility": "private",
    "run_root": "runs/routing-dev/support-ext-v1",
    "search_cap": 864,
    "ceiling_gpu_hours": 1.0,
    # the ORIGINAL Step-4 surface: overlap target + comparator root
    "original_surface_lock_sha256":
        "61c4e85a53683c9e2dbcbf15f60794935a76a86d979a69412a97f44ea9f2562b",
    "original_surface_dir": "runs/routing-dev/support-v1/surface",
    "original_c_fixed_path":
        "plans/conductor/evidence/routing_dev_support_v1/c_fixed_dev.json",
    # measured Step-4 basis for the exact cost derivation (231_f):
    # 4,824 planned node executions cost 0.0732 GPU-h
    "cost_basis": {"step4_planned_node_executions": 4824,
                   "step4_measured_gpu_hours": 0.0732},
    # 260_f §2: one overlap rule — a latent is globally assigned to
    # at most one direction bucket; quotas per (Code cell x direction)
    "selector": {
        "target_latents": 3,
        "reduced_power_latents": 2,
        "min_renderer_strata": 2,
        "min_non_goal_first": 1,
    },
    "lineage": {
        "parent_entry_sha256":
            "88c037a188c6c8f5aca21e7690ea288b76dd1f64eb53f6fc2647196d32cb0eeb",
        "outcome_informed": True,
        "motivating_evidence":
            "253_s exposure reading; 260_f signed design Unit A",
    },
}
CONFIG_SHA256 = content_sha256(EXTENSION_CONFIG)

EXTENSION_LAUNCH_KIND = "routing-dev-extension-launch-v1"
_EXTENSION_LAUNCH_KEYS = frozenset({
    "kind", "declaration_sha256", "namespace",
    "worker_visible_fingerprint", "runtime_profile_fingerprint",
    "worker_pool_fingerprint", "request_contract", "cache_identity",
    "prefix_k", "search_cap", "budget_gpu_hours", "run_root",
    "original_surface_lock_sha256", "planned_node_executions",
    "planned_new_node_executions", "expected_new_gpu_hours",
    "routing_source_sha256", "driver", "environment_manifest_sha256",
    "scientific_design_sha256",
})
_SCIENTIFIC_DESIGN_FIELDS = (
    "declaration_sha256", "namespace", "worker_visible_fingerprint",
    "runtime_profile_fingerprint", "worker_pool_fingerprint",
    "request_contract", "cache_identity", "prefix_k", "search_cap",
    "original_surface_lock_sha256",
)

_PRELAUNCH_FILES = ("declaration.json", "env_manifest.json",
                    "extension_launch.json")
_OUTPUT_FILES = ("run_record.json", "selection.json",
                 "comparator.json", "disclosure.json")


def tranche_freeze() -> dict[str, Any]:
    return lightweight_freeze({
        "kind": "support_extension",
        "question": ("Unit A: what structural direction support does "
                     "the six-cell prefix 0..47 add — per-cell "
                     "direction-disjoint latent buckets, renderer "
                     "strata, non-goal_first coverage, and the "
                     "eligible common-cell set for Q3?"),
        "motivation": "260_f signed design Unit A; 253_s exposure "
                      "reading; 257_s B3 extension contract",
        "config": EXTENSION_CONFIG,
        "budget_gpu_hours": EXTENSION_CONFIG["ceiling_gpu_hours"],
    })


def extension_cohort() -> dict[str, list[int]]:
    k = EXTENSION_CONFIG["prefix_k"]
    return {cell: list(range(k)) for cell in CELL_IDS}


def planned_node_counts(declaration: Mapping[str, Any]
                        ) -> dict[str, int]:
    """The exact cost denominators (257_s feasibility): total planned
    node executions for the full prefix and for the genuinely new
    indices >= original_prefix_k."""
    original_k = EXTENSION_CONFIG["original_prefix_k"]
    total = 0
    new = 0
    for obs in declaration["observations"]:
        nodes = obs["assignments"] * obs["num_nodes"]
        total += nodes
        if int(obs["observation_id"].split(":")[2]) >= original_k:
            new += nodes
    return {"planned_node_executions": total,
            "planned_new_node_executions": new}


def expected_cost_derivation(counts: Mapping[str, int]
                             ) -> dict[str, float]:
    """The exact expected-cost derivation from the ledger-recorded
    Step-4 basis (259_s: exact derivation blocks the freeze)."""
    basis = EXTENSION_CONFIG["cost_basis"]
    per_node = basis["step4_measured_gpu_hours"] \
        / basis["step4_planned_node_executions"]
    return {
        "gpu_hours_per_node_execution": per_node,
        "expected_new_gpu_hours": round(
            counts["planned_new_node_executions"] * per_node, 4),
        "full_regeneration_bound_gpu_hours": round(
            counts["planned_node_executions"] * per_node, 4),
    }


def build_extension_launch_manifest(*, declaration: Mapping[str, Any],
                                    environment_manifest:
                                    Mapping[str, Any]
                                    ) -> dict[str, Any]:
    """The ONE pre-launch record for the extension — self-contained:
    no probe rule, no comparator; binds the original Step-4 lock (the
    overlap-gate target), the exact planned node counts, and the
    frozen budget."""
    from .charter import routing_execution_digest
    config = EXTENSION_CONFIG
    dev_support.validate_dev_cohort(
        config["namespace"], declaration["cohort"],
        declaration["renderers"], declaration["visibility"])
    k = config["prefix_k"]
    for cell in CELL_IDS:
        if declaration["cohort"].get(cell) != list(range(k)):
            raise InfrastructureError(
                f"{cell}: the extension cohort must be the complete "
                f"outcome-blind prefix 0..{k - 1} (260_f Unit A)")
    if declaration["renderers"] != config["renderers"] \
            or declaration["visibility"] != config["visibility"]:
        raise InfrastructureError(
            "extension declaration renderers/visibility are not the "
            "frozen ones")
    total = len(declaration["observations"])
    if total != config["search_cap"]:
        raise InfrastructureError(
            f"extension declares {total} rendered observations; the "
            f"frozen design needs exactly {config['search_cap']}")
    counts = planned_node_counts(declaration)
    derivation = expected_cost_derivation(counts)
    if derivation["expected_new_gpu_hours"] > \
            config["ceiling_gpu_hours"]:
        raise InfrastructureError(
            "expected extension cost exceeds the frozen ceiling")
    digest = routing_execution_digest(DRIVER)
    manifest = {
        "kind": EXTENSION_LAUNCH_KIND,
        "declaration_sha256": content_sha256(dict(declaration)),
        "namespace": declaration["namespace"],
        "worker_visible_fingerprint":
            declaration["worker_visible_fingerprint"],
        "runtime_profile_fingerprint":
            declaration["runtime_profile_fingerprint"],
        "worker_pool_fingerprint":
            declaration["worker_pool_fingerprint"],
        "request_contract": declaration["request_contract"],
        "cache_identity": declaration["cache_identity"],
        "prefix_k": k,
        "search_cap": config["search_cap"],
        "budget_gpu_hours": config["ceiling_gpu_hours"],
        "run_root": config["run_root"],
        "original_surface_lock_sha256":
            config["original_surface_lock_sha256"],
        "planned_node_executions": counts["planned_node_executions"],
        "planned_new_node_executions":
            counts["planned_new_node_executions"],
        "expected_new_gpu_hours": derivation["expected_new_gpu_hours"],
        "routing_source_sha256": digest["routing_source_sha256"],
        "driver": digest["driver"],
        "environment_manifest_sha256":
            dev_support.validate_environment_manifest_binding(
                environment_manifest),
    }
    manifest["scientific_design_sha256"] = content_sha256(
        {f: manifest[f] for f in _SCIENTIFIC_DESIGN_FIELDS})
    manifest["manifest_sha256"] = content_sha256(manifest)
    return manifest


def validate_extension_launch_manifest(manifest: Mapping[str, Any],
                                       declaration: Mapping[str, Any],
                                       *, recompute: bool = True
                                       ) -> dict[str, Any]:
    if not isinstance(manifest, Mapping) \
            or set(manifest) != _EXTENSION_LAUNCH_KEYS | \
            {"manifest_sha256"}:
        raise InfrastructureError(
            "extension-launch manifest keys do not match the closed "
            "schema")
    if manifest["kind"] != EXTENSION_LAUNCH_KIND:
        raise InfrastructureError(
            f"unknown extension-launch kind {manifest['kind']!r}")
    body = {k: v for k, v in manifest.items()
            if k != "manifest_sha256"}
    if content_sha256(body) != manifest["manifest_sha256"]:
        raise InfrastructureError(
            "extension-launch manifest does not rehash")
    if manifest["scientific_design_sha256"] != content_sha256(
            {f: manifest[f] for f in _SCIENTIFIC_DESIGN_FIELDS}):
        raise InfrastructureError(
            "extension-launch scientific-design hash does not rehash")
    if manifest["declaration_sha256"] != \
            content_sha256(dict(declaration)):
        raise InfrastructureError(
            "extension-launch manifest is bound to a different "
            "declaration")
    for key in ("namespace", "worker_visible_fingerprint",
                "runtime_profile_fingerprint",
                "worker_pool_fingerprint", "request_contract",
                "cache_identity"):
        if manifest[key] != declaration[key]:
            raise InfrastructureError(
                f"extension-launch manifest {key} does not match the "
                "declaration")
    counts = planned_node_counts(declaration)
    if manifest["planned_node_executions"] != \
            counts["planned_node_executions"] \
            or manifest["planned_new_node_executions"] != \
            counts["planned_new_node_executions"]:
        raise InfrastructureError(
            "extension-launch planned node counts do not rederive "
            "from the declaration")
    if manifest["original_surface_lock_sha256"] != \
            EXTENSION_CONFIG["original_surface_lock_sha256"]:
        raise InfrastructureError(
            "extension-launch original-lock binding is not the frozen "
            "Step-4 lock")
    if manifest["run_root"] != EXTENSION_CONFIG["run_root"]:
        raise InfrastructureError(
            "extension-launch run root is not the frozen lifecycle "
            "root (262_s)")
    if recompute:
        from .charter import routing_execution_digest
        digest = routing_execution_digest(manifest["driver"])
        if digest["routing_source_sha256"] != \
                manifest["routing_source_sha256"]:
            raise InfrastructureError(
                "extension-launch source digest does not recompute "
                "from the tree — the source moved after the freeze")
    return dict(manifest)


# --- the overlap equality gate (257_s B3; BEFORE lock acceptance) --------------

def _payoff_rows(surface_dir: Path) -> dict[tuple[str, tuple[int, ...]],
                                            dict[str, Any]]:
    rows: dict[tuple[str, tuple[int, ...]], dict[str, Any]] = {}
    with (surface_dir / "payoffs.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            key = (row["observation_id"], tuple(row["assignment"]))
            if key in rows:
                raise InfrastructureError(
                    f"duplicate payoff row {key!r}")
            rows[key] = row
    return rows


def verify_overlap_equality(new_surface_dir: str | Path,
                            original_surface_dir: str | Path) -> int:
    """257_s B3: BEFORE the new lock is accepted, every original
    observation's payoff AND terminal value must be reproduced
    exactly by the new surface — observation by observation,
    assignment by assignment. The original rows are read from the
    ORIGINAL locked surface directory. Returns the number of
    compared rows."""
    original = _payoff_rows(Path(original_surface_dir))
    if not original:
        raise InfrastructureError("original surface has no payoff rows")
    new = _payoff_rows(Path(new_surface_dir))
    compared = 0
    for key, row in sorted(original.items()):
        if key not in new:
            raise InfrastructureError(
                f"overlap gate: {key!r} missing from the extension "
                "surface (257_s B3)")
        for field in ("payoff", "terminal_value"):
            if new[key][field] != row[field]:
                raise InfrastructureError(
                    f"overlap gate: {key!r} {field} "
                    f"{new[key][field]!r} != original {row[field]!r} "
                    "— the extension does not reproduce the locked "
                    "support (257_s B3)")
        compared += 1
    return compared


# --- the immutable comparator (257_s B3: never reselect) -----------------------

def load_original_surface(surface_dir: str | Path | None = None
                          ) -> dict[str, Any]:
    return dev_support.load_dev_surface(
        surface_dir or EXTENSION_CONFIG["original_surface_dir"],
        expected_lock_sha256=EXTENSION_CONFIG[
            "original_surface_lock_sha256"])


def immutable_comparator(original_loaded: Mapping[str, Any],
                         extension_lock_sha256: str
                         ) -> dict[str, Any]:
    """The extension's ONLY comparator path: verify the ORIGINAL
    Step-4 `c_fixed_dev` record against the ORIGINAL lock (216_s F3
    full rederivation — a foreign or tampered record refuses), then
    derive an extension-scoped CONSUMER record carrying frozen
    worker 2. `select_c_fixed_dev` is never called on the extension
    surface; only ScaleLift consumes this record — C2 and ModelAcc
    are surface-defined (259_s)."""
    lock = original_loaded.get("lock", {})
    if lock.get("lock_sha256") != \
            EXTENSION_CONFIG["original_surface_lock_sha256"]:
        raise InfrastructureError(
            "immutable comparator must be rooted in the ORIGINAL "
            "Step-4 locked surface (257_s B3)")
    record = json.loads(Path(
        EXTENSION_CONFIG["original_c_fixed_path"]).read_text("utf-8"))
    worker = dev_support.verify_c_fixed_for(original_loaded, record)
    consumer = {
        "kind": "routing-dev-extension-scale-lift-comparator-v1",
        "c_fixed_dev": worker,
        "source_record_sha256": record["record_sha256"],
        "original_surface_lock_sha256": lock["lock_sha256"],
        "extension_surface_lock_sha256": extension_lock_sha256,
        "reselected": False,
        "consumes": "scale_lift_only",
        "development_only": True,
    }
    consumer["record_sha256"] = content_sha256(consumer)
    return consumer


# --- the total selector (259_s/260_f) ------------------------------------------

def public_subtype_record(cell_id: str, latent_index: int,
                          _cache: dict = {}) -> dict[str, Any]:
    """264_s P1: the FROZEN public-subtype contract — the label comes
    from `baselines.observable_subtype` over the sanitized
    `public_feature_record` projection (derivable from the public
    prompt alone; generator-only fields cannot reach it). The
    generator-side collision flags are returned SEPARATELY and may
    only appear under an explicitly generator-side disclosure label —
    never inside the public subtype."""
    key = (cell_id, latent_index)
    if key not in _cache:
        from tasks.conductor import baselines, program
        from tasks.conductor.profiles import DEFAULT_PROFILE
        latent = program.generate_latent(
            cell_id, EXTENSION_CONFIG["namespace"], latent_index,
            DEFAULT_PROFILE).latent
        record = baselines.public_feature_record(latent)
        subtype = baselines.observable_subtype(cell_id, record.params)
        if subtype not in baselines.OBSERVABLE_SUBTYPES[cell_id]:
            raise InfrastructureError(
                f"{cell_id}: subtype {subtype!r} outside the frozen "
                "levels")
        _cache[key] = {
            "subtype": subtype,
            # 266_s P1: the frozen public numeric factors, derived
            # through the sanitized record — lossless, no bins
            "public_numeric_values":
                dict(record.public_numeric_values),
            "generator_side_collisions": {
                "public_numeric_collision":
                    bool(latent.get("public_numeric_collision")),
                "sink_public_numeric_collision":
                    bool(latent.get("sink_public_numeric_collision")),
            },
        }
    return _cache[key]


def direction_table(loaded: Mapping[str, Any]
                    ) -> dict[str, dict[str, Any]]:
    """Per-observation direction from authenticated surface geometry —
    the probe-report semantics (`derive_pair_entry`), never rollout
    data — plus the observable public-factor subtype (262_s P1-3)."""
    from .telemetry import derive_pair_entry
    table: dict[str, dict[str, Any]] = {}
    for obs in loaded["observations"]:
        entry = derive_pair_entry(obs["observation_id"],
                                  obs["cell_id"], loaded["surface"])
        if entry is None:
            direction = "no_pair"
        elif not entry["distinct_payoff"]:
            direction = "tied"
        else:
            direction = f"w{entry['direction']}_favoured"
        latent_index = int(obs["observation_id"].split(":")[2])
        public = public_subtype_record(obs["cell_id"], latent_index)
        table[obs["observation_id"]] = {
            "cell_id": obs["cell_id"],
            "renderer_id": obs["renderer_id"],
            "latent_index": latent_index,
            "latent_program_id": obs["latent_program_id"],
            "direction": direction,
            "subtype": public["subtype"],
            "public_numeric_values":
                dict(public["public_numeric_values"]),
            "generator_side_collisions":
                public["generator_side_collisions"],
        }
    return table


def _code_bearing_cells() -> list[str]:
    from tasks.conductor.stage1 import NODE_FAMILIES
    return sorted(cell for cell, families in NODE_FAMILIES.items()
                  if any(f == "code" for f in families.values()))


def run_extension_selector(loaded: Mapping[str, Any]
                           ) -> dict[str, Any]:
    """The signed TOTAL selector (258_f §4.1 / 260_f §2 as repaired
    by 262_s P1-1/P1-2):

    - the CANDIDATE DOMAIN is indices >= original_prefix_k — legacy
      0..5 latents never qualify for direction buckets; they appear
      only in the complete yield/legacy disclosure (Anchor material);
    - frozen bucket ordering (Code cells ascending, w2 before w3);
      when a candidate latent qualifies for more than one bucket, the
      FIRST bucket in that order consumes it (direction-disjoint by
      construction; renderer reversals stay diagnostics);
    - within each bucket, the CANONICAL QUOTA-BOUNDED SUBSET:
      ascending latent index, stopping once the quota constraints
      (target latents, renderer strata, non-goal_first coverage) are
      all met; qualifying-but-unselected candidates are disclosed as
      screened surplus (Unit B may place them ONLY in Direction or
      Screened-but-unused, never Bridge);
    - dispositions enumerate ALL Code cells x both directions
      (explicit dropped at zero yield), and Q3 common-cell
      eligibility derives from ACCEPTABLE DISPOSITION STATES, never
      raw bucket sizes."""
    config = EXTENSION_CONFIG["selector"]
    domain_start = EXTENSION_CONFIG["original_prefix_k"]
    table = direction_table(loaded)
    # per latent: favoured renderer strata per direction
    latents: dict[tuple[str, int], dict[str, dict[str, str]]] = {}
    for oid, row in table.items():
        key = (row["cell_id"], row["latent_index"])
        latents.setdefault(key, {"w2_favoured": {}, "w3_favoured": {}})
        if row["direction"] in ("w2_favoured", "w3_favoured"):
            latents[key][row["direction"]][row["renderer_id"]] = oid
    # legacy (index < original_prefix_k) direction yield: disclosure
    # only — never candidates (262_s P1-1)
    legacy_disclosure: dict[str, dict[str, list[int]]] = {}
    reversals: list[dict[str, Any]] = []
    candidates: dict[tuple[str, int],
                     dict[str, dict[str, str]]] = {}
    for (cell, index) in sorted(latents):
        favoured = latents[(cell, index)]
        n2 = len(favoured["w2_favoured"])
        n3 = len(favoured["w3_favoured"])
        if n2 == 0 and n3 == 0:
            continue
        if index < domain_start:
            bucket = legacy_disclosure.setdefault(
                cell, {"w2_favoured": [], "w3_favoured": []})
            if n2:
                bucket["w2_favoured"].append(index)
            if n3:
                bucket["w3_favoured"].append(index)
            continue
        if n2 > 0 and n3 > 0:
            # renderer-induced winner reversal: a DIAGNOSTIC of
            # renderer sensitivity, never bidirectional evidence
            # (260_f §2)
            reversals.append({"cell_id": cell, "latent_index": index,
                              "w2_renderers":
                                  sorted(favoured["w2_favoured"]),
                              "w3_renderers":
                                  sorted(favoured["w3_favoured"])})
        candidates[(cell, index)] = favoured

    def member_entry(cell: str, index: int, direction: str
                     ) -> dict[str, Any]:
        strata = candidates[(cell, index)][direction]
        return {"cell_id": cell, "latent_index": index,
                "direction": direction,
                "favoured_renderers": sorted(strata),
                "observation_ids": [strata[r] for r in sorted(strata)],
                "non_goal_first": sorted(
                    r for r in strata if r != "goal_first")}

    # frozen bucket order: Code cells ascending, w2 before w3; the
    # FIRST bucket a latent qualifies for consumes it
    code_cells = _code_bearing_cells()
    consumed: set[tuple[str, int]] = set()
    owner: dict[tuple[str, int], str] = {}
    for cell in code_cells:
        for direction in ("w2_favoured", "w3_favoured"):
            for (c, index) in sorted(candidates):
                if c != cell or (c, index) in consumed:
                    continue
                if candidates[(c, index)][direction]:
                    consumed.add((c, index))
                    owner[(c, index)] = direction
    buckets: dict[str, list[dict[str, Any]]] = {}
    surplus: dict[str, list[dict[str, Any]]] = {}
    dispositions: dict[str, dict[str, Any]] = {}
    for cell in code_cells:
        for direction in ("w2_favoured", "w3_favoured"):
            pool = [index for (c, index) in sorted(candidates)
                    if c == cell and owner.get((c, index)) == direction]
            selected: list[dict[str, Any]] = []
            strata_seen: set[str] = set()
            non_gf = 0

            def quota_met() -> bool:
                return (len(selected) >= config["target_latents"]
                        and len(strata_seen)
                        >= config["min_renderer_strata"]
                        and non_gf >= config["min_non_goal_first"])

            rest: list[dict[str, Any]] = []
            for index in pool:
                entry = member_entry(cell, index, direction)
                if quota_met():
                    rest.append(entry)
                    continue
                selected.append(entry)
                strata_seen.update(entry["favoured_renderers"])
                non_gf += 1 if entry["non_goal_first"] else 0
            key = f"{cell}|{direction}"
            buckets[key] = selected
            surplus[key] = rest
            n = len(selected)
            strata = sorted(strata_seen)
            if n >= config["target_latents"]:
                status = "full_quota"
            elif n >= config["reduced_power_latents"]:
                status = "reduced_power_disclosed"
            else:
                status = "dropped_from_q3"
            if status != "dropped_from_q3" and (
                    len(strata) < config["min_renderer_strata"]
                    or non_gf < config["min_non_goal_first"]):
                status = "quota_constraints_unmet"
            dispositions[key] = {
                "latents": n, "renderer_strata": strata,
                "non_goal_first_latents": non_gf, "status": status}
    # 262_s P1-2: Q3 eligibility derives from ACCEPTABLE disposition
    # states — a quota_constraints_unmet direction cannot authorize a
    # common cell
    acceptable = {"full_quota", "reduced_power_disclosed"}
    common_cells = sorted(
        cell for cell in code_cells
        if dispositions[f"{cell}|w2_favoured"]["status"] in acceptable
        and dispositions[f"{cell}|w3_favoured"]["status"] in acceptable)
    # subtype/public-factor yield disclosure (262_s P1-3): every
    # observation of the surface enters every stratum family
    yield_disclosure: dict[str, dict[str, int]] = {}
    for row in table.values():
        collisions = row["generator_side_collisions"]
        collision_label = (
            f"pnc={collisions['public_numeric_collision']}"
            f"+sink={collisions['sink_public_numeric_collision']}")
        for factor in (f"cell|{row['cell_id']}",
                       f"renderer|{row['renderer_id']}",
                       f"subtype|{row['cell_id']}+{row['subtype']}",
                       f"cell+renderer|{row['cell_id']}"
                       f"+{row['renderer_id']}",
                       f"cell+renderer+subtype|{row['cell_id']}"
                       f"+{row['renderer_id']}+{row['subtype']}",
                       # generator-side ANALYSIS ONLY (264_s P1):
                       # collision flags never enter the public
                       # subtype strata
                       f"generator-side-collision|{row['cell_id']}"
                       f"+{collision_label}"):
            bucket = yield_disclosure.setdefault(factor, {
                "w2_favoured": 0, "w3_favoured": 0, "tied": 0,
                "no_pair": 0})
            bucket[row["direction"]] += 1
    # 266_s P1: the LOSSLESS identity-bound public-factor
    # disclosure — cell/renderer/latent identity, the exact frozen
    # subtype, the derived public numeric factors (no bins), and the
    # direction; collision and other generator-derived fields stay
    # in their separately labelled strata, never here
    public_factor_disclosure = {
        oid: {
            "cell_id": row["cell_id"],
            "renderer_id": row["renderer_id"],
            "latent_index": row["latent_index"],
            "latent_program_id": row["latent_program_id"],
            "subtype": row["subtype"],
            "public_numeric_values":
                dict(row["public_numeric_values"]),
            "direction": row["direction"],
        }
        for oid, row in sorted(table.items())}
    record = {
        "kind": "routing-dev-extension-selection-v1",
        "config_sha256": CONFIG_SHA256,
        "selector": dict(config),
        "candidate_domain": {
            "first_index": domain_start,
            "last_index": EXTENSION_CONFIG["prefix_k"] - 1},
        "extension_surface_lock_sha256":
            loaded["lock"]["lock_sha256"],
        "direction_buckets": buckets,
        "screened_surplus": surplus,
        "legacy_direction_disclosure": legacy_disclosure,
        "dispositions": dispositions,
        "eligible_common_cells_q3": common_cells,
        "renderer_reversal_diagnostics": reversals,
        "yield_disclosure": yield_disclosure,
        "public_factor_disclosure": public_factor_disclosure,
    }
    record["record_sha256"] = content_sha256(record)
    return record


def verify_extension_selection(loaded: Mapping[str, Any],
                               record: Mapping[str, Any]) -> None:
    """The selection verifier (259_s): the persisted record must
    rehash AND rederive byte-exactly from the locked surface."""
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    if content_sha256(body) != record.get("record_sha256"):
        raise InfrastructureError(
            "extension selection record does not rehash")
    rederived = run_extension_selector(loaded)
    if json.loads(json.dumps(rederived)) != \
            json.loads(json.dumps(dict(record))):
        raise InfrastructureError(
            "extension selection does not rederive from the locked "
            "surface (259_s total-selector gate)")


# --- the tracked runner --------------------------------------------------------

def prepare_extension_launch(*, run_dir: str | Path,
                             _runtime_factory: Callable[[], Any]
                             | None = None,
                             _environment_builder:
                             Callable[[], dict[str, Any]] | None = None
                             ) -> dict[str, Any]:
    """Phase 1: build and persist every prelaunch input exactly once."""
    run_dir = Path(run_dir)
    if run_dir.resolve() != \
            Path(EXTENSION_CONFIG["run_root"]).resolve():
        raise InfrastructureError(
            f"run_dir {run_dir} is not the frozen lifecycle root "
            f"{EXTENSION_CONFIG['run_root']} (262_s)")
    prelaunch = run_dir / "prelaunch"
    if prelaunch.exists():
        raise InfrastructureError(
            f"{prelaunch} exists; a launch is prepared exactly once")
    rt = (_runtime_factory or _default_runtime)()
    try:
        declaration = dev_support.build_dev_declaration(
            rt, tag=EXTENSION_CONFIG["tranche"],
            namespace=EXTENSION_CONFIG["namespace"],
            cohort=extension_cohort(),
            renderers=EXTENSION_CONFIG["renderers"],
            visibility=EXTENSION_CONFIG["visibility"])
    finally:
        rt.close()
    environment = (_environment_builder or _default_environment)()
    manifest = build_extension_launch_manifest(
        declaration=declaration, environment_manifest=environment)
    prelaunch.mkdir(parents=True)
    for name, payload in (("declaration.json", declaration),
                          ("env_manifest.json", environment),
                          ("extension_launch.json", manifest)):
        (prelaunch / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    return manifest


def _load_prelaunch(run_dir: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in _PRELAUNCH_FILES:
        path = run_dir / "prelaunch" / name
        if not path.exists():
            raise InfrastructureError(
                f"{path} is missing — run `prepare` first")
        out[name.split(".")[0]] = json.loads(
            path.read_text(encoding="utf-8"))
    return out


def execute_extension(*, run_dir: str | Path,
                      expected_manifest_sha256: str,
                      expected_head_sha256: str,
                      ledger_path: str | Path = LEDGER_PATH,
                      _runtime_factory: Callable[[], Any] | None = None,
                      _environment_builder:
                      Callable[[], dict[str, Any]] | None = None,
                      _original_surface_dir: str | Path | None = None
                      ) -> dict[str, Any]:
    """Phase 2: fully validate BEFORE the irreversible admission; run
    under the abort handler AFTER it; the overlap gate runs BEFORE
    the new lock is accepted; comparator selection is never invoked."""
    run_dir = Path(run_dir)
    prelaunch = _load_prelaunch(run_dir)
    declaration = prelaunch["declaration"]
    frozen_env = prelaunch["env_manifest"]
    manifest = prelaunch["extension_launch"]

    # --- 1. FULL pre-admission validation ------------------------------
    manifest = validate_extension_launch_manifest(manifest, declaration)
    if manifest["manifest_sha256"] != expected_manifest_sha256:
        raise InfrastructureError(
            "prepared extension-launch manifest is not the externally "
            "frozen one")
    # 262_s: the lifecycle root is identity-bound — copied prelaunch
    # artifacts cannot be executed under a different root
    if run_dir.resolve() != Path(manifest["run_root"]).resolve():
        raise InfrastructureError(
            f"run_dir {run_dir} is not the manifest's identity-bound "
            f"run root {manifest['run_root']} (262_s)")
    if expected_head_sha256 != \
            EXTENSION_CONFIG["lineage"]["parent_entry_sha256"]:
        raise InfrastructureError(
            "expected_head_sha256 must equal the lineage parent "
            "frozen in EXTENSION_CONFIG (260_f Unit A)")
    if dev_support.validate_environment_manifest_binding(frozen_env) \
            != manifest["environment_manifest_sha256"]:
        raise InfrastructureError(
            "persisted environment manifest is not the one the "
            "manifest binds")
    live_env = (_environment_builder or _default_environment)()
    dev_support.validate_environment_manifest_binding(live_env)
    attest_environment(frozen_env, live_env)
    # the original surface must load under the frozen Step-4 lock
    # BEFORE admission — the overlap target and comparator root exist
    original_loaded = load_original_surface(_original_surface_dir)
    surface_dir = run_dir / "surface"
    output_paths = [run_dir / name for name in _OUTPUT_FILES]
    output_paths.append(run_dir / "execute_env_manifest.json")
    for path in [surface_dir, *output_paths]:
        if path.exists():
            raise InfrastructureError(
                f"{path} exists — outputs are preflighted before "
                "admission")

    # --- 2. ADMIT (irreversible from here) -----------------------------
    frozen = tranche_freeze()
    entry = {
        "kind": "support_extension",
        "question": frozen["question"],
        "motivating_evidence":
            EXTENSION_CONFIG["lineage"]["motivating_evidence"],
        "freeze": {
            "extension_launch_sha256": manifest["manifest_sha256"],
            "config_sha256": CONFIG_SHA256,
            "freeze_sha256": frozen["freeze_sha256"],
            "original_surface_lock_sha256":
                manifest["original_surface_lock_sha256"],
            "scientific_design_sha256":
                manifest["scientific_design_sha256"],
        },
        "parent": EXTENSION_CONFIG["lineage"]["parent_entry_sha256"],
        "budget_allocated_gpu_hours": manifest["budget_gpu_hours"],
        "outcome_informed":
            EXTENSION_CONFIG["lineage"]["outcome_informed"],
        "cohort_selection": "outcome_blind",
    }
    admitted = admit_and_append_launch(entry, expected_head_sha256,
                                       ledger_path,
                                       launch_manifest=manifest)
    head = admitted["entry_sha256"]
    started = time.monotonic()
    deadline = started \
        + EXTENSION_CONFIG["ceiling_gpu_hours"] * 3600.0

    # --- 3. Post-admission work under the abort handler ----------------
    try:
        _persist_verified(run_dir / "execute_env_manifest.json",
                          live_env)
        rt = (_runtime_factory or _default_runtime)()
        try:
            dev_support.materialize_dev_support(
                rt, declaration, surface_dir,
                launch_manifest=manifest,
                environment_manifest=frozen_env,
                expected_manifest_sha256=expected_manifest_sha256,
                ledger_path=ledger_path, expected_head_sha256=head,
                _launch_validator=validate_extension_launch_manifest,
                _admitted_kind="support_extension",
                _admitted_manifest_key="extension_launch_sha256",
                deadline_monotonic=deadline)
        finally:
            rt.close()
        # 257_s B3: the overlap gate runs BEFORE the new lock is
        # accepted
        original_dir = Path(_original_surface_dir
                            or EXTENSION_CONFIG["original_surface_dir"])
        overlap_rows = verify_overlap_equality(surface_dir,
                                               original_dir)
        lock = dev_support.build_surface_lock(surface_dir)
        loaded = dev_support.load_dev_surface(
            surface_dir, expected_lock_sha256=lock["lock_sha256"])
        selection = run_extension_selector(loaded)
        verify_extension_selection(loaded, selection)
        comparator = immutable_comparator(original_loaded,
                                          lock["lock_sha256"])
        yields = dev_support.direction_yields(loaded["surface"],
                                              loaded["observations"])
        record = {
            "run": EXTENSION_CONFIG["tranche"],
            "surface_dir": str(surface_dir),
            "extension_launch_sha256": manifest["manifest_sha256"],
            "surface_lock_sha256": lock["lock_sha256"],
            "original_surface_lock_sha256":
                manifest["original_surface_lock_sha256"],
            "overlap_rows_verified": overlap_rows,
            "launch_entry_sha256": head,
            "selection_sha256": selection["record_sha256"],
            "comparator_sha256": comparator["record_sha256"],
            "eligible_common_cells_q3":
                selection["eligible_common_cells_q3"],
            "dispositions": selection["dispositions"],
        }
        for name, payload in (("disclosure.json", yields),
                              ("selection.json", selection),
                              ("comparator.json", comparator),
                              ("run_record.json", record)):
            _persist_verified(run_dir / name, payload)
    except BaseException as error:
        measured = round((time.monotonic() - started) / 3600.0, 4)
        append_ledger_entry(
            {"kind": "closeout", "question": frozen["question"],
             "motivating_evidence": "support extension ABORTED",
             "freeze": {
                 "extension_launch_sha256":
                     manifest["manifest_sha256"],
                 "partial_artifact_hashes":
                     _hash_directory(run_dir)},
             "parent": head,
             "budget_allocated_gpu_hours": 0.0,
             "budget_consumed_gpu_hours": measured,
             "closes_entry_sha256": head,
             "terminal_status": "aborted",
             "interpretation": f"{type(error).__name__}: {error}",
             "outcome_informed": True,
             "outcome_pointer": str(run_dir)},
            head, ledger_path)
        raise

    # --- 4. SUCCESS closeout -------------------------------------------
    measured = round((time.monotonic() - started) / 3600.0, 4)
    closeout = append_ledger_entry(
        {"kind": "closeout", "question": frozen["question"],
         "motivating_evidence": "measured support-extension cost",
         "freeze": {
             "surface_lock_sha256": lock["lock_sha256"],
             "run_record_file_sha256":
                 _sha_file(run_dir / "run_record.json"),
             "execute_env_file_sha256":
                 _sha_file(run_dir / "execute_env_manifest.json"),
             "terminal_artifact_hashes": _hash_directory(run_dir),
             "rendered_observations": len(loaded["observations"]),
         },
         "parent": head,
         "budget_allocated_gpu_hours": 0.0,
         "budget_consumed_gpu_hours": measured,
         "closes_entry_sha256": head,
         "terminal_status": "complete",
         "outcome_informed": True,
         "outcome_pointer": str(run_dir / "run_record.json")},
        head, ledger_path)
    return {**record, "measured_gpu_hours": measured,
            "closeout_entry_sha256": closeout["entry_sha256"],
            "ledger_head": closeout["entry_sha256"]}


def verify_extension_outputs(run_dir: str | Path,
                             closeout: Mapping[str, Any],
                             original_surface_dir: str | Path | None
                             = None) -> None:
    """Post-hoc terminal verification: exact inventory, surface
    reload under the closeout's lock, overlap gate re-run, selection
    rederivation, and the immutable comparator re-verified against
    the ORIGINAL lock."""
    run_dir = Path(run_dir)
    freeze = closeout.get("freeze", {})
    if closeout.get("terminal_status") == "aborted":
        bound = freeze.get("partial_artifact_hashes")
        if not bound:
            raise InfrastructureError(
                "aborted closeout carries an empty partial inventory")
        if _hash_directory(run_dir) != dict(bound):
            raise InfrastructureError(
                "partial evidence is not exactly the bound inventory")
        return
    if closeout.get("terminal_status") != "complete":
        raise InfrastructureError("not a terminal closeout")
    bound = freeze.get("terminal_artifact_hashes")
    if not bound or _hash_directory(run_dir) != dict(bound):
        raise InfrastructureError(
            "terminal evidence is not exactly the bound inventory")
    for name, key in (("run_record.json", "run_record_file_sha256"),
                      ("execute_env_manifest.json",
                       "execute_env_file_sha256")):
        if _sha_file(run_dir / name) != freeze.get(key):
            raise InfrastructureError(
                f"{name} does not match the closeout binding")
    record = json.loads(
        (run_dir / "run_record.json").read_text("utf-8"))
    if record.get("run") != EXTENSION_CONFIG["tranche"] \
            or record.get("surface_lock_sha256") != \
            freeze.get("surface_lock_sha256"):
        raise InfrastructureError(
            "run record does not match the extension closeout")
    loaded = dev_support.load_dev_surface(
        run_dir / "surface",
        expected_lock_sha256=freeze.get("surface_lock_sha256"))
    if freeze.get("rendered_observations") != \
            len(loaded["observations"]):
        raise InfrastructureError(
            "closeout rendered_observations != the authenticated "
            "population")
    original_dir = Path(original_surface_dir
                        or EXTENSION_CONFIG["original_surface_dir"])
    overlap = verify_overlap_equality(run_dir / "surface",
                                      original_dir)
    if overlap != record.get("overlap_rows_verified"):
        raise InfrastructureError(
            "overlap row count does not match the run record")
    selection = json.loads(
        (run_dir / "selection.json").read_text("utf-8"))
    verify_extension_selection(loaded, selection)
    if selection["record_sha256"] != record.get("selection_sha256"):
        raise InfrastructureError(
            "selection record does not match the run record")
    comparator = json.loads(
        (run_dir / "comparator.json").read_text("utf-8"))
    body = {k: v for k, v in comparator.items()
            if k != "record_sha256"}
    if content_sha256(body) != comparator.get("record_sha256") \
            or comparator.get("record_sha256") != \
            record.get("comparator_sha256"):
        raise InfrastructureError(
            "comparator record does not rehash or does not match the "
            "run record")
    if comparator.get("reselected") is not False \
            or comparator.get("c_fixed_dev") != 2 \
            or comparator.get("original_surface_lock_sha256") != \
            EXTENSION_CONFIG["original_surface_lock_sha256"]:
        raise InfrastructureError(
            "comparator is not the immutable Step-4 worker (257_s B3)")
    original_loaded = load_original_surface(original_surface_dir)
    reverified = immutable_comparator(
        original_loaded, freeze.get("surface_lock_sha256"))
    if reverified != comparator:
        raise InfrastructureError(
            "comparator does not rederive from the ORIGINAL locked "
            "surface (257_s B3)")


def main(argv: list[str] | None = None) -> int:
    """The reproducible entry points (262_s): every launch argument
    is a reviewed hash — nothing defaults to trust."""
    import argparse
    parser = argparse.ArgumentParser(prog="extension_run")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    execute = sub.add_parser("execute")
    execute.add_argument("--expected-manifest-sha256", required=True)
    execute.add_argument("--expected-head-sha256", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--closeout-entry-sha256", required=True)
    args = parser.parse_args(argv)
    run_root = EXTENSION_CONFIG["run_root"]
    if args.command == "prepare":
        manifest = prepare_extension_launch(run_dir=run_root)
        print(json.dumps({"manifest_sha256":
                          manifest["manifest_sha256"]}, indent=1))
        return 0
    if args.command == "execute":
        result = execute_extension(
            run_dir=run_root,
            expected_manifest_sha256=args.expected_manifest_sha256,
            expected_head_sha256=args.expected_head_sha256)
        print(json.dumps({k: result[k] for k in
                          ("surface_lock_sha256", "measured_gpu_hours",
                           "closeout_entry_sha256", "ledger_head")},
                         indent=1))
        return 0
    from .ledger import ledger_head, verify_ledger_head
    entries = verify_ledger_head(ledger_head(LEDGER_PATH), LEDGER_PATH)
    matches = [e for e in entries
               if e.get("entry_sha256") == args.closeout_entry_sha256]
    if not matches:
        raise InfrastructureError(
            f"no ledger entry {args.closeout_entry_sha256!r}")
    verify_extension_outputs(run_root, matches[0])
    print(json.dumps({"verdict": "PASS"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
