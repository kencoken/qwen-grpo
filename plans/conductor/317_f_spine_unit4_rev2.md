# 317_f — Spine Unit 4 REV2 (response to 316_s)

Both P1s and the P2 repaired. The committed appendix was
REGENERATED through the fixed generator (never hand-edited); the
contract/projection/mixture identities are untouched. Full suite:
**1020 passed under `-W error`, TRUE exit 0** (same count — every
reviewer reproduction was added inside the existing two Unit-4
tests).

## 1. P1 — `require_launchable` rederives, never trusts

The boundary is now `require_launchable(contract, plan)`: it
validates the registered input record, REDERIVES the complete plan
from the plan's own persisted inputs under the authenticated
contract, compares the supplied record TYPE-SENSITIVELY
(`_strict_equal`: bool is never an int, int is never a float, NaN
never equals anything), and only then rejects the genuine stop
branch. All of the reviewer's forged plans are permanent
regressions:

- the capacity-zero stop plan re-labelled launchable/1-epoch/
  under-target → refuses at the rederivation;
- `launch_epochs=999` on a genuine capacity-one plan → refuses;
- boolean `launch_epochs=True` → refuses (type-sensitive);
- NaN `available_generation_seconds` → refuses;
- a forged `operational_ceiling_seconds` in the input record →
  refuses (the ceiling is rederived from the CONTRACT);
- a plan without the registered input record → refuses;
- the genuine capacity-one plan still passes.

## 2. P1 — the signed traceability matrix

The generated appendix now carries **§8 "Signed traceability
matrix"** — the merge-gated mapping `requirement → field →
enforcement → regression → artifact`, fifteen rows covering: the
Q1 counted event / gate / population; the four Q2 quantities
(marginal, eligibility, conditional, contrasts); the sentinel
complete block; the schedule identity; exact C2 equivalence; the
sizing derivation; cap + launch; and the appendix gate itself.
Deferred obligations are NAMED with their owner, never dropped:
launch-freeze persistence and the checkpoint/evaluation
trajectories are explicit DEFERRED-to-Unit-5 rows.

The sentinel section (§5) was rebuilt to expose the COMPLETE
signed obligation set: it now iterates
`contract.diagnostics.sentinel.fields_required` (an unmapped
field makes generation itself refuse), showing every
first-occurrence family in BOTH index spaces (group and update),
both raw denominators (`group_denominator` = 15 from the
projection; `completion_denominator` computed by
`sentinel_checkpoint_block` — the legacy C2 block does not
persist it), and the two trajectories as deferred-to-Unit-5 rows.

## 3. P2 — byte-exact appendix verification

`verify_appendix` compares RAW BYTES against the UTF-8 encoding
of a fresh generation. Regression: a CRLF rewrite of the committed
appendix — textually identical (asserted) — now refuses. The
returned `bytes` equals the on-disk size (asserted against
`stat().st_size`); the 315_f §3 figure was a character count
mis-stated as bytes — recorded here as a correction, 315_f itself
unedited. The regenerated appendix is 11,187 bytes.

## 4. Scope of change

Only `p0_cap.py`, `p0_tables.py`, the regenerated committed
appendix, and `test_routing_dev.py` changed. Contract/projection/
mixture identities unchanged; the equivalence oracle still PASS
25/25 at `f1912078…`.

## 5. Next

Sign-off on this rev2 → Unit 5 (the first real consumer;
`P0LaunchFreeze` only after the routing_dev_val lock, cycle/
R_cycle, and beta smoke inputs exist) → the merge gate.
