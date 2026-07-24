"""§8.4B direct-gradient feasibility replay — executable frozen contract
(unit 3, per 142_s finding 2).

Everything the GPU call depends on is frozen HERE, before sampling:

- literal model/tokenizer revisions (the Stage-0C launch profile's
  conductor model — worker 3's frozen base checkpoint) and the adapter
  decision: NF4-quantized base plus a FRESHLY INITIALIZED LoRA adapter
  with the frozen Stage-0 configuration (LoRA B-matrices zero-initialized
  so outputs equal the quantized base; the adapter is loaded anyway so
  the sampling path is byte-identical to the Stage-2 path);
- every sampling parameter (temperature 1.0, nucleus/top-k explicitly
  disabled, 128-token cap, EOS stopping);
- SINGLETON generation with one seeded torch generator per
  (observation_id, prompt_sha256, completion_index) — no batching, per
  the D16 batch-sensitivity evidence and 142_s's recommendation;
- the exact candidate-specific chat messages and their rendered-request
  hashes (built and hashed before sampling);
- the eligible w2/w3 pair table, derived from the pinned payoff surface
  BEFORE sampling;
- the complete 2,304-key output accounting: malformed, wrong-length and
  truncated completions REMAIN in the 64-sample denominator;
- the source-bound replay manifest.

The replay may not use formal Stage-1 populations, select a prompt,
change either prompt, or become another prompt-development round
(132_s §8.4B).
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping

import numpy as np

from . import stage1
from .profiles import canonical_json
from .stage1_validation import (clopper_pearson_upper, scenario_seed)
from .types import InfrastructureError

# --- frozen replay contract -----------------------------------------------------

REPLAY_CONTRACT: dict[str, Any] = {
    "contract": "stage1-replay-v1",
    # literal checkpoint identity (= STAGE0C_LAUNCH_PROFILE conductor
    # model; asserted against it by test, never retyped elsewhere)
    "model_id": "Qwen/Qwen2.5-3B-Instruct",
    "revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
    "adapter": "fresh-lora-r16-a32-d0.05-zero-B",  # base-equivalent
    "quantization": {"load_in_4bit": "true", "quant_type": "nf4",
                     "double_quant": "true",
                     "compute_dtype": "bfloat16"},
    "attn_implementation": "sdpa",
    "sampling": {"do_sample": "true", "temperature": "1.0",
                 "top_p": "disabled", "top_k": "disabled",
                 "max_new_tokens": 128, "stop": "eos"},
    "generation_batch": 1,          # singleton, one generator per draw
    "completions_per_observation_per_prompt": 64,
    "observations": 18,
    "prompts": 2,
    "total_completions": 2_304,
    "support_declaration_sha256":
        "6df4c42b69f8480c9da01d60e664f618eec971d0f0cdd2aa90828cc7d39c4fff",
    "surface_manifest_sha256":
        "221a04d53403f14c537a3d43336eb6630ca6fe5682f5e3f8aa66f78ace679c23",
    "prompt_fewshot_sha256": stage1.PROMPT_FEWSHOT_SHA256,
    "prompt_schema_only_sha256": stage1.PROMPT_SCHEMA_ONLY_SHA256,
    "conservative_bound_tail": "0.05/(2*O) familywise one-sided CP",
    "direction_floor": "0.10",      # not-demonstrated below this (both
                                    # prompts) prevents confirmation
}


def completion_seed(observation_id: str, prompt_sha256: str,
                    completion_index: int) -> int:
    """One seed per singleton draw — the frozen RNG semantics."""
    if not 0 <= completion_index < \
            REPLAY_CONTRACT["completions_per_observation_per_prompt"]:
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


def g_direct_gradient(p2: float, p3: float,
                      group_size: int = 8) -> float:
    """P(at least one of each variant in `group_size` draws) — the
    §8.4B inclusion-exclusion sensitivity surface; monotone in both
    arguments."""
    if p2 < 0 or p3 < 0 or p2 + p3 > 1.0 + 1e-12:
        raise ValueError(f"(p2={p2}, p3={p3}) outside the simplex")
    return (1.0 - (1.0 - p2) ** group_size - (1.0 - p3) ** group_size
            + (1.0 - p2 - p3) ** group_size)


# --- accounting and artifact -----------------------------------------------------------

def expected_completion_keys(observation_ids: Iterable[str]
                             ) -> frozenset[str]:
    """The complete 2,304-key accounting: every (observation, prompt,
    index) singleton draw appears exactly once."""
    obs = sorted(observation_ids)
    if len(obs) != REPLAY_CONTRACT["observations"]:
        raise InfrastructureError(
            f"replay support must be exactly "
            f"{REPLAY_CONTRACT['observations']} observations, got "
            f"{len(obs)}")
    n = REPLAY_CONTRACT["completions_per_observation_per_prompt"]
    keys = frozenset(
        f"{o}|{p}|{i:02d}"
        for o in obs
        for p in (REPLAY_CONTRACT["prompt_fewshot_sha256"],
                  REPLAY_CONTRACT["prompt_schema_only_sha256"])
        for i in range(n))
    assert len(keys) == REPLAY_CONTRACT["total_completions"]
    return keys


def rendered_request_sha256(chat_template_applied_text: str) -> str:
    return hashlib.sha256(
        chat_template_applied_text.encode("utf-8")).hexdigest()


def build_replay_manifest(execution_manifest_sha256: str,
                          observation_ids: Iterable[str],
                          rendered_request_hashes: Mapping[str, str],
                          pair_table: Mapping[str, Mapping[str, Any]]
                          ) -> dict[str, Any]:
    """The source-bound replay manifest, complete before sampling:
    contract, execution identity, the 36 rendered-request hashes
    (18 observations x 2 candidate prompts), the eligible-pair table,
    and the per-completion seed recipe."""
    obs = sorted(observation_ids)
    expected_rr = {f"{o}|{p}" for o in obs
                   for p in (REPLAY_CONTRACT["prompt_fewshot_sha256"],
                             REPLAY_CONTRACT["prompt_schema_only_sha256"])}
    if set(rendered_request_hashes) != expected_rr:
        raise InfrastructureError(
            "rendered-request hash set does not cover exactly "
            "observation x candidate-prompt")
    body: dict[str, Any] = {
        "manifest": "stage1-replay-manifest-v1",
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


def summarize_replay(counts: Mapping[str, Mapping[str, int]],
                     pair_table: Mapping[str, Mapping[str, Any]]
                     ) -> dict[str, Any]:
    """From integer counts {obs|prompt_sha: {k2, k3, n}} (malformed,
    wrong-length and truncated completions stay in n), compute per
    direction u in {2, 3} the point aggregate of g and the conservative
    upper sensitivity: Bonferroni one-sided familywise CP upper bounds
    on every observation's p2 and p3 at tail 0.05/(2*O), substituted
    into monotone g; upper value 1 when the bounded pair leaves the
    simplex. Direction status: `demonstrated` iff the conservative
    upper value >= 0.10 for at least one prompt; `not_demonstrated` iff
    below 0.10 for both; `unknown` iff unrepresented in the retained
    support."""
    comparisons = [key for key, row in counts.items()
                   if pair_table[key.split("|")[0]]["distinct_payoff"]]
    n_comp = len(comparisons)
    prompts = (REPLAY_CONTRACT["prompt_fewshot_sha256"],
               REPLAY_CONTRACT["prompt_schema_only_sha256"])
    directions: dict[str, dict[str, Any]] = {}
    for u in (2, 3):
        rep = [o for o, row in pair_table.items()
               if row["direction"] == u]
        if not rep:
            directions[str(u)] = {"status": "unknown"}
            continue
        per_prompt: dict[str, dict[str, float]] = {}
        for prompt_sha in prompts:
            points, uppers = [], []
            for obs in rep:
                row = counts[f"{obs}|{prompt_sha}"]
                k2, k3, n = row["k2"], row["k3"], row["n"]
                if not (type(k2) is int and type(k3) is int
                        and type(n) is int and 0 <= k2 + k3 <= n):
                    raise InfrastructureError(
                        f"malformed counts at {obs}: {row!r}")
                tail = 0.05 / (2 * n_comp)
                u2 = clopper_pearson_upper(k2, n, tail)
                u3 = clopper_pearson_upper(k3, n, tail)
                points.append(g_direct_gradient(k2 / n, k3 / n))
                uppers.append(
                    1.0 if u2 + u3 > 1.0
                    else g_direct_gradient(u2, u3))
            # equal weight over represented observations (renderer/
            # latent/cell aggregation collapses to this on the 18-obs
            # diagnostic support: one latent per cell, one obs per
            # renderer)
            per_prompt[prompt_sha] = {
                "g_point": float(np.mean(points)) if points else 0.0,
                "g_conservative_upper":
                    float(np.mean(uppers)) if uppers else 0.0,
            }
        floor = float(REPLAY_CONTRACT["direction_floor"])
        demonstrated = any(v["g_conservative_upper"] >= floor
                           for v in per_prompt.values())
        directions[str(u)] = {
            "status": "demonstrated" if demonstrated
                      else "not_demonstrated",
            "represented_observations": len(rep),
            "per_prompt": per_prompt,
        }
    return {"directions": directions, "comparisons": n_comp}
