"""Descriptive B feasibility diagnostic — 195_f (rev3 of 190_f/193_f).

Separately identified, DESCRIPTIVE-ONLY machinery: it authorizes
nothing, computes no pass/fail, and its report is labelled as
iid-singleton plug-in prediction. Attempt-1 identities are never
touched; the formal v1-domain B seeds are neither consumed nor
derived here.

Contents: the frozen diagnostic contract and self-hashed pre-sampling
manifest (195_f §4.1); the exact seed registry (§4.2, 9,216 keys,
unpadded indices); the frozen counting boundary and integer artifact
with its count identities (§4.3); the authenticating verifier that
reproduces every count from raw evidence (§4.4); the descriptive
report over verifier-authenticated integers (§4.2/4.3); the
success/abort archiver (§4.5); the reward-blind smoke and the
one-shot driver sharing the repaired generation helper (§3); and the
CLI. Budgets are frozen literals (§4.6).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from . import stage1
from . import stage1_amend1 as am
from . import stage1_replay as sr
from .profiles import canonical_json
from .types import InfrastructureError, parse_render_instance_id

# --- §4.1/§4.2: frozen identity ---------------------------------------------------

B_DIAG_TAG = "stage1-b-diagnostic-v1"
B_DIAG_SEED_DOMAIN = "stage1-b-diagnostic-v1"
B_DIAG_RUN_ROOT = "runs/stage1-b-diagnostic"
B_DIAG_EVIDENCE_PARENT = Path("plans/conductor/evidence")

SMOKE_SEED_DOMAIN = "throwaway-b-smoke-v1"
SMOKE_COMPLETIONS_PER_PROMPT = 8            # ≤16 total (2 prompts)
SMOKE_DEADLINE_SECONDS = 10 * 60
DIAG_DEADLINE_SECONDS = 3 * 3600
MIN_FREE_VRAM_MIB = 8_192

REWARD_LEVELS = ("0", "0.5", "1")           # the frozen ladder

B_DIAGNOSTIC_CONTRACT: dict[str, Any] = {
    "contract": B_DIAG_TAG,
    # model/tokenizer identity (tokenizer revision pinned = model
    # revision; the chat-template hash is a LOAD-TIME value bound in
    # the manifest)
    "model_id": sr.REPLAY_CONTRACT["model_id"],
    "revision": sr.REPLAY_CONTRACT["revision"],
    "tokenizer_revision": sr.REPLAY_CONTRACT["revision"],
    # full construction + decoding literals (shared with the formal
    # replay contract; the smoke uses the same helper and kwargs)
    "adapter": sr.REPLAY_CONTRACT["adapter"],
    "quantization": dict(sr.REPLAY_CONTRACT["quantization"]),
    "attn_implementation": sr.REPLAY_CONTRACT["attn_implementation"],
    "sampling": dict(sr.REPLAY_CONTRACT["sampling"]),
    "generation_batch": 1,
    "rng_semantics": ("global CPU+CUDA RNG reset per singleton draw "
                      "from the registered diagnostic seed"),
    # scope
    "completions_per_observation_per_prompt": sr.REPLAY_COMPLETIONS,
    "observations": 18,
    "prompts": 2,
    "total_completions": 9_216,
    "support_declaration_sha256":
        sr.REPLAY_CONTRACT["support_declaration_sha256"],
    "surface_manifest_sha256":
        sr.REPLAY_CONTRACT["surface_manifest_sha256"],
    "prompt_fewshot_sha256": stage1.PROMPT_FEWSHOT_SHA256,
    "prompt_schema_only_sha256": stage1.PROMPT_SCHEMA_ONLY_SHA256,
    # seed identity (195_f §4.2, exact)
    "seed_domain": B_DIAG_SEED_DOMAIN,
    "seed_recipe": ("uint64_be(SHA256(utf8(domain||U+001F||key))"
                    "[0:8]); key = 'B-diag|{observation_id}|"
                    "{prompt_sha256}|{index}', index unpadded 0..255"),
    # parser and reward identity (code under the committed source
    # digest bound in the manifest)
    "parser": ("parser.parse_routing_action + "
               "grpo_task.positional_to_semantic"),
    "parseable_definition": "utf-8 encodable and json.loads succeeds",
    "valid_definition": ("the complete frozen parse_routing_action "
                         "schema succeeds"),
    "reward": ("levels {0, 0.5, 1}; non-valid -> 0; valid -> the "
               "pinned-surface payoff of the semantic assignment"),
    # budgets (frozen literals, 195_f §4.6)
    "smoke_completions_max": 2 * SMOKE_COMPLETIONS_PER_PROMPT,
    "smoke_deadline_seconds": SMOKE_DEADLINE_SECONDS,
    "diagnostic_deadline_seconds": DIAG_DEADLINE_SECONDS,
    "attempts": 1,
    "status": "descriptive; authorizes nothing; support is "
              "development data from first inspection",
}
_PROMPT_SHAS = (stage1.PROMPT_FEWSHOT_SHA256,
                stage1.PROMPT_SCHEMA_ONLY_SHA256)


def diagnostic_seed(observation_id: str, prompt_sha256: str,
                    index: int) -> int:
    """The exact 195_f §4.2 derivation (== am.seed on the diagnostic
    domain): uint64_be(SHA256(utf8(domain ␟ key))[0:8]), key with the
    UNPADDED index."""
    if not 0 <= index < sr.REPLAY_COMPLETIONS:
        raise InfrastructureError(f"index {index} out of range")
    return am.seed(B_DIAG_SEED_DOMAIN,
                   f"B-diag|{observation_id}|{prompt_sha256}|{index}")


def build_diagnostic_seed_registry(observation_ids: Iterable[str]
                                   ) -> dict[str, int]:
    """The exact 9,216-key registry (18 × 2 × 256, unpadded)."""
    obs = sorted(observation_ids)
    if len(obs) != 18 or len(set(obs)) != 18:
        raise InfrastructureError("diagnostic support must be exactly "
                                  "18 unique observations")
    registry = {
        f"B-diag|{oid}|{sha}|{i}": diagnostic_seed(oid, sha, i)
        for oid in obs for sha in _PROMPT_SHAS
        for i in range(sr.REPLAY_COMPLETIONS)}
    if len(registry) != 9_216:
        raise InfrastructureError("diagnostic registry != 9,216 keys")
    return registry


def generation_config_digest() -> str:
    """Hash of the exact kwargs the shared generation helper uses."""
    desc = {k: repr(v) for k, v in sr.GENERATION_KWARGS.items()}
    return hashlib.sha256(
        canonical_json(desc).encode("utf-8")).hexdigest()


# --- 197_s finding 1: the smoke/launch lock ------------------------------------------

SMOKE_RECORD_PATH = Path("plans/conductor/b_diagnostic_smoke_record.json")
LAUNCH_LOCK_PATH = Path("plans/conductor/b_diagnostic_launch_lock.json")


def current_executable_identity() -> dict[str, str]:
    """The four identities the smoke record carries and the launch
    lock must match (195_f §3 steps 4-5)."""
    from .stage1_manifest import stage1_source_digest
    return {
        "source_digest": stage1_source_digest(),
        "contract_sha256": hashlib.sha256(canonical_json(
            B_DIAGNOSTIC_CONTRACT).encode("utf-8")).hexdigest(),
        "generation_config_sha256": generation_config_digest(),
        "model_revision": B_DIAGNOSTIC_CONTRACT["revision"],
        "tokenizer_revision":
            B_DIAGNOSTIC_CONTRACT["tokenizer_revision"],
    }


def build_launch_lock(smoke_record_path: Path | str, *,
                      seed_registry: Mapping[str, int],
                      lock_path: Path | str | None = None
                      ) -> dict[str, Any]:
    """Step-5 launch lock: proves smoked executable == launched
    executable. Requires the PERSISTED smoke record to be complete
    and to carry exactly the CURRENT executable identities; binds the
    record's bytes, the identities, and the canonical seed-registry
    digest; self-hashed and written to the lock path."""
    import os
    record_path = Path(smoke_record_path)
    record_bytes = record_path.read_bytes()
    record = json.loads(record_bytes)
    if not isinstance(record, dict) or \
            record.get("status") != "complete":
        raise InfrastructureError(
            "launch lock refused: smoke record is not a complete run")
    ident = current_executable_identity()
    for field, value in ident.items():
        if record.get(field) != value:
            raise InfrastructureError(
                f"launch lock refused: smoke record {field!r} != the "
                "current executable — re-smoke after any change "
                "(195_f §3)")
    body = {
        "launch_lock": B_DIAG_TAG,
        "smoke_record_path": str(record_path),
        "smoke_record_sha256": hashlib.sha256(
            record_bytes).hexdigest(),
        "seed_registry_sha256": am.seed_registry_digest(seed_registry),
        **ident,
    }
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    lock = dict(body)
    lock["launch_lock_sha256"] = digest
    path = Path(lock_path if lock_path is not None
                else LAUNCH_LOCK_PATH)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(lock, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    return lock


def validate_launch_lock(lock: Mapping[str, Any], *,
                         seed_registry: Mapping[str, int]) -> None:
    """The consuming boundary (197_s finding 1): the diagnostic may
    not sample retained support unless the committed launch lock
    matches the CURRENT executable identities, the canonical
    registry, and the persisted smoke record's bytes."""
    body = {k: v for k, v in lock.items() if k != "launch_lock_sha256"}
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if digest != lock.get("launch_lock_sha256"):
        raise InfrastructureError("launch lock hash mismatch")
    if lock.get("launch_lock") != B_DIAG_TAG:
        raise InfrastructureError("not a B-diagnostic launch lock")
    ident = current_executable_identity()
    for field, value in ident.items():
        if lock.get(field) != value:
            raise InfrastructureError(
                f"launch lock {field!r} != the current executable — "
                "smoked != launched; return to review and re-smoke")
    if lock.get("seed_registry_sha256") != \
            am.seed_registry_digest(seed_registry):
        raise InfrastructureError(
            "launch lock does not bind this seed registry")
    record_path = Path(lock["smoke_record_path"])
    if not record_path.is_file():
        raise InfrastructureError(
            "the smoke record the launch lock binds is absent")
    if hashlib.sha256(record_path.read_bytes()).hexdigest() != \
            lock["smoke_record_sha256"]:
        raise InfrastructureError(
            "smoke record bytes != the launch lock binding")


# --- §4.1: the self-hashed pre-sampling manifest -----------------------------------

def build_diagnostic_manifest(env_manifest_sha256: str,
                              source_digest: str,
                              chat_template_sha256: str,
                              observation_ids: Iterable[str],
                              rendered_request_hashes: Mapping[str, str],
                              seed_registry: Mapping[str, int]
                              ) -> dict[str, Any]:
    obs = sorted(observation_ids)
    expected_rr = {f"{o}|{p}" for o in obs for p in _PROMPT_SHAS}
    if set(rendered_request_hashes) != expected_rr:
        raise InfrastructureError(
            "rendered-request hashes do not cover exactly "
            "observation x prompt")
    if set(seed_registry) != {
            f"B-diag|{o}|{p}|{i}" for o in obs for p in _PROMPT_SHAS
            for i in range(sr.REPLAY_COMPLETIONS)}:
        raise InfrastructureError("seed registry key set mismatch")
    body: dict[str, Any] = {
        "manifest": "stage1-b-diagnostic-manifest-v1",
        "contract": dict(B_DIAGNOSTIC_CONTRACT),
        "environment_manifest_sha256": env_manifest_sha256,
        "stage1_source_sha256": source_digest,
        "chat_template_sha256": chat_template_sha256,
        "generation_config_sha256": generation_config_digest(),
        "observation_ids": obs,
        "rendered_request_sha256": dict(
            sorted(rendered_request_hashes.items())),
        "seed_registry_sha256": am.seed_registry_digest(seed_registry),
    }
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    out = dict(body)
    out["manifest_sha256"] = digest
    return out


def validate_diagnostic_manifest(manifest: Mapping[str, Any]) -> str:
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if digest != manifest.get("manifest_sha256"):
        raise InfrastructureError("diagnostic manifest hash mismatch")
    if manifest.get("manifest") != "stage1-b-diagnostic-manifest-v1" \
            or manifest.get("contract") != B_DIAGNOSTIC_CONTRACT:
        raise InfrastructureError(
            "diagnostic manifest kind/contract mismatch")
    return digest


# --- §4.3: the frozen counting boundary --------------------------------------------

def _reward_level(payoff: float) -> str:
    if payoff == 0.5:
        return "0.5"
    if payoff == 1.0:
        return "1"
    raise InfrastructureError(
        f"pinned-surface payoff {payoff!r} outside the frozen "
        "{0.5, 1.0} support levels — contract violation (195_f §4.3)")


def count_from_raw(raw: Mapping[str, str],
                   rows: Mapping[str, Mapping[str, Any]],
                   surface: Mapping[tuple[str, tuple[int, ...]], float]
                   ) -> dict[str, dict[str, Any]]:
    """THE counting function (used by the driver AND re-run by the
    verifier on the same raw bytes): per (observation × prompt) —
    n = 256; `parseable` (utf-8 + json.loads); `valid` (complete
    frozen parse schema); sparse semantic assignment→count map over
    VALID draws; reward-level counts over ALL draws (non-valid → 0,
    valid → the pinned-surface payoff)."""
    from .grpo_task import positional_to_semantic
    from .parser import ActionSchemaError, parse_routing_action
    results: dict[str, dict[str, Any]] = {}
    for oid, row in sorted(rows.items()):
        positions = row["positions"]
        if isinstance(positions, str):
            positions = json.loads(positions)
        for sha in _PROMPT_SHAS:
            parseable = valid = 0
            assignments: dict[str, int] = {}
            levels = {level: 0 for level in REWARD_LEVELS}
            for i in range(sr.REPLAY_COMPLETIONS):
                text = raw[f"{oid}|{sha}|{i:03d}"]
                try:
                    text.encode("utf-8")
                except UnicodeEncodeError:
                    # 197_s: non-UTF-8 output is non-parseable and
                    # reward-zero, never an abort
                    levels["0"] += 1
                    continue
                try:
                    json.loads(text)
                except ValueError:
                    levels["0"] += 1
                    continue
                parseable += 1
                try:
                    action = parse_routing_action(text,
                                                  row["num_steps"])
                except ActionSchemaError:
                    levels["0"] += 1
                    continue
                valid += 1
                semantic = tuple(positional_to_semantic(action,
                                                        positions))
                akey = ",".join(str(w) for w in semantic)
                assignments[akey] = assignments.get(akey, 0) + 1
                payoff = surface.get((oid, semantic))
                if payoff is None:
                    raise InfrastructureError(
                        f"{oid}: valid assignment {semantic} has no "
                        "pinned-surface row — the surface must cover "
                        "the full 4^S space")
                levels[_reward_level(float(payoff))] += 1
            results[f"{oid}|{sha}"] = {
                "n": sr.REPLAY_COMPLETIONS, "parseable": parseable,
                "valid": valid,
                "assignments": dict(sorted(assignments.items())),
                "reward_levels": levels,
            }
    return results


def _check_result_row(key: str, row: Mapping[str, Any]) -> None:
    """The frozen §4.3 identities, enforced at build AND load."""
    for field in ("n", "parseable", "valid"):
        if type(row.get(field)) is not int or row[field] < 0:
            raise InfrastructureError(f"{key}: bad {field!r}")
    if not (0 <= row["valid"] <= row["parseable"] <= row["n"] == 256):
        raise InfrastructureError(
            f"{key}: valid <= parseable <= n == 256 violated")
    assignments = row.get("assignments")
    levels = row.get("reward_levels")
    if not isinstance(assignments, dict) or not isinstance(levels, dict):
        raise InfrastructureError(f"{key}: malformed maps")
    if set(row) != {"n", "parseable", "valid", "assignments",
                    "reward_levels"}:
        raise InfrastructureError(f"{key}: wrong field set")
    if any(type(v) is not int or v < 0 for v in assignments.values()):
        raise InfrastructureError(f"{key}: bad assignment count")
    if set(levels) != set(REWARD_LEVELS) or \
            any(type(v) is not int or v < 0 for v in levels.values()):
        raise InfrastructureError(f"{key}: bad reward levels")
    if sum(assignments.values()) != row["valid"]:
        raise InfrastructureError(
            f"{key}: sum(assignments) != valid")
    if sum(levels.values()) != 256:
        raise InfrastructureError(f"{key}: sum(reward levels) != 256")
    if levels["0"] != 256 - row["valid"]:
        raise InfrastructureError(
            f"{key}: reward_0 != 256 - valid (frozen 194_s identity; "
            "the pinned surface has no payoff-0 rows)")


def build_diagnostic_artifact(manifest_sha256: str,
                              env_manifest_sha256: str,
                              raw_completions_sha256: str,
                              results: Mapping[str, Mapping[str, Any]],
                              observation_ids: Iterable[str]
                              ) -> dict[str, Any]:
    expected = {f"{o}|{p}" for o in sorted(observation_ids)
                for p in _PROMPT_SHAS}
    if set(results) != expected:
        raise InfrastructureError(
            "diagnostic results != exact observation x prompt set")
    for key, row in results.items():
        _check_result_row(key, row)
    body = {
        "artifact": "B-diagnostic", "tag": B_DIAG_TAG,
        "manifest_sha256": manifest_sha256,
        "environment_manifest_sha256": env_manifest_sha256,
        "raw_completions_sha256": raw_completions_sha256,
        "results": {k: {"n": v["n"], "parseable": v["parseable"],
                        "valid": v["valid"],
                        "assignments": dict(sorted(
                            v["assignments"].items())),
                        "reward_levels": dict(v["reward_levels"])}
                    for k, v in sorted(results.items())},
    }
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    out = dict(body)
    out["artifact_sha256"] = digest
    return out


def load_diagnostic_artifact(artifact: Mapping[str, Any],
                             manifest_sha256: str) -> dict[str, Any]:
    body = {k: v for k, v in artifact.items() if k != "artifact_sha256"}
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    if digest != artifact.get("artifact_sha256"):
        raise InfrastructureError("diagnostic artifact hash mismatch")
    if artifact.get("artifact") != "B-diagnostic" or \
            artifact.get("tag") != B_DIAG_TAG:
        raise InfrastructureError("diagnostic artifact kind/tag "
                                  "mismatch")
    if artifact.get("manifest_sha256") != manifest_sha256:
        raise InfrastructureError(
            "diagnostic artifact names a different manifest")
    for key, row in artifact["results"].items():
        _check_result_row(key, row)
    return dict(artifact)


# --- §4.4: the authenticating verifier ----------------------------------------------

def load_pinned_diagnostic_inputs() -> dict[str, Any]:
    """The authoritative loader: pinned surface, support rows,
    messages, rendered-request hashes, tokenizer (shared with the
    formal replay path)."""
    return sr._load_replay_inputs_full()


def verify_b_diagnostic_evidence(artifact: Mapping[str, Any], *,
                                 manifest: Mapping[str, Any],
                                 raw_completions_text: str,
                                 env_manifest: Mapping[str, Any],
                                 pinned_loader:
                                 Callable[[], dict[str, Any]] | None
                                 = None) -> dict[str, dict[str, Any]]:
    """THE consuming boundary (195_f §4.4): exact 9,216 raw keys,
    `raw_completions_sha256` binding, full reparse reproducing
    `parseable` AND `valid` exactly, positional→semantic conversion,
    rescore against the pinned surface, exact equality with every
    persisted assignment and reward-level count, the §4.3 identities,
    the manifest self-hash + regenerated rendered-request hashes +
    registry digest, and the environment binding. Returns the
    authenticated results."""
    from .stage1_manifest import validate_env_manifest
    env_sha = validate_env_manifest(env_manifest)
    manifest_sha = validate_diagnostic_manifest(manifest)
    if manifest["environment_manifest_sha256"] != env_sha:
        raise InfrastructureError(
            "diagnostic manifest does not bind this environment")
    loaded = load_diagnostic_artifact(artifact, manifest_sha)
    if loaded["environment_manifest_sha256"] != env_sha:
        raise InfrastructureError(
            "diagnostic artifact does not bind this environment")

    loader = pinned_loader or load_pinned_diagnostic_inputs
    inputs = loader()
    surface, rows = inputs["surface"], inputs["rows"]
    if sorted(rows) != manifest["observation_ids"]:
        raise InfrastructureError(
            "manifest observation ids != authoritative support")
    if manifest["rendered_request_sha256"] != dict(
            sorted(inputs["rr_hashes"].items())):
        raise InfrastructureError(
            "manifest rendered-request hashes do not regenerate")
    registry = build_diagnostic_seed_registry(sorted(rows))
    if manifest["seed_registry_sha256"] != \
            am.seed_registry_digest(registry):
        raise InfrastructureError(
            "manifest seed-registry digest != the canonical registry")
    # 197_s finding 2: provenance claims are independently RE-DERIVED,
    # never accepted as well-formed hashes
    if manifest["stage1_source_sha256"] != \
            env_manifest["stage1_source_sha256"]:
        raise InfrastructureError(
            "manifest stage1_source_sha256 != the validated "
            "environment manifest's source identity")
    if manifest["generation_config_sha256"] != \
            generation_config_digest():
        raise InfrastructureError(
            "manifest generation_config_sha256 != the digest of the "
            "frozen generation kwargs")
    tokenizer = inputs.get("tokenizer")
    chat_template = getattr(tokenizer, "chat_template", None)
    if chat_template is None:
        raise InfrastructureError(
            "the pinned loader supplied no tokenizer chat template — "
            "chat_template_sha256 cannot be verified (197_s)")
    if manifest["chat_template_sha256"] != hashlib.sha256(
            str(chat_template).encode("utf-8")).hexdigest():
        raise InfrastructureError(
            "manifest chat_template_sha256 != the pinned tokenizer's "
            "chat template")

    raw_sha = hashlib.sha256(
        raw_completions_text.encode("utf-8")).hexdigest()
    if raw_sha != loaded["raw_completions_sha256"]:
        raise InfrastructureError(
            "raw completions do not hash to the artifact binding")
    raw = json.loads(raw_completions_text)
    if set(raw) != sr.expected_completion_keys(sorted(rows)):
        raise InfrastructureError(
            "raw completions do not cover exactly the 9,216 keys")

    recounted = count_from_raw(raw, rows, surface)
    persisted = {k: dict(v) for k, v in loaded["results"].items()}
    if recounted != persisted:
        raise InfrastructureError(
            "persisted diagnostic counts do not reproduce from the "
            "raw completions")
    return recounted


# --- §4.2/§4.3: the descriptive report ----------------------------------------------

REPORT_LABEL = ("descriptive; iid-singleton plug-in predictions, not "
                "measurements of batched GRPO groups or gradients; "
                "authorizes nothing; support is development data from "
                "first inspection")


def _plugin_quantities(row: Mapping[str, Any],
                       pair: Mapping[str, Any] | None
                       ) -> dict[str, Any]:
    n = row["n"]
    p_levels = {lv: row["reward_levels"][lv] / n
                for lv in REWARD_LEVELS}
    zero_var = sum(p ** 8 for p in p_levels.values())
    diversity = sum(1.0 - (1.0 - p) ** 8 for p in p_levels.values())
    out: dict[str, Any] = {
        "parse_rate": row["parseable"] / n,
        "valid_rate": row["valid"] / n,
        "zero_variance_group_fraction": zero_var,
        "expected_reward_level_diversity": diversity,
        # 197_s finding 3: signed outputs — the full reward-level
        # frequencies and the action distribution travel per row
        "reward_rate_0": p_levels["0"],
        "reward_rate_0.5": p_levels["0.5"],
        "reward_rate_1": p_levels["1"],
        "assignment_rates": {k: v / n
                             for k, v in row["assignments"].items()},
        "p2": None, "p3": None, "g8": None,
    }
    if pair is not None:
        w2 = ",".join(str(w) for w in pair["assignment_w2"])
        w3 = ",".join(str(w) for w in pair["assignment_w3"])
        p2 = row["assignments"].get(w2, 0) / n
        p3 = row["assignments"].get(w3, 0) / n
        out.update({"p2": p2, "p3": p3,
                    "g8": sr.g_direct_gradient(p2, p3)})
    return out


def _aggregate_detail(values_by_obs: Mapping[str, float],
                      obs_meta: Mapping[str, Mapping[str, str]]
                      ) -> dict[str, Any]:
    """197_s finding 3: the frozen renderer→latent→equal-cell
    weighting, EXPOSED at every level — per-cell means plus the
    overall equal-cell mean (the overall value equals
    `sr._aggregate` by construction)."""
    cells: dict[str, dict[str, dict[str, float]]] = {}
    for obs, value in values_by_obs.items():
        meta = obs_meta[obs]
        cells.setdefault(meta["cell_id"], {}).setdefault(
            meta["latent"], {})[meta["renderer"]] = value
    per_cell = {}
    for cell, latents in sorted(cells.items()):
        latent_means = [sum(r.values()) / len(r)
                        for r in latents.values()]
        per_cell[cell] = sum(latent_means) / len(latent_means)
    return {"equal_cell": sum(per_cell.values()) / len(per_cell),
            "per_cell": per_cell}


def build_b_diagnostic_report(results: Mapping[str, Mapping[str, Any]],
                              pair_table: Mapping[str,
                                                  Mapping[str, Any]],
                              obs_meta: Mapping[str,
                                                Mapping[str, str]]
                              ) -> dict[str, Any]:
    """From VERIFIER-AUTHENTICATED integers only. Per-(observation ×
    prompt) rows first, then renderer→latent→equal-cell aggregation
    (the frozen weighting). Direction summaries (p2/p3/g8) use ONLY
    distinct-payoff pairs, reported separately for w2-favoured and
    w3-favoured; tied pairs are reported separately and never
    described as gradient-bearing; parse/valid/reward summaries use
    all 18 observations."""
    per_row: dict[str, dict[str, Any]] = {}
    for key, row in results.items():
        oid, sha = key.rsplit("|", 1)
        pair = pair_table.get(oid)
        q = _plugin_quantities(row, pair)
        q["population"] = (
            "tied_pair" if pair is not None
            and not pair["distinct_payoff"] else
            f"w{pair['direction']}_favoured" if pair is not None
            else "no_pair")
        per_row[key] = q

    def _agg(metric: str, keys: list[str],
             prompt_sha: str) -> dict[str, Any] | None:
        values = {k.rsplit("|", 1)[0]: per_row[k][metric]
                  for k in keys if k.endswith(prompt_sha)
                  and per_row[k][metric] is not None}
        if not values:
            return None
        return _aggregate_detail(values, obs_meta)

    populations = {
        "all_18": [k for k in per_row],
        "w2_favoured": [k for k, q in per_row.items()
                        if q["population"] == "w2_favoured"],
        "w3_favoured": [k for k, q in per_row.items()
                        if q["population"] == "w3_favoured"],
        "tied_pairs": [k for k, q in per_row.items()
                       if q["population"] == "tied_pair"],
    }
    # 197_s finding 3: explicit denominators and support composition
    n_pairs = len(pair_table)
    n_distinct = sum(1 for p in pair_table.values()
                     if p["distinct_payoff"])
    report: dict[str, Any] = {
        "label": REPORT_LABEL,
        "support_composition": {
            "observations": len(obs_meta),
            "pair_observations": n_pairs,
            "distinct_payoff_pairs": n_distinct,
            "w2_favoured": sum(1 for p in pair_table.values()
                               if p["direction"] == 2),
            "w3_favoured": sum(1 for p in pair_table.values()
                               if p["direction"] == 3),
            "tied_pairs": n_pairs - n_distinct,
        },
        "populations": {
            pop: {"row_count": len(keys),
                  "observation_count":
                      len({k.rsplit("|", 1)[0] for k in keys})}
            for pop, keys in populations.items()},
        "per_observation_prompt": per_row,
        "aggregates": {},
    }
    for prompt_name, sha in (("fewshot", _PROMPT_SHAS[0]),
                             ("schema_only", _PROMPT_SHAS[1])):
        block: dict[str, Any] = {}
        for pop, keys in populations.items():
            metrics = ["parse_rate", "valid_rate",
                       "zero_variance_group_fraction",
                       "expected_reward_level_diversity",
                       "reward_rate_0", "reward_rate_0.5",
                       "reward_rate_1"]
            if pop in ("w2_favoured", "w3_favoured"):
                metrics += ["p2", "p3", "g8"]
            if pop == "tied_pairs":
                # selection behavior only — never gradient-bearing
                metrics += ["p2", "p3"]
            block[pop] = {m: _agg(m, keys, sha) for m in metrics}
        report["aggregates"][prompt_name] = block
    return report


# --- preflight, smoke, driver, archiver (§3, §4.5) ----------------------------------

def vram_preflight() -> dict[str, Any]:
    """Ollama/free-VRAM preflight (195_f §3): refuse to load the model
    unless free VRAM >= the floor; the result is part of the record."""
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.free,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True).stdout.strip()
    free_mib, total_mib = (int(x.strip()) for x in out.split(","))
    record = {"free_mib": free_mib, "total_mib": total_mib,
              "floor_mib": MIN_FREE_VRAM_MIB}
    if free_mib < MIN_FREE_VRAM_MIB:
        raise InfrastructureError(
            f"VRAM preflight: {free_mib} MiB free < "
            f"{MIN_FREE_VRAM_MIB} MiB floor — resolve (ollama?) first")
    return record


SMOKE_OOD_USER = ("SMOKE (throwaway, out-of-distribution): respond "
                  "with a routing action for a 1-step task.")
SMOKE_OID = "smoke-ood-00000"


def _load_smoke_tokenizer():
    """197_s: the synthetic smoke needs ONLY the tokenizer — never
    the retained-support surface or rows."""
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(
        B_DIAGNOSTIC_CONTRACT["model_id"],
        revision=B_DIAGNOSTIC_CONTRACT["tokenizer_revision"])


def run_b_smoke(_inputs: Mapping[str, Any] | None = None,
                record_path: Path | str | None = None
                ) -> dict[str, Any]:
    """The reward-blind smoke (195_f §3): SAME helper
    (`sr._generate`), SAME constructor (`sr._build_replay_model`),
    SAME kwargs (`sr.GENERATION_KWARGS`); one synthetic OOD input;
    both frozen system prompts; ≤16 completions; 10-minute in-loop
    monotonic deadline; discloses ONLY shape/runtime validity.
    Outputs are discarded — never parsed, scored, or persisted. The
    record (identities included) is PERSISTED for the launch lock."""
    import os
    import time

    from .stage1_manifest import build_stage1_env_manifest
    preflight = None if _inputs is not None else vram_preflight()
    env = build_stage1_env_manifest()
    tokenizer = (_inputs or {}).get("tokenizer") or \
        _load_smoke_tokenizer()
    rows = {SMOKE_OID: {"positions": json.dumps(["n1"]),
                        "num_steps": 1}}
    messages = {}
    for sha, text in ((_PROMPT_SHAS[0], stage1.prompt_fewshot()),
                      (_PROMPT_SHAS[1], stage1.prompt_schema_only())):
        messages[f"{SMOKE_OID}|{sha}"] = [
            {"role": "system", "content": text},
            {"role": "user", "content": SMOKE_OOD_USER}]

    started = time.monotonic()
    record: dict[str, Any] = {
        "smoke": B_DIAG_TAG, "preflight": preflight,
        "environment_manifest_sha256":
            env["execution_manifest_sha256"],
        # the four identities the launch lock must match, plus the
        # explicit tokenizer revision (197_s)
        **current_executable_identity(),
        "budget_completions": 2 * SMOKE_COMPLETIONS_PER_PROMPT,
        "deadline_seconds": SMOKE_DEADLINE_SECONDS,
    }

    def _persist_record() -> None:
        path = Path(record_path if record_path is not None
                    else SMOKE_RECORD_PATH)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=1), encoding="utf-8")
        os.replace(tmp, path)

    try:
        # 197_s: record the prompt tensor shapes explicitly (same
        # tokenizer call the shared helper makes)
        record["prompt_input_ids_shapes"] = {
            sha: list(tokenizer.apply_chat_template(
                messages[f"{SMOKE_OID}|{sha}"], tokenize=True,
                return_tensors="pt",
                add_generation_prompt=True)["input_ids"].shape)
            for sha in _PROMPT_SHAS}
        model = (_inputs or {}).get("_model") or \
            sr._build_replay_model()
        raw: dict[str, str] = {}
        sr._generate(
            model, tokenizer, rows, messages, {}, raw, {},
            seed_of=lambda oid, sha, i: am.seed(
                SMOKE_SEED_DOMAIN, f"{oid}|{sha}|{i}"),
            n_completions=SMOKE_COMPLETIONS_PER_PROMPT,
            deadline_seconds=SMOKE_DEADLINE_SECONDS)
        record.update({
            "status": "complete",
            "completions": len(raw),
            "nonempty_completions": sum(1 for t in raw.values() if t),
            "completion_char_lengths": sorted(len(t)
                                              for t in raw.values()),
            "wall_seconds": round(time.monotonic() - started, 1),
        })
        try:
            import torch
            record["vram_peak_mib"] = int(
                torch.cuda.max_memory_allocated() / 2**20)
        except Exception:
            record["vram_peak_mib"] = None
        _persist_record()
    except BaseException as error:
        record.update({"status": "aborted",
                       "error": f"{type(error).__name__}: {error}",
                       "wall_seconds": round(
                           time.monotonic() - started, 1)})
        _persist_record()
        raise SmokeFailure(json.dumps(record, indent=1)) from error
    return record


class SmokeFailure(InfrastructureError):
    """Smoke abort carrying its engineering record verbatim."""


def run_b_diagnostic(*, allow_dirty: bool = False,
                     _inputs: Mapping[str, Any] | None = None,
                     launch_lock_path: Path | str | None = None
                     ) -> dict[str, Any]:
    """The one-shot diagnostic (195_f §4): LAUNCH LOCK enforced at
    this consuming boundary (197_s finding 1 — retained support
    cannot be sampled without a committed lock matching the current
    executable, the registry, and the persisted smoke record) →
    preflight → manifest persisted BEFORE model work → shared
    repaired helper with the registered diagnostic seeds, 3-hour
    in-loop monotonic deadline and staged persistence → integer
    artifact with the frozen identities → authenticating
    verification → complete record. Aborts atomically preserve the
    CURRENT in-memory raw map (mid-block included, 197_s finding 4)
    and the aborted record."""
    import os
    import time

    from .stage1_manifest import (build_stage1_env_manifest,
                                  stage1_source_digest)
    preflight = None if _inputs is not None else vram_preflight()
    env = build_stage1_env_manifest(allow_dirty=allow_dirty)
    env_sha = env["execution_manifest_sha256"]
    inputs = _inputs or sr._load_replay_inputs_full()
    surface, rows = inputs["surface"], inputs["rows"]
    messages, rr_hashes = inputs["messages"], inputs["rr_hashes"]
    tokenizer = inputs["tokenizer"]
    chat_template = getattr(tokenizer, "chat_template", None) or ""
    registry = build_diagnostic_seed_registry(sorted(rows))

    # 197_s finding 1: no lock, no sampling
    lock_file = Path(launch_lock_path if launch_lock_path is not None
                     else LAUNCH_LOCK_PATH)
    if not lock_file.is_file():
        raise InfrastructureError(
            "no committed launch lock — the diagnostic may not "
            "sample retained support (197_s finding 1; 195_f §3 "
            "step 5)")
    validate_launch_lock(
        json.loads(lock_file.read_text(encoding="utf-8")),
        seed_registry=registry)

    manifest = build_diagnostic_manifest(
        env_sha, stage1_source_digest(),
        hashlib.sha256(str(chat_template).encode("utf-8")).hexdigest(),
        sorted(rows), rr_hashes, registry)

    out_dir = am.claim_run_root(B_DIAG_RUN_ROOT)
    (out_dir / "diagnostic_manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    (out_dir / "env_manifest.json").write_text(
        json.dumps(env, indent=1), encoding="utf-8")
    record: dict[str, Any] = {"status": "running",
                              "tag": B_DIAG_TAG,
                              "preflight": preflight,
                              "manifest_sha256":
                                  manifest["manifest_sha256"],
                              "started_unix": int(time.time())}
    started = time.monotonic()
    (out_dir / "run_record.json").write_text(
        json.dumps(record, indent=1), encoding="utf-8")

    raw: dict[str, str] = {}

    def _flush_partial(*_args: str) -> None:
        # ensure_ascii=True: surrogate/non-UTF-8 completions are
        # escaped rather than crashing persistence (197_s)
        tmp = out_dir / "raw_completions_partial.json.tmp"
        tmp.write_text(
            json.dumps(dict(sorted(raw.items())), ensure_ascii=True),
            encoding="utf-8")
        os.replace(tmp, out_dir / "raw_completions_partial.json")

    def _registered_seed(oid: str, sha: str, i: int) -> int:
        value = registry.get(f"B-diag|{oid}|{sha}|{i}")
        if value is None:
            raise InfrastructureError(
                f"no registered diagnostic seed for {oid}|{sha}|{i}")
        return value

    def _finish(status: str, error_text: str | None = None) -> None:
        record["status"] = status
        record["wall_seconds"] = int(time.monotonic() - started)
        if error_text:
            record["error"] = error_text
        (out_dir / "run_record.json").write_text(
            json.dumps(record, indent=1), encoding="utf-8")

    try:
        model = (_inputs or {}).get("_model") or \
            sr._build_replay_model()
        sr._generate(model, tokenizer, rows, messages, {}, raw, {},
                     seed_of=_registered_seed,
                     deadline_seconds=DIAG_DEADLINE_SECONDS,
                     on_block_complete=_flush_partial)
        if set(raw) != sr.expected_completion_keys(sorted(rows)):
            raise InfrastructureError(
                f"accounting incomplete: {len(raw)} raw completions")
        raw_blob = json.dumps(dict(sorted(raw.items())),
                              ensure_ascii=True)
        raw_sha = hashlib.sha256(raw_blob.encode("utf-8")).hexdigest()
        (out_dir / "raw_completions.json").write_text(
            raw_blob, encoding="utf-8")
        (out_dir / "raw_completions_partial.json").unlink(
            missing_ok=True)
        results = count_from_raw(raw, rows, surface)
        artifact = build_diagnostic_artifact(
            manifest["manifest_sha256"], env_sha, raw_sha, results,
            sorted(rows))
        (out_dir / "artifact_B_diagnostic.json").write_text(
            json.dumps(artifact, indent=1), encoding="utf-8")
        reloaded = json.loads(
            (out_dir / "artifact_B_diagnostic.json").read_text(
                encoding="utf-8"))
        verify_b_diagnostic_evidence(
            reloaded, manifest=manifest,
            raw_completions_text=raw_blob, env_manifest=env,
            pinned_loader=(lambda: inputs) if _inputs else None)
        _finish("complete")
    except BaseException as error:
        # 197_s finding 4: atomically persist the CURRENT in-memory
        # raw map — mid-block completions are never lost
        try:
            _flush_partial()
        except Exception:
            pass  # the abort record below still lands
        _finish("aborted", f"{type(error).__name__}: {error}")
        raise
    return {"run_dir": str(out_dir),
            "manifest_sha256": manifest["manifest_sha256"],
            "raw_completions_sha256": raw_sha,
            "artifact_sha256": artifact["artifact_sha256"]}


DIAG_SUCCESS_FILES = frozenset({
    "diagnostic_manifest.json", "env_manifest.json",
    "raw_completions.json", "artifact_B_diagnostic.json",
    "run_record.json"})


def archive_b_diagnostic(mode: str,
                         run_dir: Path | str | None = None,
                         evidence_parent: Path | str | None = None,
                         pinned_loader=None) -> dict[str, Any]:
    """§4.5 archiver, mirroring the attempt-1 semantics: staged copy
    + byte/length/SHA-256 manifest + verification + atomic rename;
    refuses a pre-existing destination. Success REQUIRES the exact
    file set, a complete record, and the §4.4 authenticating
    verifier; abort preserves whatever exists (partial raw included)
    WITHOUT trusting a complete artifact, recording validation
    errors."""
    if mode not in ("success", "abort"):
        raise InfrastructureError(f"unknown archive mode {mode!r}")
    src = Path(run_dir if run_dir is not None else B_DIAG_RUN_ROOT)
    if not src.is_dir():
        raise InfrastructureError(f"{src} does not exist")
    errors: list[str] = []
    manifest_sha = None
    try:
        manifest = json.loads(
            (src / "diagnostic_manifest.json").read_text("utf-8"))
        if isinstance(manifest, dict):
            manifest_sha = validate_diagnostic_manifest(manifest)
        else:
            errors.append("diagnostic manifest is not a JSON object")
    except FileNotFoundError:
        errors.append("diagnostic manifest absent")
    except (ValueError, InfrastructureError) as error:
        errors.append(f"diagnostic manifest invalid: {error}")

    # 197_s: the run record's TERMINAL status and the present files
    # are validated in BOTH modes (recorded in abort, refused in
    # success via the checks below)
    status = "absent"
    record_file = src / "run_record.json"
    if record_file.is_file():
        try:
            loaded_record = json.loads(record_file.read_text("utf-8"))
            status = loaded_record.get("status", "unknown") \
                if isinstance(loaded_record, dict) else "malformed"
        except ValueError:
            status = "unreadable"
    if status not in ("complete", "aborted"):
        errors.append(f"run record status {status!r} is not terminal")
    present = sorted(p.name for p in src.iterdir() if p.is_file())
    if "run_record.json" not in present:
        errors.append("run record absent")

    if mode == "success":
        if errors:
            raise InfrastructureError(
                "success archive refused: " + "; ".join(errors))
        got = {p.name for p in src.iterdir() if p.is_file()}
        if got != set(DIAG_SUCCESS_FILES):
            raise InfrastructureError(
                f"success archive refused: file set (missing "
                f"{sorted(set(DIAG_SUCCESS_FILES) - got)}, extra "
                f"{sorted(got - set(DIAG_SUCCESS_FILES))})")
        run_record = json.loads(
            (src / "run_record.json").read_text("utf-8"))
        if run_record.get("status") != "complete":
            raise InfrastructureError("success archive refused: run "
                                      "record not complete")
        verify_b_diagnostic_evidence(
            json.loads((src / "artifact_B_diagnostic.json"
                        ).read_text("utf-8")),
            manifest=manifest,
            raw_completions_text=(src / "raw_completions.json"
                                  ).read_text("utf-8"),
            env_manifest=json.loads(
                (src / "env_manifest.json").read_text("utf-8")),
            pinned_loader=pinned_loader)

    if manifest_sha is not None:
        first12 = manifest_sha[:12]
    else:
        path = src / "diagnostic_manifest.json"
        raw_bytes = path.read_bytes() if path.is_file() else b"missing"
        first12 = hashlib.sha256(raw_bytes).hexdigest()[:12]
    parent = Path(evidence_parent if evidence_parent is not None
                  else B_DIAG_EVIDENCE_PARENT)
    dest = parent / f"stage1_b_diagnostic_{first12}"
    staging = parent / f".staging_stage1_b_diagnostic_{first12}"
    if dest.exists():
        raise InfrastructureError(f"{dest} already exists — evidence "
                                  "archives are immutable")
    if staging.exists():
        raise InfrastructureError(f"{staging} already exists — stale "
                                  "staging")
    files: dict[str, dict[str, Any]] = {}
    staging.mkdir(parents=True)
    for path in sorted(src.iterdir()):
        if not path.is_file():
            raise InfrastructureError(
                f"{src}: unexpected non-file entry {path.name!r}")
        data = path.read_bytes()
        (staging / path.name).write_bytes(data)
        files[path.name] = {"sha256":
                            hashlib.sha256(data).hexdigest(),
                            "bytes": len(data)}
    evidence_manifest = {
        "manifest": "stage1-b-diagnostic-evidence-v1", "mode": mode,
        "diagnostic_manifest_sha256": manifest_sha,
        "run_status": status, "files_present": present,
        "validation_errors": errors, "files": files,
    }
    text = json.dumps(evidence_manifest, indent=1)
    (staging / "evidence_manifest.json").write_text(text,
                                                    encoding="utf-8")
    for name, entry in files.items():
        archived = (staging / name).read_bytes()
        if archived != (src / name).read_bytes() or \
                hashlib.sha256(archived).hexdigest() != entry["sha256"]:
            raise InfrastructureError(
                f"archive verification failed: {name}")
    staging.rename(dest)
    return {"evidence_dir": str(dest), "mode": mode,
            "evidence_manifest_sha256": hashlib.sha256(
                text.encode("utf-8")).hexdigest(),
            "validation_errors": errors}


# --- CLI -----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Descriptive B diagnostic commands (195_f)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("smoke", "run", "report"):
        sub.add_parser(name)
    archive = sub.add_parser("archive")
    archive.add_argument("--mode", required=True,
                         choices=("success", "abort"))
    args = parser.parse_args(argv)

    if args.command == "smoke":
        print(json.dumps(run_b_smoke(), indent=1))
    elif args.command == "run":
        print(json.dumps(run_b_diagnostic(), indent=1, default=str))
    elif args.command == "archive":
        print(json.dumps(archive_b_diagnostic(args.mode), indent=1))
    else:
        src = Path(B_DIAG_RUN_ROOT)
        manifest = json.loads(
            (src / "diagnostic_manifest.json").read_text("utf-8"))
        env = json.loads(
            (src / "env_manifest.json").read_text("utf-8"))
        artifact = json.loads(
            (src / "artifact_B_diagnostic.json").read_text("utf-8"))
        raw_text = (src / "raw_completions.json").read_text("utf-8")
        results = verify_b_diagnostic_evidence(
            artifact, manifest=manifest,
            raw_completions_text=raw_text, env_manifest=env)
        inputs = load_pinned_diagnostic_inputs()
        cell_of = {oid: row["cell_id"]
                   for oid, row in inputs["rows"].items()}
        table = sr.pair_table_from_surface(inputs["surface"], cell_of)
        report = build_b_diagnostic_report(
            results, table, sr.observation_meta(inputs["rows"]))
        print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
