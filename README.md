<p align="center">
  <img src="assets/mascot.png" alt="ptk" width="200"/>
</p>

<p align="center">
  <strong>ptk — Python Token Killer</strong><br/>
  <strong>Minimize LLM tokens from Python objects in one call</strong><br/>
  Zero dependencies • Auto type detection • 361 tests
</p>

<table align="center">
  <tr>
    <td align="left" valign="middle">
      <a href="https://github.com/amahi2001/python-token-killer/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/amahi2001/python-token-killer/ci.yml?branch=main&style=flat-square&label=CI" alt="CI"/></a><br/>
      <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"/><br/>
      <img src="https://img.shields.io/badge/mypy-strict-blue?style=flat-square" alt="mypy strict"/><br/>
      <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License"/></a>
    </td>
  </tr>
</table>

---

## The Problem

Every time your app calls an LLM, you're paying for tokens like these:

```json
{
  "user": {
    "id": 8821,
    "name": "Alice Chen",
    "email": "alice@example.com",
    "bio": null,
    "avatar_url": null,
    "phone": null,
    "address": null,
    "metadata": {},
    "preferences": {
      "theme": "dark",
      "notifications": null,
      "newsletter": null
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-06-20T14:22:00Z",
    "last_login": null,
    "is_verified": true,
    "is_active": true
  },
  "errors": null,
  "warnings": []
}
```

One call to `ptk` later:

```python
import ptk
ptk(response)
```

```json
{"user":{"id":8821,"name":"Alice Chen","email":"alice@example.com","preferences":{"theme":"dark"},"created_at":"2024-01-15T10:30:00Z","updated_at":"2024-06-20T14:22:00Z","is_verified":true,"is_active":true}}
```

**52% fewer tokens. Zero information lost. Zero config.**

```bash
pip install python-token-killer
# or
uv add python-token-killer
```

---

## Benchmarks

Real token counts via tiktoken (`cl100k_base` — same tokenizer as GPT-4 and Claude):

```
Input                          Tokens (before)   Tokens (after)   Saved
─────────────────────────────────────────────────────────────────────────
API response (JSON)                    1,450              792      45%
Python module (code → sigs)            2,734              309      89%
CI log (58 lines, errors only)         1,389              231      83%
50 user records (tabular)              2,774              922      67%
Verbose prose (text)                     101               74      27%
─────────────────────────────────────────────────────────────────────────
Total                                 11,182            2,627      76%
```

At GPT-4o pricing ($2.50/1M input tokens), that 76% reduction on **10k tokens/day** saves ~**$6/month per user**. At scale, it compounds.

Run yourself: `python benchmarks/bench.py`

---

## How It Works

`ptk` detects your input type and routes to the right compression strategy automatically:

| Input | What happens | Saves |
|---|---|---|
| `dict` / `list` | Strips `null`, `""`, `[]`, `{}` recursively. Tabular encoding for uniform arrays. | 40–70% |
| Code | Strips comments (preserving `# noqa`, `# type: ignore`, `TODO`). Collapses docstrings. Extracts signatures. | 25–89% |
| Logs | Collapses duplicate lines with counts. Filters to errors + stack traces only. | 60–90% |
| Diffs | Folds unchanged context. Strips git noise (`index`, `old mode`). | 50–75% |
| Text | Abbreviates `implementation→impl`, `configuration→config`. Removes filler phrases. | 10–30% |

---

## Usage

```python
import ptk

# Any Python object — auto-detected, one call
ptk.minimize(api_response)        # dict/list → compact JSON, nulls stripped
ptk.minimize(source_code)         # strips comments, collapses docstrings
ptk.minimize(log_output)          # dedup repeated lines, keep errors
ptk.minimize(git_diff)            # fold context, keep changes
ptk.minimize(any_object)          # always returns a string, never raises

# Aggressive mode — maximum compression
ptk.minimize(response, aggressive=True)

# Force content type
ptk.minimize(text, content_type="code", mode="signatures")  # sigs only
ptk.minimize(logs, content_type="log", errors_only=True)    # errors only

# Stats — token counts + savings
ptk.stats(response)
# {
#   "output": "...",
#   "original_tokens": 1450,
#   "minimized_tokens": 792,
#   "savings_pct": 45.4,
#   "content_type": "dict"
# }

# Callable shorthand
ptk(response)  # same as ptk.minimize(response)
```

---

## Real-World Examples

### RAG Pipeline — compress retrieved documents before they enter the prompt

The most common place tokens are wasted in production. Retrieval returns full documents; you only need the content.

```python
import ptk

def build_context(docs: list[dict]) -> str:
    """Compress retrieved docs before injecting into an LLM prompt."""
    chunks = []
    for doc in docs:
        content = ptk.minimize(doc["content"])   # strip boilerplate
        chunks.append(f"[{doc['source']}]\n{content}")
    return "\n\n---\n\n".join(chunks)
```

See [`examples/rag_pipeline.py`](examples/rag_pipeline.py) for a full working demo with token counts.

---

### LangGraph / LangChain — compress tool outputs between nodes

```python
import ptk

def compress_tool_output(state: dict) -> dict:
    """Drop this node between any tool call and the next LLM call."""
    state["messages"][-1]["content"] = ptk.minimize(
        state["messages"][-1]["content"], aggressive=True
    )
    return state
```

See [`examples/langgraph_agent.py`](examples/langgraph_agent.py) — a complete agent loop with live token savings printed per step.

---

### Log Triage — paste only what matters to Claude / GPT

```python
import ptk

# 10,000-line CI log → only the failures, instantly
errors = ptk.minimize(ci_log, content_type="log", aggressive=True)
# Feed `errors` to your LLM. 80%+ fewer tokens, same diagnostic signal.
```

See [`examples/log_triage.py`](examples/log_triage.py) — reads a real log file, shows before/after.

---

## API Reference

### `ptk.minimize(obj, *, aggressive=False, content_type=None, **kw) → str`

- `aggressive=True` — maximum compression (timestamps stripped, sigs-only for code, errors-only for logs)
- `content_type` — override auto-detection: `"dict"`, `"list"`, `"code"`, `"log"`, `"diff"`, `"text"`
- `format` — dict output format: `"json"` (default), `"kv"`, `"tabular"`
- `mode` — code mode: `"clean"` (default) or `"signatures"`
- `errors_only` — log mode: keep only errors + stack traces

### `ptk.stats(obj, **kw) → dict`

Same as `minimize` but returns `output`, `original_tokens`, `minimized_tokens`, `savings_pct`, `content_type`.

### `ptk(obj)` — callable shorthand

The module itself is callable. `ptk(x)` is identical to `ptk.minimize(x)`.

---

## Comparison

| Tool | Type | What it does |
|---|---|---|
| **ptk** | Python library | One call, any Python object, zero deps |
| [RTK](https://github.com/rtk-ai/rtk) | Rust CLI | Compresses shell command output for coding agents |
| [claw-compactor](https://github.com/open-compress/claw-compactor) | Python library | 14-stage AST-aware pipeline, heavier setup |
| [LLMLingua](https://github.com/microsoft/LLMLingua) | Python library | Neural compression, requires GPU |

---

## Design

- **Zero required dependencies** — stdlib only. `tiktoken` optional for exact token counts.
- **Never raises** — any Python object produces a string. Circular refs, `bytes`, `nan`, generators — all handled.
- **Never mutates** — your input is always untouched.
- **Thread-safe** — stateless singleton minimizers.
- **Fast** — precompiled regexes, `frozenset` lookups, single-pass algorithms. Microseconds per call.

---

## Development

```bash
git clone https://github.com/amahi2001/python-token-killer.git
cd python-token-killer
uv sync          # installs all dev dependencies, creates .venv automatically
make check       # lint + typecheck + 361 tests
```

## License

MIT
