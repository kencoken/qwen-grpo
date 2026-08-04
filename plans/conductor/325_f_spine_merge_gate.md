# 325_f — Unit 5 SIGNED; contract-spine MERGE GATE record

Rev3 approved (323_s follow-up note); the non-blocking wording
cleanup is applied in this commit: the two remaining
deferred-cadence/evaluation/telemetry references
(`LAUNCH_ADMISSION_OUTSTANDING` and the `deferred_to` field) now
name the authenticated `P0ExecutionIdentity`, consistently with
the module header and the appendix.

## 1. The merge gate (303_f §10), executed at this commit

| Gate | Result |
|---|---|
| Full suite under `-W error` | **1023 passed, TRUE exit 0** |
| Committed archives reverify | PASS — the C1/C2 verifiers, the extension/probe/resume verifiers, and `verify_c2_replay_source` all run inside the suite; standalone `verify_c2_replay_source` = PASS. (Known documented exception: the historical B archive verifies only at checkout ≤ `0f56a65`.) |
| Exact C2 equivalence oracle | **PASS, 25/25 fields**, projection `f1912078…` (standalone + in-suite) |
| Traceability appendix | **PASS, byte-exact, 12,819 bytes** (reviewed per 323_s) |
| Reviewer sign-off | Rev3 approved |

Frozen identities at merge: contract `d47a63ff…`/`8b348b0f…`;
projection `f1912078…`/`41f15c5d…`; mixture
`135a72bf…`/`b305d9c8…`; runtime profile `202bc377…`; launch
freeze schema `p0-launch-freeze-v1` (no instance, no default pin).

## 2. Registered post-merge obligations (the reviewer's closing note)

The post-merge launch-admission unit MUST, before any P0
execution is authorized:

1. resolve and verify the precursor artifacts (routing_dev_val
   lock, cycle, R_cycle, beta smoke) under their pinned hashes;
2. validate the EXTERNAL execution/environment identity (the
   execution-manifest launch argument of 305_f §1; the
   environment attestation against
   `runtime.attested_environment_sha256`);
3. supply the authenticated trajectory index sets (with
   cadence/evaluation/telemetry configuration) through the
   `P0ExecutionIdentity`.

`prepare_p0_dataset` remains dataset preparation only; its
`launch_admission` block stays DEFERRED until that unit lands.

## 3. Merge

`conductor_spine` (this commit) merges into `conductor_stage1`
(at `6b1d542`, the exact branch point — no divergence). Post-merge
sequence per 303_f §10: `routing_dev_val` lock → cycle/`R_cycle`
→ beta smoke → the real `P0LaunchFreeze` instance (hash
externally reviewed) + launch admission → checkpoint-zero eval →
P0 with sentinel tracking.
