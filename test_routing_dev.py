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
from tasks.routing import extension_run, ledger, support_run, telemetry

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
    entry = {"kind": "engineering_smoke", "question": "q",
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
    # 228_s F2: final reserves refuse UNCONDITIONALLY
    with pytest.raises(InfrastructureError, match="not yet enabled"):
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
        ledger.admit_and_append_launch(
            _entry(kind="training_run"), None, empty)
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
            _entry(kind="training_run",
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
