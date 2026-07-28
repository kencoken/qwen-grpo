Not quite ready to relaunch. The failure was handled correctly and the technical diagnosis is convincing, but two narrow provenance issues should be fixed first.

### Blocking findings

1. The successor launch would be recorded incorrectly.

[`execute_resume_validation()`](/private/tmp/review243/tasks/routing/resume_validation.py:1374) still emits:

- stale motivation: `240_f rev4`
- `parent=None`
- `outcome_informed=False`

REV6 directly follows the aborted run and outcome-informed dtype diagnostic. The append-only entry should cite `243_f`, the aborted closeout `237d4c21…`, and smoke closeout `943b9d7c…`; use the smoke closeout as lineage parent and set `outcome_informed=True`.

2. FP32 adapters are an unrecorded training-precision amendment.

The configuration still describes BF16 computation without declaring adapter dtype, while `_build_trainer()` now casts adapters to FP32. This changes the uninterrupted arm’s arithmetic, optimizer state and potentially its sampled trajectory—not merely checkpoint serialization. Consequently, [`243_f`’s “nothing else changes” wording](/private/tmp/review243/plans/conductor/243_f_resume_validation_launch_abort_and_rev6.md:43) is too strong.

Add `adapter_dtype: "float32"` to the frozen LoRA configuration and derive/assert the cast from it. State that:

- REV6 deliberately amends numerical precision while preserving the resume-equivalence question, gates, data, seed and tolerance.
- FP32 adapters become normative for the forthcoming routing-training/P0 builder. No shared-builder refactor is necessary yet, but a later BF16 P0 would not be covered by this validation.

### Confirmed sound

- The original launch aborted and closed correctly.
- Its 53-file inventory remains byte-exact.
- The diagnostic was properly logged as outcome-informed.
- All 504 LoRA tensors had matching keys/shapes and differed only as BF16 fresh versus FP32 resumed.
- The proposed cast is technically credible and has negligible 4090 impact.
- Ledger chain verifies; no launches are open.
- `59.8968` GPU-hours remain; the new v4 root is absent.
- Preflight passes at `24,079 / 24,564 MiB`.
- `975` tests pass under warnings-as-errors; diff and worktree are clean.

No additional GPU smoke is necessary—the refrozen exact rerun is the appropriate confirmation. After these metadata/config changes, rederive the hashes and perform only a narrow mechanical check before relaunch.