"""Generate the Stage-0B chat-template byte fixture: SHA-256 of the
**canonical rendered request bytes** (§1.5 — chat template over
(system, user)) for every cell × step × endpoint, plus the 18 fork_join
two-call shortcut workflows through their endpoint pairs.

This replaces the provisional Stage-0A request hashes as the cache-key
byte-stability target: `byte_stability.json` pins user-message bytes with
a symbolic system identity; this fixture pins the exact bytes the cache
keys on (§1.10), rendered through the pinned tokenizers of the default
runtime profile. Direct-arm (B1/B3/B4/B5) rendering runs on the policy
model outside the worker pool and is fixed at Stage 1A with `calibrate.py`;
its user bytes remain pinned by the 0A fixture.

Run:  uv run python -m tasks.conductor.gen_chat_fixtures
Regenerating after an intentional freeze-relevant change (model revision,
chat template, D16 prompt, renderer) requires the corresponding version
bump and (post-qualification) retires qualification sets.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import oracle, program, render
from .profiles import DEFAULT_PROFILE
from .resources import InstanceRegistry
from .runtime import DEFAULT_RUNTIME_PROFILE
from .types import CELL_IDS, ENDPOINT_NAMES
from .workers import WorkerPool

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "chat_template_bytes.json"


def build_fixture(pool: WorkerPool) -> dict[str, str]:
    fixture: dict[str, str] = {
        f"chat_template:{name}": pool.chat_template_sha(name)
        for name in sorted(set(ENDPOINT_NAMES.values()))}
    for cell in CELL_IDS:
        latent = program.generate_latent(cell, "construction", 0,
                                         DEFAULT_PROFILE).latent
        inst = program.render_instance(latent, "resource_first", "private")
        registry = InstanceRegistry(inst["public_manifest"],
                                    inst["private_registry"])
        steps = program.workflow_steps(latent)
        previous: dict[int, int] = {}
        for position, step in enumerate(steps, start=1):
            resource_text = (registry.payload_text(step["resource"])
                             if step["resource"] else None)
            user = render.build_worker_request(
                inst["public_prompt"], step["subtask"],
                resource_text=resource_text,
                previous_results=dict(previous)
                if step["access"] == "all" else None)
            # The Conductor may route any step to any endpoint, so the
            # rendered-bytes matrix is pinned for all three.
            for endpoint in sorted(set(ENDPOINT_NAMES.values())):
                rendered = pool.render_request(endpoint, user)
                key = f"{cell}:step{position}:{step['access']}:{endpoint}"
                fixture[key] = hashlib.sha256(rendered).hexdigest()
            previous[position] = latent["node_values"][step["node"]]

    # 18 shortcut workflows × 2 calls (fork_join, D12), now through the
    # real chat templates of the pair endpoints.
    latent = program.generate_latent("fork_join", "construction", 0,
                                     DEFAULT_PROFILE).latent
    inst = program.render_instance(latent, "resource_first", "private")
    registry = InstanceRegistry(inst["public_manifest"],
                                inst["private_registry"])
    params = latent["public_params"]
    for orientation, pair in oracle.enumerate_two_call_workflows():
        subtasks = render.two_call_subtasks(orientation, params)
        first_handle = (params["H1"] if orientation == "lookup_first"
                        else params["H2"])
        second_handle = (params["H2"] if orientation == "lookup_first"
                         else params["H1"])
        user1 = render.build_worker_request(
            inst["public_prompt"], subtasks[0],
            resource_text=registry.payload_text(first_handle))
        user2 = render.build_worker_request(
            inst["public_prompt"], subtasks[1],
            resource_text=registry.payload_text(second_handle),
            previous_results={1: latent["node_values"][
                "n1" if orientation == "lookup_first" else "n2"]})
        for call, (endpoint, user) in enumerate(
                [(pair[0], user1), (pair[1], user2)], start=1):
            rendered = pool.render_request(ENDPOINT_NAMES[endpoint], user)
            key = f"two_call:{orientation}:{pair[0]}{pair[1]}:call{call}"
            fixture[key] = hashlib.sha256(rendered).hexdigest()
    return fixture


def main() -> None:
    pool = WorkerPool(DEFAULT_RUNTIME_PROFILE, device="cpu")
    FIXTURE_PATH.parent.mkdir(exist_ok=True)
    fixture = build_fixture(pool)
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=1, sort_keys=True)
                            + "\n")
    print(f"wrote {len(fixture)} rendered-request hashes to {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
