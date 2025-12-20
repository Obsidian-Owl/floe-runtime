# floe-runtime Makefile
# Provides consistent commands that mirror CI exactly

.PHONY: check lint typecheck security test test-unit test-contract test-integration format install hooks docker-up docker-down docker-logs help

# Default target
help:
	@echo "floe-runtime development commands:"
	@echo ""
	@echo "Code Quality:"
	@echo "  make check           - Run all CI checks (lint, type, security, test)"
	@echo "  make lint            - Run linting (ruff, isort)"
	@echo "  make typecheck       - Run mypy strict type checking"
	@echo "  make security        - Run security scans (bandit)"
	@echo "  make format          - Auto-format code"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests in Docker (unit + contract + integration)"
	@echo "  make test-unit       - Run unit tests only (no Docker required)"
	@echo "  make test-contract   - Run contract tests only (no Docker required)"
	@echo "  make test-integration - Run integration tests only in Docker"
	@echo ""
	@echo "Docker Services:"
	@echo "  make docker-up       - Start test infrastructure"
	@echo "  make docker-down     - Stop test infrastructure"
	@echo "  make docker-logs     - View service logs"
	@echo ""
	@echo "Setup:"
	@echo "  make install         - Install dependencies"
	@echo "  make hooks           - Install git hooks"
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

# Tests - ALL tests run in Docker for consistent hostname resolution
test:
	@echo "🧪 Running all tests in Docker..."
	@./testing/docker/scripts/run-all-tests.sh

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

# ==============================================================================
# Docker Test Infrastructure
# ==============================================================================

# Run unit tests (no Docker required)
test-unit:
	@echo "🧪 Running unit tests..."
	uv run pytest packages/*/tests/unit/ -v --tb=short

# Run contract tests (no Docker required)
test-contract:
	@echo "🧪 Running contract tests..."
	uv run pytest tests/contract/ packages/*/tests/contract/ -v --tb=short

# Run integration tests inside Docker network (zero-config)
test-integration:
	@echo "🐳 Running integration tests in Docker..."
	@./testing/docker/scripts/run-integration-tests.sh

# Start Docker services (storage profile)
docker-up:
	@echo "🚀 Starting Docker services..."
	cd testing/docker && docker compose --profile storage up -d --wait
	@echo "✅ Services ready!"
	@echo "   Polaris:    http://localhost:8181"
	@echo "   LocalStack: http://localhost:4566"

# Stop Docker services
docker-down:
	@echo "🛑 Stopping Docker services..."
	cd testing/docker && docker compose --profile storage --profile test down
	@echo "✅ Services stopped"

# View Docker service logs
docker-logs:
	cd testing/docker && docker compose --profile storage logs -f
