"""ptk — Python Token Killer.

Minimize LLM tokens from Python objects in one call.

    import ptk
    ptk.minimize({"users": [{"name": "Alice", "age": 30}]})
    ptk(some_dict)  # shorthand

"""

from __future__ import annotations

from typing import Any

from ptk._base import MinResult, _serialize
from ptk._types import ContentType, detect
from ptk.minimizers import (
    CodeMinimizer,
    DictMinimizer,
    DiffMinimizer,
    ListMinimizer,
    LogMinimizer,
    TextMinimizer,
)

__version__ = "0.1.0"
__all__ = [
    "minimize",
    "stats",
    "detect_type",
    "MinResult",
    "ContentType",
    # minimizer classes (for direct use / subclassing)
    "DictMinimizer",
    "ListMinimizer",
    "CodeMinimizer",
    "LogMinimizer",
    "DiffMinimizer",
    "TextMinimizer",
]

# ── singleton minimizer instances (created once, reused) ────────────────

_ROUTER: dict[ContentType, Any] = {
    ContentType.DICT: DictMinimizer(),
    ContentType.LIST: ListMinimizer(),
    ContentType.CODE: CodeMinimizer(),
    ContentType.LOG: LogMinimizer(),
    ContentType.DIFF: DiffMinimizer(),
    ContentType.TEXT: TextMinimizer(),
}


# ── public API ──────────────────────────────────────────────────────────


def minimize(
    obj: Any,
    *,
    aggressive: bool = False,
    content_type: ContentType | str | None = None,
    **kw: Any,
) -> str:
    """Minimize tokens from any Python object.

    Args:
        obj: dict, list, str (code/log/diff/text), or anything with __str__.
        aggressive: Apply maximum compression (may lose some fidelity).
        content_type: Force a content type instead of auto-detecting.
            Accepts ContentType enum or string ("dict", "code", "log", etc.)
        **kw: Forwarded to the minimizer (format, mode, errors_only, etc.)

    Returns:
        Minimized string representation.
    """
    ct = _resolve_type(obj, content_type)
    result: str = _ROUTER[ct].run(obj, aggressive=aggressive, **kw).output
    return result


def stats(
    obj: Any,
    *,
    aggressive: bool = False,
    content_type: ContentType | str | None = None,
    **kw: Any,
) -> dict[str, Any]:
    """Return compression statistics without discarding the result.

    Returns:
        {
            "output": <minimized string>,
            "original_len": int,     # character count
            "minimized_len": int,    # character count
            "savings_pct": float,    # e.g. 73.2
            "content_type": str,     # e.g. "dict"
            "original_tokens": int | None,  # if tiktoken available
            "minimized_tokens": int | None,
        }
    """
    ct = _resolve_type(obj, content_type)
    result = _ROUTER[ct].run(obj, aggressive=aggressive, **kw)

    original_str = _serialize(obj)
    orig_tok, min_tok = _estimate_tokens(original_str, result.output)

    return {
        "output": result.output,
        "original_len": result.original_len,
        "minimized_len": result.minimized_len,
        "savings_pct": result.savings_pct,
        "content_type": ct.name.lower(),
        "original_tokens": orig_tok,
        "minimized_tokens": min_tok,
    }


def detect_type(obj: Any) -> str:
    """Return the auto-detected content type as a lowercase string."""
    return detect(obj).name.lower()


# ── callable module trick ───────────────────────────────────────────────
# Allows `import ptk; ptk(obj)` as shorthand for `ptk.minimize(obj)`.

import sys as _sys  # noqa: E402
import types as _types  # noqa: E402


class _CallableModule(_types.ModuleType):
    """Module that's also callable — `ptk(obj)` works."""

    def __call__(self, obj: Any, **kw: Any) -> str:
        return minimize(obj, **kw)

    def __repr__(self) -> str:
        return f"<module 'ptk' v{__version__}>"


# Swap this module's class so `ptk(...)` works
_self = _sys.modules[__name__]
_self.__class__ = _CallableModule


# ── private helpers ─────────────────────────────────────────────────────


def _resolve_type(obj: Any, hint: ContentType | str | None) -> ContentType:
    if hint is None:
        return detect(obj)
    if isinstance(hint, ContentType):
        return hint
    # string lookup
    return ContentType[hint.upper()]


def _estimate_tokens(original: str, minimized: str) -> tuple[int | None, int | None]:
    """Try tiktoken for accurate counts, fall back to len//4 heuristic."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(original)), len(enc.encode(minimized))
    except ImportError:
        # fast heuristic: ~4 chars per token for English
        return len(original) // 4, len(minimized) // 4
