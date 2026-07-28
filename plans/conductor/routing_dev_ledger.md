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

## entry 4 — resume_validation

```json
{
 "budget_allocated_gpu_hours": 0.5,
 "entry_sha256": "36ac27c640ed45b2d66ad017c7f99e54b22a619e25f2a570b297fbbe6afa5848",
 "freeze": {
  "attested_environment_sha256": "372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42",
  "config_sha256": "1c8d2a5df9ee8e05b5d9590d15ce72836312e140b1f2bafed36654fb0acbe578",
  "environment_manifest_sha256": "eb12c4322fa3a6d19e90bad992536a68256ef4c66276cbb165651c6a9165970d",
  "freeze_sha256": "1f7bd7764c48eba5439aac312b7510a6b1654916509bb0374971896464093f09",
  "identity_manifest_sha256": "2f15ea865200cc4ea808b48b074949a2a24668a9c37c19b04bfa4fd5c3f20b05",
  "session_preflight_sha256": "7e79f947786a7a5859aaedbebedd5decc0b3cb6439d1c8da545adbd7c6ecb08e"
 },
 "kind": "resume_validation",
 "motivating_evidence": "240_f rev4 freeze; 232_s item 2",
 "outcome_informed": false,
 "parent": null,
 "previous_entry_sha256": "264066e66d60ab8819ec5382122690ad73f798391eeafdeb6ba763ed17ac3f2b",
 "question": "Does the v1 checkpoint contract hold on the real GRPOTrainer stack \u2014 boundary-only checkpoints, exact counter/RNG/sampler restoration, aborted tails preserved-but-excluded, and an interrupted run indistinguishable from an uninterrupted one?"
}
```

## entry 5 — closeout

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "budget_consumed_gpu_hours": 0.0224,
 "closes_entry_sha256": "36ac27c640ed45b2d66ad017c7f99e54b22a619e25f2a570b297fbbe6afa5848",
 "entry_sha256": "237d4c21d07cc72fb7e9fc92d41703a0243a315db755a7c6e1459cbae12625dd",
 "freeze": {
  "freeze_sha256": "1f7bd7764c48eba5439aac312b7510a6b1654916509bb0374971896464093f09",
  "partial_artifact_hashes": {
   "checkpoint_zero_hashes.json": "5c8454510e7df36eb9246969328d15d977d2c045b9ad76cd616f9cf9882e04fa",
   "environment_manifest.json": "2db1d36644185d067d7de0835d525290549ef999ef014439eaf880ff263e517c",
   "identity_manifest.json": "24af93cfc6a0309a0d321c8d8946e7b143e17aab5db129d616bcd8f951a833be",
   "interrupted/README.md": "486cc0ee115fc43260172a6a99cab4122a1fc8816521cb83e3607af43f2a489b",
   "interrupted/actions.jsonl": "0253cffa0009fc588a220cdfc7662d15baaa85739e52e5ef798785b86bda3dc7",
   "interrupted/bundle/adapter.safetensors": "b2b059ce862611bd219ee78ed840d299e33bd4b5ae79fc14898465fd0116ad76",
   "interrupted/bundle/checkpoint_record.json": "e00d29bd839242d42c4bf5a77a2fd6f276cfd7bad1662015cad824459df00372",
   "interrupted/bundle/optimizer.pt": "09ae1e92d97b709340e76e7e081afacd893b58a9db939550a855fb76a963fb59",
   "interrupted/bundle/rng_state.json": "2d3a5a4d77001a2763e96b5c0594bc0a4bc44ce769a23a2edc1a81250556a64e",
   "interrupted/bundle/scheduler.pt": "aa9d429ddb46e5dcbd5d675fddea3c1fc689eda5c0591f942ee11e2c397da60b",
   "interrupted/checkpoint-3/README.md": "019d86d85224adc7d5a1e8b06ea654167055137f2531ff4f8b985d05b40bea76",
   "interrupted/checkpoint-3/adapter_config.json": "2b12a498d993303f901c6d571ac799d43c5db8ccb635b02ef30094e5159df539",
   "interrupted/checkpoint-3/adapter_model.safetensors": "eed3e3ff57c1a275ecc5f167a13d760a4ed3221f8de89c29b1743f6bdbc069e0",
   "interrupted/checkpoint-3/chat_template.jinja": "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f",
   "interrupted/checkpoint-3/optimizer.pt": "09ae1e92d97b709340e76e7e081afacd893b58a9db939550a855fb76a963fb59",
   "interrupted/checkpoint-3/rng_state.pth": "362b1757c728b526cc02c86cd4f56ddaeaef5f99f9b4ca8ceda7aca8c46a60b1",
   "interrupted/checkpoint-3/scheduler.pt": "aa9d429ddb46e5dcbd5d675fddea3c1fc689eda5c0591f942ee11e2c397da60b",
   "interrupted/checkpoint-3/tokenizer.json": "3fd169731d2cbde95e10bf356d66d5997fd885dd8dbb6fb4684da3f23b2585d8",
   "interrupted/checkpoint-3/tokenizer_config.json": "04b1682c59acbd057f4c9072297faa73d56fc9de053094c659cdb4c464f58f86",
   "interrupted/checkpoint-3/trainer_state.json": "6662e8646be86b9175f31f7e529ca73493c5187539a6297f4665f958d5b4fcf8",
   "interrupted/checkpoint-3/training_args.bin": "732a7304a5eba72140c3e8dd4f30a5e8805c023bf9fa573638221c7dff87a362",
   "resume/actions.jsonl": "9efab0ac0138b9ba1c39e01a51dded5d8c91015b5e55d28dd6ccda8445fb751a",
   "schedule.json": "ec14b7f16add230d70333fae5b0343bb0844c1c2c1026d04aa869fadd9e7dcc6",
   "session_preflight.json": "b60be37258c4d5463829a56ba6d26806ed7010dae946373b0626b4c34065f3f4",
   "uninterrupted/README.md": "699e127b85dfe88ed9a780c6531c05df744cb88e48030daef8ddbf7550e2705f",
   "uninterrupted/actions.jsonl": "72181c2243004bc0b3f2548dc295e4a7c9be5d4a9d027469b5fddd666f347da6",
   "uninterrupted/bundle/adapter.safetensors": "b2b059ce862611bd219ee78ed840d299e33bd4b5ae79fc14898465fd0116ad76",
   "uninterrupted/bundle/checkpoint_record.json": "cc3085a34d9a940c711840ae34aa36f87e65781bf7c5259924a7294a62895be0",
   "uninterrupted/bundle/optimizer.pt": "09ae1e92d97b709340e76e7e081afacd893b58a9db939550a855fb76a963fb59",
   "uninterrupted/bundle/rng_state.json": "2d3a5a4d77001a2763e96b5c0594bc0a4bc44ce769a23a2edc1a81250556a64e",
   "uninterrupted/bundle/scheduler.pt": "aa9d429ddb46e5dcbd5d675fddea3c1fc689eda5c0591f942ee11e2c397da60b",
   "uninterrupted/checkpoint-3/README.md": "019d86d85224adc7d5a1e8b06ea654167055137f2531ff4f8b985d05b40bea76",
   "uninterrupted/checkpoint-3/adapter_config.json": "2b12a498d993303f901c6d571ac799d43c5db8ccb635b02ef30094e5159df539",
   "uninterrupted/checkpoint-3/adapter_model.safetensors": "eed3e3ff57c1a275ecc5f167a13d760a4ed3221f8de89c29b1743f6bdbc069e0",
   "uninterrupted/checkpoint-3/chat_template.jinja": "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f",
   "uninterrupted/checkpoint-3/optimizer.pt": "09ae1e92d97b709340e76e7e081afacd893b58a9db939550a855fb76a963fb59",
   "uninterrupted/checkpoint-3/rng_state.pth": "362b1757c728b526cc02c86cd4f56ddaeaef5f99f9b4ca8ceda7aca8c46a60b1",
   "uninterrupted/checkpoint-3/scheduler.pt": "aa9d429ddb46e5dcbd5d675fddea3c1fc689eda5c0591f942ee11e2c397da60b",
   "uninterrupted/checkpoint-3/tokenizer.json": "3fd169731d2cbde95e10bf356d66d5997fd885dd8dbb6fb4684da3f23b2585d8",
   "uninterrupted/checkpoint-3/tokenizer_config.json": "04b1682c59acbd057f4c9072297faa73d56fc9de053094c659cdb4c464f58f86",
   "uninterrupted/checkpoint-3/trainer_state.json": "8c6d56fc0371b08f92cf98052a75f5c012cf3ecede316a8271ca4efdef033eed",
   "uninterrupted/checkpoint-3/training_args.bin": "14f9ebbf8d66a588b60ffc44e1682783d9631e8f9c5a7bbecfcad0117ea437b0",
   "uninterrupted/checkpoint-6/README.md": "019d86d85224adc7d5a1e8b06ea654167055137f2531ff4f8b985d05b40bea76",
   "uninterrupted/checkpoint-6/adapter_config.json": "2b12a498d993303f901c6d571ac799d43c5db8ccb635b02ef30094e5159df539",
   "uninterrupted/checkpoint-6/adapter_model.safetensors": "0661d061f27f33eba6ec8f159841b428ee10d5731a590d86c23488f47980d8ce",
   "uninterrupted/checkpoint-6/chat_template.jinja": "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f",
   "uninterrupted/checkpoint-6/optimizer.pt": "2fe62c08d0eb57ef7635f79f14fd9f999ba32b279222df22cd10f5f6f0308254",
   "uninterrupted/checkpoint-6/rng_state.pth": "8dddc5b359db4893722fb5ea6c1600ce3d3909b9bebba9f182e06882ac89a2a0",
   "uninterrupted/checkpoint-6/scheduler.pt": "51e38dd1b409772167eaac5bea07e67925403fdd6e714095ddd2daabf6699880",
   "uninterrupted/checkpoint-6/tokenizer.json": "3fd169731d2cbde95e10bf356d66d5997fd885dd8dbb6fb4684da3f23b2585d8",
   "uninterrupted/checkpoint-6/tokenizer_config.json": "04b1682c59acbd057f4c9072297faa73d56fc9de053094c659cdb4c464f58f86",
   "uninterrupted/checkpoint-6/trainer_state.json": "2c36ab7ac277daa0b752afc5c93327079f92d3a8048de1726b15e929e041c6a4",
   "uninterrupted/checkpoint-6/training_args.bin": "14f9ebbf8d66a588b60ffc44e1682783d9631e8f9c5a7bbecfcad0117ea437b0"
  }
 },
 "interpretation": "InfrastructureError: adapter: base_model.model.model.layers.0.mlp.down_proj.lora_A.default.weight shape/dtype mismatch",
 "kind": "closeout",
 "motivating_evidence": "resume validation ABORTED",
 "outcome_informed": false,
 "outcome_pointer": "runs/routing-dev/resume-validation-v3",
 "parent": "36ac27c640ed45b2d66ad017c7f99e54b22a619e25f2a570b297fbbe6afa5848",
 "previous_entry_sha256": "36ac27c640ed45b2d66ad017c7f99e54b22a619e25f2a570b297fbbe6afa5848",
 "question": "Does the v1 checkpoint contract hold on the real GRPOTrainer stack \u2014 boundary-only checkpoints, exact counter/RNG/sampler restoration, aborted tails preserved-but-excluded, and an interrupted run indistinguishable from an uninterrupted one?",
 "terminal_status": "aborted"
}
```

## entry 6 — engineering_smoke

```json
{
 "budget_allocated_gpu_hours": 0.1,
 "entry_sha256": "9886eae46c377bbb43f6980a1cd6d68f9828470744422bfc854c9dbd1b5a237d",
 "freeze": {
  "freeze_sha256": "9407ac822569db146db5e9e8093195f42f8429055891af6fed754bb23d7cc427"
 },
 "kind": "engineering_smoke",
 "motivating_evidence": "aborted closeout 237d4c21d07c",
 "outcome_informed": true,
 "parent": "237d4c21d07cc72fb7e9fc92d41703a0243a315db755a7c6e1459cbae12625dd",
 "previous_entry_sha256": "237d4c21d07cc72fb7e9fc92d41703a0243a315db755a7c6e1459cbae12625dd",
 "question": "Why do the live LoRA state dicts of a fresh trainer and a checkpoint-resumed trainer differ in shape/dtype (Step-5 abort 237d4c21)?"
}
```

## entry 7 — closeout

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "budget_consumed_gpu_hours": 0.0076,
 "closes_entry_sha256": "9886eae46c377bbb43f6980a1cd6d68f9828470744422bfc854c9dbd1b5a237d",
 "entry_sha256": "943b9d7ce8c7ebcd908101489a8f0a866ccc575c8538f727d633415e918ca212",
 "freeze": {
  "freeze_sha256": "9407ac822569db146db5e9e8093195f42f8429055891af6fed754bb23d7cc427",
  "terminal_artifact_hashes": {
   "findings.json": "3264b06c0cd5dec71bbfd41fb3928ce2e12efcf9a7a956bb98d0533f05533614",
   "t2.jsonl": "9efab0ac0138b9ba1c39e01a51dded5d8c91015b5e55d28dd6ccda8445fb751a"
  }
 },
 "kind": "closeout",
 "motivating_evidence": "dtype smoke complete",
 "outcome_informed": true,
 "outcome_pointer": "runs/routing-dev/smoke-dtype-1/findings.json",
 "parent": "9886eae46c377bbb43f6980a1cd6d68f9828470744422bfc854c9dbd1b5a237d",
 "previous_entry_sha256": "9886eae46c377bbb43f6980a1cd6d68f9828470744422bfc854c9dbd1b5a237d",
 "question": "Why do the live LoRA state dicts of a fresh trainer and a checkpoint-resumed trainer differ in shape/dtype (Step-5 abort 237d4c21)?",
 "terminal_status": "complete"
}
```
