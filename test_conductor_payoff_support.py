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
    assert 0 < manifest["unique_singleton_generations"] <= 804
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
    ("drop", "incomplete"),
    ("duplicate", "duplicate"),
    ("foreign", "not in the declared support"),
    ("payoff", "world-outcome ladder"),
    ("declaration", "different support declaration"),
])
def test_loader_fails_closed(tmp_path, fake_declaration, corrupt, match):
    rt, declaration = fake_declaration
    out = tmp_path / "surface"
    materialize_support(rt, out)
    payoffs = (out / "payoffs.jsonl").read_text().splitlines()
    if corrupt == "drop":
        (out / "payoffs.jsonl").write_text("\n".join(payoffs[:-1]) + "\n")
    elif corrupt == "duplicate":
        (out / "payoffs.jsonl").write_text(
            "\n".join(payoffs + [payoffs[0]]) + "\n")
    elif corrupt == "foreign":
        row = json.loads(payoffs[0])
        row["observation_id"] = "not_a_cell:worker_dev:00099:x:rf:private"
        (out / "payoffs.jsonl").write_text(
            "\n".join(payoffs + [json.dumps(row)]) + "\n")
    elif corrupt == "payoff":
        row = json.loads(payoffs[0])
        row["payoff"] = 0.0
        (out / "payoffs.jsonl").write_text(
            "\n".join([json.dumps(row)] + payoffs[1:]) + "\n")
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
