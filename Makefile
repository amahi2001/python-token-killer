.PHONY: install test lint typecheck check bench fix build clean

# Install all dev dependencies into the uv-managed venv
install:
	uv sync --locked --all-groups

# Run everything CI runs — use this before every PR
check: lint typecheck test

test:
	uv run pytest tests/ -v --tb=short

lint:
	uv run ruff check src/ tests/ benchmarks/ examples/
	uv run ruff format --check src/ tests/

typecheck:
	uv run mypy --strict src/ptk/

bench:
	uv run python benchmarks/bench.py

# Auto-fix lint and formatting issues (all dirs — matches pre-commit scope)
fix:
	uv run ruff check --fix src/ tests/ benchmarks/ examples/
	uv run ruff format src/ tests/ benchmarks/ examples/

# Build wheel + sdist (use --no-sources for PyPI compatibility)
build:
	uv build --no-sources

clean:
	rm -rf dist/ __pycache__ .pytest_cache .mypy_cache .ruff_cache *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
