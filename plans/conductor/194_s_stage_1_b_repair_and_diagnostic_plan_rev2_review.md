`193_f` closes the four issues raised in `192_s`, but I found three narrow items that should be corrected before sign-off. No broader redesign is needed.

### 1. Smoke must authenticate the launched bytes

The current order is:

1. implement;
2. smoke;
3. changed-lines review and fixes;
4. lock and launch.

A review-driven fix could therefore change the diagnostic path after its only smoke. I need to correct the ordering I previously suggested.

Use:

1. implement and test;
2. changed-lines review and repairs;
3. freeze the candidate source/configuration digest;
4. smoke exactly those bytes, recording source digest, contract hash, model/tokenizer revision and generation-config hash;
5. commit a launch lock proving `smoked executable == launched executable`;
6. run the diagnostic.

Any executable change after the smoke returns to review and requires a newly authorized smoke.

### 2. Tighten the estimand populations and count boundary

The frozen support contains nine Code-pair observations, but only three have distinct payoffs: two favour worker 2, one favours worker 3; the other six are ties.

Rev3 should state:

- `p2`, `p3` and `g8` direction summaries use only `payoff_w2 != payoff_w3`;
- tied pairs are reported separately and never described as gradient-bearing;
- parse/valid/action/reward/zero-variance/diversity summaries use all 18 observations;
- these are iid-singleton plug-in predictions, not measurements of batched GRPO groups or actual gradients;
- `E[# distinct levels in 8] = Σ_L [1 − (1 − p_L)^8]`.

Also define:

- `parseable`: UTF-8-encodable and JSON decoding succeeds;
- `valid`: the complete frozen `parse_routing_action` schema succeeds—not merely correct length.

The raw verifier must reproduce both counts exactly, bind `raw_completions_sha256`, and enforce `reward_0 == 256 − valid` under the frozen ladder.

### 3. Complete seed and archive identity

Replace “frozen 8-byte SHA-256 recipe” with the exact formula:

`uint64_be(SHA256(utf8(domain + U+001F + key))[0:8])`

Freeze unpadded indices `0…255`, the exact 9,216-key registry, and its digest.

Add the diagnostic success/abort archiver explicitly to implementation scope. It needs a unique atomic evidence root, exact file set and byte hashes; success requires the authenticating verifier, while abort preserves partial raw data and the run record without trusting a complete artifact.

Everything else is in good shape, including the complete request manifest, raw rescoring concept, nonlinear aggregation order, direction reporting, shared smoke path, deadlines, VRAM preflight and descriptive-only scope. The 9,216-draw run remains credible on the 4090 within three hours.

After these focused corrections, I recommend sign-off without another broad review.