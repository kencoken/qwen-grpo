# 201_f — B diagnostic candidate freeze (195_f §3 step 3)

Reviewer's final mechanical changed-lines check passed; Ken approved
freeze → smoke → lock → run (2026-07-27). The candidate executable
is FROZEN at these identities (`current_executable_identity()`,
verified this session against a clean tree):

- `source_digest =
  105d8c0e1399f7696c71db5dbcf173d1a5b705b4b260393b2217a376941cee2f`
- `uv_lock_sha256 =
  f5486ec478b080aa79c6d0444478b019d2ce6262173a643fd1d6aa8f779e48c9`
- `contract_sha256 =
  1e2f63fc23b8b82174f4e431b704401ac172d130de45ac65db23bd076bf9a110`
- `generation_config_sha256 =
  1feb76057fe336d7a1333fafa3c3985687316412234efc18384b48f874b29ffb`
- `model_revision = tokenizer_revision =
  aa8e72537993ba99e69dfaafa59ed015b17504d1`

Sequence from here (frozen): the smoke runs EXACTLY these bytes and
persists its identity-carrying record
(`plans/conductor/b_diagnostic_smoke_record.json`, committed); the
launch lock is built from that record and the materialized
9,216-key diagnostic seed registry
(`plans/conductor/b_diagnostic_launch_lock.json`, committed); the
one-shot diagnostic runs only from the locked state (the consuming
boundary re-validates smoked == locked == launched). Any executable
change after the smoke returns to review with a newly authorized
smoke. GPU preflight at freeze: 24,079 MiB free of 24,564.
