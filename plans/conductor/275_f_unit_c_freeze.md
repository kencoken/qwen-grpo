# 275_f — Unit C: pre-C audit + exposure-sample implementation + FREEZE (for review)

Unit B is signed; this document (a) records the mandated pre-Unit-C
code-invalidation audit, and (b) freezes the Unit-C runner
(`tasks/routing/unit_c_sample.py`) BEFORE its GPU run. Full CPU
suite: **1002 passed under `-W error`, TRUE exit 0**.

## 1. The pre-C code-invalidation audit (260_f §3, full charter scope)

Mechanical diff of every trainer-path file against the commit at
which the Step-6 probe EXECUTED (`8567942`):

| Path | Scope | Diff |
|---|---|---:|
| `tasks/routing/resume_validation.py` | rollout generation, reward, traces, trainer construction | **0 lines** |
| `tasks/routing/probe_run.py` | sampling, grouping, schedule machinery | **0 lines** |
| `tasks/routing/checkpoint.py` | accounting, checkpoint contract | **0 lines** |
| `tasks/conductor/parser.py` | parsing | **0 lines** |
| `tasks/conductor/grpo_task.py` | action semantics | **0 lines** |
| `tasks/conductor/stage1.py` / `program.py` / `policy.py` / `profiles.py` / `stage1_replay.py` | prompt, generation, families | **0 lines** |

Changed since the probe: `dev_support.py` (materializer hooks,
loader dispatch, cache-served invariant — materialization infra),
`extension_run.py` + `p0_mixture.py` (new; materialization and the
CPU schedule), `ledger.py` (admission kinds), `telemetry.py` (+116:
the extension ScaleLift comparator boundary — POST-HOC reporting,
itself review-hardened through 262_s→266_s; the in-rollout reward
path is `make_validation_reward`, untouched). **Verdict: no
invalidation** — rollout generation, sampling, grouping, parsing,
and reward are byte-identical to the validated probe; Unit C runs
on the unchanged trainer path, and the Step-6 probe remains a valid
projection basis (used only as disclosed transport in Unit B).

## 2. What Unit C is (and is not)

Per 269_s §7 OPTION 1: the preregistered projections (274_f) chose
the candidate BEFORE this run. Unit C VALIDATES the frozen mixture
`0100df2b…` — it cannot choose a mixture; any change afterward is a
new B/C iteration with new identities. The evaluation is mechanical
and preregistered in the frozen config:

- **Q1 gate** (the frozen Unit-B criterion): per critical cell, ≥2
  Q1-counted groups (reward-1.0 fully family-correct + reward-0.5
  strictly-lower-fc completions in one group) among BRIDGE draws,
  spanning ≥2 distinct latents. Any cell failing →
  **stop-and-review, no P0 launch**. Renderer occupancy REPORTED,
  not gated (the 274_f supersession).
- **Q2** = exact schedule delivery (70 `math_code→w3` + 90
  `fork_join→w2` composite draws) + REPORTED ckpt-0 C2-eligible
  completions — zero is the recorded starting condition, never a
  failure and never a direct-C2-exposure claim.
- Zero-variance fraction, per-class draws, anchor coverage, and the
  stratified yields are reported against the Unit-B projections.
- The frozen decision rule emits only: "Q1 authorized (+ Q2 as the
  unlocking experiment)" or "stop-and-review". Measured rates
  become P0-freeze sizing inputs; nothing else.

## 3. The frozen run

5 identical passes over the frozen 157-row epoch = **785 groups /
6,280 completions** through the REAL trainer loop; the exact
Step-5-validated construction (identical literals to the probe —
NF4 base at revision `aa8e7253…`, fp32 LoRA — asserted equal in
tests), fresh seed **20260801**, full determinism; the amended
zero-update contract (785 real optimizer steps at lr=0/beta=0,
zero effective updates, exact checkpoint-zero adapter equality,
proven over two persisted maps); rewards from the LOCKED extension
surface; scoring through the consumption-verified extension
ScaleLift comparator (`9220c2c7…` — never reselecting).

**Runtime bound (273_s caution):** expected ≈0.944 GPU-h at the
measured 4.33 s/group; frozen ceiling **1.25 GPU-h** as a
conservative per-step stop-bound (a ceiling is a bound, not a
target; the ~0.3 GPU-h margin covers load variance without
pressuring the abort machinery). Envelope: 58.86 remaining, reserve
5.0 intact — admissible.

Lifecycle: the validated Step-5/6 shape — prelaunch evidence before
admission (ledger kind `standalone_evaluation`,
`cohort_selection: outcome_conditioned` DISCLOSED,
`outcome_informed: true`, head anchor = frozen lineage parent
`b88eba02…`); abort closeout with measured cost + partial
inventory; success requires the anchored `verify_unit_c_run`
(environment/identity anchors, mixture rederivation, schedule =
five frozen passes, zero-mutation over two persisted maps,
counters 785/785/785/6280, exact telemetry schema, exact report
rederivation) BEFORE the complete closeout.

## 4. CPU verification in this commit

The frozen mixture rederives byte-exactly on the restored evidence
surface AND on the live locked surface; the schedule is five
identical frozen passes; the identity manifest self-hashes; the
comparator authenticates; a full synthetic 785-row archive passes
the report and the anchored verifier, the sabotaged-cell branch
emits stop-and-review, and anchor substitution / final-map mismatch
/ schedule tampering all refuse. Construction literals are asserted
equal to the validated probe's (seed excepted).

## 5. Frozen identities (FULL — the launch arguments)

- Config:
  `c013c5e90745babc8dba5e249e3919e23a25debb420938a3cf0ccd289bd583c2`
- Freeze:
  `29cc9d5960de1c29e6308e2a79660e7395cb5f1b90f2a06240f205620d96efc4`
- Static execution-identity manifest:
  `4c674d963a57b3078d95f4eefa4f2282b73ed006d77b399a2c582f86406cb609`
- Attested environment (unchanged host):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head (= frozen lineage parent, anchor-enforced):
  `b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd`
- Inputs: mixture record `0100df2b…` (rederived at launch, frozen
  in config); extension lock `ccb1c3e2…`; comparator `9220c2c7…`.

Launch: `execute_unit_c(expected_freeze_sha256=…29cc9d59,
expected_identity_sha256=…4c674d96,
expected_environment_sha256=…372f958f,
expected_head_sha256=…b88eba02)`.

## 6. Next

Reviewer pass on this freeze → GPU run with the §5 hashes →
closeout + exposure-report review → the preregistered decision →
val/cycle/`R_cycle` (231_f basis) → beta=1e-3 timing smoke → P0
freeze (audit REPEATED there) → checkpoint-zero eval → P0.
