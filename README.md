# ptk — Python Token Killer

[![CI](https://github.com/amahi2001/python-token-killer/actions/workflows/ci.yml/badge.svg)](https://github.com/amahi2001/python-token-killer/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Minimize LLM tokens from Python objects in one call. Zero required dependencies. 322 tests.

Inspired by [RTK (Rust Token Killer)](https://github.com/rtk-ai/rtk) — but designed as a Python library for programmatic use, not a CLI proxy.

```python
import ptk

ptk.minimize({"users": [{"name": "Alice", "bio": None, "age": 30}]})
# → '{"users":[{"name":"Alice","age":30}]}'

ptk(my_dict)          # callable shorthand
ptk(my_dict, aggressive=True)  # max compression
```

## Install

```bash
pip install python-token-killer
```

Optional: `pip install python-token-killer[tiktoken]` for exact token counting.

## Benchmarks

Real token counts via tiktoken (`cl100k_base`, same tokenizer as GPT-4 / Claude):

```
Benchmark                      Original  Default   Saved    Aggressive  Saved
API response (JSON)                1450      792   45.4%         782   46.1%
Python module (code)               2734     2113   22.7%         309   88.7%
Server log (58 lines)              1389     1388    0.1%         231   83.4%
50 user records (list)             2774      922   66.8%         922   66.8%
Verbose paragraph (text)            101       96    5.0%          74   26.7%
                                 ─────────────────────────────────────────────
TOTAL                             11182     7424   33.6%        2627   76.5%
```

Run yourself: `python benchmarks/bench.py`

## What It Does

ptk auto-detects your input type and routes to the right minimizer:

| Input Type | Strategy | Typical Savings |
|---|---|---|
| `dict` | Null stripping, key shortening, flattening, compact JSON | 30–60% |
| `list` | Dedup, schema-once tabular, sampling | 40–70% |
| Code `str` | Comment stripping (pragma-preserving), docstring collapse, signature extraction | 25–80% |
| Logs `str` | Line dedup with counts, error-only filtering, stack trace preservation | 60–90% |
| Diffs `str` | Context folding, noise stripping | 50–75% |
| Text `str` | Word/phrase abbreviation, filler removal, stopword removal | 10–30% |

## API

### `ptk.minimize(obj, *, aggressive=False, content_type=None, **kw) → str`

Main entry point. Auto-detects type, applies the right strategy, returns a minimized string.

```python
# auto-detect
ptk.minimize({"key": "value"})

# force content type
ptk.minimize(some_string, content_type="code")
ptk.minimize(some_string, content_type="log")

# dict output formats
ptk.minimize(data, format="kv")       # key:value lines
ptk.minimize(data, format="tabular")  # header-once tabular

# code: signatures only (huge savings)
ptk.minimize(code, content_type="code", mode="signatures")

# logs: errors only
ptk.minimize(logs, content_type="log", errors_only=True)
```

### `ptk.stats(obj, **kw) → dict`

Same compression, but returns statistics:

```python
ptk.stats(big_api_response)
# {
#   "output": "...",
#   "original_len": 4200,
#   "minimized_len": 1800,
#   "savings_pct": 57.1,
#   "content_type": "dict",
#   "original_tokens": 1050,
#   "minimized_tokens": 450,
# }
```

### `ptk(obj)` — callable module

```python
import ptk
ptk(some_dict)  # equivalent to ptk.minimize(some_dict)
```

## Features by Minimizer

### DictMinimizer
- Strips `None`, `""`, `[]`, `{}` recursively (preserves `0` and `False`)
- Key shortening: `description` → `desc`, `timestamp` → `ts`, `configuration` → `cfg`, etc.
- Single-child flattening: `{"a": {"b": val}}` → `{"a.b": val}` (aggressive)
- Output formats: compact JSON (default), key-value lines, header-once tabular

### ListMinimizer
- Uniform list-of-dicts → schema-once tabular: declare fields once, one row per item
- Primitive dedup with counts: `["a", "a", "a", "b"]` → `a (x3)\nb`
- Large array sampling with first/last preservation (aggressive, threshold: 50)

### CodeMinimizer
- Strips comments while **preserving pragmas**: `# noqa`, `# type: ignore`, `# TODO`, `# FIXME`, `// eslint-disable`
- Collapses multi-line docstrings to first line only
- Signature extraction mode: pulls `def`, `class`, `fn`, `func` across Python, JS, Rust, Go
- Normalizes blank lines and trailing whitespace

### LogMinimizer
- Consecutive duplicate line collapse with `(xN)` counts
- Error-only filtering preserving: ERROR, WARN, FATAL, CRITICAL, stack traces, "failed" keyword
- Timestamp stripping (aggressive)

### DiffMinimizer
- Folds unchanged context lines to `... N lines ...`
- Strips noise: `index`, `old mode`, `new mode`, `similarity`, `Binary files` (aggressive)
- Preserves: `+`/`-` lines, `@@` hunks, `---`/`+++` headers, `\ No newline at end of file`

### TextMinimizer
- Word abbreviation: `implementation` → `impl`, `configuration` → `config`, `production` → `prod`, etc.
- Phrase abbreviation: `in order to` → `to`, `due to the fact that` → `because`, etc.
- Filler removal: strips `Furthermore,`, `Moreover,`, `In addition,`, `Additionally,`
- Stopword removal (aggressive): strips `the`, `a`, `is`, `very`, etc.

## Use Cases

### Agent Frameworks (LangGraph / LangChain)

```python
import ptk

def compress_context(state):
    state["context"] = ptk.minimize(state["context"], aggressive=True)
    return state
```

### Claude Code Skills

```python
#!/usr/bin/env python3
import ptk, json, sys
data = json.load(open(sys.argv[1]))
print(ptk(data))
```

### API Response Cleanup

```python
response = requests.get("https://api.example.com/users").json()
clean = ptk.minimize(response)  # strip nulls, compact JSON
```

## Comparison with Alternatives

| Tool | Approach | Best For |
|---|---|---|
| **ptk** | Type-detecting Python library, one-liner API | Programmatic use in scripts, agents, frameworks |
| [RTK](https://github.com/rtk-ai/rtk) | Rust CLI proxy for shell commands | Coding agents (Claude Code, OpenCode) |
| [claw-compactor](https://github.com/open-compress/claw-compactor) | 14-stage pipeline, AST-aware | Heavy-duty workspace compression |
| [toons](https://pypi.org/project/toons/) | TOON serialization format | Tabular data in LLM prompts |
| [LLMLingua](https://github.com/microsoft/LLMLingua) | Neural prompt compression | Natural language, requires GPU |

## Design Principles

- **Zero deps** — stdlib only. tiktoken is optional for exact counts.
- **Builtins-first** — `frozenset` for O(1) lookups, precompiled regexes, `slots=True` frozen dataclasses.
- **DRY** — shared `strip_nullish()`, `dedup_lines()` reused across minimizers.
- **Type-routed** — O(1) detection for dicts/lists, first-2KB heuristic for strings.
- **Safe by default** — aggressive mode is opt-in. Default never destroys meaning.

## Development

```bash
git clone https://github.com/amahi2001/python-token-killer.git
cd ptk
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## License

MIT
