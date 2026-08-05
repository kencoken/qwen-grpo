# 372_f — P0 PRELAUNCH (prepared manifest, for the narrow review)

The probe passed (371_f, all eight stages, 0.0168 GPU-h);
`prepare_p0_launch` has now run EXACTLY ONCE on the clean tree
at `34fd303`, and this document records the exact prepared
identities for the narrow real-manifest review the rev5 sign-off
directs. **No GPU work beyond the disclosed probe; no ledger
entry** — the launch executes only after this sign-off, with
exactly these hashes.

## 1. The prepared manifest

| field | value |
|---|---|
| **`manifest_sha256`** | `f59b056ec96b09b5c889f25e6a857f20ebd6f40ed3b8e06fd24abe4a3d53f8e8` |
| kind | `routing-dev-p0-launch-v1` |
| `launch_freeze_sha256` (approved) | `88c6635aadb2d0ca1c766efc937123b7ece427190cfe3ce3675ac8f269ebccfc` |
| `execution_identity_sha256` (approved) | `b5749ecac2e8e2444dd2ebb6193054fb721ea1686751ffd73d0c3938d80b1e1d` |
| `science_contract_sha256` | `d47a63ff435e3b2964f09f0d97f287ee722cae5bbc7df58104d7e10c6d519517` |
| `budget_gpu_hours` | `10.0` (the contract's operational ceiling) |
| driver | `tasks/routing/p0_execution.py` |
| run_root / execution_root | `runs/routing-dev/p0-v1` / `/home/ken/qwen-grpo/runs/routing-dev/p0-v1` |
| **`lineage_parent_sha256`** | `df4bf7ad7c649a5b550b58673368811854c42493125f86a68e6abbf5ce91da56` |
| `routing_source_sha256` | `0dccc3b78570e8b4705b05f6d3a55d81f2f3ed8a980a5e05a388fa9d41583666` (the tree at `34fd303`) |
| `environment_manifest_sha256` | `16294450f605feedc5c2ad2d6e76098c9a0886a4768b46cff76cbb235d091b76` |

Per the rev5 sign-off note: the lineage parent binds the ACTUAL
reviewed post-probe launch head — the committed ledger still
heads at `df4bf7ad…` (22 entries verify; the probe touched no
ledger), so the frozen constant and the actual head COINCIDE and
the first-launch lineage check binds exactly.

## 2. Persisted prelaunch inputs (exactly once)

`runs/routing-dev/p0-v1/prelaunch/` holds exactly four files:

| file | sha256 |
|---|---|
| `env_manifest.json` | `be5d2a7ad1453a05ce34c8c9732cbc916254b4e29e56a782ce5303aa6cd2fe01` |
| `p0_launch.json` | `162bf01205a9b8a4bd8d12e187d977eaffc762d20eb057a81d654f073498a7c8` |
| `launch_freeze.json` (byte copy of the committed artifact) | `940e5e943326de559586b1ae8ac9603037bbd550788209b740c0b4e73fe792a5` |
| `execution_identity.json` (byte copy) | `9c9d07494c75bddf22fbd586c6513ee02b0aa2050fc2fb3aa6c5808e38f5261b` |

A second preparation refuses. Committing THIS document does not
perturb the manifest (the source digest covers routing sources +
driver, not plans documents; environment attestation exempts
documentation-commit fields).

## 3. Admission state

Envelope 3.5059 consumed / 56.4941 remaining; FINAL 1.0 R_cycle
reserve — admission requires remaining ≥ 10.0 + 1.0, satisfied
with wide margin. Admission is the manifest-MANDATORY
`training_run` branch (external hash + prepared environment +
resolved run root; first-launch-only; the 346_f final-reserve
cross-check) and `execute_p0_run` calls it as the ONLY source of
trainer inputs, after the ≥20 GiB VRAM preflight.

## 4. Execution expectation (from the signed record)

39 epochs / 6,123 updates; cadence checkpoints+evaluations at
{0, 628, …, 5652, 6123} (retained v1 bundles, CRN evaluations
under realization `a8e9cf73…`); projected total **9.4029 h**
against the 10.0 h cumulative ceiling (≈0.597 h headroom);
development-only; timing and verification evidence only — no
routing-learning claims from the run itself.

## 5. Requested sign-off

Approve launching with EXACTLY manifest
`f59b056ec96b09b5c889f25e6a857f20ebd6f40ed3b8e06fd24abe4a3d53f8e8`
on EXACTLY head
`df4bf7ad7c649a5b550b58673368811854c42493125f86a68e6abbf5ce91da56`,
run root `runs/routing-dev/p0-v1`, budget 10.0 GPU-h. Any other
manifest hash, head, or root is out of scope and requires
re-preparation.
