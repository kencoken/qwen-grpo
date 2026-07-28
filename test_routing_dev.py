"""Routing development-track infrastructure battery (211_f §15 step 3,
hardened per 214_s): namespaces + disjointness, charter constants +
strict natural mixture + driver-inclusive execution digest, dev
surface materialization behind its surface lock, the enforced
first-probe rule, c_fixed_dev on lock-validated surfaces,
authenticated stratified telemetry with C1/ModelAcc/C2, the
append-only ledger with launch/closeout linkage and head binding, and
the v1 checkpoint/resume contract with bound state artifacts."""

import json

import pytest

from tasks.conductor import program
from tasks.conductor.cache import WorkerCompletionCache
from tasks.conductor.pool_runtime import FourWorkerRuntime
from tasks.conductor.profiles import DEFAULT_PROFILE
from tasks.conductor.stage1_replay import pair_table_from_surface
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
    """The 191_f/211_f disjointness test: regenerate id prefixes across
    ALL namespaces and check zero intersection."""
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


# --- charter: natural mixture, digest, freezes (211_f §§1, 6, 12) --------------

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
    population = _mixture_population(latents_per_cell=2)
    weights = charter.natural_mixture_weights(population)
    assert sum(weights.values()) == pytest.approx(1.0)
    # equal cells (6), equal latents within cell (2), equal renderers
    # within latent (3): every observation weighs 1/36
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
    assert "tasks/conductor/grpo_task.py" in \
        digest["routing_source_files"]
    assert "tasks/routing/checkpoint.py" in \
        digest["routing_source_files"]
    with pytest.raises(InfrastructureError, match="actual training "
                       "driver"):
        charter.routing_execution_digest("train.py")


def test_execution_digest_accepts_a_module_inside_the_set():
    digest = charter.routing_execution_digest(checkpoint)
    assert digest["driver"] == "tasks/routing/checkpoint.py"


def test_lightweight_freeze_requires_the_211f_fields():
    record = {"kind": "engineering_smoke", "question": "q",
              "motivation": "m", "config": {"x": 1},
              "budget_gpu_hours": 0.5}
    frozen = charter.lightweight_freeze(record)
    assert frozen["freeze_sha256"]
    with pytest.raises(InfrastructureError, match="missing"):
        charter.lightweight_freeze({k: v for k, v in record.items()
                                    if k != "budget_gpu_hours"})
    with pytest.raises(InfrastructureError, match="positive budget"):
        charter.lightweight_freeze({**record, "budget_gpu_hours": 0})


def test_claim_run_root_refuses_reuse(tmp_path):
    root = charter.claim_run_root("probe-1", base=tmp_path)
    assert root.is_dir()
    with pytest.raises(InfrastructureError, match="never overwrite"):
        charter.claim_run_root("probe-1", base=tmp_path)
    with pytest.raises(InfrastructureError, match="bad run root"):
        charter.claim_run_root("a/b", base=tmp_path)


# --- dev surfaces behind their lock (211_f §4, 214_s P1) ------------------------

def _wrong_worker3(request: bytes) -> str:
    return "<artifact>lookup(resource, \"nope\", \"nope\")</artifact>"


def dev_fake_rt(tmp_path, sabotage_w3: bool = False):
    """Perfect completions for the DEV_COHORT observations; optionally
    worker 3 answers wrongly so Code pairs get distinct payoffs."""
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


EXECUTION = {"routing_source_sha256": "1a" * 32,
             "driver": "tasks/routing/dev_support.py",
             "environment_manifest_sha256": "2b" * 32}


@pytest.fixture(scope="module")
def locked_surface(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("dev-surface")
    rt = dev_fake_rt(tmp_path, sabotage_w3=True)
    declaration = dev_support.build_dev_declaration(
        rt, tag="routing-dev-support-test-v1",
        namespace="routing_dev", cohort=DEV_COHORT,
        renderers=DEV_RENDERERS, visibility="private")
    out = tmp_path / "surface"
    dev_support.materialize_dev_support(rt, declaration, out)
    rt.close()
    lock = dev_support.build_surface_lock(out, **EXECUTION)
    return out, lock


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


def test_dev_observations_live_in_the_dev_namespace():
    observations = dev_support.dev_cohort_observations(
        "routing_dev", DEV_COHORT, DEV_RENDERERS, "private")
    assert len(observations) == 6 * len(DEV_RENDERERS)
    for obs in observations:
        assert ":routing_dev:" in obs["observation_id"]


def test_declaration_binds_the_execution_identity(tmp_path):
    """214_s P1 reproduction: a materially different declared request
    contract must REFUSE materialization."""
    rt = dev_fake_rt(tmp_path)
    declaration = dev_support.build_dev_declaration(
        rt, tag="t", namespace="routing_dev", cohort=DEV_COHORT,
        renderers=DEV_RENDERERS, visibility="private")
    assert declaration["runtime_profile_fingerprint"] == \
        rt.runtime_profile_fingerprint
    assert declaration["cache_identity"].startswith(
        "worker_completions/slw/")
    tampered = dict(declaration,
                    request_contract="worker-blocks-task-first-v0")
    with pytest.raises(InfrastructureError, match="request_contract"):
        dev_support.materialize_dev_support(rt, tampered,
                                            tmp_path / "surface")
    rt.close()


def test_dev_surface_roundtrip_under_its_lock(locked_surface):
    out, lock = locked_surface
    loaded = dev_support.load_dev_surface(
        out, expected_lock_sha256=lock["lock_sha256"])
    surface = loaded["surface"]
    # per renderer: 3x4 atomic + 2x16 two-step + 64 fork = 108
    assert len(surface) == 108 * len(DEV_RENDERERS)
    assert set(surface.values()) <= {0.5, 1.0}
    assert loaded["lock"]["lock_sha256"] == lock["lock_sha256"]
    # sabotaged worker 3: every Code pair is w2-favoured
    cell_of = {obs["observation_id"]: obs["cell_id"]
               for obs in loaded["observations"]}
    table = pair_table_from_surface(surface, cell_of)
    assert {entry["direction"] for entry in table.values()} == {2}


def test_surface_lock_is_required_and_exact(locked_surface, tmp_path):
    out, lock = locked_surface
    with pytest.raises(InfrastructureError, match="externally frozen"):
        dev_support.load_dev_surface(
            out, expected_lock_sha256="0" * 64)
    with pytest.raises(InfrastructureError, match="no surface lock"):
        dev_support.load_dev_surface(
            tmp_path, expected_lock_sha256=lock["lock_sha256"])
    with pytest.raises(InfrastructureError, match="locked exactly "
                       "once"):
        dev_support.build_surface_lock(out, **EXECUTION)


def test_surface_lock_detects_tampered_bytes(tmp_path):
    rt = dev_fake_rt(tmp_path)
    declaration = dev_support.build_dev_declaration(
        rt, tag="t2", namespace="routing_dev", cohort=DEV_COHORT,
        renderers=DEV_RENDERERS, visibility="private")
    out = tmp_path / "surface"
    dev_support.materialize_dev_support(rt, declaration, out)
    rt.close()
    lock = dev_support.build_surface_lock(out, **EXECUTION)
    payoffs = out / "payoffs.jsonl"
    rows = payoffs.read_text().splitlines()
    payoffs.write_text("\n".join(rows[:-1]) + "\n")
    with pytest.raises(InfrastructureError, match="bytes on disk"):
        dev_support.load_dev_surface(
            out, expected_lock_sha256=lock["lock_sha256"])


def test_direction_yields_disclose_every_observation(locked_surface):
    out, lock = locked_surface
    loaded = dev_support.load_dev_surface(
        out, expected_lock_sha256=lock["lock_sha256"])
    yields = dev_support.direction_yields(loaded["surface"],
                                          loaded["observations"])
    assert len(yields["per_observation"]) == len(loaded["observations"])
    for cell in ("code_atomic", "math_code", "fork_join"):
        assert yields["per_cell"][cell]["w2_favoured"] == 3
    for cell in ("lookup_atomic", "lookup_math", "math_atomic"):
        assert yields["per_cell"][cell]["no_pair"] == 3


def test_c_fixed_dev_selection_and_record(locked_surface):
    out, lock = locked_surface
    loaded = dev_support.load_dev_surface(
        out, expected_lock_sha256=lock["lock_sha256"])
    record = dev_support.select_c_fixed_dev(loaded)
    assert record["c_fixed_dev"] == 2
    assert record["tie"] is False
    assert record["candidate_scores"]["2"] == 1.0
    assert record["candidate_scores"]["3"] == 0.5
    assert record["surface_lock_sha256"] == lock["lock_sha256"]
    assert record["development_only"] is True
    assert dev_support.validate_c_fixed_record(record) == 2
    tampered = dict(record, c_fixed_dev=3)
    with pytest.raises(InfrastructureError, match="rehash"):
        dev_support.validate_c_fixed_record(tampered)


def test_c_fixed_dev_requires_the_locked_loader_result():
    with pytest.raises(InfrastructureError, match="lock-validated"):
        dev_support.select_c_fixed_dev(
            {"surface": {}, "observations": [], "lock": {}})


# --- probe rules (211_f §§4-5, 210_s issue 4, 214_s P1) --------------------------

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
    # a hand-built first-probe rule with the wrong shape refuses even
    # when correctly hashed
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
    out, lock = locked_surface
    frozen = cohorts.freeze_first_probe_rule(
        prefix_length_per_cell=6, groups_per_observation=2)
    with pytest.raises(InfrastructureError, match="under-covers"):
        cohorts.bind_probe_cohort(frozen, out, lock["lock_sha256"])


def test_probe_cohort_binds_the_surface_lock(locked_surface):
    out, lock = locked_surface
    frozen = cohorts.freeze_reprobe_rule(
        namespace="routing_dev", prefix_length_per_cell=1,
        renderers=RENDERER_IDS, visibility="private", group_size=8,
        groups_per_observation=2)
    bound = cohorts.bind_probe_cohort(frozen, out,
                                      lock["lock_sha256"])
    assert bound["rule_sha256"] == frozen["rule_sha256"]
    assert bound["surface_lock_sha256"] == lock["lock_sha256"]
    assert bound["payoffs_sha256"] == lock["payoffs_sha256"]
    assert len(bound["observation_ids"]) == 6 * len(RENDERER_IDS)
    with pytest.raises(InfrastructureError, match="externally frozen"):
        cohorts.bind_probe_cohort(frozen, out, "0" * 64)


# --- telemetry (211_f §7, 214_s P1: authenticated) --------------------------------

OBS = "code_atomic:routing_dev:00000:abcdef01:resource_first:private"
SURFACE = {(OBS, (0,)): 0.5, (OBS, (1,)): 0.5, (OBS, (2,)): 1.0,
           (OBS, (3,)): 0.5}
SURFACE_TIED = {(OBS, (0,)): 0.5, (OBS, (1,)): 0.5, (OBS, (2,)): 1.0,
                (OBS, (3,)): 1.0}


def _c_fixed_record(worker=2):
    body = {"comparator": "c_fixed_dev-v1", "c_fixed_dev": worker,
            "development_only": True}
    body["record_sha256"] = charter.content_sha256(body)
    return body


def _completion(valid, assignment, reward, parseable=None):
    return {"parseable": parseable if parseable is not None else valid,
            "valid": valid,
            "assignment": assignment, "reward": reward}


def test_group_stats_contrasts_and_views():
    group = {"observation_id": OBS, "completions": [
        _completion(False, None, 0.0),            # malformed
        _completion(True, [2], 1.0),              # w2 (winner)
        _completion(True, [3], 0.5),              # w3
        _completion(True, [0], 0.5),              # wrong family
    ]}
    stats = telemetry.group_stats(group, surface=SURFACE,
                                  c_fixed_record=_c_fixed_record())
    assert stats["cell_id"] == "code_atomic"
    assert stats["renderer_id"] == "resource_first"
    assert stats["latent_program_id"] == \
        "code_atomic:routing_dev:00000:abcdef01"
    assert stats["direction"] == "w2_favoured"
    assert stats["format_contrast"] is True
    assert stats["semantic_contrast"] is True
    assert stats["direct_contrast"] is True
    assert stats["variant_hits"] == {"w2": 1, "w3": 1}
    # C1: malformed scores 0 and STAYS in the denominator
    assert stats["c1_mean"] == pytest.approx((0 + 1 + 1 + 0) / 4)
    # broader ModelAcc: only the winner variant scores 1; malformed,
    # wrong-specialist and wrong-family all score 0 IN the denominator
    assert stats["model_acc"] == (1.0, 4)
    # C2: conditional on code choice in {2,3}
    assert stats["c2_eligible"] == 2
    assert stats["c2_optimal"] == 1
    # ScaleLift vs c_fixed_dev=2: w3 row 0.5-1.0=-0.5; others 0
    assert stats["scale_lift_mean"] == pytest.approx(-0.5 / 4)
    assert stats["zero_variance_level"] is None


def test_group_stats_authenticates_rewards_and_identity():
    # reward disagreeing with the authenticated surface refuses
    group = {"observation_id": OBS, "completions": [
        _completion(True, [2], 0.5)]}
    with pytest.raises(InfrastructureError, match="authenticated "
                       "payoff"):
        telemetry.group_stats(group, surface=SURFACE,
                              c_fixed_record=_c_fixed_record())
    # invalid completions must carry reward 0
    group = {"observation_id": OBS, "completions": [
        _completion(False, None, 0.5)]}
    with pytest.raises(InfrastructureError, match="scores malformed"):
        telemetry.group_stats(group, surface=SURFACE,
                              c_fixed_record=_c_fixed_record())
    # valid-but-not-parseable is a contradiction
    group = {"observation_id": OBS, "completions": [
        _completion(True, [2], 1.0, parseable=False)]}
    with pytest.raises(InfrastructureError, match="contradiction"):
        telemetry.group_stats(group, surface=SURFACE,
                              c_fixed_record=_c_fixed_record())
    # assignment schema is exact
    group = {"observation_id": OBS, "completions": [
        _completion(True, [2, 2], 1.0)]}
    with pytest.raises(InfrastructureError, match="action schema"):
        telemetry.group_stats(group, surface=SURFACE,
                              c_fixed_record=_c_fixed_record())
    # a tampered comparator record refuses
    group = {"observation_id": OBS, "completions": [
        _completion(True, [2], 1.0)]}
    with pytest.raises(InfrastructureError, match="rehash"):
        telemetry.group_stats(
            group, surface=SURFACE,
            c_fixed_record=dict(_c_fixed_record(), c_fixed_dev=3))


def test_group_stats_zero_variance_and_tied_pairs():
    group = {"observation_id": OBS, "completions": [
        _completion(True, [2], 1.0)] * 8}
    stats = telemetry.group_stats(group, surface=SURFACE_TIED,
                                  c_fixed_record=_c_fixed_record())
    assert stats["direction"] == "tied"
    assert stats["zero_variance_level"] == "1"
    assert stats["c2_optimal"] is None       # tied: never scored
    assert stats["c2_eligible"] == 8
    assert stats["model_acc"] is None
    assert stats["direct_contrast"] is False


def test_group_stats_refuses_missing_collapse_row():
    """math_code: the collapse of a wrong-family-at-n1 action lands on
    a non-pair row, which the surface must still cover."""
    obs2 = "math_code:routing_dev:00000:abcdef01:resource_first:private"
    surface = {(obs2, (1, 2)): 1.0, (obs2, (1, 3)): 0.5,
               (obs2, (0, 3)): 0.5}   # no (0, 2) row
    group = {"observation_id": obs2, "completions": [
        _completion(True, [0, 3], 0.5)]}
    with pytest.raises(InfrastructureError, match="collapse row"):
        telemetry.group_stats(group, surface=surface,
                              c_fixed_record=_c_fixed_record())


def test_group_stats_refuses_off_ladder_reward():
    group = {"observation_id": OBS, "completions": [
        _completion(True, [2], 0.75)]}
    with pytest.raises(InfrastructureError, match="frozen ladder"):
        telemetry.group_stats(group, surface=SURFACE,
                              c_fixed_record=_c_fixed_record())


def test_aggregate_stratified_reports_counts_and_denominators():
    groups = []
    for reward, assignment in ((1.0, [2]), (0.5, [3])):
        group = {"observation_id": OBS, "completions": [
            _completion(True, assignment, reward)] * 4}
        groups.append(telemetry.group_stats(
            group, surface=SURFACE,
            c_fixed_record=_c_fixed_record()))
    report = telemetry.aggregate_stratified(groups)
    total = report["total"]
    assert total["groups"] == 2
    assert total["valid"] == {"count": 8, "denominator": 8, "rate": 1.0}
    assert total["zero_variance"]["all_1"]["count"] == 1
    assert total["zero_variance"]["all_0.5"]["count"] == 1
    assert total["direct_contrast"]["count"] == 0
    assert total["model_acc"] == \
        {"count": 4.0, "denominator": 8, "rate": 0.5}
    assert total["c2_optimal_specialist"] == \
        {"count": 4, "denominator": 8, "rate": 0.5}
    # 214_s reporting repairs
    assert total["worker_frequencies"] == {"2": 4, "3": 4}
    assert total["assignment_frequencies"] == {"2": 4, "3": 4}
    assert total["repeated_output_concentration_mean"] == 1.0
    equal_cell = report["equal_cell"]
    assert equal_cell["cells"] == ["code_atomic"]
    assert equal_cell["mean_reward"] == pytest.approx(0.75)
    key = "code_atomic|resource_first|w2_favoured"
    assert key in report["by_cell_renderer_direction"]
    with pytest.raises(InfrastructureError, match="no groups"):
        telemetry.aggregate_stratified([])


def test_equal_cell_view_weights_hierarchically():
    """Two cells; cell A has two latents (one with 2 groups), cell B
    one latent — the equal-cell mean is NOT the pooled mean."""
    def synthetic(cell, latent, renderer, reward):
        oid = f"{cell}:{latent}:{renderer}"
        return {"cell_id": cell, "latent_program_id": f"{cell}:{latent}",
                "renderer_id": renderer, "observation_id": oid,
                "n": 4, "parseable": 4, "valid": 4,
                "mean_reward": reward, "zero_variance_level": "1",
                "format_contrast": False, "semantic_contrast": False,
                "direct_contrast": False, "c1_mean": 1.0,
                "scale_lift_mean": 0.0,
                "reward_levels": {"0": 0, "0.5": 0, "1": 4},
                "model_acc": None, "c2_eligible": 0, "c2_optimal": None,
                "variant_hits": None, "assignment_counts": {"2": 4},
                "worker_counts": {"2": 4},
                "routing_entropy_bits": 0.0,
                "max_assignment_concentration": 1.0}
    groups = [synthetic("A", "l1", "r1", 1.0),
              synthetic("A", "l1", "r1", 0.0),
              synthetic("A", "l2", "r1", 1.0),
              synthetic("B", "l1", "r1", 0.0)]
    view = telemetry.equal_cell_view(groups)
    # cell A: latent l1 -> 0.5, latent l2 -> 1.0 => 0.75; cell B: 0.0
    assert view["mean_reward"] == pytest.approx((0.75 + 0.0) / 2)


# --- ledger (211_f §§10, 12; 214_s P1 lifecycle) -----------------------------------

def _entry(**overrides):
    entry = {"kind": "engineering_smoke", "question": "q",
             "motivating_evidence": "202_f priors",
             "freeze": {"config_sha256": "ab" * 32},
             "parent": None, "budget_allocated_gpu_hours": 0.5,
             "outcome_informed": False}
    entry.update(overrides)
    return entry


def _reserve(status="provisional", hours=6.0):
    return {"status": status, "r_cycle_gpu_hours": hours,
            "assumed_cohort_size": 3000,
            "evaluation_multiplier": 2.0,
            "measured_seconds_per_observation": 4.2,
            "rounding": "ceil to whole GPU-hours"}


def test_ledger_append_read_roundtrip_and_chain(tmp_path):
    path = tmp_path / "ledger.md"
    first = ledger.append_ledger_entry(_entry(), path,
                                       expected_head_sha256=None)
    second = ledger.append_ledger_entry(
        _entry(kind="reserve_update", reserve=_reserve(),
               budget_allocated_gpu_hours=0.0), path,
        expected_head_sha256=first["entry_sha256"])
    entries = ledger.read_ledger(path)
    assert [e["entry_sha256"] for e in entries] == \
        [first["entry_sha256"], second["entry_sha256"]]
    assert ledger.ledger_head(path) == second["entry_sha256"]


def test_ledger_detects_edits_removals_and_suffix_deletion(tmp_path):
    path = tmp_path / "ledger.md"
    ledger.append_ledger_entry(_entry(), path)
    head_after_one = ledger.ledger_head(path)
    ledger.append_ledger_entry(_entry(question="q2"), path)
    head = ledger.ledger_head(path)
    text = path.read_text()
    with open(path, "w") as handle:
        handle.write(text.replace('"question": "q"',
                                  '"question": "edited"'))
    with pytest.raises(InfrastructureError, match="edited"):
        ledger.read_ledger(path)
    # removal of a MIDDLE entry: chain break
    blocks = text.split("\n## entry ")
    with open(path, "w") as handle:
        handle.write(blocks[0] + "\n## entry " + blocks[2])
    with pytest.raises(InfrastructureError, match="chain broken"):
        ledger.read_ledger(path)
    # SUFFIX deletion: chain still verifies — only the externally
    # committed head catches it (214_s P1)
    with open(path, "w") as handle:
        handle.write(blocks[0] + "\n## entry " + blocks[1])
    assert ledger.read_ledger(path)  # chain alone cannot see it
    with pytest.raises(InfrastructureError, match="externally "
                       "committed head"):
        ledger.verify_ledger_head(head, path)
    assert ledger.verify_ledger_head(head_after_one, path)


def test_ledger_entry_schema_fails_closed(tmp_path):
    path = tmp_path / "ledger.md"
    with pytest.raises(InfrastructureError, match="missing required"):
        ledger.append_ledger_entry(
            {k: v for k, v in _entry().items() if k != "question"},
            path)
    with pytest.raises(InfrastructureError, match="unknown fields"):
        ledger.append_ledger_entry(_entry(surprise=1), path)
    with pytest.raises(InfrastructureError, match="unknown entry kind"):
        ledger.append_ledger_entry(_entry(kind="vibes"), path)
    with pytest.raises(InfrastructureError, match="cohort_selection"):
        ledger.append_ledger_entry(
            _entry(cohort_selection="whatever"), path)
    with pytest.raises(InfrastructureError, match="linked closeout"):
        ledger.append_ledger_entry(
            _entry(budget_consumed_gpu_hours=0.1), path)


def test_reserve_requires_its_numerical_basis(tmp_path):
    path = tmp_path / "ledger.md"
    incomplete = {"status": "provisional", "r_cycle_gpu_hours": 6.0}
    with pytest.raises(InfrastructureError, match="numerical basis"):
        ledger.append_ledger_entry(
            _entry(kind="reserve_update", reserve=incomplete,
                   budget_allocated_gpu_hours=0.0), path)
    ledger.append_ledger_entry(
        _entry(kind="reserve_update", reserve=_reserve(),
               budget_allocated_gpu_hours=0.0), path)


def test_launch_closeout_linkage_and_envelope(tmp_path):
    path = tmp_path / "ledger.md"
    launch = ledger.append_ledger_entry(
        _entry(budget_allocated_gpu_hours=3.0), path)
    state = ledger.envelope_state(ledger.read_ledger(path))
    assert state["consumed_gpu_hours"] == pytest.approx(3.0)
    assert state["open_launches"] == [launch["entry_sha256"]]
    # closeout replaces the allocation with the measured cost
    ledger.append_ledger_entry(
        _entry(kind="closeout",
               closes_entry_sha256=launch["entry_sha256"],
               budget_consumed_gpu_hours=1.25,
               budget_allocated_gpu_hours=0.0), path)
    state = ledger.envelope_state(ledger.read_ledger(path))
    assert state["consumed_gpu_hours"] == pytest.approx(1.25)
    assert state["open_launches"] == []
    assert state["remaining_gpu_hours"] == pytest.approx(60 - 1.25)
    # double closeout refuses; unknown target refuses
    with pytest.raises(InfrastructureError, match="already closed"):
        ledger.append_ledger_entry(
            _entry(kind="closeout",
                   closes_entry_sha256=launch["entry_sha256"],
                   budget_consumed_gpu_hours=1.0,
                   budget_allocated_gpu_hours=0.0), path)
    with pytest.raises(InfrastructureError, match="not a recorded "
                       "launch"):
        ledger.append_ledger_entry(
            _entry(kind="closeout", closes_entry_sha256="0" * 64,
                   budget_consumed_gpu_hours=1.0,
                   budget_allocated_gpu_hours=0.0), path)


def test_admissibility_ordinary_closure_and_initial_support():
    reserve = _reserve(hours=6.0)
    ledger.check_launch_admissible(
        remaining_gpu_hours=20.0, launch_max_gpu_hours=10.0,
        reserve=reserve)
    with pytest.raises(InfrastructureError, match="inadmissible"):
        ledger.check_launch_admissible(
            remaining_gpu_hours=15.0, launch_max_gpu_hours=10.0,
            reserve=reserve)
    # closure CONSUMES the reserve (no double count)
    ledger.check_launch_admissible(
        remaining_gpu_hours=6.0, launch_max_gpu_hours=5.5,
        reserve=reserve, closure=True)
    with pytest.raises(InfrastructureError, match="exceeds the "
                       "reserved"):
        ledger.check_launch_admissible(
            remaining_gpu_hours=20.0, launch_max_gpu_hours=6.5,
            reserve=reserve, closure=True)
    # the INITIAL support materialization launches against the bare
    # envelope, exactly once, before any reserve exists (214_s P1)
    ledger.check_launch_admissible(
        remaining_gpu_hours=60.0, launch_max_gpu_hours=4.0,
        reserve=None, initial_support=True)
    with pytest.raises(InfrastructureError, match="only BEFORE"):
        ledger.check_launch_admissible(
            remaining_gpu_hours=60.0, launch_max_gpu_hours=4.0,
            reserve=reserve, initial_support=True)
    with pytest.raises(InfrastructureError, match="no reserve"):
        ledger.check_launch_admissible(
            remaining_gpu_hours=20.0, launch_max_gpu_hours=1.0,
            reserve=None)


# --- checkpoint/resume (211_f §11, 214_s P1) -----------------------------------------

IDENTITIES = {key: f"{key}-value" for key in checkpoint.IDENTITY_KEYS}
ARTIFACTS = {"adapter": "a" * 64, "optimizer": "b" * 64,
             "scheduler": "c" * 64, "rng": "d" * 64, "scaler": None}


def _accountant_at_boundary():
    accountant = checkpoint.GroupAccountant()
    accountant.record_generation(groups=2, completions=16)
    accountant.record_update(consumed_groups=2)
    return accountant


def _record(**overrides):
    kwargs = dict(
        identities=IDENTITIES,
        counters=_accountant_at_boundary().authorize_checkpoint(),
        rng_state={"python": [1], "numpy": [2], "torch_cpu": [3],
                   "torch_cuda": None},
        state_artifact_hashes=ARTIFACTS,
        sampler_position={"next_global_group_index": 2},
        run_id="p0", segment_id="p0-seg1", parent_checkpoint=None)
    kwargs.update(overrides)
    return checkpoint.build_checkpoint_record(**kwargs)


def test_group_accountant_enforces_the_v1_boundary():
    accountant = checkpoint.GroupAccountant()
    accountant.record_generation(groups=2, completions=16)
    with pytest.raises(InfrastructureError, match="v1 boundary"):
        accountant.authorize_checkpoint()
    accountant.record_update(consumed_groups=1)
    with pytest.raises(InfrastructureError, match="v1 boundary"):
        accountant.authorize_checkpoint()
    accountant.record_update(consumed_groups=1)
    counters = accountant.authorize_checkpoint()
    assert counters["generated_groups"] == counters["consumed_groups"] \
        == 2
    with pytest.raises(InfrastructureError, match="never generated"):
        accountant.record_update(consumed_groups=1)


def test_group_accountant_restores_only_validated_counters():
    counters = _accountant_at_boundary().authorize_checkpoint()
    restored = checkpoint.GroupAccountant.restore(counters)
    assert restored.at_v1_boundary()
    assert restored.sampled_completions == 16
    with pytest.raises(InfrastructureError, match="v1 boundary"):
        checkpoint.GroupAccountant.restore(
            dict(counters, generated_groups=3))
    with pytest.raises(InfrastructureError, match="impossible"):
        checkpoint.GroupAccountant.restore(
            dict(counters, sampled_completions=1))


def test_checkpoint_record_roundtrip_and_fail_closed_resume():
    record = _record()
    restored = checkpoint.validate_resume(record, IDENTITIES,
                                          ARTIFACTS)
    assert restored["counters"]["consumed_groups"] == 2
    changed = dict(IDENTITIES, prompt_sha256="other")
    with pytest.raises(InfrastructureError, match="prompt_sha256"):
        checkpoint.validate_resume(record, changed, ARTIFACTS)
    tampered = dict(record)
    tampered["counters"] = dict(record["counters"],
                                optimizer_updates=99)
    with pytest.raises(InfrastructureError, match="rehash"):
        checkpoint.validate_resume(tampered, IDENTITIES, ARTIFACTS)
    # state artifacts on disk must match the bound hashes
    with pytest.raises(InfrastructureError, match="bundle was "
                       "altered"):
        checkpoint.validate_resume(
            record, IDENTITIES, dict(ARTIFACTS, adapter="e" * 64))


def test_checkpoint_record_binds_state_artifacts(tmp_path):
    for name, content in (("adapter.safetensors", b"AA"),
                          ("optimizer.pt", b"BB"),
                          ("scheduler.pt", b"CC"), ("rng.json", b"DD")):
        (tmp_path / name).write_bytes(content)
    hashes = checkpoint.hash_state_artifacts(tmp_path, {
        "adapter": "adapter.safetensors", "optimizer": "optimizer.pt",
        "scheduler": "scheduler.pt", "rng": "rng.json"})
    assert hashes["scaler"] is None
    record = _record(state_artifact_hashes=hashes)
    assert record["state_artifact_sha256"] == hashes
    with pytest.raises(InfrastructureError, match="missing required"):
        checkpoint.hash_state_artifacts(tmp_path, {
            "adapter": "adapter.safetensors"})
    with pytest.raises(InfrastructureError, match="absent from the "
                       "bundle"):
        checkpoint.hash_state_artifacts(tmp_path, {
            "adapter": "nope.safetensors", "optimizer": "optimizer.pt",
            "scheduler": "scheduler.pt", "rng": "rng.json"})


def test_checkpoint_record_refuses_off_boundary_counters():
    with pytest.raises(InfrastructureError, match="v1 boundary"):
        _record(counters={"generated_groups": 3, "consumed_groups": 2,
                          "optimizer_updates": 1,
                          "sampled_completions": 24})


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
    assert sorted(g["global_group_index"] for g in
                  merged["trajectory"]) == list(range(6))


def test_merge_segments_enforces_identity_and_linkage():
    first = _segment("s1", "aborted", 0, 3, range(5))
    # complete segment with rows beyond its own cutoff: impossible
    with pytest.raises(InfrastructureError, match="impossible "
                       "history"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 0, 3, range(5))])
    # wrong parent linkage
    with pytest.raises(InfrastructureError, match="linkage broken"):
        checkpoint.merge_segments(
            [first, _segment("s2", "complete", 3, 6, range(3, 6),
                             parent="ckpt-other")])
    # resume counter disagrees with the parent checkpoint
    with pytest.raises(InfrastructureError, match="parent[\\s\\S]*"
                       "recorded"):
        checkpoint.merge_segments(
            [first, _segment("s2", "complete", 4, 6, range(4, 6),
                             parent=first["checkpoint_id"])])
    # config change is a fork
    with pytest.raises(InfrastructureError, match="FORK"):
        checkpoint.merge_segments(
            [first, _segment("s2", "complete", 3, 6, range(3, 6),
                             parent=first["checkpoint_id"],
                             config="other")])
    # mixed run ids
    with pytest.raises(InfrastructureError, match="one run identity"):
        checkpoint.merge_segments(
            [first, _segment("s2", "complete", 3, 6, range(3, 6),
                             parent=first["checkpoint_id"],
                             run_id="p1")])
    # first segment must start from scratch
    with pytest.raises(InfrastructureError, match="from scratch"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 1, 3, range(1, 3))])
    # duplicates and non-terminal statuses
    with pytest.raises(InfrastructureError, match="not contiguous"):
        checkpoint.merge_segments(
            [_segment("s1", "complete", 0, 3, [0, 2, 2])])
    with pytest.raises(InfrastructureError, match="non-terminal"):
        checkpoint.merge_segments(
            [_segment("s1", "running", 0, 0, [])])


def test_rng_capture_is_complete_and_restorable():
    import numpy
    # 214_s reproduction: two states differing ONLY in position must
    # capture differently
    numpy.random.seed(11)
    numpy.random.rand(2)
    state_pos2 = checkpoint.capture_rng_state()
    numpy.random.seed(11)
    numpy.random.rand(4)
    state_pos4 = checkpoint.capture_rng_state()
    assert charter.content_sha256(state_pos2) != \
        charter.content_sha256(state_pos4)
    # capture -> restore -> identical draws on every stream
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
