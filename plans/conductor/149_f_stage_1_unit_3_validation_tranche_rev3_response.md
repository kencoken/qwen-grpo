# 149_f — Response to 148_s (rev-3 lock review)

All six blocking findings and the smaller correction are implemented.
`147_f` is preserved at its reviewed bytes; the preregistration of
record is reissued as
`150_f_stage_1_unit_3_validation_tranche_prereg_rev4.md`. Unit-3 tests:
71; full CPU suite: **732 passed** under `-W error`. No frozen
simulation or GPU replay executed.

**1. Seeds verbatim — fixed.** The `% 2**63` is removed from
`run_replay`; `completion_seed` outputs (full unsigned 64-bit, exactly
as preregistered) are applied directly via
`torch.manual_seed`/`torch.cuda.manual_seed_all`.

**2. Model condition — fixed, with the honest framing.** The replay
now constructs the model with the same frozen kwargs the Stage-2
trainer freezes: `torch_dtype=torch.bfloat16`, `sdpa`, NF4
double-quant, `prepare_model_for_kbit_training` applied explicitly
(TRL's path), and `LoraConfig(..., task_type="CAUSAL_LM")`. The
"byte-identical Stage-2 sampling path" claim is withdrawn everywhere:
B is described as a **separately frozen singleton replay regime**
(`regime: "singleton-replay-v1"` in the contract) — singleton batching
is deliberate (D16 batch sensitivity) and incompatible with
byte-identity to trainer rollouts, so the contract says what it is.

**3. B evidence verified at the consuming boundary — implemented.**
New `verify_replay_evidence(artifact, env_manifest, replay_manifest,
raw_completions_text, surface, support_rows)`:

- `validate_env_manifest` (new, in `stage1_manifest.py`) proves the
  execution identity IS the content hash of a valid
  `stage1-environment-v2` manifest with the current source identity —
  `aggregate_verdict` uses it too, closing the "same 64-hex string"
  gap;
- the replay manifest must self-hash, carry the frozen
  `REPLAY_CONTRACT` verbatim, and bind the same execution identity;
  the artifact must name exactly that manifest;
- the raw-completions file must hash to the artifact's
  `raw_completions_sha256` and cover exactly the 9,216 keys;
- the pair table and observation meta are REDERIVED from the pinned
  surface and support rows and must equal the embedded copies;
- all completions are REPARSED (`recount_from_raw`) and must reproduce
  the artifact counts exactly.

`aggregate_verdict` consumes B only as this evidence bundle; the
148_s attack — a self-rehashed artifact turning blocking results into
`unknown`/`confirm_possible=True` — is a named refusing test.
`load_b_artifact` is relabeled structural-only and additionally
requires `raw_completions_sha256`.

**4. Agreement represents D1 — fixed.** Stake-ordinary agreement
datasets now use the exact D1 shape (five equally weighted σ = 0.75
cells at the ordinary looks); stake-fork uses the D2 shape; the
equivalence family alternates the +0.10/−0.10 boundaries; pilot uses
the D5 shape (heterogeneous σ, unequal counts 12×5+6).

**5. Real aborts and failure records — implemented.**
`run_d_battery_scenario` takes an in-loop deadline (checked every 50
trials) and interrupts mid-scenario, carrying the partial error count
in the abort message. `run_full_tranche` refuses to overwrite an
existing formal run directory, persists every stage boundary as it
completes (environment manifest first, then deterministic-set outcome,
benchmark + deadline, A, C, agreement, each D scenario's partial
result and wall time), and writes an `aborted` run record with the
error on any failure — an agreement failure or runtime abort now
leaves the complete evidence trail on disk. The replay directory has
the same refuse-overwrite rule.

**6. Preregistration consistency — reissued forward.** 150_f rev 4
corrects "64-sample denominator" → 256 and replaces the "per-completion
seed table" promise with what the implementation does: the manifest
carries the deterministic seed RECIPE, applied verbatim (no modulus);
the exact seeds are a pure function of it and no table is persisted.

**Smaller correction — fixed.** `sequential_stake_decision` computes
its point estimate with the new `point_estimate` — the same
eligible-cluster, equal-cell statistic the bootstrap resamples; a NaN
row no longer poisons the point, and a zero-eligible cell leaves the
gate unresolved.

Per 148_s, only a mechanical verification of these exact points should
now be needed before locking.
