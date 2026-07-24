"""Stage-1 population and provenance layer — 132_s §4 (unit 2, rev2 per
139_s).

Responsibilities, all CPU-side and execution-free:

1. **Successor source/environment identity.** The complete Stage-1 source
   digest covers every tracked ``tasks/conductor/*.py`` file — a strict
   superset of the eight historical ``SOURCE_DIGEST_FILES`` plus the
   reviewer-required ``contract.py`` floor (134_s), asserted fail-closed
   at digest time. Formal execution manifests are content-addressed and
   reject dirty trees by default (139_s).

2. **Population registrars and the authoritative validator.**
   Registration is deterministic and generation-free; consumption always
   goes through :func:`validate_population_manifest`, which recomputes
   the hash and re-derives phase, profile, source identity, cells,
   schedules, counts, and every latent/render id (139_s finding 1).
   Only the registered frozen profile candidate is accepted (finding 2);
   qualification registration consumes the validated construction
   manifest, not a free profile argument.

3. **Gate-row verification with derived denominators.** Expected row
   identities are derived from the validated manifest and the frozen
   ``stage1`` denominator contract — never caller-supplied (finding 3) —
   and every row must bind both the population identity and a
   content-addressed execution identity. The full runtime/worker/request
   fingerprint join (exception-to-code mapping, pool fingerprints)
   lands with the unit-4 execution layer; until then those fields are
   simply absent from row schemas here, and this layer never claims to
   check them.

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

_CONSTRUCTION_KIND = "stage1-construction-population-v1"
_QUALIFICATION_KIND = "stage1-qualification-population-v1"

# 139_s finding 2: registration accepts only the frozen candidate set.
REGISTERED_PROFILE_VERSIONS = frozenset(
    version for versions in stage1.PROFILE_CANDIDATES.values()
    for version in versions)


class ManifestError(ValueError):
    """Fail-closed population/provenance validation error."""


# --- 1. successor source digest and execution identity -----------------------

def stage1_source_files() -> tuple[str, ...]:
    """Every tracked .py under tasks/conductor/, sorted — the complete
    source identity (125_s gap: pool_runtime/executor/... were never
    digest-bound). Tracked-only, so an untracked scratch file cannot
    silently enter the execution identity; uncommitted edits to tracked
    files ARE hashed (working-tree bytes), and formal execution
    manifests reject dirty trees outright (139_s)."""
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


def build_stage1_env_manifest(*, allow_dirty: bool = False
                              ) -> dict[str, Any]:
    """`stage1-environment-v2`, content-addressed: the ce0 environment
    machinery (127_f prerequisite 1) extended with the complete source
    identity and hashed canonically (139_s finding 3 — an execution
    identity rows can bind). A dirty tree is refused unless
    `allow_dirty=True` (development only), in which case the complete
    uncommitted diff is content-addressed too (139_s smaller item 2).
    Fails closed if the GPU cannot be queried. Not called by tests."""
    from .ce0 import build_env_manifest
    env = build_env_manifest()
    if env.pop("git_dirty"):
        if not allow_dirty:
            raise InfrastructureError(
                "dirty working tree: a formal execution manifest binds "
                "committed state; commit or stash first (139_s)")
        diff = subprocess.run(["git", "diff", "HEAD"], capture_output=True,
                              text=True, check=True).stdout
        env["git_dirty"] = 1
        env["git_diff_sha256"] = hashlib.sha256(
            diff.encode("utf-8")).hexdigest()
    else:
        env["git_dirty"] = 0
    env["manifest"] = "stage1-environment-v2"
    env["stage1_source_sha256"] = stage1_source_digest()
    env["stage1_source_files"] = list(stage1_source_files())
    env["historical_stage0_source_sha256"] = (
        "688f7e06da6e9ca04b1714663b032efc178d2790ef8859c3275ddd52e276cee8")
    env["execution_manifest_sha256"] = hashlib.sha256(
        canonical_json(env).encode("utf-8")).hexdigest()
    return env


def validate_env_manifest(env: Mapping[str, Any]) -> str:
    """148_s finding 3: an execution identity is only trustworthy when
    it is proven to BE the content hash of a valid
    `stage1-environment-v2` manifest — a bare 64-hex string proves only
    equality. Recomputes the content hash, checks the manifest kind and
    required fields, and (retirement fail-closed) the source identity
    against current bytes. Returns the verified identity."""
    if env.get("manifest") != "stage1-environment-v2":
        raise ManifestError(
            f"not a stage1-environment-v2 manifest: "
            f"{env.get('manifest')!r}")
    declared = env.get("execution_manifest_sha256")
    if not declared:
        raise ManifestError("environment manifest carries no "
                            "execution_manifest_sha256")
    body = {k: v for k, v in env.items()
            if k != "execution_manifest_sha256"}
    recomputed = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if recomputed != declared:
        raise ManifestError(
            "environment manifest hash mismatch — the execution "
            "identity is not the hash of this manifest")
    for field in ("git_commit", "uv_lock_sha256", "stage1_source_sha256",
                  "stage1_source_files", "gpu", "torch"):
        if field not in env:
            raise ManifestError(f"environment manifest missing "
                                f"{field!r}")
    if env["stage1_source_sha256"] != stage1_source_digest():
        raise ManifestError(
            "environment manifest bound to a different source identity "
            "— retirement is fail-closed at load (132_s §11.4)")
    return declared


# --- 2. registrars and the authoritative validator ---------------------------

def _enforce_registered_profile(profile: Mapping[str, Any]) -> str:
    validate_profile(dict(profile))
    version = profile_version(dict(profile))
    if version not in REGISTERED_PROFILE_VERSIONS:
        raise ManifestError(
            f"profile {version} is not a registered candidate "
            f"({sorted(REGISTERED_PROFILE_VERSIONS)}); a formal "
            "population accepts only the frozen candidates (139_s)")
    return version


def _cell_ids(cell_id: str, namespace: str, indices: Iterable[int],
              dp_version: str) -> list[dict[str, Any]]:
    """Deterministic latent/render ids WITHOUT generation: the id is a
    function of (generator version, profile version, namespace, cell,
    index) alone, so registration reveals nothing about instances."""
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
                          visible_clusters: int,
                          with_b1: bool) -> dict[str, Any]:
    """Expected-count block, derived from the frozen stage1 denominator
    contract — the single source for §7.1 row arithmetic. Extended per
    139_s finding 4 with the full independent node-execution grid and
    per-edge intervention rows."""
    s = len(stage1.NODE_FAMILIES[cell_id])
    observations = n_clusters * stage1.RENDERERS_PER_LATENT
    counts: dict[str, Any] = {
        "latent_clusters": n_clusters,
        "private_observations": observations,
        "visible_observations":
            visible_clusters * stage1.RENDERERS_PER_LATENT,
        "assignment_rows_per_observation": 4 ** s,
        "assignment_rows": observations * (4 ** s),
        "one_call_rows": observations * 4,
        # full independent (observation, node, logical worker) grid —
        # every node under every logical worker, reference-gold
        # predecessor context (139_s finding 4)
        "independent_node_execution_rows":
            observations * s * len(stage1.WORKER_FAMILIES),
        "selected_route_rows":
            n_clusters * stage1.selected_route_rows_per_latent(cell_id),
        "truncation_rows_by_worker": {
            str(worker): n_clusters *
            stage1.truncation_rows_per_latent(cell_id, worker)
            for worker in sorted(stage1.WORKER_FAMILIES)},
        # one corrupted execution per private observation per directed
        # edge; eligibility-conditional persistence/consistency ratios
        # are outcome-dependent and bound at materialization
        "intervention_rows_by_edge": {
            f"{src}->{dst}": observations
            for (src, dst) in stage1.CELL_INTERVENTION_EDGES[cell_id]},
    }
    if with_b1:
        # §5.3: one canonical resource_first row per construction cluster
        counts["b1_fitting_rows"] = n_clusters
    if cell_id == "fork_join":
        counts["two_call_shortcut_rows"] = observations * 32
    return counts


# Support classes that are NOT deterministic at registration, recorded so
# their absence is an explicit decision rather than an omission (139_s):
SUPPORT_DEFERRED = (
    "selected_route_rows_by_worker: deterministic only once the "
    "construction-frozen deployable mapping d exists; computed then via "
    "stage1.selected_route_rows_per_worker and bound in the selection "
    "artifact (unit 4)",
    "cache/physical-generation counts: outcome-dependent; bound in the "
    "materialization manifest",
    "B2/B3/B4/B6/echo/no-op execution support: registered with the unit-4 "
    "execution harness; B3 consumes the visible slice named here",
)


def _finalize(manifest: dict[str, Any]) -> dict[str, Any]:
    body = canonical_json(manifest)
    manifest = dict(manifest)
    manifest["population_manifest_sha256"] = hashlib.sha256(
        body.encode("utf-8")).hexdigest()
    return manifest


def register_construction_population(
        profile: Mapping[str, Any]) -> dict[str, Any]:
    """The one formal construction cohort: indices 30-129 per cell, all
    three private renderers, D4-validated, expected counts bound. Only
    a registered frozen profile candidate is accepted."""
    dp_version = _enforce_registered_profile(profile)
    indices = list(CONSTRUCTION_FORMAL_COHORT)
    validate_construction_cohort(indices)
    manifest: dict[str, Any] = {
        "manifest": _CONSTRUCTION_KIND,
        "namespace": "construction",
        "generator_version": GENERATOR_VERSION,
        "profile_version": dp_version,
        "renderer_ids": list(RENDERER_IDS),
        "visibility": "private",
        "index_range": [indices[0], indices[-1] + 1],
        "cells": {
            cell: {
                "ids": _cell_ids(cell, "construction", indices,
                                 dp_version),
                "expected_counts": _expected_cell_counts(
                    cell, len(indices), visible_clusters=0, with_b1=True),
            } for cell in STAGE1_CELLS},
        "support_deferred": list(SUPPORT_DEFERRED),
        "stage1_source_sha256": stage1_source_digest(),
    }
    return _finalize(manifest)


def register_qualification_population(
        construction_manifest: Mapping[str, Any]) -> dict[str, Any]:
    """The MAXIMUM deterministic qualification population, registered
    before the first worker call (132_s §8.1); looks reveal immutable
    prefixes of exactly these ids.

    Consumes the VALIDATED construction manifest (139_s finding 2): the
    profile identity is inherited from it, never re-supplied, and the
    construction identity is embedded. When the construction reveal
    later freezes the deployable/control artifact, that artifact binds
    this manifest's hash (unit 4); qualification cannot precede it in
    the §3.3 phase order."""
    validate_population_manifest(construction_manifest,
                                 kind=_CONSTRUCTION_KIND)
    dp_version = construction_manifest["profile_version"]
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
        ids = _cell_ids(cell, "qualification", range(cap), dp_version)
        for row in ids[:vis_n]:
            row["visible_render_instance_ids"] = [
                render_instance_id(row["latent_program_id"], renderer,
                                   "visible")
                for renderer in RENDERER_IDS]
        counts = _expected_cell_counts(cell, cap, visible_clusters=vis_n,
                                       with_b1=False)
        # per-look denominator blocks (139_s finding 4): the immutable
        # prefix arithmetic, frozen at registration
        counts["per_look"] = {
            str(look): _expected_cell_counts(
                cell, look,
                visible_clusters=min(vis_n, look), with_b1=False)
            for look in schedule}
        cells[cell] = {
            "look_schedule": list(schedule),
            "ids": ids,
            "expected_counts": counts,
        }
    manifest: dict[str, Any] = {
        "manifest": _QUALIFICATION_KIND,
        "namespace": "qualification",
        "generator_version": GENERATOR_VERSION,
        "profile_version": dp_version,
        "construction_manifest_sha256":
            construction_manifest["population_manifest_sha256"],
        "renderer_ids": list(RENDERER_IDS),
        "visible_slice_clusters": vis_n,
        "cells": cells,
        "support_deferred": list(SUPPORT_DEFERRED),
        "stage1_source_sha256": stage1_source_digest(),
    }
    return _finalize(manifest)


def validate_population_manifest(manifest: Mapping[str, Any], *,
                                 kind: str) -> None:
    """THE authoritative consumption gate (139_s finding 1): recomputes
    the content hash and re-derives phase, profile, source identity,
    cells, schedules, counts, and every latent/render id. Every public
    consumer in this module calls it; downstream units must too."""
    if manifest.get("manifest") != kind:
        raise ManifestError(
            f"manifest kind {manifest.get('manifest')!r} != required "
            f"{kind!r} — a construction manifest is not a qualification "
            "manifest")
    declared = manifest.get("population_manifest_sha256")
    if not declared:
        raise ManifestError("manifest carries no "
                            "population_manifest_sha256")
    body = {k: v for k, v in manifest.items()
            if k != "population_manifest_sha256"}
    recomputed = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if recomputed != declared:
        raise ManifestError(
            f"manifest hash mismatch: declared {declared[:8]}..., "
            f"recomputed {recomputed[:8]}... — content was mutated after "
            "hashing")
    if manifest["profile_version"] not in REGISTERED_PROFILE_VERSIONS:
        raise ManifestError(
            f"manifest profile {manifest['profile_version']} is not a "
            "registered frozen candidate")
    if manifest["generator_version"] != GENERATOR_VERSION:
        raise ManifestError(
            f"generator version {manifest['generator_version']} != "
            f"current {GENERATOR_VERSION} — retired population")
    if manifest["stage1_source_sha256"] != stage1_source_digest():
        raise ManifestError(
            "manifest bound to a different source identity — retirement "
            "is fail-closed at load (132_s §11.4)")
    if list(manifest["renderer_ids"]) != list(RENDERER_IDS):
        raise ManifestError("renderer list mismatch")
    if set(manifest["cells"]) != set(STAGE1_CELLS):
        raise ManifestError(
            f"cells {sorted(manifest['cells'])} != {sorted(STAGE1_CELLS)}")

    namespace = manifest["namespace"]
    dp_version = manifest["profile_version"]
    vis_n = (len(stage1.VISIBLE_SLICE_QUALIFICATION_CLUSTERS)
             if kind == _QUALIFICATION_KIND else 0)
    for cell, block in manifest["cells"].items():
        if kind == _CONSTRUCTION_KIND:
            indices = [row["latent_index"] for row in block["ids"]]
            validate_construction_cohort(indices)
        else:
            cap = namespace_cap("qualification", cell)
            schedule = (stage1.FORK_LOOK_SCHEDULE if cell == "fork_join"
                        else stage1.ORDINARY_LOOK_SCHEDULE)
            if list(block["look_schedule"]) != list(schedule):
                raise ManifestError(f"{cell}: look schedule mismatch")
            if [row["latent_index"] for row in block["ids"]] != \
                    list(range(cap)):
                raise ManifestError(
                    f"{cell}: ids are not the complete maximum "
                    f"population [0, {cap})")
        # regenerate every id from first principles — a mutated or
        # truncated id set cannot survive this
        expected_ids = _cell_ids(cell, namespace,
                                 [row["latent_index"]
                                  for row in block["ids"]], dp_version)
        for got, want in zip(block["ids"], expected_ids):
            if got["latent_program_id"] != want["latent_program_id"] or \
                    list(got["render_instance_ids"]) != \
                    want["render_instance_ids"]:
                raise ManifestError(
                    f"{cell}: id row {got['latent_index']} does not "
                    "regenerate from its own identity material")
            has_visible = "visible_render_instance_ids" in got
            should_have = got["latent_index"] < vis_n
            if has_visible != should_have:
                raise ManifestError(
                    f"{cell}: visible-slice placement wrong at index "
                    f"{got['latent_index']}")
            if has_visible and list(got["visible_render_instance_ids"]) \
                    != [render_instance_id(want["latent_program_id"],
                                           renderer, "visible")
                        for renderer in RENDERER_IDS]:
                raise ManifestError(
                    f"{cell}: visible ids do not regenerate at index "
                    f"{got['latent_index']}")
        # recompute the expected-count block
        n = len(block["ids"])
        want_counts = _expected_cell_counts(
            cell, n, visible_clusters=min(vis_n, n),
            with_b1=(kind == _CONSTRUCTION_KIND))
        if kind == _QUALIFICATION_KIND:
            want_counts["per_look"] = {
                str(look): _expected_cell_counts(
                    cell, look, visible_clusters=min(vis_n, look),
                    with_b1=False)
                for look in block["look_schedule"]}
        if block["expected_counts"] != want_counts:
            raise ManifestError(f"{cell}: expected-count block does not "
                                "recompute from the denominator contract")


def validate_qualification_looks(cell_looks: Mapping[str, int]) -> None:
    """Phase-specific schedule validation (136_s finding 2; hardened per
    139_s: non-empty, plain positive ints only — `100.0` is not a
    look)."""
    if not cell_looks:
        raise ManifestError("empty look mapping")
    for cell, look in cell_looks.items():
        if cell not in STAGE1_CELLS:
            raise ManifestError(f"unknown cell_id {cell!r}")
        if type(look) is not int or look <= 0:
            raise ManifestError(
                f"look for {cell} must be a plain positive int, got "
                f"{look!r}")
        schedule = (stage1.FORK_LOOK_SCHEDULE if cell == "fork_join"
                    else stage1.ORDINARY_LOOK_SCHEDULE)
        if look not in schedule:
            raise ManifestError(
                f"qualification look {look!r} not in the registered "
                f"schedule {schedule} for {cell}")


def qualification_prefix(manifest: Mapping[str, Any],
                         cell_looks: Mapping[str, int]
                         ) -> dict[str, list[str]]:
    """The immutable id prefix a look reveals — never a resample. The
    manifest is validated on every call (139_s finding 1)."""
    validate_population_manifest(manifest, kind=_QUALIFICATION_KIND)
    validate_qualification_looks(cell_looks)
    out: dict[str, list[str]] = {}
    for cell, look in cell_looks.items():
        ids = manifest["cells"][cell]["ids"]
        out[cell] = [row["latent_program_id"] for row in ids[:look]]
    return out


# --- 3. gate-row verification with derived denominators -----------------------

_GATES = ("truncation", "node_execution", "selected_route",
          "intervention")


def expected_row_keys(manifest: Mapping[str, Any], *, kind: str,
                      cell: str, gate: str,
                      worker: int | None = None,
                      deployable: Mapping[str, int] | None = None,
                      clusters: int | None = None) -> frozenset[str]:
    """Structured expected row identities, derived from the VALIDATED
    manifest plus the frozen denominator contract — never supplied by
    the caller (139_s finding 3).

    Key grammar: `{render_instance_id}|{node}|w{worker}|{gate}` for
    worker-executed rows; `{render_instance_id}|{src}->{dst}|{gate}` for
    intervention rows. `clusters` restricts to the first-N immutable
    prefix (a look); None means the full registered population."""
    validate_population_manifest(manifest, kind=kind)
    if gate not in _GATES:
        raise ManifestError(f"unknown gate {gate!r}")
    if cell not in STAGE1_CELLS:
        raise ManifestError(f"unknown cell {cell!r}")
    id_rows = manifest["cells"][cell]["ids"]
    if clusters is not None:
        if type(clusters) is not int or not 0 < clusters <= len(id_rows):
            raise ManifestError(f"bad cluster prefix {clusters!r}")
        id_rows = id_rows[:clusters]
    nodes = stage1.NODE_FAMILIES[cell]
    keys: set[str] = set()
    for row in id_rows:
        for rid in row["render_instance_ids"]:
            if gate == "truncation":
                if worker is None:
                    raise ManifestError("truncation keys need a worker")
                for node in stage1.on_contract_nodes(cell, worker):
                    keys.add(f"{rid}|{node}|w{worker}|truncation")
            elif gate == "node_execution":
                for node in sorted(nodes):
                    for wid in sorted(stage1.WORKER_FAMILIES):
                        keys.add(f"{rid}|{node}|w{wid}|node_execution")
            elif gate == "selected_route":
                if deployable is None:
                    raise ManifestError(
                        "selected-route keys need the construction-"
                        "frozen deployable mapping d")
                # validates coverage/worker ids as a side effect
                stage1.selected_route_rows_per_worker(cell, deployable)
                for node, wid in deployable.items():
                    keys.add(f"{rid}|{node}|w{wid}|selected_route")
            else:  # intervention
                for (src, dst) in stage1.CELL_INTERVENTION_EDGES[cell]:
                    keys.add(f"{rid}|{src}->{dst}|intervention")
    if not keys:
        raise ManifestError(
            f"gate {gate!r} has no registered denominator in {cell} "
            "(e.g. truncation for a worker with no on-contract nodes) — "
            "not evaluable")
    return frozenset(keys)


_ROW_REQUIRED_FIELDS = ("row_key", "population_manifest_sha256",
                        "execution_manifest_sha256")
_HEX64 = frozenset("0123456789abcdef")


def verify_gate_rows(manifest: Mapping[str, Any], *, kind: str, cell: str,
                     gate: str, rows: Iterable[Mapping[str, Any]],
                     execution_manifest_sha256: str,
                     worker: int | None = None,
                     deployable: Mapping[str, int] | None = None,
                     clusters: int | None = None) -> None:
    """Fail-closed gate-row verification (132_s §4): missing,
    duplicated, stale, partial, or unregistered rows raise; every row
    must bind BOTH the population identity and the content-addressed
    execution identity. Request/worker/pool fingerprints are additional
    row fields checked by the unit-4 execution layer; their absence here
    is a recorded boundary, not a claim of coverage."""
    if (len(execution_manifest_sha256) != 64
            or not set(execution_manifest_sha256) <= _HEX64):
        raise ManifestError("execution_manifest_sha256 must be 64 "
                            "lowercase hex characters")
    expected = expected_row_keys(manifest, kind=kind, cell=cell,
                                 gate=gate, worker=worker,
                                 deployable=deployable, clusters=clusters)
    manifest_sha = manifest["population_manifest_sha256"]
    seen: set[str] = set()
    for row in rows:
        for field in _ROW_REQUIRED_FIELDS:
            if field not in row:
                raise ManifestError(f"partial row (missing {field!r}): "
                                    f"{dict(row)!r}")
        key = row["row_key"]
        if row["population_manifest_sha256"] != manifest_sha:
            raise ManifestError(
                f"stale row {key!r}: bound to population "
                f"{row['population_manifest_sha256'][:8]}..., expected "
                f"{manifest_sha[:8]}...")
        if row["execution_manifest_sha256"] != execution_manifest_sha256:
            raise ManifestError(
                f"foreign execution identity on row {key!r}: "
                f"{row['execution_manifest_sha256'][:8]}... != "
                f"{execution_manifest_sha256[:8]}...")
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
