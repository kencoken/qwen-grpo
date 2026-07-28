# 245_f — Step-5 rev6 provenance repair (response to 244_s)

Both findings fixed; hashes rederived. Full CPU suite: **976 passed
under `-W error`, TRUE exit 0** (60 in the routing battery). No new
GPU work; the ledger head is unchanged (`943b9d7c…`).

## 1. The successor launch records its true lineage (F1)

The relaunch lineage is FROZEN CONFIG, not code side-effects
(`RESUME_VALIDATION_CONFIG["lineage"]`, regression-tested): the
ledger entry will carry
`motivating_evidence = "243_f rev6 freeze; aborted rev5 closeout
237d4c21…; outcome-informed dtype-smoke closeout 943b9d7c…"`,
`parent = 943b9d7c…` (the smoke closeout, full hash), and
`outcome_informed = True`.

## 2. FP32 adapters are a DECLARED precision amendment (F2)

- `lora.adapter_dtype = "float32"` is now a frozen configuration
  field, and `_build_trainer` derives the cast from it (any other
  value refuses — a different adapter precision needs its own
  reviewed tranche).
- **Stated plainly, correcting 243_f §3's "nothing else changes"**:
  REV6 deliberately amends the training's NUMERICAL PRECISION — the
  uninterrupted arm's arithmetic, optimizer state, and potentially
  its sampled trajectory differ from a bf16-adapter run. What is
  preserved is the resume-equivalence QUESTION and its instruments:
  the gates, the data/schedule, the seed, and the frozen exact
  tolerance.
- **FP32 adapters are normative going forward**: the forthcoming
  routing-training/P0 builder inherits this precision. No
  shared-builder refactor is needed yet, but a later bf16-adapter
  P0 would NOT be covered by this validation and would need its own
  resume-validation pass.

## 3. REV7 identities (FULL — the relaunch arguments)

- Config:
  `40e1ecc5169111be33f93f00cd50f1819c1c55492957a64d3b0e4d6f831ff2f6`
- Freeze:
  `c73107e0813f2b5ef63a248ae76e958ba78697352233a52786593d5b0c73fd6a`
- Static execution-identity manifest:
  `3af6b03a64debb66a17b70771f599682432373ee2271f8500b7662b3d24f974c`
- Attested environment (unchanged):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head (unchanged):
  `943b9d7ce8c7ebcd908101489a8f0a866ccc575c8538f727d633415e918ca212`

## 4. Next

Per 244_s: "No additional GPU smoke is necessary — the refrozen
exact rerun is the appropriate confirmation. After these
metadata/config changes, rederive the hashes and perform only a
narrow mechanical check before relaunch." The relaunch is
`execute_resume_validation` with the four §3 hashes.
