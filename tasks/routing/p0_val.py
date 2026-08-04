"""P0 precursors, Unit V — the `routing_dev_val` outcome-blind
cohort freeze, the val surface tranche, and the val lock (the
SIGNED precursors plan 326_f/328_f/330_f §1; repaired per 332_s).

V1 (CPU): the outcome-blind cohort — six cells equally, the
DETERMINISTIC latent prefix 0–4 per cell, ALL THREE renderers (90
observations) under the frozen natural-mixture definition — plus
the COMPLETE evaluation identity: the full-digest
common-random-number seed derivation (330_f §1 / 332_s P1-4: the
complete SHA-256 integer mod 2^31, slots 0..7, NO checkpoint
index; the 720-seed schedule hash is frozen), the FULL sampling
options, the ordered observation list, batching, and the
latent-level descriptive framing.

V2 (GPU, <= 0.35 GPU-h, deadline-ENFORCED): `prepare_val_launch`
/ `execute_val_run` — the two-phase pattern with the dedicated
`val_materialization` ledger admission (332_s P0-1), the
closed-schema val-launch manifest (source digest recomputed; the
signed tranche-freeze hash bound), the frozen C2 lineage parent
enforced, `materialize_dev_support` under the budget deadline,
the post-run semantic-overlap gate against BOTH the training and
cycle populations, and the val-specific terminal verifier before
the success closeout.

V3 (CPU): `build_val_lock` — loads and fully verifies the
materialized surface FIRST (332_s P1-3), checks the surface IS the
frozen cohort, binds the canonical natural-mixture weights (332_s
P1-5) and the overlap-gate result, and writes once.
`load_val_lock` REDERIVES the cohort/evaluation identity/weights
from the frozen config under a closed schema and can authenticate
the underlying surface bytes.

Never-trained-on is STRUCTURAL: the P0 trainer consumes only the
pinned mixture schedule; `routing_dev_val` appears in no training
schedule. All val evidence is development-only."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from tasks.conductor.types import (
    RENDERER_IDS,
    InfrastructureError,
)

from . import dev_support
from .charter import (
    canonical_json,
    content_sha256,
    routing_execution_digest,
)
from .ledger import (
    LEDGER_PATH,
    admit_and_append_launch,
    append_ledger_entry,
)
from .p0_launch import P0_RUNTIME_PROFILE_SHA256
from .support_run import (
    _default_environment,
    _default_runtime,
    _hash_directory,
    _persist_verified,
    _sha_file,
    attest_environment,
)

DRIVER = "tasks/routing/p0_val.py"
VAL_RUN_ROOT = "runs/routing-dev/val-surface-v1"
VAL_LAUNCH_KIND = "routing-dev-val-launch-v1"
VAL_LOCK_KIND = "routing-dev-val-lock-v1"

VAL_CELLS = ("code_atomic", "fork_join", "lookup_atomic",
             "lookup_math", "math_atomic", "math_code")

VAL_CONFIG: dict[str, Any] = {
    "tranche": "routing-dev-val-surface-v1",
    "namespace": "routing_dev_val",
    # the outcome-blind DETERMINISTIC prefix — no selection function
    "cohort": {cell: [0, 1, 2, 3, 4] for cell in VAL_CELLS},
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
        "domain": "p0_val_eval",
        "base_seed": 20260804,
        "seed_rule": ("int(sha256(domain || base_seed || "
                      "observation_id || completion_slot), 16) mod "
                      "2^31 over the COMPLETE digest (332_s P1-4); "
                      "slots 0..7 only; NO checkpoint index (common "
                      "random numbers, 330_f §1) — the checkpoint "
                      "lives in provenance only"),
        # the FULL sampling identity (332_s): the eval runner must
        # construct generation from THIS record, nothing implicit
        "sampling": {"do_sample": True, "temperature": 1.0,
                     "top_p": 1.0, "top_k": None,
                     "repetition_penalty": 1.0,
                     "max_new_tokens": 128, "group_size": 8},
        "runtime_profile_sha256": P0_RUNTIME_PROFILE_SHA256,
        "batching": ("canonical (cell, latent index, renderer) "
                     "order; one 8-completion group per observation "
                     "per checkpoint; the ordered observation list "
                     "is bound in the val lock"),
        "framing": ("paired latent-level DESCRIPTIVE evidence "
                    "(5 clusters per cell) — never completion-level "
                    "precision claims"),
        "held_out_meaning": (
            "validation tests HELD-OUT LATENT/RESOURCE INSTANCES, "
            "not template-disjoint prompts (334_s): "
            "alpha-normalized latent/resource semantics are the "
            "HARD disjointness requirement; alpha-normalized "
            "prompt-template overlap with the training population "
            "is DISCLOSED, and repeated-template vs novel-template "
            "results MAY be reported descriptively"),
    },
    "never_trained_on": (
        "structural — the P0 trainer consumes only the pinned "
        "mixture schedule (record_sha256 135a72bf4deb77048371074636"
        "d88ffebf6bd07d1c00ae349b6fcee221975b3f); routing_dev_val "
        "appears in no training schedule"),
    "development_only": True,
    "search_cap": 90,
    "budget_gpu_hours": 0.35,
    "run_root": VAL_RUN_ROOT,
    "predictions": {
        "identity_intersection_all_namespaces": 0,
        "alpha_normalized_semantic_overlap": 0,
        "alpha_normalized_prompt_overlap_disclosed": (
            "measured pre-launch: 21 unique val-training template "
            "collisions affecting 39/90 val observations; 15 "
            "val-cycle affecting 30/90; 30 cycle-training — "
            "DISCLOSED, not gated (334_s)"),
        "complete_4S_surfaces": ("every observation's full 4^S "
                                 "assignment space authenticated"),
        "measured_cost_gpu_hours": ("0.05-0.15 (calibration: the "
                                    "extension materialized 864 "
                                    "observations in 0.4934)"),
    },
    "lineage": {
        "parent_entry_sha256":
            "2bf50c1e5b31a7acf28dc9391ea4fc021a82cacb20906692558c"
            "f36174266fbe",
        "outcome_informed": False,
        "motivating_evidence": "330_f-signed precursors plan Unit V",
    },
}
VAL_CONFIG_SHA256 = \
    "73376e07cf83197bb210093bb31a38f5dbf4e17101eb6d61cc273b899a6deccf"

# the complete frozen 720-seed schedule identity (332_s P1-4):
# content hash over [(observation_id, slot, seed)] in canonical
# order — recomputed and enforced by `seed_schedule()`
VAL_SEED_SCHEDULE_SHA256 = \
    "7f5f65181e41b8011e2a5ccd735dc287ce6b1fd77e948d004ac4e9a1d6035215"

_VAL_LAUNCH_KEYS = frozenset({
    "kind", "declaration_sha256", "namespace",
    "worker_visible_fingerprint", "runtime_profile_fingerprint",
    "worker_pool_fingerprint", "request_contract", "cache_identity",
    "val_config_sha256", "val_freeze_sha256", "search_cap",
    "budget_gpu_hours", "driver", "run_root", "execution_root",
    "lineage_parent_sha256",
    "routing_source_sha256", "environment_manifest_sha256",
    "support", "scientific_design_sha256",
})

_VAL_DESIGN_FIELDS = (
    "declaration_sha256", "namespace", "worker_visible_fingerprint",
    "runtime_profile_fingerprint", "worker_pool_fingerprint",
    "request_contract", "cache_identity", "val_config_sha256",
    "val_freeze_sha256", "search_cap",
)


def _validated_config() -> dict[str, Any]:
    if content_sha256(VAL_CONFIG) != VAL_CONFIG_SHA256:
        raise InfrastructureError(
            "VAL_CONFIG was mutated after import")
    return VAL_CONFIG


# --- V1: the outcome-blind cohort + evaluation identity ------------------------

def val_cohort_observations() -> list[dict[str, Any]]:
    """The cohort regenerated from the frozen generator in canonical
    (cell, index, renderer) order — 90 observations."""
    config = _validated_config()
    return dev_support.dev_cohort_observations(
        config["namespace"], config["cohort"], config["renderers"],
        config["visibility"])


def seed_for_completion(observation_id: str, completion_slot: int,
                        *, domain: str | None = None,
                        base_seed: int | None = None) -> int:
    """The frozen common-random-number derivation (330_f §1; 332_s
    P1-4): the COMPLETE SHA-256 digest as an integer, mod 2^31.
    The same (observation, slot) draws at EVERY checkpoint — the
    checkpoint index is provenance, never RNG input. Slots are
    bounded by the frozen group size (0..7)."""
    config = _validated_config()
    evaluation = config["evaluation"]
    domain = domain or evaluation["domain"]
    base = base_seed if base_seed is not None \
        else evaluation["base_seed"]
    group_size = evaluation["sampling"]["group_size"]
    if not isinstance(completion_slot, int) \
            or isinstance(completion_slot, bool) \
            or not 0 <= completion_slot < group_size:
        raise InfrastructureError(
            f"completion_slot must be an integer in "
            f"[0, {group_size}) (332_s)")
    payload = f"{domain}||{base}||{observation_id}" \
              f"||{completion_slot}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest(), 16) % (2 ** 31)


def seed_schedule() -> list[tuple[str, int, int]]:
    """The complete frozen 720-entry seed schedule in canonical
    order, enforced against the reviewed pin."""
    config = _validated_config()
    group_size = config["evaluation"]["sampling"]["group_size"]
    schedule = [
        (obs["observation_id"], slot,
         seed_for_completion(obs["observation_id"], slot))
        for obs in val_cohort_observations()
        for slot in range(group_size)]
    digest = content_sha256([list(entry) for entry in schedule])
    if digest != VAL_SEED_SCHEDULE_SHA256:
        raise InfrastructureError(
            "the derived seed schedule does not match the frozen "
            "schedule pin (332_s P1-4)")
    return schedule


# identity-only fields normalized away (330_f §5); `public_params`
# is the non-serializable factor OBJECT whose content is already
# fully present in `params`/`factor_assignment`/`public_manifest`
_LATENT_NONSEMANTIC_FIELDS = frozenset({
    "latent_program_id", "namespace", "latent_index", "seed",
    "public_params"})

# 334_s P1-1: opaque resource handles (R-8V9 style) are
# identity-only ALIASES — they must be canonicalized before any
# overlap claim is substantive
_RESOURCE_HANDLE_RE = re.compile(r"R-[0-9A-Z]{3}")


def alpha_normalize(text: str) -> str:
    """Replace each opaque resource handle consistently with R0,
    R1, ... in order of first appearance (334_s P1-1)."""
    mapping: dict[str, str] = {}

    def _sub(match: re.Match) -> str:
        handle = match.group(0)
        if handle not in mapping:
            mapping[handle] = f"R{len(mapping)}"
        return mapping[handle]

    return _RESOURCE_HANDLE_RE.sub(_sub, text)


def _handle_mapping(latent: Mapping[str, Any]) -> dict[str, str]:
    """336_s P1-1: the alpha mapping derives from the
    `public_manifest` ORDER (the semantic presentation order) —
    never from serialization order, which depends on the original
    handle spelling."""
    mapping: dict[str, str] = {}
    for handle in latent.get("public_manifest", ()):
        if isinstance(handle, str) \
                and _RESOURCE_HANDLE_RE.fullmatch(handle) \
                and handle not in mapping:
            mapping[handle] = f"R{len(mapping)}"
    return mapping


def _replace_handles(obj: Any, mapping: Mapping[str, str]) -> Any:
    """Recursively replace KNOWN handles in keys and values BEFORE
    canonical serialization (336_s P1-1); an undeclared handle
    refuses — every semantic handle must be in the public
    manifest."""
    if isinstance(obj, str):
        def _sub(match: re.Match) -> str:
            handle = match.group(0)
            if handle not in mapping:
                raise InfrastructureError(
                    f"handle {handle} appears in the semantic body "
                    "but not in the public manifest — the alpha "
                    "mapping would be unstable (336_s P1-1)")
            return mapping[handle]
        return _RESOURCE_HANDLE_RE.sub(_sub, obj)
    if isinstance(obj, Mapping):
        return {_replace_handles(k, mapping):
                _replace_handles(v, mapping)
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_replace_handles(item, mapping) for item in obj]
    return obj


def normalized_latent_semantics(latent: Mapping[str, Any]) -> str:
    """The latent's SEMANTIC content with namespace/identity-only
    fields removed (identity-derived `seed` included) AND resource
    handles ALPHA-NORMALIZED handle-INVARIANTLY (336_s P1-1: the
    mapping derives from public-manifest order and is applied
    recursively to keys and values BEFORE canonical serialization
    — a consistent renaming of every handle cannot change this
    hash)."""
    body = {k: v for k, v in latent.items()
            if k not in _LATENT_NONSEMANTIC_FIELDS}
    return content_sha256(
        _replace_handles(body, _handle_mapping(latent)))


def semantic_overlap_report(
        observations: list[Mapping[str, Any]],
        reference_observations: list[Mapping[str, Any]]
        ) -> dict[str, Any]:
    """The substantive overlap checks (330_f §5; 334_s): the HARD
    gate is alpha-normalized latent/resource SEMANTIC disjointness
    (must be empty); alpha-normalized PROMPT-TEMPLATE overlap is
    DISCLOSED — totals, per-cell stratification, and the FROZEN
    collision membership (336_s) — never gated. Rendered prompts
    carry no identity strings (verified); both sides must be
    non-empty (the check must have teeth)."""
    from tasks.conductor import program
    from tasks.conductor.policy import policy_messages

    def _prompt_of(obs: Mapping[str, Any]) -> str:
        latent = obs["latent"]
        inst = obs.get("instance") or program.render_instance(
            latent, obs["renderer_id"],
            obs["observation_id"].split(":")[5])
        steps = [{"subtask": s["subtask"], "resource": s["resource"],
                  "access": s["access"]}
                 for s in program.workflow_steps(latent)]
        prompt = policy_messages(inst, steps)[1]["content"]
        oid = obs["observation_id"]
        if oid in prompt or latent["namespace"] in prompt:
            raise InfrastructureError(
                f"{oid}: the rendered prompt embeds an identity "
                "string — the prompt-overlap check would be "
                "tautological")
        return prompt

    semantics = {normalized_latent_semantics(o["latent"])
                 for o in observations}
    reference_semantics = {normalized_latent_semantics(o["latent"])
                           for o in reference_observations}
    prompts = [alpha_normalize(_prompt_of(o))
               for o in observations]
    reference_prompts = {alpha_normalize(_prompt_of(o))
                         for o in reference_observations}
    if not (semantics and reference_semantics and prompts
            and reference_prompts):
        raise InfrastructureError(
            "semantic-overlap check requires non-empty populations")
    collisions = set(prompts) & reference_prompts
    affected_ids = sorted(
        obs["observation_id"]
        for obs, prompt in zip(observations, prompts)
        if prompt in reference_prompts)
    affected_by_cell: dict[str, int] = {}
    for obs, prompt in zip(observations, prompts):
        if prompt in reference_prompts:
            affected_by_cell[obs["cell_id"]] = \
                affected_by_cell.get(obs["cell_id"], 0) + 1
    report = {
        # the HARD requirement (334_s): alpha-normalized
        # latent/resource semantics are disjoint
        "semantic_intersection":
            len(semantics & reference_semantics),
        # DISCLOSED, not gated (334_s): validation tests held-out
        # latent/resource instances, not template-disjoint prompts.
        # 336_s: the collision MEMBERSHIP is frozen and stratified
        # by cell (template reuse is strongly cell-confounded) —
        # any repeated-vs-novel descriptive report uses THIS frozen
        # membership.
        "alpha_prompt_collisions": len(collisions),
        "alpha_prompt_affected_candidates":
            sum(1 for p in prompts if p in reference_prompts),
        "affected_candidate_ids": affected_ids,
        "affected_by_cell": dict(sorted(
            affected_by_cell.items())),
        "candidate_observations": len(prompts),
        "candidate_semantics": len(semantics),
        "reference_semantics": len(reference_semantics),
    }
    if report["semantic_intersection"] != 0:
        raise InfrastructureError(
            f"population overlap is not empty: {report} — the val "
            "cohort must be semantically disjoint under alpha "
            "normalization (330_f §5; 334_s)")
    return report


def _regenerate_latent(obs: Mapping[str, Any]) -> dict[str, Any]:
    from tasks.conductor import program
    from tasks.conductor.profiles import DEFAULT_PROFILE
    oid = obs["observation_id"]
    return program.generate_latent(
        obs["cell_id"], oid.split(":")[1], int(oid.split(":")[2]),
        DEFAULT_PROFILE).latent


def cycle_cohort_observations() -> list[dict[str, Any]]:
    """The PLANNED Unit-Y cycle cohort (same shape, namespace
    routing_dev_cycle) — regenerated here ONLY for the three-way
    overlap gate; its own freeze is Unit Y."""
    config = _validated_config()
    return dev_support.dev_cohort_observations(
        "routing_dev_cycle", config["cohort"], config["renderers"],
        config["visibility"])


def three_way_overlap_reports(
        training_observations: list[Mapping[str, Any]]
        ) -> dict[str, Any]:
    """332_s: the signed plan's checks across training, validation
    AND cycle populations — all pairwise intersections empty."""
    val_obs = val_cohort_observations()
    cycle_obs = cycle_cohort_observations()
    return {
        "val_vs_training": semantic_overlap_report(
            val_obs, training_observations),
        "val_vs_cycle": semantic_overlap_report(val_obs, cycle_obs),
        "cycle_vs_training": semantic_overlap_report(
            cycle_obs, training_observations),
    }


def val_tranche_freeze() -> dict[str, Any]:
    """The preregistered V1 record the reviewer signs BEFORE any
    GPU launch: the config, the regenerated cohort identities, the
    seed-schedule pin, the planned execution volume, and the
    falsifiable predictions."""
    from tasks.conductor import oracle
    config = _validated_config()
    observations = val_cohort_observations()
    planned = sum(
        len(oracle.enumerate_assignments(obs["num_nodes"]))
        * obs["num_nodes"] for obs in observations)
    body = {
        "kind": "p0_val_tranche",
        "question": ("Unit V: the outcome-blind routing_dev_val "
                     "cohort — natural mixture, never trained on — "
                     "with complete authenticated 4^S surfaces, "
                     "locked as the P0 checkpoint-evaluation "
                     "population"),
        "motivation": "330_f-signed precursors plan §1",
        "config": config,
        "config_sha256": VAL_CONFIG_SHA256,
        "seed_schedule_sha256": VAL_SEED_SCHEDULE_SHA256,
        "observation_ids": [obs["observation_id"]
                            for obs in observations],
        "observations_total": len(observations),
        "planned_step_executions": planned,
        "development_only": True,
    }
    body["freeze_sha256"] = content_sha256(body)
    return body


# --- V2: the launch (two-phase, val-specific manifest) -------------------------

def _require_frozen_cohort_declaration(
        declaration: Mapping[str, Any]) -> None:
    """334_s P1-2: the ONE cohort validator, shared by the builder
    AND the revalidation boundary — the declaration must BE the
    frozen val cohort, down to the regenerated observation rows."""
    from tasks.conductor import oracle
    config = _validated_config()
    dev_support.validate_dev_cohort(
        declaration["namespace"], declaration["cohort"],
        declaration["renderers"], declaration["visibility"])
    if declaration["namespace"] != config["namespace"] \
            or declaration["cohort"] != config["cohort"] \
            or declaration["renderers"] != config["renderers"] \
            or declaration["visibility"] != config["visibility"]:
        raise InfrastructureError(
            "the declaration is not the frozen val cohort")
    for cell, indices in declaration["cohort"].items():
        if sorted(indices) != list(range(len(indices))):
            raise InfrastructureError(
                f"{cell}: declared indices are not the "
                "outcome-blind prefix 0..k-1 (211_f §4)")
    expected_rows = [
        {"observation_id": o["observation_id"],
         "cell_id": o["cell_id"],
         "renderer_id": o["renderer_id"],
         "num_nodes": o["num_nodes"],
         "assignments": len(oracle.enumerate_assignments(
             o["num_nodes"]))}
        for o in val_cohort_observations()]
    if declaration["observations"] != expected_rows:
        raise InfrastructureError(
            "the declaration's observation rows are not the "
            "regenerated frozen cohort (334_s P1-2)")
    total = len(declaration["observations"])
    if total > config["search_cap"]:
        raise InfrastructureError(
            f"declaration screens {total} rendered observations, "
            f"above the frozen cap {config['search_cap']}")


def build_val_launch_manifest(*, declaration: Mapping[str, Any],
                              environment_manifest: Mapping[str, Any],
                              execution_root: str | Path
                              ) -> dict[str, Any]:
    """The ONE pre-launch record for the val tranche: no probe rule
    (nothing is selected from this surface); the outcome-blind
    prefix check is retained; the manifest binds the frozen
    VAL_CONFIG identity, the SIGNED tranche-freeze hash (332_s
    P1-7), the declaration, the driver digest, the environment
    bytes, the search cap, and the budget."""
    config = _validated_config()
    _require_frozen_cohort_declaration(declaration)
    digest = routing_execution_digest(DRIVER)
    manifest = {
        "kind": VAL_LAUNCH_KIND,
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
        "val_config_sha256": VAL_CONFIG_SHA256,
        "val_freeze_sha256": val_tranche_freeze()["freeze_sha256"],
        "search_cap": config["search_cap"],
        "budget_gpu_hours": config["budget_gpu_hours"],
        "driver": DRIVER,
        "run_root": config["run_root"],
        # 336_s P1-3: the ACTUAL resolved execution root is bound
        # (attempt identity — OUTSIDE the scientific-design hash,
        # so an aborted retry preserves the design)
        "execution_root": str(Path(execution_root).resolve()),
        # 336_s P1-2: the frozen initial parent is part of the
        # validated launch contract, enforced at LEDGER admission
        "lineage_parent_sha256":
            config["lineage"]["parent_entry_sha256"],
        "routing_source_sha256": digest["routing_source_sha256"],
        "environment_manifest_sha256":
            dev_support.validate_environment_manifest_binding(
                environment_manifest),
        "support": config["tranche"],
    }
    manifest["scientific_design_sha256"] = content_sha256(
        {field: manifest[field] for field in _VAL_DESIGN_FIELDS})
    manifest["manifest_sha256"] = content_sha256(
        {k: v for k, v in manifest.items()
         if k != "manifest_sha256"})
    return manifest


def validate_val_launch_manifest(manifest: Mapping[str, Any],
                                 declaration: Mapping[str, Any],
                                 *, recompute: bool = True
                                 ) -> dict[str, Any]:
    """The strict CLOSED-SCHEMA revalidation boundary (332_s P1-7)
    consumed by `materialize_dev_support` and the persisted-launch
    loader: exact key set, rehash, design rehash, declaration and
    config bindings, the signed tranche-freeze hash, and (with
    `recompute`) the source digest recomputed from the tree."""
    if not isinstance(manifest, Mapping) \
            or set(manifest) != _VAL_LAUNCH_KEYS | \
            {"manifest_sha256"}:
        raise InfrastructureError(
            "val-launch manifest keys do not match the closed "
            "schema (332_s)")
    if manifest["kind"] != VAL_LAUNCH_KIND:
        raise InfrastructureError(
            f"unknown val launch kind {manifest['kind']!r}")
    body = {k: v for k, v in manifest.items()
            if k != "manifest_sha256"}
    if content_sha256(body) != manifest["manifest_sha256"]:
        raise InfrastructureError("val launch manifest does not "
                                  "rehash")
    if manifest["scientific_design_sha256"] != content_sha256(
            {field: manifest[field]
             for field in _VAL_DESIGN_FIELDS}):
        raise InfrastructureError(
            "val scientific-design identity does not recompute")
    if manifest["declaration_sha256"] != \
            content_sha256(dict(declaration)):
        raise InfrastructureError(
            "val launch manifest does not bind this declaration")
    if manifest["val_config_sha256"] != VAL_CONFIG_SHA256:
        raise InfrastructureError(
            "val launch manifest does not bind the frozen "
            "VAL_CONFIG")
    if manifest["val_freeze_sha256"] != \
            val_tranche_freeze()["freeze_sha256"]:
        raise InfrastructureError(
            "val launch manifest does not bind the signed "
            "tranche freeze (332_s)")
    # 334_s P1-2: every configuration-owned field is REDERIVED from
    # the frozen config — a correctly re-signed manifest carrying a
    # different budget/cap/driver/root/tag refuses here
    config = _validated_config()
    for key, frozen_value in (
            ("budget_gpu_hours", config["budget_gpu_hours"]),
            ("search_cap", config["search_cap"]),
            ("support", config["tranche"]),
            ("driver", DRIVER),
            ("run_root", config["run_root"]),
            ("lineage_parent_sha256",
             config["lineage"]["parent_entry_sha256"]),
            ("namespace", config["namespace"])):
        if manifest[key] != frozen_value:
            raise InfrastructureError(
                f"val launch manifest {key} = {manifest[key]!r} "
                f"diverges from the frozen configuration value "
                f"{frozen_value!r} (334_s P1-2)")
    _require_frozen_cohort_declaration(declaration)
    for key in ("worker_visible_fingerprint",
                "runtime_profile_fingerprint",
                "worker_pool_fingerprint", "request_contract",
                "cache_identity"):
        if manifest[key] != declaration[key]:
            raise InfrastructureError(
                f"val launch manifest {key} does not match the "
                "declaration")
    if recompute:
        digest = routing_execution_digest(DRIVER)
        if manifest["routing_source_sha256"] != \
                digest["routing_source_sha256"]:
            raise InfrastructureError(
                "val launch manifest source digest does not match "
                "the tree (332_s P1-7)")
    return dict(manifest)


def prepare_val_launch(*, run_dir: str | Path = VAL_RUN_ROOT,
                       _runtime_factory: Callable[[], Any]
                       | None = None,
                       _environment_builder:
                       Callable[[], dict[str, Any]] | None = None
                       ) -> dict[str, Any]:
    """Phase 1: build and persist every prelaunch input exactly
    once. The prepared manifest/environment/declaration hashes go
    to the narrow prelaunch review (332_s P1-7); `execute_val_run`
    then REQUIRES the reviewed manifest hash."""
    config = _validated_config()
    run_dir = Path(run_dir)
    prelaunch = run_dir / "prelaunch"
    if prelaunch.exists():
        raise InfrastructureError(
            f"{prelaunch} exists; a launch is prepared exactly once")
    rt = (_runtime_factory or _default_runtime)()
    try:
        declaration = dev_support.build_dev_declaration(
            rt, tag=config["tranche"], namespace=config["namespace"],
            cohort=config["cohort"], renderers=config["renderers"],
            visibility=config["visibility"])
    finally:
        rt.close()
    environment = (_environment_builder or _default_environment)()
    manifest = build_val_launch_manifest(
        declaration=declaration, environment_manifest=environment,
        execution_root=run_dir)
    prelaunch.mkdir(parents=True)
    for name, payload in (("declaration.json", declaration),
                          ("env_manifest.json", environment),
                          ("val_launch.json", manifest),
                          ("val_freeze.json", val_tranche_freeze())):
        (prelaunch / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    return manifest


def execute_val_run(*, run_dir: str | Path = VAL_RUN_ROOT,
                    expected_manifest_sha256: str,
                    expected_head_sha256: str | None,
                    question: str, motivating_evidence: str,
                    ledger_path: str | Path = LEDGER_PATH,
                    _runtime_factory: Callable[[], Any]
                    | None = None,
                    _environment_builder:
                    Callable[[], dict[str, Any]] | None = None
                    ) -> dict[str, Any]:
    """Phase 2: full validation BEFORE the irreversible admission
    (kind `val_materialization`, 332_s P0-1); materialization under
    the ENFORCED budget deadline (332_s P1-6); the surface lock;
    the three-way overlap gate; the val lock; the terminal
    verifier; then the success closeout. The FIRST launch is
    admitted only on the frozen C2 lineage parent; a retry only
    after an aborted-closed identical-design attempt (334_s P1-3;
    the ledger admission block enforces the same rules
    authoritatively)."""
    config = _validated_config()
    # --- 0. lineage + retry admission state (334_s P1-3), BEFORE
    # any file access: first launch ONLY from the frozen C2 head;
    # never after an open or completed attempt. (Design equality
    # for an aborted retry is checked after the manifest loads;
    # the ledger admission block re-enforces everything.)
    from .ledger import verify_ledger_head
    chain = verify_ledger_head(expected_head_sha256, ledger_path)
    prior = [e for e in chain if e["kind"] == "val_materialization"]
    if not prior:
        if expected_head_sha256 != \
                config["lineage"]["parent_entry_sha256"]:
            raise InfrastructureError(
                "the FIRST val launch is admitted on the frozen "
                "lineage parent (the C2 closeout head) — a "
                "different head refuses (334_s P1-3)")
    else:
        closed = {e.get("closes_entry_sha256"): e for e in chain
                  if e["kind"] == "closeout"}
        for attempt in prior:
            closeout = closed.get(attempt["entry_sha256"])
            if closeout is None:
                raise InfrastructureError(
                    "a prior val attempt is OPEN — no new launch "
                    "(334_s P1-3)")
            if closeout.get("terminal_status") == "complete":
                raise InfrastructureError(
                    "a completed val materialization exists — a "
                    "second launch is never a retry (334_s P1-3)")
    run_dir = Path(run_dir)
    prelaunch = run_dir / "prelaunch"
    declaration = json.loads(
        (prelaunch / "declaration.json").read_text("utf-8"))
    frozen_env = json.loads(
        (prelaunch / "env_manifest.json").read_text("utf-8"))
    manifest = json.loads(
        (prelaunch / "val_launch.json").read_text("utf-8"))

    # --- 1. full pre-admission validation --------------------------
    manifest = validate_val_launch_manifest(manifest, declaration)
    if manifest["manifest_sha256"] != expected_manifest_sha256:
        raise InfrastructureError(
            "prepared val-launch manifest is not the externally "
            "frozen one")
    # 336_s P1-3: the manifest binds the ACTUAL execution root;
    # the resolved path must match, and the registered attempt-root
    # rule holds — attempt 1 executes under the frozen run_root,
    # attempt N under run_root + "-rN"
    if str(run_dir.resolve()) != manifest["execution_root"]:
        raise InfrastructureError(
            "the execution directory is not the root the manifest "
            "binds (336_s P1-3)")
    attempt = len(prior) + 1
    required_root = config["run_root"] if attempt == 1 \
        else f"{config['run_root']}-r{attempt}"
    if not manifest["execution_root"].endswith(required_root):
        raise InfrastructureError(
            f"attempt {attempt} must execute under the registered "
            f"attempt root .../{required_root} (336_s P1-3)")
    if dev_support.validate_environment_manifest_binding(frozen_env) \
            != manifest["environment_manifest_sha256"]:
        raise InfrastructureError(
            "persisted environment manifest is not the one the "
            "manifest binds")
    live_env = (_environment_builder or _default_environment)()
    dev_support.validate_environment_manifest_binding(live_env)
    attest_environment(frozen_env, live_env)
    surface_dir = run_dir / "surface"
    outputs = [surface_dir, run_dir / "run_record.json",
               run_dir / "val_lock.json",
               run_dir / "overlap_report.json",
               run_dir / "execute_env_manifest.json"]
    for path in outputs:
        if path.exists():
            raise InfrastructureError(
                f"{path} exists — outputs are preflighted before "
                "admission")

    # --- 2. aborted-retry design equality (334_s P1-3) -------------
    for attempt in prior:
        if attempt["freeze"].get("scientific_design_sha256") \
                != manifest["scientific_design_sha256"]:
            raise InfrastructureError(
                "an aborted-val retry must preserve the "
                "scientific design (334_s P1-3)")

    # --- 3. ADMIT (irreversible from here) -------------------------
    entry = {
        "kind": "val_materialization",
        "question": question,
        "motivating_evidence": motivating_evidence,
        "freeze": {
            "val_launch_sha256": manifest["manifest_sha256"],
            "val_config_sha256": VAL_CONFIG_SHA256,
            "val_freeze_sha256": manifest["val_freeze_sha256"],
            "scientific_design_sha256":
                manifest["scientific_design_sha256"],
        },
        # 334_s P1-3: the ACTUAL lineage parent is persisted
        "parent": expected_head_sha256,
        "budget_allocated_gpu_hours": manifest["budget_gpu_hours"],
        "outcome_informed": False,
        "cohort_selection": "outcome_blind",
    }
    admitted = admit_and_append_launch(entry, expected_head_sha256,
                                       ledger_path,
                                       launch_manifest=manifest)
    head = admitted["entry_sha256"]
    started = time.monotonic()
    deadline = started + manifest["budget_gpu_hours"] * 3600.0

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
                _launch_validator=validate_val_launch_manifest,
                _admitted_kind="val_materialization",
                _admitted_manifest_key="val_launch_sha256",
                deadline_monotonic=deadline)
        finally:
            rt.close()
        # 334_s: the final observation must not finish past the
        # ceiling and still close successfully
        if time.monotonic() > deadline:
            raise InfrastructureError(
                "materialization finished past the 0.35 GPU-h "
                "budget deadline — the run aborts (334_s)")
        lock = dev_support.build_surface_lock(surface_dir)
        loaded = dev_support.load_dev_surface(
            surface_dir, expected_lock_sha256=lock["lock_sha256"])
        # the post-run THREE-WAY overlap gate (332_s): training,
        # validation, and cycle populations pairwise disjoint
        from .p0_replay import restore_extension_surface_if_absent
        from .unit_c2_sample import UNIT_C2_CONFIG
        training = dev_support.load_dev_surface(
            restore_extension_surface_if_absent(),
            expected_lock_sha256=UNIT_C2_CONFIG[
                "extension_surface_lock_sha256"])
        overlap = three_way_overlap_reports(
            [{**obs, "latent": _regenerate_latent(obs)}
             for obs in training["observations"]])
        _persist_verified(run_dir / "overlap_report.json", overlap)
        val_lock = build_val_lock(surface_dir,
                                  overlap_report=overlap)
        record = {
            "run": "routing-dev-val-surface-v1",
            "surface_dir": str(surface_dir),
            "val_launch_sha256": manifest["manifest_sha256"],
            "surface_lock_sha256": lock["lock_sha256"],
            "val_lock_sha256": val_lock["record_sha256"],
            "launch_entry_sha256": head,
            "overlap_report": overlap,
            "development_only": True,
        }
        _persist_verified(run_dir / "run_record.json", record)
        # 332_s P1-7: the val-specific terminal verifier runs
        # BEFORE the success closeout, authenticating the admitted
        # launch from the chain (336_s P1-4)
        verify_val_run(run_dir, ledger_path=ledger_path,
                       expected_head_sha256=head,
                       expected_val_lock_sha256=val_lock[
                           "record_sha256"])
    except BaseException as error:
        measured = round((time.monotonic() - started) / 3600.0, 4)
        append_ledger_entry(
            {"kind": "closeout", "question": question,
             "motivating_evidence": "val run ABORTED",
             "freeze": {
                 "val_launch_sha256": manifest["manifest_sha256"],
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

    measured = round((time.monotonic() - started) / 3600.0, 4)
    closeout = append_ledger_entry(
        {"kind": "closeout", "question": question,
         "motivating_evidence": "measured val-surface cost",
         "freeze": {
             "surface_lock_sha256": lock["lock_sha256"],
             "val_lock_sha256": val_lock["record_sha256"],
             "val_lock_file_sha256":
                 _sha_file(run_dir / "val_lock.json"),
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
         "outcome_informed": False,
         "outcome_pointer": str(run_dir / "run_record.json")},
        head, ledger_path)
    return {**record, "measured_gpu_hours": measured,
            "closeout_entry_sha256": closeout["entry_sha256"],
            "ledger_head": closeout["entry_sha256"]}


# --- V3: the val lock ----------------------------------------------------------

_VAL_LOCK_KEYS = frozenset({
    "kind", "val_config_sha256", "namespace", "cohort", "renderers",
    "visibility", "natural_mixture", "natural_mixture_weights",
    "evaluation", "seed_schedule_sha256", "ordered_observation_ids",
    "overlap_report", "surface_lock_sha256",
    "surface_lock_file_sha256", "never_trained_on",
    "development_only",
})


_OVERLAP_DISCLOSURE_FIELDS = frozenset({
    "semantic_intersection", "alpha_prompt_collisions",
    "alpha_prompt_affected_candidates", "affected_candidate_ids",
    "affected_by_cell", "candidate_observations",
    "candidate_semantics", "reference_semantics"})


def _canonical_weights(observations: list[Mapping[str, Any]]
                       ) -> list[list[Any]]:
    """The canonical natural-mixture weights (332_s P1-5): the
    frozen charter definition applied to the exact ordered cohort —
    currently 1/90 for every observation — as ordered
    [observation_id, weight] pairs."""
    from .charter import natural_mixture_weights
    weights = natural_mixture_weights(list(observations))
    return [[obs["observation_id"],
             weights[obs["observation_id"]]]
            for obs in observations]


def build_val_lock(surface_dir: str | Path, *,
                   overlap_report: Mapping[str, Any]
                   ) -> dict[str, Any]:
    """The V3 record (332_s P1-3): the COMPLETE materialized
    surface is loaded and verified FIRST; the surface must BE the
    frozen cohort; the lock binds the config hash, the canonical
    natural-mixture weights, the COMPLETE evaluation identity, the
    seed-schedule pin, the three-way overlap result, and the
    surface-lock hashes. Written exactly once; `record_sha256` is
    the `routing_dev_val_lock_sha256` pin."""
    config = _validated_config()
    surface_dir = Path(surface_dir)
    lock_path = surface_dir.parent / "val_lock.json"
    if lock_path.exists():
        raise InfrastructureError(
            f"{lock_path} exists; the val lock is written exactly "
            "once")
    surface_lock = json.loads(
        (surface_dir / "surface_lock.json").read_text("utf-8"))
    # authenticate the surface BYTES under its own lock before any
    # claim is copied out of it (332_s P1-3)
    loaded = dev_support.load_dev_surface(
        surface_dir, expected_lock_sha256=surface_lock["lock_sha256"])
    observations = val_cohort_observations()
    ordered_ids = [obs["observation_id"] for obs in observations]
    surface_ids = [obs["observation_id"]
                   for obs in loaded["observations"]]
    if sorted(surface_ids) != sorted(ordered_ids):
        raise InfrastructureError(
            "the materialized surface is not the frozen val cohort")
    required = {"val_vs_training", "val_vs_cycle",
                "cycle_vs_training"}
    disclosure_fields = _OVERLAP_DISCLOSURE_FIELDS
    if not isinstance(overlap_report, Mapping) \
            or set(overlap_report) != required or any(
                set(overlap_report[key]) != disclosure_fields
                or overlap_report[key]["semantic_intersection"] != 0
                for key in required):
        raise InfrastructureError(
            "the val lock requires the three-way overlap report: "
            "the HARD alpha-normalized semantic gate at zero and "
            "the complete prompt-overlap DISCLOSURE (334_s)")
    record = {
        "kind": VAL_LOCK_KIND,
        "val_config_sha256": VAL_CONFIG_SHA256,
        "namespace": config["namespace"],
        "cohort": config["cohort"],
        "renderers": config["renderers"],
        "visibility": config["visibility"],
        "natural_mixture": config["natural_mixture"],
        "natural_mixture_weights": _canonical_weights(observations),
        "evaluation": config["evaluation"],
        "seed_schedule_sha256": VAL_SEED_SCHEDULE_SHA256,
        "ordered_observation_ids": ordered_ids,
        "overlap_report": {key: dict(overlap_report[key])
                           for key in sorted(required)},
        "surface_lock_sha256": surface_lock["lock_sha256"],
        "surface_lock_file_sha256":
            _sha_file(surface_dir / "surface_lock.json"),
        "never_trained_on": config["never_trained_on"],
        "development_only": True,
    }
    record["record_sha256"] = content_sha256(record)
    lock_path.write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    return record


def load_val_lock(path: str | Path, expected_sha256: str, *,
                  surface_dir: str | Path) -> dict[str, Any]:
    """The strict consuming loader (332_s P1-3; 334_s P1-4): the
    externally reviewed hash is REQUIRED; the schema is CLOSED; the
    cohort, evaluation identity, weights, and seed-schedule pin are
    REDERIVED from the frozen config (a rehashed record carrying a
    different base seed refuses HERE, not only at the hash); the
    overlap result must carry the hard zero semantic gate and the
    complete disclosure; and the underlying surface BYTES are
    ALWAYS authenticated under the bound lock — the scientific
    consuming boundary never accepts an unauthenticated surface."""
    config = _validated_config()
    payload = json.loads(Path(path).read_text("utf-8"))
    if not isinstance(payload, dict) \
            or set(payload) != _VAL_LOCK_KEYS | {"record_sha256"}:
        raise InfrastructureError(
            "val lock keys do not match the closed schema (332_s)")
    body = {k: v for k, v in payload.items()
            if k != "record_sha256"}
    if content_sha256(body) != payload.get("record_sha256") \
            or payload["record_sha256"] != expected_sha256:
        raise InfrastructureError(
            "val lock does not rehash to the externally reviewed "
            "value")
    observations = val_cohort_observations()
    rederived = {
        "kind": VAL_LOCK_KIND,
        "val_config_sha256": VAL_CONFIG_SHA256,
        "namespace": config["namespace"],
        "cohort": config["cohort"],
        "renderers": config["renderers"],
        "visibility": config["visibility"],
        "natural_mixture": config["natural_mixture"],
        "natural_mixture_weights": _canonical_weights(observations),
        "evaluation": config["evaluation"],
        "seed_schedule_sha256": VAL_SEED_SCHEDULE_SHA256,
        "ordered_observation_ids": [obs["observation_id"]
                                    for obs in observations],
        "never_trained_on": config["never_trained_on"],
        "development_only": True,
    }
    for key, expected in rederived.items():
        if payload[key] != expected:
            raise InfrastructureError(
                f"val lock field {key!r} does not rederive from "
                "the frozen config (332_s P1-3)")
    required = {"val_vs_training", "val_vs_cycle",
                "cycle_vs_training"}
    disclosure_fields = _OVERLAP_DISCLOSURE_FIELDS
    if set(payload["overlap_report"]) != required or any(
            set(payload["overlap_report"][key]) != disclosure_fields
            or payload["overlap_report"][key][
                "semantic_intersection"] != 0
            for key in required):
        raise InfrastructureError(
            "val lock does not bind the hard-gated, fully "
            "disclosed three-way overlap result (334_s)")
    surface_dir = Path(surface_dir)
    if _sha_file(surface_dir / "surface_lock.json") != \
            payload["surface_lock_file_sha256"]:
        raise InfrastructureError(
            "surface lock bytes do not match the val lock binding")
    dev_support.load_dev_surface(
        surface_dir,
        expected_lock_sha256=payload["surface_lock_sha256"])
    return payload


def verify_val_run(run_dir: str | Path, *,
                   ledger_path: str | Path,
                   expected_head_sha256: str | None,
                   expected_val_lock_sha256: str | None
                   ) -> dict[str, Any]:
    """The val terminal verifier (334_s P1-4; 336_s P1-4): the
    launch and closeout are AUTHENTICATED from the verified ledger
    chain — never caller-supplied. Modes by chain state: the launch
    open at the tail = in-run (pre-closeout; the execution-root
    binding is enforced); an aborted closeout = partial hashes
    byte-for-byte and NO val lock; a complete closeout = exact
    terminal inventory plus every duplicated closeout/run-record
    identity cross-checked. Always: prelaunch environment self-hash
    against the manifest; the exact file inventory; execution-env
    attestation; mandatory authenticated surface; run record under
    a CLOSED schema; the three-way overlap RECOMPUTED fresh."""
    from .ledger import verify_ledger_head
    config = _validated_config()
    run_dir = Path(run_dir)
    hashes = _hash_directory(run_dir)
    chain = verify_ledger_head(expected_head_sha256, ledger_path)

    # --- authenticate the launch + closeout from the chain ---------
    declaration = json.loads(
        (run_dir / "prelaunch" / "declaration.json")
        .read_text("utf-8"))
    manifest = validate_val_launch_manifest(
        json.loads((run_dir / "prelaunch" / "val_launch.json")
                   .read_text("utf-8")),
        declaration, recompute=False)
    launches = [e for e in chain
                if e["kind"] == "val_materialization"
                and e["freeze"].get("val_launch_sha256")
                == manifest["manifest_sha256"]]
    if len(launches) != 1:
        raise InfrastructureError(
            f"the verified chain holds {len(launches)} launches "
            "binding this manifest — exactly one is required "
            "(336_s P1-4)")
    launch = launches[0]
    closeouts = [e for e in chain if e["kind"] == "closeout"
                 and e.get("closes_entry_sha256")
                 == launch["entry_sha256"]]
    closeout = closeouts[0] if closeouts else None
    if closeout is None and chain[-1]["entry_sha256"] != \
            launch["entry_sha256"]:
        raise InfrastructureError(
            "an unclosed val launch must be the chain tail "
            "(336_s P1-4)")

    # --- the prelaunch environment binds to the manifest -----------
    prelaunch_env = json.loads(
        (run_dir / "prelaunch" / "env_manifest.json")
        .read_text("utf-8"))
    if dev_support.validate_env_self_hash(prelaunch_env) != \
            manifest["environment_manifest_sha256"]:
        raise InfrastructureError(
            "the prelaunch environment does not bind to the "
            "manifest (336_s P1-4)")

    if closeout is not None \
            and closeout.get("terminal_status") == "aborted":
        if closeout["freeze"].get("partial_artifact_hashes") \
                != hashes:
            raise InfrastructureError(
                "aborted-run evidence does not match the "
                "closeout's partial hashes (334_s P1-4)")
        if expected_val_lock_sha256 is not None \
                or (run_dir / "val_lock.json").exists():
            raise InfrastructureError(
                "an aborted val run never carries a val lock "
                "(334_s P1-4)")
        return {"verdict": "PASS", "terminal_status": "aborted",
                "launch_entry_sha256": launch["entry_sha256"]}

    if expected_val_lock_sha256 is None:
        raise InfrastructureError(
            "a complete val run verifies under its reviewed val "
            "lock hash (334_s P1-4)")
    if closeout is None:
        # in-run: the execution root is bound (336_s P1-3); an
        # archived copy verifies post-hoc through its closeout
        if str(run_dir.resolve()) != manifest["execution_root"]:
            raise InfrastructureError(
                "the verified directory is not the manifest's "
                "bound execution root (336_s P1-3)")

    # --- exact inventory -------------------------------------------
    surface_dir = run_dir / "surface"
    expected_files = {
        "prelaunch/declaration.json", "prelaunch/env_manifest.json",
        "prelaunch/val_launch.json", "prelaunch/val_freeze.json",
        "surface/payoffs.jsonl", "surface/manifest.json",
        "surface/declaration.json", "surface/support_launch.json",
        "surface/env_manifest.json", "surface/surface_lock.json",
        "surface/traces/traces/manifest.json",
        "surface/traces/traces/steps.jsonl",
        "execute_env_manifest.json", "overlap_report.json",
        "run_record.json", "val_lock.json",
    }
    if set(hashes) != expected_files:
        missing = sorted(expected_files - set(hashes))
        extra = sorted(set(hashes) - expected_files)
        raise InfrastructureError(
            f"run inventory is not exactly the expected file set: "
            f"missing {missing[:3]}, extra {extra[:3]} (334_s "
            "P1-4)")

    # --- environment + persisted-manifest cross-bindings -----------
    execute_env = json.loads(
        (run_dir / "execute_env_manifest.json").read_text("utf-8"))
    dev_support.validate_env_self_hash(execute_env)
    attest_environment(prelaunch_env, execute_env)
    persisted_manifest = json.loads(
        (surface_dir / "support_launch.json").read_text("utf-8"))
    if persisted_manifest.get("manifest_sha256") != \
            manifest["manifest_sha256"]:
        raise InfrastructureError(
            "the surface's persisted launch manifest is not the "
            "prelaunch manifest (334_s P1-4)")

    # --- the lock, the surface, the record -------------------------
    lock = load_val_lock(run_dir / "val_lock.json",
                         expected_val_lock_sha256,
                         surface_dir=surface_dir)
    record = json.loads(
        (run_dir / "run_record.json").read_text("utf-8"))
    expected_record_keys = {
        "run", "surface_dir", "val_launch_sha256",
        "surface_lock_sha256", "val_lock_sha256",
        "launch_entry_sha256", "overlap_report",
        "development_only"}
    if set(record) != expected_record_keys:
        raise InfrastructureError(
            "run record keys do not match the closed schema "
            "(334_s P1-4)")
    if record["run"] != config["tranche"] \
            or record["val_launch_sha256"] != \
            manifest["manifest_sha256"] \
            or record["val_lock_sha256"] != \
            expected_val_lock_sha256 \
            or record["surface_lock_sha256"] != \
            lock["surface_lock_sha256"] \
            or record["launch_entry_sha256"] != \
            launch["entry_sha256"] \
            or record["development_only"] is not True:
        raise InfrastructureError(
            "run record does not bind the authenticated launch, "
            "manifest, and locks (336_s P1-4)")

    # --- complete-closeout cross-checks ----------------------------
    if closeout is not None:
        freeze = closeout["freeze"]
        checks = {
            "terminal_artifact_hashes": (
                freeze.get("terminal_artifact_hashes"), hashes),
            "surface_lock_sha256": (
                freeze.get("surface_lock_sha256"),
                lock["surface_lock_sha256"]),
            "val_lock_sha256": (freeze.get("val_lock_sha256"),
                                expected_val_lock_sha256),
            "val_lock_file_sha256": (
                freeze.get("val_lock_file_sha256"),
                _sha_file(run_dir / "val_lock.json")),
            "run_record_file_sha256": (
                freeze.get("run_record_file_sha256"),
                _sha_file(run_dir / "run_record.json")),
            "execute_env_file_sha256": (
                freeze.get("execute_env_file_sha256"),
                _sha_file(run_dir / "execute_env_manifest.json")),
            "rendered_observations": (
                freeze.get("rendered_observations"),
                len(lock["ordered_observation_ids"])),
        }
        for name, (claimed, actual) in checks.items():
            if claimed != actual:
                raise InfrastructureError(
                    f"closeout field {name!r} does not match the "
                    "verified evidence (336_s P1-4)")

    # --- the overlap gate, RECOMPUTED fresh ------------------------
    from .p0_replay import restore_extension_surface_if_absent
    from .unit_c2_sample import UNIT_C2_CONFIG
    training = dev_support.load_dev_surface(
        restore_extension_surface_if_absent(),
        expected_lock_sha256=UNIT_C2_CONFIG[
            "extension_surface_lock_sha256"])
    fresh = three_way_overlap_reports(
        [{**obs, "latent": _regenerate_latent(obs)}
         for obs in training["observations"]])
    persisted = json.loads(
        (run_dir / "overlap_report.json").read_text("utf-8"))
    if fresh != persisted or fresh != lock["overlap_report"] \
            or fresh != record["overlap_report"]:
        raise InfrastructureError(
            "the freshly recomputed three-way overlap does not "
            "match the persisted/bound results (334_s P1-4)")
    return {"verdict": "PASS",
            "terminal_status": ("complete" if closeout is not None
                                else "in_run"),
            "launch_entry_sha256": launch["entry_sha256"],
            "val_lock_sha256": expected_val_lock_sha256,
            "surface_lock_sha256": lock["surface_lock_sha256"]}
