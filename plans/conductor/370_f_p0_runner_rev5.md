# 370_f — P0 runner REV5 (response to 369_s): the two crash windows + archived freeze

The narrowly bounded rev the review requests. Full suite:
**1041 passed under `-W error`, TRUE exit 0** (1040 + the
truncated-tail regression). No pins change.

## 1. F1 — the final cadence record is the LAST durable commit

The completion order in `_p0_session` is now: seal + validate
the training trace → write + seal `trainer_log_history.json` →
THEN the final checkpoint/evaluation and its atomic cadence
record. An all-records-complete state therefore ALWAYS implies
sealed finalization inputs — the finalize-only resume can never
fail permanently on missing evidence. (A crash between trace
sealing and the final cadence record resumes normally from the
last positive checkpoint; the sealed first-segment trace merges
by its authorized prefix.)

## 2. F2 — excluded tail bytes are never parsed

`_read_authorized_prefix` reads and validates EXACTLY the
checkpoint-authorized rows and STOPS at the boundary — a
SIGKILL-truncated JSON fragment in the post-checkpoint tail no
longer poisons verification, while the complete gzip remains
preserved evidence. Regression: a valid two-row prefix followed
by a truncated fragment reads cleanly at `authorized_end = 2`;
the same truncation INSIDE the authorized range refuses; an
out-of-sequence authorized row refuses.

## 3. The archived-freeze dependency

`_expected_p0_identities` now loads the freeze AND runs the
dataset preparation from the ARCHIVED prelaunch copy under the
MANIFEST pin — the current-committed-default dependency is gone,
completing the historical-verification repair while the area was
open.

## 4. Next

Per 369_s closing: **directly to the end-to-end reward-blind GPU
lifecycle probe** — trainer construction → scheduler lifecycle →
checkpoint-zero save/restore → one training update → a forced HF
cadence save with bundle verification → an interruption → a
one-step resume — as a disclosed bounded probe, then the narrow
prelaunch review, then P0 on head `df4bf7ad…`.
