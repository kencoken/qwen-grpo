# 160_f — Amend-once Unit A: evidence archive and amendment contract

Unit A of 158_s §10, on 159_f's acceptance. CPU-only, execution-free;
nothing statistical ran. Full CPU suite: **749 passed** under
`-W error` (14 new Unit-A tests).

## 1. v1 evidence archived and verified (158_s §2)

`plans/conductor/evidence/stage1_pre_ce1_v1_ae26ba5d/` now holds the
exact bytes (`cp -p`, never regenerated) of all seven frozen files plus
the post-hoc diagnostic — every SHA-256 verified equal to the 157_f/
158_s values at copy time and re-verified by `verify_v1_evidence_archive()`
(the entry gate the amended lock will call). Added:

- `agreement_diagnostic_script.py` — the exact retrospective
  regenerating script, labelled post-hoc descriptive, pinned to v1
  commit `da8424b` for regeneration;
- `evidence_manifest.json` — byte lengths, hashes, roles
  (frozen / post-hoc descriptive), and the identity block (153_f hash,
  reviewed executable commit `75b852f…`, lock commit `da8424b…`, source
  digest `8034178f…`, execution identity `ae26ba5d…`, outcome commit
  `20507e6…`). Manifest SHA-256 at archive time:
  `8acecc77a2b9fff9391195f60185191188df106d4216f55f5394dcb1bb69bc95`
  (returned by the verifier; the execution bundle binds it).

Tamper probes are tests: a flipped byte, a missing file, and a
manifest/bytes disagreement each refuse.

## 2. The amendment contract (`tasks/conductor/stage1_amend1.py`)

- **Identities (§9):** `stage1-validation-amend1-v1`,
  `stage1-replay-amend1-v1`, `stage1-tranche-artifact-amend1-v1`;
  attempt id `stage1-pre-ce1-amend1-attempt-1`; run roots
  `runs/stage1-validation-amend1/`, `runs/stage1-replay-amend1/`.
- **Seed domains (§9.3):** `seed(domain, key)` with the frozen
  derivation; A/C under the fresh domain, D/B under the retained v1
  domain — `seed(DB_SEED_DOMAIN, k) == scenario_seed(k)` is asserted
  by test (D per-trial and B per-completion seeds reproduce v1
  exactly), and A/C keys are asserted to differ from v1.
- **Canonical seed registry:** 48 A-position + 24 A-router + 48
  C-path + 40,000 D per-trial entries (40,120 total; B's 9,216
  concrete completion keys join at lock when the support ids bind
  into the bundle), with a deterministic content digest
  (`seed_registry_digest`) for the bundle.
- **Amended registries:** the 48 coupled C paths
  (`C|{schedule}|{elig}|{theta}|{dist}|10000|coupled-path-v1`, no look
  component) and the 120 marginal look summaries (fork marginals at
  the AMENDED looks 100/500); the eight amended D ids with §6's
  alphas (D6 id retained/statistic amended; D7/D8 new frozen ids).
- **Persistence branch contract (§4):** boundary r = 0.10; frozen
  branch names; `persistence_tail_allocation` (ordinary
  a = 0.05/3 → a_zero = a_ratio = 0.05/6; fork a = 0.05/2 → 0.05/4);
  80 bisection iterations, 1e-12 endpoint atol; the exact per-look
  serialization field list. The statistic itself is Unit B.
- **Execution bundle (§9.1):** `build_execution_bundle` /
  `validate_execution_bundle` — all 13 required fields, frozen
  attempt-id/tag/root literals enforced, canonical self-hash as the
  amended execution identity; tamper and missing-field probes refuse.
- **Atomic run-root claim (§9.2):** `claim_run_root` — ANY
  pre-existing path, including an empty directory, refuses.
- **Old-artifact refusal:** `finalize_artifact`/`load_artifact` take a
  tag (default v1); a v1 artifact refuses an amend1 loader and vice
  versa (tested both ways).

## 3. Fork cap (100,200) → (100,500) applied (§5.1)

`NAMESPACE_CONFIG` qualification fork cap 500 with look schedule
(100, 500); `stage1.FORK_LOOK_SCHEDULE = (100, 500)`. Verified
ripples: fork tail alpha unchanged at 0.05/2 (still two looks);
`PERSISTENCE_LOOKS`/`POSITION_SCENARIOS`/manifest per-look blocks/
prefix machinery follow automatically; the aggregate-router support
stays at the first 100 per cell. Five existing tests updated to the
amended cap (each annotated with the 158_s citation).

**Mechanical cost deltas of record** (CE0 measured basis,
0.377 s/generation in-process): fork qualification surface at cap =
500 × 40 = 20,000 physical generations (was 8,000) — worst-case
+12,000 generations ≈ +75 min worker time, incurred only if fork
expands to its terminal look; registered-maximum projections update
accordingly in the final successor's cost table. D2's sequential fork
scenario runs ≈ 2.5× its v1 wall (500 vs 200 clusters/look) — carried
into the §5.4 pre-lock benchmark.

## 4. Deferred per 158_s §10

Unit B: the score/Fieller statistic, zero-event branch implementation,
coupled-path C runner, timing/reference probes. Unit C: D runner
changes (10,000 inner, agreement-path removal, D2 schedule literal,
D6–D8 reissue), the B C2/C1 decision matrix, aggregate updates.
Unit D: changed-lines review, the final placeholder-free successor,
and the separate lock. The v1 `stage1_tranche`/`stage1_validation`
machinery is intentionally untouched this unit except for the tag
parameter — the v1 D2 literal `(100,200)` remains until Unit C.
