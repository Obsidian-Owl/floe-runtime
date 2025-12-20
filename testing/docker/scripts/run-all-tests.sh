#!/bin/bash
# Run ALL tests (unit + integration) inside Docker network
#
# This script runs all pytest tests inside a Docker container on the same
# network as the test services. This ensures consistent hostname resolution
# for both unit and integration tests.
#
# Usage:
#   ./run-all-tests.sh                     # Run all tests
#   ./run-all-tests.sh -k "test_append"    # Run specific tests
#   ./run-all-tests.sh -v --tb=short       # Pass pytest options
#
# The full profile is used to ensure all services are available.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"

cd "$DOCKER_DIR"

echo "==> Starting test infrastructure (profile: full)..."
# Start services without --wait (init containers exit immediately which causes --wait to fail)
docker compose --profile full up -d

echo "==> Waiting for polaris-init to complete..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    STATUS=$(docker inspect -f "{{.State.Status}}" floe-polaris-init 2>/dev/null || echo "not_found")
    if [[ "$STATUS" == "exited" ]]; then
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
done

if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
    echo "Error: polaris-init did not complete in time" >&2
    docker compose logs polaris-init
    exit 1
fi

EXIT_CODE=$(docker inspect -f "{{.State.ExitCode}}" floe-polaris-init 2>/dev/null || echo "1")
if [[ "$EXIT_CODE" != "0" ]]; then
    echo "Error: polaris-init failed with exit code $EXIT_CODE" >&2
    docker compose logs polaris-init
    exit 1
fi
echo "   polaris-init completed successfully"

echo "==> Loading Polaris credentials..."
if [[ -f "$DOCKER_DIR/config/polaris-credentials.env" ]]; then
    # shellcheck disable=SC1091
    source "$DOCKER_DIR/config/polaris-credentials.env"
    export POLARIS_CLIENT_ID POLARIS_CLIENT_SECRET
    echo "   Credentials loaded (Client ID: $POLARIS_CLIENT_ID)"
else
    echo "Warning: Credentials file not found, using environment defaults" >&2
fi

echo "==> Waiting for full profile services..."

# Wait for Polaris health endpoint
echo "   Waiting for Polaris health..."
MAX_ATTEMPTS=60
ATTEMPT=0
while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    if curl -sf http://localhost:8182/q/health >/dev/null 2>&1; then
        echo "   Polaris is healthy"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
done
if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
    echo "Error: Polaris health check failed" >&2
    exit 1
fi

# Wait for Cube readiness
echo "   Waiting for Cube..."
ATTEMPT=0
while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    if curl -sf http://localhost:4000/readyz >/dev/null 2>&1; then
        echo "   Cube is ready"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
done
if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
    echo "Error: Cube readiness check failed" >&2
    exit 1
fi

# Wait for Marquez
echo "   Waiting for Marquez..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    if curl -sf http://localhost:5002/api/v1/namespaces >/dev/null 2>&1; then
        echo "   Marquez is ready"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
done
if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
    echo "Error: Marquez readiness check failed" >&2
    exit 1
fi

# Wait for cube-init to complete
echo "   Waiting for cube-init..."
MAX_ATTEMPTS=60
ATTEMPT=0
while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    STATUS=$(docker inspect -f "{{.State.Status}}" floe-cube-init 2>/dev/null || echo "not_found")
    if [[ "$STATUS" == "exited" ]]; then
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 2
done
if [[ $ATTEMPT -eq $MAX_ATTEMPTS ]]; then
    echo "Error: cube-init did not complete in time" >&2
    docker compose logs cube-init
    exit 1
fi

EXIT_CODE=$(docker inspect -f "{{.State.ExitCode}}" floe-cube-init 2>/dev/null || echo "1")
if [[ "$EXIT_CODE" != "0" ]]; then
    echo "Error: cube-init failed with exit code $EXIT_CODE" >&2
    docker compose logs cube-init
    exit 1
fi
echo "   cube-init completed successfully"

echo "==> Building test runner..."
docker compose --profile full --profile test build test-runner

# Explicitly list all test directories (glob doesn't expand inside docker run)
TEST_DIRS=(
    "tests/"
    "packages/floe-cli/tests/"
    "packages/floe-core/tests/"
    "packages/floe-cube/tests/"
    "packages/floe-dagster/tests/"
    "packages/floe-dbt/tests/"
    "packages/floe-iceberg/tests/"
    "packages/floe-polaris/tests/"
    "packages/floe-synthetic/tests/"
)

echo "==> Running ALL tests (unit + integration)..."
echo "   Test directories: ${TEST_DIRS[*]}"
docker compose --profile full --profile test run --rm test-runner \
    uv run pytest "${TEST_DIRS[@]}" -v --tb=short -p no:cacheprovider "$@"

echo "==> All tests completed"
