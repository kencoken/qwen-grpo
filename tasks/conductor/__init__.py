"""Toy Conductor environment (Stage 0A) — see conductor_cell_specs.md v0.8.

The frozen executable specification lives at the repo root
(`conductor_cell_specs.md`, rev8/v0.8); the plan contract is
`plans/conductor/13_f_plan_rev6.md`. Module map:

- `types`      — spec §1.1–1.3, §1.6 limits, §1.7: codes, canonical ints,
                 resources, IR ref/op schemas, WorkerResult.
- `program`    — spec §1.3, §1.13–1.14, §2, §3: identity/seeds, samplers,
                 primitives, scheduler, cell generators, interventions.
- `render`     — spec §1.4–1.5, §1.12, §3 renderer strings.
- `resources`  — manifests, instance-scoped registries, disclosure.
- `parser`     — spec §1.5 routing schema; plan contracts 1–2.
- `contract`   — spec §1.6–1.7 artifact envelope + WorkerResult paths.
- `tools`      — spec §1.6 grammars/evaluators (independent of `program`).
- `prompts`    — D16 system prompts + demonstrations (separate freeze).

Stage 0B adds the runtime layer (plan rev6 §8, spec §1.10):

- `runtime`    — versioned runtime profile, caching fingerprints,
                 `build_runtime`/`close` lifecycle.
- `workers`    — NF4 worker pool, chat-template request rendering,
                 batched greedy generation + telemetry.
- `cache`      — SQLite write-through completion cache (three-part key).
- `executor`   — gains wave batching (worker × depth) and JSONL traces.
"""
