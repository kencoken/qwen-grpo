"""Routing development-track infrastructure battery (211_f §15 step 3):
namespaces + disjointness, charter constants + natural mixture +
execution digest, dev surface materialization/loading, the frozen
probe-selection rule, c_fixed_dev, stratified telemetry with C1/C2,
the append-only ledger with reserve accounting, and the v1
checkpoint/resume contract."""

import json

import pytest

from tasks.conductor import program
from tasks.conductor.cache import WorkerCompletionCache
from tasks.conductor.pool_runtime import FourWorkerRuntime
from tasks.conductor.profiles import DEFAULT_PROFILE
from tasks.conductor.stage1_replay import pair_table_from_surface
from tasks.conductor.types import CELL_IDS, NAMESPACES, InfrastructureError
from tasks.routing import charter, checkpoint, cohorts, dev_support, ledger
from tasks.routing import telemetry

from test_conductor_executor import perfect_worker
from test_conductor_pool_runtime import FakeFourPool, profile_with

DEV_COHORT = {"lookup_atomic": [0], "code_atomic": [0, 1]}
DEV_RENDERERS = ("resource_first", "goal_first")


# --- namespaces (211_f §3) ----------------------------------------------------

def test_dev_namespaces_registered_with_charter_caps():
    charter.verify_namespace_registration()
    for namespace in charter.DEV_NAMESPACES:
        assert namespace in NAMESPACES


def test_namespace_id_prefixes_have_zero_intersection():
    """The 191_f/211_f disjointness test: regenerate id prefixes across
    ALL namespaces and check zero intersection — both the full ids and
    the seed-derived hex8 material."""
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

def test_natural_mixture_weights_are_the_130s_target():
    observations = []
    # 2 cells; cell A has 1 latent with 2 renderers, cell B has 2
    # latents with 1 renderer each.
    observations.append({"observation_id": "a1r1", "cell_id": "A",
                         "latent_program_id": "A:l1"})
    observations.append({"observation_id": "a1r2", "cell_id": "A",
                         "latent_program_id": "A:l1"})
    observations.append({"observation_id": "b1r1", "cell_id": "B",
                         "latent_program_id": "B:l1"})
    observations.append({"observation_id": "b2r1", "cell_id": "B",
                         "latent_program_id": "B:l2"})
    for obs in observations:
        obs["renderer_id"] = "x"
    weights = charter.natural_mixture_weights(observations)
    assert weights["a1r1"] == weights["a1r2"] == pytest.approx(0.25)
    assert weights["b1r1"] == weights["b2r1"] == pytest.approx(0.25)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_natural_mixture_refuses_duplicates_and_empty():
    with pytest.raises(InfrastructureError, match="empty"):
        charter.natural_mixture_weights([])
    obs = {"observation_id": "x", "cell_id": "A",
           "latent_program_id": "A:l1", "renderer_id": "r"}
    with pytest.raises(InfrastructureError, match="duplicate"):
        charter.natural_mixture_weights([obs, dict(obs)])


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


# --- dev surfaces (211_f §4) ----------------------------------------------------

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


@pytest.fixture
def dev_surface_dir(tmp_path):
    rt = dev_fake_rt(tmp_path, sabotage_w3=True)
    declaration = dev_support.build_dev_declaration(
        rt.pool, tag="routing-dev-support-test-v1",
        namespace="routing_dev", cohort=DEV_COHORT,
        renderers=DEV_RENDERERS, visibility="private")
    out = tmp_path / "surface"
    dev_support.materialize_dev_support(rt, declaration, out)
    rt.close()
    return out


def test_dev_cohort_validation_fails_closed():
    cases = [
        ({"namespace": "train"}, "not a development namespace"),
        ({"cohort": {}}, "empty development cohort"),
        ({"cohort": {"nope": [0]}}, "unknown cell"),
        ({"cohort": {"code_atomic": [0, 0]}}, "duplicate latent index"),
        ({"cohort": {"code_atomic": [2000]}}, "outside"),
        ({"cohort": {"code_atomic": [True]}}, "non-integer"),
        ({"renderers": ()}, "no renderers"),
        ({"renderers": ("resource_first", "resource_first")},
         "distinct members"),
        ({"visibility": "public"}, "unknown visibility"),
    ]
    base = {"namespace": "routing_dev", "cohort": {"code_atomic": [0]},
            "renderers": ("resource_first",), "visibility": "private"}
    for override, match in cases:
        kwargs = {**base, **override}
        with pytest.raises(InfrastructureError, match=match):
            dev_support.validate_dev_cohort(
                kwargs["namespace"], kwargs["cohort"],
                kwargs["renderers"], kwargs["visibility"])


def test_dev_observations_live_in_the_dev_namespace():
    observations = dev_support.dev_cohort_observations(
        "routing_dev", DEV_COHORT, DEV_RENDERERS, "private")
    assert len(observations) == 3 * len(DEV_RENDERERS)
    for obs in observations:
        assert ":routing_dev:" in obs["observation_id"]


def test_dev_surface_materialize_load_roundtrip(dev_surface_dir):
    loaded = dev_support.load_dev_surface(dev_surface_dir)
    surface = loaded["surface"]
    # 1 lookup obs x 4 + 2 code obs x 4, per renderer
    assert len(surface) == (1 * 4 + 2 * 4) * len(DEV_RENDERERS)
    assert set(surface.values()) <= {0.5, 1.0}
    assert loaded["declaration"]["namespace"] == "routing_dev"
    # sabotaged worker 3: the code family-correct w3 variant scores 0.5
    cell_of = {obs["observation_id"]: obs["cell_id"]
               for obs in loaded["observations"]}
    table = pair_table_from_surface(surface, cell_of)
    directions = {entry["direction"] for entry in table.values()}
    assert directions == {2}


def test_dev_surface_loader_fails_closed(dev_surface_dir, tmp_path):
    # payoff tamper (rehash payoffs so only the re-score check fires)
    import hashlib
    payoffs = dev_surface_dir / "payoffs.jsonl"
    rows = [json.loads(line) for line in
            payoffs.read_text().splitlines()]
    rows[0]["payoff"] = 0.0
    payoffs.write_text("".join(json.dumps(r, sort_keys=True) + "\n"
                               for r in rows))
    manifest_path = dev_surface_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["payoffs_sha256"] = hashlib.sha256(
        payoffs.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=1,
                                        sort_keys=True) + "\n")
    with pytest.raises(InfrastructureError, match="re-scored"):
        dev_support.load_dev_surface(dev_surface_dir)


def test_dev_surface_refuses_wrong_declaration(dev_surface_dir):
    declaration_path = dev_surface_dir / "declaration.json"
    declaration = json.loads(declaration_path.read_text())
    declaration["cohort"]["code_atomic"] = [0]
    declaration_path.write_text(json.dumps(declaration, indent=1,
                                           sort_keys=True) + "\n")
    with pytest.raises(InfrastructureError, match="different "
                       "declaration|does not match"):
        dev_support.load_dev_surface(dev_surface_dir)


def test_direction_yields_disclose_every_observation(dev_surface_dir):
    loaded = dev_support.load_dev_surface(dev_surface_dir)
    yields = dev_support.direction_yields(loaded["surface"],
                                          loaded["observations"])
    per_obs = yields["per_observation"]
    assert len(per_obs) == len(loaded["observations"])
    assert yields["per_cell"]["code_atomic"]["w2_favoured"] == \
        2 * len(DEV_RENDERERS)
    assert yields["per_cell"]["lookup_atomic"]["no_pair"] == \
        len(DEV_RENDERERS)


def test_c_fixed_dev_selection_and_record(dev_surface_dir):
    loaded = dev_support.load_dev_surface(dev_surface_dir)
    record = dev_support.select_c_fixed_dev(
        loaded["surface"], loaded["observations"],
        {"payoffs_sha256": loaded["manifest"]["payoffs_sha256"]})
    # sabotaged worker 3 loses every code observation
    assert record["c_fixed_dev"] == 2
    assert record["tie"] is False
    assert record["candidate_scores"]["2"] == 1.0
    assert record["candidate_scores"]["3"] == 0.5
    assert record["development_only"] is True
    assert record["record_sha256"] == charter.content_sha256(
        {k: v for k, v in record.items() if k != "record_sha256"})


def test_c_fixed_dev_refuses_without_code_observations():
    with pytest.raises(InfrastructureError, match="undefined"):
        dev_support.select_c_fixed_dev(
            {}, [{"observation_id": "x", "cell_id": "lookup_atomic",
                  "latent_program_id": "l"}], {})


# --- probe rule (211_f §4, 210_s issue 4) ----------------------------------------

def _frozen_rule(**overrides):
    kwargs = dict(namespace="routing_dev", prefix_length_per_cell=1,
                  renderers=DEV_RENDERERS, visibility="private",
                  group_size=8, groups_per_observation=2)
    kwargs.update(overrides)
    return cohorts.freeze_probe_rule(**kwargs)


def test_probe_rule_freeze_and_apply_are_deterministic():
    frozen = _frozen_rule()
    assert frozen["rule_sha256"] == _frozen_rule()["rule_sha256"]
    spec = cohorts.probe_cohort_spec(frozen)
    assert set(spec["cohort"]) == set(CELL_IDS)
    assert all(v == [0] for v in spec["cohort"].values())


def test_probe_rule_schema_is_closed_against_outcome_smuggling():
    frozen = _frozen_rule()
    smuggled = {"rule": {**frozen["rule"],
                         "preferred_direction": "w2_favoured"},
                "rule_sha256": charter.content_sha256(
                    {**frozen["rule"],
                     "preferred_direction": "w2_favoured"})}
    with pytest.raises(InfrastructureError, match="closed schema"):
        cohorts.validate_probe_rule(smuggled)
    tampered = {"rule": dict(frozen["rule"]),
                "rule_sha256": "0" * 64}
    with pytest.raises(InfrastructureError, match="rehash"):
        cohorts.validate_probe_rule(tampered)


def test_probe_rule_application_fails_closed_on_under_coverage():
    frozen = _frozen_rule(prefix_length_per_cell=2)
    observations = dev_support.dev_cohort_observations(
        "routing_dev", {cell: [0] for cell in CELL_IDS},
        DEV_RENDERERS, "private")
    declaration = {
        "namespace": "routing_dev", "visibility": "private",
        "observations": [
            {"observation_id": obs["observation_id"],
             "cell_id": obs["cell_id"],
             "renderer_id": obs["renderer_id"]}
            for obs in observations]}
    with pytest.raises(InfrastructureError, match="under-covers"):
        cohorts.apply_probe_rule(frozen, declaration)


def test_probe_cohort_binding_adds_only_hashes():
    frozen = _frozen_rule()
    observations = dev_support.dev_cohort_observations(
        "routing_dev", {cell: [0] for cell in CELL_IDS},
        DEV_RENDERERS, "private")
    declaration = {
        "namespace": "routing_dev", "visibility": "private",
        "observations": [
            {"observation_id": obs["observation_id"],
             "cell_id": obs["cell_id"],
             "renderer_id": obs["renderer_id"]}
            for obs in observations]}
    bound = cohorts.bind_probe_cohort(frozen, declaration,
                                      {"payoffs_sha256": "ab" * 32})
    assert bound["rule_sha256"] == frozen["rule_sha256"]
    assert len(bound["observation_ids"]) == \
        len(CELL_IDS) * len(DEV_RENDERERS)
    assert bound["observation_ids"] == \
        cohorts.apply_probe_rule(frozen, declaration)


# --- telemetry (211_f §7) ---------------------------------------------------------

OBS = "code_atomic:routing_dev:00000:abcdef01:resource_first:private"
META = {"cell_id": "code_atomic", "renderer_id": "resource_first",
        "latent_program_id": "code_atomic:routing_dev:00000:abcdef01"}
PAIR = {"cell_id": "code_atomic", "assignment_w2": [2],
        "assignment_w3": [3], "payoff_w2": 1.0, "payoff_w3": 0.5,
        "distinct_payoff": True, "direction": 2}
SURFACE = {(OBS, (0,)): 0.5, (OBS, (1,)): 0.5, (OBS, (2,)): 1.0,
           (OBS, (3,)): 0.5}


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
    stats = telemetry.group_stats(group, meta=META, pair_entry=PAIR,
                                  surface=SURFACE, c_fixed_dev=2)
    assert stats["direction"] == "w2_favoured"
    assert stats["format_contrast"] is True
    assert stats["semantic_contrast"] is True
    assert stats["direct_contrast"] is True
    assert stats["variant_hits"] == {"w2": 1, "w3": 1}
    # C1: malformed scores 0 and STAYS in the denominator
    assert stats["c1_mean"] == pytest.approx((0 + 1 + 1 + 0) / 4)
    # C2: eligible = code choice in {2,3} (w2 + w3 rows only);
    # the wrong-family 0 row is NOT eligible but stays in ModelAcc-
    # style views via c1; optimal = the payoff winner w2
    assert stats["c2_eligible"] == 2
    assert stats["c2_optimal"] == 1
    # ScaleLift vs c_fixed_dev=2: w2 row collapses to itself (0);
    # w3 row: 0.5 - payoff(w2)=1.0 -> -0.5; wrong family unchanged
    # (0); malformed contributes 0
    assert stats["scale_lift_mean"] == pytest.approx(-0.5 / 4)
    assert stats["zero_variance_level"] is None


def test_group_stats_zero_variance_and_tied_pairs():
    tied = dict(PAIR, payoff_w3=1.0, distinct_payoff=False,
                direction=None)
    group = {"observation_id": OBS, "completions": [
        _completion(True, [2], 1.0)] * 8}
    stats = telemetry.group_stats(group, meta=META, pair_entry=tied,
                                  surface=SURFACE, c_fixed_dev=2)
    assert stats["direction"] == "tied"
    assert stats["zero_variance_level"] == "1"
    assert stats["c2_optimal"] is None       # tied: never scored
    assert stats["c2_eligible"] == 8
    assert stats["direct_contrast"] is False


def test_group_stats_refuses_missing_collapse_row():
    surface = {(OBS, (2,)): 1.0}   # no (3,) row
    group = {"observation_id": OBS, "completions": [
        _completion(True, [2], 1.0)]}
    with pytest.raises(InfrastructureError, match="collapse row"):
        telemetry.group_stats(group, meta=META, pair_entry=PAIR,
                              surface=surface, c_fixed_dev=3)


def test_group_stats_refuses_off_ladder_reward():
    group = {"observation_id": OBS, "completions": [
        _completion(True, [2], 0.75)]}
    with pytest.raises(InfrastructureError, match="frozen ladder"):
        telemetry.group_stats(group, meta=META, pair_entry=PAIR,
                              surface=SURFACE, c_fixed_dev=2)


def test_aggregate_stratified_reports_counts_and_denominators():
    groups = []
    for reward, assignment in ((1.0, [2]), (0.5, [3])):
        group = {"observation_id": OBS, "completions": [
            _completion(True, assignment, reward)] * 4}
        groups.append(telemetry.group_stats(
            group, meta=META, pair_entry=PAIR, surface=SURFACE,
            c_fixed_dev=2))
    report = telemetry.aggregate_stratified(groups)
    total = report["total"]
    assert total["groups"] == 2
    assert total["valid"] == {"count": 8, "denominator": 8, "rate": 1.0}
    assert total["zero_variance"]["all_1"]["count"] == 1
    assert total["zero_variance"]["all_0.5"]["count"] == 1
    assert total["direct_contrast"]["count"] == 0
    assert total["c2_optimal_specialist"] == \
        {"count": 4, "denominator": 8, "rate": 0.5}
    key = "code_atomic|resource_first|w2_favoured"
    assert key in report["by_cell_renderer_direction"]
    with pytest.raises(InfrastructureError, match="no groups"):
        telemetry.aggregate_stratified([])


# --- ledger (211_f §§10, 12) -------------------------------------------------------

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
    first = ledger.append_ledger_entry(_entry(), path)
    second = ledger.append_ledger_entry(
        _entry(kind="reserve_update", reserve=_reserve()), path)
    entries = ledger.read_ledger(path)
    assert [e["entry_sha256"] for e in entries] == \
        [first["entry_sha256"], second["entry_sha256"]]
    assert entries[1]["previous_entry_sha256"] == first["entry_sha256"]


def test_ledger_detects_edits_and_removals(tmp_path):
    path = tmp_path / "ledger.md"
    ledger.append_ledger_entry(_entry(), path)
    ledger.append_ledger_entry(_entry(question="q2"), path)
    text = path.read_text()
    with open(path, "w") as handle:
        handle.write(text.replace('"question": "q"',
                                  '"question": "edited"'))
    with pytest.raises(InfrastructureError, match="edited"):
        ledger.read_ledger(path)
    # removal: keep only the second block
    blocks = text.split("\n## entry ")
    with open(path, "w") as handle:
        handle.write(blocks[0] + "\n## entry " + blocks[2])
    with pytest.raises(InfrastructureError, match="chain broken"):
        ledger.read_ledger(path)


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


def test_reserve_requires_its_numerical_basis(tmp_path):
    path = tmp_path / "ledger.md"
    incomplete = {"status": "provisional", "r_cycle_gpu_hours": 6.0}
    with pytest.raises(InfrastructureError, match="numerical basis"):
        ledger.append_ledger_entry(
            _entry(kind="reserve_update", reserve=incomplete), path)
    ledger.append_ledger_entry(
        _entry(kind="reserve_update", reserve=_reserve()), path)


def test_envelope_state_charges_allocation_until_closed_out(tmp_path):
    path = tmp_path / "ledger.md"
    ledger.append_ledger_entry(
        _entry(budget_allocated_gpu_hours=3.0), path)
    ledger.append_ledger_entry(
        _entry(budget_allocated_gpu_hours=3.0,
               budget_consumed_gpu_hours=1.25), path)
    ledger.append_ledger_entry(
        _entry(kind="reserve_update", reserve=_reserve(),
               budget_allocated_gpu_hours=0.0), path)
    state = ledger.envelope_state(ledger.read_ledger(path))
    assert state["consumed_gpu_hours"] == pytest.approx(4.25)
    assert state["remaining_gpu_hours"] == pytest.approx(60 - 4.25)
    assert state["reserve"]["status"] == "provisional"


def test_admissibility_ordinary_and_closure():
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
    with pytest.raises(InfrastructureError, match="no reserve"):
        ledger.check_launch_admissible(
            remaining_gpu_hours=20.0, launch_max_gpu_hours=1.0,
            reserve=None)


# --- checkpoint/resume (211_f §11) ---------------------------------------------------

IDENTITIES = {key: f"{key}-value" for key in checkpoint.IDENTITY_KEYS}


def _accountant_at_boundary():
    accountant = checkpoint.GroupAccountant()
    accountant.record_generation(groups=2, completions=16)
    accountant.record_update(consumed_groups=2)
    return accountant


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
    assert counters["optimizer_updates"] == 2
    with pytest.raises(InfrastructureError, match="never generated"):
        accountant.record_update(consumed_groups=1)


def test_checkpoint_record_roundtrip_and_fail_closed_resume():
    counters = _accountant_at_boundary().authorize_checkpoint()
    record = checkpoint.build_checkpoint_record(
        identities=IDENTITIES, counters=counters,
        rng_state={"python": [1], "numpy": [2], "torch_cpu": [3],
                   "torch_cuda": None},
        sampler_position={"next_global_group_index": 2},
        run_id="p0", segment_id="p0-seg1", parent_checkpoint=None)
    restored = checkpoint.validate_resume(record, IDENTITIES)
    assert restored["counters"]["consumed_groups"] == 2
    assert restored["sampler_position"] == \
        {"next_global_group_index": 2}
    changed = dict(IDENTITIES, prompt_sha256="other")
    with pytest.raises(InfrastructureError, match="prompt_sha256"):
        checkpoint.validate_resume(record, changed)
    tampered = dict(record)
    tampered["counters"] = dict(record["counters"],
                                optimizer_updates=99)
    with pytest.raises(InfrastructureError, match="rehash"):
        checkpoint.validate_resume(tampered, IDENTITIES)


def test_checkpoint_record_refuses_off_boundary_counters():
    with pytest.raises(InfrastructureError, match="v1 boundary"):
        checkpoint.build_checkpoint_record(
            identities=IDENTITIES,
            counters={"generated_groups": 3, "consumed_groups": 2,
                      "optimizer_updates": 1,
                      "sampled_completions": 24},
            rng_state={"python": [1], "numpy": [2], "torch_cpu": [3],
                       "torch_cuda": None},
            sampler_position={"next_global_group_index": 2},
            run_id="p0", segment_id="s", parent_checkpoint=None)


def test_merge_segments_excludes_aborted_tail_but_preserves_it():
    segments = [
        {"segment_id": "s1", "status": "aborted",
         "checkpoint_consumed_groups": 3,
         "groups": [{"global_group_index": i} for i in range(5)]},
        {"segment_id": "s2", "status": "complete",
         "checkpoint_consumed_groups": 6,
         "groups": [{"global_group_index": i} for i in range(3, 6)]},
    ]
    merged = checkpoint.merge_segments(segments)
    assert merged["merged_groups"] == 6
    assert [g["global_group_index"] for g in
            merged["excluded_aborted_evidence"]] == [3, 4]
    assert sorted(g["global_group_index"] for g in
                  merged["trajectory"]) == list(range(6))


def test_merge_segments_refuses_gaps_and_duplicates():
    with pytest.raises(InfrastructureError, match="duplicates"):
        checkpoint.merge_segments([
            {"segment_id": "s", "status": "complete",
             "checkpoint_consumed_groups": 2,
             "groups": [{"global_group_index": 0},
                        {"global_group_index": 0}]}])
    with pytest.raises(InfrastructureError, match="missing groups"):
        checkpoint.merge_segments([
            {"segment_id": "s", "status": "complete",
             "checkpoint_consumed_groups": 3,
             "groups": [{"global_group_index": 0},
                        {"global_group_index": 2}]}])
    with pytest.raises(InfrastructureError, match="start at group 0"):
        checkpoint.merge_segments([
            {"segment_id": "s", "status": "complete",
             "checkpoint_consumed_groups": 2,
             "groups": [{"global_group_index": 1}]}])
    with pytest.raises(InfrastructureError, match="non-terminal"):
        checkpoint.merge_segments([
            {"segment_id": "s", "status": "running",
             "checkpoint_consumed_groups": 0, "groups": []}])


def test_isolated_rng_restores_every_stream():
    import numpy
    import torch
    random_module = __import__("random")
    with checkpoint.isolated_rng():
        pass
    before = (random_module.random(), numpy.random.rand(),
              torch.rand(1).item())
    # replaying the same draws after an isolated block that consumed
    # randomness must give identical values
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
    del before


def test_capture_rng_state_is_serializable():
    state = checkpoint.capture_rng_state()
    json.dumps(state)
    assert set(state) == {"python", "numpy", "torch_cpu", "torch_cuda"}
