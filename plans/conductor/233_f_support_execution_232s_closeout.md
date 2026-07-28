# 233_f — Step-4 close-out (response to 232_s)

Both findings are fixed; no GPU rerun, no ledger change. Step 4 is
formally closed and Step 5 is next.

## 1. The complete trace archive is committed (finding 1)

`plans/conductor/evidence/routing_dev_support_v1/surface/traces/
traces/` now holds the trace manifest byte-for-byte and
`steps.jsonl.gz` — a DETERMINISTIC compressed copy (`gzip -n -9`,
no timestamp/name header; 364 KB for the 17 MB JSONL). Restoration:
`gunzip -c steps.jsonl.gz > steps.jsonl` reproduces the exact
original bytes — sha256 `d62ac1e1…`, equal to the surface lock's
`trace_steps_sha256` binding.

**Clean reconstruction demonstrated this session**: a replica run
directory was assembled from COMMITTED bytes only (the four
prelaunch records, the six surface files, the trace manifest, the
decompressed trace steps, and the five run outputs — all 17
terminal files) and passed the full
`support_run.verify_terminal_outputs` against the recorded complete
closeout: exact 17-file inventory equality, execute-environment
self-hash, run-record identity cross-checks, the fail-closed
`load_dev_surface` reload under the closeout's lock, comparator
rederivation, and the population cross-check. A clean clone can now
reconstruct and fully verify the run.

## 2. Erratum: the admitted-launch identity in 231_f (finding 2)

231_f §1 mislabeled `6506f117…` as the launch entry. The correct
ledger sequence (the artifacts and chain were always correct; this
is a prose correction, recorded forward — 231_f stands as written):

- admitted support launch: **`f0d4651c…`** (entry 1)
- complete closeout: **`6506f117…`** (entry 2)
- provisional reserve / current ledger head: **`264066e6…`**
  (entry 3)

The 231_f commit message carries the same mislabel; it is not
amended (pushed history), and this erratum is the record.

## 3. Reviewer findings adopted into the plan (no freeze changes)

232_s's independent verification (all 4,824 trace rows accounted:
1,136 successes, 2,240 typed failures, 1,448 expected dependency
blocks; zero infrastructure/world failures or token-cap events;
cost and reserve rederive exactly) and its reading are adopted:

- **The frozen first probe is UNCHANGED**: 108 bound observations,
  4 groups/observation, G=8, 3,456 completions. Denominators for
  its review: 432 groups; 216 Code-bearing; 24 on direction-bearing
  observations (16 w2-favoured, 8 w3-favoured) — OPPORTUNITIES
  only; few or zero exact contrasts is underexposure evidence, not
  a failed experiment. The probe primarily measures structured-
  action validity, family routing, semantic reward variance, and
  actual specialist co-sampling.
- The support reads as **family routing plus coarse task/renderer-
  conditioned model choice** (6/54 direction-bearing over five
  independent latents; five of six under `goal_first`; no
  within-cell bidirectionality; oracle-over-`c_fixed_dev` headroom
  ≈ 1.85 pp within Code-bearing cells) — narrower than rich
  per-instance selection, and the P0 design must treat it that way.
- **Direction-enriched P0 support is likely** and will be
  explicitly outcome-conditioned: latent-level selection with full
  renderer crossing, seeking more w3-favoured cases, non-
  `goal_first` cases, and ideally within-cell bidirectionality;
  with many cell × renderer × direction strata empty, the
  charter's exact-final-P0-cohort zero-update exposure sample is
  the safer route (over stratum reweighting); natural-mixture
  evaluation stays alongside any enrichment.

## 4. Next (the 232_s sequence)

1. ~~Archive traces + erratum~~ — this document.
2. Prepare/review and freeze the Step-5 GPU resume-validation
   tranche with an EXACT ceiling (212_f reminder 2), including the
   real GRPOTrainer checkpoint wiring it must exercise.
3. Run and close out resume validation.
4. Freeze and run the unchanged grouped probe.
5. Design P0 from the probe's MEASURED exposure, not surface counts.
