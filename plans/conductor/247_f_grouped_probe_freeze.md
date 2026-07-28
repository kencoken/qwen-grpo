# 247_f — Step-6 grouped-probe FREEZE (draft for review)

The UNCHANGED registered design (211_f §5, 231_f binding, 232_s
denominators), implemented as `tasks/routing/probe_run.py` in the
validated Step-5 lifecycle shape and frozen here for review BEFORE
the GPU run. Full CPU suite: **979 passed under `-W error`, TRUE
exit 0** (63 in the routing battery). Also in this commit: the
Stage-5 preservation item (§4).

## 1. Every 244_s-requested binding, frozen

- **FP32 LoRA**: `lora.adapter_dtype = "float32"` — the declared
  REV6 precision amendment, normative for P0; the builder refuses
  any other value.
- **The exact P0 checkpoint-zero construction** validated by Step
  5: NF4 (double-quant, bf16 compute) Qwen2.5-3B base at **model
  revision `aa8e7253…`**, LoRA r16/α32/dropout 0.05 on the seven
  projection targets, same tokenizer, same few-shot prompt
  construction (prompt sha in the identity manifest), fp32 adapter
  pin post-construction.
- **Cohort/rule**: bound cohort `7f31bd09…` (108 observations) and
  first-probe rule `0b616b88…` — the committed rule bytes
  revalidate against the frozen hash, the cohort REDERIVES from
  rule + locked surface (`61c4e85a…`) and must equal the frozen
  binding; both hashes also sit in the launch entry's freeze.
- **Sampling seeds**: probe seed `20260729` (fresh), full reseed
  before construction, `full_determinism = True`.
- **Grouping semantics**: G=8 completions per group, one group per
  optimizer step (per-device 2 × grad-accum 4, generation at each
  accumulation cycle — the Step-5-validated shape), temperature
  1.0, max 128 new tokens; schedule = bound order × 4 consecutive
  groups per observation = **432 groups / 3,456 completions**.
- **Zero-update mechanism, PROVEN not assumed**:
  `learning_rate = 0`, `beta = 0` through the REAL trainer loop;
  the final adapter must hash-equal the persisted checkpoint-zero
  map or the run aborts; counters must equal the design-derived
  432/432/432/3456; every trace row must match the frozen schedule.
- **New run root**: `runs/routing-dev/probe-v1` (exactly-once).
- **Ceiling**: the charter's **3.0 GPU-hours** (211_f §5), enforced
  per optimizer step; expected wall ≈ 35 min at the measured
  Step-5 pace.
- **Current ledger head**: `1a8d41fd…` (the Step-5 complete
  closeout); lineage frozen in config — parent = that closeout,
  `outcome_informed = false`, `cohort_selection = outcome_blind`
  (ledger-enforced for probe launches).
- **Abort handling**: the Step-5 lifecycle verbatim — prelaunch
  evidence (environment, identity manifest, preflight, schedule,
  bound cohort) persisted BEFORE admission; any post-admission
  failure appends an ABORTED closeout with measured cost and the
  content-hashed partial inventory; success requires the persisted
  report to rederive through `verify_probe_run` BEFORE the complete
  closeout (which binds the report/record file hashes and the exact
  terminal inventory).
- **Reporting boundary**: `telemetry.probe_report` (the reviewed
  218_s/220_s boundary — exact ids, multiplicities, group size
  against the frozen cohort + rule), with groups rebuilt from the
  full trace rows and re-authenticated against the locked surface
  and the rederived `c_fixed_dev` record.

## 2. Frozen identities (FULL — the launch arguments)

- Config:
  `638165129bd4665280cbf7da8471a54eb1385cd2dc0f072e91908780a497a6e4`
- Freeze:
  `f68813b60cdc5fe9edcf41b2caef4621ede95d3deba432ad1ffcaf51f89b269b`
- Static execution-identity manifest:
  `547a44b409c137c6160c1992787dd92cd7126bfab19ed42739f1881381c3eee0`
- Attested environment (unchanged host):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head:
  `1a8d41fde4ffb64a9d9d9886f8fbcf9dc20578ab33c3c0d72a44fa8ea9b6a44a`

Launch: `execute_probe(expected_freeze_sha256,
expected_identity_sha256, expected_environment_sha256,
expected_head_sha256)`.

## 3. Registered-measurement discipline (232_s / 244_s)

**Stage 5's six groups are NOT used to estimate routing exposure or
size P0** — they were a checkpoint-fidelity instrument on a
6-observation engineering schedule. The 432-group probe is the
registered exposure measurement; its denominators for review remain
432 total / 216 Code-bearing / 24 on direction-bearing observations
(16 w2-favoured, 8 w3-favoured) — opportunities, not thresholds;
few or zero exact contrasts is underexposure evidence, not failure.

## 4. Stage-5 preservation (reviewer wrap-up item)

The 2.4 GB `resume-validation-v4` root is backed up:
`/home/ken/backups/resume-validation-v4-20260728.tar.gz` (2.1 GB),
sha256
`926a1e7ae63a0102543d1338be1a0b5afa83296c566536eff9a647368ad8b27f`
— the compact Git evidence cannot independently reconstruct the
tensor comparison; this archive (and the live root) can, via
`verify_resume_validation`.

## 5. CPU verification in this commit

The frozen hashes rederive; the committed rule bytes revalidate;
the cohort binding REDERIVES from the committed evidence surface
via the production restore path (clean-clone valid); the schedule
builds 432 rows in bound order ×4; trace rows rebuild into
authenticated group inputs (a tampered reward still refuses); the
identity manifest is deterministic and self-hashing.

## 6. Next

Reviewer pass on this freeze, then the GPU run with the §2 hashes,
its close-out and report review — and P0 designed from the MEASURED
exposure.
