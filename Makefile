# floe-runtime Makefile
# Provides consistent commands that mirror CI exactly

.PHONY: check lint typecheck security test format install hooks help

# Default target
help:
	@echo "floe-runtime development commands:"
	@echo ""
	@echo "  make check      - Run all CI checks (lint, type, security, test)"
	@echo "  make lint       - Run linting (ruff, isort)"
	@echo "  make typecheck  - Run mypy strict type checking"
	@echo "  make security   - Run security scans (bandit)"
	@echo "  make test       - Run pytest"
	@echo "  make format     - Auto-format code"
	@echo "  make install    - Install dependencies"
	@echo "  make hooks      - Install git hooks"
	@echo ""

# Full CI check - mirrors .github/workflows/ci.yml exactly
check: lint typecheck security test
	@echo "✅ All checks passed!"

# Lint checks - mirrors CI lint job
lint:
	@echo "📋 Running lint checks..."
	uv run ruff check .
	uv run ruff format --check .
	uv run isort --check packages/

# Type checking - mirrors CI typecheck job
typecheck:
	@echo "🔬 Running type check..."
	uv run mypy --strict packages/*/src/

# Security scanning - mirrors CI security job
security:
	@echo "🔒 Running security scan..."
	uv run bandit -r packages/*/src/ -ll -q

# Tests - mirrors CI test job
test:
	@echo "🧪 Running tests..."
	uv run pytest packages/*/tests/ -q --tb=short

# Auto-format code
format:
	@echo "🎨 Formatting code..."
	uv run ruff format .
	uv run isort packages/

# Install dependencies
install:
	uv sync --all-packages

# Install git hooks
hooks:
	git config core.hooksPath .githooks
	@echo "✅ Git hooks installed from .githooks/"
