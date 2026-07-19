"""Generate the §4 byte-stability fixture: SHA-256 of every canonical
worker-request byte string — one per cell × step × access pattern, the
plural `Resources:` forms (B3/B5), and all 18 shortcut workflows × 2 calls.

Run:  uv run python -m tasks.conductor.gen_byte_fixtures
Regenerating after an intentional freeze-relevant change requires a
generator-version bump and (post-qualification) retires qualification sets.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import baselines, oracle, program, render
from .profiles import DEFAULT_PROFILE
from .resources import InstanceRegistry
from .types import CELL_IDS

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "byte_stability.json"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_fixture() -> dict[str, str]:
    fixture: dict[str, str] = {}
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
            request = render.build_worker_request(
                inst["public_prompt"], step["subtask"],
                resource_text=resource_text,
                previous_results=dict(previous)
                if step["access"] == "all" else None)
            fixture[f"{cell}:step{position}:{step['access']}"] = _sha(request)
            previous[position] = latent["node_values"][step["node"]]
        # Plural-resources forms (harness-only): B3 visible direct and B5.
        fixture[f"{cell}:B3"] = _sha(
            baselines.build_b3_request(inst, registry))
        fixture[f"{cell}:B5"] = _sha(
            baselines.build_b5_request(inst, registry)[0])

    # 18 shortcut workflows × 2 calls (fork_join, D12): request bytes are
    # keyed by (orientation, endpoint pair, call) — the endpoint pair enters
    # the canonical rendered request through the system prompt at 0B; here
    # the fixture pins (system name, user bytes) per call.
    latent = program.generate_latent("fork_join", "construction", 0,
                                     DEFAULT_PROFILE).latent
    inst = program.render_instance(latent, "resource_first", "private")
    registry = InstanceRegistry(inst["public_manifest"],
                                inst["private_registry"])
    params = latent["params"]
    endpoint_names = {0: "lookup", 1: "math", 2: "code"}
    for orientation, pair in oracle.enumerate_two_call_workflows():
        subtasks = render.two_call_subtasks(orientation, params)
        first_handle = (params["H1"] if orientation == "lookup_first"
                        else params["H2"])
        second_handle = (params["H2"] if orientation == "lookup_first"
                         else params["H1"])
        req1 = render.build_worker_request(
            inst["public_prompt"], subtasks[0],
            resource_text=registry.payload_text(first_handle))
        req2 = render.build_worker_request(
            inst["public_prompt"], subtasks[1],
            resource_text=registry.payload_text(second_handle),
            previous_results={1: latent["node_values"][
                "n1" if orientation == "lookup_first" else "n2"]})
        for call, (endpoint, req) in enumerate(
                [(pair[0], req1), (pair[1], req2)], start=1):
            key = f"two_call:{orientation}:{pair[0]}{pair[1]}:call{call}"
            fixture[key] = _sha(f"SYSTEM_{endpoint_names[endpoint].upper()}"
                                "\x00" + req)
    return fixture


def main() -> None:
    FIXTURE_PATH.parent.mkdir(exist_ok=True)
    fixture = build_fixture()
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=1, sort_keys=True)
                            + "\n")
    print(f"wrote {len(fixture)} request hashes to {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
