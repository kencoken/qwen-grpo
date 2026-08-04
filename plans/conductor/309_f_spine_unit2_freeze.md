# 309_f — Unit 1 LOCKED; Spine Unit 2: contract instance + strict schedule loader (for review)

Unit 1 is locked at its signed rev2 identities (§1). Unit 2
implements 303_f §9 step 2 with both carried reminders PROVEN.
Full suite: **1013 passed under `-W error`, TRUE exit 0** (legacy
C1/C2 verifiers passing inside it).

## 1. Unit-1 locked identities (the signed pins)

- Pinned mixture: self `135a72bf…`, file `b305d9c8…` (both enforced
  in code).
- Compatibility projection (v2, with the exact maps): self
  `f1912078…`, file `41f15c5d…` (both enforced in code).
- Schema: `p0-science-contract-v2`.
- Replay-source pins: as committed in `p0_replay.REPLAY_SOURCE`.

## 2. The contract instance (`tasks/routing/p0_contract.py`)

`build_p0_science_contract()` constructs the instance **from the
authoritative in-code sources** (`REPLAY_SOURCE`, the artifact
pins, the pinned mixture's sentinel ids) — never hand-transcribed;
the Unit-1 disclosure is the stated reason. Frozen once to
`plans/conductor/p0/p0_science_contract.json`:

- **Contract hash (the external pin for this review to record):**
  `d47a63ff435e3b2964f09f0d97f287ee722cae5bbc7df58104d7e10c6d519517`
- Contract file hash:
  `8b348b0fae433a775e2bcfe4d29a9d7a26a7389ae88b98f5b95a5d0e968de611`

Contents: the 15 input pins (including the C2 identity/environment
anchors and both projection hashes); the 301_f scope (with the Q2
description carrying the "authorized to be trained, not shown
learned" boundary); the typed Q1 rule (event + gates + the
authenticated 13/34/13 sizing counts over 5 epochs); the typed Q2
rule (marginal gate, eligibility, the conditional estimand with
its numeric baselines 8/152 and 0/15 separate from the marginals
73/108); the sizing rule with the closed cap semantics; and the
complete diagnostics specification. Tests: the frozen instance
equals a fresh build from sources; loads only under the pin; the
one-time freeze refuses overwrite; a tampered committed contract
refuses.

## 3. The strict schedule loader (`tasks/routing/p0_schedule.py`)

A loader/VALIDATOR only — the module contains no import of the
legacy builder anywhere:

- `epoch_schedule(contract)` — the frozen 157-row epoch from the
  double-bound artifact, validated against the CONTRACT's pins;
- `schedule_for_epochs(contract, n)` — N identical passes; the
  count arrives from the later `P0LaunchFreeze`; the loader bounds
  it (positive non-boolean int; **n > nominal refuses — spare
  capacity never authorizes extra training**);
- `population_of` — the effective population map with the
  CONTRACT's sentinel override;
- `build_trainer_rows(contract, n, surface_dir)` — trainer rows
  regenerated from the LOCKED surface, identity-checked per
  observation, clean-clone capable.

**The carried reminders, proven in tests:**

1. **Legacy builder DISABLED**: with `build_mixture_v2`
   monkeypatched to raise, the loader produces the epoch, the
   5-epoch schedule, and the trainer rows — it never touches the
   builder.
2. **Clean-clone-restored surface**: trainer rows build from an
   isolated replica restored from committed evidence (never the
   live `runs/` tree), with the builder still disabled.

**Equivalence spot-check**: the loader's 5-epoch schedule is
byte-equal to the frozen projection's C2 schedule (the full Unit-3
replay equivalence comes next; this confirms the loader serves the
C2-authorized experiment).

## 4. Next

Reviewer pass on this unit (recording `d47a63ff…` as the external
contract pin) → Unit 3: the P0-forward estimands
(`p0_estimands.py`) and the exact C2 replay equivalence against
the frozen projection — with the carried reminder that the
action-sensitivity regression must use a COHERENT VALID
alternative that changes a scientific result.
