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
    but per-worker completions (simulating different weights). Owns its
    profile like the real pool (113_s F1)."""

    def __init__(self, profile, completions):
        self.profile = copy.deepcopy(profile)
        self._completions = completions  # worker_id -> completion text
        self.singleton_calls = []
        self.singleton_generations = 0

    def chat_template_sha(self, worker_id):
        return "ct" + "0" * 62

    def system_prompt(self, worker_id):
        return f"SYSTEM_{WORKER_TO_ENDPOINT[worker_id].upper()}"

    def render_request(self, worker_id, user_message):
        return f"{self.system_prompt(worker_id)}\x00{user_message}".encode()

    def generate_singleton(self, worker_id, request):
        self.singleton_calls.append(worker_id)
        self.singleton_generations += 1
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
    pool = FakeFourPool(profile, completions)
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
        FourWorkerRuntime(profile, FakeFourPool(profile, {}),
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
    rt, pool = build_rt(tmp_path, {w: completion for w in range(4)},
                        device="cpu")
    items = [WorkflowItem(
        item_id="fj", action=parser.routing_to_workflow(swapped, steps),
        public_prompt=inst["public_prompt"], registry=registry,
        request_contract=CONTRACT_TASK_LAST)]

    with PoolTraceWriter("run-a", rt, base_dir=tmp_path / "runs") as trace:
        results, telemetry = rt.execute_batch(items, trace=trace)
    assert results[0].terminal == inst["gold_answer"]
    assert sorted(w for w, _ in telemetry) == sorted(swapped)

    trace_dir = tmp_path / "runs" / "run-a" / "traces"
    manifest = json.loads((trace_dir / "manifest.json").read_text())
    assert manifest["trace_schema_version"] == 2
    assert manifest["worker_pool_fingerprint"] == rt.pool_fingerprint
    assert set(manifest["worker_fingerprints"]) == set(
        WORKER_NAMES.values())
    physical = {tuple(e["workers"]) for e in manifest["logical_to_physical"]}
    assert physical == {("lookup_1p5b", "math_1p5b", "code_1p5b"),
                        ("code_3b",)}
    assert manifest["status"] == "complete"
    lines = [json.loads(line) for line in
             (trace_dir / "steps.jsonl").read_text().splitlines()]
    assert [line["worker_id"] for line in lines] == swapped
    w3_line = next(line for line in lines if line["worker_id"] == 3)
    assert w3_line["worker_name"] == "code_3b"
    assert w3_line["endpoint_family"] == "code"
    assert w3_line["physical_key"]["model_id"] == "Qwen/Qwen2.5-3B-Instruct"
    assert w3_line["physical_key"]["device"] == "cpu"
    assert w3_line["physical_key"]["quantization"] == \
        FOUR_WORKER_RUNTIME_PROFILE["nf4"]
    assert w3_line["selected_worker_fp"] == rt.worker_fingerprints[3]
    assert w3_line["endpoint_family_fp"] == \
        rt.endpoint_family_fingerprints["code"]
    assert w3_line["runtime_profile_fingerprint"] == \
        rt.runtime_profile_fingerprint
    # 113_s F4: exact request provenance on every real-call row.
    for line in lines:
        assert line["binding_sha256"]
        assert line["user_message"].startswith("Problem:")
        assert line["request_text"].endswith(line["user_message"])
        import hashlib as _h
        assert _h.sha256(line["request_text"].encode()).hexdigest() == \
            line["request_sha256"]
    rt.close()


def test_pool_trace_writer_is_not_the_refused_v1_class(tmp_path):
    from tasks.conductor.executor import TraceWriter
    assert not issubclass(PoolTraceWriter, TraceWriter)


# --- rendering matches the reviewed fixture ----------------------------------

def test_real_pool_rendering_matches_the_pool_fixture():
    """FourWorkerPool must render exactly the bytes the reviewed
    pool_rendered_requests.json fixture pins (108_s F3)."""
    from tasks.conductor import render
    from tasks.conductor.gen_chat_fixtures import FIXTURE_PATH
    try:
        pool = FourWorkerPool(profile_with(device="cpu"))
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
        FourWorkerPool(profile_with(device="cpu"),
                       prompts=resolve_prompts("rev9"))


# =============================================================================
# 113_s findings: execution-identity binding, frozen treatments, device.
# =============================================================================

@pytest.mark.parametrize("mutate,match", [
    (lambda p: p["worker_runtime"].update(max_new_tokens=1),
     "256-token singleton"),
    (lambda p: p["nf4"].update(compute_dtype="float16"), "frozen NF4"),
    (lambda p: p["tools"].update(code="invented-v9"), "TOOL_VERSIONS"),
    (lambda p: p.update(resource_policy="invented-policy"),
     "resource_policy"),
    (lambda p: p.update(device=""), "device"),
])
def test_frozen_treatment_settings_admit_no_variation(mutate, match):
    """113_s F2: a declared setting the executor does not run is
    fabricated provenance."""
    profile = copy.deepcopy(FOUR_WORKER_RUNTIME_PROFILE)
    mutate(profile)
    with pytest.raises(ProfileError, match=match):
        validate_pool_profile(profile)


def test_runtime_refuses_a_pool_with_a_different_profile(tmp_path):
    """113_s F1: fingerprints must describe what the pool executes."""
    profile_a = profile_with(cache_path=str(tmp_path / "a.sqlite"))
    profile_b = profile_with(cache_path=str(tmp_path / "b.sqlite"),
                             visibility_condition="visible")
    pool_b = FakeFourPool(profile_b, {})
    with pytest.raises(InfrastructureError, match="pool profile"):
        FourWorkerRuntime(profile_a, pool_b,
                          WorkerCompletionCache(profile_a["cache_path"]))


def test_execute_batch_preflights_the_request_contract(tmp_path):
    """113_s F1: a default (v0-contract) WorkflowItem cannot execute
    under a task_last profile, and no worker call happens first."""
    latent, inst, registry, steps = make_env("lookup_atomic")
    rt, pool = build_rt(tmp_path, {0: "<artifact>1</artifact>"})
    item = WorkflowItem(  # default request_contract = v0
        item_id="i", action=parser.routing_to_workflow([0], steps),
        public_prompt=inst["public_prompt"], registry=registry)
    with pytest.raises(InfrastructureError, match="request contract"):
        rt.execute_batch([item])
    assert pool.singleton_calls == []
    rt.close()


def test_execute_batch_refuses_a_foreign_trace(tmp_path):
    latent, inst, registry, steps = make_env("lookup_atomic")
    rt_a, _ = build_rt(tmp_path, {0: "<artifact>1</artifact>"},
                       cache_name="a.sqlite")
    rt_b, _ = build_rt(tmp_path, {0: "<artifact>1</artifact>"},
                       cache_name="b.sqlite",
                       visibility_condition="visible")
    item = WorkflowItem(
        item_id="i", action=parser.routing_to_workflow([0], steps),
        public_prompt=inst["public_prompt"], registry=registry,
        request_contract=CONTRACT_TASK_LAST)
    trace_b = PoolTraceWriter("run-b", rt_b, base_dir=tmp_path / "runs")
    with pytest.raises(InfrastructureError, match="bound to this runtime"):
        rt_a.execute_batch([item], trace=trace_b)
    trace_b.close("aborted")
    rt_a.close()
    rt_b.close()


def test_trace_write_verifies_the_producing_call_record(tmp_path):
    """113_s F4: a CallRecord from another worker or runtime cannot be
    recorded under this trace's fingerprints."""
    import dataclasses
    latent, inst, registry, steps = make_env("lookup_atomic")
    rt, _ = build_rt(tmp_path, {0: "<artifact>1</artifact>"})
    item = WorkflowItem(
        item_id="i", action=parser.routing_to_workflow([0], steps),
        public_prompt=inst["public_prompt"], registry=registry,
        request_contract=CONTRACT_TASK_LAST)
    trace = PoolTraceWriter("run-a", rt, base_dir=tmp_path / "runs")
    record = rt.worker_call_batch(0, ["user"])[0]
    step = executor.StepRecord(1, 0, None, None, "user", record.completion,
                               False, "bind")
    forged_worker = dataclasses.replace(
        record, selected_worker_fp=rt.worker_fingerprints[1])
    with pytest.raises(InfrastructureError, match="producer fingerprint"):
        trace.write_step("i", step, forged_worker)
    forged_runtime = dataclasses.replace(
        record, runtime_fingerprint="rtp-0000000000000000")
    with pytest.raises(InfrastructureError, match="different runtime"):
        trace.write_step("i", step, forged_runtime)
    forged_bytes = dataclasses.replace(record, request_text="tampered")
    with pytest.raises(InfrastructureError, match="hash"):
        trace.write_step("i", step, forged_bytes)
    trace.write_step("i", step, record)  # the genuine record passes
    trace.close()
    rt.close()


def test_device_is_execution_and_cache_identity(tmp_path):
    """113_s F3: a CPU-configured runtime must not serve CUDA-produced
    cache rows — device is in wv and slw, so the lookup misses."""
    rt_cuda, _ = build_rt(tmp_path, {0: "<artifact>cuda</artifact>"},
                          device="cuda")
    rt_cpu, pool_cpu = build_rt(tmp_path,
                                {0: "<artifact>cpu</artifact>"},
                                device="cpu")
    assert rt_cuda.worker_visible_fingerprint != \
        rt_cpu.worker_visible_fingerprint
    assert rt_cuda.worker_fingerprints[0] != rt_cpu.worker_fingerprints[0]
    # Same cache file: the CUDA-produced row is invisible to the CPU
    # runtime's key, so it generates its own.
    rt_cuda.worker_call_batch(0, ["u"])
    record = rt_cpu.worker_call_batch(0, ["u"])[0]
    assert not record.cache_hit
    assert record.completion == "<artifact>cpu</artifact>"
    rt_cuda.close()
    rt_cpu.close()


def test_aborted_execution_marks_the_trace_aborted(tmp_path):
    rt, _ = build_rt(tmp_path, {0: "<artifact>1</artifact>"})
    with pytest.raises(RuntimeError):
        with PoolTraceWriter("run-a", rt,
                             base_dir=tmp_path / "runs") as trace:
            raise RuntimeError("boom")
    manifest = json.loads(
        (tmp_path / "runs" / "run-a" / "traces"
         / "manifest.json").read_text())
    assert manifest["status"] == "aborted"
    assert manifest["closed"] is True
    rt.close()


# =============================================================================
# 115_s findings: provenance immutability, preflight bypass, per-cell bound.
# =============================================================================

def test_runtime_provenance_is_immutable_after_construction(tmp_path):
    """115_s F1: neither the caller's dict nor the profile property can
    move preflight or trace metadata off the recorded fingerprints."""
    profile = profile_with(cache_path=str(tmp_path / "cache.sqlite"))
    pool = FakeFourPool(profile, {0: "<artifact>1</artifact>"})
    rt = FourWorkerRuntime(profile, pool,
                           WorkerCompletionCache(profile["cache_path"]))
    rtp_before = rt.runtime_profile_fingerprint
    # Mutating the caller's original changes nothing.
    profile["device"] = "mutated"
    profile["request_contract"] = "worker-blocks-v0"
    # Mutating the returned property changes nothing either.
    view = rt.profile
    view["device"] = "mutated"
    view["request_contract"] = "worker-blocks-v0"
    assert rt.profile["device"] == "cuda"
    assert rt.profile["request_contract"] == CONTRACT_TASK_LAST
    assert rt.runtime_profile_fingerprint == rtp_before
    # A v0 item is still refused after both mutation attempts.
    latent, inst, registry, steps = make_env("lookup_atomic")
    item = WorkflowItem(
        item_id="i", action=parser.routing_to_workflow([0], steps),
        public_prompt=inst["public_prompt"], registry=registry)
    with pytest.raises(InfrastructureError, match="request contract"):
        rt.execute_batch([item])
    with pytest.raises(TypeError):
        rt.worker_fingerprints[0] = "forged"  # type: ignore[index]
    rt.close()


def test_public_executor_composition_cannot_bypass_the_preflight(tmp_path):
    """115_s F2: the reviewer's reproduction — executor +
    worker_call_batch + a bound v2 trace — raises before any call."""
    latent, inst, registry, steps = make_env("lookup_atomic")
    rt, pool = build_rt(tmp_path, {0: "<artifact>1</artifact>"})
    item = WorkflowItem(  # default v0 contract
        item_id="i", action=parser.routing_to_workflow([0], steps),
        public_prompt=inst["public_prompt"], registry=registry)
    trace = PoolTraceWriter("run-a", rt, base_dir=tmp_path / "runs")
    with pytest.raises(InfrastructureError, match="request contract"):
        executor.execute_workflow_batch([item], rt.worker_call_batch,
                                        trace=trace)
    assert pool.singleton_calls == []
    trace.close("aborted")
    rt.close()


def test_smoke_per_cell_bound_is_enforced():
    """115_s F3: an index past the consumed 0-29 construction prefix
    is rejected before any runtime or cache construction."""
    from tasks.conductor.smoke import validate_per_cell
    assert validate_per_cell(2) == 2
    assert validate_per_cell(30) == 30
    for bad in (0, 31, -1):
        with pytest.raises(SystemExit, match="per-cell"):
            validate_per_cell(bad)


def test_trace_write_rejects_internally_inconsistent_records(tmp_path):
    """115_s P2 hardening: swapped same-worker records, missing binding
    hashes and non-rerendering user messages all refuse to persist."""
    import dataclasses
    latent, inst, registry, steps = make_env("lookup_atomic")
    rt, pool = build_rt(
        tmp_path,
        {0: lambda req: f"<artifact>{len(req)}</artifact>"})
    trace = PoolTraceWriter("run-a", rt, base_dir=tmp_path / "runs")
    record = rt.worker_call_batch(0, ["user"])[0]
    good = executor.StepRecord(1, 0, None, None, "user",
                               record.completion, False, "bind")
    # Same worker, different call record (swapped completion).
    other = rt.worker_call_batch(0, ["other user"])[0]
    with pytest.raises(InfrastructureError, match="completion"):
        trace.write_step("i", good, dataclasses.replace(
            other, request_text=record.request_text,
            request_sha256=record.request_sha256))
    # A real call without a binding hash.
    unbound = executor.StepRecord(1, 0, None, None, "user",
                                  record.completion, False, None)
    with pytest.raises(InfrastructureError, match="binding"):
        trace.write_step("i", unbound, record)
    # A user message that does not re-render to the recorded bytes.
    mismatched = executor.StepRecord(1, 0, None, None, "tampered user",
                                     record.completion, False, "bind")
    with pytest.raises(InfrastructureError, match="re-render"):
        trace.write_step("i", mismatched, record)
    trace.write_step("i", good, record)  # the consistent row persists
    trace.close()
    rt.close()
