#!/usr/bin/env python3
"""Claude Code skill helper — minimize file contents before injection.

Place this in your Claude Code project's skills directory or call it
from a CLAUDE.md instruction to compress large files before they
enter the context window.

Usage in CLAUDE.md:
    When reading large JSON files, pipe through ptk first:
    ```
    python examples/claude_code_skill.py data/large_response.json
    ```

Usage as a standalone pipe:
    cat large_file.json | python examples/claude_code_skill.py --stdin
    cat server.log | python examples/claude_code_skill.py --stdin --type log --aggressive
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import ptk


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ptk — minimize tokens from files")
    parser.add_argument("file", nargs="?", help="File to minimize")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--type", choices=["dict", "list", "code", "log", "diff", "text"],
                        default=None, help="Force content type (default: auto-detect)")
    parser.add_argument("--aggressive", "-a", action="store_true", help="Max compression")
    parser.add_argument("--stats", "-s", action="store_true", help="Print stats to stderr")
    args = parser.parse_args()

    # read input
    if args.stdin:
        raw = sys.stdin.read()
    elif args.file:
        raw = Path(args.file).read_text()
    else:
        parser.print_help()
        sys.exit(1)

    # try to parse as JSON first
    import contextlib

    obj: object = raw
    with contextlib.suppress(json.JSONDecodeError, ValueError):
        obj = json.loads(raw)

    # minimize
    if args.stats:
        s = ptk.stats(obj, aggressive=args.aggressive, content_type=args.type)
        print(s["output"])
        print(
            f"[ptk] {s['content_type']}: {s['original_tokens']} → {s['minimized_tokens']} tokens "
            f"({s['savings_pct']}% saved)",
            file=sys.stderr,
        )
    else:
        print(ptk.minimize(obj, aggressive=args.aggressive, content_type=args.type))


if __name__ == "__main__":
    main()
