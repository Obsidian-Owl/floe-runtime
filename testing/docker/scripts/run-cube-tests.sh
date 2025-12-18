#!/bin/bash
# Run Cube integration tests with full infrastructure
#
# This script starts the full Docker Compose profile (including Cube, Trino,
# and test data) and runs the floe-cube integration tests.
#
# Usage:
#   ./run-cube-tests.sh                     # Run all Cube integration tests
#   ./run-cube-tests.sh -k "test_json"      # Run specific tests
#   ./run-cube-tests.sh -v --tb=short       # Pass pytest options
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - No other setup required (zero-config)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$DOCKER_DIR")")"

cd "$DOCKER_DIR"

echo "==> Starting full test infrastructure (includes Cube, Trino, Polaris)..."
docker compose --profile full up -d

echo "==> Waiting for services to be healthy..."
# Wait for Cube to be ready
echo "    Waiting for Cube..."
timeout 120 sh -c 'until curl -sf http://localhost:4000/readyz >/dev/null 2>&1; do sleep 5; done' || {
    echo "Error: Cube did not become healthy in time" >&2
    docker compose logs cube
    exit 1
}
echo "    Cube is ready"

# Wait for cube-init to complete (loads test data)
echo "==> Waiting for cube-init to complete (loading test data)..."
timeout 300 sh -c 'until docker inspect -f "{{.State.Status}}" floe-cube-init 2>/dev/null | grep -q "exited"; do sleep 5; done' || {
    echo "Error: cube-init did not complete in time" >&2
    docker compose logs cube-init
    exit 1
}

# Check cube-init exit code
EXIT_CODE=$(docker inspect -f "{{.State.ExitCode}}" floe-cube-init 2>/dev/null || echo "1")
if [[ "$EXIT_CODE" != "0" ]]; then
    echo "Error: cube-init failed with exit code $EXIT_CODE" >&2
    docker compose logs cube-init
    exit 1
fi
echo "    Test data loaded successfully"

# Verify Polaris credentials exist
echo "==> Loading Polaris credentials..."
if [[ -f "$DOCKER_DIR/config/polaris-credentials.env" ]]; then
    # shellcheck disable=SC1091
    source "$DOCKER_DIR/config/polaris-credentials.env"
    export POLARIS_CLIENT_ID POLARIS_CLIENT_SECRET
    echo "    Credentials loaded (Client ID: $POLARIS_CLIENT_ID)"
else
    echo "Warning: Credentials file not found, using environment defaults"
fi

echo "==> Running Cube integration tests..."
cd "$PROJECT_ROOT"

# Set environment variables for the tests
export CUBE_API_URL="http://localhost:4000"
export CUBE_API_TOKEN=""  # Dev mode doesn't require auth

# Run the tests
uv run pytest -m integration packages/floe-cube/tests/integration/ "$@"

echo "==> Cube integration tests completed"
