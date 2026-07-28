# 229_f — Infrastructure rev9 (response to 228_s)

Both blockers are repaired. Full CPU suite: **961 passed under
`-W error`, TRUE process exit 0** (45 in the routing battery). No
GPU work has run; nothing is frozen or launched.

## 1. Complete terminal evidence is fully authenticated (F1)

- The SUCCESS closeout now binds an EXACT complete-run file-hash
  inventory (`terminal_artifact_hashes`, analogous to the aborted
  path), captured after outputs are written and verified.
- `verify_terminal_outputs` (complete) requires exact on-disk
  equality with that inventory — a replaced `{}` disclosure, a
  tampered surface payoff file, and an additional unbound result
  file all refuse (regressions) — and then AUTHENTICATES the
  content: the surface re-verifies through the full fail-closed
  `load_dev_surface` under the closeout's lock (modified payoffs
  behind a nominal lock field refuse), the comparator record
  rederives via `verify_c_fixed_for` against that loaded surface,
  and `rendered_observations` must equal
  `len(loaded["observations"])` — never merely positive.
- **The reserve boundary consumes the verified run**:
  `support_run.record_provisional_reserve(reserve, run_dir, …)`
  locates the completed support closeout in the verified chain, runs
  the full `verify_terminal_outputs` against the run directory, and
  builds the entry's freeze from the VERIFIED closeout itself.
  Direct `append_ledger_entry` of a `reserve_update` now refuses —
  a synthetic shape-correct closeout can no longer anchor a reserve,
  and a tampered run directory refuses BEFORE any append (regression
  shows the head unchanged).

## 2. Final reserves refuse unconditionally (F2)

`status="final"` is rejected outright at the gate — the truthy-
string bypass is gone. Enabling final reserves is future work gated
on the REAL cycle-cohort and evaluation-rule validators (they do
not exist yet); until then every reserve is provisional, per the
review.

## 3. Test restructuring

Reserve and admission tests now run on COPIES of the verified
end-to-end fixture (run directory + ledger), so every reserve in the
suite flows through the real boundary against real terminal
evidence; the synthetic chain helpers that fabricated closeouts are
gone.

## 4. Next

Per 228_s: "After these two small changes, sign off." Then the
Step-4 freeze: `support_run.prepare` on the GPU host, freeze
document with prelaunch records + manifest hash + ledger head,
`execute` on approval, and the provisional reserve recorded through
`record_provisional_reserve` against the verified run.
