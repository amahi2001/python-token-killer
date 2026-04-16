.PHONY: install test test-unit test-adversarial test-real-world \
        lint typecheck check bench fix build clean \
        version release

# ── Development ──────────────────────────────────────────────────────────────

install:
	uv sync --locked --all-groups

# Run everything CI runs — use this before every PR
check: lint typecheck test

test:
	uv run pytest tests/ -v --tb=short

test-unit:
	uv run pytest tests/unit/ -v --tb=short

test-adversarial:
	uv run pytest tests/adversarial/ -v --tb=short

test-real-world:
	uv run pytest tests/real_world/ -v --tb=short

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

# Build wheel + sdist
build: clean
	uv build --no-sources

clean:
	rm -rf dist/ __pycache__ .pytest_cache .mypy_cache .ruff_cache *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ── Release ───────────────────────────────────────────────────────────────────
# Usage: make release VERSION=0.2.0
#
# What it does (in order):
#   1. Validates VERSION is set and not already tagged
#   2. Runs the full check suite (lint + typecheck + tests)
#   3. Bumps __version__ in src/ptk/__init__.py
#   4. Updates uv.lock (version read by hatch from __init__.py)
#   5. Commits: "chore: release vVERSION"
#   6. Tags the commit as vVERSION
#   7. Pushes commit + tag → triggers publish.yml → PyPI

release:
	@[ -n "$(VERSION)" ] || { echo "Usage: make release VERSION=x.y.z"; exit 1; }
	@git diff --quiet || { echo "Uncommitted changes — commit or stash first"; exit 1; }
	@git diff --cached --quiet || { echo "Staged changes — commit first"; exit 1; }
	@git fetch --tags -q
	@git rev-parse v$(VERSION) > /dev/null 2>&1 && \
		{ echo "Tag v$(VERSION) already exists"; exit 1; } || true
	@echo "Running check suite..."
	@$(MAKE) check
	@echo "Bumping version to $(VERSION)..."
	@sed -i '' 's/^__version__ = ".*"/__version__ = "$(VERSION)"/' src/ptk/__init__.py
	@sed -i '' 's/^    def test_version/    def test_version/' tests/unit/test_api.py
	@sed -i '' 's/assert ptk.__version__ == ".*"/assert ptk.__version__ == "$(VERSION)"/' tests/unit/test_api.py
	@uv lock --quiet
	@git add src/ptk/__init__.py tests/unit/test_api.py uv.lock
	@git commit -m "chore: release v$(VERSION)"
	@git tag v$(VERSION)
	@git push && git push origin v$(VERSION)
	@echo ""
	@echo "✓ v$(VERSION) tagged and pushed."
	@echo "  Watch CI: https://github.com/amahi2001/python-token-killer/actions"
	@echo "  Then publish the release draft on GitHub to trigger PyPI upload."

# Show current version
version:
	@grep '^__version__' src/ptk/__init__.py | cut -d'"' -f2
