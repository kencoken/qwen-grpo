# Unit 3 rev2 — response to the 118_s review

All three P1 findings fixed; the smaller canary finding fixed; the
surface cleanly rematerialized under the hardened schema (the
reviewer's simpler option). Battery: **653 tests** under
warnings-as-errors (rev1: 641); agreement unchanged at
**16,665/16,665**.

## F1 — the loader re-scores, never trusts

`load_support_surface` regenerates the observation→gold mapping from
the frozen generator and requires
`payoff == score_terminal(terminal_value, regenerated_gold)` for every
row — the reviewer's flipped-row reproduction (`0.5 → 1.0` with a
failed stored terminal) now aborts with the mismatch named. Rows are
exact-schema and exact-typed: unknown/missing keys, non-`str`
observation ids, `bool`-aliased assignment entries and non-exact-int
terminals all abort (regressions for each).

## F2 — the surface binds its complete execution provenance

The manifest is a versioned exact schema (`surface_schema_version` 1,
frozen key set — an invented field aborts) carrying content hashes of
`payoffs.jsonl` and both trace files. The loader verifies, in order:
manifest schema; declaration bytes; declaration-matching wv and pool
fingerprints; payoffs and trace content hashes; trace
`closed`/`status=complete`; trace wv/pool/rtp equal to the surface
manifest; `steps_written == planned_step_executions`; the generation
accounting invariants (`0 < unique ≤ uncached ≤ executed ≤ planned`,
`uncached + cache_hits == executed`); and the declared row count. All
four reviewer reproductions — invented pool fingerprint, invented
runtime fingerprint, contradictory counts, in-range payoff edits — are
now negative regressions (the in-range edit dies on re-scoring or, if
un-rehashed, on the content hash). A fabricated directory without a
real complete trace cannot pass.

**Unit-4 pin:** the rematerialized surface manifest hash is
`221a04d53403f14c537a3d43336eb6630ca6fe5682f5e3f8aa66f78ace679c23`
(`runs/stage0-support/manifest.json`); the §10.1 launch profile will
record it as the `precomputed_surface` binding.

## F3 — visibility is checked explicitly

`materialize_support` requires the runtime's `visibility_condition` to
equal the declaration's (it is deliberately outside the worker-visible
fingerprint, so it needs its own check), and both materialization and
loading verify the **complete** regenerated support description —
cells, renderers, arities, assignment counts, namespace/ordinal/
visibility constants, planned steps, worker ids and pool fingerprint —
not only observation ids. A `visible` runtime is refused (regression).

## Smaller finding — exact canary direction

`run_canary` now derives the expected reward pair from the registered
record and requires exact agreement (worker 2 → 0.5, worker 3 → 1.0);
a reversed disagreement fails with its own message. Both directions
are covered by a fake-pool regression pair.

## Rematerialization (RTX 4090)

Identical execution to rev1 — 324 rows, 560 executed step records, 124
unique singleton generations, 46.3 s, zero cold cache hits — now under
the v1 manifest schema with all artifact hashes, verified end-to-end
by the hardened loader, and the canary exact-check passing.

## Noted from the interpretation section

The reviewer's framing is adopted for unit 4's expectations: best
fixed Code choice (worker 2) 17/18, always-worker-3 16/18,
context-conditioned selection 18/18; equal-observation uniform-action
success ≈ 19.8% (not the row-weighted 7.4%); the unique fork winner
occupies 1/64 of valid actions (~12% chance a uniform group of eight
contains it) — family routing is expected to emerge before reliable
scale selection, with substantial zero-variance noise in fork groups.
CE0 will time full commands and record lifecycle peak VRAM, which the
47s materialization timer deliberately excluded.
