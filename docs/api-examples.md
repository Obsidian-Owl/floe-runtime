# API Examples

Comprehensive examples for all floe-runtime APIs. These examples work with the demo profile running.

---

## Prerequisites

```bash
# Start the demo stack
cd testing/docker
docker compose --profile demo up -d

# Verify services are healthy
./scripts/health-check.sh --profile demo
```

---

## Cube REST API

Base URL: `http://localhost:4000/cubejs-api/v1`

### Get Schema (Meta)

```bash
curl -s http://localhost:4000/cubejs-api/v1/meta | jq
```

Response includes available cubes, measures, and dimensions.

### Simple Query

```bash
# Total order count
curl -s http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Orders.count"]
    }
  }' | jq
```

### Query with Multiple Measures

```bash
# Orders summary
curl -s http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": [
        "Orders.count",
        "Orders.totalAmount",
        "Orders.averageOrderValue"
      ]
    }
  }' | jq
```

### Query with Dimensions

```bash
# Orders grouped by status
curl -s http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Orders.count", "Orders.totalAmount"],
      "dimensions": ["Orders.status"]
    }
  }' | jq
```

### Query with Time Dimension

```bash
# Daily order counts for last 30 days
curl -s http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Orders.count"],
      "timeDimensions": [{
        "dimension": "Orders.orderDate",
        "granularity": "day",
        "dateRange": "last 30 days"
      }]
    }
  }' | jq
```

### Query with Filters

```bash
# Only completed orders
curl -s http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Orders.count", "Orders.totalAmount"],
      "filters": [{
        "dimension": "Orders.status",
        "operator": "equals",
        "values": ["completed"]
      }]
    }
  }' | jq
```

### Query with Sorting and Limit

```bash
# Top 5 customer segments by revenue
curl -s http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Customers.totalRevenue", "Customers.count"],
      "dimensions": ["Customers.segment"],
      "order": {"Customers.totalRevenue": "desc"},
      "limit": 5
    }
  }' | jq
```

### Customer Segments Query

```bash
# Customer distribution by segment and churn risk
curl -s http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Customers.count", "Customers.averageOrderValue"],
      "dimensions": ["Customers.segment", "Customers.churnRisk"]
    }
  }' | jq
```

### Product Analytics Query

```bash
# Products by category with performance tier
curl -s http://localhost:4000/cubejs-api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "measures": ["Products.totalRevenue", "Products.totalUnitsSold"],
      "dimensions": ["Products.category", "Products.performanceTier"]
    }
  }' | jq
```

---

## Cube GraphQL API

Endpoint: `http://localhost:4000/cubejs-api/graphql`

### Simple Query

```bash
curl -s http://localhost:4000/cubejs-api/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ cube(measures: [\"Orders.count\"]) { Orders { count } } }"
  }' | jq
```

### Query with Dimensions

```bash
curl -s http://localhost:4000/cubejs-api/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ cube(measures: [\"Customers.count\"], dimensions: [\"Customers.segment\"]) { Customers { count segment } } }"
  }' | jq
```

### Complex Query with Filters

```bash
curl -s http://localhost:4000/cubejs-api/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetVIPCustomers { cube(measures: [\"Customers.count\", \"Customers.totalRevenue\"], filters: [{dimension: \"Customers.segment\", operator: equals, values: [\"vip\"]}]) { Customers { count totalRevenue } } }"
  }' | jq
```

### Schema Introspection

```bash
curl -s http://localhost:4000/cubejs-api/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ __schema { types { name fields { name } } } }"
  }' | jq '.data.__schema.types | map(select(.name | startswith("Orders") or startswith("Customers") or startswith("Products")))'
```

---

## Cube SQL API (Postgres Wire Protocol)

Connection details:
- Host: `localhost`
- Port: `15432`
- User: `cube`
- Password: `cube`
- Database: `cube`

### Using psql

```bash
# Simple query
PGPASSWORD=cube psql -h localhost -p 15432 -U cube -d cube \
  -c "SELECT MEASURE(count) FROM Orders"

# Query with dimension
PGPASSWORD=cube psql -h localhost -p 15432 -U cube -d cube \
  -c "SELECT status, MEASURE(count), MEASURE(total_amount) FROM Orders GROUP BY 1"

# Customer segments
PGPASSWORD=cube psql -h localhost -p 15432 -U cube -d cube \
  -c "SELECT segment, MEASURE(count), MEASURE(total_revenue) FROM Customers GROUP BY 1 ORDER BY 3 DESC"
```

### Using Python (psycopg2)

```python
import psycopg2

# Connect to Cube SQL API
conn = psycopg2.connect(
    host='localhost',
    port=15432,
    user='cube',
    password='cube',
    database='cube'
)

cursor = conn.cursor()

# Simple query
cursor.execute("SELECT MEASURE(count) FROM Orders")
print(f"Total orders: {cursor.fetchone()[0]}")

# Query with dimensions
cursor.execute("""
    SELECT segment, MEASURE(count), MEASURE(total_revenue)
    FROM Customers
    GROUP BY 1
    ORDER BY 3 DESC
""")
for row in cursor.fetchall():
    print(f"Segment {row[0]}: {row[1]} customers, ${row[2]} revenue")

cursor.close()
conn.close()
```

### Using Python (SQLAlchemy)

```python
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://cube:cube@localhost:15432/cube')

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT category, MEASURE(count), MEASURE(total_revenue)
        FROM Products
        GROUP BY 1
    """))
    for row in result:
        print(f"{row[0]}: {row[1]} products, ${row[2]}")
```

---

## Polaris REST API (Iceberg Catalog)

Base URL: `http://localhost:8181/api/catalog/v1`

Note: Polaris uses OAuth2 authentication. Credentials are auto-generated during init.

### Load Credentials

```bash
# Source the auto-generated credentials
source testing/docker/config/polaris-credentials.env

echo "Client ID: $POLARIS_CLIENT_ID"
echo "Secret: $POLARIS_CLIENT_SECRET"
```

### Get OAuth2 Token

```bash
source testing/docker/config/polaris-credentials.env

TOKEN=$(curl -s -X POST "http://localhost:8181/api/catalog/v1/oauth/tokens" \
  -d "grant_type=client_credentials" \
  -d "client_id=$POLARIS_CLIENT_ID" \
  -d "client_secret=$POLARIS_CLIENT_SECRET" \
  -d "scope=PRINCIPAL_ROLE:ALL" | jq -r '.access_token')

echo "Token: $TOKEN"
```

### List Namespaces

```bash
curl -s http://localhost:8181/api/catalog/v1/namespaces \
  -H "Authorization: Bearer $TOKEN" | jq
```

### List Tables in Namespace

```bash
curl -s "http://localhost:8181/api/catalog/v1/namespaces/default/tables" \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Get Table Metadata

```bash
curl -s "http://localhost:8181/api/catalog/v1/namespaces/default/tables/orders" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## Marquez Lineage API

Base URL: `http://localhost:5002/api/v1`

### List Namespaces

```bash
curl -s http://localhost:5002/api/v1/namespaces | jq
```

### List Jobs in Namespace

```bash
curl -s "http://localhost:5002/api/v1/namespaces/default/jobs" | jq
```

### List Datasets

```bash
curl -s "http://localhost:5002/api/v1/namespaces/default/datasets" | jq
```

### Get Dataset Lineage

```bash
# Replace with actual dataset name
curl -s "http://localhost:5002/api/v1/lineage?nodeId=dataset:default:orders" | jq
```

### Get Job Runs

```bash
# Replace with actual job name
curl -s "http://localhost:5002/api/v1/namespaces/default/jobs/demo_pipeline/runs" | jq
```

---

## Dagster GraphQL API

Endpoint: `http://localhost:3000/graphql`

### List Repositories

```bash
curl -s http://localhost:3000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ repositoriesOrError { ... on RepositoryConnection { nodes { name location { name } } } } }"
  }' | jq
```

### List Assets

```bash
curl -s http://localhost:3000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ assetsOrError { ... on AssetConnection { nodes { key { path } } } } }"
  }' | jq
```

### Get Asset Materializations

```bash
curl -s http://localhost:3000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetAsset($assetKey: AssetKeyInput!) { assetOrError(assetKey: $assetKey) { ... on Asset { assetMaterializations(limit: 5) { runId timestamp } } } }",
    "variables": {"assetKey": {"path": ["synthetic_data"]}}
  }' | jq
```

### Launch Pipeline Run

```bash
curl -s http://localhost:3000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation LaunchRun($params: ExecutionParams!) { launchRun(executionParams: $params) { ... on LaunchRunSuccess { run { runId status } } ... on PythonError { message } } }",
    "variables": {
      "params": {
        "selector": {
          "repositoryLocationName": "demo.orchestration",
          "repositoryName": "__repository__",
          "pipelineName": "demo_pipeline_job"
        }
      }
    }
  }' | jq
```

### Get Run Status

```bash
# Replace RUN_ID with actual run ID
curl -s http://localhost:3000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetRun($runId: ID!) { runOrError(runId: $runId) { ... on Run { runId status startTime endTime } } }",
    "variables": {"runId": "RUN_ID"}
  }' | jq
```

### List Schedules

```bash
curl -s http://localhost:3000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ schedulesOrError { ... on Schedules { results { name cronSchedule scheduleState { status } } } } }"
  }' | jq
```

### List Sensors

```bash
curl -s http://localhost:3000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ sensorsOrError { ... on Sensors { results { name sensorState { status } minIntervalSeconds } } } }"
  }' | jq
```

---

## Jaeger Tracing API

Base URL: `http://localhost:16686/api`

### List Services

```bash
curl -s http://localhost:16686/api/services | jq
```

### Get Traces for Service

```bash
# Replace SERVICE with actual service name
curl -s "http://localhost:16686/api/traces?service=SERVICE&limit=10" | jq
```

### Get Specific Trace

```bash
# Replace TRACE_ID with actual trace ID
curl -s "http://localhost:16686/api/traces/TRACE_ID" | jq
```

---

## Trino SQL API

Trino provides standard JDBC/ODBC interface and REST API.

### Using Trino CLI

```bash
# Connect to Trino
docker exec -it floe-trino trino

# List catalogs
SHOW CATALOGS;

# List schemas in iceberg catalog
SHOW SCHEMAS FROM iceberg;

# List tables
SHOW TABLES FROM iceberg.default;

# Query data
SELECT * FROM iceberg.default.orders LIMIT 10;
```

### Using curl

```bash
# Submit query
curl -s http://localhost:8080/v1/statement \
  -H "X-Trino-User: admin" \
  -d "SELECT count(*) FROM iceberg.default.orders" | jq
```

---

## LocalStack S3 API

Base URL: `http://localhost:4566`

### List Buckets

```bash
aws --endpoint-url=http://localhost:4566 s3 ls
```

### List Objects in Bucket

```bash
aws --endpoint-url=http://localhost:4566 s3 ls s3://warehouse/ --recursive
```

### Get Object

```bash
aws --endpoint-url=http://localhost:4566 s3 cp s3://warehouse/path/to/file.parquet -
```

---

## Common Response Formats

### Cube REST Response

```json
{
  "data": [
    {
      "Orders.count": 1500,
      "Orders.totalAmount": 125000.50
    }
  ],
  "lastRefreshTime": "2024-01-15T10:30:00.000Z",
  "annotation": {
    "measures": {
      "Orders.count": { "title": "Count", "type": "number" },
      "Orders.totalAmount": { "title": "Total Amount", "type": "number" }
    }
  }
}
```

### Marquez Lineage Response

```json
{
  "graph": [
    {
      "id": "job:default:demo_pipeline",
      "type": "JOB",
      "inEdges": [...],
      "outEdges": [...]
    }
  ]
}
```

### Dagster Run Response

```json
{
  "data": {
    "launchRun": {
      "run": {
        "runId": "abc123-def456",
        "status": "STARTING"
      }
    }
  }
}
```

---

## Error Handling

### Cube API Errors

```json
{
  "error": "Cube not found: InvalidCube"
}
```

### Polaris Authentication Error

```json
{
  "error": {
    "message": "Not authorized",
    "type": "NotAuthorizedException",
    "code": 401
  }
}
```

### Dagster Validation Error

```json
{
  "data": {
    "launchRun": {
      "__typename": "InvalidSubsetError",
      "message": "No matching jobs"
    }
  }
}
```
