# 341_f — Unit V EXECUTED: the routing_dev_val surface is materialized and LOCKED (for execution sign-off)

The V2 launch ran under the 340_f-signed arguments
(`424b692d…` on head `2bf50c1e…`) and completed cleanly; the V3
lock was produced in-run and the chain-authenticated terminal
verifier passed both in-run and post-hoc. **Unit V's GPU work is
complete.**

## 1. Outcomes vs the registered predictions

| prediction (signed freeze) | outcome |
|---|---|
| cost 0.05–0.15 GPU-h within the 0.35 ceiling | **0.0637 GPU-h measured** ✓ |
| complete 4^S surfaces, all 90 observations | surface locked; `rendered_observations: 90`; the surface lock refuses otherwise ✓ |
| alpha-normalized semantic overlap 0 (hard gate) | 0 / 0 / 0 (val↔training, val↔cycle, cycle↔training) ✓ |
| disclosed template overlap equals the pre-launch measurements | EXACT: 21 collisions / 39 affected (val↔training); 15 / 30 (val↔cycle); 30 (cycle↔training) — frozen membership bound in the lock ✓ |
| identity intersection with all namespaces 0 | by construction; asserted in the standing tests ✓ |

## 2. Identities

| record | hash |
|---|---|
| launch entry (`val_materialization`, parent = the frozen C2 head) | `5ef73f79804730948109bb810822c47a66664e2562388cb2a480f3c6e83d9bc0` |
| surface lock | `3698caa180bea70f7df1b97ace7c480defeb97bc90d7b08c81da9d206b5309be` |
| **val lock — the `routing_dev_val_lock_sha256` pin** | `2aecdf28ad25cae10e494aa9fc1a95138a9feb5a29ab0636314b847987caf19d` |
| closeout = the NEW LEDGER HEAD (19 entries verify) | `929e172415845471f2fe613ef71a36eb57d47492cfa58c4e511e95403a5ed11c` |

Envelope: 3.1305 + 0.0637 = **3.1942 GPU-h consumed / 56.8058
remaining**; the provisional 5.0 R_cycle reserve intact (its
replacement is Unit Y). Evidence at
`runs/routing-dev/val-surface-v1/` (exact 16-file inventory bound
byte-for-byte by the closeout).

## 3. Verification

- The in-run terminal verifier ran BEFORE the success closeout
  (chain-authenticated launch; exact inventory; environment
  attestation; mandatory surface authentication; fresh three-way
  overlap recomputation).
- POST-HOC, from the committed ledger at the new head:
  `verify_val_run` = **PASS / complete**, re-authenticating the
  launch and closeout from the chain and recomputing the overlap
  gate fresh.
- `load_val_lock` rederives the cohort, evaluation identity
  (CRN seeds, full sampling options), canonical 1/90 weights, and
  the seed-schedule pin from the frozen config, and authenticates
  the surface bytes.

Launch-shell note (disclosed): two attempts to start the launcher
in a background shell failed at `import tasks` (the background
shell does not inherit the repo working directory) BEFORE any
validation or admission — no ledger entry, no file, and no GPU
work resulted; the script was made cwd-independent and the third
invocation is the recorded run.

## 4. Proposed at sign-off

1. Record `2aecdf28…` as the externally reviewed
   `routing_dev_val_lock_sha256` (the `PrecursorOutputs` pin).
2. Decide evidence archival: mirroring the extension pattern, the
   val surface + lock can be archived under
   `plans/conductor/evidence/val_surface_v1/` for clean-clone
   restoration (the P0 checkpoint evaluations consume this
   surface at run time). Proposed, not yet done.
3. Unit Y rev1 (cycle record + final R_cycle) and Unit T rev1
   (beta smoke) follow — drafts are staged out-of-repo per
   instruction and will be issued with this unit's hashes filled
   in.
