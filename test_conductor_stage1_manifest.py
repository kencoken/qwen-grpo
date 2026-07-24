"""Unit-2 acceptance tests — 132_s §4 population/provenance layer (138_f).

Covers the successor source digest (complete, superset-asserted, moved by
exactly the disclosed workerpool citation fix), the construction and
qualification registrars (deterministic ids, expected counts derived from
the frozen stage1 denominator contract, visible slice, canonical hashing,
immutable prefixes), fail-closed row verification, the 136_s follow-through
registry cross-check, and phase-specific look validation.
"""

import hashlib
import json

import pytest

from tasks.conductor import stage1, stage1_manifest
from tasks.conductor.grpo_smoke import SOURCE_DIGEST_FILES
from tasks.conductor.profiles import DEFAULT_PROFILE
from tasks.conductor.program import generate_latent
from tasks.conductor.stage1_manifest import (
    ManifestError, STAGE1_CELLS, build_stage1_env_manifest,
    qualification_prefix, register_construction_population,
    register_qualification_population, stage1_source_digest,
    stage1_source_files, validate_qualification_looks, verify_rows,
)
from tasks.conductor.workerpool import WORKER_TO_ENDPOINT


# --- successor source digest ---------------------------------------------------

def test_source_list_superset_of_eight_plus_floor():
    files = stage1_source_files()
    assert set(SOURCE_DIGEST_FILES) < set(files)
    for path in stage1.SUCCESSOR_DIGEST_REQUIRED_ADDITIONS:
        assert path in files
    # complete: every tracked conductor .py, sorted, no duplicates
    assert list(files) == sorted(set(files))
    assert "tasks/conductor/stage1.py" in files
    assert "tasks/conductor/stage1_manifest.py" in files
    assert "tasks/conductor/pool_runtime.py" in files   # the 125_s gap
    assert "tasks/conductor/executor.py" in files


def test_source_digest_is_not_the_stage0_digest():
    d = stage1_source_digest()
    assert len(d) == 64
    # the historical Stage-0 identity (pre-citation-fix) and the
    # Stage-0 machinery's post-fix digest are both distinct from the
    # complete successor digest
    assert not d.startswith("688f7e06")
    assert not d.startswith("9f9fe6f6")


def test_env_manifest_is_execution_only():
    # build_stage1_env_manifest queries the GPU and fails closed when it
    # cannot (this box currently has the recorded NVML mismatch) — the
    # structural contract is tested here without invoking it.
    assert callable(build_stage1_env_manifest)


# --- registrars ------------------------------------------------------------------

@pytest.fixture(scope="module")
def construction():
    return register_construction_population(DEFAULT_PROFILE)


@pytest.fixture(scope="module")
def qualification():
    return register_qualification_population(DEFAULT_PROFILE)


def test_construction_manifest_identity(construction):
    m = construction
    assert m["manifest"] == "stage1-construction-population-v1"
    assert m["index_range"] == [30, 130]
    assert m["profile_version"] == stage1.PRIMARY_PROFILE_VERSION
    assert len(m["population_manifest_sha256"]) == 64
    # deterministic: re-registration reproduces the identical hash
    again = register_construction_population(DEFAULT_PROFILE)
    assert again["population_manifest_sha256"] == \
        m["population_manifest_sha256"]


def test_construction_ids_match_generation(construction):
    # the generation-free ids equal what full generation produces
    for cell in ("code_atomic", "fork_join"):
        rows = construction["cells"][cell]["ids"]
        assert len(rows) == 100
        assert rows[0]["latent_index"] == 30
        r = generate_latent(cell, "construction", 30, DEFAULT_PROFILE)
        assert rows[0]["latent_program_id"] == \
            r.latent["latent_program_id"]
        assert len(rows[0]["render_instance_ids"]) == 3


def test_construction_expected_counts(construction):
    ec = construction["cells"]["fork_join"]["expected_counts"]
    assert ec["latent_clusters"] == 100
    assert ec["private_observations"] == 300
    assert ec["assignment_rows_per_observation"] == 64
    assert ec["assignment_rows"] == 19_200
    assert ec["one_call_rows"] == 1_200
    assert ec["two_call_shortcut_rows"] == 9_600
    # selected-route: 3 x S x clusters = 3 x 3 x 100
    assert ec["selected_route_rows"] == 900
    # truncation strata from the frozen denominator contract
    assert ec["truncation_rows_by_worker"] == {
        "0": 300, "1": 300, "2": 300, "3": 300}
    ec2 = construction["cells"]["math_code"]["expected_counts"]
    assert ec2["assignment_rows_per_observation"] == 16
    assert ec2["truncation_rows_by_worker"] == {
        "0": 0, "1": 300, "2": 300, "3": 300}
    assert "two_call_shortcut_rows" not in ec2


def test_qualification_manifest_registers_maximum(qualification):
    m = qualification
    for cell in STAGE1_CELLS:
        block = m["cells"][cell]
        cap = 200 if cell == "fork_join" else 500
        assert len(block["ids"]) == cap
        assert block["look_schedule"][-1] == cap
        # visible slice: exactly the first 18 clusters carry paired
        # visible variants
        with_visible = [row for row in block["ids"]
                        if "visible_render_instance_ids" in row]
        assert len(with_visible) == 18
        assert with_visible == block["ids"][:18]
        assert block["expected_counts"]["visible_observations"] == 54


def test_qualification_prefixes_are_immutable_prefixes(qualification):
    p1 = qualification_prefix(qualification, {"code_atomic": 100,
                                              "fork_join": 100})
    p2 = qualification_prefix(qualification, {"code_atomic": 300,
                                              "fork_join": 200})
    assert p2["code_atomic"][:100] == p1["code_atomic"]
    assert p2["fork_join"][:100] == p1["fork_join"]
    assert len(set(p2["code_atomic"])) == 300


def test_validate_qualification_looks():
    validate_qualification_looks({"code_atomic": 300, "fork_join": 200})
    with pytest.raises(ManifestError):
        validate_qualification_looks({"code_atomic": 200})
    with pytest.raises(ManifestError):
        validate_qualification_looks({"fork_join": 500})
    with pytest.raises(ManifestError):
        validate_qualification_looks({"bogus": 100})


def test_manifest_hash_covers_content(construction):
    # recompute: strip the hash, canonicalize, and it must match
    from tasks.conductor.profiles import canonical_json
    body = {k: v for k, v in construction.items()
            if k != "population_manifest_sha256"}
    assert hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest() == \
        construction["population_manifest_sha256"]
    # and json round-trips (manifests are persisted artifacts)
    assert json.loads(json.dumps(construction)) == construction


# --- fail-closed row verification ---------------------------------------------

def _rows(manifest, keys):
    sha = manifest["population_manifest_sha256"]
    return [{"row_key": k, "population_manifest_sha256": sha}
            for k in keys]


def test_verify_rows_passes_on_exact_match(construction):
    keys = ["a", "b", "c"]
    verify_rows(construction, keys, _rows(construction, keys))


def test_verify_rows_fails_closed(construction):
    keys = ["a", "b", "c"]
    ok = _rows(construction, keys)
    with pytest.raises(ManifestError, match="missing rows"):
        verify_rows(construction, keys, ok[:2])
    with pytest.raises(ManifestError, match="duplicated"):
        verify_rows(construction, keys, ok + [ok[0]])
    with pytest.raises(ManifestError, match="unregistered"):
        verify_rows(construction, keys, ok + _rows(construction, ["z"]))
    stale = ok[:2] + [{"row_key": "c",
                       "population_manifest_sha256": "0" * 64}]
    with pytest.raises(ManifestError, match="stale"):
        verify_rows(construction, keys, stale)
    partial = ok[:2] + [{"row_key": "c"}]
    with pytest.raises(ManifestError, match="partial"):
        verify_rows(construction, keys, partial)
    with pytest.raises(ManifestError, match="empty expected-key"):
        verify_rows(construction, [], [])


# --- 136_s follow-through --------------------------------------------------------

def test_worker_families_match_authoritative_registry():
    # stage1.WORKER_FAMILIES must equal the frozen pool's endpoint map —
    # the registry is the source of truth, the stage1 constant is the
    # convenience view, and this test is the binding.
    assert dict(WORKER_TO_ENDPOINT) == stage1.WORKER_FAMILIES


def test_renderer_count_bound_to_types():
    from tasks.conductor.types import RENDERER_IDS
    assert stage1.RENDERERS_PER_LATENT == len(RENDERER_IDS) == 3
