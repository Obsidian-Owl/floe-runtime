#!/bin/bash
# Run unit tests (no Docker services required)
#
# Unit tests run directly on the host machine and don't require any Docker
# services. They use mocks for external dependencies.
#
# Usage:
#   ./run-unit-tests.sh                            # Run all unit tests
#   ./run-unit-tests.sh packages/floe-core/tests/  # Run specific package
#   ./run-unit-tests.sh -k "test_validation"       # Run specific tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"

cd "$PROJECT_ROOT"

echo "==> Running unit tests..."
uv run pytest -m "not integration" "$@"

echo "==> Unit tests completed"
