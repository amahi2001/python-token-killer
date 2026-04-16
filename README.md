<p align="center">
  <img src="assets/mascot.png" alt="ptk" width="200"/>
</p>

<p align="center">
  <strong>ptk — Python Token Killer</strong><br/>
  <strong>One call. Any Python object. Fewer tokens.</strong><br/>
  Zero dependencies · Auto type detection · 361 tests
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

## Your LLM calls carry dead weight

A typical API response you feed into an agent:

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

Seven null fields, two empty containers. Your LLM reads them, bills you for them, learns nothing from them. `ptk` strips the noise:

```python
import ptk
ptk(response)
```

```json
{"user":{"id":8821,"name":"Alice Chen","email":"alice@example.com","preferences":{"theme":"dark"},"created_at":"2024-01-15T10:30:00Z","updated_at":"2024-06-20T14:22:00Z","is_verified":true,"is_active":true}}
```

52% fewer tokens. Same information. No config needed.

```bash
pip install python-token-killer
# or
uv add python-token-killer
```

---

## Benchmarks

Token counts via tiktoken (`cl100k_base`, the tokenizer behind GPT-4 and Claude):

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

At Claude Sonnet 4.6 pricing ($3/1M input tokens), a 76% reduction on 100k tokens/day saves ~$6/month per user. Multiply that by your user base and your agent loop iterations.

Run it yourself: `python benchmarks/bench.py`

---

## How it works

You pass `ptk` any Python object. It detects the content type and picks the right compression strategy:

| Input           | Strategy                                                                                                   | Savings |
| --------------- | ---------------------------------------------------------------------------------------------------------- | ------- |
| `dict` / `list` | Strips `null`, `""`, `[]`, `{}` recursively. Tabular encoding for uniform arrays.                          | 40–70%  |
| Code            | Strips comments (preserves `# noqa`, `# type: ignore`, `TODO`). Collapses docstrings. Extracts signatures. | 25–89%  |
| Logs            | Collapses duplicate lines with counts. Filters to errors and stack traces.                                 | 60–90%  |
| Diffs           | Folds unchanged context. Strips git noise (`index`, `old mode`).                                           | 50–75%  |
| Text            | Abbreviates verbose words (`implementation→impl`, `configuration→config`). Removes filler.                 | 10–30%  |

---

## Usage

```python
import ptk

# ── auto-detected, one call ──────────────────────────────────
ptk.minimize(api_response)        # dict/list → compact JSON, nulls stripped
ptk.minimize(source_code)         # strips comments, collapses docstrings
ptk.minimize(log_output)          # dedup repeated lines, keep errors
ptk.minimize(git_diff)            # fold context, keep changes
ptk.minimize(any_object)          # always returns a string, never raises

# ── aggressive mode: maximum compression ─────────────────────
ptk.minimize(response, aggressive=True)

# ── force content type ───────────────────────────────────────
ptk.minimize(text, content_type="code", mode="signatures")  # sigs only
ptk.minimize(logs, content_type="log", errors_only=True)    # errors only

# ── stats: token counts + savings ────────────────────────────
ptk.stats(response)
# {
#   "output": "...",
#   "original_tokens": 1450,
#   "minimized_tokens": 792,
#   "savings_pct": 45.4,
#   "content_type": "dict"
# }

# ── callable shorthand ───────────────────────────────────────
ptk(response)  # same as ptk.minimize(response)

# ── preserve nulls when they carry meaning ───────────────────
ptk.minimize({"status": "pending", "error": None}, strip_nulls=False)
# → {"status":"pending","error":null}
```

---

## Real-world examples

### RAG pipeline: compress retrieved docs before they hit the prompt

Your retriever returns full documents. The LLM needs the content, not the metadata scaffolding around it.

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

Full working demo with token counts: [`examples/rag_pipeline.py`](examples/rag_pipeline.py)

---

### LangGraph / LangChain: compress tool outputs between nodes

Drop this node between a tool call and the next LLM call. Tool outputs shrink before they re-enter the context window.

```python
import ptk

def compress_tool_output(state: dict) -> dict:
    """Compress the last tool message before the next LLM call."""
    state["messages"][-1]["content"] = ptk.minimize(
        state["messages"][-1]["content"], aggressive=True
    )
    return state
```

Complete agent loop with per-step token savings: [`examples/langgraph_agent.py`](examples/langgraph_agent.py)

---

### Log triage: feed only failures to your LLM

A 10,000-line CI log collapses to the failures and their stack traces.

```python
import ptk

errors = ptk.minimize(ci_log, content_type="log", aggressive=True)
# 80%+ fewer tokens, same diagnostic signal.
```

Before/after demo: [`examples/log_triage.py`](examples/log_triage.py)

---

## API reference

### `ptk.minimize(obj, *, aggressive=False, content_type=None, **kw) → str`

- **`aggressive=True`** maximizes compression: timestamps stripped, signatures-only for code, errors-only for logs
- **`content_type`** overrides auto-detection: `"dict"`, `"list"`, `"code"`, `"log"`, `"diff"`, `"text"`
- **`format`** controls dict output: `"json"` (default), `"kv"`, `"tabular"`
- **`mode`** controls code output: `"clean"` (default) or `"signatures"`
- **`errors_only`** filters logs to errors and stack traces

### `ptk.stats(obj, **kw) → dict`

Same interface as `minimize`. Returns `output`, `original_tokens`, `minimized_tokens`, `savings_pct`, `content_type`.

### `ptk(obj)` callable shorthand

The module itself is callable. `ptk(x)` equals `ptk.minimize(x)`.

---

## Comparison

| Tool                                                              | Type           | Tradeoff                                          |
| ----------------------------------------------------------------- | -------------- | ------------------------------------------------- |
| **ptk**                                                           | Python library | One call, any Python object, zero deps            |
| [RTK](https://github.com/rtk-ai/rtk)                              | Rust CLI       | Compresses shell command output for coding agents |
| [claw-compactor](https://github.com/open-compress/claw-compactor) | Python library | 14-stage AST-aware pipeline, heavier setup        |
| [LLMLingua](https://github.com/microsoft/LLMLingua)               | Python library | Neural compression, requires GPU                  |

---

## Design

- **Zero required dependencies.** Stdlib only. `tiktoken` is optional for exact token counts.
- **Never raises.** Any Python object produces a string. Circular refs, `bytes`, `nan`, generators all handled.
- **Never mutates.** Your input stays untouched.
- **Thread-safe.** Stateless singleton minimizers.
- **Fast.** Precompiled regexes, `frozenset` lookups, single-pass algorithms. Microseconds per call.

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
