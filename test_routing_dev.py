"""Routing development-track infrastructure battery (211_f §15 step 3,
hardened per 214_s/216_s/218_s/220_s): namespaces + disjointness,
strict natural mixture, driver-inclusive execution digest, the
support-launch manifest consumed by an ADMITTED materialization, the
tracked support runner end-to-end (prepare → admit → materialize →
lock → disclose/select/bind → closeout), enforced first-probe
binding, rederived cohorts and comparators, authenticated telemetry
with the complete equal-cell estimand, the head-bound ledger with
same-entry admission, and the v1 checkpoint/resume contract."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tasks.conductor import program
from tasks.conductor.cache import WorkerCompletionCache
from tasks.conductor.pool_runtime import FourWorkerRuntime
from tasks.conductor.profiles import DEFAULT_PROFILE, canonical_json
from tasks.conductor.stage1_replay import pair_table_from_surface
from tasks.conductor.types import (
    CELL_IDS, NAMESPACES, RENDERER_IDS, InfrastructureError,
)
from tasks.routing import charter, checkpoint, cohorts, dev_support
from tasks.routing import extension_run, ledger, p0_c2_equivalence, p0_cap, p0_contract, p0_cycle, p0_estimands, p0_launch, p0_smoke, p0_mixture, p0_mixture_v2, p0_replay, p0_schedule, p0_schema, p0_tables, p0_val, support_run, telemetry, unit_c2_sample, unit_c_sample

from test_conductor_executor import perfect_worker
from test_conductor_pool_runtime import FakeFourPool, profile_with

# The signed first probe needs a factor-balanced prefix (multiple of
# 6), so the test cohort is the exact outcome-blind 6-prefix.
DEV_COHORT = {cell: list(range(6)) for cell in CELL_IDS}
DEV_RENDERERS = RENDERER_IDS
SEARCH_CAP = 108     # rendered observations: 6 cells x 6 x 3 (220_s F4)
DRIVER = "tasks/routing/dev_support.py"


def _first_probe_rule(prefix=6):
    return cohorts.freeze_first_probe_rule(
        prefix_length_per_cell=prefix, groups_per_observation=2)


# --- namespaces (211_f §3) ----------------------------------------------------

def test_dev_namespaces_registered_with_charter_caps():
    charter.verify_namespace_registration()
    for namespace in charter.DEV_NAMESPACES:
        assert namespace in NAMESPACES


def test_namespace_id_prefixes_have_zero_intersection():
    ids: dict[str, set] = {}
    for namespace in NAMESPACES:
        prefix = set()
        for cell in CELL_IDS:
            for index in range(2):
                latent = program.generate_latent(
                    cell, namespace, index, DEFAULT_PROFILE).latent
                prefix.add(latent["latent_program_id"])
        ids[namespace] = prefix
    names = list(ids)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert not (ids[a] & ids[b]), (a, b)


def test_policy_dev_cohort_b_is_untouched():
    from tasks.conductor.program import policy_dev_cohort
    labels = {policy_dev_cohort(index) for index in range(24, 48)}
    assert len(labels) == 1


# --- charter -------------------------------------------------------------------

def _mixture_population(latents_per_cell=1):
    population = []
    for cell in CELL_IDS:
        for latent_index in range(latents_per_cell):
            latent = f"{cell}:routing_dev_val:{latent_index:05d}:aa00bb11"
            for renderer in RENDERER_IDS:
                population.append({
                    "observation_id": f"{latent}:{renderer}:private",
                    "cell_id": cell, "latent_program_id": latent,
                    "renderer_id": renderer})
    return population


def test_natural_mixture_weights_are_the_130s_target():
    weights = charter.natural_mixture_weights(
        _mixture_population(latents_per_cell=2))
    assert sum(weights.values()) == pytest.approx(1.0)
    assert all(w == pytest.approx(1 / 36) for w in weights.values())


def test_natural_mixture_requires_the_complete_population():
    with pytest.raises(InfrastructureError, match="empty"):
        charter.natural_mixture_weights([])
    population = _mixture_population()
    with pytest.raises(InfrastructureError, match="all six cells"):
        charter.natural_mixture_weights(
            [obs for obs in population
             if obs["cell_id"] != "fork_join"])
    with pytest.raises(InfrastructureError,
                       match="complete renderer crossing"):
        charter.natural_mixture_weights(
            [obs for obs in population
             if not (obs["cell_id"] == "fork_join"
                     and obs["renderer_id"] == "bound_var")])
    with pytest.raises(InfrastructureError, match="duplicate"):
        charter.natural_mixture_weights(population + [population[0]])


def test_execution_digest_includes_the_driver_or_refuses():
    digest = charter.routing_execution_digest(
        "tasks/routing/support_run.py")
    assert digest["driver"] == "tasks/routing/support_run.py"
    with pytest.raises(InfrastructureError, match="actual training "
                       "driver"):
        charter.routing_execution_digest("train.py")


def test_lightweight_freeze_requires_the_211f_fields():
    record = {"kind": "engineering_smoke", "question": "q",
              "motivation": "m", "config": {"x": 1},
              "budget_gpu_hours": 0.5}
    assert charter.lightweight_freeze(record)["freeze_sha256"]
    with pytest.raises(InfrastructureError, match="missing"):
        charter.lightweight_freeze({k: v for k, v in record.items()
                                    if k != "budget_gpu_hours"})
    with pytest.raises(InfrastructureError, match="finite positive"):
        charter.lightweight_freeze({**record,
                                    "budget_gpu_hours": float("nan")})


def test_claim_run_root_refuses_reuse(tmp_path):
    assert charter.claim_run_root("probe-1", base=tmp_path).is_dir()
    with pytest.raises(InfrastructureError, match="never overwrite"):
        charter.claim_run_root("probe-1", base=tmp_path)
    with pytest.raises(InfrastructureError, match="bad run root"):
        charter.claim_run_root("a/b", base=tmp_path)


# --- fakes ---------------------------------------------------------------------

def _env_manifest(**extra):
    """A CANONICAL stage1-environment-v2 manifest bound to the CURRENT
    source identity (the stage1 validator requires it)."""
    from tasks.conductor.stage1_manifest import (
        stage1_source_digest, stage1_source_files,
    )
    body = {"manifest": "stage1-environment-v2",
            "git_commit": "deadbeef", "git_dirty": 0,
            "uv_lock_sha256": "aa" * 32,
            "stage1_source_sha256": stage1_source_digest(),
            "stage1_source_files": list(stage1_source_files()),
            "gpu": "cpu-test", "torch": "0", "numpy": "0",
            "scipy": "0", **extra}
    sha = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    return {**body, "execution_manifest_sha256": sha}


def _wrong_worker3(request: bytes) -> str:
    return "<artifact>lookup(resource, \"nope\", \"nope\")</artifact>"


def dev_fake_rt(tmp_path, sabotage_w3: bool = False):
    observations = dev_support.dev_cohort_observations(
        "routing_dev", DEV_COHORT, DEV_RENDERERS, "private")
    by_task = {}
    for obs in observations:
        _, worker_call = perfect_worker(obs["latent"])
        for step in program.workflow_steps(obs["latent"]):
            request = f"Task:\n{step['subtask']}\n\nx"
            by_task[step["subtask"]] = worker_call(None, request)

    def completion(request: bytes) -> str:
        user = request.decode("utf-8").split("\x00", 1)[1]
        task = user.split("Task:\n", 1)[1].split("\n\n", 1)[0]
        return by_task[task]

    workers = {w: completion for w in range(4)}
    if sabotage_w3:
        workers[3] = _wrong_worker3
    profile = profile_with(cache_path=str(tmp_path / "cache.sqlite"),
                           device="cpu")
    pool = FakeFourPool(profile, workers)
    return FourWorkerRuntime(
        profile, pool, WorkerCompletionCache(profile["cache_path"]))


# --- the tracked runner end-to-end (220_s F5) -----------------------------------

@pytest.fixture(scope="module")
def support_run_fixture(tmp_path_factory):
    """The full Step-4 sequence through the tracked runner: prepare →
    admit → materialize → lock → disclose/select/bind → closeout."""
    tmp = tmp_path_factory.mktemp("support-run")
    run_dir = tmp / "run"
    ledger_path = tmp / "ledger.md"
    rule = _first_probe_rule()
    manifest = support_run.prepare_support_launch(
        run_dir=run_dir, tag="routing-dev-support-test-v1",
        cohort=DEV_COHORT, renderers=DEV_RENDERERS,
        visibility="private", frozen_probe_rule=rule,
        search_cap=SEARCH_CAP, budget_gpu_hours=1.0,
        _runtime_factory=lambda: dev_fake_rt(tmp, sabotage_w3=True),
        _environment_builder=_env_manifest)
    record = support_run.execute_support_run(
        run_dir=run_dir,
        expected_manifest_sha256=manifest["manifest_sha256"],
        expected_head_sha256=None, question="cold-start support",
        motivating_evidence="211_f §4", ledger_path=ledger_path,
        _runtime_factory=lambda: dev_fake_rt(tmp, sabotage_w3=True),
        # 222_s F2 policy: git_commit alone may differ between
        # preparation and launch (the freeze commit)
        _environment_builder=lambda: _env_manifest(
            git_commit="feedbeef"))
    loaded = dev_support.load_dev_surface(
        run_dir / "surface",
        expected_lock_sha256=record["surface_lock_sha256"])
    return {"tmp": tmp, "run_dir": run_dir,
            "ledger_path": ledger_path, "rule": rule,
            "manifest": manifest, "record": record, "loaded": loaded}


def test_support_runner_owns_the_full_sequence(support_run_fixture):
    fx = support_run_fixture
    record = fx["record"]
    # the ledger holds the admitted launch (naming the manifest) and
    # its closeout with the measured cost
    entries = ledger.verify_ledger_head(record["ledger_head"],
                                        fx["ledger_path"])
    assert [e["kind"] for e in entries] == \
        ["support_materialization", "closeout"]
    assert entries[0]["freeze"]["support_launch_sha256"] == \
        fx["manifest"]["manifest_sha256"]
    assert entries[0]["budget_allocated_gpu_hours"] == 1.0
    assert entries[1]["closes_entry_sha256"] == \
        entries[0]["entry_sha256"]
    assert entries[1]["terminal_status"] == "complete"
    state = ledger.envelope_state(entries)
    assert state["consumed_gpu_hours"] == \
        entries[1]["budget_consumed_gpu_hours"]
    assert state["open_launches"] == []
    # outputs persisted once, incl. the execute-time environment
    for name in ("disclosure.json", "c_fixed_dev.json",
                 "probe_cohort.json", "run_record.json",
                 "execute_env_manifest.json"):
        assert (fx["run_dir"] / name).exists()
    # the persisted run record precedes the closeout (no closeout sha)
    persisted = json.loads(
        (fx["run_dir"] / "run_record.json").read_text())
    assert "closeout_entry_sha256" not in persisted
    assert persisted["surface_lock_sha256"] == \
        record["surface_lock_sha256"]
    # the driver the manifest names is the runner itself, digested
    assert fx["manifest"]["driver"] == "tasks/routing/support_run.py"
    # prepare refuses a second run; execute refuses replay (head moved)
    with pytest.raises(InfrastructureError, match="prepared exactly "
                       "once"):
        support_run.prepare_support_launch(
            run_dir=fx["run_dir"], tag="t", cohort=DEV_COHORT,
            renderers=DEV_RENDERERS, visibility="private",
            frozen_probe_rule=fx["rule"], search_cap=SEARCH_CAP,
            budget_gpu_hours=1.0,
            _runtime_factory=lambda: None,
            _environment_builder=_env_manifest)
    with pytest.raises(InfrastructureError,
                       match="externally committed head|preflighted"):
        support_run.execute_support_run(
            run_dir=fx["run_dir"],
            expected_manifest_sha256=fx["manifest"]["manifest_sha256"],
            expected_head_sha256=None, question="q",
            motivating_evidence="m", ledger_path=fx["ledger_path"],
            _runtime_factory=lambda: None,
            _environment_builder=lambda: _env_manifest(
                git_commit="feedbeef"))


def test_execute_validates_before_the_irreversible_admission(
        support_run_fixture, tmp_path):
    """222_s F1/F2: a bad prelaunch or a drifted live environment
    refuses BEFORE admission — the ledger stays empty."""
    fx = support_run_fixture
    fresh_ledger = tmp_path / "ledger.md"
    # live environment drift on a load-bearing field (torch)
    with pytest.raises(InfrastructureError, match="frozen snapshot"):
        support_run.execute_support_run(
            run_dir=fx["run_dir"],
            expected_manifest_sha256=fx["manifest"]["manifest_sha256"],
            expected_head_sha256=None, question="q",
            motivating_evidence="m", ledger_path=fresh_ledger,
            _runtime_factory=lambda: None,
            _environment_builder=lambda: _env_manifest(torch="9.9"))
    assert ledger.read_ledger(fresh_ledger) == []
    # outputs already exist -> preflight refusal, still no admission
    with pytest.raises(InfrastructureError, match="preflighted"):
        support_run.execute_support_run(
            run_dir=fx["run_dir"],
            expected_manifest_sha256=fx["manifest"]["manifest_sha256"],
            expected_head_sha256=None, question="q",
            motivating_evidence="m", ledger_path=fresh_ledger,
            _runtime_factory=lambda: None,
            _environment_builder=lambda: _env_manifest(
                git_commit="feedbeef"))
    assert ledger.read_ledger(fresh_ledger) == []


def test_attestation_compares_the_complete_body():
    """224_s F1 reproduction: a changed field the old allow-list never
    named (transformers) must refuse; only documentation-commit
    fields are exempt."""
    frozen = _env_manifest(transformers="4.0", python="3.12")
    live_ok = _env_manifest(transformers="4.0", python="3.12",
                            git_commit="feedbeef")
    support_run.attest_environment(frozen, live_ok)
    drifted = _env_manifest(transformers="5.13", python="3.12")
    with pytest.raises(InfrastructureError, match="transformers"):
        support_run.attest_environment(frozen, drifted)
    # a field present on only one side is attested too
    extra = _env_manifest(python="3.12")
    with pytest.raises(InfrastructureError, match="transformers"):
        support_run.attest_environment(frozen, extra)


def test_success_closeout_binds_terminal_artifacts(
        support_run_fixture, tmp_path):
    """224_s F1: replacing execute_env_manifest.json or the run
    record after completion is detectable from the closeout."""
    fx = support_run_fixture
    entries = ledger.read_ledger(fx["ledger_path"])
    closeout = entries[-1]
    assert closeout["freeze"]["execute_env_file_sha256"]
    assert closeout["freeze"]["run_record_file_sha256"]
    replica = tmp_path / "run"
    shutil.copytree(fx["run_dir"], replica)
    support_run.verify_terminal_outputs(replica, closeout)
    (replica / "execute_env_manifest.json").write_text(
        json.dumps(_env_manifest(gpu="other"), indent=1,
                   sort_keys=True) + "\n")
    with pytest.raises(InfrastructureError, match="terminal artifact "
                       "was altered"):
        support_run.verify_terminal_outputs(replica, closeout)
    # 226_s F2 reproduction: {} files whose raw hashes match a forged
    # closeout no longer verify — content must be VALID evidence
    forged_dir = tmp_path / "forged"
    forged_dir.mkdir()
    for name in ("run_record.json", "execute_env_manifest.json"):
        (forged_dir / name).write_text("{}")
    forged_hash = hashlib.sha256(b"{}").hexdigest()
    forged = dict(closeout)
    forged["freeze"] = {"surface_lock_sha256": "5f" * 32,
                       "run_record_file_sha256": forged_hash,
                       "execute_env_file_sha256": forged_hash,
                       "rendered_observations": 108}
    with pytest.raises(InfrastructureError, match="missing|not a "
                       "stage1|not a support-run"):
        support_run.verify_terminal_outputs(forged_dir, forged)


def test_post_admission_failure_aborts_closed(tmp_path):
    """222_s F1: a runtime failure AFTER admission appends an ABORTED
    closeout with the measured cost and preserves partial evidence —
    and the aborted launch is replaceable under the recovery rule."""
    tmp = tmp_path
    run_dir = tmp / "run"
    ledger_path = tmp / "ledger.md"
    rule = _first_probe_rule()
    manifest = support_run.prepare_support_launch(
        run_dir=run_dir, tag="abort-test", cohort=DEV_COHORT,
        renderers=DEV_RENDERERS, visibility="private",
        frozen_probe_rule=rule, search_cap=SEARCH_CAP,
        budget_gpu_hours=1.0,
        _runtime_factory=lambda: dev_fake_rt(tmp, sabotage_w3=True),
        _environment_builder=_env_manifest)

    def exploding_runtime():
        raise RuntimeError("CUDA fell over")

    with pytest.raises(RuntimeError, match="CUDA fell over"):
        support_run.execute_support_run(
            run_dir=run_dir,
            expected_manifest_sha256=manifest["manifest_sha256"],
            expected_head_sha256=None, question="q",
            motivating_evidence="m", ledger_path=ledger_path,
            _runtime_factory=exploding_runtime,
            _environment_builder=_env_manifest)
    entries = ledger.read_ledger(ledger_path)
    assert [e["kind"] for e in entries] == \
        ["support_materialization", "closeout"]
    assert entries[1]["terminal_status"] == "aborted"
    assert "CUDA fell over" in entries[1]["interpretation"]
    state = ledger.envelope_state(entries)
    assert state["open_launches"] == []
    # 224_s F2: the aborted closeout binds a content-hashed manifest
    # of the partial evidence, and it verifies
    partial = entries[1]["freeze"]["partial_artifact_hashes"]
    assert "execute_env_manifest.json" in partial
    assert "prelaunch/declaration.json" in partial
    support_run.verify_terminal_outputs(run_dir, entries[1])
    (run_dir / "execute_env_manifest.json").write_text("{}\n")
    with pytest.raises(InfrastructureError, match="not exactly the "
                       "bound inventory"):
        support_run.verify_terminal_outputs(run_dir, entries[1])
    design = dev_support.scientific_design_sha256(manifest)
    retry = {"kind": "support_materialization", "question": "retry",
             "motivating_evidence": "aborted engineering failure",
             "freeze": {"support_launch_sha256":
                        manifest["manifest_sha256"],
                        "scientific_design_sha256": design},
             "parent": None, "budget_allocated_gpu_hours": 1.0,
             "outcome_informed": False,
             "cohort_selection": "outcome_blind"}
    # 224_s F2: a CHANGED scientific design (self-consistent manifest
    # + entry, but a different cohort/rule identity) is not a retry
    changed_manifest = dict(manifest, search_cap=SEARCH_CAP + 6,
                            manifest_sha256="cd" * 32)
    changed = dict(retry, freeze={
        "support_launch_sha256": "cd" * 32,
        "scientific_design_sha256":
            dev_support.scientific_design_sha256(changed_manifest)})
    with pytest.raises(InfrastructureError, match="preserve the "
                       "scientific design"):
        ledger.admit_and_append_launch(
            changed, entries[-1]["entry_sha256"], ledger_path,
            launch_manifest=changed_manifest)
    # a design-preserving retry is admissible (fresh reviewed freeze)
    ledger.admit_and_append_launch(
        retry, entries[-1]["entry_sha256"], ledger_path,
        launch_manifest=manifest)
    # …but an OPEN (unclosed) support launch still blocks
    entries = ledger.read_ledger(ledger_path)
    with pytest.raises(InfrastructureError, match="open or completed"):
        ledger.admit_and_append_launch(
            dict(retry, question="again"),
            entries[-1]["entry_sha256"], ledger_path,
            launch_manifest=manifest)


def test_materialization_cannot_run_unadmitted(support_run_fixture,
                                               tmp_path):
    """220_s F1: a valid manifest + env without the recorded
    admission refuses at the ledger check."""
    fx = support_run_fixture
    prelaunch = fx["run_dir"] / "prelaunch"
    declaration = json.loads(
        (prelaunch / "declaration.json").read_text())
    env = json.loads((prelaunch / "env_manifest.json").read_text())
    manifest = json.loads(
        (prelaunch / "support_launch.json").read_text())
    rt = dev_fake_rt(fx["tmp"], sabotage_w3=True)
    empty_ledger = tmp_path / "ledger.md"
    with pytest.raises(InfrastructureError, match="unadmitted"):
        dev_support.materialize_dev_support(
            rt, declaration, tmp_path / "surface",
            launch_manifest=manifest, environment_manifest=env,
            expected_manifest_sha256=manifest["manifest_sha256"],
            ledger_path=empty_ledger, expected_head_sha256=None)
    # an admitted entry naming a DIFFERENT manifest also refuses
    fake = _fake_manifest(budget=1.0)
    other = ledger.admit_and_append_launch(
        _support_entry(fake), None, empty_ledger,
        launch_manifest=fake)
    with pytest.raises(InfrastructureError, match="different "
                       "support-launch manifest"):
        dev_support.materialize_dev_support(
            rt, declaration, tmp_path / "surface",
            launch_manifest=manifest, environment_manifest=env,
            expected_manifest_sha256=manifest["manifest_sha256"],
            ledger_path=empty_ledger,
            expected_head_sha256=other["entry_sha256"])
    rt.close()


def test_support_admission_requires_the_manifest_linkage(tmp_path):
    path = tmp_path / "ledger.md"
    manifest = _fake_manifest(budget=2.0)
    entry = _support_entry(manifest)
    # without the manifest: refuse
    with pytest.raises(InfrastructureError, match="admitted WITH"):
        ledger.admit_and_append_launch(entry, None, path)
    # freeze naming a different hash: refuse
    with pytest.raises(InfrastructureError, match="exact "
                       "support-launch manifest"):
        ledger.admit_and_append_launch(
            {**entry, "freeze": {**entry["freeze"],
                                 "support_launch_sha256": "cd" * 32}},
            None, path, launch_manifest=manifest)
    # budget mismatch: refuse
    with pytest.raises(InfrastructureError, match="differs from the "
                       "manifest budget"):
        ledger.admit_and_append_launch(
            {**entry, "budget_allocated_gpu_hours": 3.0}, None, path,
            launch_manifest=manifest)
    ledger.admit_and_append_launch(entry, None, path,
                                   launch_manifest=manifest)


# --- support-launch manifest (218_s/220_s F1-F4) --------------------------------

def _fixture_declaration(fx):
    return json.loads(
        (fx["run_dir"] / "prelaunch" / "declaration.json").read_text())


def test_support_launch_manifest_binds_all_prelaunch_inputs(
        support_run_fixture):
    fx = support_run_fixture
    declaration = _fixture_declaration(fx)
    env = _env_manifest()
    manifest = dev_support.build_support_launch_manifest(
        declaration=declaration, frozen_probe_rule=fx["rule"],
        search_cap=SEARCH_CAP, budget_gpu_hours=1.0, driver=DRIVER,
        environment_manifest=env)
    assert manifest["probe_rule_sha256"] == fx["rule"]["rule_sha256"]
    # 220_s F3: a reprobe rule cannot drive the support launch
    reprobe = cohorts.freeze_reprobe_rule(
        namespace="routing_dev", prefix_length_per_cell=6,
        renderers=RENDERER_IDS, visibility="private", group_size=8,
        groups_per_observation=2)
    with pytest.raises(InfrastructureError, match="signed first "
                       "probe"):
        dev_support.build_support_launch_manifest(
            declaration=declaration, frozen_probe_rule=reprobe,
            search_cap=SEARCH_CAP, budget_gpu_hours=1.0,
            driver=DRIVER, environment_manifest=env)
    # a rule the declaration cannot serve refuses BEFORE execution
    with pytest.raises(InfrastructureError, match="under-covers"):
        dev_support.build_support_launch_manifest(
            declaration=declaration,
            frozen_probe_rule=_first_probe_rule(prefix=12),
            search_cap=1000, budget_gpu_hours=1.0, driver=DRIVER,
            environment_manifest=env)
    # 220_s F4: the cap counts RENDERED OBSERVATIONS (108 here)
    with pytest.raises(InfrastructureError, match="rendered "
                       "observations"):
        dev_support.build_support_launch_manifest(
            declaration=declaration, frozen_probe_rule=fx["rule"],
            search_cap=107, budget_gpu_hours=1.0, driver=DRIVER,
            environment_manifest=env)
    # non-prefix cohort indices refuse (outcome-blindness)
    skewed = dict(declaration)
    skewed["cohort"] = {**declaration["cohort"],
                        "code_atomic": [0, 1, 2, 3, 4, 6]}
    with pytest.raises(InfrastructureError, match="prefix 0..k-1"):
        dev_support.build_support_launch_manifest(
            declaration=skewed, frozen_probe_rule=fx["rule"],
            search_cap=1000, budget_gpu_hours=1.0, driver=DRIVER,
            environment_manifest=env)
    # fictional environments refuse (canonical stage1 validator)
    fake_env = {"manifest": "test-environment",
                "git_commit": "deadbeef"}
    fake_env["execution_manifest_sha256"] = hashlib.sha256(
        canonical_json(fake_env).encode("utf-8")).hexdigest()
    with pytest.raises(InfrastructureError, match="not a stage1"):
        dev_support.build_support_launch_manifest(
            declaration=declaration, frozen_probe_rule=fx["rule"],
            search_cap=SEARCH_CAP, budget_gpu_hours=1.0,
            driver=DRIVER, environment_manifest=fake_env)
    with pytest.raises(InfrastructureError, match="finite"):
        dev_support.build_support_launch_manifest(
            declaration=declaration, frozen_probe_rule=fx["rule"],
            search_cap=SEARCH_CAP, budget_gpu_hours=float("nan"),
            driver=DRIVER, environment_manifest=env)


def test_dev_cohort_validation_fails_closed():
    full = {cell: [0] for cell in CELL_IDS}
    cases = [
        ({"namespace": "train"}, "not a development namespace"),
        ({"cohort": {}}, "empty development cohort"),
        ({"cohort": {"code_atomic": [0]}}, "all six cells"),
        ({"cohort": {**full, "code_atomic": [0, 0]}},
         "duplicate latent index"),
        ({"cohort": {**full, "code_atomic": [2000]}}, "outside"),
        ({"cohort": {**full, "code_atomic": [True]}}, "non-integer"),
        ({"renderers": ()}, "no renderers"),
        ({"renderers": ("resource_first",)}, "ALL renderers"),
        ({"renderers": ("bound_var", "goal_first", "resource_first")},
         "canonical order"),
        ({"visibility": "public"}, "unknown visibility"),
    ]
    base = {"namespace": "routing_dev", "cohort": full,
            "renderers": RENDERER_IDS, "visibility": "private"}
    for override, match in cases:
        kwargs = {**base, **override}
        with pytest.raises(InfrastructureError, match=match):
            dev_support.validate_dev_cohort(
                kwargs["namespace"], kwargs["cohort"],
                kwargs["renderers"], kwargs["visibility"])


# --- surface lock + environment bytes (220_s F2) --------------------------------

def _copy_surface(fx, tmp_path):
    target = tmp_path / "surface"
    shutil.copytree(fx["run_dir"] / "surface", target)
    return target


def test_dev_surface_roundtrip_under_its_lock(support_run_fixture):
    fx = support_run_fixture
    loaded = fx["loaded"]
    surface = loaded["surface"]
    # per renderer per index: 3x4 + 2x16 + 64 = 108 rows; x6 x3
    assert len(surface) == 108 * 6 * 3
    assert set(surface.values()) <= {0.5, 1.0}
    assert loaded["lock"]["support_launch_sha256"] == \
        fx["manifest"]["manifest_sha256"]
    assert loaded["lock"]["probe_rule_sha256"] == \
        fx["rule"]["rule_sha256"]
    cell_of = {obs["observation_id"]: obs["cell_id"]
               for obs in loaded["observations"]}
    table = pair_table_from_surface(surface, cell_of)
    assert {entry["direction"] for entry in table.values()} == {2}


def test_surface_lock_is_required_and_exact(support_run_fixture,
                                            tmp_path):
    fx = support_run_fixture
    out = fx["run_dir"] / "surface"
    lock_sha = fx["record"]["surface_lock_sha256"]
    with pytest.raises(InfrastructureError, match="externally frozen"):
        dev_support.load_dev_surface(out, expected_lock_sha256="0" * 64)
    with pytest.raises(InfrastructureError, match="no surface lock"):
        dev_support.load_dev_surface(
            tmp_path, expected_lock_sha256=lock_sha)
    with pytest.raises(InfrastructureError, match="locked exactly "
                       "once"):
        dev_support.build_surface_lock(out)


def test_surface_lock_detects_tampered_bytes(support_run_fixture,
                                             tmp_path):
    fx = support_run_fixture
    lock_sha = fx["record"]["surface_lock_sha256"]
    # payoff truncation
    tampered = _copy_surface(fx, tmp_path)
    payoffs = tampered / "payoffs.jsonl"
    rows = payoffs.read_text().splitlines()
    payoffs.write_text("\n".join(rows[:-1]) + "\n")
    with pytest.raises(InfrastructureError, match="bytes on disk"):
        dev_support.load_dev_surface(tampered,
                                     expected_lock_sha256=lock_sha)


def test_environment_bytes_are_bound(support_run_fixture, tmp_path):
    """220_s F2 reproduction: replacing env_manifest.json after
    locking refuses — via the lock's file-hash binding AND the
    always-on self-hash check."""
    fx = support_run_fixture
    lock_sha = fx["record"]["surface_lock_sha256"]
    replaced = _copy_surface(fx, tmp_path)
    (replaced / "env_manifest.json").write_text("{}\n")
    with pytest.raises(InfrastructureError, match="bytes on disk|"
                       "not a stage1"):
        dev_support.load_dev_surface(replaced,
                                     expected_lock_sha256=lock_sha)
    # even a canonical-shaped replacement with a valid self-hash dies
    # on the lock's file-hash binding
    other = tmp_path / "other"
    shutil.copytree(fx["run_dir"] / "surface", other)
    (other / "env_manifest.json").write_text(
        json.dumps(_env_manifest(gpu="other-host"), indent=1,
                   sort_keys=True) + "\n")
    with pytest.raises(InfrastructureError,
                       match="bytes on disk|launch manifest binding"):
        dev_support.load_dev_surface(other,
                                     expected_lock_sha256=lock_sha)


def test_historical_load_still_verifies_env_self_hash():
    env = _env_manifest()
    assert dev_support.validate_env_self_hash(env)
    with pytest.raises(InfrastructureError, match="hash mismatch"):
        dev_support.validate_env_self_hash(
            dict(env, git_commit="other"))
    with pytest.raises(InfrastructureError, match="not a stage1"):
        dev_support.validate_env_self_hash({})


# --- disclosure, comparator, probe binding --------------------------------------

def test_direction_yields_disclose_every_observation(
        support_run_fixture):
    loaded = support_run_fixture["loaded"]
    yields = dev_support.direction_yields(loaded["surface"],
                                          loaded["observations"])
    assert len(yields["per_observation"]) == len(loaded["observations"])
    for cell in ("code_atomic", "math_code", "fork_join"):
        assert yields["per_cell"][cell]["w2_favoured"] == 18
    for cell in ("lookup_atomic", "lookup_math", "math_atomic"):
        assert yields["per_cell"][cell]["no_pair"] == 18


def test_c_fixed_dev_selection_verification_and_forgery(
        support_run_fixture):
    fx = support_run_fixture
    loaded = fx["loaded"]
    record = fx["record"]["c_fixed_dev"]
    assert record["c_fixed_dev"] == 2
    assert record["candidate_scores"] == {"2": 1.0, "3": 0.5}
    assert dev_support.verify_c_fixed_for(loaded, record) == 2
    with pytest.raises(InfrastructureError, match="rehash"):
        dev_support.verify_c_fixed_for(
            loaded, dict(record, c_fixed_dev=3))
    forged = {k: v for k, v in record.items() if k != "record_sha256"}
    forged["candidate_scores"] = {"2": 0.5, "3": 1.0}
    forged["c_fixed_dev"] = 3
    forged["record_sha256"] = charter.content_sha256(forged)
    with pytest.raises(InfrastructureError, match="rederive"):
        dev_support.verify_c_fixed_for(loaded, forged)
    foreign = {k: v for k, v in record.items() if k != "record_sha256"}
    foreign["surface_lock_sha256"] = "0" * 64
    foreign["record_sha256"] = charter.content_sha256(foreign)
    with pytest.raises(InfrastructureError, match="different surface "
                       "lock"):
        dev_support.verify_c_fixed_for(loaded, foreign)


def test_probe_rule_shapes_and_outcome_blindness():
    frozen = _first_probe_rule()
    rule = cohorts.validate_probe_rule(frozen)
    assert rule["namespace"] == "routing_dev"
    assert rule["group_size"] == 8
    with pytest.raises(InfrastructureError, match="divisible by 6"):
        cohorts.freeze_first_probe_rule(
            prefix_length_per_cell=4, groups_per_observation=2)
    bad = dict(frozen["rule"], group_size=1)
    with pytest.raises(InfrastructureError, match="group size"):
        cohorts.validate_probe_rule(
            {"rule": bad, "rule_sha256": charter.content_sha256(bad)})
    smuggled = dict(frozen["rule"],
                    preferred_direction="w2_favoured")
    with pytest.raises(InfrastructureError, match="closed schema"):
        cohorts.validate_probe_rule(
            {"rule": smuggled,
             "rule_sha256": charter.content_sha256(smuggled)})


def test_probe_binding_is_locked_to_the_launched_rule(
        support_run_fixture):
    """220_s F3 reproduction: a different (even valid first-probe)
    rule cannot bind a surface launched under another rule."""
    fx = support_run_fixture
    out = fx["run_dir"] / "surface"
    lock_sha = fx["record"]["surface_lock_sha256"]
    bound = fx["record"]["probe_cohort"]
    assert bound["rule_sha256"] == fx["rule"]["rule_sha256"]
    assert len(bound["observation_ids"]) == 108
    other_rule = cohorts.freeze_first_probe_rule(
        prefix_length_per_cell=6, groups_per_observation=1)
    with pytest.raises(InfrastructureError, match="different probe "
                       "rule"):
        cohorts.bind_probe_cohort(other_rule, out, lock_sha)
    with pytest.raises(InfrastructureError, match="externally frozen"):
        cohorts.bind_probe_cohort(fx["rule"], out, "0" * 64)


# --- telemetry (211_f §7; 216_s F3/F4; 218_s F3; 220_s F3) -----------------------

def _family_correct(cell):
    from tasks.conductor.stage1 import NODE_FAMILIES, WORKER_FAMILIES
    families = NODE_FAMILIES[cell]
    assignment = []
    for node in sorted(families):
        family = families[node]
        if family == "code":
            assignment.append(2)
        else:
            (member,) = [w for w, f in WORKER_FAMILIES.items()
                         if f == family]
            assignment.append(member)
    return assignment


def _completion(valid, assignment, reward, parseable=None):
    return {"parseable": parseable if parseable is not None else valid,
            "valid": valid,
            "assignment": assignment, "reward": reward}


@pytest.fixture(scope="module")
def telemetry_context(support_run_fixture):
    loaded = support_run_fixture["loaded"]
    return loaded, support_run_fixture["record"]["c_fixed_dev"]


def _code_obs(loaded, renderer="resource_first"):
    for obs in loaded["observations"]:
        if obs["cell_id"] == "code_atomic" \
                and obs["renderer_id"] == renderer:
            return obs["observation_id"]
    raise AssertionError


def test_group_stats_contrasts_and_views(telemetry_context):
    loaded, record = telemetry_context
    oid = _code_obs(loaded)
    surface = loaded["surface"]
    group = {"observation_id": oid, "completions": [
        _completion(False, None, 0.0),
        _completion(True, [2], surface[(oid, (2,))]),
        _completion(True, [3], surface[(oid, (3,))]),
        _completion(True, [0], surface[(oid, (0,))]),
    ]}
    stats = telemetry.group_stats(group, loaded=loaded,
                                  c_fixed_record=record)
    assert stats["cell_id"] == "code_atomic"
    assert stats["direction"] == "w2_favoured"
    assert stats["format_contrast"] is True
    assert stats["direct_contrast"] is True
    assert stats["c1_mean"] == pytest.approx((0 + 1 + 1 + 0) / 4)
    assert stats["model_acc"] == (1.0, 4)
    assert stats["c2_eligible"] == 2
    assert stats["c2_optimal"] == 1
    assert stats["scale_lift_mean"] == pytest.approx(
        (surface[(oid, (3,))] - surface[(oid, (2,))]) / 4)


def test_group_stats_authenticates_and_gates_membership(
        telemetry_context):
    loaded, record = telemetry_context
    oid = _code_obs(loaded)
    with pytest.raises(InfrastructureError, match="authenticated "
                       "payoff"):
        telemetry.group_stats(
            {"observation_id": oid,
             "completions": [_completion(True, [2], 0.5)]},
            loaded=loaded, c_fixed_record=record)
    with pytest.raises(InfrastructureError, match="scores malformed"):
        telemetry.group_stats(
            {"observation_id": oid,
             "completions": [_completion(False, None, 0.5)]},
            loaded=loaded, c_fixed_record=record)
    with pytest.raises(InfrastructureError, match="contradiction"):
        telemetry.group_stats(
            {"observation_id": oid,
             "completions": [_completion(True, [2], 1.0,
                                         parseable=False)]},
            loaded=loaded, c_fixed_record=record)
    with pytest.raises(InfrastructureError, match="action schema"):
        telemetry.group_stats(
            {"observation_id": oid,
             "completions": [_completion(True, [2, 2], 1.0)]},
            loaded=loaded, c_fixed_record=record)
    foreign = ("code_atomic:routing_dev:01999:abcdef01:"
               "resource_first:private")
    with pytest.raises(InfrastructureError, match="not an observation "
                       "of the locked support"):
        telemetry.group_stats(
            {"observation_id": foreign,
             "completions": [_completion(False, None, 0.0)]},
            loaded=loaded, c_fixed_record=record)
    with pytest.raises(InfrastructureError, match="frozen ladder"):
        telemetry.group_stats(
            {"observation_id": oid,
             "completions": [_completion(True, [2], 0.75)]},
            loaded=loaded, c_fixed_record=record)


def test_group_stats_no_pair_and_tied(telemetry_context):
    loaded, record = telemetry_context
    oid = next(obs["observation_id"] for obs in loaded["observations"]
               if obs["cell_id"] == "lookup_atomic")
    surface = loaded["surface"]
    reference = _family_correct("lookup_atomic")
    group = {"observation_id": oid, "completions": [
        _completion(True, reference,
                    surface[(oid, tuple(reference))])] * 8}
    stats = telemetry.group_stats(group, loaded=loaded,
                                  c_fixed_record=record)
    assert stats["direction"] == "no_pair"
    assert stats["zero_variance_level"] == "1"
    assert stats["c2_optimal"] is None
    assert stats["model_acc"] is None
    obs = "code_atomic:routing_dev:00000:abcdef01:resource_first:private"
    tied_surface = {(obs, (0,)): 0.5, (obs, (1,)): 0.5,
                    (obs, (2,)): 1.0, (obs, (3,)): 1.0}
    entry = telemetry.derive_pair_entry(obs, "code_atomic",
                                        tied_surface)
    assert entry["distinct_payoff"] is False
    assert entry["direction"] is None


def _bound_groups(fx, loaded, record, groups_per_observation=2,
                  group_size=8):
    surface = loaded["surface"]
    cell_of = {obs["observation_id"]: obs["cell_id"]
               for obs in loaded["observations"]}
    groups = []
    for oid in fx["record"]["probe_cohort"]["observation_ids"]:
        assignment = _family_correct(cell_of[oid])
        reward = surface[(oid, tuple(assignment))]
        for _ in range(groups_per_observation):
            groups.append(telemetry.group_stats(
                {"observation_id": oid, "completions":
                 [_completion(True, assignment, reward)] * group_size},
                loaded=loaded, c_fixed_record=record))
    return groups


def test_probe_report_requires_the_frozen_design(support_run_fixture,
                                                 telemetry_context):
    fx = support_run_fixture
    loaded, record = telemetry_context
    bound = fx["record"]["probe_cohort"]
    groups = _bound_groups(fx, loaded, record)
    report = telemetry.probe_report(groups, loaded=loaded,
                                    bound_cohort=bound,
                                    frozen_rule=fx["rule"])
    assert report["design"]["observations"] == 108
    assert report["total"]["groups"] == 216
    assert report["equal_cell"]["model_acc"]["value"] == 1.0
    # extra / missing / wrong-size groups refuse (218_s F3)
    with pytest.raises(InfrastructureError, match="multiplicities"):
        telemetry.probe_report(groups + groups[:1], loaded=loaded,
                               bound_cohort=bound,
                               frozen_rule=fx["rule"])
    with pytest.raises(InfrastructureError, match="multiplicities"):
        telemetry.probe_report(groups[:-1], loaded=loaded,
                               bound_cohort=bound,
                               frozen_rule=fx["rule"])
    # 220_s F3: a self-rehashed cohort record with curated ids does
    # not survive rederivation
    curated = {k: v for k, v in bound.items() if k != "cohort_sha256"}
    curated["observation_ids"] = bound["observation_ids"][:54] * 2
    curated["cohort_sha256"] = charter.content_sha256(curated)
    with pytest.raises(InfrastructureError, match="rederive"):
        telemetry.probe_report(groups, loaded=loaded,
                               bound_cohort=curated,
                               frozen_rule=fx["rule"])
    # a rule that is not the LAUNCHED rule refuses even if the cohort
    # record were rebuilt for it
    other_rule = cohorts.freeze_first_probe_rule(
        prefix_length_per_cell=6, groups_per_observation=1)
    with pytest.raises(InfrastructureError, match="different frozen "
                       "rule|different probe rule"):
        telemetry.probe_report(groups, loaded=loaded,
                               bound_cohort=bound,
                               frozen_rule=other_rule)


def test_equal_cell_view_refuses_partial_populations(
        support_run_fixture, telemetry_context):
    fx = support_run_fixture
    loaded, record = telemetry_context
    groups = _bound_groups(fx, loaded, record,
                           groups_per_observation=1)
    partial = [g for g in groups if g["cell_id"] != "fork_join"]
    with pytest.raises(InfrastructureError, match="all six cells"):
        telemetry.equal_cell_view(partial)
    missing_renderer = [
        g for g in groups
        if not (g["cell_id"] == "fork_join"
                and g["renderer_id"] == "bound_var")]
    with pytest.raises(InfrastructureError,
                       match="complete renderer crossing"):
        telemetry.equal_cell_view(missing_renderer)
    with pytest.raises(InfrastructureError, match="no groups"):
        telemetry.aggregate_stratified([])
    # frequencies carry denominators
    report = telemetry.aggregate_stratified(groups)
    assert report["total"]["worker_frequencies"]["denominator"] == \
        sum(report["total"]["worker_frequencies"]["counts"].values())


# --- ledger (211_f §§10, 12; 218_s F2; 220_s F1) ---------------------------------

def _entry(**overrides):
    # 352_s #1: engineering_smoke now REQUIRES its manifest, so the
    # generic launch-boundary tests use standalone_evaluation
    entry = {"kind": "standalone_evaluation", "question": "q",
             "motivating_evidence": "202_f priors",
             "freeze": {"config_sha256": "ab" * 32},
             "parent": None, "budget_allocated_gpu_hours": 0.5,
             "outcome_informed": False}
    entry.update(overrides)
    return entry


def _note(**overrides):
    defaults = {"kind": "cycle_synthesis",
                "budget_allocated_gpu_hours": 0.0}
    defaults.update(overrides)
    return _entry(**defaults)


def _reserve(status="provisional", hours=7.0, seconds=4.2):
    return {"status": status, "r_cycle_gpu_hours": hours,
            "assumed_cohort_size": 3000,
            "evaluation_multiplier": 2.0,
            "measured_seconds_per_observation": seconds,
            "measured_support_gpu_hours": 1.5,
            "rounding": "ceil_to_whole_gpu_hours"}



def _fake_manifest(budget=4.0, cap=108):
    manifest = {field: f"{field}-v"
                for field in dev_support._SCIENTIFIC_DESIGN_FIELDS
                if field != "search_cap"}
    manifest["search_cap"] = cap
    manifest["manifest_sha256"] = "ab" * 32
    manifest["budget_gpu_hours"] = budget
    return manifest


def _support_entry(manifest, **overrides):
    entry = {"kind": "support_materialization", "question": "q",
             "motivating_evidence": "m",
             "freeze": {"support_launch_sha256":
                        manifest["manifest_sha256"],
                        "scientific_design_sha256":
                        dev_support.scientific_design_sha256(manifest)},
             "parent": None,
             "budget_allocated_gpu_hours":
                 manifest["budget_gpu_hours"],
             "outcome_informed": False,
             "cohort_selection": "outcome_blind"}
    entry.update(overrides)
    return entry


def test_ledger_chain_and_head_mechanics(tmp_path):
    path = tmp_path / "ledger.md"
    first = ledger.append_ledger_entry(_note(), None, path)
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.append_ledger_entry(_note(), None, path)
    second = ledger.append_ledger_entry(
        _note(question="q2"), first["entry_sha256"], path)
    head = second["entry_sha256"]
    assert ledger.ledger_head(path) == head
    text = path.read_text()
    with open(path, "w") as handle:
        handle.write(text.replace('"question": "q"',
                                  '"question": "edited"'))
    with pytest.raises(InfrastructureError, match="edited"):
        ledger.read_ledger(path)
    blocks = text.split("\n## entry ")
    with open(path, "w") as handle:
        handle.write(blocks[0] + "\n## entry " + blocks[2])
    with pytest.raises(InfrastructureError, match="chain broken"):
        ledger.read_ledger(path)
    with open(path, "w") as handle:
        handle.write(blocks[0] + "\n## entry " + blocks[1])
    assert ledger.read_ledger(path)
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.verify_ledger_head(head, path)


def test_ledger_entry_schema_fails_closed(tmp_path):
    path = tmp_path / "ledger.md"
    with pytest.raises(InfrastructureError, match="missing required"):
        ledger.append_ledger_entry(
            {k: v for k, v in _note().items() if k != "question"},
            None, path)
    with pytest.raises(InfrastructureError, match="unknown fields"):
        ledger.append_ledger_entry(_note(surprise=1), None, path)
    with pytest.raises(InfrastructureError, match="unknown entry kind"):
        ledger.append_ledger_entry(_note(kind="vibes"), None, path)
    with pytest.raises(InfrastructureError, match="cohort_selection"):
        ledger.append_ledger_entry(
            _note(cohort_selection="whatever"), None, path)
    with pytest.raises(InfrastructureError, match="linked closeout"):
        ledger.append_ledger_entry(
            _note(budget_consumed_gpu_hours=0.1), None, path)
    with pytest.raises(InfrastructureError, match="terminal_status"):
        ledger.append_ledger_entry(
            _note(terminal_status="complete"), None, path)
    with pytest.raises(InfrastructureError, match="terminal_status"):
        ledger.append_ledger_entry(
            _note(kind="closeout", closes_entry_sha256="0" * 64,
                  budget_consumed_gpu_hours=0.1), None, path)
    with pytest.raises(InfrastructureError, match="outcome_blind"):
        ledger.admit_and_append_launch(
            _entry(kind="grouped_probe"), None, path)
    with pytest.raises(InfrastructureError, match="admit_and_append"):
        ledger.append_ledger_entry(_entry(), None, path)
    with pytest.raises(InfrastructureError, match="finite"):
        ledger.admit_and_append_launch(
            _entry(budget_allocated_gpu_hours=float("nan")), None,
            path)


def test_reserve_requires_numerical_basis_and_exact_rounding():
    incomplete = {"status": "provisional", "r_cycle_gpu_hours": 6.0}
    with pytest.raises(InfrastructureError, match="numerical basis"):
        ledger.validate_reserve(incomplete)
    with pytest.raises(InfrastructureError, match="must recompute"):
        ledger.validate_reserve(_reserve(hours=6.0))
    with pytest.raises(InfrastructureError, match="must recompute"):
        ledger.validate_reserve(_reserve(hours=9.0))
    with pytest.raises(InfrastructureError, match="must recompute"):
        ledger.validate_reserve(_reserve(hours=7.0, seconds=4.3))
    ledger.validate_reserve(_reserve(hours=8.0, seconds=4.3))
    with pytest.raises(InfrastructureError, match="frozen policy"):
        ledger.validate_reserve(
            dict(_reserve(), rounding="ceil to whole GPU-hours"))
    with pytest.raises(InfrastructureError, match="finite"):
        ledger.validate_reserve(
            dict(_reserve(), r_cycle_gpu_hours=float("inf")))
    with pytest.raises(InfrastructureError, match="finite"):
        ledger.validate_reserve(
            dict(_reserve(), measured_support_gpu_hours=float("nan")))


def _fixture_copy(fx, tmp_path):
    """The verified fixture run + its ledger, copied so reserve tests
    can mutate the chain."""
    run_copy = tmp_path / "run"
    shutil.copytree(fx["run_dir"], run_copy)
    ledger_copy = tmp_path / "ledger.md"
    shutil.copy2(fx["ledger_path"], ledger_copy)
    return run_copy, ledger_copy, ledger.ledger_head(ledger_copy)


def _derived_reserve(fx, **overrides):
    """A reserve whose basis REDERIVES from the fixture's real
    closeout (consumed x 3600 / 108 observations)."""
    import math
    closeout = ledger.read_ledger(fx["ledger_path"])[-1]
    consumed = closeout["budget_consumed_gpu_hours"]
    seconds = consumed * 3600.0 / 108
    reserve = _reserve(seconds=seconds, **overrides)
    reserve["measured_support_gpu_hours"] = consumed
    reserve["r_cycle_gpu_hours"] = float(math.ceil(
        reserve["assumed_cohort_size"]
        * reserve["evaluation_multiplier"] * seconds / 3600.0))
    return reserve


def test_reserve_consumes_the_verified_terminal_run(
        support_run_fixture, tmp_path):
    """228_s F1/F2 + 224_s F3: reserves go through
    record_provisional_reserve, which verifies the terminal run; the
    ledger refuses direct reserve appends; final reserves refuse
    unconditionally."""
    fx = support_run_fixture
    run_copy, ledger_copy, head = _fixture_copy(fx, tmp_path)
    # direct ledger appends are barred
    with pytest.raises(InfrastructureError,
                       match="record_provisional_reserve"):
        ledger.append_ledger_entry(
            _note(kind="reserve_update",
                  reserve=_derived_reserve(fx)), head, ledger_copy)
    # an empty ledger has no completed support to consume
    with pytest.raises(InfrastructureError, match="no completed "
                       "support closeout"):
        support_run.record_provisional_reserve(
            _derived_reserve(fx), run_dir=run_copy, question="q",
            motivating_evidence="m", expected_head_sha256=None,
            ledger_path=tmp_path / "empty.md")
    # the 226_s undersizing reproduction refuses at the gate
    undersized = _derived_reserve(fx)
    undersized["measured_seconds_per_observation"] = 0.1
    undersized["r_cycle_gpu_hours"] = 1.0
    with pytest.raises(InfrastructureError, match="rederive exactly"):
        support_run.record_provisional_reserve(
            undersized, run_dir=run_copy, question="q",
            motivating_evidence="m", expected_head_sha256=head,
            ledger_path=ledger_copy)
    # 228_s F2 as amended by Unit Y (330_f §3): a final reserve
    # without BOTH derivations (and the cycle-record bindings)
    # still refuses — the provisional boundary can never mint one
    with pytest.raises(InfrastructureError, match="whole-valued"):
        support_run.record_provisional_reserve(
            _derived_reserve(fx, status="final"), run_dir=run_copy,
            question="q", motivating_evidence="m",
            expected_head_sha256=head, ledger_path=ledger_copy)
    # a tampered run directory refuses BEFORE any append
    (run_copy / "extra_results.json").write_text("{}")
    with pytest.raises(InfrastructureError, match="not exactly the "
                       "bound inventory"):
        support_run.record_provisional_reserve(
            _derived_reserve(fx), run_dir=run_copy, question="q",
            motivating_evidence="m", expected_head_sha256=head,
            ledger_path=ledger_copy)
    assert ledger.ledger_head(ledger_copy) == head
    (run_copy / "extra_results.json").unlink()
    # the honest reserve appends
    reserve_entry = support_run.record_provisional_reserve(
        _derived_reserve(fx), run_dir=run_copy, question="q",
        motivating_evidence="m", expected_head_sha256=head,
        ledger_path=ledger_copy)
    assert reserve_entry["freeze"]["support_closeout_sha256"] == head
    # a second reserve while a launch is OPEN refuses
    probe = ledger.admit_and_append_launch(
        _entry(kind="grouped_probe", cohort_selection="outcome_blind",
               budget_allocated_gpu_hours=3.0),
        reserve_entry["entry_sha256"], ledger_copy)
    with pytest.raises(InfrastructureError, match="launch is open"):
        support_run.record_provisional_reserve(
            _derived_reserve(fx), run_dir=run_copy, question="q",
            motivating_evidence="m",
            expected_head_sha256=probe["entry_sha256"],
            ledger_path=ledger_copy)


def test_launch_closeout_linkage_and_envelope(
        support_run_fixture, tmp_path):
    fx = support_run_fixture
    run_copy, path, head = _fixture_copy(fx, tmp_path)
    support_consumed = ledger.read_ledger(path)[-1][
        "budget_consumed_gpu_hours"]
    reserve_entry = support_run.record_provisional_reserve(
        _derived_reserve(fx), run_dir=run_copy, question="q",
        motivating_evidence="m", expected_head_sha256=head,
        ledger_path=path)
    launch = ledger.admit_and_append_launch(
        _entry(budget_allocated_gpu_hours=3.0),
        reserve_entry["entry_sha256"], path)
    state = ledger.envelope_state(ledger.read_ledger(path))
    assert state["consumed_gpu_hours"] == \
        pytest.approx(support_consumed + 3.0)
    closeout = ledger.append_ledger_entry(
        _note(kind="closeout",
              closes_entry_sha256=launch["entry_sha256"],
              budget_consumed_gpu_hours=1.25,
              terminal_status="complete"),
        launch["entry_sha256"], path)
    state = ledger.envelope_state(ledger.read_ledger(path))
    assert state["consumed_gpu_hours"] == \
        pytest.approx(support_consumed + 1.25)
    assert state["open_launches"] == []
    with pytest.raises(InfrastructureError, match="already closed"):
        ledger.append_ledger_entry(
            _note(kind="closeout",
                  closes_entry_sha256=launch["entry_sha256"],
                  budget_consumed_gpu_hours=1.0,
                  terminal_status="complete"),
            closeout["entry_sha256"], path)
    with pytest.raises(InfrastructureError, match="not a recorded "
                       "launch"):
        ledger.append_ledger_entry(
            _note(kind="closeout", closes_entry_sha256="0" * 64,
                  budget_consumed_gpu_hours=1.0,
                  terminal_status="complete"),
            closeout["entry_sha256"], path)


def test_admission_verifies_the_persisted_ledger_itself(
        support_run_fixture, tmp_path):
    fx = support_run_fixture
    # empty-ledger paths: only a support launch may open the chain,
    # and its design identity is required + verified
    empty = tmp_path / "empty.md"
    manifest = _fake_manifest(budget=4.0)
    with pytest.raises(InfrastructureError, match="ABORTED-closed"):
        # (a manifestless ordinary kind — training_run now
        # REQUIRES its P0 execution manifest, 359_f)
        ledger.admit_and_append_launch(
            _entry(kind="standalone_evaluation"), None, empty)
    missing_design = _support_entry(manifest)
    missing_design["freeze"] = {"support_launch_sha256":
                                manifest["manifest_sha256"]}
    with pytest.raises(InfrastructureError, match="scientific_design"):
        ledger.admit_and_append_launch(missing_design, None, empty,
                                       launch_manifest=manifest)
    support = ledger.admit_and_append_launch(
        _support_entry(manifest), None, empty,
        launch_manifest=manifest)
    with pytest.raises(InfrastructureError, match="open or completed"):
        ledger.admit_and_append_launch(
            _support_entry(manifest), support["entry_sha256"], empty,
            launch_manifest=manifest)
    # the verified fixture chain: reserve -> probe -> bounded launches
    run_copy, path, head = _fixture_copy(fx, tmp_path)
    reserve_entry = support_run.record_provisional_reserve(
        _derived_reserve(fx), run_dir=run_copy, question="q",
        motivating_evidence="m", expected_head_sha256=head,
        ledger_path=path)
    r_cycle = reserve_entry["reserve"]["r_cycle_gpu_hours"]
    head = reserve_entry["entry_sha256"]
    probe = ledger.admit_and_append_launch(
        _entry(kind="grouped_probe",
               cohort_selection="outcome_blind",
               budget_allocated_gpu_hours=3.0), head, path)
    head = probe["entry_sha256"]
    # an ordinary launch that would breach max + R_cycle refuses
    with pytest.raises(InfrastructureError, match="inadmissible"):
        ledger.admit_and_append_launch(
            _entry(kind="standalone_evaluation",
                   budget_allocated_gpu_hours=60.0), head, path)
    with pytest.raises(InfrastructureError, match="exceeds the "
                       "reserved"):
        ledger.admit_and_append_launch(
            _entry(kind="cycle_closure",
                   budget_allocated_gpu_hours=r_cycle + 0.5),
            head, path)
    closure = ledger.admit_and_append_launch(
        _entry(kind="cycle_closure",
               budget_allocated_gpu_hours=r_cycle), head, path)
    with pytest.raises(InfrastructureError, match="not a launch kind"):
        ledger.admit_and_append_launch(
            _note(kind="reserve_update", reserve=_reserve()),
            closure["entry_sha256"], path)



# --- checkpoint/resume (unchanged contracts, 216_s F5/F6 + 218_s F4) -------------

IDENTITIES = {key: f"{key}-value" for key in checkpoint.IDENTITY_KEYS}
RNG_STATE = {"python": {"version": 3, "internal_state": [1],
                        "gauss_next": None},
             "numpy": {"name": "MT19937", "keys": [1], "pos": 0,
                       "has_gauss": 0, "cached_gaussian": 0.0},
             "torch_cpu": [1], "torch_cuda": None}


def _accountant_at_boundary():
    accountant = checkpoint.GroupAccountant()
    accountant.record_generation(groups=2, completions=16)
    accountant.record_update(consumed_groups=2)
    return accountant


@pytest.fixture
def bundle(tmp_path):
    for name in ("adapter", "optimizer", "scheduler"):
        (tmp_path / checkpoint.CHECKPOINT_BUNDLE_FILENAMES[name]) \
            .write_bytes(name.encode())
    rng_sha = checkpoint.persist_rng_state(tmp_path, RNG_STATE)
    filenames = {name: checkpoint.CHECKPOINT_BUNDLE_FILENAMES[name]
                 for name in ("adapter", "optimizer", "scheduler",
                              "rng")}
    hashes = checkpoint.hash_state_artifacts(tmp_path, filenames)
    record = checkpoint.build_checkpoint_record(
        identities=IDENTITIES,
        counters=_accountant_at_boundary().authorize_checkpoint(),
        rng_state=RNG_STATE, state_artifact_hashes=hashes,
        sampler_position={"next_global_group_index": 2},
        run_id="p0", segment_id="p0-seg1", parent_checkpoint=None)
    assert record["rng_state_sha256"] == rng_sha
    return tmp_path, record


def test_group_accountant_enforces_the_v1_boundary():
    accountant = checkpoint.GroupAccountant()
    accountant.record_generation(groups=2, completions=16)
    with pytest.raises(InfrastructureError, match="v1 boundary"):
        accountant.authorize_checkpoint()
    accountant.record_update(consumed_groups=2)
    counters = accountant.authorize_checkpoint()
    with pytest.raises(InfrastructureError, match="never generated"):
        accountant.record_update(consumed_groups=1)
    restored = checkpoint.GroupAccountant.restore(counters)
    assert restored.at_v1_boundary()
    with pytest.raises(InfrastructureError, match="v1 boundary"):
        checkpoint.GroupAccountant.restore(
            dict(counters, generated_groups=3))
    with pytest.raises(InfrastructureError, match="impossible"):
        checkpoint.GroupAccountant.restore(
            dict(counters, sampled_completions=1))


def test_resume_verifies_the_bundle_mandatorily(bundle):
    bundle_dir, record = bundle
    restored = checkpoint.validate_resume(record, IDENTITIES,
                                          bundle_dir=bundle_dir)
    assert restored["counters"]["consumed_groups"] == 2
    with pytest.raises(InfrastructureError, match="prompt_sha256"):
        checkpoint.validate_resume(
            record, dict(IDENTITIES, prompt_sha256="other"),
            bundle_dir=bundle_dir)
    tampered = dict(record)
    tampered["counters"] = dict(record["counters"],
                                optimizer_updates=99)
    with pytest.raises(InfrastructureError, match="rehash"):
        checkpoint.validate_resume(tampered, IDENTITIES,
                                   bundle_dir=bundle_dir)
    (bundle_dir / checkpoint.CHECKPOINT_BUNDLE_FILENAMES["adapter"]) \
        .write_bytes(b"ALTERED")
    with pytest.raises(InfrastructureError, match="bundle was "
                       "altered"):
        checkpoint.validate_resume(record, IDENTITIES,
                                   bundle_dir=bundle_dir)


def test_resume_cross_binds_the_rng_artifact(tmp_path):
    for name in ("adapter", "optimizer", "scheduler"):
        (tmp_path / checkpoint.CHECKPOINT_BUNDLE_FILENAMES[name]) \
            .write_bytes(name.encode())
    other = dict(RNG_STATE, torch_cpu=[2])
    checkpoint.persist_rng_state(tmp_path, other)
    filenames = {name: checkpoint.CHECKPOINT_BUNDLE_FILENAMES[name]
                 for name in ("adapter", "optimizer", "scheduler",
                              "rng")}
    hashes = checkpoint.hash_state_artifacts(tmp_path, filenames)
    record = checkpoint.build_checkpoint_record(
        identities=IDENTITIES,
        counters=_accountant_at_boundary().authorize_checkpoint(),
        rng_state=RNG_STATE, state_artifact_hashes=hashes,
        sampler_position={"next_global_group_index": 2},
        run_id="p0", segment_id="s", parent_checkpoint=None)
    with pytest.raises(InfrastructureError, match="rng_state_sha256"):
        checkpoint.validate_resume(record, IDENTITIES,
                                   bundle_dir=tmp_path)


def _segment(segment_id, status, resume_from, cutoff, indices,
             parent=None, checkpoint_id=None, run_id="p0",
             config="cfg"):
    return {"segment_id": segment_id, "run_id": run_id,
            "config_sha256": config, "status": status,
            "checkpoint_id": checkpoint_id or f"ckpt-{segment_id}",
            "parent_checkpoint": parent,
            "resume_from_consumed_groups": resume_from,
            "checkpoint_consumed_groups": cutoff,
            "groups": [{"global_group_index": i} for i in indices]}


def test_merge_segments_excludes_aborted_tail_but_preserves_it():
    first = _segment("s1", "aborted", 0, 3, range(5))
    second = _segment("s2", "complete", 3, 6, range(3, 6),
                      parent=first["checkpoint_id"])
    merged = checkpoint.merge_segments([first, second])
    assert merged["merged_groups"] == 6
    assert [g["global_group_index"] for g in
            merged["excluded_aborted_evidence"]] == [3, 4]


def test_merge_segments_requires_exact_ranges():
    with pytest.raises(InfrastructureError, match="exact in-order"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 0, 2, [1, 0])])
    with pytest.raises(InfrastructureError, match="omits checkpointed"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 0, 3, [0, 1])])
    with pytest.raises(InfrastructureError, match="exact range"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 0, 3, range(5))])
    with pytest.raises(InfrastructureError, match="omits checkpointed"):
        checkpoint.merge_segments(
            [_segment("s1", "aborted", 0, 3, [0, 1])])


def test_merge_segments_enforces_identity_and_linkage():
    first = _segment("s1", "aborted", 0, 3, range(5))
    with pytest.raises(InfrastructureError, match="linkage broken"):
        checkpoint.merge_segments(
            [first, _segment("s2", "complete", 3, 6, range(3, 6),
                             parent="ckpt-other")])
    with pytest.raises(InfrastructureError, match="parent[\\s\\S]*"
                       "recorded"):
        checkpoint.merge_segments(
            [first, _segment("s2", "complete", 4, 6, range(4, 6),
                             parent=first["checkpoint_id"])])
    with pytest.raises(InfrastructureError, match="FORK"):
        checkpoint.merge_segments(
            [first, _segment("s2", "complete", 3, 6, range(3, 6),
                             parent=first["checkpoint_id"],
                             config="other")])
    with pytest.raises(InfrastructureError, match="one run identity"):
        checkpoint.merge_segments(
            [first, _segment("s2", "complete", 3, 6, range(3, 6),
                             parent=first["checkpoint_id"],
                             run_id="p1")])
    with pytest.raises(InfrastructureError, match="from scratch"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 1, 3, range(1, 3))])
    with pytest.raises(InfrastructureError, match="non-terminal"):
        checkpoint.merge_segments(
            [_segment("s1", "running", 0, 0, [])])


def test_rng_capture_is_complete_and_restorable():
    import numpy
    numpy.random.seed(11)
    numpy.random.rand(2)
    state_pos2 = checkpoint.capture_rng_state()
    numpy.random.seed(11)
    numpy.random.rand(4)
    state_pos4 = checkpoint.capture_rng_state()
    assert charter.content_sha256(state_pos2) != \
        charter.content_sha256(state_pos4)
    import random as random_module
    import torch
    random_module.seed(3)
    numpy.random.seed(3)
    torch.manual_seed(3)
    random_module.random()
    numpy.random.rand()
    snapshot = checkpoint.capture_rng_state()
    expected = (random_module.random(), numpy.random.rand(),
                torch.rand(1).item())
    checkpoint.restore_rng_state(snapshot)
    replayed = (random_module.random(), numpy.random.rand(),
                torch.rand(1).item())
    assert replayed == expected
    json.dumps(snapshot)


def test_isolated_rng_restores_every_stream():
    import numpy
    import torch
    random_module = __import__("random")
    random_module.seed(7)
    numpy.random.seed(7)
    torch.manual_seed(7)
    with checkpoint.isolated_rng():
        random_module.random()
        numpy.random.rand()
        torch.rand(1)
    replay = (random_module.random(), numpy.random.rand(),
              torch.rand(1).item())
    random_module.seed(7)
    numpy.random.seed(7)
    torch.manual_seed(7)
    expected = (random_module.random(), numpy.random.rand(),
                torch.rand(1).item())
    assert replay == expected


# --- Step-5 resume-validation tranche (211_f §11; CPU-testable parts) -----------

from tasks.routing import resume_validation


def _reconstructed_support(tmp_path):
    """The REAL Step-4 surface, restored from committed evidence via
    the PRODUCTION path (235_s portability note) and loaded under its
    committed lock — so these tests also re-verify the frozen config
    against the actual artifacts on any clean clone."""
    replica = tmp_path / "surface"
    support_run.restore_surface_evidence(
        "plans/conductor/evidence/routing_dev_support_v1/surface",
        replica)
    return resume_validation.load_locked_support(replica)


@pytest.fixture(scope="module")
def step4_support(tmp_path_factory):
    return _reconstructed_support(tmp_path_factory.mktemp("step4"))


def test_resume_validation_freeze_is_exact():
    frozen = resume_validation.tranche_freeze()
    assert frozen["budget_gpu_hours"] == 0.5          # the EXACT ceiling
    config = frozen["config"]
    assert config["comparison_tolerance"] == 0.0
    assert config["checkpoint_at_update"] == 3
    assert config["total_updates"] == 6
    # 235_s F4: the schedule exceeds the update budget
    assert config["schedule_length"] > config["total_updates"]
    # 235_s F1/F3: same horizon, fault-stopped, post-checkpoint tail
    assert config["fault_at_update"] > config["checkpoint_at_update"]
    assert config["fault_at_update"] < config["total_updates"]
    # 235_s F7: determinism is part of the frozen claim
    assert config["full_determinism"] is True
    assert frozen["freeze_sha256"]
    assert resume_validation.CONFIG_SHA256 == charter.content_sha256(
        resume_validation.RESUME_VALIDATION_CONFIG)


def test_training_schedule_is_deterministic_and_bound(step4_support):
    loaded = step4_support
    rows = resume_validation.training_schedule(loaded)
    assert len(rows) == 8
    ids = [row["observation_id"] for row in rows]
    assert ids == sorted(ids)      # canonical order
    for row in rows:
        assert row["prompt"][0]["role"] == "system"
        assert row["prompt"][1]["role"] == "user"
    identities = resume_validation.schedule_identities(rows)
    assert set(identities) == {"training_cohort_sha256",
                               "renderer_schedule_sha256",
                               "prompt_sha256"}
    # regenerating gives identical identities
    assert resume_validation.schedule_identities(
        resume_validation.training_schedule(loaded)) == identities


def test_validation_reward_authenticates_and_traces(step4_support,
                                                    tmp_path):
    loaded = step4_support
    rows = resume_validation.training_schedule(loaded)
    row = rows[0]
    reference = _family_correct(row["cell_id"])
    positions = json.loads(row["positions"])
    # a valid positional action for the reference semantic assignment
    from tasks.conductor.oracle import semantic_to_positional
    positional = semantic_to_positional(reference, row["cell_id"],
                                        positions)
    valid_text = json.dumps({"worker_ids": positional})
    accountant = checkpoint.GroupAccountant()
    trace = tmp_path / "actions.jsonl"
    reward = resume_validation.make_validation_reward(
        loaded["surface"], accountant, trace, group_size=8)
    completions = [valid_text] * 7 + ["not json"]
    rewards = reward(
        completions,
        observation_id=[row["observation_id"]] * 8,
        positions=[row["positions"]] * 8,
        num_steps=[row["num_steps"]] * 8)
    expected = loaded["surface"][(row["observation_id"],
                                  tuple(reference))]
    assert rewards[:7] == [expected] * 7
    assert rewards[7] == 0.0                     # malformed -> 0
    assert accountant.generated_groups == 1
    assert accountant.sampled_completions == 8
    lines = resume_validation.read_trace(trace)
    assert len(lines) == 1
    assert lines[0]["global_group_index"] == 0
    assert lines[0]["rewards"] == rewards
    # 235_s F4: traces carry completions, actions and assignments
    assert lines[0]["completions"][0] == valid_text
    assert lines[0]["actions"][7] is None          # malformed
    assert lines[0]["assignments"][0] == list(reference)
    # a partial group refuses
    with pytest.raises(InfrastructureError, match="whole groups"):
        reward(completions[:4],
               observation_id=[row["observation_id"]] * 4,
               positions=[row["positions"]] * 4,
               num_steps=[row["num_steps"]] * 4)


def test_comparison_enforces_the_frozen_tolerance():
    import copy

    import torch
    base = {
        "adapter": {"lora.w": torch.ones(2, 2)},
        "optimizer": {"state": {0: {"exp_avg": torch.zeros(2)}},
                      "param_groups": [{"lr": 1e-5, "params": [0]}]},
        "scheduler": {"last_epoch": 6},
        "next_sampler_identity": "obs-7",
        "counters": {"generated_groups": 6, "consumed_groups": 6,
                     "optimizer_updates": 6,
                     "sampled_completions": 48},
        "trace_sequence": [[i, f"obs-{i}", [0.5] * 8]
                           for i in range(6)],
        "trace_cardinality": 6,
    }
    same = copy.deepcopy(base)
    verdict = resume_validation.compare_runs(base, same)
    assert verdict["verdict"] == "PASS"
    perturbed = copy.deepcopy(base)
    perturbed["adapter"]["lora.w"] = torch.ones(2, 2) * 1.001
    with pytest.raises(InfrastructureError, match="lora.w"):
        resume_validation.compare_runs(base, perturbed)
    # 235_s F4: parameter-group membership is compared
    regrouped = copy.deepcopy(base)
    regrouped["optimizer"]["param_groups"][0]["params"] = [1]
    with pytest.raises(InfrastructureError, match="group.0.params"):
        resume_validation.compare_runs(base, regrouped)
    drifted = copy.deepcopy(base)
    drifted["counters"]["consumed_groups"] = 5
    with pytest.raises(InfrastructureError, match="counters differ"):
        resume_validation.compare_runs(base, drifted)
    moved = copy.deepcopy(base)
    moved["next_sampler_identity"] = "other"
    with pytest.raises(InfrastructureError, match="sampler"):
        resume_validation.compare_runs(base, moved)
    # 235_s F4: an END cursor is itself a design failure
    ended = copy.deepcopy(base)
    ended["next_sampler_identity"] = "END"
    same_end = copy.deepcopy(ended)
    with pytest.raises(InfrastructureError, match="END"):
        resume_validation.compare_runs(ended, same_end)
    reordered = copy.deepcopy(base)
    reordered["trace_sequence"] = list(
        reversed(reordered["trace_sequence"]))
    with pytest.raises(InfrastructureError, match="trace sequences"):
        resume_validation.compare_runs(base, reordered)
    fewer = copy.deepcopy(base)
    fewer["trace_cardinality"] = 5
    with pytest.raises(InfrastructureError, match="cardinality"):
        resume_validation.compare_runs(base, fewer)


def test_tensor_state_hashes_distinguish_and_stabilize():
    import torch
    state = {"a": torch.ones(2, dtype=torch.bfloat16),
             "b": torch.zeros(3)}
    first = resume_validation.tensor_state_hashes(state)
    assert first == resume_validation.tensor_state_hashes(state)
    other = {"a": torch.ones(2, dtype=torch.bfloat16) * 2,
             "b": torch.zeros(3)}
    assert first != resume_validation.tensor_state_hashes(other)


def test_bundle_written_only_at_the_checkpoint_step():
    """237_s F1: HF saves at updates 3 AND 6 — the bundle gate skips
    non-checkpoint steps and refuses a duplicate write."""
    class _State:
        def __init__(self, step):
            self.global_step = step

    bc = resume_validation._BoundaryCallback(
        checkpoint.GroupAccountant(), Path("unused-bundle"),
        {}, "run", "seg", hf_output_dir=Path("unused"),
        checkpoint_at=3)
    # a save at update 6 is a no-op for the bundle
    bc.callback.on_save(None, _State(6), None, model=None)
    assert bc.record is None
    # a second write at the checkpoint step refuses
    bc.record = {"sentinel": True}
    with pytest.raises(InfrastructureError, match="exactly once"):
        bc.callback.on_save(None, _State(3), None, model=None)


def test_identity_manifest_is_deterministic(step4_support):
    loaded = step4_support
    rows = resume_validation.training_schedule(loaded)
    first = resume_validation.static_identity_manifest(loaded, rows)
    second = resume_validation.static_identity_manifest(loaded, rows)
    assert first == second
    assert first["surface_lock_sha256"] == \
        resume_validation.RESUME_VALIDATION_CONFIG[
            "surface_lock_sha256"]
    assert first["manifest_sha256"] == charter.content_sha256(
        {k: v for k, v in first.items() if k != "manifest_sha256"})


def test_exact_comparison_refuses_non_finite():
    import copy

    import torch
    base = {
        "adapter": {"lora.w": torch.ones(2, 2)},
        "optimizer": {"state": {}, "param_groups": []},
        "scheduler": {"last_epoch": 6},
        "next_sampler_identity": "obs-7",
        "counters": {"generated_groups": 6, "consumed_groups": 6,
                     "optimizer_updates": 6,
                     "sampled_completions": 48},
        "trace_sequence": [], "trace_cardinality": 0,
    }
    poisoned = copy.deepcopy(base)
    poisoned["adapter"]["lora.w"] = torch.full((2, 2), float("nan"))
    with pytest.raises(InfrastructureError, match="non-finite"):
        resume_validation.compare_runs(base, poisoned)
    # NaN on BOTH sides refuses too (237_s F5 reproduction)
    both = copy.deepcopy(poisoned)
    with pytest.raises(InfrastructureError, match="non-finite"):
        resume_validation.compare_runs(poisoned, both)


def test_final_state_cross_checks_the_frozen_schedule(step4_support):
    """237_s F6: trace observation ids must BE the schedule prefix."""
    loaded = step4_support
    rows = resume_validation.training_schedule(loaded)
    accountant = checkpoint.GroupAccountant()
    accountant.record_generation(groups=2, completions=16)
    accountant.record_update(consumed_groups=1)
    accountant.record_update(consumed_groups=1)
    good = [{"global_group_index": i,
             "observation_id": rows[i]["observation_id"],
             "completions": ["x"] * 8, "actions": [None] * 8,
             "assignments": [None] * 8, "rewards": [0.0] * 8}
            for i in range(2)]
    final = {"adapter": {}, "optimizer": {}, "scheduler": {}}
    state = resume_validation._final_state(final, accountant, rows,
                                           good)
    assert state["next_sampler_identity"] == \
        rows[2]["observation_id"]
    swapped = [dict(good[0],
                    observation_id=rows[5]["observation_id"])] \
        + good[1:]
    with pytest.raises(InfrastructureError, match="frozen schedule"):
        resume_validation._final_state(final, accountant, rows,
                                       swapped)


def test_hf_equivalence_is_strict(tmp_path):
    """239_s F3: a missing adapter file refuses; adapter comparison
    goes through normalized names; missing RNG streams refuse."""
    import torch
    from safetensors.torch import save_file
    bundle = tmp_path / "bundle"
    hf = tmp_path / "checkpoint-3"
    bundle.mkdir()
    hf.mkdir()
    tensor = torch.ones(2)
    save_file({"base_model.model.layers.0.q_proj.lora_A.default"
               ".weight": tensor},
              str(bundle / checkpoint.CHECKPOINT_BUNDLE_FILENAMES[
                  "adapter"]))
    optimizer = {"state": {}, "param_groups": []}
    torch.save(optimizer, bundle / "optimizer.pt")
    torch.save({"last_epoch": 3}, bundle / "scheduler.pt")
    rng = dict(RNG_STATE)
    checkpoint.persist_rng_state(bundle, rng)
    torch.save(optimizer, hf / "optimizer.pt")
    torch.save({"last_epoch": 3}, hf / "scheduler.pt")
    torch.save({"cpu": torch.tensor(RNG_STATE["torch_cpu"],
                                    dtype=torch.uint8),
                "python": (3, tuple(RNG_STATE["python"][
                    "internal_state"]), None),
                "numpy": ("MT19937", torch.tensor([1]).numpy(), 0, 0,
                          0.0)},
               hf / "rng_state.pth")

    def _record():
        return {"sampler_position": {"hf_checkpoint_sha256":
                resume_validation._hf_checkpoint_hashes(hf)}}

    # missing adapter file refuses (never skipped)
    with pytest.raises(InfrastructureError, match="lacks "
                       "adapter_model"):
        resume_validation.verify_hf_checkpoint_against_bundle(
            bundle, hf, _record())
    # matching adapter under a DIFFERENT name grammar passes the
    # normalized comparison
    save_file({"base_model.model.layers.0.q_proj.lora_A.weight":
               tensor}, str(hf / "adapter_model.safetensors"))
    resume_validation.verify_hf_checkpoint_against_bundle(
        bundle, hf, _record())
    # a changed tensor refuses through the normalized names
    save_file({"base_model.model.layers.0.q_proj.lora_A.weight":
               tensor * 2}, str(hf / "adapter_model.safetensors"))
    with pytest.raises(InfrastructureError, match="hf-vs-bundle "
                       "adapter"):
        resume_validation.verify_hf_checkpoint_against_bundle(
            bundle, hf, _record())
    # a missing python RNG stream refuses
    save_file({"base_model.model.layers.0.q_proj.lora_A.weight":
               tensor}, str(hf / "adapter_model.safetensors"))
    torch.save({"cpu": torch.tensor(RNG_STATE["torch_cpu"],
                                    dtype=torch.uint8)},
               hf / "rng_state.pth")
    with pytest.raises(InfrastructureError, match="python stream"):
        resume_validation.verify_hf_checkpoint_against_bundle(
            bundle, hf, _record())


def test_attested_environment_hash_survives_the_freeze_commit():
    env_a = _env_manifest(git_commit="deadbeef")
    env_b = _env_manifest(git_commit="feedbeef")
    assert resume_validation.attested_environment_sha256(env_a) == \
        resume_validation.attested_environment_sha256(env_b)
    drifted = _env_manifest(torch="9.9")
    assert resume_validation.attested_environment_sha256(env_a) != \
        resume_validation.attested_environment_sha256(drifted)


def test_preflight_semantics_must_have_passed():
    """241_s P1: self-consistently archived but FAILED or malformed
    preflights refuse."""
    floor = resume_validation.RESUME_VALIDATION_CONFIG[
        "min_free_vram_mib"]
    good = {"free_mib": floor + 100, "total_mib": 24564,
            "floor_mib": floor}
    resume_validation.verify_preflight_semantics(good)
    with pytest.raises(InfrastructureError, match="FAILED"):
        resume_validation.verify_preflight_semantics(
            dict(good, free_mib=floor - 1))
    with pytest.raises(InfrastructureError, match="not the frozen"):
        resume_validation.verify_preflight_semantics(
            dict(good, floor_mib=1))
    with pytest.raises(InfrastructureError, match="impossible"):
        resume_validation.verify_preflight_semantics(
            dict(good, total_mib=floor))
    with pytest.raises(InfrastructureError, match="schema"):
        resume_validation.verify_preflight_semantics(
            {**good, "extra": 1})
    with pytest.raises(InfrastructureError, match="non-negative int"):
        resume_validation.verify_preflight_semantics(
            dict(good, free_mib=float("nan")))


def test_bundle_identities_must_match_the_archived_manifests(
        step4_support):
    """241_s P1: every ckpt.IDENTITY_KEYS field is pinned by the
    archived identity/environment manifests — a relabelled field
    (self-consistently rehashed) refuses."""
    loaded = step4_support
    rows = resume_validation.training_schedule(loaded)
    manifest = resume_validation.static_identity_manifest(loaded, rows)
    env_sha = "ab" * 32
    expected = resume_validation.expected_bundle_identities(
        manifest, env_sha)
    assert set(expected) == set(checkpoint.IDENTITY_KEYS)
    assert expected["environment_manifest_sha256"] == env_sha
    assert expected["prompt_sha256"] == manifest["prompt_sha256"]
    # a manifest lacking an identity field refuses
    truncated = {k: v for k, v in manifest.items()
                 if k != "prompt_sha256"}
    with pytest.raises(InfrastructureError, match="prompt_sha256"):
        resume_validation.expected_bundle_identities(truncated,
                                                     env_sha)


def test_tensor_mismatch_message_names_the_dtypes():
    """243_f: the Step-5 abort message lacked the actual dtypes — the
    refusal now states them."""
    import torch
    a = {"w": torch.ones(2, dtype=torch.bfloat16)}
    b = {"w": torch.ones(2, dtype=torch.float32)}
    with pytest.raises(InfrastructureError,
                       match="bfloat16.*float32|float32.*bfloat16"):
        resume_validation.compare_tensor_states(a, b, 0.0, "adapter")


def test_rev6_declares_precision_and_lineage():
    """244_s: the fp32 adapter amendment and the outcome-informed
    relaunch lineage are FROZEN config, not code side-effects."""
    config = resume_validation.RESUME_VALIDATION_CONFIG
    assert config["lora"]["adapter_dtype"] == "float32"
    lineage = config["lineage"]
    assert lineage["outcome_informed"] is True
    assert lineage["parent_entry_sha256"] == (
        "943b9d7ce8c7ebcd908101489a8f0a866ccc575c8538f727d633415e"
        "918ca212")
    assert "243_f" in lineage["motivating_evidence"]
    assert "237d4c21" in lineage["motivating_evidence"]


# --- Step-6 grouped probe (CPU-testable parts) ----------------------------------

from tasks.routing import probe_run


def test_probe_freeze_binds_the_registered_design():
    frozen = probe_run.tranche_freeze()
    config = frozen["config"]
    assert frozen["budget_gpu_hours"] == 3.0        # charter ceiling
    assert config["probe_rule_sha256"] == (
        "0b616b8863bf73263c11c63cd8cc1572b880e6586f15059bde642c2a"
        "397c9f7b")
    assert config["probe_cohort_sha256"] == (
        "7f31bd091aaa97664e71ecb86b17078861b4e28af284162ee6ac5033"
        "8d661e3b")
    assert config["total_groups"] == 432
    assert config["groups_per_observation"] == 4
    assert config["grpo"]["learning_rate"] == 0.0   # zero-update
    assert config["grpo"]["beta"] == 0.0
    assert config["lora"]["adapter_dtype"] == "float32"
    assert config["lineage"]["outcome_informed"] is False
    assert config["lineage"]["parent_entry_sha256"] == (
        "1a8d41fde4ffb64a9d9d9886f8fbcf9dc20578ab33c3c0d72a44fa8e"
        "a9b6a44a")
    # the committed rule bytes revalidate against the frozen hash
    rule = probe_run.load_frozen_rule()
    assert rule["rule"]["group_size"] == 8
    assert rule["rule"]["groups_per_observation"] == 4


def test_probe_cohort_and_schedule_rederive(step4_support, tmp_path,
                                            monkeypatch):
    """The frozen cohort binding rederives from committed bytes, and
    the schedule is the bound order × 4 consecutive groups."""
    replica = tmp_path / "surface"
    support_run.restore_surface_evidence(
        "plans/conductor/evidence/routing_dev_support_v1/surface",
        replica)
    monkeypatch.setitem(probe_run.PROBE_CONFIG, "surface_dir",
                        str(replica))
    cohort = probe_run.bound_cohort()
    assert cohort["cohort_sha256"] == \
        probe_run.PROBE_CONFIG["probe_cohort_sha256"]
    assert len(cohort["observation_ids"]) == 108
    loaded = step4_support
    rows = probe_run.probe_schedule(loaded, cohort)
    assert len(rows) == 432
    assert [r["observation_id"] for r in rows[:4]] == \
        [cohort["observation_ids"][0]] * 4
    assert rows[4]["observation_id"] == cohort["observation_ids"][1]
    manifest = probe_run.static_identity_manifest(loaded, cohort)
    assert manifest["probe_cohort_sha256"] == cohort["cohort_sha256"]
    assert manifest["manifest_sha256"] == charter.content_sha256(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"})


def test_probe_groups_rebuild_from_trace_rows(step4_support):
    """Trace rows rebuild into authenticated group_stats inputs; a
    reward disagreeing with the surface still refuses downstream."""
    loaded = step4_support
    record = dev_support.select_c_fixed_dev(loaded)
    oid = _code_obs(loaded)
    surface = loaded["surface"]
    valid_text = json.dumps({"worker_ids": [2]})
    row = {"global_group_index": 0, "observation_id": oid,
           "completions": [valid_text] * 7 + ["nope"],
           "actions": [[2]] * 7 + [None],
           "assignments": [[2]] * 7 + [None],
           "rewards": [surface[(oid, (2,))]] * 7 + [0.0]}
    groups = probe_run.groups_from_trace([row], loaded, record)
    assert groups[0]["valid"] == 7
    assert groups[0]["parseable"] == 7
    tampered = dict(row, rewards=[0.5] * 7 + [0.0])
    with pytest.raises(InfrastructureError, match="re-derivation"):
        probe_run.groups_from_trace([tampered], loaded, record)
    # 248_s F2 reproduction: a completion SELECTING worker 2 recorded
    # as worker 3 with worker 3's authenticated reward refuses
    flipped = dict(row,
                   actions=[[3]] * 7 + [None],
                   assignments=[[3]] * 7 + [None],
                   rewards=[surface[(oid, (3,))]] * 7 + [0.0])
    with pytest.raises(InfrastructureError, match="re-derivation"):
        probe_run.groups_from_trace([flipped], loaded, record)
    # unequal parallel arrays refuse rather than zip-truncate
    short = dict(row, rewards=row["rewards"][:7])
    with pytest.raises(InfrastructureError, match="parallel arrays"):
        probe_run.groups_from_trace([short], loaded, record)
    # a malformed completion recorded as valid refuses
    fake_valid = dict(row,
                      completions=["nope"] * 8,
                      actions=[[2]] * 8, assignments=[[2]] * 8,
                      rewards=[surface[(oid, (2,))]] * 8)
    with pytest.raises(InfrastructureError, match="recorded as "
                       "valid"):
        probe_run.groups_from_trace([fake_valid], loaded, record)


def test_probe_head_must_be_the_frozen_lineage_parent(tmp_path):
    """248_s smaller item: the launch head cannot be substituted."""
    with pytest.raises(InfrastructureError, match="lineage parent"):
        probe_run.execute_probe(
            expected_freeze_sha256=probe_run.tranche_freeze()[
                "freeze_sha256"],
            expected_identity_sha256="0" * 64,
            expected_environment_sha256="0" * 64,
            expected_head_sha256="0" * 64,
            ledger_path=tmp_path / "ledger.md",
            _environment_builder=lambda: (_ for _ in ()).throw(
                AssertionError("must refuse before env build")))


def test_probe_preflight_and_support_matrix(step4_support):
    floor = probe_run.PROBE_CONFIG["min_free_vram_mib"]
    good = {"free_mib": floor + 1, "total_mib": 24564,
            "floor_mib": floor}
    probe_run._verify_probe_preflight(good)
    with pytest.raises(InfrastructureError, match="FAILED"):
        probe_run._verify_probe_preflight(dict(good,
                                               free_mib=floor - 1))
    # the support matrix covers the COMPLETE grid incl. zeros
    loaded = step4_support
    record = dev_support.select_c_fixed_dev(loaded)
    oid = _code_obs(loaded)
    surface = loaded["surface"]
    groups = probe_run.groups_from_trace([{
        "global_group_index": 0, "observation_id": oid,
        "completions": [json.dumps({"worker_ids": [2]})] * 8,
        "actions": [[2]] * 8, "assignments": [[2]] * 8,
        "rewards": [surface[(oid, (2,))]] * 8}], loaded, record)
    matrix = probe_run.support_matrix(groups)
    assert len(matrix) == 6 * 3 * 4
    assert matrix["code_atomic|resource_first|tied"] == 1
    assert sum(matrix.values()) == 1
    # zero-denominator strata are PRESENT, not omitted (248_s)
    assert set(v for k, v in matrix.items()
               if k != "code_atomic|resource_first|tied") == {0}


def test_probe_archive_verifier_lifecycle(step4_support, tmp_path,
                                          monkeypatch):
    """248_s smaller item: the independent verifier PASSES a complete
    synthetic archive built from committed evidence, and refuses
    schedule tampering, identity-manifest (provenance) tampering, and
    a final-map mismatch."""
    replica = tmp_path / "surface"
    support_run.restore_surface_evidence(
        "plans/conductor/evidence/routing_dev_support_v1/surface",
        replica)
    monkeypatch.setitem(probe_run.PROBE_CONFIG, "surface_dir",
                        str(replica))
    loaded = probe_run.load_locked_support()
    cohort = probe_run.bound_cohort()
    rows = probe_run.probe_schedule(loaded, cohort)
    identity = probe_run.static_identity_manifest(loaded, cohort)
    env = json.loads(Path(
        "plans/conductor/evidence/resume_validation_v4/"
        "environment_manifest.json").read_text("utf-8"))
    config = probe_run.PROBE_CONFIG
    preflight = {"free_mib": config["min_free_vram_mib"] + 79,
                 "total_mib": 24564,
                 "floor_mib": config["min_free_vram_mib"]}
    run_root = tmp_path / "probe"
    run_root.mkdir()
    from tasks.conductor.grpo_task import positional_to_semantic
    surface = loaded["surface"]
    group_size = config["grpo"]["group_size"]
    trace_lines = []
    for i, row in enumerate(rows):
        oid = row["observation_id"]
        positions = json.loads(row["positions"])
        action = [2] * row["num_steps"]
        semantic = list(positional_to_semantic(action, positions))
        reward = float(surface[(oid, tuple(semantic))])
        text_ = json.dumps({"worker_ids": action})
        trace_lines.append(json.dumps({
            "global_group_index": i, "observation_id": oid,
            "completions": [text_] * group_size,
            "actions": [action] * group_size,
            "assignments": [semantic] * group_size,
            "rewards": [reward] * group_size}))
    (run_root / "actions.jsonl").write_text(
        "\n".join(trace_lines) + "\n", encoding="utf-8")
    adapter_map = {"lora_A.default.weight": "aa" * 32}
    for name in ("checkpoint_zero_hashes.json",
                 "checkpoint_final_hashes.json"):
        (run_root / name).write_text(
            json.dumps(adapter_map, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    for name, payload in (
            ("environment_manifest.json", env),
            ("identity_manifest.json", identity),
            ("session_preflight.json", preflight),
            ("schedule.json",
             [row["observation_id"] for row in rows]),
            ("bound_cohort.json", dict(cohort))):
        (run_root / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    total = config["total_groups"]
    counters = {"generated_groups": total, "consumed_groups": total,
                "optimizer_updates": total,
                "sampled_completions": total * group_size}
    record = {
        "tranche": config["tranche"],
        "freeze_sha256": probe_run.tranche_freeze()["freeze_sha256"],
        "config_sha256": probe_run.CONFIG_SHA256,
        "identity_manifest_sha256": identity["manifest_sha256"],
        "environment_manifest_sha256":
            dev_support.validate_env_self_hash(env),
        "attested_environment_sha256":
            resume_validation.attested_environment_sha256(env),
        "session_preflight": preflight,
        "session_preflight_sha256": charter.content_sha256(preflight),
        "checkpoint_zero_adapter_sha256":
            charter.content_sha256(adapter_map),
        "final_adapter_sha256": charter.content_sha256(adapter_map),
        "counters": counters,
        "probe_cohort_sha256": cohort["cohort_sha256"],
        "execution_telemetry": {
            "group_accounting": counters,
            "surface_reward_lookups": total * group_size,
            "live_worker_calls": 0,
            "worker_cache": "not-applicable",
            "wall_seconds": 1.0,
            "deadline_seconds": config["ceiling_gpu_hours"] * 3600.0,
            "peak_reserved_vram_mib": 0,
            "session_preflight": preflight,
        },
    }
    report = probe_run.build_probe_report(run_root)

    def write_record(payload):
        (run_root / "probe_record.json").write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")

    def verify():
        return probe_run.verify_probe_run(
            run_root, identity["manifest_sha256"],
            record["attested_environment_sha256"])

    (run_root / "probe_report.json").write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    write_record(record)
    assert verify()["verdict"] == "PASS"
    assert report["support_matrix"]["code_atomic|resource_first|tied"] \
        > 0

    # schedule tampering refuses
    schedule_path = run_root / "schedule.json"
    good_schedule = schedule_path.read_text("utf-8")
    swapped = json.loads(good_schedule)
    swapped[0], swapped[4] = swapped[4], swapped[0]
    schedule_path.write_text(json.dumps(swapped, indent=1) + "\n",
                             encoding="utf-8")
    with pytest.raises(InfrastructureError, match="schedule"):
        verify()
    schedule_path.write_text(good_schedule, encoding="utf-8")

    # provenance (identity manifest) tampering refuses
    identity_path = run_root / "identity_manifest.json"
    good_identity = identity_path.read_text("utf-8")
    tampered = json.loads(good_identity)
    tampered["seed"] = "1"
    identity_path.write_text(
        json.dumps(tampered, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    with pytest.raises(InfrastructureError, match="rehash or bind"):
        verify()
    identity_path.write_text(good_identity, encoding="utf-8")

    # 250_s P1 reproduction: COHERENT relabelling — alter the identity
    # manifest, REHASH it, and update the record pointer; internal
    # coherence holds, the external anchor refuses
    relabelled = json.loads(good_identity)
    relabelled["seed"] = "1"
    del relabelled["manifest_sha256"]
    relabelled["manifest_sha256"] = charter.content_sha256(relabelled)
    identity_path.write_text(
        json.dumps(relabelled, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    relabelled_record = dict(
        record, identity_manifest_sha256=relabelled["manifest_sha256"])
    write_record(relabelled_record)
    with pytest.raises(InfrastructureError,
                       match="not the REVIEWED one"):
        verify()
    identity_path.write_text(good_identity, encoding="utf-8")
    write_record(record)

    # 250_s P1 reproduction: coherently relabelled ENVIRONMENT —
    # altered, rehashed, both record hashes updated; the attested
    # anchor refuses
    env_path = run_root / "environment_manifest.json"
    good_env = env_path.read_text("utf-8")
    fake_env = json.loads(good_env)
    fake_env["torch"] = "9.9.9"
    body = {k: v for k, v in fake_env.items()
            if k != "execution_manifest_sha256"}
    from tasks.conductor.profiles import canonical_json
    fake_env["execution_manifest_sha256"] = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    env_path.write_text(
        json.dumps(fake_env, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    relabelled_record = dict(
        record,
        environment_manifest_sha256=fake_env[
            "execution_manifest_sha256"],
        attested_environment_sha256=resume_validation
        .attested_environment_sha256(fake_env))
    write_record(relabelled_record)
    with pytest.raises(InfrastructureError,
                       match="not the REVIEWED one"):
        verify()
    env_path.write_text(good_env, encoding="utf-8")
    write_record(record)

    # telemetry-schema tightening (250_s nonblocking): a wrong
    # deadline refuses
    bad_telemetry = dict(record["execution_telemetry"],
                         deadline_seconds=1.0)
    write_record(dict(record, execution_telemetry=bad_telemetry))
    with pytest.raises(InfrastructureError, match="frozen ceiling"):
        verify()
    write_record(record)

    # final-map mismatch refuses on the PERSISTED maps
    final_path = run_root / "checkpoint_final_hashes.json"
    good_final = final_path.read_text("utf-8")
    final_path.write_text(
        json.dumps({"lora_A.default.weight": "bb" * 32}, indent=1,
                   sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(InfrastructureError,
                       match="zero-mutation gate FAILS"):
        verify()
    final_path.write_text(good_final, encoding="utf-8")
    assert verify()["verdict"] == "PASS"

# --- Unit A: the support-extension runner (260_f signed design) ----------------

PRISTINE_EXT_CONFIG = copy.deepcopy(extension_run.EXTENSION_CONFIG)


def ext_fake_rt(tmp_path, cohort, sabotage_w3=True):
    """dev_fake_rt generalized to an arbitrary prefix cohort, with the
    same sabotaged worker 3 as the Step-4 fixture so overlap rows
    reproduce exactly."""
    observations = dev_support.dev_cohort_observations(
        "routing_dev", cohort, DEV_RENDERERS, "private")
    by_task = {}
    for obs in observations:
        _, worker_call = perfect_worker(obs["latent"])
        for step in program.workflow_steps(obs["latent"]):
            request = f"Task:\n{step['subtask']}\n\nx"
            by_task[step["subtask"]] = worker_call(None, request)

    def completion(request: bytes) -> str:
        user = request.decode("utf-8").split("\x00", 1)[1]
        task = user.split("Task:\n", 1)[1].split("\n\n", 1)[0]
        return by_task[task]

    workers = {w: completion for w in range(4)}
    if sabotage_w3:
        workers[3] = _wrong_worker3
    profile = profile_with(cache_path=str(tmp_path / "ext-cache.sqlite"),
                           device="cpu")
    pool = FakeFourPool(profile, workers)
    return FourWorkerRuntime(
        profile, pool, WorkerCompletionCache(profile["cache_path"]))


def test_extension_freeze_binds_the_registered_design():
    config = PRISTINE_EXT_CONFIG
    assert config["prefix_k"] == 48
    assert config["original_prefix_k"] == 6
    assert config["search_cap"] == 864
    assert config["ceiling_gpu_hours"] == 1.0
    assert config["original_surface_lock_sha256"].startswith("61c4e85a")
    assert config["lineage"]["parent_entry_sha256"].startswith(
        "88c037a1")
    assert config["lineage"]["outcome_informed"] is True
    assert config["selector"] == {
        "target_latents": 3, "reduced_power_latents": 2,
        "min_renderer_strata": 2, "min_non_goal_first": 1}
    assert extension_run.CONFIG_SHA256 == charter.content_sha256(config)
    cohort = {cell: list(range(48)) for cell in CELL_IDS}
    assert {cell: sorted(v) for cell, v in cohort.items()} \
        == {cell: list(range(48)) for cell in CELL_IDS}


def test_extension_cost_derivation_is_exact():
    """257_s feasibility figures rederive exactly from the Step-4
    evidence declaration and the frozen cost basis."""
    declaration = json.loads(Path(
        "plans/conductor/evidence/routing_dev_support_v1/surface/"
        "declaration.json").read_text("utf-8"))
    counts = extension_run.planned_node_counts(declaration)
    assert counts == {"planned_node_executions": 4824,
                      "planned_new_node_executions": 0}
    per_index = 4824 // 6
    assert per_index * 42 == 33768
    assert per_index * 48 == 38592
    derivation = extension_run.expected_cost_derivation(
        {"planned_node_executions": 38592,
         "planned_new_node_executions": 33768})
    assert derivation["expected_new_gpu_hours"] == 0.5124
    assert derivation["full_regeneration_bound_gpu_hours"] == 0.5856
    assert derivation["expected_new_gpu_hours"] \
        < PRISTINE_EXT_CONFIG["ceiling_gpu_hours"]


@pytest.fixture(scope="module")
def extension_fixture(support_run_fixture, tmp_path_factory):
    """The full Unit-A sequence on a prefix-7 extension of the
    prefix-6 Step-4 fixture surface: prepare → admit (with reserve on
    record) → materialize under deadline → OVERLAP GATE → lock →
    total selector → immutable comparator → closeout."""
    fx = support_run_fixture
    tmp = tmp_path_factory.mktemp("extension")
    run_copy = tmp / "orig-run"
    shutil.copytree(fx["run_dir"], run_copy)
    ledger_copy = tmp / "ledger.md"
    shutil.copy2(fx["ledger_path"], ledger_copy)
    head = ledger.ledger_head(ledger_copy)
    reserve_entry = support_run.record_provisional_reserve(
        _derived_reserve(fx), run_dir=run_copy, question="q",
        motivating_evidence="m", expected_head_sha256=head,
        ledger_path=ledger_copy)
    head = reserve_entry["entry_sha256"]

    mp = pytest.MonkeyPatch()
    cohort = {cell: list(range(7)) for cell in CELL_IDS}
    for key, value in (
            ("prefix_k", 7),
            ("search_cap", 6 * 7 * 3),
            ("original_surface_dir", str(run_copy / "surface")),
            ("original_surface_lock_sha256",
             fx["record"]["surface_lock_sha256"]),
            ("original_c_fixed_path",
             str(run_copy / "c_fixed_dev.json"))):
        mp.setitem(extension_run.EXTENSION_CONFIG, key, value)
    mp.setitem(extension_run.EXTENSION_CONFIG["lineage"],
               "parent_entry_sha256", head)

    # 259_s test obligation 2: comparator selection must be
    # UNREACHABLE on the extension surface — every rederivation call
    # is spied and must carry the ORIGINAL lock.
    select_calls = []
    real_select = dev_support.select_c_fixed_dev

    def spying_select(loaded):
        select_calls.append(loaded["lock"]["lock_sha256"])
        return real_select(loaded)

    mp.setattr(dev_support, "select_c_fixed_dev", spying_select)

    pre_extension_ledger = tmp / "ledger-pre-extension.md"
    shutil.copy2(ledger_copy, pre_extension_ledger)
    run_dir = tmp / "ext-run"
    mp.setitem(extension_run.EXTENSION_CONFIG, "run_root",
               str(run_dir))
    manifest = extension_run.prepare_extension_launch(
        run_dir=run_dir,
        _runtime_factory=lambda: ext_fake_rt(tmp, cohort),
        _environment_builder=_env_manifest)
    result = extension_run.execute_extension(
        run_dir=run_dir,
        expected_manifest_sha256=manifest["manifest_sha256"],
        expected_head_sha256=head,
        ledger_path=ledger_copy,
        _runtime_factory=lambda: ext_fake_rt(tmp, cohort),
        _environment_builder=lambda: _env_manifest(
            git_commit="feedbeef"),
        _original_surface_dir=run_copy / "surface")
    entries = ledger.verify_ledger_head(result["ledger_head"],
                                        ledger_copy)
    yield {"tmp": tmp, "run_dir": run_dir, "ledger_path": ledger_copy,
           "manifest": manifest, "result": result,
           "closeout": entries[-1], "launch": entries[-2],
           "original_dir": run_copy / "surface",
           "original_run": run_copy, "cohort": cohort,
           "select_calls": select_calls, "admission_head": head,
           "pre_extension_ledger": pre_extension_ledger}
    mp.undo()


def test_extension_end_to_end(extension_fixture):
    fx = extension_fixture
    result = fx["result"]
    original_rows = extension_run._payoff_rows(fx["original_dir"])
    assert result["overlap_rows_verified"] == len(original_rows)
    assert result["original_surface_lock_sha256"] == \
        extension_run.EXTENSION_CONFIG["original_surface_lock_sha256"]
    # the comparator is the immutable Step-4 worker, never reselected
    comparator = json.loads(
        (fx["run_dir"] / "comparator.json").read_text("utf-8"))
    assert comparator["c_fixed_dev"] == 2
    assert comparator["reselected"] is False
    assert comparator["consumes"] == "scale_lift_only"
    # 259_s: every comparator rederivation touched ONLY the original
    # lock — selection on the extension lock is unreachable
    assert fx["select_calls"]
    assert set(fx["select_calls"]) == {
        extension_run.EXTENSION_CONFIG["original_surface_lock_sha256"]}
    # the launch entry is a support_extension bound to the manifest
    assert fx["launch"]["kind"] == "support_extension"
    assert fx["launch"]["freeze"]["extension_launch_sha256"] == \
        fx["manifest"]["manifest_sha256"]
    assert fx["launch"]["outcome_informed"] is True
    assert fx["launch"]["cohort_selection"] == "outcome_blind"
    assert fx["closeout"]["terminal_status"] == "complete"
    # the selector produced dispositions and the Q3 common-cell set
    selection = json.loads(
        (fx["run_dir"] / "selection.json").read_text("utf-8"))
    assert selection["dispositions"]
    assert isinstance(selection["eligible_common_cells_q3"], list)
    domain_start = \
        extension_run.EXTENSION_CONFIG["original_prefix_k"]
    for bucket, members in selection["direction_buckets"].items():
        indices = [m["latent_index"] for m in members]
        assert indices == sorted(indices)
        # 262_s P1-1: legacy indices never enter direction buckets
        assert all(i >= domain_start for i in indices)
    for bucket, members in selection["screened_surplus"].items():
        assert all(m["latent_index"] >= domain_start for m in members)
    # 262_s P1-2: eligibility derives from acceptable dispositions
    acceptable = {"full_quota", "reduced_power_disclosed"}
    for cell in selection["eligible_common_cells_q3"]:
        for direction in ("w2_favoured", "w3_favoured"):
            assert selection["dispositions"][
                f"{cell}|{direction}"]["status"] in acceptable
    # all three Code cells x both directions carry dispositions
    assert set(selection["dispositions"]) == {
        f"{cell}|{direction}"
        for cell in ("code_atomic", "fork_join", "math_code")
        for direction in ("w2_favoured", "w3_favoured")}
    # 262_s P1-3: every observation enters the subtype disclosure
    total_obs = 6 * 7 * 3
    cell_strata = {k: v for k, v in
                   selection["yield_disclosure"].items()
                   if k.startswith("cell|")}
    assert sum(sum(v.values()) for v in cell_strata.values()) \
        == total_obs
    subtype_strata = {k: v for k, v in
                      selection["yield_disclosure"].items()
                      if k.startswith("subtype|")}
    assert sum(sum(v.values()) for v in subtype_strata.values()) \
        == total_obs
    assert any(k.startswith("cell+renderer+subtype|")
               for k in selection["yield_disclosure"])
    # one latent never sits in two buckets (260_f §2)
    seen = {}
    for bucket, members in selection["direction_buckets"].items():
        for m in members:
            key = (m["cell_id"], m["latent_index"])
            assert key not in seen, f"{key} in two buckets"
            seen[key] = bucket
    # post-hoc verification passes from the archive
    extension_run.verify_extension_outputs(
        fx["run_dir"], fx["closeout"],
        original_surface_dir=fx["original_dir"])


def test_extension_overlap_gate_refuses_divergence(extension_fixture,
                                                   tmp_path):
    fx = extension_fixture
    tampered = tmp_path / "surface"
    shutil.copytree(fx["run_dir"] / "surface", tampered)
    rows = [json.loads(line) for line in
            (tampered / "payoffs.jsonl").read_text("utf-8")
            .splitlines()]

    def write(rows_):
        (tampered / "payoffs.jsonl").write_text(
            "\n".join(json.dumps(r, sort_keys=True) for r in rows_)
            + "\n", encoding="utf-8")

    original = extension_run._payoff_rows(fx["original_dir"])
    first_key = sorted(original)[0]
    idx = next(i for i, r in enumerate(rows)
               if (r["observation_id"], tuple(r["assignment"]))
               == first_key)
    # a changed payoff refuses
    flipped = copy.deepcopy(rows)
    flipped[idx]["payoff"] = 0.25
    write(flipped)
    with pytest.raises(InfrastructureError, match="payoff"):
        extension_run.verify_overlap_equality(tampered,
                                              fx["original_dir"])
    # a changed terminal value refuses
    flipped = copy.deepcopy(rows)
    flipped[idx]["terminal_value"] = "tampered"
    write(flipped)
    with pytest.raises(InfrastructureError, match="terminal_value"):
        extension_run.verify_overlap_equality(tampered,
                                              fx["original_dir"])
    # a missing overlap row refuses
    write([r for i, r in enumerate(rows) if i != idx])
    with pytest.raises(InfrastructureError, match="missing"):
        extension_run.verify_overlap_equality(tampered,
                                              fx["original_dir"])
    # the untampered surface passes
    write(rows)
    assert extension_run.verify_overlap_equality(
        tampered, fx["original_dir"]) == len(original)


def test_extension_comparator_is_immutable(extension_fixture,
                                           tmp_path, monkeypatch):
    fx = extension_fixture
    extension_loaded = dev_support.load_dev_surface(
        fx["run_dir"] / "surface",
        expected_lock_sha256=fx["result"]["surface_lock_sha256"])
    # rooted in the EXTENSION surface → refuses
    with pytest.raises(InfrastructureError, match="ORIGINAL"):
        extension_run.immutable_comparator(
            extension_loaded, fx["result"]["surface_lock_sha256"])
    # a tampered original record refuses at the rehash
    original_loaded = dev_support.load_dev_surface(
        fx["original_dir"],
        expected_lock_sha256=extension_run.EXTENSION_CONFIG[
            "original_surface_lock_sha256"])
    record = json.loads(Path(extension_run.EXTENSION_CONFIG[
        "original_c_fixed_path"]).read_text("utf-8"))
    record["c_fixed_dev"] = 3
    tampered_path = tmp_path / "c_fixed_dev.json"
    tampered_path.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setitem(extension_run.EXTENSION_CONFIG,
                        "original_c_fixed_path", str(tampered_path))
    with pytest.raises(InfrastructureError, match="rehash"):
        extension_run.immutable_comparator(
            original_loaded,
            fx["result"]["surface_lock_sha256"])


def test_extension_selection_verifier_and_tampering(extension_fixture):
    fx = extension_fixture
    loaded = dev_support.load_dev_surface(
        fx["run_dir"] / "surface",
        expected_lock_sha256=fx["result"]["surface_lock_sha256"])
    selection = json.loads(
        (fx["run_dir"] / "selection.json").read_text("utf-8"))
    extension_run.verify_extension_selection(loaded, selection)
    # a curated bucket (dropped member) refuses even when rehashed
    tampered = copy.deepcopy(selection)
    for bucket, members in tampered["direction_buckets"].items():
        if members:
            members.pop()
            break
    body = {k: v for k, v in tampered.items() if k != "record_sha256"}
    tampered["record_sha256"] = charter.content_sha256(body)
    with pytest.raises(InfrastructureError, match="rederive"):
        extension_run.verify_extension_selection(loaded, tampered)
    # a corrupted hash refuses first
    corrupted = dict(selection, record_sha256="ab" * 32)
    with pytest.raises(InfrastructureError, match="rehash"):
        extension_run.verify_extension_selection(loaded, corrupted)


def test_extension_deadline_enforced(extension_fixture, tmp_path):
    """The ceiling is enforced per observation BEFORE any worker
    executes (259_s test obligation 4)."""
    fx = extension_fixture
    prelaunch = fx["run_dir"] / "prelaunch"
    declaration = json.loads(
        (prelaunch / "declaration.json").read_text("utf-8"))
    manifest = json.loads(
        (prelaunch / "extension_launch.json").read_text("utf-8"))
    frozen_env = json.loads(
        (prelaunch / "env_manifest.json").read_text("utf-8"))
    ledger_copy = tmp_path / "ledger.md"
    shutil.copy2(fx["ledger_path"], ledger_copy)
    # the fixture ledger head is the extension closeout; admit a fresh
    # extension launch for this materialization attempt
    head = ledger.ledger_head(ledger_copy)
    frozen = extension_run.tranche_freeze()
    admitted = ledger.admit_and_append_launch(
        {"kind": "support_extension", "question": frozen["question"],
         "motivating_evidence": "deadline test",
         "freeze": {"extension_launch_sha256":
                    manifest["manifest_sha256"],
                    "scientific_design_sha256":
                    manifest["scientific_design_sha256"]},
         "parent": head,
         "budget_allocated_gpu_hours":
             manifest["budget_gpu_hours"],
         "outcome_informed": True,
         "cohort_selection": "outcome_blind"},
        head, ledger_copy, launch_manifest=manifest)

    class ExplodingRuntime:
        """The real runtime identity, but any worker execution past
        the deadline explodes."""

        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def execute_batch(self, *a, **k):
            raise AssertionError("a worker executed past the deadline")

    rt = ext_fake_rt(fx["tmp"], fx["cohort"])
    try:
        exploding = ExplodingRuntime(rt)
        with pytest.raises(InfrastructureError,
                           match="deadline exceeded"):
            dev_support.materialize_dev_support(
                exploding, declaration, tmp_path / "surface",
                launch_manifest=manifest,
                environment_manifest=frozen_env,
                expected_manifest_sha256=manifest["manifest_sha256"],
                ledger_path=ledger_copy,
                expected_head_sha256=admitted["entry_sha256"],
                _launch_validator=
                extension_run.validate_extension_launch_manifest,
                _admitted_kind="support_extension",
                _admitted_manifest_key="extension_launch_sha256",
                deadline_monotonic=0.0)
    finally:
        rt.close()
    assert not (tmp_path / "surface" / "payoffs.jsonl").exists()


def test_support_extension_admission_boundary(extension_fixture,
                                              tmp_path):
    """260_f Unit A: the ledger admits a support extension only WITH
    its own manifest, bound hash, budget, and design identity."""
    fx = extension_fixture
    ledger_copy = tmp_path / "ledger.md"
    shutil.copy2(fx["ledger_path"], ledger_copy)
    head = ledger.ledger_head(ledger_copy)
    manifest = fx["manifest"]
    base = {"kind": "support_extension", "question": "q",
            "motivating_evidence": "m",
            "freeze": {"extension_launch_sha256":
                       manifest["manifest_sha256"],
                       "scientific_design_sha256":
                       manifest["scientific_design_sha256"]},
            "parent": head,
            "budget_allocated_gpu_hours":
                manifest["budget_gpu_hours"],
            "outcome_informed": True,
            "cohort_selection": "outcome_blind"}
    with pytest.raises(InfrastructureError, match="WITH its"):
        ledger.admit_and_append_launch(dict(base), head, ledger_copy)
    with pytest.raises(InfrastructureError,
                       match="extension-launch manifest, not"):
        ledger.admit_and_append_launch(
            dict(base), head, ledger_copy,
            launch_manifest={"kind": "other"})
    bad = dict(base, freeze={"extension_launch_sha256": "ab" * 32,
                             "scientific_design_sha256":
                             manifest["scientific_design_sha256"]})
    with pytest.raises(InfrastructureError, match="exact "
                       "extension-launch manifest hash"):
        ledger.admit_and_append_launch(bad, head, ledger_copy,
                                       launch_manifest=manifest)
    bad = dict(base, budget_allocated_gpu_hours=0.5)
    with pytest.raises(InfrastructureError, match="differs from the "
                       "manifest budget"):
        ledger.admit_and_append_launch(bad, head, ledger_copy,
                                       launch_manifest=manifest)
    bad = dict(base)
    bad.pop("cohort_selection")
    with pytest.raises(InfrastructureError, match="outcome_blind"):
        ledger.admit_and_append_launch(bad, head, ledger_copy,
                                       launch_manifest=manifest)


def test_extension_overlap_divergence_aborts_before_lock(
        extension_fixture, tmp_path, monkeypatch):
    """259_s test obligation 1: overlap validation runs BEFORE the
    new lock is accepted — a run whose workers diverge from the
    original support materializes, then ABORTS at the overlap gate
    with NO surface lock written."""
    fx = extension_fixture
    ledger_copy = tmp_path / "ledger.md"
    shutil.copy2(fx["pre_extension_ledger"], ledger_copy)
    head = ledger.ledger_head(ledger_copy)
    run_dir = tmp_path / "divergent-run"
    monkeypatch.setitem(extension_run.EXTENSION_CONFIG, "run_root",
                        str(run_dir))
    # a HEALTHY worker 3 diverges from the sabotaged original
    manifest = extension_run.prepare_extension_launch(
        run_dir=run_dir,
        _runtime_factory=lambda: ext_fake_rt(
            tmp_path, fx["cohort"], sabotage_w3=False),
        _environment_builder=_env_manifest)
    with pytest.raises(InfrastructureError, match="overlap gate"):
        extension_run.execute_extension(
            run_dir=run_dir,
            expected_manifest_sha256=manifest["manifest_sha256"],
            expected_head_sha256=head,
            ledger_path=ledger_copy,
            _runtime_factory=lambda: ext_fake_rt(
                tmp_path, fx["cohort"], sabotage_w3=False),
            _environment_builder=lambda: _env_manifest(
                git_commit="feedbeef"),
            _original_surface_dir=fx["original_dir"])
    assert not (run_dir / "surface" / "surface_lock.json").exists()
    entries = ledger.verify_ledger_head(
        ledger.ledger_head(ledger_copy), ledger_copy)
    closeout = entries[-1]
    assert closeout["kind"] == "closeout"
    assert closeout["terminal_status"] == "aborted"
    assert "overlap gate" in closeout["interpretation"]
    assert closeout["freeze"]["partial_artifact_hashes"]
    extension_run.verify_extension_outputs(
        run_dir, closeout, original_surface_dir=fx["original_dir"])


def test_extension_selector_excludes_legacy_and_matches_step4(
        step4_support, monkeypatch):
    """262_s P1-1: on the REAL Step-4 surface (prefix 6) with the
    pristine domain (candidates = 6..47), every latent is legacy —
    buckets are empty, all dispositions dropped, and the legacy
    disclosure reproduces the reviewer's probe exactly."""
    for key in ("original_prefix_k", "prefix_k", "namespace"):
        monkeypatch.setitem(extension_run.EXTENSION_CONFIG, key,
                            PRISTINE_EXT_CONFIG[key])
    record = extension_run.run_extension_selector(step4_support)
    assert all(not members for members in
               record["direction_buckets"].values())
    assert all(d["status"] == "dropped_from_q3"
               for d in record["dispositions"].values())
    assert record["eligible_common_cells_q3"] == []
    legacy = record["legacy_direction_disclosure"]
    assert legacy["code_atomic"]["w2_favoured"] == [5]
    assert legacy["fork_join"]["w2_favoured"] == [1, 5]
    assert legacy["math_code"]["w3_favoured"] == [2, 3]
    # subtype disclosure covers all 108 observations
    cell_strata = {k: v for k, v in record["yield_disclosure"].items()
                   if k.startswith("cell|")}
    assert sum(sum(v.values()) for v in cell_strata.values()) == 108
    # 264_s P1: subtypes are EXACTLY the frozen public levels — and
    # math_atomic templates / lookup_math signs / fork_join branch
    # orders are represented, not collapsed
    from tasks.conductor.baselines import OBSERVABLE_SUBTYPES
    seen: dict[str, set] = {}
    for key in record["yield_disclosure"]:
        if key.startswith("subtype|"):
            cell, label = key.split("|", 1)[1].split("+", 1)
            seen.setdefault(cell, set()).add(label)
    for cell, labels in seen.items():
        assert labels <= set(OBSERVABLE_SUBTYPES[cell]), (cell, labels)
    assert len(seen["math_atomic"]) > 1
    assert len(seen["fork_join"]) > 1
    # generator-side collision analysis is SEPARATELY labelled and
    # never inside the public subtype strata
    assert any(k.startswith("generator-side-collision|")
               for k in record["yield_disclosure"])
    assert not any("pnc=" in k for k in record["yield_disclosure"]
                   if k.startswith("cell+renderer+subtype|"))
    # 266_s P1: the lossless identity-bound public-factor disclosure —
    # every observation, exact frozen subtype + derived numeric
    # factors, no private or generator-derived fields
    from tasks.conductor import baselines
    disclosure = record["public_factor_disclosure"]
    assert len(disclosure) == 108
    closed_keys = {"cell_id", "renderer_id", "latent_index",
                   "latent_program_id", "subtype",
                   "public_numeric_values", "direction"}
    for oid, row in disclosure.items():
        assert set(row) == closed_keys, oid
        latent = program.generate_latent(
            row["cell_id"], "routing_dev", row["latent_index"],
            DEFAULT_PROFILE).latent
        feature = baselines.public_feature_record(latent)
        assert row["subtype"] == baselines.observable_subtype(
            row["cell_id"], feature.params)
        assert row["public_numeric_values"] == \
            feature.public_numeric_values
        assert row["latent_program_id"] == \
            latent["latent_program_id"]
        assert "collision" not in json.dumps(row)


def test_extension_scale_lift_consumer_boundary(extension_fixture):
    """262_s P1-4: the extension comparator record WORKS in the real
    scoring boundary — ScaleLift computes on the extension surface
    without reselection; the original record refuses there; a
    tampered consumer refuses."""
    fx = extension_fixture
    loaded = dev_support.load_dev_surface(
        fx["run_dir"] / "surface",
        expected_lock_sha256=fx["result"]["surface_lock_sha256"])
    comparator = json.loads(
        (fx["run_dir"] / "comparator.json").read_text("utf-8"))
    # 264_s: an EXACT nonzero ScaleLift case — a group selecting
    # worker 3 on an observation where the fixed-w2 collapse pays
    # differently
    surface = loaded["surface"]
    oid = next(
        o["observation_id"] for o in loaded["observations"]
        if o["cell_id"] == "code_atomic"
        and surface[(o["observation_id"], (3,))]
        != surface[(o["observation_id"], (2,))])
    reward3 = surface[(oid, (3,))]
    expected_lift = reward3 - surface[(oid, (2,))]
    assert expected_lift != 0.0
    group = {"observation_id": oid,
             "completions": [
                 {"parseable": True, "valid": True,
                  "assignment": [3], "reward": reward3}] * 4}
    stats = telemetry.group_stats(group, loaded=loaded,
                                  c_fixed_record=comparator)
    assert stats["scale_lift_mean"] == pytest.approx(expected_lift)
    assert stats["cell_id"] == "code_atomic"
    # 264_s P1 reproduction: a correctly REHASHED record with bogus
    # source/original locks and a flipped worker refuses AT
    # CONSUMPTION
    forged = dict(comparator, c_fixed_dev=3,
                  source_record_sha256="ab" * 32,
                  original_surface_lock_sha256="cd" * 32)
    body = {k: v for k, v in forged.items() if k != "record_sha256"}
    forged["record_sha256"] = charter.content_sha256(body)
    with pytest.raises(InfrastructureError, match="264_s P1"):
        telemetry.group_stats(group, loaded=loaded,
                              c_fixed_record=forged)
    # each field is independently load-bearing
    for tamper in ({"c_fixed_dev": 3},
                   {"source_record_sha256": "ab" * 32},
                   {"original_surface_lock_sha256": "cd" * 32}):
        forged = dict(comparator, **tamper)
        body = {k: v for k, v in forged.items()
                if k != "record_sha256"}
        forged["record_sha256"] = charter.content_sha256(body)
        with pytest.raises(InfrastructureError, match="264_s P1"):
            telemetry.group_stats(group, loaded=loaded,
                                  c_fixed_record=forged)
    # the ORIGINAL c_fixed record cannot score the extension surface
    original_record = json.loads(Path(extension_run.EXTENSION_CONFIG[
        "original_c_fixed_path"]).read_text("utf-8"))
    with pytest.raises(InfrastructureError, match="different surface "
                       "lock"):
        telemetry.group_stats(group, loaded=loaded,
                              c_fixed_record=original_record)
    # a consumer bound to a different extension lock refuses
    tampered = dict(comparator,
                    extension_surface_lock_sha256="ab" * 32)
    body = {k: v for k, v in tampered.items() if k != "record_sha256"}
    tampered["record_sha256"] = charter.content_sha256(body)
    with pytest.raises(InfrastructureError, match="different "
                       "extension surface lock"):
        telemetry.group_stats(group, loaded=loaded,
                              c_fixed_record=tampered)
    # reselected/scope flags are load-bearing
    tampered = dict(comparator, reselected=True)
    body = {k: v for k, v in tampered.items() if k != "record_sha256"}
    tampered["record_sha256"] = charter.content_sha256(body)
    with pytest.raises(InfrastructureError, match="never-reselected"):
        telemetry.group_stats(group, loaded=loaded,
                              c_fixed_record=tampered)


def test_extension_cache_served_retry_completes(extension_fixture,
                                                tmp_path, monkeypatch):
    """262_s smaller item: a reviewed retry served ENTIRELY from the
    warm slw cache (zero live generations) completes and locks."""
    fx = extension_fixture
    ledger_copy = tmp_path / "ledger.md"
    shutil.copy2(fx["pre_extension_ledger"], ledger_copy)
    head = ledger.ledger_head(ledger_copy)
    run_dir = tmp_path / "retry-run"
    monkeypatch.setitem(extension_run.EXTENSION_CONFIG, "run_root",
                        str(run_dir))
    manifest = extension_run.prepare_extension_launch(
        run_dir=run_dir,
        _runtime_factory=lambda: ext_fake_rt(fx["tmp"], fx["cohort"]),
        _environment_builder=_env_manifest)
    result = extension_run.execute_extension(
        run_dir=run_dir,
        expected_manifest_sha256=manifest["manifest_sha256"],
        expected_head_sha256=head,
        ledger_path=ledger_copy,
        _runtime_factory=lambda: ext_fake_rt(fx["tmp"], fx["cohort"]),
        _environment_builder=lambda: _env_manifest(
            git_commit="feedbeef"),
        _original_surface_dir=fx["original_dir"])
    surface_manifest = json.loads(
        (run_dir / "surface" / "manifest.json").read_text("utf-8"))
    assert surface_manifest["uncached_step_records"] == 0
    assert surface_manifest["unique_singleton_generations"] == 0
    assert surface_manifest["cache_hits"] == \
        surface_manifest["executed_step_records"] > 0
    entries = ledger.verify_ledger_head(result["ledger_head"],
                                        ledger_copy)
    assert entries[-1]["terminal_status"] == "complete"


def test_extension_cli_is_hash_bound(extension_fixture):
    """262_s smaller item: the CLI exists, requires the reviewed
    hashes, and the verify command refuses an unknown closeout."""
    with pytest.raises(SystemExit):
        extension_run.main(["execute"])          # hashes are required
    with pytest.raises(SystemExit):
        extension_run.main(["verify"])
    with pytest.raises(InfrastructureError, match="no ledger entry"):
        extension_run.main(["verify",
                            "--closeout-entry-sha256", "ab" * 32])


# --- Unit B: the P0 mixture (269_s scope) --------------------------------------

@pytest.fixture(scope="module")
def p0_mixture_fixture(tmp_path_factory):
    """The REAL committed extension surface + frozen selection, via
    the production restore path — clean-clone valid. The extension
    fixture's module-scoped config patch may still be active in
    full-suite order, so the PRISTINE values are pinned here."""
    mp = pytest.MonkeyPatch()
    for key in ("original_surface_lock_sha256", "original_prefix_k",
                "prefix_k", "search_cap", "run_root",
                "original_c_fixed_path", "namespace",
                "original_surface_dir"):
        mp.setitem(extension_run.EXTENSION_CONFIG, key,
                   PRISTINE_EXT_CONFIG[key])
    replica = tmp_path_factory.mktemp("mixture") / "surface"
    support_run.restore_surface_evidence(
        "plans/conductor/evidence/support_extension_v1/surface",
        replica)
    loaded = dev_support.load_dev_surface(
        replica, expected_lock_sha256=p0_mixture.MIXTURE_CONFIG[
            "extension_surface_lock_sha256"])
    selection = p0_mixture.load_frozen_selection()
    mixture = p0_mixture.build_mixture(loaded, selection)
    yield {"loaded": loaded, "selection": selection,
           "mixture": mixture}
    mp.undo()


def test_p0_mixture_is_the_269s_schedule(p0_mixture_fixture):
    fx = p0_mixture_fixture
    mixture = fx["mixture"]
    proj = mixture["projections"]
    assert proj["epoch_rows"] == 157
    assert proj["class_rows"] == {"q2_composite": 32,
                                  "direct_specialist_control": 5,
                                  "anchor": 18,
                                  "goal_first_control": 18,
                                  "bridge": 84}
    # 271_s B1: the fork_join w2 renderer allocation is the EXPLICIT
    # frozen quota — 4 bound_var + 14 goal_first
    disclosure = fx["selection"]["public_factor_disclosure"]
    fj_strata = {}
    for oid, cls in mixture["class_assignment"].items():
        if cls == "q2_composite" \
                and disclosure[oid]["cell_id"] == "fork_join":
            renderer = disclosure[oid]["renderer_id"]
            fj_strata[renderer] = fj_strata.get(renderer, 0) + 1
    assert fj_strata == {"bound_var": 4, "goal_first": 14}
    # 271_s B4: composite-only balance excludes the direct-specialist
    # control; code_atomic w3 rows are that control class
    exposure = proj["q2_exposure_rows_per_epoch"]
    assert exposure == {"w2_favoured": 18, "w3_favoured": 14}
    for oid, cls in mixture["class_assignment"].items():
        if disclosure[oid]["cell_id"] == "code_atomic" \
                and disclosure[oid]["direction"] == "w3_favoured":
            assert cls == "direct_specialist_control"
    # constraints + disclosures
    assert proj["p_w3_given_goal_first"] <= 0.5
    assert proj["p_w3_given_goal_first_payoff_distinct"] > 0.5
    # 271_s B2 + 273_s: the statistic IS the frozen criterion —
    # latent-block occupancy (>=2 counted from >=2 DISTINCT latents),
    # exact figures asserted
    assert proj["q1"]["fork_join"][
        "prospective_pass_probability"] == 0.9826
    assert proj["q1"]["math_atomic"][
        "prospective_pass_probability"] == 0.9085
    assert proj["q1"]["math_code"][
        "prospective_pass_probability"] == 0.9085
    for cell, q in proj["q1"].items():
        assert q["prospective_pass_probability"] >= 0.9, cell
        # independent recomputation of the block-occupancy statistic
        latents = p0_mixture.MIXTURE_CONFIG["quotas"][
            "bridge_latents"][cell]
        p = q["p_group_q1_counted_ckpt0"]
        draws_per_latent = 3 * 5
        occupied = 1.0 - (1.0 - p) ** draws_per_latent
        expect = 1.0 - (1.0 - occupied) ** latents \
            - latents * occupied * (1.0 - occupied) ** (latents - 1)
        assert q["prospective_pass_probability"] == \
            pytest.approx(expect, abs=5e-4)
        # 273_s: renderer representation superseded — occupancy is
        # DISCLOSED, not gated
        assert "renderer_two_strata_occupancy_disclosed" in q
    assert p0_mixture.MIXTURE_CONFIG["q1_gate_criterion"][
        "renderer_representation"]["superseded"] is True
    # 273_s wording: bounded imbalance is DISCLOSED with the
    # fixed-worker payoffs, and the Q2-only goal_first conditional
    # is exactly 0.5
    assert proj["constant_worker_payoffs_on_composite_rows"] == {
        "always_w2": 0.78125, "always_w3": 0.71875}
    assert proj["p_w3_given_goal_first_q2_composite_only"] == 0.5
    # 271_s B4: true Q1 rate for code_atomic is 32/72
    assert proj["q1"]["code_atomic"][
        "p_group_q1_counted_ckpt0"] == pytest.approx(32 / 72, abs=1e-4)
    # latent 42 screened; lookups anchor-only; anchor identity;
    # bridge never payoff-distinct
    for oid, cls in mixture["class_assignment"].items():
        row = disclosure[oid]
        assert not (row["cell_id"] == "fork_join"
                    and row["latent_index"] == 42)
        if row["cell_id"] in ("lookup_atomic", "lookup_math"):
            assert cls == "anchor"
        if cls == "anchor":
            assert row["latent_index"] == 0
        if cls == "bridge":
            assert row["direction"] in ("tied", "no_pair")
    assert sorted(mixture["schedule_rows"]) == sorted(
        oid for oid, m in mixture["multiplicities"].items()
        for _ in range(m))
    p0_mixture.verify_mixture(fx["loaded"], fx["selection"], mixture)


def test_p0_mixture_q1_rates_rederive_from_archive(p0_mixture_fixture,
                                                   tmp_path,
                                                   monkeypatch):
    """271_s B4: the frozen q1_counted_rates literals rederive from
    the committed probe archive under the registered definition."""
    replica = tmp_path / "surface"
    support_run.restore_surface_evidence(
        "plans/conductor/evidence/routing_dev_support_v1/surface",
        replica)
    original = dev_support.load_dev_surface(
        replica,
        expected_lock_sha256=extension_run.PRISTINE_ORIGINAL_LOCK
        if hasattr(extension_run, "PRISTINE_ORIGINAL_LOCK")
        else PRISTINE_EXT_CONFIG["original_surface_lock_sha256"])
    rates = p0_mixture.q1_counted_rates_from_archive(original)
    assert rates == p0_mixture.MIXTURE_CONFIG["q1_counted_rates"]


def test_p0_mixture_bridge_predicate_registered_condition():
    """271_s smaller item: the reward-0.5 route must have STRICTLY
    LOWER family correctness."""
    from tasks.conductor.stage1 import NODE_FAMILIES, WORKER_FAMILIES
    fams = sorted(NODE_FAMILIES["math_atomic"])
    (fc_worker,) = [w for w, f in WORKER_FAMILIES.items()
                    if f == NODE_FAMILIES["math_atomic"][fams[0]]]
    wrong = next(w for w in range(4) if w != fc_worker
                 and WORKER_FAMILIES.get(w)
                 != NODE_FAMILIES["math_atomic"][fams[0]])
    # 0.5 only on the family-correct route: NOT bridge-eligible
    assert not p0_mixture.bridge_eligible(
        "math_atomic", {(fc_worker,): 1.0, (wrong,): 1.0})
    assert not p0_mixture.bridge_eligible(
        "math_atomic", {(fc_worker,): 0.5, (wrong,): 0.0})
    # reward-1 family-correct + 0.5 on a lower-fc route: eligible
    assert p0_mixture.bridge_eligible(
        "math_atomic", {(fc_worker,): 1.0, (wrong,): 0.5})


def test_p0_mixture_verifier_and_bindings(p0_mixture_fixture,
                                          tmp_path, monkeypatch):
    fx = p0_mixture_fixture
    # a curated schedule refuses even when rehashed
    tampered = copy.deepcopy(fx["mixture"])
    tampered["schedule_rows"] = tampered["schedule_rows"][:-1]
    body = {k: v for k, v in tampered.items() if k != "record_sha256"}
    tampered["record_sha256"] = charter.content_sha256(body)
    with pytest.raises(InfrastructureError, match="rederive"):
        p0_mixture.verify_mixture(fx["loaded"], fx["selection"],
                                  tampered)
    # 271_s B3: a modified selection RETAINING the frozen pointer
    # refuses at the CONSUMING boundary (body rehash)
    forged = copy.deepcopy(fx["selection"])
    forged["eligible_common_cells_q3"] = ["fork_join"]
    with pytest.raises(InfrastructureError, match="does not rehash"):
        p0_mixture.build_mixture(fx["loaded"], forged)
    # a selection with a DIFFERENT (self-consistent) hash refuses at
    # the expected-record check
    body = {k: v for k, v in forged.items() if k != "record_sha256"}
    forged["record_sha256"] = charter.content_sha256(body)
    with pytest.raises(InfrastructureError, match="not the frozen"):
        p0_mixture.build_mixture(fx["loaded"], forged)
    # tampered frozen-selection bytes refuse at the loader
    bad = tmp_path / "selection.json"
    bad.write_text(json.dumps(forged), encoding="utf-8")
    monkeypatch.setitem(p0_mixture.MIXTURE_CONFIG,
                        "selection_evidence_path", str(bad))
    with pytest.raises(InfrastructureError, match="not the frozen"):
        p0_mixture.load_frozen_selection()
    monkeypatch.undo()
    # 271_s B3: the LIVE-CONFIG guard — a mutated config cannot ride
    # under the import-time frozen hash
    monkeypatch.setitem(
        p0_mixture.MIXTURE_CONFIG["quotas"], "q2_w2_fork_join",
        {"bound_var": 0, "goal_first": 5})
    with pytest.raises(InfrastructureError, match="mutated after "
                       "import"):
        p0_mixture.build_mixture(fx["loaded"], fx["selection"])
    # 273_s smaller item: the freeze mirrors the guard
    with pytest.raises(InfrastructureError, match="mutated after "
                       "import"):
        p0_mixture.tranche_freeze()
    monkeypatch.undo()
    # constraint logic itself: rebind BOTH config and its hash so the
    # guard passes, then the Q2 minimum refuses
    mutated = copy.deepcopy(p0_mixture.MIXTURE_CONFIG)
    mutated["quotas"]["q2_w2_fork_join"] = {"bound_var": 0,
                                            "goal_first": 5}
    monkeypatch.setattr(p0_mixture, "MIXTURE_CONFIG", mutated)
    monkeypatch.setattr(p0_mixture, "CONFIG_SHA256",
                        charter.content_sha256(mutated))
    with pytest.raises(InfrastructureError, match="under the frozen "
                       "minimum"):
        p0_mixture.build_mixture(fx["loaded"], fx["selection"])


# --- Unit C: the exact-schedule zero-update exposure sample --------------------

PRISTINE_UNIT_C_CONFIG = copy.deepcopy(unit_c_sample.UNIT_C_CONFIG)


def test_unit_c_freeze_binds_the_frozen_candidate():
    config = PRISTINE_UNIT_C_CONFIG
    assert config["mixture_record_sha256"].startswith("0100df2b")
    assert config["mixture_config_sha256"].startswith("92f933e8")
    assert config["extension_surface_lock_sha256"].startswith(
        "ccb1c3e2")
    assert config["epochs"] == 5
    assert config["epoch_rows"] == 157
    assert config["total_groups"] == 785
    assert config["ceiling_gpu_hours"] == 1.25
    assert config["grpo"]["seed"] == 20260801
    assert config["grpo"]["learning_rate"] == 0.0
    assert config["grpo"]["beta"] == 0.0
    assert config["lineage"]["parent_entry_sha256"].startswith(
        "b88eba02")
    assert "785 real trainer optimizer-step calls" in \
        config["zero_update_mechanism"]
    # the construction literals are EXACTLY the Step-5-validated ones
    probe = probe_run.PROBE_CONFIG
    assert config["model_id"] == probe["model_id"]
    assert config["revision"] == probe["revision"]
    assert config["lora"] == probe["lora"]
    assert config["quantization"] == probe["quantization"]
    for key, value in probe["grpo"].items():
        if key != "seed":
            assert config["grpo"][key] == value, key
    assert unit_c_sample.CONFIG_SHA256 == \
        charter.content_sha256(config)


@pytest.fixture(scope="module")
def unit_c_fixture(tmp_path_factory):
    """The restored extension surface + frozen mixture, with the
    Unit-C config pinned to the replica (config sha rebound so the
    freeze/verify guards stay internally consistent)."""
    mp = pytest.MonkeyPatch()
    for key in ("original_surface_lock_sha256", "original_prefix_k",
                "prefix_k", "search_cap", "run_root",
                "original_c_fixed_path", "namespace",
                "original_surface_dir"):
        mp.setitem(extension_run.EXTENSION_CONFIG, key,
                   PRISTINE_EXT_CONFIG[key])
    replica = tmp_path_factory.mktemp("unit-c") / "surface"
    support_run.restore_surface_evidence(
        "plans/conductor/evidence/support_extension_v1/surface",
        replica)
    mp.setitem(unit_c_sample.UNIT_C_CONFIG, "extension_surface_dir",
               str(replica))
    mp.setattr(unit_c_sample, "CONFIG_SHA256", charter.content_sha256(
        unit_c_sample.UNIT_C_CONFIG))
    loaded = unit_c_sample.load_locked_extension()
    mixture = unit_c_sample.frozen_mixture(loaded)
    yield {"loaded": loaded, "mixture": mixture}
    mp.undo()


def test_unit_c_schedule_and_identity(unit_c_fixture):
    fx = unit_c_fixture
    rows = unit_c_sample.unit_c_schedule(fx["loaded"], fx["mixture"])
    assert len(rows) == 785
    epoch = fx["mixture"]["schedule_rows"]
    ids = [r["observation_id"] for r in rows]
    assert ids == epoch * 5          # five identical frozen passes
    manifest = unit_c_sample.static_identity_manifest(
        fx["loaded"], fx["mixture"])
    body = {k: v for k, v in manifest.items()
            if k != "manifest_sha256"}
    assert manifest["manifest_sha256"] == charter.content_sha256(body)
    assert manifest["mixture_record_sha256"] == \
        fx["mixture"]["record_sha256"]
    # the comparator loader authenticates the frozen Unit-A record
    comparator = unit_c_sample.load_extension_comparator()
    assert comparator["c_fixed_dev"] == 2
    assert comparator["reselected"] is False


def _unit_c_synthetic_archive(fx, run_root, sabotage_cell=None,
                              q2_specialists=True, crossed=False):
    """A full synthetic 785-row archive: bridge groups carry the Q1
    event (except `sabotage_cell`), everything else is a uniform
    valid group; rewards authenticate against the locked surface."""
    from tasks.conductor import program
    from tasks.conductor.grpo_task import positional_to_semantic
    from tasks.conductor.profiles import DEFAULT_PROFILE
    from tasks.conductor.stage1 import NODE_FAMILIES, WORKER_FAMILIES

    loaded, mixture = fx["loaded"], fx["mixture"]
    surface = loaded["surface"]
    selection = p0_mixture.load_frozen_selection()
    disclosure = selection["public_factor_disclosure"]
    classes = mixture["class_assignment"]
    rows = unit_c_sample.unit_c_schedule(loaded, mixture)
    run_root.mkdir(parents=True, exist_ok=True)

    def fc(cell, assignment):
        fams = NODE_FAMILIES[cell]
        nodes = sorted(fams)
        return sum(1 for n, w in zip(nodes, assignment)
                   if WORKER_FAMILIES.get(w) == fams[n]) / len(nodes)

    plan_cache = {}

    def code_idx(cell):
        fams = NODE_FAMILIES[cell]
        nodes = sorted(fams)
        for i, node in enumerate(nodes):
            if fams[node] == "code":
                return i
        return None

    def group_plan(oid, cell, positions, num_steps, mode):
        key = (oid, mode)
        if key in plan_cache:
            return plan_cache[key]
        candidates = []
        import itertools
        for action in itertools.product(range(4), repeat=num_steps):
            semantic = tuple(positional_to_semantic(
                list(action), positions))
            payoff = surface.get((oid, semantic))
            if payoff is None:
                continue
            candidates.append((list(action), list(semantic), payoff,
                               fc(cell, semantic)))
        if mode == "q1":
            r1 = next(c for c in candidates
                      if c[2] == 1.0 and c[3] == 1.0)
            half = next(c for c in candidates
                        if c[2] == 0.5 and c[3] < 1.0)
            plan = [r1] * 4 + [half] * 4
        elif mode == "specialists":
            idx = code_idx(cell)
            w2 = next(c for c in candidates if c[1][idx] == 2)
            w3 = next(c for c in candidates if c[1][idx] == 3)
            plan = [w2] * 4 + [w3] * 4
        elif mode == "crossed_w2":
            idx = code_idx(cell)
            w2 = next(c for c in candidates if c[1][idx] == 2)
            plan = [w2] * 8
        elif mode == "crossed_w3":
            idx = code_idx(cell)
            w3 = next(c for c in candidates if c[1][idx] == 3)
            plan = [w3] * 8
        else:
            first = candidates[0]
            plan = [first] * 8
        plan_cache[key] = plan
        return plan

    lines = []
    for i, row in enumerate(rows):
        oid = row["observation_id"]
        cell = disclosure[oid]["cell_id"]
        positions = json.loads(row["positions"])
        cls = classes.get(oid)
        if cls == "bridge" and cell in unit_c_sample.CRITICAL_CELLS \
                and cell != sabotage_cell:
            mode = "q1"
        elif cls == "q2_composite" and crossed:
            # 278_s P1 reproduction: every math_code->w3 row selects
            # worker 2; every fork_join->w2 row selects worker 3
            mode = "crossed_w2" if cell == "math_code" \
                else "crossed_w3"
        elif cls in ("q2_composite", "direct_specialist_control") \
                and q2_specialists:
            mode = "specialists"
        else:
            mode = "uniform"
        plan = group_plan(oid, cell, positions, row["num_steps"],
                          mode)
        lines.append(json.dumps({
            "global_group_index": i, "observation_id": oid,
            "completions": [json.dumps({"worker_ids": a})
                            for a, _, _, _ in plan],
            "actions": [a for a, _, _, _ in plan],
            "assignments": [s for _, s, _, _ in plan],
            "rewards": [p for _, _, p, _ in plan]}))
    (run_root / "actions.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    return rows


def test_unit_c_exposure_report_and_verifier(unit_c_fixture,
                                             tmp_path, monkeypatch):
    fx = unit_c_fixture
    run_root = tmp_path / "unit-c"
    rows = _unit_c_synthetic_archive(fx, run_root)
    report = unit_c_sample.build_exposure_report(run_root)
    # every critical cell passes the frozen block-occupancy gate
    assert report["q1_gate_pass_all_cells"] is True
    for cell, gate in report["q1_gate"].items():
        assert gate["pass"] is True
        assert len(gate["distinct_latents"]) >= 2
    # 276_s B1: per-direction Q2 blocks over q2_composite ONLY
    assert report["q2_blocks"]["math_code|w3_favoured"]["draws"] == 70
    assert report["q2_blocks"]["fork_join|w2_favoured"]["draws"] == 90
    for block in report["q2_blocks"].values():
        assert block["code_worker_selections"]["2"] >= 8
        assert block["code_worker_selections"]["3"] >= 8
    # 276_s B2: the measurable cold-start gate authorizes Q2
    assert report["q2_cold_start_gate"]["pass"] is True
    assert report["preregistered_decision"].startswith(
        "Q1 + Q2 hierarchical-unlocking authorized")
    assert report["per_class_draws"]["bridge"] == 84 * 5
    # 276_s B3: the registered strata carry raw denominators; the
    # sizing inputs and frozen rule are in the report
    assert any(k.count("|") == 3 for k in report["strata"])
    sample_stratum = next(iter(report["strata"].values()))
    assert {"draws", "valid_completions", "zero_variance_groups",
            "q1_counted_groups",
            "code_worker_selections"} <= set(sample_stratum)
    assert report["anchor_stability"]
    assert set(report["q1_counted_per_epoch_measured"]) == set(
        unit_c_sample.CRITICAL_CELLS)
    assert report["p0_sizing_rule"][
        "target_q1_counted_groups_per_critical_cell"] == 100

    # 276_s B1 regression: non-Q2 eligibility positive while the Q2
    # population's eligibility is ZERO — and the cold-start gate
    # fails, reaching the signed Q1-only branch (276_s B2)
    fail_root = tmp_path / "unit-c-q2fail"
    _unit_c_synthetic_archive(fx, fail_root, q2_specialists=False)
    fail_report = unit_c_sample.build_exposure_report(fail_root)
    q2_eligible = sum(
        block["c2_eligible_completions"]
        for block in fail_report["q2_blocks"].values())
    assert q2_eligible == 0
    # bridge rows DO carry eligible completions (fc incl. the Code
    # specialist) — the old population bug would have reported them
    bridge_eligible_completions = sum(
        s["code_worker_selections"]["2"]
        + s["code_worker_selections"]["3"]
        for key, s in fail_report["strata"].items()
        if key.endswith("|bridge"))
    assert bridge_eligible_completions > 0
    assert fail_report["q2_cold_start_gate"]["pass"] is False
    assert "Q1-only" in fail_report["preregistered_decision"]

    # 278_s P1 reproduction: CROSSED-WRONG selections — massive
    # global marginals in both workers, zero on-target — must FAIL
    crossed_root = tmp_path / "unit-c-crossed"
    _unit_c_synthetic_archive(fx, crossed_root, crossed=True)
    crossed_report = unit_c_sample.build_exposure_report(crossed_root)
    marginals = crossed_report[
        "q2_specialist_marginals_valid_completions_diagnostic"]
    assert marginals["2"] >= 8 and marginals["3"] >= 8
    gate = crossed_report["q2_cold_start_gate"]
    assert gate["pass"] is False
    for detail in gate["per_direction"].values():
        assert detail["target_selections"] == 0
        assert detail["pass"] is False
    assert "Q1-only" in crossed_report["preregistered_decision"]

    # 278_s P1: the mechanical sizing derivation (exact integers)
    sizing = unit_c_sample.derive_p0_size(
        {"code_atomic": 100, "fork_join": 20,
         "math_atomic": 10, "math_code": 4})
    assert sizing["derived_epochs"] == 125        # ceil(500/4)
    assert sizing["derived_groups"] == 125 * 157
    assert sizing["min_cell"] == "math_code"
    assert unit_c_sample.derive_p0_size(
        {"code_atomic": 1, "fork_join": 1,
         "math_atomic": 1, "math_code": 0})["derivable"] is False
    derived = report["p0_size_derived"]
    assert derived["derivable"] is True
    assert derived["derived_epochs"] >= 1
    assert derived["operational_ceiling_hours"] == 10.0
    # 280_s P1: the frozen cap formula is executable and its
    # semantics are fixed — the ceiling is NOT all rollout
    cap = unit_c_sample.derive_p0_cap(
        cumulative_consumed_seconds=1800.0,
        measured_finalization_reserve_seconds=2400.0,
        frozen_non_rollout_overhead_seconds=600.0,
        measured_whole_epoch_seconds=600.0)
    assert cap["available_generation_seconds"] == 31200.0
    assert cap["capped_epochs"] == 52
    assert cap["stop_for_reviewed_amendment"] is False
    exhausted = unit_c_sample.derive_p0_cap(
        cumulative_consumed_seconds=35000.0,
        measured_finalization_reserve_seconds=2000.0,
        frozen_non_rollout_overhead_seconds=0.0,
        measured_whole_epoch_seconds=600.0)
    assert exhausted["capped_epochs"] == 0
    assert exhausted["stop_for_reviewed_amendment"] is True
    assert "UNDER-TARGET" in cap["capped_semantics"]
    # the frozen key-set binding matches the validated construction
    key_set = unit_c_sample.UNIT_C_CONFIG["lora_key_set"]
    real_keys = sorted(json.loads(Path(
        "plans/conductor/evidence/grouped_probe_v1/"
        "checkpoint_zero_hashes.json").read_text("utf-8")))
    assert len(real_keys) == key_set["count"] == 504
    assert charter.content_sha256(real_keys) == \
        key_set["sorted_keys_sha256"]

    # 278_s smaller item: a truncated archive cannot produce a
    # report at all
    truncated_root = tmp_path / "unit-c-truncated"
    truncated_root.mkdir()
    lines = (run_root / "actions.jsonl").read_text(
        "utf-8").splitlines()
    (truncated_root / "actions.jsonl").write_text(
        "\n".join(lines[:580]) + "\n", encoding="utf-8")
    with pytest.raises(InfrastructureError, match="frozen "
                       "785-row schedule"):
        unit_c_sample.build_exposure_report(truncated_root)

    # the failure branch: a silent math_code bridge cell stops
    sab_root = tmp_path / "unit-c-sab"
    _unit_c_synthetic_archive(fx, sab_root,
                              sabotage_cell="math_code")
    sab_report = unit_c_sample.build_exposure_report(sab_root)
    assert sab_report["q1_gate"]["math_code"]["pass"] is False
    assert sab_report["q1_gate_pass_all_cells"] is False
    assert "stop-and-review" in sab_report["preregistered_decision"]

    # the anchored verifier over a complete archive
    env = json.loads(Path(
        "plans/conductor/evidence/resume_validation_v4/"
        "environment_manifest.json").read_text("utf-8"))
    identity = unit_c_sample.static_identity_manifest(
        fx["loaded"], fx["mixture"])
    config = unit_c_sample.UNIT_C_CONFIG
    preflight = {"free_mib": config["min_free_vram_mib"] + 79,
                 "total_mib": 24564,
                 "floor_mib": config["min_free_vram_mib"]}
    real_keys = sorted(json.loads(Path(
        "plans/conductor/evidence/grouped_probe_v1/"
        "checkpoint_zero_hashes.json").read_text("utf-8")))
    adapter_map = {key: "aa" * 32 for key in real_keys}
    total = config["total_groups"]
    group_size = config["grpo"]["group_size"]
    counters = {"generated_groups": total, "consumed_groups": total,
                "optimizer_updates": total,
                "sampled_completions": total * group_size}
    trace_rows = resume_validation.read_trace(
        run_root / "actions.jsonl")
    valid = sum(1 for row in trace_rows for a in row["actions"]
                if a is not None)
    for name, payload in (
            ("environment_manifest.json", env),
            ("identity_manifest.json", identity),
            ("session_preflight.json", preflight),
            ("schedule.json",
             [r["observation_id"] for r in rows]),
            ("checkpoint_zero_hashes.json", adapter_map),
            ("checkpoint_final_hashes.json", adapter_map)):
        (run_root / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    record = {
        "tranche": config["tranche"],
        "freeze_sha256":
            unit_c_sample.tranche_freeze()["freeze_sha256"],
        "config_sha256": unit_c_sample.CONFIG_SHA256,
        "identity_manifest_sha256": identity["manifest_sha256"],
        "environment_manifest_sha256":
            dev_support.validate_env_self_hash(env),
        "attested_environment_sha256":
            resume_validation.attested_environment_sha256(env),
        "session_preflight": preflight,
        "session_preflight_sha256":
            charter.content_sha256(preflight),
        "checkpoint_zero_adapter_sha256":
            charter.content_sha256(adapter_map),
        "final_adapter_sha256": charter.content_sha256(adapter_map),
        "counters": counters,
        "mixture_record_sha256": fx["mixture"]["record_sha256"],
        "execution_telemetry": {
            "group_accounting": counters,
            "surface_reward_lookups": valid,
            "live_worker_calls": 0,
            "worker_cache": "not-applicable",
            "wall_seconds": 1.0,
            "deadline_seconds":
                config["ceiling_gpu_hours"] * 3600.0,
            "peak_reserved_vram_mib": 0,
            "session_preflight": preflight,
        },
    }
    for name, payload in (("exposure_report.json", report),
                          ("sample_record.json", record)):
        (run_root / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    result = unit_c_sample.verify_unit_c_run(
        run_root, identity["manifest_sha256"],
        record["attested_environment_sha256"])
    assert result["verdict"] == "PASS"
    assert result["decision"].startswith(
        "Q1 + Q2 hierarchical-unlocking authorized")
    # anchors refuse substitution
    with pytest.raises(InfrastructureError, match="REVIEWED"):
        unit_c_sample.verify_unit_c_run(
            run_root, "ab" * 32,
            record["attested_environment_sha256"])
    # 278_s smaller item: {} == {} cannot satisfy zero-mutation
    zero_path = run_root / "checkpoint_zero_hashes.json"
    final_path = run_root / "checkpoint_final_hashes.json"
    good_zero = zero_path.read_text("utf-8")
    good_final_ = final_path.read_text("utf-8")
    for path_ in (zero_path, final_path):
        path_.write_text("{}\n", encoding="utf-8")
    with pytest.raises(InfrastructureError, match="no substrate"):
        unit_c_sample.verify_unit_c_run(
            run_root, identity["manifest_sha256"],
            record["attested_environment_sha256"])
    # 280_s P2: a one-key lora map is NOT the validated 504-key set
    partial = {"base_model.model.lora_A.default.weight": "aa" * 32}
    partial_digests = dict(
        record,
        checkpoint_zero_adapter_sha256=charter.content_sha256(
            partial),
        final_adapter_sha256=charter.content_sha256(partial))
    for path_ in (zero_path, final_path):
        path_.write_text(json.dumps(partial, indent=1,
                                    sort_keys=True) + "\n",
                         encoding="utf-8")
    (run_root / "sample_record.json").write_text(
        json.dumps(partial_digests, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    with pytest.raises(InfrastructureError, match="504-key"):
        unit_c_sample.verify_unit_c_run(
            run_root, identity["manifest_sha256"],
            record["attested_environment_sha256"])
    (run_root / "sample_record.json").write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    zero_path.write_text(good_zero, encoding="utf-8")
    final_path.write_text(good_final_, encoding="utf-8")

    # a final-map mismatch refuses on the persisted maps — the
    # FULL validated key set with one mutated value, so the tamper
    # reaches the zero-mutation comparison itself
    good = final_path.read_text("utf-8")
    mutated_map = dict(adapter_map)
    mutated_map[real_keys[0]] = "bb" * 32
    final_path.write_text(json.dumps(
        mutated_map, indent=1,
        sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(InfrastructureError,
                       match="zero-mutation gate FAILS"):
        unit_c_sample.verify_unit_c_run(
            run_root, identity["manifest_sha256"],
            record["attested_environment_sha256"])
    final_path.write_text(good, encoding="utf-8")
    # a tampered schedule refuses against the frozen mixture
    schedule_path = run_root / "schedule.json"
    good_schedule = schedule_path.read_text("utf-8")
    swapped = json.loads(good_schedule)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    schedule_path.write_text(json.dumps(swapped, indent=1) + "\n",
                             encoding="utf-8")
    with pytest.raises(InfrastructureError, match="frozen mixture"):
        unit_c_sample.verify_unit_c_run(
            run_root, identity["manifest_sha256"],
            record["attested_environment_sha256"])
    schedule_path.write_text(good_schedule, encoding="utf-8")
    assert unit_c_sample.verify_unit_c_run(
        run_root, identity["manifest_sha256"],
        record["attested_environment_sha256"])["verdict"] == "PASS"


# --- Unit B2: the versioned mixture (290_f signed plan) ------------------------

def test_b2_freeze_v1_untouched_and_c1_hard_gate(monkeypatch,
                                                 tmp_path):
    """288_s §1: the V1 path is byte-untouched (its frozen identities
    stand) and the committed C1 archive reverifies through it — the
    HARD GATE, here running at the B2 freeze. Pristine values are
    computed from the import-time captures so earlier module-scoped
    fixtures cannot leak into the gate."""
    assert charter.content_sha256(PRISTINE_UNIT_C_CONFIG) == (
        "69f73a5811922bea3ef6d04a891817bec13e30729b1741f4500f2f1f2bb"
        "02d59")
    assert p0_mixture.CONFIG_SHA256 == (
        "92f933e84d6c1c83f258437da30e352a79da7c3e01df87d3ffdf9f7ddc"
        "386bf8")
    # run the gate under the PRISTINE V1 config regardless of test
    # order (other fixtures patch the live globals module-scoped)
    monkeypatch.setattr(unit_c_sample, "UNIT_C_CONFIG",
                        copy.deepcopy(PRISTINE_UNIT_C_CONFIG))
    monkeypatch.setattr(unit_c_sample, "CONFIG_SHA256",
                        charter.content_sha256(
                            PRISTINE_UNIT_C_CONFIG))
    result = p0_mixture_v2.reverify_c1_archive()
    assert result["verdict"] == "PASS"
    assert "stop-and-review" in result["decision"]
    # B2 config literals
    config = p0_mixture_v2.MIXTURE_V2_CONFIG
    assert config["quotas"]["bridge_latents"] == {
        "code_atomic": 2, "fork_join": 13, "math_code": 13,
        "math_atomic": 0}
    assert config["p0_sizing_rule"]["sizing_cells"] == [
        "code_atomic", "fork_join", "math_code"]
    assert config["prospective_probability_refusal"][
        "superseded"] is True
    assert config["lineage"]["parent_entry_sha256"].startswith(
        "9f4661a8")
    assert p0_mixture_v2.CONFIG_V2_SHA256 == charter.content_sha256(
        config)
    # 292_s B1 / 294_s: the AUTHORITATIVE C1-basis verifier is the
    # only rate path, runs FRESH each call, and tolerates a valid
    # later ledger suffix (the C1 closeout is a HISTORICAL entry
    # within the chain, not required to be the head)
    assert p0_mixture_v2.verify_c1_basis() == {
        "code_atomic": [32, 60], "fork_join": [3, 60],
        "math_code": [7, 150]}
    assert p0_mixture_v2.c1_rates_rederived() == \
        p0_mixture_v2.verify_c1_basis()
    frozen = p0_mixture_v2.tranche_freeze()
    assert frozen["freeze_sha256"]
    # 294_s regression (a): tampering AFTER an earlier successful
    # call refuses — no cache at the mandatory boundary
    real_verify = unit_c_sample.verify_unit_c_run

    def failing_verify(*a, **k):
        raise InfrastructureError("tampered after warm call")

    monkeypatch.setattr(unit_c_sample, "verify_unit_c_run",
                        failing_verify)
    with pytest.raises(InfrastructureError, match="tampered after "
                       "warm call"):
        p0_mixture_v2.verify_c1_basis()
    with pytest.raises(InfrastructureError, match="tampered after "
                       "warm call"):
        p0_mixture_v2.tranche_freeze()
    monkeypatch.setattr(unit_c_sample, "verify_unit_c_run",
                        real_verify)
    # 294_s regression (b): a valid LATER ledger suffix does not
    # break the historical-closeout check
    import shutil as _shutil
    ledger_copy = tmp_path / "ledger-suffix.md"
    _shutil.copy2(ledger.LEDGER_PATH, ledger_copy)
    head = ledger.ledger_head(ledger_copy)
    ledger.append_ledger_entry(
        _note(question="post-C1 bookkeeping",
              motivating_evidence="294_s suffix regression"),
        head, ledger_copy)
    assert p0_mixture_v2.verify_c1_basis(
        ledger_path=ledger_copy) == {
        "code_atomic": [32, 60], "fork_join": [3, 60],
        "math_code": [7, 150]}
    # 292_s B2: the pure decision function over the frozen matrix
    decide = p0_mixture_v2.decide_c2_outcome
    assert "stop-and-review" in decide(q1_pass=False, q2_pass=True)
    assert "Q1 + Q2" in decide(q1_pass=True, q2_pass=True)
    assert "Q1-only" in decide(q1_pass=True, q2_pass=False)
    assert "no scientific outcome" in decide(
        q1_pass=True, q2_pass=True, infrastructure_abort=True)
    contract = config["outcome_contract"]
    assert "bridge-class" in contract["q1_population"]
    assert "direct_specialist_control" in contract["q2_population"]
    # 292_s B3: the frozen schedule identity is mechanically pinned
    assert p0_mixture_v2.EXPECTED_MIXTURE_V2_RECORD_SHA256 == (
        "135a72bf4deb77048371074636d88ffebf6bd07d1c00ae349b6fcee221"
        "975b3f")
    assert p0_mixture_v2.EXPECTED_EPOCH_ROWS == 157


@pytest.fixture(scope="module")
def b2_fixture(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    for key in ("original_surface_lock_sha256", "original_prefix_k",
                "prefix_k", "search_cap", "run_root",
                "original_c_fixed_path", "namespace",
                "original_surface_dir"):
        mp.setitem(extension_run.EXTENSION_CONFIG, key,
                   PRISTINE_EXT_CONFIG[key])
    # the B2 build runs the FULL C1 gate (verify_c1_basis), which
    # needs the PRISTINE V1 config regardless of test order
    mp.setattr(unit_c_sample, "UNIT_C_CONFIG",
               copy.deepcopy(PRISTINE_UNIT_C_CONFIG))
    mp.setattr(unit_c_sample, "CONFIG_SHA256",
               charter.content_sha256(PRISTINE_UNIT_C_CONFIG))
    replica = tmp_path_factory.mktemp("b2") / "surface"
    support_run.restore_surface_evidence(
        "plans/conductor/evidence/support_extension_v1/surface",
        replica)
    loaded = dev_support.load_dev_surface(
        replica, expected_lock_sha256=p0_mixture_v2.MIXTURE_V2_CONFIG[
            "extension_surface_lock_sha256"])
    selection = p0_mixture_v2.load_frozen_selection_v2()
    mixture = p0_mixture_v2.build_mixture_v2(loaded, selection)
    yield {"loaded": loaded, "selection": selection,
           "mixture": mixture}
    mp.undo()


def test_b2_mixture_is_the_290f_schedule(b2_fixture):
    fx = b2_fixture
    m = fx["mixture"]
    disclosure = fx["selection"]["public_factor_disclosure"]
    assert len(m["schedule_rows"]) == 157
    class_rows = {}
    bridge_cells = {}
    bridge_latents = {}
    for oid, cls in m["class_assignment"].items():
        mult = m["multiplicities"][oid]
        class_rows[cls] = class_rows.get(cls, 0) + mult
        if cls == "bridge":
            cell = disclosure[oid]["cell_id"]
            bridge_cells[cell] = bridge_cells.get(cell, 0) + mult
            bridge_latents.setdefault(cell, set()).add(
                disclosure[oid]["latent_index"])
    assert class_rows == {"q2_composite": 32,
                          "direct_specialist_control": 5,
                          "anchor": 18, "goal_first_control": 18,
                          "bridge": 84}
    # the 283_s reallocation: 6/39/39, sentinel ZERO
    assert bridge_cells == {"code_atomic": 6, "fork_join": 39,
                            "math_code": 39}
    assert {cell: len(v) for cell, v in bridge_latents.items()} == {
        "code_atomic": 2, "fork_join": 13, "math_code": 13}
    # the sentinel: math_atomic present ONLY as its anchor rows
    sentinel = m["sentinel"]
    assert sentinel["cell"] == "math_atomic"
    assert sentinel["training_exposed"] is True
    assert sentinel["rows_per_epoch"] == 3
    for oid in sentinel["observation_ids"]:
        assert disclosure[oid]["latent_index"] == 0
        assert m["class_assignment"][oid] == "anchor"
    assert set(sentinel["excluded_from"]) == {
        "direct_q1_gate", "sizing_minimum", "authorization",
        "headline_q1"}
    # heuristics disclosed (never gated): the 288_s figures
    per_cell = m["heuristic_projections"]["per_cell"]
    assert per_cell["code_atomic"]["heuristic_counted_per_epoch"] \
        == 3.2
    assert per_cell["fork_join"]["heuristic_counted_per_epoch"] \
        == 1.95
    assert per_cell["math_code"]["heuristic_counted_per_epoch"] \
        == 1.82
    assert "NOT" in m["heuristic_projections"]["basis"]
    # Q2/controls/anchor unchanged from the V1 candidate
    assert m["q2_exposure_rows_per_epoch"] == {"w2_favoured": 18,
                                               "w3_favoured": 14}
    # 292_s B3: the build IS the pinned frozen identity
    assert m["record_sha256"] == \
        p0_mixture_v2.EXPECTED_MIXTURE_V2_RECORD_SHA256
    p0_mixture_v2.verify_mixture_v2(fx["loaded"], fx["selection"], m)
    # 292_s B3: a rehashed self-consistent variant refuses at the
    # PIN before any rederivation
    tampered = copy.deepcopy(m)
    tampered["schedule_rows"] = tampered["schedule_rows"][:-1]
    body = {k: v for k, v in tampered.items() if k != "record_sha256"}
    tampered["record_sha256"] = charter.content_sha256(body)
    with pytest.raises(InfrastructureError, match="frozen schedule "
                       "identity"):
        p0_mixture_v2.verify_mixture_v2(fx["loaded"], fx["selection"],
                                        tampered)


def test_b2_sentinel_block_is_executable(b2_fixture):
    """288_s §5: worker-1 events are the estimand; [2]/[3] is not
    Math unlocking; firsts are recorded."""
    fx = b2_fixture
    disclosure = fx["selection"]["public_factor_disclosure"]
    classes = fx["mixture"]["class_assignment"]
    record = fx["mixture"]
    sentinel_ids = record["sentinel"]["observation_ids"]
    sentinel_oid = sentinel_ids[0]
    surface = fx["loaded"]["surface"]
    r_w0 = surface[(sentinel_oid, (0,))]
    r_w1 = surface[(sentinel_oid, (1,))]
    assert r_w1 == 1.0 and r_w0 == 0.5
    all_zero = {"global_group_index": 5,
                "observation_id": sentinel_oid,
                "completions": ["x"] * 8,
                "actions": [[0]] * 8, "assignments": [[0]] * 8,
                "rewards": [r_w0] * 8}
    block = p0_mixture_v2.sentinel_block([all_zero], record)
    assert block["groups"] == 1
    assert block["worker1_selections"] == 0
    assert block["reward_varying_groups"] == 0
    assert block["first_worker1_group_index"] is None
    assert block["first_worker1_update_index"] is None
    # 292_s: a NON-SENTINEL math_atomic row cannot contaminate —
    # bound to the frozen ids, not the cell
    foreign = dict(all_zero, observation_id=next(
        oid for oid, row in disclosure.items()
        if row["cell_id"] == "math_atomic"
        and oid not in sentinel_ids))
    block = p0_mixture_v2.sentinel_block([foreign], record)
    assert block["groups"] == 0
    # 294_s: the population is STRUCTURALLY bound — a rehashed
    # record with a foreign sentinel population refuses at the pin
    forged = copy.deepcopy(record)
    forged["sentinel"]["observation_ids"] = sorted(
        set(sentinel_ids) | {foreign["observation_id"]})
    body = {k: v for k, v in forged.items() if k != "record_sha256"}
    forged["record_sha256"] = charter.content_sha256(body)
    with pytest.raises(InfrastructureError, match="PINNED"):
        p0_mixture_v2.sentinel_block([all_zero], forged)
    # a record with the pin but a tampered body refuses at the rehash
    stolen = copy.deepcopy(forged)
    stolen["record_sha256"] = \
        p0_mixture_v2.EXPECTED_MIXTURE_V2_RECORD_SHA256
    with pytest.raises(InfrastructureError, match="rehash"):
        p0_mixture_v2.sentinel_block([all_zero], stolen)
    # a worker-3 selection is NOT Math unlocking
    w3_row = dict(all_zero, actions=[[3]] * 8,
                  assignments=[[3]] * 8,
                  rewards=[surface[(sentinel_oid, (3,))]] * 8)
    block = p0_mixture_v2.sentinel_block([w3_row], record)
    assert block["worker1_selections"] == 0
    # a real worker-1 unlock records counts + BOTH first indices
    unlock = {"global_group_index": 9,
              "observation_id": sentinel_oid,
              "completions": ["x"] * 8,
              "actions": [[1]] * 4 + [[0]] * 4,
              "assignments": [[1]] * 4 + [[0]] * 4,
              "rewards": [r_w1] * 4 + [r_w0] * 4}
    block = p0_mixture_v2.sentinel_block([unlock], record)
    assert block["worker1_selections"] == 4
    assert block["reward1_completions"] == 4
    assert block["reward_varying_groups"] == 1
    assert block["q1_counted_groups"] == 1
    assert block["first_worker1_group_index"] == 9
    assert block["first_worker1_update_index"] == 9
    assert block["first_q1_counted_group_index"] == 9
    assert block["first_q1_counted_update_index"] == 9


def test_b2_sizing_excludes_the_sentinel():
    sizing = p0_mixture_v2.derive_p0_size_v2(
        {"code_atomic": 16, "fork_join": 10, "math_code": 9,
         "math_atomic": 0}, 5)
    assert sizing["derivable"] is True       # ma=0 no longer blocks
    assert sizing["min_cell"] == "math_code"
    assert sizing["derived_epochs"] == 56    # ceil(500/9)
    assert sizing["derived_groups"] == 56 * 157
    assert "math_atomic" not in sizing["sizing_cells"]
    dead = p0_mixture_v2.derive_p0_size_v2(
        {"code_atomic": 16, "fork_join": 0, "math_code": 9,
         "math_atomic": 0}, 5)
    assert dead["derivable"] is False
    cap = p0_mixture_v2.derive_p0_cap_v2(
        cumulative_consumed_seconds=1800.0,
        measured_finalization_reserve_seconds=2400.0,
        frozen_non_rollout_overhead_seconds=600.0,
        measured_whole_epoch_seconds=600.0)
    assert cap["capped_epochs"] == 52
    assert cap["stop_for_reviewed_amendment"] is False


# --- Unit C2: the exposure sample on the pinned B2 mixture ---------------------

PRISTINE_UNIT_C2_CONFIG = copy.deepcopy(unit_c2_sample.UNIT_C2_CONFIG)


def test_c2_freeze_binds_the_pinned_candidate():
    config = PRISTINE_UNIT_C2_CONFIG
    assert config["mixture_record_sha256"] == \
        p0_mixture_v2.EXPECTED_MIXTURE_V2_RECORD_SHA256
    assert config["mixture_config_sha256"].startswith("66d62b92")
    assert config["epochs"] == 5
    assert config["total_groups"] == 785
    assert config["grpo"]["seed"] == 20260803    # fresh
    assert config["ceiling_gpu_hours"] == 1.25
    assert config["lineage"]["parent_entry_sha256"].startswith(
        "9f4661a8")
    # identical construction literals to the validated V1 (seed only)
    v1 = PRISTINE_UNIT_C2_CONFIG, PRISTINE_UNIT_C_CONFIG
    for key in ("model_id", "revision", "lora", "quantization",
                "policy_max_new_tokens", "lora_key_set",
                "zero_update_mechanism"):
        if key == "zero_update_mechanism":
            continue
        assert config[key] == PRISTINE_UNIT_C_CONFIG[key], key
    for key, value in PRISTINE_UNIT_C_CONFIG["grpo"].items():
        if key != "seed":
            assert config["grpo"][key] == value, key
    assert unit_c2_sample.CONFIG_SHA256 == charter.content_sha256(
        config)


@pytest.fixture(scope="module")
def c2_fixture(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    for key in ("original_surface_lock_sha256", "original_prefix_k",
                "prefix_k", "search_cap", "run_root",
                "original_c_fixed_path", "namespace",
                "original_surface_dir"):
        mp.setitem(extension_run.EXTENSION_CONFIG, key,
                   PRISTINE_EXT_CONFIG[key])
    mp.setattr(unit_c_sample, "UNIT_C_CONFIG",
               copy.deepcopy(PRISTINE_UNIT_C_CONFIG))
    mp.setattr(unit_c_sample, "CONFIG_SHA256",
               charter.content_sha256(PRISTINE_UNIT_C_CONFIG))
    replica = tmp_path_factory.mktemp("c2") / "surface"
    support_run.restore_surface_evidence(
        "plans/conductor/evidence/support_extension_v1/surface",
        replica)
    mp.setitem(unit_c2_sample.UNIT_C2_CONFIG,
               "extension_surface_dir", str(replica))
    mp.setattr(unit_c2_sample, "CONFIG_SHA256",
               charter.content_sha256(unit_c2_sample.UNIT_C2_CONFIG))
    loaded = unit_c2_sample.load_locked_extension()
    mixture = unit_c2_sample.pinned_mixture(loaded)
    yield {"loaded": loaded, "mixture": mixture}
    mp.undo()


def test_c2_schedule_and_row_predicates(c2_fixture):
    """294_s obligation: EXECUTABLE row predicates with
    cross-population tests — every scheduled row belongs to exactly
    one population; Q1 = bridge-only; Q2 excludes the control; the
    sentinel population is the pinned ids."""
    fx = c2_fixture
    mixture = fx["mixture"]
    rows = unit_c2_sample.unit_c2_schedule(fx["loaded"], mixture)
    assert len(rows) == 785
    assert [r["observation_id"] for r in rows] == \
        list(mixture["schedule_rows"]) * 5
    sentinel_ids = set(mixture["sentinel"]["observation_ids"])
    populations = {}
    for oid in set(mixture["schedule_rows"]):
        population = unit_c2_sample.row_population(mixture, oid)
        populations[population] = populations.get(population, 0) + 1
        # exactly one population per row
        flags = [unit_c2_sample.is_q1_population(mixture, oid),
                 unit_c2_sample.is_q2_population(mixture, oid),
                 unit_c2_sample.is_sentinel_population(mixture, oid)]
        assert sum(flags) <= 1
        if oid in sentinel_ids:
            assert unit_c2_sample.is_sentinel_population(mixture, oid)
            assert not unit_c2_sample.is_q1_population(mixture, oid)
        if unit_c2_sample.is_q1_population(mixture, oid):
            assert mixture["class_assignment"][oid] == "bridge"
        if unit_c2_sample.is_q2_population(mixture, oid):
            assert mixture["class_assignment"][oid] == "q2_composite"
    # the control is NOT in the Q2 population
    for oid, cls in mixture["class_assignment"].items():
        if cls == "direct_specialist_control":
            assert not unit_c2_sample.is_q2_population(mixture, oid)
    # sentinel rows are anchor-class but sentinel-population
    assert populations["sentinel"] == 3
    manifest = unit_c2_sample.static_identity_manifest(
        fx["loaded"], mixture)
    body = {k: v for k, v in manifest.items()
            if k != "manifest_sha256"}
    assert manifest["manifest_sha256"] == charter.content_sha256(body)
    # a foreign row refuses population lookup
    with pytest.raises(InfrastructureError, match="not in the "
                       "pinned mixture"):
        unit_c2_sample.row_population(mixture, "nonexistent:row")


def test_c2_report_gates_and_decision(c2_fixture, tmp_path):
    """Synthetic 785-row archives exercise the gate branches on the
    B2 schedule through the frozen decision function."""
    fx = c2_fixture

    def build_archive(root, q1_cells=("code_atomic", "fork_join",
                                      "math_code"),
                      q2_specialists=True):
        from tasks.conductor.grpo_task import positional_to_semantic
        from tasks.conductor.stage1 import (
            NODE_FAMILIES, WORKER_FAMILIES,
        )
        loaded, mixture = fx["loaded"], fx["mixture"]
        surface = loaded["surface"]
        selection = p0_mixture_v2.load_frozen_selection_v2()
        disclosure = selection["public_factor_disclosure"]
        rows = unit_c2_sample.unit_c2_schedule(loaded, mixture)
        root.mkdir(parents=True, exist_ok=True)

        def fc(cell, assignment):
            fams = NODE_FAMILIES[cell]
            nodes = sorted(fams)
            return sum(1 for n, w in zip(nodes, assignment)
                       if WORKER_FAMILIES.get(w) == fams[n]) \
                / len(nodes)

        def code_idx(cell):
            fams = NODE_FAMILIES[cell]
            nodes = sorted(fams)
            for i, node in enumerate(nodes):
                if fams[node] == "code":
                    return i
            return None

        plan_cache = {}

        def group_plan(oid, cell, positions, num_steps, mode):
            key = (oid, mode)
            if key in plan_cache:
                return plan_cache[key]
            import itertools
            candidates = []
            for action in itertools.product(range(4),
                                            repeat=num_steps):
                semantic = tuple(positional_to_semantic(
                    list(action), positions))
                payoff = surface.get((oid, semantic))
                if payoff is None:
                    continue
                candidates.append(
                    (list(action), list(semantic), payoff,
                     fc(cell, semantic)))
            if mode == "q1":
                r1 = next(c for c in candidates
                          if c[2] == 1.0 and c[3] == 1.0)
                half = next(c for c in candidates
                            if c[2] == 0.5 and c[3] < 1.0)
                plan = [r1] * 4 + [half] * 4
            elif mode == "specialists":
                idx = code_idx(cell)
                w2 = next(c for c in candidates if c[1][idx] == 2)
                w3 = next(c for c in candidates if c[1][idx] == 3)
                plan = [w2] * 4 + [w3] * 4
            else:
                plan = [candidates[0]] * 8
            plan_cache[key] = plan
            return plan

        lines = []
        for i, row in enumerate(rows):
            oid = row["observation_id"]
            cell = disclosure[oid]["cell_id"]
            positions = json.loads(row["positions"])
            population = unit_c2_sample.row_population(mixture, oid)
            if population == "bridge" and cell in q1_cells:
                mode = "q1"
            elif population in ("q2_composite",
                                "direct_specialist_control") \
                    and q2_specialists:
                mode = "specialists"
            else:
                mode = "uniform"
            plan = group_plan(oid, cell, positions,
                              row["num_steps"], mode)
            lines.append(json.dumps({
                "global_group_index": i, "observation_id": oid,
                "completions": [json.dumps({"worker_ids": a})
                                for a, _, _, _ in plan],
                "actions": [a for a, _, _, _ in plan],
                "assignments": [s for _, s, _, _ in plan],
                "rewards": [p for _, _, p, _ in plan]}))
        (root / "actions.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")

    # PASS branch: all three cells + specialists
    pass_root = tmp_path / "c2-pass"
    build_archive(pass_root)
    report = unit_c2_sample.build_exposure_report(pass_root)
    assert report["q1_gate_pass_all_cells"] is True
    for cell, gate in report["q1_gate"].items():
        assert gate["pass"] is True
        assert len(gate["distinct_latents"]) >= 2
    assert report["q2_cold_start_gate"]["pass"] is True
    assert report["preregistered_decision"] == \
        "Q1 + Q2 hierarchical-unlocking authorized"
    # sizing derives over the direct-Q1 cells; sentinel absent
    assert report["p0_size_derived"]["derivable"] is True
    assert "math_atomic" not in \
        report["p0_size_derived"]["sizing_cells"]
    # the sentinel block is present, bound to the pinned record,
    # and all-[0]-style silent here (uniform anchor rows)
    sentinel = report["sentinel_block"]
    assert sentinel["cell"] == "math_atomic"
    assert sentinel["groups"] == 15          # 3 rows x 5 epochs
    assert report["per_population_draws"]["sentinel"] == 15
    assert report["per_population_draws"]["bridge"] == 84 * 5

    # Q1-only branch: fork_join silent -> direct-Q1 FAILS (stop);
    # then a Q2-fail variant reaches maximum-Q1-only
    stop_root = tmp_path / "c2-stop"
    build_archive(stop_root, q1_cells=("code_atomic", "math_code"))
    stop_report = unit_c2_sample.build_exposure_report(stop_root)
    assert stop_report["q1_gate"]["fork_join"]["pass"] is False
    assert stop_report["preregistered_decision"] == \
        "stop-and-review (no P0 launch)"
    assert stop_report["p0_size_derived"]["derivable"] is False

    q1only_root = tmp_path / "c2-q1only"
    build_archive(q1only_root, q2_specialists=False)
    q1only_report = unit_c2_sample.build_exposure_report(q1only_root)
    assert q1only_report["q1_gate_pass_all_cells"] is True
    assert q1only_report["q2_cold_start_gate"]["pass"] is False
    assert "Q1-only" in q1only_report["preregistered_decision"]

    # --- the anchored verifier over the complete pass archive ------
    env = json.loads(Path(
        "plans/conductor/evidence/resume_validation_v4/"
        "environment_manifest.json").read_text("utf-8"))
    identity = unit_c2_sample.static_identity_manifest(
        fx["loaded"], fx["mixture"])
    config = unit_c2_sample.UNIT_C2_CONFIG
    preflight = {"free_mib": config["min_free_vram_mib"] + 79,
                 "total_mib": 24564,
                 "floor_mib": config["min_free_vram_mib"]}
    real_keys = sorted(json.loads(Path(
        "plans/conductor/evidence/grouped_probe_v1/"
        "checkpoint_zero_hashes.json").read_text("utf-8")))
    adapter_map = {key: "aa" * 32 for key in real_keys}
    total = config["total_groups"]
    group_size = config["grpo"]["group_size"]
    counters = {"generated_groups": total, "consumed_groups": total,
                "optimizer_updates": total,
                "sampled_completions": total * group_size}
    trace_rows = resume_validation.read_trace(
        pass_root / "actions.jsonl")
    valid = sum(1 for row in trace_rows for a in row["actions"]
                if a is not None)
    rows = unit_c2_sample.unit_c2_schedule(fx["loaded"],
                                           fx["mixture"])
    for name, payload in (
            ("environment_manifest.json", env),
            ("identity_manifest.json", identity),
            ("session_preflight.json", preflight),
            ("schedule.json",
             [r["observation_id"] for r in rows]),
            ("checkpoint_zero_hashes.json", adapter_map),
            ("checkpoint_final_hashes.json", adapter_map)):
        (pass_root / name).write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    record = {
        "tranche": config["tranche"],
        "freeze_sha256":
            unit_c2_sample.tranche_freeze()["freeze_sha256"],
        "config_sha256": unit_c2_sample.CONFIG_SHA256,
        "identity_manifest_sha256": identity["manifest_sha256"],
        "environment_manifest_sha256":
            dev_support.validate_env_self_hash(env),
        "attested_environment_sha256":
            resume_validation.attested_environment_sha256(env),
        "session_preflight": preflight,
        "session_preflight_sha256":
            charter.content_sha256(preflight),
        "checkpoint_zero_adapter_sha256":
            charter.content_sha256(adapter_map),
        "final_adapter_sha256": charter.content_sha256(adapter_map),
        "counters": counters,
        "mixture_record_sha256":
            fx["mixture"]["record_sha256"],
        "execution_telemetry": {
            "group_accounting": counters,
            "surface_reward_lookups": valid,
            "live_worker_calls": 0,
            "worker_cache": "not-applicable",
            "wall_seconds": 1.0,
            "deadline_seconds":
                config["ceiling_gpu_hours"] * 3600.0,
            "peak_reserved_vram_mib": 0,
            "session_preflight": preflight,
        },
    }

    def write_record(payload):
        (pass_root / "sample_record.json").write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")

    (pass_root / "exposure_report.json").write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    write_record(record)
    result = unit_c2_sample.verify_unit_c2_run(
        pass_root, identity["manifest_sha256"],
        record["attested_environment_sha256"])
    assert result["verdict"] == "PASS"
    assert result["decision"] == \
        "Q1 + Q2 hierarchical-unlocking authorized"
    # 297_s regression: a SINGLE-FIELD mixture-provenance tamper in
    # the sample record refuses
    forged = dict(record, mixture_record_sha256="deadbeef" * 8)
    write_record(forged)
    with pytest.raises(InfrastructureError, match="mixture "
                       "provenance"):
        unit_c2_sample.verify_unit_c2_run(
            pass_root, identity["manifest_sha256"],
            record["attested_environment_sha256"])
    write_record(record)
    assert unit_c2_sample.verify_unit_c2_run(
        pass_root, identity["manifest_sha256"],
        record["attested_environment_sha256"])["verdict"] == "PASS"


# --- P0 spine Unit 1: schema, pinned artifact, frozen projection ---------------

def _sample_contract():
    return p0_schema.P0ScienceContract(
        schema_version=p0_schema.SCHEMA_VERSION,
        input_pins=p0_schema.InputPins(
            extension_surface_lock_sha256="a" * 64,
            selection_record_sha256="b" * 64,
            selection_file_sha256="c" * 64,
            comparator_record_sha256="d" * 64,
            pinned_mixture_record_sha256="e" * 64,
            pinned_mixture_file_sha256="f" * 64,
            c2_closeout_entry_sha256="1" * 64,
            c2_actions_file_sha256="2" * 64,
            c2_report_file_sha256="3" * 64,
            c2_schedule_file_sha256="4" * 64,
            c2_record_file_sha256="5" * 64,
            c2_identity_manifest_sha256="6" * 64,
            c2_attested_environment_sha256="7" * 64,
            c2_projection_sha256="8" * 64,
            c2_projection_file_sha256="9" * 64),
        scope=p0_schema.ActiveScope(
            q1_direct_cells=("code_atomic", "fork_join", "math_code"),
            q2_description="coarse cell-correlated unlocking",
            q3="out_of_scope",
            sentinel_cell="math_atomic",
            sentinel_observation_ids=("x", "y", "z"),
            sentinel_excluded_from=("direct_q1_gate",
                                    "sizing_minimum",
                                    "authorization", "headline_q1"),
            sentinel_training_exposed=True),
        q1=p0_schema.Q1Rule(
            version="q1-v2", population="bridge_rows",
            event=p0_schema.Q1CountedEvent(
                rule_id="q1-counted-v1",
                valid_completions_only=True, same_group=True,
                high_reward=1.0, high_family_correctness="full",
                low_reward=0.5,
                low_family_correctness="strictly_lower"),
            min_counted_groups_per_cell=2,
            min_distinct_latents_among_counted=2,
            sizing_counts=(("code_atomic", 13), ("fork_join", 34),
                           ("math_code", 13)),
            sizing_epochs=5),
        q2=p0_schema.Q2Rule(
            version="q2-v2",
            marginal_rule_id="q2-marginal-v1",
            marginal_min_target_selections=8,
            marginal_min_distinct_latents=2,
            marginal_population="valid_q2_composite",
            marginal_upstream_correctness_required=False,
            per_direction_targets=(("math_code|w3_favoured", 3),
                                   ("fork_join|w2_favoured", 2)),
            eligibility=p0_schema.EligibilityRule(
                rule_id="c2-eligibility-v1",
                non_code_routing="family_correct",
                code_worker_in=(2, 3),
                malformed_completions="excluded"),
            conditional_rule_id="q2-conditional-v1",
            conditional_numerator="c2_optimal",
            conditional_denominator="c2_eligible",
            conditional_zero_denominator="undefined",
            conditional_baselines=(
                p0_schema.ConditionalBaseline(
                    direction="fork_join|w2_favoured",
                    numerator=8, denominator=152),
                p0_schema.ConditionalBaseline(
                    direction="math_code|w3_favoured",
                    numerator=0, denominator=15)),
            marginal_baselines=(("fork_join|w2_favoured", 73),
                                ("math_code|w3_favoured", 108))),
        sizing=p0_schema.SizingRule(
            target_q1_counted_groups_per_sizing_cell=100,
            groups_per_epoch=157, nominal_epochs=39,
            operational_ceiling_hours=10.0,
            cap=p0_schema.CapRule(
                rule_id="p0-cap-v1",
                launch_epochs="min_nominal_capacity",
                capacity_inputs=(
                    "operational_ceiling_seconds",
                    "cumulative_consumed_seconds",
                    "measured_finalization_reserve_seconds",
                    "frozen_non_rollout_overhead_seconds",
                    "measured_whole_epoch_seconds"),
                capacity_zero_action="stop_reviewed_amendment",
                under_target_action="disclosed_under_target",
                spare_capacity_action="no_extra_training")),
        diagnostics=p0_schema.RequiredDiagnostics(
            items=("q1_counted_by_cell", "q2_eligibility",
                   "q2_optimality",
                   "q2_choice_conditional_on_eligibility",
                   "q2_marginal_target_selections",
                   "direct_and_semantic_contrasts",
                   "sentinel_block", "zero_variance_rate",
                   "invalid_completion_rate"),
            sentinel=p0_schema.SentinelDiagnostics(
                fields_required=(
                    "worker1_selections", "worker1_completions",
                    "reward1_completions", "reward_varying_groups",
                    "q1_counted_groups", "group_denominator",
                    "completion_denominator", "first_group_indices",
                    "first_update_indices", "checkpoint_trajectory",
                    "evaluation_trajectory"))))


def test_p0_schema_typed_invariants(tmp_path):
    import dataclasses
    contract = _sample_contract()
    # deep immutability
    with pytest.raises(dataclasses.FrozenInstanceError):
        contract.schema_version = "x"
    with pytest.raises(dataclasses.FrozenInstanceError):
        contract.q1.min_counted_groups_per_cell = 1
    # 307_s P1-3: booleans cannot pose as integers, from DIRECT
    # construction
    with pytest.raises(InfrastructureError, match="non-boolean"):
        p0_schema.Q1Rule(
            version="q1-v2", population="bridge_rows",
            event=contract.q1.event,
            min_counted_groups_per_cell=True,
            min_distinct_latents_among_counted=2,
            sizing_counts=contract.q1.sizing_counts,
            sizing_epochs=5)
    # non-finite floats refuse
    with pytest.raises(InfrastructureError, match="finite"):
        dataclasses.replace(contract.sizing,
                            operational_ceiling_hours=float("nan"))
    # wrong cell sets refuse
    with pytest.raises(InfrastructureError, match="exactly"):
        dataclasses.replace(contract.scope,
                            q1_direct_cells=("code_atomic",))
    # malformed hashes refuse
    with pytest.raises(InfrastructureError, match="hex"):
        dataclasses.replace(contract.input_pins,
                            c2_closeout_entry_sha256="XYZ")
    # the marginal gate cannot become conditional
    with pytest.raises(InfrastructureError, match="UNCONDITIONAL"):
        dataclasses.replace(
            contract.q2,
            marginal_upstream_correctness_required=True)
    # baselines are numeric records with num <= denom
    with pytest.raises(InfrastructureError, match="numerator"):
        p0_schema.ConditionalBaseline(
            direction="math_code|w3_favoured",
            numerator=16, denominator=15)
    # the sentinel diagnostic set is complete and closed
    with pytest.raises(InfrastructureError, match="exactly"):
        p0_schema.SentinelDiagnostics(
            fields_required=("worker1_selections",))
    # the 301_f diagnostics list is complete, not a menu
    with pytest.raises(InfrastructureError, match="missing"):
        p0_schema.RequiredDiagnostics(
            items=("q1_counted_by_cell",),
            sentinel=contract.diagnostics.sentinel)
    # canonical round-trip through the strict loader
    digest = p0_schema.contract_sha256(contract)
    path = tmp_path / "contract.json"
    assert p0_schema.save_contract(contract, path) == digest
    loaded = p0_schema.load_contract(path, digest)
    assert loaded == contract
    # external authentication required; tampered typed field refuses
    # at CONSTRUCTION inside the loader
    with pytest.raises(InfrastructureError, match="externally "
                       "reviewed"):
        p0_schema.load_contract(path, "0" * 64)
    payload = json.loads(path.read_text("utf-8"))
    payload["q1"]["min_counted_groups_per_cell"] = True
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="non-boolean"):
        p0_schema.load_contract(bad, digest)
    payload = json.loads(path.read_text("utf-8"))
    payload["extra"] = 1
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="unknown fields"):
        p0_schema.load_contract(bad, digest)


def test_p0_unit1_artifacts_and_replay_source(b2_fixture, tmp_path):
    """The pinned artifact double-binds and equals a fresh legacy
    rederivation; the frozen projection carries the exact 302_s
    values; the replay-source verifier passes and its tamper
    regressions refuse."""
    # pinned mixture: rehash + pin + byte-level equality with a
    # fresh legacy build on the restored surface
    pinned = p0_replay.load_pinned_mixture()
    assert pinned["record_sha256"] == \
        p0_mixture_v2.EXPECTED_MIXTURE_V2_RECORD_SHA256
    fresh = b2_fixture["mixture"]
    assert json.loads(json.dumps(fresh)) == pinned
    # one-time materialization refuses overwrite
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_replay.materialize_pinned_mixture()
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_replay.freeze_projection()
    # the frozen projection: rehash + the exact frozen values
    projection = p0_replay.load_projection()
    assert projection["per_population_draws"] == {
        "anchor": 75, "bridge": 420,
        "direct_specialist_control": 25, "goal_first_control": 90,
        "q2_composite": 160, "sentinel": 15}
    assert sum(g["counted_groups"]
               for g in projection["q1_gate"].values()) == 60
    assert projection["p0_size_derived"]["derived_epochs"] == 39
    assert projection["p0_size_derived"]["derived_groups"] == 6123
    assert projection["zero_variance_groups"] == 662
    assert projection["invalid_completions"] == 38
    assert projection["valid_completions"] == 6242
    assert projection["preregistered_decision"] == \
        "Q1 + Q2 hierarchical-unlocking authorized"
    assert len(projection["epoch_rows"]) == 157
    assert len(projection["schedule_rows"]) == 785
    assert projection["schedule_rows"] == \
        projection["epoch_rows"] * 5
    assert projection["mixture_record_sha256"] == \
        pinned["record_sha256"]
    # 307_s P1-4: exact mapping parity is IN the projection
    assert projection["class_assignment"] == \
        pinned["class_assignment"]
    assert projection["multiplicities"] == pinned["multiplicities"]
    assert projection["sentinel_observation_ids"] == \
        sorted(pinned["sentinel"]["observation_ids"])
    populations = projection["population_by_observation"]
    assert len(populations) == 150
    for oid in projection["sentinel_observation_ids"]:
        assert populations[oid] == "sentinel"
    # source pins agree with the module pins
    assert projection["source"]["report_file_sha256"] == \
        p0_replay.REPLAY_SOURCE["c2_report_file_sha256"]
    # the replay-source verifier passes on the committed state
    assert p0_replay.verify_c2_replay_source()["verdict"] == "PASS"
    # 307_s P1-1: an INCOMPLETE archive refuses — deleting the
    # identity manifest (a non-core file under the old check) fails
    # exact-set equality
    incomplete = tmp_path / "evidence-incomplete"
    shutil.copytree(p0_replay.C2_EVIDENCE_DIR, incomplete)
    (incomplete / "identity_manifest.json").unlink()
    with pytest.raises(InfrastructureError, match="missing"):
        p0_replay.verify_c2_replay_source(evidence_dir=incomplete)
    # an EXTRA file refuses too
    extra = tmp_path / "evidence-extra"
    shutil.copytree(p0_replay.C2_EVIDENCE_DIR, extra)
    (extra / "unbound.json").write_text("{}", encoding="utf-8")
    with pytest.raises(InfrastructureError, match="extra"):
        p0_replay.verify_c2_replay_source(evidence_dir=extra)
    # a tampered identity manifest refuses at manifest validation
    badid = tmp_path / "evidence-badid"
    shutil.copytree(p0_replay.C2_EVIDENCE_DIR, badid)
    identity = json.loads(
        (badid / "identity_manifest.json").read_text("utf-8"))
    identity["seed"] = "1"
    body = {k: v for k, v in identity.items()
            if k != "manifest_sha256"}
    identity["manifest_sha256"] = charter.content_sha256(body)
    (badid / "identity_manifest.json").write_text(
        json.dumps(identity, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    with pytest.raises(InfrastructureError):
        p0_replay.verify_c2_replay_source(evidence_dir=badid)
    # tamper regression: a modified evidence byte refuses BEFORE any
    # replay
    tampered = tmp_path / "evidence"
    shutil.copytree(p0_replay.C2_EVIDENCE_DIR, tampered)
    lines = (tampered / "actions.jsonl").read_text(
        "utf-8").splitlines()
    (tampered / "actions.jsonl").write_text(
        "\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(InfrastructureError):
        p0_replay.verify_c2_replay_source(evidence_dir=tampered)
    # 307_s P1-2: a tampered source cannot mint a projection —
    # extraction authenticates the bundle first
    with pytest.raises(InfrastructureError):
        p0_replay.extract_projection(evidence_dir=tampered)
    # 307_s P1-2/P2: a coherently REWRITTEN projection (recomputed
    # self-hash) refuses at the reviewed file pin; reformatted
    # pinned-mixture bytes refuse likewise
    rewritten = tmp_path / "projection.json"
    body = {k: v for k, v in projection.items()
            if k != "projection_sha256"}
    body["preregistered_decision"] = "forged decision"
    body["projection_sha256"] = charter.content_sha256(body)
    rewritten.write_text(json.dumps(body, indent=1, sort_keys=True)
                         + "\n", encoding="utf-8")
    with pytest.raises(InfrastructureError, match="file"):
        p0_replay.load_projection(path=rewritten)
    reformatted = tmp_path / "mixture.json"
    reformatted.write_text(json.dumps(pinned), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="file"):
        p0_replay.load_pinned_mixture(path=reformatted)


# --- P0 spine Unit 2: the contract instance + strict schedule loader -----------

def test_p0_contract_instance_and_pins(tmp_path):
    """The frozen instance equals a fresh build from the
    authoritative sources; it loads only under the externally
    reviewed pin; tampering refuses."""
    contract = p0_contract.load_p0_science_contract()
    rebuilt = p0_contract.build_p0_science_contract()
    assert contract == rebuilt
    assert p0_schema.contract_sha256(contract) == \
        p0_contract.CONTRACT_SHA256
    # the pins flow from the authoritative sources, not transcription
    assert contract.input_pins.c2_actions_file_sha256 == \
        p0_replay.REPLAY_SOURCE["c2_actions_file_sha256"]
    assert contract.input_pins.pinned_mixture_record_sha256 == \
        p0_mixture_v2.EXPECTED_MIXTURE_V2_RECORD_SHA256
    assert contract.input_pins.c2_projection_sha256 == \
        p0_replay.PROJECTION_SHA256
    # the sentinel ids are the pinned mixture's
    pinned = p0_replay.load_pinned_mixture()
    assert list(contract.scope.sentinel_observation_ids) == \
        sorted(pinned["sentinel"]["observation_ids"])
    # the C2-measured values are in the frozen rules
    assert dict(contract.q1.sizing_counts) == {
        "code_atomic": 13, "fork_join": 34, "math_code": 13}
    assert {b.direction: (b.numerator, b.denominator)
            for b in contract.q2.conditional_baselines} == {
        "fork_join|w2_favoured": (8, 152),
        "math_code|w3_favoured": (0, 15)}
    # one-time freeze refuses overwrite
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_contract.freeze_contract()
    # a tampered committed contract refuses under the pin
    tampered = tmp_path / "contract.json"
    payload = json.loads(Path(
        p0_contract.CONTRACT_PATH).read_text("utf-8"))
    payload["sizing"]["nominal_epochs"] = 40
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="externally "
                       "reviewed"):
        p0_contract.load_p0_science_contract(path=tampered)


def test_p0_contract_cross_checks_the_projection(monkeypatch):
    """310_s P1: construction MECHANICALLY cross-checks the
    C2-derived values against the double-bound projection — a
    projection carrying different values makes the build refuse."""
    real = p0_replay.load_projection()
    altered = copy.deepcopy(real)
    altered["p0_size_derived"]["sizing_cells"]["fork_join"] = 33
    monkeypatch.setattr(p0_replay, "load_projection",
                        lambda *a, **k: altered)
    with pytest.raises(InfrastructureError, match="sizing counts"):
        p0_contract.build_p0_science_contract()
    altered = copy.deepcopy(real)
    altered["q2_blocks"]["fork_join|w2_favoured"][
        "c2_optimal_completions"] = 9
    monkeypatch.setattr(p0_replay, "load_projection",
                        lambda *a, **k: altered)
    with pytest.raises(InfrastructureError, match="conditional "
                       "baseline"):
        p0_contract.build_p0_science_contract()
    altered = copy.deepcopy(real)
    altered["q2_cold_start_gate"]["per_direction"][
        "math_code|w3_favoured"]["target_selections"] = 107
    monkeypatch.setattr(p0_replay, "load_projection",
                        lambda *a, **k: altered)
    with pytest.raises(InfrastructureError, match="marginal "
                       "baseline"):
        p0_contract.build_p0_science_contract()


def test_p0_schedule_loader_reminders(tmp_path, monkeypatch):
    """The two 305_f-approval reminders, proven: the loader works
    with the LEGACY BUILDER DISABLED, and from a
    CLEAN-CLONE-RESTORED surface."""
    contract = p0_contract.load_p0_science_contract()

    # reminder 1: the legacy builder is DISABLED — the loader never
    # touches it
    def exploding_builder(*a, **k):
        raise AssertionError(
            "the schedule loader must never invoke the legacy "
            "builder")

    monkeypatch.setattr(p0_mixture_v2, "build_mixture_v2",
                        exploding_builder)
    epoch = p0_schedule.epoch_schedule(contract)
    assert len(epoch) == 157
    s5 = p0_schedule.schedule_for_epochs(contract, 5)
    assert s5 == epoch * 5
    # the loaded schedule IS the C2-authorized experiment
    projection = p0_replay.load_projection()
    assert epoch == projection["epoch_rows"]
    assert s5 == projection["schedule_rows"]
    # bounds: the launch freeze supplies epochs; the loader bounds
    with pytest.raises(InfrastructureError, match="positive"):
        p0_schedule.schedule_for_epochs(contract, 0)
    with pytest.raises(InfrastructureError, match="positive"):
        p0_schedule.schedule_for_epochs(contract, True)
    with pytest.raises(InfrastructureError, match="spare capacity"):
        p0_schedule.schedule_for_epochs(contract, 40)
    # 310_s P1: population_of loads the AUTHENTICATED mixture
    # internally — no caller-supplied mapping has a path in
    for oid in contract.scope.sentinel_observation_ids:
        assert p0_schedule.population_of(contract, oid) == "sentinel"
    bridge_oid = next(
        oid for oid, cls in
        p0_replay.load_pinned_mixture()["class_assignment"].items()
        if cls == "bridge")
    assert p0_schedule.population_of(contract, bridge_oid) \
        == "bridge"
    with pytest.raises(InfrastructureError, match="not a scheduled"):
        p0_schedule.population_of(contract, "foreign:row")
    # 310_s P1 regression: a one-field population substitution with
    # a stale record hash cannot enter — the double-bound loader
    # refuses the forged artifact at both bindings
    forged = copy.deepcopy(p0_replay.load_pinned_mixture())
    forged["class_assignment"][bridge_oid] = "q2_composite"
    forged_path = tmp_path / "forged_mixture.json"
    forged_path.write_text(
        json.dumps(forged, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    with pytest.raises(InfrastructureError, match="file"):
        p0_replay.load_pinned_mixture(path=forged_path)
    with pytest.raises(InfrastructureError):
        p0_replay.load_pinned_mixture(
            path=forged_path,
            expected_file_sha256=__import__("hashlib").sha256(
                forged_path.read_bytes()).hexdigest())

    # reminder 2: trainer rows from a CLEAN-CLONE-RESTORED surface
    # (an isolated replica; the legacy builder still disabled)
    replica = tmp_path / "surface"
    support_run.restore_surface_evidence(
        "plans/conductor/evidence/support_extension_v1/surface",
        replica)
    rows = p0_schedule.build_trainer_rows(contract, 1,
                                          surface_dir=replica)
    assert len(rows) == 157
    assert [r["observation_id"] for r in rows] == epoch
    assert all(r["prompt"][0]["role"] == "system" for r in rows[:3])
    # 310_s P2: repeated rows do not share mutable prompts
    dup_oid = next(oid for oid in epoch if epoch.count(oid) > 1)
    first, second = [i for i, r in enumerate(rows)
                     if r["observation_id"] == dup_oid][:2]
    rows[first]["prompt"][0]["content"] = "MUTATED"
    assert rows[second]["prompt"][0]["content"] != "MUTATED"


# --- spine Unit 3: estimands + the exact C2 replay equivalence (312_f) ---------

def test_p0_estimand_rules():
    """The versioned typed estimand rules, including BOTH 305_f §3
    counterexamples: a semantic contrast is not a Q1 counted event,
    and marginal support is not conditional success."""
    from types import SimpleNamespace
    contract = p0_contract.load_p0_science_contract()
    event = contract.q1.event
    elig = contract.q2.eligibility
    # family-correct fraction + the frozen reward ladder
    assert p0_estimands.family_correct_fraction(
        "fork_join", (0, 2, 1)) == 1.0
    assert p0_estimands.family_correct_fraction(
        "fork_join", (0, 2, 0)) == pytest.approx(2 / 3)
    with pytest.raises(InfrastructureError, match="workers"):
        p0_estimands.family_correct_fraction("fork_join", (0, 2))
    assert p0_estimands.reward_level(0.5) == 0.5
    with pytest.raises(InfrastructureError, match="ladder"):
        p0_estimands.reward_level(0.75)
    # the Q1 counted event (valid-only, same-group)
    assert p0_estimands.q1_counted_event(
        event, "code_atomic", [1.0, 0.5], [(2,), (0,)])
    assert not p0_estimands.q1_counted_event(
        event, "code_atomic", [1.0, 0.5], [None, (0,)])
    assert not p0_estimands.q1_counted_event(
        event, "code_atomic", [0.5, 0.5], [(2,), (0,)])
    # COUNTEREXAMPLE 1: levels 1 and 0.5 co-present (a semantic
    # contrast) with the 0.5 FULLY family-correct — NOT a Q1 event
    rewards, assignments = [1.0, 0.5], [(2,), (3,)]
    assert p0_estimands.group_contrasts(
        "code_atomic", rewards, assignments, None)[
        "semantic_contrast"]
    assert not p0_estimands.q1_counted_event(
        event, "code_atomic", rewards, assignments)
    with pytest.raises(InfrastructureError, match="unknown Q1"):
        p0_estimands.q1_counted_event(SimpleNamespace(
            rule_id="q1-counted-v99", valid_completions_only=True,
            same_group=True, high_reward=1.0,
            high_family_correctness="full", low_reward=0.5,
            low_family_correctness="strictly_lower"),
            "code_atomic", [], [])
    # eligibility (malformed EXCLUDED; specialist pool enforced)
    assert p0_estimands.c2_eligible_completion(
        elig, "fork_join", (0, 2, 1))
    assert not p0_estimands.c2_eligible_completion(
        elig, "fork_join", (0, 1, 1))
    assert not p0_estimands.c2_eligible_completion(
        elig, "fork_join", (1, 2, 1))
    assert not p0_estimands.c2_eligible_completion(
        elig, "fork_join", None)
    # 313_s P1: STRUCTURALLY malformed assignments are excluded
    # everywhere an estimand accepts an assignment — the reviewer's
    # reproductions are permanent regressions
    assert not p0_estimands.valid_assignment(
        "fork_join", (0, 2, 1, 0))
    assert not p0_estimands.valid_assignment("fork_join", (0,))
    assert not p0_estimands.valid_assignment(
        "fork_join", (0, True, 1))
    assert not p0_estimands.valid_assignment(
        "fork_join", (0, 7, 1))
    assert p0_estimands.valid_assignment("fork_join", (0, 2, 1))
    assert not p0_estimands.c2_eligible_completion(
        elig, "fork_join", (0, 2, 1, 0))
    assert not p0_estimands.marginal_target_selection(
        "fork_join", (0, 2, 1, 0), 2)
    assert not p0_estimands.marginal_target_selection(
        "fork_join", (0,), 2)
    assert not p0_estimands.q1_counted_event(
        event, "fork_join", [1.0, 0.5],
        [(0, 2, 1, 0), (0, 2, 0)])
    # COUNTEREXAMPLE 2: the target Code worker with a family-WRONG
    # non-Code slot — a marginal selection that is NOT eligible
    marginal_only = (1, 2, 1)
    assert p0_estimands.marginal_target_selection(
        "fork_join", marginal_only, 2)
    assert not p0_estimands.c2_eligible_completion(
        elig, "fork_join", marginal_only)
    # optimality is defined WITHIN eligibility
    pair = {"assignment_w2": [0, 2, 1], "assignment_w3": [0, 3, 1],
            "direction": 2, "distinct_payoff": True}
    assert p0_estimands.c2_optimal_completion(
        elig, "fork_join", (0, 2, 1), pair)
    assert not p0_estimands.c2_optimal_completion(
        elig, "fork_join", (0, 3, 1), pair)
    assert not p0_estimands.c2_optimal_completion(
        elig, "fork_join", (0, 2, 1), {**pair, "direction": None})
    assert not p0_estimands.c2_optimal_completion(
        elig, "fork_join", marginal_only, pair)
    # direct contrast requires BOTH VALID variants in one group
    assert p0_estimands.group_contrasts(
        "fork_join", [1.0, 0.5], [(0, 2, 1), (0, 3, 1)],
        pair)["direct_contrast"]
    assert not p0_estimands.group_contrasts(
        "fork_join", [1.0, 0.5], [(0, 2, 1), (0, 2, 1)],
        pair)["direct_contrast"]
    assert not p0_estimands.group_contrasts(
        "fork_join", [1.0, 0.5], [(0, 2, 1), (0, 3, 1, 0)],
        pair)["direct_contrast"]
    # the conditional estimand: zero denominator is UNDEFINED
    assert p0_estimands.conditional_choice(0, 15) == 0.0
    assert p0_estimands.conditional_choice(0, 0) is None
    assert p0_estimands.conditional_choice(8, 152) \
        == pytest.approx(8 / 152)
    with pytest.raises(InfrastructureError, match="count pair"):
        p0_estimands.conditional_choice(9, 8)
    # gates
    gate, ok = p0_estimands.evaluate_q1_gate(
        contract.q1, ("code_atomic",),
        {"code_atomic": {"counted_groups": 2, "latents": {1, 2},
                         "renderers": {"bound_var"},
                         "bridge_draws": 5}})
    assert ok and gate["code_atomic"]["pass"]
    _, ok = p0_estimands.evaluate_q1_gate(
        contract.q1, ("code_atomic",),
        {"code_atomic": {"counted_groups": 2, "latents": {1},
                         "renderers": {"bound_var"},
                         "bridge_draws": 5}})
    assert not ok
    q2_gate = p0_estimands.evaluate_q2_cold_start_gate(
        contract.q2,
        {"math_code|w3_favoured": {"selections": 8,
                                   "latents": {1, 2}},
         "fork_join|w2_favoured": {"selections": 7,
                                   "latents": {1, 2}}})
    assert q2_gate["per_direction"]["math_code|w3_favoured"]["pass"]
    assert not q2_gate["per_direction"]["fork_join|w2_favoured"][
        "pass"]
    assert not q2_gate["pass"]
    # sizing + the four-branch decision
    cap = {"note": "frozen prose"}
    sized = p0_estimands.derive_sizing(
        contract.sizing, ("code_atomic", "fork_join", "math_code"),
        {"code_atomic": 13, "fork_join": 34, "math_code": 13},
        5, cap)
    assert sized["derived_epochs"] == 39 \
        and sized["derived_groups"] == 6123 \
        and sized["min_cell"] == "code_atomic"
    stopped = p0_estimands.derive_sizing(
        contract.sizing, ("code_atomic",), {"code_atomic": 0},
        5, cap)
    assert not stopped["derivable"]
    matrix = p0_mixture_v2.MIXTURE_V2_CONFIG["outcome_contract"][
        "decision_matrix"]
    assert p0_estimands.decide_outcome(
        matrix, q1_pass=True, q2_pass=True) \
        == "Q1 + Q2 hierarchical-unlocking authorized"
    assert p0_estimands.decide_outcome(
        matrix, q1_pass=False, q2_pass=True) == matrix["q1_fail"]
    assert p0_estimands.decide_outcome(
        matrix, q1_pass=True, q2_pass=False) \
        == matrix["q1_pass_q2_fail"]
    assert p0_estimands.decide_outcome(
        matrix, q1_pass=True, q2_pass=True,
        infrastructure_abort=True) == matrix["infrastructure_abort"]
    with pytest.raises(InfrastructureError, match="branches"):
        p0_estimands.decide_outcome(
            {"q1_fail": "x"}, q1_pass=True, q2_pass=True)


def test_p0_sentinel_estimand():
    """The complete per-checkpoint sentinel block: both raw
    denominators, worker-1 events as the estimand (the [2]/[3]
    regression retained), firsts in group AND update indices, the
    contract-bound population, and the exact legacy view shape."""
    from types import SimpleNamespace
    contract = p0_contract.load_p0_science_contract()
    scope, event = contract.scope, contract.q1.event
    ids = list(scope.sentinel_observation_ids)
    rows = [
        {"observation_id": ids[0], "global_group_index": 0,
         "rewards": [0.0, 0.0], "assignments": [[0], [0]]},
        {"observation_id":
         "code_atomic:routing_dev:00008:67774cab:goal_first:private",
         "global_group_index": 1,
         "rewards": [1.0], "assignments": [[2]]},
        # the [2]/[3] regression: different routing, NOT unlocking
        {"observation_id": ids[1], "global_group_index": 3,
         "rewards": [0.0, 0.0], "assignments": [[2], [3]]},
        {"observation_id": ids[2], "global_group_index": 5,
         "rewards": [1.0, 0.5, 0.0],
         "assignments": [[1], [0], None]},
    ]
    block = p0_estimands.sentinel_checkpoint_block(
        scope, event, rows, updates_per_group=2)
    assert block["group_denominator"] == 3
    assert block["completion_denominator"] == 7
    assert block["worker1_selections"] == 1
    assert block["worker1_completions"] == 1
    assert block["reward1_completions"] == 1
    assert block["reward_varying_groups"] == 1
    assert block["q1_counted_groups"] == 1
    assert block["first_group_indices"] == {
        "worker1": 5, "reward1": 5, "varying": 5, "q1_counted": 5}
    assert block["first_update_indices"]["worker1"] == 10
    # the legacy view carries the exact frozen C2 field shape
    frozen_sentinel = p0_replay.load_projection()["sentinel_block"]
    view = p0_estimands.sentinel_legacy_view(block)
    assert set(view) == set(frozen_sentinel)
    assert view["groups"] == 3 and view["first_worker1_group_index"] \
        == 5 and view["first_worker1_update_index"] == 10
    # population bound: ids outside the sentinel cell refuse
    bad = SimpleNamespace(
        sentinel_observation_ids=("code_atomic:x:y",),
        sentinel_cell="math_atomic", sentinel_training_exposed=True)
    with pytest.raises(InfrastructureError, match="outside the "
                       "contract"):
        p0_estimands.sentinel_checkpoint_block(bad, event, [])
    empty = SimpleNamespace(
        sentinel_observation_ids=(), sentinel_cell="math_atomic",
        sentinel_training_exposed=True)
    with pytest.raises(InfrastructureError, match="empty sentinel"):
        p0_estimands.sentinel_checkpoint_block(empty, event, [])
    with pytest.raises(InfrastructureError, match="positive "
                       "non-boolean"):
        p0_estimands.sentinel_checkpoint_block(
            scope, event, [], updates_per_group=True)
    # 313_s: a forged group index refuses inside the sentinel block
    with pytest.raises(InfrastructureError, match="non-negative "
                       "non-boolean"):
        p0_estimands.sentinel_checkpoint_block(scope, event, [
            {"observation_id": ids[0], "global_group_index": True,
             "rewards": [0.0], "assignments": [[0]]}])


@pytest.fixture(scope="module")
def c2_replay_ctx():
    contract = p0_contract.load_p0_science_contract()
    mixture = p0_replay.load_pinned_mixture()
    surface_dir = p0_replay.restore_extension_surface_if_absent()
    loaded = dev_support.load_dev_surface(
        surface_dir,
        expected_lock_sha256=contract.input_pins
        .extension_surface_lock_sha256)
    selection = p0_mixture_v2.load_frozen_selection_v2()
    trace_rows = resume_validation.read_trace(
        Path("plans/conductor/evidence/unit_c2_v1/actions.jsonl"))
    return {"contract": contract, "mixture": mixture,
            "loaded": loaded,
            "disclosure": selection["public_factor_disclosure"],
            "trace_rows": trace_rows,
            "frozen": p0_replay.load_projection()}


def test_p0_c2_replay_equivalence(c2_replay_ctx):
    """The oracle (303_f §3): the raw-trace rederivation reproduces
    the frozen projection EXACTLY — derived under guards proving the
    evaluator never invokes the legacy report builder, never reads
    the source report's values, and never consumes the frozen
    projection (305_f §2)."""
    frozen = c2_replay_ctx["frozen"]
    real_read_text = Path.read_text

    def guarded_read_text(self, *args, **kwargs):
        if "exposure_report" in str(self):
            raise AssertionError(
                "the evaluator read the source report")
        return real_read_text(self, *args, **kwargs)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            unit_c2_sample, "build_exposure_report",
            lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("legacy report builder invoked")))
        mp.setattr(
            p0_c2_equivalence, "load_projection",
            lambda *a, **k: (_ for _ in ()).throw(
                AssertionError(
                    "the evaluator consumed the frozen projection")))
        mp.setattr(Path, "read_text", guarded_read_text)
        derived = p0_c2_equivalence.derive_c2_projection()
    assert derived == frozen
    assert derived["projection_sha256"] == \
        p0_replay.PROJECTION_SHA256
    result = p0_c2_equivalence.verify_c2_equivalence()
    assert result["verdict"] == "PASS"
    assert result["fields_compared"] == len(frozen)


def test_p0_c2_replay_sensitivity(c2_replay_ctx):
    """The 305_f sensitivity set: row reorder; a population
    substitution that alters the projection MAPPING comparison; the
    CARRIED REMINDER — a COHERENT VALID alternative action that
    changes a scientific result (and, as the contrast, a corrupted
    redundant field refuses as corruption, never scoring as an
    alternative result)."""
    kwargs = {key: c2_replay_ctx[key]
              for key in ("contract", "mixture", "loaded",
                          "disclosure")}
    trace = c2_replay_ctx["trace_rows"]
    frozen = c2_replay_ctx["frozen"]
    contract = kwargs["contract"]
    # (a) row reorder refuses at the pinned-schedule identity
    swapped = list(trace)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    with pytest.raises(InfrastructureError, match="pinned schedule"):
        p0_c2_equivalence.derive_from_trace(swapped, **kwargs)
    # 313_s P1: scheduled ids repeat — swapping two COMPLETE rows
    # for the SAME observation preserves the id sequence and must
    # refuse at the physical-position binding
    by_oid = {}
    for position, row in enumerate(trace):
        by_oid.setdefault(row["observation_id"], []).append(position)
    dup_first, dup_second = next(
        positions[:2] for positions in by_oid.values()
        if len(positions) > 1)
    same_id_swap = list(trace)
    same_id_swap[dup_first], same_id_swap[dup_second] = \
        same_id_swap[dup_second], same_id_swap[dup_first]
    assert [r["observation_id"] for r in same_id_swap] \
        == [r["observation_id"] for r in trace]
    with pytest.raises(InfrastructureError,
                       match="physical row position"):
        p0_c2_equivalence.derive_from_trace(same_id_swap, **kwargs)
    # a forged index on a non-sentinel row likewise refuses
    forged_index = copy.deepcopy(trace[:3]) + list(trace[3:])
    forged_index[1]["global_group_index"] = 999999
    with pytest.raises(InfrastructureError,
                       match="physical row position"):
        p0_c2_equivalence.derive_from_trace(forged_index, **kwargs)
    # (b) a one-observation population substitution alters the
    # projection mapping comparison (and the per-population draws)
    doctored = copy.deepcopy(c2_replay_ctx["mixture"])
    sub_oid = next(oid for oid, cls in
                   doctored["class_assignment"].items()
                   if cls == "goal_first_control")
    doctored["class_assignment"][sub_oid] = "anchor"
    derived = p0_c2_equivalence.derive_from_trace(
        trace, **{**kwargs, "mixture": doctored})
    diff = p0_c2_equivalence.compare_projections(derived, frozen)
    assert "population_by_observation" in diff
    assert "per_population_draws" in diff
    assert "class_assignment" in diff
    # (c) CARRIED REMINDER: replace the single reward-1.0 fully
    # family-correct completion of a counted bridge group with a
    # COPY of a coherent 0.5 completion from the same group — every
    # consistency check passes, and a scientific result changes
    population = frozen["population_by_observation"]
    disclosure = kwargs["disclosure"]
    found = None
    for preferred in contract.scope.q1_direct_cells:
        for idx, row in enumerate(trace):
            oid = row["observation_id"]
            if population[oid] != "bridge":
                continue
            cell = disclosure[oid]["cell_id"]
            if cell != preferred:
                continue
            pairs = list(zip(row["rewards"], row["assignments"]))
            highs = [i for i, (r, a) in enumerate(pairs)
                     if r == 1.0 and a is not None
                     and p0_estimands.family_correct_fraction(
                         cell, a) == 1.0]
            lows = [i for i, (r, a) in enumerate(pairs)
                    if r == 0.5 and a is not None
                    and p0_estimands.family_correct_fraction(
                        cell, a) < 1.0]
            if len(highs) == 1 and lows:
                found = (idx, cell, highs[0], lows[0])
                break
        if found:
            break
    assert found is not None
    idx, cell, high_i, low_j = found
    altered = copy.deepcopy(trace)
    for key in ("completions", "actions", "assignments", "rewards"):
        altered[idx][key][high_i] = copy.deepcopy(
            altered[idx][key][low_j])
    derived = p0_c2_equivalence.derive_from_trace(altered, **kwargs)
    diff = p0_c2_equivalence.compare_projections(derived, frozen)
    assert "q1_gate" in diff
    assert "q1_counted_per_epoch_measured" in diff
    assert derived["q1_gate"][cell]["counted_groups"] \
        == frozen["q1_gate"][cell]["counted_groups"] - 1
    if cell == "code_atomic":
        # the sizing minimum moved: the derived experiment changes
        assert "p0_size_derived" in diff
        assert derived["p0_size_derived"]["derived_epochs"] != \
            frozen["p0_size_derived"]["derived_epochs"]
    # (d) the contrast: corrupting ONLY the stored reward is
    # detected as corruption, never scored as an alternative
    corrupted = copy.deepcopy(trace)
    corrupted[idx]["rewards"][high_i] = 0.5
    with pytest.raises(InfrastructureError,
                       match="corrupted redundant"):
        p0_c2_equivalence.derive_from_trace(corrupted, **kwargs)


# --- spine Unit 4: registered cap arithmetic + generated tables (315_f) --------

def test_p0_cap_arithmetic():
    """The 305_f §5 record: every cap input + all three values, the
    closed branches, the min() identity, and exact parity with the
    frozen legacy formula."""
    from types import SimpleNamespace
    contract = p0_contract.load_p0_science_contract()
    base = {"measured_finalization_reserve_seconds": 0.0,
            "frozen_non_rollout_overhead_seconds": 0.0,
            "measured_whole_epoch_seconds": 600.0}
    # input validation
    with pytest.raises(InfrastructureError, match="finite"):
        p0_cap.derive_capacity(
            contract, cumulative_consumed_seconds=float("nan"),
            **base)
    with pytest.raises(InfrastructureError, match="finite"):
        p0_cap.derive_capacity(
            contract, cumulative_consumed_seconds=True, **base)
    with pytest.raises(InfrastructureError, match="non-negative"):
        p0_cap.derive_capacity(
            contract, cumulative_consumed_seconds=-1.0, **base)
    with pytest.raises(InfrastructureError, match="positive"):
        p0_cap.derive_capacity(
            contract, cumulative_consumed_seconds=0.0,
            measured_finalization_reserve_seconds=0.0,
            frozen_non_rollout_overhead_seconds=0.0,
            measured_whole_epoch_seconds=0.0)
    # an unregistered cap rule refuses before any arithmetic
    forged = SimpleNamespace(sizing=SimpleNamespace(
        cap=SimpleNamespace(
            rule_id="p0-cap-v2",
            launch_epochs="min_nominal_capacity",
            capacity_inputs=p0_cap.REGISTERED_CAPACITY_INPUTS)))
    with pytest.raises(InfrastructureError, match="unregistered"):
        p0_cap.derive_capacity(
            forged, cumulative_consumed_seconds=0.0, **base)
    # spare-capacity branch: capacity >= nominal -> run EXACTLY the
    # nominal; spare is recorded, never trained
    plan = p0_cap.derive_launch_plan(
        contract, cumulative_consumed_seconds=0.0, **base)
    assert plan["capacity_epochs"] == 60
    assert plan["nominal_epochs"] == 39
    assert plan["launch_epochs"] == 39
    assert plan["branch"] == "no_extra_training"
    assert plan["spare_epochs_not_trained"] == 21
    assert plan["launch_epochs"] == min(plan["nominal_epochs"],
                                        plan["capacity_epochs"])
    assert tuple(plan["inputs"]) == \
        p0_cap.REGISTERED_CAPACITY_INPUTS
    assert p0_cap.require_launchable(contract, plan) is plan
    # disclosed under-target branch, with quantified projection
    plan = p0_cap.derive_launch_plan(
        contract, cumulative_consumed_seconds=8000.0,
        measured_finalization_reserve_seconds=1000.0,
        frozen_non_rollout_overhead_seconds=500.0,
        measured_whole_epoch_seconds=2000.0)
    assert plan["capacity_epochs"] == 13
    assert plan["launch_epochs"] == 13
    assert plan["branch"] == "disclosed_under_target"
    assert plan["projected_q1_counted_by_cell"] == {
        "code_atomic": 33.8, "fork_join": 88.4, "math_code": 33.8}
    assert plan["target_q1_counted_groups_per_sizing_cell"] == 100
    assert plan["launch_epochs"] == min(plan["nominal_epochs"],
                                        plan["capacity_epochs"])
    # stop branch: capacity <= 0 is never a launch
    plan = p0_cap.derive_launch_plan(
        contract, cumulative_consumed_seconds=36000.0, **base)
    assert plan["capacity_epochs"] == 0
    assert plan["launch_epochs"] == 0
    assert plan["branch"] == "stop_reviewed_amendment"
    assert not plan["launchable"]
    with pytest.raises(InfrastructureError, match="reviewed scope "
                       "amendment"):
        p0_cap.require_launchable(contract, plan)
    # 316_s P1: the boundary REDERIVES the plan from its persisted
    # inputs — the reviewer's forged plans are permanent regressions
    forged_stop = dict(plan)
    forged_stop["launchable"] = True
    forged_stop["launch_epochs"] = 1
    forged_stop["branch"] = "disclosed_under_target"
    with pytest.raises(InfrastructureError, match="forged plan"):
        p0_cap.require_launchable(contract, forged_stop)
    capacity_one = p0_cap.derive_launch_plan(
        contract, cumulative_consumed_seconds=0.0,
        measured_finalization_reserve_seconds=0.0,
        frozen_non_rollout_overhead_seconds=0.0,
        measured_whole_epoch_seconds=30000.0)
    assert capacity_one["capacity_epochs"] == 1
    forged_epochs = dict(capacity_one)
    forged_epochs["launch_epochs"] = 999
    with pytest.raises(InfrastructureError, match="forged plan"):
        p0_cap.require_launchable(contract, forged_epochs)
    forged_bool = dict(capacity_one)
    forged_bool["launch_epochs"] = True
    with pytest.raises(InfrastructureError, match="forged plan"):
        p0_cap.require_launchable(contract, forged_bool)
    forged_nan = dict(capacity_one)
    forged_nan["available_generation_seconds"] = float("nan")
    with pytest.raises(InfrastructureError, match="forged plan"):
        p0_cap.require_launchable(contract, forged_nan)
    forged_ceiling = dict(capacity_one)
    forged_ceiling["inputs"] = dict(capacity_one["inputs"])
    forged_ceiling["inputs"]["operational_ceiling_seconds"] = 1e9
    with pytest.raises(InfrastructureError, match="forged plan"):
        p0_cap.require_launchable(contract, forged_ceiling)
    with pytest.raises(InfrastructureError, match="registered "
                       "input record"):
        p0_cap.require_launchable(contract, {"launchable": True,
                                             "launch_epochs": 5})
    assert p0_cap.require_launchable(contract, capacity_one) \
        is capacity_one
    # 318_s P1: a genuine plan survives the repository's canonical
    # sorted-key JSON round-trip (key order is NOT identity)
    round_tripped = json.loads(json.dumps(capacity_one,
                                          sort_keys=True))
    assert list(round_tripped["inputs"]) \
        != list(capacity_one["inputs"])
    assert p0_cap.require_launchable(contract, round_tripped) \
        is round_tripped
    # ... while missing or extra input keys still refuse
    missing_key = json.loads(json.dumps(capacity_one))
    del missing_key["inputs"]["measured_whole_epoch_seconds"]
    with pytest.raises(InfrastructureError, match="registered "
                       "input record"):
        p0_cap.require_launchable(contract, missing_key)
    extra_key = json.loads(json.dumps(capacity_one))
    extra_key["inputs"]["bonus_seconds"] = 0.0
    with pytest.raises(InfrastructureError, match="registered "
                       "input record"):
        p0_cap.require_launchable(contract, extra_key)
    extra_top = json.loads(json.dumps(capacity_one))
    extra_top["bonus_field"] = 1
    with pytest.raises(InfrastructureError, match="forged plan"):
        p0_cap.require_launchable(contract, extra_top)
    # exact parity with the frozen legacy formula on shared inputs
    for consumed, reserve, overhead, whole in (
            (0.0, 0.0, 0.0, 600.0),
            (8000.0, 1000.0, 500.0, 2000.0),
            (30000.0, 3000.0, 2999.9, 700.0),
            (36000.0, 0.0, 0.0, 100.0),
            (35990.0, 5.0, 4.9, 1.0)):
        legacy = p0_mixture_v2.derive_p0_cap_v2(
            cumulative_consumed_seconds=consumed,
            measured_finalization_reserve_seconds=reserve,
            frozen_non_rollout_overhead_seconds=overhead,
            measured_whole_epoch_seconds=whole)
        mine = p0_cap.derive_capacity(
            contract, cumulative_consumed_seconds=consumed,
            measured_finalization_reserve_seconds=reserve,
            frozen_non_rollout_overhead_seconds=overhead,
            measured_whole_epoch_seconds=whole)
        assert mine["capacity_epochs"] == legacy["capped_epochs"]
        assert mine["available_generation_seconds"] == \
            legacy["available_generation_seconds"]


def test_p0_traceability_appendix(tmp_path, monkeypatch):
    """303_f §8: the committed appendix is byte-equal to a fresh
    generation from the authenticated artifacts — an edited number
    or a diverging artifact value is mechanically detected."""
    result = p0_tables.verify_appendix()
    assert result["verdict"] == "PASS"
    assert result["bytes"] == \
        Path(p0_tables.APPENDIX_PATH).stat().st_size
    committed = Path(p0_tables.APPENDIX_PATH).read_text("utf-8")
    # 316_s P1: the signed traceability matrix and the complete
    # sentinel obligation set are present
    assert "## 8. Signed traceability matrix" in committed
    assert "| requirement | field | enforcement | regression | " \
        "artifact |" in committed
    contract = p0_contract.load_p0_science_contract()
    for field in contract.diagnostics.sentinel.fields_required:
        assert f"`{field}`" in committed
    # the Unit-5 obligations are now NAMED with their implemented
    # enforcement (no dangling deferred rows)
    assert "DEFERRED to Unit 5" not in committed
    assert "p0_launch.build_p0_launch_freeze" in committed
    assert "p0_launch.assemble_sentinel_trajectories" in committed
    assert "p0_launch.prepare_p0_dataset" in committed
    # 321_s: launch admission is EXPLICITLY deferred, never marked
    # complete before the precursor artifacts exist
    assert "Launch admission (execution + precursor binding)" \
        in committed
    assert "**DEFERRED** to the post-merge unit" in committed
    # every reviewed identity and headline value is in the tables
    assert p0_contract.CONTRACT_SHA256 in committed
    assert p0_replay.PROJECTION_SHA256 in committed
    assert p0_replay.PINNED_MIXTURE_FILE_SHA256 in committed
    assert "| derived groups | 6123 |" in committed
    assert "0/15" in committed and "8/152" in committed
    assert "**Q1 + Q2 hierarchical-unlocking authorized**" \
        in committed
    # an edited number diverges
    tampered = tmp_path / "appendix.md"
    tampered.write_text(
        committed.replace("| derived groups | 6123 |",
                          "| derived groups | 6124 |"),
        encoding="utf-8")
    with pytest.raises(InfrastructureError, match="diverges"):
        p0_tables.verify_appendix(tampered)
    # 316_s P2: verification is BYTE-exact — a CRLF rewrite with
    # identical text refuses
    crlf = tmp_path / "appendix_crlf.md"
    crlf.write_bytes(
        committed.replace("\n", "\r\n").encode("utf-8"))
    assert crlf.read_text("utf-8").replace("\r\n", "\n") \
        == committed
    with pytest.raises(InfrastructureError, match="diverges"):
        p0_tables.verify_appendix(crlf)
    # a diverging artifact value changes the generation (the
    # numbers COME from the artifacts, not from prose)
    altered = copy.deepcopy(p0_replay.load_projection())
    altered["zero_variance_groups"] = 663
    monkeypatch.setattr(p0_tables, "load_projection",
                        lambda *a, **k: altered)
    assert p0_tables.generate_traceability_appendix() != committed
    with pytest.raises(InfrastructureError, match="diverges"):
        p0_tables.verify_appendix()


# --- spine Unit 5: P0LaunchFreeze schema + the first real consumer (320_f) -----

def _launch_runtime_fields():
    import hashlib as _hashlib
    from tasks.conductor.stage1 import prompt_fewshot
    return {
        "model_id": "Qwen/Qwen2.5-3B-Instruct",
        "model_revision":
            "aa8e72537993ba99e69dfaafa59ed015b17504d1",
        "quantization": "nf4",
        "lora_adapter_dtype": "float32",
        "lora_key_set_sha256":
            "e44ecb9caf0be396aaaceae6802dbaab9209677103ba263c89"
            "ca9a7ea65f6215",
        "prompt_sha256": _hashlib.sha256(
            prompt_fewshot().encode("utf-8")).hexdigest(),
        "runtime_profile_sha256":
            p0_launch.P0_RUNTIME_PROFILE_SHA256,
        "group_size": 8,
        "seed": 20260901,
        "temperature": 1.0,
        "learning_rate": 1e-5,
        "beta": 1e-3,
        "policy_max_new_tokens": 128,
        "attested_environment_sha256":
            p0_replay.REPLAY_SOURCE["attested_environment_sha256"],
    }


_LAUNCH_PRECURSORS = {
    "routing_dev_val_lock_sha256": "1a" * 32,
    "cycle_record_sha256": "2b" * 32,
    "r_cycle_record_sha256": "3c" * 32,
    "beta_smoke_record_sha256": "4d" * 32,
}


def test_p0_launch_freeze_schema(tmp_path):
    """The p0-launch-freeze-v1 schema: verbatim plan persistence,
    the unfreezable stop branch, closed fields (no execution-
    manifest hash, no terminal hashes), and the strict loader
    REQUIRING the externally reviewed hash."""
    import dataclasses
    contract = p0_contract.load_p0_science_contract()
    runtime = _launch_runtime_fields()
    plan = p0_cap.derive_launch_plan(
        contract, cumulative_consumed_seconds=8000.0,
        measured_finalization_reserve_seconds=1000.0,
        frozen_non_rollout_overhead_seconds=500.0,
        measured_whole_epoch_seconds=2000.0)
    assert plan["branch"] == "disclosed_under_target"
    freeze = p0_launch.build_p0_launch_freeze(
        plan_record=plan, precursors=_LAUNCH_PRECURSORS,
        runtime=runtime, contract=contract)
    # verbatim persistence: the typed plan round-trips exactly
    assert p0_cap._strict_equal(freeze.launch_plan.to_record(),
                                plan)
    assert freeze.science_contract_sha256 == \
        p0_contract.CONTRACT_SHA256
    # the closed schema carries NO execution-manifest / terminal
    # hash field (305_f §1)
    names = {f.name for f in dataclasses.fields(freeze)}
    assert names == {"schema_version", "science_contract_sha256",
                     "precursors", "launch_plan", "runtime"}
    # save + load under the REQUIRED reviewed hash
    out = tmp_path / "launch_freeze.json"
    digest = p0_launch.save_launch_freeze(freeze, out)
    assert digest == p0_launch.freeze_sha256(freeze)
    loaded = p0_launch.load_p0_launch_freeze(out, digest)
    assert loaded == freeze
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_launch.save_launch_freeze(freeze, out)
    with pytest.raises(InfrastructureError, match="reviewed"):
        p0_launch.load_p0_launch_freeze(out, "0" * 64)
    tampered = json.loads(out.read_text("utf-8"))
    tampered["launch_plan"]["launch_epochs"] = 14
    bad = tmp_path / "tampered.json"
    bad.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="reviewed"):
        p0_launch.load_p0_launch_freeze(bad, digest)
    extra = json.loads(out.read_text("utf-8"))
    extra["execution_manifest_sha256"] = "9e" * 32
    payload = {k: v for k, v in extra.items()
               if k != "freeze_sha256"}
    extra["freeze_sha256"] = charter.content_sha256(payload)
    bad2 = tmp_path / "extra.json"
    bad2.write_text(json.dumps(extra), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="closed schema"):
        p0_launch.load_p0_launch_freeze(bad2,
                                        extra["freeze_sha256"])
    # the stop branch is UNFREEZABLE
    stop = p0_cap.derive_launch_plan(
        contract, cumulative_consumed_seconds=36000.0,
        measured_finalization_reserve_seconds=0.0,
        frozen_non_rollout_overhead_seconds=0.0,
        measured_whole_epoch_seconds=600.0)
    with pytest.raises(InfrastructureError, match="reviewed scope "
                       "amendment"):
        p0_launch.build_p0_launch_freeze(
            plan_record=stop, precursors=_LAUNCH_PRECURSORS,
            runtime=runtime, contract=contract)
    # a forged plan refuses at the Unit-4 boundary
    forged = json.loads(json.dumps(plan))
    forged["launch_epochs"] = 39
    with pytest.raises(InfrastructureError, match="forged plan"):
        p0_launch.build_p0_launch_freeze(
            plan_record=forged, precursors=_LAUNCH_PRECURSORS,
            runtime=runtime, contract=contract)
    # branch-inconsistent typed plans refuse at construction
    with pytest.raises(InfrastructureError, match="under-target "
                       "branch"):
        record = json.loads(json.dumps(plan))
        del record["projected_q1_counted_by_cell"]
        record["spare_epochs_not_trained"] = 3
        p0_launch.LaunchPlan.from_record(record)
    # runtime validation: bool seed, NaN lr, wrong construction
    with pytest.raises(InfrastructureError, match="seed"):
        p0_launch.RuntimeIdentity(
            **{**runtime, "seed": True})
    with pytest.raises(InfrastructureError, match="finite"):
        p0_launch.RuntimeIdentity(
            **{**runtime, "learning_rate": float("nan")})
    with pytest.raises(InfrastructureError, match="REAL training"):
        p0_launch.RuntimeIdentity(
            **{**runtime, "learning_rate": 0.0})
    # 321_s: the runtime must BIND to the canonical profile and the
    # ACTUAL prompt — the reviewer's reproductions refuse at build
    with pytest.raises(InfrastructureError, match="frozen"):
        p0_launch.build_p0_launch_freeze(
            plan_record=plan, precursors=_LAUNCH_PRECURSORS,
            runtime={**runtime, "beta": 0.04}, contract=contract)
    with pytest.raises(InfrastructureError, match="ACTUAL"):
        p0_launch.build_p0_launch_freeze(
            plan_record=plan, precursors=_LAUNCH_PRECURSORS,
            runtime={**runtime, "prompt_sha256": "0" * 64},
            contract=contract)
    with pytest.raises(InfrastructureError, match="canonical"):
        p0_launch.build_p0_launch_freeze(
            plan_record=plan, precursors=_LAUNCH_PRECURSORS,
            runtime={**runtime,
                     "runtime_profile_sha256": "9f" * 32},
            contract=contract)
    with pytest.raises(InfrastructureError, match="validated "
                       "construction"):
        p0_launch.RuntimeIdentity(
            **{**runtime, "quantization": "int8"})
    with pytest.raises(InfrastructureError, match="40-hex"):
        p0_launch.RuntimeIdentity(
            **{**runtime, "model_revision": "aa8e"})
    with pytest.raises(InfrastructureError, match="precursors"):
        p0_launch.PrecursorOutputs(
            **{**_LAUNCH_PRECURSORS,
               "cycle_record_sha256": "zz" * 32})


def test_p0_sentinel_trajectories():
    """321_s P1: trajectory assembly enforces the exact frozen
    index sets (checkpoint zero + final mandatory; truncation and
    emptiness refuse), semantic counter/denominator/first-index
    validation, deep-copied immutability, and EXPLICIT
    infrastructure-abort prefix handling."""
    import copy as _copy
    contract = p0_contract.load_p0_science_contract()
    scope, event = contract.scope, contract.q1.event
    ids = list(scope.sentinel_observation_ids)
    quiet_rows = [{"observation_id": ids[0],
                   "global_group_index": 0,
                   "rewards": [0.0] * 8,
                   "assignments": [[0]] * 8}]
    block = p0_estimands.sentinel_checkpoint_block(
        scope, event, quiet_rows)
    event_rows = [{"observation_id": ids[0],
                   "global_group_index": 3,
                   "rewards": [1.0, 0.5] + [0.0] * 6,
                   "assignments": [[1], [0]] + [None] * 6}]
    active = p0_estimands.sentinel_checkpoint_block(
        scope, event, event_rows)

    def assemble(ckpts, evals, **kw):
        kw.setdefault("expected_checkpoint_indices", (0, 157, 314))
        kw.setdefault("expected_evaluation_indices", (0, 314))
        return p0_launch.assemble_sentinel_trajectories(
            contract, ckpts, evals, **kw)

    result = assemble([(0, block), (157, active), (314, block)],
                      [(0, block), (314, block)])
    assert result["status"] == "complete"
    assert result["checkpoint_trajectory"][1][0] == 157
    # deep copy: mutating the source block cannot reach the result
    block["worker1_selections"] = 999999
    assert result["checkpoint_trajectory"][0][1][
        "worker1_selections"] == 0
    block = p0_estimands.sentinel_checkpoint_block(
        scope, event, quiet_rows)
    # empty and truncated COMPLETE trajectories refuse (321_s)
    with pytest.raises(InfrastructureError, match="not complete"):
        assemble([], [(0, block), (314, block)])
    with pytest.raises(InfrastructureError, match="not complete"):
        assemble([(0, block), (157, block)],
                 [(0, block), (314, block)])
    # the expected sets themselves are validated: checkpoint zero
    # is mandatory; empty expected refuses
    with pytest.raises(InfrastructureError, match="checkpoint "
                       "zero"):
        assemble([(157, block)], [(0, block)],
                 expected_checkpoint_indices=(157,))
    with pytest.raises(InfrastructureError, match="empty"):
        assemble([], [], expected_checkpoint_indices=())
    # 323_s: checkpoint zero PLUS a positive final are mandatory —
    # a single-element expected set refuses
    with pytest.raises(InfrastructureError, match="positive final"):
        assemble([(0, block)], [(0, block), (314, block)],
                 expected_checkpoint_indices=(0,))
    # infrastructure abort: EXPLICIT, disclosed, strict prefix
    aborted = assemble([(0, block)], [(0, block)],
                       status="infrastructure_abort",
                       expected_evaluation_indices=(0, 314))
    assert aborted["status"] == "infrastructure_abort"
    assert aborted["disclosed_truncation"] == {
        "checkpoints_observed": 1, "checkpoints_expected": 3,
        "evaluations_observed": 1, "evaluations_expected": 2}
    with pytest.raises(InfrastructureError, match="PREFIX"):
        assemble([(157, block)], [(0, block)],
                 status="infrastructure_abort")
    # 323_s: an abort BETWEEN streams — one stream complete, the
    # other a strict prefix — is a valid disclosed abort
    between = assemble([(0, block), (157, block), (314, block)],
                       [(0, block)],
                       status="infrastructure_abort")
    assert between["disclosed_truncation"] == {
        "checkpoints_observed": 3, "checkpoints_expected": 3,
        "evaluations_observed": 1, "evaluations_expected": 2}
    # ... but BOTH streams complete is not an abort
    with pytest.raises(InfrastructureError, match="not an abort"):
        assemble([(0, block), (157, block), (314, block)],
                 [(0, block), (314, block)],
                 status="infrastructure_abort")
    with pytest.raises(InfrastructureError, match="unknown "
                       "trajectory status"):
        assemble([(0, block)], [(0, block)], status="partial")
    # semantic validation (the 321_s reproductions)
    def broken(**changes):
        bad = _copy.deepcopy(block)
        bad.update(changes)
        return [(0, bad), (157, bad), (314, bad)]

    evals = [(0, block), (314, block)]
    with pytest.raises(InfrastructureError, match="exposure"):
        assemble(broken(training_exposed=False), evals)
    with pytest.raises(InfrastructureError, match="non-negative "
                       "non-boolean"):
        assemble(broken(group_denominator=-1), evals)
    with pytest.raises(InfrastructureError, match="impossible "
                       "count"):
        assemble(broken(worker1_selections=999), evals)
    with pytest.raises(InfrastructureError, match="non-negative "
                       "non-boolean"):
        assemble(broken(completion_denominator=True), evals)
    bad_first = _copy.deepcopy(block)
    bad_first["first_group_indices"] = {
        **bad_first["first_group_indices"], "worker1": True}
    with pytest.raises(InfrastructureError, match="first index"):
        assemble([(0, bad_first), (157, bad_first),
                  (314, bad_first)], evals)
    # count/index consistency: a positive counter with a None
    # first index (and the reverse) refuse
    with pytest.raises(InfrastructureError, match="count/index "
                       "consistency"):
        assemble(broken(worker1_selections=1,
                        worker1_completions=1), evals)
    stale_first = _copy.deepcopy(active)
    stale_first["worker1_selections"] = 0
    stale_first["worker1_completions"] = 0
    with pytest.raises(InfrastructureError, match="count/index "
                       "consistency"):
        assemble([(0, stale_first), (157, stale_first),
                  (314, stale_first)], evals)
    with pytest.raises(InfrastructureError, match="counted cannot "
                       "exceed varying"):
        assemble(broken(q1_counted_groups=1), evals)
    # 323_s: the PRODUCER invariants — states the block producer
    # cannot emit refuse
    with pytest.raises(InfrastructureError, match="emits them "
                       "identically"):
        assemble(broken(worker1_selections=2,
                        worker1_completions=1), evals)
    seven_rows = [{"observation_id": ids[0],
                   "global_group_index": 0,
                   "rewards": [0.0] * 7,
                   "assignments": [[0]] * 7}]
    seven = p0_estimands.sentinel_checkpoint_block(
        scope, event, seven_rows)
    with pytest.raises(InfrastructureError, match="frozen group "
                       "size"):
        assemble([(0, seven), (157, seven), (314, seven)], evals)
    drifted = _copy.deepcopy(active)
    drifted["first_update_indices"] = {
        **drifted["first_update_indices"], "worker1": 999}
    with pytest.raises(InfrastructureError, match="binds the two "
                       "index spaces"):
        assemble([(0, drifted), (157, drifted), (314, drifted)],
                 evals)
    incomplete = _copy.deepcopy(block)
    del incomplete["completion_denominator"]
    with pytest.raises(InfrastructureError, match="COMPLETE"):
        assemble([(0, incomplete), (157, incomplete),
                  (314, incomplete)], evals)
    foreign = _copy.deepcopy(block)
    foreign["observation_ids"] = ["math_atomic:x:y"]
    with pytest.raises(InfrastructureError, match="frozen "
                       "sentinel"):
        assemble([(0, foreign), (157, foreign), (314, foreign)],
                 evals)


def test_p0_first_consumer_prepare(tmp_path, monkeypatch):
    """The first real consumer end-to-end: every input through a
    reviewed pin, the plan rederived at admission, the standing
    oracles invoked FRESH, the dataset from the strict loader."""
    contract = p0_contract.load_p0_science_contract()
    plan = p0_cap.derive_launch_plan(
        contract, cumulative_consumed_seconds=0.0,
        measured_finalization_reserve_seconds=0.0,
        frozen_non_rollout_overhead_seconds=0.0,
        measured_whole_epoch_seconds=30000.0)
    assert plan["capacity_epochs"] == 1
    freeze = p0_launch.build_p0_launch_freeze(
        plan_record=plan, precursors=_LAUNCH_PRECURSORS,
        runtime=_launch_runtime_fields(), contract=contract)
    out = tmp_path / "launch_freeze.json"
    digest = p0_launch.save_launch_freeze(freeze, out)
    calls = {"equivalence": 0, "appendix": 0}
    real_equivalence = p0_c2_equivalence.verify_c2_equivalence
    real_appendix = p0_tables.verify_appendix

    def counting_equivalence(*args, **kwargs):
        calls["equivalence"] += 1
        return real_equivalence(*args, **kwargs)

    def counting_appendix(*args, **kwargs):
        calls["appendix"] += 1
        return real_appendix(*args, **kwargs)

    monkeypatch.setattr(p0_c2_equivalence, "verify_c2_equivalence",
                        counting_equivalence)
    monkeypatch.setattr(p0_tables, "verify_appendix",
                        counting_appendix)
    bundle = p0_launch.prepare_p0_dataset(out, digest)
    assert calls == {"equivalence": 1, "appendix": 1}
    assert bundle["launch_epochs"] == 1
    assert bundle["groups_total"] == 157
    assert bundle["gates"] == {"launch_plan": "REDERIVED",
                               "runtime_binding": "BOUND",
                               "c2_equivalence": "PASS",
                               "appendix": "PASS"}
    # 321_s: dataset preparation NEVER authorizes an execution —
    # launch admission is explicitly deferred with its outstanding
    # obligations named
    assert bundle["launch_admission"]["status"] == "DEFERRED"
    assert len(bundle["launch_admission"]["outstanding"]) == 4
    assert [r["observation_id"] for r in bundle["trainer_rows"]] \
        == bundle["schedule"]
    assert bundle["runtime"].seed == 20260901
    # a freeze pinning a DIFFERENT contract refuses
    import dataclasses
    forged = dataclasses.replace(
        freeze, science_contract_sha256="ab" * 32)
    out2 = tmp_path / "forged_freeze.json"
    digest2 = p0_launch.save_launch_freeze(forged, out2)
    with pytest.raises(InfrastructureError, match="different "
                       "science contract"):
        p0_launch.prepare_p0_dataset(out2, digest2)
    # 321_s reproduction: a hand-crafted freeze DECLARING a forged
    # prompt loads structurally but refuses at preparation — the
    # freeze must bind the execution it authorizes
    forged_prompt = dataclasses.replace(
        freeze, runtime=dataclasses.replace(
            freeze.runtime, prompt_sha256="0" * 64))
    out3 = tmp_path / "forged_prompt.json"
    digest3 = p0_launch.save_launch_freeze(forged_prompt, out3)
    assert p0_launch.load_p0_launch_freeze(out3, digest3) \
        == forged_prompt
    with pytest.raises(InfrastructureError, match="ACTUAL"):
        p0_launch.prepare_p0_dataset(out3, digest3)


# --- precursors Unit V: the routing_dev_val freeze (331_f/333_f/335_f) ---------

# captured at import, BEFORE any fixture patches the config (the
# PRISTINE pattern): the production lineage parent + config pin
PRISTINE_VAL_LINEAGE = \
    p0_val.VAL_CONFIG["lineage"]["parent_entry_sha256"]
PRISTINE_VAL_CONFIG_SHA256 = p0_val.VAL_CONFIG_SHA256


def test_p0_val_cohort_and_seeds(monkeypatch):
    """V1: the outcome-blind cohort, identity disjointness across
    EVERY registered namespace, the full-digest CRN derivation with
    its known vector and frozen 720-seed schedule, and the
    preregistered freeze record."""
    obs = p0_val.val_cohort_observations()
    assert len(obs) == 90
    assert {o["cell_id"] for o in obs} == set(p0_val.VAL_CELLS)
    for o in obs:
        parts = o["observation_id"].split(":")
        assert parts[1] == "routing_dev_val"
        assert int(parts[2]) in range(5)
    keys = [(o["cell_id"], int(o["observation_id"].split(":")[2]),
             o["renderer_id"]) for o in obs]
    assert keys == sorted(keys, key=lambda k: (k[0], k[1]))
    val_latents = {o["latent_program_id"] for o in obs}
    for namespace in sorted(program.NAMESPACE_CONFIG):
        if namespace == "routing_dev_val":
            continue
        other = {program.generate_latent(
            cell, namespace, index, DEFAULT_PROFILE
        ).latent["latent_program_id"]
            for cell in p0_val.VAL_CELLS for index in range(5)}
        assert val_latents & other == set(), namespace
    freeze = p0_val.val_tranche_freeze()
    assert freeze["observations_total"] == 90
    assert freeze["planned_step_executions"] == 4020
    assert freeze["config_sha256"] == p0_val.VAL_CONFIG_SHA256
    assert freeze["seed_schedule_sha256"] == \
        p0_val.VAL_SEED_SCHEDULE_SHA256
    monkeypatch.setitem(p0_val.VAL_CONFIG, "search_cap", 91)
    with pytest.raises(InfrastructureError, match="mutated"):
        p0_val.val_cohort_observations()
    monkeypatch.undo()
    first = obs[0]["observation_id"]
    assert first == ("code_atomic:routing_dev_val:00000:70caabb1:"
                     "resource_first:private")
    assert p0_val.seed_for_completion(first, 0) == 1176822329
    schedule = p0_val.seed_schedule()
    assert len(schedule) == 720
    assert len({seed for _, _, seed in schedule}) == 720
    monkeypatch.setattr(p0_val, "VAL_SEED_SCHEDULE_SHA256",
                        "0" * 64)
    with pytest.raises(InfrastructureError, match="schedule pin"):
        p0_val.seed_schedule()
    monkeypatch.undo()
    import inspect
    assert "checkpoint" not in str(
        inspect.signature(p0_val.seed_for_completion))
    assert p0_val.seed_for_completion(first, 0) == \
        p0_val.seed_for_completion(first, 0)
    assert p0_val.seed_for_completion(first, 0) != \
        p0_val.seed_for_completion(first, 0, domain="cycle_eval")
    for bad_slot in (8, -1, True):
        with pytest.raises(InfrastructureError, match="0, 8"):
            p0_val.seed_for_completion(first, bad_slot)


@pytest.fixture(scope="module")
def val_training_reference():
    training = dev_support.load_dev_surface(
        p0_replay.restore_extension_surface_if_absent(),
        expected_lock_sha256=unit_c2_sample.UNIT_C2_CONFIG[
            "extension_surface_lock_sha256"])
    return [{**o, "latent": p0_val._regenerate_latent(o)}
            for o in training["observations"]]


def test_p0_val_alpha_normalized_overlap(val_training_reference):
    """334_s P1-1: opaque resource handles are alpha-normalized;
    the HARD gate is alpha-normalized SEMANTIC disjointness (zero
    throughout), while alpha-normalized PROMPT-template overlap is
    DISCLOSED at the reviewer's measured values — validation tests
    held-out latent/resource instances, not template-disjoint
    prompts."""
    assert p0_val.alpha_normalize(
        "reads R-8V9 then R-1E3 then R-8V9") == \
        "reads R0 then R1 then R0"
    # 336_s P1-1: HANDLE-INVARIANCE — consistently renaming every
    # handle so its lexical order REVERSES must not change the
    # semantic hash, for EVERY frozen multi-handle latent (val +
    # cycle cohorts), including the reviewer's concrete example
    import re as _re

    def _rename_everywhere(obj, renames):
        if isinstance(obj, str):
            return _re.compile(r"R-[0-9A-Z]{3}").sub(
                lambda m: renames.get(m.group(0), m.group(0)), obj)
        if isinstance(obj, dict):
            return {_rename_everywhere(k, renames):
                    _rename_everywhere(v, renames)
                    for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_rename_everywhere(x, renames) for x in obj]
        return obj

    reviewed_example = ("fork_join:routing_dev_val:00001:beaa828e:"
                        "resource_first:private")
    seen_example = False
    multi_handle = 0
    for o in (p0_val.val_cohort_observations()
              + p0_val.cycle_cohort_observations()):
        latent = o["latent"]
        handles = sorted(set(_re.findall(
            r"R-[0-9A-Z]{3}", json.dumps(
                latent.get("public_manifest", [])))))
        if len(handles) < 2:
            continue
        multi_handle += 1
        if o["observation_id"] == reviewed_example:
            seen_example = True
        # ascending handles -> replacements whose sort REVERSES
        renames = {h: f"R-{chr(90 - i)}ZZ"
                   for i, h in enumerate(handles)}
        assert sorted(renames.values(), reverse=True) == \
            [renames[h] for h in handles]
        renamed = _rename_everywhere(
            {k: v for k, v in latent.items()
             if k != "public_params"}, renames)
        renamed["public_params"] = latent["public_params"]
        assert p0_val.normalized_latent_semantics(renamed) == \
            p0_val.normalized_latent_semantics(latent), \
            o["observation_id"]
    assert multi_handle > 0 and seen_example
    reports = p0_val.three_way_overlap_reports(
        val_training_reference)
    for report in reports.values():
        assert report["semantic_intersection"] == 0
    # the DISCLOSED template overlap — the reviewer's measurements
    # as regressions
    assert reports["val_vs_training"][
        "alpha_prompt_collisions"] == 21
    assert reports["val_vs_training"][
        "alpha_prompt_affected_candidates"] == 39
    assert reports["val_vs_cycle"]["alpha_prompt_collisions"] == 15
    assert reports["val_vs_cycle"][
        "alpha_prompt_affected_candidates"] == 30
    assert reports["cycle_vs_training"][
        "alpha_prompt_collisions"] == 30
    # the hard gate bites: a smuggled val latent refuses
    obs = p0_val.val_cohort_observations()
    with pytest.raises(InfrastructureError, match="overlap is not "
                       "empty"):
        p0_val.semantic_overlap_report(
            obs, val_training_reference + [obs[0]])
    with pytest.raises(InfrastructureError, match="non-empty"):
        p0_val.semantic_overlap_report(obs, [])


def _val_declaration():
    from tasks.conductor import oracle
    config = p0_val.VAL_CONFIG
    observations = p0_val.val_cohort_observations()
    return {
        "support": config["tranche"],
        "namespace": config["namespace"],
        "cohort": {cell: sorted(config["cohort"][cell])
                   for cell in sorted(config["cohort"])},
        "renderers": config["renderers"],
        "visibility": config["visibility"],
        "observations": [
            {"observation_id": o["observation_id"],
             "cell_id": o["cell_id"],
             "renderer_id": o["renderer_id"],
             "num_nodes": o["num_nodes"],
             "assignments": len(oracle.enumerate_assignments(
                 o["num_nodes"]))}
            for o in observations],
        "worker_visible_fingerprint": "wv" * 8,
        "runtime_profile_fingerprint": "rp" * 8,
        "worker_pool_fingerprint": "wp" * 8,
        "request_contract": "rc-test",
        "cache_identity": "worker_completions/slw/rc-test",
    }


def _resign(manifest, **changes):
    body = {k: v for k, v in manifest.items()
            if k != "manifest_sha256"}
    body.update(changes)
    body["scientific_design_sha256"] = charter.content_sha256(
        {f: body[f] for f in p0_val._VAL_DESIGN_FIELDS})
    body["manifest_sha256"] = charter.content_sha256(body)
    return body


def test_p0_val_launch_manifest_rederives_the_frozen_launch():
    """334_s P1-2: every configuration-owned field is REDERIVED —
    a correctly re-signed manifest carrying a changed budget, cap,
    tag, driver, run root, or cohort refuses."""
    declaration = _val_declaration()
    environment = _env_manifest()
    manifest = p0_val.build_val_launch_manifest(
        declaration=declaration, environment_manifest=environment,
        execution_root="runs/routing-dev/val-surface-v1")
    assert manifest["run_root"] == p0_val.VAL_RUN_ROOT
    assert manifest["lineage_parent_sha256"] == \
        p0_val.VAL_CONFIG["lineage"]["parent_entry_sha256"]
    assert manifest["execution_root"].endswith(
        "runs/routing-dev/val-surface-v1")
    validated = p0_val.validate_val_launch_manifest(
        manifest, declaration)
    assert validated["manifest_sha256"] == \
        manifest["manifest_sha256"]
    for field, forged in (
            ("budget_gpu_hours", 2.0),
            ("search_cap", 200),
            ("support", "routing-dev-val-surface-v2"),
            ("driver", "tasks/routing/support_run.py"),
            ("run_root", "runs/routing-dev/elsewhere"),
            ("lineage_parent_sha256", "ab" * 32)):
        with pytest.raises(InfrastructureError,
                           match="frozen configuration value"):
            p0_val.validate_val_launch_manifest(
                _resign(manifest, **{field: forged}), declaration)
    # a re-signed COHORT substitution refuses at the shared
    # frozen-cohort validator
    curated = copy.deepcopy(declaration)
    curated["cohort"]["fork_join"] = [0, 1, 2, 3, 7]
    resigned = _resign(
        manifest,
        declaration_sha256=charter.content_sha256(dict(curated)))
    with pytest.raises(InfrastructureError, match="not the frozen "
                       "val cohort"):
        p0_val.validate_val_launch_manifest(resigned, curated)
    extra = dict(manifest)
    extra["execution_note"] = "x"
    with pytest.raises(InfrastructureError, match="closed schema"):
        p0_val.validate_val_launch_manifest(extra, declaration)
    resigned_digest = _resign(manifest,
                              routing_source_sha256="ab" * 32)
    with pytest.raises(InfrastructureError, match="source digest"):
        p0_val.validate_val_launch_manifest(resigned_digest,
                                            declaration)
    with pytest.raises(InfrastructureError, match="regenerated "
                       "frozen cohort"):
        truncated = copy.deepcopy(declaration)
        truncated["observations"] = \
            truncated["observations"][:-1]
        p0_val.build_val_launch_manifest(
            declaration=truncated,
            environment_manifest=environment,
            execution_root="runs/routing-dev/val-surface-v1")


def val_fake_rt(tmp_path):
    observations = p0_val.val_cohort_observations()
    by_task = {}
    for obs in observations:
        _, worker_call = perfect_worker(obs["latent"])
        for step in program.workflow_steps(obs["latent"]):
            by_task[step["subtask"]] = worker_call(
                None, f"Task:\n{step['subtask']}\n\nx")

    def completion(request: bytes) -> str:
        user = request.decode("utf-8").split("\x00", 1)[1]
        task = user.split("Task:\n", 1)[1].split("\n\n", 1)[0]
        return by_task[task]

    profile = profile_with(cache_path=str(tmp_path / "cache.sqlite"),
                           device="cpu")
    pool = FakeFourPool(profile, {w: completion for w in range(4)})
    return FourWorkerRuntime(
        profile, pool, WorkerCompletionCache(profile["cache_path"]))


def _seed_reserve_ledger(ledger_path, tag="primary"):
    """Mirror the real ledger's pre-val state: a completed support
    run and the provisional R_cycle reserve. `tag` differentiates
    ledgers (entries carry no timestamp, so identical seeds would
    produce identical head hashes)."""
    support_entry = ledger._append(
        {"kind": "support_materialization",
         "question": f"support ({tag})",
         "motivating_evidence": "test mirror",
         "freeze": {"support_launch_sha256": "ab" * 32,
                    "scientific_design_sha256": "cd" * 32},
         "parent": None, "budget_allocated_gpu_hours": 1.0,
         "outcome_informed": False,
         "cohort_selection": "outcome_blind"}, None, ledger_path)
    support_close = ledger._append(
        {"kind": "closeout", "question": "support",
         "motivating_evidence": "test mirror",
         "freeze": {"surface_lock_sha256": "ef" * 32,
                    "run_record_file_sha256": "12" * 32,
                    "execute_env_file_sha256": "34" * 32,
                    "rendered_observations": 3000},
         "parent": support_entry["entry_sha256"],
         "budget_allocated_gpu_hours": 0.0,
         "budget_consumed_gpu_hours": 0.5,
         "closes_entry_sha256": support_entry["entry_sha256"],
         "terminal_status": "complete", "outcome_informed": False},
        support_entry["entry_sha256"], ledger_path)
    return ledger._append(
        {"kind": "reserve_update", "question": "provisional reserve",
         "motivating_evidence": "231_f basis (test mirror)",
         "freeze": {"support_closeout_sha256":
                    support_close["entry_sha256"],
                    "surface_lock_sha256": "ef" * 32},
         "parent": support_close["entry_sha256"],
         "budget_allocated_gpu_hours": 0.0,
         "outcome_informed": False,
         "reserve": {"status": "provisional",
                     "r_cycle_gpu_hours": 1.0,
                     "assumed_cohort_size": 3000,
                     "evaluation_multiplier": 2.0,
                     # 0.5 h x 3600 / 3000 rendered (rederives)
                     "measured_seconds_per_observation": 0.6,
                     "measured_support_gpu_hours": 0.5,
                     "rounding": "ceil_to_whole_gpu_hours"}},
        support_close["entry_sha256"], ledger_path)


def _patch_val_lineage(mp, parent_sha256):
    """Patch the frozen lineage parent COHERENTLY (config + pin) so
    the first-launch head check is exercised for real against a
    test ledger."""
    mp.setitem(p0_val.VAL_CONFIG["lineage"], "parent_entry_sha256",
               parent_sha256)
    mp.setattr(p0_val, "VAL_CONFIG_SHA256",
               charter.content_sha256(p0_val.VAL_CONFIG))


@pytest.fixture(scope="module")
def val_run_fixture(tmp_path_factory):
    """334_s: the consolidated CPU-fake end-to-end lifecycle —
    prepare -> lineage-checked admit -> materialize -> surface lock
    -> three-way overlap gate -> val lock -> terminal verification
    -> closeout — with the frozen-lineage check exercised for real
    against the mirrored ledger head."""
    tmp = tmp_path_factory.mktemp("val-run")
    # 336_s P1-3: the registered attempt-1 root name
    run_dir = tmp / "runs/routing-dev/val-surface-v1"
    ledger_path = tmp / "ledger.md"
    reserve_entry = _seed_reserve_ledger(ledger_path)
    mp = pytest.MonkeyPatch()
    _patch_val_lineage(mp, reserve_entry["entry_sha256"])
    try:
        manifest = p0_val.prepare_val_launch(
            run_dir=run_dir,
            _runtime_factory=lambda: val_fake_rt(tmp),
            _environment_builder=_env_manifest)
        record = p0_val.execute_val_run(
            run_dir=run_dir,
            expected_manifest_sha256=manifest["manifest_sha256"],
            expected_head_sha256=reserve_entry["entry_sha256"],
            question="val surface",
            motivating_evidence="330_f Unit V",
            ledger_path=ledger_path,
            _runtime_factory=lambda: val_fake_rt(tmp),
            _environment_builder=lambda: _env_manifest(
                git_commit="feedbeef"))
        yield {"tmp": tmp, "run_dir": run_dir,
               "ledger_path": ledger_path, "manifest": manifest,
               "record": record, "mp": mp,
               "reserve_head": reserve_entry["entry_sha256"]}
    finally:
        mp.undo()


def test_p0_val_run_end_to_end(val_run_fixture):
    fx = val_run_fixture
    record = fx["record"]
    entries = ledger.verify_ledger_head(record["ledger_head"],
                                        fx["ledger_path"])
    assert [e["kind"] for e in entries] == \
        ["support_materialization", "closeout", "reserve_update",
         "val_materialization", "closeout"]
    launch = entries[3]
    assert launch["freeze"]["val_launch_sha256"] == \
        fx["manifest"]["manifest_sha256"]
    assert launch["freeze"]["val_freeze_sha256"] == \
        p0_val.val_tranche_freeze()["freeze_sha256"]
    # 334_s P1-3: the ACTUAL lineage parent is persisted
    assert launch["parent"] == fx["reserve_head"]
    assert launch["budget_allocated_gpu_hours"] == 0.35
    assert entries[4]["terminal_status"] == "complete"
    assert entries[4]["freeze"]["rendered_observations"] == 90
    surface_dir = fx["run_dir"] / "surface"
    lock = p0_val.load_val_lock(
        fx["run_dir"] / "val_lock.json",
        record["val_lock_sha256"], surface_dir=surface_dir)
    assert lock["ordered_observation_ids"] == [
        o["observation_id"]
        for o in p0_val.val_cohort_observations()]
    weights = dict(map(tuple, lock["natural_mixture_weights"]))
    assert all(abs(w - 1 / 90) < 1e-12 for w in weights.values())
    # the overlap disclosure is BOUND into the lock
    assert lock["overlap_report"]["val_vs_training"][
        "alpha_prompt_collisions"] == 21
    # the full terminal verifier, authenticated from the chain
    verdict = p0_val.verify_val_run(
        fx["run_dir"], ledger_path=fx["ledger_path"],
        expected_head_sha256=record["ledger_head"],
        expected_val_lock_sha256=record["val_lock_sha256"])
    assert verdict["verdict"] == "PASS"
    assert verdict["terminal_status"] == "complete"
    assert verdict["launch_entry_sha256"] == \
        launch["entry_sha256"]
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_val.build_val_lock(
            surface_dir, overlap_report=record["overlap_report"])
    # 334_s P1-3: after a COMPLETED attempt, no second launch
    with pytest.raises(InfrastructureError, match="never a retry"):
        p0_val.execute_val_run(
            run_dir=fx["run_dir"],
            expected_manifest_sha256=fx["manifest"][
                "manifest_sha256"],
            expected_head_sha256=record["ledger_head"],
            question="q", motivating_evidence="m",
            ledger_path=fx["ledger_path"])


def test_p0_val_terminal_verifier_bites(val_run_fixture, tmp_path):
    """334_s P1-4: the verifier refuses a deleted file, an unbound
    extra file, and a tampered overlap report."""
    import shutil
    fx = val_run_fixture
    record = fx["record"]

    def verify(run_dir, **kw):
        kw.setdefault("ledger_path", fx["ledger_path"])
        kw.setdefault("expected_head_sha256",
                      record["ledger_head"])
        kw.setdefault("expected_val_lock_sha256",
                      record["val_lock_sha256"])
        return p0_val.verify_val_run(run_dir, **kw)

    run_copy = tmp_path / "run-copy"
    shutil.copytree(fx["run_dir"], run_copy)
    assert verify(run_copy)["verdict"] == "PASS"
    (run_copy / "execute_env_manifest.json").unlink()
    with pytest.raises(InfrastructureError, match="missing"):
        verify(run_copy)
    shutil.copytree(fx["run_dir"], run_copy, dirs_exist_ok=True)
    (run_copy / "unbound_extra.json").write_text("{}")
    with pytest.raises(InfrastructureError, match="extra"):
        verify(run_copy)
    (run_copy / "unbound_extra.json").unlink()
    # 336_s P1-4: a forged run-record identity refuses (the bytes
    # diverge from the closeout's bound file hash)
    forged_record = json.loads(
        (run_copy / "run_record.json").read_text("utf-8"))
    forged_record["run"] = "forged-run"
    (run_copy / "run_record.json").write_text(
        json.dumps(forged_record, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    with pytest.raises(InfrastructureError):
        verify(run_copy)
    # 338_s P1-2: a forged surface_dir refuses at the SEMANTIC
    # record binding (checked before the closeout file hashes)
    shutil.copytree(fx["run_dir"], run_copy, dirs_exist_ok=True)
    forged_record = json.loads(
        (run_copy / "run_record.json").read_text("utf-8"))
    forged_record["surface_dir"] = "/elsewhere/surface"
    (run_copy / "run_record.json").write_text(
        json.dumps(forged_record, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    with pytest.raises(InfrastructureError, match="does not bind "
                       "the authenticated"):
        verify(run_copy)
    # 338_s P1-2: synthetic rehashed chains — an aborted closeout
    # naming the WRONG manifest, and a closeout whose parent is not
    # the launch it closes, both refuse. (The seeded ledger is
    # deterministic, so the same tag reproduces the fixture's
    # reserve head and the fx manifest admits.)
    def _forged_chain(tmp_name, *, closeout_overrides):
        forged_ledger = tmp_path / tmp_name
        reserve = _seed_reserve_ledger(forged_ledger)
        launch = ledger.admit_and_append_launch(
            {"kind": "val_materialization", "question": "q",
             "motivating_evidence": "m",
             "freeze": {
                 "val_launch_sha256":
                     fx["manifest"]["manifest_sha256"],
                 "val_config_sha256": p0_val.VAL_CONFIG_SHA256,
                 "val_freeze_sha256":
                     fx["manifest"]["val_freeze_sha256"],
                 "scientific_design_sha256":
                     fx["manifest"]["scientific_design_sha256"]},
             "parent": reserve["entry_sha256"],
             "budget_allocated_gpu_hours": 0.35,
             "outcome_informed": False,
             "cohort_selection": "outcome_blind"},
            reserve["entry_sha256"], forged_ledger,
            launch_manifest=fx["manifest"])
        closeout_entry = {
            "kind": "closeout", "question": "q",
            "motivating_evidence": "aborted",
            "freeze": {"val_launch_sha256":
                       fx["manifest"]["manifest_sha256"],
                       "partial_artifact_hashes":
                       p0_val._hash_directory(fx["run_dir"])},
            "parent": launch["entry_sha256"],
            "budget_allocated_gpu_hours": 0.0,
            "budget_consumed_gpu_hours": 0.01,
            "closes_entry_sha256": launch["entry_sha256"],
            "terminal_status": "aborted",
            "outcome_informed": False, "outcome_pointer": "x"}
        closeout_entry.update(closeout_overrides)
        tail = ledger.append_ledger_entry(
            closeout_entry, launch["entry_sha256"], forged_ledger)
        return forged_ledger, tail
    wrong_manifest_ledger, tail1 = _forged_chain(
        "forged-manifest.md",
        closeout_overrides={"freeze": {
            "val_launch_sha256": "ff" * 32,
            "partial_artifact_hashes":
                p0_val._hash_directory(fx["run_dir"])}})
    with pytest.raises(InfrastructureError, match="does not name "
                       "this launch manifest"):
        p0_val.verify_val_run(
            fx["run_dir"], ledger_path=wrong_manifest_ledger,
            expected_head_sha256=tail1["entry_sha256"],
            expected_val_lock_sha256=None)
    wrong_parent_ledger, tail2 = _forged_chain(
        "forged-parent.md",
        closeout_overrides={"parent": record["ledger_head"]})
    with pytest.raises(InfrastructureError, match="not the launch "
                       "it closes"):
        p0_val.verify_val_run(
            fx["run_dir"], ledger_path=wrong_parent_ledger,
            expected_head_sha256=tail2["entry_sha256"],
            expected_val_lock_sha256=None)
    shutil.copytree(fx["run_dir"], run_copy, dirs_exist_ok=True)
    tampered = json.loads(
        (run_copy / "overlap_report.json").read_text("utf-8"))
    tampered["val_vs_training"]["alpha_prompt_collisions"] = 0
    (run_copy / "overlap_report.json").write_text(
        json.dumps(tampered), encoding="utf-8")
    with pytest.raises(InfrastructureError):
        verify(run_copy)
    # a forged HEAD cannot authenticate anything
    with pytest.raises(InfrastructureError):
        verify(fx["run_dir"], expected_head_sha256="ab" * 32)


def test_p0_val_lineage_retry_and_deadline(val_run_fixture,
                                           tmp_path, monkeypatch):
    """336_s P1-2/P1-3 + the deadline correction: the LEDGER
    enforces the manifest's frozen initial parent (wrong-parent
    direct admission refuses; correct-parent succeeds;
    identical-design retry succeeds only after an aborted
    closeout); the registered attempt-root rule binds execution;
    a past-deadline materialization aborts into an aborted-closed
    entry that verifies as aborted."""
    fx = val_run_fixture
    # the PRODUCTION lineage parent is the frozen C2 closeout
    assert PRISTINE_VAL_LINEAGE == \
        p0_replay.REPLAY_SOURCE["c2_closeout_entry_sha256"]
    # a first launch from any other head refuses at the runner
    other_ledger = tmp_path / "other-ledger.md"
    other_reserve = _seed_reserve_ledger(other_ledger, tag="other")
    assert other_reserve["entry_sha256"] != fx["reserve_head"]
    with pytest.raises(InfrastructureError, match="FROZEN lineage "
                       "parent|frozen\\s+lineage"):
        p0_val.execute_val_run(
            run_dir=tmp_path / "never-prepared",
            expected_manifest_sha256="aa" * 32,
            expected_head_sha256=other_reserve["entry_sha256"],
            question="q", motivating_evidence="m",
            ledger_path=other_ledger)

    def val_entry(manifest, parent):
        return {"kind": "val_materialization", "question": "q",
                "motivating_evidence": "m",
                "freeze": {
                    "val_launch_sha256":
                        manifest["manifest_sha256"],
                    "val_config_sha256": p0_val.VAL_CONFIG_SHA256,
                    "val_freeze_sha256":
                        manifest["val_freeze_sha256"],
                    "scientific_design_sha256":
                        manifest["scientific_design_sha256"]},
                "parent": parent,
                "budget_allocated_gpu_hours": 0.35,
                "outcome_informed": False,
                "cohort_selection": "outcome_blind"}

    # 336_s P1-2: the FX manifest binds the FX lineage parent —
    # direct ledger admission on the foreign head REFUSES
    with pytest.raises(InfrastructureError, match="frozen initial "
                       "parent"):
        ledger.admit_and_append_launch(
            val_entry(fx["manifest"],
                      other_reserve["entry_sha256"]),
            other_reserve["entry_sha256"], other_ledger,
            launch_manifest=fx["manifest"])
    # a manifest built FOR this ledger admits on the correct parent
    mp = pytest.MonkeyPatch()
    _patch_val_lineage(mp, other_reserve["entry_sha256"])
    try:
        manifest_other = p0_val.build_val_launch_manifest(
            declaration=_val_declaration(),
            environment_manifest=_env_manifest(),
            execution_root=tmp_path / "other-root")
        open_entry = ledger.admit_and_append_launch(
            val_entry(manifest_other,
                      other_reserve["entry_sha256"]),
            other_reserve["entry_sha256"], other_ledger,
            launch_manifest=manifest_other)
        # an OPEN prior attempt blocks any new val launch
        with pytest.raises(InfrastructureError, match="OPEN"):
            ledger.admit_and_append_launch(
                val_entry(manifest_other,
                          open_entry["entry_sha256"]),
                open_entry["entry_sha256"], other_ledger,
                launch_manifest=manifest_other)
        aborted_close = ledger.append_ledger_entry(
            {"kind": "closeout", "question": "q",
             "motivating_evidence": "aborted",
             "freeze": {"val_launch_sha256":
                        manifest_other["manifest_sha256"],
                        "partial_artifact_hashes": {}},
             "parent": open_entry["entry_sha256"],
             "budget_allocated_gpu_hours": 0.0,
             "budget_consumed_gpu_hours": 0.01,
             "closes_entry_sha256": open_entry["entry_sha256"],
             "terminal_status": "aborted",
             "outcome_informed": False, "outcome_pointer": "x"},
            open_entry["entry_sha256"], other_ledger)
        # 336_s: an IDENTICAL-design retry admits after the abort
        retried = ledger.admit_and_append_launch(
            val_entry(manifest_other,
                      aborted_close["entry_sha256"]),
            aborted_close["entry_sha256"], other_ledger,
            launch_manifest=manifest_other)
        retry_close = ledger.append_ledger_entry(
            {"kind": "closeout", "question": "q",
             "motivating_evidence": "aborted",
             "freeze": {"val_launch_sha256":
                        manifest_other["manifest_sha256"],
                        "partial_artifact_hashes": {}},
             "parent": retried["entry_sha256"],
             "budget_allocated_gpu_hours": 0.0,
             "budget_consumed_gpu_hours": 0.01,
             "closes_entry_sha256": retried["entry_sha256"],
             "terminal_status": "aborted",
             "outcome_informed": False, "outcome_pointer": "x"},
            retried["entry_sha256"], other_ledger)
        # ... but a CHANGED-design retry refuses
        changed_design = _resign(dict(manifest_other),
                                 search_cap=89)
        with pytest.raises(InfrastructureError, match="preserve "
                           "the scientific design"):
            ledger.admit_and_append_launch(
                val_entry(changed_design,
                          retry_close["entry_sha256"]),
                retry_close["entry_sha256"], other_ledger,
                launch_manifest=changed_design)
    finally:
        mp.undo()

    # the deadline: a materialization finishing past the ceiling
    # ABORTS and verifies as aborted (no val lock); the registered
    # attempt-root rule is exercised on the way
    abort_tmp = tmp_path / "deadline"
    abort_run = abort_tmp / "runs/routing-dev/val-surface-v1"
    abort_ledger = abort_tmp / "ledger.md"
    abort_tmp.mkdir()
    abort_reserve = _seed_reserve_ledger(abort_ledger,
                                         tag="deadline")
    mp = pytest.MonkeyPatch()
    _patch_val_lineage(mp, abort_reserve["entry_sha256"])
    try:
        # a prepared launch under a NON-registered root refuses
        wrong_root = abort_tmp / "wrongname"
        wrong_manifest = p0_val.prepare_val_launch(
            run_dir=wrong_root,
            _runtime_factory=lambda: val_fake_rt(abort_tmp),
            _environment_builder=_env_manifest)
        with pytest.raises(InfrastructureError, match="registered "
                           "attempt root"):
            p0_val.execute_val_run(
                run_dir=wrong_root,
                expected_manifest_sha256=wrong_manifest[
                    "manifest_sha256"],
                expected_head_sha256=abort_reserve["entry_sha256"],
                question="q", motivating_evidence="m",
                ledger_path=abort_ledger,
                _runtime_factory=lambda: val_fake_rt(abort_tmp),
                _environment_builder=lambda: _env_manifest(
                    git_commit="feedbeef"))
        manifest2 = p0_val.prepare_val_launch(
            run_dir=abort_run,
            _runtime_factory=lambda: val_fake_rt(abort_tmp),
            _environment_builder=_env_manifest)
        clock = iter([0.0] + [10 ** 6] * 20)
        monkeypatch.setattr(p0_val.time, "monotonic",
                            lambda: next(clock))
        monkeypatch.setattr(
            dev_support, "materialize_dev_support",
            lambda *a, **k: None)
        with pytest.raises(InfrastructureError, match="budget "
                           "deadline"):
            p0_val.execute_val_run(
                run_dir=abort_run,
                expected_manifest_sha256=manifest2[
                    "manifest_sha256"],
                expected_head_sha256=abort_reserve["entry_sha256"],
                question="q", motivating_evidence="m",
                ledger_path=abort_ledger,
                _runtime_factory=lambda: val_fake_rt(abort_tmp),
                _environment_builder=lambda: _env_manifest(
                    git_commit="feedbeef"))
        monkeypatch.undo()
        tail = ledger.read_ledger(abort_ledger)[-1]
        assert tail["kind"] == "closeout"
        assert tail["terminal_status"] == "aborted"
        # the aborted-run verifier: the closeout authenticated from
        # the chain; partial hashes verify; no val lock
        assert p0_val.verify_val_run(
            abort_run, ledger_path=abort_ledger,
            expected_head_sha256=tail["entry_sha256"],
            expected_val_lock_sha256=None
        )["terminal_status"] == "aborted"
    finally:
        mp.undo()


def test_p0_val_late_abort_and_full_retry(tmp_path, monkeypatch):
    """338_s P1-1 + the committed full retry: an abort AFTER lock
    creation closes out with val_lock.json as hashed partial
    evidence and VERIFIES as aborted (the lock is an unadmitted
    candidate, never consumable); the identical-design attempt 2
    then runs the FULL CPU-fake lifecycle under the registered
    -r2 root and verifies complete."""
    tmp = tmp_path / "late-abort"
    tmp.mkdir()
    run1 = tmp / "runs/routing-dev/val-surface-v1"
    ledger_path = tmp / "ledger.md"
    reserve = _seed_reserve_ledger(ledger_path, tag="late")
    mp = pytest.MonkeyPatch()
    _patch_val_lineage(mp, reserve["entry_sha256"])
    try:
        manifest1 = p0_val.prepare_val_launch(
            run_dir=run1,
            _runtime_factory=lambda: val_fake_rt(tmp),
            _environment_builder=_env_manifest)
        # force a failure AFTER the val lock is written: the
        # in-run terminal verifier raises
        real_verify = p0_val.verify_val_run
        monkeypatch.setattr(
            p0_val, "verify_val_run",
            lambda *a, **k: (_ for _ in ()).throw(
                InfrastructureError("forced late failure")))
        with pytest.raises(InfrastructureError, match="forced "
                           "late failure"):
            p0_val.execute_val_run(
                run_dir=run1,
                expected_manifest_sha256=manifest1[
                    "manifest_sha256"],
                expected_head_sha256=reserve["entry_sha256"],
                question="q", motivating_evidence="m",
                ledger_path=ledger_path,
                _runtime_factory=lambda: val_fake_rt(tmp),
                _environment_builder=lambda: _env_manifest(
                    git_commit="feedbeef"))
        monkeypatch.undo()
        tail = ledger.read_ledger(ledger_path)[-1]
        assert tail["terminal_status"] == "aborted"
        assert (run1 / "val_lock.json").exists()
        # 338_s P1-1: the late-aborted archive VERIFIES, with the
        # lock recorded as an unadmitted candidate
        verdict = real_verify(
            run1, ledger_path=ledger_path,
            expected_head_sha256=tail["entry_sha256"],
            expected_val_lock_sha256=None)
        assert verdict["terminal_status"] == "aborted"
        assert verdict["unadmitted_val_lock_candidate"] is True
        # ... and it never verifies AS a lock-bearing run
        lock_payload = json.loads(
            (run1 / "val_lock.json").read_text("utf-8"))
        with pytest.raises(InfrastructureError):
            real_verify(
                run1, ledger_path=ledger_path,
                expected_head_sha256=tail["entry_sha256"],
                expected_val_lock_sha256=lock_payload[
                    "record_sha256"])
        # attempt 2: the FULL identical-design retry under the
        # registered -r2 root
        run2 = tmp / "runs/routing-dev/val-surface-v1-r2"
        manifest2 = p0_val.prepare_val_launch(
            run_dir=run2,
            _runtime_factory=lambda: val_fake_rt(tmp),
            _environment_builder=_env_manifest)
        assert manifest2["scientific_design_sha256"] == \
            manifest1["scientific_design_sha256"]
        assert manifest2["manifest_sha256"] != \
            manifest1["manifest_sha256"]
        record = p0_val.execute_val_run(
            run_dir=run2,
            expected_manifest_sha256=manifest2["manifest_sha256"],
            expected_head_sha256=tail["entry_sha256"],
            question="q", motivating_evidence="m",
            ledger_path=ledger_path,
            _runtime_factory=lambda: val_fake_rt(tmp),
            _environment_builder=lambda: _env_manifest(
                git_commit="feedbeef"))
        assert real_verify(
            run2, ledger_path=ledger_path,
            expected_head_sha256=record["ledger_head"],
            expected_val_lock_sha256=record["val_lock_sha256"]
        )["terminal_status"] == "complete"
    finally:
        mp.undo()


def test_p0_val_evidence_restores_clean_clone(tmp_path,
                                              monkeypatch):
    """The 341_f closure gate: the COMMITTED Unit-V evidence
    restores the exact 16-file terminal root (deterministic gunzip)
    and passes the chain-authenticated terminal verifier under the
    COMMITTED ledger head and the externally reviewed val-lock
    pin. PRISTINE config pinned (the module fixture patches the
    lineage for its test ledger)."""
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    restored = p0_val.restore_val_evidence(
        target_run_dir=tmp_path / "restored")
    verdict = p0_val.verify_val_run(
        restored,
        ledger_path=ledger.LEDGER_PATH,
        expected_head_sha256=ledger.ledger_head(),
        expected_val_lock_sha256=p0_val.VAL_LOCK_SHA256)
    assert verdict["verdict"] == "PASS"
    assert verdict["terminal_status"] == "complete"
    assert verdict["val_lock_sha256"] == p0_val.VAL_LOCK_SHA256
    # the reviewed pin is the recorded constant
    assert p0_val.VAL_LOCK_SHA256 == (
        "2aecdf28ad25cae10e494aa9fc1a95138a9feb5a29ab0636314b8479"
        "87caf19d")
    with pytest.raises(InfrastructureError, match="refusing to "
                       "overwrite"):
        p0_val.restore_val_evidence(
            target_run_dir=tmp_path / "restored")


# --- precursors Unit Y: the cycle record + the final R_cycle (343_f) -----------

def test_p0_cycle_record(monkeypatch):
    """Y1: the committed cycle record — outcome-blind cohort, CRN
    seeds distinct from val, the fixed zero+final checkpoint rule,
    authenticated execution identities and overlap re-assertion,
    strict rederiving loader. PRISTINE val config pinned (the val
    fixture patches the lineage)."""
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    obs = p0_cycle.cycle_cohort_observations()
    assert len(obs) == 90
    for o in obs:
        assert o["observation_id"].split(":")[1] == \
            "routing_dev_cycle"
    schedule = p0_cycle.cycle_seed_schedule()
    assert len(schedule) == 720
    assert len({seed for _, _, seed in schedule}) == 720
    # the cycle seeds are DISTINCT from the val seeds at the same
    # coordinates (different namespace ids, domain, and base seed)
    val_first = p0_val.val_cohort_observations()[0]
    assert p0_val.seed_for_completion(
        val_first["observation_id"], 0) != \
        p0_cycle.cycle_seed_for_completion(
            obs[0]["observation_id"], 0)
    assert p0_cycle.CYCLE_CONFIG["evaluation"]["base_seed"] == \
        20260805 != p0_val.VAL_CONFIG["evaluation"]["base_seed"]
    # the committed record loads under its pin and rederives
    record = p0_cycle.load_cycle_record()
    assert record["record_sha256"] == p0_cycle.CYCLE_RECORD_SHA256
    assert record["ordered_observation_ids"] == [
        o["observation_id"] for o in obs]
    assert record["checkpoint_rule"]["evaluate"] == [
        "checkpoint_zero", "final_checkpoint"]
    assert record["val_lock_sha256"] == p0_val.VAL_LOCK_SHA256
    weights = dict(map(tuple, record["natural_mixture_weights"]))
    assert all(abs(w - 1 / 90) < 1e-12 for w in weights.values())
    # 344_s P1-1: execution identities come from the
    # VAL-LOCK-BOUND SURFACE LOCK (and the prelaunch manifest
    # must agree)
    surface_lock = json.loads(Path(
        p0_val.VAL_EVIDENCE_DIR,
        "surface/surface_lock.json").read_text("utf-8"))
    manifest = json.loads(Path(
        p0_val.VAL_EVIDENCE_DIR,
        "prelaunch/val_launch.json").read_text("utf-8"))
    for field, value in record["execution_identities"].items():
        assert surface_lock[field] == value
        assert manifest[field] == value
    # 344_s P1-1: the COMPLETE cycle declaration is frozen
    declaration = record["declaration"]
    assert declaration["planned_step_executions"] == 4020
    assert len(declaration["observations"]) == 90
    assert declaration["worker_ids"] == [0, 1, 2, 3]
    assert declaration["prompt_revision"] == "rev10"
    for key in ("generator_version",
                "difficulty_profile_version",
                "semantic_schedule_sha256",
                "rendered_prompt_schedule_sha256"):
        assert declaration[key]
    # 344_s P1-2: the closed one-reveal reporting rule binds the
    # frozen contract and the frozen template membership
    schema = record["report_schema"]
    assert schema["rule_id"] == "cycle-report-v1"
    assert schema["science_contract_sha256"] == \
        p0_contract.CONTRACT_SHA256
    assert "45 of 90" in schema["repeated_vs_novel_templates"]
    assert len(record["overlap_reassertion"][
        "cycle_vs_training"]["affected_candidate_ids"]) == 45
    # overlap re-assertion binds the val lock's frozen numbers
    assert record["overlap_reassertion"]["val_vs_cycle"][
        "alpha_prompt_collisions"] == 15
    assert record["overlap_reassertion"]["cycle_vs_training"][
        "alpha_prompt_affected_candidates"] == 45
    # a rehashed record with a different seed refuses at the
    # REDERIVATION, not only the hash
    forged = copy.deepcopy(record)
    forged["evaluation"]["base_seed"] = 999
    body = {k: v for k, v in forged.items()
            if k != "record_sha256"}
    forged["record_sha256"] = charter.content_sha256(body)
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json",
                                     delete=False) as handle:
        json.dump(forged, handle)
        forged_path = handle.name
    with pytest.raises(InfrastructureError, match="rederive"):
        p0_cycle.load_cycle_record(
            forged_path, expected_sha256=forged["record_sha256"])
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_cycle.freeze_cycle_record()


def test_p0_r_cycle_final_reserve(tmp_path, monkeypatch):
    """Y2: both derivations recompute; the max rule; the closure
    proof; the validator-gated ledger final path — rehearsed on a
    COPY of the REAL ledger. PRISTINE val config pinned."""
    import shutil
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    record = p0_cycle.load_r_cycle_reserve_record()
    assert record["r_cycle_gpu_hours"] == 1.0
    basis = record["registered_basis"]
    assert basis["measured_seconds_per_observation"] == \
        basis["measured_support_gpu_hours"] * 3600.0 \
        / basis["rendered_observations"]
    assert basis["ceiling_gpu_hours"] == 1.0
    itemized = record["itemized_closure_ceiling"]
    assert itemized["total_gpu_hours"] == round(sum(
        item["gpu_hours"] for item in itemized["items"]), 4)
    assert itemized["total_gpu_hours"] <= \
        record["r_cycle_gpu_hours"]
    # 344_s P1-3: every measured item DERIVES from its
    # authenticated source
    items = {item["obligation"]: item
             for item in itemized["items"]}
    val_closeout = [e for e in ledger.read_ledger()
                    if e["entry_sha256"] ==
                    p0_cycle.CYCLE_CONFIG["lineage"][
                        "parent_entry_sha256"]][0]
    assert items["cycle_surface_materialization"]["gpu_hours"] \
        == val_closeout["budget_consumed_gpu_hours"]
    assert items["two_checkpoint_inference"]["gpu_hours"] == \
        round(2 * 90 * (3648.0 / 785) / 3600.0, 6)
    assert items["verification_traces_archival"]["gpu_hours"] == \
        p0_cycle.VERIFICATION_ARCHIVAL_ALLOWANCE_GPU_HOURS
    assert items["checkpoint_loading_evaluator_startup"][
        "gpu_hours"] == \
        p0_cycle.CHECKPOINT_LOAD_STARTUP_ALLOWANCE_GPU_HOURS
    assert record["cycle_record_sha256"] == \
        p0_cycle.CYCLE_RECORD_SHA256
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_cycle.freeze_r_cycle_reserve_record()
    # validate_reserve: the final max-of-two rule
    final_reserve = {
        "status": "final", "r_cycle_gpu_hours": 2.0,
        "assumed_cohort_size": 90, "evaluation_multiplier": 2.0,
        "measured_seconds_per_observation": 2.44,
        "measured_support_gpu_hours": 0.0732,
        "itemized_ceiling_gpu_hours": 2.0,
        "rounding": "ceil_to_whole_gpu_hours"}
    ledger.validate_reserve(final_reserve)
    with pytest.raises(InfrastructureError, match="recompute "
                       "exactly"):
        ledger.validate_reserve(
            {**final_reserve, "r_cycle_gpu_hours": 1.0})
    with pytest.raises(InfrastructureError, match="whole-valued"):
        ledger.validate_reserve(
            {**final_reserve, "itemized_ceiling_gpu_hours": 1.5,
             "r_cycle_gpu_hours": 1.5})
    with pytest.raises(InfrastructureError, match="whole-valued"):
        ledger.validate_reserve(
            {k: v for k, v in final_reserve.items()
             if k != "itemized_ceiling_gpu_hours"})
    with pytest.raises(InfrastructureError, match="FINAL"):
        ledger.validate_reserve(
            {**final_reserve, "status": "provisional",
             "r_cycle_gpu_hours": 1.0,
             "itemized_ceiling_gpu_hours": 1.0})
    # the ledger final path, rehearsed on a TRUNCATED copy of the
    # real ledger (the REAL ledger now carries the appended final
    # reserve at entry 20; the rehearsal replays the append from
    # the frozen parent — a valid chain PREFIX)
    frozen_parent = p0_cycle.CYCLE_CONFIG["lineage"][
        "parent_entry_sha256"]
    real_head_before = ledger.ledger_head()
    full_text = Path(ledger.LEDGER_PATH).read_text("utf-8")
    truncated = full_text[:full_text.index("\n## entry 20 ")]
    ledger_copy = tmp_path / "ledger.md"
    ledger_copy.write_text(truncated, encoding="utf-8")
    assert ledger.ledger_head(ledger_copy) == frozen_parent
    # 344_s P1-4: only the FROZEN parent head admits the append
    with pytest.raises(InfrastructureError, match="frozen parent"):
        p0_cycle.record_final_r_cycle(
            expected_head_sha256="ab" * 32,
            ledger_path=ledger_copy)
    appended = p0_cycle.record_final_r_cycle(
        expected_head_sha256=frozen_parent,
        ledger_path=ledger_copy)
    entries = ledger.verify_ledger_head(
        appended["entry_sha256"], ledger_copy)
    state = ledger.envelope_state(
        entries, charter.CYCLE_ENVELOPE_GPU_HOURS)
    assert state["reserve"]["r_cycle_gpu_hours"] == 1.0
    assert state["reserve"]["status"] == "final"
    # the rehearsal reproduces the REAL appended entry exactly
    real_final = [e for e in ledger.read_ledger()
                  if e["kind"] == "reserve_update"
                  and e["reserve"]["status"] == "final"]
    assert len(real_final) == 1
    assert appended["entry_sha256"] == \
        real_final[0]["entry_sha256"]
    # 344_s P1-4: a SECOND final reserve refuses (head has moved
    # off the frozen parent, and the once-only rule also bites)
    with pytest.raises(InfrastructureError, match="frozen parent"):
        p0_cycle.record_final_r_cycle(
            expected_head_sha256=appended["entry_sha256"],
            ledger_path=ledger_copy)
    # ... and on the REAL ledger, any further append refuses
    with pytest.raises(InfrastructureError, match="frozen parent"):
        p0_cycle.record_final_r_cycle(
            expected_head_sha256=ledger.ledger_head())
    # a final append WITHOUT the cycle-record bindings refuses
    with pytest.raises(InfrastructureError, match="must bind"):
        ledger._append(
            {"kind": "reserve_update", "question": "q",
             "motivating_evidence": "m",
             "freeze": {"support_closeout_sha256":
                        p0_cycle.SUPPORT_CLOSEOUT_SHA256,
                        "surface_lock_sha256":
                        p0_cycle.SUPPORT_SURFACE_LOCK_SHA256},
             "parent": appended["entry_sha256"],
             "budget_allocated_gpu_hours": 0.0,
             "outcome_informed": False,
             "reserve": {
                 "status": "final", "r_cycle_gpu_hours": 1.0,
                 "assumed_cohort_size": 90,
                 "evaluation_multiplier": 2.0,
                 "measured_seconds_per_observation": 2.44,
                 "measured_support_gpu_hours": 0.0732,
                 "itemized_ceiling_gpu_hours": 1.0,
                 "rounding": "ceil_to_whole_gpu_hours"}},
            appended["entry_sha256"], ledger_copy)
    # the REAL ledger is untouched by the rehearsal (the head is
    # exactly what it was before; the chain may legitimately have
    # grown past entry 20 — e.g. the smoke launch/closeout — so
    # the final-reserve entry need not be the head)
    assert ledger.ledger_head() == real_head_before


# --- precursors Unit T: the beta timing smoke (347_f) --------------------------

def test_p0_smoke_design(monkeypatch):
    """Unit T rev2 CPU boundaries: the persisted freeze as a
    strict identity boundary; the shape-proving closed measurement
    schema; the two-pass conservative pricing; the exact-value
    mapping; the manifest rederivation."""
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    config = p0_smoke.SMOKE_CONFIG
    assert charter.content_sha256(config) == \
        p0_smoke.SMOKE_CONFIG_SHA256
    assert config["budget_gpu_hours"] == 0.75
    assert p0_smoke.CADENCE_UPDATES == (0, 628, 1256, 1884, 2512,
                                        3140, 3768, 4396, 5024,
                                        5652, 6123)
    assert len({p0_val.VAL_CONFIG["evaluation"]["base_seed"],
                p0_cycle.CYCLE_CONFIG["evaluation"]["base_seed"],
                config["training"]["seed"]}) == 3
    observations = p0_smoke.timing_cohort_observations()
    assert len(observations) == 90
    assert all(o["observation_id"].split(":")[1] == "routing_dev"
               for o in observations)
    schedule = p0_smoke.timing_seed_schedule()
    assert len(schedule) == 720
    # 348_s #4: the PERSISTED freeze loads strictly and rederives
    freeze = p0_smoke.load_smoke_freeze()
    assert freeze["freeze_sha256"] == p0_smoke.SMOKE_FREEZE_SHA256
    assert freeze["science_contract_sha256"] == \
        p0_contract.CONTRACT_SHA256
    assert freeze["pinned_mixture_record_sha256"] == \
        p0_replay.REPLAY_SOURCE["pinned_mixture_record_sha256"]
    assert freeze["extension_surface_lock_sha256"] == \
        p0_replay.REPLAY_SOURCE["extension_surface_lock_sha256"]
    import hashlib as _hashlib
    from tasks.conductor.stage1 import prompt_fewshot
    assert freeze["prompt_sha256"] == _hashlib.sha256(
        prompt_fewshot().encode("utf-8")).hexdigest()
    with pytest.raises(InfrastructureError, match="reviewed"):
        p0_smoke.load_smoke_freeze(expected_sha256="0" * 64)
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_smoke.freeze_smoke_tranche()
    monkeypatch.setitem(p0_smoke.SMOKE_CONFIG,
                        "budget_gpu_hours", 0.7)
    with pytest.raises(InfrastructureError, match="mutated"):
        p0_smoke.timing_cohort_observations()
    monkeypatch.undo()
    # the mapping on synthetic measurements (348_s: two passes,
    # conservative max pricing, EXACT values)
    measurements = {
        "startup_seconds": 150.0,
        "checkpoint_zero_eval_seconds": 420.0,
        "whole_epoch_seconds": 840.0,
        "per_group_generation_seconds": [5.0] * 156 + [9.0],
        "checkpoint_bundle_write_seconds": 4.0,
        "post_epoch_eval_seconds": 433.0,
        "trace_flush_archive_seconds": 3.0,
        "per_epoch_trace_bytes": 15_000_000,
        "peak_reserved_vram_mib": 9000,
        "warmup_lr_trajectory":
            [1e-05 * i / 10 for i in range(1, 11)] + [1e-05],
        "optimizer_updates": 157,
        "reference_kl_logged_events": 9,
        "adapter_state_changed": True,
    }
    inputs = p0_smoke.derive_cap_inputs(measurements)
    # eval price = max(420, 433) = 433, used EVERYWHERE
    assert inputs["components"]["eval_price_seconds"] == 433.0
    assert inputs["frozen_non_rollout_overhead_seconds"] == \
        433.0 + 9 * (433.0 + 4.0) + 150.0
    assert inputs["components"]["full_run_trace_seconds"] == 141.0
    assert inputs["measured_finalization_reserve_seconds"] == \
        9.0 + 433.0 + 4.0 + 141.0
    assert inputs["cumulative_consumed_seconds"] == 0.0
    projection = p0_smoke.worked_launch_projection(measurements)
    assert projection["binding"] is False
    plan = projection["plan"]
    assert plan["launch_epochs"] == min(plan["nominal_epochs"],
                                        plan["capacity_epochs"])
    # 348_s #3: the shape proofs bite
    with pytest.raises(InfrastructureError, match="closed field"):
        p0_smoke.validate_measurements(
            {**measurements, "mean_reward": 0.5})
    flat = [1e-05] * 11
    with pytest.raises(InfrastructureError, match="frozen "
                       "constant_with_warmup"):
        p0_smoke.validate_measurements(
            {**measurements, "warmup_lr_trajectory": flat})
    wrong_plateau = [2e-05 * i / 10 for i in range(1, 11)] \
        + [2e-05]
    with pytest.raises(InfrastructureError, match="frozen "
                       "constant_with_warmup"):
        p0_smoke.validate_measurements(
            {**measurements,
             "warmup_lr_trajectory": wrong_plateau})
    with pytest.raises(InfrastructureError, match="smaller than "
                       "the sum"):
        p0_smoke.validate_measurements(
            {**measurements, "whole_epoch_seconds": 10.0})
    with pytest.raises(InfrastructureError, match="exactly 157"):
        p0_smoke.validate_measurements(
            {**measurements, "optimizer_updates": 156})
    with pytest.raises(InfrastructureError, match="reference"):
        p0_smoke.validate_measurements(
            {**measurements, "reference_kl_logged_events": 0})
    with pytest.raises(InfrastructureError, match="adapter"):
        p0_smoke.validate_measurements(
            {**measurements, "adapter_state_changed": False})
    # 350_s #4: the EXECUTED seed realization is frozen
    realization = p0_smoke.executed_seed_realization()
    assert len(realization) == 90
    assert realization[0][1] == p0_val.seed_for_completion(
        realization[0][0], 0, domain="timing_smoke",
        base_seed=20260806)
    monkeypatch.setattr(p0_smoke, "TIMING_EXECUTED_SEEDS_SHA256",
                        "0" * 64)
    with pytest.raises(InfrastructureError, match="frozen pin"):
        p0_smoke.executed_seed_realization()
    monkeypatch.undo()
    # 350_s #1: the ESTABLISHED reward boundary normalizes
    # TRL message-list completions (the reproduction shape)
    from tasks.routing import checkpoint as ckpt_module
    accountant = ckpt_module.GroupAccountant()
    surface = {("obs:a", (2,)): 1.0}
    trace = tmp_path_maker = None
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        trace_path = Path(tmp) / "trace.jsonl"
        base_reward = resume_validation.make_validation_reward(
            surface, accountant, trace_path, group_size=8)
        completions = [[{"role": "assistant",
                         "content": "{\"worker_ids\": [2]}"}]] * 8
        rewards = base_reward(
            completions, observation_id=["obs:a"] * 8,
            positions=[json.dumps(["p1"])] * 8,
            num_steps=[1] * 8)
        assert rewards == [1.0] * 8
        assert trace_path.exists()
    # 350_s #4: console reporters are stripped
    class _FakeHandler:
        def __init__(self):
            from transformers.trainer_callback import (
                PrinterCallback,
                ProgressCallback,
            )
            self.callbacks = [PrinterCallback(),
                              ProgressCallback()]

    class _FakeTrainer:
        def __init__(self):
            self.callback_handler = _FakeHandler()

        def remove_callback(self, kind):
            self.callback_handler.callbacks = [
                c for c in self.callback_handler.callbacks
                if not isinstance(c, kind)]

    fake = _FakeTrainer()
    p0_smoke._strip_console_callbacks(fake)
    assert fake.callback_handler.callbacks == []
    # 350_s #5: the deadline helper bites
    with pytest.raises(InfrastructureError, match="deadline "
                       "exceeded"):
        p0_smoke._check_deadline(0.0, "test point")
    # 350_s #5: the manifest-bound smoke admission is authoritative
    # (a forged budget refuses at the ledger)
    # the launch manifest rederives the frozen launch
    manifest = p0_smoke.build_smoke_launch_manifest(
        environment_manifest=_env_manifest(),
        execution_root="runs/routing-dev/beta-smoke-v1")
    validated = p0_smoke.validate_smoke_launch_manifest(manifest)
    assert validated["manifest_sha256"] == \
        manifest["manifest_sha256"]
    assert manifest["lineage_parent_sha256"] == \
        p0_smoke.SMOKE_CONFIG["lineage"]["parent_entry_sha256"]
    resigned = {k: v for k, v in manifest.items()
                if k != "manifest_sha256"}
    resigned["budget_gpu_hours"] = 2.0
    resigned["manifest_sha256"] = charter.content_sha256(resigned)
    with pytest.raises(InfrastructureError, match="diverges"):
        p0_smoke.validate_smoke_launch_manifest(resigned)


def test_p0_smoke_rev4_lifecycle(monkeypatch, tmp_path):
    """352_s direct regressions: manifestless admission, callback
    ordering, abort cleanup, terminal-proof mutation."""
    # --- 352_s #1: a manifestless smoke with fabricated hashes
    # can never admit (the reviewer's reproduction)
    ledger_path = tmp_path / "ledger.md"
    seeded = _seed_reserve_ledger(ledger_path, tag="smoke-adm")
    head = seeded["entry_sha256"]
    entry = {"kind": "engineering_smoke",
             "question": "manifestless smoke",
             "motivating_evidence": "352_s #1 reproduction",
             "freeze": {"smoke_launch_sha256": "ab" * 32,
                        "smoke_freeze_sha256": "cd" * 32,
                        "smoke_config_sha256": "ef" * 32},
             "parent": head, "budget_allocated_gpu_hours": 0.75,
             "outcome_informed": False}
    with pytest.raises(InfrastructureError, match="WITH its"):
        ledger.admit_and_append_launch(entry, head, ledger_path)
    with pytest.raises(InfrastructureError,
                       match="binds a smoke-launch"):
        ledger.admit_and_append_launch(
            entry, head, ledger_path,
            launch_manifest={"kind": "some-other-manifest-v1"})
    # a coherent manifest whose hash the entry does not name
    with pytest.raises(InfrastructureError, match="exact "
                       "smoke-launch manifest hash"):
        ledger.admit_and_append_launch(
            entry, head, ledger_path,
            launch_manifest={
                "kind": "routing-dev-beta-smoke-launch-v1",
                "manifest_sha256": "99" * 32,
                "budget_gpu_hours": 0.75,
                "smoke_freeze_sha256": "cd" * 32,
                "lineage_parent_sha256": head})
    # --- 352_s #2: lifecycle ordering — deadline BEFORE the step,
    # consumption at the OPTIMIZER, never inside the reward
    from tasks.routing import checkpoint as ckpt_module
    instrumentation = p0_smoke._EpochInstrumentation()
    accountant = ckpt_module.GroupAccountant()
    expired = p0_smoke._make_update_callback(
        instrumentation, accountant, deadline=0.0)
    with pytest.raises(InfrastructureError,
                       match="deadline exceeded"):
        expired.on_step_begin(None, None, None)
    import time as _time
    callback = p0_smoke._make_update_callback(
        instrumentation, accountant,
        deadline=_time.monotonic() + 3600.0)
    callback.on_step_begin(None, None, None)
    # consumption cannot precede generation — the rev3 defect
    # (record_update inside the reward) is structurally refused
    with pytest.raises(InfrastructureError,
                       match="never generated"):
        callback.on_optimizer_step(None, None, None)
    accountant.record_generation(1, 8)
    assert accountant.optimizer_updates == 0
    callback.on_optimizer_step(None, None, None)
    assert accountant.optimizer_updates == 1
    assert accountant.consumed_groups == 1
    callback.on_step_end(None, None, None)
    assert instrumentation.updates == 1
    # --- 352_s #4: abort cleanup seals raw traces and discards
    # trained state; a cleanup failure propagates (no closeout)
    run_dir = tmp_path / "abort-run"
    sealed = run_dir / "sealed"
    sealed.mkdir(parents=True)
    (sealed / "training_trace.jsonl").write_text(
        '{"row": 1}\n', encoding="utf-8")
    (sealed / "eval_ckpt0.jsonl.gz").write_bytes(b"already")
    bundle = run_dir / "checkpoint_bundle"
    bundle.mkdir()
    (bundle / "adapter_state.safetensors").write_bytes(b"lora")
    hf_dir = run_dir / "checkpoint-42"
    hf_dir.mkdir()
    (hf_dir / "weights.bin").write_bytes(b"w")
    p0_smoke._sanitize_for_abort(run_dir)
    assert not bundle.exists() and not hf_dir.exists()
    assert not (sealed / "training_trace.jsonl").exists()
    assert (sealed / "training_trace.jsonl.gz").exists()
    assert (sealed / "eval_ckpt0.jsonl.gz").read_bytes() == \
        b"already"
    (sealed / "late_trace.jsonl").write_text("x\n",
                                             encoding="utf-8")

    def _fail_seal(path):
        raise OSError("disk full")

    monkeypatch.setattr(p0_smoke, "_seal_file", _fail_seal)
    with pytest.raises(OSError, match="disk full"):
        p0_smoke._sanitize_for_abort(run_dir)
    monkeypatch.undo()
    # --- 352_s #3: the checkpoint proof is validated, never
    # trusted — every mutation channel refuses
    proof = {"checkpoint_sha256": "aa" * 32,
             "state_artifact_sha256": {
                 "adapter": "bb" * 32, "optimizer": "cc" * 32,
                 "scheduler": "dd" * 32, "rng": "ee" * 32},
             "counters": {"generated_groups": 157,
                          "consumed_groups": 157,
                          "optimizer_updates": 157,
                          "sampled_completions": 157 * 8}}
    p0_smoke._validate_checkpoint_proof(proof)
    with pytest.raises(InfrastructureError,
                       match="one-epoch expectation"):
        p0_smoke._validate_checkpoint_proof(
            {**proof, "counters": {**proof["counters"],
                                   "optimizer_updates": 156}})
    with pytest.raises(InfrastructureError,
                       match="closed schema"):
        p0_smoke._validate_checkpoint_proof(
            {**proof, "extra_claim": True})
    missing_rng = {k: v for k, v in
                   proof["state_artifact_sha256"].items()
                   if k != "rng"}
    with pytest.raises(InfrastructureError,
                       match="bundle manifest"):
        p0_smoke._validate_checkpoint_proof(
            {**proof, "state_artifact_sha256": missing_rng})
    with pytest.raises(InfrastructureError, match="malformed"):
        p0_smoke._validate_checkpoint_proof(
            {**proof, "checkpoint_sha256": "abc"})
    assert set(p0_smoke._SEALED_INVENTORY) == {
        "training_trace.jsonl.gz", "eval_ckpt0.jsonl.gz",
        "eval_post.jsonl.gz", "trainer_log_history.json.gz"}


def test_p0_smoke_reward_entry_deadline():
    """355_s: the step BEGINS before the deadline; generation
    finishes AFTER it — the reward entry refuses, so scoring and
    consumption never occur."""
    import time as _time
    from tasks.routing import checkpoint as ckpt_module
    instrumentation = p0_smoke._EpochInstrumentation()
    accountant = ckpt_module.GroupAccountant()
    # warm the factory's lazy transformers import so the timing
    # window below is not consumed by first-import cost
    p0_smoke._make_update_callback(instrumentation, accountant,
                                   deadline=0.0)
    deadline = _time.monotonic() + 1.0
    callback = p0_smoke._make_update_callback(
        instrumentation, accountant, deadline=deadline)
    callback.on_step_begin(None, None, None)
    scored = []

    def base_reward(completions=None, **kwargs):
        scored.append(completions)
        accountant.record_generation(1, 8)
        return [0.0] * 8

    reward = p0_smoke._make_smoke_reward(
        base_reward, instrumentation, deadline)
    _time.sleep(1.1)
    with pytest.raises(InfrastructureError,
                       match="training reward entry"):
        reward(completions=[["late"]] * 8)
    assert scored == []
    assert accountant.generated_groups == 0
    with pytest.raises(InfrastructureError,
                       match="never generated"):
        callback.on_optimizer_step(None, None, None)
    # the same path scores normally inside the deadline
    instrumentation.start_epoch()
    live = p0_smoke._make_smoke_reward(
        base_reward, instrumentation, _time.monotonic() + 3600.0)
    assert live(completions=[["ok"]] * 8) == [0.0] * 8
    assert accountant.generated_groups == 1
    assert len(scored) == 1


# --- precursors Unit L: the real freeze + execution identity + admission -------

def test_p0_unit_l_freeze_and_identity(monkeypatch, tmp_path):
    """Unit L: the chain-authenticated smoke record; the BINDING
    plan derivation; the real P0LaunchFreeze under its pin; the
    frozen cadence in both unit systems; the P0ExecutionIdentity
    strict rederiving loader."""
    from tasks.routing import p0_execution
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    # the smoke record authenticates through the verified chain
    record = p0_execution.authenticate_smoke_record()
    assert record["smoke_freeze_sha256"] == \
        p0_smoke.SMOKE_FREEZE_SHA256
    monkeypatch.setattr(p0_execution, "BETA_SMOKE_RECORD_SHA256",
                        "0" * 64)
    with pytest.raises(InfrastructureError, match="reviewed"):
        p0_execution.authenticate_smoke_record()
    monkeypatch.undo()
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    # anchoring the closeout at a different chain entry refuses
    monkeypatch.setattr(
        p0_execution, "SMOKE_CLOSEOUT_SHA256",
        "929e1724" + p0_execution.SMOKE_CLOSEOUT_SHA256[8:])
    with pytest.raises(InfrastructureError, match="chain"):
        p0_execution.authenticate_smoke_record()
    monkeypatch.undo()
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    # the BINDING derivation: 39/41/39, no extra training
    plan = p0_execution.derive_real_launch_plan()
    assert (plan["nominal_epochs"], plan["capacity_epochs"],
            plan["launch_epochs"]) == (39, 41, 39)
    assert plan["branch"] == "no_extra_training"
    assert plan["spare_epochs_not_trained"] == 2
    # the real freeze loads under its pin and binds everything
    freeze = p0_execution.load_real_launch_freeze()
    assert p0_cap._strict_equal(freeze.launch_plan.to_record(),
                                plan)
    assert freeze.runtime.seed == p0_execution.P0_TRAINING_SEED
    assert len({p0_execution.P0_TRAINING_SEED, 20260804,
                20260805, 20260806}) == 4
    assert freeze.runtime.attested_environment_sha256 == \
        p0_replay.REPLAY_SOURCE["attested_environment_sha256"]
    with pytest.raises(InfrastructureError, match="reviewed"):
        p0_launch.load_p0_launch_freeze(
            p0_launch.LAUNCH_FREEZE_PATH, "0" * 64)
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_execution.freeze_real_p0_launch()
    # the frozen cadence in BOTH unit systems
    cadence = p0_execution.derive_cadence(39, 157)
    assert tuple(cadence["update_indices"]) == \
        p0_smoke.CADENCE_UPDATES
    assert cadence["epoch_labels"][0] == 0
    assert cadence["epoch_labels"][-1] == 39
    trimmed = p0_execution.derive_cadence(10, 157)
    assert trimmed["epoch_labels"] == [0, 4, 8, 10]
    with pytest.raises(InfrastructureError, match="positive"):
        p0_execution.derive_cadence(0, 157)
    # the identity loads under its pin and rederives
    identity = p0_execution.load_p0_execution_identity(
        expected_sha256=p0_execution.P0_EXECUTION_IDENTITY_SHA256)
    assert identity["launch_freeze_sha256"] == \
        p0_execution.P0_LAUNCH_FREEZE_SHA256
    assert identity["telemetry"]["trajectory_index_sets"][
        "checkpoint_trajectory"] == cadence["update_indices"]
    evaluation = identity["evaluation"]
    assert evaluation["base_seed"] == 20260804
    assert evaluation["val_lock_sha256"] == \
        p0_val.VAL_LOCK_SHA256
    assert evaluation["seed_schedule_sha256"] == \
        p0_val.VAL_SEED_SCHEDULE_SHA256
    assert "NO checkpoint index" in evaluation["seed_rule"]
    assert identity["training_seed"] == 20260807
    with pytest.raises(InfrastructureError, match="reviewed"):
        p0_execution.load_p0_execution_identity(
            expected_sha256="0" * 64)
    # a REHASHED identity with a mutated cadence refuses at the
    # rederivation
    payload = json.loads(Path(
        p0_execution.EXECUTION_IDENTITY_PATH).read_text("utf-8"))
    body = {k: v for k, v in payload.items()
            if k != "record_sha256"}
    body["cadence"] = dict(body["cadence"])
    body["cadence"]["update_indices"] = \
        list(body["cadence"]["update_indices"])
    body["cadence"]["update_indices"][3] = 1885
    forged = dict(body)
    forged["record_sha256"] = charter.content_sha256(body)
    forged_path = tmp_path / "forged_identity.json"
    forged_path.write_text(json.dumps(forged), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="rederive"):
        p0_execution.load_p0_execution_identity(
            forged_path, expected_sha256=forged["record_sha256"])
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_execution.freeze_p0_execution_identity(
            launch_freeze_sha256=
            p0_execution.P0_LAUNCH_FREEZE_SHA256)


def test_p0_unit_l_admission(monkeypatch, tmp_path):
    """Unit L: the closed execution manifest; the fail-closed
    admit_p0_execution on a COPY of the real ledger (the real
    ledger untouched); the 346_f final-reserve cross-check; the
    manifest-mandatory training_run branch; open-attempt refusal."""
    import shutil
    from tasks.routing import p0_execution
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    live_env = json.loads(Path(
        "runs/routing-dev/beta-smoke-v1/execute_env_manifest.json"
    ).read_text("utf-8"))
    manifest = p0_execution.build_p0_execution_manifest(
        environment_manifest=live_env,
        execution_root=tmp_path / "p0-v1")
    validated = p0_execution.validate_p0_execution_manifest(
        manifest)
    assert validated["manifest_sha256"] == \
        manifest["manifest_sha256"]
    assert manifest["lineage_parent_sha256"] == \
        p0_execution.SMOKE_CLOSEOUT_SHA256
    assert manifest["budget_gpu_hours"] == 10.0
    resigned = {k: v for k, v in manifest.items()
                if k != "manifest_sha256"}
    resigned["budget_gpu_hours"] = 20.0
    resigned["manifest_sha256"] = charter.content_sha256(resigned)
    with pytest.raises(InfrastructureError, match="diverges"):
        p0_execution.validate_p0_execution_manifest(resigned)
    # the manifest-mandatory training_run ledger branch
    ledger_copy = tmp_path / "ledger.md"
    shutil.copy(ledger.LEDGER_PATH, ledger_copy)
    head = ledger.ledger_head(ledger_copy)
    assert head == p0_execution.SMOKE_CLOSEOUT_SHA256
    bare = {"kind": "training_run", "question": "q",
            "motivating_evidence": "m",
            "freeze": {"launch_freeze_sha256": "ab" * 32},
            "parent": head, "budget_allocated_gpu_hours": 10.0,
            "outcome_informed": False}
    with pytest.raises(InfrastructureError, match="WITH its"):
        ledger.admit_and_append_launch(bare, head, ledger_copy)
    with pytest.raises(InfrastructureError,
                       match="P0 execution manifest"):
        ledger.admit_and_append_launch(
            bare, head, ledger_copy,
            launch_manifest={"kind": "wrong-kind-v1"})
    # the 346_f duplicate-final-reserve cross-check
    chain = ledger.verify_ledger_head(head, ledger_copy)
    check = p0_execution._cross_check_final_reserve(chain)
    assert check["r_cycle_gpu_hours"] == 1.0
    fake_final = {"kind": "reserve_update", "entry_sha256": "9" * 64,
                  "reserve": {"status": "final",
                              "r_cycle_gpu_hours": 1.0}}
    with pytest.raises(InfrastructureError, match="exactly one"):
        p0_execution._cross_check_final_reserve(
            chain + [fake_final])
    divergent = json.loads(json.dumps(chain))
    for entry in divergent:
        if entry["kind"] == "reserve_update" \
                and entry["reserve"].get("status") == "final":
            entry["reserve"]["r_cycle_gpu_hours"] = 3.0
    with pytest.raises(InfrastructureError, match="diverges"):
        p0_execution._cross_check_final_reserve(divergent)
    # 360_s P2-4: the COMPLETE reserve projection is compared —
    # a mutated rounding field or a forged freeze binding refuses
    mutated = json.loads(json.dumps(chain))
    for entry in mutated:
        if entry["kind"] == "reserve_update" \
                and entry["reserve"].get("status") == "final":
            entry["reserve"]["rounding"] = "floor"
    with pytest.raises(InfrastructureError, match="diverges"):
        p0_execution._cross_check_final_reserve(mutated)
    forged_binding = json.loads(json.dumps(chain))
    for entry in forged_binding:
        if entry["kind"] == "reserve_update" \
                and entry["reserve"].get("status") == "final":
            entry["freeze"]["cycle_record_sha256"] = "ab" * 32
    with pytest.raises(InfrastructureError, match="bindings"):
        p0_execution._cross_check_final_reserve(forged_binding)
    # the full fail-closed admission on the COPY
    run_dir = tmp_path / "p0-v1"
    bundle = p0_execution.admit_p0_execution(
        execution_manifest=manifest,
        expected_manifest_sha256=manifest["manifest_sha256"],
        prepared_environment=live_env,
        expected_head_sha256=head,
        question="P0 admission rehearsal (Unit L)",
        motivating_evidence="359_f CPU boundary test",
        run_dir=run_dir,
        ledger_path=ledger_copy,
        _live_environment=live_env)
    assert bundle["preparation"]["gates"]["launch_plan"] == \
        "REDERIVED"
    assert bundle["preparation"]["groups_total"] == 6123
    # 360_s P2-3: the completed admission returns ADMITTED
    assert bundle["admission"]["status"] == "ADMITTED"
    assert bundle["admission"]["launch_entry_sha256"] == \
        bundle["launch_entry_sha256"]
    assert bundle["preparation"]["launch_admission"]["status"] \
        == "ADMITTED"
    assert bundle["reserve_check"]["r_cycle_gpu_hours"] == 1.0
    entries = ledger.verify_ledger_head(
        bundle["launch_entry_sha256"], ledger_copy)
    assert entries[-1]["kind"] == "training_run"
    assert entries[-1]["parent"] == head
    # 360_s P1-1: a SECOND admission refuses — first-launch-only
    with pytest.raises(InfrastructureError,
                       match="first-launch-only"):
        p0_execution.admit_p0_execution(
            execution_manifest=manifest,
            expected_manifest_sha256=manifest["manifest_sha256"],
            prepared_environment=live_env,
            expected_head_sha256=bundle["launch_entry_sha256"],
            question="q", motivating_evidence="m",
            run_dir=run_dir, ledger_path=ledger_copy,
            _live_environment=live_env)
    # assemble the prelaunch directory the runner would have
    # persisted (the SAME manifest + env + artifact byte copies)
    prelaunch = run_dir / "prelaunch"
    prelaunch.mkdir(parents=True)
    (prelaunch / "p0_launch.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    (prelaunch / "env_manifest.json").write_text(
        json.dumps(live_env, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    for name, source in (
            ("launch_freeze.json", p0_launch.LAUNCH_FREEZE_PATH),
            ("execution_identity.json",
             p0_execution.EXECUTION_IDENTITY_PATH)):
        (prelaunch / name).write_bytes(Path(source).read_bytes())
    # 363_s F5 reproduction: an impossible EMPTY run refuses at
    # the exact frozen cadence; a negative runtime refuses too
    empty_record = {
        "run": "routing-dev-p0-v1",
        "p0_launch_manifest_sha256": manifest["manifest_sha256"],
        "launch_freeze_sha256": manifest["launch_freeze_sha256"],
        "execution_identity_sha256":
            manifest["execution_identity_sha256"],
        "launch_entry_sha256": bundle["launch_entry_sha256"],
        "cadence_completed": [], "checkpoints": {},
        "whole_run_seconds": -1.0, "sealed_sha256": {},
        "development_only": True}
    (run_dir / "p0_record.json").write_text(
        json.dumps(empty_record), encoding="utf-8")
    with pytest.raises(InfrastructureError,
                       match="eleven-point cadence"):
        p0_execution.verify_p0_run(
            run_dir, ledger_path=ledger_copy,
            expected_head_sha256=bundle["launch_entry_sha256"])
    cadence = p0_execution.load_p0_execution_identity(
        expected_sha256=manifest["execution_identity_sha256"]
    )["cadence"]["update_indices"]
    negative = dict(empty_record)
    negative["cadence_completed"] = list(cadence)
    negative["checkpoints"] = {str(i): {} for i in cadence}
    (run_dir / "p0_record.json").write_text(
        json.dumps(negative), encoding="utf-8")
    with pytest.raises(InfrastructureError,
                       match="non-negative finite"):
        p0_execution.verify_p0_run(
            run_dir, ledger_path=ledger_copy,
            expected_head_sha256=bundle["launch_entry_sha256"])
    (run_dir / "p0_record.json").unlink()
    # 363_s F4: the EXPLICIT terminal abort closes the launch with
    # the cumulative consumed time; a second abort refuses
    import time as _time3
    p0_execution._append_session_entry(run_dir, {
        "kind": "session_start", "session_index": 1,
        "mode": "fresh", "start_group_index": 0,
        "resume_update_index": None,
        "wall_start_utc": _time3.time()})
    p0_execution._record_resumable_interruption(
        run_dir, 1, 9000.0, RuntimeError("X"))
    aborted = p0_execution.terminally_abort_p0(
        run_dir=run_dir, question="q",
        reason="360_s reproduction (2.5 GPU-h consumed)",
        ledger_path=ledger_copy)
    assert aborted["terminal_status"] == "aborted"
    assert aborted["budget_consumed_gpu_hours"] == 2.5
    with pytest.raises(InfrastructureError, match="already "
                       "closed"):
        p0_execution.terminally_abort_p0(
            run_dir=run_dir, question="q", reason="again",
            ledger_path=ledger_copy)
    with pytest.raises(InfrastructureError,
                       match="first-launch-only"):
        p0_execution.admit_p0_execution(
            execution_manifest=manifest,
            expected_manifest_sha256=manifest["manifest_sha256"],
            prepared_environment=live_env,
            expected_head_sha256=ledger.ledger_head(ledger_copy),
            question="q", motivating_evidence="m",
            run_dir=run_dir, ledger_path=ledger_copy,
            _live_environment=live_env)
    # 360_s P1-2 reproduction: a re-signed manifest (arbitrary
    # root, zeroed environment hash) refuses at the EXTERNAL hash
    forged = {k: v for k, v in manifest.items()
              if k != "manifest_sha256"}
    forged["execution_root"] = str(tmp_path / "elsewhere")
    forged["environment_manifest_sha256"] = "0" * 64
    forged["manifest_sha256"] = charter.content_sha256(forged)
    with pytest.raises(InfrastructureError, match="externally "
                       "supplied"):
        p0_execution.admit_p0_execution(
            execution_manifest=forged,
            expected_manifest_sha256=manifest["manifest_sha256"],
            prepared_environment=live_env,
            expected_head_sha256=head,
            question="q", motivating_evidence="m",
            run_dir=run_dir, ledger_path=ledger_copy,
            _live_environment=live_env)
    # a prepared environment that does not bind refuses
    with pytest.raises(InfrastructureError, match="prepared "
                       "environment"):
        p0_execution.admit_p0_execution(
            execution_manifest=manifest,
            expected_manifest_sha256=manifest["manifest_sha256"],
            prepared_environment=_env_manifest(),
            expected_head_sha256=head,
            question="q", motivating_evidence="m",
            run_dir=run_dir, ledger_path=ledger_copy,
            _live_environment=live_env)
    # a run root that diverges from the execution root refuses
    with pytest.raises(InfrastructureError, match="resolved run "
                       "root"):
        p0_execution.admit_p0_execution(
            execution_manifest=manifest,
            expected_manifest_sha256=manifest["manifest_sha256"],
            prepared_environment=live_env,
            expected_head_sha256=head,
            question="q", motivating_evidence="m",
            run_dir=tmp_path / "wrong-root",
            ledger_path=ledger_copy,
            _live_environment=live_env)
    # a live environment that does not attest refuses (step 4
    # precedes the chain-head check, so the stale head is
    # unreached; the ESTABLISHED prepared-vs-live attestation
    # helper raises)
    with pytest.raises(InfrastructureError,
                       match="differs from the frozen snapshot"):
        p0_execution.admit_p0_execution(
            execution_manifest=manifest,
            expected_manifest_sha256=manifest["manifest_sha256"],
            prepared_environment=live_env,
            expected_head_sha256=head,
            question="q", motivating_evidence="m",
            run_dir=run_dir, ledger_path=ledger_copy,
            _live_environment=_env_manifest())
    # the REAL ledger is untouched
    assert ledger.ledger_head() == head


def test_p0_runner_cpu_boundaries(monkeypatch, tmp_path):
    """The P0 runner rev2 CPU boundaries: the frozen eval
    realization (CRN continuity); the exactly-once prelaunch; the
    cadence callback (save-request at intermediates only, resume
    skip-list honored); the RESUMABLE interruption record
    (cumulative, no ledger write, checkpoints retained); the
    LoRA-key/dtype assertion inputs."""
    from tasks.routing import p0_execution
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    # the executed realization: 90 slot-0 seeds, frozen pin, CRN
    # continuity, and the pin BOUND inside the identity (363_s F2)
    seeds = p0_execution.p0_eval_seed_realization()
    assert len(seeds) == 90
    assert seeds[0][1] == 1176822329
    identity = p0_execution.load_p0_execution_identity(
        expected_sha256=p0_execution.P0_EXECUTION_IDENTITY_SHA256)
    realization = identity["evaluation"][
        "checkpoint_eval_realization"]
    assert realization["realization_sha256"] == \
        p0_execution.P0_EVAL_REALIZATION_SHA256
    assert "num_return_sequences" in realization["rule"]
    monkeypatch.setattr(p0_execution,
                        "P0_EVAL_REALIZATION_SHA256", "0" * 64)
    with pytest.raises(InfrastructureError, match="frozen pin"):
        p0_execution.p0_eval_seed_realization()
    monkeypatch.undo()
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    # exactly-once prelaunch persistence (four files, byte copies)
    live_env = json.loads(Path(
        "runs/routing-dev/beta-smoke-v1/execute_env_manifest.json"
    ).read_text("utf-8"))
    run_dir = tmp_path / "p0-v1"
    manifest = p0_execution.prepare_p0_launch(
        run_dir=run_dir, _environment_builder=lambda: live_env)
    assert p0_execution.validate_p0_execution_manifest(
        manifest)["manifest_sha256"] == manifest["manifest_sha256"]
    prelaunch = run_dir / "prelaunch"
    assert sorted(p.name for p in prelaunch.iterdir()) == [
        "env_manifest.json", "execution_identity.json",
        "launch_freeze.json", "p0_launch.json"]
    assert (prelaunch / "execution_identity.json").read_bytes() \
        == Path(p0_execution.EXECUTION_IDENTITY_PATH).read_bytes()
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_execution.prepare_p0_launch(
            run_dir=run_dir, _environment_builder=lambda: live_env)
    # the cadence callback: deadline BEFORE the step; consumption
    # at the optimizer; save requests at REMAINING intermediates
    # only; the cadence event fires at on_save via the HF binding
    from types import SimpleNamespace

    from tasks.routing import checkpoint as ckpt_module
    accountant = ckpt_module.GroupAccountant()
    instrumentation = p0_smoke._EpochInstrumentation()
    context = {"deadline": 0.0, "accountant": accountant,
               "instrumentation": instrumentation}
    expired = p0_execution._make_p0_callback(
        context, [0, 628, 1256, 6123])
    with pytest.raises(InfrastructureError,
                       match="deadline exceeded"):
        expired.on_step_begin(None, None, None)
    import time as _time
    context["deadline"] = _time.monotonic() + 3600.0
    callback = p0_execution._make_p0_callback(
        context, [0, 628, 1256, 6123])
    with pytest.raises(InfrastructureError,
                       match="never generated"):
        callback.on_optimizer_step(None, None, None)

    def _state(step):
        return SimpleNamespace(global_step=step)

    def _control():
        return SimpleNamespace(should_save=False)

    instrumentation.start_epoch()
    control = _control()
    callback.on_step_end(None, _state(627), control)
    assert control.should_save is False
    control = _control()
    callback.on_step_end(None, _state(628), control)
    assert control.should_save is True
    control = _control()
    callback.on_step_end(None, _state(6123), control)
    assert control.should_save is False  # final != intermediate
    # a RESUMED session skips already-completed intermediates
    resumed = p0_execution._make_p0_callback(
        context, [0, 628, 1256, 6123], already_completed=(628,))
    control = _control()
    resumed.on_step_end(None, _state(628), control)
    assert control.should_save is False
    # on_save fires the cadence event bound to the HF checkpoint
    fired = []
    monkeypatch.setattr(
        p0_execution, "_p0_cadence_event",
        lambda ctx, step, hf_dir: fired.append((step,
                                                hf_dir.name)))
    hf_root = tmp_path / "hf"
    (hf_root / "checkpoint-628").mkdir(parents=True)
    callback.on_save(SimpleNamespace(output_dir=str(hf_root)),
                     _state(628), _control())
    assert fired == [(628, "checkpoint-628")]
    with pytest.raises(InfrastructureError, match="absent"):
        callback.on_save(
            SimpleNamespace(output_dir=str(hf_root)),
            _state(1256), _control())
    monkeypatch.undo()
    monkeypatch.setitem(p0_val.VAL_CONFIG["lineage"],
                        "parent_entry_sha256", PRISTINE_VAL_LINEAGE)
    monkeypatch.setattr(p0_val, "VAL_CONFIG_SHA256",
                        PRISTINE_VAL_CONFIG_SHA256)
    # 365_s: the HASH-CHAINED session log — interruptions seal
    # raws, RETAIN checkpoints, close the session; cumulative
    # accounting is validated; tampering and NaN refuse; a killed
    # session gets a conservative inferred end
    abort_dir = tmp_path / "interrupted"
    sealed = abort_dir / "sealed"
    sealed.mkdir(parents=True)
    (sealed / "training_trace_s1.jsonl").write_text(
        '{"row": 1}\n', encoding="utf-8")
    bundle = abort_dir / "checkpoint_bundle_upd628"
    bundle.mkdir()
    (bundle / "adapter_state.safetensors").write_bytes(b"resume")
    import time as _time2
    p0_execution._append_session_entry(abort_dir, {
        "kind": "session_start", "session_index": 1,
        "mode": "fresh", "start_group_index": 0,
        "resume_update_index": None,
        "wall_start_utc": _time2.time()})
    p0_execution._record_resumable_interruption(
        abort_dir, 1, 100.0, RuntimeError("gpu fell over"))
    assert not (sealed / "training_trace_s1.jsonl").exists()
    assert (sealed / "training_trace_s1.jsonl.gz").exists()
    assert bundle.exists()
    state = p0_execution._session_state(abort_dir)
    assert state["cumulative_elapsed_seconds"] == 100.0
    assert state["unclosed_session_index"] is None
    # a killed session (start, no end) closes with an INFERRED
    # conservative wall-clock elapsed at the next entry point
    p0_execution._append_session_entry(abort_dir, {
        "kind": "session_start", "session_index": 2,
        "mode": "resume", "start_group_index": 628,
        "resume_update_index": 628,
        "wall_start_utc": _time2.time() - 50.0})
    state = p0_execution._session_state(abort_dir)
    assert state["unclosed_session_index"] == 2
    state = p0_execution._close_killed_session(abort_dir, state)
    assert state["unclosed_session_index"] is None
    assert state["cumulative_elapsed_seconds"] >= 150.0
    # a NaN elapsed can never enter the chain
    with pytest.raises(InfrastructureError,
                       match="non-negative finite"):
        p0_execution._append_session_entry(abort_dir, {
            "kind": "session_end", "session_index": 3,
            "elapsed_seconds": float("nan"), "status": "x"})
    # a REWRITTEN line breaks the chain
    log = abort_dir / "sessions.jsonl"
    lines = log.read_text("utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["elapsed_seconds"] = 0.0
    tampered_line = json.dumps(tampered, sort_keys=True)
    log.write_text("\n".join([tampered_line] + lines[1:]) + "\n",
                   encoding="utf-8")
    with pytest.raises(InfrastructureError, match="chain"):
        p0_execution._load_sessions(abort_dir)
    # 365_s F2: cadence records are atomic, once-only, contiguous
    cadence_dir = tmp_path / "cadence-run"
    cadence_dir.mkdir()
    record = {"update_index": 0, "bundle_seconds": 1.0,
              "eval_seconds": 2.0,
              "checkpoint_proof": {"checkpoint_sha256": "a" * 64,
                                   "state_artifact_sha256": {},
                                   "counters": {}},
              "hf_checkpoint_dir": None}
    p0_execution._write_cadence_record(cadence_dir, record)
    with pytest.raises(InfrastructureError, match="exactly once"):
        p0_execution._write_cadence_record(cadence_dir, record)
    loaded = p0_execution._load_cadence_records(
        cadence_dir, [0, 628, 1256])
    assert list(loaded) == ["0"]
    gap = {**record, "update_index": 1256}
    p0_execution._write_cadence_record(cadence_dir, gap)
    with pytest.raises(InfrastructureError, match="contiguous"):
        p0_execution._load_cadence_records(
            cadence_dir, [0, 628, 1256])
    # excluded evidence is never overwritten
    (cadence_dir / "sealed").mkdir()
    (cadence_dir / "sealed" / "eval_upd628.jsonl.gz"
     ).write_bytes(b"partial")
    p0_execution._exclude_partial_evidence(
        cadence_dir, "eval_upd628.jsonl.gz", 2)
    assert (cadence_dir / "excluded"
            / "s2_eval_upd628.jsonl.gz").read_bytes() == b"partial"
    assert "sentinel-block" in " ".join(
        p0_execution.P0_RUNNER_OUTSTANDING)
