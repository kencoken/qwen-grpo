# Unit 4 — Stage-0C trainer integration (106_s §§10.1–10.3)

Battery: **668 CPU tests** under warnings-as-errors (unit 3: 653);
agreement unchanged at **16,665/16,665**. The reward-bearing smoke is
implemented and gated (below); the non-reward-bearing demo check ran on
the GPU and passes.

## The single reward (§10.1) — `grpo_task.py`

`make_conductor_reward(surface)` is the one trainer-facing callable:
malformed action string → 0.0; schema-valid action whose workflow
failed in the world → 0.5; correct terminal → 1.0. The repository's
generic `format_reward` is deliberately NOT added (it would change the
relative advantages between the three ladder levels); action parse rate
is telemetry derived from the persisted per-completion action trace.
In `precomputed_surface` mode a schema-valid action with no outcome row
raises — an infrastructure abort, never a reward. Positional actions
are converted to stable-node-order assignments by inverting the frozen
`semantic_to_positional` mapping (round-trip tested on both fork
orders). Unit tests pin all three rewards AND the abort path through
the actual callable handed to `GRPOTrainer`, in TRL's conversational
completion shape.

## The frozen schedule and dataset

`smoke_schedule()` = declaration order, two rounds: 36 prompt groups,
each of the 18 §9.4 observations exactly twice — recorded and
deterministic; the dataset is materialized in schedule order and the
trainer runs `shuffle_dataset=False`, so stochastic resampling cannot
replace it. 36 groups ÷ 2 groups/update = the 18 declared updates,
exactly one epoch.

## Policy prompt and demonstrations (§10.2) — `policy.py`, DRAFT

The system prompt presents four OPAQUE ids ("0, 1, 2, or 3") and the
output contract; a leakage test asserts no model names, sizes,
families, or size relations appear (no "qwen/3b/1.5b/coder/model/
large/small/checkpoint/parameter"). The observation is Problem +
numbered reference steps (+ resource handles and uses-earlier-results
markers) + the instruction line. Four hand-written OUT-OF-DOMAIN
demonstrations cover all four ids with valid parseable actions;
workers 2 and 3 appear on matched Code-like steps.

**Demo drafting disclosure (4 GPU probes, non-reward-bearing):** the
§10.2 requirement that both Code workers execute the matched demos
turned into a live demonstration of the D16 failure modes. Draft 1
("entry at position N of the series", `Q-` handles): worker 2
substituted the handle (`at(Q-3F7, 2)`) on both demos — the in-domain
"zero-based index … requested resource" phrasing AND the `R-` handle
format turn out to be load-bearing for the 1.5B worker's
resource-word discipline (rev9's contrasts name `R-…` handles
specifically). Draft 3 fixed worker 2 but worker 3 produced its
invented `at(at(resource, 1), 2)` nesting on one demo; adjusting that
demo to index 0 under a fresh handle settled both workers:

```text
demo 2 (R-7Q3, [8,3,5,9], index 2 -> 5): w2 OK, w3 OK
demo 3 (R-5T4, [6,2,7],  index 0 -> 6): w2 OK, w3 OK
```

`demo-check` is a standing CLI command; the final demo pair is
executable by BOTH workers as §10.2 requires.

## Named launch profile and smoke (§10.1/§10.3) — `grpo_smoke.py`

`STAGE0C_LAUNCH_PROFILE` (sha `b05f92ee…` at this commit) records every
scientific setting explicitly: the Conductor on worker 3's frozen base
checkpoint (revision-pinned in `model_init_kwargs`), NF4 + BF16 +
gradient checkpointing, LoRA r16/α32/0.05 on all seven projections,
beta 1e-3, group 8, temperature 1.0, batch 2×8 (= two groups/update,
validated arithmetically), lr 1e-5, 10-step warmup, constant schedule,
the repository's DAPO loss, adamw_torch, seed 0, policy cap 128,
worker cap 256 + physical batch 1, `workflow_max_steps` 3,
`worker_outcome_mode = precomputed_surface`, the pool fingerprint, the
**pinned surface manifest hash `221a04d5…`** (118_s), the policy
prompt hash, W&B project `qwen-grpo-conductor` with the profile and
surface hashes in the run name, eval disabled (`n_eval=0`). This entry
constructs its own `GRPOConfig` — `train.py` and its CLI defaults are
untouched, so no repository default can silently fill a scientific
setting. The trained model is discarded (`save_strategy="no"`).

Launch preflights: profile validation (prompt-hash drift detection),
surface pin + fail-closed load, and the exact-direction w2/w3 canary
(workers released afterwards — §10.4 mode 1, no resident worker during
GRPO). The run persists `launch_profile.json`, the complete
`actions.jsonl` trace, and a `summary.json` with the §10.3 figures
(parse rate, reward frequencies, zero-variance-group fraction, groups
containing both 1.0 and lower, per-worker selection counts + entropy,
per-topology means, wall/VRAM).

## THE GATE — §10.2 prompt review required before the smoke runs

`run` refuses while `policy_prompt_review` is null: the Conductor
prompt and demonstration bytes must be reviewed and fingerprinted
BEFORE any reward-bearing output exists, because once smoke output is
inspected those bytes freeze (a later change is a new launch profile).
The prompt is committed here as DRAFT with sha recorded in the launch
profile; on review sign-off, `policy_prompt_review` is set to the
review record's name and the smoke runs.

Expectations already calibrated (118_s interpretation, recorded in
119_f): ≈19.8% success under uniform valid actions; ~12% chance a
uniform group of eight contains the unique fork winner; family routing
expected before scale selection; heavy zero-variance noise in fork
groups. Failure of the CE0 "sane, non-degenerate" definition is a
Stage-0 no-go, not an invitation to tune demonstrations.
