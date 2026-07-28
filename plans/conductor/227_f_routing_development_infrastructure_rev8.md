# 227_f — Infrastructure rev8 (response to 226_s)

The two consuming-boundary items are repaired. Full CPU suite:
**961 passed under `-W error`, TRUE process exit 0** (45 in the
routing battery). No GPU work has run; nothing is frozen or
launched.

## 1. The reserve's timing basis derives (F1)

- The complete-support closeout now persists the timing denominator:
  `rendered_observations` (the authenticated observation count) in
  its freeze, alongside the measured cost it already carried.
- The reserve gate REDERIVES: `measured_seconds_per_observation`
  must equal `budget_consumed_gpu_hours × 3600 /
  rendered_observations` EXACTLY — the reviewer's 1.5-hour /
  0.1-seconds reproduction refuses ("must rederive exactly"), and
  the r_cycle ceiling recomputation then rides on the derived
  basis.
- `status="final"` is rejected at this stage: a final reserve
  requires the frozen cycle-cohort and evaluation-rule identities
  in its freeze — until those exist, reserves are provisional.

## 2. Terminal verification proves valid evidence (F2)

- The LIVE environment manifest is canonically self-hash validated
  at execute before attestation or archival — an invalid
  `execution_manifest_sha256` refuses.
- `verify_terminal_outputs` is status-specific and closed:
  - **Complete**: the exact required output set must exist
    (disclosure, comparator, probe cohort, run record, execute-time
    environment); the bound run-record/execute-env bytes must
    match; the execute-time environment must PARSE and self-hash;
    the run record's identities cross-check against the closeout,
    the surface lock ON DISK (its `lock_sha256` must be the
    closeout's), the rehashing comparator record, and the rehashing
    probe-cohort record; the timing denominator must be present.
    The reviewer's `{}`-files-with-matching-hashes reproduction
    refuses on content validation.
  - **Aborted**: the bound partial-artifact inventory must be
    NON-EMPTY and EXACTLY the files on disk — missing, extra, and
    altered files all refuse.
- The reserve gate additionally requires the referenced closeout to
  carry the canonical complete-support terminal binding (surface
  lock + both file hashes + denominator) — a minimal freeze cannot
  anchor a reserve.

## 3. Next

Reviewer sign-off ("after this small terminal-manifest and
reserve-derivation repair, I would sign off"), then the Step-4
freeze: `support_run.prepare` on the GPU host, freeze document with
prelaunch records + manifest hash + ledger head, `execute` on
approval; the provisional reserve then rederives its basis from the
completed closeout by construction.
