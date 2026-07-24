# 157_f — Unit-3 tranche execution outcome (partial: stopped at the
agreement gate)

**Executed under lock 156_f** (prereg 153_f @ `235acb78…`, lock commit
`da8424b`, clean tree). The tranche ran the frozen order and **stopped
fail-closed at the agreement gate: 998/1000 agreements, one dataset
short of the 999 minimum** (one-sided 95% Wilson LB ≥ 0.995). The
reduced-replicate D battery refused to run, exactly as designed; the B
replay was not started (the frozen order stops at the failed gate).
Every stage boundary persisted; total wall 420 s. This document is the
execution record and the verdict input for the single reviewed
amend-once decision. It proposes nothing that runs.

## 1. Execution identity and artifacts

Execution manifest `ae26ba5d…` (self-hashed `stage1-environment-v2`,
clean tree at `da8424b`). Persisted, content-addressed:

| artifact | sha256 |
|---|---|
| `env_manifest.json` | `caa666660ee4ebbbf88189771fc8f2322799964f891a1a68fbc1fac639c7b189` |
| `deterministic_equivalence.json` | `12c48da5e2a57e2f2f9a011cd9acbe3d903ee1aaa306fb52b01f9877a3d940cd` |
| `benchmark.json` | `1fd09bff0b9fc7476b8a72cca2e4700e9af4c8ba30506aa2185b1b4ba5cf07e3` |
| `artifact_A.json` | `3ad61310142e1c07062e77afff9da764a5fd4d14c0a6b6456efa8359251eae24` |
| `artifact_C.json` | `eb4c13912f7f4da1f7f7511fb5021852af39367545964efbf3186b652ea900a7` |
| `agreement.json` | `21f8267c42bf6546b02736b909df37c11660ceda4e2bc2ea67d38a34f806f492` |
| `run_record.json` (aborted; wall times) | `6a0b6fac3561f45bf439415b5f84a6a1ca1caf05485b1430f251bc6055a71cf0` |

Deterministic equivalence set: **exact match** on all six analytically
forced decisions. Benchmark: 0.187 s/outer trial (in-loop deadline
3,734 s/scenario, never reached).

## 2. Check A — PASSED every gated cell (predictions hit)

All 8 gated position cells and all 4 gated router cells pass the 80%
Wilson criterion, most with enormous margin:

| cell | predicted (terminal-look LB) | measured ever-pass | Wilson LB |
|---|---:|---:|---:|
| ordinary_div1 δ=.15 σ=.50 | 0.987 | 0.9950 | 0.9937 |
| ordinary_div2 δ=.15 σ=.50 | 0.987 | 0.9936 | 0.9921 |
| ordinary_div3 δ=.15 σ=.50 | 0.987 | 0.9946 | 0.9933 |
| fork_div3 δ=.15 σ=.50 (worst gated) | 0.921 | 0.9432 | 0.9393 |
| router core eff=.10 σ=.50 | 0.994 | 0.9972 | 0.9962 |
| router core_fork eff=.10 σ=.50 | 0.998 | 0.9989 | 0.9982 |

Mandatory disclosures: δ=0.10 sits at its point-materiality boundary
(ordinary 0.6875 ever-pass, fork 0.5291 — as 132_s anticipated);
stress σ=0.95: ordinary 0.9035 (predicted 0.880), fork 0.4540
(predicted 0.436). The multi-look ever-pass values sit slightly above
the terminal-look analytic lower bounds, exactly as the prediction
model implies. **The look caps are adequately powered for every
required family/model position at the frozen materiality.**

## 3. Check C — zero-persistence PASSES; power criterion FAILS as
predicted (the amend-once trigger)

| criterion cell | measured pass rate | Wilson LB | predicted | verdict |
|---|---:|---:|---:|---|
| ordinary N=500 e=0.65 θ=0 | 1.0000 | 0.9997 | 1.000 | zero-persistence PASS |
| fork N=200 e=0.60 θ=0 | 1.0000 | 0.9997 | 1.000 | zero-persistence PASS |
| ordinary N=500 e=0.65 θ=0.05 | **0.5418** | 0.5336 | 0.541 | power **FAIL** (needs ≥ 0.80) |
| fork N=200 e=0.60 θ=0.05 | **0.1421** | 0.1365 | 0.144 | power **FAIL** |

Additional disclosure the amendment must confront: at θ = 0.10 — the
gate's own boundary — the envelope passes at rate ≈ 0.000–0.002. The
operational bound is so conservative that the gate as frozen
distinguishes only θ ≈ 0 from θ ≳ 0.05; it cannot admit a cell whose
true persistence sits anywhere near (even well below) the nominal 10%
threshold. The full 120-cell grid (including row-dispersed stress) is
in `artifact_C.json`.

## 4. The agreement gate — 998/1000, failed, and RIGHT to fail

The frozen criterion (145_s-directed: Wilson LB ≥ 0.995 ⇒ minimum
999/1000) failed by one dataset. The deterministic diagnostic re-run
(frozen seeds; same 998/1000) identifies both disagreements:

| dataset | family | boundary | 2,000-rep decision | 10,000-rep decision |
|---:|---|---|---|---|
| i=110 | pilot_unequal | δ=0.08 | **pass** | not_pass |
| i=383 | stake_fork | δ=0.12 | **pass** | unresolved |

Both flips are **anti-conservative**: the reduced-replicate
implementation declared `pass` where production said otherwise. Two
readings of the criterion existed in the lineage — 132_s's plain text
("agree at least 99.5% of the time": observed 0.998 would PASS) and
the 145_s-directed Wilson-LB reading (requires 999: FAILS). The strict
reading is the one that caught two anti-conservative boundary flips.
We consider this dispositive against relaxing back to the plain-rate
reading.

## 5. Prediction scorecard (141_f, unchanged through five revisions)

Every registered falsifiable prediction hit: A/router acceptance
passed with margin (worst gated cell 0.9432 vs predicted 0.921); the C
power criterion failed at both hard cells within 0.002/0.001 of the
exact-binomial predictions; zero-persistence passed everywhere. The
preregistration's model of the design was correct. The one outcome not
predicted was the agreement gate margin itself (998 vs 999) — no
prediction was registered for it.

## 6. Verdict input and the recommended single amendment

`confirm_possible` is **false** on two independent grounds: the C
power criterion (predicted; the §8.4C amend-once branch anticipated by
132_s itself) and the agreement gate (not predicted; makes the
2,000-replicate D battery unavailable as frozen). D and B never ran.

Per 132_s §8.4 the tranche outcome is ONE reviewed decision: confirm,
or amend once in a new reviewed plan before construction registration.
We recommend a single amendment covering both grounds:

1. **Persistence gate operating point (§8.4C ground).** The envelope
   as frozen is unresolvable-in-practice at the floors (§3 above). The
   amendment must sharpen the bound, change a cap, or change the gate
   (132_s's own enumerated options). We deliberately propose no
   replacement numbers here — that is the amendment plan's job, made
   with the reviewer against the full 120-cell artifact.
2. **D-battery replicate policy (agreement ground).** Run the D
   battery at FULL production replicates (10,000 inner), deleting the
   reduced-replicate approximation and with it the agreement gate
   (which exists only to authorize the reduction). Measured basis:
   0.187 s/trial at 2,000 replicates ⇒ ≈ 0.93 s/trial at 10,000 ⇒
   ≈ 1.3 h/bootstrap scenario, ≈ 6.5–7 h for the battery — inside the
   12 h single-tranche gate. The alternative (keep 2,000 and adopt the
   plain-rate reading) is rejected per §4: both observed flips were
   anti-conservative.
3. **Rerun scope.** Per 132_s, the amended tranche reruns every
   mechanically affected frozen check under a fresh lock and execution
   identity: A and C (cheap, ~1 min, unchanged machinery — their
   results above are expected to reproduce modulo the amended
   persistence gate's C evaluation), the D battery at the amended
   policy, and B (unrun; once, under the amended tranche's identity).

Until that amendment plan is reviewed and signed, no D scenario, no B
completion, and no construction work runs. Next lineage number: 158
(the amendment plan).
