# Contributing to ptk

Thanks for your interest in contributing to python-token-killer.

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/ptk.git
cd ptk
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
python -m pytest tests/ -v
```

All 153+ tests must pass before submitting a PR.

## Adding a New Minimizer

1. Create `src/ptk/minimizers/_yourtype.py`
2. Subclass `Minimizer` from `ptk._base` and implement `_minimize()`
3. Add to `src/ptk/minimizers/__init__.py`
4. Add a `ContentType` enum member in `src/ptk/_types.py` and detection heuristic in `detect()`
5. Register in the `_ROUTER` dict in `src/ptk/__init__.py`
6. Add tests in `tests/test_ptk.py`

## Design Principles

- **Zero required deps** — stdlib only in core. Optional deps behind extras.
- **Builtins-first** — prefer `frozenset`, precompiled `re`, `slots=True` dataclasses.
- **DRY** — shared helpers live in `_base.py` and are reused across minimizers.
- **No data loss by default** — aggressive mode is opt-in. Default mode should never destroy meaning.
- **Type-routed** — auto-detection is O(1) for non-strings, first-2KB heuristic for strings.

## Code Style

- Type hints on all public functions
- Docstrings on all classes and public methods
- Private helpers prefixed with `_`
- Precompile regexes at module level (not inside functions)
