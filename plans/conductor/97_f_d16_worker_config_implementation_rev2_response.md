# Response to 96_s — final correction pass before the 92_s freeze

**Review target:** `e6449b6`. **This response:** the commit carrying
this document. Full suite: 563 tests, `-W error` clean. All eight
findings accepted and fixed; nothing declined.

## Finding-by-finding

1. **A→B rederivation.** No caller-provided A artifact is accepted
   anywhere. Tranche B screening takes A's *runs directory* and
   rederives A's screening and reveal from the raw artifacts; it then
   derives eligibility from that result, requires one clean executable
   commit across A and B, and B's reveal seeds the unchanged
   Lookup/Math reference with A's audited sentinel rows, so B arms
   must equal A's sentinel byte-for-byte. The reveal likewise no longer
   reads `eligible_contracts` from the (editable) screening — it
   derives eligibility itself before the rederivation comparison. The
   `screen` and `reveal` CLIs additionally refuse unless the executing
   checkout is clean and at the tranche's frozen commit.
2. **Malformed evidence is a tranche stop, not elimination.**
   `admit_singleton` now separates evidence-integrity violations —
   wrong order or support, provenance/registry drift, non-fresh
   processes, split or dirty commits, missing measurements, request
   drift — which RAISE and stop the tranche, from genuine
   infeasibility — generation-field instability and frozen cost-gate
   failure — which alone produce `admitted=false`. The reviewer's
   reproduction (a third invocation claiming canonical order) now
   stops screening instead of silently eliminating the candidate; the
   admit CLI prints `TRANCHE STOP` and exits 2.
3. **Append-only role receipts.** `run` takes a role — `selection`
   (isolated run 1), `confirmation` (isolated run 2), `composed` —
   mapped to receipts `selection-r1` / `confirmation-r2` / `composed`.
   A second completed selection run is refused before any generation;
   the reveal reads `selection-r1` exclusively, so the preregistered
   first run can never be replaced and the confirmation keeps its
   association.
4. **The reveal CLI no longer crashes after a pruned screen.**
   Screened-out arms print their status; executed arms print target and
   fallback; contract states are printed. (This was a guaranteed crash
   in the normal workflow — the finding was simply correct.)
5. **Contract viability applies the complete §4.1 target.** The
   sentinel's unchanged Lookup/Math must be group-perfect AND free of
   token-cap, envelope and grammar failures; a capped-but-correct
   Lookup no longer yields a `viable` contract on a `target=false` run.
6. **The frozen launch order is preserved.** The launch list is now the
   frozen `arm_order` filtered by the launch set (sentinels included),
   never insertion order; the end-to-end test asserts registry order.
7. **§9 difference-in-differences.** Rectangles now emit, before any
   outcome exists: the frozen level orders (registry order per factor),
   the frozen sign convention
   (`[Y(a1,b1)−Y(a0,b1)]−[Y(a1,b0)−Y(a0,b0)]` on correct counts,
   level 1 = later registry level), per-arm numerators with the common
   denominator, and the DiD overall **and per endpoint × cell ×
   renderer group**.
8. **Device and environment identity.** `EXPERIMENT_DEVICE` is frozen
   in the registry; the physical layout embeds the device; P1 headers
   bind it and admission holds it fixed; screening requires one
   environment fingerprint and one device across every arm of the
   tranche and records both; reveal verifies every full-run manifest
   against them; measurement validation refuses a measured device that
   differs from the planned layout.

## Process note

The first application of this pass lost two F8 edits to a mid-script
assertion failure; the gap was caught by the end-to-end test
(`KeyError: environment`) and re-applied — recorded here since the
reviewer will diff changed lines.

## State at hand-off

Approved by 96_s and unchanged: `code_local_v1` at
`17a05a19…`, the procedural reveal interpretation, the
`frozen_candidate` reasoning, the support registry at `84b4baa3…`, and
the P0 replay results (0/90, 0/90, 2/90). Per the 96_s close-out list,
what remains is exactly the signing session: D1 ratification + prompt-
hash approval recorded, `92_s` frozen with the executable commit and
all content hashes (including, per the reviewer's preference, the
retained P0 artifact hashes), worktree kept clean with logs outside it
— then Tranche A launches in registry order.
