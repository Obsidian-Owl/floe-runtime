# Demo Quickstart Guide

Run the floe-runtime demo e-commerce pipeline in 5 minutes.

---

## Prerequisites

- Docker Desktop with 8GB+ RAM allocated
- Docker Compose v2.x
- `curl` and `jq` for API testing (optional)

---

## Quick Start

```bash
# Navigate to testing directory
cd testing/docker

# Start the complete demo stack
docker compose --profile demo up -d

# Wait for initialization (~2-3 minutes on first run)
# Check service health
./scripts/health-check.sh --profile demo
```

---

## What Gets Started

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Dagster UI** | 3000 | http://localhost:3000 | Asset orchestration, run monitoring |
| **Cube Playground** | 4000 | http://localhost:4000 | Visual query builder, semantic layer |
| **Jaeger UI** | 16686 | http://localhost:16686 | Distributed tracing |
| **Marquez Web** | 3001 | http://localhost:3001 | Data lineage visualization |
| **Trino UI** | 8080 | http://localhost:8080 | SQL query console |
| PostgreSQL | 5432 | - | Metadata storage |
| LocalStack | 4566 | - | S3/STS emulation |
| Polaris | 8181 | - | Iceberg catalog |

---

## Demo Pipeline Overview

The demo showcases a complete e-commerce analytics pipeline:

```
Synthetic Data (floe-synthetic)
    │
    ├─► raw.customers   ─┐
    ├─► raw.orders       │  Bronze Layer (Iceberg tables)
    ├─► raw.products     │
    └─► raw.order_items ─┘
           │
           ▼
    dbt Transformations (via Trino)
           │
    ├─► staging.stg_*        Silver Layer (views)
    ├─► intermediate.int_*   Gold Layer (tables)
    └─► marts.mart_*         Analytics (tables)
           │
           ▼
    Cube Semantic Layer
           │
    ├─► Orders cube      ─┐
    ├─► Customers cube    │  REST / GraphQL / SQL APIs
    └─► Products cube    ─┘
```

### Data Models

| Layer | Models | Description |
|-------|--------|-------------|
| **Staging** | stg_customers, stg_orders, stg_products, stg_order_items | Cleaned source data |
| **Intermediate** | int_customer_orders, int_order_items_enriched, int_product_performance | Business logic |
| **Marts** | mart_revenue, mart_customer_segments, mart_product_analytics | Analytics-ready |

### Cube Semantic Models

| Cube | Source | Measures | Key Dimensions |
|------|--------|----------|----------------|
| **Orders** | mart_revenue | count, totalAmount, averageOrderValue | orderDate |
| **Customers** | mart_customer_segments | count, totalRevenue, averageOrderValue | segment, churnRisk |
| **Products** | mart_product_analytics | count, totalRevenue, totalUnitsSold | category, performanceTier |

---

## Verify Services

### Option 1: Health Check Script

```bash
./scripts/health-check.sh --profile demo --verbose
```

Expected output:
```
==> Checking floe-runtime test infrastructure (profile: demo)

Base Services:
  ✓ PostgreSQL: healthy
  ✓ Jaeger: healthy

Storage Services:
  ✓ LocalStack: healthy
  ✓ Polaris: healthy
  ✓ LocalStack Init: completed successfully
  ✓ Polaris Init: completed successfully

...

Demo Services:
  ✓ Dagster Webserver: healthy
  ✓ Dagster Daemon: running

==> All services healthy!
```

### Option 2: Manual Checks

```bash
# Dagster UI
curl -s http://localhost:3000/health | jq

# Cube API
curl -s http://localhost:4000/readyz

# Jaeger
curl -s http://localhost:16686/api/services | jq

# Marquez
curl -s http://localhost:5002/api/v1/namespaces | jq
```

---

## Showcase the Demo

Run the interactive demo showcase:

```bash
./scripts/demo-showcase.sh

# Or with browser auto-open
./scripts/demo-showcase.sh --open

# Interactive mode (pause between sections)
./scripts/demo-showcase.sh --interactive
```

---

## Explore the UIs

### 1. Dagster UI (http://localhost:3000)

The orchestration layer showing:
- **Assets**: synthetic_data, dbt_transformations, cube_preaggregations
- **Jobs**: demo_pipeline_job, dbt_refresh_job
- **Schedules**: demo_hourly_schedule, demo_daily_schedule
- **Sensors**: file_arrival_sensor, api_trigger_sensor

**Try**: Click on "Assets" → View the dependency graph

### 2. Cube Playground (http://localhost:4000)

Visual query builder for the semantic layer:
- Select measures (Orders.count, Customers.totalRevenue)
- Add dimensions (Orders.orderDate, Customers.segment)
- Run queries and see results

**Try**: Build a query showing revenue by customer segment

### 3. Jaeger UI (http://localhost:16686)

Distributed tracing for pipeline runs:
- Service: floe-runtime
- View trace timelines
- Analyze latency

### 4. Marquez Web (http://localhost:3001)

Data lineage visualization:
- View job runs
- Trace data flow between datasets
- Explore namespaces

### 5. Trino UI (http://localhost:8080)

SQL query console:
- Query Iceberg tables directly
- View query history
- Monitor cluster status

**Try**: Run `SHOW SCHEMAS FROM iceberg`

---

## Query the APIs

### Cube REST API

```bash
# Get total order count
curl -s http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Orders.count", "Orders.totalAmount"]
    }
  }' | jq
```

### Cube GraphQL API

```bash
curl -s http://localhost:4000/cubejs-api/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ cube(measures: [\"Customers.count\"], dimensions: [\"Customers.segment\"]) { Customers { count segment } } }"
  }' | jq
```

### Cube SQL API (Postgres Wire Protocol)

```bash
# Using psql
PGPASSWORD=cube psql -h localhost -p 15432 -U cube -d cube \
  -c "SELECT MEASURE(count) FROM Orders"

# Using Python
python -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=15432, user='cube', password='cube', database='cube')
cur = conn.cursor()
cur.execute('SELECT MEASURE(count) FROM Orders')
print(cur.fetchone())
"
```

---

## Trigger Pipeline Runs

### Via Dagster UI

1. Go to http://localhost:3000
2. Click "Assets" in sidebar
3. Select assets to materialize
4. Click "Materialize"

### Via API Trigger Sensor

```bash
# Create trigger file
touch /tmp/demo_trigger

# The api_trigger_sensor will detect this and start a run
# Check Dagster UI for the new run
```

### Via Dagster GraphQL

```bash
curl -s http://localhost:3000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { launchRun(executionParams: { selector: { repositoryLocationName: \"demo.orchestration\", repositoryName: \"__repository__\", pipelineName: \"demo_pipeline_job\" } }) { ... on LaunchRunSuccess { run { runId } } } }"
  }' | jq
```

---

## Stop the Demo

```bash
# Stop all services
docker compose --profile demo down

# Stop and remove volumes (full cleanup)
docker compose --profile demo down -v
```

---

## Troubleshooting

### Services Won't Start

```bash
# Check Docker resource allocation (needs 8GB+ RAM)
docker system info | grep Memory

# Check for port conflicts
lsof -i :3000  # Dagster
lsof -i :4000  # Cube
lsof -i :8080  # Trino
```

### Polaris Init Fails

```bash
# Check polaris-init logs
docker logs floe-polaris-init

# Restart polaris-init
docker compose restart polaris-init
```

### Cube Shows No Data

```bash
# Check if Cube can connect to Trino
docker logs floe-cube | grep -i error

# Verify Trino has data
docker exec floe-trino trino --execute "SHOW SCHEMAS FROM iceberg"

# Re-run cube-init
docker compose restart cube-init
```

### Dagster Can't Find Modules

```bash
# Check Dagster logs
docker logs floe-dagster-webserver

# Verify module path
docker exec floe-dagster-webserver python -c "import demo.orchestration"
```

---

## Understanding the Demo Environment

### Why Jaeger Shows No Traces

The demo assets are **placeholder implementations** that return mock data. They don't execute real operations (dbt runs, API calls) and therefore don't generate traces.

```python
# Current demo asset (placeholder - no spans created)
def synthetic_data() -> dict[str, int]:
    return {"customers": 100, "products": 50, ...}
```

**The tracing infrastructure is fully implemented** in `floe-dagster`:
- `TracingManager` with OpenTelemetry integration
- OTLP exporter configured for Jaeger
- Span creation, attributes, and error recording

**To see traces**: Use the full `FloeAssetFactory` which automatically instruments assets, or manually add `TracingManager.start_span()` calls.

### Why Marquez Shows No Lineage

OpenLineage emission is **disabled in the demo configuration** and demo assets don't emit lineage events.

**The lineage infrastructure is fully implemented** in `floe-dagster`:
- `OpenLineageEmitter` with START/COMPLETE/FAIL lifecycle
- Dataset tracking (inputs/outputs)
- Integration with `FloeAssetFactory`

**To see lineage**: Enable `lineage.enabled: true` in configuration and use assets that emit OpenLineage events.

### DuckDB vs Trino

The architecture supports **both compute engines** for different use cases:

| Engine | Use Case | Admin UI |
|--------|----------|----------|
| **DuckDB** | Local development, embedded | None (use DBeaver, VS Code SQLTools) |
| **Trino** | Integration testing with Iceberg/Polaris | http://localhost:8080 |

- **DuckDB** is the default compute target for local development (fast, zero-config)
- **Trino** is used in Docker Compose for integration testing (Iceberg table operations, OAuth2 with Polaris)
- Both are valid - the architecture is target-agnostic

See `docs/03-solution-strategy.md` for the "Target agnostic" design principle.

### Cube Pre-Aggregation Warning

The warning "consider using external pre-aggregation" is **expected and correct** for this demo environment.

| Setting | Environment | Storage Location |
|---------|-------------|------------------|
| `external: false` | Dev/Testing | Source database (Trino) |
| `external: true` | Production | Cube Store + S3/GCS |

**Current configuration is intentional**:
- No cloud storage dependency (S3/GCS not required)
- Pre-aggregations stored in Trino tables
- Sufficient for single-user development
- Warning is informational, not an error

**For production**: Enable `external: true` with Cube Store and S3 bucket configuration. See `docs/adr/0001-cube-semantic-layer.md` for details.

---

## Next Steps

- See [docs/api-examples.md](api-examples.md) for comprehensive API reference
- See [testing/docker/README.md](../testing/docker/README.md) for infrastructure details
- See [docs/06-deployment-view.md](06-deployment-view.md) for production deployment
