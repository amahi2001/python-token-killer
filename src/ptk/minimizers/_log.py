"""Log minimizer — dedup repeated lines, error-only filtering."""

from __future__ import annotations

import re
from typing import Any

from ptk._base import Minimizer, dedup_lines

# precompiled
_LOG_LEVEL = re.compile(
    r'\b(ERROR|WARN(?:ING)?|CRITICAL|FATAL|EXCEPTION|SEVERE|PANIC)\b',
    re.IGNORECASE,
)
_TIMESTAMP = re.compile(
    r'^\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}[.,]?\d*\s*(?:[+-]\d{2}:?\d{2}|Z)?\s*',
    re.MULTILINE,
)
# stack trace markers — lines matching these are always preserved
_STACKTRACE_RE = re.compile(
    r'^\s*(Traceback \(most recent|File "|\s+raise |'
    r'\w+Error:|\w+Exception:|\w+Warning:|at \S+\.\S+\()',
    re.MULTILINE,
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

        if aggressive:
            text = _TIMESTAMP.sub("", text)

        text = dedup_lines(text)

        if aggressive or kw.get("errors_only", False):
            text = _errors_only(text)

        return text.strip()


def _errors_only(text: str) -> str:
    """Keep error/warning lines, stack traces, 'failed' keyword lines, + context."""
    lines = text.split("\n")
    keep: set[int] = set()
    for i, line in enumerate(lines):
        is_important = (
            _LOG_LEVEL.search(line)
            or _STACKTRACE_RE.match(line)
            or "failed" in line.lower()
        )
        if is_important:
            # keep the important line + 1 line of context before/after
            keep.update(range(max(0, i - 1), min(len(lines), i + 2)))
    if not keep:
        return text  # no errors found — return deduped version
    return "\n".join(lines[i] for i in sorted(keep))
