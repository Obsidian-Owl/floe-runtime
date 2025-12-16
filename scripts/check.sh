#!/usr/bin/env bash
# Pre-push validation script - mirrors CI checks exactly
# Run this before pushing to catch issues early

set -e

echo "🔍 Running pre-push checks (mirrors CI)..."
echo ""

cd "$(git rev-parse --show-toplevel)"

echo "📋 Lint checks..."
uv run ruff check .
uv run ruff format --check .
uv run isort --check packages/
echo "✅ Lint passed"
echo ""

echo "🔬 Type check..."
uv run mypy --strict packages/*/src/
echo "✅ Type check passed"
echo ""

echo "🔒 Security scan..."
uv run bandit -r packages/*/src/ -ll -q
echo "✅ Security scan passed"
echo ""

echo "🧪 Tests..."
uv run pytest packages/*/tests/ -q --tb=short
echo "✅ Tests passed"
echo ""

echo "🎉 All checks passed! Safe to push."
