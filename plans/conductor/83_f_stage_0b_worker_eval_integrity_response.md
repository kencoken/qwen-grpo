# Response to 82_s — worker-eval integrity review

**Review target:** `13491e7`. **This response:** the commit carrying this
document. All findings were reproduced as described before fixing; the
full suite is at 543 tests (8 new), `-W error` clean.

## Triage principle

Agreed with Ken before implementation: prioritize corrections for failure
modes reachable through ordinary operator or code-drift error — the ones
practically likely to change pipeline results — over hardening whose
exploitation requires deliberately rehashing artifacts. Every blocking
finding had at least one realistic path and received a fix; three
sub-recommendations were declined with rationale below, and one
(commit equality in candidate comparisons) was resolved to a middle
ground Ken signed off.

## Finding-by-finding disposition

### Finding 1 — P1 admission preconditions: **fixed**

The realistic path was not forgery but the CLI's own flexibility: `p1`
legitimately accepts small diagnostic shapes (`--per-cell 1`, one
renderer), and `admit` checked only that the three runs were mutually
consistent. `admit_singleton` now requires, beyond the existing
held-fixed and equality checks:

- an explicit `expected_namespace` (CLI `--namespace`, required — no
  default, since `worker_dev` awaits the D1 erratum);
- the registered design: per-cell 10, the full three-renderer crossing,
  private visibility, exactly 300 cases (`P1_PER_CELL`/`P1_CASES`);
- per-case `request_sha256` equality across all three runs (equal
  completions over different request bytes now fail — this also catches
  generator/prompt drift between invocations, e.g. across a rebase);
- one clean commit across all three runs, and three distinct pids as
  fresh-process evidence.

The applied thresholds are recorded in the verdict output. The missing
§7.4 authority is now `confirm_repeat_run` (plus the `confirm` CLI
subcommand): two *loaded evaluator runs* of one candidate must agree on
every manifest field outside run identity, on case support, and bit-wise
on `request_sha256`/completion/finish-reason/token-count/cap for every
called row. Tests: `test_admit_preconditions_reject_unregistered_designs`,
`test_confirm_repeat_run_and_cli`.

### Finding 2 — P0 physical-chunk fidelity: **fixed**

Accepted in full — this was the one finding that would silently corrupt
the physics P0 exists to reconstruct (a declared 17-request chunk
executing as 16+1 inside `pool.generate`). `load_cohort` now requires:

- a pinned `user_message_sha256` on every entry (previously optional);
- nonempty chunks, no duplicate entries;
- chunk size ≤ the endpoint's microbatch from the runtime profile, with
  an error message naming the silent-split hazard.

The CLI threads the built profile into the check. Test:
`test_p0_cohort_requires_pins_and_exact_physical_chunks`.

### Finding 3 — provenance vs. actual execution: **fixed (verify form)**

- **Cache half — accepted as the most practically dangerous item in the
  review:** `build_runtime(profile)` defaults to the real SQLite cache,
  so the corrupting state was one forgotten argument away, and a cold
  cache mislabels every row `disabled`. `singleton_call` now verifies
  the cache *is* the no-op type before generating (the cache-hit check
  remains as a second layer). Test:
  `test_singleton_call_requires_noop_cache_before_generation` asserts
  refusal happens before any generation.
- **Profile half — implemented as verification rather than API
  immutability:** `build_manifest` rederives the profile fingerprint
  from `runtime.profile` and refuses on drift; `load_run` rederives the
  stored manifest profile's fingerprint likewise. This gives the same
  detection guarantee as privatizing `Runtime.profile` without API
  churn. Tests: `test_manifest_refuses_profile_mutated_after_build`,
  and the `altered_profile` case in
  `test_loader_rejects_relabelled_and_impossible_rows`.

### Finding 4 — loader identity: **fixed**

Accepted — not for the tampering reproduction primarily, but because the
same missing checks would mis-load runs across *code drift*, and a
concrete instance is pending: the Math endpoint-swap erratum. A
pre-swap run loaded under post-swap code would previously have rescored
silently under the new schedule. The loader now:

- requires every isolated row to be `called` (§4.3 scheduled == called;
  an impossible blocked-with-value row is refused);
- compares each isolated row's `endpoint_name`, `observation_id`,
  `evaluation_mode`, `position`, predecessor source/positions,
  `user_message` and `binding_sha256` against the regenerated case;
- applies the corresponding identity comparison to composed rows
  against the regenerated plan.

Test: `test_loader_rejects_relabelled_and_impossible_rows`.

### Finding 5 — label-driven identity / permissive comparison: **fixed in four parts, one declined**

- **Frozen bundles resolve through the registry:** with
  `frozen_candidate=True`, the declared bundle must equal
  `resolve_prompts(revision)` exactly, and the registry's status (never
  the caller's dataclass field) must be FROZEN. Hand-built draft
  bundles remain legal for candidate iteration. A frozen-candidate
  manifest additionally requires the full renderer crossing. Tests:
  `test_frozen_candidate_refuses_forged_bundle`,
  `test_frozen_candidate_requires_full_renderer_crossing`.
- **The declared dimension must actually differ:**
  `compare_worker_eval_runs` now refuses arms that are identical on the
  declared dimension (fingerprint paths alone do not count), catching
  the "I thought I swapped the prompt" configuration error.
- **The model allowlist is the checkpoint identity only:** per-endpoint
  `model_id`/`revision` plus what follows (fingerprints, chat
  templates, tokenizer facts). Token caps and microbatch can no longer
  ride along under a declared "model" difference.
- **Renderer subsets are not comparable:** both runs must carry the
  full three-renderer crossing — comparing candidates on
  `resource_first` alone is precisely the 78_s finding-3 mistake this
  branch exists to prevent. Diagnostic subsets remain runnable and
  loadable; they are simply not comparison- or freeze-grade.
- **Git (middle ground, Ken's sign-off):** comparisons now *refuse
  dirty worktrees* on either side; commit *inequality* between
  candidate runs remains permitted but is always present in the
  reported differing fields. Rationale: comparability is carried by the
  held-fixed manifest fields plus loader-side population regeneration,
  not by commit identity, and refusing would invalidate hour-scale GPU
  runs over docs-only commits. P1 *admission* is stricter (one clean
  commit), because its three runs are minutes apart by design.
  Test: `test_comparison_requires_real_difference_crossing_and_clean_tree`.

### Lower-severity items

- **`node_family` is now the node's operator** (`seq_at`, `modular`,
  …), not the endpoint class — accepted as the most result-relevant
  item in the review: worst-node-stratum analysis (78_s endpoint
  recommendation) needs operator granularity, and the endpoint class
  was redundant with the endpoint column. Summary strata keys become
  `endpoint|cell|operator|renderer`.
- **Summary gap endpoints:** `best_renderer` added alongside
  `worst_renderer`; with `by_renderer` and `paired` counts, the §5.5
  max–min gap and flip rate derive exactly. Rates stay out of the
  stored summary to preserve counts-only exact rederivation.
- **Manifest environment:** best-effort `nvidia_driver` via
  `nvidia-smi` added. Applied P1 thresholds are recorded in the admit
  verdict (above).

## Declined, with rationale

1. **Privatizing/freezing `Runtime.profile`** — the fingerprint
   rederivation at both manifest build and load gives equivalent
   detection with no API churn; nothing in the codebase mutates it.
2. **Verifying the request contract against the builder
   implementation** — that amounts to hashing source code. The digest
   already binds the block order and the exact final-line string; a
   behavioral change to `build_worker_request` moves the request
   hashes, the chat byte fixtures, and the loader's regenerated
   `user_message` comparison. In-repo, version-controlled code is not
   label-driven identity in the sense the plan guards against.
3. **The complete status-conditional row schema** — 80_f finding 1
   deliberately rejected a schema-validation layer. The load-bearing
   conditional fields (request/completion/cache on called rows, nulls
   on uncalled) were already enforced; finding 4's identity checks
   close the remaining exploitable combination (status relabeling).
4. **Model generation-config EOS set in the manifest** — it is a
   property of the pinned model revision, known only after the lazy
   model load, and validated at decode time; the tokenizer-level EOS is
   already recorded in `tokenizer_facts`.

## Verification

- Full suite: 543 passed (8 new tests), warnings-as-errors clean.
- Every reproduced behavior in the review now has a failing-then-fixed
  test at the boundary the reviewer named.
- No change to generation, rendering, parsing, tool, or cache behavior;
  the fixes are validation and provenance only, per the review's own
  scoping.
