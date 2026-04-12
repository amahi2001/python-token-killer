"""Log minimizer — dedup repeated lines, error-only filtering."""

from __future__ import annotations

import re
from typing import Any

from ptk._base import Minimizer, dedup_lines

# precompiled
_LOG_LEVEL = re.compile(
    r"\b(ERROR|WARN(?:ING)?|CRITICAL|FATAL|EXCEPTION|SEVERE|PANIC)\b",
    re.IGNORECASE,
)
_TIMESTAMP = re.compile(
    r"^\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}[.,]?\d*\s*(?:[+-]\d{2}:?\d{2}|Z)?\s*",
    re.MULTILINE,
)
# stack trace markers — lines matching these are always preserved
_STACKTRACE_RE = re.compile(
    r'^\s*(Traceback \(most recent|File "|\s+raise |'
    r"\w+Error:|\w+Exception:|\w+Warning:|at \S+\.\S+\()",
    re.MULTILINE,
)
# test-runner pass markers — never kept as context in errors_only mode
_PASS_MARKERS: frozenset[str] = frozenset(
    {
        "PASSED",
        " PASS",
        "--- PASS",
        "... ok",
        " ok",
        "test result: ok",
        "✓",
    }
)


class LogMinimizer(Minimizer):
    """Compress log output via deduplication and error filtering.

    Strategies:
    1. Strip timestamps (aggressive) — timestamps are rarely useful to an LLM
    2. Collapse consecutive duplicate lines with counts
    3. Keep only error/warning lines (aggressive)
    """

    def _minimize(self, obj: Any, *, aggressive: bool = False, **kw: Any) -> str:
        text = obj if isinstance(obj, str) else str(obj)

        # bail early on blank input
        if not text.strip():
            return ""

        if aggressive:
            text = _TIMESTAMP.sub("", text)

        text = dedup_lines(text)

        if aggressive or kw.get("errors_only", False):
            text = _errors_only(text)

        return text.strip()


def _errors_only(text: str) -> str:
    """Keep error/warning lines, stack traces, 'failed' keyword lines, + context.

    Pass-marker lines (PASSED, --- PASS, ... ok, etc.) are never kept even
    as context around errors — they are pure noise in an error report.
    """
    lines = text.split("\n")
    keep: set[int] = set()
    for i, line in enumerate(lines):
        ll = line.lower()
        is_important = (
            _LOG_LEVEL.search(line)
            or _STACKTRACE_RE.match(line)
            or "failed" in ll
            or "fail:" in ll  # go test: --- FAIL: TestName
            or " fail " in ll  # standalone FAIL line
            or "error" in ll  # build errors, compiler output
            or "panicked" in ll  # rust panic
            or "assertion" in ll  # assertion errors
        )
        if is_important:
            # keep the important line + 1 line of context before/after,
            # but exclude pure pass-marker lines from the context window
            for j in range(max(0, i - 1), min(len(lines), i + 2)):
                if not any(marker in lines[j] for marker in _PASS_MARKERS):
                    keep.add(j)
    if not keep:
        return text  # no errors found — return deduped version
    return "\n".join(lines[i] for i in sorted(keep))
