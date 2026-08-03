# 306_f — Spine Unit 1: schema + pinned artifact + frozen projection (for review)

The 305_f-signed sequence's Unit 1, on `conductor_spine`. Full
suite: **1011 passed under `-W error`, TRUE exit 0** (the legacy C1
and C2 verifiers run inside it — the standing gate holds).

## 1. The schema (`tasks/routing/p0_schema.py`)

`P0ScienceContract` as nested FROZEN dataclasses with tuples
throughout (no mutable containers in the hashed body):
`InputPins` (content/file hashes only — nothing commit-dependent,
per the 305_f §1 dependency graph), `ActiveScope` (Q1-direct cells,
Q2 description, Q3 out-of-scope, the sentinel with its exclusions),
`Q1Rule` / `Q2Rule` (versioned, typed — the Q2 rule carries the
marginal gate, the conditional-estimand definition with its
zero-denominator-is-None semantics, and BOTH baseline families
separately: conditional 8/152 & 0/15, marginal 73 & 108),
`SizingRule` (the 304_s §5 nominal/capacity/launch split as rules),
`RequiredDiagnostics` (the 301_f list). Canonical serialization,
explicit `schema_version`, and a STRICT loader: closed field sets,
version check, tuple reconstruction, and the **externally reviewed
expected hash required** — a self-consistent file alone refuses.
Tests cover deep immutability, round-trip, and refusals for wrong
hash, missing hash, unknown fields, wrong version, tampered body.

## 2. The pinned-mixture artifact

`plans/conductor/p0/pinned_mixture_v2.json` — materialized ONCE
through the LEGACY builder from its authenticated inputs (302_s §4
step 1), committed, and double-bound:

- self-hash pin: `135a72bf…` (the frozen B2 candidate);
- file hash: `b305d9c8c808…` — recorded here:
  `b305d9c808d21ba8ced0c21b01076497160527ba8164d588df35e20417a7deb6`.

Tests: rehash + pin; BYTE-LEVEL equality with a fresh legacy
rederivation on the clean-clone-restored surface; the one-time
materializer refuses overwrite. Unit 2's strict schedule loader
consumes this file.

## 3. The frozen compatibility projection

`plans/conductor/p0/c2_compatibility_projection.json` — the
expected canonical scientific projection, EXTRACTED from the
authenticated C2 archive and frozen NOW, before the Unit-3
evaluator exists (305_f §2). Self-hash `6a913547…`; file hash
`e30a6cb966534110fceb18a481e8cb205bfffaaba099b1a9a77735d64b937a74`.
It carries the full 302_s §3 list: the ordered 157-row epoch and
785-row schedule; the population draws (75/420/25/90/160/15); the
complete Q1 gate blocks (60 counted total), Q2 blocks + cold-start
gate, direct-control block, full strata; the sentinel block with
every first-occurrence field; sizing 39/6,123; 662 zero-variance
groups; 6,242 valid / 38 invalid completions; and the exact
decision string. Identity fields expected to change under new
source are excluded. The Unit-3 evaluator will be compared against
THESE bytes and may neither call the legacy report builder nor
read the source report.

## 4. The authenticated replay source (`tasks/routing/p0_replay.py`)

`verify_c2_replay_source()` verifies, in order: the ledger chain
CONTAINS the C2 complete closeout `2bf50c1e…` with the frozen
report/record bindings; the evidence bytes equal the
closeout-bound terminal inventory (including the four pinned file
hashes: actions `8e705317…`, report `03152f0e…`, schedule
`c2687919…`, record `cc42c16b…`) BEFORE any replay; the reviewed
identity (`7b19aeb9…`) and environment (`372f958f…`) anchors; the
locked extension surface with the CLEAN-CLONE restoration path;
the frozen selection and comparator; and the pinned-mixture
artifact. PASS on the committed state; a tampered-evidence
regression refuses before replay.

**Disclosure — a caught transcription error:** my first version of
the four file-hash pins carried fabricated tails (transcribed from
12-character prefixes in an earlier terminal listing). The
closeout-binding check itself REFUSED them on first run; the pins
were corrected to the true full hashes and the projection refrozen
before anything was committed. The error never reached a commit,
and it is a live demonstration that the inventory binding bites —
but the freeze records it because the review should know the pins
were re-derived once.

## 5. Carried reminders (from the 305_f approval)

- **Unit 2** must prove the schedule loader works with the legacy
  builder DISABLED and from a clean-clone-restored surface.
- **Unit 3**'s action-sensitivity regression must use a COHERENT
  VALID alternative that changes a scientific result — not merely
  corrupt redundant stored fields.

## 6. Next

Reviewer pass on this unit → Unit 2 (`p0_contract.py` — the
contract INSTANCE with its externally reviewed hash — and the
strict pinned-schedule loader, under the §5 reminder).
