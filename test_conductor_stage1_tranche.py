"""Unit-3 tests for the tranche runner, D registry, artifacts, verdict,
and the executable B replay contract (142_s findings 1-4; revised per
145_s: 256 completions, not_ruled_out naming, strict schemas, execution
binding, corrected agreement criterion, cluster-level DGP variance).

Includes the 145_s-requested refusal probes: empty B, mixed manifests,
1/1 agreement, impossible counts, and incomplete replay outputs. No
frozen grid, coverage scenario, or GPU replay executes here.
"""

import json

import numpy as np
import pytest

from tasks.conductor import stage1, stage1_validation as sv
from tasks.conductor import stage1_replay as sr
from tasks.conductor import stage1_tranche as st
from tasks.conductor.grpo_smoke import STAGE0C_LAUNCH_PROFILE
from tasks.conductor.types import InfrastructureError

FEW = sr.REPLAY_CONTRACT["prompt_fewshot_sha256"]
SO = sr.REPLAY_CONTRACT["prompt_schema_only_sha256"]

def _env_manifest():
    import hashlib
    from tasks.conductor.profiles import canonical_json
    from tasks.conductor.stage1_manifest import (stage1_source_digest,
                                                 stage1_source_files)
    body = {"manifest": "stage1-environment-v2", "git_commit": "t" * 40,
            "git_dirty": 0, "uv_lock_sha256": "u" * 64,
            "stage1_source_sha256": stage1_source_digest(),
            "stage1_source_files": list(stage1_source_files()),
            "gpu": "test-gpu", "torch": "test",
            "numpy": "test", "scipy": "test"}
    sha = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    return {**body, "execution_manifest_sha256": sha}


ENV = _env_manifest()
EXEC_SHA = ENV["execution_manifest_sha256"]


def _support_rows():
    """18 synthetic support observations: 3 pair-bearing cells x 1 obs
    + 15 code-free fillers, positional order == sorted nodes."""
    rows = {}
    pair_cells = [("code_atomic", ["n1"]),
                  ("math_code", ["n1", "n2"]),
                  ("fork_join", ["n1", "n2", "n3"])]
    for idx, (cell, positions) in enumerate(pair_cells):
        oid = (f"{cell}:worker_dev:{idx:05d}:aaaaaaa{idx}:"
               "resource_first:private")
        rows[oid] = {"cell_id": cell, "num_steps": len(positions),
                     "positions": positions}
    for i in range(15):
        oid = (f"lookup_atomic:worker_dev:{i + 10:05d}:bbbbbb{i:02x}:"
               "goal_first:private")
        rows[oid] = {"cell_id": "lookup_atomic", "num_steps": 1,
                     "positions": ["n1"]}
    return rows


def _surface(rows):
    surface = {}
    payoffs = {"code_atomic": (0.5, 1.0),      # w3 direction
               "math_code": (1.0, 1.0),        # tie
               "fork_join": (1.0, 0.5)}        # w2 direction
    for oid, meta in rows.items():
        pair = sr.family_correct_variants(meta["cell_id"])
        if pair is None:
            continue
        w2, w3 = pair
        p2, p3 = payoffs[meta["cell_id"]]
        surface[(oid, tuple(w2))] = p2
        surface[(oid, tuple(w3))] = p3
    return surface


def _b_evidence(k2=30, k3=30, exec_sha=None):
    """A complete, self-consistent B evidence bundle whose raw
    completions genuinely reparse to the counts."""
    import hashlib
    exec_sha = exec_sha or EXEC_SHA
    rows = _support_rows()
    surface = _surface(rows)
    cell_of = {o: m["cell_id"] for o, m in rows.items()}
    table = sr.pair_table_from_surface(surface, cell_of)
    meta = sr.observation_meta(rows)
    raw, counts = {}, {}
    for oid, m in sorted(rows.items()):
        pair = table.get(oid)
        for p in (FEW, SO):
            for i in range(sr.REPLAY_COMPLETIONS):
                if pair is not None and i < k2:
                    action = pair["assignment_w2"]
                elif pair is not None and i < k2 + k3:
                    action = pair["assignment_w3"]
                else:
                    raw[f"{oid}|{p}|{i:03d}"] = "malformed"
                    continue
                raw[f"{oid}|{p}|{i:03d}"] = json.dumps(
                    {"worker_ids": list(action)})
            if pair is not None:
                counts[f"{oid}|{p}"] = {"k2": k2, "k3": k3,
                                        "n": sr.REPLAY_COMPLETIONS}
    raw_text = json.dumps(dict(sorted(raw.items())), ensure_ascii=False)
    raw_sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    rr = {f"{o}|{p}": "a" * 64 for o in sorted(rows)
          for p in (FEW, SO)}
    manifest = sr.build_replay_manifest(exec_sha, rows, rr, table)
    artifact = st.finalize_artifact(
        "B", exec_sha, counts,
        extra={"pair_table": manifest["eligible_pairs"],
               "obs_meta": meta,
               "replay_manifest_sha256":
                   manifest["replay_manifest_sha256"],
               "raw_completions_sha256": raw_sha})
    def loader():
        return surface, rows, rr
    return {"artifact": artifact, "replay_manifest": manifest,
            "raw_completions_text": raw_text, "loader": loader,
            "surface": surface, "support_rows": rows}



# --- exact grid registries ------------------------------------------------------

def test_registry_cardinalities():
    reg = st.expected_result_keys()
    assert len(st.a_position_cells()) == 48
    assert len(st.a_router_cells()) == 24
    assert len(st.c_cells()) == 120
    assert len(reg["A_position"]) == 48
    assert len(reg["A_router"]) == 24
    assert len(reg["C"]) == 120
    assert len(reg["D"]) == 8
    assert not (reg["A_position"] & reg["A_router"])


def test_d_registry_frozen_shape():
    ids = [s["id"] for s in st.D_SCENARIOS]
    assert len(ids) == 8 <= sv.COVERAGE_SCENARIO_CAP
    assert ids == sorted(ids)
    for s in st.D_SCENARIOS:
        assert s["error_decision"] in ("pass", "undercover")
        assert 0 < s["allocated_alpha"] < 0.20
        assert callable(s["dgp"])
    assert any("seq_null_ordinary" in i for i in ids)
    assert any("seq_null_fork" in i for i in ids)
    assert any("equiv_boundary_plus" in i for i in ids)
    assert any("equiv_boundary_minus" in i for i in ids)
    assert any("pilot" in i for i in ids)
    assert sum("persist" in i for i in ids) == 3


def test_d_scenarios_execute_one_trial_each():
    for s in st.D_SCENARIOS:
        decision = s["dgp"](123456789)
        assert decision in ("pass", "fail", "unresolved", "not_pass",
                            "cover", "undercover")


def test_dgp_rows_have_cluster_level_variance():
    # 145_s finding 4: one cluster-level draw carried through all
    # renderer rows — perfect renderer correlation, cluster-mean SD =
    # sigma exactly (not sigma/sqrt(3))
    rng = np.random.default_rng(11)
    rows = st._tp_rows(rng, 0.15, 0.75, 4_000)
    assert np.array_equal(rows[:, 0], rows[:, 1])
    assert np.array_equal(rows[:, 0], rows[:, 2])
    assert rows.mean(axis=1).std(ddof=1) == pytest.approx(0.75,
                                                          abs=0.03)


# --- agreement gate (145_s finding 3) -------------------------------------------

def test_agreement_criterion_wilson_999_of_1000():
    # the frozen criterion: one-sided 95% Wilson LB >= 0.995 on exactly
    # 1,000 datasets — 999/1000 is the minimum pass; 995/1000 fails
    assert st.agreement_passes({"agree_count": 1_000,
                                "datasets": 1_000})
    assert st.agreement_passes({"agree_count": 999, "datasets": 1_000})
    assert not st.agreement_passes({"agree_count": 998,
                                    "datasets": 1_000})
    assert not st.agreement_passes({"agree_count": 995,
                                    "datasets": 1_000})


def test_agreement_rejects_wrong_sample_sizes():
    with pytest.raises(st.TrancheError, match="exactly"):
        st.agreement_passes({"agree_count": 1, "datasets": 1})  # 1/1
    with pytest.raises(st.TrancheError, match="exactly"):
        st.agreement_passes({"agree_count": 500, "datasets": 500})
    with pytest.raises(st.TrancheError, match="malformed"):
        st.agreement_passes({"agree_count": 1_001, "datasets": 1_000})
    with pytest.raises(st.TrancheError, match="malformed"):
        st.agreement_passes({"agree_count": 999.0, "datasets": 1_000})


def test_agreement_families_cover_reduced_replicate_scenarios():
    # the gate's datasets must represent D1-D5 (stake ordinary/fork,
    # equivalence, pilot-unequal), not only ordinary stakes
    assert set(st._AGREEMENT_FAMILIES) == {
        "stake_ordinary", "stake_fork", "equivalence", "pilot_unequal"}
    # each family's decision function runs (tiny replicates, throwaway)
    rng = np.random.default_rng(12)
    assert st._agreement_decision(
        "stake_ordinary", [st._tp_rows(rng, 0.3, 0.3, 500)], 50, 1) \
        in ("pass", "fail", "unresolved")
    assert st._agreement_decision(
        "equivalence", [st._tp_rows(rng, 0.0, 0.3, 500)], 50, 1) \
        in ("pass", "fail", "unresolved")
    assert st._agreement_decision(
        "pilot_unequal", [st._tp_rows(rng, 0.0, 0.4, n)
                          for n in (12, 12, 6)], 50, 1) \
        in ("pass", "not_pass")


def test_agreement_gate_blocks_bootstrap_scenarios():
    bad = {"agree_count": 900, "datasets": 1_000}
    with pytest.raises(st.TrancheError, match="agreement gate"):
        st.run_d_battery(bad)


def test_deterministic_equivalence_set_passes_production_inference():
    # the required deterministic 10,000-replicate equivalence check
    # (145_s finding 3): constant data, analytically known decisions,
    # exact match required — raises on any mismatch
    results = st.run_deterministic_equivalence_set()
    assert results == {
        "inside_zero": "pass", "boundary_plus": "fail",
        "boundary_minus": "fail", "outside_plus": "fail",
        "outside_minus": "fail", "inside_edge": "pass"}


# --- artifacts (145_s finding 2) --------------------------------------------------

def test_artifact_requires_valid_exec_identity_and_schema():
    with pytest.raises(st.TrancheError, match="64 lowercase hex"):
        st.finalize_artifact("A", "short", {})
    with pytest.raises(st.TrancheError, match="unknown artifact"):
        st.finalize_artifact("X", EXEC_SHA, {})
    # wrong field set for the artifact kind refuses at finalize
    with pytest.raises(st.TrancheError, match="fields"):
        st.finalize_artifact("A", EXEC_SHA,
                             {"k": {"pass_count": 1, "trials": 10}})
    # reserved-field shadowing refuses
    ok_row = {"pass_count": 1, "fail_count": 1, "unresolved_count": 8,
              "trials": 10}
    with pytest.raises(st.TrancheError, match="reserved"):
        st.finalize_artifact("A", EXEC_SHA, {"k": ok_row},
                             extra={"results": {}})


def _a_artifact(exec_sha=EXEC_SHA, tamper_key=None):
    reg = st.expected_result_keys()
    res = {}
    for key in reg["A_position"] | reg["A_router"]:
        res[key] = {"pass_count": 9_500, "fail_count": 0,
                    "unresolved_count": 500, "trials": 10_000}
    if tamper_key:
        res[tamper_key] = {"pass_count": 9_500, "fail_count": 100,
                           "unresolved_count": 500, "trials": 10_000}
    return st.finalize_artifact("A", exec_sha, res)


def test_load_rejects_impossible_counts_and_wrong_trials():
    key = next(iter(st.expected_result_keys()["A_position"]))
    bad = _a_artifact(tamper_key=key)  # counts sum to 10,100
    with pytest.raises(st.TrancheError, match="impossible counts"):
        st.load_artifact(bad, "A",
                         st.expected_result_keys()["A_position"]
                         | st.expected_result_keys()["A_router"],
                         EXEC_SHA)
    reg = st.expected_result_keys()
    res = {k: {"pass_count": 90, "fail_count": 0,
               "unresolved_count": 10, "trials": 100}  # wrong trials
           for k in reg["D"]}
    with pytest.raises(st.TrancheError):
        st.finalize_artifact("D", EXEC_SHA, res)  # wrong fields for D
    d_res = {k: {"error_count": 0, "trials": 100} for k in reg["D"]}
    art = st.finalize_artifact("D", EXEC_SHA, d_res)
    with pytest.raises(st.TrancheError, match="frozen"):
        st.load_artifact(art, "D", reg["D"], EXEC_SHA)


def test_load_rejects_mixed_executions():
    # 145_s probe: artifacts from different executions may not combine
    art = _a_artifact(exec_sha="f" * 64)
    reg = st.expected_result_keys()
    with pytest.raises(st.TrancheError, match="foreign execution"):
        st.load_artifact(art, "A",
                         reg["A_position"] | reg["A_router"], EXEC_SHA)


# --- fail-closed aggregate verdict -------------------------------------------------

def _full_artifacts(c_power_pass=True, b_k=30):
    reg = st.expected_result_keys()
    a_res = {k: {"pass_count": 9_500, "fail_count": 0,
                 "unresolved_count": 500, "trials": 10_000}
             for k in reg["A_position"] | reg["A_router"]}
    c_res = {}
    for key in reg["C"]:
        theta = float(key.split("|")[4])
        n = sv.PERSISTENCE_TRIALS
        k = n if theta == 0.0 else (9_000 if c_power_pass else 1_440)
        c_res[key] = {"pass_count": k, "unresolved_count": 0,
                      "trials": n}
    d_res = {sc["id"]: {"error_count": 0,
                        "trials": sv.COVERAGE_OUTER_TRIALS}
             for sc in st.D_SCENARIOS}
    a = st.finalize_artifact("A", EXEC_SHA, a_res)
    c = st.finalize_artifact("C", EXEC_SHA, c_res)
    d = st.finalize_artifact(
        "D", EXEC_SHA, d_res,
        extra={"agreement": {"agree_count": 999, "datasets": 1_000}})
    return a, c, d, _b_evidence(k2=b_k, k3=b_k)


def test_aggregate_verdict_confirm_path():
    a, c, d, b = _full_artifacts()
    v = st.aggregate_verdict(a, c, d, b, env_manifest=ENV,
                         b_pinned_loader=b['loader'])
    assert v["confirm_possible"] is True
    assert v["D_failing"] == []
    assert v["B_directions_blocking"] == []


def test_aggregate_verdict_c_failure_predicted_path():
    a, c, d, b = _full_artifacts(c_power_pass=False)
    v = st.aggregate_verdict(a, c, d, b, env_manifest=ENV,
                         b_pinned_loader=b['loader'])
    assert v["confirm_possible"] is False
    assert len(v["C_power_failing"]) == 2


def test_aggregate_verdict_requires_valid_env_manifest():
    # 148_s finding 3: the identity must be the hash of a valid
    # environment manifest, not a bare matching string
    a, c, d, b = _full_artifacts()
    from tasks.conductor.stage1_manifest import ManifestError
    with pytest.raises(ManifestError, match="environment"):
        st.aggregate_verdict(a, c, d, b, env_manifest={
            **ENV, "execution_manifest_sha256": "e" * 64})
    with pytest.raises(ManifestError, match="stage1-environment-v2"):
        st.aggregate_verdict(a, c, d, b,
                             env_manifest={"manifest": "bogus"})


def test_aggregate_verdict_empty_or_partial_b_refuses():
    a, c, d, b = _full_artifacts()
    with pytest.raises(st.TrancheError, match="missing"):
        st.aggregate_verdict(a, c, d, {}, env_manifest=ENV,
                             b_pinned_loader=b["loader"])
    truncated = dict(b)
    raw = json.loads(b["raw_completions_text"])
    raw.pop(next(iter(raw)))
    truncated["raw_completions_text"] = json.dumps(
        dict(sorted(raw.items())), ensure_ascii=False)
    with pytest.raises(InfrastructureError, match="hash"):
        st.aggregate_verdict(a, c, d, truncated, env_manifest=ENV,
                             b_pinned_loader=b["loader"])


def test_aggregate_verdict_self_rehashed_b_refuses():
    # the 148_s attack: re-finalize the artifact with tampered counts
    # (valid self-hash) — the raw-completion recount must refuse it
    a, c, d, b = _full_artifacts()
    art = b["artifact"]
    tampered_counts = {k: {"k2": 0, "k3": 0, "n": sr.REPLAY_COMPLETIONS}
                       for k in art["results"]}
    rehashed = st.finalize_artifact(
        "B", EXEC_SHA, tampered_counts,
        extra={"pair_table": art["pair_table"],
               "obs_meta": art["obs_meta"],
               "replay_manifest_sha256": art["replay_manifest_sha256"],
               "raw_completions_sha256":
                   art["raw_completions_sha256"]})
    evil = dict(b, artifact=rehashed)
    with pytest.raises(InfrastructureError, match="reproduce"):
        st.aggregate_verdict(a, c, d, evil, env_manifest=ENV,
                             b_pinned_loader=b["loader"])


def test_aggregate_verdict_b_not_demonstrated_blocks():
    a, c, d, _ = _full_artifacts()
    b = _b_evidence(k2=0, k3=0)
    v = st.aggregate_verdict(a, c, d, b, env_manifest=ENV,
                         b_pinned_loader=b['loader'])
    assert v["B_directions_blocking"] == ["2", "3"]
    assert v["confirm_possible"] is False


def test_aggregate_verdict_mixed_executions_refuse():
    a, c, d, _ = _full_artifacts()
    foreign = _b_evidence(exec_sha="f" * 64)
    with pytest.raises((st.TrancheError, InfrastructureError)):
        st.aggregate_verdict(a, c, d, foreign, env_manifest=ENV,
                             b_pinned_loader=foreign["loader"])


def test_aggregate_verdict_d_agreement_failure():
    a, c, d, b = _full_artifacts()
    d_bad = st.finalize_artifact(
        "D", EXEC_SHA, {k: dict(v) for k, v in d["results"].items()},
        extra={"agreement": {"agree_count": 995, "datasets": 1_000}})
    v = st.aggregate_verdict(a, c, d_bad, b, env_manifest=ENV,
                             b_pinned_loader=b["loader"])
    assert "agreement" in v["D_failing"]
    assert v["confirm_possible"] is False


def test_verify_replay_evidence_regenerates_the_manifest():
    b = _b_evidence()
    # wrong contract inside a REHASHED replay manifest refuses: the
    # verifier regenerates the complete expected manifest internally
    bad = json.loads(json.dumps(b["replay_manifest"]))
    bad["contract"] = dict(bad["contract"], total_completions=2_304)
    body = {k: v for k, v in bad.items()
            if k != "replay_manifest_sha256"}
    import hashlib as _h
    from tasks.conductor.profiles import canonical_json
    bad["replay_manifest_sha256"] = _h.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    with pytest.raises(InfrastructureError, match="authoritative"):
        sr.verify_replay_evidence(
            b["artifact"], env_manifest=ENV, replay_manifest=bad,
            raw_completions_text=b["raw_completions_text"],
            pinned_loader=b["loader"])
    # 151_s probe: a rehashed manifest with ONE altered request hash
    # is refused against the regenerated authoritative values
    bad2 = json.loads(json.dumps(b["replay_manifest"]))
    rr_key = next(iter(bad2["rendered_request_sha256"]))
    bad2["rendered_request_sha256"][rr_key] = "b" * 64
    body2 = {k: v for k, v in bad2.items()
             if k != "replay_manifest_sha256"}
    bad2["replay_manifest_sha256"] = _h.sha256(
        canonical_json(body2).encode("utf-8")).hexdigest()
    with pytest.raises(InfrastructureError, match="authoritative"):
        sr.verify_replay_evidence(
            b["artifact"], env_manifest=ENV, replay_manifest=bad2,
            raw_completions_text=b["raw_completions_text"],
            pinned_loader=b["loader"])
    # a pinned surface that rederives a different pair table refuses
    surface2 = dict(b["surface"])
    key = next(k for k in surface2
               if k[0].startswith("code_atomic")
               and surface2[k] == 1.0)   # flip the w3 win -> direction
    surface2[key] = 0.0
    rows = b["support_rows"]

    def loader2():
        rr = {f"{o}|{p}": "a" * 64 for o in sorted(rows)
              for p in (FEW, SO)}
        return surface2, rows, rr
    with pytest.raises(InfrastructureError, match="authoritative"):
        sr.verify_replay_evidence(
            b["artifact"], env_manifest=ENV,
            replay_manifest=b["replay_manifest"],
            raw_completions_text=b["raw_completions_text"],
            pinned_loader=loader2)


def test_recount_handles_real_build_smoke_rows():
    # 151_s finding 1: positions arrive as JSON text from the REAL
    # support rows; the recount must parse them
    from tasks.conductor.grpo_task import build_smoke_rows
    rows = {r["observation_id"]: r for r in build_smoke_rows()}
    assert len(rows) == 18
    code_obs = next(o for o, r in rows.items()
                    if r["cell_id"] == "fork_join")
    meta = rows[code_obs]
    assert isinstance(meta["positions"], str)  # JSON text, the trap
    pair = sr.family_correct_variants("fork_join")
    positions = json.loads(meta["positions"])
    # craft one parseable completion selecting the w2 variant in the
    # REAL positional order
    by_node = dict(zip(sorted(positions), pair[0]))
    positional = [by_node[n] for n in positions]
    table = {code_obs: {"cell_id": "fork_join",
                        "assignment_w2": pair[0],
                        "assignment_w3": pair[1],
                        "distinct_payoff": 1, "direction": 2}}
    raw = {}
    for p in (FEW, SO):
        for i in range(sr.REPLAY_COMPLETIONS):
            raw[f"{code_obs}|{p}|{i:03d}"] = (
                json.dumps({"worker_ids": positional}) if i < 7
                else "malformed")
    counts = sr.recount_from_raw(raw, table, rows)
    for p in (FEW, SO):
        assert counts[f"{code_obs}|{p}"] == {
            "k2": 7, "k3": 0, "n": sr.REPLAY_COMPLETIONS}


# --- B replay contract --------------------------------------------------------------

def test_replay_contract_256_and_launch_profile():
    model = STAGE0C_LAUNCH_PROFILE["conductor_model"]
    assert sr.REPLAY_CONTRACT["model_id"] == model["model_id"]
    assert sr.REPLAY_CONTRACT["revision"] == model["revision"]
    assert sr.REPLAY_CONTRACT["quantization"] == \
        STAGE0C_LAUNCH_PROFILE["quantization"]
    assert sr.REPLAY_COMPLETIONS == 256          # 145_s amendment
    assert sr.REPLAY_CONTRACT[
        "completions_per_observation_per_prompt"] == 256
    assert sr.REPLAY_CONTRACT["total_completions"] == 9_216
    assert sr.REPLAY_CONTRACT["generation_batch"] == 1


def test_completion_seed_range():
    assert sr.completion_seed("o", "p" * 64, 255) != \
        sr.completion_seed("o", "p" * 64, 254)
    with pytest.raises(ValueError):
        sr.completion_seed("o", "p" * 64, 256)


def test_family_correct_variants_per_cell():
    assert sr.family_correct_variants("lookup_atomic") is None
    assert sr.family_correct_variants("code_atomic") == ([2], [3])
    assert sr.family_correct_variants("math_code") == ([1, 2], [1, 3])
    assert sr.family_correct_variants("fork_join") == \
        ([0, 2, 1], [0, 3, 1])


def test_pair_table_from_surface_mapping():
    surface = {("o1", (2,)): 0.5, ("o1", (3,)): 1.0}
    table = sr.pair_table_from_surface(surface, {"o1": "code_atomic"})
    assert table["o1"]["direction"] == 3
    with pytest.raises(InfrastructureError, match="missing"):
        sr.pair_table_from_surface({("o1", (2,)): 0.5},
                                   {"o1": "code_atomic"})


def test_expected_completion_keys_9216():
    obs = [f"o{i:02d}" for i in range(18)]
    keys = sr.expected_completion_keys(obs)
    assert len(keys) == 9_216
    with pytest.raises(InfrastructureError, match="exactly 18"):
        sr.expected_completion_keys(obs[:17])


def test_summarize_replay_fail_closed_and_statuses():
    rows = _support_rows()
    surface = _surface(rows)
    table = sr.pair_table_from_surface(
        surface, {o: m["cell_id"] for o, m in rows.items()})
    meta = sr.observation_meta(rows)
    counts = {f"{o}|{p}": {"k2": 30, "k3": 28,
                           "n": sr.REPLAY_COMPLETIONS}
              for o in table for p in (FEW, SO)}
    out = sr.summarize_replay(counts, table, meta)
    assert out["comparisons"] == 4      # 2 distinct-payoff obs x 2
    assert out["directions"]["2"]["status"] == "not_ruled_out"
    assert out["directions"]["3"]["status"] == "not_ruled_out"
    # 145_s: not_ruled_out replaces "demonstrated" — an upper bound
    # above the floor does not demonstrate feasibility
    assert "demonstrated" not in {
        out["directions"]["2"]["status"],
        out["directions"]["3"]["status"]}
    # zero counts at 256: the branch is now reachable and BLOCKS
    low = {k: {"k2": 0, "k3": 0, "n": sr.REPLAY_COMPLETIONS}
           for k in counts}
    out_low = sr.summarize_replay(low, table, meta)
    assert out_low["directions"]["2"]["status"] == "not_demonstrated"
    assert out_low["directions"]["3"]["status"] == "not_demonstrated"
    # incomplete keys refuse (145_s probe)
    partial = dict(counts)
    partial.pop(next(iter(partial)))
    with pytest.raises(InfrastructureError, match="count keys"):
        sr.summarize_replay(partial, table, meta)
    # arbitrary n refuses
    bad_n = {k: {"k2": 0, "k3": 0, "n": 64} for k in counts}
    with pytest.raises(InfrastructureError, match="malformed"):
        sr.summarize_replay(bad_n, table, meta)
    # impossible counts refuse
    bad = dict(counts)
    bad[next(iter(bad))] = {"k2": 200, "k3": 100,
                            "n": sr.REPLAY_COMPLETIONS}
    with pytest.raises(InfrastructureError, match="malformed"):
        sr.summarize_replay(bad, table, meta)
    # missing meta refuses
    with pytest.raises(InfrastructureError, match="meta"):
        sr.summarize_replay(counts, table, {})


def test_summarize_uses_frozen_weighting_not_raw_average():
    # two same-direction observations in ONE cell must count as one
    # cell, not two raw observations: add a second fork renderer with
    # an extreme count and check the cell-equal aggregate differs from
    # the raw mean
    rows = _support_rows()
    surface = _surface(rows)
    table = sr.pair_table_from_surface(
        surface, {o: m["cell_id"] for o, m in rows.items()})
    fork_obs = next(o for o in table if o.startswith("fork_join"))
    second = fork_obs.replace("resource_first", "bound_var")
    table[second] = dict(table[fork_obs])
    meta = sr.observation_meta(list(table))
    counts = {}
    for o, row in table.items():
        for p in (FEW, SO):
            k = 60 if "bound_var" in o else 10
            counts[f"{o}|{p}"] = {"k2": k, "k3": k,
                                  "n": sr.REPLAY_COMPLETIONS}
    out = sr.summarize_replay(counts, table, meta)
    d2 = out["directions"]["2"]["per_prompt"][FEW]
    # renderer-mean within the single fork latent: g((10+60)/2/256-ish)
    # vs raw mean of two observations — the weighted value equals the
    # renderer-averaged value, strictly between the two obs values
    g_low = sr.g_direct_gradient(10 / 256, 10 / 256)
    g_high = sr.g_direct_gradient(60 / 256, 60 / 256)
    assert g_low < d2["g_point"] < g_high
    assert d2["g_point"] == pytest.approx((g_low + g_high) / 2,
                                          rel=1e-9)


def test_load_b_artifact_structural_fail_closed():
    b = _b_evidence()["artifact"]
    loaded = sr.load_b_artifact(json.loads(json.dumps(b)), EXEC_SHA)
    assert loaded["results"]
    with pytest.raises(st.TrancheError, match="foreign execution"):
        sr.load_b_artifact(b, "f" * 64)
    stripped = {k: v for k, v in b.items() if k != "obs_meta"}
    with pytest.raises(InfrastructureError, match="obs_meta"):
        sr.load_b_artifact(stripped, EXEC_SHA)
    stripped2 = {k: v for k, v in b.items()
                 if k != "raw_completions_sha256"}
    with pytest.raises(InfrastructureError, match="raw_completions"):
        sr.load_b_artifact(stripped2, EXEC_SHA)
    tampered = dict(b)
    key = next(iter(b["results"]))
    tampered["results"] = {**b["results"],
                           key: {"k2": 1, "k3": 1,
                                 "n": sr.REPLAY_COMPLETIONS}}
    with pytest.raises(st.TrancheError, match="hash mismatch"):
        sr.load_b_artifact(tampered, EXEC_SHA)


def test_replay_manifest_and_meta():
    rows = _support_rows()
    surface = _surface(rows)
    table = sr.pair_table_from_surface(
        surface, {o: m["cell_id"] for o, m in rows.items()})
    obs = sorted(table)
    rr = {f"{o}|{p}": "a" * 64 for o in obs for p in (FEW, SO)}
    m = sr.build_replay_manifest(EXEC_SHA, obs, rr, table)
    assert m["manifest"] == "stage1-replay-manifest-v2"
    assert m["contract"]["total_completions"] == 9_216
    with pytest.raises(InfrastructureError, match="rendered-request"):
        sr.build_replay_manifest(EXEC_SHA, obs,
                                 dict(list(rr.items())[:-1]), table)
    meta = sr.observation_meta(obs)
    assert meta[obs[0]]["cell_id"] == "code_atomic"
    assert meta[obs[0]]["renderer"] == "resource_first"


# --- 154_s: the abort boundary covers the ENTIRE post-`running` sequence ---

def _replay_probe_setup(tmp_path, monkeypatch):
    import tasks.conductor.stage1_manifest as sm
    monkeypatch.setattr(sr, "REPLAY_RUN_DIR",
                        str(tmp_path / "stage1-replay"))
    monkeypatch.setattr(sm, "build_stage1_env_manifest",
                        lambda allow_dirty=False: dict(ENV))
    b = _b_evidence()
    surface, rows, rr = b["loader"]()
    return {"surface": surface, "rows": rows, "messages": {},
            "rr_hashes": rr, "tokenizer": None}


def _read_record(tmp_path):
    return json.loads(
        (tmp_path / "stage1-replay" / "run_record.json").read_text(
            encoding="utf-8"))


def test_run_replay_model_load_failure_writes_aborted(tmp_path,
                                                      monkeypatch):
    inputs = _replay_probe_setup(tmp_path, monkeypatch)

    def boom():
        raise RuntimeError("CUDA out of memory (probe)")
    monkeypatch.setattr(sr, "_build_replay_model", boom)
    with pytest.raises(RuntimeError, match="probe"):
        sr.run_replay(_inputs=inputs)
    record = _read_record(tmp_path)
    assert record["status"] == "aborted"
    assert "RuntimeError" in record["error"]
    assert "wall_seconds" in record
    # the pre-model persistence survived the abort
    run_dir = tmp_path / "stage1-replay"
    assert (run_dir / "env_manifest.json").exists()
    assert (run_dir / "replay_manifest.json").exists()


def test_run_replay_finalization_failure_writes_aborted(tmp_path,
                                                        monkeypatch):
    # post-generation failure: generation "succeeds" but produces
    # incomplete accounting — the finalization path must abort with a
    # record, not leave `running`
    inputs = _replay_probe_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(sr, "_build_replay_model", lambda: None)
    monkeypatch.setattr(
        sr, "_generate",
        lambda model, tok, rows, msgs, table, raw, counts: None)
    with pytest.raises(InfrastructureError, match="accounting"):
        sr.run_replay(_inputs=inputs)
    record = _read_record(tmp_path)
    assert record["status"] == "aborted"
    assert "accounting" in record["error"]
    assert "wall_seconds" in record
