# Routing development ledger (211_f §12 — append-only)

One fenced JSON block per entry; each entry hashes itself and
chains the previous entry's hash. Never edit a recorded entry.

## entry 1 — support_materialization

```json
{
 "budget_allocated_gpu_hours": 1.0,
 "cohort_selection": "outcome_blind",
 "entry_sha256": "f0d4651cdec35f0a555d464175ffca4ce27148cda857b250ac180a94f7edd3f2",
 "freeze": {
  "probe_rule_sha256": "0b616b8863bf73263c11c63cd8cc1572b880e6586f15059bde642c2a397c9f7b",
  "scientific_design_sha256": "dc86014132ef0c5eca0ef24333228f13566c329e002643df2f280fc1cd72d074",
  "support_launch_sha256": "ea4c28061f49275e5902d811a3626e772867c1d99de566978353764e0e67ca22"
 },
 "kind": "support_materialization",
 "motivating_evidence": "230_f freeze @c7c5513; charter 211_f signed 212_f; priors 202_f/203_f",
 "outcome_informed": false,
 "parent": null,
 "previous_entry_sha256": null,
 "question": "Materialize the outcome-blind routing_dev 6-prefix support (211_f \u00a74): full 4^S surfaces, direction yields, c_fixed_dev, probe cohort"
}
```

## entry 2 — closeout

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "budget_consumed_gpu_hours": 0.0732,
 "closes_entry_sha256": "f0d4651cdec35f0a555d464175ffca4ce27148cda857b250ac180a94f7edd3f2",
 "entry_sha256": "6506f117180c9b2a2fafbd745ca9b19082b18e2c63d49a71e0a2dbce4da4c283",
 "freeze": {
  "execute_env_file_sha256": "bd2d8e7446de559c9f7ce3a1bdbf8df9ec118690416709e29780bd6434abb84a",
  "rendered_observations": 108,
  "run_record_file_sha256": "047216c38532bb56641e5cbd7833c17db551a4d71bd29c4167948bf0b2e328e0",
  "surface_lock_sha256": "61c4e85a53683c9e2dbcbf15f60794935a76a86d979a69412a97f44ea9f2562b",
  "terminal_artifact_hashes": {
   "c_fixed_dev.json": "688c90d7ae8dc5e318d13488a87dc52c07ed7b2f0bb4fd05fe716f8bfc16b7ee",
   "disclosure.json": "dd38426c638cf5c5794b239f79fea1bd9fbb1d1559be79e424924188843a0b7e",
   "execute_env_manifest.json": "bd2d8e7446de559c9f7ce3a1bdbf8df9ec118690416709e29780bd6434abb84a",
   "prelaunch/declaration.json": "432effa9f2f7824278620e6e85a10527d027afc1817c9b28b205f2ba10ea948f",
   "prelaunch/env_manifest.json": "73a9bda6bf1bf603b57ae29d35d69f408ee06c800386bb6e48440b8cd9858707",
   "prelaunch/probe_rule.json": "5e2fb351f5e65473d6b5b9fa225aacb8e20038e438c2c5fe57960243879e36dc",
   "prelaunch/support_launch.json": "2540e5648d8cf13124ba73bc8474e8e745b858d004fc35317a61d146682ac43d",
   "probe_cohort.json": "8056f9669d4a519271d3a19d91e9ba86e3aea5c16ef7f98524e44088a66b7cd4",
   "run_record.json": "047216c38532bb56641e5cbd7833c17db551a4d71bd29c4167948bf0b2e328e0",
   "surface/declaration.json": "432effa9f2f7824278620e6e85a10527d027afc1817c9b28b205f2ba10ea948f",
   "surface/env_manifest.json": "73a9bda6bf1bf603b57ae29d35d69f408ee06c800386bb6e48440b8cd9858707",
   "surface/manifest.json": "beb975d36c4ea4282c9a4acfd739fabb2b487a4ffc9d163a92d34623e2b58915",
   "surface/payoffs.jsonl": "109669f85e98a4be33830185e8e83f260ddce035fb9f60738fa5c96f31073464",
   "surface/support_launch.json": "2540e5648d8cf13124ba73bc8474e8e745b858d004fc35317a61d146682ac43d",
   "surface/surface_lock.json": "45aae0b720384d0600594f3d4b227aa79431d4e3bb43c16ea5f2bbaee57c7eef",
   "surface/traces/traces/manifest.json": "41724f491d860efe2b0e9e7b54453fe891fdf804541e414f532c537f48319321",
   "surface/traces/traces/steps.jsonl": "d62ac1e1ded5c746ddf510e7960b078a44efeb39248ecff9a3175ffeb120ebd6"
  }
 },
 "kind": "closeout",
 "motivating_evidence": "measured support run cost",
 "outcome_informed": false,
 "outcome_pointer": "runs/routing-dev/support-v1/run_record.json",
 "parent": "f0d4651cdec35f0a555d464175ffca4ce27148cda857b250ac180a94f7edd3f2",
 "previous_entry_sha256": "f0d4651cdec35f0a555d464175ffca4ce27148cda857b250ac180a94f7edd3f2",
 "question": "Materialize the outcome-blind routing_dev 6-prefix support (211_f \u00a74): full 4^S surfaces, direction yields, c_fixed_dev, probe cohort",
 "terminal_status": "complete"
}
```

## entry 3 — reserve_update

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "entry_sha256": "264066e66d60ab8819ec5382122690ad73f798391eeafdeb6ba763ed17ac3f2b",
 "freeze": {
  "support_closeout_sha256": "6506f117180c9b2a2fafbd745ca9b19082b18e2c63d49a71e0a2dbce4da4c283",
  "surface_lock_sha256": "61c4e85a53683c9e2dbcbf15f60794935a76a86d979a69412a97f44ea9f2562b"
 },
 "kind": "reserve_update",
 "motivating_evidence": "verified complete closeout 6506f117180c9b2a",
 "outcome_informed": false,
 "parent": "6506f117180c9b2a2fafbd745ca9b19082b18e2c63d49a71e0a2dbce4da4c283",
 "previous_entry_sha256": "6506f117180c9b2a2fafbd745ca9b19082b18e2c63d49a71e0a2dbce4da4c283",
 "question": "Provisional R_cycle from measured support timing (230_f \u00a73 basis)",
 "reserve": {
  "assumed_cohort_size": 3000,
  "evaluation_multiplier": 2.0,
  "measured_seconds_per_observation": 2.44,
  "measured_support_gpu_hours": 0.0732,
  "r_cycle_gpu_hours": 5.0,
  "rounding": "ceil_to_whole_gpu_hours",
  "status": "provisional"
 }
}
```
