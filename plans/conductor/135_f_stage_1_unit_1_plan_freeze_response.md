# 135_f — Response to 134_s (unit-1 critique)

All three blocking findings are implemented; all six lower-severity items
are addressed (five implemented, one recorded for unit 2 with an enforced
floor). Tests: 130 pass in the unit-1/program files; full CPU suite green
under `-W error`. Point-by-point dispositions below.

## Blocking findings

**1. Fork intervention gates scoped to both edges — implemented.**
`stage1.py` now carries `INTERVENTION_DIAGNOSTICS`,
`CELL_INTERVENTION_EDGES` (`lookup_math`/`math_code`: `n1→n2`;
`fork_join`: `n1→n3` and `n2→n3`), and `intervention_gate_names(cell)`
generating the full edge × diagnostic cross-product as individually named
gates (`corruption_n1_n3`, `old_answer_persistence_n2_n3`, …).
`GATE_MATRIX` mandatory entries are built from that function, so the
matrix cannot drift from the edge table. Tests assert exact cardinality
(6 for fork, 3 per chain, 0 for atomic), uniqueness, membership of every
cross-product name in the cell's mandatory set, and that every edge
endpoint exists in generated reference programs.

**2. Protocol-denominator contract — implemented machine-readably.**
`stage1.py` now provides `WORKER_FAMILIES`, `NODE_FAMILIES`,
`RENDERERS_PER_LATENT = 3`, and:

- `on_contract_nodes(cell, worker)` — the on-contract stratum;
- `truncation_rows_per_latent(cell, worker)` = 3 × on-contract nodes;
- `selected_route_rows_per_latent(cell)` = 3 × S;
- `selected_route_rows_per_worker(cell, deployable)` = 3 × selected nodes
  per worker, validating that the mapping covers exactly the cell's
  semantic nodes with known worker ids (fail-closed on missing, foreign,
  or unknown entries).

`NODE_FAMILIES` is acceptance-tested against generated reference programs
(op → family over multiple latent indices per cell, covering template and
factor variation), and the full 6-cell × 4-worker on-contract table is
pinned literally in the tests. Unit 2 derives expected manifest counts
from these functions rather than re-deriving strata.

**3. Prompt candidates and format repair — implemented, taking the
recommended no-repair choice.**

- *Few-shot preserved and pinned:* `prompt_fewshot()` returns the exact
  `SYSTEM_CONDUCTOR` bytes and fails closed against
  `PROMPT_FEWSHOT_SHA256 = fe9bba0d…adb29070` — the full digest whose
  prefix is the Stage-0 policy-freeze identity (verified by test).
- *Schema-only defined and pinned:* `prompt_schema_only()` derives the
  candidate mechanically — `SYSTEM_CONDUCTOR` minus its trailing
  demonstration block — never retyped, and fails closed against
  `PROMPT_SCHEMA_ONLY_SHA256 = 9efe8998…c721e9fb`. Tests verify it is a
  strict prefix of the few-shot bytes ending at the output-contract line
  (`…nothing else.`), contains the `{"worker_ids": [...]}` contract, and
  contains no examples — exactly 132_s §10.1's "identical instructions,
  observation skeleton, and output contract with the demonstrations
  removed—no replacement task examples." No frozen file was edited; the
  derivation lives in `stage1.py`.
- *No-repair frozen:* `FORMAT_REPAIR_V1 = None` in `stage1.py`. Per
  132_s §10.1, with none frozen no repair is allowed; a format-failing
  candidate is simply ineligible. `policy_dev` cohort B (24–47) stays
  registered but unused and is never reassigned (comment updated in
  `program.py`, asserted by test). `133_f` §1 note 1 is corrected in
  place with a marked correction note — the unit is open under review, so
  this is an implementation-cycle fix, not a rewrite of a signed record.

## Lower-severity items

1. **`policy_dev_cohort` domain guard** — added: same plain-int rule as
   `generate_latent` (`bool` excluded explicitly, floats and strings
   rejected); tests cover `True`, `1.0`, `"0"`.
2. **`bootstrap_seed` canonicalization** — the function now takes a
   `Mapping[cell_id, look]` and builds the vector itself via the new
   `canonical_cell_look_vector()` (sorted by cell id; cells validated
   against the known six; looks validated against the correct
   ordinary/fork schedule). The manifest digest argument is validated as
   exactly 64 lowercase hex characters; empty gate ids rejected. Callers
   can no longer supply a non-canonical string.
3. **Shallow-router encoder frozen** — one-hot in frozen level orders,
   no hashing/embeddings, unseen level = load error: `cell_id` levels
   lexicographic (`SHALLOW_ROUTER_CELL_LEVELS`), `node_id` levels
   `(n1, n2, n3)`, subtype levels bound to the existing frozen
   `baselines.OBSERVABLE_SUBTYPES` contract, namespaced `cell:level` and
   concatenated in cell order (`shallow_router_subtype_levels()`), then
   numerics `(p, q, t, k, i)` with missing −1 — byte-compatible with
   `baselines.feature_row`'s conventions. Tested for completeness, order,
   and uniqueness.
4. **`contract.py` in the successor digest** — recorded as an enforced
   floor: `SUCCESSOR_DIGEST_REQUIRED_ADDITIONS =
   ("tasks/conductor/contract.py",)` with a test that it is disjoint from
   the historical eight. Unit 2's complete list must be a superset; its
   acceptance test will assert against this constant. Agreed on the
   substance: the Stage-0 digest never bound the B1/B3/B4 direct-answer
   parser.
5. **Exact pins** — the full `INFRA_RETRY_CODES` dictionary and the
   complete 17-key `GATE_THRESHOLDS` mapping are now asserted literally
   in tests, not by shape.
6. **"Ninth namespace"** — corrected to seventh in `133_f` (marked).

## Test evidence

- `test_conductor_stage1.py` + `test_conductor_program.py`: 130 passed,
  `-W error`.
- Full CPU-compatible suite: **632 passed** under `-W error`
  (`test_conductor_worker_eval.py` remains subject to the recorded NVML
  driver/library mismatch on this box — the reviewer's separate CPU-only
  run of those 79 tests is noted with thanks).
- Stage-0 executable source digest unchanged (`688f7e06…`): the eight
  frozen files were not touched by any of these changes.

## Note on residual risk

The no-repair freeze slightly widens 133_f residual note 1: with no
repair path, a format-failing prompt candidate is ineligible outright,
and if the *other* candidate then fails only general fork gates, §9.2's
both-prompts predicate still forces a full stop rather than the Core
fallback. Unchanged from the accepted position — Stage 0 measured
144/144 reward-blind format validity for the few-shot prompt, and the
schema-only candidate is a strict subset of those bytes sharing the
output contract — but stated here so the accepted exposure is recorded
against the final repair decision rather than the phantom repair path.
