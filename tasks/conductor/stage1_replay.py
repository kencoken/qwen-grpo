"""§8.4B direct-gradient feasibility replay — executable frozen contract
(unit 3; rev per 145_s: 256 completions, `not_ruled_out` naming,
end-to-end driver, validated summarize/loader).

Everything the GPU call depends on is frozen HERE, before sampling:

- literal model/tokenizer revisions (the Stage-0C launch profile's
  conductor model) and the adapter decision: NF4-quantized base plus a
  FRESHLY INITIALIZED LoRA adapter with the frozen Stage-0 configuration
  (zero-initialized B matrices — outputs equal the quantized base; the
  adapter is loaded through the same frozen construction the Stage-2
  trainer uses, with TRL's k-bit preparation applied explicitly; B is a
  SEPARATELY FROZEN SINGLETON REPLAY REGIME, not byte-identical trainer
  batching);
- every sampling parameter; SINGLETON generation with one seeded torch
  generator per (observation_id, prompt_sha256, completion_index);
- **256 completions per observation per prompt** (145_s-directed
  amendment of 132_s §8.4B's 64: at 64 the `not_demonstrated` branch is
  mathematically unreachable; at 256 it is meaningfully reachable —
  U_CP(0;256) ~ 0.025 -> g ~ 0.031 < 0.10). Total 9,216 completions.
- the eligible w2/w3 pair table derived from the pinned surface BEFORE
  sampling; the complete 9,216-key accounting; malformed, wrong-length
  and truncated completions REMAIN in the 256-sample denominator.

Status vocabulary (145_s): `not_ruled_out` (a conservative upper bound
above the floor does NOT demonstrate feasibility), `not_demonstrated`
(upper bound below the floor for BOTH prompts — blocks confirmation),
`unknown` (direction unrepresented in the retained support). B is a
minimally informative early-warning screen: it can rule out feasibility
in sufficiently low-frequency cases, may not catch one-sided collapse
(one assignment absent, the other common), and the 576-draw cold-start
gate remains the definitive signal-density check.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from . import stage1
from .profiles import canonical_json
from .stage1_validation import clopper_pearson_upper, scenario_seed
from .types import InfrastructureError, parse_render_instance_id

# --- frozen replay contract -----------------------------------------------------

REPLAY_COMPLETIONS = 256          # 145_s-directed amendment (was 64)
REPLAY_GROUP_SIZE = 8             # the g() group size (Stage-2 frozen)

REPLAY_CONTRACT: dict[str, Any] = {
    "contract": "stage1-replay-v2",
    "model_id": "Qwen/Qwen2.5-3B-Instruct",
    "revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
    "adapter": "fresh-lora-r16-a32-d0.05-zero-B-kbit-prepared",
    "regime": "singleton-replay-v1",  # separately frozen; NOT trainer batching
    "quantization": {"load_in_4bit": "true", "quant_type": "nf4",
                     "double_quant": "true",
                     "compute_dtype": "bfloat16"},
    "attn_implementation": "sdpa",
    "sampling": {"do_sample": "true", "temperature": "1.0",
                 "top_p": "disabled", "top_k": "disabled",
                 "max_new_tokens": 128, "stop": "eos"},
    "generation_batch": 1,          # singleton, one generator per draw
    "completions_per_observation_per_prompt": REPLAY_COMPLETIONS,
    "observations": 18,
    "prompts": 2,
    "total_completions": 9_216,
    "support_declaration_sha256":
        "6df4c42b69f8480c9da01d60e664f618eec971d0f0cdd2aa90828cc7d39c4fff",
    "surface_manifest_sha256":
        "221a04d53403f14c537a3d43336eb6630ca6fe5682f5e3f8aa66f78ace679c23",
    "prompt_fewshot_sha256": stage1.PROMPT_FEWSHOT_SHA256,
    "prompt_schema_only_sha256": stage1.PROMPT_SCHEMA_ONLY_SHA256,
    # O is frozen structurally: the number of (distinct-payoff
    # observation) x (prompt candidate) comparisons derived from the
    # pre-sampling pair table — never from caller-supplied counts.
    "conservative_bound_tail": "0.05/(2*O) familywise one-sided CP",
    "direction_floor": "0.10",
}
_PROMPT_SHAS = (REPLAY_CONTRACT["prompt_fewshot_sha256"],
                REPLAY_CONTRACT["prompt_schema_only_sha256"])


def completion_seed(observation_id: str, prompt_sha256: str,
                    completion_index: int) -> int:
    """One seed per singleton draw — the frozen RNG semantics."""
    if not 0 <= completion_index < REPLAY_COMPLETIONS:
        raise ValueError(f"completion index {completion_index} out of "
                         "range")
    return scenario_seed(
        f"B|{observation_id}|{prompt_sha256}|{completion_index}")


# --- eligible-pair table (derived BEFORE sampling) --------------------------------

def family_correct_variants(cell_id: str) -> tuple[list[int], list[int]] \
        | None:
    """The two otherwise-identical family-correct assignments for a cell
    with a Code node — unique because Lookup/Math nodes each have
    exactly one family-correct worker. None for Code-free cells."""
    nodes = stage1.NODE_FAMILIES[cell_id]
    base: dict[str, int] = {}
    code_node = None
    for node in sorted(nodes):
        family = nodes[node]
        if family == "code":
            if code_node is not None:
                raise InfrastructureError(
                    f"{cell_id}: multiple Code nodes — variant pair is "
                    "not unique; contract must be revisited")
            code_node = node
        else:
            (base[node],) = [w for w, f in stage1.WORKER_FAMILIES.items()
                             if f == family]
    if code_node is None:
        return None
    w2 = [base.get(n, 2) if n != code_node else 2 for n in sorted(nodes)]
    w3 = [base.get(n, 3) if n != code_node else 3 for n in sorted(nodes)]
    return w2, w3


def eligible_pair_table(surface_rows: Iterable[Mapping[str, Any]],
                        cell_of: Mapping[str, str]
                        ) -> dict[str, dict[str, Any]]:
    """Per observation: the w2/w3 family-correct variant assignments,
    their cached payoffs, distinctness, and the winning direction.
    Derived from the pinned surface before any sampling; a missing
    variant row is an error, never a silent skip."""
    payoff: dict[tuple[str, tuple[int, ...]], float] = {}
    for row in surface_rows:
        payoff[(row["observation_id"], tuple(row["assignment"]))] = \
            row["payoff"]
    table: dict[str, dict[str, Any]] = {}
    for obs_id, cell in sorted(cell_of.items()):
        variants = family_correct_variants(cell)
        if variants is None:
            continue
        w2, w3 = variants
        key2, key3 = (obs_id, tuple(w2)), (obs_id, tuple(w3))
        if key2 not in payoff or key3 not in payoff:
            raise InfrastructureError(
                f"{obs_id}: family-correct variant row missing from the "
                "pinned surface")
        p2, p3 = payoff[key2], payoff[key3]
        direction = None
        if p2 != p3:
            direction = 2 if p2 > p3 else 3
        table[obs_id] = {
            "cell_id": cell, "assignment_w2": w2, "assignment_w3": w3,
            "payoff_w2": p2, "payoff_w3": p3,
            "distinct_payoff": p2 != p3, "direction": direction,
        }
    return table


def pair_table_from_surface(surface: Mapping[tuple[str, tuple[int, ...]],
                                             float],
                            cell_of: Mapping[str, str]
                            ) -> dict[str, dict[str, Any]]:
    """Adapter for the pinned surface mapping form returned by
    grpo_smoke.verify_surface_pin/load_support_surface."""
    rows = [{"observation_id": obs_id, "assignment": list(assignment),
             "payoff": value}
            for (obs_id, assignment), value in surface.items()]
    return eligible_pair_table(rows, cell_of)


def g_direct_gradient(p2: float, p3: float,
                      group_size: int = REPLAY_GROUP_SIZE) -> float:
    """P(at least one of each variant in `group_size` draws) — the
    §8.4B inclusion-exclusion sensitivity surface; monotone in both
    arguments."""
    if p2 < 0 or p3 < 0 or p2 + p3 > 1.0 + 1e-12:
        raise ValueError(f"(p2={p2}, p3={p3}) outside the simplex")
    return (1.0 - (1.0 - p2) ** group_size - (1.0 - p3) ** group_size
            + (1.0 - p2 - p3) ** group_size)


# --- accounting, manifest, artifact ------------------------------------------------

def expected_completion_keys(observation_ids: Iterable[str]
                             ) -> frozenset[str]:
    """The complete 9,216-key accounting: every (observation, prompt,
    index) singleton draw appears exactly once."""
    obs = sorted(observation_ids)
    if len(obs) != REPLAY_CONTRACT["observations"]:
        raise InfrastructureError(
            f"replay support must be exactly "
            f"{REPLAY_CONTRACT['observations']} observations, got "
            f"{len(obs)}")
    keys = frozenset(
        f"{o}|{p}|{i:03d}"
        for o in obs for p in _PROMPT_SHAS
        for i in range(REPLAY_COMPLETIONS))
    assert len(keys) == REPLAY_CONTRACT["total_completions"]
    return keys


def expected_count_keys(pair_table: Mapping[str, Mapping[str, Any]]
                        ) -> frozenset[str]:
    """The exact per-(observation, prompt) count-row key set the B
    artifact must cover: every pair-table observation, both prompts."""
    if not pair_table:
        raise InfrastructureError("empty pair table — B is not "
                                  "evaluable")
    return frozenset(f"{o}|{p}" for o in sorted(pair_table)
                     for p in _PROMPT_SHAS)


def observation_meta(observation_ids: Iterable[str]
                     ) -> dict[str, dict[str, str]]:
    """(cell, latent, renderer) identity per observation, parsed from
    the render-instance id grammar — the aggregation skeleton."""
    meta = {}
    for obs_id in observation_ids:
        rid = parse_render_instance_id(obs_id)
        meta[obs_id] = {"cell_id": rid.latent.cell_id,
                        "latent": rid.latent_program_id,
                        "renderer": rid.renderer_id}
    return meta


def rendered_request_sha256(chat_template_applied_text: str) -> str:
    return hashlib.sha256(
        chat_template_applied_text.encode("utf-8")).hexdigest()


def build_replay_manifest(execution_manifest_sha256: str,
                          observation_ids: Iterable[str],
                          rendered_request_hashes: Mapping[str, str],
                          pair_table: Mapping[str, Mapping[str, Any]]
                          ) -> dict[str, Any]:
    """The source-bound replay manifest, complete before sampling."""
    obs = sorted(observation_ids)
    expected_rr = {f"{o}|{p}" for o in obs for p in _PROMPT_SHAS}
    if set(rendered_request_hashes) != expected_rr:
        raise InfrastructureError(
            "rendered-request hash set does not cover exactly "
            "observation x candidate-prompt")
    body: dict[str, Any] = {
        "manifest": "stage1-replay-manifest-v2",
        "contract": dict(REPLAY_CONTRACT),
        "execution_manifest_sha256": execution_manifest_sha256,
        "observation_ids": obs,
        "rendered_request_sha256": dict(
            sorted(rendered_request_hashes.items())),
        "eligible_pairs": {
            o: {"cell_id": row["cell_id"],
                "assignment_w2": list(row["assignment_w2"]),
                "assignment_w3": list(row["assignment_w3"]),
                "distinct_payoff": int(row["distinct_payoff"]),
                "direction": int(row["direction"] or 0)}
            for o, row in sorted(pair_table.items())},
        "seed_recipe": "scenario_seed('B|{obs}|{prompt_sha}|{index}')",
    }
    digest = hashlib.sha256(
        canonical_json(body).encode("utf-8")).hexdigest()
    out = dict(body)
    out["replay_manifest_sha256"] = digest
    return out


def load_b_artifact(artifact: Mapping[str, Any],
                    execution_manifest_sha256: str) -> dict[str, Any]:
    """Structural B loader: content hash, execution identity, embedded
    pair table/meta, exact count-row key set, n == 256, count
    identities. STRUCTURAL ONLY — formal consumption goes through
    `verify_replay_evidence`, which re-derives the pair table from the
    pinned surface and reparses the raw completions (148_s finding 3);
    this loader alone cannot authenticate the counts."""
    from .stage1_tranche import load_artifact
    for field in ("pair_table", "obs_meta", "replay_manifest_sha256",
                  "raw_completions_sha256"):
        if field not in artifact:
            raise InfrastructureError(f"B artifact missing {field!r}")
    pair_table = artifact["pair_table"]
    expected = expected_count_keys(pair_table)
    return load_artifact(artifact, "B", expected,
                         execution_manifest_sha256,
                         b_n=REPLAY_COMPLETIONS)


def _sanitized_pair_table(pair_table: Mapping[str, Mapping[str, Any]]
                          ) -> dict[str, dict[str, Any]]:
    """The ints/strings-only form embedded in manifests/artifacts."""
    return {o: {"cell_id": row["cell_id"],
                "assignment_w2": list(row["assignment_w2"]),
                "assignment_w3": list(row["assignment_w3"]),
                "distinct_payoff": int(row["distinct_payoff"]),
                "direction": int(row["direction"] or 0)}
            for o, row in sorted(pair_table.items())}


def recount_from_raw(raw: Mapping[str, str],
                     pair_table: Mapping[str, Mapping[str, Any]],
                     steps_of: Mapping[str, Mapping[str, Any]]
                     ) -> dict[str, dict[str, int]]:
    """Independent recount: reparse every persisted completion for the
    pair-bearing observations and rebuild the k2/k3/n table. Pure CPU;
    used by `verify_replay_evidence` to authenticate artifact counts."""
    from .parser import ActionSchemaError, parse_routing_action
    from .grpo_task import positional_to_semantic
    counts: dict[str, dict[str, int]] = {}
    for obs_id, pair in sorted(pair_table.items()):
        meta = steps_of[obs_id]
        # build_smoke_rows stores positions as JSON text to survive
        # Dataset column typing (151_s finding 1) — parse either form
        positions = meta["positions"]
        if isinstance(positions, str):
            positions = json.loads(positions)
        for sha in _PROMPT_SHAS:
            k2 = k3 = 0
            for i in range(REPLAY_COMPLETIONS):
                text = raw[f"{obs_id}|{sha}|{i:03d}"]
                try:
                    action = parse_routing_action(text,
                                                  meta["num_steps"])
                except ActionSchemaError:
                    continue
                semantic = list(positional_to_semantic(action,
                                                       positions))
                if semantic == list(pair["assignment_w2"]):
                    k2 += 1
                elif semantic == list(pair["assignment_w3"]):
                    k3 += 1
            counts[f"{obs_id}|{sha}"] = {"k2": k2, "k3": k3,
                                         "n": REPLAY_COMPLETIONS}
    return counts


def load_pinned_replay_inputs() -> tuple[
        Mapping[tuple[str, tuple[int, ...]], float],
        dict[str, dict[str, Any]], dict[str, str]]:
    """THE authoritative loader for the consuming boundary (151_s
    finding 2): the pinned surface (hash-verified), the 18 support
    rows, and the REGENERATED rendered-request hashes for both
    candidate prompts — nothing caller-supplied."""
    from transformers import AutoTokenizer
    from .grpo_smoke import verify_surface_pin
    from .grpo_task import build_smoke_rows
    surface = verify_surface_pin()
    rows = {row["observation_id"]: row for row in build_smoke_rows()}
    tokenizer = AutoTokenizer.from_pretrained(
        REPLAY_CONTRACT["model_id"],
        revision=REPLAY_CONTRACT["revision"])
    prompts = {REPLAY_CONTRACT["prompt_fewshot_sha256"]:
                   stage1.prompt_fewshot(),
               REPLAY_CONTRACT["prompt_schema_only_sha256"]:
                   stage1.prompt_schema_only()}
    rr: dict[str, str] = {}
    for oid, row in rows.items():
        user = row["prompt"][1]
        for sha, text in prompts.items():
            msg = [{"role": "system", "content": text}, dict(user)]
            rr[f"{oid}|{sha}"] = rendered_request_sha256(
                tokenizer.apply_chat_template(
                    msg, tokenize=False, add_generation_prompt=True))
    return surface, rows, rr


def verify_replay_evidence(artifact: Mapping[str, Any], *,
                           env_manifest: Mapping[str, Any],
                           replay_manifest: Mapping[str, Any],
                           raw_completions_text: str,
                           pinned_loader=None) -> dict[str, Any]:
    """THE consuming boundary for B evidence (148_s finding 3; hardened
    per 151_s finding 2): the pinned surface, support rows and
    rendered-request hashes are loaded/REGENERATED internally — never
    caller-supplied — and the COMPLETE expected replay manifest is
    rebuilt and required to equal the supplied one exactly (observation
    ids, eligible pairs, request hashes, contract, hash — a rehashed
    manifest with any altered field is refused). Then the raw
    completions are hash-matched, accounted, and REPARSED to exact
    count reproduction. `pinned_loader` exists for tests only and
    defaults to the authoritative loader."""
    from .stage1_manifest import validate_env_manifest
    exec_sha = validate_env_manifest(env_manifest)
    b = load_b_artifact(artifact, exec_sha)

    loader = pinned_loader or load_pinned_replay_inputs
    surface, support_rows, regenerated_rr = loader()
    cell_of = {oid: row["cell_id"] for oid, row in support_rows.items()}
    derived_table = pair_table_from_surface(surface, cell_of)
    expected_manifest = build_replay_manifest(
        exec_sha, support_rows, regenerated_rr, derived_table)
    if dict(replay_manifest) != expected_manifest:
        raise InfrastructureError(
            "replay manifest does not equal the authoritative "
            "regenerated manifest (observation ids, eligible pairs, "
            "request hashes, contract and hash must all match)")
    if b["replay_manifest_sha256"] != \
            expected_manifest["replay_manifest_sha256"]:
        raise InfrastructureError(
            "artifact names a different replay manifest")

    raw_sha = hashlib.sha256(
        raw_completions_text.encode("utf-8")).hexdigest()
    if raw_sha != b["raw_completions_sha256"]:
        raise InfrastructureError("raw completions do not hash to the "
                                  "artifact's raw_completions_sha256")
    raw = json.loads(raw_completions_text)
    if set(raw) != expected_completion_keys(support_rows):
        raise InfrastructureError("raw completions do not cover exactly "
                                  "the 9,216 accounting keys")

    if _sanitized_pair_table(derived_table) != \
            _sanitized_pair_table(b["pair_table"]):
        raise InfrastructureError(
            "embedded pair table does not rederive from the pinned "
            "surface")
    if observation_meta(support_rows) != b["obs_meta"]:
        raise InfrastructureError(
            "embedded observation meta does not rederive from the "
            "support ids")

    recounted = recount_from_raw(raw, derived_table, support_rows)
    if recounted != {k: dict(v) for k, v in b["results"].items()}:
        raise InfrastructureError(
            "artifact counts do not reproduce from the raw completions")
    return summarize_replay(recounted, derived_table,
                            observation_meta(support_rows))


def summarize_replay(counts: Mapping[str, Mapping[str, int]],
                     pair_table: Mapping[str, Mapping[str, Any]],
                     obs_meta: Mapping[str, Mapping[str, str]]
                     ) -> dict[str, Any]:
    """From integer counts {`obs|prompt_sha`: {k2, k3, n}} (malformed,
    wrong-length and truncated completions stay in n = 256), compute per
    direction u in {2, 3} the aggregate of g under the frozen weighting
    — renderer-within-latent, latent-within-cell, cells equally, over
    the observations whose pair favours u — and the conservative upper
    sensitivity (Bonferroni familywise CP uppers at tail 0.05/(2*O),
    O = 2 x distinct-payoff observations, DERIVED from the pair table).

    Fail-closed: the count keys must be exactly pair-table x prompts;
    n must equal the frozen 256; counts must be possible; every
    pair-table observation needs meta. Statuses: `not_ruled_out`,
    `not_demonstrated` (blocks), `unknown` (unrepresented)."""
    expected = expected_count_keys(pair_table)
    if set(counts) != expected:
        raise InfrastructureError(
            f"count keys != pair-table x prompts (missing "
            f"{len(expected - set(counts))}, extra "
            f"{len(set(counts) - expected)})")
    if set(pair_table) - set(obs_meta):
        raise InfrastructureError("observation meta incomplete")
    for key, row in counts.items():
        if set(row) != {"k2", "k3", "n"}:
            raise InfrastructureError(f"malformed count row {key!r}")
        k2, k3, n = row["k2"], row["k3"], row["n"]
        if not all(type(v) is int for v in (k2, k3, n)) or \
                n != REPLAY_COMPLETIONS or k2 < 0 or k3 < 0 or \
                k2 + k3 > n:
            raise InfrastructureError(
                f"malformed counts at {key!r}: {dict(row)!r}")
    n_distinct = sum(1 for row in pair_table.values()
                     if row["distinct_payoff"])
    o_comparisons = 2 * n_distinct     # frozen structural definition
    floor = float(REPLAY_CONTRACT["direction_floor"])
    directions: dict[str, dict[str, Any]] = {}
    for u in (2, 3):
        rep = [o for o, row in pair_table.items()
               if row["direction"] == u]
        if not rep:
            directions[str(u)] = {"status": "unknown"}
            continue
        per_prompt: dict[str, dict[str, float]] = {}
        for prompt_sha in _PROMPT_SHAS:
            points_by_obs, uppers_by_obs = {}, {}
            for obs in rep:
                row = counts[f"{obs}|{prompt_sha}"]
                k2, k3, n = row["k2"], row["k3"], row["n"]
                tail = 0.05 / (2 * o_comparisons)
                u2 = clopper_pearson_upper(k2, n, tail)
                u3 = clopper_pearson_upper(k3, n, tail)
                points_by_obs[obs] = g_direct_gradient(k2 / n, k3 / n)
                uppers_by_obs[obs] = (
                    1.0 if u2 + u3 > 1.0 else g_direct_gradient(u2, u3))
            per_prompt[prompt_sha] = {
                "g_point": _aggregate(points_by_obs, obs_meta),
                "g_conservative_upper":
                    _aggregate(uppers_by_obs, obs_meta),
            }
        ruled_in = any(v["g_conservative_upper"] >= floor
                       for v in per_prompt.values())
        directions[str(u)] = {
            "status": "not_ruled_out" if ruled_in
                      else "not_demonstrated",
            "represented_observations": len(rep),
            "per_prompt": per_prompt,
        }
    return {"directions": directions, "comparisons": o_comparisons}


def _aggregate(values_by_obs: Mapping[str, float],
               obs_meta: Mapping[str, Mapping[str, str]]) -> float:
    """The frozen §8.4B weighting: mean over renderers within latent,
    mean over latents within cell, equal mean over cells — never a raw
    observation average (145_s finding 1)."""
    cells: dict[str, dict[str, dict[str, float]]] = {}
    for obs, value in values_by_obs.items():
        meta = obs_meta[obs]
        cells.setdefault(meta["cell_id"], {}).setdefault(
            meta["latent"], {})[meta["renderer"]] = value
    cell_means = []
    for latents in cells.values():
        latent_means = [float(np.mean(list(renderers.values())))
                        for renderers in latents.values()]
        cell_means.append(float(np.mean(latent_means)))
    return float(np.mean(cell_means))


# --- the GPU driver -------------------------------------------------------------------

REPLAY_RUN_DIR = "runs/stage1-replay"


def run_replay(*, allow_dirty: bool = False) -> dict[str, Any]:
    """Execute the frozen replay end-to-end on the GPU box: environment
    manifest → pinned surface → pair table → candidate messages and
    rendered-request hashes → replay manifest (all BEFORE sampling) →
    seeded singleton generation → parse/classify → raw-completion
    artifact + validated B artifact, persisted and reloaded."""
    import torch
    from peft import (LoraConfig, get_peft_model,
                      prepare_model_for_kbit_training)
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig)

    from .grpo_smoke import verify_surface_pin
    from .grpo_task import build_smoke_rows
    from .parser import ActionSchemaError, parse_routing_action
    from .grpo_task import positional_to_semantic
    from .stage1_manifest import build_stage1_env_manifest
    from .stage1_tranche import finalize_artifact, load_artifact

    env = build_stage1_env_manifest(allow_dirty=allow_dirty)
    exec_sha = env["execution_manifest_sha256"]
    surface = verify_surface_pin()

    rows = {row["observation_id"]: row for row in build_smoke_rows()}
    if len(rows) != REPLAY_CONTRACT["observations"]:
        raise InfrastructureError(
            f"support has {len(rows)} observations, contract says "
            f"{REPLAY_CONTRACT['observations']}")
    cell_of = {oid: row["cell_id"] for oid, row in rows.items()}
    pair_table = pair_table_from_surface(surface, cell_of)
    obs_meta = observation_meta(rows)

    prompts = {
        REPLAY_CONTRACT["prompt_fewshot_sha256"]:
            stage1.prompt_fewshot(),
        REPLAY_CONTRACT["prompt_schema_only_sha256"]:
            stage1.prompt_schema_only(),
    }
    tokenizer = AutoTokenizer.from_pretrained(
        REPLAY_CONTRACT["model_id"],
        revision=REPLAY_CONTRACT["revision"])
    messages: dict[str, list[dict[str, str]]] = {}
    rr_hashes: dict[str, str] = {}
    for oid, row in rows.items():
        user = row["prompt"][1]
        assert user["role"] == "user"
        for sha, text in prompts.items():
            msg = [{"role": "system", "content": text}, dict(user)]
            messages[f"{oid}|{sha}"] = msg
            rr_hashes[f"{oid}|{sha}"] = rendered_request_sha256(
                tokenizer.apply_chat_template(
                    msg, tokenize=False, add_generation_prompt=True))
    manifest = build_replay_manifest(exec_sha, rows, rr_hashes,
                                     pair_table)

    # Run-directory exclusion and manifest persistence happen BEFORE
    # any model work (151_s finding 4): an aborted GPU run must leave
    # the environment, replay manifest, and an aborted record on disk.
    import time as _time
    out_dir = Path(REPLAY_RUN_DIR)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise InfrastructureError(
            f"{out_dir} already holds a formal replay run — refusing "
            "to overwrite (148_s finding 5)")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "env_manifest.json").write_text(
        json.dumps(env, indent=1), encoding="utf-8")
    (out_dir / "replay_manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")
    record: dict[str, Any] = {"status": "running",
                              "started_unix": int(_time.time())}
    (out_dir / "run_record.json").write_text(
        json.dumps(record, indent=1), encoding="utf-8")

    def _finish(status: str, error_text: str | None = None) -> None:
        record["status"] = status
        record["wall_seconds"] = int(_time.time()
                                     - record["started_unix"])
        if error_text:
            record["error"] = error_text
        (out_dir / "run_record.json").write_text(
            json.dumps(record, indent=1), encoding="utf-8")

    # The SAME frozen construction the Stage-2 trainer uses
    # (grpo_smoke model_init_kwargs + LoraConfig, with TRL's k-bit
    # preparation applied explicitly, 148_s finding 2): bfloat16 dtype,
    # sdpa attention, NF4 double-quant, CAUSAL_LM task type. B remains
    # a SEPARATELY FROZEN SINGLETON REPLAY REGIME — generation batching
    # is deliberately singleton (D16 batch sensitivity), so it is not
    # byte-identical to trainer rollouts and is never described as
    # such.
    quant = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(
        REPLAY_CONTRACT["model_id"],
        revision=REPLAY_CONTRACT["revision"],
        torch_dtype=torch.bfloat16,
        quantization_config=quant, device_map="cuda:0",
        attn_implementation=REPLAY_CONTRACT["attn_implementation"])
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM"))
    model.eval()

    counts: dict[str, dict[str, int]] = {}
    raw: dict[str, str] = {}
    try:
        _generate(model, tokenizer, rows, messages, pair_table, raw,
                  counts)
    except BaseException as error:
        _finish("aborted", f"{type(error).__name__}: {error}")
        raise

    expected = expected_completion_keys(rows)
    if set(raw) != expected:
        _finish("aborted", "completion accounting incomplete")
        raise InfrastructureError(
            f"completion accounting incomplete: {len(raw)} != "
            f"{len(expected)}")
    raw_blob = json.dumps(dict(sorted(raw.items())), ensure_ascii=False)
    raw_sha = hashlib.sha256(raw_blob.encode("utf-8")).hexdigest()
    (out_dir / "raw_completions.json").write_text(raw_blob,
                                                  encoding="utf-8")
    artifact = finalize_artifact(
        "B", exec_sha, counts,
        # the SANITIZED pair table (ints/strings only — the same form
        # the manifest freezes) so the artifact is canonical-hashable
        extra={"pair_table": manifest["eligible_pairs"],
               "obs_meta": obs_meta,
               "replay_manifest_sha256":
                   manifest["replay_manifest_sha256"],
               "raw_completions_sha256": raw_sha})
    path = out_dir / "artifact_B.json"
    path.write_text(json.dumps(artifact, indent=1), encoding="utf-8")
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    load_b_artifact(reloaded, exec_sha)
    _finish("complete")
    return {"artifact_path": str(path),
            "replay_manifest_sha256":
                manifest["replay_manifest_sha256"],
            "raw_completions_sha256": raw_sha,
            "summary": summarize_replay(counts, pair_table, obs_meta)}


def _generate(model, tokenizer, rows, messages, pair_table, raw,
              counts) -> None:
    """The generation loop, isolated so the driver's abort handling
    wraps exactly the GPU work. Note the frozen RNG semantics: the
    GLOBAL CPU and CUDA RNG state is reset per singleton draw from the
    preregistered seed — there is no per-draw generator object."""
    import torch
    from .parser import ActionSchemaError, parse_routing_action
    from .grpo_task import positional_to_semantic
    for oid, row in sorted(rows.items()):
        positions = json.loads(row["positions"])
        pair = pair_table.get(oid)
        for sha in _PROMPT_SHAS:
            key = f"{oid}|{sha}"
            enc = tokenizer.apply_chat_template(
                messages[key], tokenize=True, return_tensors="pt",
                add_generation_prompt=True).to(model.device)
            k2 = k3 = 0
            for i in range(REPLAY_COMPLETIONS):
                # full unsigned 64-bit seed, EXACTLY as preregistered —
                # no modulus (148_s finding 1); the pinned torch build
                # accepts the full range
                seed = completion_seed(oid, sha, i)
                torch.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)
                with torch.no_grad():
                    out = model.generate(
                        enc, do_sample=True, temperature=1.0,
                        top_p=None, top_k=None,
                        max_new_tokens=REPLAY_CONTRACT["sampling"][
                            "max_new_tokens"],
                        pad_token_id=tokenizer.eos_token_id)
                text = tokenizer.decode(out[0, enc.shape[1]:],
                                        skip_special_tokens=True)
                raw[f"{key}|{i:03d}"] = text
                if pair is None:
                    continue
                try:
                    action = parse_routing_action(text,
                                                  row["num_steps"])
                except ActionSchemaError:
                    continue  # stays in the denominator
                semantic = list(positional_to_semantic(action,
                                                       positions))
                if semantic == pair["assignment_w2"]:
                    k2 += 1
                elif semantic == pair["assignment_w3"]:
                    k3 += 1
            if pair is not None:
                counts[key] = {"k2": k2, "k3": k3,
                               "n": REPLAY_COMPLETIONS}

