# Contributing to ptk

## Quick Start

```bash
git clone https://github.com/amahi2001/python-token-killer.git
cd python-token-killer

# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dev dependencies — uv manages the venv automatically
uv sync

# Run everything CI runs — must pass before opening a PR
make check
```

That's it. `uv sync` reads `uv.lock`, creates `.venv`, and installs every dev tool pinned to exact versions. No manual venv activation needed — `uv run` handles it.

## Commands

| Command | What it does |
|---|---|
| `make check` | Lint + typecheck + tests (the one command before every PR) |
| `make test` | Tests only (361 tests, ~0.6s) |
| `make lint` | `ruff check` + `ruff format --check` |
| `make typecheck` | `mypy --strict` |
| `make bench` | Benchmarks with tiktoken |
| `make fix` | Auto-fix lint and formatting issues |
| `make build` | Build wheel + sdist (`dist/`) |
| `make clean` | Remove caches and build artifacts |

All commands use `uv run` — they work whether or not you've activated the venv.

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

Any Python object passed to `ptk.minimize()` must produce a string — never an exception. `Minimizer.run()` wraps every `_minimize()` call in a try/except that catches `RecursionError`, `ValueError`, `TypeError`, and `OverflowError`, falling back to `str(obj)`.

### 2. Never mutate the input

All minimizers must create new objects. The original `obj` passed to `minimize()` must be identical after the call. `test_adversarial.py::TestInputMutation` verifies this with `deepcopy` comparisons.

### 3. Zero required dependencies

The library must work with `pip install python-token-killer` and nothing else. No numpy, no tiktoken in the core. Optional extras are fine — import them inside try/except.

## Gotchas You'll Hit

### The callable module trick

`__init__.py` swaps its own `__class__` to `_CallableModule` so `ptk(obj)` works. Imports must be structured carefully — `sys` and `types` are imported after the public API definitions with `# noqa: E402`. Don't reorganize imports without testing `ptk({"a": 1})` interactively.

### `_serialize` vs `_minimize`

`_serialize(obj)` is called before `_minimize()` — it only measures the original length for stats. It must never raise (it has its own try/except). The actual output comes from `_minimize()`.

### `from __future__ import annotations`

Every source file uses this for PEP 563 deferred annotation evaluation on Python 3.10. Don't remove it.

### Regexes are precompiled

All regex patterns are compiled at module import time as module-level constants. Never call `re.compile()` inside a function.

### Pragma preservation in CodeMinimizer

When stripping comments, `_strip_comment_if_safe()` checks each comment against `_PRAGMA_KEYWORDS` before removing it. Comments containing `noqa`, `type: ignore`, `TODO`, `FIXME`, `eslint-disable`, etc. survive.

### Thread safety

Minimizers are stateless singletons stored in `_ROUTER`. Don't add instance attributes that change between calls.

## Adding a New Minimizer

1. Create `src/ptk/minimizers/_yourtype.py`, subclass `Minimizer`, implement `_minimize()`
2. Add `ContentType.YOURTYPE = auto()` to `_types.py` + detection heuristic in `detect()`
3. Register in `_ROUTER` in `__init__.py`
4. Export from `minimizers/__init__.py`
5. Add tests in `test_ptk.py` (feature) and `test_adversarial.py` (edge cases)

## Dependency Groups

ptk uses [PEP 735](https://peps.python.org/pep-0735/) dependency groups:

| Group | Contents | Install |
|---|---|---|
| `test` | pytest | `uv sync --only-group test` |
| `lint` | ruff | `uv sync --only-group lint` |
| `typecheck` | mypy | `uv sync --only-group typecheck` |
| `bench` | tiktoken | `uv sync --only-group bench` |
| `hooks` | pre-commit | `uv sync --only-group hooks` |
| `dev` | all of the above | `uv sync` (default) |

CI installs only what each job needs. `uv sync` with no flags installs `dev` (everything).

## Pre-commit Hooks

```bash
uv run pre-commit install
```

After that, `ruff` and `mypy` run automatically on every `git commit`. `make check` is the equivalent without needing hooks installed.

## PR Checklist

- `make check` passes
- New code has tests in `test_ptk.py` (feature) and/or `test_adversarial.py` (edge cases)
- No new required dependencies added
- Docstrings on new public classes/methods
- CHANGELOG.md updated under `[Unreleased]` if user-facing
