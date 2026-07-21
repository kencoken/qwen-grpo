"""Worker-eval battery — Tranche A (plan 81_f §8 Gate A): fail-closed
prompt binding, owned runtime configuration, cache-disabled singleton
generation, manifest/call-row provenance."""

import hashlib
import json

import pytest

from tasks.conductor import prompts as prompts_mod
from tasks.conductor.cache import CompletionCache
from tasks.conductor.profiles import ProfileError, canonical_json
from tasks.conductor.prompts import (
    D16_REVISION, PROMPT_REVISIONS, resolve_prompts,
)
from tasks.conductor.runtime import (
    DEFAULT_RUNTIME_PROFILE, build_runtime, runtime_profile_fingerprint,
)
from tasks.conductor.types import InfrastructureError
from tasks.conductor.worker_eval import (
    CACHE_SOURCE_DISABLED, NullCache, REQUEST_CONTRACTS, RunWriter,
    build_manifest, git_provenance, make_called_row,
    resolve_request_contract, singleton_call,
)

from test_conductor_runtime import FakePool, profile_with

BUNDLE = resolve_prompts()


def eval_runtime(pool=None):
    """Cache-disabled runtime over a fake pool whose prompts are the real
    resolved bundle (so manifests bind against actual = declared). The
    cache_path is pinned (Conductor-only key, unused by NullCache) so two
    eval runtimes share a runtime-profile fingerprint."""
    profile = profile_with(cache_path="unused.sqlite")
    pool = pool or FakePool(
        system_prompts={name: BUNDLE.text(name)
                        for name, _ in BUNDLE.prompts})
    return build_runtime(profile, pool=pool, cache=NullCache())


def make_manifest(rt, **overrides):
    kwargs = dict(
        run_id="run-1", purpose="tranche-a-test",
        population={"namespace": "worker_dev", "per_cell": 30,
                    "renderers": ["resource_first", "goal_first",
                                  "bound_var"], "visibility": "private"},
        endpoint_schedule_version="d16-operator-aligned-v1",
        candidate_label="rev0-baseline",
        request_contract_key="worker-blocks-v0",
        expected_calls=2,
        git_info={"commit": "0" * 40, "dirty": False, "diff_sha256": None},
    )
    kwargs.update(overrides)
    return build_manifest(rt, BUNDLE, **kwargs)


# --- prompt binding (81_f §5.2; Gate A) --------------------------------------

def test_unknown_prompt_revision_fails():
    with pytest.raises(ProfileError, match="unknown worker prompt revision"):
        resolve_prompts("rev999")


def test_prompt_content_mismatch_fails_and_names_endpoint():
    good = BUNDLE.sha256()
    with pytest.raises(ProfileError, match="math"):
        resolve_prompts(D16_REVISION,
                        expected_sha256={**good, "math": "0" * 64})
    assert resolve_prompts(D16_REVISION, expected_sha256=good) == BUNDLE


def test_bundle_is_immutable_against_registry_mutation(monkeypatch):
    bundle = resolve_prompts()
    monkeypatch.setitem(PROMPT_REVISIONS[D16_REVISION], "math", "EVIL")
    assert bundle.text("math") != "EVIL"
    # Re-resolving against the previously recorded hashes now fails: the
    # declared revision no longer means the same bytes.
    with pytest.raises(ProfileError, match="math"):
        resolve_prompts(D16_REVISION, expected_sha256=bundle.sha256())


def test_bundle_rejects_unknown_endpoint():
    with pytest.raises(ProfileError):
        BUNDLE.text("direct")


def test_actual_prompt_hash_enters_worker_visible_and_endpoint_scopes():
    base = eval_runtime(pool=FakePool())
    changed = eval_runtime(
        pool=FakePool(system_prompts={"math": "reworded"}))
    assert (base.runtime_profile_fingerprint
            == changed.runtime_profile_fingerprint)
    assert (base.worker_visible_fingerprint
            != changed.worker_visible_fingerprint)
    assert (base.endpoint_fingerprints["math"]
            != changed.endpoint_fingerprints["math"])
    assert (base.endpoint_fingerprints["lookup"]
            == changed.endpoint_fingerprints["lookup"])


# --- owned configuration (81_f §6.2; Gate A) ---------------------------------

def test_caller_mutation_after_build_changes_nothing(tmp_path):
    profile = profile_with(cache_path=str(tmp_path / "unused.sqlite"))
    rt = build_runtime(profile, pool=FakePool(), cache=NullCache())
    before = rt.runtime_profile_fingerprint
    profile["workers"]["code"]["max_new_tokens"] = 1
    profile["decoding"]["do_sample"] = "true"
    assert rt.profile["workers"]["code"]["max_new_tokens"] == 256
    assert runtime_profile_fingerprint(rt.profile) == before


# --- cache-disabled singleton generation (81_f §6.2, §6.5; Gate A) -----------

def test_nullcache_identical_requests_stay_two_generations():
    pool = FakePool()
    rt = eval_runtime(pool=pool)
    first = singleton_call(rt, "math", "same message")
    second = singleton_call(rt, "math", "same message")
    assert len(pool.generate_calls) == 2
    assert all(len(reqs) == 1 for _, reqs in pool.generate_calls)
    assert not first.cache_hit and not second.cache_hit
    assert first.request_sha256 == second.request_sha256


def test_singleton_call_refuses_cache_hits(tmp_path):
    profile = profile_with(cache_path=str(tmp_path / "cache.sqlite"))
    rt = build_runtime(profile, pool=FakePool(),
                       cache=CompletionCache(profile["cache_path"]))
    singleton_call(rt, "math", "message")  # miss: generated, then stored
    with pytest.raises(InfrastructureError, match="cache"):
        singleton_call(rt, "math", "message")


def test_call_record_request_text_round_trips():
    pool = FakePool()
    rt = eval_runtime(pool=pool)
    record = singleton_call(rt, "code", "user msg")
    rendered = pool.render_request("code", "user msg")
    assert record.request_text.encode("utf-8") == rendered
    assert (hashlib.sha256(rendered).hexdigest() == record.request_sha256)


# --- call rows (81_f §5.3; Gate A hash validation) ---------------------------

def row_for(record):
    return make_called_row(
        run_id="run-1", case_id="case-1", observation_id="obs-1",
        position=1, latent_program_id="lp-1", cell_id="math_atomic",
        renderer_id="resource_first", node_id="n1",
        endpoint_name="math", evaluation_mode="isolated",
        predecessor_source="none", predecessor_positions=[],
        generation_ordinal=0, user_message="user msg",
        binding_sha256="b" * 64, record=record)


def test_called_row_hashes_validate():
    rt = eval_runtime()
    record = singleton_call(rt, "math", "user msg")
    row = row_for(record)
    assert row["request_sha256"] == hashlib.sha256(
        row["request_text"].encode("utf-8")).hexdigest()
    assert row["completion_sha256"] == hashlib.sha256(
        row["completion"].encode("utf-8")).hexdigest()
    assert row["cache_source"] == CACHE_SOURCE_DISABLED
    assert (row["physical_batch_size"], row["physical_batch_slot"]) == (1, 0)


def test_called_row_refuses_cache_served_record(tmp_path):
    profile = profile_with(cache_path=str(tmp_path / "cache.sqlite"))
    rt = build_runtime(profile, pool=FakePool(),
                       cache=CompletionCache(profile["cache_path"]))
    rt.worker_call_batch("math", ["m"])
    (hit,) = rt.worker_call_batch("math", ["m"])
    assert hit.cache_hit
    with pytest.raises(InfrastructureError):
        row_for(hit)


# --- request-contract binding (81_f §5.2) ------------------------------------

def test_request_contract_resolves_with_content_digest():
    contract = resolve_request_contract("worker-blocks-v0")
    assert contract["digest"] == hashlib.sha256(canonical_json(
        dict(REQUEST_CONTRACTS["worker-blocks-v0"])).encode()).hexdigest()
    with pytest.raises(ProfileError, match="unknown request contract"):
        resolve_request_contract("task_last")


# --- manifest binding (81_f §5.1; Gate A) ------------------------------------

def test_manifest_binds_actual_prompts(tmp_path):
    rt = eval_runtime()
    manifest = make_manifest(rt)
    assert manifest["system_prompts"]["sha256"] == BUNDLE.sha256()
    assert manifest["system_prompts"]["text"] == dict(BUNDLE.prompts)
    assert manifest["system_prompts"]["revision"] == D16_REVISION
    assert manifest["worker_visible_fingerprint"] \
        == rt.worker_visible_fingerprint
    assert manifest["request_contract"]["key"] == "worker-blocks-v0"
    assert manifest["status"] == "running"


def test_manifest_refuses_declared_actual_prompt_mismatch(tmp_path):
    # Pool renders FakePool defaults, not the declared rev0 strings.
    rt = eval_runtime(pool=FakePool())
    with pytest.raises(ProfileError, match="actually renders"):
        make_manifest(rt)


def test_frozen_candidate_run_refuses_draft_bundle(tmp_path):
    rt = eval_runtime()
    assert BUNDLE.status == "DRAFT"
    with pytest.raises(ProfileError, match="DRAFT"):
        make_manifest(rt, frozen_candidate=True)


def test_manifest_owns_its_profile_copy(tmp_path):
    rt = eval_runtime()
    manifest = make_manifest(rt)
    rt.profile["workers"]["math"]["max_new_tokens"] = 1
    assert manifest["runtime_profile"]["workers"]["math"][
        "max_new_tokens"] == 256


def test_git_provenance_shape():
    info = git_provenance()
    assert len(info["commit"]) == 40
    assert isinstance(info["dirty"], bool)
    assert (info["diff_sha256"] is None) == (not info["dirty"])


# --- run writer (81_f §5.1) --------------------------------------------------

def write_run(tmp_path, rows, expected=None, name="run-1"):
    rt = eval_runtime()
    manifest = make_manifest(
        rt, expected_calls=len(rows) if expected is None else expected)
    writer = RunWriter(tmp_path / name, manifest)
    for row in rows:
        writer.write_call(row)
    return writer


def two_rows(tmp_path):
    rt = eval_runtime()
    return [row_for(singleton_call(rt, "math", f"msg {i}"))
            for i in range(2)]


def read_manifest(run_dir):
    return json.loads((run_dir / "manifest.json").read_text())


def test_writer_refuses_existing_run_dir(tmp_path):
    (tmp_path / "run-1").mkdir()
    rt = eval_runtime()
    with pytest.raises(InfrastructureError, match="already exists"):
        RunWriter(tmp_path / "run-1", make_manifest(rt))


def test_writer_complete_records_counts_and_payload_hashes(tmp_path):
    rows = two_rows(tmp_path)
    writer = write_run(tmp_path, rows)
    writer.close()
    manifest = read_manifest(tmp_path / "run-1")
    assert manifest["status"] == "complete"
    assert manifest["written_rows"] == {"calls": 2}
    calls_bytes = (tmp_path / "run-1" / "calls.jsonl").read_bytes()
    assert manifest["payload_sha256"]["calls.jsonl"] \
        == hashlib.sha256(calls_bytes).hexdigest()
    loaded = [json.loads(line) for line in
              calls_bytes.decode().splitlines()]
    assert loaded == [json.loads(json.dumps(r, sort_keys=True))
                      for r in rows]
    assert writer.manifest_sha256 == hashlib.sha256(
        (tmp_path / "run-1" / "manifest.json").read_bytes()).hexdigest()


def test_writer_exception_marks_run_aborted(tmp_path):
    rows = two_rows(tmp_path)
    rt = eval_runtime()
    with pytest.raises(RuntimeError, match="boom"):
        with RunWriter(tmp_path / "run-1",
                       make_manifest(rt, expected_calls=2)) as writer:
            writer.write_call(rows[0])
            raise RuntimeError("boom")
    manifest = read_manifest(tmp_path / "run-1")
    assert manifest["status"] == "aborted"
    assert manifest["written_rows"] == {"calls": 1}


def test_writer_row_shortfall_cannot_complete(tmp_path):
    rows = two_rows(tmp_path)
    writer = write_run(tmp_path, rows[:1], expected=2)
    with pytest.raises(InfrastructureError, match="planned"):
        writer.close()
    assert read_manifest(tmp_path / "run-1")["status"] == "aborted"


def test_writer_refuses_rows_after_finalize(tmp_path):
    rows = two_rows(tmp_path)
    writer = write_run(tmp_path, rows)
    writer.close()
    with pytest.raises(InfrastructureError, match="finalized"):
        writer.write_call(rows[0])


# --- real-pool prompt binding (skip-guarded like the fixture test) -----------

def test_real_pool_renders_bound_bundle_not_module_globals(monkeypatch):
    try:
        from tasks.conductor.workers import WorkerPool
        pool = WorkerPool(DEFAULT_RUNTIME_PROFILE, device="cpu")
    except OSError as error:
        pytest.skip(f"pinned tokenizers unavailable: {error}")
    rendered = pool.render_request("math", "probe")
    assert BUNDLE.text("math").encode("utf-8") in rendered
    # Post-construction registry mutation must not change rendering.
    monkeypatch.setitem(PROMPT_REVISIONS[D16_REVISION], "math", "EVIL")
    monkeypatch.setitem(prompts_mod.SYSTEM_PROMPTS, "math", "EVIL")
    assert pool.render_request("math", "probe") == rendered
    pool.close()
