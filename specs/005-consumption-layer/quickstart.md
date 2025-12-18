# Quickstart: Consumption Layer (floe-cube)

**Feature Branch**: `005-consumption-layer`
**Date**: 2025-12-18

## Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Existing floe-runtime project with dbt models
- CompiledArtifacts generated via `floe compile`

## 1. Enable Consumption in floe.yaml

```yaml
# floe.yaml
name: my-data-project
version: "1.0.0"

# ... existing configuration ...

consumption:
  enabled: true
  cube:
    port: 4000
    database_type: trino  # or postgres, snowflake, bigquery, databricks
    api_secret_ref: cube-api-secret  # K8s secret name
    dev_mode: true  # Enable Cube Playground
    pre_aggregations:
      refresh_schedule: "*/30 * * * *"
    security:
      row_level: true
      filter_column: organization_id  # User-managed: filter on any column you choose
```

## 2. Add Cube Metadata to dbt Models

```yaml
# dbt/models/orders.yml
version: 2

models:
  - name: orders
    description: Order transactions
    meta:
      cube:
        primary_key: id
        measures:
          - name: count
            type: count
          - name: total_amount
            sql: amount
            type: sum
          - name: average_amount
            sql: amount
            type: avg
    columns:
      - name: id
        description: Primary key
        meta:
          cube:
            primary_key: true
      - name: organization_id
        description: Organization identifier for row-level security
      - name: status
        description: Order status
        meta:
          cube:
            type: string
      - name: amount
        description: Order amount
        meta:
          cube:
            type: number
      - name: created_at
        description: Order creation timestamp
        meta:
          cube:
            type: time
```

## 3. Compile and Generate Cube Configuration

```bash
# Compile floe.yaml to CompiledArtifacts
floe compile

# Generate Cube configuration (after floe-cube is implemented)
floe cube generate

# Output:
# - .floe/cube/cube.js (Cube configuration)
# - .floe/cube/schema/*.yaml (Cube schemas from dbt models)
```

## 4. Start Test Infrastructure

```bash
# Start full test stack including Cube
cd testing/docker
docker compose --profile full up -d

# Verify services are healthy
curl http://localhost:4000/readyz  # Cube API
curl http://localhost:8080/v1/info # Trino
```

## 5. Query Data via REST API

```bash
# Get JWT token (in production, from your auth provider)
# Example: generate with jwt.io or your auth provider
export CUBE_TOKEN="<your-jwt-token-here>"

# Query orders by status
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Authorization: Bearer $CUBE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "measures": ["Orders.count", "Orders.totalAmount"],
    "dimensions": ["Orders.status"],
    "timeDimensions": [{
      "dimension": "Orders.createdAt",
      "granularity": "day",
      "dateRange": "Last 7 days"
    }]
  }'
```

## 6. Query Data via GraphQL

```bash
curl -X POST http://localhost:4000/cubejs-api/graphql \
  -H "Authorization: Bearer $CUBE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ cube { orders { count totalAmount status } } }"
  }'
```

## 7. Connect BI Tool via SQL API

```bash
# Connect with psql (Postgres client)
PGPASSWORD=$CUBE_TOKEN psql -h localhost -p 15432 -U cube -d cube

# Run SQL query
SELECT status, COUNT(*), SUM(amount) as total
FROM orders
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY status;
```

## 8. Test Row-Level Security

Row-level security filters data based on user-defined JWT claims (e.g., organization_id, department).

```bash
# JWT for organization "acme" (contains u.organization_id: "acme")
export ORG_ACME_TOKEN="eyJ...organization_id:acme..."

# JWT for organization "globex" (contains u.organization_id: "globex")
export ORG_GLOBEX_TOKEN="eyJ...organization_id:globex..."

# Query with acme context - should only see acme's data
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Authorization: Bearer $ORG_ACME_TOKEN" \
  -d '{"measures": ["Orders.count"]}'

# Query with globex context - should only see globex's data
curl -X POST http://localhost:4000/cubejs-api/v1/load \
  -H "Authorization: Bearer $ORG_GLOBEX_TOKEN" \
  -d '{"measures": ["Orders.count"]}'
```

**Note**: This is user-managed, role-based security within your deployment. It is distinct from SaaS tenant isolation (which provides separate environments per customer).

## 9. Verify OpenLineage Events

```bash
# Check Marquez for query lineage
curl http://localhost:5000/api/v1/namespaces/floe-cube/jobs

# Should show cube.orders.query jobs with run events
```

## Development Workflow

```bash
# Run unit tests
uv run pytest packages/floe-cube/tests/unit/

# Run integration tests (requires Docker)
./testing/docker/scripts/run-integration-tests.sh -k "cube"

# Type checking
uv run mypy --strict packages/floe-cube/

# Linting
uv run ruff check packages/floe-cube/
```

## Troubleshooting

### Cube won't start

```bash
# Check Cube logs
docker compose logs cube

# Verify Trino is healthy (Cube depends on it)
curl http://localhost:8080/v1/info
```

### Row-level security not filtering

1. Verify JWT contains the required claim (e.g., `u.organization_id`)
2. Check `security.row_level: true` in floe.yaml
3. Ensure cube schema includes `filter_column` definition matching your JWT claim

### Pre-aggregations not building

```bash
# Check Cube Store logs
docker compose logs cube

# Verify S3 bucket exists
aws --endpoint-url=http://localhost:4566 s3 ls s3://cube-preaggs/
```

### OpenLineage events not appearing

1. Check Marquez is healthy: `curl http://localhost:5001/healthcheck`
2. Verify `observability.openlineage_enabled: true` in floe.yaml
3. Check Cube logs for emission warnings

## Next Steps

- Configure pre-aggregations for frequently-queried data
- Set up monitoring dashboards for query performance
- Integrate with your JWT provider for production auth
- Configure semantic layer governance rules
