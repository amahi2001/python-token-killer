# Contributing to ptk

## Quick Start

```bash
git clone https://github.com/amahi2001/python-token-killer.git
cd python-token-killer
python -m venv .venv && source .venv/bin/activate
make install
make check   # runs lint + typecheck + tests — this is what CI runs
```

`make check` must pass before you open a PR. If it passes locally, CI will pass.

## Commands

| Command | What it does |
|---|---|
| `make check` | Lint + typecheck + tests (run this before every PR) |
| `make test` | Tests only (322 tests, ~0.5s) |
| `make lint` | Ruff check + format check |
| `make typecheck` | mypy --strict |
| `make bench` | Benchmarks with tiktoken (requires `pip install tiktoken`) |
| `make fix` | Auto-fix lint and formatting issues |
| `make clean` | Remove caches and build artifacts |

## Architecture in 30 Seconds

```
ptk.minimize(obj)
  → _types.detect(obj)          # what is this? dict, list, code, log, diff, text
  → _ROUTER[type]               # pick the singleton minimizer
  → minimizer.run(obj)          # _serialize for measurement, _minimize for output
  → MinResult(output, lengths)  # frozen dataclass
```

Every file has one job:

```
src/ptk/
  __init__.py         Public API + callable module trick + router
  _types.py           ContentType enum + detect() heuristics
  _base.py            Minimizer ABC + MinResult + shared helpers
  minimizers/
    _dict.py          DictMinimizer    (null strip, key shorten, flatten)
    _list.py          ListMinimizer    (tabular, dedup, sampling)
    _code.py          CodeMinimizer    (comments, docstrings, signatures)
    _log.py           LogMinimizer     (dedup lines, error filter, stack traces)
    _diff.py          DiffMinimizer    (context folding, noise strip)
    _text.py          TextMinimizer    (abbreviation, filler removal, stopwords)
```

## The Three Rules

These are non-negotiable. PRs that break them will be rejected.

### 1. `minimize()` must never raise

Any Python object passed to `ptk.minimize()` must produce a string — never an exception. This is the core contract. `Minimizer.run()` wraps every `_minimize()` call in a try/except that catches `RecursionError`, `ValueError`, `TypeError`, and `OverflowError`, falling back to `str(obj)`.

If your minimizer can't handle an input, it should degrade gracefully (return a less-compressed string), not crash. The adversarial test suite (`test_adversarial.py`) will catch this — it throws circular references, `float('nan')`, generators, objects with broken `__str__`, and much more at every code path.

### 2. Never mutate the input

All minimizers must create new objects. The original `obj` passed to `minimize()` must be identical after the call. `test_adversarial.py::TestInputMutation` verifies this with `deepcopy` comparisons. If you're transforming a dict, build a new one — don't modify in place.

### 3. Zero required dependencies

The library must work with `pip install python-token-killer` and nothing else. No numpy, no tiktoken, no tree-sitter in the core. Optional extras are fine (`[tiktoken]` exists for exact token counting), but import them inside a try/except and provide a fallback.

## Gotchas You'll Hit

### The callable module trick

`__init__.py` swaps its own `__class__` to `_CallableModule` so `ptk(obj)` works. This means:
- Imports must be structured carefully — `sys` and `types` are imported after the public API definitions (with `# noqa: E402`)
- If you add new top-level names, they're accessible as attributes of the callable module
- Don't reorganize imports in `__init__.py` without testing `ptk({"a": 1})` interactively

### `_serialize` vs `_minimize`

`_serialize(obj)` is called in `Minimizer.run()` **before** `_minimize()` — it's only used to measure the original length for stats. It must never raise (it has its own try/except). The actual output comes from `_minimize()`. These are two different paths with different error handling.

### `from __future__ import annotations`

Every source file uses this. It means type annotations are strings at runtime (PEP 563), which lets us use `dict[str, Any]` on Python 3.10 without `from typing import Dict`. Don't remove it.

### Regexes are precompiled

All regex patterns are compiled at module import time as module-level constants (`_BLOCK_COMMENT`, `_TIMESTAMP`, etc.). Never call `re.compile()` inside a function — it defeats the purpose and adds per-call overhead.

### Pragma preservation in CodeMinimizer

When stripping comments, `_strip_comment_if_safe()` checks each comment against `_PRAGMA_KEYWORDS` before removing it. Comments containing `noqa`, `type: ignore`, `TODO`, `FIXME`, `eslint-disable`, etc. survive. If you add a new comment-stripping pattern, it must go through this check.

### Thread safety

Minimizers are stateless singletons stored in `_ROUTER`. They're created once at import time and reused across all calls. Don't add instance attributes that change between calls — this would break thread safety. `test_adversarial.py::TestConcurrency` runs 10 threads simultaneously to verify this.

## Adding a New Minimizer

This is the most common type of contribution. Here's the full checklist:

### 1. Create the minimizer

Create `src/ptk/minimizers/_yourtype.py`:

```python
"""YourType minimizer — one-line description."""

from __future__ import annotations

from typing import Any

from ptk._base import Minimizer


class YourTypeMinimizer(Minimizer):
    """Compress YourType via specific strategies.

    Strategies:
    1. Default mode — conservative, no data loss
    2. Aggressive mode — maximum compression, some fidelity loss
    """

    def _minimize(self, obj: Any, *, aggressive: bool = False, **kw: Any) -> str:
        text = obj if isinstance(obj, str) else str(obj)

        # your compression logic here
        # use helpers from _base if applicable (strip_nullish, dedup_lines)

        return text
```

### 2. Add detection

In `src/ptk/_types.py`:
- Add `YOURTYPE = auto()` to the `ContentType` enum
- Add a detection heuristic in `detect()` — order matters (first match wins)
- Detection should be fast — check the first ~2KB only

### 3. Wire it up

In `src/ptk/__init__.py`:
- Import your minimizer
- Add to `__all__`
- Add to `_ROUTER`: `ContentType.YOURTYPE: YourTypeMinimizer()`

In `src/ptk/minimizers/__init__.py`:
- Add the import and `__all__` entry

### 4. Write tests

In `tests/test_ptk.py`:
- Detection tests (does `detect()` identify your content type?)
- Basic compression (does it compress?)
- Aggressive mode (does it compress more?)
- Edge cases (empty input, single line, unicode)
- Feature-specific tests (whatever your minimizer does)

In `tests/test_adversarial.py`:
- Add your type to `TestAPIContracts.SAMPLE_INPUTS`
- Add a content type mismatch test in `TestContentTypeMismatch`

### 5. Verify

```bash
make check   # must pass
```

## Writing Tests

The test suite has two files with different purposes:

### `test_ptk.py` — "Does it work correctly?"

Feature tests. Each minimizer has its own test class. Tests verify:
- Correct output for known inputs
- Aggressive vs default mode differences
- Edge cases specific to that minimizer
- Detection accuracy

### `test_adversarial.py` — "Can I break it?"

Chaos tests. These don't test specific outputs — they test that ptk **doesn't crash** on adversarial inputs. Categories:
- Type chaos (every Python builtin type)
- Circular references and deep nesting
- Unicode and encoding edge cases
- Regex safety (pathological patterns)
- API contract guarantees (return types, dict completeness)
- Input mutation (deepcopy before/after)
- Concurrency (thread safety)
- Performance (large inputs under 5 seconds)
- Idempotency (minimizing twice = same result)

If you add a new minimizer, the parametrized tests in `TestAPIContracts` will automatically test it once you add a sample to `SAMPLE_INPUTS`.

## Code Style

- `mypy --strict` must pass — all public functions need full type annotations
- `ruff check` must pass — imports sorted, no unused variables, no deprecated patterns
- Docstrings on all classes and public methods
- Private helpers prefixed with `_`
- Line length: 100 chars (configured in pyproject.toml)
- `make fix` will auto-fix most formatting and import issues

## PR Etiquette

- Keep PRs focused — one feature or fix per PR
- Run `make check` before pushing
- If you're adding a minimizer, include benchmarks showing token savings on realistic data
- Update CHANGELOG.md under an `[Unreleased]` section
- If your change affects the public API, update README.md
