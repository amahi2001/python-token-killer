---
layout: home

hero:
  name: "ptk"
  text: "python-token-killer"
  tagline: "Stop paying for nulls. One call strips dead weight from any Python object before it hits your LLM."
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: API Reference
      link: /api/reference

features:
  - icon: ⚡
    title: Zero config, any object
    details: Pass a dict, a log string, source code, a git diff — ptk detects the type and picks the right compression. No setup, no schema.
  - icon: 🔬
    title: 40–89% fewer tokens
    details: Null stripping on JSON cuts 40–70%. Signature extraction from Python modules cuts 89%. Errors-only log filtering cuts 83%. Every strategy is measurable.
  - icon: 🔒
    title: Zero dependencies, never raises
    details: stdlib only. Any Python object produces a string output. Circular refs, bytes, generators, NaN — all handled. Thread-safe singleton minimizers.
---

## How much does it save?

Token counts via tiktoken (`cl100k_base`):

| Input | Before | After | Saved |
|---|---|---|---|
| API response (JSON) | 1,450 | 792 | 45% |
| Python module (signatures only) | 2,734 | 309 | 89% |
| CI log (errors only) | 1,389 | 231 | 83% |
| 50 user records (tabular) | 2,774 | 922 | 67% |
| Verbose prose | 101 | 74 | 27% |
| **Total** | **11,182** | **2,627** | **76%** |

At Claude Sonnet pricing ($3/1M input tokens), 76% savings on 100k tokens/day saves ~$6/month per user.

## Install

```bash
pip install python-token-killer
# or
uv add python-token-killer
```

## First call

```python
import ptk

response = {
    "user": {"id": 8821, "name": "Alice Chen", "bio": None, "avatar_url": None},
    "errors": None,
    "warnings": []
}

ptk(response)
# → '{"user":{"id":8821,"name":"Alice Chen"}}'
```

Seven null fields gone. Same information. No config.
