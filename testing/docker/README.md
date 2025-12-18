# floe-runtime E2E Test Infrastructure

Docker Compose configuration for local integration and E2E testing of the complete floe-runtime data stack.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         floe-runtime Test Stack                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Cube v0.36  │    │  Trino 479   │    │    Spark     │  Consumption │
│  │  (Port 4000) │    │ (Port 8080)  │    │ (Port 10000) │  & Compute   │
│  │  + cube-init │    │  + OAuth2    │    │              │              │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│         │                   │                   │                       │
│         └───────────────────┼───────────────────┘                       │
│                             │                                           │
│                     ┌───────┴───────┐                                  │
│                     │    Polaris    │  Iceberg REST Catalog            │
│                     │  (Port 8181)  │  OAuth2 credentials via init     │
│                     │ + polaris-init│                                  │
│                     └───────┬───────┘                                  │
│                             │                                           │
│         ┌───────────────────┼───────────────────┐                      │
│         │                   │                   │                       │
│  ┌──────┴───────┐    ┌──────┴───────┐    ┌──────┴───────┐              │
│  │  PostgreSQL  │    │  LocalStack  │    │   Marquez    │  Storage &   │
│  │ (Port 5432)  │    │ (Port 4566)  │    │ (Port 5002)  │  Lineage     │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                         │
│  ┌──────────────┐                                                      │
│  │   Jaeger     │  Observability                                       │
│  │ (Port 16686) │                                                      │
│  └──────────────┘                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Navigate to testing directory
cd testing/docker

# Start base services (PostgreSQL + Jaeger)
docker compose up -d

# Start with storage profile (adds LocalStack + Polaris)
docker compose --profile storage up -d

# Start with compute profile (adds Trino + Spark)
docker compose --profile compute up -d

# Start all services (full profile)
docker compose --profile full up -d
```

## Profiles

| Profile | Services | Use Case | Tests |
|---------|----------|----------|-------|
| (none) | PostgreSQL, Jaeger | Unit tests, dbt-postgres target | - |
| `storage` | + LocalStack (S3+STS+IAM), Polaris, polaris-init | Iceberg storage tests | 62 tests |
| `compute` | + Trino 479, Spark | Compute engine tests | - |
| `full` | + Cube v0.36, cube-init, Marquez | E2E tests, semantic layer | 21 tests |

## Service Versions

| Service | Version | Notes |
|---------|---------|-------|
| PostgreSQL | 16-alpine | Multi-database setup |
| LocalStack | latest | S3 + STS + IAM emulation |
| Polaris | localstack/polaris | Pre-configured for LocalStack S3 |
| Trino | 479 | OAuth2 support for Polaris authentication |
| Spark | 3.5.1 + Iceberg 1.5.0 | tabulario/spark-iceberg image |
| Cube | v0.36 | Trino driver, pre-aggregations |
| Marquez | 0.49.0 | OpenLineage backend |
| Jaeger | latest | OpenTelemetry collector |

## Services

### Core Infrastructure

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Relational database (catalog persistence, dbt target) |
| Jaeger | 16686 | Distributed tracing UI |

### Storage Layer (--profile storage)

| Service | Port | Description |
|---------|------|-------------|
| LocalStack | 4566 | AWS emulator (S3, STS, IAM) for production-aligned testing |
| Polaris | 8181, 8182 | Apache Polaris - Iceberg REST catalog (OAuth2 auth) |
| polaris-init | - | Extracts credentials, creates warehouse, writes Trino config |

### Compute Layer (--profile compute)

| Service | Port | Description |
|---------|------|-------------|
| Trino | 8080 | Distributed SQL query engine (OAuth2 auth to Polaris) |
| Spark | 8888, 10000 | Apache Spark with Iceberg |

### Full Stack (--profile full)

| Service | Port | Description |
|---------|------|-------------|
| Cube | 4000, 15432 | Semantic layer (REST/GraphQL/SQL APIs) |
| cube-init | - | Creates orders table, loads 15,500 test rows |
| Marquez | 5002, 5001 | OpenLineage backend for data lineage |
| Marquez Web | 3001 | Lineage visualization UI |

## Service URLs

After starting services, access UIs at:

| Service | URL | Notes |
|---------|-----|-------|
| LocalStack Health | http://localhost:4566/_localstack/health | - |
| Polaris API | http://localhost:8181/api/catalog/v1/config | OAuth2 (auto-generated) |
| Trino UI | http://localhost:8080 | - |
| Jaeger UI | http://localhost:16686 | - |
| Spark Notebooks | http://localhost:8888 | - |
| Cube REST API | http://localhost:4000 | Dev mode (no auth required) |
| Cube SQL API | localhost:15432 | Postgres wire protocol |
| Marquez API | http://localhost:5002 | - |
| Marquez UI | http://localhost:3001 | - |

## Automatic Credential Management

Polaris auto-generates OAuth2 credentials on startup. The `polaris-init` container:
1. Extracts credentials from Polaris logs
2. Creates warehouse catalog with proper permissions
3. Writes `polaris-credentials.env` for Python tests
4. Writes `trino-iceberg.properties` with OAuth2 config for Trino

**Files generated:**

```
config/
├── polaris-credentials.env      # For Python tests (PyIceberg)
└── trino-iceberg.properties     # For Trino Iceberg connector (OAuth2)
```

Both files are git-ignored and regenerated on each `docker compose up`.

### Trino-Polaris Authentication

Trino 479 requires OAuth2 for Polaris REST catalog. The generated `trino-iceberg.properties`:

```properties
# Auto-generated by polaris-init
iceberg.rest-catalog.security=OAUTH2
iceberg.rest-catalog.oauth2.server-uri=http://polaris:8181/api/catalog/v1/oauth/tokens
iceberg.rest-catalog.oauth2.credential=<client_id>:<client_secret>
iceberg.rest-catalog.oauth2.scope=PRINCIPAL_ROLE:ALL
```

## Running Integration Tests

### Storage Profile Tests (62 tests)

```bash
# Start storage profile
docker compose --profile storage up -d

# Wait for polaris-init to complete
docker compose logs polaris-init --tail 20

# Run tests
source config/polaris-credentials.env
uv run pytest -m integration packages/floe-polaris/tests/ packages/floe-iceberg/tests/ -v
```

### Full Profile Tests (21 tests)

```bash
# Start full profile
docker compose --profile full up -d

# Wait for cube-init to complete (loads 15,500 test rows)
docker compose logs cube-init --tail 20

# Run Cube integration tests
uv run pytest packages/floe-cube/tests/integration/ -v
```

**cube-init creates:**
- `iceberg.default` namespace
- `orders` table with schema (id, customer_id, status, region, amount, created_at)
- 15,500 test rows for pagination testing

**Cube test coverage (T036-T039):**
- T036: REST API returns JSON for valid queries
- T037: REST API authentication handling
- T038: REST API pagination over 10k rows
- T039: Pre-aggregations (using `external: false` for Trino storage)

## Cube Configuration

### Pre-aggregations

Cube is configured with pre-aggregations using `external: false` to store in Trino/Iceberg
(the Trino driver only supports GCS for external bucket, not S3/LocalStack):

```javascript
// cube-schema/Orders.js
preAggregations: {
  base: {
    type: `originalSql`,
    external: false,  // Store in Trino, not external bucket
  },
  ordersByDay: {
    measures: [CUBE.count, CUBE.totalAmount],
    dimensions: [CUBE.status],
    timeDimension: CUBE.createdAt,
    granularity: `day`,
    external: false,
    useOriginalSqlPreAggregations: true,
  },
},
```

### Cube Environment

Key environment variables:
- `CUBEJS_DB_TYPE=trino` - Uses Trino driver
- `CUBEJS_DB_USER=trino` - Required for Trino 479 (X-Trino-User header)
- `CUBEJS_DEV_MODE=true` - Disables authentication for testing

## Databases

PostgreSQL is pre-configured with multiple databases:

| Database | Purpose |
|----------|---------|
| polaris | Iceberg catalog metadata (unused - Polaris uses in-memory) |
| marquez | OpenLineage data |
| floe_dev | Development/testing |
| floe_dbt | dbt compute target |

## S3 Buckets

LocalStack is pre-configured with buckets:

| Bucket | Purpose |
|--------|---------|
| warehouse | Iceberg table data |
| iceberg | Alternative Iceberg location |
| cube-preaggs | Cube pre-aggregation storage (unused - using internal) |
| dbt-artifacts | dbt artifacts storage |

## Health Checks

```bash
# Check service status
docker compose ps

# Check specific service health
curl -f http://localhost:8181/api/catalog/v1/config         # Polaris
curl -f http://localhost:4566/_localstack/health            # LocalStack
curl -f http://localhost:4000/readyz                        # Cube
curl -f http://localhost:5002/api/v1/namespaces             # Marquez
docker exec floe-trino trino --execute "SELECT 1"           # Trino
```

## Clean up

```bash
# Stop all containers
docker compose --profile full down

# Remove volumes (fresh start)
docker compose --profile full down -v

# Remove everything including images
docker compose --profile full down -v --rmi all
```

## Troubleshooting

### Polaris credentials not working

The `polaris-init` container must complete successfully:
```bash
docker compose logs polaris-init
# Should show: "Polaris initialization complete"
```

### Trino can't connect to Polaris

Check if `trino-iceberg.properties` was generated:
```bash
cat config/trino-iceberg.properties
# Should contain oauth2.credential=<client_id>:<client_secret>
```

### Cube queries failing with auth error

Ensure `CUBEJS_DB_USER=trino` is set (required for Trino 479):
```bash
docker compose logs cube | grep -i auth
```

### cube-init fails with "table already exists"

This is OK - the script is idempotent. Check if data was loaded:
```bash
docker compose logs cube-init | grep "Total rows"
# Should show: "Total rows: 15500"
```

### LocalStack buckets not created

The `localstack-init` service runs once. Check logs:
```bash
docker compose logs localstack-init
```

### Out of memory

Reduce Spark memory in `spark-defaults.conf`:
```properties
spark.driver.memory=1g
spark.executor.memory=1g
```

## Integration with floe-runtime

This infrastructure tests the complete floe-runtime stack:

1. **floe-polaris** (62 tests): Catalog management via Polaris REST API
2. **floe-iceberg** (62 tests): Iceberg table operations via PyIceberg
3. **floe-cube** (21 tests): Semantic layer over Iceberg tables via Trino
4. **floe-dbt**: Profile generation, dbt execution against PostgreSQL/Trino
5. **floe-dagster**: Asset materialization orchestration
6. **floe-core**: CompiledArtifacts validation

Run tests with:

```bash
# Storage profile tests (62 tests)
./scripts/run-integration-tests.sh

# Full profile tests (21 tests)
docker compose --profile full up -d
uv run pytest packages/floe-cube/tests/integration/ -v
```
