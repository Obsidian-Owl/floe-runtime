#!/usr/bin/env bash
# Linting script for CI
set -euo pipefail

echo "=== Running Linters ==="

echo "Running ruff..."
uv run ruff check .

echo "Running black..."
uv run black --check .

echo "Running isort..."
uv run isort --check packages/

echo ""
echo "✓ All linters passed"
