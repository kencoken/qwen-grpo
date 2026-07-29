"""Development-only Q3 task-discovery harness.

This module is intentionally separate from the frozen production generator.
It constructs latent Code programs from the existing sequence semantics,
renders matched target conditions, executes the frozen w2/w3 workers through
the registered four-worker runtime, and scores the requested scalar target
independently.

The production reference IR has no sequence-valued nodes.  The experimental
latent therefore records sequence-valued semantic nodes for provenance, but
every requested target is an existing legal scalar Code artifact and is
executed by the unchanged ``cell-specs-v0.8`` parser/tool.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import re
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import contract, executor, program, render, worker_eval
from .pool_runtime import (
    FOUR_WORKER_RUNTIME_PROFILE,
    build_pool_runtime,
)
from .profiles import DEFAULT_PROFILE
from .resources import InstanceRegistry
from .tools import Binding, binding_sha256
from .types import (
    RENDERER_IDS,
    SYNTAX_REJECTION_CODES,
    InfrastructureError,
    IntegerList,
)
from .workerpool import (
    STAGE0_POOL_FINGERPRINT,
    STAGE0_WORKER_POOL,
    WORKER_NAMES,
)

SCHEMA_VERSION = 1
GENERATOR_VERSION = "q3-task-discovery-generator-v1"
SCORER_VERSION = "q3-task-discovery-scorer-v1"
CELL_ID = "code_scope_composition"
WORKER_IDS = (2, 3)
RENDERERS = tuple(RENDERER_IDS)
REQUEST_CONTRACT = render.CONTRACT_TASK_LAST
WORDING_FAMILIES = ("canonical", "alternate")
EXPECTED_POOL_FINGERPRINT = "wp-197e286115f56e4a"
EXPECTED_WORKER_VISIBLE_FINGERPRINT = "wv-4e196a1c467d108b"
EXPECTED_WORKER_FINGERPRINTS = {
    2: "slw-bfb9b10016770298",
    3: "slw-247bf2139befbc03",
}
EXPECTED_CODE_FAMILY_FINGERPRINT = "epf-d8f834da028432d3"
EXPECTED_CHECKPOINTS: dict[tuple[str, str], dict[str, Any]] = {
    (
        "Qwen/Qwen2.5-1.5B-Instruct",
        "989aa7980e4cf806f80c7fef2b1adb7bc71aa306",
    ): {
        "workers": ["lookup_1p5b", "math_1p5b", "code_1p5b"],
        "measured_parameters": 1_543_714_304,
    },
    (
        "Qwen/Qwen2.5-3B-Instruct",
        "aa8e72537993ba99e69dfaafa59ed015b17504d1",
    ): {
        "workers": ["code_3b"],
        "measured_parameters": 3_085_938_688,
    },
}
MAX_PHYSICAL_GENERATIONS = 2_000
MAX_GPU_SECONDS = 10 * 60 * 60
MAX_HOLDOUT_REVEALS = 2

STRATEGY_CONDITIONS: dict[str, tuple[str, ...]] = {
    "strategy1": ("intermediate_target", "terminal_target"),
    "strategy2": ("relevant_continuation", "distracting_continuation"),
    "strategy3": (
        "direct_literal",
        "direct_bound",
        "nested_literal",
        "nested_bound",
    ),
}

# These predictions are semantic and prospective.  They are never inferred
# from individual rows or numeric values.
DEFAULT_SEMANTIC_ROUTER: dict[str, int] = {
    "intermediate_target": 2,
    "terminal_target": 3,
    "relevant_continuation": 3,
    "distracting_continuation": 2,
    "direct_literal": 2,
    "direct_bound": 3,
    "nested_literal": 2,
    "nested_bound": 3,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(_json_bytes(value))
    os.replace(tmp, path)


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as handle:
        for row in rows:
            handle.write(_json_bytes(dict(row)))
    os.replace(tmp, path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line]


def _git_info() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], check=True, capture_output=True, text=True,
        ).stdout.strip()

    status = run("status", "--porcelain")
    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty": bool(status),
        "status_sha256": _sha256_text(status),
    }


PROVENANCE_SOURCE_PATHS = (
    "tasks/conductor/q3_discovery.py",
    "tasks/conductor/program.py",
    "tasks/conductor/render.py",
    "tasks/conductor/executor.py",
    "tasks/conductor/contract.py",
    "tasks/conductor/tools.py",
    "tasks/conductor/pool_runtime.py",
    "tasks/conductor/workerpool.py",
    "tasks/conductor/prompts.py",
    "plans/conductor/exploration/q3_task_discovery/"
    "00_q3_task_discovery_overnight_plan.md",
)


def _source_digests() -> dict[str, str]:
    return {
        path: _sha256_bytes(Path(path).read_bytes())
        for path in PROVENANCE_SOURCE_PATHS
    }


@dataclass(frozen=True)
class DiscoveryLatent:
    strategy_id: str
    strategy_revision: str
    namespace: str
    latent_index: int
    latent_id: str
    paired_latent_id: str
    seed_sha256: str
    handle: str
    sequence: tuple[int, ...]
    unique_sequence: tuple[int, ...]
    threshold: int
    count_index: int
    rotation: int
    literal_index: int
    references: dict[str, int]
    reference_artifacts: dict[str, str]
    semantic_program: dict[str, Any]

    def resource(self) -> IntegerList:
        return IntegerList(payload=self.sequence)


@dataclass(frozen=True)
class DiscoveryCase:
    case_id: str
    observation_id: str
    strategy_id: str
    strategy_revision: str
    namespace: str
    split: str
    latent_id: str
    paired_latent_id: str
    latent_index: int
    renderer: str
    wording_family: str
    condition: str
    semantic_factors: dict[str, Any]
    target_node: str
    target_scope: str
    handle: str
    sequence: tuple[int, ...]
    previous_results: dict[int, int]
    public_prompt: str
    task_block: str
    user_message: str
    request_user_sha256: str
    binding_sha256: str
    reference_target: int
    reference_artifact: str
    alternate_targets: dict[str, int]
    source_case_id: str | None = None
    expected_direction: str | None = None

    def binding(self) -> Binding:
        return Binding(
            resources={self.handle: IntegerList(payload=self.sequence)},
            steps=dict(self.previous_results),
        )


def generate_latent(strategy_id: str, strategy_revision: str,
                    namespace: str, latent_index: int) -> DiscoveryLatent:
    """Generate one deterministic latent before any language rendering."""
    if strategy_id not in STRATEGY_CONDITIONS:
        raise ValueError(f"unknown strategy {strategy_id!r}")
    token = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
    for name, value in (
            ("strategy_revision", strategy_revision),
            ("namespace", namespace)):
        if not isinstance(value, str) or not token.fullmatch(value):
            raise ValueError(
                f"{name} must match {token.pattern!r}, got {value!r}")
    if not isinstance(latent_index, int) or isinstance(latent_index, bool) \
            or latent_index < 0:
        raise ValueError("latent_index must be nonnegative")
    material = (
        f"{GENERATOR_VERSION}|{strategy_id}|{strategy_revision}|"
        f"{namespace}|{latent_index}"
    )
    seed_sha = _sha256_text(material)
    rng = random.Random(int(seed_sha[:16], 16))

    for _attempt in range(10_000):
        unique_count = rng.randint(8, 11)
        unique = rng.sample(range(10, 100), unique_count)
        duplicate_count = rng.randint(3, 7)
        duplicates = [rng.choice(unique) for _ in range(duplicate_count)]
        rng.shuffle(duplicates)
        sequence = tuple(unique + duplicates)

        count_index = rng.randint(1, unique_count - 2)
        # With pairwise-distinct values, this gives exactly count_index
        # values strictly above the threshold.
        threshold = sorted(unique)[-(count_index + 1)]
        if program.count_gt(program.stable_unique(sequence), threshold) \
                != count_index:
            continue
        rotation = rng.randint(1, unique_count - 1)
        literal_index = rng.randint(0, unique_count - 1)
        if literal_index == count_index:
            continue

        deduped = program.stable_unique(sequence)
        rotated = program.rotate_left(deduped, rotation)
        references = {
            "intermediate": count_index,
            "direct_literal": program.at(sequence, literal_index),
            "direct_bound": program.at(sequence, count_index),
            "nested_literal": program.at(rotated, literal_index),
            "nested_bound": program.at(rotated, count_index),
        }
        # Keep target attribution unambiguous.  This is a semantic
        # construction constraint, never an outcome-based instance search.
        if len(set(references.values())) != len(references):
            continue
        break
    else:
        raise InfrastructureError(
            f"failed to generate semantic latent from {material}")

    handle_rng = random.Random(int(seed_sha[16:32], 16))
    handle = (
        f"R-{handle_rng.randrange(10)}"
        f"{chr(ord('A') + handle_rng.randrange(26))}"
        f"{handle_rng.randrange(10)}"
    )
    latent_id = (
        f"{CELL_ID}:{namespace}:{latent_index:05d}:{seed_sha[:8]}"
    )
    pair_id = (
        f"{strategy_id}:{strategy_revision}:{namespace}:{latent_index:05d}:"
        f"{seed_sha[:8]}"
    )
    artifacts = {
        "intermediate": (
            f"count_gt(stable_unique(resource), {threshold})"
        ),
        "direct_literal": f"at(resource, {literal_index})",
        "direct_bound": "at(resource, step_1)",
        "nested_literal": (
            "at(rotate_left(stable_unique(resource), "
            f"{rotation}), {literal_index})"
        ),
        "nested_bound": (
            "at(rotate_left(stable_unique(resource), "
            f"{rotation}), step_1)"
        ),
    }
    semantic_program = {
        "schema": "q3-experimental-typed-code-graph-v1",
        "nodes": [
            {"id": "u", "op": "stable_unique",
             "args": {"xs": {"res": handle}}, "type": "integer_list"},
            {"id": "n1", "op": "count_gt",
             "args": {"xs": {"node": "u"}, "t": {"lit": threshold}},
             "type": "integer"},
            {"id": "v", "op": "rotate_left",
             "args": {"xs": {"node": "u"}, "k": {"lit": rotation}},
             "type": "integer_list"},
            {"id": "n2", "op": "at",
             "args": {"xs": {"res": handle},
                      "i": {"lit": literal_index}},
             "type": "integer"},
            {"id": "n3", "op": "at",
             "args": {"xs": {"res": handle}, "i": {"node": "n1"}},
             "type": "integer"},
            {"id": "n4", "op": "at",
             "args": {"xs": {"node": "v"},
                      "i": {"lit": literal_index}},
             "type": "integer"},
            {"id": "n5", "op": "at",
             "args": {"xs": {"node": "v"}, "i": {"node": "n1"}},
                "type": "integer"},
        ],
        "step_numbering": {"step_1": "n1"},
        "condition_paths": {
            "intermediate": ["n1"],
            "direct_literal": ["n2"],
            "direct_bound": ["n1", "n3"],
            "nested_literal": ["n4"],
            "nested_bound": ["n1", "n5"],
        },
        "sink": "n5",
        "note": (
            "u and v are experimental latent sequence nodes; all requested "
            "targets compile to unchanged legal scalar Code artifacts"
        ),
    }
    latent = DiscoveryLatent(
        strategy_id=strategy_id,
        strategy_revision=strategy_revision,
        namespace=namespace,
        latent_index=latent_index,
        latent_id=latent_id,
        paired_latent_id=pair_id,
        seed_sha256=seed_sha,
        handle=handle,
        sequence=sequence,
        unique_sequence=tuple(deduped),
        threshold=threshold,
        count_index=count_index,
        rotation=rotation,
        literal_index=literal_index,
        references=references,
        reference_artifacts=artifacts,
        semantic_program=semantic_program,
    )
    validate_discovery_latent(latent)
    return latent


def validate_discovery_latent(latent: DiscoveryLatent) -> None:
    """Validate the experimental typed graph and all executable targets."""
    graph = latent.semantic_program
    if graph.get("schema") != "q3-experimental-typed-code-graph-v1":
        raise InfrastructureError(f"{latent.latent_id}: graph schema drift")
    nodes = {node["id"]: node for node in graph.get("nodes", [])}
    if set(nodes) != {"u", "n1", "v", "n2", "n3", "n4", "n5"}:
        raise InfrastructureError(
            f"{latent.latent_id}: graph node set drift")
    expected_types = {
        "u": "integer_list", "n1": "integer", "v": "integer_list",
        "n2": "integer", "n3": "integer", "n4": "integer",
        "n5": "integer",
    }
    if {key: node["type"] for key, node in nodes.items()} \
            != expected_types:
        raise InfrastructureError(
            f"{latent.latent_id}: graph type assignment drift")
    if graph.get("step_numbering") != {"step_1": "n1"}:
        raise InfrastructureError(
            f"{latent.latent_id}: step_1 must denote scalar n1")
    if graph.get("sink") != "n5":
        raise InfrastructureError(f"{latent.latent_id}: sink must be n5")

    unique = program.stable_unique(latent.sequence)
    rotated = program.rotate_left(unique, latent.rotation)
    recomputed = {
        "intermediate": program.count_gt(unique, latent.threshold),
        "direct_literal": program.at(
            latent.sequence, latent.literal_index),
        "direct_bound": program.at(
            latent.sequence, latent.count_index),
        "nested_literal": program.at(rotated, latent.literal_index),
        "nested_bound": program.at(rotated, latent.count_index),
    }
    if recomputed != latent.references:
        raise InfrastructureError(
            f"{latent.latent_id}: independent references drift")
    binding = Binding(
        resources={latent.handle: latent.resource()},
        steps={1: latent.count_index},
    )
    for target, artifact in latent.reference_artifacts.items():
        result = contract.run_worker_output(
            2, f"<artifact>{artifact}</artifact>", binding)
        if result.status != "success" \
                or result.value != latent.references[target]:
            raise InfrastructureError(
                f"{latent.latent_id}:{target}: artifact/tool disagreement")


def render_problem(latent: DiscoveryLatent, renderer_id: str) -> str:
    """Render one latent plan through the three existing renderer strata."""
    if renderer_id not in RENDERERS:
        raise ValueError(f"unknown renderer {renderer_id!r}")
    h = latent.handle
    t = latent.threshold
    k = latent.rotation
    i = latent.literal_index
    if renderer_id == "resource_first":
        return (
            f"Resource {h} contains an integer sequence. Keep only the first "
            f"occurrence of each value, and let j be the count of retained "
            f"values greater than {t}. Rotate the retained sequence left by "
            f"{k} positions. The plan defines four scalar checks: index {i} "
            f"of the original sequence, index j of the original sequence, "
            f"index {i} of the rotated retained sequence, and index j of the "
            "rotated retained sequence. The last check is the terminal "
            "result."
        )
    if renderer_id == "goal_first":
        return (
            f"The terminal result is the value at zero-based index j after "
            f"the sequence in {h} is reduced to first occurrences and "
            f"rotated left by {k}, where j is how many retained values are "
            f"greater than {t}. For comparison the same plan also defines "
            f"the values at index {i} and at index j in the original "
            f"sequence, and at index {i} in the rotated retained sequence."
        )
    return (
        f"Let u be the sequence in {h} after later repeated occurrences are "
        f"removed. Let j = count(u > {t}) and let v be u rotated left by "
        f"{k}. The plan's scalar checks are original[{i}], original[j], "
        f"v[{i}], and v[j]; v[j] is terminal."
    )


def _task_for(target: str, latent: DiscoveryLatent,
              wording_family: str) -> str:
    if wording_family not in WORDING_FAMILIES:
        raise ValueError(f"unknown wording family {wording_family!r}")
    t = latent.threshold
    k = latent.rotation
    i = latent.literal_index
    canonical = {
        "intermediate": (
            "Remove later occurrences of repeated values from the integer "
            "sequence in the requested resource and count the values greater "
            f"than {t}."
        ),
        "direct_literal": (
            f"Return the value at zero-based index {i} in the integer "
            "sequence from the requested resource."
        ),
        "direct_bound": (
            "Return the value at zero-based index step_1 in the integer "
            "sequence from the requested resource."
        ),
        "nested_literal": (
            "Remove later occurrences of repeated values from the integer "
            "sequence in the requested resource, rotate the remaining "
            f"sequence left by {k} positions, and return the value at "
            f"zero-based index {i}."
        ),
        "nested_bound": (
            "Remove later occurrences of repeated values from the integer "
            "sequence in the requested resource, rotate the remaining "
            f"sequence left by {k} positions, and return the value at "
            "zero-based index step_1."
        ),
    }
    alternate = {
        "intermediate": (
            "Keep the first occurrence of every value in the requested "
            f"sequence; return how many kept values are above {t}."
        ),
        "direct_literal": (
            f"Select element {i}, using zero-based indexing, directly from "
            "the requested integer sequence."
        ),
        "direct_bound": (
            "Select directly from the requested integer sequence at the "
            "zero-based position supplied as step_1."
        ),
        "nested_literal": (
            "Keep first occurrences in the requested sequence, left-rotate "
            f"the result by {k}, then select zero-based position {i}."
        ),
        "nested_bound": (
            "Keep first occurrences in the requested sequence, left-rotate "
            f"the result by {k}, then select the zero-based position supplied "
            "as step_1."
        ),
    }
    table = canonical if wording_family == "canonical" else alternate
    return table[target]


def _condition_target(strategy_id: str, condition: str) -> str:
    mapping = {
        ("strategy1", "intermediate_target"): "direct_bound",
        ("strategy1", "terminal_target"): "nested_bound",
        ("strategy2", "relevant_continuation"): "nested_bound",
        ("strategy2", "distracting_continuation"): "nested_literal",
        ("strategy3", "direct_literal"): "direct_literal",
        ("strategy3", "direct_bound"): "direct_bound",
        ("strategy3", "nested_literal"): "nested_literal",
        ("strategy3", "nested_bound"): "nested_bound",
    }
    try:
        return mapping[(strategy_id, condition)]
    except KeyError as exc:
        raise ValueError(
            f"condition {condition!r} is not part of {strategy_id!r}"
        ) from exc


def _semantic_factors(strategy_id: str, condition: str,
                      target: str) -> dict[str, Any]:
    nested = target.startswith("nested")
    bound = target.endswith("bound")
    scope = {
        "intermediate": "intermediate",
        "direct_literal": "side_probe",
        "direct_bound": "side_probe",
        "nested_literal": "side_probe",
        "nested_bound": "terminal",
    }[target]
    return {
        "target_condition": condition,
        "target_family": target,
        "target_scope": scope,
        "composition": (
            "nested" if nested or target == "intermediate" else "direct"
        ),
        "argument_source": "predecessor" if bound else "literal",
        "predecessor_relevance": "relevant" if bound else "irrelevant",
        "rotation_relevance": "relevant" if nested else "irrelevant",
        "terminal_continuation_relevance": (
            "relevant" if target == "nested_bound" else "irrelevant"
        ),
        "task_cell": CELL_ID,
        "strategy": strategy_id,
    }


def cases_for_latent(latent: DiscoveryLatent,
                     renderers: Sequence[str],
                     wording_family: str,
                     conditions: Sequence[str] | None = None
                     ) -> list[DiscoveryCase]:
    cases: list[DiscoveryCase] = []
    resource = latent.resource()
    registry = InstanceRegistry(
        [latent.handle], {latent.handle: resource.to_json()})
    selected_conditions = (
        tuple(conditions)
        if conditions is not None
        else STRATEGY_CONDITIONS[latent.strategy_id]
    )
    declared_conditions = set(STRATEGY_CONDITIONS[latent.strategy_id])
    if not selected_conditions \
            or len(set(selected_conditions)) != len(selected_conditions) \
            or any(condition not in declared_conditions
                   for condition in selected_conditions):
        raise ValueError(
            "conditions must be a nonempty unique subset of "
            f"{STRATEGY_CONDITIONS[latent.strategy_id]}")
    for renderer_id in renderers:
        public_prompt = render_problem(latent, renderer_id)
        for condition in selected_conditions:
            target = _condition_target(latent.strategy_id, condition)
            previous = (
                {1: latent.count_index}
                if target.endswith("bound")
                or latent.strategy_id in {"strategy2", "strategy3"}
                else {}
            )
            task = _task_for(target, latent, wording_family)
            user_message, binding = executor.build_worker_call(
                public_prompt,
                task,
                latent.handle,
                registry,
                previous if previous else None,
                contract=REQUEST_CONTRACT,
            )
            observation_id = (
                f"{latent.latent_id}:{renderer_id}:{condition}:"
                f"{wording_family}:private"
            )
            case_id = f"{observation_id}:target"
            target_scope = {
                "intermediate": "intermediate",
                "direct_literal": "side_probe",
                "direct_bound": "side_probe",
                "nested_literal": "side_probe",
                "nested_bound": "terminal",
            }[target]
            cases.append(DiscoveryCase(
                case_id=case_id,
                observation_id=observation_id,
                strategy_id=latent.strategy_id,
                strategy_revision=latent.strategy_revision,
                namespace=latent.namespace,
                split=latent.namespace,
                latent_id=latent.latent_id,
                paired_latent_id=latent.paired_latent_id,
                latent_index=latent.latent_index,
                renderer=renderer_id,
                wording_family=wording_family,
                condition=condition,
                semantic_factors=_semantic_factors(
                    latent.strategy_id, condition, target),
                target_node={
                    "intermediate": "n1",
                    "direct_literal": "n2",
                    "direct_bound": "n3",
                    "nested_literal": "n4",
                    "nested_bound": "n5",
                }[target],
                target_scope=target_scope,
                handle=latent.handle,
                sequence=latent.sequence,
                previous_results=previous,
                public_prompt=public_prompt,
                task_block=task,
                user_message=user_message,
                request_user_sha256=_sha256_text(user_message),
                binding_sha256=binding_sha256(binding),
                reference_target=latent.references[target],
                reference_artifact=latent.reference_artifacts[target],
                alternate_targets={
                    key: value for key, value in latent.references.items()
                    if key != target
                },
            ))
    return cases


def build_strategy_cases(strategy_id: str, strategy_revision: str,
                         namespace: str, latent_start: int,
                         latent_count: int, renderers: Sequence[str],
                         wording_family: str,
                         conditions: Sequence[str] | None = None
                         ) -> tuple[list[DiscoveryLatent],
                                    list[DiscoveryCase]]:
    if latent_count < 1:
        raise ValueError("latent_count must be positive")
    if len(set(renderers)) != len(renderers) \
            or any(renderer not in RENDERERS for renderer in renderers):
        raise ValueError(f"renderers must be unique members of {RENDERERS}")
    latents = [
        generate_latent(
            strategy_id, strategy_revision, namespace, latent_start + index)
        for index in range(latent_count)
    ]
    cases = [
        case
        for latent in latents
        for case in cases_for_latent(
            latent, renderers, wording_family, conditions)
    ]
    return latents, cases


BASELINE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "cell_id": "code_atomic",
        "namespace": "routing_dev",
        "latent_index": 0,
        "renderer": "goal_first",
        "node_id": "n1",
        "condition": "retained_both_correct",
        "expected_direction": "both",
        "source_case_id":
            "code_atomic:routing_dev:00000:e23a43bd:"
            "goal_first:private:n1",
        "user_sha256":
            "064cc3c742b528798723211c89e4b142cd62d166897be39c69f97ff9f2302dfc",
        "request_sha256":
            "9b829caa9f71021eb9b5e83205ad997e3eba0cca2b3f4561843707d8edb79f7a",
        "reference_target": 1,
        "expected_rejection": {2: None, 3: None},
    },
    {
        "cell_id": "code_atomic",
        "namespace": "routing_dev",
        "latent_index": 5,
        "renderer": "goal_first",
        "node_id": "n1",
        "condition": "retained_w2_only_protocol",
        "expected_direction": "w2",
        "source_case_id":
            "code_atomic:routing_dev:00005:bcd17865:"
            "goal_first:private:n1",
        "user_sha256":
            "6a0de53c0cf7a7253e9de5ee6260a8a41b1b9ee959b0f98555571316100d1c30",
        "request_sha256":
            "ac2a56c321b6b4a20f0743a25bb3fa4e98263670de87473e1ca15f7e6dd4472c",
        "reference_target": 9,
        "expected_rejection": {2: None, 3: "E_PARSE"},
    },
    {
        "cell_id": "code_atomic",
        "namespace": "routing_dev",
        "latent_index": 9,
        "renderer": "goal_first",
        "node_id": "n1",
        "condition": "retained_w3_only_protocol",
        "expected_direction": "w3",
        "source_case_id":
            "code_atomic:routing_dev:00009:b1e65b09:"
            "goal_first:private:n1",
        "user_sha256":
            "9abe4ee58a53e3c212d9e9041b922aff27c9c32e77ca6de6c99cc4c5dac041fa",
        "request_sha256":
            "11c1381fc3cac19b0a2bac2d19bd4a2f520db3a36770b6c7ab70c05458c1bac7",
        "reference_target": 3,
        "expected_rejection": {2: "E_PARSE", 3: None},
    },
    {
        "cell_id": "fork_join",
        "namespace": "routing_dev",
        "latent_index": 1,
        "renderer": "bound_var",
        "node_id": "n2",
        "condition": "retained_w2_only_legal_semantic",
        "expected_direction": "w2_legal_semantic_w3",
        "source_case_id":
            "fork_join:routing_dev:00001:3b8d777f:"
            "bound_var:private:n2",
        "user_sha256":
            "9ccb389c8b14b2828fed06340580e91b9b28cc4788f2eb541361cb4a95fd4991",
        "request_sha256":
            "97ff7338e70cba258b11e4ac245a81682c5f07d327d9f3d825ce0a713355dacc",
        "reference_target": 6,
        "expected_rejection": {2: None, 3: None},
    },
)


def build_baseline_cases() -> list[DiscoveryCase]:
    """Regenerate four retained support nodes through the current builder."""
    cases: list[DiscoveryCase] = []
    for ordinal, spec in enumerate(BASELINE_SPECS):
        latent = program.generate_latent(
            spec["cell_id"], spec["namespace"], spec["latent_index"],
            DEFAULT_PROFILE,
        ).latent
        generated, labels = worker_eval.node_cases_for_latent(
            latent,
            [spec["renderer"]],
            "private",
            request_contract_key=REQUEST_CONTRACT,
        )
        joined = [
            (case, label)
            for case, label in zip(generated, labels)
            if label.node_id == spec["node_id"]
        ]
        if len(joined) != 1:
            raise InfrastructureError(
                f"baseline spec {spec} resolved to {len(joined)} cases")
        source, label = joined[0]
        if source.case_id != spec["source_case_id"]:
            raise InfrastructureError(
                f"baseline source drift: {source.case_id!r} != "
                f"{spec['source_case_id']!r}")
        if _sha256_text(source.user_message) != spec["user_sha256"]:
            raise InfrastructureError(
                f"baseline {source.case_id}: user-message bytes drift")
        if label.expected_value != spec["reference_target"]:
            raise InfrastructureError(
                f"baseline {source.case_id}: reference target drift")
        if source.endpoint_name != "code":
            raise InfrastructureError(
                f"baseline {source.case_id} is not a Code node")
        if len(source.resources) != 1:
            raise InfrastructureError(
                f"baseline {source.case_id} does not authorize one resource")
        handle, resource = source.resources[0]
        if not isinstance(resource, IntegerList):
            raise InfrastructureError(
                f"baseline {source.case_id} resource is not IntegerList")
        instance = program.render_instance(
            latent, spec["renderer"], "private")
        steps = {
            step["node"]: step for step in program.workflow_steps(latent)
        }
        task = steps[spec["node_id"]]["subtask"]
        cases.append(DiscoveryCase(
            case_id=f"baseline:{ordinal}:{source.case_id}",
            observation_id=source.observation_id,
            strategy_id="baseline",
            strategy_revision="retained-routing-dev-v1",
            namespace=spec["namespace"],
            split="baseline",
            latent_id=label.latent_program_id,
            paired_latent_id=label.latent_program_id,
            latent_index=spec["latent_index"],
            renderer=spec["renderer"],
            wording_family="frozen-production",
            condition=spec["condition"],
            semantic_factors={
                "task_cell": spec["cell_id"],
                "node_family": label.node_family,
                "baseline_expected_direction": spec["expected_direction"],
                "baseline_expected_request_sha256":
                    spec["request_sha256"],
                "baseline_expected_rejection": {
                    str(key): value
                    for key, value in spec["expected_rejection"].items()
                },
            },
            target_node=spec["node_id"],
            target_scope="retained_node",
            handle=handle,
            sequence=resource.payload,
            previous_results=dict(source.steps),
            public_prompt=instance["public_prompt"],
            task_block=task,
            user_message=source.user_message,
            request_user_sha256=_sha256_text(source.user_message),
            binding_sha256=source.binding_sha256,
            reference_target=label.expected_value,
            reference_artifact="retained independent node label",
            alternate_targets={},
            source_case_id=source.case_id,
            expected_direction=spec["expected_direction"],
        ))
    return cases


def validate_reference_agreement(case: DiscoveryCase) -> None:
    """Prove the independently computed label agrees with the frozen tool."""
    if case.strategy_id == "baseline":
        return
    completion = f"<artifact>{case.reference_artifact}</artifact>"
    result = contract.run_worker_output(2, completion, case.binding())
    if result.status != "success" or result.value != case.reference_target:
        raise InfrastructureError(
            f"{case.case_id}: reference artifact/tool disagreement: "
            f"{result!r} != {case.reference_target}")


def _artifact_body(completion: str) -> str | None:
    try:
        return contract.parse_envelope(completion)
    except Exception:
        return None


def classify_failure(case: DiscoveryCase, result: Any,
                     completion: str) -> str | None:
    """Classify one incorrect row under the plan's required taxonomy."""
    correct = (
        result.status == "success"
        and result.value == case.reference_target
    )
    if correct:
        return None
    if result.rejection_code in SYNTAX_REJECTION_CODES:
        return "parse/grammar"
    if result.status == "typed_failure":
        if result.rejection_code in {
            "E_NO_RESOURCE", "E_RESOURCE_KIND", "E_UNKNOWN_IDENT",
            "E_UNKNOWN_KEY", "E_UNKNOWN_FIELD",
        }:
            return "resource/identifier protocol"
        if result.rejection_code in {
            "E_INDEX_RANGE", "E_BAD_ARG",
        }:
            return "threshold/index/value"
        return "other legal semantic error"

    if result.status == "success":
        matching = [
            name for name, value in case.alternate_targets.items()
            if value == result.value
        ]
        if matching:
            return "over-composition/wrong target"
        body = _artifact_body(completion) or ""
        expected_bound = case.reference_artifact.endswith(
            "step_1)") or ", step_1)" in case.reference_artifact
        if expected_bound != ("step_1" in body):
            return "predecessor/binding"
        if any(token in body for token in (
                "count_gt", "at", "rotate_left", "stable_unique")):
            return "threshold/index/value"
        return "other legal semantic error"
    return "other legal semantic error"


def _case_record(case: DiscoveryCase) -> dict[str, Any]:
    row = asdict(case)
    row["sequence"] = list(case.sequence)
    row["previous_results"] = {
        str(key): value for key, value in case.previous_results.items()
    }
    return row


def _latent_record(latent: DiscoveryLatent) -> dict[str, Any]:
    row = asdict(latent)
    row["sequence"] = list(latent.sequence)
    row["unique_sequence"] = list(latent.unique_sequence)
    return row


def _runtime_manifest(runtime: Any) -> dict[str, Any]:
    profile = runtime.profile
    return {
        "worker_pool_fingerprint": runtime.pool_fingerprint,
        "runtime_profile_fingerprint":
            runtime.runtime_profile_fingerprint,
        "worker_visible_fingerprint":
            runtime.worker_visible_fingerprint,
        "selected_worker_fingerprints": {
            str(worker_id): runtime.worker_fingerprints[worker_id]
            for worker_id in WORKER_IDS
        },
        "endpoint_family_fingerprint":
            runtime.endpoint_family_fingerprints["code"],
        "chat_template_sha256": {
            spec.name: runtime.chat_template_shas[spec.name]
            for spec in runtime.specs if spec.worker_id in WORKER_IDS
        },
        "system_prompt_sha256": {
            spec.name: runtime.system_prompt_shas[spec.name]
            for spec in runtime.specs if spec.worker_id in WORKER_IDS
        },
        "request_contract":
            worker_eval.resolve_request_contract(REQUEST_CONTRACT),
        "profile": profile,
        "generation_policy": worker_eval.GENERATION_POLICY_SINGLETON,
    }


def _build_runtime(out_dir: Path) -> Any:
    profile = copy.deepcopy(FOUR_WORKER_RUNTIME_PROFILE)
    profile["profile_name"] = "q3-task-discovery"
    profile["cache_path"] = str(
        (out_dir.parent / "cache.sqlite").resolve())
    return build_pool_runtime(profile)


def _validate_runtime_identity(runtime: Any) -> None:
    if runtime.pool_fingerprint != EXPECTED_POOL_FINGERPRINT:
        raise InfrastructureError("frozen worker-pool fingerprint drift")
    if runtime.worker_visible_fingerprint != \
            EXPECTED_WORKER_VISIBLE_FINGERPRINT:
        raise InfrastructureError("frozen worker-visible fingerprint drift")
    if {
            worker_id: runtime.worker_fingerprints[worker_id]
            for worker_id in WORKER_IDS
    } != EXPECTED_WORKER_FINGERPRINTS:
        raise InfrastructureError("frozen selected-worker fingerprint drift")
    if runtime.endpoint_family_fingerprints["code"] != \
            EXPECTED_CODE_FAMILY_FINGERPRINT:
        raise InfrastructureError("frozen Code-family fingerprint drift")


def _preflight_rendered_requests(runtime: Any,
                                 cases: Sequence[DiscoveryCase]) -> None:
    """Render both workers before generation and prove byte equivalence."""
    seen_messages: set[str] = set()
    for case in cases:
        if case.user_message in seen_messages:
            raise InfrastructureError(
                f"{case.case_id}: duplicate request within one run")
        seen_messages.add(case.user_message)
        rendered = {
            worker_id: runtime.pool.render_request(
                worker_id, case.user_message)
            for worker_id in WORKER_IDS
        }
        if rendered[2] != rendered[3]:
            raise InfrastructureError(
                f"{case.case_id}: preflight w2/w3 request bytes differ")
        if case.strategy_id == "baseline":
            expected = case.semantic_factors[
                "baseline_expected_request_sha256"]
            if _sha256_bytes(rendered[2]) != expected:
                raise InfrastructureError(
                    f"{case.source_case_id}: retained request identity drift")


def _call_key(case_id: str, worker_id: int) -> str:
    return _sha256_bytes(_json_bytes({
        "case_id": case_id,
        "worker_id": worker_id,
    }))


def _initial_cache_state(runtime: Any,
                         cases: Sequence[DiscoveryCase]) -> dict[str, Any]:
    """Record which exact planned keys existed before the first call."""
    present_keys = []
    for worker_id in WORKER_IDS:
        selected_fp = runtime.worker_fingerprints[worker_id]
        for case in cases:
            request = runtime.pool.render_request(
                worker_id, case.user_message)
            if runtime.cache.lookup(
                    runtime.worker_visible_fingerprint,
                    selected_fp,
                    request) is not None:
                present_keys.append(_call_key(case.case_id, worker_id))
    return {
        "checked_keys": len(cases) * len(WORKER_IDS),
        "present_keys": sorted(present_keys),
        "present_count": len(present_keys),
    }


def _validate_initial_cache_state(
        state: Mapping[str, Any],
        cases: Sequence[DiscoveryCase]) -> set[str]:
    planned = {
        _call_key(case.case_id, worker_id)
        for worker_id in WORKER_IDS for case in cases
    }
    present = state.get("present_keys")
    if not isinstance(present, list) \
            or any(not isinstance(key, str) for key in present) \
            or len(set(present)) != len(present) \
            or not set(present).issubset(planned) \
            or state.get("checked_keys") != len(planned) \
            or state.get("present_count") != len(present):
        raise InfrastructureError("initial cache-state evidence is invalid")
    return set(present)


def _checkpoint_report_identity(
        report: Sequence[Mapping[str, Any]],
        require_loaded: bool) -> bool:
    """Validate the exact two frozen physical checkpoints fail-closed."""
    if len(report) != len(EXPECTED_CHECKPOINTS):
        return False
    seen: set[tuple[str, str]] = set()
    for entry in report:
        key = (entry.get("model_id"), entry.get("revision"))
        if key not in EXPECTED_CHECKPOINTS or key in seen:
            return False
        seen.add(key)
        expected = EXPECTED_CHECKPOINTS[key]
        loaded = entry.get("loaded")
        if not isinstance(loaded, bool) \
                or entry.get("workers") != expected["workers"]:
            return False
        measured = entry.get("measured_parameters")
        if loaded and measured != expected["measured_parameters"]:
            return False
        if not loaded and measured is not None:
            return False
        if require_loaded and not loaded:
            return False
    return seen == set(EXPECTED_CHECKPOINTS)


def _merge_checkpoint_evidence(
        report: Sequence[Mapping[str, Any]],
        rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Merge current model state with validated physical row evidence.

    A resumed process may skip an already-recorded worker and therefore not
    reload its checkpoint. A physical row is nevertheless direct execution
    evidence that the row's registered worker checkpoint was loaded.
    """
    if not _checkpoint_report_identity(report, require_loaded=False):
        raise InfrastructureError(
            "physical checkpoint report identity drift")
    exercised_workers = {
        row["worker_name"] for row in rows
        if row["physical_generation"]
    }
    merged = []
    for raw in report:
        entry = dict(raw)
        row_evidence = bool(
            exercised_workers.intersection(entry["workers"]))
        if not entry["loaded"] and row_evidence:
            key = (entry["model_id"], entry["revision"])
            entry["loaded"] = True
            entry["measured_parameters"] = \
                EXPECTED_CHECKPOINTS[key]["measured_parameters"]
            entry["loaded_evidence"] = "validated_physical_generation"
        else:
            entry["loaded_evidence"] = (
                "current_session_checkpoint"
                if entry["loaded"] else "none"
            )
        merged.append(entry)
    return merged


def _generation_declaration(
        latents: Sequence[DiscoveryLatent],
        cases: Sequence[DiscoveryCase]) -> dict[str, Any]:
    if not cases:
        raise InfrastructureError("a run must contain at least one case")
    if not latents:
        if any(case.strategy_id != "baseline" for case in cases):
            raise InfrastructureError("missing strategy latents")
        return {
            "kind": "retained_baseline",
            "strategy_id": "baseline",
            "strategy_revision": "retained-routing-dev-v1",
            "source_case_ids": [
                case.source_case_id for case in cases],
            "case_count": len(cases),
        }
    values = {
        "strategy_id": {latent.strategy_id for latent in latents},
        "strategy_revision": {
            latent.strategy_revision for latent in latents},
        "namespace": {latent.namespace for latent in latents},
        "wording_family": {case.wording_family for case in cases},
    }
    if any(len(value) != 1 for value in values.values()):
        raise InfrastructureError(
            f"run mixes generator identities: {values}")
    indices = [latent.latent_index for latent in latents]
    if indices != list(range(indices[0], indices[0] + len(indices))):
        raise InfrastructureError("latent indices are not a contiguous range")
    # Renderer order is part of the deterministic case-file order. Preserve
    # the caller's first-seen order so verification regenerates identical
    # bytes even when the CLI order is not lexical.
    renderers = list(dict.fromkeys(case.renderer for case in cases))
    conditions = list(dict.fromkeys(case.condition for case in cases))
    strategy_id = next(iter(values["strategy_id"]))
    declared_conditions = set(STRATEGY_CONDITIONS[strategy_id])
    if not conditions or any(
            condition not in declared_conditions for condition in conditions):
        raise InfrastructureError(
            "run contains an invalid generated condition subset")
    expected_cases = (
        len(latents) * len(renderers)
        * len(conditions)
    )
    if len(cases) != expected_cases:
        raise InfrastructureError("case crossing is incomplete")
    return {
        "kind": "generated_strategy",
        "generator_version": GENERATOR_VERSION,
        "strategy_id": strategy_id,
        "strategy_revision":
            next(iter(values["strategy_revision"])),
        "namespace": next(iter(values["namespace"])),
        "latent_start": indices[0],
        "latent_count": len(indices),
        "renderers": renderers,
        "wording_family": next(iter(values["wording_family"])),
        "conditions": conditions,
    }


def _validate_router(router: Mapping[str, int],
                     conditions: set[str], label: str) -> dict[str, int]:
    normalized = dict(router)
    if set(normalized) != conditions:
        raise InfrastructureError(
            f"{label} keys {sorted(normalized)} != observed conditions "
            f"{sorted(conditions)}")
    if any(
            not isinstance(worker, int) or isinstance(worker, bool)
            or worker not in WORKER_IDS
            for worker in normalized.values()):
        raise InfrastructureError(
            f"{label} must map every condition to exact integer 2 or 3")
    return {str(key): int(value) for key, value in normalized.items()}


def _budget_preflight(out_dir: Path, run_spec: Mapping[str, Any],
                      purpose: str, planned_calls: int,
                      resume: bool) -> dict[str, Any]:
    prior_physical = 0
    prior_gpu_seconds = 0.0
    prior_holdouts = 0
    prior_namespaces: set[str] = set()
    prior_runs = []
    for path in sorted(out_dir.parent.glob("*/manifest.json")):
        if path == out_dir / "manifest.json":
            continue
        manifest = _read_json(path)
        if manifest.get("status") != "complete":
            raise InfrastructureError(
                f"another discovery run is incomplete: {path.parent}")
        prior_physical += int(manifest.get("physical_generations", 0))
        prior_gpu_seconds += float(manifest.get("gpu_seconds", 0.0))
        if "holdout" in str(manifest.get("purpose", "")).lower():
            prior_holdouts += 1
        prior_spec = manifest.get("run_spec", {})
        if prior_spec.get("namespace"):
            prior_namespaces.add(prior_spec["namespace"])
        prior_runs.append(manifest["run_id"])
    if prior_physical + planned_calls > MAX_PHYSICAL_GENERATIONS:
        raise InfrastructureError(
            f"projected physical calls {prior_physical + planned_calls} "
            f"exceed cap {MAX_PHYSICAL_GENERATIONS}")
    namespace = run_spec.get("namespace")
    if not resume and namespace and namespace in prior_namespaces:
        raise InfrastructureError(
            f"namespace {namespace!r} was already revealed")
    if "holdout" in purpose.lower() \
            and prior_holdouts >= MAX_HOLDOUT_REVEALS:
        raise InfrastructureError(
            f"holdout reveal cap {MAX_HOLDOUT_REVEALS} reached")
    if prior_gpu_seconds >= MAX_GPU_SECONDS:
        raise InfrastructureError("cumulative GPU-hour cap already reached")
    return {
        "prior_complete_runs": prior_runs,
        "prior_physical_generations": prior_physical,
        "prior_gpu_seconds": prior_gpu_seconds,
        "prior_holdout_reveals": prior_holdouts,
        "planned_calls_this_run": planned_calls,
        "projected_physical_upper_bound":
            prior_physical + planned_calls,
        "physical_generation_cap": MAX_PHYSICAL_GENERATIONS,
        "gpu_seconds_cap": MAX_GPU_SECONDS,
        "holdout_reveal_cap": MAX_HOLDOUT_REVEALS,
    }


def _append_jsonl(handle: Any, row: Mapping[str, Any]) -> None:
    handle.write(_json_bytes(dict(row)))
    handle.flush()
    os.fsync(handle.fileno())


def _raw_call_row(case: DiscoveryCase, worker_id: int, record: Any,
                  result: Any, elapsed_seconds: float,
                  recovered_cache_generation: bool = False
                  ) -> dict[str, Any]:
    stages = worker_eval.parse_stages(record.completion, result)
    correct = (
        result.status == "success"
        and result.value == case.reference_target
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case.case_id,
        "observation_id": case.observation_id,
        "strategy_id": case.strategy_id,
        "strategy_revision": case.strategy_revision,
        "split": case.split,
        "namespace": case.namespace,
        "latent_id": case.latent_id,
        "paired_latent_id": case.paired_latent_id,
        "latent_index": case.latent_index,
        "semantic_factors": case.semantic_factors,
        "renderer": case.renderer,
        "wording_family": case.wording_family,
        "condition": case.condition,
        "target_node": case.target_node,
        "target_scope": case.target_scope,
        "worker_id": worker_id,
        "worker_name": WORKER_NAMES[worker_id],
        "request_user_sha256": case.request_user_sha256,
        "request_sha256": record.request_sha256,
        "request_text": record.request_text,
        "binding_sha256": case.binding_sha256,
        "runtime_profile_fingerprint": record.runtime_fingerprint,
        "selected_worker_fingerprint": record.selected_worker_fp,
        "completion": record.completion,
        "completion_sha256": _sha256_text(record.completion),
        "finish_reason": record.finish_reason,
        "generated_tokens": record.generated_tokens,
        "generation_hit_token_cap": record.generation_hit_token_cap,
        "cache_hit": record.cache_hit,
        "physical_generation": (
            not record.cache_hit or recovered_cache_generation),
        "recovered_cache_generation": recovered_cache_generation,
        "elapsed_seconds": elapsed_seconds,
        "envelope_outcome": stages["envelope_outcome"],
        "grammar_outcome": stages["grammar_outcome"],
        "parse_status": (
            "legal" if stages["envelope_outcome"] == "ok"
            and stages["grammar_outcome"] == "ok" else "failed"
        ),
        "status": result.status,
        "rejection_code": result.rejection_code,
        "artifact_valid": result.artifact_valid,
        "tool_executed": result.tool_executed,
        "observed_value": result.value,
        "reference_target": case.reference_target,
        "reference_artifact": case.reference_artifact,
        "semantic_correct": correct,
        "failure_class": classify_failure(
            case, result, record.completion),
        "source_case_id": case.source_case_id,
        "expected_direction": case.expected_direction,
        "scorer_version": SCORER_VERSION,
    }


def _compact_call_row(row: Mapping[str, Any]) -> dict[str, Any]:
    excluded = {"request_text", "completion"}
    return {key: value for key, value in row.items()
            if key not in excluded}


def _validate_recorded_rows(
        rows: Sequence[Mapping[str, Any]],
        cases: Sequence[DiscoveryCase],
        runtime: Any) -> None:
    """Fail closed on every persisted execution and scoring field."""
    case_map = {case.case_id: case for case in cases}
    if len(case_map) != len(cases):
        raise InfrastructureError("duplicate planned case_id")
    seen: set[tuple[str, int]] = set()
    case_fields = (
        "observation_id", "strategy_id", "strategy_revision", "split",
        "namespace", "latent_id", "paired_latent_id", "latent_index",
        "renderer", "wording_family", "condition", "target_node",
        "target_scope", "semantic_factors", "request_user_sha256",
        "binding_sha256", "reference_target", "reference_artifact",
        "source_case_id", "expected_direction",
    )
    for row in rows:
        case_id = row.get("case_id")
        worker_id = row.get("worker_id")
        key = (case_id, worker_id)
        if case_id not in case_map or worker_id not in WORKER_IDS:
            raise InfrastructureError(f"unplanned persisted row {key}")
        if key in seen:
            raise InfrastructureError(f"duplicate persisted row {key}")
        seen.add(key)
        case = case_map[case_id]
        expected_case = _case_record(case)
        for field in case_fields:
            expected = expected_case[field]
            if row.get(field) != expected:
                raise InfrastructureError(
                    f"{case_id} w{worker_id}: persisted {field} drift")
        if row.get("worker_name") != WORKER_NAMES[worker_id]:
            raise InfrastructureError(
                f"{case_id} w{worker_id}: worker name drift")
        expected_request = runtime.pool.render_request(
            worker_id, case.user_message)
        if row.get("request_text") != expected_request.decode("utf-8") \
                or row.get("request_sha256") != \
                _sha256_bytes(expected_request):
            raise InfrastructureError(
                f"{case_id} w{worker_id}: rendered request drift")
        if _sha256_text(case.user_message) != \
                row.get("request_user_sha256"):
            raise InfrastructureError(
                f"{case_id} w{worker_id}: user request hash drift")
        if binding_sha256(case.binding()) != row.get("binding_sha256"):
            raise InfrastructureError(
                f"{case_id} w{worker_id}: binding hash drift")
        if row.get("runtime_profile_fingerprint") != \
                runtime.runtime_profile_fingerprint:
            raise InfrastructureError(
                f"{case_id} w{worker_id}: runtime fingerprint drift")
        if row.get("selected_worker_fingerprint") != \
                runtime.worker_fingerprints[worker_id]:
            raise InfrastructureError(
                f"{case_id} w{worker_id}: worker fingerprint drift")
        completion = row.get("completion")
        if not isinstance(completion, str) \
                or _sha256_text(completion) != row.get("completion_sha256"):
            raise InfrastructureError(
                f"{case_id} w{worker_id}: completion hash drift")
        result = contract.run_worker_output(
            2, completion, case.binding())
        stages = worker_eval.parse_stages(completion, result)
        correct = (
            result.status == "success"
            and result.value == case.reference_target
        )
        expected_score = {
            "envelope_outcome": stages["envelope_outcome"],
            "grammar_outcome": stages["grammar_outcome"],
            "parse_status": (
                "legal" if stages["envelope_outcome"] == "ok"
                and stages["grammar_outcome"] == "ok" else "failed"
            ),
            "status": result.status,
            "rejection_code": result.rejection_code,
            "artifact_valid": result.artifact_valid,
            "tool_executed": result.tool_executed,
            "observed_value": result.value,
            "semantic_correct": correct,
            "failure_class": classify_failure(case, result, completion),
            "scorer_version": SCORER_VERSION,
        }
        for field, expected in expected_score.items():
            if row.get(field) != expected:
                raise InfrastructureError(
                    f"{case_id} w{worker_id}: score field {field} drift")
        recovered = bool(row.get("recovered_cache_generation", False))
        if bool(row.get("physical_generation")) != (
                not bool(row.get("cache_hit")) or recovered):
            raise InfrastructureError(
                f"{case_id} w{worker_id}: physical/cache accounting drift")


def _validate_paired_requests(rows: Sequence[Mapping[str, Any]],
                              cases: Sequence[DiscoveryCase]) -> None:
    by_case: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_case[row["case_id"]].append(row)
    expected_ids = {case.case_id for case in cases}
    if set(by_case) != expected_ids:
        raise InfrastructureError(
            "completed rows do not cover exactly the planned cases")
    for case_id, pair in by_case.items():
        if {row["worker_id"] for row in pair} != set(WORKER_IDS) \
                or len(pair) != 2:
            raise InfrastructureError(
                f"{case_id}: not exactly one w2/w3 row")
        if len({row["request_sha256"] for row in pair}) != 1:
            raise InfrastructureError(
                f"{case_id}: w2/w3 rendered request bytes differ")
        if len({row["request_user_sha256"] for row in pair}) != 1:
            raise InfrastructureError(
                f"{case_id}: w2/w3 user-message bytes differ")
        if len({row["selected_worker_fingerprint"] for row in pair}) != 2:
            raise InfrastructureError(
                f"{case_id}: w2/w3 selector identities collapsed")


def _baseline_disposition(
        rows: Sequence[Mapping[str, Any]],
        initial_cache_state: Mapping[str, Any]) -> dict[str, Any]:
    cold_preflight = (
        initial_cache_state.get("present_count") == 0
        and initial_cache_state.get("checked_keys") == len(rows)
        and initial_cache_state.get("present_keys") == []
    )
    by_case: dict[str, dict[int, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_case[row["case_id"]][row["worker_id"]] = row
    checks = []
    passed = True
    for case_id, pair in sorted(by_case.items()):
        expected = pair[2]["expected_direction"]
        factors = pair[2]["semantic_factors"]
        expected_request = factors[
            "baseline_expected_request_sha256"]
        expected_rejection = factors["baseline_expected_rejection"]
        c2 = bool(pair[2]["semantic_correct"])
        c3 = bool(pair[3]["semantic_correct"])
        actual = (
            "both" if c2 and c3 else
            "w2" if c2 else
            "w3" if c3 else
            "neither"
        )
        direction_pass = (
            actual == expected
            or expected == "w2_legal_semantic_w3"
            and actual == "w2"
            and pair[3]["parse_status"] == "legal"
            and pair[3]["status"] == "success"
            and not pair[3]["semantic_correct"]
        )
        identity_pass = all(
            row["request_sha256"] == expected_request
            and row["physical_generation"]
            for row in pair.values()
        ) and cold_preflight
        rejection_pass = all(
            pair[worker_id]["rejection_code"]
            == expected_rejection[str(worker_id)]
            for worker_id in WORKER_IDS
        )
        protocol_pass = (
            expected not in {"w2", "w3"}
            or (
                pair[3 if expected == "w2" else 2]["failure_class"]
                == "parse/grammar"
            )
        )
        row_pass = (
            direction_pass and identity_pass and rejection_pass
            and protocol_pass
        )
        checks.append({
            "case_id": case_id,
            "expected": expected,
            "actual": actual,
            "w2_failure_class": pair[2]["failure_class"],
            "w3_failure_class": pair[3]["failure_class"],
            "direction_pass": direction_pass,
            "identity_and_cold_call_pass": identity_pass,
            "rejection_pass": rejection_pass,
            "protocol_class_pass": protocol_pass,
            "pass": row_pass,
        })
        passed = passed and row_pass
    return {
        "passed": passed,
        "initial_cache_cold": cold_preflight,
        "checks": checks,
    }


def execute_run(out_dir: Path, latents: Sequence[DiscoveryLatent],
                cases: Sequence[DiscoveryCase], purpose: str,
                resume: bool = False,
                semantic_router: Mapping[str, int] | None = None,
                renderer_router: Mapping[str, int] | None = None
                ) -> dict[str, Any]:
    """Execute or resume one append-only frozen-treatment run."""
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    latents_path = out_dir / "latents.jsonl"
    cases_path = out_dir / "cases.jsonl"
    calls_path = out_dir / "calls.jsonl"
    compact_path = out_dir / "compact_rows.jsonl"
    summary_path = out_dir / "summary.json"
    if resume and not manifest_path.exists():
        raise InfrastructureError(
            "--resume requires an existing incomplete manifest")

    if len(cases) * len(WORKER_IDS) > MAX_PHYSICAL_GENERATIONS:
        raise InfrastructureError("one run exceeds the physical-call cap")
    if len({case.case_id for case in cases}) != len(cases):
        raise InfrastructureError("duplicate planned case identity")
    for case in cases:
        validate_reference_agreement(case)
    for latent in latents:
        validate_discovery_latent(latent)

    latent_rows = [_latent_record(latent) for latent in latents]
    case_rows = [_case_record(case) for case in cases]
    latent_bytes = b"".join(_json_bytes(row) for row in latent_rows)
    case_bytes = b"".join(_json_bytes(row) for row in case_rows)
    latent_sha = _sha256_bytes(latent_bytes)
    cases_sha = _sha256_bytes(case_bytes)
    run_spec = _generation_declaration(latents, cases)
    conditions = {case.condition for case in cases}
    if semantic_router is None:
        if run_spec["kind"] == "retained_baseline":
            semantic_router = {
                case.condition: (
                    3 if case.expected_direction == "w3" else 2)
                for case in cases
            }
        else:
            semantic_router = {
                condition: DEFAULT_SEMANTIC_ROUTER[condition]
                for condition in conditions
            }
    frozen_semantic_router = _validate_router(
        semantic_router, conditions, "semantic_router")
    frozen_renderer_router = None
    if renderer_router is not None:
        frozen_renderer_router = _validate_router(
            renderer_router, {case.renderer for case in cases},
            "renderer_router")
    run_spec["semantic_router"] = frozen_semantic_router
    run_spec["renderer_router"] = frozen_renderer_router
    source_digests = _source_digests()
    planned_calls = len(cases) * len(WORKER_IDS)
    budget = _budget_preflight(
        out_dir, run_spec, purpose, planned_calls, resume)

    own_artifacts = (
        manifest_path, latents_path, cases_path, calls_path,
        compact_path, summary_path,
    )
    if manifest_path.exists():
        manifest = _read_json(manifest_path)
        if not resume:
            raise InfrastructureError(
                f"{out_dir} already has a manifest; pass --resume only "
                "for an incomplete matching run")
        if manifest["status"] == "complete":
            raise InfrastructureError(f"{out_dir} is already complete")
        expected_manifest = {
            "purpose": purpose,
            "run_spec": run_spec,
            "latents_sha256": latent_sha,
            "cases_sha256": cases_sha,
            "source_sha256": source_digests,
        }
        for field, expected in expected_manifest.items():
            if manifest.get(field) != expected:
                raise InfrastructureError(
                    f"resume manifest {field} does not match")
        if not latents_path.exists() or not cases_path.exists() \
                or _sha256_bytes(latents_path.read_bytes()) != latent_sha \
                or _sha256_bytes(cases_path.read_bytes()) != cases_sha:
            raise InfrastructureError(
                "resume latent/case files do not match manifest")
    else:
        stale = [str(path) for path in own_artifacts if path.exists()]
        if stale:
            raise InfrastructureError(
                f"new run refuses pre-existing artifacts: {stale}")
        _write_jsonl(latents_path, latent_rows)
        _write_jsonl(cases_path, case_rows)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": out_dir.name,
            "purpose": purpose,
            "status": "running",
            "started_utc": _utc_now(),
            "git": _git_info(),
            "source_sha256": source_digests,
            "generator_version": GENERATOR_VERSION,
            "scorer_version": SCORER_VERSION,
            "task_cell": CELL_ID,
            "visibility": "private",
            "workers": list(WORKER_IDS),
            "run_spec": run_spec,
            "budget_preflight": budget,
            "planned_cases": len(cases),
            "planned_calls": planned_calls,
            "latents_sha256": latent_sha,
            "cases_sha256": cases_sha,
            "sessions": [],
            "raw_locations": {
                "latents": str(latents_path),
                "cases": str(cases_path),
                "calls": str(calls_path),
            },
        }
        _write_json(manifest_path, manifest)

    wall_start = time.monotonic()
    runtime = _build_runtime(out_dir)
    checkpoint_report: list[dict[str, Any]] = []
    session = {
        "started_utc": _utc_now(),
        "resume": resume,
        "preexisting_rows": 0,
        "status": "running",
    }
    try:
        _validate_runtime_identity(runtime)
        _preflight_rendered_requests(runtime, cases)
        runtime_info = _runtime_manifest(runtime)
        environment = worker_eval.environment_versions()
        if "runtime" in manifest and manifest["runtime"] != runtime_info:
            raise InfrastructureError("resume runtime identity drift")
        if "environment" in manifest \
                and manifest["environment"] != environment:
            raise InfrastructureError("resume environment identity drift")
        manifest.setdefault("runtime", runtime_info)
        manifest.setdefault("environment", environment)

        existing = _read_jsonl(calls_path)
        if "initial_cache_state" not in manifest:
            if existing:
                raise InfrastructureError(
                    "rows exist without initial cache-state evidence")
            manifest["initial_cache_state"] = _initial_cache_state(
                runtime, cases)
        initial_present_keys = _validate_initial_cache_state(
            manifest["initial_cache_state"], cases)
        if purpose == "known-support baseline" and initial_present_keys:
            raise InfrastructureError(
                "known-support baseline was not cold before its first call")

        _validate_recorded_rows(existing, cases, runtime)
        done_keys = {
            (row["case_id"], row["worker_id"]) for row in existing}
        session["preexisting_rows"] = len(existing)
        manifest["sessions"].append(session)
        _write_json(manifest_path, manifest)

        prior_gpu = float(budget["prior_gpu_seconds"])
        recorded_gpu = sum(
            float(row["elapsed_seconds"]) for row in existing
            if row["physical_generation"]
            and not row.get("recovered_cache_generation", False)
        )
        generated_before = runtime.pool.singleton_generations
        appended_uncached = 0
        with calls_path.open("ab") as handle:
            for worker_id in WORKER_IDS:
                for case in cases:
                    key = (case.case_id, worker_id)
                    if key in done_keys:
                        continue
                    if prior_gpu + recorded_gpu >= MAX_GPU_SECONDS:
                        raise InfrastructureError(
                            "cumulative GPU-hour cap reached during run")
                    started = time.monotonic()
                    (record,) = runtime.worker_call_batch(
                        worker_id, [case.user_message])
                    elapsed = time.monotonic() - started
                    if not record.cache_hit:
                        appended_uncached += 1
                        recorded_gpu += elapsed
                    if record.selected_worker_fp != \
                            runtime.worker_fingerprints[worker_id]:
                        raise InfrastructureError(
                            f"{case.case_id}: producer worker fp mismatch")
                    if record.runtime_fingerprint != \
                            runtime.runtime_profile_fingerprint:
                        raise InfrastructureError(
                            f"{case.case_id}: producer runtime fp mismatch")
                    result = contract.run_worker_output(
                        2, record.completion, case.binding())
                    key_was_initially_present = (
                        _call_key(case.case_id, worker_id)
                        in initial_present_keys
                    )
                    recovered_generation = (
                        resume and record.cache_hit
                        and not key_was_initially_present
                    )
                    if not resume and record.cache_hit != \
                            key_was_initially_present:
                        raise InfrastructureError(
                            f"{case.case_id} w{worker_id}: cache state "
                            "changed after frozen preflight")
                    row = _raw_call_row(
                        case, worker_id, record, result, elapsed,
                        recovered_cache_generation=recovered_generation,
                    )
                    _append_jsonl(handle, row)
                    done_keys.add(key)
        observed_singletons = (
            runtime.pool.singleton_generations - generated_before)
        if observed_singletons != appended_uncached:
            raise InfrastructureError(
                "pool singleton count disagrees with uncached rows")
        checkpoint_report = runtime.pool.checkpoint_report()
        session.update({
            "status": "complete",
            "completed_utc": _utc_now(),
            "wall_seconds": time.monotonic() - wall_start,
            "physical_singletons_observed": observed_singletons,
        })
        # Persist the completed generation session before post-processing.
        # A later scoring or artifact error must not turn completed GPU work
        # into an apparently live session whose time is lost on resume.
        _write_json(manifest_path, manifest)
    except BaseException:
        session.update({
            "status": "interrupted",
            "ended_utc": _utc_now(),
            "wall_seconds": time.monotonic() - wall_start,
        })
        _write_json(manifest_path, manifest)
        raise
    finally:
        runtime.close()

    rows = _read_jsonl(calls_path)
    checkpoint_report = _merge_checkpoint_evidence(
        checkpoint_report, rows)
    # Runtime is closed but its immutable provenance and tokenizers are no
    # longer needed: all row-level checks ran before close, then pairing is
    # checked over the complete denominator here.
    _validate_paired_requests(rows, cases)
    compact = [_compact_call_row(row) for row in rows]
    _write_jsonl(compact_path, compact)
    summary = summarize_rows(
        rows, frozen_semantic_router, frozen_renderer_router)
    if purpose == "known-support baseline":
        baseline = _baseline_disposition(
            rows, manifest["initial_cache_state"])
        summary["baseline"] = baseline
        both_checkpoints_loaded = _checkpoint_report_identity(
            checkpoint_report, require_loaded=True)
        summary["baseline"]["both_checkpoints_loaded"] = \
            both_checkpoints_loaded
        summary["baseline"]["passed"] = (
            summary["baseline"]["passed"]
            and both_checkpoints_loaded
            and len(rows) == 8
        )
        if not summary["baseline"]["passed"]:
            raise InfrastructureError(
                "known-support baseline did not reproduce expected behavior")
    _write_json(summary_path, summary)

    physical = sum(bool(row["physical_generation"]) for row in rows)
    recovered = sum(bool(row.get("recovered_cache_generation", False))
                    for row in rows)
    generation_seconds = sum(
        float(row["elapsed_seconds"]) for row in rows
        if row["physical_generation"]
        and not row.get("recovered_cache_generation", False))
    manifest.update({
        "status": "complete",
        "completed_utc": _utc_now(),
        "wall_seconds": sum(
            float(item.get("wall_seconds", 0.0))
            for item in manifest["sessions"]),
        "physical_generations": physical,
        "cache_hits": sum(bool(row["cache_hit"]) for row in rows),
        "recovered_cache_generations": recovered,
        "gpu_seconds": generation_seconds,
        "gpu_time_complete": recovered == 0,
        "gpu_time_method": (
            "sum of wall durations for physical singleton calls on an "
            "otherwise idle exclusive RTX 4090; includes model first-load"
        ),
        "checkpoint_report": checkpoint_report,
        "artifacts": {
            "latents_sha256": _sha256_bytes(latents_path.read_bytes()),
            "cases_sha256": _sha256_bytes(cases_path.read_bytes()),
            "calls_sha256": _sha256_bytes(calls_path.read_bytes()),
            "compact_rows_sha256":
                _sha256_bytes(compact_path.read_bytes()),
            "summary_sha256": _sha256_bytes(summary_path.read_bytes()),
        },
    })
    _write_json(manifest_path, manifest)
    return manifest


def _outcome(c2: bool, c3: bool) -> str:
    if c2 and c3:
        return "both_correct"
    if c2:
        return "only_w2_correct"
    if c3:
        return "only_w3_correct"
    return "neither_correct"


def _paired_observations(
        rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_case: dict[str, dict[int, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        worker_id = int(row["worker_id"])
        if worker_id not in WORKER_IDS:
            raise InfrastructureError(
                f"summary received non-Code worker {worker_id}")
        if worker_id in by_case[row["case_id"]]:
            raise InfrastructureError(
                f"duplicate summary row {row['case_id']} w{worker_id}")
        by_case[row["case_id"]][worker_id] = row
    observations = []
    for case_id, pair in sorted(by_case.items()):
        if set(pair) != set(WORKER_IDS):
            raise InfrastructureError(
                f"{case_id}: summary pair has workers {sorted(pair)}")
        left, right = pair[2], pair[3]
        for field in (
                "strategy_id", "strategy_revision", "split", "namespace",
                "latent_id", "paired_latent_id", "latent_index",
                "renderer", "wording_family", "condition", "target_node",
                "target_scope", "request_sha256", "reference_target"):
            if left[field] != right[field]:
                raise InfrastructureError(
                    f"{case_id}: paired {field} differs")
        c2 = bool(left["semantic_correct"])
        c3 = bool(right["semantic_correct"])
        observations.append({
            "case_id": case_id,
            "strategy_id": left["strategy_id"],
            "strategy_revision": left["strategy_revision"],
            "split": left["split"],
            "namespace": left["namespace"],
            "latent_id": left["latent_id"],
            "paired_latent_id": left["paired_latent_id"],
            "latent_index": left["latent_index"],
            "renderer": left["renderer"],
            "wording_family": left["wording_family"],
            "condition": left["condition"],
            "target_node": left["target_node"],
            "target_scope": left["target_scope"],
            "semantic_factors": left["semantic_factors"],
            "request_sha256": left["request_sha256"],
            "request_bytes": len(left["request_text"].encode("utf-8")),
            "w2_correct": c2,
            "w3_correct": c3,
            "outcome": _outcome(c2, c3),
            "w2_syntax_failed": left["parse_status"] == "failed",
            "w3_syntax_failed": right["parse_status"] == "failed",
            "w2_parse_protocol_failed": left["failure_class"] in {
                "parse/grammar", "resource/identifier protocol"},
            "w3_parse_protocol_failed": right["failure_class"] in {
                "parse/grammar", "resource/identifier protocol"},
            "w2_typed_tool_rejected": (
                left["status"] == "typed_failure"
                and left["parse_status"] == "legal"),
            "w3_typed_tool_rejected": (
                right["status"] == "typed_failure"
                and right["parse_status"] == "legal"),
            "w2_legal_semantic_failed": (
                left["status"] == "success" and not c2),
            "w3_legal_semantic_failed": (
                right["status"] == "success" and not c3),
            "w2_failure_class": left["failure_class"],
            "w3_failure_class": right["failure_class"],
        })
    return observations


def _matrix_entry(observations: Sequence[Mapping[str, Any]],
                  key: str) -> dict[str, Any]:
    counts = Counter(obs["outcome"] for obs in observations)
    n = len(observations)
    return {
        "key": key,
        "rendered_observations": n,
        "independent_latents": len({
            obs["paired_latent_id"] for obs in observations}),
        "both_correct": counts["both_correct"],
        "only_w2_correct": counts["only_w2_correct"],
        "only_w3_correct": counts["only_w3_correct"],
        "neither_correct": counts["neither_correct"],
        "w2_correct": sum(bool(obs["w2_correct"])
                          for obs in observations),
        "w3_correct": sum(bool(obs["w3_correct"])
                          for obs in observations),
        "w2_accuracy": (
            sum(bool(obs["w2_correct"]) for obs in observations) / n
            if n else None
        ),
        "w3_accuracy": (
            sum(bool(obs["w3_correct"]) for obs in observations) / n
            if n else None
        ),
        "w2_syntax_failures": sum(
            bool(obs["w2_syntax_failed"]) for obs in observations),
        "w3_syntax_failures": sum(
            bool(obs["w3_syntax_failed"]) for obs in observations),
        "w2_parse_protocol_failures": sum(
            bool(obs["w2_parse_protocol_failed"])
            for obs in observations),
        "w3_parse_protocol_failures": sum(
            bool(obs["w3_parse_protocol_failed"])
            for obs in observations),
        "w2_typed_tool_rejections": sum(
            bool(obs["w2_typed_tool_rejected"])
            for obs in observations),
        "w3_typed_tool_rejections": sum(
            bool(obs["w3_typed_tool_rejected"])
            for obs in observations),
        "w2_legal_semantic_failures": sum(
            bool(obs["w2_legal_semantic_failed"])
            for obs in observations),
        "w3_legal_semantic_failures": sum(
            bool(obs["w3_legal_semantic_failed"])
            for obs in observations),
    }


def _renderer_stability(
        observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for obs in observations:
        groups[(obs["paired_latent_id"], obs["condition"])].append(obs)
    stable = Counter()
    strict = Counter()
    reversals = []
    detail = []
    for (latent, condition), group in sorted(groups.items()):
        directions = [
            "w2" if obs["outcome"] == "only_w2_correct"
            else "w3" if obs["outcome"] == "only_w3_correct"
            else "tie"
            for obs in group
        ]
        c2 = directions.count("w2")
        c3 = directions.count("w3")
        if c2 >= 2 and c3 == 0:
            stable["w2"] += 1
            direction = "w2"
        elif c3 >= 2 and c2 == 0:
            stable["w3"] += 1
            direction = "w3"
        else:
            direction = None
        if len(group) == 3 and c2 == 3:
            strict["w2"] += 1
        if len(group) == 3 and c3 == 3:
            strict["w3"] += 1
        reversal = c2 > 0 and c3 > 0
        if reversal:
            reversals.append({
                "paired_latent_id": latent,
                "condition": condition,
                "by_renderer": {
                    obs["renderer"]: (
                        "w2" if obs["outcome"] == "only_w2_correct"
                        else "w3" if obs["outcome"] == "only_w3_correct"
                        else "tie"
                    ) for obs in group
                },
            })
        detail.append({
            "paired_latent_id": latent,
            "condition": condition,
            "renderers": len(group),
            "w2_unique_renderers": c2,
            "w3_unique_renderers": c3,
            "renderer_stable_direction": direction,
            "renderer_reversal": reversal,
        })
    paired_direction_support: dict[str, set[str]] = defaultdict(set)
    for row in detail:
        if row["renderer_stable_direction"]:
            paired_direction_support[row["paired_latent_id"]].add(
                row["renderer_stable_direction"])
    target_count = len(groups)
    paired_count = len({latent for latent, _condition in groups})
    return {
        "independent_latent_targets": len(groups),
        "renderer_stable_unique_win_targets": dict(stable),
        "renderer_stable_unique_win_mass": {
            "w2": stable["w2"] / target_count if target_count else 0.0,
            "w3": stable["w3"] / target_count if target_count else 0.0,
        },
        "strict_all_three_unique_win_targets": dict(strict),
        "renderer_reversal_count": len(reversals),
        "renderer_reversals": reversals,
        "paired_latents_with_stable_w2_and_w3_conditions": sum(
            directions == {"w2", "w3"}
            for directions in paired_direction_support.values()),
        "paired_latent_bidirectional_stable_rate": (
            sum(directions == {"w2", "w3"}
                for directions in paired_direction_support.values())
            / paired_count if paired_count else 0.0
        ),
        "detail": detail,
    }


def _independent_latent_metrics(
        observations: Sequence[Mapping[str, Any]],
        semantic_router: Mapping[str, int]) -> dict[str, Any]:
    """Collapse renderer replicas before computing target-level metrics."""
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for obs in observations:
        groups[(obs["paired_latent_id"], obs["condition"])].append(obs)
    units = []
    for (latent_id, condition), group in sorted(groups.items()):
        if len({obs["renderer"] for obs in group}) != len(group):
            raise InfrastructureError(
                f"{latent_id}|{condition}: duplicate renderer replica")
        n_renderers = len(group)
        w2_fraction = sum(
            bool(obs["w2_correct"]) for obs in group) / n_renderers
        w3_fraction = sum(
            bool(obs["w3_correct"]) for obs in group) / n_renderers
        w2_majority = w2_fraction > 0.5
        w3_majority = w3_fraction > 0.5
        selected = semantic_router[condition]
        units.append({
            "paired_latent_id": latent_id,
            "condition": condition,
            "renderers": n_renderers,
            "w2_renderer_fraction": w2_fraction,
            "w3_renderer_fraction": w3_fraction,
            "oracle_renderer_fraction": sum(
                bool(obs["w2_correct"] or obs["w3_correct"])
                for obs in group) / n_renderers,
            "w2_majority_correct": w2_majority,
            "w3_majority_correct": w3_majority,
            "semantic_router_majority_correct": (
                w2_majority if selected == 2 else w3_majority),
            "majority_outcome": _outcome(w2_majority, w3_majority),
        })
    n = len(units)
    counts = Counter(unit["majority_outcome"] for unit in units)
    c2 = sum(unit["w2_majority_correct"] for unit in units)
    c3 = sum(unit["w3_majority_correct"] for unit in units)
    semantic = sum(
        unit["semantic_router_majority_correct"] for unit in units) / n
    oracle = sum(
        unit["w2_majority_correct"] or unit["w3_majority_correct"]
        for unit in units) / n
    best = max(c2, c3) / n
    return {
        "unit": (
            "paired latent × semantic target, renderer replicas collapsed"
        ),
        "majority_rule": (
            "worker correct on strictly more than half of renderer replicas"
        ),
        "latent_targets": n,
        "paired_latents": len({
            unit["paired_latent_id"] for unit in units}),
        "both_correct": counts["both_correct"],
        "only_w2_correct": counts["only_w2_correct"],
        "only_w3_correct": counts["only_w3_correct"],
        "neither_correct": counts["neither_correct"],
        "w2_majority_accuracy": c2 / n,
        "w3_majority_accuracy": c3 / n,
        "best_fixed_majority_accuracy": best,
        "uniform_random_majority_expected_accuracy": (c2 + c3) / (2 * n),
        "semantic_router_majority_accuracy": semantic,
        "hindsight_oracle_majority_accuracy": oracle,
        "oracle_minus_best_fixed_majority": oracle - best,
        "semantic_router_minus_best_fixed_majority": semantic - best,
        "mean_renderer_accuracy": {
            "w2": sum(unit["w2_renderer_fraction"]
                      for unit in units) / n,
            "w3": sum(unit["w3_renderer_fraction"]
                      for unit in units) / n,
            "oracle": sum(unit["oracle_renderer_fraction"]
                          for unit in units) / n,
        },
        "detail": units,
    }


def _fit_renderer_router(
        observations: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    router = {}
    for renderer_id in sorted({obs["renderer"] for obs in observations}):
        subset = [obs for obs in observations
                  if obs["renderer"] == renderer_id]
        c2 = sum(bool(obs["w2_correct"]) for obs in subset)
        c3 = sum(bool(obs["w3_correct"]) for obs in subset)
        router[renderer_id] = 3 if c3 > c2 else 2
    return router


def _router_accuracy(observations: Sequence[Mapping[str, Any]],
                     router: Mapping[str, int],
                     field: str) -> float:
    if not observations:
        return 0.0
    levels = {str(obs[field]) for obs in observations}
    if set(router) != levels:
        raise InfrastructureError(
            f"{field} router keys {sorted(router)} != {sorted(levels)}")
    if any(
            not isinstance(worker, int) or isinstance(worker, bool)
            or worker not in WORKER_IDS
            for worker in router.values()):
        raise InfrastructureError(f"{field} router has invalid worker")
    correct = 0
    for obs in observations:
        selected = router[str(obs[field])]
        correct += int(bool(obs[f"w{selected}_correct"]))
    return correct / len(observations)


def _fit_text_length_control(
        observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not observations:
        return {"threshold_bytes": None, "short_worker": 2,
                "long_worker": 2, "accuracy": 0.0}
    values = sorted({int(obs["request_bytes"]) for obs in observations})
    candidates = [values[0] - 1, *values]
    best: tuple[float, int, int, int] | None = None
    for threshold in candidates:
        for short_worker, long_worker in ((2, 3), (3, 2), (2, 2), (3, 3)):
            correct = 0
            for obs in observations:
                worker = (
                    short_worker if obs["request_bytes"] <= threshold
                    else long_worker
                )
                correct += int(bool(obs[f"w{worker}_correct"]))
            accuracy = correct / len(observations)
            candidate = (accuracy, -threshold, -short_worker, -long_worker)
            if best is None or candidate > best:
                best = candidate
                chosen = (threshold, short_worker, long_worker, accuracy)
    threshold, short_worker, long_worker, accuracy = chosen
    return {
        "fit_scope": "optimistic in-sample diagnostic",
        "threshold_bytes": threshold,
        "short_worker": short_worker,
        "long_worker": long_worker,
        "accuracy": accuracy,
    }


def summarize_rows(
        rows: Sequence[Mapping[str, Any]],
        semantic_router: Mapping[str, int],
        renderer_router: Mapping[str, int] | None = None,
        ) -> dict[str, Any]:
    observations = _paired_observations(rows)
    if not observations:
        raise InfrastructureError("cannot summarize an empty run")
    n = len(observations)
    c2 = sum(bool(obs["w2_correct"]) for obs in observations)
    c3 = sum(bool(obs["w3_correct"]) for obs in observations)
    oracle = sum(
        bool(obs["w2_correct"] or obs["w3_correct"])
        for obs in observations) / n
    best_fixed_worker = 3 if c3 > c2 else 2
    best_fixed = max(c2, c3) / n
    random_accuracy = (c2 + c3) / (2 * n)
    semantic_accuracy = _router_accuracy(
        observations, semantic_router, "condition")
    effective_renderer_router = (
        dict(renderer_router)
        if renderer_router is not None
        else _fit_renderer_router(observations)
    )
    renderer_accuracy = _router_accuracy(
        observations, effective_renderer_router, "renderer")

    matrix_groups: dict[tuple[str, str, str],
                        list[Mapping[str, Any]]] = defaultdict(list)
    condition_groups: dict[tuple[str, str],
                           list[Mapping[str, Any]]] = defaultdict(list)
    for obs in observations:
        matrix_groups[(
            obs["strategy_id"], obs["condition"], obs["renderer"]
        )].append(obs)
        condition_groups[(
            obs["strategy_id"], obs["condition"]
        )].append(obs)
    matrices = [
        _matrix_entry(
            group,
            "|".join(key),
        )
        for key, group in sorted(matrix_groups.items())
    ]
    condition_matrices = [
        _matrix_entry(group, "|".join(key))
        for key, group in sorted(condition_groups.items())
    ]
    overall = _matrix_entry(observations, "overall")
    stability = _renderer_stability(observations)
    independent = _independent_latent_metrics(
        observations, semantic_router)
    payoff_distinct = sum(
        obs["w2_correct"] != obs["w3_correct"]
        for obs in observations)
    oracle_gain = oracle - best_fixed
    semantic_gain = semantic_accuracy - best_fixed
    taxonomy = {
        f"w{worker_id}": dict(Counter(
            obs[f"w{worker_id}_failure_class"]
            for obs in observations
            if obs[f"w{worker_id}_failure_class"] is not None
        ))
        for worker_id in WORKER_IDS
    }
    per_target_renderer_means = []
    target_groups: dict[tuple[str, str],
                        list[Mapping[str, Any]]] = defaultdict(list)
    for obs in observations:
        target_groups[(
            obs["paired_latent_id"], obs["condition"]
        )].append(obs)
    for key, group in target_groups.items():
        per_target_renderer_means.append({
            "paired_latent_id": key[0],
            "condition": key[1],
            "renderers": len(group),
            "w2_mean_renderer_accuracy": sum(
                bool(obs["w2_correct"]) for obs in group) / len(group),
            "w3_mean_renderer_accuracy": sum(
                bool(obs["w3_correct"]) for obs in group) / len(group),
            "w2_all_renderers_correct": all(
                bool(obs["w2_correct"]) for obs in group),
            "w3_all_renderers_correct": all(
                bool(obs["w3_correct"]) for obs in group),
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "scorer_version": SCORER_VERSION,
        "rendered_observation_metrics": overall,
        "independent_latent_metrics": independent,
        "independent_support": {
            "paired_latents": len({
                obs["paired_latent_id"] for obs in observations}),
            "latent_targets": len(target_groups),
            "per_latent_target_renderer_means":
                per_target_renderer_means,
        },
        "matrices_by_strategy_condition_renderer": matrices,
        "matrices_by_strategy_condition": condition_matrices,
        "failure_taxonomy": taxonomy,
        "routing": {
            "best_fixed_worker": best_fixed_worker,
            "best_fixed_accuracy": best_fixed,
            "uniform_random_worker_expected_accuracy": random_accuracy,
            "semantic_router": dict(semantic_router),
            "semantic_router_accuracy": semantic_accuracy,
            "renderer_only_router": effective_renderer_router,
            "renderer_only_router_scope": (
                "externally supplied"
                if renderer_router is not None
                else "optimistic in-sample diagnostic"
            ),
            "renderer_only_router_accuracy": renderer_accuracy,
            "text_length_control": _fit_text_length_control(observations),
            "hindsight_per_observation_oracle_accuracy": oracle,
            "oracle_minus_best_fixed": oracle_gain,
            "semantic_router_minus_best_fixed": semantic_gain,
            "oracle_gain_captured_by_semantic_router": (
                semantic_gain / oracle_gain if oracle_gain > 0 else None
            ),
        },
        "renderer_stability": stability,
        "group_of_eight_projection": {
            "payoff_distinct_observations": payoff_distinct,
            "payoff_distinct_rate": payoff_distinct / n,
            "iid_uniform_worker_sampling_nonzero_diversity_probability":
                (payoff_distinct / n) * (1.0 - 2.0 * (0.5 ** 8)),
            "forced_four_w2_four_w3_nonzero_diversity_probability":
                payoff_distinct / n,
            "assumption": (
                "binary semantic-correctness reward and initially balanced "
                "w2/w3 sampling; diagnostic projection only"
            ),
        },
    }


def _summary_markdown(summary: Mapping[str, Any]) -> str:
    overall = summary["rendered_observation_metrics"]
    routing = summary["routing"]
    lines = [
        "# Q3 discovery run summary",
        "",
        "## Overall",
        "",
        "| n | both | only w2 | only w3 | neither | w2 acc | w3 acc |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {overall['rendered_observations']} | "
            f"{overall['both_correct']} | {overall['only_w2_correct']} | "
            f"{overall['only_w3_correct']} | {overall['neither_correct']} | "
            f"{overall['w2_accuracy']:.3f} | "
            f"{overall['w3_accuracy']:.3f} |"
        ),
        "",
        "## Strategy × condition × renderer",
        "",
        "| stratum | n | both | only w2 | only w3 | neither | w2 acc | w3 acc |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["matrices_by_strategy_condition_renderer"]:
        lines.append(
            f"| {row['key']} | {row['rendered_observations']} | "
            f"{row['both_correct']} | {row['only_w2_correct']} | "
            f"{row['only_w3_correct']} | {row['neither_correct']} | "
            f"{row['w2_accuracy']:.3f} | {row['w3_accuracy']:.3f} |"
        )
    lines += [
        "",
        "## Routers",
        "",
        f"- Best fixed: w{routing['best_fixed_worker']} at "
        f"{routing['best_fixed_accuracy']:.3f}",
        f"- Uniform random expected: "
        f"{routing['uniform_random_worker_expected_accuracy']:.3f}",
        f"- Semantic router: {routing['semantic_router_accuracy']:.3f}",
        f"- Renderer-only router: "
        f"{routing['renderer_only_router_accuracy']:.3f}",
        f"- Hindsight oracle: "
        f"{routing['hindsight_per_observation_oracle_accuracy']:.3f}",
        "",
    ]
    return "\n".join(lines)


def _case_from_record(row: Mapping[str, Any]) -> DiscoveryCase:
    values = dict(row)
    values["sequence"] = tuple(values["sequence"])
    values["previous_results"] = {
        int(key): value
        for key, value in values["previous_results"].items()
    }
    return DiscoveryCase(**values)


def verify_run(run_dir: Path) -> dict[str, Any]:
    """Re-execute pure scoring and rederive compact artifacts from raw rows."""
    run_dir = run_dir.resolve()
    manifest = _read_json(run_dir / "manifest.json")
    if manifest["status"] != "complete":
        raise InfrastructureError(f"{run_dir} is not complete")
    if manifest.get("source_sha256") != _source_digests():
        raise InfrastructureError("current scorer/generator source drift")
    latents_path = run_dir / "latents.jsonl"
    cases_path = run_dir / "cases.jsonl"
    calls_path = run_dir / "calls.jsonl"
    compact_path = run_dir / "compact_rows.jsonl"
    summary_path = run_dir / "summary.json"
    for path in (
            latents_path, cases_path, calls_path, compact_path, summary_path):
        if not path.exists():
            raise InfrastructureError(f"missing run artifact {path}")
    if _sha256_bytes(latents_path.read_bytes()) != \
            manifest["latents_sha256"] \
            or _sha256_bytes(cases_path.read_bytes()) != \
            manifest["cases_sha256"]:
        raise InfrastructureError("latent/case file hash drift")

    run_spec = manifest["run_spec"]
    if run_spec["kind"] == "retained_baseline":
        regenerated_latents: list[DiscoveryLatent] = []
        regenerated_cases = build_baseline_cases()
    else:
        regenerated_latents, regenerated_cases = build_strategy_cases(
            run_spec["strategy_id"],
            run_spec["strategy_revision"],
            run_spec["namespace"],
            run_spec["latent_start"],
            run_spec["latent_count"],
            tuple(run_spec["renderers"]),
            run_spec["wording_family"],
            tuple(run_spec["conditions"]),
        )
    regenerated_latent_bytes = b"".join(
        _json_bytes(_latent_record(latent))
        for latent in regenerated_latents)
    regenerated_case_bytes = b"".join(
        _json_bytes(_case_record(case))
        for case in regenerated_cases)
    if regenerated_latent_bytes != latents_path.read_bytes() \
            or regenerated_case_bytes != cases_path.read_bytes():
        raise InfrastructureError(
            "persisted generation does not regenerate from run_spec")
    cases = regenerated_cases
    rows = _read_jsonl(run_dir / "calls.jsonl")
    _validate_initial_cache_state(
        manifest["initial_cache_state"], cases)
    runtime = _build_runtime(run_dir)
    try:
        _validate_runtime_identity(runtime)
        if _runtime_manifest(runtime) != manifest["runtime"]:
            raise InfrastructureError("runtime manifest does not rederive")
        _preflight_rendered_requests(runtime, cases)
        _validate_recorded_rows(rows, cases, runtime)
    finally:
        runtime.close()
    _validate_paired_requests(rows, cases)

    summary = summarize_rows(
        rows,
        run_spec["semantic_router"],
        run_spec["renderer_router"],
    )
    if manifest["purpose"] == "known-support baseline":
        summary["baseline"] = _baseline_disposition(
            rows, manifest["initial_cache_state"])
        summary["baseline"]["both_checkpoints_loaded"] = \
            _checkpoint_report_identity(
                manifest["checkpoint_report"], require_loaded=True)
        summary["baseline"]["passed"] = (
            summary["baseline"]["passed"]
            and summary["baseline"]["both_checkpoints_loaded"]
            and len(rows) == 8
        )
    compact_bytes = b"".join(
        _json_bytes(_compact_call_row(row)) for row in rows)
    summary_bytes = _json_bytes(summary)
    expected_hashes = manifest["artifacts"]
    checks = {
        "latents_sha256": _sha256_bytes(latents_path.read_bytes()),
        "cases_sha256": _sha256_bytes(cases_path.read_bytes()),
        "calls_sha256": _sha256_bytes(calls_path.read_bytes()),
        "compact_rows_sha256": _sha256_bytes(compact_bytes),
        "summary_sha256": _sha256_bytes(summary_bytes),
    }
    wrong_hashes = {
        key: (expected_hashes[key], value)
        for key, value in checks.items()
        if expected_hashes[key] != value
    }
    if wrong_hashes:
        raise InfrastructureError(
            f"{run_dir}: artifact hash drift {wrong_hashes}")
    if compact_path.read_bytes() != compact_bytes:
        raise InfrastructureError("on-disk compact rows do not rederive")
    if summary_path.read_bytes() != summary_bytes:
        raise InfrastructureError("on-disk summary does not rederive")
    physical = sum(bool(row["physical_generation"]) for row in rows)
    recovered = sum(bool(row.get("recovered_cache_generation", False))
                    for row in rows)
    gpu_seconds = sum(
        float(row["elapsed_seconds"]) for row in rows
        if row["physical_generation"]
        and not row.get("recovered_cache_generation", False))
    totals = {
        "physical_generations": physical,
        "cache_hits": sum(bool(row["cache_hit"]) for row in rows),
        "recovered_cache_generations": recovered,
        "gpu_seconds": gpu_seconds,
        "gpu_time_complete": recovered == 0,
    }
    for field, expected in totals.items():
        if manifest.get(field) != expected:
            raise InfrastructureError(f"manifest total {field} drift")
    return {
        "status": "verified",
        "run_dir": str(run_dir),
        "calls": len(rows),
        "cases": len(cases),
        "artifact_hashes": checks,
    }


def _parse_renderers(value: str) -> tuple[str, ...]:
    result = tuple(part.strip() for part in value.split(",") if part.strip())
    if not result:
        raise argparse.ArgumentTypeError("at least one renderer is required")
    if len(set(result)) != len(result) \
            or any(renderer not in RENDERERS for renderer in result):
        raise argparse.ArgumentTypeError(
            f"renderers must be unique comma-separated members of "
            f"{','.join(RENDERERS)}")
    return result


def _parse_conditions(value: str) -> tuple[str, ...]:
    result = tuple(part.strip() for part in value.split(",") if part.strip())
    if not result or len(set(result)) != len(result):
        raise argparse.ArgumentTypeError(
            "conditions must be a nonempty comma-separated unique list")
    return result


def _load_router(value: str | None,
                 default: Mapping[str, int]) -> dict[str, int]:
    if value is None:
        return dict(default)
    path = Path(value)
    payload = (
        json.loads(path.read_text(encoding="utf-8"))
        if path.exists() else json.loads(value)
    )
    if not isinstance(payload, dict) or any(
            not isinstance(worker, int) or isinstance(worker, bool)
            or worker not in WORKER_IDS
            for worker in payload.values()):
        raise ValueError("router must be an object mapping to worker 2 or 3")
    return {str(key): int(worker) for key, worker in payload.items()}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Q3 task-discovery development harness")
    sub = parser.add_subparsers(dest="command", required=True)

    baseline = sub.add_parser(
        "baseline", help="run four retained known-support checks")
    baseline.add_argument("--out-dir", type=Path, required=True)
    baseline.add_argument("--resume", action="store_true")

    run = sub.add_parser("run", help="execute a complete strategy surface")
    run.add_argument("--out-dir", type=Path, required=True)
    run.add_argument("--strategy", choices=sorted(STRATEGY_CONDITIONS),
                     required=True)
    run.add_argument("--revision", required=True)
    run.add_argument("--namespace", required=True)
    run.add_argument("--latent-start", type=int, default=0)
    run.add_argument("--latents", type=int, required=True)
    run.add_argument("--renderers", type=_parse_renderers, required=True)
    run.add_argument(
        "--conditions", type=_parse_conditions,
        help="optional ordered subset of complete strategy conditions")
    run.add_argument("--wording-family", choices=WORDING_FAMILIES,
                     default="canonical")
    run.add_argument("--purpose", default="strategy development")
    run.add_argument(
        "--semantic-router",
        help="frozen JSON object or path mapping every condition to w2/w3")
    run.add_argument(
        "--renderer-router",
        help="optional frozen JSON object or path mapping every renderer")
    run.add_argument("--resume", action="store_true")

    dry = sub.add_parser(
        "dry-run", help="generate and validate cases without model calls")
    dry.add_argument("--strategy", choices=sorted(STRATEGY_CONDITIONS),
                     required=True)
    dry.add_argument("--revision", required=True)
    dry.add_argument("--namespace", required=True)
    dry.add_argument("--latent-start", type=int, default=0)
    dry.add_argument("--latents", type=int, required=True)
    dry.add_argument("--renderers", type=_parse_renderers, required=True)
    dry.add_argument(
        "--conditions", type=_parse_conditions,
        help="optional ordered subset of complete strategy conditions")
    dry.add_argument("--wording-family", choices=WORDING_FAMILIES,
                     default="canonical")

    summarize = sub.add_parser(
        "summarize", help="rederive metrics from one raw run")
    summarize.add_argument("--run-dir", type=Path, required=True)
    summarize.add_argument(
        "--semantic-router",
        help="JSON object or path mapping condition to worker id")
    summarize.add_argument(
        "--renderer-router",
        help="JSON object or path mapping renderer to worker id")

    verify = sub.add_parser(
        "verify", help="re-score and hash-check a completed run")
    verify.add_argument("--run-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "baseline":
        manifest = execute_run(
            args.out_dir,
            [],
            build_baseline_cases(),
            "known-support baseline",
            resume=args.resume,
        )
        print(json.dumps(manifest, sort_keys=True, indent=2))
        return 0
    if args.command in {"run", "dry-run"}:
        latents, cases = build_strategy_cases(
            args.strategy,
            args.revision,
            args.namespace,
            args.latent_start,
            args.latents,
            args.renderers,
            args.wording_family,
            args.conditions,
        )
        for case in cases:
            validate_reference_agreement(case)
        if args.command == "dry-run":
            result = {
                "strategy": args.strategy,
                "revision": args.revision,
                "namespace": args.namespace,
                "latents": len(latents),
                "cases": len(cases),
                "planned_calls": len(cases) * len(WORKER_IDS),
                "conditions": list(dict.fromkeys(
                    case.condition for case in cases)),
                "renderers": list(args.renderers),
                "wording_family": args.wording_family,
                "latents_sha256": _sha256_bytes(b"".join(
                    _json_bytes(_latent_record(latent))
                    for latent in latents)),
                "cases_sha256": _sha256_bytes(b"".join(
                    _json_bytes(_case_record(case))
                    for case in cases)),
            }
            print(json.dumps(result, sort_keys=True, indent=2))
            return 0
        manifest = execute_run(
            args.out_dir,
            latents,
            cases,
            args.purpose,
            resume=args.resume,
            semantic_router=(
                _load_router(args.semantic_router, {})
                if args.semantic_router else None
            ),
            renderer_router=(
                _load_router(args.renderer_router, {})
                if args.renderer_router else None
            ),
        )
        print(json.dumps(manifest, sort_keys=True, indent=2))
        return 0
    if args.command == "summarize":
        run_dir = args.run_dir.resolve()
        rows = _read_jsonl(run_dir / "calls.jsonl")
        manifest = _read_json(run_dir / "manifest.json")
        semantic = _load_router(
            args.semantic_router,
            manifest["run_spec"]["semantic_router"])
        renderer_router = (
            _load_router(args.renderer_router, {})
            if args.renderer_router
            else manifest["run_spec"]["renderer_router"]
        )
        summary = summarize_rows(rows, semantic, renderer_router)
        if manifest["purpose"] == "known-support baseline":
            summary["baseline"] = _baseline_disposition(
                rows, manifest["initial_cache_state"])
            summary["baseline"]["both_checkpoints_loaded"] = \
                _checkpoint_report_identity(
                    manifest["checkpoint_report"], require_loaded=True)
            summary["baseline"]["passed"] = (
                summary["baseline"]["passed"]
                and summary["baseline"]["both_checkpoints_loaded"]
                and len(rows) == 8
            )
        custom = bool(args.semantic_router or args.renderer_router)
        if custom:
            tag = _sha256_bytes(_json_bytes({
                "semantic_router": semantic,
                "renderer_router": renderer_router,
            }))[:12]
            output_json = run_dir / f"derived_summary_{tag}.json"
            output_md = run_dir / f"derived_summary_{tag}.md"
            _write_json(output_json, summary)
            output_md.write_text(
                _summary_markdown(summary), encoding="utf-8")
        elif (run_dir / "summary.json").read_bytes() != \
                _json_bytes(summary):
            raise InfrastructureError(
                "frozen summary does not rederive; refusing overwrite")
        print(json.dumps(summary, sort_keys=True, indent=2))
        return 0
    if args.command == "verify":
        print(json.dumps(
            verify_run(args.run_dir), sort_keys=True, indent=2))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
