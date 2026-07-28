"""Routing development-track infrastructure battery (211_f §15 step 3,
hardened per 214_s and 216_s): namespaces + disjointness, strict
natural mixture, driver-inclusive execution digest, the pre-launch
execution lock consumed by materialization and extended by the
surface lock, enforced probe rules, rederived c_fixed_dev,
authenticated + membership-gated telemetry with the complete
equal-cell estimand, the head-bound append-only ledger with derived
admission, and the v1 checkpoint/resume contract with mandatory
bundle verification."""

import hashlib
import json

import pytest

from tasks.conductor import program
from tasks.conductor.cache import WorkerCompletionCache
from tasks.conductor.pool_runtime import FourWorkerRuntime
from tasks.conductor.profiles import DEFAULT_PROFILE, canonical_json
from tasks.conductor.stage1_replay import (
    family_correct_variants, pair_table_from_surface,
)
from tasks.conductor.types import (
    CELL_IDS, NAMESPACES, RENDERER_IDS, InfrastructureError,
)
from tasks.routing import charter, checkpoint, cohorts, dev_support
from tasks.routing import ledger, telemetry

from test_conductor_executor import perfect_worker
from test_conductor_pool_runtime import FakeFourPool, profile_with

DEV_COHORT = {cell: [0] for cell in CELL_IDS}
DEV_RENDERERS = RENDERER_IDS


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
    assert len(labels) == 1  # cohort B (24-47) is one intact block


# --- charter: natural mixture, digest, freezes ---------------------------------

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
        "tasks/routing/charter.py")
    assert digest["driver"] == "tasks/routing/charter.py"
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
    with pytest.raises(InfrastructureError, match="positive budget"):
        charter.lightweight_freeze({**record, "budget_gpu_hours": 0})


def test_claim_run_root_refuses_reuse(tmp_path):
    assert charter.claim_run_root("probe-1", base=tmp_path).is_dir()
    with pytest.raises(InfrastructureError, match="never overwrite"):
        charter.claim_run_root("probe-1", base=tmp_path)
    with pytest.raises(InfrastructureError, match="bad run root"):
        charter.claim_run_root("a/b", base=tmp_path)


# --- support-launch manifest and dev surfaces (211_f §4, 218_s F1) ---------------

def _env_manifest(**extra):
    """A CANONICAL stage1-environment-v2 manifest: the stage1
    validator requires the current source identity and the exact
    self-hash convention, so a fictional environment cannot pass."""
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


DRIVER = "tasks/routing/dev_support.py"
SEARCH_CAP = 12


def _probe_rule():
    return cohorts.freeze_reprobe_rule(
        namespace="routing_dev", prefix_length_per_cell=1,
        renderers=RENDERER_IDS, visibility="private", group_size=8,
        groups_per_observation=2)


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


def _materialize(tmp_path, sabotage_w3=True, tag="routing-dev-test-v1"):
    rt = dev_fake_rt(tmp_path, sabotage_w3=sabotage_w3)
    declaration = dev_support.build_dev_declaration(
        rt, tag=tag, namespace="routing_dev", cohort=DEV_COHORT,
        renderers=DEV_RENDERERS, visibility="private")
    env = _env_manifest()
    launch = dev_support.build_support_launch_manifest(
        declaration=declaration, frozen_probe_rule=_probe_rule(),
        search_cap=SEARCH_CAP, budget_gpu_hours=1.0, driver=DRIVER,
        environment_manifest=env)
    out = tmp_path / "surface"
    dev_support.materialize_dev_support(
        rt, declaration, out, launch_manifest=launch,
        environment_manifest=env,
        expected_manifest_sha256=launch["manifest_sha256"])
    rt.close()
    return out


@pytest.fixture(scope="module")
def locked_surface(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("dev-surface")
    out = _materialize(tmp_path)
    lock = dev_support.build_surface_lock(out)
    loaded = dev_support.load_dev_surface(
        out, expected_lock_sha256=lock["lock_sha256"])
    return out, lock, loaded


def test_support_launch_manifest_binds_all_prelaunch_inputs(tmp_path):
    rt = dev_fake_rt(tmp_path)
    declaration = dev_support.build_dev_declaration(
        rt, tag="t", namespace="routing_dev", cohort=DEV_COHORT,
        renderers=DEV_RENDERERS, visibility="private")
    rt.close()
    env = _env_manifest()
    launch = dev_support.build_support_launch_manifest(
        declaration=declaration, frozen_probe_rule=_probe_rule(),
        search_cap=SEARCH_CAP, budget_gpu_hours=1.0, driver=DRIVER,
        environment_manifest=env)
    assert launch["probe_rule_sha256"] == _probe_rule()["rule_sha256"]
    assert launch["declaration_sha256"] == \
        charter.content_sha256(dict(declaration))
    assert dev_support.validate_support_launch_manifest(
        launch, declaration)
    # 218_s F1 reproduction: a FICTIONAL environment manifest (self-
    # consistent but not the canonical stage1 kind / source identity)
    # refuses
    fake_env = {"manifest": "test-environment",
                "git_commit": "deadbeef"}
    fake_env["execution_manifest_sha256"] = hashlib.sha256(
        canonical_json(fake_env).encode("utf-8")).hexdigest()
    with pytest.raises(InfrastructureError, match="not a stage1"):
        dev_support.build_support_launch_manifest(
            declaration=declaration, frozen_probe_rule=_probe_rule(),
            search_cap=SEARCH_CAP, budget_gpu_hours=1.0,
            driver=DRIVER, environment_manifest=fake_env)
    wrong_source = _env_manifest(stage1_source_sha256="0" * 64)
    with pytest.raises(InfrastructureError, match="different source "
                       "identity"):
        dev_support.build_support_launch_manifest(
            declaration=declaration, frozen_probe_rule=_probe_rule(),
            search_cap=SEARCH_CAP, budget_gpu_hours=1.0,
            driver=DRIVER, environment_manifest=wrong_source)
    # search cap must cover the declared screen; budgets must be
    # finite (218_s F2)
    with pytest.raises(InfrastructureError, match="search cap"):
        dev_support.build_support_launch_manifest(
            declaration=declaration, frozen_probe_rule=_probe_rule(),
            search_cap=3, budget_gpu_hours=1.0, driver=DRIVER,
            environment_manifest=env)
    with pytest.raises(InfrastructureError, match="finite"):
        dev_support.build_support_launch_manifest(
            declaration=declaration, frozen_probe_rule=_probe_rule(),
            search_cap=SEARCH_CAP, budget_gpu_hours=float("nan"),
            driver=DRIVER, environment_manifest=env)
    with pytest.raises(InfrastructureError, match="actual training "
                       "driver"):
        dev_support.build_support_launch_manifest(
            declaration=declaration, frozen_probe_rule=_probe_rule(),
            search_cap=SEARCH_CAP, budget_gpu_hours=1.0,
            driver="train.py", environment_manifest=env)


def test_materialization_consumes_the_frozen_manifest(tmp_path):
    rt = dev_fake_rt(tmp_path)
    declaration = dev_support.build_dev_declaration(
        rt, tag="t", namespace="routing_dev", cohort=DEV_COHORT,
        renderers=DEV_RENDERERS, visibility="private")
    env = _env_manifest()
    launch = dev_support.build_support_launch_manifest(
        declaration=declaration, frozen_probe_rule=_probe_rule(),
        search_cap=SEARCH_CAP, budget_gpu_hours=1.0, driver=DRIVER,
        environment_manifest=env)
    # not the externally frozen hash
    with pytest.raises(InfrastructureError, match="externally frozen"):
        dev_support.materialize_dev_support(
            rt, declaration, tmp_path / "surface",
            launch_manifest=launch, environment_manifest=env,
            expected_manifest_sha256="0" * 64)
    # a tampered SOURCE identity refuses at the live recompute
    bad = {k: v for k, v in launch.items() if k != "manifest_sha256"}
    bad["routing_source_sha256"] = "1" * 64
    bad["manifest_sha256"] = charter.content_sha256(bad)
    with pytest.raises(InfrastructureError, match="does not recompute"):
        dev_support.materialize_dev_support(
            rt, declaration, tmp_path / "surface",
            launch_manifest=bad, environment_manifest=env,
            expected_manifest_sha256=bad["manifest_sha256"])
    # a different declaration than the bound one refuses
    other = dict(declaration, support="other-tag")
    with pytest.raises(InfrastructureError, match="different "
                       "declaration"):
        dev_support.materialize_dev_support(
            rt, other, tmp_path / "surface", launch_manifest=launch,
            environment_manifest=env,
            expected_manifest_sha256=launch["manifest_sha256"])
    rt.close()


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


def test_declaration_binds_the_execution_identity(tmp_path):
    rt = dev_fake_rt(tmp_path)
    declaration = dev_support.build_dev_declaration(
        rt, tag="t", namespace="routing_dev", cohort=DEV_COHORT,
        renderers=DEV_RENDERERS, visibility="private")
    assert declaration["runtime_profile_fingerprint"] == \
        rt.runtime_profile_fingerprint
    tampered = dict(declaration,
                    request_contract="worker-blocks-task-first-v0")
    env = _env_manifest()
    launch = dev_support.build_support_launch_manifest(
        declaration=tampered, frozen_probe_rule=_probe_rule(),
        search_cap=SEARCH_CAP, budget_gpu_hours=1.0, driver=DRIVER,
        environment_manifest=env)
    with pytest.raises(InfrastructureError, match="request_contract"):
        dev_support.materialize_dev_support(
            rt, tampered, tmp_path / "surface", launch_manifest=launch,
            environment_manifest=env,
            expected_manifest_sha256=launch["manifest_sha256"])
    rt.close()


def test_dev_surface_roundtrip_under_its_lock(locked_surface):
    out, lock, loaded = locked_surface
    surface = loaded["surface"]
    assert len(surface) == 108 * len(DEV_RENDERERS)
    assert set(surface.values()) <= {0.5, 1.0}
    assert loaded["lock"]["support_launch_sha256"]
    assert (out / "env_manifest.json").exists()
    cell_of = {obs["observation_id"]: obs["cell_id"]
               for obs in loaded["observations"]}
    table = pair_table_from_surface(surface, cell_of)
    assert {entry["direction"] for entry in table.values()} == {2}


def test_surface_lock_is_required_and_exact(locked_surface, tmp_path):
    out, lock, _ = locked_surface
    with pytest.raises(InfrastructureError, match="externally frozen"):
        dev_support.load_dev_surface(out, expected_lock_sha256="0" * 64)
    with pytest.raises(InfrastructureError, match="no surface lock"):
        dev_support.load_dev_surface(
            tmp_path, expected_lock_sha256=lock["lock_sha256"])
    with pytest.raises(InfrastructureError, match="locked exactly "
                       "once"):
        dev_support.build_surface_lock(out)


def test_surface_lock_detects_tampered_bytes(tmp_path):
    out = _materialize(tmp_path, sabotage_w3=False, tag="t2")
    lock = dev_support.build_surface_lock(out)
    payoffs = out / "payoffs.jsonl"
    rows = payoffs.read_text().splitlines()
    payoffs.write_text("\n".join(rows[:-1]) + "\n")
    with pytest.raises(InfrastructureError, match="bytes on disk"):
        dev_support.load_dev_surface(
            out, expected_lock_sha256=lock["lock_sha256"])


def test_direction_yields_disclose_every_observation(locked_surface):
    _, _, loaded = locked_surface
    yields = dev_support.direction_yields(loaded["surface"],
                                          loaded["observations"])
    assert len(yields["per_observation"]) == len(loaded["observations"])
    for cell in ("code_atomic", "math_code", "fork_join"):
        assert yields["per_cell"][cell]["w2_favoured"] == 3
    for cell in ("lookup_atomic", "lookup_math", "math_atomic"):
        assert yields["per_cell"][cell]["no_pair"] == 3


def test_c_fixed_dev_selection_verification_and_forgery(locked_surface):
    _, lock, loaded = locked_surface
    record = dev_support.select_c_fixed_dev(loaded)
    assert record["c_fixed_dev"] == 2
    assert record["candidate_scores"] == {"2": 1.0, "3": 0.5}
    assert record["surface_lock_sha256"] == lock["lock_sha256"]
    assert dev_support.verify_c_fixed_for(loaded, record) == 2
    # tampered selection: rehash fails
    with pytest.raises(InfrastructureError, match="rehash"):
        dev_support.verify_c_fixed_for(
            loaded, dict(record, c_fixed_dev=3))
    # fully forged but self-consistent record: rederivation fails
    forged = {k: v for k, v in record.items() if k != "record_sha256"}
    forged["candidate_scores"] = {"2": 0.5, "3": 1.0}
    forged["c_fixed_dev"] = 3
    forged["record_sha256"] = charter.content_sha256(forged)
    with pytest.raises(InfrastructureError, match="rederive"):
        dev_support.verify_c_fixed_for(loaded, forged)
    # a record bound to a different lock refuses
    foreign = {k: v for k, v in record.items() if k != "record_sha256"}
    foreign["surface_lock_sha256"] = "0" * 64
    foreign["record_sha256"] = charter.content_sha256(foreign)
    with pytest.raises(InfrastructureError, match="different surface "
                       "lock"):
        dev_support.verify_c_fixed_for(loaded, foreign)


# --- probe rules ---------------------------------------------------------------

def test_first_probe_rule_enforces_the_signed_shape():
    frozen = cohorts.freeze_first_probe_rule(
        prefix_length_per_cell=6, groups_per_observation=2)
    rule = cohorts.validate_probe_rule(frozen)
    assert rule["namespace"] == "routing_dev"
    assert rule["group_size"] == 8
    assert list(rule["renderers"]) == list(RENDERER_IDS)
    with pytest.raises(InfrastructureError, match="divisible by 6"):
        cohorts.freeze_first_probe_rule(
            prefix_length_per_cell=4, groups_per_observation=2)
    bad = dict(frozen["rule"], group_size=1)
    with pytest.raises(InfrastructureError, match="group size"):
        cohorts.validate_probe_rule(
            {"rule": bad, "rule_sha256": charter.content_sha256(bad)})
    bad = dict(frozen["rule"], namespace="routing_dev_val")
    with pytest.raises(InfrastructureError, match="first probe runs"):
        cohorts.validate_probe_rule(
            {"rule": bad, "rule_sha256": charter.content_sha256(bad)})


def test_reprobe_rule_stays_flexible_but_outcome_blind():
    frozen = cohorts.freeze_reprobe_rule(
        namespace="routing_dev", prefix_length_per_cell=1,
        renderers=RENDERER_IDS, visibility="private", group_size=16,
        groups_per_observation=1)
    assert cohorts.validate_probe_rule(frozen)["group_size"] == 16
    smuggled = dict(frozen["rule"], preferred_direction="w2_favoured")
    with pytest.raises(InfrastructureError, match="closed schema"):
        cohorts.validate_probe_rule(
            {"rule": smuggled,
             "rule_sha256": charter.content_sha256(smuggled)})
    tampered = {"rule": dict(frozen["rule"]), "rule_sha256": "0" * 64}
    with pytest.raises(InfrastructureError, match="rehash"):
        cohorts.validate_probe_rule(tampered)


def test_probe_rule_application_fails_closed_on_under_coverage(
        locked_surface):
    out, lock, _ = locked_surface
    frozen = cohorts.freeze_first_probe_rule(
        prefix_length_per_cell=6, groups_per_observation=2)
    with pytest.raises(InfrastructureError, match="under-covers"):
        cohorts.bind_probe_cohort(frozen, out, lock["lock_sha256"])


def test_probe_cohort_binds_the_surface_lock(locked_surface):
    out, lock, _ = locked_surface
    frozen = cohorts.freeze_reprobe_rule(
        namespace="routing_dev", prefix_length_per_cell=1,
        renderers=RENDERER_IDS, visibility="private", group_size=8,
        groups_per_observation=2)
    bound = cohorts.bind_probe_cohort(frozen, out,
                                      lock["lock_sha256"])
    assert bound["surface_lock_sha256"] == lock["lock_sha256"]
    assert len(bound["observation_ids"]) == 6 * len(RENDERER_IDS)
    with pytest.raises(InfrastructureError, match="externally frozen"):
        cohorts.bind_probe_cohort(frozen, out, "0" * 64)


# --- telemetry (211_f §7; 216_s F3/F4) -------------------------------------------

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
def telemetry_context(locked_surface):
    _, _, loaded = locked_surface
    record = dev_support.select_c_fixed_dev(loaded)
    return loaded, record


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
        _completion(True, [2], surface[(oid, (2,))]),   # winner (1.0)
        _completion(True, [3], surface[(oid, (3,))]),   # w3 (0.5)
        _completion(True, [0], surface[(oid, (0,))]),   # wrong family
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
    assert stats["zero_variance_level"] is None


def test_group_stats_authenticates_and_gates_membership(
        telemetry_context):
    loaded, record = telemetry_context
    oid = _code_obs(loaded)
    # reward disagreeing with the authenticated surface refuses
    with pytest.raises(InfrastructureError, match="authenticated "
                       "payoff"):
        telemetry.group_stats(
            {"observation_id": oid,
             "completions": [_completion(True, [2], 0.5)]},
            loaded=loaded, c_fixed_record=record)
    # invalid completions must carry reward 0
    with pytest.raises(InfrastructureError, match="scores malformed"):
        telemetry.group_stats(
            {"observation_id": oid,
             "completions": [_completion(False, None, 0.5)]},
            loaded=loaded, c_fixed_record=record)
    # valid-but-not-parseable is a contradiction
    with pytest.raises(InfrastructureError, match="contradiction"):
        telemetry.group_stats(
            {"observation_id": oid,
             "completions": [_completion(True, [2], 1.0,
                                         parseable=False)]},
            loaded=loaded, c_fixed_record=record)
    # exact action schema
    with pytest.raises(InfrastructureError, match="action schema"):
        telemetry.group_stats(
            {"observation_id": oid,
             "completions": [_completion(True, [2, 2], 1.0)]},
            loaded=loaded, c_fixed_record=record)
    # 216_s F3: a foreign observation refuses BEFORE any scoring,
    # even with all-invalid completions
    foreign = ("code_atomic:routing_dev:01999:abcdef01:"
               "resource_first:private")
    with pytest.raises(InfrastructureError, match="not an observation "
                       "of the locked support"):
        telemetry.group_stats(
            {"observation_id": foreign,
             "completions": [_completion(False, None, 0.0)]},
            loaded=loaded, c_fixed_record=record)


def test_group_stats_zero_variance_and_tied_pairs(telemetry_context):
    loaded, record = telemetry_context
    # math_code observations are w2-favoured here; a lookup cell has
    # no pair; ties need a tied surface — synthesize by using the
    # no-pair cell for zero-variance and checking tied logic via
    # derive_pair_entry directly
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
    assert stats["direct_contrast"] is False


def test_derive_pair_entry_reports_ties():
    obs = "code_atomic:routing_dev:00000:abcdef01:resource_first:private"
    tied_surface = {(obs, (0,)): 0.5, (obs, (1,)): 0.5,
                    (obs, (2,)): 1.0, (obs, (3,)): 1.0}
    entry = telemetry.derive_pair_entry(obs, "code_atomic",
                                        tied_surface)
    assert entry["distinct_payoff"] is False
    assert entry["direction"] is None
    with pytest.raises(InfrastructureError, match="variant row "
                       "missing"):
        telemetry.derive_pair_entry(obs, "code_atomic",
                                    {(obs, (2,)): 1.0})


def test_group_stats_refuses_off_ladder_reward(telemetry_context):
    loaded, record = telemetry_context
    oid = _code_obs(loaded)
    with pytest.raises(InfrastructureError, match="frozen ladder"):
        telemetry.group_stats(
            {"observation_id": oid,
             "completions": [_completion(True, [2], 0.75)]},
            loaded=loaded, c_fixed_record=record)


def _full_population_groups(loaded, record):
    """One authenticated family-correct group per observation — the
    complete 6×3 crossing the equal-cell estimand requires."""
    surface = loaded["surface"]
    groups = []
    for obs in loaded["observations"]:
        oid = obs["observation_id"]
        assignment = _family_correct(obs["cell_id"])
        reward = surface[(oid, tuple(assignment))]
        group = {"observation_id": oid, "completions": [
            _completion(True, assignment, reward)] * 4}
        groups.append(telemetry.group_stats(group, loaded=loaded,
                                            c_fixed_record=record))
    return groups


def test_aggregate_stratified_full_population(telemetry_context):
    loaded, record = telemetry_context
    groups = _full_population_groups(loaded, record)
    report = telemetry.aggregate_stratified(groups)
    total = report["total"]
    assert total["groups"] == 18
    assert total["valid"]["rate"] == 1.0
    assert total["valid"]["denominator"] == 72
    # frequencies carry denominators (216_s lower severity)
    assert total["worker_frequencies"]["denominator"] == \
        sum(total["worker_frequencies"]["counts"].values())
    # every family-correct w2 choice is the winner on code cells
    assert total["model_acc"]["rate"] == 1.0
    equal_cell = report["equal_cell"]
    assert equal_cell["cells"] == sorted(CELL_IDS)
    # hierarchical eligible-only views with raw totals (216_s F4)
    assert equal_cell["model_acc"]["value"] == 1.0
    assert equal_cell["model_acc"]["cells"] == \
        ["code_atomic", "fork_join", "math_code"]
    assert equal_cell["model_acc"]["denominator"] == 36  # 9 obs x 4
    assert equal_cell["c2_optimal_specialist"]["value"] == 1.0
    key = "code_atomic|resource_first|w2_favoured"
    assert key in report["by_cell_renderer_direction"]


def test_probe_report_requires_the_frozen_design(locked_surface,
                                                 telemetry_context):
    """218_s F3: the report boundary requires exact observation ids,
    multiplicities and group size from the bound cohort + rule — the
    reviewer's extra-authenticated-group reproduction refuses."""
    out, lock, loaded = locked_surface
    _, record = telemetry_context
    frozen = _probe_rule()   # G=8, 2 groups/observation
    bound = cohorts.bind_probe_cohort(frozen, out,
                                      lock["lock_sha256"])
    surface = loaded["surface"]

    def make_group(oid, cell):
        assignment = _family_correct(cell)
        reward = surface[(oid, tuple(assignment))]
        return telemetry.group_stats(
            {"observation_id": oid, "completions":
             [_completion(True, assignment, reward)] * 8},
            loaded=loaded, c_fixed_record=record)

    cell_of = {obs["observation_id"]: obs["cell_id"]
               for obs in loaded["observations"]}
    groups = [make_group(oid, cell_of[oid])
              for oid in bound["observation_ids"]
              for _ in range(2)]
    report = telemetry.probe_report(groups, loaded=loaded,
                                    bound_cohort=bound,
                                    frozen_rule=frozen)
    assert report["design"]["observations"] == 18
    assert report["design"]["group_size"] == 8
    assert report["total"]["groups"] == 36
    # an EXTRA authenticated group refuses (the 218_s reproduction)
    extra_oid = bound["observation_ids"][0]
    with pytest.raises(InfrastructureError, match="multiplicities"):
        telemetry.probe_report(
            groups + [make_group(extra_oid, cell_of[extra_oid])],
            loaded=loaded, bound_cohort=bound, frozen_rule=frozen)
    # a missing group refuses
    with pytest.raises(InfrastructureError, match="multiplicities"):
        telemetry.probe_report(groups[:-1], loaded=loaded,
                               bound_cohort=bound, frozen_rule=frozen)
    # wrong group size refuses
    wrong_g = list(groups)
    oid = bound["observation_ids"][0]
    small = telemetry.group_stats(
        {"observation_id": oid, "completions":
         [_completion(True, _family_correct(cell_of[oid]),
                      surface[(oid,
                               tuple(_family_correct(cell_of[oid])))])]
         * 4},
        loaded=loaded, c_fixed_record=record)
    wrong_g[0] = small
    with pytest.raises(InfrastructureError, match="group sizes"):
        telemetry.probe_report(wrong_g, loaded=loaded,
                               bound_cohort=bound, frozen_rule=frozen)
    # a tampered cohort record refuses; a foreign rule refuses
    tampered = dict(bound, observation_ids=bound["observation_ids"][:1])
    with pytest.raises(InfrastructureError, match="rehash"):
        telemetry.probe_report(groups, loaded=loaded,
                               bound_cohort=tampered,
                               frozen_rule=frozen)
    other_rule = cohorts.freeze_reprobe_rule(
        namespace="routing_dev", prefix_length_per_cell=1,
        renderers=RENDERER_IDS, visibility="private", group_size=16,
        groups_per_observation=2)
    with pytest.raises(InfrastructureError, match="different frozen "
                       "rule"):
        telemetry.probe_report(groups, loaded=loaded,
                               bound_cohort=bound,
                               frozen_rule=other_rule)


def test_equal_cell_view_refuses_partial_populations(
        telemetry_context):
    loaded, record = telemetry_context
    groups = _full_population_groups(loaded, record)
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


# --- ledger (211_f §§10, 12; 216_s F2) ---------------------------------------------

def _entry(**overrides):
    entry = {"kind": "engineering_smoke", "question": "q",
             "motivating_evidence": "202_f priors",
             "freeze": {"config_sha256": "ab" * 32},
             "parent": None, "budget_allocated_gpu_hours": 0.5,
             "outcome_informed": False}
    entry.update(overrides)
    return entry


def _reserve(status="provisional", hours=7.0, seconds=4.2):
    # basis: 3000 obs x 2.0 passes x 4.2 s / 3600 = 7.0 h; ceil = 7.0
    return {"status": status, "r_cycle_gpu_hours": hours,
            "assumed_cohort_size": 3000,
            "evaluation_multiplier": 2.0,
            "measured_seconds_per_observation": seconds,
            "rounding": "ceil_to_whole_gpu_hours"}


def _note(**overrides):
    """A bookkeeping (non-launch) entry for chain-mechanics tests."""
    return _entry(kind="cycle_synthesis",
                  budget_allocated_gpu_hours=0.0, **overrides)


def test_ledger_append_requires_the_external_head(tmp_path):
    path = tmp_path / "ledger.md"
    first = ledger.append_ledger_entry(_note(), None, path)
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.append_ledger_entry(_note(), None, path)
    second = ledger.append_ledger_entry(
        _note(question="q2"), first["entry_sha256"], path)
    assert ledger.ledger_head(path) == second["entry_sha256"]


def test_ledger_detects_edits_removals_and_suffix_deletion(tmp_path):
    path = tmp_path / "ledger.md"
    first = ledger.append_ledger_entry(_note(), None, path)
    ledger.append_ledger_entry(_note(question="q2"),
                               first["entry_sha256"], path)
    head = ledger.ledger_head(path)
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
    # SUFFIX deletion passes the bare chain; the head catches it, and
    # every boundary requires the head
    with open(path, "w") as handle:
        handle.write(blocks[0] + "\n## entry " + blocks[1])
    assert ledger.read_ledger(path)
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.verify_ledger_head(head, path)
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.append_ledger_entry(_note(question="q3"), head, path)


def test_ledger_entry_schema_fails_closed(tmp_path):
    path = tmp_path / "ledger.md"
    with pytest.raises(InfrastructureError, match="missing required"):
        ledger.admit_and_append_launch(
            {k: v for k, v in _entry().items() if k != "question"},
            None, path)
    with pytest.raises(InfrastructureError, match="unknown fields"):
        ledger.admit_and_append_launch(_entry(surprise=1), None, path)
    with pytest.raises(InfrastructureError, match="unknown entry kind"):
        ledger.admit_and_append_launch(_entry(kind="vibes"), None,
                                       path)
    with pytest.raises(InfrastructureError, match="cohort_selection"):
        ledger.admit_and_append_launch(
            _entry(cohort_selection="whatever"), None, path)
    with pytest.raises(InfrastructureError, match="linked closeout"):
        ledger.admit_and_append_launch(
            _entry(budget_consumed_gpu_hours=0.1), None, path)
    with pytest.raises(InfrastructureError, match="outcome_blind"):
        ledger.admit_and_append_launch(
            _entry(kind="grouped_probe"), None, path)
    # 218_s F2: launches cannot bypass admission via the plain append
    with pytest.raises(InfrastructureError, match="admit_and_append"):
        ledger.append_ledger_entry(_entry(), None, path)
    # NaN budgets fail closed
    with pytest.raises(InfrastructureError, match="finite"):
        ledger.admit_and_append_launch(
            _entry(budget_allocated_gpu_hours=float("nan")), None,
            path)


def test_reserve_requires_numerical_basis_and_exact_rounding(tmp_path):
    path = tmp_path / "ledger.md"
    incomplete = {"status": "provisional", "r_cycle_gpu_hours": 6.0}
    with pytest.raises(InfrastructureError, match="numerical basis"):
        ledger.append_ledger_entry(
            _entry(kind="reserve_update", reserve=incomplete,
                   budget_allocated_gpu_hours=0.0), None, path)
    # 218_s minor: the rounding POLICY is frozen and recomputed
    # exactly — below-basis and above-ceil reserves both refuse
    with pytest.raises(InfrastructureError, match="must recompute"):
        ledger.validate_reserve(_reserve(hours=6.0))
    with pytest.raises(InfrastructureError, match="must recompute"):
        ledger.validate_reserve(_reserve(hours=9.0))
    # measured 4.3 s -> implied 7.1667 -> exact ceil is 8.0
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
        _entry(kind="reserve_update", reserve=_reserve(),
               budget_allocated_gpu_hours=0.0), None, path)


def test_launch_closeout_linkage_and_envelope(tmp_path):
    path = tmp_path / "ledger.md"
    reserve_entry = ledger.append_ledger_entry(
        _entry(kind="reserve_update", reserve=_reserve(),
               budget_allocated_gpu_hours=0.0), None, path)
    launch = ledger.admit_and_append_launch(
        _entry(budget_allocated_gpu_hours=3.0),
        reserve_entry["entry_sha256"], path)
    state = ledger.envelope_state(ledger.read_ledger(path))
    assert state["consumed_gpu_hours"] == pytest.approx(3.0)
    assert state["open_launches"] == [launch["entry_sha256"]]
    closeout = ledger.append_ledger_entry(
        _entry(kind="closeout",
               closes_entry_sha256=launch["entry_sha256"],
               budget_consumed_gpu_hours=1.25,
               budget_allocated_gpu_hours=0.0),
        launch["entry_sha256"], path)
    state = ledger.envelope_state(ledger.read_ledger(path))
    assert state["consumed_gpu_hours"] == pytest.approx(1.25)
    assert state["open_launches"] == []
    with pytest.raises(InfrastructureError, match="already closed"):
        ledger.append_ledger_entry(
            _entry(kind="closeout",
                   closes_entry_sha256=launch["entry_sha256"],
                   budget_consumed_gpu_hours=1.0,
                   budget_allocated_gpu_hours=0.0),
            closeout["entry_sha256"], path)
    with pytest.raises(InfrastructureError, match="not a recorded "
                       "launch"):
        ledger.append_ledger_entry(
            _entry(kind="closeout", closes_entry_sha256="0" * 64,
                   budget_consumed_gpu_hours=1.0,
                   budget_allocated_gpu_hours=0.0),
            closeout["entry_sha256"], path)


def test_admission_verifies_the_persisted_ledger_itself(tmp_path):
    """218_s F2: admission takes the path + head + prospective entry;
    there is no caller-supplied entries list to spoof, and the checked
    kind/budget IS the recorded kind/budget."""
    path = tmp_path / "ledger.md"
    # empty ledger: ONLY the first support materialization launches
    with pytest.raises(InfrastructureError, match="FIRST support"):
        ledger.admit_and_append_launch(
            _entry(kind="training_run"), None, path)
    support = ledger.admit_and_append_launch(
        _entry(kind="support_materialization",
               cohort_selection="outcome_blind",
               budget_allocated_gpu_hours=4.0), None, path)
    # the launch was RECORDED with the admitted kind/budget
    entries = ledger.read_ledger(path)
    assert entries[-1]["kind"] == "support_materialization"
    assert entries[-1]["budget_allocated_gpu_hours"] == 4.0
    # a SECOND support refuses — derived from the persisted chain;
    # replaying the empty-ledger admission is impossible because the
    # head no longer matches
    with pytest.raises(InfrastructureError, match="prior support"):
        ledger.admit_and_append_launch(
            _entry(kind="support_materialization",
                   cohort_selection="outcome_blind",
                   budget_allocated_gpu_hours=4.0),
            support["entry_sha256"], path)
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.admit_and_append_launch(
            _entry(kind="support_materialization",
                   cohort_selection="outcome_blind",
                   budget_allocated_gpu_hours=4.0), None, path)
    reserve_entry = ledger.append_ledger_entry(
        _entry(kind="reserve_update", reserve=_reserve(),
               budget_allocated_gpu_hours=0.0),
        support["entry_sha256"], path)
    head = reserve_entry["entry_sha256"]
    probe = ledger.admit_and_append_launch(
        _entry(kind="grouped_probe",
               cohort_selection="outcome_blind",
               budget_allocated_gpu_hours=3.0), head, path)
    head = probe["entry_sha256"]
    # remaining = 60 - 4 - 3 = 53; 50 + 7 > 53 refuses
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
    assert ledger.read_ledger(path)[-1]["entry_sha256"] == \
        closure["entry_sha256"]
    with pytest.raises(InfrastructureError, match="not a launch kind"):
        ledger.admit_and_append_launch(
            _entry(kind="reserve_update", reserve=_reserve(),
                   budget_allocated_gpu_hours=1.0),
            closure["entry_sha256"], path)


# --- checkpoint/resume (211_f §11; 216_s F5/F6) --------------------------------------

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
    """A complete checkpoint bundle under the fixed filename manifest."""
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
    assert counters["generated_groups"] == 2
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
    assert restored["rng_state"] == json.loads(
        json.dumps(RNG_STATE))
    # identity mismatch names the key
    with pytest.raises(InfrastructureError, match="prompt_sha256"):
        checkpoint.validate_resume(
            record, dict(IDENTITIES, prompt_sha256="other"),
            bundle_dir=bundle_dir)
    # a tampered record refuses
    tampered = dict(record)
    tampered["counters"] = dict(record["counters"],
                                optimizer_updates=99)
    with pytest.raises(InfrastructureError, match="rehash"):
        checkpoint.validate_resume(tampered, IDENTITIES,
                                   bundle_dir=bundle_dir)
    # altered adapter bytes on disk refuse — verification is not
    # optional (216_s F5)
    (bundle_dir / checkpoint.CHECKPOINT_BUNDLE_FILENAMES["adapter"]) \
        .write_bytes(b"ALTERED")
    with pytest.raises(InfrastructureError, match="bundle was "
                       "altered"):
        checkpoint.validate_resume(record, IDENTITIES,
                                   bundle_dir=bundle_dir)


def test_resume_cross_binds_the_rng_artifact(tmp_path):
    """A record whose bound FILE hash covers a different RNG state
    than its rng_state_sha256 claims is caught by the cross-binding
    (the file-hash check alone would pass)."""
    for name in ("adapter", "optimizer", "scheduler"):
        (tmp_path / checkpoint.CHECKPOINT_BUNDLE_FILENAMES[name]) \
            .write_bytes(name.encode())
    other = dict(RNG_STATE, torch_cpu=[2])
    checkpoint.persist_rng_state(tmp_path, other)   # file holds OTHER
    filenames = {name: checkpoint.CHECKPOINT_BUNDLE_FILENAMES[name]
                 for name in ("adapter", "optimizer", "scheduler",
                              "rng")}
    hashes = checkpoint.hash_state_artifacts(tmp_path, filenames)
    record = checkpoint.build_checkpoint_record(
        identities=IDENTITIES,
        counters=_accountant_at_boundary().authorize_checkpoint(),
        rng_state=RNG_STATE,               # record claims RNG_STATE
        state_artifact_hashes=hashes,      # but binds the OTHER file
        sampler_position={"next_global_group_index": 2},
        run_id="p0", segment_id="s", parent_checkpoint=None)
    with pytest.raises(InfrastructureError, match="rng_state_sha256"):
        checkpoint.validate_resume(record, IDENTITIES,
                                   bundle_dir=tmp_path)


def test_checkpoint_record_refuses_off_boundary_counters():
    with pytest.raises(InfrastructureError, match="v1 boundary"):
        checkpoint.build_checkpoint_record(
            identities=IDENTITIES,
            counters={"generated_groups": 3, "consumed_groups": 2,
                      "optimizer_updates": 1,
                      "sampled_completions": 24},
            rng_state=RNG_STATE,
            state_artifact_hashes={"adapter": "a" * 64,
                                   "optimizer": "b" * 64,
                                   "scheduler": "c" * 64,
                                   "rng": "d" * 64, "scaler": None},
            sampler_position={"next_global_group_index": 2},
            run_id="p0", segment_id="s", parent_checkpoint=None)


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
    # 216_s F6 reproductions: reordered rows refuse …
    with pytest.raises(InfrastructureError, match="exact in-order"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 0, 2, [1, 0])])
    # … and every segment must carry its checkpointed groups: a
    # complete segment short of its cutoff refuses (218_s F4 message)
    with pytest.raises(InfrastructureError, match="omits checkpointed"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 0, 3, [0, 1])])
    # rows BEYOND a complete segment's own checkpoint refuse
    with pytest.raises(InfrastructureError, match="exact range"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 0, 3, range(5))])
    # 218_s F4: an ABORTED segment must also carry every checkpointed
    # group — cutoff 3 with rows [0, 1] omits group 2
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
