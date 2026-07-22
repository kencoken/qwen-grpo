"""Frozen candidate registry for the 92_s scope × model × prompt
experiment.

A candidate id names one complete worker configuration: the Code
endpoint's checkpoint, the shared request contract, and the Code prompt
condition (Lookup/Math are the generic 1.5B checkpoint with rev9 texts
in every candidate). Treatment identity is content — registered
revisions, prompt hashes and contract digests enter every artifact; the
id is a join key, never evidence.

Parameter counts are registry-declared (92_s §3) and verified against
the loaded models at measurement time; a mismatch is a registry error to
fix before freeze, not a value to shrug at.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

from .profiles import ProfileError
from .prompts import resolve_prompts
from .render import CONTRACT_CURRENT, CONTRACT_TASK_LAST
from .runtime import DEFAULT_RUNTIME_PROFILE

# --- §2.1 Code model checkpoints ---------------------------------------------

CODE_MODELS: dict[str, dict[str, Any]] = {
    "coder_1p5b": {
        "model_id": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        "revision": "2e1fd397ee46e1388853d2af2c993145b0f1098a",
        "parameters": 1_543_714_304,
    },
    "generic_1p5b": {
        "model_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "revision": "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
        "parameters": 1_543_714_304,
    },
    # coder_3b is the one checkpoint never exercised locally; its
    # declared parameter count is validated at first Tranche-B load, and
    # a mismatch is a HARD STOP requiring a new preregistration — never
    # an in-place post-freeze registry correction (94_s).
    "coder_3b": {
        "model_id": "Qwen/Qwen2.5-Coder-3B-Instruct",
        "revision": "488639f1ff808d1d3d0ba301aef8c11461451ec5",
        "parameters": 3_085_938_688,
    },
    "generic_3b": {
        "model_id": "Qwen/Qwen2.5-3B-Instruct",
        "revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1",
        "parameters": 3_085_938_688,
    },
}

# Declared parameters per physical checkpoint key (model_id, revision).
CHECKPOINT_PARAMETERS = {
    (cfg["model_id"], cfg["revision"]): cfg["parameters"]
    for cfg in CODE_MODELS.values()
}

REQUEST_CONTRACT_KEYS = {"current": CONTRACT_CURRENT,
                         "task_last": CONTRACT_TASK_LAST}

# 96_s finding 8: the CUDA device is frozen across every P1 arm and
# full run; a run on any other device refuses at verification.
EXPERIMENT_DEVICE = "cuda"
CODE_PROMPTS = ("rev9", "code_local_v1")

_TRANCHE_MODELS = {"A": ("coder_1p5b", "generic_1p5b"),
                   "B": ("coder_3b", "generic_3b")}

# §7: fixed arm order alternating model / request contract / prompt.
_ARM_PATTERN = (
    (0, "current", "rev9"), (1, "task_last", "rev9"),
    (0, "task_last", "code_local_v1"), (1, "current", "code_local_v1"),
    (0, "task_last", "rev9"), (1, "current", "rev9"),
    (0, "current", "code_local_v1"), (1, "task_last", "code_local_v1"),
)


def candidate_id(model_key: str, contract_label: str,
                 prompt_revision: str) -> str:
    return f"{model_key}-{contract_label}-{prompt_revision}"


def arm_order(tranche: str) -> list[str]:
    """The frozen execution order for a tranche's eight candidates."""
    models = _TRANCHE_MODELS[tranche]
    return [candidate_id(models[m], contract, prompt)
            for m, contract, prompt in _ARM_PATTERN]


CANDIDATES: dict[str, dict[str, str]] = {}
for _tranche, _models in _TRANCHE_MODELS.items():
    for _model in _models:
        for _contract in REQUEST_CONTRACT_KEYS:
            for _prompt in CODE_PROMPTS:
                CANDIDATES[candidate_id(_model, _contract, _prompt)] = {
                    "code_model": _model,
                    "contract_label": _contract,
                    "request_contract_key": REQUEST_CONTRACT_KEYS[_contract],
                    "code_prompt": _prompt,
                    "tranche": _tranche,
                }


# 99_f follow-up candidate (post-Tranche-A terminal stop, 98_f): ONE
# bounded Math amendment on the anchor configuration, registered under
# its own preregistration outside the frozen 92_s tranches. The
# "code_prompt" field names the full bundle revision; rev10's Lookup
# and Code texts are byte-identical to rev9.
CANDIDATES["generic_1p5b-task_last-rev10"] = {
    "code_model": "generic_1p5b",
    "contract_label": "task_last",
    "request_contract_key": REQUEST_CONTRACT_KEYS["task_last"],
    "code_prompt": "rev10",
    "tranche": "F1",
}

# 101_f follow-up candidates: the rev11 Code amendment on the anchor,
# plus the conditional coder escalation arm (run only if the anchor
# misses the target; the paired prefix evidence in 100_f argues it
# will not be needed).
for _model in ("generic_1p5b", "coder_1p5b"):
    CANDIDATES[f"{_model}-task_last-rev11"] = {
        "code_model": _model,
        "contract_label": "task_last",
        "request_contract_key": REQUEST_CONTRACT_KEYS["task_last"],
        "code_prompt": "rev11",
        "tranche": "F2",
    }


def sentinel_order(contract_label: str, tranche: str) -> list[str]:
    """§7 frozen sentinel designation order for one request contract."""
    if contract_label not in REQUEST_CONTRACT_KEYS:
        raise ProfileError(f"unknown contract label {contract_label!r}")
    models = _TRANCHE_MODELS[tranche]
    generic = next(m for m in models if m.startswith("generic"))
    coder = next(m for m in models if m.startswith("coder"))
    return [candidate_id(model, contract_label, prompt)
            for prompt in ("rev9", "code_local_v1")
            for model in (generic, coder)]


def candidate_config(cid: str) -> dict[str, str]:
    if cid not in CANDIDATES:
        raise ProfileError(f"unknown candidate {cid!r}; registered: "
                           f"{arm_order('A')} + tranche B")
    return dict(CANDIDATES[cid])


def candidate_runtime_profile(cid: str) -> dict[str, Any]:
    """The exact runtime profile this candidate executes: the Code worker
    swapped to the registered checkpoint, the profile prompt label bound
    to the candidate's bundle revision (92_s §6.8)."""
    config = candidate_config(cid)
    model = CODE_MODELS[config["code_model"]]
    profile = copy.deepcopy(DEFAULT_RUNTIME_PROFILE)
    profile["workers"]["code"] = {
        "model_id": model["model_id"], "revision": model["revision"],
        "max_new_tokens": 256, "microbatch": 16,
    }
    profile["prompts"] = {"d16_revision": config["code_prompt"]}
    return profile


def candidate_bundle(cid: str):
    return resolve_prompts(candidate_config(cid)["code_prompt"])


def physical_layout(profile: Mapping[str, Any],
                    device: str = EXPERIMENT_DEVICE) -> dict[str, Any]:
    """Planned physical-worker layout (92_s §3): unique checkpoint keys,
    declared parameters and the logical-endpoint mapping. Logical
    endpoints stay distinct; only model/tokenizer objects are shared."""
    by_key: dict[tuple[str, str], list[str]] = {}
    for endpoint in sorted(profile["workers"]):
        worker = profile["workers"][endpoint]
        by_key.setdefault((worker["model_id"], worker["revision"]),
                          []).append(endpoint)
    checkpoints = []
    for (model_id, revision), endpoints in sorted(by_key.items()):
        if (model_id, revision) not in CHECKPOINT_PARAMETERS:
            raise ProfileError(
                f"checkpoint ({model_id}, {revision}) is not in the "
                "candidate registry; declared parameters are unknown")
        checkpoints.append({
            "model_id": model_id,
            "revision": revision,
            "endpoints": endpoints,
            "declared_parameters":
                CHECKPOINT_PARAMETERS[(model_id, revision)],
        })
    return {
        "unique_checkpoints": len(checkpoints),
        "declared_parameter_sum": sum(c["declared_parameters"]
                                      for c in checkpoints),
        "quantization": copy.deepcopy(profile["nf4"]),
        "device": device,
        "checkpoints": checkpoints,
    }
