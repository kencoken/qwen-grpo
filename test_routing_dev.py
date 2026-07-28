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


# --- execution lock and dev surfaces (211_f §4, 216_s F1) -----------------------

def _env_manifest(**extra):
    body = {"manifest": "test-environment", "git_commit": "deadbeef",
            "uv_lock_sha256": "aa" * 32, **extra}
    sha = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    return {**body, "execution_manifest_sha256": sha}


DRIVER = "tasks/routing/dev_support.py"


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
    execution = dev_support.build_execution_lock(DRIVER,
                                                 _env_manifest())
    out = tmp_path / "surface"
    dev_support.materialize_dev_support(rt, declaration, out,
                                        execution)
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


def test_execution_lock_recomputes_and_refuses_invention():
    lock = dev_support.build_execution_lock(DRIVER, _env_manifest())
    assert dev_support.validate_execution_lock(lock)
    # invented provenance: edit the source sha and rehash — the live
    # recompute refuses (216_s F1 reproduction)
    forged = {k: v for k, v in lock.items() if k != "lock_sha256"}
    forged["routing_source_sha256"] = "0" * 64
    forged["lock_sha256"] = charter.content_sha256(forged)
    with pytest.raises(InfrastructureError, match="does not recompute"):
        dev_support.validate_execution_lock(forged)
    # a driver outside the digested set cannot even build a lock
    with pytest.raises(InfrastructureError, match="actual training "
                       "driver"):
        dev_support.build_execution_lock("train.py", _env_manifest())
    # an environment manifest that is not self-consistent refuses
    bad_env = dict(_env_manifest(), git_commit="other")
    with pytest.raises(InfrastructureError, match="hash mismatch"):
        dev_support.build_execution_lock(DRIVER, bad_env)


def test_materialization_consumes_the_execution_lock(tmp_path):
    rt = dev_fake_rt(tmp_path)
    declaration = dev_support.build_dev_declaration(
        rt, tag="t", namespace="routing_dev", cohort=DEV_COHORT,
        renderers=DEV_RENDERERS, visibility="private")
    lock = dev_support.build_execution_lock(DRIVER, _env_manifest())
    forged = {k: v for k, v in lock.items() if k != "lock_sha256"}
    forged["environment_manifest_sha256"] = "0" * 64
    forged["lock_sha256"] = charter.content_sha256(forged)
    # forged env identity passes rehash but the record persists; a
    # tampered SOURCE identity refuses at consumption:
    bad = dict(forged, routing_source_sha256="1" * 64)
    bad = {k: v for k, v in bad.items() if k != "lock_sha256"}
    bad["lock_sha256"] = charter.content_sha256(bad)
    with pytest.raises(InfrastructureError, match="does not recompute"):
        dev_support.materialize_dev_support(
            rt, declaration, tmp_path / "surface", bad)
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
    execution = dev_support.build_execution_lock(DRIVER,
                                                 _env_manifest())
    with pytest.raises(InfrastructureError, match="request_contract"):
        dev_support.materialize_dev_support(
            rt, tampered, tmp_path / "surface", execution)
    rt.close()


def test_dev_surface_roundtrip_under_its_lock(locked_surface):
    out, lock, loaded = locked_surface
    surface = loaded["surface"]
    assert len(surface) == 108 * len(DEV_RENDERERS)
    assert set(surface.values()) <= {0.5, 1.0}
    assert loaded["lock"]["execution_lock_sha256"]
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


def _reserve(status="provisional", hours=7.0):
    # basis: 3000 obs x 2.0 passes x 4.2 s / 3600 = 7.0 h exactly
    return {"status": status, "r_cycle_gpu_hours": hours,
            "assumed_cohort_size": 3000,
            "evaluation_multiplier": 2.0,
            "measured_seconds_per_observation": 4.2,
            "rounding": "ceil to whole GPU-hours"}


def test_ledger_append_requires_the_external_head(tmp_path):
    path = tmp_path / "ledger.md"
    first = ledger.append_ledger_entry(_entry(), None, path)
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.append_ledger_entry(_entry(), None, path)
    second = ledger.append_ledger_entry(
        _entry(question="q2"), first["entry_sha256"], path)
    assert ledger.ledger_head(path) == second["entry_sha256"]


def test_ledger_detects_edits_removals_and_suffix_deletion(tmp_path):
    path = tmp_path / "ledger.md"
    first = ledger.append_ledger_entry(_entry(), None, path)
    ledger.append_ledger_entry(_entry(question="q2"),
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
    # so does any subsequent append (which now requires the head)
    with open(path, "w") as handle:
        handle.write(blocks[0] + "\n## entry " + blocks[1])
    assert ledger.read_ledger(path)
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.verify_ledger_head(head, path)
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.append_ledger_entry(_entry(question="q3"), head, path)


def test_ledger_entry_schema_fails_closed(tmp_path):
    path = tmp_path / "ledger.md"
    with pytest.raises(InfrastructureError, match="missing required"):
        ledger.append_ledger_entry(
            {k: v for k, v in _entry().items() if k != "question"},
            None, path)
    with pytest.raises(InfrastructureError, match="unknown fields"):
        ledger.append_ledger_entry(_entry(surprise=1), None, path)
    with pytest.raises(InfrastructureError, match="unknown entry kind"):
        ledger.append_ledger_entry(_entry(kind="vibes"), None, path)
    with pytest.raises(InfrastructureError, match="cohort_selection"):
        ledger.append_ledger_entry(
            _entry(cohort_selection="whatever"), None, path)
    with pytest.raises(InfrastructureError, match="linked closeout"):
        ledger.append_ledger_entry(
            _entry(budget_consumed_gpu_hours=0.1), None, path)
    # 216_s F2: support/probe launches must declare outcome-blindness
    with pytest.raises(InfrastructureError, match="outcome_blind"):
        ledger.append_ledger_entry(
            _entry(kind="support_materialization"), None, path)
    with pytest.raises(InfrastructureError, match="outcome_blind"):
        ledger.append_ledger_entry(
            _entry(kind="grouped_probe"), None, path)


def test_reserve_requires_numerical_basis_and_recomputation(tmp_path):
    path = tmp_path / "ledger.md"
    incomplete = {"status": "provisional", "r_cycle_gpu_hours": 6.0}
    with pytest.raises(InfrastructureError, match="numerical basis"):
        ledger.append_ledger_entry(
            _entry(kind="reserve_update", reserve=incomplete,
                   budget_allocated_gpu_hours=0.0), None, path)
    # 216_s: a reserve below its own basis refuses
    with pytest.raises(InfrastructureError, match="below its own "
                       "basis"):
        ledger.append_ledger_entry(
            _entry(kind="reserve_update", reserve=_reserve(hours=6.0),
                   budget_allocated_gpu_hours=0.0), None, path)
    ledger.append_ledger_entry(
        _entry(kind="reserve_update", reserve=_reserve(),
               budget_allocated_gpu_hours=0.0), None, path)


def test_launch_closeout_linkage_and_envelope(tmp_path):
    path = tmp_path / "ledger.md"
    launch = ledger.append_ledger_entry(
        _entry(budget_allocated_gpu_hours=3.0), None, path)
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


def test_admission_is_derived_from_the_verified_ledger(tmp_path):
    path = tmp_path / "ledger.md"
    # empty ledger: ONLY the first support materialization is
    # admissible, against the bare envelope
    entries = ledger.verify_ledger_head(None, path)
    ledger.check_launch_admissible(
        entries=entries, launch_kind="support_materialization",
        launch_max_gpu_hours=4.0)
    with pytest.raises(InfrastructureError, match="FIRST support"):
        ledger.check_launch_admissible(
            entries=entries, launch_kind="engineering_smoke",
            launch_max_gpu_hours=1.0)
    # record the support launch; a SECOND support without a reserve
    # now refuses — "first, exactly once" is derived, not asserted
    support = ledger.append_ledger_entry(
        _entry(kind="support_materialization",
               cohort_selection="outcome_blind",
               budget_allocated_gpu_hours=4.0), None, path)
    entries = ledger.verify_ledger_head(support["entry_sha256"], path)
    with pytest.raises(InfrastructureError, match="prior support"):
        ledger.check_launch_admissible(
            entries=entries, launch_kind="support_materialization",
            launch_max_gpu_hours=4.0)
    # with the reserve recorded, ordinary + closure rules apply
    reserve_entry = ledger.append_ledger_entry(
        _entry(kind="reserve_update", reserve=_reserve(),
               budget_allocated_gpu_hours=0.0),
        support["entry_sha256"], path)
    entries = ledger.verify_ledger_head(reserve_entry["entry_sha256"],
                                        path)
    state = ledger.check_launch_admissible(
        entries=entries, launch_kind="grouped_probe",
        launch_max_gpu_hours=3.0)
    assert state["reserve"]["status"] == "provisional"
    # remaining = 60 - 4 = 56; an ordinary launch of 50 would breach
    # max + R_cycle (50 + 7 > 56)
    with pytest.raises(InfrastructureError, match="inadmissible"):
        ledger.check_launch_admissible(
            entries=entries, launch_kind="training_run",
            launch_max_gpu_hours=50.0)
    ledger.check_launch_admissible(
        entries=entries, launch_kind="cycle_closure",
        launch_max_gpu_hours=6.5)
    with pytest.raises(InfrastructureError, match="exceeds the "
                       "reserved"):
        ledger.check_launch_admissible(
            entries=entries, launch_kind="cycle_closure",
            launch_max_gpu_hours=7.5)
    with pytest.raises(InfrastructureError, match="not a launch kind"):
        ledger.check_launch_admissible(
            entries=entries, launch_kind="reserve_update",
            launch_max_gpu_hours=1.0)


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
    # … and a complete segment must cover [resume_from, cutoff)
    with pytest.raises(InfrastructureError, match="exact range"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 0, 3, [0, 1])])
    with pytest.raises(InfrastructureError, match="exact range"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 0, 3, range(5))])


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
