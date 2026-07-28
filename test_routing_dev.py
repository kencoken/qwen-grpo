"""Routing development-track infrastructure battery (211_f §15 step 3,
hardened per 214_s/216_s/218_s/220_s): namespaces + disjointness,
strict natural mixture, driver-inclusive execution digest, the
support-launch manifest consumed by an ADMITTED materialization, the
tracked support runner end-to-end (prepare → admit → materialize →
lock → disclose/select/bind → closeout), enforced first-probe
binding, rederived cohorts and comparators, authenticated telemetry
with the complete equal-cell estimand, the head-bound ledger with
same-entry admission, and the v1 checkpoint/resume contract."""

import hashlib
import json
import shutil

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
from tasks.routing import ledger, support_run, telemetry

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
        _runtime_factory=lambda: dev_fake_rt(tmp, sabotage_w3=True))
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
    state = ledger.envelope_state(entries)
    assert state["consumed_gpu_hours"] == \
        entries[1]["budget_consumed_gpu_hours"]
    assert state["open_launches"] == []
    # outputs persisted once
    for name in ("disclosure.json", "c_fixed_dev.json",
                 "probe_cohort.json", "run_record.json"):
        assert (fx["run_dir"] / name).exists()
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
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        support_run.execute_support_run(
            run_dir=fx["run_dir"],
            expected_manifest_sha256=fx["manifest"]["manifest_sha256"],
            expected_head_sha256=None, question="q",
            motivating_evidence="m", ledger_path=fx["ledger_path"],
            _runtime_factory=lambda: None)


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
    other = ledger.admit_and_append_launch(
        {"kind": "support_materialization", "question": "q",
         "motivating_evidence": "m",
         "freeze": {"support_launch_sha256": "ab" * 32},
         "parent": None, "budget_allocated_gpu_hours": 1.0,
         "outcome_informed": False,
         "cohort_selection": "outcome_blind"},
        None, empty_ledger,
        launch_manifest={"manifest_sha256": "ab" * 32,
                         "budget_gpu_hours": 1.0})
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
    entry = {"kind": "support_materialization", "question": "q",
             "motivating_evidence": "m",
             "freeze": {"support_launch_sha256": "ab" * 32},
             "parent": None, "budget_allocated_gpu_hours": 2.0,
             "outcome_informed": False,
             "cohort_selection": "outcome_blind"}
    manifest = {"manifest_sha256": "ab" * 32, "budget_gpu_hours": 2.0}
    # without the manifest: refuse
    with pytest.raises(InfrastructureError, match="admitted WITH"):
        ledger.admit_and_append_launch(entry, None, path)
    # freeze naming a different hash: refuse
    with pytest.raises(InfrastructureError, match="exact "
                       "support-launch manifest"):
        ledger.admit_and_append_launch(
            {**entry, "freeze": {"support_launch_sha256": "cd" * 32}},
            None, path, launch_manifest=manifest)
    # budget mismatch: refuse
    with pytest.raises(InfrastructureError, match="differs from the "
                       "manifest budget"):
        ledger.admit_and_append_launch(
            {**entry, "budget_allocated_gpu_hours": 3.0}, None, path,
            launch_manifest={**manifest, "budget_gpu_hours": 2.0})
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
            "rounding": "ceil_to_whole_gpu_hours"}


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
    with pytest.raises(InfrastructureError, match="outcome_blind"):
        ledger.admit_and_append_launch(
            _entry(kind="grouped_probe"), None, path)
    with pytest.raises(InfrastructureError, match="admit_and_append"):
        ledger.append_ledger_entry(_entry(), None, path)
    with pytest.raises(InfrastructureError, match="finite"):
        ledger.admit_and_append_launch(
            _entry(budget_allocated_gpu_hours=float("nan")), None,
            path)


def test_reserve_requires_numerical_basis_and_exact_rounding(tmp_path):
    path = tmp_path / "ledger.md"
    incomplete = {"status": "provisional", "r_cycle_gpu_hours": 6.0}
    with pytest.raises(InfrastructureError, match="numerical basis"):
        ledger.append_ledger_entry(
            _note(kind="reserve_update", reserve=incomplete), None,
            path)
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
    ledger.append_ledger_entry(
        _note(kind="reserve_update", reserve=_reserve()), None, path)


def test_launch_closeout_linkage_and_envelope(tmp_path):
    path = tmp_path / "ledger.md"
    reserve_entry = ledger.append_ledger_entry(
        _note(kind="reserve_update", reserve=_reserve()), None, path)
    launch = ledger.admit_and_append_launch(
        _entry(budget_allocated_gpu_hours=3.0),
        reserve_entry["entry_sha256"], path)
    state = ledger.envelope_state(ledger.read_ledger(path))
    assert state["consumed_gpu_hours"] == pytest.approx(3.0)
    closeout = ledger.append_ledger_entry(
        _note(kind="closeout",
              closes_entry_sha256=launch["entry_sha256"],
              budget_consumed_gpu_hours=1.25),
        launch["entry_sha256"], path)
    state = ledger.envelope_state(ledger.read_ledger(path))
    assert state["consumed_gpu_hours"] == pytest.approx(1.25)
    assert state["open_launches"] == []
    with pytest.raises(InfrastructureError, match="already closed"):
        ledger.append_ledger_entry(
            _note(kind="closeout",
                  closes_entry_sha256=launch["entry_sha256"],
                  budget_consumed_gpu_hours=1.0),
            closeout["entry_sha256"], path)
    with pytest.raises(InfrastructureError, match="not a recorded "
                       "launch"):
        ledger.append_ledger_entry(
            _note(kind="closeout", closes_entry_sha256="0" * 64,
                  budget_consumed_gpu_hours=1.0),
            closeout["entry_sha256"], path)


def test_admission_verifies_the_persisted_ledger_itself(tmp_path):
    path = tmp_path / "ledger.md"
    manifest = {"manifest_sha256": "ab" * 32, "budget_gpu_hours": 4.0}
    support_entry = _entry(
        kind="support_materialization",
        cohort_selection="outcome_blind",
        freeze={"support_launch_sha256": "ab" * 32},
        budget_allocated_gpu_hours=4.0)
    with pytest.raises(InfrastructureError, match="FIRST support"):
        ledger.admit_and_append_launch(
            _entry(kind="training_run"), None, path)
    support = ledger.admit_and_append_launch(
        support_entry, None, path, launch_manifest=manifest)
    entries = ledger.read_ledger(path)
    assert entries[-1]["kind"] == "support_materialization"
    assert entries[-1]["budget_allocated_gpu_hours"] == 4.0
    with pytest.raises(InfrastructureError, match="prior support"):
        ledger.admit_and_append_launch(
            support_entry, support["entry_sha256"], path,
            launch_manifest=manifest)
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.admit_and_append_launch(
            support_entry, None, path, launch_manifest=manifest)
    reserve_entry = ledger.append_ledger_entry(
        _note(kind="reserve_update", reserve=_reserve()),
        support["entry_sha256"], path)
    head = reserve_entry["entry_sha256"]
    probe = ledger.admit_and_append_launch(
        _entry(kind="grouped_probe",
               cohort_selection="outcome_blind",
               budget_allocated_gpu_hours=3.0), head, path)
    head = probe["entry_sha256"]
    with pytest.raises(InfrastructureError, match="inadmissible"):
        ledger.admit_and_append_launch(
            _entry(kind="training_run",
                   budget_allocated_gpu_hours=50.0), head, path)
    with pytest.raises(InfrastructureError, match="exceeds the "
                       "reserved"):
        ledger.admit_and_append_launch(
            _entry(kind="cycle_closure",
                   budget_allocated_gpu_hours=7.5), head, path)
    closure = ledger.admit_and_append_launch(
        _entry(kind="cycle_closure", budget_allocated_gpu_hours=6.5),
        head, path)
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
