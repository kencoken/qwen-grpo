"""Stage-1 population and provenance layer — 132_s §4 (unit 2).

Three responsibilities, all CPU-side and execution-free:

1. **Successor source/environment identity.** The complete Stage-1 source
   digest covers every tracked ``tasks/conductor/*.py`` file — a strict
   superset of the eight historical ``SOURCE_DIGEST_FILES`` plus the
   reviewer-required ``contract.py`` floor (134_s), asserted fail-closed
   at digest time. Stage-0 digests remain historical evidence, never a
   Stage-1 execution identity.

2. **Population registrars.** Deterministic, generation-free registration
   of the formal construction cohort and the maximum qualification
   population, with exact latent/render-instance ids, expected counts
   derived from the frozen ``stage1`` denominator functions (never
   re-derived ad hoc), the visible-slice expansion, and a canonical-JSON
   SHA-256 identity. Phase-specific look validation lives here, not in
   the population-independent seed serializer (136_s finding 2).

3. **Fail-closed row verification** for ``gate_report``: a missing,
   duplicated, stale, or partial row is an error, never a payoff of 0 or
   0.5 (132_s §4).

Nothing in this module loads a model, reads a payoff surface, or reveals
an outcome; it binds identities before execution.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import stage1
from .grpo_smoke import SOURCE_DIGEST_FILES
from .profiles import canonical_json, profile_version, validate_profile
from .program import (
    CONSTRUCTION_FORMAL_COHORT, GENERATOR_VERSION,
    latent_program_id, namespace_cap, render_instance_id, seed_material,
    validate_construction_cohort,
)
from .types import InfrastructureError, RENDERER_IDS

_CONDUCTOR_DIR = Path("tasks/conductor")

STAGE1_CELLS = ("lookup_atomic", "math_atomic", "code_atomic",
                "lookup_math", "math_code", "fork_join")


class ManifestError(ValueError):
    """Fail-closed population/provenance validation error."""


# --- 1. successor source digest ----------------------------------------------

def stage1_source_files() -> tuple[str, ...]:
    """Every tracked .py under tasks/conductor/, sorted — the complete
    source identity (125_s gap: pool_runtime/executor/... were never
    digest-bound). Tracked-only, so an untracked scratch file cannot
    silently enter the execution identity; a dirty tree is caught by the
    environment manifest's `git_dirty` instead."""
    out = subprocess.run(
        ["git", "ls-files", str(_CONDUCTOR_DIR / "*.py")],
        capture_output=True, text=True, check=True).stdout
    files = tuple(sorted(line for line in out.splitlines() if line))
    if not files:
        raise InfrastructureError("git ls-files returned no conductor "
                                  "sources — wrong working directory?")
    required = set(SOURCE_DIGEST_FILES) | \
        set(stage1.SUCCESSOR_DIGEST_REQUIRED_ADDITIONS)
    missing = required - set(files)
    if missing:
        raise InfrastructureError(
            f"successor source list must be a superset of the historical "
            f"eight plus the 134_s floor; missing {sorted(missing)}")
    return files


def stage1_source_digest() -> str:
    """Same name\\0bytes\\0 chaining as the Stage-0
    `executable_source_digest`, over the complete file list."""
    digest = hashlib.sha256()
    for name in stage1_source_files():
        digest.update(name.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(Path(name).read_bytes())
        digest.update(b"\x00")
    return digest.hexdigest()


def build_stage1_env_manifest() -> dict[str, Any]:
    """`stage1-environment-v1`: the ce0 environment machinery (127_f
    prerequisite 1) extended with the complete source identity. Fails
    closed if the GPU cannot be queried — an execution manifest for a
    box that cannot run is a contradiction. Not called by tests."""
    from .ce0 import build_env_manifest
    env = build_env_manifest()
    env["manifest"] = "stage1-environment-v1"
    env["stage1_source_sha256"] = stage1_source_digest()
    env["stage1_source_files"] = list(stage1_source_files())
    env["historical_stage0_source_sha256"] = (
        "688f7e06da6e9ca04b1714663b032efc178d2790ef8859c3275ddd52e276cee8")
    return env


# --- 2. population registrars -------------------------------------------------

def _cell_ids(cell_id: str, namespace: str, indices: Iterable[int],
              profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Deterministic latent/render ids WITHOUT generation: the id is a
    function of (generator version, profile version, namespace, cell,
    index) alone, so registration reveals nothing about instances."""
    dp_version = profile_version(dict(profile))
    rows = []
    for index in indices:
        material = seed_material(GENERATOR_VERSION, dp_version, namespace,
                                 cell_id, index)
        lp_id = latent_program_id(cell_id, namespace, index, material)
        rows.append({
            "latent_index": index,
            "latent_program_id": lp_id,
            "render_instance_ids": [
                render_instance_id(lp_id, renderer, "private")
                for renderer in RENDERER_IDS],
        })
    return rows


def _expected_cell_counts(cell_id: str, n_clusters: int,
                          visible_clusters: int) -> dict[str, int]:
    """Expected-count block, derived from the frozen stage1 denominator
    contract — the single source for 7.1 row arithmetic."""
    s = len(stage1.NODE_FAMILIES[cell_id])
    observations = n_clusters * stage1.RENDERERS_PER_LATENT
    counts = {
        "latent_clusters": n_clusters,
        "private_observations": observations,
        "visible_observations":
            visible_clusters * stage1.RENDERERS_PER_LATENT,
        "assignment_rows_per_observation": 4 ** s,
        "assignment_rows": observations * (4 ** s),
        "one_call_rows": observations * 4,
        "selected_route_rows":
            n_clusters * stage1.selected_route_rows_per_latent(cell_id),
        "truncation_rows_by_worker": {
            str(worker): n_clusters *
            stage1.truncation_rows_per_latent(cell_id, worker)
            for worker in sorted(stage1.WORKER_FAMILIES)},
    }
    if cell_id == "fork_join":
        counts["two_call_shortcut_rows"] = observations * 32
    return counts


def _finalize(manifest: dict[str, Any]) -> dict[str, Any]:
    body = canonical_json(manifest)
    manifest = dict(manifest)
    manifest["population_manifest_sha256"] = hashlib.sha256(
        body.encode("utf-8")).hexdigest()
    return manifest


def register_construction_population(
        profile: Mapping[str, Any]) -> dict[str, Any]:
    """The one formal construction cohort: indices 30-129 per cell, all
    three private renderers, D4-validated, expected counts bound."""
    validate_profile(dict(profile))
    indices = list(CONSTRUCTION_FORMAL_COHORT)
    validate_construction_cohort(indices)
    manifest: dict[str, Any] = {
        "manifest": "stage1-construction-population-v1",
        "namespace": "construction",
        "generator_version": GENERATOR_VERSION,
        "profile_version": profile_version(dict(profile)),
        "renderer_ids": list(RENDERER_IDS),
        "visibility": "private",
        "index_range": [indices[0], indices[-1] + 1],
        "cells": {
            cell: {
                "ids": _cell_ids(cell, "construction", indices, profile),
                "expected_counts": _expected_cell_counts(
                    cell, len(indices), visible_clusters=0),
            } for cell in STAGE1_CELLS},
        "stage1_source_sha256": stage1_source_digest(),
    }
    return _finalize(manifest)


def validate_qualification_looks(cell_looks: Mapping[str, int]) -> None:
    """Phase-specific schedule validation (136_s finding 2: this lives
    in the manifest layer, not the seed serializer)."""
    for cell, look in cell_looks.items():
        if cell not in STAGE1_CELLS:
            raise ManifestError(f"unknown cell_id {cell!r}")
        schedule = (stage1.FORK_LOOK_SCHEDULE if cell == "fork_join"
                    else stage1.ORDINARY_LOOK_SCHEDULE)
        if look not in schedule:
            raise ManifestError(
                f"qualification look {look!r} not in the registered "
                f"schedule {schedule} for {cell}")


def register_qualification_population(
        profile: Mapping[str, Any]) -> dict[str, Any]:
    """The MAXIMUM deterministic qualification population, registered
    before the first worker call (132_s §8.1); looks reveal immutable
    prefixes of exactly these ids. The first 18 clusters per cell carry
    paired visible variants (visible slice, §4.1) whose rows support
    B3/echo/no-op diagnostics only."""
    validate_profile(dict(profile))
    vis_n = len(stage1.VISIBLE_SLICE_QUALIFICATION_CLUSTERS)
    cells: dict[str, Any] = {}
    for cell in STAGE1_CELLS:
        cap = namespace_cap("qualification", cell)
        schedule = (stage1.FORK_LOOK_SCHEDULE if cell == "fork_join"
                    else stage1.ORDINARY_LOOK_SCHEDULE)
        if cap != schedule[-1]:
            raise ManifestError(
                f"{cell}: qualification cap {cap} != terminal look "
                f"{schedule[-1]}")
        ids = _cell_ids(cell, "qualification", range(cap), profile)
        for row in ids[:vis_n]:
            row["visible_render_instance_ids"] = [
                render_instance_id(row["latent_program_id"], renderer,
                                   "visible")
                for renderer in RENDERER_IDS]
        cells[cell] = {
            "look_schedule": list(schedule),
            "ids": ids,
            "expected_counts": _expected_cell_counts(
                cell, cap, visible_clusters=vis_n),
        }
    manifest: dict[str, Any] = {
        "manifest": "stage1-qualification-population-v1",
        "namespace": "qualification",
        "generator_version": GENERATOR_VERSION,
        "profile_version": profile_version(dict(profile)),
        "renderer_ids": list(RENDERER_IDS),
        "visible_slice_clusters": vis_n,
        "cells": cells,
        "stage1_source_sha256": stage1_source_digest(),
    }
    return _finalize(manifest)


def qualification_prefix(manifest: Mapping[str, Any],
                         cell_looks: Mapping[str, int]
                         ) -> dict[str, list[str]]:
    """The immutable id prefix a look reveals — never a resample."""
    validate_qualification_looks(cell_looks)
    out: dict[str, list[str]] = {}
    for cell, look in cell_looks.items():
        ids = manifest["cells"][cell]["ids"]
        out[cell] = [row["latent_program_id"] for row in ids[:look]]
    return out


# --- 3. fail-closed gate-report row verification -------------------------------

_ROW_REQUIRED_FIELDS = ("row_key", "population_manifest_sha256")


def verify_rows(manifest: Mapping[str, Any],
                expected_keys: Iterable[str],
                rows: Iterable[Mapping[str, Any]]) -> None:
    """`gate_report` fails closed on a missing, duplicated, stale, or
    partial row (132_s §4). `expected_keys` come from the manifest's
    registered ids/strata; `rows` are the artifact rows presented for a
    gate. No verification failure may ever be scored as reward 0/0.5."""
    expected = set(expected_keys)
    if not expected:
        raise ManifestError("empty expected-key set — a gate with no "
                            "registered denominator is not evaluable")
    manifest_sha = manifest.get("population_manifest_sha256")
    if not manifest_sha:
        raise ManifestError("manifest carries no "
                            "population_manifest_sha256")
    seen: set[str] = set()
    for row in rows:
        for field in _ROW_REQUIRED_FIELDS:
            if field not in row:
                raise ManifestError(f"partial row (missing {field!r}): "
                                    f"{dict(row)!r}")
        key = row["row_key"]
        if row["population_manifest_sha256"] != manifest_sha:
            raise ManifestError(
                f"stale row {key!r}: bound to manifest "
                f"{row['population_manifest_sha256'][:8]}..., expected "
                f"{manifest_sha[:8]}...")
        if key in seen:
            raise ManifestError(f"duplicated row {key!r}")
        if key not in expected:
            raise ManifestError(f"unregistered row {key!r}")
        seen.add(key)
    missing = expected - seen
    if missing:
        raise ManifestError(
            f"missing rows ({len(missing)}): "
            f"{sorted(missing)[:3]}{'...' if len(missing) > 3 else ''}")
