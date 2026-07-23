# Unit 4 rev2 — response to 123_s and the formal 122_f probe outcome

All ten pre-freeze acceptance items (123_s §10, 1–8 plus the two GPU
steps) are implemented; results of the cache-backed verification, the
format probe, the freeze and the smoke are appended as they complete.
Battery at this commit: **673 tests** under warnings-as-errors.

## Formal probe outcome record (123_s §8.1)

**Round-by-round workflow matrix** (probe of the 122_f preregistered
candidate set; round 1 = the one permitted repair, which changed only
the specialist Problem wording from goal-chained to resource-first
imperative — steps, payloads, workers and gold unchanged):

| workflow | action | round 0 | round 1 |
|---|---|---|---|
| direct | `[0]` | pass (27) | pass (27) |
| dependency | `[0,1]` | pass (28) | pass (28) |
| independent→final, assigned | `[2,3,1]` | pass (19) | pass (19) |
| independent→final, swapped | `[3,2,1]` | pass (19) | pass (19) |
| specialist→check, assigned | `[3,2]` | **fail** | **fail** |
| specialist→check, swapped | `[2,3]` | pass (6) | pass (6) |

**Both failed worker-3 outputs, verbatim:**

```text
round 0: <artifact>at(count_gt(stable_unique(resource), 4), 3)</artifact>
round 1: <artifact>at(rotate_left(stable_unique(resource), 3),
                     count_gt(stable_unique(resource), 4))</artifact>
```

**Short-circuit record (123_s §8.3):** in both failing `[3,2]` runs,
worker 3 failed at step 1 (typed failure), step 2 was
dependency-blocked, and worker 2 therefore never executed step 2 in
the assigned workflow. The earlier claim that "both Code workers
execute every Code node in both Code-bearing demos" described the
planned assignments, not reached nodes, and is corrected: worker 2's
step-2 execution evidence comes from the swapped `[2,3]`… step-2
worker-3 execution and the round-independent swapped runs; the
narrowed claims in `policy.py` now distinguish the matched pair from
the asymmetric example.

**Corrected cumulative request accounting (123_s §8.2):** 8 distinct
rendered request hashes in each round, 6 shared between rounds —
**10 distinct rendered request hashes cumulatively** and **14 distinct
(worker fingerprint, request) completions**, verified directly from
the demo-check cache. The earlier "8 unique requests" figure was
per-round, not cumulative.

**Budget exhaustion:** the one batched repair round for the
specialist_check type was consumed; execution stopped at the gate
(commit `9c910a7`) before the format probe, the freeze, the canary and
any reward-bearing output. **Neither the payoff surface nor any
reward-bearing output was loaded or inspected at any point in the
probe**: the demo-check imports neither, and its only GPU outputs were
the worker completions recorded above.

## 123_s corrections implemented

1–2. Demonstrated actions amended to the approved `[3,2,1]` and
`[2,3]` — both routes already executed successfully through the exact
runtime in the recorded rounds.
3. The demo checker cross-swaps only the explicitly matched
independent→final pair; the specialist example runs only its
demonstrated route (requiring universal cross-executability would
contradict the heterogeneity that motivates the pool).
4. `policy.py` records the narrowed exchangeability claim (matched
pair = independent→final only), the asymmetric-capability status of
the specialist example, and the approved framing verbatim — including
that the demonstrations supply a **limited routing prior** (family
compatibility plus a coarse within-Code cue) and must not be described
as format-only. Stage 0 is demonstration-bootstrapped routing, not
routing from an uninformed initialization.
7. The system prompt wording is the approved neutral form ("Workers
differ in how they handle a step in the context of the full request…"),
with a test asserting the old wording is gone.
8. `verify_freeze` now compares an `executable_source_sha256` — a
deterministic digest over the eight source files that produce the
model-visible bundle and the smoke (fixture excluded, so no
self-reference); the Git commit at freeze is recorded as
informational. The `run` path fails closed if those bytes change.

## Interpretation adopted (123_s §3)

The endpoint treatment is the complete combination
`checkpoint + system prompt + request contract + visible context`;
the Conductor learns compatibility between workflow context and fixed
model–prompt–contract endpoints. No worker-prompt amendment and no
`local_only` switch (a later mechanistic ablation): the failure
survived two materially different Problem formulations, prior D16
additions traded modes, and a request-scope change would invalidate
fingerprints, sentinels, the canary and the surface.

## Deferred decision registered (123_s §9)

The Stage-2 demonstration treatment (few-shot as primary vs
schema-only, with the untrained few-shot baseline as the mandatory
comparison and a one-seed no-demonstration pilot preferred) is
explicitly deferred to the Stage-2 prompt freeze — recorded here so it
is chosen, not silently settled by the Stage-0 prompt.

## GPU results (appended 2026-07-23)

**Item 9 — cache-backed final demo verification:** all five approved
executions pass (`[0]`→27, `[0,1]`→28, `[3,2,1]`→19, swapped
`[2,3,1]`→19, `[2,3]`→6) with **0 new singleton generations** — fully
served by the probe cache, as the review predicted.

**Item 10 — reward-blind format probe:** 144/144 completions valid
schema AND correct action length in every topology (atomic 72/72,
two_step 48/48, fork 24/24 — all 1.00 against the 0.80 floor). The
action-length confound is empirically absent; no schema repair used.

**Item 11 — freeze:** `stage0c_policy_freeze.json` (sha `6cf44e2d…`)
records the literal digests — system prompt `fe9bba0d…`, 18 rendered
observation hashes, pinned chat template, launch profile `0815c033…`,
support declaration, executable-source digest — and names the review
record. Committed at `65a5fbe`.

**Item 12 — canary + the single reward-bearing smoke**
(`runs/stage0c-smoke-0815c033-221a04d5`, W&B run 3satfxr9):

```text
status complete; 18 updates, 288 completions in 36 ordered groups
(schedule enforced online); wall 153.2s; peak reserved VRAM 14.43 GiB
(post-canary reset — workers absent during GRPO)
canary: w2 0.5 / w3 1.0 (exact registered direction)
action parse rate 0.9965 (287/288; the one malformed action was
  {"worker_ids": [3, 4]} — id 4 out of range, reward 0.0)
reward frequencies: 0.0 x1, 0.5 x148, 1.0 x139  (48.3% success)
zero-variance groups 28/36 (0.778); groups with 1.0 AND lower: 7
worker selections: 0:214, 1:121, 2:74, 3:69; entropy 1.84 bits
at the Code position specifically: w0:25, w1:15, w2:49, w3:54
per-topology mean reward: atomic 0.767, two_step 0.760, fork 0.615
surface lookups 287 (= valid actions); zero infrastructure aborts
```

Every §10.4 "sane, non-degenerate" condition holds: all four ids in
schema-valid actions; workers 2 AND 3 each at Code positions; 1.0
outcomes present; mixed-reward groups present. Sampled success (48.3%)
is far above the ~19.8% uniform-action expectation — the demonstrations
supply a substantial routing prior exactly as 123_s §5 anticipated,
which is the disclosed demonstration-bootstrapped framing; the
few-shot-vs-no-few-shot measurement remains the registered Stage-2
decision. The trained adapter and optimizer state are discarded.
