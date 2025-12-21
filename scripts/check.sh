#!/usr/bin/env bash
# Pre-push validation script - uses standardized Makefile targets
# Run this before pushing to catch issues early

set -e

echo "🔍 Running pre-push checks (mirrors CI)..."
echo ""

cd "$(git rev-parse --show-toplevel)"

echo "📋 Lint checks..."
make lint
echo ""

echo "🔬 Type check..."
make typecheck
echo ""

echo "🔒 Security scan..."
make security
echo ""

echo "🧪 Unit Tests (integration tests run in Docker CI)..."
make test-unit
echo ""

echo "🎉 All checks passed! Safe to push."
