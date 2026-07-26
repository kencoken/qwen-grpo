# 189_f — Route-B sign-off repair (response to 188_s)

The sign-off blocker and all four small corrections are implemented.
187_f stands at reviewed bytes; its defects are corrected forward
here. Full CPU suite with the new verifier module tracked: **902
passed under `-W error`, TRUE exit 0.**

## 1. The executable verifier is committed (blocker)

The 187_f "recipe" block was imports and comments — it could not
have produced the displayed output (which came from an uncommitted
scratch script). That is a reproducibility-record defect, now
closed: **`tasks/conductor/stage1_attempt1_ledger.py`** is the
committed, executable verifier —
`uv run python -m tasks.conductor.stage1_attempt1_ledger` — and
covers the full 188_s list: the archive manifest's own hash against
the 185_f pin plus every consumed file's sha256/byte row; the
bundle's self-hash and cross-root equality; A/C/D reloads through
the frozen fail-closed loaders (exact key sets, amend1 tags, bundle
binding, schemas, branch-telemetry exact set); the exact 12 gated A
rows from the frozen grid enumeration and acceptance constants; the
C §5.3 hard-path criteria; every D Wilson upper against its frozen
ceiling with the expected INSIDE/EXCEEDS pattern asserted; the D8
per-look branch counts and support rule; the run statuses, the
absence of any B completion, and the absence of any aggregate; and
the D5 binomial tail. Any discrepancy raises; it writes nothing.

Verbatim output of the committed verifier:

```
1. archive manifest 114cf207dd98… verified; 20 files match their rows
2. execution bundle 9b5f1ab85f26… self-hash + cross-root equality verified
3. A/C/D reload through the frozen fail-closed loaders (exact keys, amend1 tags, bundle binding, schemas)
4a. A: 12/12 gated cells >= 0.8; worst LB 0.98996 (A|fork_div3|0.15|0.5)
4b. C: hard-path criteria met (failures: [])
4c. D1_seq_null_ordinary_div3: 12/5000 UB=0.0038 ceiling=0.02167 -> INSIDE
4c. D2_seq_null_fork_div3: 15/5000 UB=0.0046 ceiling=0.02167 -> INSIDE
4c. D3_equiv_boundary_plus: 81/5000 UB=0.0194 ceiling=0.03125 -> INSIDE
4c. D4_equiv_boundary_minus: 101/5000 UB=0.0237 ceiling=0.03125 -> INSIDE
4c. D5_pilot_hetero_unequal: 157/5000 UB=0.0357 ceiling=0.03125 -> EXCEEDS
4c. D6_persist_const_theta10: 208/5000 UB=0.0465 ceiling=0.06250 -> INSIDE
4c. D7_persist_rowdispersed_theta10: 199/5000 UB=0.0446 ceiling=0.06250 -> INSIDE
4c. D8_persist_hybrid_theta01_fork: 0/5000 UB=0.0005 ceiling=0.06250 -> INSIDE
4c. branch D8_persist_hybrid_theta01_fork|look100: {'zero_branch': 2782, 'positive_branch': 2218, 'denominator_unresolved': 0, 'trials': 5000}
4c. branch D8_persist_hybrid_theta01_fork|look500: {'zero_branch': 257, 'positive_branch': 4743, 'denominator_unresolved': 0, 'trials': 5000}
4c. D8 branch support: ok
5. statuses: validation=complete, replay=aborted (wall 1s, error 'AttributeError: '); zero B completions; no aggregate
6. P[K>=157 | n=5000, p=0.025] = 0.002879
ALL ATTEMPT-1 LEDGER CHECKS PASSED
```

## 2. Small corrections (record-only for 185_f/187_f, which stand)

1. **Wording**: 187_f §2's "A power validated" and "statistic
   calibrated" are restated as: A and D6–D8 **met the registered
   power/undercoverage screens on the specified grids** — scoped
   design evidence, not general validation.
2. **Erratum for 185_f §2's D1/D2 display**: the ceiling is
   `alpha + max(0.005, 0.25·alpha)` = 0.0167 + 0.005 =
   **2.1667%**, not the 2.08% shown there (that figure applied the
   0.25·alpha term below the 0.005 floor). The INSIDE verdicts are
   unaffected (Wilson UBs 0.38%/0.46%); the committed verifier
   prints the correct ceilings.
3. **Wording**: 187_f §3's "B's actual measurement arrives under
   Route B" is restated as: **a separately identified B diagnostic
   MAY be run under Route B** — it is a distinct, separately
   preregistered activity, not an entitlement of the route choice.
4. **Authorization scope, explicit**: Route B acceptance (187_f)
   authorizes ONLY the disposition and the planning direction. It
   does NOT authorize B generation, the B diagnostic, or any GRPO
   run — each requires its own reviewed, source-frozen plan first
   (186_s status header).

## 3. Launch-plan requirement (carried forward as binding)

Per 188_s: the development-track launch plan must (a) create a
**genuinely new development namespace disjoint from ALL existing
identities** — construction, qualification, `policy_dev`,
train/dev/test — not merely protect policy_dev cohort B; and (b)
freeze **numerical limits for both the initial training budget and
the prompt-iteration budget**. These join the 187_f §4 guards
(conductor-prompt-only iteration per 103_s; explicit smoke
completion budget).

Ready for sign-off.
