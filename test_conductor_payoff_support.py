"""Unit-3 battery: identity-selected support declaration, 4^S surface
materialization and fail-closed loading, the w2/w3 disagreement canary
record, and the retained-request sentinels (106_s §§9.4-9.5)."""

import json

import pytest

from tasks.conductor import payoff_support, program
from tasks.conductor.cache import WorkerCompletionCache
from tasks.conductor.payoff_support import (
    build_support_declaration, load_support_surface, materialize_support,
    run_sentinels, support_observations,
)
from tasks.conductor.pool_runtime import FourWorkerRuntime
from tasks.conductor.profiles import DEFAULT_PROFILE
from tasks.conductor.types import InfrastructureError

from test_conductor_executor import perfect_worker
from test_conductor_pool_runtime import FakeFourPool, profile_with


def _union_completions():
    """One completion function answering every support task correctly
    (by Task block), whatever worker renders it."""
    by_task = {}
    for obs in support_observations():
        _, worker_call = perfect_worker(obs["latent"])
        latent = obs["latent"]
        for step in program.workflow_steps(latent):
            request = f"Task:\n{step['subtask']}\n\nx"
            by_task[step["subtask"]] = worker_call(None, request)

    def completion(request: bytes) -> str:
        user = request.decode("utf-8").split("\x00", 1)[1]
        task = user.split("Task:\n", 1)[1].split("\n\n", 1)[0]
        return by_task[task]
    return completion


def fake_rt(tmp_path):
    profile = profile_with(cache_path=str(tmp_path / "cache.sqlite"),
                           device="cpu")
    completion = _union_completions()
    pool = FakeFourPool(profile, {w: completion for w in range(4)})
    return FourWorkerRuntime(
        profile, pool, WorkerCompletionCache(profile["cache_path"]))


@pytest.fixture
def fake_declaration(tmp_path, monkeypatch):
    """Bind the declaration to the fake runtime's identity so CPU tests
    can materialize; the committed real declaration binds the real
    tokenizers and the cuda device."""
    rt = fake_rt(tmp_path)
    declaration = build_support_declaration(rt.pool)
    path = tmp_path / "stage0_support.json"
    path.write_text(json.dumps(declaration, indent=1, sort_keys=True)
                    + "\n")
    monkeypatch.setattr(payoff_support, "DECLARATION_PATH", path)
    return rt, declaration


# --- declaration -------------------------------------------------------------

def test_committed_declaration_matches_the_frozen_identity_rule():
    committed = json.loads(
        payoff_support.DECLARATION_PATH.read_text())
    observations = support_observations()
    assert len(observations) == 18
    assert [obs["observation_id"] for obs in observations] == \
        [obs["observation_id"] for obs in committed["observations"]]
    counts = sorted(obs["assignments"]
                    for obs in committed["observations"])
    assert counts == [4] * 9 + [16] * 6 + [64] * 3
    assert committed["planned_step_executions"] == 804
    assert committed["ordinal"] == 0
    assert committed["worker_pool_fingerprint"] == "wp-197e286115f56e4a"
    assert committed["request_contract"] == "worker-blocks-task-last-v1"
    assert committed["device"] == "cuda"


# --- materialization and fail-closed loading ---------------------------------

def test_materialize_and_verify_roundtrip(tmp_path, fake_declaration):
    rt, declaration = fake_declaration
    manifest = materialize_support(rt, tmp_path / "surface")
    assert manifest["payoff_rows"] == 9 * 4 + 6 * 16 + 3 * 64  # 324
    assert manifest["planned_step_executions"] == 804
    assert 0 < manifest["unique_singleton_generations"] \
        <= manifest["uncached_step_records"] <= 804
    surface = load_support_surface(tmp_path / "surface")
    assert len(surface) == 324
    assert set(surface.values()) <= {0.5, 1.0}
    # The reference assignment reaches gold under the perfect fake:
    # payoff 1.0 for every observation's family-canonical routing.
    from tasks.conductor.agreement import ENDPOINT_FOR_OP
    for obs in support_observations():
        nodes = {n["id"]: n
                 for n in obs["latent"]["reference_program"]["nodes"]}
        reference = tuple(
            ENDPOINT_FOR_OP[nodes[node]["op"]]
            for node in sorted(nodes))
        assert surface[(obs["observation_id"], reference)] == 1.0
    # A second materialization into the same directory refuses.
    with pytest.raises(InfrastructureError, match="refusing"):
        materialize_support(rt, tmp_path / "surface")
    rt.close()


def test_materialize_refuses_a_mismatched_runtime(tmp_path):
    """The committed real declaration binds real tokenizers and cuda;
    the fake runtime must be refused."""
    rt = fake_rt(tmp_path)
    with pytest.raises(InfrastructureError, match="worker-visible"):
        materialize_support(rt, tmp_path / "surface")
    rt.close()


@pytest.mark.parametrize("corrupt,match", [
    # Content-hash-consistent corruptions (the _tamper helper rehashes
    # payoffs.jsonl so each downstream check is isolated); an
    # un-rehashed edit is caught earlier by the 118_s content binding.
    ("drop", "incomplete"),
    ("duplicate", "duplicate"),
    ("foreign", "not in the declared support"),
    ("payoff", "re-scored"),
    ("unhashed", "manifest content hash"),
    ("declaration", "regenerated support description"),
])
def test_loader_fails_closed(tmp_path, fake_declaration, corrupt, match):
    rt, declaration = fake_declaration
    out = tmp_path / "surface"
    materialize_support(rt, out)
    if corrupt == "drop":
        _tamper(out, mutate_row=lambda rows: rows.pop())
    elif corrupt == "duplicate":
        _tamper(out, mutate_row=lambda rows: rows.append(rows[0]))
    elif corrupt == "foreign":
        def foreign(rows):
            row = dict(rows[0])
            row["observation_id"] = \
                "not_a_cell:worker_dev:00099:x:rf:private"
            rows.append(row)
        _tamper(out, mutate_row=foreign)
    elif corrupt == "payoff":
        def zero(rows):
            rows[0]["payoff"] = 0.0
        _tamper(out, mutate_row=zero)
    elif corrupt == "unhashed":
        def flip(rows):
            rows[0]["payoff"] = 0.0
        _tamper(out, mutate_row=flip, rehash=False)
    elif corrupt == "declaration":
        path = payoff_support.DECLARATION_PATH
        declaration["planned_step_executions"] = 805
        path.write_text(json.dumps(declaration, indent=1, sort_keys=True)
                        + "\n")
    with pytest.raises(InfrastructureError, match=match):
        load_support_surface(out)
    rt.close()


# --- canary ------------------------------------------------------------------

def test_canary_record_regenerates_and_sits_outside_the_support():
    canary = json.loads(payoff_support.CANARY_PATH.read_text())
    latent = program.generate_latent(
        canary["cell_id"], canary["namespace"], canary["ordinal"],
        DEFAULT_PROFILE).latent
    inst = program.render_instance(latent, canary["renderer_id"],
                                   canary["visibility"])
    assert inst["render_instance_id"] == canary["observation_id"]
    assert canary["ordinal"] != 0 and not canary["in_ordinal0_support"]
    support_ids = {obs["observation_id"]
                   for obs in support_observations()}
    assert canary["observation_id"] not in support_ids
    expected = canary["expected"]
    assert expected["worker_2_correct"] != expected["worker_3_correct"]
    assert canary["provenance"]  # source artifacts hashed


# --- sentinels ---------------------------------------------------------------

def test_sentinel_fixture_matches_the_pool_rendering():
    """Continuity check: the retained rendered-request hashes must be
    exactly what the four-worker pool renders today (both workers)."""
    from tasks.conductor.pool_runtime import FourWorkerPool
    sentinels = json.loads(payoff_support.SENTINELS_PATH.read_text())
    assert len(sentinels["cases"]) == 6
    try:
        pool = FourWorkerPool(profile_with(device="cpu"))
    except OSError as error:
        pytest.skip(f"pinned tokenizers unavailable: {error}")
    import hashlib
    for entry in sentinels["cases"]:
        for worker in (2, 3):
            rendered = pool.render_request(worker, entry["user_message"])
            assert hashlib.sha256(rendered).hexdigest() == \
                entry["request_sha256"], (entry["case_id"], worker)
    pool.close()


def test_sentinels_refuse_a_pool_that_renders_differently(tmp_path):
    rt = fake_rt(tmp_path)
    with pytest.raises(InfrastructureError, match="rendered request"):
        run_sentinels(rt.pool, "23")
    with pytest.raises(InfrastructureError, match="order"):
        run_sentinels(rt.pool, "24")
    rt.close()


# =============================================================================
# 118_s findings: independent re-scoring, provenance binding, visibility.
# =============================================================================

def _tamper(out, mutate_row=None, mutate_manifest=None, rehash=True):
    """Apply a mutation and (optionally) keep the content hashes
    consistent, isolating the check under test."""
    payoff_path = out / "payoffs.jsonl"
    if mutate_row is not None:
        rows = [json.loads(l) for l in payoff_path.read_text().splitlines()]
        mutate_row(rows)
        payoff_path.write_text(
            "\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n")
    manifest = json.loads((out / "manifest.json").read_text())
    if rehash:
        import hashlib
        manifest["payoffs_sha256"] = hashlib.sha256(
            payoff_path.read_bytes()).hexdigest()
    if mutate_manifest is not None:
        mutate_manifest(manifest)
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n")


def test_loader_rescores_payoffs_from_terminal_values(
        tmp_path, fake_declaration):
    """118_s F1: the reviewer's reproduction — flipping a genuine 0.5
    row to payoff 1.0 must abort, because the stored terminal outcome
    re-scores to 0.5 against the regenerated gold."""
    rt, _ = fake_declaration
    out = tmp_path / "surface"
    materialize_support(rt, out)

    def flip(rows):
        row = next(r for r in rows if r["payoff"] == 0.5)
        row["payoff"] = 1.0
    _tamper(out, mutate_row=flip)
    with pytest.raises(InfrastructureError, match="re-scored"):
        load_support_surface(out)
    rt.close()


@pytest.mark.parametrize("mutate_manifest,match", [
    (lambda m: m.update(worker_pool_fingerprint="wp-0000000000000000"),
     "does not match the declaration"),
    (lambda m: m.update(runtime_profile_fingerprint="rtp-000000000000"),
     "does not match the surface manifest"),
    (lambda m: m.update(executed_step_records=10_000),
     "accounting"),
    (lambda m: m.update(payoff_rows=999), "payoff rows"),
    (lambda m: m.update(surface_schema_version=99), "schema"),
    (lambda m: m.update(invented_field=1), "keys"),
])
def test_loader_verifies_manifest_provenance(
        tmp_path, fake_declaration, mutate_manifest, match):
    """118_s F2: invented fingerprints, contradictory counts and
    off-schema manifests all abort."""
    rt, _ = fake_declaration
    out = tmp_path / "surface"
    materialize_support(rt, out)
    _tamper(out, mutate_manifest=mutate_manifest)
    with pytest.raises(InfrastructureError, match=match):
        load_support_surface(out)
    rt.close()


def test_loader_verifies_trace_artifacts(tmp_path, fake_declaration):
    """118_s F2: a tampered or incomplete trace invalidates the
    surface — a fabricated directory with no real trace cannot pass."""
    rt, _ = fake_declaration
    out = tmp_path / "surface"
    materialize_support(rt, out)
    steps = out / "traces" / "traces" / "steps.jsonl"
    lines = steps.read_text().splitlines()
    steps.write_text("\n".join(lines[:-1]) + "\n")
    with pytest.raises(InfrastructureError, match="trace steps.jsonl"):
        load_support_surface(out)
    rt.close()


def test_loader_rejects_mistyped_rows(tmp_path, fake_declaration):
    rt, _ = fake_declaration
    out = tmp_path / "surface"
    materialize_support(rt, out)

    def booleanize(rows):
        rows[0]["assignment"] = [bool(w) for w in rows[0]["assignment"]]
    _tamper(out, mutate_row=booleanize)
    with pytest.raises(InfrastructureError, match="mistyped"):
        load_support_surface(out)
    rt.close()


def test_visible_runtime_cannot_materialize_the_private_support(
        tmp_path, fake_declaration, monkeypatch):
    """118_s F3: visibility sits outside the worker-visible
    fingerprint, so it is checked explicitly against the declaration."""
    _, declaration = fake_declaration
    profile = profile_with(cache_path=str(tmp_path / "v.sqlite"),
                           device="cpu",
                           visibility_condition="visible")
    pool = FakeFourPool(profile, {w: _union_completions()
                                  for w in range(4)})
    rt = FourWorkerRuntime(
        profile, pool, WorkerCompletionCache(profile["cache_path"]))
    with pytest.raises(InfrastructureError, match="visibility"):
        materialize_support(rt, tmp_path / "surface-visible")
    rt.close()


def test_canary_requires_the_exact_registered_direction(
        tmp_path, monkeypatch):
    """118_s smaller finding: a reversed disagreement must fail."""
    from tasks.conductor.payoff_support import run_canary
    canary = json.loads(payoff_support.CANARY_PATH.read_text())
    latent = program.generate_latent(
        canary["cell_id"], canary["namespace"], canary["ordinal"],
        DEFAULT_PROFILE).latent
    _, worker_call = perfect_worker(latent)

    def completion_for(request: bytes):
        return worker_call(None, request.decode().split("\x00", 1)[1])

    # Fake pool matching the registered direction: w2 wrong, w3 right.
    profile = profile_with(cache_path=str(tmp_path / "c.sqlite"),
                           device="cpu")
    pool = FakeFourPool(profile, {2: "no artifact", 3: completion_for})
    rt = FourWorkerRuntime(
        profile, pool, WorkerCompletionCache(profile["cache_path"]))
    outcome = run_canary(rt)
    assert outcome["rewards"] == {"2": 0.5, "3": 1.0}
    rt.close()

    # Reversed direction: differs, but must FAIL the exact check.
    profile2 = profile_with(cache_path=str(tmp_path / "c2.sqlite"),
                            device="cpu")
    pool2 = FakeFourPool(profile2, {2: completion_for, 3: "no artifact"})
    rt2 = FourWorkerRuntime(
        profile2, pool2, WorkerCompletionCache(profile2["cache_path"]))
    with pytest.raises(InfrastructureError, match="registered direction"):
        run_canary(rt2)
    rt2.close()
