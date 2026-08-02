# 289_f — Unit-C closure erratum for 282_f (immutable record)

The dedicated erratum record for the Unit-C execution record
(282_f), per 288_s. 282_f itself is not edited (record-don't-edit);
this document is the durable correction. All figures verified
against the committed archive `plans/conductor/evidence/unit_c_v1/`.

## E1 — Preflight figures

282_f §1 stated "preflight 24,079 MiB". The authenticated archive
(`session_preflight.json`, bound by the closeout inventory and the
record's preflight hash) records:

- free: **23,687 MiB**
- total: **24,082 MiB**
- floor: 20,000 MiB

The archived, admitted figures are the record.

## E2 — Transport wording

282_f §3's "the TRANSPORT ASSUMPTION ITSELF failed" overstates what
the evidence supports: the original basis was two singleton
successes, and those exact observations also failed to reproduce in
Unit C. The corrected conclusion (283_s wording):

> The homogeneous per-cell transport projection did not reproduce;
> the atomic-Math tail is too rare, heterogeneous or seed-unstable
> to support the frozen exposure guarantee.

The quoted ≈1.5% probability remains a plug-in diagnostic under the
transported rate, not a calibrated p-value.

## E3 — Addendum (verified strengthening, from 283_s)

All **1,320 of 1,320** valid `math_atomic` completions — 165 groups
(150 Bridge + 15 Anchor), every latent, renderer, and subtype —
selected exactly `[0]`; it was the only distinct action observed.
There is effectively no checkpoint-zero exploration of worker 1 on
atomic Math under this prompt and sampling configuration. Added
multiplicity would be expected mostly to buy identical groups and
is not supported as a remedy.
