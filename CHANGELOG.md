# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

---

## [0.1.0] - 2026-04-09

Initial public release.

### API

- `ptk.minimize(obj)` — auto-detects content type, applies the right compression strategy, returns a minimized string. Accepts `aggressive`, `content_type`, and minimizer-specific kwargs.
- `ptk.stats(obj)` — same compression, returns a dict with `output`, `original_tokens`, `minimized_tokens`, `savings_pct`, `content_type`.
- `ptk.detect_type(obj)` — returns the auto-detected content type as a string.
- `ptk(obj)` — callable module shorthand for `ptk.minimize(obj)`.

### Minimizers

- **DictMinimizer** — recursive null/empty stripping (preserves `0` and `False`), key shortening (`description` → `desc`, `configuration` → `cfg`, 30+ mappings), single-child flattening, kv/tabular output formats.
- **ListMinimizer** — schema-once tabular encoding for uniform list-of-dicts, primitive dedup with `(xN)` counts, deterministic even-spaced sampling with first/last preservation.
- **CodeMinimizer** — comment stripping with pragma preservation (`# noqa`, `# type: ignore`, `# TODO`, `# FIXME`, `// eslint-disable`), multi-line docstring collapse to first line, multi-language signature extraction (Python, JS, Rust, Go).
- **LogMinimizer** — consecutive duplicate line collapse, timestamp stripping, error-only filtering with stack trace preservation (`Traceback`, `File`, `*Error:`, `*Exception:`), `"failed"` keyword preservation, FATAL/CRITICAL treated as errors.
- **DiffMinimizer** — context line folding to `... N lines ...`, noise stripping (`index`, `old mode`, `new mode`, `similarity`, `Binary files`), `\ No newline at end of file` preservation.
- **TextMinimizer** — 20+ word abbreviations (`implementation` → `impl`, `configuration` → `config`, `production` → `prod`, case-preserving), 16 phrase abbreviations (`in order to` → `to`, `due to the fact that` → `because`), 13 filler phrase removals (`Furthermore,`, `Moreover,`, `Additionally,`), stopword removal (aggressive mode).

### Benchmarks

Real token counts via tiktoken (`cl100k_base`):

| Benchmark | Original | Default | Saved | Aggressive | Saved |
|---|---|---|---|---|---|
| API response (JSON) | 1,450 | 792 | 45.4% | 782 | 46.1% |
| Python module (code) | 2,734 | 2,113 | 22.7% | 309 | 88.7% |
| Server log (58 lines) | 1,389 | 1,388 | 0.1% | 231 | 83.4% |
| 50 user records (list) | 2,774 | 922 | 66.8% | 922 | 66.8% |
| Verbose paragraph (text) | 101 | 96 | 5.0% | 74 | 26.7% |
| **Total** | **11,182** | **7,424** | **33.6%** | **2,627** | **76.5%** |

Bundled sample data and runner: `python benchmarks/bench.py`

### Tests

322 tests across two suites:

- **test_ptk.py** (153 tests) — feature coverage for all 6 minimizers, type detection, base helpers, API contracts, and real-world payloads.
- **test_adversarial.py** (169 tests) — type chaos (None, bytes, sets, circular refs, broken `__str__`, dataclasses, generators, inf/nan), deep nesting (100-level dicts, 10k-wide structures), unicode (emoji, CJK, RTL, null bytes, surrogates, BOM), regex safety (pathological backtracking, unclosed constructs, 100k newlines), API contracts (parametrized across 9 input types), input mutation verification (deepcopy before/after), thread safety (10 concurrent threads), performance (all benchmarks under 5s), idempotency, and content type mismatch degradation.

### Examples

- `examples/clean_api_response.py` — standalone script + stdin pipe for JSON cleanup.
- `examples/langchain_middleware.py` — LangGraph node, callable wrapper, batch document minimizer.
- `examples/claude_code_skill.py` — CLI tool with `--stdin`, `--type`, `--aggressive`, `--stats` flags.

### Infrastructure

- Zero required dependencies — stdlib only. tiktoken optional (`pip install python-token-killer[tiktoken]`).
- `mypy --strict` clean across all 10 source files.
- `ruff check` clean across all source, tests, benchmarks, and examples.
- `py.typed` marker for PEP 561 type checker support.
- GitHub Actions CI workflow (Python 3.10–3.13 matrix).
- `AGENTS.md` + `CLAUDE.md` for coding agent context.
- MIT license.
