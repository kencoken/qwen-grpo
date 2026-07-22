"""Generate the committed Stage-0 canary and sentinel fixtures from the
retained 99_f/104_f run artifacts (106_s §§9.4-9.5).

- **Canary**: the first (sorted by case id) `code_atomic` worker-2 vs
  worker-3 node-correctness disagreement between the retained
  `generic_1p5b-task_last-rev10` and `generic_3b-task_last-rev10` runs.
  Atomic cell ⇒ node reward = terminal reward, so the pair is a
  deterministic terminal-reward disagreement. Selected by identity rule
  (first sorted), deliberately FOR disagreement — excluded from every
  aggregate summary. Its latent ordinal is outside the ordinal-0
  support by construction.
- **Sentinels**: the six first-latent Code-node cases (code_atomic n1
  and fork_join n2, three renderers each) with each worker's retained
  completion and generation telemetry. Workers 2 and 3 must reproduce
  these bit-for-bit in fresh singleton processes (§9.5).

Provenance: source run paths and the SHA-256 of every consulted
artifact file are recorded inside the fixtures.

Run:  uv run python -m tasks.conductor.gen_stage0_fixtures
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from .payoff_support import CANARY_PATH, SENTINELS_PATH

W2_RUN = Path("runs/99f-rev10/generic_1p5b-task_last-rev10-sel-r1")
W3_RUN = Path("runs/104f-3b-screen/generic_3b-task_last-rev10-sel-r1")

SENTINEL_CASES = [
    f"{cell}:worker_dev:00000:{latent_sha}:{renderer}:private:{node}"
    for cell, latent_sha, node in (("code_atomic", "641a0144", "n1"),
                                   ("fork_join", "5b6d01a9", "n2"))
    for renderer in ("resource_first", "goal_first", "bound_var")
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path, want_scores: bool) -> dict[str, dict]:
    rows = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if want_scores and row.get("row_type") != "node":
                continue
            rows[row["case_id"]] = row
    return rows


def build_canary() -> dict:
    w2 = _load(W2_RUN / "scores.jsonl", True)
    w3 = _load(W3_RUN / "scores.jsonl", True)
    disagreements = sorted(
        case for case, row in w2.items()
        if row["cell_id"] == "code_atomic"
        and row["node_correct"] != w3[case]["node_correct"])
    case = disagreements[0]
    cell, namespace, ordinal, _, renderer, visibility, _ = case.split(":")
    observation_id = case.rsplit(":", 1)[0]
    return {
        "canary": "stage0-w2-w3-disagreement-v1",
        "selection_rule": "first sorted code_atomic node-correctness "
                          "disagreement between the retained rev10 "
                          "worker-2 and worker-3 runs",
        "case_id": case,
        "observation_id": observation_id,
        "cell_id": cell,
        "namespace": namespace,
        "ordinal": int(ordinal),
        "renderer_id": renderer,
        "visibility": visibility,
        "expected": {
            "worker_2_correct": w2[case]["node_correct"],
            "worker_3_correct": w3[case]["node_correct"],
        },
        "in_ordinal0_support": int(ordinal) == 0,
        "aggregate_exclusion": "excluded from every aggregate smoke "
                               "reward/variance/routing summary "
                               "(106_s §9.4)",
        "provenance": {
            str(W2_RUN / "scores.jsonl"): _sha(W2_RUN / "scores.jsonl"),
            str(W3_RUN / "scores.jsonl"): _sha(W3_RUN / "scores.jsonl"),
        },
    }


def build_sentinels() -> dict:
    w2_calls = _load(W2_RUN / "calls.jsonl", False)
    w3_calls = _load(W3_RUN / "calls.jsonl", False)
    cases = []
    for case in SENTINEL_CASES:
        w2, w3 = w2_calls[case], w3_calls[case]
        if w2["user_message"] != w3["user_message"] \
                or w2["request_sha256"] != w3["request_sha256"]:
            raise SystemExit(f"{case}: retained runs disagree on request "
                             "identity — refusing to build sentinels")
        cases.append({
            "case_id": case,
            "user_message": w2["user_message"],
            "request_sha256": w2["request_sha256"],
            **{f"worker_{worker}": {
                "completion": row["completion"],
                "finish_reason": row["finish_reason"],
                "generated_tokens": row["generated_tokens"],
                "generation_hit_token_cap":
                    row["generation_hit_token_cap"],
            } for worker, row in (("2", w2), ("3", w3))},
        })
    return {
        "sentinels": "stage0-retained-requests-v1",
        "selection_rule": "first-latent Code-node cases (code_atomic n1, "
                          "fork_join n2) x three renderers, from the "
                          "retained rev10 worker-2 and worker-3 runs",
        "cases": cases,
        "provenance": {
            str(W2_RUN / "calls.jsonl"): _sha(W2_RUN / "calls.jsonl"),
            str(W3_RUN / "calls.jsonl"): _sha(W3_RUN / "calls.jsonl"),
        },
    }


def main() -> int:
    for path, payload in ((CANARY_PATH, build_canary()),
                          (SENTINELS_PATH, build_sentinels())):
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=1, sort_keys=True)
            handle.write("\n")
        print(f"{path} (sha256 {_sha(path)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
