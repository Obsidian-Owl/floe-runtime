#!/usr/bin/env bash
# Type checking script for CI
set -euo pipefail

echo "=== Running Type Checker ==="

uv run mypy --strict packages/

echo ""
echo "✓ Type checking passed"
