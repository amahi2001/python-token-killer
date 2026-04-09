# AGENTS.md

## Project Overview

**ptk (python-token-killer)** is a zero-dependency Python library that minimizes LLM tokens from Python objects. It auto-detects content type (dict, list, code, log, diff, text) and applies the right compression strategy.

## Architecture

```
ptk.minimize(obj) → _types.detect(obj) → _ROUTER[type].run(obj) → MinResult
```

- `src/ptk/__init__.py` — Public API (`minimize`, `stats`, `detect_type`), callable module trick, router
- `src/ptk/_types.py` — ContentType enum + detection heuristics (O(1) for non-strings, 2KB scan for strings)
- `src/ptk/_base.py` — `Minimizer` ABC, `MinResult` frozen dataclass, shared helpers (`strip_nullish`, `dedup_lines`, `_serialize`)
- `src/ptk/minimizers/` — Six strategy implementations:
  - `_dict.py` — Null stripping, key shortening, flattening, kv/tabular formats
  - `_list.py` — Schema-once tabular, dedup with counts, sampling
  - `_code.py` — Comment stripping (pragma-preserving), docstring collapse, signature extraction
  - `_log.py` — Line dedup, timestamp strip, error-only filter, stack trace preservation
  - `_diff.py` — Context folding, noise stripping
  - `_text.py` — Word/phrase abbreviation, filler removal, stopword removal

## Key Design Rules

- **Zero required dependencies.** Never add a required dep to pyproject.toml. tiktoken is optional.
- **`minimize()` must NEVER raise on valid Python objects.** `Minimizer.run()` catches `RecursionError`, `ValueError`, `TypeError`, `OverflowError` and falls back to `str(obj)`.
- **`_serialize()` must NEVER raise.** It uses `default=str` + try/except for length measurement.
- **Inputs are never mutated.** All minimizers create new objects. Tests verify via deepcopy comparison.
- **Minimizers are stateless singletons.** Thread-safe by design — no instance state.
- **Regexes are precompiled at module level.** Never compile inside a function.
- **Pragmas are preserved.** CodeMinimizer keeps `# noqa`, `# type: ignore`, `# TODO`, `// eslint-disable`, etc.

## Commands

```bash
# run tests (322 tests, <0.5s)
PYTHONPATH=src python -m pytest tests/ -v

# run benchmarks (requires tiktoken)
python benchmarks/bench.py

# type check
mypy --strict src/ptk/

# lint
ruff check src/ tests/
```

## Test Structure

- `tests/test_ptk.py` — 153 feature tests covering all minimizers, detection, helpers, API
- `tests/test_adversarial.py` — 169 adversarial tests: type chaos, circular refs, deep nesting, unicode, regex safety, concurrency, mutation, performance, idempotency, content type mismatch

## Adding a Minimizer

1. Create `src/ptk/minimizers/_yourtype.py` — subclass `Minimizer`, implement `_minimize()`
2. Add `ContentType.YOURTYPE` to `_types.py` + detection heuristic in `detect()`
3. Register in `_ROUTER` in `__init__.py`
4. Export from `minimizers/__init__.py`
5. Add tests in both test files
