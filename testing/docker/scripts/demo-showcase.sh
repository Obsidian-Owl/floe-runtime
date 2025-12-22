#!/bin/bash
# demo-showcase.sh - Interactive demonstration of floe-runtime capabilities
#
# This script showcases all aspects of the floe-runtime demo:
# - Service health verification
# - Web UI access
# - Cube REST/GraphQL/SQL API examples
# - Dagster orchestration status
# - Marquez lineage
# - Jaeger tracing
#
# Usage:
#   ./demo-showcase.sh              # Run full showcase (prints URLs)
#   ./demo-showcase.sh --open       # Auto-open browser tabs for UIs
#   ./demo-showcase.sh --section ui # Show UI URLs only
#   ./demo-showcase.sh --section api # Demo API calls
#   ./demo-showcase.sh --section data # Show data counts
#   ./demo-showcase.sh --interactive # Pause between sections
#   ./demo-showcase.sh --help       # Show this help
#
# Requirements:
#   - Docker Compose demo profile running
#   - curl and jq installed
#
# Covers: 007-FR-029 (E2E validation tests)
# Covers: 007-FR-031 (Medallion architecture demo)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default options
OPEN_BROWSER=false
INTERACTIVE=false
SECTION="all"

# Service URLs
DAGSTER_URL="http://localhost:3000"
CUBE_URL="http://localhost:4000"
JAEGER_URL="http://localhost:16686"
MARQUEZ_URL="http://localhost:3001"
MARQUEZ_API_URL="http://localhost:5002"
TRINO_URL="http://localhost:8080"
POLARIS_URL="http://localhost:8181"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --open|-o)
            OPEN_BROWSER=true
            shift
            ;;
        --interactive|-i)
            INTERACTIVE=true
            shift
            ;;
        --section|-s)
            SECTION="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --open, -o         Auto-open browser tabs for UIs"
            echo "  --interactive, -i  Pause between sections"
            echo "  --section, -s SEC  Run specific section: ui, api, data, all"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Sections:"
            echo "  ui     - Show UI URLs and optionally open browsers"
            echo "  api    - Demo Cube REST, GraphQL, SQL APIs"
            echo "  data   - Show data counts from Cube"
            echo "  all    - Run all sections (default)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Helper functions
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_subheader() {
    echo ""
    echo -e "${CYAN}▸ $1${NC}"
    echo ""
}

print_success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "  ${RED}✗${NC} $1"
}

print_info() {
    echo -e "  ${YELLOW}→${NC} $1"
}

print_url() {
    echo -e "  ${BOLD}$1${NC}: ${CYAN}$2${NC}"
}

pause_if_interactive() {
    if [[ "$INTERACTIVE" == "true" ]]; then
        echo ""
        echo -e "${YELLOW}Press Enter to continue...${NC}"
        read -r
    fi
}

open_url() {
    local url=$1
    if [[ "$OPEN_BROWSER" == "true" ]]; then
        if command -v open &> /dev/null; then
            open "$url" 2>/dev/null || true
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$url" 2>/dev/null || true
        fi
    fi
}

check_service() {
    local url=$1
    local name=$2
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [[ "$status" == "200" ]]; then
        print_success "$name: responding (HTTP $status)"
        return 0
    else
        print_error "$name: HTTP $status"
        return 1
    fi
}

# ==============================================================================
# SECTION: Services Check
# ==============================================================================
section_services() {
    print_header "Service Health Check"

    local failed=0

    print_subheader "Core Services"
    check_service "$DAGSTER_URL/health" "Dagster UI" || failed=1
    check_service "$CUBE_URL/readyz" "Cube API" || failed=1
    check_service "$JAEGER_URL/api/services" "Jaeger" || failed=1
    check_service "$MARQUEZ_API_URL/api/v1/namespaces" "Marquez API" || failed=1
    check_service "$TRINO_URL/v1/info" "Trino" || failed=1

    if [[ $failed -eq 0 ]]; then
        echo ""
        print_success "All services healthy!"
    else
        echo ""
        print_error "Some services are not responding. Run: docker compose --profile demo up -d"
        exit 1
    fi

    pause_if_interactive
}

# ==============================================================================
# SECTION: UI Gallery
# ==============================================================================
section_ui() {
    print_header "Web UI Gallery"

    print_subheader "Available Interfaces"
    print_url "Dagster UI" "$DAGSTER_URL"
    echo "      Asset orchestration, job runs, schedules"
    echo ""
    print_url "Cube Playground" "$CUBE_URL"
    echo "      Visual query builder, schema explorer"
    echo ""
    print_url "Jaeger UI" "$JAEGER_URL"
    echo "      Distributed tracing, latency analysis"
    echo ""
    print_url "Marquez Web" "$MARQUEZ_URL"
    echo "      Data lineage graphs, job history"
    echo ""
    print_url "Trino UI" "$TRINO_URL"
    echo "      SQL console, query history"

    if [[ "$OPEN_BROWSER" == "true" ]]; then
        echo ""
        print_info "Opening browser tabs..."
        open_url "$DAGSTER_URL"
        sleep 0.5
        open_url "$CUBE_URL"
        sleep 0.5
        open_url "$JAEGER_URL"
        sleep 0.5
        open_url "$MARQUEZ_URL"
    fi

    pause_if_interactive
}

# ==============================================================================
# SECTION: Cube REST API Demo
# ==============================================================================
section_cube_rest() {
    print_header "Cube REST API Demo"

    print_subheader "Query: Total Orders and Revenue"
    echo -e "  ${YELLOW}curl -s $CUBE_URL/cubejs-api/v1/load -d '{\"query\": {\"measures\": [\"Orders.count\", \"Orders.totalAmount\"]}}'${NC}"
    echo ""

    local response
    response=$(curl -s "$CUBE_URL/cubejs-api/v1/load" \
        -H "Content-Type: application/json" \
        -d '{"query": {"measures": ["Orders.count", "Orders.totalAmount"]}}' 2>/dev/null || echo '{"error": "Failed to connect"}')

    if echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        echo -e "  ${GREEN}Response:${NC}"
        echo "$response" | jq -C '.data' 2>/dev/null || echo "$response"
    else
        print_error "Query failed. Is Cube running?"
        echo "$response" | jq -C 2>/dev/null || echo "$response"
    fi

    pause_if_interactive

    print_subheader "Query: Orders by Status"
    echo -e "  ${YELLOW}curl -s $CUBE_URL/cubejs-api/v1/load -d '{\"query\": {\"measures\": [\"Orders.count\"], \"dimensions\": [\"Orders.status\"]}}'${NC}"
    echo ""

    response=$(curl -s "$CUBE_URL/cubejs-api/v1/load" \
        -H "Content-Type: application/json" \
        -d '{"query": {"measures": ["Orders.count"], "dimensions": ["Orders.status"]}}' 2>/dev/null || echo '{"error": "Failed"}')

    if echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        echo -e "  ${GREEN}Response:${NC}"
        echo "$response" | jq -C '.data' 2>/dev/null || echo "$response"
    fi

    pause_if_interactive
}

# ==============================================================================
# SECTION: Cube GraphQL API Demo
# ==============================================================================
section_cube_graphql() {
    print_header "Cube GraphQL API Demo"

    print_subheader "Query: Customer Segments"
    local query='{ cube(measures: ["Customers.count"], dimensions: ["Customers.segment"]) { Customers { count segment } } }'
    echo -e "  ${YELLOW}GraphQL Query:${NC}"
    echo "    $query"
    echo ""

    local response
    response=$(curl -s "$CUBE_URL/cubejs-api/graphql" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" 2>/dev/null || echo '{"error": "Failed"}')

    if echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        echo -e "  ${GREEN}Response:${NC}"
        echo "$response" | jq -C '.data.cube' 2>/dev/null || echo "$response"
    else
        print_error "GraphQL query failed"
        echo "$response" | jq -C 2>/dev/null || echo "$response"
    fi

    pause_if_interactive
}

# ==============================================================================
# SECTION: Cube SQL API Demo
# ==============================================================================
section_cube_sql() {
    print_header "Cube SQL API Demo (Postgres Wire Protocol)"

    print_subheader "Connection Info"
    echo "  Host: localhost"
    echo "  Port: 15432"
    echo "  User: cube"
    echo "  Password: cube"
    echo "  Database: cube"
    echo ""

    print_subheader "Python Example (psycopg2)"
    echo -e "${YELLOW}"
    cat << 'EOF'
    import psycopg2
    conn = psycopg2.connect(
        host='localhost',
        port=15432,
        user='cube',
        password='cube',
        database='cube'
    )
    cur = conn.cursor()
    cur.execute('SELECT MEASURE(count) FROM Orders')
    print(cur.fetchone())
EOF
    echo -e "${NC}"

    print_subheader "psql Example"
    echo -e "  ${YELLOW}PGPASSWORD=cube psql -h localhost -p 15432 -U cube -d cube -c \"SELECT MEASURE(count) FROM Orders\"${NC}"

    # Try to execute if psql is available
    if command -v psql &> /dev/null; then
        echo ""
        print_info "Executing query..."
        PGPASSWORD=cube psql -h localhost -p 15432 -U cube -d cube -c "SELECT MEASURE(count) FROM Orders" 2>/dev/null || \
            print_error "Could not connect to Cube SQL API"
    fi

    pause_if_interactive
}

# ==============================================================================
# SECTION: Data Overview
# ==============================================================================
section_data() {
    print_header "Data Overview"

    print_subheader "Orders Summary"
    local orders
    orders=$(curl -s "$CUBE_URL/cubejs-api/v1/load" \
        -H "Content-Type: application/json" \
        -d '{"query": {"measures": ["Orders.count", "Orders.totalAmount", "Orders.averageOrderValue"]}}' 2>/dev/null)

    if echo "$orders" | jq -e '.data[0]' > /dev/null 2>&1; then
        local count total_amount avg
        count=$(echo "$orders" | jq -r '.data[0]["Orders.count"] // "N/A"')
        total_amount=$(echo "$orders" | jq -r '.data[0]["Orders.totalAmount"] // "N/A"')
        avg=$(echo "$orders" | jq -r '.data[0]["Orders.averageOrderValue"] // "N/A"')
        echo "  Total Orders:       $count"
        echo "  Total Revenue:      \$$total_amount"
        echo "  Avg Order Value:    \$$avg"
    else
        print_error "Could not fetch orders data"
    fi

    print_subheader "Customer Segments"
    local customers
    customers=$(curl -s "$CUBE_URL/cubejs-api/v1/load" \
        -H "Content-Type: application/json" \
        -d '{"query": {"measures": ["Customers.count"], "dimensions": ["Customers.segment"]}}' 2>/dev/null)

    if echo "$customers" | jq -e '.data' > /dev/null 2>&1; then
        echo "$customers" | jq -r '.data[] | "  \(.["Customers.segment"] // "unknown"): \(.["Customers.count"])"' 2>/dev/null
    fi

    print_subheader "Product Categories"
    local products
    products=$(curl -s "$CUBE_URL/cubejs-api/v1/load" \
        -H "Content-Type: application/json" \
        -d '{"query": {"measures": ["Products.count", "Products.totalRevenue"], "dimensions": ["Products.category"]}}' 2>/dev/null)

    if echo "$products" | jq -e '.data' > /dev/null 2>&1; then
        echo "$products" | jq -r '.data[] | "  \(.["Products.category"] // "unknown"): \(.["Products.count"]) products, $\(.["Products.totalRevenue"]) revenue"' 2>/dev/null
    fi

    pause_if_interactive
}

# ==============================================================================
# SECTION: Marquez Lineage
# ==============================================================================
section_lineage() {
    print_header "Marquez Data Lineage"

    print_subheader "Available Namespaces"
    local namespaces
    namespaces=$(curl -s "$MARQUEZ_API_URL/api/v1/namespaces" 2>/dev/null)

    if echo "$namespaces" | jq -e '.namespaces' > /dev/null 2>&1; then
        echo "$namespaces" | jq -r '.namespaces[] | "  - \(.name)"' 2>/dev/null || echo "  (no namespaces found)"
    else
        print_info "No lineage data yet. Run the pipeline to generate lineage events."
    fi

    print_subheader "Lineage UI"
    print_url "Marquez Web" "$MARQUEZ_URL"
    echo "      View data flow graphs and job history"

    if [[ "$OPEN_BROWSER" == "true" ]]; then
        open_url "$MARQUEZ_URL"
    fi

    pause_if_interactive
}

# ==============================================================================
# SECTION: Jaeger Tracing
# ==============================================================================
section_tracing() {
    print_header "Jaeger Distributed Tracing"

    print_subheader "Available Services"
    local services
    services=$(curl -s "$JAEGER_URL/api/services" 2>/dev/null)

    if echo "$services" | jq -e '.data' > /dev/null 2>&1; then
        echo "$services" | jq -r '.data[] | "  - \(.)"' 2>/dev/null || echo "  (no services traced yet)"
    else
        print_info "No traces yet. Run the pipeline to generate traces."
    fi

    print_subheader "Tracing UI"
    print_url "Jaeger UI" "$JAEGER_URL"
    echo "      Search traces, analyze latency, view service dependencies"

    if [[ "$OPEN_BROWSER" == "true" ]]; then
        open_url "$JAEGER_URL"
    fi

    pause_if_interactive
}

# ==============================================================================
# SECTION: Dagster Status
# ==============================================================================
section_dagster() {
    print_header "Dagster Orchestration"

    print_subheader "Dagster UI"
    print_url "Dagster UI" "$DAGSTER_URL"
    echo "      Assets: synthetic_data, dbt_transformations, cube_preaggregations"
    echo "      Jobs: demo_pipeline_job, dbt_refresh_job"
    echo "      Schedules: demo_hourly_schedule, demo_daily_schedule"

    print_subheader "Trigger a Pipeline Run"
    echo "  Option 1: Use the Dagster UI"
    echo "    1. Go to $DAGSTER_URL"
    echo "    2. Click 'Assets' in sidebar"
    echo "    3. Select assets to materialize"
    echo "    4. Click 'Materialize'"
    echo ""
    echo "  Option 2: Use the API trigger sensor"
    echo "    touch /tmp/demo_trigger"
    echo "    # The sensor will detect this and start a run"

    if [[ "$OPEN_BROWSER" == "true" ]]; then
        open_url "$DAGSTER_URL"
    fi

    pause_if_interactive
}

# ==============================================================================
# MAIN
# ==============================================================================

print_header "floe-runtime Demo Showcase"
echo "  This demo showcases the complete floe-runtime data stack:"
echo "  - Dagster orchestration with dbt transformations"
echo "  - Cube semantic layer (REST, GraphQL, SQL APIs)"
echo "  - Iceberg tables via Polaris catalog"
echo "  - Observability with Jaeger and Marquez"

case "$SECTION" in
    ui)
        section_services
        section_ui
        ;;
    api)
        section_services
        section_cube_rest
        section_cube_graphql
        section_cube_sql
        ;;
    data)
        section_services
        section_data
        ;;
    all)
        section_services
        section_ui
        section_cube_rest
        section_cube_graphql
        section_cube_sql
        section_data
        section_dagster
        section_lineage
        section_tracing
        ;;
    *)
        echo "Unknown section: $SECTION" >&2
        echo "Valid sections: ui, api, data, all" >&2
        exit 1
        ;;
esac

print_header "Demo Complete!"
echo "  For more information, see:"
echo "    - docs/demo-quickstart.md"
echo "    - docs/api-examples.md"
echo "    - testing/docker/README.md"
echo ""
