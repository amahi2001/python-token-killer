"""Dict/JSON minimizer — biggest token wins live here."""

from __future__ import annotations

import json
from typing import Any

from ptk._base import Minimizer, strip_nullish


class DictMinimizer(Minimizer):
    """Compress dicts via null-stripping, key shortening, and compact serialization.

    Strategies applied in order:
    1. Strip nullish values (None, "", [], {})
    2. Flatten single-child nesting  (aggressive)
    3. Shorten keys to abbreviated forms (aggressive)
    4. Serialize with minimal separators

    The `format` kwarg controls output encoding:
      - "json"    (default) — compact json.dumps
      - "kv"      — key:value lines (great for flat dicts)
      - "tabular" — header-once tabular format (auto for list-of-dicts values)
    """

    def _minimize(self, obj: Any, *, aggressive: bool = False, **kw: Any) -> str:
        if not isinstance(obj, dict):
            obj = {"_": obj}

        d = strip_nullish(obj)

        if aggressive:
            d = _flatten_single_children(d)
            d = _shorten_dotted_keys(d)
            d = _shorten_keys(d)

        fmt = kw.get("format", "json")
        if fmt == "kv":
            return _to_kv(d)
        if fmt == "tabular":
            return _to_tabular(d)
        return json.dumps(d, separators=(",", ":"), default=str)


# ── internal helpers ────────────────────────────────────────────────────

def _flatten_single_children(d: dict[str, Any], _depth: int = 0) -> dict[str, Any]:
    """Collapse {"a": {"b": val}} → {"a.b": val} up to 4 levels."""
    if _depth > 4:
        return d
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict) and len(v) == 1:
            inner_k, inner_v = next(iter(v.items()))
            flattened = _flatten_single_children(
                {f"{k}.{inner_k}": inner_v}, _depth + 1
            )
            out.update(flattened)
        else:
            out[k] = v
    return out


# common verbose key → short form (extensible)
_KEY_MAP: dict[str, str] = {
    "description": "desc",
    "message": "msg",
    "timestamp": "ts",
    "created_at": "ts",
    "updated_at": "upd",
    "configuration": "cfg",
    "config": "cfg",
    "environment": "env",
    "database": "db",
    "information": "info",
    "response": "resp",
    "request": "req",
    "function": "fn",
    "parameters": "params",
    "arguments": "args",
    "exception": "exc",
    "traceback": "tb",
    "status_code": "code",
    "content_type": "ctype",
    "application": "app",
    "transaction": "txn",
    "identifier": "id",
    "metadata": "meta",
    "properties": "props",
    "connection": "conn",
    "password": "pw",
    "username": "user",
    "directory": "dir",
    "reference": "ref",
    "implementation": "impl",
    "notifications": "notifs",
    "repository": "repo",
}


def _shorten_keys(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively shorten known verbose keys."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        short = _KEY_MAP.get(k, k)
        if isinstance(v, dict):
            out[short] = _shorten_keys(v)
        elif isinstance(v, list):
            out[short] = [_shorten_keys(i) if isinstance(i, dict) else i for i in v]
        else:
            out[short] = v
    return out


def _shorten_dotted_keys(d: dict[str, Any]) -> dict[str, Any]:
    """Shorten individual segments of dotted keys (from flattening)."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if "." in k:
            parts = [_KEY_MAP.get(p, p) for p in k.split(".")]
            out[".".join(parts)] = v
        else:
            out[k] = v
    return out


def _to_kv(d: dict[str, Any], _prefix: str = "") -> str:
    """Flat key:value format — one line per leaf."""
    lines: list[str] = []
    for k, v in d.items():
        full = f"{_prefix}{k}"
        if isinstance(v, dict):
            lines.append(_to_kv(v, f"{full}."))
        else:
            lines.append(f"{full}:{v}")
    return "\n".join(lines)


def _to_tabular(d: dict[str, Any]) -> str:
    """Render any list-of-dicts values as header-once tabular rows.

    Non-list values render as kv pairs above the table.
    """
    kv_lines: list[str] = []
    table_lines: list[str] = []

    for k, v in d.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            # collect union of all keys (preserving order)
            fields: list[str] = list(dict.fromkeys(f for row in v for f in row))
            table_lines.append(f"{k}[{len(v)}]{{{','.join(fields)}}}:")
            for row in v:
                vals = (str(row.get(f, "")) for f in fields)
                table_lines.append(f"  {','.join(vals)}")
        else:
            kv_lines.append(f"{k}:{v}")

    return "\n".join(kv_lines + table_lines)
