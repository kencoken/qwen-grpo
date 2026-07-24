# 137_f — Response to 136_s (unit-1 final review)

Both blockers are fixed; unit 1 is submitted for close-out.

**1. One source of truth for intervention edges — fixed.** The duplicate
table in `stage1.py` is deleted; `CELL_INTERVENTION_EDGES` is now imported
from `types.py` — the same object generation and estimand scoring use. A
new test asserts object identity (`is`, not `==`) between `stage1`'s
reference and `types.py`'s table, since an equal copy is exactly the drift
risk being excluded. All cross-product, cardinality, and
generated-program-endpoint tests are retained and now exercise the
authoritative table.

**2. Population-independent bootstrap canonicalizer — fixed.**
`canonical_cell_look_vector` no longer validates against qualification
schedules. Its checks are exactly the four requested: known cell,
`type(count) is int` (rejecting `bool` and integral floats, which compare
equal to ints but would otherwise mint a distinct-or-colliding serialized
seed identity), count > 0, and sorted canonical serialization.
Phase-specific schedule/count validation is deferred to unit 2's
population manifest, as directed. New tests cover `pilot_gate` (12),
`dev_select` (24), both final test mixtures (56 across six cells, 67
across Core), the policy-dev direction count (72), an off-schedule but
valid count, seed generation through each, and rejection of `100.0` and
`True`.

**Follow-through, part now / part unit 2.** The renderer count is no
longer a duplicate literal: `RENDERERS_PER_LATENT = len(RENDERER_IDS)`,
bound to the authoritative list in `types.py`. The `WORKER_FAMILIES`
cross-check against the authoritative worker registry is accepted as a
unit-2 acceptance test (alongside the successor-digest superset assertion
already pinned in `SUCCESSOR_DIGEST_REQUIRED_ADDITIONS`).

**Test evidence:** focused unit-1/program files 133 passed; full
CPU-compatible suite **635 passed**, both under `-W error`. Stage-0
executable source digest unchanged; no frozen file touched.

Per the 136_s recommendation, we treat unit 1 as ready to close on this
commit and will begin unit 2 (population and provenance layer: canonical
manifests, registered construction/qualification prefixes, complete
source/environment binding including `contract.py`, fail-closed
`gate_report`, and the queued `workerpool.py` `108_f`→`108_s` citation
correction) without another broad audit.
