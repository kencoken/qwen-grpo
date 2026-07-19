"""Baseline arms, diagnostic pseudo-workers, frozen shallow predictor —
spec §1.11.

Direct arms (B1/B3/B4) use `SYSTEM_DIRECT` and the answer-line protocol;
request text is built with the same frozen blocks as worker requests.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
from sklearn.tree import DecisionTreeClassifier

from . import contract, render
from .resources import InstanceRegistry
from .tools import Binding
from .types import INTEGER_TOKEN_RE, InfrastructureError, WorkerResult

B5_TASK = "Complete the task and return the final result."


def build_b1_request(instance: dict[str, Any]) -> str:
    """B1 public-only direct: `Problem` only."""
    return render.build_worker_request(instance["public_prompt"], None,
                                       direct=True)


def build_b2_request(instance: dict[str, Any], subtask: str
                     ) -> tuple[str, Binding]:
    """B2 endpoint-without-resource: worker request minus the `Resource`
    block and with the authorized binding set empty (both channels)."""
    request = render.build_worker_request(instance["public_prompt"], subtask)
    return request, Binding()


def build_b3_request(instance: dict[str, Any],
                     registry: InstanceRegistry) -> str:
    """B3 visible direct: `Problem` + plural `Resources:` (self-solving
    diagnosis; no `SELF` action, so not delegation)."""
    return render.build_worker_request(
        instance["public_prompt"], None,
        resources_texts=registry.union_payload_texts(), direct=True)


def build_b4_request(instance: dict[str, Any], subtask: str,
                     resource_text: str | None,
                     gold_previous: dict[int, int] | None) -> str:
    """B4 local-node: same blocks as an endpoint worker with gold
    predecessor values; only the final line differs."""
    return render.build_worker_request(
        instance["public_prompt"], subtask, resource_text=resource_text,
        previous_results=gold_previous, direct=True)


def build_b5_request(instance: dict[str, Any],
                     registry: InstanceRegistry) -> tuple[str, Binding]:
    """B5 one-call whole-task: plural union payload (harness-only exception
    to the one-resource-per-step rule; never available to the policy)."""
    request = render.build_worker_request(
        instance["public_prompt"], B5_TASK,
        resources_texts=registry.union_payload_texts())
    binding = Binding(resources={h: registry.resolve(h)
                                 for h in registry.manifest})
    return request, binding


def generic_subtasks(num_steps: int) -> list[str]:
    """B6: every subtask replaced by the frozen GENERIC_SUBTASK (D13)."""
    return [render.GENERIC_SUBTASK] * num_steps


# --- §1.11 diagnostic pseudo-workers (synthetic=true, §1.7) -----------------

_TASK_BLOCK_RE = re.compile(r"^Task:\n(.*?)(?:\n\n|\Z)", re.M | re.S)


def echo_worker(request: str) -> WorkerResult:
    """Value = last canonical-integer token in the `Task` block (frozen
    §1.13 token boundaries), else typed_failure(E_PARSE)."""
    m = _TASK_BLOCK_RE.search(request)
    if m:
        last = None
        for tok in INTEGER_TOKEN_RE.finditer(m.group(1)):
            last = tok.group(0)
        if last is not None:
            return contract.pseudo_result(int(last))
    return contract.pseudo_result(None, "E_PARSE")


def noop_worker(request: str) -> WorkerResult:
    """Value 0 always (D17). Not a guaranteed floor: `math_code` permits a
    true index 0 — `noop_correct` workflows are reported, not excluded."""
    return contract.pseudo_result(0)


# --- §1.11 frozen shallow predictor -----------------------------------------

# Observable subtype: derivable from the public prompt alone (frozen level
# lists). Generator-only fields (target_stratum, renderer id, split id) are
# explicitly excluded from B1 controls.
OBSERVABLE_SUBTYPES: dict[str, tuple[str, ...]] = {
    "lookup_atomic": ("constant",),
    "math_atomic": ("T1", "T2", "T3"),
    "code_atomic": ("count", "select"),
    "lookup_math": ("minus", "plus"),
    "math_code": ("constant",),
    "fork_join": ("lookup_first", "code_first"),
}

_NUMERIC_COLUMNS = ("p", "q", "t", "k", "i")  # frozen order


def observable_subtype(cell_id: str, params: dict[str, Any]) -> str:
    if cell_id == "math_atomic":
        return params["template"]
    if cell_id == "code_atomic":
        return params["shape"]
    if cell_id == "lookup_math":
        return "minus" if params["sign"] == "-" else "plus"
    if cell_id == "fork_join":
        return params["branch_order"]
    return "constant"


def feature_row(cell_id: str, params: dict[str, Any],
                public_numeric_values: dict[str, int]) -> list[int]:
    """Frozen feature contract: subtype one-hot in the frozen level order,
    then numeric columns exactly [p, q, t, k, i]; missing numeric → −1.
    Keys, fields, handles, entity names, generator-only fields excluded."""
    levels = OBSERVABLE_SUBTYPES[cell_id]
    subtype = observable_subtype(cell_id, params)
    row = [1 if subtype == level else 0 for level in levels]
    row += [public_numeric_values.get(name, -1)
            for name in _NUMERIC_COLUMNS]
    return row


def fit_shallow_predictor(cell_id: str,
                          latents: list[dict[str, Any]]
                          ) -> DecisionTreeClassifier:
    """One classifier per cell; frozen hyperparameters; one training row per
    latent cluster (canonical resource_first rendering). Fitted on
    construction data only, then frozen. Prediction ties → lowest class
    label (sklearn argmax picks the first/lowest label on ties)."""
    if any(latent["cell_id"] != cell_id for latent in latents):
        raise InfrastructureError("mixed-cell training rows")
    X = [feature_row(cell_id, latent["params"],
                     latent["public_numeric_values"]) for latent in latents]
    y = [latent["gold_answer"] for latent in latents]
    model = DecisionTreeClassifier(max_depth=3, criterion="gini",
                                   min_samples_leaf=5, random_state=0)
    model.fit(np.asarray(X), np.asarray(y))
    return model


def shallow_predict(model: DecisionTreeClassifier, cell_id: str,
                    params: dict[str, Any],
                    public_numeric_values: dict[str, int]) -> int:
    row = feature_row(cell_id, params, public_numeric_values)
    return int(model.predict(np.asarray([row]))[0])
