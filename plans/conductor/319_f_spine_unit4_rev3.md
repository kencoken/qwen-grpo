# 319_f — Spine Unit 4 REV3 (response to 318_s)

The single P1 repaired, code-only. Full suite: **1020 passed under
`-W error`, TRUE exit 0**. No artifact changed — the committed
appendix (11,187 bytes) and every identity are untouched.

## 1. P1 — key membership, never key order

`require_launchable` validated the input record with
`tuple(plan["inputs"]) != REGISTERED_CAPACITY_INPUTS`, making
dictionary ITERATION ORDER part of identity — so a genuine plan
failed admission after the repository's canonical sorted-key JSON
round-trip, which is exactly how Unit 5 will persist the record.

The check is now **exact key MEMBERSHIP**
(`set(plan["inputs"]) != set(REGISTERED_CAPACITY_INPUTS)`);
missing or extra keys still refuse. The type-sensitive full-plan
rederivation compare is retained unchanged (`_strict_equal` was
already order-insensitive for dictionaries — it compares key sets
and then values per key).

Regressions added:

- **sorted-key round-trip acceptance**: a genuine capacity-one
  plan through `json.loads(json.dumps(plan, sort_keys=True))` —
  the test asserts the key order actually CHANGED, then that
  admission passes;
- a missing input key refuses at the registered-record check;
- an extra input key refuses at the registered-record check;
- an extra TOP-LEVEL field refuses at the rederivation compare
  (a persisted record with fields the derivation never produced
  is not a genuine plan).

All prior 316_s/317_f regressions (forged branch/epoch/boolean/
NaN/ceiling, genuine stop/under-target/spare branches, legacy
parity) pass unchanged.

## 2. Next

Sign-off → Unit 5 (the first real consumer; `P0LaunchFreeze`
only after the routing_dev_val lock, cycle/R_cycle, and beta
smoke inputs exist) → the merge gate.
