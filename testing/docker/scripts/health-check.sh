#!/bin/bash
# Manual health check for floe-runtime test infrastructure
#
# This script verifies that all services in the test infrastructure are healthy
# and properly configured. Use it to diagnose infrastructure issues before
# running integration tests.
#
# Usage:
#   ./health-check.sh                # Check default (storage) profile
#   ./health-check.sh --profile full # Check all services including Cube
#   ./health-check.sh --verbose      # Show detailed service info
#
# Exit codes:
#   0 - All services healthy
#   1 - One or more services unhealthy or missing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
PROFILE="storage"
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--profile storage|compute|full] [--verbose]"
            echo ""
            echo "Options:"
            echo "  --profile PROFILE  Docker Compose profile to check (default: storage)"
            echo "  --verbose, -v      Show detailed service information"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

cd "$DOCKER_DIR"

echo -e "${BLUE}==> Checking floe-runtime test infrastructure (profile: $PROFILE)${NC}"
echo ""

# Track overall status
FAILED=0

# Function to check if a container is running and healthy
check_container() {
    local name=$1
    local display_name=$2

    if ! docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
        echo -e "  ${RED}✗${NC} ${display_name}: not running"
        return 1
    fi

    local health
    health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || echo "none")
    local status=$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null)

    if [[ "$health" == "healthy" ]]; then
        echo -e "  ${GREEN}✓${NC} ${display_name}: healthy"
        if [[ "$VERBOSE" == "true" ]]; then
            local ports=$(docker port "$name" 2>/dev/null | head -3)
            if [[ -n "$ports" ]]; then
                echo "      Ports: $(echo "$ports" | tr '\n' ' ')"
            fi
        fi
        return 0
    elif [[ "$health" == "none" && "$status" == "running" ]]; then
        echo -e "  ${YELLOW}~${NC} ${display_name}: running (no healthcheck)"
        return 0
    else
        echo -e "  ${RED}✗${NC} ${display_name}: ${health:-$status}"
        return 1
    fi
}

# Function to check an HTTP endpoint
check_endpoint() {
    local url=$1
    local name=$2
    local expected_status=${3:-200}

    local status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

    if [[ "$status" == "$expected_status" ]]; then
        echo -e "  ${GREEN}✓${NC} ${name}: responding (HTTP ${status})"
        return 0
    else
        echo -e "  ${RED}✗${NC} ${name}: HTTP ${status} (expected ${expected_status})"
        return 1
    fi
}

# Function to check if an init container completed successfully
check_init_container() {
    local name=$1
    local display_name=$2

    local status=$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo "not_found")
    local exit_code=$(docker inspect -f '{{.State.ExitCode}}' "$name" 2>/dev/null || echo "unknown")

    if [[ "$status" == "exited" && "$exit_code" == "0" ]]; then
        echo -e "  ${GREEN}✓${NC} ${display_name}: completed successfully"
        return 0
    elif [[ "$status" == "not_found" ]]; then
        echo -e "  ${RED}✗${NC} ${display_name}: not found"
        return 1
    elif [[ "$status" == "running" ]]; then
        echo -e "  ${YELLOW}~${NC} ${display_name}: still running..."
        return 1
    else
        echo -e "  ${RED}✗${NC} ${display_name}: ${status} (exit code: ${exit_code})"
        return 1
    fi
}

# ==============================================================================
# BASE SERVICES (always checked)
# ==============================================================================
echo -e "${BLUE}Base Services:${NC}"

check_container "floe-postgres" "PostgreSQL" || FAILED=1
check_container "floe-jaeger" "Jaeger" || FAILED=1

if [[ "$VERBOSE" == "true" ]]; then
    echo ""
    echo -e "${BLUE}Base Endpoints:${NC}"
    check_endpoint "http://localhost:16686" "Jaeger UI" || FAILED=1
fi

# ==============================================================================
# STORAGE PROFILE
# ==============================================================================
if [[ "$PROFILE" == "storage" || "$PROFILE" == "compute" || "$PROFILE" == "full" ]]; then
    echo ""
    echo -e "${BLUE}Storage Services:${NC}"

    check_container "floe-localstack" "LocalStack" || FAILED=1
    check_container "floe-polaris" "Polaris" || FAILED=1
    check_init_container "floe-localstack-init" "LocalStack Init" || FAILED=1
    check_init_container "floe-polaris-init" "Polaris Init" || FAILED=1

    echo ""
    echo -e "${BLUE}Storage Endpoints:${NC}"
    check_endpoint "http://localhost:4566/_localstack/health" "LocalStack Health" || FAILED=1
    # Polaris REST API returns 401 without auth - that's expected (service is running)
    check_endpoint "http://localhost:8182/q/health" "Polaris Health" || FAILED=1

    # Check Polaris credentials file exists
    if [[ -f "$DOCKER_DIR/config/polaris-credentials.env" ]]; then
        echo -e "  ${GREEN}✓${NC} Polaris credentials: found"
        if [[ "$VERBOSE" == "true" ]]; then
            source "$DOCKER_DIR/config/polaris-credentials.env"
            echo "      Client ID: ${POLARIS_CLIENT_ID:-not set}"
        fi
    else
        echo -e "  ${RED}✗${NC} Polaris credentials: not found (run polaris-init first)"
        FAILED=1
    fi
fi

# ==============================================================================
# COMPUTE PROFILE
# ==============================================================================
if [[ "$PROFILE" == "compute" || "$PROFILE" == "full" ]]; then
    echo ""
    echo -e "${BLUE}Compute Services:${NC}"

    check_container "floe-trino" "Trino" || FAILED=1
    check_container "floe-spark" "Spark" || FAILED=1

    echo ""
    echo -e "${BLUE}Compute Endpoints:${NC}"
    check_endpoint "http://localhost:8080/v1/info" "Trino REST API" || FAILED=1

    # Verify Trino can query Iceberg catalog
    if [[ "$VERBOSE" == "true" ]]; then
        echo ""
        echo -e "${BLUE}Trino Iceberg Connectivity:${NC}"
        if docker exec floe-trino trino --execute "SHOW SCHEMAS FROM iceberg" >/dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} Trino Iceberg catalog: accessible"
        else
            echo -e "  ${RED}✗${NC} Trino Iceberg catalog: not accessible"
            FAILED=1
        fi
    fi
fi

# ==============================================================================
# FULL PROFILE
# ==============================================================================
if [[ "$PROFILE" == "full" || "$PROFILE" == "demo" ]]; then
    echo ""
    echo -e "${BLUE}Full Profile Services:${NC}"

    check_container "floe-cube" "Cube" || FAILED=1
    check_container "floe-marquez" "Marquez" || FAILED=1
    check_container "floe-marquez-web" "Marquez Web" || FAILED=1

    echo ""
    echo -e "${BLUE}Full Profile Endpoints:${NC}"
    check_endpoint "http://localhost:4000/readyz" "Cube REST API" || FAILED=1
    check_endpoint "http://localhost:5001/healthcheck" "Marquez Admin" || FAILED=1
    check_endpoint "http://localhost:3001" "Marquez Web UI" || FAILED=1

    # Verify Cube can query data
    if [[ "$VERBOSE" == "true" ]]; then
        echo ""
        echo -e "${BLUE}Cube Data Connectivity:${NC}"
        # Simple meta query to verify Cube is configured
        cube_response=$(curl -s "http://localhost:4000/cubejs-api/v1/meta" 2>/dev/null)
        if echo "$cube_response" | grep -q "cubes"; then
            echo -e "  ${GREEN}✓${NC} Cube schema: loaded"
        else
            echo -e "  ${YELLOW}~${NC} Cube schema: may need cube-init"
        fi
    fi
fi

# ==============================================================================
# DEMO PROFILE
# ==============================================================================
if [[ "$PROFILE" == "demo" ]]; then
    echo ""
    echo -e "${BLUE}Demo Profile Services:${NC}"

    check_container "floe-dagster-webserver" "Dagster Webserver" || FAILED=1
    check_container "floe-dagster-daemon" "Dagster Daemon" || FAILED=1

    echo ""
    echo -e "${BLUE}Demo Profile Endpoints:${NC}"
    check_endpoint "http://localhost:3000/health" "Dagster UI" || FAILED=1

    # Verify Dagster can load definitions
    if [[ "$VERBOSE" == "true" ]]; then
        echo ""
        echo -e "${BLUE}Dagster Connectivity:${NC}"
        dagster_response=$(curl -s "http://localhost:3000/graphql" \
            -H "Content-Type: application/json" \
            -d '{"query": "{ repositoriesOrError { ... on RepositoryConnection { nodes { name } } } }"}' 2>/dev/null)
        if echo "$dagster_response" | grep -q "nodes"; then
            echo -e "  ${GREEN}✓${NC} Dagster definitions: loaded"
        else
            echo -e "  ${YELLOW}~${NC} Dagster definitions: may be loading"
        fi
    fi
fi

# ==============================================================================
# SUMMARY
# ==============================================================================
echo ""
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}==> All services healthy!${NC}"
    exit 0
else
    echo -e "${RED}==> Some services are unhealthy. Check the output above.${NC}"
    echo ""
    echo "Troubleshooting tips:"
    echo "  - Start services: cd testing/docker && docker compose --profile $PROFILE up -d"
    echo "  - View logs: docker compose logs <service-name>"
    echo "  - Restart unhealthy service: docker compose restart <service-name>"
    exit 1
fi
