.PHONY: install test lint typecheck check bench clean

# Run everything a PR needs to pass
check: lint typecheck test

install:
	pip install -e ".[dev]"

test:
	PYTHONPATH=src python -m pytest tests/ -v --tb=short

lint:
	ruff check src/ tests/ benchmarks/ examples/
	ruff format --check src/ tests/

typecheck:
	mypy --strict src/ptk/

bench:
	python benchmarks/bench.py

# auto-fix lint issues
fix:
	ruff check --fix src/ tests/ benchmarks/ examples/
	ruff format src/ tests/

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
