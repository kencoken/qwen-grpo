"""Unit-2 acceptance tests — 132_s §4 population/provenance layer
(138_f, rev2 per 139_s).

Beyond the 138_f coverage, this exercises every attack the 139_s review
reproduced: a construction manifest presented as a qualification
manifest, an id mutated after hashing, truncated support, a modified but
schema-valid profile, caller-attested expected keys, and rows lacking an
execution identity.
"""

import hashlib
import json

import pytest

from tasks.conductor import stage1
from tasks.conductor.grpo_smoke import SOURCE_DIGEST_FILES
from tasks.conductor.profiles import DEFAULT_PROFILE, canonical_json
from tasks.conductor.program import generate_latent
from tasks.conductor.stage1_manifest import (
    ManifestError, REGISTERED_PROFILE_VERSIONS, STAGE1_CELLS,
    build_stage1_env_manifest, expected_row_keys, qualification_prefix,
    register_construction_population, register_qualification_population,
    stage1_source_digest, stage1_source_files,
    validate_population_manifest, validate_qualification_looks,
    verify_gate_rows,
)
from tasks.conductor.workerpool import WORKER_TO_ENDPOINT

CONSTRUCTION_KIND = "stage1-construction-population-v1"
QUALIFICATION_KIND = "stage1-qualification-population-v1"


def _rehash(manifest):
    """Re-finalize a (tampered) manifest so only content checks can
    catch it — used to prove validation is not hash-only."""
    body = {k: v for k, v in manifest.items()
            if k != "population_manifest_sha256"}
    manifest = dict(manifest)
    manifest["population_manifest_sha256"] = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    return manifest


# --- successor source digest ---------------------------------------------------

def test_source_list_superset_of_eight_plus_floor():
    files = stage1_source_files()
    assert set(SOURCE_DIGEST_FILES) < set(files)
    for path in stage1.SUCCESSOR_DIGEST_REQUIRED_ADDITIONS:
        assert path in files
    assert list(files) == sorted(set(files))
    assert "tasks/conductor/stage1.py" in files
    assert "tasks/conductor/stage1_manifest.py" in files
    assert "tasks/conductor/pool_runtime.py" in files   # the 125_s gap
    assert "tasks/conductor/executor.py" in files


def test_source_digest_is_not_the_stage0_digest():
    d = stage1_source_digest()
    assert len(d) == 64
    assert not d.startswith("688f7e06")
    assert not d.startswith("9f9fe6f6")


def test_env_manifest_is_execution_only():
    # build_stage1_env_manifest queries the GPU and content-addresses
    # itself; its dirty-tree refusal and hash field are structural
    # contracts asserted in 140_f — not invoked in unit tests.
    assert callable(build_stage1_env_manifest)


# --- registrars ------------------------------------------------------------------

@pytest.fixture(scope="module")
def construction():
    return register_construction_population(DEFAULT_PROFILE)


@pytest.fixture(scope="module")
def qualification(construction):
    return register_qualification_population(construction)


def test_construction_manifest_identity(construction):
    m = construction
    assert m["manifest"] == CONSTRUCTION_KIND
    assert m["index_range"] == [30, 130]
    assert m["profile_version"] == stage1.PRIMARY_PROFILE_VERSION
    validate_population_manifest(m, kind=CONSTRUCTION_KIND)
    again = register_construction_population(DEFAULT_PROFILE)
    assert again["population_manifest_sha256"] == \
        m["population_manifest_sha256"]


def test_construction_ids_match_generation(construction):
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
    assert ec["selected_route_rows"] == 900
    assert ec["truncation_rows_by_worker"] == {
        "0": 300, "1": 300, "2": 300, "3": 300}
    # 139_s finding 4: complete independent grid + intervention edges
    assert ec["independent_node_execution_rows"] == 300 * 3 * 4
    assert ec["intervention_rows_by_edge"] == {
        "n1->n3": 300, "n2->n3": 300}
    assert ec["b1_fitting_rows"] == 100
    ec2 = construction["cells"]["math_code"]["expected_counts"]
    assert ec2["independent_node_execution_rows"] == 300 * 2 * 4
    assert ec2["intervention_rows_by_edge"] == {"n1->n2": 300}
    assert "two_call_shortcut_rows" not in ec2
    ec3 = construction["cells"]["lookup_atomic"]["expected_counts"]
    assert ec3["intervention_rows_by_edge"] == {}


def test_qualification_consumes_construction_manifest(construction,
                                                      qualification):
    m = qualification
    assert m["construction_manifest_sha256"] == \
        construction["population_manifest_sha256"]
    assert m["profile_version"] == construction["profile_version"]
    validate_population_manifest(m, kind=QUALIFICATION_KIND)
    # and it cannot be built from a non-manifest
    with pytest.raises(ManifestError):
        register_qualification_population({"manifest": "bogus"})


def test_qualification_registers_maximum_with_per_look_blocks(
        qualification):
    for cell in STAGE1_CELLS:
        block = qualification["cells"][cell]
        cap = 200 if cell == "fork_join" else 500
        assert len(block["ids"]) == cap
        with_visible = [row for row in block["ids"]
                        if "visible_render_instance_ids" in row]
        assert len(with_visible) == 18
        assert with_visible == block["ids"][:18]
        looks = block["look_schedule"]
        per_look = block["expected_counts"]["per_look"]
        assert set(per_look) == {str(look) for look in looks}
        first = per_look[str(looks[0])]
        assert first["latent_clusters"] == looks[0]
        assert first["visible_observations"] == 54  # 18 x 3 within look 100


# --- 139_s finding 2: frozen profile enforcement ---------------------------------

def test_registered_candidates_are_the_frozen_set():
    assert REGISTERED_PROFILE_VERSIONS == {stage1.PRIMARY_PROFILE_VERSION}


def test_modified_but_valid_profile_is_rejected():
    tampered = json.loads(json.dumps(DEFAULT_PROFILE))
    tampered["cells"]["math_code"]["L_band"] = [8, 12]  # schema-valid
    with pytest.raises(ManifestError, match="not a registered candidate"):
        register_construction_population(tampered)


# --- 139_s finding 1: consumption-time validation ---------------------------------

def test_wrong_kind_rejected(construction, qualification):
    # the reviewer's reproduction: construction accepted as qualification
    with pytest.raises(ManifestError, match="kind"):
        qualification_prefix(construction, {"code_atomic": 100})
    with pytest.raises(ManifestError, match="kind"):
        validate_population_manifest(construction,
                                     kind=QUALIFICATION_KIND)
    with pytest.raises(ManifestError, match="kind"):
        validate_population_manifest(qualification,
                                     kind=CONSTRUCTION_KIND)


def test_mutated_id_rejected_even_after_rehash(qualification):
    tampered = json.loads(json.dumps(qualification))
    tampered["cells"]["code_atomic"]["ids"][7]["latent_program_id"] = \
        "code_atomic:qualification:00007:deadbeef"
    # without rehash: hash mismatch
    with pytest.raises(ManifestError, match="hash mismatch"):
        validate_population_manifest(tampered, kind=QUALIFICATION_KIND)
    # WITH rehash: the id fails first-principles regeneration
    with pytest.raises(ManifestError, match="regenerate"):
        validate_population_manifest(_rehash(tampered),
                                     kind=QUALIFICATION_KIND)


def test_truncated_support_rejected(qualification):
    tampered = json.loads(json.dumps(qualification))
    tampered["cells"]["fork_join"]["ids"] = \
        tampered["cells"]["fork_join"]["ids"][:150]
    with pytest.raises(ManifestError):
        validate_population_manifest(_rehash(tampered),
                                     kind=QUALIFICATION_KIND)


def test_tampered_counts_rejected(construction):
    tampered = json.loads(json.dumps(construction))
    tampered["cells"]["math_code"]["expected_counts"][
        "assignment_rows"] -= 16
    with pytest.raises(ManifestError, match="recompute"):
        validate_population_manifest(_rehash(tampered),
                                     kind=CONSTRUCTION_KIND)


def test_visible_slice_misplacement_rejected(qualification):
    tampered = json.loads(json.dumps(qualification))
    del tampered["cells"]["math_atomic"]["ids"][3][
        "visible_render_instance_ids"]
    with pytest.raises(ManifestError, match="visible-slice placement"):
        validate_population_manifest(_rehash(tampered),
                                     kind=QUALIFICATION_KIND)


def test_prefixes_are_immutable_prefixes(qualification):
    p1 = qualification_prefix(qualification, {"code_atomic": 100,
                                              "fork_join": 100})
    p2 = qualification_prefix(qualification, {"code_atomic": 300,
                                              "fork_join": 200})
    assert p2["code_atomic"][:100] == p1["code_atomic"]
    assert p2["fork_join"][:100] == p1["fork_join"]
    assert len(set(p2["code_atomic"])) == 300


def test_validate_qualification_looks_hardened():
    validate_qualification_looks({"code_atomic": 300, "fork_join": 200})
    with pytest.raises(ManifestError):
        validate_qualification_looks({})            # empty (139_s)
    with pytest.raises(ManifestError):
        validate_qualification_looks({"code_atomic": 100.0})  # float
    with pytest.raises(ManifestError):
        validate_qualification_looks({"code_atomic": True})   # bool
    with pytest.raises(ManifestError):
        validate_qualification_looks({"code_atomic": 200})
    with pytest.raises(ManifestError):
        validate_qualification_looks({"fork_join": 500})
    with pytest.raises(ManifestError):
        validate_qualification_looks({"bogus": 100})


# --- 139_s finding 3: derived denominators + execution identity -------------------

EXEC_SHA = "c" * 64


def _rows(manifest, keys):
    sha = manifest["population_manifest_sha256"]
    return [{"row_key": k, "population_manifest_sha256": sha,
             "execution_manifest_sha256": EXEC_SHA} for k in keys]


def test_expected_keys_derived_not_supplied(construction):
    keys = expected_row_keys(construction, kind=CONSTRUCTION_KIND,
                             cell="math_code", gate="truncation",
                             worker=2)
    # 100 clusters x 3 renderers x 1 on-contract node (n2) for worker 2
    assert len(keys) == 300
    assert all(k.endswith("|n2|w2|truncation") for k in keys)
    grid = expected_row_keys(construction, kind=CONSTRUCTION_KIND,
                             cell="math_code", gate="node_execution")
    assert len(grid) == 300 * 2 * 4
    interv = expected_row_keys(construction, kind=CONSTRUCTION_KIND,
                               cell="fork_join", gate="intervention")
    assert len(interv) == 600
    assert any("n1->n3" in k for k in interv)
    # counts agree with the manifest's registered expectation
    ec = construction["cells"]["math_code"]["expected_counts"]
    assert len(grid) == ec["independent_node_execution_rows"]


def test_expected_keys_selected_route_requires_deployable(construction):
    with pytest.raises(ManifestError, match="deployable"):
        expected_row_keys(construction, kind=CONSTRUCTION_KIND,
                          cell="math_code", gate="selected_route")
    keys = expected_row_keys(construction, kind=CONSTRUCTION_KIND,
                             cell="math_code", gate="selected_route",
                             deployable={"n1": 1, "n2": 3})
    assert len(keys) == 600
    assert all("|w1|" in k or "|w3|" in k for k in keys)


def test_expected_keys_reject_empty_denominator(construction):
    # worker 0 has no on-contract nodes in math_code: not evaluable
    with pytest.raises(ManifestError, match="not evaluable"):
        expected_row_keys(construction, kind=CONSTRUCTION_KIND,
                          cell="math_code", gate="truncation", worker=0)


def test_expected_keys_look_prefix(construction, qualification):
    full = expected_row_keys(qualification, kind=QUALIFICATION_KIND,
                             cell="code_atomic", gate="node_execution")
    look = expected_row_keys(qualification, kind=QUALIFICATION_KIND,
                             cell="code_atomic", gate="node_execution",
                             clusters=100)
    assert len(full) == 500 * 3 * 1 * 4
    assert len(look) == 100 * 3 * 1 * 4
    assert look < full


def test_verify_gate_rows_pass_and_fail_closed(construction):
    kw = dict(kind=CONSTRUCTION_KIND, cell="math_code",
              gate="truncation", worker=2,
              execution_manifest_sha256=EXEC_SHA)
    keys = sorted(expected_row_keys(construction, kind=CONSTRUCTION_KIND,
                                    cell="math_code", gate="truncation",
                                    worker=2))
    ok = _rows(construction, keys)
    verify_gate_rows(construction, rows=ok, **kw)
    with pytest.raises(ManifestError, match="missing rows"):
        verify_gate_rows(construction, rows=ok[:-1], **kw)
    with pytest.raises(ManifestError, match="duplicated"):
        verify_gate_rows(construction, rows=ok + [ok[0]], **kw)
    with pytest.raises(ManifestError, match="unregistered"):
        verify_gate_rows(construction,
                         rows=ok + _rows(construction, ["z"]), **kw)
    stale = list(ok)
    stale[0] = dict(stale[0], population_manifest_sha256="0" * 64)
    with pytest.raises(ManifestError, match="stale"):
        verify_gate_rows(construction, rows=stale, **kw)
    foreign = list(ok)
    foreign[0] = dict(foreign[0], execution_manifest_sha256="d" * 64)
    with pytest.raises(ManifestError, match="foreign execution"):
        verify_gate_rows(construction, rows=foreign, **kw)
    partial = list(ok)
    partial[0] = {"row_key": partial[0]["row_key"],
                  "population_manifest_sha256":
                      construction["population_manifest_sha256"]}
    with pytest.raises(ManifestError, match="partial"):
        verify_gate_rows(construction, rows=partial, **kw)
    with pytest.raises(ManifestError, match="64 lowercase hex"):
        verify_gate_rows(construction, rows=ok,
                         **{**kw, "execution_manifest_sha256": "short"})


def test_verify_gate_rows_validates_manifest_first(construction):
    tampered = _rehash({**json.loads(json.dumps(construction)),
                        "profile_version": "dp-0000000000000000"})
    with pytest.raises(ManifestError, match="registered"):
        verify_gate_rows(tampered, kind=CONSTRUCTION_KIND,
                         cell="math_code", gate="truncation", worker=2,
                         rows=[], execution_manifest_sha256=EXEC_SHA)


# --- 136_s follow-through ----------------------------------------------------------

def test_worker_families_match_authoritative_registry():
    assert dict(WORKER_TO_ENDPOINT) == stage1.WORKER_FAMILIES


def test_renderer_count_bound_to_types():
    from tasks.conductor.types import RENDERER_IDS
    assert stage1.RENDERERS_PER_LATENT == len(RENDERER_IDS) == 3


def test_manifest_json_round_trips(construction, qualification):
    assert json.loads(json.dumps(construction)) == construction
    assert json.loads(json.dumps(qualification)) == qualification
