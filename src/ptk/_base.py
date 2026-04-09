"""Base minimizer protocol + shared utilities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MinResult:
    """Immutable result from a minimizer pass."""

    output: str
    original_len: int
    minimized_len: int

    @property
    def savings_pct(self) -> float:
        if self.original_len == 0:
            return 0.0
        return round((1 - self.minimized_len / self.original_len) * 100, 1)


class Minimizer(ABC):
    """Base class all minimizers inherit from.

    Subclasses only need to implement `_minimize`.
    The public `run()` method handles result wrapping.
    """

    @abstractmethod
    def _minimize(self, obj: Any, *, aggressive: bool = False, **kw: Any) -> str:
        """Return the minimized string representation."""

    def run(self, obj: Any, *, aggressive: bool = False, **kw: Any) -> MinResult:
        original = _serialize(obj)
        try:
            minimized = self._minimize(obj, aggressive=aggressive, **kw)
        except (RecursionError, ValueError, TypeError, OverflowError):
            # graceful degradation: fall back to str() if minimizer can't handle the input
            minimized = str(obj)
        return MinResult(
            output=minimized,
            original_len=len(original),
            minimized_len=len(minimized),
        )


# ── shared helpers (used across minimizers) ─────────────────────────────


def _serialize(obj: Any) -> str:
    """Cheaply serialize an object to string for length measurement.

    Must NEVER raise — this is used for metrics, not output.
    Handles circular refs, non-serializable types, tuple keys, etc.
    """
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (dict, list, tuple)):
        import json

        try:
            return json.dumps(obj, separators=(",", ":"), default=str)
        except (ValueError, TypeError, OverflowError):
            # circular reference, non-string keys, or other json failure
            return str(obj)
    return str(obj)


def _is_nullish(v: object) -> bool:
    """Check if a value is 'empty' — None, "", [], or {}.

    Type-checks first to avoid hashing unhashable types.
    """
    if v is None:
        return True
    if isinstance(v, str):
        return v == ""
    if isinstance(v, list):
        return len(v) == 0
    if isinstance(v, dict):
        return len(v) == 0
    return False


def strip_nullish(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively strip None, empty string, empty list, empty dict values."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if _is_nullish(v):
            continue
        if isinstance(v, dict):
            cleaned = strip_nullish(v)
            if cleaned:
                out[k] = cleaned
        elif isinstance(v, list):
            cleaned_list = [
                strip_nullish(i) if isinstance(i, dict) else i for i in v if not _is_nullish(i)
            ]
            if cleaned_list:
                out[k] = cleaned_list
        else:
            out[k] = v
    return out


def dedup_lines(text: str, *, threshold: int = 2) -> str:
    """Collapse consecutive duplicate lines into `<line> (xN)`.

    Uses a single-pass algorithm — O(n) time, O(1) extra per group.
    """
    lines = text.split("\n")
    if len(lines) <= 1:
        return text

    result: list[str] = []
    prev = lines[0]
    count = 1

    for line in lines[1:]:
        if line == prev:
            count += 1
        else:
            _flush(result, prev, count, threshold)
            prev = line
            count = 1
    _flush(result, prev, count, threshold)
    return "\n".join(result)


def _flush(result: list[str], line: str, count: int, threshold: int) -> None:
    if count >= threshold:
        result.append(f"{line} (x{count})")
    else:
        result.extend([line] * count)
