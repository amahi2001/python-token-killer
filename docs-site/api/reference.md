# API Reference

## `ptk(obj)` — callable shorthand

The module itself is callable. `ptk(obj)` is identical to `ptk.minimize(obj)`.

```python
import ptk

ptk({"user": {"id": 1, "name": "Alice", "bio": None}})
# → '{"user":{"id":1,"name":"Alice"}}'
```

---

## `ptk.minimize(obj, *, aggressive=False, content_type=None, **kw) → str`

Compresses `obj` and returns a string. Never raises on valid Python objects.

### Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `obj` | `Any` | — | Any Python object |
| `aggressive` | `bool` | `False` | Maximum compression: strips timestamps, sigs-only for code, errors-only for logs |
| `content_type` | `str \| None` | `None` | Override auto-detection: `"dict"`, `"list"`, `"code"`, `"log"`, `"diff"`, `"text"` |
| `strip_nulls` | `bool` | `True` | For dicts/lists: strip `None`, `""`, `[]`, `{}` |
| `format` | `str` | `"json"` | Dict output format: `"json"`, `"kv"`, `"tabular"` |
| `mode` | `str` | `"clean"` | Code output mode: `"clean"` or `"signatures"` |
| `errors_only` | `bool` | `False` | For logs: keep only errors and stack traces |

### Examples

```python
import ptk

# ── dict/list ────────────────────────────────────────────────
ptk.minimize(api_response)
# Strips None, "", [], {} recursively. Returns compact JSON.

ptk.minimize(records, format="tabular")
# Uniform list of dicts → TSV-style table. 60–70% savings.

ptk.minimize(response, strip_nulls=False)
# Preserve nulls when they carry semantic meaning.

# ── code ─────────────────────────────────────────────────────
ptk.minimize(source_code)
# Strips comments (preserves # noqa, # type: ignore, TODO).
# Collapses docstrings to one line.

ptk.minimize(source_code, mode="signatures")
# Returns function/class signatures only. Up to 89% savings.

ptk.minimize(source_code, aggressive=True)
# Combines signature extraction with maximum noise removal.

# ── logs ─────────────────────────────────────────────────────
ptk.minimize(ci_log)
# Collapses duplicate lines with counts. Preserves stack traces.

ptk.minimize(ci_log, errors_only=True)
# Keeps only ERROR/CRITICAL lines and their stack traces.

ptk.minimize(ci_log, aggressive=True)
# errors_only + timestamp stripping + line dedup.

# ── diffs ────────────────────────────────────────────────────
ptk.minimize(git_diff)
# Folds unchanged context (@@...@@ blocks). Strips git noise:
# index lines, old/new mode, binary indicators.

# ── text ─────────────────────────────────────────────────────
ptk.minimize(prose)
# Abbreviates verbose words: implementation→impl, configuration→config.
# Removes filler phrases and stopwords.

# ── force type ───────────────────────────────────────────────
ptk.minimize(text, content_type="code")
# Treats any string as code regardless of content.
```

---

## `ptk.stats(obj, **kw) → dict`

Same interface as `minimize`. Returns a dict with the compressed output plus token counts.

### Return value

```python
{
    "output": str,            # the compressed string
    "original_tokens": int,   # token count before compression
    "minimized_tokens": int,  # token count after compression
    "savings_pct": float,     # percentage saved, e.g. 45.4
    "content_type": str,      # detected or forced type
}
```

`original_tokens` and `minimized_tokens` use `tiktoken` (`cl100k_base`) when installed. Without it, they fall back to `len(text) // 4`.

### Example

```python
import ptk

result = ptk.stats(api_response)
print(f"Saved {result['savings_pct']:.1f}% ({result['original_tokens']} → {result['minimized_tokens']} tokens)")
# → Saved 45.4% (1450 → 792 tokens)
```

---

## `ptk.detect_type(obj) → str`

Returns the detected content type without compressing.

```python
ptk.detect_type({"key": "value"})         # → "dict"
ptk.detect_type([1, 2, 3])               # → "list"
ptk.detect_type("def foo():\n    pass")  # → "code"
ptk.detect_type("ERROR: connection refused\nTraceback...") # → "log"
ptk.detect_type("@@ -1,3 +1,4 @@\n+new line") # → "diff"
ptk.detect_type("Some prose text.")      # → "text"
```

Detection is fast: O(1) for non-strings (checks Python type), 2KB scan for strings.

---

## Content type strategies

| Type | Trigger | Key savings |
| --- | --- | --- |
| `dict` | `isinstance(obj, dict)` | Null stripping, key shortening, tabular encoding |
| `list` | `isinstance(obj, list)` | Schema-once tabular, dedup with counts, sampling |
| `code` | `def `, `class `, `import ` in first 2KB | Comment strip (pragma-safe), docstring collapse, sig extraction |
| `log` | `ERROR`, `WARNING`, `Traceback` in first 2KB | Line dedup with counts, error filter, stack trace preservation |
| `diff` | `@@` or `+++ ` / `--- ` in first 2KB | Context folding, git noise strip |
| `text` | fallback for all strings | Word abbreviation, filler removal, stopword removal |

---

## Error handling guarantees

- `minimize()` **never raises** on valid Python objects. `RecursionError`, `ValueError`, `TypeError`, `OverflowError` inside a minimizer all fall back to `str(obj)`.
- `minimize()` **never mutates** the input. Verified by deepcopy comparison in the test suite.
- The module is **thread-safe**. Minimizers are stateless singletons.
