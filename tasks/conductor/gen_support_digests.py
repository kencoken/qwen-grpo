"""Generate the frozen pre-P1 support-digest registry (94_s finding 6).

For every registered candidate: content hashes of the complete 300-case
P1 and 900-case full support — case identities, endpoints, user-message
hashes and rendered request digests — computed from the frozen
generator, prompt registry, request contracts and pinned tokenizers.
Committed BEFORE any P1 output exists; admission and reveal refuse a
plan or run that does not match.

Run:  uv run python -m tasks.conductor.gen_support_digests \
          --out tasks/conductor/fixtures/support_digests.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .candidates import CANDIDATES
from .worker_eval_probe import compute_support_digest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    digests = {}
    for cid in sorted(CANDIDATES):
        digests[cid] = compute_support_digest(cid)
        print(f"{cid}: p1 {digests[cid]['p1_identity_sha256'][:16]} "
              f"full {digests[cid]['full_identity_sha256'][:16]}")
    out = Path(args.out)
    with out.open("x", encoding="utf-8") as handle:
        json.dump(digests, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print(f"{len(digests)} candidates -> {out} (sha256 "
          f"{hashlib.sha256(out.read_bytes()).hexdigest()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
