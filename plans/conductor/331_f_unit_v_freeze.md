# 331_f — Precursors plan LOCKED; Unit V: the routing_dev_val freeze (for review, BEFORE any GPU launch)

The precursors plan is locked at its signed rev3
(326_f/328_f/330_f @e381980). This is the Unit-V preregistration:
V1 (the outcome-blind cohort + evaluation identity) is
implemented and frozen; V2 (the GPU tranche) and V3 (the lock)
are implemented and tested but launch ONLY after this freeze is
signed. Full suite: **1026 passed under `-W error`, TRUE exit 0**
(1023 + three new tests; the standing spine gates pass inside
it).

## 1. Identities

- **`VAL_CONFIG_SHA256` =
  `4d717337e5d765b2186a67a994e46eb7f5d89adc9f8b22ac802387e0943d1818`**
- **freeze record (`val_tranche_freeze`) =
  `43c60a40cc89f2de0c554d55693072e06675a8828f78ec8f2c22e040e30fbc6f`**
- lineage parent = the C2 closeout `2bf50c1e…` (the current
  verified ledger head, 17 entries); `outcome_informed: False`;
  `cohort_selection: outcome_blind`.

## 2. V1 — the outcome-blind cohort + the complete evaluation identity

`tasks/routing/p0_val.py`, all CPU:

- namespace `routing_dev_val`; the six cells equally; the
  DETERMINISTIC latent prefix 0–4 per cell; ALL THREE renderers;
  **90 observations** in canonical (cell, index, renderer) order;
  visibility private; the frozen 211_f natural-mixture weights.
  The reviewer's planned-volume figure reproduces exactly:
  **4,020 planned step executions** (in the freeze record).
- **Common-random-number seeds (330_f §1)**:
  `seed_for_completion(observation_id, completion_slot)` =
  sha256(domain ‖ base_seed 20260804 ‖ observation_id ‖ slot) mod
  2³¹ — the signature has NO checkpoint parameter (asserted in
  test); identical draws at every checkpoint; distinct across
  slots, observations, and domains (`p0_val_eval` here).
- decoding from the canonical runtime profile `202bc377…`
  (temperature 1.0, cap 128, G=8); batching = one 8-completion
  group per observation per checkpoint in the bound order;
  framing = paired latent-level DESCRIPTIVE evidence (5 clusters
  per cell), carried into the lock and every report.
- **Substantive semantic separation (330_f §5)**:
  `semantic_overlap_report` normalizes away
  namespace/identity-only latent fields (id, namespace, index,
  identity-derived seed, and the non-serializable factor object
  whose content is already in the semantic fields) and checks the
  RENDERED POLICY PROMPTS carry no identity strings (guarded in
  code — a prompt embedding an id would make the check
  tautological and refuses). Measured NOW against the locked
  extension (training) surface: **semantic intersection 0 of
  30 vs 288; prompt intersection 0** — and the forged-collision
  regression proves the check bites. Identity disjointness across
  namespaces is asserted by regeneration (routing_dev and
  routing_dev_cycle ids at the same coordinates never collide).
- a mutated `VAL_CONFIG` refuses at every consuming function
  (hash-guarded).

## 3. V2 — the launch (implemented; NOT launched)

`prepare_val_launch` / `execute_val_run` — the two-phase
support-run pattern with a VAL-specific manifest
(`routing-dev-val-launch-v1`): NO probe rule (nothing is selected
from this surface); the outcome-blind prefix check retained; the
manifest binds the frozen `VAL_CONFIG` hash, the declaration, the
driver digest (`tasks/routing/p0_val.py`), the environment bytes,
the 90-observation search cap, and the **0.35 GPU-h budget**.
Execution: full pre-admission validation → ledger admission
(kind `support_materialization`, on the verified head) →
`materialize_dev_support` (the frozen §4 machinery, complete
authenticated 4^S surfaces) → `build_surface_lock` → the
POST-RUN semantic-overlap gate (the §2 predictions falsified
in-run) → the val lock → closeout binding the terminal artifact
bytes and the rendered-observation count. Abort path: partial
evidence content-hashed in an aborted closeout; the 330_f §5
retry rule applies (a partial materialization is never locked;
identical-design retries get a new execution identity and
cumulative accounting).

## 4. V3 — the val lock

`build_val_lock` (written exactly once): binds the config hash,
the cohort, the natural-mixture weights, the COMPLETE evaluation
identity (ordered observation ids, seed rule, decoding, batching,
framing), the surface-lock self-hash AND file hash, the
never-trained-on statement (structural — the P0 trainer consumes
only the pinned mixture `135a72bf…`), and `development_only`.
Its `record_sha256` is the `routing_dev_val_lock_sha256` pin the
`P0LaunchFreeze` consumes; `load_val_lock` REQUIRES the
externally reviewed hash.

## 5. Registered falsifiable predictions (in the freeze record)

1. identity intersection with ALL namespaces = 0 (verified CPU);
2. normalized semantic overlap = 0 AND rendered-prompt overlap =
   0 vs the training surface (verified CPU; re-verified in-run as
   the post-run gate);
3. complete 4^S surfaces for every observation (the surface lock
   refuses otherwise);
4. measured cost 0.05–0.15 GPU-h within the 0.35 ceiling
   (calibration: 864 observations = 0.4934 GPU-h).

## 6. Next

Reviewer sign-off on THIS freeze → V2 launch (admission on the
verified head) → V3 lock → Unit Y (cycle + the final R_cycle
reserve record). Lineage 332+.
