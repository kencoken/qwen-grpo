# 92_s §6 prerequisite implementation + `code_local_v1` draft

**Status:** implemented; full suite 560 tests, `-W error` clean. The
`code_local_v1` prompt text (§2 below) is submitted for Ken's and the
reviewer's review — it must be approved and its hash frozen into `92_s`
before that document changes to FROZEN. No `worker_dev` command has run;
the D1 ratification record (92_s §6.1) remains Ken's entry.

## 1. What landed, per 92_s §6

- **§6.4 — the contracts configure the builder.**
  `render.build_worker_request` takes a `contract` key:
  `worker-blocks-v0` (unchanged bytes, pinned by the existing fixtures)
  or `worker-blocks-task-last-v1`
  (Problem → Resource(s) → Previous → Task → the exact §2.2 final line;
  a golden byte test pins the order). The contract threads through the
  single shared `build_worker_call` and `WorkflowItem.request_contract`,
  so isolated and composed calls render identically per contract; a
  `direct` task-last combination is refused.
- **§6.5 — candidate registry and physical sharing.** New
  `candidates.py`: the four §2.1 checkpoints with declared parameter
  counts, 16 candidate ids (8 per tranche) in the §7 alternating arm
  order, the frozen sentinel order, per-candidate runtime profiles
  (Code worker swapped, profile prompt label bound to the bundle), and
  `physical_layout`. `WorkerPool` now keys model/tokenizer objects by
  `(model_id, revision)` — a generic-Code arm holds ONE resident 1.5B
  checkpoint, a Coder arm two — with per-call endpoint prompts and
  unchanged per-endpoint fingerprints, plus `checkpoint_report()` for
  measured layouts. Tests pin the sharing counts and parameter-sum
  ordering. The declared parameter counts are best-known values,
  verified against `sum(p.numel())` at first GPU load; a mismatch is a
  registry fix before freeze.
- **§6.6 — candidate-aware P1 and admission.**
  `p1 --candidate <id>` resolves the registered profile/bundle/contract
  and emits the candidate key, contract digest and §6.9 sequence
  hashes. Admission for candidate runs regenerates the *candidate's*
  plan — including canonical rendered request hashes from the
  registered prompt, tokenizer/chat template and user message — and
  verifies the profile fingerprint, prompt hashes and contract digest
  against the registry. Cross-admission fails in tests: the same runs
  relabelled as the task-last or `code_local_v1` sibling are refused.
- **§6.7 — the thin runner.** `run --candidate <id> --mode
  isolated|composed` writes one complete RunWriter artifact over the
  full `worker_dev` population, with the planned physical layout in the
  manifest and loader-validated `measurements.json` (wall, idle/peak
  reserved VRAM, per-endpoint latency, actual checkpoint report with
  measured parameters). `RunWriter` still refuses existing directories;
  restarts are fresh run ids.
- **§6.8 — comparisons.** `request_contract` comparison is re-enabled,
  requiring a digest difference *and* proven per-case request-byte
  differences (a metadata-only arm refuses as a no-op). Prompt
  comparison is endpoint-scoped (`prompt_endpoint`): only the declared
  endpoint's prompt bytes and derived fingerprints may differ; other
  endpoints' hashes must be identical. `build_manifest` refuses a
  profile whose `prompts.d16_revision` disagrees with the resolved
  bundle.
- **§6.9 — support plans.** `candidate_p1_cases`/`candidate_full_cases`
  with the loader-proven nested-projection relationship (P1 = the
  first-10-latent projection of the full plan, in plan order) and
  canonical + exact-reversal sequence hashes in every P1 artifact.
- **§6.10 — screening and reveal (the minimal honest version, per the
  agreed workflow-discipline reading).** `screen` derives, per
  candidate: admission, cost, and the three-state
  `target_prefix_clean` — computed by strict recompute (labels
  regenerated, tools re-run; stored semantic fields never trusted) —
  and fixes the launch manifest (prefix-clean candidates + one
  sentinel per contract from the frozen order), printing only those
  fields. `reveal` strict-loads every launched full run, enforces
  unchanged-endpoint byte equality across arms sharing a contract
  (mismatch = reproducibility stop), derives §4.1 target verdicts and
  applies the §8 lexicographic selection mechanically.
- **§6.2 — the P0 cohort is frozen.**
  `gen_p0_cohort.py` reconstructed the physical chunks from the
  retained `d16-rev9-confirm` trace:
  **90 Code calls in chunks [16, 16, 13, 16, 16, 13]** — two 45-request
  waves each split at microbatch 16, exactly the recorded rev9
  grouping. Every entry's request hash was verified against the frozen
  generator before writing. The committable fixture is
  `tasks/conductor/fixtures/p0_rev9_code_cohort.json`
  (sha256 `c0f53203a62662b3…`); a test pins its loadability and chunk
  structure. Per §6.3, the Math per-cell-15/30 observation is retained
  as historical evidence only — no cohort was manufactured for it.

## 2. `code_local_v1` — draft for review (92_s §2.3)

Registered as `PROMPT_REVISIONS["code_local_v1"]` (Lookup/Math texts
byte-identical to rev9; code sha256 `7aa430845b7ca12c…`). Derivation,
each choice traceable to retained evidence only:

1. **Task-locality is the first sentence** ("Complete only the assigned
   Task — the Problem is background context…"): the dominant
   alternative-renderer failure composed the global Problem (78_s
   finding 3); rev3 carried this rule mid-prompt, rev4 cut it, rev9
   never restored it explicitly.
2. **No wrong exemplars anywhere.** rev7 showed a copyable wrong string
   that flatters the model's defensive prior becomes a template; rev8
   showed removing the copy still leaves re-invented guards. rev9 kept
   three "Wrong:" contrasts; v1 states positive rules only ("written
   exactly as given", "any step_k you are given is already a valid
   zero-based index, even when it is large").
3. **The rev4 winning layout** (critical rules first, three worked
   examples, rules + envelope restated last) and **the rev9
   matched-regime `step_1 = 10` demonstration** are kept; demonstration
   payloads are the same machine-verified objects, interpolated at
   import so the text cannot drift from what the runtime accepts.
4. **Model-neutral:** no wording targets a specific checkpoint's
   quirks; no parser repair, retry, range hint or hidden answer
   information.

Approving this text (or amending it — any change re-hashes) is a freeze
prerequisite; after `92_s` freezes, no edits are possible without a new
preregistration.

## 3. Remaining before Tranche A

1. Ken records D1 ratification (92_s §6.1) — gates every `worker_dev`
   command including P1.
2. Ken + reviewer approve `code_local_v1` (§2 above).
3. Ken freezes `92_s` with the content hashes (prompt shas, contract
   digests, cohort sha, candidate registry).
4. Then, on this machine: P0 replay (original ×2, reversed, singleton —
   artifact + exit 0 each), Tranche A's eight P1 triplets, `screen`,
   the launched full runs, `reveal`.

The `coder_3b` revision pin (`488639f1…`) is the one checkpoint never
exercised locally; it is validated (tokenizer resolution + parameter
check) at first Tranche B use, which is acceptable because Tranche B
only triggers on a documented Tranche A failure.
