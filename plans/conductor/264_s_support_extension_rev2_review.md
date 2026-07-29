## Verdict

Rev2 is much closer, but I would **not launch yet**. The selector, Q3, CLI, retry, and run-root fixes are correct. Two scientific-integrity issues remain.

### [P1] The new “observable subtype” is not the frozen public subtype

[`observable_subtype`](/home/ken/qwen-grpo/tasks/routing/extension_run.py:399) derives labels from public key names plus collision flags. This causes two problems:

- It collapses genuine public subtypes. A 48-latent probe found:

  - `math_atomic`: all T1/T2/T3 collapsed into one label.
  - `lookup_math`: plus/minus are not represented.
  - `fork_join`: lookup-first/code-first are not represented.

- `public_numeric_collision` and especially `sink_public_numeric_collision` depend on comparison with private/reference-program node values. They are not observable from the public prompt and therefore leak generator-derived information into a purported public-shortcut control.

Use the existing frozen contract in [`baselines.py`](/home/ken/qwen-grpo/tasks/conductor/baselines.py:127):

- `baselines.public_feature_record`
- `baselines.observable_subtype`
- its derived `public_numeric_values`

Collision diagnostics can remain separately labelled as generator-side analysis, but must not enter `cell+renderer+subtype`. Tests should assert the exact permitted subtype levels, not merely count that every observation received some label.

### [P1] ScaleLift still trusts a forgeable comparator marker

[`validate_extension_comparator_for`](/home/ken/qwen-grpo/tasks/routing/telemetry.py:132) verifies the extension lock and flags, but does not authenticate:

- `original_surface_lock_sha256`
- `source_record_sha256`
- that `c_fixed_dev` equals the worker derived from the original Step-4 record

I constructed a correctly rehashed record with bogus source/original locks and `c_fixed_dev = 3`; the real consumer accepted it and returned worker 3.

Construction-time and post-hoc verification do not satisfy the signed requirement that the telemetry consuming boundary verify the original comparator. At consumption, reverify the original record against the original locked surface and require all three fields above to agree—without selecting on the extension.

Add a regression showing a rehashed worker-3/bogus-source record fails through `group_stats`. The positive test should also assert an exact, nonzero ScaleLift case rather than only checking that a float was produced.

### Correctly closed

- Candidate selection is restricted to indices `6–47`.
- Legacy `0–5` support is disclosure/Anchor-only.
- Ordered, latent-disjoint, quota-bounded selection is implemented.
- All Code cell × direction dispositions are present.
- Q3 common-cell eligibility uses acceptable disposition states.
- CLI, run-root binding and cache-only retry work.
- Full suite: `995 passed` under warnings-as-errors.
- All hashes, costs, ledger identity, prelaunch bytes and environment attestation verify.

Minor documentation correction: `263_f` says prelaunch was prepared at `0213b32`; the environment manifest records `35599ca`. More precisely, it used source bytes from `0213b32` and was prepared at `35599ca`.

After the two P1 repairs, regenerate the prelaunch/freeze and perform one narrow changed-lines review. There is no need to reopen the selector architecture.