# 127_f — Stage-0 go/no-go handoff (106_s §14)

**Decision: GO** (with the 128_s record-only erratum below). Every
§14 exit criterion is met; CE0 passed all frozen gates at the
preregistered commit, with every prediction confirmed or beaten.
Stage 0 stops here per §3: no construction, qualification or headline
GRPO seed runs under the 106_s document. Stages 1–2 are revised from
the measured four-worker evidence below.

## §14 exit criteria

| criterion | status | evidence |
|---|---|---|
| Cell-spec erratum signed + implemented | ✓ | 106_s §§6/8 (frozen, Ken-signed); units 1–4, per-unit reviews 108–125 closed |
| Registry + fingerprints frozen; D16 closed with the worker-side hashes as the selected artifact | ✓ | `wp-197e286115f56e4a`; rev10 bundle SHAs + `task_last` digest in the 106_s Freeze Record; D16's universal-worker requirement retired (§6.4) — the selected artifact is the four-worker pool |
| 0A compatibility tests + recorded agreement | ✓ | 674 tests -W error; 16,665/16,665 over exactly 10,000 latents (unchanged through every unit) |
| 0B real-pool smoke, cache/provenance, traces | ✓ | 114_f cold smoke (33 cold / 33 warm, byte-identical replay); slw-keyed cache isolation; v2 traces with producer verification |
| Deterministic w2-vs-w3 pair changes terminal reward; sampled completions drive the scorer; distribution recorded | ✓ | canary w2 0.5 / w3 1.0 exact (registered direction) in every consuming run; smoke 287/288 parsed actions scored through the single reward; full distribution in 124_f |
| CE0 memory/runtime/reward gates | ✓ | below |
| No construction examples beyond the consumed prefix; no qualification examples | ✓ | support = worker_dev ordinal 0; smoke items ⊂ consumed 0–29 D16 prefix; asserted per unit |
| Stage-1 prerequisites enumerated, not represented complete | ✓ | below |
| Handoff with commit/profile/artifacts/metrics/decision | ✓ | this document |

## CE0 (preregistered entry + results in conductor_log.md)

Executable commit `55a680f` (clean tree); artifact
`runs/ce0/ce0_results.json`
(`c52592b97d783f493f9c49e26081259025abda22d192c7122539894404d1731c`),
environment manifest inside (torch 2.11.0+cu130, transformers 5.13.0,
TRL 1.7.1, peft 0.19.1, bitsandbytes 0.49.2, driver 595.71.05,
RTX 4090 24564 MiB; `uv.lock` `f5486ec4…`).

| measurement | predicted | measured |
|---|---|---|
| materialization unique generations | 124 | **124** |
| materialization in-process / full-command | 46–55 s / 90–240 s | **46.7 s / 51.1 s** (startup+loads 4.4 s) |
| worker-phase device peak | ≤ 6 GiB | **3.77 GiB** |
| surface disk | ~3–4 MB | **3.6 MB** |
| reference-route live benchmark: physical generations | exactly 30 | **30** |
| reference-route live benchmark: wall / per-generation | ≤ 60 s | **9.5 s / 0.315 s** |
| reference-route live benchmark: terminals reached | **17/18** | **17/18** |
| enumeration (324 through S=3) | < 5 s | **< 0.1 s** |

**Gates (frozen):** max observed peak reserved VRAM 14.43 GiB
(training phase; worker phases 3.77 / 1.2 GiB) < 22 GiB ✓; projected
seed at the **diagnostic-surface scale**: first seed 43.4 min,
additional 42.6 min (pre-materialized; live mode 84.8 min) — and at a
100-latent-per-cell reference scale (128_s): ~32,400 payoff rows,
~12,400 expected physical generations, ~78 min materialization, ~2 h
including training; even a pessimistic no-dedup extrapolation is
~9.1 h — all ≤ the 12 h gate ✓ (the real estimate is recomputed when
the Stage-2 population and schedule freeze); zero infrastructure
failures represented as reward ✓; sane non-degenerate distribution
held by the recorded smoke ✓. Gate-provenance note (128_s): the VRAM
and seed gates are computed from CE0 measurements; the
no-infra-failures and sane-distribution gates are **manually carried
prior evidence** from the recorded unit-4 smoke and the
trainer-callable abort tests, not values the CE0 command recomputed.
**Deployment: pre-materialized routing (mode 1); modes 2/3 not
implemented, per the frozen §10.4 rule.**

## Erratum (128_s close-out pass — record-only; GO stands)

1. The 43.4-minute figure prices the 18-observation **diagnostic**
   surface, not a full Stage-2 seed; the reference-scale projection
   above supersedes it as the planning number.
2. The "live worst case" is renamed the **reference-route live
   benchmark**: its family-reference routing selects worker 2 at every
   Code node, so worker 3 was not exercised there. Worker 3 WAS
   exercised by the complete materialization (all four workers evenly:
   31 distinct requests each, per the 128_s verification).
3. "17/18" counts **terminals reached**, not verified-correct answers;
   the identity of the `math_code × goal_first` miss rests on the
   earlier surface evidence, not on the persisted CE0 result.
4. The automated `go` flag mixes computed gates with declared prior
   evidence (see the gate-provenance note above); the record now
   distinguishes them.
5. "Every prediction hit" is corrected: the full-command wall (51.1 s)
   **beat** the 90–240 s prediction rather than falling inside it, and
   "startup+loads 4.4 s" was wrong — model loading is lazy and
   occurred inside the 46.7 s materialization timer; the 4.4 s is
   interpreter and import overhead only.
6. The CE0 materialization manifest is content-addressed:
   `runs/ce0/materialize/manifest.json` =
   `1e52c399a6e60ebe7c0d475ec3c5f8374f5cd9ca963d63d5c86365cb8f12b6f7`.

Naming note (closure): the reviewer documents 108/110/113/115 were
misprefixed `_f` and are renamed `_s` at closure; historical documents
and freeze-digested source cite them by their original names, which
map one-to-one to the `_s` names.

## Frozen artifact identity (what Stage 1/2 consumes)

- Worker pool `wp-197e286115f56e4a` (4 workers / 2 checkpoints;
  parameters device-verified), rev10 bundle, `task_last` contract.
- Support declaration `6df4c42b…` (18 identity-selected observations);
  materialized surface manifest `221a04d5…` (324 rows, re-scoring
  fail-closed loader); canary + sentinel fixtures (`5ac8b52b…`,
  `cd143e07…`).
- Policy freeze `6cf44e2d…` (system prompt `fe9bba0d…`, 18 observation
  hashes, chat template, launch profile `0815c033…`, partial source
  digest — scope note and full environment provenance in 126_f).
- Recorded runs: unit-2 smoke, `runs/stage0-support`,
  `runs/stage0c-smoke-0815c033-221a04d5` (W&B `3satfxr9`), `runs/ce0`
  — all content-addressed in 124_f/126_f/this document.

## What Stage 0 measured (carried evidence)

- The pool is genuinely heterogeneous in both directions
  (`math_code×goal_first` needs worker 3; `fork_join×bound_var/
  goal_first` need worker 2; reference routing 17/18) — inside the
  frozen support and reproduced live in CE0.
- The few-shot-conditioned pretrained policy, while being updated for
  18 GRPO steps, achieved 48.3% rollout success (halves 38.9%→57.6%);
  the demonstration contribution is NOT identified (125_s) — the
  untrained-few-shot baseline is the mandatory Stage-2 comparison.
- Sampled scale contrast was one-directional (two worker-2-advantage
  fork groups); reward variance sparse (8/36 groups). The ≥64-group
  cold-start analysis remains a Stage-1 gate.
- Format is a solved layer: 144/144 reward-blind validity; 287/288 in
  the smoke.

## Stage-1 prerequisites — enumerated, NOT complete

1. CE1 gate table + population/execution manifests (built on the CE0
   environment-manifest machinery; complete source digest per 125_s).
2. The frozen <2% parse/truncation gate mapping onto two intentionally
   imperfect Code workers (per worker / per route / pool quantity) —
   CE1 decides before construction (106_s §15).
3. ≥64-group cold-start measurement per stratum (validity ≥80%,
   non-zero-variance ≥25%, win+lower ≥10%).
4. B1 control fitting; `SYSTEM_DIRECT` freeze (a Stage-1 prompt
   blocker, not part of the worker-side freeze); D4 consumed-prefix
   decision; the formal construction difficulty-band decision —
   especially the `math_code` index band (the D16-era ≤8 mitigation)
   — before the construction screen (128_s).
5. Stage-2 demonstration treatment (few-shot primary vs schema-only;
   untrained few-shot baseline mandatory; one-seed no-demo pilot
   preferred) — registered decision, 123_s §9.
6. Effective routing-stakes sufficiency per position; Stage-2
   cached-vs-live materialization policy (evidence: pre-materialized).
7. Deferred design notes: 107_s Code-only orchestration; the 103_s
   complementary-1.5B-policies orchestration prereg; `local_only` /
   BF16 / constrained decoding as later ablations; unseen
   paraphrase/semantic renderer before any generalization claim.

**Stage 0 is closed.** The next work item is the Stage-1/2 revision
from this evidence — a design document for review, not code.
