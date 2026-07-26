"""195_f implementation tests: the BatchEncoding repair regression,
the diagnostic seed registry/contract/manifest, the frozen counting
boundary and its identities, the authenticating verifier, the
descriptive report estimands, the smoke, the driver, and the
archiver. CPU only; no GPU, no frozen seed, no retained-support
outcome is produced (all completions here are synthetic)."""

import hashlib
import json

import pytest
import torch
from transformers import BatchEncoding

from tasks.conductor import stage1
from tasks.conductor import stage1_amend1 as am
from tasks.conductor import stage1_b_diagnostic as bd
from tasks.conductor import stage1_replay as sr
from tasks.conductor.types import InfrastructureError

FEW = stage1.PROMPT_FEWSHOT_SHA256
SO = stage1.PROMPT_SCHEMA_ONLY_SHA256


def _env_manifest():
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


# --- fixtures: synthetic support with a FULL 4^S surface ---------------------------

def _support_rows():
    rows = {}
    pair_cells = [("code_atomic", ["n1"]),      # w3-favoured
                  ("math_code", ["n1", "n2"]),  # tie
                  ("fork_join", ["n1", "n2", "n3"])]  # w2-favoured
    for idx, (cell, positions) in enumerate(pair_cells):
        oid = (f"{cell}:worker_dev:{idx:05d}:aaaaaaa{idx}:"
               "resource_first:private")
        rows[oid] = {"cell_id": cell, "num_steps": len(positions),
                     "positions": json.dumps(positions)}
    for i in range(15):
        oid = (f"lookup_atomic:worker_dev:{i + 10:05d}:bbbbbb{i:02x}:"
               "goal_first:private")
        rows[oid] = {"cell_id": "lookup_atomic", "num_steps": 1,
                     "positions": json.dumps(["n1"])}
    return rows


def _full_surface(rows):
    """EVERY 4^S assignment gets a row (payoffs in {0.5, 1.0} only —
    the 195_f §4.3 verified property of the real surface)."""
    from itertools import product
    surface = {}
    favoured = {"code_atomic": ([3], 1.0), "fork_join": ([0, 2, 1], 1.0)}
    for oid, meta in rows.items():
        n = meta["num_steps"]
        for assignment in product(range(4), repeat=n):
            surface[(oid, assignment)] = 0.5
        fav = favoured.get(meta["cell_id"])
        if fav is not None:
            surface[(oid, tuple(fav[0]))] = fav[1]
    return surface


def _pair_table(rows, surface):
    cell_of = {o: m["cell_id"] for o, m in rows.items()}
    return sr.pair_table_from_surface(surface, cell_of)


def _make_raw(rows, k_valid=None):
    """Synthetic raw completions: per (obs, prompt) — 5 malformed,
    3 parseable-not-valid, the rest valid, cycling assignments
    (weighted toward the family-correct variants when present)."""
    raw = {}
    table = _pair_table(rows, _full_surface(rows))
    for oid, meta in sorted(rows.items()):
        n = meta["num_steps"]
        pair = table.get(oid)
        for sha in (FEW, SO):
            for i in range(sr.REPLAY_COMPLETIONS):
                key = f"{oid}|{sha}|{i:03d}"
                if i < 5:
                    raw[key] = "not json {"
                elif i < 8:
                    raw[key] = json.dumps({"unexpected": "shape"})
                elif pair is not None and i < 48:
                    raw[key] = json.dumps(
                        {"worker_ids": list(pair["assignment_w2"])})
                elif pair is not None and i < 78:
                    raw[key] = json.dumps(
                        {"worker_ids": list(pair["assignment_w3"])})
                else:
                    raw[key] = json.dumps(
                        {"worker_ids": [1] * n})
    return raw


def _diag_fixture():
    rows = _support_rows()
    surface = _full_surface(rows)
    raw = _make_raw(rows)
    raw_text = json.dumps(dict(sorted(raw.items())),
                          ensure_ascii=False)
    raw_sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    rr = {f"{o}|{p}": "a" * 64 for o in sorted(rows)
          for p in (FEW, SO)}
    registry = bd.build_diagnostic_seed_registry(sorted(rows))
    tokenizer = _StubTokenizer()
    manifest = bd.build_diagnostic_manifest(
        ENV["execution_manifest_sha256"],
        ENV["stage1_source_sha256"],
        hashlib.sha256(tokenizer.chat_template.encode(
            "utf-8")).hexdigest(),
        sorted(rows), rr, registry)
    results = bd.count_from_raw(raw, rows, surface)
    artifact = bd.build_diagnostic_artifact(
        manifest["manifest_sha256"], ENV["execution_manifest_sha256"],
        raw_sha, results, sorted(rows))
    inputs = {"surface": surface, "rows": rows, "rr_hashes": rr,
              "messages": {}, "tokenizer": tokenizer}
    return {"rows": rows, "surface": surface, "raw": raw,
            "raw_text": raw_text, "manifest": manifest,
            "results": results, "artifact": artifact,
            "loader": lambda: inputs, "inputs": inputs}


# --- the BatchEncoding repair (195_f §2) --------------------------------------------

class _StubTokenizer:
    eos_token_id = 0
    chat_template = "stub-template"

    def apply_chat_template(self, msgs, tokenize=False,
                            return_tensors=None,
                            add_generation_prompt=False):
        assert tokenize and return_tensors == "pt"
        return BatchEncoding({
            "input_ids": torch.tensor([[5, 6, 7]]),
            "attention_mask": torch.tensor([[1, 1, 1]])})

    def decode(self, ids, skip_special_tokens=False):
        return json.dumps({"worker_ids": [2]})


class _StubModel:
    device = "cpu"

    def __init__(self):
        self.calls = 0

    def generate(self, input_ids, attention_mask=None,
                 pad_token_id=None, **kwargs):
        # the 195_f regression: generate MUST receive tensors, not a
        # BatchEncoding — this assertion fails against pre-repair code
        assert isinstance(input_ids, torch.Tensor)
        assert input_ids.ndim == 2
        assert isinstance(attention_mask, torch.Tensor)
        assert set(kwargs) == set(sr.GENERATION_KWARGS)
        self.calls += 1
        return torch.cat([input_ids,
                          torch.tensor([[9, 9]])], dim=1)


def _smoke_rows_one():
    return {"code_atomic:worker_dev:00000:aaaaaaa0:resource_first:"
            "private": {"cell_id": "code_atomic", "num_steps": 1,
                        "positions": json.dumps(["n1"])}}


def test_generate_batchencoding_regression():
    rows = _smoke_rows_one()
    oid = next(iter(rows))
    messages = {f"{oid}|{p}": [] for p in (FEW, SO)}
    surface = _full_surface(rows)
    table = _pair_table(rows, surface)
    raw, counts = {}, {}
    model = _StubModel()
    sr._generate(model, _StubTokenizer(), rows, messages, table, raw,
                 counts, seed_of=lambda o, s, i: 1,
                 n_completions=4)
    assert model.calls == 8            # 2 prompts x 4
    assert len(raw) == 8
    # decode sliced at the prompt length: only the 2 new tokens
    # reached decode; the fixed text parses and counts as w2
    for p in (FEW, SO):
        assert counts[f"{oid}|{p}"] == {"k2": 4, "k3": 0, "n": 4}


def test_generate_deadline_and_block_callback():
    rows = _smoke_rows_one()
    oid = next(iter(rows))
    messages = {f"{oid}|{p}": [] for p in (FEW, SO)}
    blocks = []
    raw = {}
    sr._generate(_StubModel(), _StubTokenizer(), rows, messages, {},
                 raw, {}, seed_of=lambda o, s, i: 1, n_completions=2,
                 on_block_complete=lambda o, s: blocks.append((o, s)))
    assert len(blocks) == 2
    with pytest.raises(InfrastructureError, match="deadline"):
        sr._generate(_StubModel(), _StubTokenizer(), rows, messages,
                     {}, {}, {}, seed_of=lambda o, s, i: 1,
                     n_completions=2, deadline_seconds=0.0)


# --- seed identity (195_f §4.2) ------------------------------------------------------

def test_diagnostic_seed_exact_formula_and_registry():
    oid, sha, i = "obs-x", "p" * 64, 7
    key = f"B-diag|{oid}|{sha}|{i}"
    manual = int.from_bytes(hashlib.sha256(
        ("stage1-b-diagnostic-v1" + "\x1f" + key).encode(
            "utf-8")).digest()[:8], "big")
    assert bd.diagnostic_seed(oid, sha, i) == manual
    with pytest.raises(InfrastructureError):
        bd.diagnostic_seed(oid, sha, 256)
    rows = _support_rows()
    registry = bd.build_diagnostic_seed_registry(sorted(rows))
    assert len(registry) == 9_216
    some = sorted(rows)[0]
    assert f"B-diag|{some}|{FEW}|0" in registry      # unpadded
    assert f"B-diag|{some}|{FEW}|000" not in registry
    assert am.seed_registry_digest(registry) == \
        am.seed_registry_digest(
            bd.build_diagnostic_seed_registry(sorted(rows)))
    with pytest.raises(InfrastructureError, match="18"):
        bd.build_diagnostic_seed_registry(sorted(rows)[:17])


# --- manifest (195_f §4.1) ------------------------------------------------------------

def test_diagnostic_manifest_fail_closed():
    f = _diag_fixture()
    manifest = f["manifest"]
    assert bd.validate_diagnostic_manifest(manifest) == \
        manifest["manifest_sha256"]
    tampered = dict(manifest, stage1_source_sha256="e" * 64)
    with pytest.raises(InfrastructureError, match="hash"):
        bd.validate_diagnostic_manifest(tampered)
    # a rehashed manifest with a modified frozen contract refuses
    body = {k: v for k, v in manifest.items()
            if k != "manifest_sha256"}
    body["contract"] = dict(body["contract"], observations
                            =17) if False else dict(body["contract"])
    body["contract"]["observations"] = 17
    from tasks.conductor.profiles import canonical_json
    body["manifest_sha256"] = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    with pytest.raises(InfrastructureError, match="contract"):
        bd.validate_diagnostic_manifest(body)


# --- counting boundary + identities (195_f §4.3) --------------------------------------

def test_count_from_raw_and_identities():
    f = _diag_fixture()
    rows, results = f["rows"], f["results"]
    pair_oid = next(o for o in rows if o.startswith("code_atomic"))
    row = results[f"{pair_oid}|{FEW}"]
    assert row["n"] == 256
    assert row["parseable"] == 251            # 5 malformed
    assert row["valid"] == 248                # +3 non-schema
    assert sum(row["assignments"].values()) == row["valid"]
    assert sum(row["reward_levels"].values()) == 256
    assert row["reward_levels"]["0"] == 256 - row["valid"]
    # w3-favoured cell: 40 w2, 30 w3, rest [1]
    assert row["assignments"]["2"] == 40
    assert row["assignments"]["3"] == 30
    # reward levels: only the favoured w3 variant scores 1.0
    assert row["reward_levels"]["1"] == 30
    lookup_oid = next(o for o in rows if o.startswith("lookup"))
    lrow = results[f"{lookup_oid}|{SO}"]
    assert lrow["valid"] == 248 and lrow["reward_levels"]["1"] == 0


def test_artifact_identities_fail_closed():
    f = _diag_fixture()
    art, manifest = f["artifact"], f["manifest"]
    loaded = bd.load_diagnostic_artifact(
        json.loads(json.dumps(art)), manifest["manifest_sha256"])
    assert loaded["results"]
    key = next(iter(f["results"]))
    for mutate, match in (
            (lambda r: r.update(valid=r["valid"] + 1), "parseable"),
            (lambda r: r["reward_levels"].update({"0": 1}),
             "reward_0|sum"),
            (lambda r: r["assignments"].update({"9": 1}),
             "assignments")):
        results = {k: {**v, "assignments": dict(v["assignments"]),
                       "reward_levels": dict(v["reward_levels"])}
                   for k, v in f["results"].items()}
        mutate(results[key])
        with pytest.raises(InfrastructureError):
            bd.build_diagnostic_artifact(
                manifest["manifest_sha256"],
                ENV["execution_manifest_sha256"], "r" * 64, results,
                sorted(f["rows"]))
    # payoff outside the frozen ladder refuses at counting time —
    # tamper a row the synthetic completions actually produce
    # (the [1]*n filler assignment on a lookup observation)
    bad_surface = dict(f["surface"])
    lookup_oid = next(o for o in f["rows"] if o.startswith("lookup"))
    bad_surface[(lookup_oid, (1,))] = 0.25
    with pytest.raises(InfrastructureError, match="0.5, 1.0"):
        bd.count_from_raw(f["raw"], f["rows"], bad_surface)


# --- verifier (195_f §4.4) --------------------------------------------------------------

def test_verifier_end_to_end_and_refusals():
    f = _diag_fixture()
    results = bd.verify_b_diagnostic_evidence(
        f["artifact"], manifest=f["manifest"],
        raw_completions_text=f["raw_text"], env_manifest=ENV,
        pinned_loader=f["loader"])
    assert results == f["results"]
    # tampered raw bytes refuse on the sha binding
    with pytest.raises(InfrastructureError, match="hash"):
        bd.verify_b_diagnostic_evidence(
            f["artifact"], manifest=f["manifest"],
            raw_completions_text=f["raw_text"] + " ",
            env_manifest=ENV, pinned_loader=f["loader"])
    # a tampered persisted count refuses on exact reproduction
    results2 = {k: {**v, "assignments": dict(v["assignments"]),
                    "reward_levels": dict(v["reward_levels"])}
                for k, v in f["results"].items()}
    key = next(k for k, v in results2.items() if v["valid"] > 1)
    akey = next(iter(results2[key]["assignments"]))
    other = "0,0,0"[:len(akey)]
    row = results2[key]
    moved = 1
    row["assignments"][akey] -= moved
    row["assignments"][other] = row["assignments"].get(other, 0) + moved
    art2 = bd.build_diagnostic_artifact(
        f["manifest"]["manifest_sha256"],
        ENV["execution_manifest_sha256"],
        hashlib.sha256(f["raw_text"].encode()).hexdigest(),
        results2, sorted(f["rows"]))
    with pytest.raises(InfrastructureError, match="reproduce"):
        bd.verify_b_diagnostic_evidence(
            art2, manifest=f["manifest"],
            raw_completions_text=f["raw_text"], env_manifest=ENV,
            pinned_loader=f["loader"])


# --- report estimands (195_f §4.2/4.3) --------------------------------------------------

def test_report_estimands_and_populations():
    f = _diag_fixture()
    table = _pair_table(f["rows"], f["surface"])
    meta = sr.observation_meta(f["rows"])
    report = bd.build_b_diagnostic_report(f["results"], table, meta)
    assert "plug-in" in report["label"]
    # per-row: p2/p3 denominators are ALL 256 draws
    pair_oid = next(o for o in f["rows"]
                    if o.startswith("code_atomic"))
    q = report["per_observation_prompt"][f"{pair_oid}|{FEW}"]
    assert q["population"] == "w3_favoured"
    assert q["p2"] == pytest.approx(40 / 256)
    assert q["p3"] == pytest.approx(30 / 256)
    assert q["g8"] == pytest.approx(
        sr.g_direct_gradient(40 / 256, 30 / 256))
    # tie cell is its own population and carries no g8 aggregate
    tie_oid = next(o for o in f["rows"] if o.startswith("math_code"))
    assert report["per_observation_prompt"][
        f"{tie_oid}|{FEW}"]["population"] == "tied_pair"
    agg = report["aggregates"]["fewshot"]
    assert "g8" not in agg["tied_pairs"]
    assert "g8" in agg["w2_favoured"] and "g8" in agg["w3_favoured"]
    # 197_s: renderer->latent->cell summaries exposed per metric
    assert agg["w3_favoured"]["g8"]["equal_cell"] == pytest.approx(
        q["g8"])
    assert "code_atomic" in agg["w3_favoured"]["g8"]["per_cell"]
    # frozen formulas on the level distribution
    row = f["results"][f"{tie_oid}|{SO}"]
    p = {lv: c / 256 for lv, c in row["reward_levels"].items()}
    qrow = report["per_observation_prompt"][f"{tie_oid}|{SO}"]
    assert qrow["zero_variance_group_fraction"] == pytest.approx(
        sum(v ** 8 for v in p.values()))
    assert qrow["expected_reward_level_diversity"] == pytest.approx(
        sum(1 - (1 - v) ** 8 for v in p.values()))
    # all-18 population aggregates exist for the shared metrics,
    # including the signed reward frequencies (197_s)
    assert agg["all_18"]["valid_rate"]["equal_cell"] is not None
    assert agg["all_18"]["reward_rate_0"]["equal_cell"] == \
        pytest.approx(1 - agg["all_18"]["valid_rate"]["equal_cell"])
    # explicit denominators and support composition
    comp = report["support_composition"]
    assert comp == {"observations": 18, "pair_observations": 3,
                    "distinct_payoff_pairs": 2, "w2_favoured": 1,
                    "w3_favoured": 1, "tied_pairs": 1}
    assert report["populations"]["all_18"]["row_count"] == 36
    assert report["populations"]["w2_favoured"]["row_count"] == 2
    # per-row action distribution travels in the signed output
    assert q["assignment_rates"]["3"] == pytest.approx(30 / 256)


# --- smoke + driver + archiver (195_f §3/§4.5) ------------------------------------------

def test_run_b_smoke_stub(tmp_path, monkeypatch):
    import tasks.conductor.stage1_manifest as sm
    monkeypatch.setattr(sm, "build_stage1_env_manifest",
                        lambda allow_dirty=False: dict(ENV))
    inputs = {"tokenizer": _StubTokenizer(), "_model": _StubModel()}
    record = bd.run_b_smoke(_inputs=inputs,
                            record_path=tmp_path / "smoke.json")
    assert record["status"] == "complete"
    assert record["completions"] == 16
    assert record["nonempty_completions"] == 16
    assert record["generation_config_sha256"] == \
        bd.generation_config_digest()
    assert record["budget_completions"] == 16
    # 197_s: tokenizer revision + prompt tensor shapes recorded, and
    # the record is PERSISTED for the launch lock
    assert record["tokenizer_revision"] == \
        bd.B_DIAGNOSTIC_CONTRACT["tokenizer_revision"]
    assert record["prompt_input_ids_shapes"] == {FEW: [1, 3],
                                                 SO: [1, 3]}
    persisted = json.loads((tmp_path / "smoke.json").read_text(
        encoding="utf-8"))
    assert persisted == record
    # 199_s: uv_lock_sha256 joins the executable identity
    assert record["uv_lock_sha256"] == hashlib.sha256(
        __import__("pathlib").Path("uv.lock").read_bytes()).hexdigest()
    # 199_s finding 2: the smoke is one-shot — a second invocation
    # refuses BEFORE preflight/model loading
    with pytest.raises(InfrastructureError, match="one-shot"):
        bd.run_b_smoke(_inputs=inputs,
                       record_path=tmp_path / "smoke.json")


def _smoke_and_lock(tmp_path, rows):
    """Persist a smoke record and build the launch lock over the
    fixture support's registry (197_s finding 1 flow)."""
    inputs = {"tokenizer": _StubTokenizer(), "_model": _StubModel()}
    bd.run_b_smoke(_inputs=inputs,
                   record_path=tmp_path / "smoke.json")
    registry = bd.build_diagnostic_seed_registry(sorted(rows))
    bd.build_launch_lock(tmp_path / "smoke.json",
                         seed_registry=registry,
                         lock_path=tmp_path / "lock.json")
    return tmp_path / "lock.json"


def test_launch_lock_binding_and_refusals(tmp_path, monkeypatch):
    import tasks.conductor.stage1_manifest as sm
    monkeypatch.setattr(sm, "build_stage1_env_manifest",
                        lambda allow_dirty=False: dict(ENV))
    rows = _support_rows()
    registry = bd.build_diagnostic_seed_registry(sorted(rows))
    lock_path = _smoke_and_lock(tmp_path, rows)
    from tasks.conductor.profiles import canonical_json
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    good_record = json.loads((tmp_path / "smoke.json").read_text(
        encoding="utf-8"))
    bd.validate_launch_lock(lock, seed_registry=registry)
    assert lock["uv_lock_sha256"] == hashlib.sha256(
        __import__("pathlib").Path("uv.lock").read_bytes()).hexdigest()
    # a lock whose identity disagrees with the current executable
    # refuses (rehashed so the self-hash passes)
    body = {k: v for k, v in lock.items()
            if k != "launch_lock_sha256"}
    body["source_digest"] = "e" * 64
    body["launch_lock_sha256"] = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    with pytest.raises(InfrastructureError, match="current"):
        bd.validate_launch_lock(body, seed_registry=registry)
    # a modified smoke record after locking refuses
    (tmp_path / "smoke.json").write_text("{}", encoding="utf-8")
    with pytest.raises(InfrastructureError, match="smoke record"):
        bd.validate_launch_lock(lock, seed_registry=registry)
    # an incomplete smoke record cannot be locked at all
    (tmp_path / "smoke2.json").write_text(
        json.dumps({"status": "aborted"}), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="JSON object|tag|complete"):
        bd.build_launch_lock(tmp_path / "smoke2.json",
                             seed_registry=registry,
                             lock_path=tmp_path / "lock2.json")
    # 199_s finding 1: a REHASHED lock pointing at an aborted record
    # is refused by the consumer's SEMANTIC re-validation
    aborted_bytes = (tmp_path / "smoke2.json").read_bytes()
    evil = {k: v for k, v in lock.items()
            if k != "launch_lock_sha256"}
    evil["smoke_record_path"] = str(tmp_path / "smoke2.json")
    evil["smoke_record_sha256"] = hashlib.sha256(
        aborted_bytes).hexdigest()
    evil["launch_lock_sha256"] = hashlib.sha256(
        canonical_json(evil).encode("utf-8")).hexdigest()
    with pytest.raises(InfrastructureError,
                       match="JSON object|tag|complete"):
        bd.validate_launch_lock(evil, seed_registry=registry)
    # an under-budget record refuses semantically too
    good = dict(good_record)
    good["completions"] = 8
    (tmp_path / "smoke3.json").write_text(json.dumps(good),
                                          encoding="utf-8")
    with pytest.raises(InfrastructureError, match="budget"):
        bd.build_launch_lock(tmp_path / "smoke3.json",
                             seed_registry=registry,
                             lock_path=tmp_path / "lock3.json")


def test_verifier_provenance_tampers_refused():
    # 197_s finding 2: the three provenance claims are independently
    # re-derived — a rehashed manifest with any of them changed
    # refuses even though its self-hash passes
    from tasks.conductor.profiles import canonical_json
    f = _diag_fixture()
    for field, match in (
            ("stage1_source_sha256", "source"),
            ("chat_template_sha256", "chat template"),
            ("generation_config_sha256", "generation")):
        body = {k: v for k, v in f["manifest"].items()
                if k != "manifest_sha256"}
        body[field] = "e" * 64
        body["manifest_sha256"] = hashlib.sha256(
            canonical_json(body).encode("utf-8")).hexdigest()
        artifact = bd.build_diagnostic_artifact(
            body["manifest_sha256"], ENV["execution_manifest_sha256"],
            hashlib.sha256(f["raw_text"].encode()).hexdigest(),
            f["results"], sorted(f["rows"]))
        with pytest.raises(InfrastructureError, match=match):
            bd.verify_b_diagnostic_evidence(
                artifact, manifest=body,
                raw_completions_text=f["raw_text"], env_manifest=ENV,
                pinned_loader=f["loader"])


def test_non_utf8_completion_is_reward_zero():
    # 197_s: a lone-surrogate completion counts as non-parseable and
    # reward-zero instead of aborting
    rows = {k: v for k, v in list(_support_rows().items())[:1]}
    surface = _full_surface(rows)
    oid = next(iter(rows))
    raw = {}
    for sha in (FEW, SO):
        for i in range(sr.REPLAY_COMPLETIONS):
            raw[f"{oid}|{sha}|{i:03d}"] = "\ud800"
    results = bd.count_from_raw(raw, rows, surface)
    row = results[f"{oid}|{FEW}"]
    assert row["parseable"] == 0 and row["valid"] == 0
    assert row["reward_levels"]["0"] == 256
    # and ensure_ascii persistence round-trips the surrogate
    blob = json.dumps(raw, ensure_ascii=True)
    blob.encode("utf-8")
    assert json.loads(blob) == raw


def test_run_b_diagnostic_end_to_end(tmp_path, monkeypatch):
    import tasks.conductor.stage1_manifest as sm
    monkeypatch.setattr(sm, "build_stage1_env_manifest",
                        lambda allow_dirty=False: dict(ENV))
    monkeypatch.setattr(bd, "B_DIAG_RUN_ROOT",
                        str(tmp_path / "b-diag"))
    f = _diag_fixture()

    class _ScriptedModel(_StubModel):
        pass

    class _ScriptedTokenizer(_StubTokenizer):
        def __init__(self):
            self._texts = {}

        def decode(self, ids, skip_special_tokens=False):
            return self._next

    tok = _ScriptedTokenizer()
    model = _ScriptedModel()

    # the smoke + launch lock use the REAL helper with stubs, so
    # they run BEFORE the scripted generator is patched in
    lock_path = _smoke_and_lock(tmp_path, f["rows"])

    def scripted_generate(mdl, tkn, rows, messages, table, raw,
                          counts, **kwargs):
        # drive the REAL helper but substitute each decoded text from
        # the fixture so counts are known
        def fake_decode(ids, skip_special_tokens=False):
            return tok._next
        tkn.decode = fake_decode
        seed_of = kwargs["seed_of"]
        for oid in sorted(rows):
            for sha in (FEW, SO):
                for i in range(sr.REPLAY_COMPLETIONS):
                    seed_of(oid, sha, i)      # registered consumption
                    raw[f"{oid}|{sha}|{i:03d}"] = \
                        f["raw"][f"{oid}|{sha}|{i:03d}"]
                cb = kwargs.get("on_block_complete")
                if cb:
                    cb(oid, sha)
    monkeypatch.setattr(sr, "_generate", scripted_generate)

    inputs = {**f["inputs"], "tokenizer": tok, "_model": model,
              "messages": {}}
    # 197_s finding 1: without a committed launch lock the diagnostic
    # refuses BEFORE claiming its root
    with pytest.raises(InfrastructureError, match="launch lock"):
        bd.run_b_diagnostic(_inputs=inputs,
                            launch_lock_path=tmp_path / "absent.json")
    out = bd.run_b_diagnostic(_inputs=inputs,
                              launch_lock_path=lock_path)
    from pathlib import Path
    run_dir = Path(out["run_dir"])
    record = json.loads((run_dir / "run_record.json").read_text(
        encoding="utf-8"))
    assert record["status"] == "complete"
    assert not (run_dir / "raw_completions_partial.json").exists()
    art = json.loads(
        (run_dir / "artifact_B_diagnostic.json").read_text(
            encoding="utf-8"))
    assert art["tag"] == bd.B_DIAG_TAG
    # success archiver over the completed root
    archive = bd.archive_b_diagnostic(
        "success", run_dir=run_dir,
        evidence_parent=tmp_path / "ev", pinned_loader=f["loader"])
    assert archive["mode"] == "success"
    assert archive["validation_errors"] == []
    with pytest.raises(InfrastructureError, match="immutable"):
        bd.archive_b_diagnostic("success", run_dir=run_dir,
                                evidence_parent=tmp_path / "ev",
                                pinned_loader=f["loader"])
    # 199_s finding 3: a complete run may not consume the immutable
    # destination through the untrusting abort path
    with pytest.raises(InfrastructureError, match="mode success"):
        bd.archive_b_diagnostic("abort", run_dir=run_dir,
                                evidence_parent=tmp_path / "ev3")
    # a second diagnostic run refuses the claimed root
    with pytest.raises(InfrastructureError, match="already exists"):
        bd.run_b_diagnostic(_inputs=inputs,
                            launch_lock_path=lock_path)


def test_diagnostic_abort_preserves_partial(tmp_path, monkeypatch):
    import tasks.conductor.stage1_manifest as sm
    monkeypatch.setattr(sm, "build_stage1_env_manifest",
                        lambda allow_dirty=False: dict(ENV))
    monkeypatch.setattr(bd, "B_DIAG_RUN_ROOT",
                        str(tmp_path / "b-diag"))
    f = _diag_fixture()

    lock_path = _smoke_and_lock(tmp_path, f["rows"])

    def dying_generate(mdl, tkn, rows, messages, table, raw, counts,
                       **kwargs):
        # 197_s finding 4: dies MID-BLOCK — no callback ever fires;
        # the exception path must still preserve every completion
        oid = sorted(rows)[0]
        for i in range(100):
            raw[f"{oid}|{FEW}|{i:03d}"] = "partial"
        raise RuntimeError("CUDA out of memory (probe)")
    monkeypatch.setattr(sr, "_generate", dying_generate)
    inputs = {**f["inputs"], "tokenizer": _StubTokenizer(),
              "_model": _StubModel(), "messages": {}}
    with pytest.raises(RuntimeError, match="probe"):
        bd.run_b_diagnostic(_inputs=inputs,
                            launch_lock_path=lock_path)
    from pathlib import Path
    run_dir = Path(str(tmp_path / "b-diag"))
    record = json.loads((run_dir / "run_record.json").read_text(
        encoding="utf-8"))
    assert record["status"] == "aborted"
    partial = json.loads(
        (run_dir / "raw_completions_partial.json").read_text(
            encoding="utf-8"))
    assert len(partial) == 100         # the mid-block completions
    # abort archiver preserves the partial evidence untrusting
    out = bd.archive_b_diagnostic("abort", run_dir=run_dir,
                                  evidence_parent=tmp_path / "ev")
    assert out["mode"] == "abort"
    from pathlib import Path as _P
    dest = _P(out["evidence_dir"])
    assert (dest / "raw_completions_partial.json").exists()
    manifest = json.loads(
        (dest / "evidence_manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_status"] == "aborted"
    assert "raw_completions_partial.json" in manifest["files_present"]
    # 199_s finding 3: abort archival is ONLY for aborted runs — a
    # non-terminal status refuses outright
    (run_dir / "run_record.json").write_text(
        json.dumps({"status": "running"}), encoding="utf-8")
    with pytest.raises(InfrastructureError, match="mode success"):
        bd.archive_b_diagnostic("abort", run_dir=run_dir,
                                evidence_parent=tmp_path / "ev4")
    # success mode REFUSES the aborted root
    with pytest.raises(InfrastructureError,
                       match="file set|complete|not terminal"):
        bd.archive_b_diagnostic("success", run_dir=run_dir,
                                evidence_parent=tmp_path / "ev2",
                                pinned_loader=f["loader"])
