#!/usr/bin/env bash
# Test script for CI
set -euo pipefail

echo "=== Running Tests ==="

uv run pytest --cov=packages --cov-report=term-missing

echo ""
echo "✓ All tests passed"
