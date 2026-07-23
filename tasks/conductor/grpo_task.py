"""Stage-0C Conductor task layer — 106_s §§10.1, 10.3 (unit 4).

Exactly ONE scalar task reward implements the frozen ladder through the
trainer-facing callable: malformed action string → 0.0; schema-valid
action whose workflow fails in the world → 0.5; correct terminal → 1.0.
The repository's generic `format_reward` is deliberately NOT added — a
second weighted reward would change the relative advantages between
malformed actions, world failures and correct executions. Action parse
rate is telemetry, derived from the persisted action trace.

In `precomputed_surface` mode every schema-valid sampled action MUST
have an outcome row: a missing row, stale pool hash or partial surface
is an infrastructure abort, never a reward (106_s §10.3). The smoke
dataset is the frozen 36-group schedule over the §9.4 support — each of
the 18 observations exactly twice, in the recorded deterministic order
(declaration order, two rounds); stochastic resampling cannot replace
it because the dataset is materialized in order and shuffling is
disabled at the trainer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from . import parser, program
from .parser import ActionSchemaError
from .payoff_support import load_declaration, support_observations
from .policy import policy_messages
from .types import InfrastructureError

WORKER_OUTCOME_MODES = ("precomputed_surface", "live_singleton")


def smoke_schedule() -> list[str]:
    """The frozen 36-group order: declaration order, two rounds
    (recorded, deterministic; equal support for every cell and
    renderer, nonzero atomic/two-step/fork coverage per round)."""
    declared = [obs["observation_id"]
                for obs in load_declaration()["observations"]]
    return declared + declared


def build_smoke_rows() -> list[dict[str, Any]]:
    """One dataset row per scheduled prompt group, in schedule order.
    Rows carry the meta the reward needs: observation id, the
    positional→semantic node order, and the step count."""
    by_id = {obs["observation_id"]: obs for obs in support_observations()}
    rows = []
    for observation_id in smoke_schedule():
        obs = by_id[observation_id]
        latent = obs["latent"]
        steps = [{"subtask": s["subtask"], "resource": s["resource"],
                  "access": s["access"]}
                 for s in program.workflow_steps(latent)]
        rows.append({
            "prompt": policy_messages(obs["instance"], steps),
            "observation_id": observation_id,
            "cell_id": obs["cell_id"],
            "num_steps": len(steps),
            # JSON-encoded to survive Dataset column typing untouched.
            "positions": json.dumps(
                latent["reference_program"]["positions"]),
        })
    return rows


def positional_to_semantic(positional: list[int],
                           positions: list[str]) -> tuple[int, ...]:
    """Invert the frozen semantic_to_positional mapping: the surface is
    keyed by stable-node-order assignments; the action is positional."""
    if len(positional) != len(positions):
        raise InfrastructureError(
            f"action length {len(positional)} != {len(positions)} steps")
    by_node = dict(zip(positions, positional))
    return tuple(by_node[node] for node in sorted(positions))


def _completion_text(completion: Any) -> str:
    """TRL passes conversational completions as message lists."""
    if isinstance(completion, str):
        return completion
    if isinstance(completion, list) and completion \
            and isinstance(completion[0], Mapping):
        return completion[0].get("content", "")
    raise InfrastructureError(
        f"unrecognized completion shape {type(completion).__name__}")


def make_conductor_reward(
        surface: Mapping[tuple[str, tuple[int, ...]], float],
        trace_path: str | Path | None = None,
        schedule: list[str] | None = None,
        group_size: int = 8) -> Callable[..., list[float]]:
    """The single trainer-facing reward callable (precomputed_surface
    mode). Every schema-valid action must find its outcome row —
    a miss aborts the run (106_s §10.3). When a `schedule` is given,
    every completion is bound to its schedule index and the arriving
    observation must match the frozen order — a resampled or reordered
    batch aborts (121_s)."""
    state = {"written": 0, "lookups": 0}

    def conductor_reward(completions: list[Any], *,
                         observation_id: list[str],
                         positions: list[str],
                         num_steps: list[int],
                         **_: Any) -> list[float]:
        rewards = []
        rows = []
        for completion, obs_id, positions_json, steps in zip(
                completions, observation_id, positions, num_steps):
            index = state["written"] + len(rows)
            schedule_index = index // group_size
            if schedule is not None:
                if schedule_index >= len(schedule) \
                        or schedule[schedule_index] != obs_id:
                    raise InfrastructureError(
                        f"completion {index} carries observation "
                        f"{obs_id!r} but schedule position "
                        f"{schedule_index} is frozen as "
                        f"{schedule[schedule_index] if schedule_index < len(schedule) else None!r}"
                        " — the frozen order was not followed")
            text = _completion_text(completion)
            node_positions = json.loads(positions_json)
            try:
                positional = parser.parse_routing_action(text, steps)
            except ActionSchemaError as error:
                rewards.append(0.0)
                rows.append({"observation_id": obs_id,
                             "schedule_index": schedule_index,
                             "completion": text,
                             "action": None,
                             "schema_error": str(error),
                             "assignment": None,
                             "reward": 0.0})
                continue
            assignment = positional_to_semantic(positional,
                                                node_positions)
            key = (obs_id, assignment)
            if key not in surface:
                raise InfrastructureError(
                    f"no outcome row for schema-valid action {key!r}; "
                    "a partial or stale surface is an infrastructure "
                    "abort, never a reward (106_s §10.3)")
            payoff = surface[key]
            state["lookups"] += 1
            rewards.append(payoff)
            rows.append({"observation_id": obs_id,
                         "schedule_index": schedule_index,
                         "completion": text,
                         "action": positional,
                         "schema_error": None,
                         "assignment": list(assignment),
                         "reward": payoff})
        if trace_path is not None:
            with Path(trace_path).open("a", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
        state["written"] += len(rows)
        # 121_s: the four online metrics, logged live when W&B is up.
        try:
            import wandb
            if wandb.run is not None:
                valid = [r for r in rows if r["schema_error"] is None]
                import math
                counts = {w: 0 for w in (0, 1, 2, 3)}
                for r in valid:
                    for w in r["action"]:
                        counts[w] += 1
                total = sum(counts.values()) or 1
                entropy = -sum((n / total) * math.log2(n / total)
                               for n in counts.values() if n)
                groups = [rows[i:i + group_size]
                          for i in range(0, len(rows), group_size)]
                wandb.log({
                    "conductor/parse_rate": len(valid) / len(rows),
                    "conductor/reward_0.0": sum(
                        r["reward"] == 0.0 for r in rows) / len(rows),
                    "conductor/reward_0.5": sum(
                        r["reward"] == 0.5 for r in rows) / len(rows),
                    "conductor/reward_1.0": sum(
                        r["reward"] == 1.0 for r in rows) / len(rows),
                    "conductor/zero_variance_group_fraction": sum(
                        len({r["reward"] for r in g}) == 1
                        for g in groups) / max(len(groups), 1),
                    "conductor/selection_entropy_bits": entropy,
                }, commit=False)
        except ImportError:
            pass
        return rewards

    conductor_reward.__name__ = "conductor_reward"
    conductor_reward.state = state
    return conductor_reward


def summarize_action_trace(trace_path: str | Path,
                           expected_schedule: list[str] | None = None,
                           group_size: int = 8) -> dict[str, Any]:
    """§10.3 recorded figures, derived from the persisted trace after
    the run. With an expected schedule the trace must be COMPLETE and
    ordered: exactly len(schedule)*group_size completions in
    len(schedule) groups of group_size, each group's rows carrying the
    frozen observation and schedule index (121_s) — a partial trace is
    never summarized as a run."""
    rows = [json.loads(line)
            for line in Path(trace_path).read_text().splitlines()]
    if expected_schedule is not None:
        expected_rows = len(expected_schedule) * group_size
        if len(rows) != expected_rows:
            raise InfrastructureError(
                f"trace holds {len(rows)} completions; the frozen "
                f"schedule requires exactly {expected_rows}")
        for index, row in enumerate(rows):
            schedule_index = index // group_size
            if row.get("schedule_index") != schedule_index or \
                    row["observation_id"] != \
                    expected_schedule[schedule_index]:
                raise InfrastructureError(
                    f"trace row {index} does not match the frozen "
                    f"schedule at group {schedule_index}")
    by_group: dict[int, list[dict]] = {}
    for index, row in enumerate(rows):
        by_group.setdefault(index // group_size, []).append(row)
    valid = [row for row in rows if row["schema_error"] is None]
    worker_counts: dict[int, int] = {w: 0 for w in (0, 1, 2, 3)}
    for row in valid:
        for worker in row["action"]:
            worker_counts[worker] += 1
    total_selections = sum(worker_counts.values()) or 1
    import math
    entropy = -sum((n / total_selections) * math.log2(n / total_selections)
                   for n in worker_counts.values() if n)
    reward_counts = {"0.0": 0, "0.5": 0, "1.0": 0}
    for row in rows:
        reward_counts[f"{row['reward']:.1f}"] += 1
    groups = list(by_group.values())
    zero_variance = sum(
        1 for group in groups
        if len({row["reward"] for row in group}) == 1)
    mixed_top = sum(
        1 for group in groups
        if any(row["reward"] == 1.0 for row in group)
        and any(row["reward"] < 1.0 for row in group))
    topology = {}
    for row in rows:
        cell = row["observation_id"].split(":")[0]
        arity = {"lookup_atomic": "atomic", "math_atomic": "atomic",
                 "code_atomic": "atomic", "lookup_math": "two_step",
                 "math_code": "two_step", "fork_join": "fork"}[cell]
        bucket = topology.setdefault(arity, {"n": 0, "reward_sum": 0.0,
                                             "valid": 0})
        bucket["n"] += 1
        bucket["reward_sum"] += row["reward"]
        bucket["valid"] += row["schema_error"] is None
    for bucket in topology.values():
        bucket["mean_reward"] = round(bucket["reward_sum"] / bucket["n"],
                                      4)
        del bucket["reward_sum"]
    return {
        "completions": len(rows),
        "groups": len(groups),
        "action_schema_valid": len(valid),
        "action_parse_rate": round(len(valid) / max(len(rows), 1), 4),
        "reward_frequencies": reward_counts,
        "zero_variance_groups": zero_variance,
        "zero_variance_fraction": round(zero_variance / max(len(groups), 1),
                                        4),
        "groups_with_win_and_loss": mixed_top,
        "worker_selection_counts": worker_counts,
        "worker_selection_entropy_bits": round(entropy, 4),
        "by_topology": topology,
    }
