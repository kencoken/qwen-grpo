# 246_f — Step 5 EXECUTED: resume validation PASSES at exact tolerance

The approved rev7 relaunch ran 2026-07-28 and **the v1 checkpoint
contract holds on the real GRPOTrainer stack — the interrupted-and-
resumed run is BIT-EXACT against the uninterrupted run** (frozen
tolerance 0.0; 504 adapter tensors, full optimizer state incl.
group membership, scheduler, real next-sampler cursor, counters,
and the full merged completion/action/assignment traces all equal).

## 1. The run (all ledger-recorded)

- Launch `8b0df6b0…` against head `943b9d7c…` — parented on the
  dtype-smoke closeout with `outcome_informed=true` and the 243_f
  lineage in its motivation (the 244_s provenance contract);
  freeze `c73107e0…`, identity `3af6b03a…`, attested environment
  `372f958f…` all matched; preflight 24,079 MiB.
- Phase A uninterrupted 0→6; phase B fault-injected after update 4
  with the v1 bundle at update 3 (checkpoint record `d13e9e1a…`);
  phase C fail-closed resume (bundle + HF equivalence, now under
  fp32 adapters on both paths) 3→6.
- **All gates passed**: identical checkpoint-zero adapters across
  the three arms (`92d9ae4a…`); identical checkpoint-3 bundles and
  trace prefixes; reward-varying groups [0, 3]; nonzero
  checkpoint-zero → checkpoint-3 update (`92d9ae4a… ≠ dd0344e8…`);
  the aborted tail (group 3) preserved in the interrupted segment
  and EXCLUDED from the 6-group merged trajectory (§11.3 exercised
  for real).
- Counters exactly the schedule-derived expectation (6/6/6/48);
  next cursor = schedule row 6 on both arms (a real observation,
  not END).
- **Measured cost 0.0237 GPU-h**; complete closeout `1a8d41fd…` (=
  the new ledger head) binding the validation record and the exact
  terminal inventory. Envelope: 0.1269 consumed, 59.8731 remaining,
  nothing open.
- `verify_resume_validation` re-derived PASS from the archive alone
  — inside the run before the closeout, and again independently
  this session.

## 2. Evidence

Compact evidence committed at
`plans/conductor/evidence/resume_validation_v4/` (validation
record, per-arm checkpoint-zero maps, environment + identity +
preflight + schedule manifests, the v1 checkpoint record, and all
three full traces, 256 KB). The 2.4 GB run root (HF checkpoints +
persisted final states) remains local, every file bound by the
closeout's terminal inventory. The aborted rev5 root
(`resume-validation-v3`) remains preserved abort evidence.

## 3. What Step 5 establishes (and its boundary)

The v1 checkpoint/resume contract is VALIDATED for the P0 training
shape: fp32 LoRA adapters (the declared REV6 precision amendment —
normative for the P0 builder) over the NF4 Qwen2.5-3B base, G=8,
one group per optimizer step, HF-native checkpointing shadowed by
the v1 bundle. An engineering resume of P0 from a v1 boundary will
reproduce the uninterrupted trajectory exactly. NOT covered:
bf16-adapter configurations (would need their own validation pass)
and checkpoints off the v1 boundary (out of contract by design).

## 4. Next (211_f §15 / 232_s sequence)

Step 6: freeze the UNCHANGED grouped probe — bound cohort
`7f31bd09…` (108 observations, rule `0b616b88…`: G=8, 4
groups/observation, 432 groups, 3,456 completions), the probe
executor built against the reviewed telemetry boundary
(`probe_report`), its 3 GPU-h charter ceiling — reviewer pass, then
the probe run, then P0 designed from MEASURED exposure.
