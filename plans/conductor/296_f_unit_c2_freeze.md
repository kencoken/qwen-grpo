# 296_f — Unit C2: audit + implementation + FREEZE (for review)

The 295_f-signed B2's empirical gate, implemented as the versioned
`tasks/routing/unit_c2_sample.py` and frozen BEFORE its GPU run.
Full suite: **1009 passed under `-W error`, TRUE exit 0**.

## 1. The repeated trainer-path invalidation audit (290_f §5 — clean)

Mechanical diff from the commit at which C1 executed (`e1aeae7`) to
HEAD: **0 diff lines** in every trainer-path file —
`resume_validation.py`, `probe_run.py`, `checkpoint.py`, the V1
`unit_c_sample.py`, `parser.py`, `grpo_task.py`, `stage1.py`,
`program.py`, `policy.py`, `profiles.py`, `stage1_replay.py`. The
ONLY change under `tasks/` since C1 is the new CPU-only
`p0_mixture_v2.py` (schedule/report-side). Per the frozen rule,
schedule/report-only changes pass mechanically: **C2 inherits C1's
validation; no smoke/revalidation required.**

## 2. What C2 is

The one sanctioned fresh run (290_f): 5 identical passes over the
PINNED B2 epoch (`135a72bf…`, rederived and pin-checked at launch) =
785 groups / 6,280 completions; construction literals asserted
identical to the validated V1 (fresh seed **20260803** only);
zero-update contract with the 504-key-set binding; rewards from the
locked extension surface; scoring through the consumption-verified
extension comparator; **C1's root and evidence untouched** (own run
root `runs/routing-dev/unit-c2-v1`).

**Preflight runs `verify_c1_basis()` FRESH, pre-admission** — the
authoritative gate (ledger chain + historical C1 closeout bindings
+ the untouched V1 archive verifier + rate equality), completing
the freeze/pre-launch/post-implementation hard-gate triple.

## 3. Executable populations and the frozen decision (294_s obligation)

`row_population` / `is_q1_population` / `is_q2_population` /
`is_sentinel_population` are small named predicates over the pinned
record, with cross-population tests: every scheduled row belongs to
exactly one population; the Q1 population is bridge-class only; the
Q2 population excludes the direct-specialist control; the sentinel
population is the pinned record's three ids (anchor-class rows,
sentinel population). The report consumes the SINGLE B2
definitions: `sentinel_block` (pinned-record-bound, first-group AND
first-update indices), `decide_c2_outcome` (the frozen four-branch
matrix), `derive_p0_size_v2` (three-cell sizing, derived only on a
direct-Q1 pass and persisted). Gates: per direct-Q1 cell ≥2 counted
groups from ≥2 latents; per-direction Q2 cold-start on the intended
target worker. Synthetic archives exercise the PASS,
stop-and-review, and maximum-Q1-only branches end-to-end.

## 4. Lifecycle

The validated shape: prelaunch evidence before admission
(`standalone_evaluation`, `cohort_selection: outcome_conditioned`
disclosed, `outcome_informed: true`, head anchor = frozen lineage
parent `9f4661a8…` — the C1 closeout, still the current head);
per-step deadline at the **1.25 GPU-h** stop-bound (expected
0.98–1.0 per 290_f); abort closeout with measured cost + partial
inventory (an infrastructure abort is "no scientific outcome" under
the frozen contract); success requires the anchored
`verify_unit_c2_run` (environment/identity anchors, pinned-mixture
rederivation, five-pass schedule, 504-key zero-mutation gate,
counters 785/785/785/6280, exact telemetry schema, exact report
rederivation) BEFORE the complete closeout.

## 5. Frozen identities (FULL — the launch arguments)

- Config:
  `5b47ada33a0223c1d8322846e536cc95285d950fb8076635008b803e49dcfb1c`
- Freeze:
  `ae51bc57476ed1a9729bd949c1651d4c88a0cbb62e310179e30af415b0fa8420`
- Static execution-identity manifest:
  `358330c8e9a9ed15b4e98860e77caf35d84d67af1baecdbbcc9443ae04db09e5`
- Attested environment (unchanged host):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head (= frozen lineage parent, anchor-enforced):
  `9f4661a84e601299951f17370eb22d9aa52f970a717b80844684240c8c550996`
- Inputs: mixture record (pinned) `135a72bf…`; B2 config
  `66d62b92…`; extension lock `ccb1c3e2…`; comparator `9220c2c7…`.

Launch: `execute_unit_c2(expected_freeze_sha256=…ae51bc57,
expected_identity_sha256=…358330c8,
expected_environment_sha256=…372f958f,
expected_head_sha256=…9f4661a8)`.

Envelope: 57.8837 remaining, reserve 5.0 intact — admissible.

## 6. Next

Reviewer pass on this freeze → GPU run with the §5 hashes →
closeout + exposure-report review → the frozen decision (direct-Q1
fail → stop; Q1+Q2 → both; Q1-only on Q2 fail with the P0 freeze
deciding worth) → the 287_f spine branch.
