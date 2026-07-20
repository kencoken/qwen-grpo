"""Baseline arms, diagnostic pseudo-workers, frozen shallow predictor —
spec §1.11.

Direct arms (B1/B3/B4) use `SYSTEM_DIRECT` and the answer-line protocol;
request text is built with the same frozen blocks as worker requests.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.tree import DecisionTreeClassifier

from . import contract, render
from .resources import InstanceRegistry
from .tools import Binding
from .types import (
    INTEGER_TOKEN_RE, PUBLIC_NUMERIC_PARAMS, InfrastructureError,
    PublicParams, WorkerResult, require_public,
)

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


def observable_subtype(cell_id: str, params: PublicParams) -> str:
    """Derivable from the public prompt alone — the projection is the only
    input, so generator-only fields cannot reach a public-only control."""
    p = require_public(params, cell_id)
    if cell_id == "math_atomic":
        return p["template"]
    if cell_id == "code_atomic":
        return p["shape"]
    if cell_id == "lookup_math":
        return "minus" if p["sign"] == "-" else "plus"
    if cell_id == "fork_join":
        return p["branch_order"]
    return "constant"


def feature_row(cell_id: str, params: PublicParams,
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


@dataclass(frozen=True)
class PublicFeatureRecord:
    """The sanitized row a public-only control may train or predict on.

    Built by `public_feature_record` from a latent; carries no registry, no
    reference program, and no private parameters — so a control that is
    meant to diagnose public-prompt shortcuts cannot accidentally consume
    private generator state.

    `public_numeric_values` is *derived from* `params` rather than accepted
    from the caller: an independently supplied mapping could inject extra
    or private-derived p/q/t/k/i values into a supposedly sanitized record.
    """

    cell_id: str
    latent_program_id: str
    namespace: str
    params: PublicParams
    gold_answer: int

    def __post_init__(self) -> None:
        require_public(self.params, self.cell_id)
        if isinstance(self.gold_answer, bool) or not isinstance(
                self.gold_answer, int):
            raise InfrastructureError("gold_answer must be an int")

    @property
    def public_numeric_values(self) -> dict[str, int]:
        return self.params.numeric_features()


def public_feature_record(latent: dict[str, Any]) -> PublicFeatureRecord:
    record = PublicFeatureRecord(
        cell_id=latent["cell_id"],
        latent_program_id=latent["latent_program_id"],
        namespace=latent["namespace"],
        params=latent["public_params"],
        gold_answer=latent["gold_answer"])
    # The derived features must agree with the generator's own §1.16
    # provenance-tagged values; a mismatch means one of the two drifted.
    if record.public_numeric_values != latent["public_numeric_values"]:
        raise InfrastructureError(
            f"derived public features {record.public_numeric_values} != "
            f"stored {latent['public_numeric_values']}")
    return record


FIT_NAMESPACE = "construction"  # §1.11: fitted on construction data only


def fit_shallow_predictor(cell_id: str, rows: list[PublicFeatureRecord]
                          ) -> DecisionTreeClassifier:
    """One classifier per cell; frozen hyperparameters; one training row per
    latent cluster (canonical resource_first rendering). Fitted on
    construction data only, then frozen. Prediction ties → lowest class
    label (sklearn argmax picks the first/lowest label on ties).

    The construction-only and one-row-per-cluster contracts are enforced
    here: this control exists to diagnose public-prompt shortcuts, so
    qualification rows leaking in would silently invalidate it.
    """
    if not rows:
        raise InfrastructureError("no training rows")
    if any(not isinstance(row, PublicFeatureRecord) for row in rows):
        raise InfrastructureError(
            "shallow predictor trains on PublicFeatureRecord rows only")
    if any(row.cell_id != cell_id for row in rows):
        raise InfrastructureError("mixed-cell training rows")
    off_namespace = sorted({row.namespace for row in rows} - {FIT_NAMESPACE})
    if off_namespace:
        raise InfrastructureError(
            f"shallow predictor is construction-only; got {off_namespace}")
    ids = [row.latent_program_id for row in rows]
    if len(set(ids)) != len(ids):
        raise InfrastructureError(
            "one training row per latent cluster; duplicate ids present")
    X = [feature_row(cell_id, row.params, row.public_numeric_values)
         for row in rows]
    y = [row.gold_answer for row in rows]
    model = DecisionTreeClassifier(max_depth=3, criterion="gini",
                                   min_samples_leaf=5, random_state=0)
    model.fit(np.asarray(X), np.asarray(y))
    return model


def shallow_predict(model: DecisionTreeClassifier, cell_id: str,
                    params: PublicParams,
                    public_numeric_values: dict[str, int]) -> int:
    row = feature_row(cell_id, params, public_numeric_values)
    return int(model.predict(np.asarray([row]))[0])


# --- §1.11 B1 reference controls (frozen fitting and selection rules) ------
#
# B1 is reported against these; leakage is decided by provenance, never by
# an accuracy near zero. All three consume only the public projection, and
# all are fitted on construction data before construction outcomes are
# inspected.

def fit_majority_class(cell_id: str, rows: list[PublicFeatureRecord]
                       ) -> dict[str, int]:
    """Per-(cell, observable subtype) majority gold value.

    Frozen tie rule: highest count, then the lowest gold value — so the
    control is a deterministic function of the construction sample.
    """
    _check_control_rows(cell_id, rows)
    counts: dict[str, Counter] = {}
    for row in rows:
        subtype = observable_subtype(cell_id, row.params)
        counts.setdefault(subtype, Counter())[row.gold_answer] += 1
    return {subtype: min(counter.items(),
                         key=lambda kv: (-kv[1], kv[0]))[0]
            for subtype, counter in counts.items()}


def majority_class_predict(model: dict[str, int], cell_id: str,
                           params: PublicParams) -> int | None:
    """None where the subtype was never seen during fitting — scored wrong,
    never silently imputed."""
    return model.get(observable_subtype(cell_id, params))


def echo_family(cell_id: str) -> tuple[str, ...]:
    """The public parameters a single-parameter echo predictor can use.

    Evaluated only in subtypes where the parameter exists (§1.11): a `k`
    echo is undefined for the count shape and is not scored there.
    """
    names = set()
    for key, params in PUBLIC_NUMERIC_PARAMS.items():
        if key == cell_id or key.startswith(f"{cell_id}_"):
            names.update(params)
    return tuple(sorted(names))


def echo_predict(parameter: str,
                 public_numeric_values: dict[str, int]) -> int | None:
    """The parameter's own value, or None where it does not exist in this
    subtype (excluded from that subtype's evaluation rather than scored)."""
    return public_numeric_values.get(parameter)


def _check_control_rows(cell_id: str, rows: list[PublicFeatureRecord]) -> None:
    if not rows:
        raise InfrastructureError("no fitting rows")
    if any(not isinstance(row, PublicFeatureRecord) for row in rows):
        raise InfrastructureError(
            "B1 controls fit on PublicFeatureRecord rows only")
    if any(row.cell_id != cell_id for row in rows):
        raise InfrastructureError("mixed-cell fitting rows")
    off = sorted({row.namespace for row in rows} - {FIT_NAMESPACE})
    if off:
        raise InfrastructureError(
            f"B1 controls are construction-only; got {off}")
    ids = [row.latent_program_id for row in rows]
    if len(set(ids)) != len(ids):
        raise InfrastructureError("duplicate latent clusters in fitting rows")
