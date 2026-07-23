# 99_f — follow-up preregistration: the rev10 Math amendment

**Status: registered by Ken's in-session direction, 2026-07-22** ("let's
try this targeted prompt fix, logged to a new prompt revision"). This is
the bounded follow-up the 98_f terminal stop mandates; the 92_s freeze
is not reopened — this document registers one new exact configuration
under §11's rule that any prompt edit reruns candidate-specific P1, the
full crossed evaluation, and fresh confirmation.

## Hypothesis and treatment

98_f isolated one deterministic failure: under the `bound_var` problem
phrasing ("Let i = `(a × b + c) mod m` …"), Math drops the parentheses
when translating to calculator syntax (`a * b + c % m`, precedence flips
the value) — 30/30 identical failures under `task_last`, 5/30 under
`current`; all other renderers copy the parenthesized form correctly.

**Treatment — `rev10`, one bounded Math amendment** (the rev9 Code
lesson applied to Math): a matched-regime `modular` worked example (the
exact failing subtask text and operand regime; machine-verified,
value 2) plus one positive-only parenthesis rule ("mod is written % and
applies to the whole parenthesized expression"). No wrong exemplar —
the paren-less form is the model's prior, and rev7 showed such strings
become templates. Lookup and Code texts are **byte-identical to rev9**
(rev9 math sha `27a21040…` unchanged; rev10 math sha
`24c16a2115eceed072c0189692bf25799e59977f199829cc1f896e9da3b48787`).

## Candidate and protocol

One candidate: **`generic_1p5b-task_last-rev10`** (the 98_f anchor with
the amended bundle), registered in `candidates.py` under tranche `F1`,
with its support-digest entry added (registry sha now `8c5efab7…`; the
frozen 16 entries verified byte-identical before the addition).
`code_local_v1` is marked retired per 98_f.

1. **P1**: three fresh processes (canonical, canonical, reversed) at
   this document's commit, clean worktree; `admit` (hard-bound
   `worker_dev`, candidate-aware, support-digest-bound). Non-admission
   or any integrity violation stops.
2. **Full crossed run**: `run --role selection` over the full 900-case
   `worker_dev` population.
3. **Evaluation, preregistered:**
   - primary: the §4.1 target (every group 30/30, zero protocol
     failures) — with particular report of `math|math_code|bound_var`
     (0/30 in 98_f);
   - regression guard: **Lookup and Code generation fields must be
     byte-identical to the Tranche A `task_last` sentinel** (their
     prompts and requests are unchanged; admitted singleton generation
     makes byte-equality the expected outcome, and any difference is a
     reproducibility stop);
   - Math strata other than the target stratum must not regress below
     their 98_f sentinel values.
4. **If the target is reached**: proceed under 92_s §10 — confirmation
   run 2 (`--role confirmation`), composed diagnostic, decision record.
5. **Stop rule**: one revision. If rev10 does not clear the target, no
   further prompt edits under this document — stop with the evidence
   and a new decision, exactly as 98_f did.

Outputs under `runs/99f-rev10/` (gitignored) until this follow-up
closes; artifact + exit-0 required of every command.
