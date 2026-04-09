# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-08

### Added

- Core `ptk.minimize()` API with auto type detection and strategy routing
- Callable module shorthand: `ptk(obj)` as alias for `ptk.minimize(obj)`
- `ptk.stats()` for compression statistics with token count estimates
- `ptk.detect_type()` for content type inspection

#### Minimizers

- **DictMinimizer** — null stripping, key shortening, single-child flattening, kv/tabular output formats
- **ListMinimizer** — schema-once tabular encoding for uniform dicts, primitive dedup with counts, large array sampling
- **CodeMinimizer** — comment stripping with pragma preservation (noqa, type: ignore, TODO, eslint-disable), docstring collapse to first line, multi-language signature extraction (Python, JS, Rust, Go)
- **LogMinimizer** — consecutive line dedup, timestamp stripping, error-only filtering with stack trace preservation, "failed" keyword preservation
- **DiffMinimizer** — context line folding, noise stripping (index/mode lines), `\ No newline` preservation
- **TextMinimizer** — phrase abbreviation, word abbreviation (implementation→impl, etc.), filler phrase removal (Furthermore, Moreover, etc.), stopword removal (aggressive mode)

#### Infrastructure

- Zero required dependencies — tiktoken optional for exact token counts
- 153 tests covering all minimizers, edge cases, and real-world payloads
- Type hints throughout with `py.typed` marker
- MIT license
