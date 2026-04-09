"""Code minimizer — comment stripping, whitespace normalization, signature extraction."""

from __future__ import annotations

import re
from typing import Any

from ptk._base import Minimizer

# ── precompiled regexes (compiled once at import time) ──────────────────

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
# Match strings first (to skip), then comments. Group 1 = string (keep), Group 2 = comment (strip).
_STRING_OR_COMMENT_C = re.compile(
    r"""("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')"""  # group 1: quoted string
    r"|"  # OR
    r"(//.*$)",  # group 2: C-style inline comment
    re.MULTILINE,
)
_STRING_OR_COMMENT_PY = re.compile(
    r"""("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')"""  # group 1: quoted string
    r"|"  # OR
    r"(#.*$)",  # group 2: Python inline comment
    re.MULTILINE,
)
_DOCSTRING = re.compile(r"(\"\"\"[\s\S]*?\"\"\"|\'\'\'[\s\S]*?\'\'\')")
_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_WS = re.compile(r"[ \t]+$", re.MULTILINE)

# pragma/directive comments that must be preserved
_PRAGMA_KEYWORDS: frozenset[str] = frozenset(
    {
        "noqa",
        "type: ignore",
        "type:ignore",
        "TODO",
        "FIXME",
        "HACK",
        "XXX",
        "pragma",
        "pylint:",
        "fmt:",
        "eslint-disable",
        "eslint-enable",
        "@ts-ignore",
        "@ts-expect-error",
        "noinspection",
    }
)

# signature patterns for common languages
_PY_SIG = re.compile(
    r"^([ \t]*(?:async\s+)?(?:def|class)\s+\w+.*?:)\s*$",
    re.MULTILINE,
)
_JS_SIG = re.compile(
    r"^([ \t]*(?:export\s+)?(?:async\s+)?(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>)[^{]*)",
    re.MULTILINE,
)
_RUST_SIG = re.compile(
    r"^([ \t]*(?:pub\s+)?(?:async\s+)?fn\s+\w+[^{]*)",
    re.MULTILINE,
)
_GO_SIG = re.compile(
    r"^([ \t]*func\s+(?:\([^)]*\)\s+)?\w+[^{]*)",
    re.MULTILINE,
)

_SIG_PATTERNS = [_PY_SIG, _JS_SIG, _RUST_SIG, _GO_SIG]


class CodeMinimizer(Minimizer):
    """Compress code by stripping comments, normalizing whitespace, extracting signatures.

    Modes (via `mode` kwarg):
      - "clean"      (default) — strip comments + normalize whitespace
      - "signatures"  — extract function/class signatures only (huge savings)
    """

    def _minimize(self, obj: Any, *, aggressive: bool = False, **kw: Any) -> str:
        code = obj if isinstance(obj, str) else str(obj)
        mode = kw.get("mode", "signatures" if aggressive else "clean")

        if mode == "signatures":
            return _extract_signatures(code)
        return _clean(code)


def _has_pragma(comment: str) -> bool:
    """Check if a comment contains a pragma/directive that must be preserved."""
    return any(kw in comment for kw in _PRAGMA_KEYWORDS)


def _strip_string_or_comment_c(m: re.Match[str]) -> str:
    """Handle string-or-comment match: keep strings, strip comments (unless pragma)."""
    if m.group(1):  # it's a quoted string — keep it
        return m.group(1)
    comment = m.group(2)  # it's a // comment
    return comment if _has_pragma(comment) else ""


def _strip_string_or_comment_py(m: re.Match[str]) -> str:
    """Handle string-or-comment match: keep strings, strip comments (unless pragma)."""
    if m.group(1):  # it's a quoted string — keep it
        return m.group(1)
    comment = m.group(2)  # it's a # comment
    return comment if _has_pragma(comment) else ""


def _strip_block_comment_if_safe(m: re.Match[str]) -> str:
    """Remove a block comment unless it contains a pragma."""
    return m.group(0) if _has_pragma(m.group(0)) else ""


def _collapse_docstring(m: re.Match[str]) -> str:
    """Collapse a multi-line docstring to its first line only."""
    full = m.group(0)
    # detect the quote style
    quote = full[:3]
    inner = full[3:-3].strip()
    lines = inner.split("\n")
    first_line = lines[0].strip() if lines else ""
    if not first_line:
        return ""
    # single-line docstrings or summaries — keep as one-liner
    return f"{quote}{first_line}{quote}"


def _clean(code: str) -> str:
    """Strip comments and normalize whitespace — language-agnostic.

    Preserves pragma comments (noqa, type: ignore, TODO, eslint-disable, etc.)
    and collapses multi-line docstrings to first line.
    """
    out = _BLOCK_COMMENT.sub(_strip_block_comment_if_safe, code)
    # strip docstrings BEFORE inline comments so triple-quotes are handled first
    out = _DOCSTRING.sub(_collapse_docstring, out)
    # use string-aware patterns to avoid stripping // or # inside string literals
    out = _STRING_OR_COMMENT_C.sub(_strip_string_or_comment_c, out)
    out = _STRING_OR_COMMENT_PY.sub(_strip_string_or_comment_py, out)
    out = _TRAILING_WS.sub("", out)
    out = _BLANK_LINES.sub("\n\n", out)
    return out.strip()


def _extract_signatures(code: str) -> str:
    """Pull out only function/class signatures — works across Python, JS, Rust, Go."""
    sigs: list[str] = []
    for pattern in _SIG_PATTERNS:
        sigs.extend(m.group(1).strip() for m in pattern.finditer(code))

    if not sigs:
        # fallback: return cleaned code if no signatures found
        return _clean(code)

    return "\n".join(sigs)
