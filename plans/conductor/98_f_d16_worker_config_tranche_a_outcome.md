# Tranche A outcome — terminal stop (92_s §11)

**Executed 2026-07-22 at the frozen executable commit `98f9300`,**
in the frozen arm order, worktree clean throughout, every command with
a valid artifact and exit 0. Screening manifest sha
`9c111234d7724fb9c0238a5df851b464938841e39e1fa41bc7a70af5a64d9afd`;
reveal artifact sha
`231510b4adbcf283fe605d652970ee71cf9636c9777d76995ab2d8f892abf147`;
raw artifacts retained under `runs/92s-tranche-a/` (gitignored).
Budget: 24 P1 invocations + 2 sentinel full runs — well inside the
preregistered cap.

## Formal result

1. **All eight configurations ADMITTED.** `singleton-v1` generation
   is bit-stable across fresh processes and order reversal for every
   model × contract × prompt configuration, within the frozen cost
   gate. Gate D's admission question is answered affirmatively for the
   entire 1.5B matrix.
2. **No configuration has a clean 300-case prefix** — so, per the
   frozen §7 logic, no Tranche A configuration can reach the 30/30
   target, and no target-search full runs were spent.
3. **Both contract sentinels executed and both contracts are
   `proven_non_target`** on full, validated Lookup/Math evidence:
   - `current`: Lookup fails on fresh instances
     (`lookup_math` 27/30 bound_var, 29/30 resource_first), Math
     25/30 on `math_code` bound_var, plus 3 grammar failures.
   - `task_last`: Lookup **perfect** (all nine groups 30/30), zero
     protocol failures — but Math collapses to **0/30** on exactly one
     stratum, `math_code` × bound_var.
4. **Therefore, per 92_s §5 and the §11 hard-stop list: the experiment
   STOPS.** `selected: None`; Tranche B is never opened (a Code-model
   change cannot repair a shared-contract failure). Any continuation
   requires a new preregistration; unrestricted prompt iteration on
   `worker_dev` remains barred.

## Decision inputs for the next preregistration

**P1 prefix correctness (/300), all arms admitted:**

| arm | correct |
|---|---:|
| generic_1p5b-task_last-rev9 | 285 |
| coder_1p5b-task_last-rev9 | 280 |
| coder_1p5b-current-rev9 | 276 |
| coder_1p5b-task_last-code_local_v1 | 276 |
| generic_1p5b-task_last-code_local_v1 | 276 |
| generic_1p5b-current-rev9 | 269 |
| generic_1p5b-current-code_local_v1 | 262 |
| coder_1p5b-current-code_local_v1 | 254 |

**Factor findings (paired, identical support):**

1. **`task_last` beats `current` in every paired contrast**
   (Δ+4 to +22). It perfects Lookup, and largely repairs the 78_s Code
   renderer collapse — `math_code` goal_first goes from **0/30**
   (current, full run) to 25/30; `fork_join` goal_first from 8/30 to
   ≥26/30. The bundled-treatment caveat stands: block order and final
   line changed together.
2. **`rev9` beats `code_local_v1` in every paired contrast**
   (Δ+4 to +22). The positive-only hypothesis is answered: rev9's
   wrong/right contrasts are load-bearing. `code_local_v1` should be
   retired.
3. **The single blocking defect of the best configuration**
   (`generic_1p5b-task_last-rev9`, 285/300, zero protocol failures)
   is one sharply localized interaction: **Math × `math_code` ×
   bound_var = 0/30** under task_last (25/30 under current — the same
   stratum is the weakest Math group under both contracts). Everything
   else in that arm's Math and Lookup is perfect.
4. **The 78_s renderer-collapse finding reproduces on fresh
   `worker_dev` instances** under the corrected evaluator — it was
   not an artifact of the consumed construction prefix — and
   Lookup/Math renderer sensitivity is a **new** finding: the rev9
   cycle never renderer-crossed those endpoints (their 90/90 and
   116/116 were resource_first-composed only).

**The obvious next preregistered question** (for Ken and the reviewer
to design, not decided here): diagnose and fix the single
Math × `math_code` × bound_var interaction under the otherwise-
dominant `task_last` contract — the retained completions for those 30
cases are in the sentinel run artifact — with
`generic_1p5b/task_last/rev9` as the anchor configuration and
`code_local_v1` retired. The 92_s machinery (registry, screening,
reveal, receipts) is reusable as-is for that follow-up.
