# 236_f — Step-5 resume-validation tranche freeze REV2 (response to 235_s)

All eight blocking findings, the four additional acceptance gates,
and the portability note are implemented. No GPU work or ledger
admission has occurred. Full CPU suite: **966 passed under
`-W error`, TRUE process exit 0** (50 in the routing battery,
including the previously ResourceWarning-flaky test, now fixed).

## 1. New frozen identities (supersede 234_f)

- **Freeze hash `711c8204…`** over config **`b4962667…`**
  (`routing-dev-resume-validation-v2`).
- EXACT ceiling unchanged: **0.5 GPU-hours** — now enforced BEFORE
  EVERY optimizer step via a deadline callback (F7), not merely
  between phases.
- **Launch requires the reviewed freeze**:
  `execute_resume_validation(expected_freeze_sha256=…)` refuses if
  the reconstructed freeze differs from the externally reviewed
  hash above (F5).

## 2. The findings, closed

1. **Identical starting weights, one launch configuration**: a full
   reseed (python/numpy/torch/CUDA) precedes EVERY model
   construction; all arms use `max_steps = total_updates = 6`; the
   interrupted arm is stopped by an INJECTED FAULT at update 4, not
   a shorter horizon; gate 1 requires identical checkpoint-zero
   adapter hashes across all three arms (content-hashed
   tensor-by-tensor).
2. **The resumed run consumes the validated state**: the v1 bundle
   binds EVERY HF checkpoint file by content hash
   (`hf_checkpoint_sha256` in the record), and
   `verify_hf_checkpoint_against_bundle` re-hashes them and
   SEMANTICALLY verifies the HF adapter (format-independent tensor
   content hashes), optimizer (flattened state incl. group
   membership), scheduler, and torch CPU/CUDA RNG against the
   bundle before `resume_from_checkpoint` may consume them.
3. **The aborted tail is real**: the fault at update 4 leaves group
   3 as a post-checkpoint tail; the interrupted segment merges as
   ABORTED with cutoff 3 — the tail must appear in
   `excluded_aborted_evidence` and stay out of the 6-group merged
   trajectory; the orchestrator AND the independent verifier both
   refuse if no tail exists (§11.3 now genuinely exercised).
4. **Complete, re-verifiable comparison**: the schedule has 8 rows
   for 6 updates, so the next-sampler cursor is a real observation
   id (compare_runs REFUSES an `END` comparison as degenerate);
   optimizer comparison includes `params` membership; traces carry
   completions, parsed actions, and semantic assignments; final
   A/C states are PERSISTED (`final_uninterrupted/`,
   `final_resumed/`: safetensors adapter + optimizer.pt +
   scheduler.pt + cursor.json, all content-hashed into the
   validation record); **`verify_resume_validation(run_root)`**
   reloads the archive alone and rederives the merge, gates 3–4,
   and the §11.5 comparison, requiring the persisted record to
   match exactly — it runs inside the tranche before the closeout
   and is available to the reviewer afterwards.
5. **Freeze identity consumed at launch** (§1 above).
6. **Safe 4090 lifecycle**: segments return CPU-moved snapshots
   only; the trainer reference is dropped inside the segment,
   garbage-collected, and allocated VRAM must return below the
   frozen 1,024 MiB floor before the next phase constructs — else
   refuse.
7. **Ceiling per step + determinism**: deadline callback on every
   `on_step_begin`; `full_determinism = True` in the frozen config
   (a nondeterministic-kernel failure on the GPU would be a
   reported finding for review).
8. **Reproducible suite**: the unclosed `trace.open()` is gone
   (`read_trace` reads-and-closes everywhere — module and tests);
   no bare `.open()` iteration remains in the package.

Additional acceptance gates (all mechanical, persisted in the
validation record and rederived by the verifier): identical
checkpoint-zero hashes; identical interrupted/uninterrupted bundles
AND trace prefixes at checkpoint 3; ≥1 reward-varying generated
group; a nonzero checkpoint-zero → checkpoint-3 adapter update
(refusing the zero-gradient trajectory that would make resume
trivially "exact").

## 3. Portability note (nonblocking item)

`support_run.restore_surface_evidence` is now the PRODUCTION restore
path for committed surface evidence (the 233_f reconstruction,
including the deterministic trace gunzip); the CPU tests consume it
— so the frozen config re-verifies against the committed Step-4
artifacts on any clean clone through production code, not a test
helper. The picome launch additionally retains the verified local
`runs/routing-dev/support-v1/` tree as its prerequisite.

## 4. Next

The 235_s changed-lines review of this rev2, then the GPU run:
`execute_resume_validation(expected_freeze_sha256="711c8204…",
expected_head_sha256="264066e6…")`, its close-out record, and the
unchanged grouped-probe freeze (step 6).
