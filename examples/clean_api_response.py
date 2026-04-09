#!/usr/bin/env python3
"""Minimize an API response before passing it to an LLM.

Usage:
    python examples/clean_api_response.py
    echo '{"key": null, "data": [1,2]}' | python examples/clean_api_response.py --stdin
"""

from __future__ import annotations

import json
import sys

import ptk


def main() -> None:
    if "--stdin" in sys.argv:
        raw = sys.stdin.read()
        data = json.loads(raw)
    else:
        # demo payload
        data = {
            "data": {
                "users": [
                    {"id": 1, "name": "Alice", "email": "alice@co.com", "bio": None,
                     "avatar_url": "", "metadata": {}, "settings": {"theme": "dark", "notifications": None}},
                    {"id": 2, "name": "Bob", "email": "bob@co.com", "bio": "",
                     "avatar_url": None, "metadata": {}, "settings": {"theme": "light", "notifications": ""}},
                ],
            },
            "meta": {"page": 1, "total": 2, "next_cursor": None},
            "errors": None,
            "warnings": [],
        }

    s = ptk.stats(data)
    print(s["output"])
    print(f"\n--- {s['savings_pct']}% smaller ({s['original_tokens']} → {s['minimized_tokens']} tokens) ---",
          file=sys.stderr)


if __name__ == "__main__":
    main()
