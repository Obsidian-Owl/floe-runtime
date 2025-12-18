#!/bin/bash
# Run integration tests inside Docker network
#
# This script runs pytest inside a Docker container on the same network as
# the test services (LocalStack, Polaris, etc.), enabling proper hostname
# resolution without requiring /etc/hosts modifications.
#
# Usage:
#   ./run-integration-tests.sh                     # Run all integration tests
#   ./run-integration-tests.sh -k "test_append"    # Run specific tests
#   ./run-integration-tests.sh -v --tb=short       # Pass pytest options
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - No other setup required (zero-config)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$DOCKER_DIR")")"

cd "$DOCKER_DIR"

echo "==> Starting test infrastructure..."
docker compose --profile storage up -d --wait

echo "==> Waiting for polaris-init to complete..."
# Wait for polaris-init to finish (it writes credentials)
timeout 60 sh -c 'until docker inspect -f "{{.State.Status}}" floe-polaris-init 2>/dev/null | grep -q "exited"; do sleep 2; done' || {
    echo "Error: polaris-init did not complete in time" >&2
    docker compose logs polaris-init
    exit 1
}

# Check polaris-init exit code
EXIT_CODE=$(docker inspect -f "{{.State.ExitCode}}" floe-polaris-init 2>/dev/null || echo "1")
if [[ "$EXIT_CODE" != "0" ]]; then
    echo "Error: polaris-init failed with exit code $EXIT_CODE" >&2
    docker compose logs polaris-init
    exit 1
fi

echo "==> Loading Polaris credentials..."
if [[ -f "$DOCKER_DIR/config/polaris-credentials.env" ]]; then
    # shellcheck disable=SC1091
    source "$DOCKER_DIR/config/polaris-credentials.env"
    export POLARIS_CLIENT_ID POLARIS_CLIENT_SECRET
    echo "   Credentials loaded (Client ID: $POLARIS_CLIENT_ID)"
else
    echo "Warning: Credentials file not found, using environment defaults"
fi

echo "==> Building test runner..."
docker compose --profile storage --profile test build test-runner

echo "==> Running integration tests..."
# Pass through any arguments to pytest
docker compose --profile storage --profile test run --rm test-runner \
    uv run pytest -m integration packages/floe-iceberg/tests/integration/ packages/floe-polaris/tests/integration/ "$@"

echo "==> Integration tests completed"
