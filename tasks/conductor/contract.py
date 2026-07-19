"""Artifact envelope and WorkerResult construction — spec §1.6, §1.7, §1.11.

The envelope contract's frozen precedence (cases 1–6), the flag truth table,
and the direct-arm answer-line protocol.
"""

from __future__ import annotations

from .tools import Binding, ToolRejection, execute_artifact
from .types import (
    SEMANTIC_REJECTION_CODES, SYNTAX_REJECTION_CODES, InfrastructureError,
    WorkerResult, classify_integer_text,
)

OPEN_TAG, CLOSE_TAG = "<artifact>", "</artifact>"


def parse_envelope(completion: str) -> str:
    """§1.6 frozen precedence over exact byte strings; returns the trimmed
    content between the tags. Text before/after the envelope is ignored."""
    if "<value>" in completion or "</value>" in completion:
        raise ToolRejection("E_UNEXPECTED_TAG")
    n_open = completion.count(OPEN_TAG)
    n_close = completion.count(CLOSE_TAG)
    if n_open == 0:
        raise ToolRejection("E_NO_ARTIFACT")
    if n_open >= 2 or n_close >= 2:
        raise ToolRejection("E_MULTI_ARTIFACT")
    if n_close == 0:
        raise ToolRejection("E_UNCLOSED_ARTIFACT")
    open_at = completion.index(OPEN_TAG)
    close_at = completion.index(CLOSE_TAG)
    if close_at < open_at:
        raise ToolRejection("E_PARSE")
    return completion[open_at + len(OPEN_TAG):close_at].strip()


# --- §1.7 truth-table constructors ------------------------------------------

def success_result(value: int) -> WorkerResult:
    return WorkerResult(status="success", value=value, rejection_code=None,
                        artifact_valid=True, tool_executed=True,
                        synthetic=False)


def typed_failure_result(code: str) -> WorkerResult:
    """Envelope + grammar/limit failures never executed a tool; the
    remaining codes are semantic rejections from an executed tool."""
    semantic = code in SEMANTIC_REJECTION_CODES
    if not semantic and code not in SYNTAX_REJECTION_CODES:
        raise InfrastructureError(f"unknown rejection code {code!r}")
    return WorkerResult(status="typed_failure", value=None,
                        rejection_code=code, artifact_valid=semantic,
                        tool_executed=semantic, synthetic=False)


def dependency_blocked_result() -> WorkerResult:
    return WorkerResult(status="dependency_blocked", value=None,
                        rejection_code=None, artifact_valid=False,
                        tool_executed=False, synthetic=False)


def pseudo_result(value: int | None, code: str | None = None) -> WorkerResult:
    """§1.7 pseudo-worker row: synthetic=true, never artifact/tool flags."""
    if (value is None) == (code is None):
        raise InfrastructureError("pseudo_result takes value xor code")
    status = "success" if value is not None else "typed_failure"
    return WorkerResult(status=status, value=value, rejection_code=code,
                        artifact_valid=False, tool_executed=False,
                        synthetic=True)


def run_worker_output(endpoint: int, completion: str,
                      binding: Binding) -> WorkerResult:
    """Envelope → grammar → tool for one raw completion (§1.6/§1.7)."""
    try:
        content = parse_envelope(completion)
        value = execute_artifact(endpoint, content, binding)
    except ToolRejection as rej:
        return typed_failure_result(rej.code)
    return success_result(value)


# --- §1.11: direct-arm answer-line protocol ---------------------------------

def parse_answer_line(completion: str) -> int | None:
    """Last non-empty line, trimmed, as a canonical integer; else None
    (scored wrong, not a typed rejection — direct arms have no artifact)."""
    for line in reversed(completion.split("\n")):
        text = line.strip()
        if text:
            return int(text) if classify_integer_text(text) is None else None
    return None
