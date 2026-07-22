"""Generate the pool-bound rendered-request fixture (108_f finding 3).

This fixture pins the complete **frozen execution configuration** of the
106_s §4 worker pool: rev10 system prompts, the `worker-blocks-task-last-v1`
request contract, and each worker's independently pinned tokenizer/chat
template. The matrix is worker-specific — `cell × step × worker`, all four
workers per step (wrong-family renderings included: they are the §9.4
assignment-surface requests) — plus the registry-derived two-call family.

It supersedes the historical `chat_template_bytes.json`, which was
generated from `DEFAULT_RUNTIME_PROFILE` (rev9 prompts, v0 contract,
retired Coder Code checkpoint) and therefore pinned the historical, not
the frozen, configuration. `byte_stability.json` is intentionally NOT
regenerated: it is the generator/semantic-rendering regression fixture
under the v0 request layout, not the selected execution-contract fixture.

Workers 2 and 3 carry separate keys whose hashes the acceptance test
asserts equal — rendered through *independently pinned tokenizers*, that
equality is the §6.2 attribution guarantee, not a shared code path.

Run:  uv run python -m tasks.conductor.gen_chat_fixtures
"""

from __future__ import annotations

import functools
import hashlib
import json
from pathlib import Path

from . import oracle, program, render
from .profiles import DEFAULT_PROFILE
from .resources import InstanceRegistry
from .types import CELL_IDS
from .worker_eval import resolve_request_contract
from .workerpool import STAGE0_POOL_FINGERPRINT, STAGE0_WORKER_POOL

FIXTURE_PATH = (Path(__file__).parent / "fixtures"
                / "pool_rendered_requests.json")


@functools.lru_cache(maxsize=4)
def _tokenizer(model_id: str, revision: str):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(model_id, revision=revision)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _render(spec, bundle, user_message: str) -> bytes:
    """Exactly the WorkerPool.render_request convention, per worker."""
    tokenizer = _tokenizer(spec.model_id, spec.model_revision)
    text = tokenizer.apply_chat_template(
        [{"role": "system", "content": bundle.text(spec.endpoint_family)},
         {"role": "user", "content": user_message}],
        tokenize=False, add_generation_prompt=True)
    return text.encode("utf-8")


def build_fixture() -> dict[str, object]:
    from .prompts import resolve_prompts
    bundle = resolve_prompts("rev10")
    contract = resolve_request_contract(render.CONTRACT_TASK_LAST)
    fixture: dict[str, object] = {
        "pool_fingerprint": STAGE0_POOL_FINGERPRINT,
        "prompt_revision": "rev10",
        "request_contract_key": contract["key"],
        "request_contract_digest": contract["digest"],
    }
    for spec in STAGE0_WORKER_POOL:
        tokenizer = _tokenizer(spec.model_id, spec.model_revision)
        fixture[f"chat_template:{spec.name}"] = _sha(
            tokenizer.chat_template.encode("utf-8"))
        fixture[f"tokenizer:{spec.name}"] = \
            f"{spec.model_id}@{spec.model_revision}"

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
                if step["access"] == "all" else None,
                contract=render.CONTRACT_TASK_LAST)
            fixture[f"{cell}:step{position}:user"] = _sha(
                user.encode("utf-8"))
            for spec in STAGE0_WORKER_POOL:
                fixture[f"{cell}:step{position}:{spec.name}"] = _sha(
                    _render(spec, bundle, user))
            previous[position] = latent["node_values"][step["node"]]

    # Registry-derived two-call family (fork_join, D12; 106_s §6.3),
    # each call rendered through the selected worker's own tokenizer
    # and family prompt under the frozen contract.
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
            resource_text=registry.payload_text(first_handle),
            contract=render.CONTRACT_TASK_LAST)
        user2 = render.build_worker_request(
            inst["public_prompt"], subtasks[1],
            resource_text=registry.payload_text(second_handle),
            previous_results={1: latent["node_values"][
                "n1" if orientation == "lookup_first" else "n2"]},
            contract=render.CONTRACT_TASK_LAST)
        for call, (worker, user) in enumerate(
                [(pair[0], user1), (pair[1], user2)], start=1):
            spec = STAGE0_WORKER_POOL[worker]
            key = f"two_call:{orientation}:{pair[0]}{pair[1]}:call{call}"
            fixture[key] = _sha(_render(spec, bundle, user))
    return fixture


def main() -> None:
    FIXTURE_PATH.parent.mkdir(exist_ok=True)
    fixture = build_fixture()
    FIXTURE_PATH.write_text(json.dumps(fixture, indent=1, sort_keys=True)
                            + "\n")
    print(f"wrote {len(fixture)} entries to {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
