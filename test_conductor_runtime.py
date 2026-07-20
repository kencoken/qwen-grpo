"""0B battery: runtime profile + fingerprint scopes, SQLite write-through
cache (isolation, telemetry survival, determinism guard), wave-batched
execution vs the sequential contract, JSONL traces + manifest, and the
chat-template byte fixture (spec §1.5, §1.10, §1.13; plan rev6 §8, D11)."""

import copy
import itertools
import json
import sqlite3
from dataclasses import dataclass

import pytest

from tasks.conductor import cache as cache_mod
from tasks.conductor import executor, parser, program, runtime
from tasks.conductor.cache import CompletionCache
from tasks.conductor.executor import TraceWriter, WorkflowItem
from tasks.conductor.profiles import DEFAULT_PROFILE, ProfileError
from tasks.conductor.resources import InstanceRegistry
from tasks.conductor.runtime import (
    DEFAULT_RUNTIME_PROFILE, Runtime, build_runtime, encode_float,
    endpoint_fingerprint, runtime_profile_fingerprint,
    validate_runtime_profile, worker_visible_fingerprint,
)
from tasks.conductor.types import ENDPOINT_NAMES, InfrastructureError
from tasks.conductor.workers import Generation

from test_conductor_executor import ALL_CELLS, make_env, perfect_worker

PROFILE = DEFAULT_RUNTIME_PROFILE


def profile_with(**top_level):
    prof = copy.deepcopy(dict(PROFILE))
    prof.update(top_level)
    return prof


# --- fake pool / deterministic backend --------------------------------------

class FakePool:
    """Backend fake honoring the WorkerPool interface: rendering prefixes
    the endpoint (distinct templates), generation echoes a scripted map or
    a default completion."""

    def __init__(self, script=None, default="<artifact>1</artifact>",
                 telemetry=None):
        self.script = script or {}
        self.default = default
        self.telemetry = telemetry or {}
        self.generate_calls = []

    def chat_template_sha(self, endpoint_name):
        return f"sha-{endpoint_name}"

    def render_request(self, endpoint_name, user_message):
        return f"{endpoint_name}\x00{user_message}".encode()

    def generate(self, endpoint_name, requests):
        self.generate_calls.append((endpoint_name, list(requests)))
        out = []
        for request in requests:
            user = request.decode().split("\x00", 1)[1]
            completion = self.script.get((endpoint_name, user), self.default)
            kwargs = dict(finish_reason="eos", generated_tokens=7,
                          generation_hit_token_cap=False)
            kwargs.update(self.telemetry)
            out.append(Generation(completion=completion, **kwargs))
        return out

    def close(self):
        pass


def make_runtime(tmp_path, profile=None, pool=None, name="cache.sqlite"):
    profile = profile or profile_with(cache_path=str(tmp_path / name))
    return build_runtime(profile, pool=pool or FakePool(),
                         cache=CompletionCache(profile["cache_path"]))


# --- profile schema + encoding ----------------------------------------------

def test_default_profile_validates():
    validate_runtime_profile(PROFILE)


def test_profile_rejects_unknown_and_missing_keys():
    with pytest.raises(ProfileError):
        validate_runtime_profile({**PROFILE, "extra": 1})
    for key in PROFILE:
        broken = {k: v for k, v in PROFILE.items() if k != key}
        with pytest.raises(ProfileError):
            validate_runtime_profile(broken)


def test_profile_rejects_bad_workers():
    prof = copy.deepcopy(dict(PROFILE))
    del prof["workers"]["math"]
    with pytest.raises(ProfileError):
        validate_runtime_profile(prof)
    prof = copy.deepcopy(dict(PROFILE))
    prof["workers"]["math"]["max_new_tokens"] = 0
    with pytest.raises(ProfileError):
        validate_runtime_profile(prof)
    prof = copy.deepcopy(dict(PROFILE))
    prof["workers"]["math"]["microbatch"] = True
    with pytest.raises(ProfileError):
        validate_runtime_profile(prof)


def test_profile_rejects_sampling_and_raw_floats():
    with pytest.raises(ProfileError):
        validate_runtime_profile(profile_with(
            decoding={"do_sample": "true", "stopping": "eos"}))
    # §1.13: float-valued fields are decimal strings, never JSON floats.
    prof = copy.deepcopy(dict(PROFILE))
    prof["batch"]["beta"] = 1e-3
    with pytest.raises(ProfileError):
        validate_runtime_profile(prof)
    prof["batch"]["beta"] = encode_float(1e-3)
    validate_runtime_profile(prof)


def test_encode_float_shortest_round_trip():
    assert encode_float(1e-3) == "0.001"
    assert encode_float(0.1) == "0.1"
    assert float(encode_float(2 / 3)) == 2 / 3


# --- fingerprint scopes (§1.10) ---------------------------------------------

SHAS = {"lookup": "sha-lookup", "math": "sha-math", "code": "sha-code"}


def test_visibility_enters_profile_but_not_worker_visible_fingerprint():
    visible = profile_with(visibility_condition="visible")
    assert (runtime_profile_fingerprint(PROFILE)
            != runtime_profile_fingerprint(visible))
    assert (worker_visible_fingerprint(PROFILE, SHAS)
            == worker_visible_fingerprint(visible, SHAS))


def test_conductor_only_fields_do_not_touch_worker_visible():
    variants = [
        profile_with(profile_name="renamed"),
        profile_with(cache_path="elsewhere.sqlite"),
        profile_with(workflow_max_steps=2),
        profile_with(policy_max_new_tokens=64),
        profile_with(batch={"group_size": 4, "prompt_groups_per_update": 1}),
        profile_with(cell_mixture={**PROFILE["cell_mixture"],
                                   "fork_join": 1}),
    ]
    base = worker_visible_fingerprint(PROFILE, SHAS)
    for variant in variants:
        assert worker_visible_fingerprint(variant, SHAS) == base
        assert (runtime_profile_fingerprint(variant)
                != runtime_profile_fingerprint(PROFILE))


def test_worker_visible_fields_change_worker_visible():
    prof = copy.deepcopy(dict(PROFILE))
    prof["workers"]["math"]["revision"] = "deadbeef"
    variants = [
        prof,
        profile_with(nf4={**PROFILE["nf4"], "double_quant": "false"}),
        profile_with(tools={**PROFILE["tools"], "math": "v0.9"}),
        profile_with(prompts={"d16_revision": "rev999"}),
        profile_with(resource_policy="other-policy"),
    ]
    base = worker_visible_fingerprint(PROFILE, SHAS)
    for variant in variants:
        assert worker_visible_fingerprint(variant, SHAS) != base
    # The resolved chat template is part of the worker-visible scope.
    assert worker_visible_fingerprint(
        PROFILE, {**SHAS, "math": "other"}) != base


def test_endpoint_fingerprints_distinct_and_pinned():
    fps = {name: endpoint_fingerprint(PROFILE, name, SHAS[name])
           for name in SHAS}
    assert len(set(fps.values())) == 3
    assert endpoint_fingerprint(PROFILE, "math", "other") != fps["math"]
    prof = copy.deepcopy(dict(PROFILE))
    prof["workers"]["math"]["max_new_tokens"] = 128
    assert endpoint_fingerprint(prof, "math", SHAS["math"]) != fps["math"]
    with pytest.raises(ProfileError):
        endpoint_fingerprint(PROFILE, "direct", "x")


# --- cache: write-through, isolation, telemetry survival --------------------

def test_write_through_then_hit(tmp_path):
    pool = FakePool(telemetry={"finish_reason": "length",
                               "generation_hit_token_cap": True,
                               "generated_tokens": 256})
    rt = make_runtime(tmp_path, pool=pool)
    first = rt.worker_call_batch("math", ["u1", "u2"])
    assert [r.cache_hit for r in first] == [False, False]
    assert len(pool.generate_calls) == 1
    second = rt.worker_call_batch("math", ["u2", "u1"])
    assert [r.cache_hit for r in second] == [True, True]
    assert len(pool.generate_calls) == 1  # no regeneration
    # §1.10: truncation telemetry survives cache hits.
    assert second[0].finish_reason == "length"
    assert second[0].generation_hit_token_cap is True
    assert second[0].generated_tokens == 256
    assert second[0].completion == first[1].completion
    rt.close()


def test_mixed_hit_miss_preserves_order(tmp_path):
    pool = FakePool(script={("math", "a"): "<artifact>10</artifact>",
                            ("math", "b"): "<artifact>20</artifact>",
                            ("math", "c"): "<artifact>30</artifact>"})
    rt = make_runtime(tmp_path, pool=pool)
    rt.worker_call_batch("math", ["b"])
    records = rt.worker_call_batch("math", ["a", "b", "c"])
    assert [r.cache_hit for r in records] == [False, True, False]
    assert [r.completion for r in records] == [
        "<artifact>10</artifact>", "<artifact>20</artifact>",
        "<artifact>30</artifact>"]
    rt.close()


def test_duplicate_requests_in_one_batch_generate_once(tmp_path):
    pool = FakePool()
    rt = make_runtime(tmp_path, pool=pool)
    records = rt.worker_call_batch("math", ["u", "u", "v", "u"])
    assert len(pool.generate_calls) == 1
    assert [len(reqs) for _, reqs in pool.generate_calls] == [2]  # u, v
    assert [r.cache_hit for r in records] == [False] * 4
    assert records[0].request_sha256 == records[1].request_sha256
    assert len(rt.cache) == 2
    rt.close()


def test_endpoint_isolation_same_user_bytes(tmp_path):
    """Same user message through two endpoints renders differently AND
    carries a different endpoint fingerprint — no cross-endpoint hits."""
    pool = FakePool()
    rt = make_runtime(tmp_path, pool=pool)
    rt.worker_call_batch("math", ["same"])
    records = rt.worker_call_batch("code", ["same"])
    assert records[0].cache_hit is False
    assert len(rt.cache) == 2
    rt.close()


def test_worker_visible_fingerprint_isolates_cache(tmp_path):
    """A capped-tokens change invalidates; a visibility flip does not
    (completions intentionally shared across visibility conditions)."""
    path = str(tmp_path / "shared.sqlite")
    base = profile_with(cache_path=path)
    rt = build_runtime(base, pool=FakePool(),
                       cache=CompletionCache(path))
    rt.worker_call_batch("math", ["u"])
    rt.close()

    visible = profile_with(cache_path=path,
                           visibility_condition="visible")
    rt2 = build_runtime(visible, pool=FakePool(),
                        cache=CompletionCache(path))
    assert rt2.worker_call_batch("math", ["u"])[0].cache_hit is True
    rt2.close()

    capped = copy.deepcopy(base)
    capped["workers"]["math"]["max_new_tokens"] = 64
    rt3 = build_runtime(capped, pool=FakePool(),
                        cache=CompletionCache(path))
    assert rt3.worker_call_batch("math", ["u"])[0].cache_hit is False
    rt3.close()


def test_cache_persists_across_reopen(tmp_path):
    path = tmp_path / "c.sqlite"
    cache = CompletionCache(path)
    gen = Generation("<artifact>5</artifact>", "eos", 4, False)
    cache.store("wv", "ep", b"req", gen)
    cache.close()
    cache2 = CompletionCache(path)
    row = cache2.lookup("wv", "ep", b"req")
    assert row is not None and row.completion == "<artifact>5</artifact>"
    assert cache2.lookup("wv", "other", b"req") is None
    assert cache2.lookup("other", "ep", b"req") is None
    cache2.close()


def test_cache_rejects_greedy_violation_and_allows_identical_restore(tmp_path):
    cache = CompletionCache(tmp_path / "c.sqlite")
    gen = Generation("<artifact>5</artifact>", "eos", 4, False)
    cache.store("wv", "ep", b"req", gen)
    cache.store("wv", "ep", b"req", gen)  # idempotent race is fine
    with pytest.raises(InfrastructureError):
        cache.store("wv", "ep", b"req",
                    Generation("<artifact>6</artifact>", "eos", 4, False))
    cache.close()


def test_cache_detects_corrupted_request_bytes(tmp_path):
    path = tmp_path / "c.sqlite"
    cache = CompletionCache(path)
    cache.store("wv", "ep", b"req", Generation("x", "eos", 1, False))
    conn = sqlite3.connect(path)
    conn.execute("UPDATE completions SET request = ?", (b"other",))
    conn.commit()
    conn.close()
    with pytest.raises(InfrastructureError):
        cache.lookup("wv", "ep", b"req")
    cache.close()


def test_runtime_guards(tmp_path):
    rt = make_runtime(tmp_path)
    with pytest.raises(InfrastructureError):
        rt.worker_call_batch("direct", ["u"])
    rt.close()
    with pytest.raises(InfrastructureError):
        rt.worker_call_batch("math", ["u"])

    class ShortPool(FakePool):
        def generate(self, endpoint_name, requests):
            return super().generate(endpoint_name, requests)[:-1]

    rt2 = make_runtime(tmp_path, pool=ShortPool(), name="c2.sqlite")
    with pytest.raises(InfrastructureError):
        rt2.worker_call_batch("math", ["u1", "u2"])
    rt2.close()


# --- wave-batched execution vs the sequential contract ----------------------

def batch_adapter(worker_call):
    @dataclass(frozen=True)
    class Record:
        completion: str

    def call(worker_id, requests):
        return [Record(worker_call(worker_id, request))
                for request in requests]
    return call


def test_batch_matches_sequential_across_cells():
    """One heterogeneous batch over all six cells reproduces each cell's
    sequential execution record-for-record. The shared batch pool answers
    by full request text, so dispatch is item-exact."""
    items, singles, combined = [], [], {}
    for index, cell in enumerate(ALL_CELLS):
        latent, inst, registry, steps = make_env(cell)
        worker_ids, worker_call = perfect_worker(latent)
        action = parser.routing_to_workflow(worker_ids, steps)
        items.append(WorkflowItem(item_id=f"item-{index}", action=action,
                                  public_prompt=inst["public_prompt"],
                                  registry=registry))
        seq = executor.execute_workflow(action, inst["public_prompt"],
                                        registry, worker_call)
        singles.append(seq)
        for step in seq.steps:
            if step.request is not None and step.completion is not None:
                combined[step.request] = step.completion

    @dataclass(frozen=True)
    class Record:
        completion: str

    def combined_call(worker_id, requests):
        return [Record(combined[request]) for request in requests]

    results = executor.execute_workflow_batch(items, combined_call)
    for result, single, cell in zip(results, singles, ALL_CELLS):
        assert result.terminal == single.terminal, cell
        assert len(result.steps) == len(single.steps)
        for got, want in zip(result.steps, single.steps):
            assert (got.position, got.worker_id, got.request,
                    got.completion, got.override_applied,
                    got.world_failure) == (
                want.position, want.worker_id, want.request,
                want.completion, want.override_applied, want.world_failure)
            assert (got.result is None) == (want.result is None)
            if got.result is not None:
                assert got.result == want.result


def test_batch_matches_sequential_under_sampled_routings():
    """Random (non-reference) routings, overrides and failure propagation:
    the batch path must reproduce the sequential records exactly."""
    latent, inst, registry, steps = make_env("lookup_math")
    _, worker_call = perfect_worker(latent)
    items, singles = [], []
    for index, routing in enumerate(itertools.product((0, 1, 2),
                                                      repeat=len(steps))):
        action = parser.routing_to_workflow(list(routing), steps)
        overrides = {1: 7} if index % 3 == 0 else {}
        singles.append(executor.execute_workflow(
            action, inst["public_prompt"], registry, worker_call,
            overrides=dict(overrides) or None))
        items.append(WorkflowItem(item_id=f"routing-{index}", action=action,
                                  public_prompt=inst["public_prompt"],
                                  registry=registry, overrides=overrides))
    results = executor.execute_workflow_batch(items,
                                              batch_adapter(worker_call))
    for got, want in zip(results, singles):
        assert got.terminal == want.terminal
        assert [(s.position, s.worker_id, s.completion, s.override_applied)
                for s in got.steps] == \
               [(s.position, s.worker_id, s.completion, s.override_applied)
                for s in want.steps]
        assert [s.result for s in got.steps] == [s.result for s in want.steps]


def test_wave_grouping_by_worker_and_depth():
    """Two same-cell items routed to one worker must share a single
    batched call per wave; distinct workers get distinct calls."""
    calls = []

    latent, inst, registry, steps = make_env("lookup_math")
    latent2, inst2, registry2, steps2 = make_env("lookup_math", index=1)
    action = parser.routing_to_workflow([0, 1], steps)
    action2 = parser.routing_to_workflow([0, 2], steps2)
    _, wc1 = perfect_worker(latent)
    _, wc2 = perfect_worker(latent2)

    @dataclass(frozen=True)
    class Record:
        completion: str

    def spy_call(worker_id, requests):
        calls.append((worker_id, len(requests)))
        out = []
        for request in requests:  # dispatch to whichever item's script knows it
            try:
                out.append(Record(wc1(worker_id, request)))
            except KeyError:
                out.append(Record(wc2(worker_id, request)))
        return out

    executor.execute_workflow_batch(
        [WorkflowItem("a", action, inst["public_prompt"], registry),
         WorkflowItem("b", action2, inst2["public_prompt"], registry2)],
        spy_call)
    # wave 1: both items' step 1 on worker 0 in ONE call; wave 2: the
    # items route step 2 to different workers -> one call each.
    assert calls == [(0, 2), (1, 1), (2, 1)]


def test_duplicate_item_ids_raise():
    latent, inst, registry, steps = make_env("lookup_atomic")
    action = parser.routing_to_workflow([0], steps)
    item = WorkflowItem("dup", action, inst["public_prompt"], registry)
    with pytest.raises(InfrastructureError):
        executor.execute_workflow_batch([item, item],
                                        batch_adapter(lambda w, r: ""))


# --- traces -----------------------------------------------------------------

def run_traced_batch(tmp_path, run_name="run-a"):
    pool = FakePool(script={})
    latent, inst, registry, steps = make_env("lookup_atomic")
    _, worker_call = perfect_worker(latent)
    action = parser.routing_to_workflow([0], steps)
    profile = profile_with(cache_path=str(tmp_path / "cache.sqlite"))
    rt = build_runtime(profile, pool=pool,
                       cache=CompletionCache(profile["cache_path"]))

    # route through the runtime so telemetry lands in the trace
    def call(worker_id, requests):
        return rt.worker_call_batch(ENDPOINT_NAMES[worker_id], requests)

    items = [WorkflowItem("lookup_atomic:construction:00000:x:rf:private",
                          action, inst["public_prompt"], registry)]
    with TraceWriter(run_name, rt, base_dir=tmp_path / "runs") as trace:
        results = executor.execute_workflow_batch(items, call, trace=trace)
    rt.close()
    return tmp_path / "runs" / run_name / "traces", results, rt


def test_trace_files_manifest_and_steps(tmp_path):
    trace_dir, results, rt = run_traced_batch(tmp_path)
    manifest = json.loads((trace_dir / "manifest.json").read_text())
    assert manifest["runtime_profile"]["profile_name"] == "stage0b-default"
    assert manifest["runtime_profile_fingerprint"].startswith("rtp-")
    assert manifest["worker_visible_fingerprint"].startswith("wv-")
    assert set(manifest["endpoint_fingerprints"]) == {"lookup", "math",
                                                      "code"}
    assert manifest["closed"] is True
    lines = [json.loads(line) for line in
             (trace_dir / "steps.jsonl").read_text().splitlines()]
    assert manifest["steps_written"] == len(lines) == 1
    line = lines[0]
    assert line["item_id"] == "lookup_atomic:construction:00000:x:rf:private"
    assert line["position"] == 1 and line["worker_id"] == 0
    assert line["finish_reason"] == "eos"
    assert line["cache_hit"] is False
    assert line["generation_hit_token_cap"] is False
    assert line["request_sha256"] is not None
    assert line["completion"] == "<artifact>1</artifact>"


def test_trace_refuses_to_overwrite(tmp_path):
    trace_dir, _, rt = run_traced_batch(tmp_path)
    profile = profile_with(cache_path=str(tmp_path / "cache2.sqlite"))
    rt2 = build_runtime(profile, pool=FakePool(),
                        cache=CompletionCache(profile["cache_path"]))
    with pytest.raises(InfrastructureError):
        TraceWriter("run-a", rt2, base_dir=tmp_path / "runs")
    rt2.close()


# --- chat-template byte fixture (§1.5 canonical rendered request) -----------

def test_chat_template_fixture_stable():
    from tasks.conductor.gen_chat_fixtures import FIXTURE_PATH, build_fixture
    try:
        from tasks.conductor.workers import WorkerPool
        pool = WorkerPool(PROFILE, device="cpu")
    except OSError as error:  # tokenizer cache unavailable offline
        pytest.skip(f"pinned tokenizers unavailable: {error}")
    stored = json.loads(FIXTURE_PATH.read_text())
    assert build_fixture(pool) == stored
    pool.close()
