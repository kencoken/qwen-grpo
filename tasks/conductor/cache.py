"""SQLite write-through completion cache — Stage 0B (spec §1.10, D11).

Rows store **raw model completions** keyed by the three-part key:
worker-visible fingerprint + endpoint fingerprint + canonical rendered
request bytes. Generation metadata (`finish_reason`, generated-token
count, `generation_hit_token_cap`) is stored with the text so truncation
telemetry survives cache hits. Executed `WorkerResult`s are never cached;
tools re-execute per call.

The full request bytes are persisted alongside their SHA-256 and compared
on every hit, so a hit can never silently serve a different request's
completion. Greedy decoding is a cache precondition (§1.10, enforced at
profile validation); a same-key store with a different completion is
therefore an infrastructure failure, not a shrug.
"""

from __future__ import annotations

import sqlite3
import hashlib
from dataclasses import dataclass
from pathlib import Path

from .types import InfrastructureError

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS completions (
    worker_visible_fp TEXT NOT NULL,
    endpoint_fp       TEXT NOT NULL,
    request_sha256    TEXT NOT NULL,
    request           BLOB NOT NULL,
    completion        TEXT NOT NULL,
    finish_reason     TEXT NOT NULL,
    generated_tokens  INTEGER NOT NULL,
    hit_token_cap     INTEGER NOT NULL,
    PRIMARY KEY (worker_visible_fp, endpoint_fp, request_sha256)
)"""


@dataclass(frozen=True)
class CacheRow:
    completion: str
    finish_reason: str
    generated_tokens: int
    generation_hit_token_cap: bool


class CompletionCache:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def lookup(self, worker_visible_fp: str, endpoint_fp: str,
               request: bytes) -> CacheRow | None:
        row = self._conn.execute(
            "SELECT request, completion, finish_reason, generated_tokens, "
            "hit_token_cap FROM completions WHERE worker_visible_fp = ? "
            "AND endpoint_fp = ? AND request_sha256 = ?",
            (worker_visible_fp, endpoint_fp, _sha(request))).fetchone()
        if row is None:
            return None
        stored_request, completion, finish_reason, tokens, hit_cap = row
        if bytes(stored_request) != request:
            raise InfrastructureError(
                "cache row request bytes do not match the queried request "
                "(SHA-256 collision or corrupted row)")
        return CacheRow(completion=completion, finish_reason=finish_reason,
                        generated_tokens=tokens,
                        generation_hit_token_cap=bool(hit_cap))

    def store(self, worker_visible_fp: str, endpoint_fp: str,
              request: bytes, generation) -> None:
        """Write-through: committed before the caller proceeds."""
        try:
            self._conn.execute(
                "INSERT INTO completions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (worker_visible_fp, endpoint_fp, _sha(request), request,
                 generation.completion, generation.finish_reason,
                 generation.generated_tokens,
                 int(generation.generation_hit_token_cap)))
            self._conn.commit()
        except sqlite3.IntegrityError:
            existing = self.lookup(worker_visible_fp, endpoint_fp, request)
            assert existing is not None
            if existing.completion != generation.completion:
                raise InfrastructureError(
                    "same cache key produced two different completions — "
                    "greedy-decoding precondition violated") from None

    def __len__(self) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM completions").fetchone()[0]

    def close(self) -> None:
        self._conn.close()


def _sha(request: bytes) -> str:
    return hashlib.sha256(request).hexdigest()
