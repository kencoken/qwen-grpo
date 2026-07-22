"""Unit-2 battery: four-worker profile validation, worker-keyed cache
isolation, D11 sharing, singleton runtime, pool-bound v2 traces, and the
executor end-to-end path over the registry pool (106_s §§9.1-9.3)."""

import copy
import hashlib
import json

import pytest

from tasks.conductor import executor, parser, program
from tasks.conductor.cache import CompletionCache, WorkerCompletionCache
from tasks.conductor.executor import WorkflowItem
from tasks.conductor.pool_runtime import (
    FOUR_WORKER_RUNTIME_PROFILE, FourWorkerPool, FourWorkerRuntime,
    PoolTraceWriter, pool_worker_visible_fingerprint,
    selected_worker_fingerprint, validate_pool_profile,
)
from tasks.conductor.profiles import DEFAULT_PROFILE, ProfileError
from tasks.conductor.render import CONTRACT_TASK_LAST
from tasks.conductor.resources import InstanceRegistry
from tasks.conductor.types import InfrastructureError
from tasks.conductor.workerpool import (
    STAGE0_WORKER_POOL, WORKER_NAMES, WORKER_TO_ENDPOINT,
)
from tasks.conductor.workers import Generation

from test_conductor_executor import make_env, perfect_worker


def profile_with(**overrides):
    profile = copy.deepcopy(FOUR_WORKER_RUNTIME_PROFILE)
    profile.update(overrides)
    return profile


# --- §9.1 profile validation -------------------------------------------------

def test_default_pool_profile_validates():
    validate_pool_profile(FOUR_WORKER_RUNTIME_PROFILE)


@pytest.mark.parametrize("mutate,match", [
    (lambda p: p.update(schema_version=1), "schema"),
    (lambda p: p["worker_pool"].pop(3), "frozen Stage-0 registry"),
    (lambda p: p["worker_pool"].append(dict(p["worker_pool"][3])),
     "ids must be exactly"),
    (lambda p: p["worker_pool"][3].update(
        model_revision="0" * 40), "frozen Stage-0 registry"),
    (lambda p: p["worker_pool"][2].update(name="code_3b"),
     "duplicate"),
    (lambda p: p["worker_pool"][0].update(extra="x"), "WorkerSpec"),
    (lambda p: p["worker_runtime"].update(microbatch=16), "singleton-v1"),
    (lambda p: p["prompts"].update(d16_revision="rev9"),
     "bundle revision"),
    (lambda p: p.update(request_contract="worker-blocks-v0"),
     "request_contract"),
    (lambda p: p.pop("worker_pool"), "keys"),
])
def test_pool_profile_fails_closed(mutate, match):
    profile = copy.deepcopy(FOUR_WORKER_RUNTIME_PROFILE)
    mutate(profile)
    with pytest.raises(ProfileError, match=match):
        validate_pool_profile(profile)


# --- fake pool ---------------------------------------------------------------

class FakeFourPool:
    """Deterministic fake honoring the pool interface: family-shared
    system prompts (so workers 2 and 3 render byte-identical requests)
    but per-worker completions (simulating different weights)."""

    _device = "cpu"

    def __init__(self, completions):
        self._completions = completions  # worker_id -> completion text
        self.singleton_calls = []

    def chat_template_sha(self, worker_id):
        return "ct" + "0" * 62

    def system_prompt(self, worker_id):
        return f"SYSTEM_{WORKER_TO_ENDPOINT[worker_id].upper()}"

    def render_request(self, worker_id, user_message):
        return f"{self.system_prompt(worker_id)}\x00{user_message}".encode()

    def generate_singleton(self, worker_id, request):
        self.singleton_calls.append(worker_id)
        text = self._completions[worker_id]
        if callable(text):
            text = text(request)
        return Generation(completion=text, finish_reason="eos",
                          generated_tokens=3,
                          generation_hit_token_cap=False)

    def close(self):
        pass


def build_rt(tmp_path, completions, cache_name="cache.sqlite", **overrides):
    profile = profile_with(cache_path=str(tmp_path / cache_name),
                           **overrides)
    pool = FakeFourPool(completions)
    return FourWorkerRuntime(
        profile, pool, WorkerCompletionCache(profile["cache_path"])), pool


# --- §9.3 cache and fingerprints ---------------------------------------------

def test_workers_2_and_3_share_bytes_but_never_cache_rows(tmp_path):
    rt, pool = build_rt(tmp_path, {2: "<artifact>two</artifact>",
                                   3: "<artifact>three</artifact>"})
    user = "Task:\nsame task\n\nfinal"
    assert pool.render_request(2, user) == pool.render_request(3, user)
    first_w2 = rt.worker_call_batch(2, [user])[0]
    first_w3 = rt.worker_call_batch(3, [user])[0]
    assert first_w2.request_text == first_w3.request_text
    assert first_w2.completion != first_w3.completion
    # Warm pass: each worker gets its OWN cached completion back.
    warm_w2 = rt.worker_call_batch(2, [user])[0]
    warm_w3 = rt.worker_call_batch(3, [user])[0]
    assert warm_w2.cache_hit and warm_w3.cache_hit
    assert warm_w2.completion == "<artifact>two</artifact>"
    assert warm_w3.completion == "<artifact>three</artifact>"
    assert pool.singleton_calls == [2, 3]  # one generation each, ever
    rt.close()


def test_shared_weights_workers_never_share_cache_rows(tmp_path):
    """Workers 0-2 share a checkpoint; identical *user* text still
    renders under different family prompts and distinct selectors."""
    rt, pool = build_rt(tmp_path, {0: "<artifact>L</artifact>",
                                   1: "<artifact>M</artifact>",
                                   2: "<artifact>C</artifact>"})
    fingerprints = set(rt.worker_fingerprints.values())
    assert len(fingerprints) == 4
    user = "Task:\nt\n\nfinal"
    for worker_id in (0, 1, 2):
        record = rt.worker_call_batch(worker_id, [user])[0]
        assert not record.cache_hit
    rt.close()


def test_duplicate_inflight_requests_are_one_singleton_generation(tmp_path):
    rt, pool = build_rt(tmp_path, {2: "<artifact>x</artifact>"})
    records = rt.worker_call_batch(2, ["same", "same", "same"])
    assert [r.cache_hit for r in records] == [False] * 3
    assert pool.singleton_calls == [2]
    rt.close()


def test_worker_visible_fingerprint_shares_across_observation_conditions(
        tmp_path):
    """D11: the Conductor observation condition is outside the
    worker-visible projection, so byte-identical requests share."""
    rt_private, _ = build_rt(tmp_path, {0: "<artifact>1</artifact>"},
                             cache_name="a.sqlite",
                             visibility_condition="private")
    rt_visible, _ = build_rt(tmp_path, {0: "<artifact>1</artifact>"},
                             cache_name="b.sqlite",
                             visibility_condition="visible")
    assert rt_private.worker_visible_fingerprint == \
        rt_visible.worker_visible_fingerprint
    assert rt_private.runtime_profile_fingerprint != \
        rt_visible.runtime_profile_fingerprint
    rt_private.close()
    rt_visible.close()


def test_selected_worker_fingerprint_binds_prompt_and_template():
    spec = STAGE0_WORKER_POOL[2]
    base = selected_worker_fingerprint(
        FOUR_WORKER_RUNTIME_PROFILE, spec, "ct-a", "sp-a")
    assert base.startswith("slw-")
    assert selected_worker_fingerprint(
        FOUR_WORKER_RUNTIME_PROFILE, spec, "ct-b", "sp-a") != base
    assert selected_worker_fingerprint(
        FOUR_WORKER_RUNTIME_PROFILE, spec, "ct-a", "sp-b") != base


def test_runtime_requires_the_worker_cache(tmp_path):
    profile = profile_with(cache_path=str(tmp_path / "cache.sqlite"))
    with pytest.raises(InfrastructureError, match="WorkerCompletionCache"):
        FourWorkerRuntime(profile, FakeFourPool({}),
                          CompletionCache(profile["cache_path"]))


def test_v1_and_v2_caches_are_disjoint_tables(tmp_path):
    path = tmp_path / "cache.sqlite"
    v1 = CompletionCache(path)
    v1.store("wv", "ep", b"req", Generation("c", "eos", 1, False))
    assert len(v1) == 1
    v2 = WorkerCompletionCache(path)
    assert len(v2) == 0  # a v1 row is never consulted by the v2 table
    assert v2.lookup("wv", "ep", b"req") is None
    v1.close()
    v2.close()


def test_unknown_worker_id_is_refused(tmp_path):
    rt, _ = build_rt(tmp_path, {0: "<artifact>1</artifact>"})
    with pytest.raises(InfrastructureError, match="registered pool"):
        rt.worker_call_batch(4, ["u"])
    rt.close()


# --- executor end-to-end over the four-worker runtime ------------------------

def _perfect_completions(latent):
    _, worker_call = perfect_worker(latent)

    def completion_for(request: bytes):
        return worker_call(None, request.decode("utf-8").split("\x00", 1)[1])
    return completion_for


def test_executor_runs_worker_3_through_runtime_with_v2_trace(tmp_path):
    latent, inst, registry, steps = make_env("fork_join")
    worker_ids, _ = perfect_worker(latent)
    swapped = [3 if w == 2 else w for w in worker_ids]
    completion = _perfect_completions(latent)
    rt, pool = build_rt(tmp_path, {w: completion for w in range(4)})
    items = [WorkflowItem(
        item_id="fj", action=parser.routing_to_workflow(swapped, steps),
        public_prompt=inst["public_prompt"], registry=registry,
        request_contract=CONTRACT_TASK_LAST)]

    def call(worker_id, requests):
        return rt.worker_call_batch(worker_id, requests)

    with PoolTraceWriter("run-a", rt, base_dir=tmp_path / "runs") as trace:
        results = executor.execute_workflow_batch(items, call, trace=trace)
    assert results[0].terminal == inst["gold_answer"]

    trace_dir = tmp_path / "runs" / "run-a" / "traces"
    manifest = json.loads((trace_dir / "manifest.json").read_text())
    assert manifest["trace_schema_version"] == 2
    assert manifest["worker_pool_fingerprint"] == rt.pool_fingerprint
    assert set(manifest["worker_fingerprints"]) == set(
        WORKER_NAMES.values())
    physical = {tuple(e["workers"]) for e in manifest["logical_to_physical"]}
    assert physical == {("lookup_1p5b", "math_1p5b", "code_1p5b"),
                        ("code_3b",)}
    lines = [json.loads(line) for line in
             (trace_dir / "steps.jsonl").read_text().splitlines()]
    assert [line["worker_id"] for line in lines] == swapped
    w3_line = next(line for line in lines if line["worker_id"] == 3)
    assert w3_line["worker_name"] == "code_3b"
    assert w3_line["endpoint_family"] == "code"
    assert w3_line["weights_key"][0] == "Qwen/Qwen2.5-3B-Instruct"
    assert w3_line["selected_worker_fp"] == rt.worker_fingerprints[3]
    rt.close()


def test_pool_trace_writer_is_not_the_refused_v1_class(tmp_path):
    from tasks.conductor.executor import TraceWriter
    assert not issubclass(PoolTraceWriter, TraceWriter)


# --- rendering matches the reviewed fixture ----------------------------------

def test_real_pool_rendering_matches_the_pool_fixture():
    """FourWorkerPool must render exactly the bytes the reviewed
    pool_rendered_requests.json fixture pins (108_f F3)."""
    from tasks.conductor import render
    from tasks.conductor.gen_chat_fixtures import FIXTURE_PATH
    try:
        pool = FourWorkerPool(FOUR_WORKER_RUNTIME_PROFILE, device="cpu")
    except OSError as error:
        pytest.skip(f"pinned tokenizers unavailable: {error}")
    fixture = json.loads(FIXTURE_PATH.read_text())
    latent = program.generate_latent("lookup_atomic", "construction", 0,
                                     DEFAULT_PROFILE).latent
    inst = program.render_instance(latent, "resource_first", "private")
    registry = InstanceRegistry(inst["public_manifest"],
                                inst["private_registry"])
    step = program.workflow_steps(latent)[0]
    user = render.build_worker_request(
        inst["public_prompt"], step["subtask"],
        resource_text=registry.payload_text(step["resource"]),
        contract=CONTRACT_TASK_LAST)
    for spec in STAGE0_WORKER_POOL:
        rendered = pool.render_request(spec.worker_id, user)
        assert hashlib.sha256(rendered).hexdigest() == \
            fixture[f"lookup_atomic:step1:{spec.name}"], spec.name
    pool.close()


def test_pool_rejects_a_bundle_that_contradicts_the_registry():
    from tasks.conductor.prompts import resolve_prompts
    with pytest.raises(InfrastructureError, match="registry declares"):
        FourWorkerPool(FOUR_WORKER_RUNTIME_PROFILE, device="cpu",
                       prompts=resolve_prompts("rev9"))
