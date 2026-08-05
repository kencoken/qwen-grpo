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

## entry 8 — resume_validation

```json
{
 "budget_allocated_gpu_hours": 0.5,
 "entry_sha256": "8b0df6b0e5956bf6562457a664ee567597ea7ff438cc0890e9cecf21deca29a4",
 "freeze": {
  "attested_environment_sha256": "372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42",
  "config_sha256": "40e1ecc5169111be33f93f00cd50f1819c1c55492957a64d3b0e4d6f831ff2f6",
  "environment_manifest_sha256": "f9c2bd2f79e98db81f207d81ddead122b4ad748707c8e0bdbdb0411316031cbd",
  "freeze_sha256": "c73107e0813f2b5ef63a248ae76e958ba78697352233a52786593d5b0c73fd6a",
  "identity_manifest_sha256": "3af6b03a64debb66a17b70771f599682432373ee2271f8500b7662b3d24f974c",
  "session_preflight_sha256": "7e79f947786a7a5859aaedbebedd5decc0b3cb6439d1c8da545adbd7c6ecb08e"
 },
 "kind": "resume_validation",
 "motivating_evidence": "243_f rev6 freeze; aborted rev5 closeout 237d4c21d07c\u2026; outcome-informed dtype-smoke closeout 943b9d7ce8c7\u2026",
 "outcome_informed": true,
 "parent": "943b9d7ce8c7ebcd908101489a8f0a866ccc575c8538f727d633415e918ca212",
 "previous_entry_sha256": "943b9d7ce8c7ebcd908101489a8f0a866ccc575c8538f727d633415e918ca212",
 "question": "Does the v1 checkpoint contract hold on the real GRPOTrainer stack \u2014 boundary-only checkpoints, exact counter/RNG/sampler restoration, aborted tails preserved-but-excluded, and an interrupted run indistinguishable from an uninterrupted one?"
}
```

## entry 9 — closeout

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "budget_consumed_gpu_hours": 0.0237,
 "closes_entry_sha256": "8b0df6b0e5956bf6562457a664ee567597ea7ff438cc0890e9cecf21deca29a4",
 "entry_sha256": "1a8d41fde4ffb64a9d9d9886f8fbcf9dc20578ab33c3c0d72a44fa8ea9b6a44a",
 "freeze": {
  "freeze_sha256": "c73107e0813f2b5ef63a248ae76e958ba78697352233a52786593d5b0c73fd6a",
  "terminal_artifact_hashes": {
   "checkpoint_zero_hashes.json": "5c8454510e7df36eb9246969328d15d977d2c045b9ad76cd616f9cf9882e04fa",
   "environment_manifest.json": "5075c5a64bb8b319c1363844378fb85353afa3ca310d0705aa33a26aa7885b5e",
   "final_resumed/adapter.safetensors": "b9853a60b35b81c6b8b4e12bfdaf6a54201add76e1268b88ac4e96f482704179",
   "final_resumed/cursor.json": "1bbb913f8edd512469e6317d87d0fb809b5f65cf122ac846187b346ad2df7ee7",
   "final_resumed/optimizer.pt": "2a0081d9e3c985b3c950c9823b022f67bd812540072b6b95a45286bcfc6d5fd7",
   "final_resumed/scheduler.pt": "51e38dd1b409772167eaac5bea07e67925403fdd6e714095ddd2daabf6699880",
   "final_uninterrupted/adapter.safetensors": "b9853a60b35b81c6b8b4e12bfdaf6a54201add76e1268b88ac4e96f482704179",
   "final_uninterrupted/cursor.json": "1bbb913f8edd512469e6317d87d0fb809b5f65cf122ac846187b346ad2df7ee7",
   "final_uninterrupted/optimizer.pt": "2a0081d9e3c985b3c950c9823b022f67bd812540072b6b95a45286bcfc6d5fd7",
   "final_uninterrupted/scheduler.pt": "51e38dd1b409772167eaac5bea07e67925403fdd6e714095ddd2daabf6699880",
   "identity_manifest.json": "45e84b608531eb45a6d3b307aedff53d5cecf60377c40f3552c6bb7ce02ba3c0",
   "interrupted/README.md": "486cc0ee115fc43260172a6a99cab4122a1fc8816521cb83e3607af43f2a489b",
   "interrupted/actions.jsonl": "0253cffa0009fc588a220cdfc7662d15baaa85739e52e5ef798785b86bda3dc7",
   "interrupted/bundle/adapter.safetensors": "18657f10014453011e4ec9223dd3f87ca8e0151451f06b261f8bc87f2c704626",
   "interrupted/bundle/checkpoint_record.json": "391165c359c90748767c3f26957155a2cacad756cd1e4d871cd0123ff6af42d5",
   "interrupted/bundle/optimizer.pt": "93e6212735c28342957bf1c43ff56cd59f75e568b044fd122acbca5b89ffd77f",
   "interrupted/bundle/rng_state.json": "2d3a5a4d77001a2763e96b5c0594bc0a4bc44ce769a23a2edc1a81250556a64e",
   "interrupted/bundle/scheduler.pt": "aa9d429ddb46e5dcbd5d675fddea3c1fc689eda5c0591f942ee11e2c397da60b",
   "interrupted/checkpoint-3/README.md": "019d86d85224adc7d5a1e8b06ea654167055137f2531ff4f8b985d05b40bea76",
   "interrupted/checkpoint-3/adapter_config.json": "bc2c19cbe88157be949ea028d425bc2968bb32330cbaad3078faab94e1674b60",
   "interrupted/checkpoint-3/adapter_model.safetensors": "1a5fab25f7f62d20fb9e3eb61c3053999b8b8d74614cf38e41aa44606f6e8064",
   "interrupted/checkpoint-3/chat_template.jinja": "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f",
   "interrupted/checkpoint-3/optimizer.pt": "93e6212735c28342957bf1c43ff56cd59f75e568b044fd122acbca5b89ffd77f",
   "interrupted/checkpoint-3/rng_state.pth": "362b1757c728b526cc02c86cd4f56ddaeaef5f99f9b4ca8ceda7aca8c46a60b1",
   "interrupted/checkpoint-3/scheduler.pt": "aa9d429ddb46e5dcbd5d675fddea3c1fc689eda5c0591f942ee11e2c397da60b",
   "interrupted/checkpoint-3/tokenizer.json": "3fd169731d2cbde95e10bf356d66d5997fd885dd8dbb6fb4684da3f23b2585d8",
   "interrupted/checkpoint-3/tokenizer_config.json": "04b1682c59acbd057f4c9072297faa73d56fc9de053094c659cdb4c464f58f86",
   "interrupted/checkpoint-3/trainer_state.json": "2cec4e764c597547461d901c5948a50ea7355ae9d28cf554bbf4e22635b0b1d6",
   "interrupted/checkpoint-3/training_args.bin": "046b8afc09be74ede74119b9ab714b3d3c45368bab41270c636e0b7e2879c026",
   "resume/actions.jsonl": "d3c630c7041e05e88e101e6e7ad7c6eb016eaf8430dbc684e4ae32e389663187",
   "schedule.json": "ec14b7f16add230d70333fae5b0343bb0844c1c2c1026d04aa869fadd9e7dcc6",
   "session_preflight.json": "b60be37258c4d5463829a56ba6d26806ed7010dae946373b0626b4c34065f3f4",
   "uninterrupted/README.md": "699e127b85dfe88ed9a780c6531c05df744cb88e48030daef8ddbf7550e2705f",
   "uninterrupted/actions.jsonl": "f409ce38341ac9feeb6eb19a546aee7b8ac473a0c434db520f83c52e1eeab3d7",
   "uninterrupted/bundle/adapter.safetensors": "18657f10014453011e4ec9223dd3f87ca8e0151451f06b261f8bc87f2c704626",
   "uninterrupted/bundle/checkpoint_record.json": "f6cabecda464de5afc06a881eec53cd72efeb6683e1ab7ea9d951e2ab0d1f939",
   "uninterrupted/bundle/optimizer.pt": "93e6212735c28342957bf1c43ff56cd59f75e568b044fd122acbca5b89ffd77f",
   "uninterrupted/bundle/rng_state.json": "2d3a5a4d77001a2763e96b5c0594bc0a4bc44ce769a23a2edc1a81250556a64e",
   "uninterrupted/bundle/scheduler.pt": "aa9d429ddb46e5dcbd5d675fddea3c1fc689eda5c0591f942ee11e2c397da60b",
   "uninterrupted/checkpoint-3/README.md": "019d86d85224adc7d5a1e8b06ea654167055137f2531ff4f8b985d05b40bea76",
   "uninterrupted/checkpoint-3/adapter_config.json": "bc2c19cbe88157be949ea028d425bc2968bb32330cbaad3078faab94e1674b60",
   "uninterrupted/checkpoint-3/adapter_model.safetensors": "1a5fab25f7f62d20fb9e3eb61c3053999b8b8d74614cf38e41aa44606f6e8064",
   "uninterrupted/checkpoint-3/chat_template.jinja": "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f",
   "uninterrupted/checkpoint-3/optimizer.pt": "93e6212735c28342957bf1c43ff56cd59f75e568b044fd122acbca5b89ffd77f",
   "uninterrupted/checkpoint-3/rng_state.pth": "362b1757c728b526cc02c86cd4f56ddaeaef5f99f9b4ca8ceda7aca8c46a60b1",
   "uninterrupted/checkpoint-3/scheduler.pt": "aa9d429ddb46e5dcbd5d675fddea3c1fc689eda5c0591f942ee11e2c397da60b",
   "uninterrupted/checkpoint-3/tokenizer.json": "3fd169731d2cbde95e10bf356d66d5997fd885dd8dbb6fb4684da3f23b2585d8",
   "uninterrupted/checkpoint-3/tokenizer_config.json": "04b1682c59acbd057f4c9072297faa73d56fc9de053094c659cdb4c464f58f86",
   "uninterrupted/checkpoint-3/trainer_state.json": "cce2261ecfe5cd530301132a8c97abeb58a53a32ff2e20be9859b304a915924e",
   "uninterrupted/checkpoint-3/training_args.bin": "88adedcfb726d0017b43fd8cb1f0613b459b64cf7c85da67d9d3d44290286321",
   "uninterrupted/checkpoint-6/README.md": "019d86d85224adc7d5a1e8b06ea654167055137f2531ff4f8b985d05b40bea76",
   "uninterrupted/checkpoint-6/adapter_config.json": "bc2c19cbe88157be949ea028d425bc2968bb32330cbaad3078faab94e1674b60",
   "uninterrupted/checkpoint-6/adapter_model.safetensors": "6b564247484405ef1e047383e9284805aa89fcbb4cdf982b215e45b7ccd6fdd0",
   "uninterrupted/checkpoint-6/chat_template.jinja": "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f",
   "uninterrupted/checkpoint-6/optimizer.pt": "acbee947422b3ba060804e99ab13d76deee0fef69dda69a9d55baa9995d8accd",
   "uninterrupted/checkpoint-6/rng_state.pth": "8dddc5b359db4893722fb5ea6c1600ce3d3909b9bebba9f182e06882ac89a2a0",
   "uninterrupted/checkpoint-6/scheduler.pt": "51e38dd1b409772167eaac5bea07e67925403fdd6e714095ddd2daabf6699880",
   "uninterrupted/checkpoint-6/tokenizer.json": "3fd169731d2cbde95e10bf356d66d5997fd885dd8dbb6fb4684da3f23b2585d8",
   "uninterrupted/checkpoint-6/tokenizer_config.json": "04b1682c59acbd057f4c9072297faa73d56fc9de053094c659cdb4c464f58f86",
   "uninterrupted/checkpoint-6/trainer_state.json": "2db049a2532556f71ca2a782163babb90856d1b87f33664619e948753dc52052",
   "uninterrupted/checkpoint-6/training_args.bin": "88adedcfb726d0017b43fd8cb1f0613b459b64cf7c85da67d9d3d44290286321",
   "validation_record.json": "ea6442141862475e2a078650764cf2046e3a6ea594933962793ccdde01bdf5aa"
  },
  "validation_record_file_sha256": "ea6442141862475e2a078650764cf2046e3a6ea594933962793ccdde01bdf5aa"
 },
 "kind": "closeout",
 "motivating_evidence": "resume validation complete",
 "outcome_informed": false,
 "outcome_pointer": "runs/routing-dev/resume-validation-v4/validation_record.json",
 "parent": "8b0df6b0e5956bf6562457a664ee567597ea7ff438cc0890e9cecf21deca29a4",
 "previous_entry_sha256": "8b0df6b0e5956bf6562457a664ee567597ea7ff438cc0890e9cecf21deca29a4",
 "question": "Does the v1 checkpoint contract hold on the real GRPOTrainer stack \u2014 boundary-only checkpoints, exact counter/RNG/sampler restoration, aborted tails preserved-but-excluded, and an interrupted run indistinguishable from an uninterrupted one?",
 "terminal_status": "complete"
}
```

## entry 10 — grouped_probe

```json
{
 "budget_allocated_gpu_hours": 3.0,
 "cohort_selection": "outcome_blind",
 "entry_sha256": "0eca0fcb77345eac695ab380058475e77aafbc494d1eefacd19ae80a45374e04",
 "freeze": {
  "attested_environment_sha256": "372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42",
  "config_sha256": "4acf08f3f34acf7f46236b29259a5a0cabaa2b20e4a2169c3fcd68ca9ecc3b53",
  "environment_manifest_sha256": "2dc59815aca4e622d23857d2488c2e5e815657d6c915a8dfdc937e598651f9d8",
  "freeze_sha256": "88fee9217e79ef261468387f1bcafc7b2a50f07eccbd04ebc4abf86f7e0fae6b",
  "identity_manifest_sha256": "2155a8bf46c87f5288b5e8e9e76d86ae5d146f9c502bed26f381d5d93b817dd6",
  "probe_cohort_sha256": "7f31bd091aaa97664e71ecb86b17078861b4e28af284162ee6ac50338d661e3b",
  "probe_rule_sha256": "0b616b8863bf73263c11c63cd8cc1572b880e6586f15059bde642c2a397c9f7b",
  "session_preflight_sha256": "7e79f947786a7a5859aaedbebedd5decc0b3cb6439d1c8da545adbd7c6ecb08e"
 },
 "kind": "grouped_probe",
 "motivating_evidence": "246_f Step-5 pass (closeout 1a8d41fd\u2026); 231_f bound cohort 7f31bd09\u2026; 211_f \u00a75 / 232_s registered design",
 "outcome_informed": false,
 "parent": "1a8d41fde4ffb64a9d9d9886f8fbcf9dc20578ab33c3c0d72a44fa8ea9b6a44a",
 "previous_entry_sha256": "1a8d41fde4ffb64a9d9d9886f8fbcf9dc20578ab33c3c0d72a44fa8ea9b6a44a",
 "question": "What exposure do REAL grouped G=8 rollouts contain on the outcome-blind routing_dev support \u2014 structured-action validity, family routing, semantic reward variance, and actual specialist co-sampling \u2014 versus the B iid-singleton plug-ins?"
}
```

## entry 11 — closeout

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "budget_consumed_gpu_hours": 0.5192,
 "closes_entry_sha256": "0eca0fcb77345eac695ab380058475e77aafbc494d1eefacd19ae80a45374e04",
 "entry_sha256": "88c037a188c6c8f5aca21e7690ea288b76dd1f64eb53f6fc2647196d32cb0eeb",
 "freeze": {
  "freeze_sha256": "88fee9217e79ef261468387f1bcafc7b2a50f07eccbd04ebc4abf86f7e0fae6b",
  "probe_record_file_sha256": "f43c20d3263a4080c50137e15260cde5720de11b5fb1699cfc19be115dd9be9f",
  "probe_report_file_sha256": "3a001c99de1ccf15e3c6a828949ca3f285ee784c0ed1a0880358b73c742df35e",
  "terminal_artifact_hashes": {
   "actions.jsonl": "44172e55ba4ae711bd526b6d48bca3ec40b258c70db9862eff0193586c1c4356",
   "bound_cohort.json": "8056f9669d4a519271d3a19d91e9ba86e3aea5c16ef7f98524e44088a66b7cd4",
   "checkpoint_final_hashes.json": "846646c1f0119b7036f85366ac7b1327d386041ed98c0188b33bf960640c82a1",
   "checkpoint_zero_hashes.json": "846646c1f0119b7036f85366ac7b1327d386041ed98c0188b33bf960640c82a1",
   "environment_manifest.json": "0a069246b8490ca8e92b194a1cc1d0c663165bef36626b9929c71a3242925e0f",
   "identity_manifest.json": "0e988d27c6eb793addb6165cb7290a598c3c7ca84d7760f1de3771c466fa7143",
   "probe_record.json": "f43c20d3263a4080c50137e15260cde5720de11b5fb1699cfc19be115dd9be9f",
   "probe_report.json": "3a001c99de1ccf15e3c6a828949ca3f285ee784c0ed1a0880358b73c742df35e",
   "schedule.json": "6de967eeef6881cfb32a49f66b18605e828b18bb639eec38f9c1def94d8c26d5",
   "session_preflight.json": "b60be37258c4d5463829a56ba6d26806ed7010dae946373b0626b4c34065f3f4"
  }
 },
 "kind": "closeout",
 "motivating_evidence": "grouped probe complete",
 "outcome_informed": false,
 "outcome_pointer": "runs/routing-dev/probe-v1/probe_report.json",
 "parent": "0eca0fcb77345eac695ab380058475e77aafbc494d1eefacd19ae80a45374e04",
 "previous_entry_sha256": "0eca0fcb77345eac695ab380058475e77aafbc494d1eefacd19ae80a45374e04",
 "question": "What exposure do REAL grouped G=8 rollouts contain on the outcome-blind routing_dev support \u2014 structured-action validity, family routing, semantic reward variance, and actual specialist co-sampling \u2014 versus the B iid-singleton plug-ins?",
 "terminal_status": "complete"
}
```

## entry 12 — support_extension

```json
{
 "budget_allocated_gpu_hours": 1.0,
 "cohort_selection": "outcome_blind",
 "entry_sha256": "68943a64fcf9c4c41c511bcffe50d4cbaa78fc80e91b14abae10e4750944b6fe",
 "freeze": {
  "config_sha256": "22de3e4e72c41c250b0298867956336552e239f7c6aa8a8ce5d790346dacdeef",
  "extension_launch_sha256": "bd8f90ca23383312f66951fc49639aa8573eb895d88ecee9dbad19d340a555f7",
  "freeze_sha256": "03f740af3ced6dd7dfccef558b024de23f210e0717560a13b551cbeb435a993e",
  "original_surface_lock_sha256": "61c4e85a53683c9e2dbcbf15f60794935a76a86d979a69412a97f44ea9f2562b",
  "scientific_design_sha256": "951e16b9b04fe83ca9f52dba1d60543b99985a293f3c43746e1607897cdd9bdd"
 },
 "kind": "support_extension",
 "motivating_evidence": "253_s exposure reading; 260_f signed design Unit A",
 "outcome_informed": true,
 "parent": "88c037a188c6c8f5aca21e7690ea288b76dd1f64eb53f6fc2647196d32cb0eeb",
 "previous_entry_sha256": "88c037a188c6c8f5aca21e7690ea288b76dd1f64eb53f6fc2647196d32cb0eeb",
 "question": "Unit A: what structural direction support does the six-cell prefix 0..47 add \u2014 per-cell direction-disjoint latent buckets, renderer strata, non-goal_first coverage, and the eligible common-cell set for Q3?"
}
```

## entry 13 — closeout

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "budget_consumed_gpu_hours": 0.4934,
 "closes_entry_sha256": "68943a64fcf9c4c41c511bcffe50d4cbaa78fc80e91b14abae10e4750944b6fe",
 "entry_sha256": "b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd",
 "freeze": {
  "execute_env_file_sha256": "8bb3a5a2e0a845ebe050730e66b297a7cbace4f37cf8b60e4c3d6c53c0b9ce55",
  "rendered_observations": 864,
  "run_record_file_sha256": "a9af3c693f44b12a9fb435ca050544ef6a3ab91b7f5939ba41411828a3512a0d",
  "surface_lock_sha256": "ccb1c3e2db2422a82919292144c0bdecc21d2cc89cb7a3a2c69bec17a2ce6d1b",
  "terminal_artifact_hashes": {
   "comparator.json": "331efa8617b95b9230a26bf891a1b4741a87cbe0f7c40dc885eb7426c349d141",
   "disclosure.json": "c68cf9c61eb235ce5fcbf4c45d96d997319260f1c98f133cd361f30bb4bb098e",
   "execute_env_manifest.json": "8bb3a5a2e0a845ebe050730e66b297a7cbace4f37cf8b60e4c3d6c53c0b9ce55",
   "prelaunch/declaration.json": "1f4587b17c02738497a64bb3c5957c4df736d560956a639bd69268f12180caa6",
   "prelaunch/env_manifest.json": "ce5265d9368383097da3b5666c56c59d30ecabfe6dfdd79eb2ed1999227718c3",
   "prelaunch/extension_launch.json": "94a98a0d415a1deeeb8851965622238a188281bda276328a9707f12600adcbc3",
   "run_record.json": "a9af3c693f44b12a9fb435ca050544ef6a3ab91b7f5939ba41411828a3512a0d",
   "selection.json": "e0bbb75d61aa0405c86a9a69a0e68957d5db995a389d1b34f353fe1dce546724",
   "surface/declaration.json": "1f4587b17c02738497a64bb3c5957c4df736d560956a639bd69268f12180caa6",
   "surface/env_manifest.json": "ce5265d9368383097da3b5666c56c59d30ecabfe6dfdd79eb2ed1999227718c3",
   "surface/manifest.json": "8c8c1b34fcca2417c6d81f073d871ab0c93f51f0e79a6c273771ed0323777b76",
   "surface/payoffs.jsonl": "35004276d072d3b21f28ca58b03a57f2508a48b6ab9aa01f05714627ba83f565",
   "surface/support_launch.json": "94a98a0d415a1deeeb8851965622238a188281bda276328a9707f12600adcbc3",
   "surface/surface_lock.json": "fc3cd5d13af582b1f3f0ecf8d85491bb09453d729146729585bc1df87f38f7af",
   "surface/traces/traces/manifest.json": "78a2a3cdab0e5959fd6cdaad8ab9e4c7a44c71c743257aece9b62ae34ca96e0b",
   "surface/traces/traces/steps.jsonl": "8740ec8ce43e67f6da794b0dac5b350a558bca455b2a37a3efb845920dd397d6"
  }
 },
 "kind": "closeout",
 "motivating_evidence": "measured support-extension cost",
 "outcome_informed": true,
 "outcome_pointer": "runs/routing-dev/support-ext-v1/run_record.json",
 "parent": "68943a64fcf9c4c41c511bcffe50d4cbaa78fc80e91b14abae10e4750944b6fe",
 "previous_entry_sha256": "68943a64fcf9c4c41c511bcffe50d4cbaa78fc80e91b14abae10e4750944b6fe",
 "question": "Unit A: what structural direction support does the six-cell prefix 0..47 add \u2014 per-cell direction-disjoint latent buckets, renderer strata, non-goal_first coverage, and the eligible common-cell set for Q3?",
 "terminal_status": "complete"
}
```

## entry 14 — standalone_evaluation

```json
{
 "budget_allocated_gpu_hours": 1.25,
 "cohort_selection": "outcome_conditioned",
 "entry_sha256": "2314cfddcd7a1af4bc6fb680df7f47069bd416fa8775d653072c89d7f7955335",
 "freeze": {
  "attested_environment_sha256": "372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42",
  "config_sha256": "69f73a5811922bea3ef6d04a891817bec13e30729b1741f4500f2f1f2bb02d59",
  "environment_manifest_sha256": "ad1c89f16d385153c171b42cd5044d28efd4f2c9b84ed29337054258fd39dbfe",
  "freeze_sha256": "c90560ddecc271a41affc13cc0b4c0598b0178063c05d301a45ceb5def7052f1",
  "identity_manifest_sha256": "6fa701a29cbb7ae3de53d9f0ba8c22bdf8989fda6efa833febcade3a608daac8",
  "mixture_record_sha256": "0100df2bbb13447aa394d31ab87eb0dab1e0660e830186eee99028e30432bc01",
  "session_preflight_sha256": "4a2a1e3f6e268372ac31db37e5b2943f2dc58bb0b2452167836d8c4466630bec"
 },
 "kind": "standalone_evaluation",
 "motivating_evidence": "274_f frozen mixture (signed); 269_s \u00a77 option 1",
 "outcome_informed": true,
 "parent": "b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd",
 "previous_entry_sha256": "b88eba021ddc42b9d0aa2ba4abc95c04347cc450f2ea7a7e749edacf691033fd",
 "question": "Unit C: at checkpoint zero on the frozen Unit-B schedule, is the preregistered Q1 reward-varying exposure present in all four critical cells, and does each scheduled Q2 direction show cold-start marginal support for its intended specialist?"
}
```

## entry 15 — closeout

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "budget_consumed_gpu_hours": 0.9768,
 "closes_entry_sha256": "2314cfddcd7a1af4bc6fb680df7f47069bd416fa8775d653072c89d7f7955335",
 "entry_sha256": "9f4661a84e601299951f17370eb22d9aa52f970a717b80844684240c8c550996",
 "freeze": {
  "exposure_report_file_sha256": "3e708f673f4d732c2bcf885c266aac44d7731f74f61b5173d4b0f0ba056ea449",
  "freeze_sha256": "c90560ddecc271a41affc13cc0b4c0598b0178063c05d301a45ceb5def7052f1",
  "sample_record_file_sha256": "7f52e420869a369b8d9c24801d3cfac018766a7014d29ae8673c42aeefdd44f7",
  "terminal_artifact_hashes": {
   "actions.jsonl": "146d80dfe65f0bccee9524b646b61207ca6e2f861c35bb8c4dc0f0f3f5156b1a",
   "checkpoint_final_hashes.json": "cd4818390a1dac57b5b7435037e96aead2228e5863888bf7ec2dbe4ade0f1c7f",
   "checkpoint_zero_hashes.json": "cd4818390a1dac57b5b7435037e96aead2228e5863888bf7ec2dbe4ade0f1c7f",
   "environment_manifest.json": "e4cb639b8c17fd3f58fe23e328642f533de9852ee8e1b2dd5b3c80695e5af892",
   "exposure_report.json": "3e708f673f4d732c2bcf885c266aac44d7731f74f61b5173d4b0f0ba056ea449",
   "identity_manifest.json": "a0515b05f672bd9863a8e2eedf427162eb314920ce37f71185b15f3cb60e135d",
   "sample_record.json": "7f52e420869a369b8d9c24801d3cfac018766a7014d29ae8673c42aeefdd44f7",
   "schedule.json": "ca5d93f69c449fab09c9120f239040a017e377c204982354bf689dd9ae9aaae4",
   "session_preflight.json": "5d6c668ca24ef6cc16026a9a65ca6fceb7bda2b2634002a7cd5842b53c28629a"
  }
 },
 "kind": "closeout",
 "motivating_evidence": "Unit-C sample complete",
 "outcome_informed": true,
 "outcome_pointer": "runs/routing-dev/unit-c-v1/exposure_report.json",
 "parent": "2314cfddcd7a1af4bc6fb680df7f47069bd416fa8775d653072c89d7f7955335",
 "previous_entry_sha256": "2314cfddcd7a1af4bc6fb680df7f47069bd416fa8775d653072c89d7f7955335",
 "question": "Unit C: at checkpoint zero on the frozen Unit-B schedule, is the preregistered Q1 reward-varying exposure present in all four critical cells, and does each scheduled Q2 direction show cold-start marginal support for its intended specialist?",
 "terminal_status": "complete"
}
```

## entry 16 — standalone_evaluation

```json
{
 "budget_allocated_gpu_hours": 1.25,
 "cohort_selection": "outcome_conditioned",
 "entry_sha256": "29690789a6a379a790bc85c3a9acc43efa84fff26eba761efb8b35899a722d59",
 "freeze": {
  "attested_environment_sha256": "372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42",
  "config_sha256": "5b47ada33a0223c1d8322846e536cc95285d950fb8076635008b803e49dcfb1c",
  "environment_manifest_sha256": "480bf685b2652dcfeee6c4ea1bbccc0db9766fa500d184093b1991ddbd7541e5",
  "freeze_sha256": "ae51bc57476ed1a9729bd949c1651d4c88a0cbb62e310179e30af415b0fa8420",
  "identity_manifest_sha256": "7b19aeb9a642478785db1aa0d24e9126cf6d6ad3358c46b6c6a44b4dd82514af",
  "mixture_record_sha256": "135a72bf4deb77048371074636d88ffebf6bd07d1c00ae349b6fcee221975b3f",
  "session_preflight_sha256": "4a2a1e3f6e268372ac31db37e5b2943f2dc58bb0b2452167836d8c4466630bec"
 },
 "kind": "standalone_evaluation",
 "motivating_evidence": "295_f-signed B2 (pinned 135a72bf\u2026); 290_f wrap-up plan; 283_s route",
 "outcome_informed": true,
 "parent": "9f4661a84e601299951f17370eb22d9aa52f970a717b80844684240c8c550996",
 "previous_entry_sha256": "9f4661a84e601299951f17370eb22d9aa52f970a717b80844684240c8c550996",
 "question": "Unit C2: at checkpoint zero on the PINNED B2 schedule, is the Q1 reward-varying exposure present in all three direct-Q1 cells, and does each scheduled Q2 direction show cold-start marginal support for its intended specialist?"
}
```

## entry 17 — closeout

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "budget_consumed_gpu_hours": 1.0142,
 "closes_entry_sha256": "29690789a6a379a790bc85c3a9acc43efa84fff26eba761efb8b35899a722d59",
 "entry_sha256": "2bf50c1e5b31a7acf28dc9391ea4fc021a82cacb20906692558cf36174266fbe",
 "freeze": {
  "exposure_report_file_sha256": "03152f0eaa7e83b34110dc6e53be550f0f761d6141861246a70f55f5587e3abe",
  "freeze_sha256": "ae51bc57476ed1a9729bd949c1651d4c88a0cbb62e310179e30af415b0fa8420",
  "sample_record_file_sha256": "cc42c16bd925282477746644e5959a5d5848c47e18308a8fc69a437fac8e27b6",
  "terminal_artifact_hashes": {
   "actions.jsonl": "8e705317676134df447b25a72532151c8068bb238a239facc266c1fb5525af34",
   "checkpoint_final_hashes.json": "ec31727cff24274f711becca4fb19336cfb3efeeab0d5cb2ec0e51c980bb51a1",
   "checkpoint_zero_hashes.json": "ec31727cff24274f711becca4fb19336cfb3efeeab0d5cb2ec0e51c980bb51a1",
   "environment_manifest.json": "ffc0caac9994dfcca9ca706254b048919173f8b2b98c1eb5a5cc664de24d74eb",
   "exposure_report.json": "03152f0eaa7e83b34110dc6e53be550f0f761d6141861246a70f55f5587e3abe",
   "identity_manifest.json": "a1f684535d33f2fd046c52162859c54104d05f7622376a1088843cdd9ba86eb8",
   "sample_record.json": "cc42c16bd925282477746644e5959a5d5848c47e18308a8fc69a437fac8e27b6",
   "schedule.json": "c2687919cd8a00768d9f5b148957f2c2013eb1b0a636f13ecb585d6bd5598b25",
   "session_preflight.json": "5d6c668ca24ef6cc16026a9a65ca6fceb7bda2b2634002a7cd5842b53c28629a"
  }
 },
 "kind": "closeout",
 "motivating_evidence": "Unit-C2 sample complete",
 "outcome_informed": true,
 "outcome_pointer": "runs/routing-dev/unit-c2-v1/exposure_report.json",
 "parent": "29690789a6a379a790bc85c3a9acc43efa84fff26eba761efb8b35899a722d59",
 "previous_entry_sha256": "29690789a6a379a790bc85c3a9acc43efa84fff26eba761efb8b35899a722d59",
 "question": "Unit C2: at checkpoint zero on the PINNED B2 schedule, is the Q1 reward-varying exposure present in all three direct-Q1 cells, and does each scheduled Q2 direction show cold-start marginal support for its intended specialist?",
 "terminal_status": "complete"
}
```

## entry 18 — val_materialization

```json
{
 "budget_allocated_gpu_hours": 0.35,
 "cohort_selection": "outcome_blind",
 "entry_sha256": "5ef73f79804730948109bb810822c47a66664e2562388cb2a480f3c6e83d9bc0",
 "freeze": {
  "scientific_design_sha256": "a9ca17c39b2ddc347ce1bf0002cad578017a65376681703d9d307ed6e1c902fa",
  "val_config_sha256": "73376e07cf83197bb210093bb31a38f5dbf4e17101eb6d61cc273b899a6deccf",
  "val_freeze_sha256": "8ba9677fe770ec96aa0ccdd4eac96238c76058eb84aaa9f7aaf38fb378c68666",
  "val_launch_sha256": "424b692d2e9f4557d88c3f7ed852931d67fbcbe6589eae54a9c4ef35cc0fe6d2"
 },
 "kind": "val_materialization",
 "motivating_evidence": "330_f-signed precursors plan Unit V; 331_f-339_f signed freeze (rev5); 340_f prelaunch sign-off",
 "outcome_informed": false,
 "parent": "2bf50c1e5b31a7acf28dc9391ea4fc021a82cacb20906692558cf36174266fbe",
 "previous_entry_sha256": "2bf50c1e5b31a7acf28dc9391ea4fc021a82cacb20906692558cf36174266fbe",
 "question": "Unit V: the outcome-blind routing_dev_val cohort \u2014 natural mixture, never trained on \u2014 with complete authenticated 4^S surfaces, locked as the P0 checkpoint-evaluation population"
}
```

## entry 19 — closeout

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "budget_consumed_gpu_hours": 0.0637,
 "closes_entry_sha256": "5ef73f79804730948109bb810822c47a66664e2562388cb2a480f3c6e83d9bc0",
 "entry_sha256": "929e172415845471f2fe613ef71a36eb57d47492cfa58c4e511e95403a5ed11c",
 "freeze": {
  "execute_env_file_sha256": "60af673443902350c6fbf2df59c0526b3efda1d266c0844c5f04900db3ceb590",
  "rendered_observations": 90,
  "run_record_file_sha256": "a3841ad4c8e238eb00431152aa730675fe5451f254628dc995cb924f4d854f9e",
  "surface_lock_sha256": "3698caa180bea70f7df1b97ace7c480defeb97bc90d7b08c81da9d206b5309be",
  "terminal_artifact_hashes": {
   "execute_env_manifest.json": "60af673443902350c6fbf2df59c0526b3efda1d266c0844c5f04900db3ceb590",
   "overlap_report.json": "c82f0faa6af0491ace0dfe44bd8ce9a7424d41226593ba6bfcc60b7d5ea1e618",
   "prelaunch/declaration.json": "e202257e177b513ed4e838023822374b5e1a8e1032220eb2789107c6a616bf05",
   "prelaunch/env_manifest.json": "4a52dfd818a3d717be189769883e606bfac3690df0a04918f0efe95516e7ae6d",
   "prelaunch/val_freeze.json": "e2f1f2d9afee8c2302c582f9588a60735509e59696b05fbf36d1d36eef372ea1",
   "prelaunch/val_launch.json": "e2a82208f082da94ae54a8219b531055977a894e736f71b69ff01b8a814491e8",
   "run_record.json": "a3841ad4c8e238eb00431152aa730675fe5451f254628dc995cb924f4d854f9e",
   "surface/declaration.json": "e202257e177b513ed4e838023822374b5e1a8e1032220eb2789107c6a616bf05",
   "surface/env_manifest.json": "4a52dfd818a3d717be189769883e606bfac3690df0a04918f0efe95516e7ae6d",
   "surface/manifest.json": "170f8f525c3cac693b7c3e5680a912af7c9308b6db6b80e4f91af3b883904c82",
   "surface/payoffs.jsonl": "68444511291684a3a9cf003b517d6758bd01465bdb19521f7e2745a912c45351",
   "surface/support_launch.json": "e2a82208f082da94ae54a8219b531055977a894e736f71b69ff01b8a814491e8",
   "surface/surface_lock.json": "e337e644a1087fc91751201756c06372d02c1be71ed95e27485a5ab7a1740407",
   "surface/traces/traces/manifest.json": "e9ed56de06a5250c29a54d14543b54dcb70276d02a8a3dbaf83dab81882d5783",
   "surface/traces/traces/steps.jsonl": "fbb37cfd161aea9b61300f184b6b961ee325f537ab0afe60b893f4a70e43aa3c",
   "val_lock.json": "675fd8086a56791c72094119269db164e749e261ec4c477a853f5d8fb5a698d3"
  },
  "val_lock_file_sha256": "675fd8086a56791c72094119269db164e749e261ec4c477a853f5d8fb5a698d3",
  "val_lock_sha256": "2aecdf28ad25cae10e494aa9fc1a95138a9feb5a29ab0636314b847987caf19d"
 },
 "kind": "closeout",
 "motivating_evidence": "measured val-surface cost",
 "outcome_informed": false,
 "outcome_pointer": "runs/routing-dev/val-surface-v1/run_record.json",
 "parent": "5ef73f79804730948109bb810822c47a66664e2562388cb2a480f3c6e83d9bc0",
 "previous_entry_sha256": "5ef73f79804730948109bb810822c47a66664e2562388cb2a480f3c6e83d9bc0",
 "question": "Unit V: the outcome-blind routing_dev_val cohort \u2014 natural mixture, never trained on \u2014 with complete authenticated 4^S surfaces, locked as the P0 checkpoint-evaluation population",
 "terminal_status": "complete"
}
```

## entry 20 — reserve_update

```json
{
 "budget_allocated_gpu_hours": 0.0,
 "entry_sha256": "6fea9e3be1f2043d38c297e50bcce36b9d225ce741d61de3ed3a56054e8dba51",
 "freeze": {
  "cycle_record_sha256": "d617ab5fbb609fc89c250e6a79627b2ed28e54603fa1fed2253d855a3abaccdc",
  "r_cycle_record_file_sha256": "77fed28121396377634eff6d9c25ad3a918990f6cd0bad5c1112b4caa77d3098",
  "r_cycle_record_sha256": "e13cf4d3605393186499cab0490d5e2bc289c77841b146841d0f52258f422265",
  "support_closeout_sha256": "6506f117180c9b2a2fafbd745ca9b19082b18e2c63d49a71e0a2dbce4da4c283",
  "surface_lock_sha256": "61c4e85a53683c9e2dbcbf15f60794935a76a86d979a69412a97f44ea9f2562b"
 },
 "kind": "reserve_update",
 "motivating_evidence": "330_f-signed plan Unit Y; the committed cycle and reserve records",
 "outcome_informed": false,
 "parent": "929e172415845471f2fe613ef71a36eb57d47492cfa58c4e511e95403a5ed11c",
 "previous_entry_sha256": "929e172415845471f2fe613ef71a36eb57d47492cfa58c4e511e95403a5ed11c",
 "question": "Unit Y: the FINAL R_cycle reserve \u2014 the cycle cohort and its evaluation rule are frozen; the reserve becomes the rounded maximum of the registered basis and the itemized closure ceiling",
 "reserve": {
  "assumed_cohort_size": 90,
  "evaluation_multiplier": 2.0,
  "itemized_ceiling_gpu_hours": 1.0,
  "measured_seconds_per_observation": 2.44,
  "measured_support_gpu_hours": 0.0732,
  "r_cycle_gpu_hours": 1.0,
  "rounding": "ceil_to_whole_gpu_hours",
  "status": "final"
 }
}
```
