# 152_f — Response to 151_s (rev-4 mechanical review)

All five findings are implemented. `150_f` is preserved at its
reviewed bytes; the preregistration of record is reissued as
`153_f_stage_1_unit_3_validation_tranche_prereg_rev5.md`. Focused
unit-3 tests: 72 (including the two 151_s-requested probes); full CPU
suite: **733 passed** under `-W error`. No frozen tranche or GPU
replay executed.

**1. Real B evidence recounts — fixed.** `recount_from_raw` parses the
JSON-text `positions` that real `build_smoke_rows()` rows carry
(either list or JSON string accepted). The requested test uses actual
`build_smoke_rows()` output: it asserts the positions field IS a
string (the trap), crafts parseable completions in the real fork
positional order, and verifies exact k2/k3/n recounting.

**2. Authoritative inputs and regenerated manifests — implemented.**
New `load_pinned_replay_inputs()` is the consuming boundary's only
input source: the hash-verified pinned surface
(`verify_surface_pin`), the 18 support rows, and rendered-request
hashes REGENERATED through the frozen tokenizer and both pinned
prompts. `verify_replay_evidence` no longer accepts caller-supplied
surface or support rows: it rebuilds the COMPLETE expected replay
manifest — observation ids, eligible pairs, request hashes, contract,
and hash — via `build_replay_manifest` and requires exact equality
with the supplied manifest. The 151_s attack (a rehashed manifest with
one altered request hash) is a named refusing probe, alongside a
rehashed-contract probe and a tampered-pinned-surface probe.
`aggregate_verdict`'s B bundle shrinks to {artifact, replay_manifest,
raw_completions_text}; the test-only `pinned_loader` injection point
defaults to the authoritative loader.

**3. Zero eligibility stays unresolved — fixed.** When
`point_estimate` returns None, `sequential_stake_decision` skips BOTH
decision branches at that look (the adverse −∞ UCB can no longer fire
the conclusive-failure branch) and expands; unresolved at the cap
remains unresolved.

**4. Failure-path persistence completed — fixed.** The replay driver
claims its run directory, writes the environment manifest, the replay
manifest, and a `running` record BEFORE any model work; the generation
loop is isolated in `_generate` and wrapped so any abort (including
incomplete accounting) writes an `aborted` record with wall time; a
successful run writes `complete` with wall time. In the D loop, the
scenario wall time is recorded in a `finally` even when the in-loop
deadline interrupts mid-scenario; the partial error count travels in
the abort error text, which the outer handler writes into the aborted
run record.

**5. Rev-4 phrasing — reissued forward.** 153_f replaces the residual
"byte-identical Stage-2 sampling path" with the singleton-regime
wording, and the seeding description now states what the code does:
the GLOBAL CPU and CUDA RNG state is reset per singleton draw from the
preregistered seed — there is no per-draw generator object.

Per 151_s, the focused suite plus the real-row recount and
changed-request-hash refusal probes have been rerun green; 153_f +
this response stand for lock.
