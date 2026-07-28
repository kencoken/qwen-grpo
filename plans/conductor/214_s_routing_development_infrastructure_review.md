## Verdict

Changes requested before Step 4. The package split is sensible and all tests pass, but several contracts currently exist only descriptively rather than at the consuming boundary.

I independently confirmed:

- 39/39 focused routing tests pass.
- 955/955 full tests pass under `-W error`.
- `git diff --check` is clean.
- No prior evidence files changed.

## Blocking findings

### P1 — The support surface is not bound to its pre-execution lock

[dev_support.py](/tmp/qwen-grpo-932802f-review.8YBh23/tasks/routing/dev_support.py:134) does not put the full runtime profile, cache identity, routing source/environment identity, or actual driver in the declaration. Materialization checks only worker-visible fingerprint, pool fingerprint, and visibility.

I changed the declared request contract to a materially different value; materialization still executed and accepted the real `task_last` contract.

Furthermore:

- `load_dev_surface()` verifies internal consistency but cannot require the externally frozen declaration/surface lock.
- `select_c_fixed_dev()` accepts arbitrary or empty `surface_hashes`.
- `bind_probe_cohort()` likewise copies arbitrary hashes without verifying them.

Step 4 therefore could persist a valid-looking surface, comparator, or probe cohort under an unrelated lock.

Introduce one closed surface-lock artifact derived from the persisted files and launch identity. Require it at materialization, loading, comparator selection, and probe binding. It should include runtime/request/cache, source/environment/driver, declaration, payoff and trace identities.

### P1 — The ledger cannot represent the next launch lifecycle

[ledger.py](/tmp/qwen-grpo-932802f-review.8YBh23/tasks/routing/ledger.py:169) has three related problems:

1. A prelaunch entry records the maximum allocation, but append-only entries cannot later acquire measured consumption. A second “closeout” entry would charge both allocation and consumption.
2. `check_launch_admissible()` refuses every launch without an existing reserve, but the initial support-materialization run must occur before its timing can establish the provisional reserve.
3. Removing the final ledger entry leaves a valid hash chain; `read_ledger()` cannot detect suffix deletion without an externally committed expected head.

Add linked launch/closeout records, with envelope accounting replacing an open launch’s allocation with its measured closeout cost. Add an explicit initial-support admission path, then apply the ordinary reserve rule afterward. Bind the expected ledger head externally.

### P1 — Checkpoint/resume does not yet bind restorable training state

[checkpoint.py](/tmp/qwen-grpo-932802f-review.8YBh23/tasks/routing/checkpoint.py:89) hashes metadata but not the actual adapter, optimizer, scheduler, scaler or raw RNG artifacts that “travel beside” it.

`capture_rng_state()` is also incomplete. In particular, it omits NumPy’s position and Gaussian state. I reproduced two different NumPy states—positions 2 and 4—producing identical captured state and hash.

`merge_segments()` additionally:

- has no run/config/checkpoint identity or parent linkage;
- does not enforce segment ordering;
- can accept rows beyond a complete segment’s checkpoint cutoff;
- can construct a contiguous-looking trajectory from impossible segment histories.

Add a checkpoint-bundle manifest hashing every state artifact, complete restorable RNG serialization, validated accountant restoration, and identity/parent/cutoff-aware segment merging.

### P1 — Telemetry trusts rather than authenticates scientific inputs

[telemetry.py](/tmp/qwen-grpo-932802f-review.8YBh23/tasks/routing/telemetry.py:75) accepts caller-supplied reward, metadata, pair direction and `c_fixed_dev`.

I reproduced a valid assignment whose authenticated payoff was `1.0` being silently reported with reward `0.5`. The code also permits:

- observation metadata from a different observation;
- a flipped caller-supplied C2 winner;
- an arbitrary fixed worker changing `ScaleLift`;
- invalid completions carrying nonzero rewards.

At this boundary, validate exact action schema and require rewards to agree with the authenticated surface. Derive or cross-check the pair direction and comparator from that same locked surface.

The required broader `ModelAcc` is also absent. Conditional C2 is implemented, but C1 cannot substitute for the full-denominator model-selection view where malformed and wrong-family choices score zero.

### P1 — The “first probe” builder does not enforce the signed probe

[cohorts.py](/tmp/qwen-grpo-932802f-review.8YBh23/tasks/routing/cohorts.py:33) accepts `routing_dev_val`, one renderer, `G=1`, and prefix length 1. The signed first probe requires:

- `routing_dev`;
- group size 8;
- renderer crossing;
- a factor-balanced prefix.

The generator’s factor blocks have sizes 1, 2, 3 and 6, so the common factor-balanced prefix must be divisible by 6. Either make this first-probe-v1 schema enforce those values or separate the generic later-reprobe builder from the exact authorized first-probe builder.

Cohort and natural-mixture validation should also require all six cells and the intended renderer crossing rather than assigning “natural” weights to whatever partial population it receives.

## Required reporting repairs

Before the grouped probe, aggregation must also add the items already required by `211_f`:

- per-worker frequencies;
- per-assignment frequencies;
- repeated-output concentration;
- renderer-within-latent, latent-within-cell, equal-cell weighting;
- raw numerator/denominator support for the applicable accuracy views.

`group_stats()` currently drops `latent_program_id`, so the registered hierarchical weighting cannot be reconstructed from its aggregate inputs.

## Package move and B archive

The `tasks/routing/` split is a good choice. Strictly, the B verifier retires because the necessary namespace additions changed `tasks/conductor/program.py` and `types.py`; placing the remaining work under `tasks/routing/` prevents further unnecessary churn.

Historical verification at `0f56a65` is an acceptable preservation strategy. I would retain an exact checkout/verification command in the preservation documentation, but this is not a blocker.

The implementation is a strong base—particularly the complete `4^S` loader and its terminal rescoring—but I would not freeze or launch Step 4 yet. These are reachable pipeline failures, not adversarial Python-object hardening, and they are cheapest to correct now before any GPU evidence exists.