#!/bin/bash
# Run integration tests inside Docker network
#
# This script runs pytest inside a Docker container on the same network as
# the test services (LocalStack, Polaris, etc.), enabling proper hostname
# resolution without requiring /etc/hosts modifications.
#
# Usage:
#   ./run-integration-tests.sh                     # Run storage profile tests
#   ./run-integration-tests.sh --profile full      # Run all tests (includes Cube, Marquez)
#   ./run-integration-tests.sh -k "test_append"    # Run specific tests
#   ./run-integration-tests.sh -v --tb=short       # Pass pytest options
#
# Profiles:
#   storage (default): LocalStack, Polaris, Jaeger - for floe-iceberg, floe-polaris tests
#   full: All services including Cube, Trino, Marquez - for floe-cube, floe-dagster tests
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - No other setup required (zero-config)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"

# Default profile
PROFILE="storage"

# Parse --profile argument
PYTEST_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

cd "$DOCKER_DIR"

echo "==> Starting test infrastructure (profile: $PROFILE)..."
docker compose --profile "$PROFILE" up -d --wait

echo "==> Waiting for polaris-init to complete..."
# Wait for polaris-init to finish (it writes credentials)
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

# Check polaris-init exit code
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

# Wait for full profile services if needed
if [[ "$PROFILE" == "full" ]]; then
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

    # Wait for cube-init to complete (loads test data)
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
    echo "   cube-init completed successfully (test data loaded)"
fi

echo "==> Building test runner..."
docker compose --profile "$PROFILE" --profile test build test-runner

# Determine which test directories to run based on profile
if [[ "$PROFILE" == "full" ]]; then
    TEST_DIRS=(
        "packages/floe-iceberg/tests/integration/"
        "packages/floe-polaris/tests/integration/"
        "packages/floe-cube/tests/integration/"
        "packages/floe-dagster/tests/integration/"
    )
else
    # Storage profile: iceberg and polaris only
    TEST_DIRS=(
        "packages/floe-iceberg/tests/integration/"
        "packages/floe-polaris/tests/integration/"
    )
fi

echo "==> Running integration tests..."
echo "   Test directories: ${TEST_DIRS[*]}"

# Pass through any arguments to pytest
docker compose --profile "$PROFILE" --profile test run --rm test-runner \
    uv run pytest "${TEST_DIRS[@]}" -v --tb=short -p no:cacheprovider "${PYTEST_ARGS[@]}"

echo "==> Integration tests completed"
