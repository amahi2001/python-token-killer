# Getting Started

## Install

```bash
pip install python-token-killer
```

Or with uv:

```bash
uv add python-token-killer
```

Python 3.10+ required. No other dependencies.

## Your first call

Pass any Python object to `ptk`. It detects the content type and compresses it:

```python
import ptk

api_response = {
    "user": {
        "id": 8821,
        "name": "Alice Chen",
        "email": "alice@example.com",
        "bio": None,
        "avatar_url": None,
        "phone": None,
        "preferences": {"theme": "dark", "notifications": None},
        "last_login": None,
        "is_verified": True,
    },
    "errors": None,
    "warnings": [],
}

result = ptk(api_response)
print(result)
# → '{"user":{"id":8821,"name":"Alice Chen","email":"alice@example.com","preferences":{"theme":"dark"},"is_verified":true}}'
```

52% fewer tokens. The seven null fields and two empty containers are gone.

## The three entry points

```python
import ptk

# Callable shorthand — most common
ptk(obj)

# Named function — same behavior
ptk.minimize(obj)

# With stats — returns token counts too
ptk.stats(obj)
# → {"output": "...", "original_tokens": 1450, "minimized_tokens": 792, "savings_pct": 45.4, "content_type": "dict"}
```

## Auto-detection

ptk identifies the content type before compressing. You don't configure it:

| Input | Detected as | Strategy |
| --- | --- | --- |
| `dict` / `list` | `dict` / `list` | Strip nulls, tabular encoding |
| String with `def ` / `class ` | `code` | Strip comments, collapse docstrings |
| String with `ERROR` / stack traces | `log` | Dedup lines, keep errors |
| String with `@@` / `+++` / `---` | `diff` | Fold context, strip git noise |
| Everything else | `text` | Abbreviate verbose words, remove filler |

To check what type ptk detected:

```python
ptk.detect_type(obj)  # → "dict" | "list" | "code" | "log" | "diff" | "text"
```

## Aggressive mode

`aggressive=True` maximizes compression — strips timestamps, extracts signatures only for code, filters to errors for logs:

```python
ptk.minimize(ci_log, aggressive=True)
# 80%+ fewer tokens on a typical CI run
```

## Override detection

Force a specific content type or mode when auto-detection isn't what you want:

```python
# Extract only function signatures from a module
ptk.minimize(source_code, content_type="code", mode="signatures")

# Keep null values that carry meaning
ptk.minimize({"status": "pending", "error": None}, strip_nulls=False)
# → '{"status":"pending","error":null}'
```

## tiktoken (optional)

`ptk.stats()` returns token counts only when `tiktoken` is installed. Install it to unlock exact savings numbers:

```bash
pip install "python-token-killer[tiktoken]"
```

Without it, `original_tokens` and `minimized_tokens` fall back to character length estimates.
