"""List/array minimizer — dedup, sampling, schema-once tabular."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from ptk._base import Minimizer, strip_nullish


class ListMinimizer(Minimizer):
    """Compress lists via dedup, sampling, and tabular encoding.

    Strategies:
    1. Strip nullish items
    2. Deduplicate exact-match items with counts
    3. For uniform list-of-dicts: schema-once tabular output
    4. For large arrays: statistical sampling (aggressive)
    """

    # max items before sampling kicks in (aggressive mode)
    SAMPLE_THRESHOLD = 50

    def _minimize(
        self, obj: Any, *, aggressive: bool = False, strip_nulls: bool = True, **kw: Any
    ) -> str:
        if not isinstance(obj, (list, tuple)):
            return json.dumps(obj, separators=(",", ":"), default=str)

        if strip_nulls:
            items = [strip_nullish(i) if isinstance(i, dict) else i for i in obj if i is not None]
        else:
            items = list(obj)

        if not items:
            return "[]"

        # ── uniform list-of-dicts → tabular ─────────────────────────
        if isinstance(items[0], dict) and all(isinstance(i, dict) for i in items):
            if aggressive and len(items) > self.SAMPLE_THRESHOLD:
                items = _sample(items, self.SAMPLE_THRESHOLD)
            return _tabular(items)

        # ── primitive list → dedup with counts ──────────────────────
        if aggressive and len(items) > self.SAMPLE_THRESHOLD:
            items = items[: self.SAMPLE_THRESHOLD]

        return _dedup_list(items)


def _tabular(rows: list[dict[str, Any]]) -> str:
    """Schema-once tabular: declare fields in header, one CSV-ish row per item."""
    fields: list[str] = list(dict.fromkeys(f for row in rows for f in row))
    header = f"[{len(rows)}]{{{','.join(fields)}}}:"
    body = "\n".join(",".join(str(row.get(f, "")) for f in fields) for row in rows)
    return f"{header}\n{body}"


def _dedup_list(items: list[Any]) -> str:
    """Collapse duplicate primitives: [a, a, a, b] → a (x3)\nb"""
    # json-serialize each item for stable hashing
    serialized = [json.dumps(i, separators=(",", ":"), default=str) for i in items]
    counts = Counter(serialized)

    # preserve first-seen order
    seen: set[str] = set()
    lines: list[str] = []
    for s in serialized:
        if s in seen:
            continue
        seen.add(s)
        c = counts[s]
        # strip quotes from simple strings for readability
        display = s.strip('"') if s.startswith('"') and s.endswith('"') else s
        lines.append(f"{display} (x{c})" if c > 1 else display)

    return "\n".join(lines)


def _sample(items: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """Deterministic even-spaced sampling — keeps first and last."""
    if n <= 0:
        return []
    if len(items) <= n:
        return items
    if n == 1:
        return [items[0]]
    step = (len(items) - 1) / (n - 1)
    indices = {round(i * step) for i in range(n)}
    sampled = [items[i] for i in sorted(indices)]
    return sampled
