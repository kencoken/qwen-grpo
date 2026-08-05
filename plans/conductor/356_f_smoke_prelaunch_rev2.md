# 356_f — Unit T beta-smoke PRELAUNCH REV2 (response to 355_s): repaired reward-entry deadline + successor manifest

The 355_s blocking finding is repaired, the superseded manifest
is recorded and archived, and the successor prelaunch identity is
prepared on the clean repaired tree. Full suite: **1036 passed
under `-W error`, TRUE exit 0** (1035 + the new 355_s
regression). **No GPU work has occurred and no ledger entry has
been written.**

## 1. The repair (355_s blocking finding)

The training reward entry checks the deadline again — my Rev4
edit had kept only `on_step_begin`, which the review correctly
shows is not equivalent (generation can begin before the
deadline, cross it, and still be scored and consumed before the
next step begins). The reward wrapper is now built by a
module-level factory:

```python
def _make_smoke_reward(base_reward, instrumentation, deadline):
    def reward(completions=None, **kwargs):
        _check_deadline(deadline, "training reward entry")
        instrumentation.on_reward_entry()
        return base_reward(completions, **kwargs)
    return reward
```

The `on_step_begin` check is RETAINED, exactly as the review
directs. Regression
(`test_p0_smoke_reward_entry_deadline`) covers the named
scenario: the step begins BEFORE the deadline
(`on_step_begin` passes), generation finishes AFTER it — the
reward entry refuses, the base reward is never called (scoring
does not occur), the accountant records nothing, and
`on_optimizer_step` structurally refuses (consumption cannot
occur); the same path scores normally inside the deadline.

Repair commit: `635e826` (code + regression + 355_s committed).

## 2. Supersession record

Manifest
`685200a5eb4b7cc2643a683330ecb00e7d4cbf5e2f1fc454539cded8318c5287`
is **SUPERSEDED** — the repair changed
`routing_source_sha256`, so the 354_f identity can never admit
(the manifest validator recomputes the source digest from the
tree and would refuse). It was never launched and never touched
the ledger. Its prepared files are archived unmodified at
`runs/routing-dev/beta-smoke-v1-superseded-685200a5-prelaunch/`
(byte hashes as recorded in 354_f §2).

## 3. The successor prelaunch identity

`prepare_smoke_launch` re-run exactly once at the repaired clean
tree `635e826`:

| field | value |
|---|---|
| **`manifest_sha256`** | `6c717d47ef7210ae927378591ea49368b81d86a11968946be2f33de58482b6e5` |
| `smoke_freeze_sha256` (UNCHANGED) | `d2d87971765d40da9d2c8aebc29e014e2ca24e82f46a7afbf6c9b32231f75eb7` |
| `smoke_config_sha256` (UNCHANGED) | `6e775b9079658799e8759a4d8d4bea969dd8bdd8c100016915c8ef6771a9cf41` |
| `routing_source_sha256` (NEW — the repair) | `d3d992173b097d8df3fc9a6c9918de2a39a65dbfae9c9213627b81c22fa5c799` |
| `environment_manifest_sha256` | `567769c2f35518bad0481b92f9f1940856e8403d4fa7045e6ae3ffa6a326aa1f` |
| `lineage_parent_sha256` (UNCHANGED, == committed head) | `6fea9e3be1f2043d38c297e50bcce36b9d225ce741d61de3ed3a56054e8dba51` |
| `budget_gpu_hours` | `0.75` |

Kind, driver, run_root, execution_root, science contract
(`d47a63ff…`), and runtime profile (`202bc377…`) are identical
to 354_f §1. The manifest round-trips
`validate_smoke_launch_manifest`. As 355_s confirms, the
freeze/configuration did NOT change and the ledger parent
remains valid — the scientific identity of the smoke is
untouched; only the source repair moved the digest.

Persisted prelaunch files (`runs/routing-dev/beta-smoke-v1/prelaunch/`):

| file | sha256 |
|---|---|
| `env_manifest.json` | `92c023a503bcec11ca6f13468b8fc68c63b555c402051a61b005aaa5d666a7a0` |
| `smoke_freeze.json` (byte-identical to 354_f) | `24ed45bb6d2cc93560736f4d1b27dba47e43606fce924b62f789b1c5720dd633` |
| `smoke_launch.json` | `2cccc4b1bf0bcda760659711ff8c212ef0d24fae79166c058dca37d39429f62c` |

## 4. Everything else stands as validated by 355_s

Ledger head `6fea9e3b…` (20 entries verify; envelope
3.1942/56.8058; final 1.0 reserve); no same-freeze launch or
execution output exists; predictions, falsifiers, and the
execution protocol are exactly 354_f §§4–5 with the manifest
hash substituted.

## 5. Requested narrow check

Per 355_s closing: only another narrow hash/head/root check is
required. Approve launching with EXACTLY manifest
`6c717d47ef7210ae927378591ea49368b81d86a11968946be2f33de58482b6e5`
on EXACTLY head
`6fea9e3be1f2043d38c297e50bcce36b9d225ce741d61de3ed3a56054e8dba51`,
run root `runs/routing-dev/beta-smoke-v1`, budget 0.75 GPU-h.
