"""Worker-eval battery — Tranche A (plan 81_f §8 Gate A): fail-closed
prompt binding, owned runtime configuration, cache-disabled singleton
generation, manifest/call-row provenance."""

import hashlib
import json

import pytest

from dataclasses import replace

from tasks.conductor import contract, program
from tasks.conductor import prompts as prompts_mod
from tasks.conductor.agreement import reference_artifact
from tasks.conductor.cache import CompletionCache
from tasks.conductor.profiles import DEFAULT_PROFILE, ProfileError, \
    canonical_json
from tasks.conductor.prompts import (
    D16_REVISION, PROMPT_REVISIONS, resolve_prompts,
)
from tasks.conductor.resources import InstanceRegistry
from tasks.conductor.runtime import (
    DEFAULT_RUNTIME_PROFILE, build_runtime, runtime_profile_fingerprint,
)
from tasks.conductor.tools import Binding
from tasks.conductor.types import CELL_IDS, RENDERER_IDS, \
    InfrastructureError
from tasks.conductor.worker_eval import (
    CACHE_SOURCE_DISABLED, NullCache, REQUEST_CONTRACTS, RunWriter,
    build_manifest, build_node_cases, case_identities, endpoint_schedule,
    git_provenance, make_called_row, node_cases_for_latent, parse_stages,
    resolve_request_contract, run_node_cases, score_node_calls,
    singleton_call,
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
    result = contract.run_worker_output(1, record.completion, Binding())
    return make_called_row(
        run_id="run-1", case_id="case-1", observation_id="obs-1",
        position=1, latent_program_id="lp-1", cell_id="math_atomic",
        renderer_id="resource_first", node_id="n1",
        endpoint_name="math", evaluation_mode="isolated",
        predecessor_source="none", predecessor_positions=[],
        generation_ordinal=0, user_message="user msg",
        binding_sha256="b" * 64, record=record, result=result,
        stages=parse_stages(record.completion, result))


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
    writer.write_summary({"note": "tranche-a-test"})
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
    assert manifest["written_rows"] == {"calls": 2, "scores": 0}
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
    assert manifest["written_rows"] == {"calls": 1, "scores": 0}


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


# =============================================================================
# Tranche B (plan 81_f §8 Gate B): isolated node cases with gold
# predecessors, strict external scoring, authorization boundaries.
# =============================================================================

POPULATION = {"namespace": "construction", "per_cell": 1,
              "renderers": list(RENDERER_IDS), "visibility": "private"}


def generate_latents(population):
    latents = {}
    for cell in CELL_IDS:
        for index in range(population["per_cell"]):
            latent = program.generate_latent(
                cell, population["namespace"], index, DEFAULT_PROFILE).latent
            latents[latent["latent_program_id"]] = latent
    return latents


def reference_script(cases, labels, latents):
    """FakePool script answering every case with its node's reference
    artifact — the perfect worker."""
    case_by_id = {case.case_id: case for case in cases}
    return {(case_by_id[lab.case_id].endpoint_name,
             case_by_id[lab.case_id].user_message):
            "<artifact>"
            + reference_artifact(latents[lab.latent_program_id], lab.node_id)
            + "</artifact>"
            for lab in labels}


def run_isolated(cases, labels, script):
    rt = eval_runtime(pool=FakePool(script=script, default="garbage"))
    rows = run_node_cases(rt, cases, None, case_identities(labels))
    return rows, score_node_calls(rows, labels)


def fixture_latent():
    return program.generate_latent("math_code", "construction", 19,
                                   DEFAULT_PROFILE).latent


# --- Gate B: reference artifacts score 100% ----------------------------------

def test_reference_artifacts_score_100_across_cells_and_renderers():
    cases, labels = build_node_cases(POPULATION)
    latents = generate_latents(POPULATION)
    rows, scores = run_isolated(cases, labels,
                                reference_script(cases, labels, latents))
    assert len(rows) == len(cases) == 30  # scheduled == called
    assert all(score["node_correct"] for score in scores)
    strata = {(s["cell_id"], s["renderer_id"]) for s in scores}
    assert strata == {(cell, renderer) for cell in CELL_IDS
                      for renderer in RENDERER_IDS}
    assert all(row["cache_source"] == CACHE_SOURCE_DISABLED for row in rows)


# --- Gate B: the rev9 legal-but-wrong fixture is detected --------------------

REV9_FIXTURE_COMPLETION = ("<artifact>at(rotate_left(stable_unique("
                           "resource), 2), step_1)</artifact>")


def test_rev9_math_code_index19_fixture_scores_incorrect():
    cases, labels = node_cases_for_latent(fixture_latent(),
                                          ["resource_first"], "private")
    (code_case, code_label), = [(c, l) for c, l in zip(cases, labels)
                                if l.node_family == "code"]
    script = {(code_case.endpoint_name, code_case.user_message):
              REV9_FIXTURE_COMPLETION}
    rows, scores = run_isolated([code_case], [code_label], script)
    (row,), (score,) = rows, scores
    # Protocol-successful: legal artifact, tool executed, status success.
    assert row["status"] == "success"
    assert row["artifact_valid"] and row["tool_executed"]
    assert row["envelope_outcome"] == "ok"
    assert row["grammar_outcome"] == "ok"
    # Reference-node incorrect: 17 versus 64 (78_s finding 1).
    assert score["observed_value"] == 17
    assert score["expected_value"] == 64
    assert not score["node_correct"]


# --- Gate B: downstream nodes are called with gold predecessors --------------

def test_downstream_called_with_gold_after_upstream_failure():
    latent = fixture_latent()
    cases, labels = node_cases_for_latent(latent, ["resource_first"],
                                          "private")
    case_by_id = {case.case_id: case for case in cases}
    (math_label,), (code_label,) = (
        [lab for lab in labels if lab.node_family == family]
        for family in ("math", "code"))
    code_case = case_by_id[code_label.case_id]
    # Upstream math emits garbage; downstream code answers correctly.
    script = {(code_case.endpoint_name, code_case.user_message):
              "<artifact>"
              + reference_artifact(latent, code_label.node_id)
              + "</artifact>"}
    rows, scores = run_isolated(cases, labels, script)
    by_case = {score["case_id"]: score for score in scores}
    # Both scheduled nodes were called: no survivor selection.
    assert len(rows) == 2
    assert all(row["call_status"] == "called" for row in rows)
    assert not by_case[math_label.case_id]["node_correct"]
    assert by_case[code_label.case_id]["node_correct"]
    # The downstream request used the gold predecessor, not the produced
    # (failed) one, through the ordinary Previous-results channel.
    assert code_label.predecessor_source == "gold"
    assert code_case.steps == ((1, math_label.expected_value),)
    assert f"step_1 = {math_label.expected_value}" in code_case.user_message


# --- Gate B: target mutation does not change execution -----------------------

def test_target_mutation_changes_scores_only():
    cases, labels = node_cases_for_latent(fixture_latent(),
                                          ["resource_first"], "private")
    latents = {labels[0].latent_program_id: fixture_latent()}
    script = reference_script(cases, labels, latents)
    rows, scores = run_isolated(cases, labels, script)
    assert all(score["node_correct"] for score in scores)
    mutated = [replace(label, expected_value=label.expected_value + 1)
               for label in labels]
    mutated_scores = score_node_calls(rows, mutated)
    assert all(not score["node_correct"] for score in mutated_scores)
    assert [s["observed_value"] for s in mutated_scores] \
        == [s["observed_value"] for s in scores]
    # Cases are label-free and deterministic: a rebuild is identical.
    rebuilt, _ = node_cases_for_latent(fixture_latent(),
                                       ["resource_first"], "private")
    assert rebuilt == cases


# --- authorization boundaries (81_f §4.2; test 9.1.8) ------------------------

def test_isolated_cases_expose_only_authorized_inputs():
    latent = program.generate_latent("fork_join", "construction", 0,
                                     DEFAULT_PROFILE).latent
    cases, labels = node_cases_for_latent(latent, ["resource_first"],
                                          "private")
    steps = program.workflow_steps(latent)
    inst = program.render_instance(latent, "resource_first", "private")
    registry = InstanceRegistry(inst["public_manifest"],
                                inst["private_registry"])
    for case, label in zip(cases, labels):
        authorized = steps[label.position - 1]["resource"]
        assert [h for h, _ in case.resources] \
            == ([authorized] if authorized else [])
        # No other registry payload appears in the request.
        for handle in registry.manifest:
            if handle != authorized:
                assert registry.payload_text(handle) \
                    not in case.user_message
        # Only strictly earlier positions are exposed, as gold values.
        assert all(k < label.position for k, _ in case.steps)
        # The node's own expected value has no channel into the binding.
        assert all(v != label.expected_value or k < label.position
                   for k, v in case.steps)


def test_schedule_is_semantic_and_positions_derive_order():
    latent = program.generate_latent("fork_join", "construction", 0,
                                     DEFAULT_PROFILE).latent
    schedule = endpoint_schedule(latent)
    positions = latent["reference_program"]["positions"]
    ops = {n["id"]: n["op"] for n in latent["reference_program"]["nodes"]}
    assert set(schedule) == set(ops)  # keyed by semantic node, not position
    cases, labels = node_cases_for_latent(latent, ["resource_first"],
                                          "private")
    for case, label in zip(cases, labels):
        assert label.position == 1 + positions.index(label.node_id)
        assert case.endpoint_name == schedule[label.node_id]


# --- parse-stage attribution (81_f §5.3; test 9.1.11) ------------------------

def stage_of(completion, endpoint=1):
    result = contract.run_worker_output(endpoint, completion, Binding())
    return parse_stages(completion, result), result


def test_envelope_and_grammar_stage_e_parse_distinguished():
    envelope, result = stage_of("</artifact>1<artifact>")
    assert result.rejection_code == "E_PARSE"
    assert envelope == {"envelope_outcome": "E_PARSE",
                        "grammar_outcome": None}
    grammar, result = stage_of("<artifact>((</artifact>")
    assert result.rejection_code == "E_PARSE"
    assert grammar == {"envelope_outcome": "ok",
                       "grammar_outcome": "E_PARSE"}
    success, result = stage_of("<artifact>1</artifact>")
    assert result.status == "success"
    assert success == {"envelope_outcome": "ok", "grammar_outcome": "ok"}


def test_stage_record_must_agree_with_terminal_result():
    with pytest.raises(InfrastructureError, match="disagrees"):
        parse_stages("</artifact>1<artifact>", contract.success_result(1))


# --- strict score joining (81_f §5.4) ----------------------------------------

def test_score_join_rejects_missing_extra_duplicate_and_drift():
    cases, labels = node_cases_for_latent(fixture_latent(),
                                          ["resource_first"], "private")
    latents = {labels[0].latent_program_id: fixture_latent()}
    rows, _ = run_isolated(cases, labels,
                           reference_script(cases, labels, latents))
    with pytest.raises(InfrastructureError, match="missing"):
        score_node_calls(rows[:1], labels)
    with pytest.raises(InfrastructureError, match="duplicate"):
        score_node_calls(rows + [rows[0]], labels)
    with pytest.raises(InfrastructureError, match="extra"):
        score_node_calls(rows, labels[:1])
    drifted = [dict(rows[0], renderer_id="goal_first")] + rows[1:]
    with pytest.raises(InfrastructureError, match="disagrees"):
        score_node_calls(drifted, labels)


# --- population plan validation ----------------------------------------------

def test_population_plan_validation_fails_closed():
    with pytest.raises(ProfileError, match="population keys"):
        build_node_cases({"namespace": "construction"})
    with pytest.raises(ProfileError, match="renderers"):
        build_node_cases({**POPULATION, "renderers": ["cursive"]})
    with pytest.raises(ProfileError, match="per_cell"):
        build_node_cases({**POPULATION, "per_cell": 0})
    with pytest.raises(ProfileError, match="cap"):
        build_node_cases({**POPULATION, "per_cell": 10 ** 9})
    with pytest.raises(ProfileError, match="endpoint schedule"):
        build_node_cases(POPULATION,
                         endpoint_schedule_version="payoff-surface-v1")
    with pytest.raises(ProfileError, match="unknown request contract"):
        build_node_cases(POPULATION, request_contract_key="task_last")


# =============================================================================
# Tranche C (plan 81_f §8 Gate C): renderer crossing, composed workflow
# diagnostic, derived summaries, strict loader, narrow run comparison.
# =============================================================================

import shutil

from tasks.conductor.prompts import PromptBundle
from tasks.conductor.worker_eval import (
    build_workflow_plan, check_renderer_support, compare_worker_eval_runs,
    load_run, run_composed_workflows, score_workflow_calls,
    summarize_worker_eval,
)

ONE_RENDERER_POP = {**POPULATION, "renderers": ["resource_first"]}


# --- renderer crossing (81_f §4.5; Gate C) -----------------------------------

def test_renderer_support_missing_duplicate_and_extra_fail():
    _, labels = node_cases_for_latent(fixture_latent(),
                                      list(RENDERER_IDS), "private")
    check_renderer_support(labels, list(RENDERER_IDS))
    missing = [lab for lab in labels if lab.renderer_id != "goal_first"]
    with pytest.raises(InfrastructureError, match="renderer support"):
        check_renderer_support(missing, list(RENDERER_IDS))
    duplicated = labels + [labels[0]]
    with pytest.raises(InfrastructureError, match="renderer support"):
        check_renderer_support(duplicated, list(RENDERER_IDS))
    with pytest.raises(InfrastructureError, match="renderer support"):
        check_renderer_support(labels, ["resource_first"])  # extra support


# --- composed workflows (81_f §4.3; Gate C denominators) ---------------------

def composed_script():
    """Reference completions keyed by user message: identical to the
    isolated script because produced values equal gold when every step
    answers correctly."""
    cases, labels = build_node_cases(ONE_RENDERER_POP)
    latents = generate_latents(ONE_RENDERER_POP)
    return reference_script(cases, labels, latents)


def test_composed_reference_run_reconciles_and_scores_terminal():
    rt = eval_runtime(pool=FakePool(script=composed_script(),
                                    default="garbage"))
    rows, wlabels = run_composed_workflows(rt, ONE_RENDERER_POP, None)
    scores = score_workflow_calls(rows, wlabels)
    assert len(scores) == 6 and all(s["terminal_correct"] for s in scores)
    summary = summarize_worker_eval({"run_id": "unwritten"}, rows, scores)
    steps = summary["composed"]["steps"]
    assert steps == {"scheduled": 10, "called": 10,
                     "dependency_blocked": 0,
                     "pre_call_world_failure": 0, "synthetic": 0}
    assert summary["composed"]["terminal_correct"] == 6


def test_composed_upstream_failure_blocks_downstream_and_reconciles():
    script = composed_script()
    cases, labels = build_node_cases(ONE_RENDERER_POP)
    case_by_id = {c.case_id: c for c in cases}
    # Remove the math step of math_code: it falls to the garbage default.
    (math_case,) = [case_by_id[lab.case_id] for lab in labels
                    if lab.cell_id == "math_code"
                    and lab.node_family == "math"]
    del script[(math_case.endpoint_name, math_case.user_message)]
    rt = eval_runtime(pool=FakePool(script=script, default="garbage"))
    rows, wlabels = run_composed_workflows(rt, ONE_RENDERER_POP, None)
    scores = score_workflow_calls(rows, wlabels)
    summary = summarize_worker_eval({"run_id": "unwritten"}, rows, scores)
    steps = summary["composed"]["steps"]
    # The blocked downstream step is a distinct category, and the four
    # categories partition the scheduled denominator exactly (§4.3).
    assert steps == {"scheduled": 10, "called": 9,
                     "dependency_blocked": 1,
                     "pre_call_world_failure": 0, "synthetic": 0}
    assert summary["composed"]["terminal_correct"] == 5
    (blocked,) = [r for r in rows
                  if r["call_status"] == "dependency_blocked"]
    assert blocked["cell_id"] == "math_code"
    assert blocked["completion"] is None and blocked["request_text"] is None
    # Survivor-selection contrast: the isolated run calls all ten.
    iso_rt = eval_runtime(pool=FakePool(script=composed_script(),
                                        default="garbage"))
    iso_rows = run_node_cases(iso_rt, cases, None, case_identities(labels))
    assert len(iso_rows) == 10
    assert all(r["call_status"] == "called" for r in iso_rows)


# --- hand-calculated paired-renderer fixture (Gate C) ------------------------

def test_hand_calculated_paired_renderer_summary():
    def score(latent, renderer, correct):
        return {"row_type": "node", "run_id": "run-h", "case_id":
                f"{latent}:{renderer}", "call_role": "on_contract_reference",
                "latent_program_id": latent, "cell_id": "code_atomic",
                "renderer_id": renderer, "node_id": "n1",
                "node_family": "code", "position": 1,
                "endpoint_name": "code", "predecessor_source": "none",
                "observed_value": 1, "expected_value": 1 if correct else 2,
                "node_correct": correct, "scorer_version": "v"}

    def call(latent, renderer):
        return {"run_id": "run-h", "evaluation_mode": "isolated",
                "call_status": "called", "generation_hit_token_cap": False,
                "envelope_outcome": "ok", "grammar_outcome": "ok",
                "tool_executed": True, "status": "success"}

    outcomes = {("L1", "resource_first"): True, ("L1", "goal_first"): True,
                ("L1", "bound_var"): False, ("L2", "resource_first"): True,
                ("L2", "goal_first"): True, ("L2", "bound_var"): True}
    scores = [score(lat, rend, ok) for (lat, rend), ok in outcomes.items()]
    calls = [call(lat, rend) for (lat, rend) in outcomes]
    summary = summarize_worker_eval({"run_id": "run-h"}, calls, scores)
    isolated = summary["isolated"]
    # Hand calculation: 6 scores, 5 correct; bound_var is the worst
    # renderer at 1/2; L1 flips across renderers, L2 does not.
    assert isolated["node_correct"] == {"n": 6, "correct": 5}
    assert isolated["by_renderer"] == {
        "resource_first": {"n": 2, "correct": 2},
        "goal_first": {"n": 2, "correct": 2},
        "bound_var": {"n": 2, "correct": 1}}
    assert isolated["worst_renderer"] == {"renderer_id": "bound_var",
                                          "n": 2, "correct": 1}
    assert isolated["paired"] == {"groups": 2, "flipped": 1}
    assert isolated["by_stratum"]["code|code_atomic|code|bound_var"] \
        == {"n": 2, "correct": 1}


# --- full run round trip through the strict loader (tests 6/15/16/19) --------

def bundle_pool(**kwargs):
    """FakePool rendering the real resolved bundle prompts, so
    manifests bind (declared == actual)."""
    return FakePool(system_prompts={name: BUNDLE.text(name)
                                    for name, _ in BUNDLE.prompts},
                    **kwargs)


def write_isolated_run(tmp_path, name="run-iso"):
    cases, labels = build_node_cases(POPULATION)
    latents = generate_latents(POPULATION)
    script = reference_script(cases, labels, latents)
    rt = eval_runtime(pool=bundle_pool(script=script, default="garbage"))
    manifest = make_manifest(rt, population=POPULATION,
                             expected_calls=len(cases),
                             expected_scores=len(labels))
    with RunWriter(tmp_path / name, manifest) as writer:
        rows = run_node_cases(rt, cases, writer, case_identities(labels))
        scores = score_node_calls(rows, labels)
        for row in scores:
            writer.write_score(row)
        writer.write_summary(summarize_worker_eval(manifest, rows, scores))
    return tmp_path / name


def tampered(src, dst, mutate_calls=None, mutate_scores=None,
             status=None):
    """Copy a run and re-establish internal consistency after mutation:
    payload hashes and counts are recomputed, so only the loader's
    regeneration checks can catch the change."""
    shutil.copytree(src, dst)
    manifest = json.loads((dst / "manifest.json").read_text())
    for name, mutate in (("calls.jsonl", mutate_calls),
                         ("scores.jsonl", mutate_scores)):
        if mutate is None:
            continue
        rows = [json.loads(line) for line in
                (dst / name).read_text().splitlines()]
        rows = mutate(rows)
        (dst / name).write_text("".join(
            json.dumps(row, sort_keys=True) + "\n" for row in rows))
    manifest["payload_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(dst.iterdir()) if path.name != "manifest.json"}
    calls = (dst / "calls.jsonl").read_text().splitlines()
    scores = (dst / "scores.jsonl").read_text().splitlines()
    manifest["written_rows"] = {"calls": len(calls), "scores": len(scores)}
    manifest["expected_rows"] = dict(manifest["written_rows"])
    if status is not None:
        manifest["status"] = status
    (dst / "manifest.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return dst


def test_loader_round_trip_and_tampering(tmp_path):
    run_dir = write_isolated_run(tmp_path)
    loaded = load_run(run_dir)
    assert loaded["summary"]["isolated"]["node_correct"] \
        == {"n": 30, "correct": 30}

    # (a) raw byte tamper: payload hash mismatch.
    plain = tmp_path / "tamper-bytes"
    shutil.copytree(run_dir, plain)
    calls_path = plain / "calls.jsonl"
    calls_path.write_text(calls_path.read_text().replace(
        "resource_first", "resource_flrst", 1))
    with pytest.raises(InfrastructureError, match="hash mismatch"):
        load_run(plain)

    # (b) an aborted run is unusable regardless of its contents.
    with pytest.raises(InfrastructureError, match="not loadable"):
        load_run(tampered(run_dir, tmp_path / "tamper-status",
                          status="aborted"))

    # (c) test 19: a self-consistent score file with an altered expected
    # value is rejected by regeneration, not by any hash.
    def bump_expected(rows):
        rows[0] = dict(rows[0], expected_value=rows[0]["expected_value"] + 1,
                       node_correct=False)
        return rows
    with pytest.raises(InfrastructureError, match="rederive"):
        load_run(tampered(run_dir, tmp_path / "tamper-expected",
                          mutate_scores=bump_expected))

    # (d) a dropped call row is a planned-population mismatch even with
    # consistent counts and hashes.
    with pytest.raises(InfrastructureError, match="population mismatch"):
        load_run(tampered(run_dir, tmp_path / "tamper-missing",
                          mutate_calls=lambda rows: rows[1:]))

    # (e) mixed run ids are rejected.
    def foreign_run(rows):
        rows[0] = dict(rows[0], run_id="run-other")
        return rows
    with pytest.raises(InfrastructureError, match="mixed run ids"):
        load_run(tampered(run_dir, tmp_path / "tamper-runid",
                          mutate_calls=foreign_run))

    # (f) test 16: the scientific evaluator cannot use the Stage-0B cache.
    def cache_served(rows):
        rows[0] = dict(rows[0], cache_source="stage0b-cache")
        return rows
    with pytest.raises(InfrastructureError, match="cache-disabled"):
        load_run(tampered(run_dir, tmp_path / "tamper-cache",
                          mutate_calls=cache_served))


def test_composed_run_round_trips_through_loader(tmp_path):
    script = composed_script()
    cases, labels = build_node_cases(ONE_RENDERER_POP)
    case_by_id = {c.case_id: c for c in cases}
    (math_case,) = [case_by_id[lab.case_id] for lab in labels
                    if lab.cell_id == "math_code"
                    and lab.node_family == "math"]
    del script[(math_case.endpoint_name, math_case.user_message)]
    rt = eval_runtime(pool=bundle_pool(script=script, default="garbage"))
    manifest = make_manifest(rt, population=ONE_RENDERER_POP,
                             evaluation_mode="composed",
                             expected_calls=10, expected_scores=6)
    with RunWriter(tmp_path / "run-comp", manifest) as writer:
        rows, wlabels = run_composed_workflows(rt, ONE_RENDERER_POP, writer)
        scores = score_workflow_calls(rows, wlabels)
        for row in scores:
            writer.write_score(row)
        writer.write_summary(summarize_worker_eval(manifest, rows, scores))
    loaded = load_run(tmp_path / "run-comp")
    assert loaded["summary"]["composed"]["steps"]["dependency_blocked"] == 1
    assert loaded["summary"]["composed"]["terminal_correct"] == 5


# --- narrow two-run comparison (test 14; Gate C) -----------------------------

def write_prompt_variant_run(tmp_path, name="run-var"):
    """Same population and completions, different worker prompts: the pool
    renders a changed math prompt and the manifest declares the matching
    bundle, so only prompt-scoped manifest fields differ."""
    variant_prompts = dict(BUNDLE.prompts)
    variant_prompts["math"] = variant_prompts["math"] + " Be brief."
    bundle = PromptBundle(revision="rev0-var", status="DRAFT",
                          prompts=tuple(sorted(variant_prompts.items())))
    cases, labels = build_node_cases(POPULATION)
    latents = generate_latents(POPULATION)
    script = reference_script(cases, labels, latents)
    rt = eval_runtime(pool=FakePool(script=script, default="garbage",
                                    system_prompts=variant_prompts))
    manifest = build_manifest(
        rt, bundle, run_id="run-1", purpose="tranche-a-test",
        population=POPULATION,
        endpoint_schedule_version="d16-operator-aligned-v1",
        candidate_label="rev0-var", request_contract_key="worker-blocks-v0",
        expected_calls=len(cases), expected_scores=len(labels),
        git_info={"commit": "0" * 40, "dirty": False, "diff_sha256": None})
    with RunWriter(tmp_path / name, manifest) as writer:
        rows = run_node_cases(rt, cases, writer, case_identities(labels))
        scores = score_node_calls(rows, labels)
        for row in scores:
            writer.write_score(row)
        writer.write_summary(summarize_worker_eval(manifest, rows, scores))
    return tmp_path / name


def test_comparison_accepts_declared_and_refuses_undeclared_differences(
        tmp_path):
    base = load_run(write_isolated_run(tmp_path, "run-base"))
    variant = load_run(write_prompt_variant_run(tmp_path, "run-var"))
    comparison = compare_worker_eval_runs(base, variant, "prompt")
    assert comparison["case_support"] == 30
    assert any(field.startswith("system_prompts")
               for field in comparison["differing_fields"])
    # Test 9.1.14: the same runs cannot be compared as if only the model
    # changed — the prompt difference is undeclared and blocks comparison.
    with pytest.raises(InfrastructureError, match="beyond declared"):
        compare_worker_eval_runs(base, variant, "model")
    with pytest.raises(ProfileError, match="allowed_difference"):
        compare_worker_eval_runs(base, variant, "vibes")
