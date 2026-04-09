"""Diff minimizer — fold unchanged context, keep only meaningful changes."""

from __future__ import annotations

from typing import Any

from ptk._base import Minimizer


class DiffMinimizer(Minimizer):
    """Compress git diffs by folding unchanged context lines.

    Strategies:
    1. Keep hunk headers (@@) and file headers (---, +++)
    2. Keep added (+) and removed (-) lines
    3. Collapse context (space-prefixed) lines to `... N lines ...`
    4. Aggressive: strip file mode changes, index lines, trailing whitespace diffs
    """

    # max unchanged context lines to keep around changes
    CONTEXT_LINES = 2

    def _minimize(self, obj: Any, *, aggressive: bool = False, **kw: Any) -> str:
        text = obj if isinstance(obj, str) else str(obj)
        ctx = kw.get("context_lines", 0 if aggressive else self.CONTEXT_LINES)
        return _fold_diff(text, context=ctx, aggressive=aggressive)


def _fold_diff(text: str, *, context: int, aggressive: bool) -> str:
    lines = text.split("\n")
    result: list[str] = []
    context_buf: list[str] = []

    for line in lines:
        # always skip noise in aggressive mode
        if aggressive and _is_noise(line):
            continue

        if _is_significant(line):
            # flush context buffer — keep only last `context` lines
            if context_buf:
                _flush_context(result, context_buf, keep=context)
                context_buf.clear()
            result.append(line)
        else:
            context_buf.append(line)

    # flush remaining context
    if context_buf:
        _flush_context(result, context_buf, keep=context)

    return "\n".join(result)


def _is_significant(line: str) -> bool:
    """Lines that carry meaningful diff information."""
    return (
        line.startswith(("+", "-", "@@", "diff ")) and not line.startswith(("+++", "---"))
    ) or line.startswith(("+++", "---"))


def _is_noise(line: str) -> bool:
    """Lines that are almost never useful to an LLM."""
    return (
        line.startswith(("index ", "old mode", "new mode", "similarity"))
        or line.startswith("rename ")
        or (line.startswith("Binary files") and "differ" in line)
    )


def _flush_context(result: list[str], buf: list[str], *, keep: int) -> None:
    """Collapse a block of context lines, keeping at most `keep` on each end."""
    if len(buf) <= keep * 2 + 1:
        result.extend(buf)
        return

    if keep > 0:
        result.extend(buf[:keep])
    folded = len(buf) - keep * 2
    if folded > 0:
        result.append(f" ... {folded} lines ...")
    if keep > 0:
        result.extend(buf[-keep:])
