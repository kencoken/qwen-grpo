# 129_f — Stage-0 completion: 128_s erratum dispositions and closure

This is the paired response to `128_s_stage_0_go_no_go_closure.md` and
the terminal record of Stage 0. **The GO stands.** The commit carrying
this document is the Stage-0 closing commit; `127_f` is preserved at
the exact bytes `128_s` reviewed (commit `242f1c1`, plus one disclosed
pointer block), and every correction lives here.

## Record-organization narrative (disclosed)

`128_s` offered two paths for its record-only corrections: correct
`127_f` in place, or supersede in the Stage-1/2 redraft. The
corrections were FIRST applied in place (commits `afc688f`/`f1529be`:
header, benchmark-table rows, the gates paragraph, an appended erratum
section, a naming note). On Ken's review of that state, the record was
reorganized to the present, cleaner form — a third mechanism, more
conservative about the reviewed artifact than either named option:
`127_f` forward-reverted to its reviewed bytes and all corrections
consolidated here. The interim state remains visible in git history;
nothing was force-pushed or rewritten.

## Dispositions of the six 128_s corrections

1. **Seed estimate rescoped.** The handoff's 43.4-minute "first seed"
   prices the 18-observation *diagnostic* surface only. The planning
   numbers are the 128_s reference-scale projections
   (100 latents/cell): ~32,400 payoff rows, ~12,400 expected physical
   generations, ~78 min materialization, **~2 h per seed including
   training**; even a pessimistic no-dedup extrapolation is ~9.1 h —
   all inside the 12 h gate, which therefore still passes. The real
   estimate is recomputed when the Stage-2 population and schedule
   freeze.
2. **"Live worst case" renamed the reference-route live benchmark.**
   Its family-reference routing selects worker 2 at every Code node,
   so worker 3 was not exercised by that benchmark. Worker 3 WAS
   exercised by the complete materialization — all four logical
   workers evenly, 31 distinct requests each (128_s verification).
   The selected pre-materialized mode is unaffected.
3. **"17/18" counts terminals reached, not verified-correct answers**;
   the identity of the `math_code × goal_first` miss rests on the
   earlier surface evidence, not the persisted CE0 result.
4. **Gate provenance distinguished.** The VRAM and seed gates are
   computed from CE0 measurements; the `no_infra_failures_as_reward`
   flag and the sane-distribution gate are **manually carried prior
   evidence** (the recorded unit-4 smoke; the trainer-callable abort
   tests) — supported facts, but not values the CE0 command
   recomputed. The automated `go` flag mixes the two; this record is
   the distinction.
5. **Prediction wording corrected.** The full-command materialization
   wall (51.1 s) *beat* the 90–240 s prediction rather than falling
   inside it, and the "startup+loads 4.4 s" gloss was wrong: model
   loading is lazy and occurred inside the 46.7 s in-process
   materialization timer; the 4.4 s is interpreter and import overhead
   only.
6. **Content addresses and the carried prerequisite.** The CE0
   materialization manifest: `runs/ce0/materialize/manifest.json` =
   `1e52c399a6e60ebe7c0d475ec3c5f8374f5cd9ca963d63d5c86365cb8f12b6f7`.
   The formal construction difficulty-band decision — especially the
   `math_code` index band (the D16-era ≤8 mitigation) — is added to
   the `127_f` Stage-1 prerequisite list as item 4's extension, to be
   decided before the construction screen.

## Naming corrections at closure

The reviewer documents 108/110/113/115 were misprefixed `_f` and are
renamed `_s` (`git mv`, commit `afc688f`). Citations in the 11
non-freeze-digested code files (60 occurrences) are corrected in place
(`f1529be`). Exactly three citations remain under the original name:
comment strings in the freeze-digested `workerpool.py`, **queued for
the Stage-1/2 launch-profile freeze** (when the successor source
digest is issued anyway) rather than regenerating the closed Stage-0
freeze for a comment edit. Ken-decided: the 10 old-name citations in
historical review-cycle documents (109/111/112/114/116_f) stay as
written, per the `81b7ec6` rename precedent — historical citation text
is never rewritten; the mapping is one-to-one. In-code citations in
freeze-digested source likewise stand until that freeze.

## Closure statement

Stage 0 is **closed — GO with this record-only erratum** (128_s's own
characterization). The authoritative closure set is: `127_f` (the
handoff as reviewed) + `128_s` (the close-out review) + this document.
Frozen identities, carried evidence and Stage-1 prerequisites are as
recorded in `127_f`, read together with the dispositions above. The
branch `conductor_stage_0b_d16` at this commit is ready for the merge
decision; the next work item is the Stage-1/2 revision design document.
