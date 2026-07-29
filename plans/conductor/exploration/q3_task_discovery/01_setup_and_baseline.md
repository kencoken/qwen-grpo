# Setup and known-support baseline

## Pre-execution record

- Plan source:
  `/home/ken/qwen-grpo-q3task-input/q3_task_discovery_overnight_plan.md`
- Committed copy:
  `plans/conductor/exploration/q3_task_discovery/00_q3_task_discovery_overnight_plan.md`
- Source/copy SHA-256:
  `36c3b61ee36c8caf5b07c8a9449648ee9a51e334d662d6c3939b3ddce8f0548e`
- Base branch: `conductor_stage1`
- Base commit:
  `95cb618dca5eab2b93b151ffaccf575753ca4f33`
  (`268_f: Unit-A EXECUTED — 864-obs extension surface locked, yield measured`)
- Exploration branch: `conductor_q3_task_discovery`
- Worktree before branch creation: clean
- Host: `picome`; GPU: NVIDIA GeForce RTX 4090, 24,564 MiB

The base is the latest Unit-A result. Its compact archive is
`plans/conductor/evidence/support_extension_v1/`; its accepted surface lock is
`ccb1c3e2db2422a82919292144c0bdecc21d2cc89cb7a3a2c69bec17a2ce6d1b`.
Unit A found `eligible_common_cells_q3 = []`. All twelve candidate-domain w3
wins were `goal_first`-only; the sole full-quota direction was fork_join/w2.
That renderer/cell collapse is the reason for this separate adaptive
task-distribution exploration.

## Frozen treatment

| Field | w2 | w3 |
|---|---|---|
| Worker id/name | `2` / `code_1p5b` | `3` / `code_3b` |
| Model | `Qwen/Qwen2.5-1.5B-Instruct` | `Qwen/Qwen2.5-3B-Instruct` |
| Revision | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` | `aa8e72537993ba99e69dfaafa59ed015b17504d1` |
| Parameters | 1,543,714,304 | 3,085,938,688 |

Shared frozen identities/settings:

- pool fingerprint `wp-197e286115f56e4a`;
- rev10 Code prompt SHA-256
  `9b08f3e6f4afad854484a13257d973e79e8664194f16cf44930644ab22e88aea`;
- request contract `worker-blocks-task-last-v1`, digest
  `8638fdad716e1e0c55b733298f8d0b4061af8dc5851ba0e6b8c99017642b5a7c`;
- Code parser/tool and artifact grammar `cell-specs-v0.8`;
- NF4, double quantization, bfloat16 compute;
- greedy EOS decoding, 256-token cap, `singleton-v1`;
- private visibility and `action-controlled-disclosure-v0`.

The exploration changes only generated semantic tasks and their language
rendering. It does not change any registered worker, prompt, request builder,
parser, tool, precision, decoding rule, or production cell.

## Standalone harness

`tasks/conductor/q3_discovery.py` is development-only. The production IR has
no sequence-valued nodes, so the conceptual sequence intermediates are
recorded only in an experimental latent program. Every scored target compiles
to an existing legal scalar Code artifact rooted at `count_gt(...)` or
`at(...)`. Gold values are computed with the independent reference primitives
in `program.py`, then agreement with the unchanged Code parser/tool is checked
before a worker call.

The runner:

- sends the identical user message to w2 and w3;
- asserts the full rendered request SHA is equal across the pair;
- keeps distinct registered selected-worker fingerprints;
- records raw completions append-only under `runs/q3-task-discovery/`;
- separately executes and scores only the requested target;
- preserves envelope, grammar, legal-semantic, request, binding, runtime and
  completion identities;
- counts actual cache misses as physical singleton generations.

Focused pre-GPU verification:

```text
uv run pytest -q \
  test_conductor_program.py test_conductor_tools.py \
  test_conductor_pool_runtime.py test_conductor_worker_eval.py \
  test_q3_discovery.py
```

Result: **242 passed**.

## Known-support check

The baseline is prospectively fixed to four retained `routing_dev` Code
nodes regenerated through the current request builder:

| Case | Expected |
|---|---|
| `code_atomic:routing_dev:00000:e23a43bd:goal_first:private:n1` | both correct |
| `code_atomic:routing_dev:00005:bcd17865:goal_first:private:n1` | only w2; w3 protocol failure |
| `code_atomic:routing_dev:00009:b1e65b09:goal_first:private:n1` | only w3; w2 protocol failure |
| `fork_join:routing_dev:00001:3b8d777f:bound_var:private:n2` | w2 correct; w3 legal but semantically wrong |

The fourth case is deliberately included to prove that a legal, successfully
executed artifact is not treated as correct merely because it parses.

Execution command and result will be appended after the frozen checkpoints
run. No new strategy task will run unless this baseline passes.
