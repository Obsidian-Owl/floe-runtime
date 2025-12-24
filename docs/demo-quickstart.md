# Demo Quickstart Guide

Run the floe-runtime demo e-commerce pipeline in 5 minutes.

**Two deployment options:**
- **[Kubernetes (Recommended)](#kubernetes-deployment)** - Production-like deployment on Docker Desktop K8s
- **[Docker Compose](#docker-compose-deployment)** - Simpler, all-in-one development stack

---

# Kubernetes Deployment

Production-like deployment using Helm charts on Docker Desktop Kubernetes.

## Prerequisites

- Docker Desktop with **Kubernetes enabled** (Settings → Kubernetes → Enable)
- 8GB+ RAM allocated to Docker Desktop
- `kubectl` configured (`kubectl cluster-info` works)
- `helm` v3.x installed
- `curl` and `jq` for API testing (optional)
- `psql` for SQL API testing (optional)

## Quick Start

```bash
# One command deploys the complete stack
make deploy-local-full

# Wait ~3-5 minutes for initialization
# Check pod status
make demo-status
```

That's it! All services are now accessible via NodePort.

## Service URLs (NodePort Access)

These URLs are **resilient** - they survive pod restarts without needing port-forward:

| Service | URL | Purpose |
|---------|-----|---------|
| **Dagster UI** | http://localhost:30000 | Asset orchestration, run monitoring |
| **Cube REST API** | http://localhost:30400 | Semantic layer queries |
| **Cube SQL API** | `psql -h localhost -p 30432 -U cube` | Postgres wire protocol |
| **Marquez UI** | http://localhost:30301 | Data lineage visualization |
| **Jaeger UI** | http://localhost:30686 | Distributed tracing |
| **MinIO Console** | http://localhost:30901 | S3 storage (user: `minioadmin`) |
| **Polaris API** | http://localhost:30181 | Iceberg catalog |
| **LocalStack** | http://localhost:30566 | S3/STS emulation |

## Verify Deployment

```bash
# Check all pods are Running
kubectl get pods -n floe

# Quick API test
curl -s http://localhost:30400/cubejs-api/v1/meta | jq '.cubes[].name'
# Expected: "Orders", "Customers"

# Dagster health
curl -s http://localhost:30000/server_info | jq
```

## Query the Cube APIs (Kubernetes)

### REST API

```bash
# Get order count and total amount
curl -s http://localhost:30400/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Orders.count", "Orders.totalAmount"]
    }
  }' | jq '.data'
```

### GraphQL API

```bash
curl -s http://localhost:30400/cubejs-api/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ cube(measures: [\"Orders.count\"], dimensions: [\"Orders.status\"]) { Orders { count status } } }"
  }' | jq '.data.cube'
```

### SQL API (Postgres Wire Protocol)

```bash
# Using psql (password: cube_password)
PGPASSWORD=cube_password psql -h localhost -p 30432 -U cube -d cube \
  -c "SELECT status, MEASURE(count) as order_count FROM Orders GROUP BY 1"

# Using Python
python3 -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=30432, user='cube', password='cube_password', database='cube')
cur = conn.cursor()
cur.execute('SELECT MEASURE(count), MEASURE(totalAmount) FROM Orders')
print(cur.fetchone())
"
```

## Cleanup

```bash
# Clean up completed Dagster run pods (accumulate over time)
make demo-cleanup

# Remove all deployments
make undeploy-local

# Or delete the entire namespace
kubectl delete namespace floe
```

## Troubleshooting (Kubernetes)

### Pod Not Starting

```bash
# Check pod status and events
kubectl describe pod <pod-name> -n floe

# Check logs (last 50 lines)
kubectl logs <pod-name> -n floe --tail=50
```

### Cube Connection Issues

```bash
# Check Cube API logs
kubectl logs -l app.kubernetes.io/component=api -n floe --tail=30

# Verify S3 connectivity
kubectl exec -it deploy/floe-cube-api -n floe -- env | grep S3
```

### Dagster Issues

```bash
# Check webserver logs
kubectl logs -l component=dagster-webserver -n floe --tail=30

# Check daemon logs
kubectl logs -l component=dagster-daemon -n floe --tail=30
```

---

# Docker Compose Deployment

Simpler development stack using Docker Compose.

## Prerequisites

- Docker Desktop with 8GB+ RAM allocated
- Docker Compose v2.x
- `curl` and `jq` for API testing (optional)

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
| **Cube SQL API** | 15432 | - | Postgres wire protocol for BI tools |
| **Jaeger UI** | 16686 | http://localhost:16686 | Distributed tracing |
| **Marquez Web** | 3001 | http://localhost:3001 | Data lineage visualization |
| **Trino UI** | 8080 | http://localhost:8080 | SQL query console |
| Cube Store Router | 10000 | - | Pre-aggregation compute |
| Cube Store Workers | 10001-10002 | - | Distributed query workers |
| PostgreSQL | 5432 | - | Metadata storage |
| LocalStack | 4566 | - | S3/STS emulation |
| Polaris | 8181 | - | Iceberg catalog

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
| **Orders** | bronze_orders | count, totalAmount, averageAmount | status, region, createdAt |
| **Customers** | bronze_customers | count, totalOrders, totalRevenue | region, createdAt |

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
- **Assets**: `bronze_customers`, `bronze_orders`, `bronze_products`, `bronze_order_items`
- **Groups**: `bronze` (data generation), `transform` (dbt placeholder)
- **Jobs**: `demo_pipeline_job` (runs all bronze assets)
- **Schedules**: `demo_hourly_schedule` (configurable)
- **Sensors**: `file_trigger_sensor` (watches for trigger files)

**Try**: Click on "Assets" → View the dependency graph → Materialize all

### 2. Cube Playground (http://localhost:4000)

Visual query builder for the semantic layer:
- Select measures (`Orders.count`, `Orders.totalAmount`, `Orders.averageAmount`)
- Add dimensions (`Orders.status`, `Orders.region`, `Customers.region`)
- Run queries and see results

**Try**: Build a query showing order count and total amount by status

### 3. Jaeger UI (http://localhost:16686)

Distributed tracing for pipeline runs:
- **Service**: `floe-demo` - select from dropdown
- **Traces**: Each asset materialization creates spans
- **Attributes**: View rows written, snapshot IDs, timing

**Try**: Materialize assets in Dagster, then find traces by service `floe-demo`

### 4. Marquez Web (http://localhost:3001)

Data lineage visualization:
- **Namespace**: `demo` - all demo jobs are here
- **Jobs**: `bronze_customers`, `bronze_orders`, `bronze_products`, `bronze_order_items`
- **Datasets**: Iceberg table inputs/outputs

**Try**: View the lineage graph showing data flow between bronze tables

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
    "query": "{ cube(measures: [\"Customers.count\"], dimensions: [\"Customers.region\"]) { Customers { count region } } }"
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

## Production-Quality Demo Architecture

This demo runs **as if in production** - it uses real data generation, real tracing, and real lineage:

### Real Data Generation

The demo generates realistic e-commerce data using `floe-synthetic`:

- **1,000 customers** with names, emails, and regional distribution
- **5,000 orders** with weighted status distribution and amounts
- **100 products** across categories (electronics, clothing, home, sports, books)
- **10,000 order items** linking orders to products

Data volumes are configurable via environment variables:
```bash
DEMO_CUSTOMERS_COUNT=10000 DEMO_ORDERS_COUNT=50000 docker compose --profile demo up -d
```

### Real Tracing in Jaeger

Every asset execution emits OpenTelemetry spans to Jaeger:

- **Service**: `floe-demo` (configurable via `OTEL_SERVICE_NAME`)
- **Spans**: `generate_customers`, `generate_orders`, `generate_products`, `generate_order_items`
- **Attributes**: `rows_written`, `snapshot_id`, `asset_name`

**To see traces**:
1. Run the demo pipeline (materialize assets in Dagster)
2. Open Jaeger UI: http://localhost:16686
3. Select service `floe-demo`
4. View trace timelines and latency analysis

### Real Lineage in Marquez

Every asset emits OpenLineage events (START, COMPLETE, FAIL):

- **Namespace**: `demo` (configurable via `OPENLINEAGE_NAMESPACE`)
- **Jobs**: `bronze_customers`, `bronze_orders`, `bronze_products`, `bronze_order_items`
- **Datasets**: `iceberg://demo/default.bronze_*`

**To see lineage**:
1. Run the demo pipeline (materialize assets in Dagster)
2. Open Marquez Web: http://localhost:3001
3. Explore namespaces and job runs
4. View data flow between datasets

### Production-Like Pre-Aggregations

The demo uses **external pre-aggregations** with Cube Store + LocalStack S3:

| Component | Purpose |
|-----------|---------|
| **Cube Store Router** | Distributed query coordination |
| **Cube Store Workers** | Pre-aggregation compute nodes |
| **LocalStack S3** | Pre-aggregation data storage |

Pre-aggregations are stored in the `floe-cube-preaggs` S3 bucket, just like production deployments using AWS S3 or GCS.

### Compute Architecture

| Engine | Purpose | Admin UI |
|--------|---------|----------|
| **Trino** | SQL queries against Iceberg tables | http://localhost:8080 |
| **Polaris** | Iceberg REST catalog (OAuth2) | http://localhost:8181 |
| **LocalStack** | S3-compatible storage for Iceberg data files | - |

Data flow:
1. **floe-synthetic** generates PyArrow tables
2. **floe-iceberg** writes to Iceberg tables via Polaris catalog
3. **Trino** queries Iceberg tables for Cube semantic layer
4. **Cube** exposes REST/GraphQL/SQL APIs

---

## Next Steps

- See [docs/api-examples.md](api-examples.md) for comprehensive API reference
- See [testing/docker/README.md](../testing/docker/README.md) for infrastructure details
- See [docs/06-deployment-view.md](06-deployment-view.md) for production deployment
