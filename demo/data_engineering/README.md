# Data Engineering Repository

**Owner**: Data Engineering Team
**Purpose**: Data pipelines, transformations, semantic models, and orchestration logic

This repository represents **Tier 1 (Pipeline Configuration)** of the three-tier architecture. It contains data engineering code that is **completely decoupled from infrastructure details**—no credentials, no endpoints, no Kubernetes config.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  Three-Tier Configuration                        │
├─────────────────────────────────────────────────────────────────┤
│ Tier 1: floe.yaml          (THIS REPO)                          │
│         └─ Pipelines, transforms, governance, logical refs       │
│                                                                  │
│ Tier 2: platform.yaml      (Platform Config Repo)               │
│         └─ Infrastructure endpoints, secret refs                 │
│                                                                  │
│ Tier 3: values.yaml        (Platform Config Repo)               │
│         └─ K8s config, secret mounts, resource limits            │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle**: The same `floe.yaml` and data engineering code works unchanged across local, dev, staging, and prod environments. Infrastructure differences are handled by `platform.yaml` (Tier 2).

## Directory Structure

```
data-engineering/
├── floe.yaml              # Tier 1: Pipeline configuration (logical references only)
├── orchestration/         # Dagster assets and jobs
│   ├── definitions.py
│   ├── assets/
│   │   ├── raw.py         # Bronze layer: Raw data ingestion
│   │   ├── cleaned.py     # Silver layer: Cleaned + enriched
│   │   └── aggregated.py  # Gold layer: Aggregated marts
│   ├── resources/
│   │   ├── catalog.py     # CatalogResource (Polaris/Iceberg)
│   │   ├── dbt.py         # DbtCliResource
│   │   └── cube.py        # CubeResource (semantic layer)
│   └── sensors/
│       └── data_quality.py
│
├── dbt/                   # SQL transformations
│   ├── dbt_project.yml
│   ├── profiles.yml       # Logical profile references (no credentials)
│   ├── models/
│   │   ├── bronze/        # Raw + lightly cleaned
│   │   │   ├── raw_customers.sql
│   │   │   ├── raw_orders.sql
│   │   │   └── raw_products.sql
│   │   ├── silver/        # Cleaned + enriched
│   │   │   ├── customers.sql
│   │   │   ├── orders.sql
│   │   │   └── products.sql
│   │   └── gold/          # Aggregated marts
│   │       ├── customer_lifetime_value.sql
│   │       ├── daily_sales_summary.sql
│   │       └── product_performance.sql
│   ├── macros/
│   ├── tests/
│   └── seeds/
│
├── cube/                  # Semantic layer (Cube.js)
│   ├── cube.yaml
│   ├── model/
│   │   ├── customers.yml
│   │   ├── orders.yml
│   │   └── products.yml
│   └── views/
│       ├── sales_dashboard.yml
│       └── customer_analytics.yml
│
├── tests/                 # Unit and integration tests
│   ├── test_assets.py
│   ├── test_dbt_models.py
│   └── fixtures/
│
├── Dockerfile             # Multi-stage build with CompiledArtifacts
├── .github/
│   └── workflows/
│       └── deploy.yml     # CI/CD: compile → build → deploy
│
└── README.md              # This file
```

## floe.yaml - Pipeline Configuration

The `floe.yaml` file defines your data pipeline using **logical references** to infrastructure:

```yaml
# floe.yaml (Data Engineer - same file works across ALL environments)
name: customer-analytics
version: "1.0.0"

# Logical references - resolved by platform.yaml at runtime
storage: default          # Platform engineer maps this to S3/LocalStack
catalog: default          # Platform engineer maps this to Polaris
compute: default          # Platform engineer maps this to DuckDB/Trino

# Data governance (defined by data engineers)
governance:
  data_classification:
    pii_detection: true
    auto_tag_pii: true
  retention:
    bronze: 2555d  # 7 years
    silver: 730d   # 2 years
    gold: 90d      # 90 days

# Observability (defined by data engineers)
observability:
  opentelemetry:
    enabled: true
    traces: true
    metrics: true
  openlineage:
    enabled: true
    namespace: customer-analytics

# Layers (Medallion Architecture)
layers:
  bronze:
    description: "Raw data + light cleaning"
    retention: 2555d
    storage: bronze  # Maps to S3 bucket iceberg-bronze

  silver:
    description: "Cleaned + enriched data"
    retention: 730d
    storage: silver  # Maps to S3 bucket iceberg-silver

  gold:
    description: "Aggregated business metrics"
    retention: 90d
    storage: gold    # Maps to S3 bucket iceberg-gold

# No credentials, no endpoints, no infrastructure details!
```

## Key Features

### 1. Environment Agnostic

Your code works **unchanged** across environments:

```python
# orchestration/resources/catalog.py
from floe_dagster.resources import CatalogResource

# This code is identical in local/dev/prod
# platform.yaml provides the actual Polaris endpoint and credentials
catalog_resource = CatalogResource.from_platform_config()
```

### 2. Medallion Architecture

Data flows through three quality layers:

| Layer | Purpose | Retention | Storage |
|-------|---------|-----------|---------|
| **Bronze** | Raw + lightly cleaned | 7 years | `s3://iceberg-bronze/` |
| **Silver** | Cleaned + enriched | 2 years | `s3://iceberg-silver/` |
| **Gold** | Aggregated marts | 90 days | `s3://iceberg-gold/` |

### 3. Type-Safe Schemas

All data models use Pydantic for validation:

```python
# orchestration/assets/raw.py
from pydantic import BaseModel, Field

class RawCustomer(BaseModel):
    customer_id: int = Field(..., gt=0)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    created_at: datetime
```

### 4. Observability Built-In

OpenTelemetry and OpenLineage enabled by default:

```python
# orchestration/assets/cleaned.py
from floe_dagster.decorators import traced_asset

@traced_asset(group="silver", compute_kind="dbt")
def customers(context, raw_customers):
    """Cleaned customer data with PII detection."""
    # Tracing, metrics, and lineage captured automatically
    ...
```

## Development Workflow

### 1. Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start local Dagster UI
dagster dev

# Access at http://localhost:3000
```

### 2. Creating New Assets

```python
# orchestration/assets/new_asset.py
from dagster import asset
from floe_dagster.resources import CatalogResource

@asset(
    group_name="silver",
    compute_kind="python",
    io_manager_key="iceberg_io_manager"
)
def new_customers_enriched(context, raw_customers):
    """Enrich customer data with external attributes."""
    catalog: CatalogResource = context.resources.catalog

    # Load from Bronze
    df = catalog.load_table("demo.bronze.raw_customers")

    # Transform
    enriched_df = enrich_customers(df)

    # Write to Silver
    catalog.write_table("demo.silver.customers_enriched", enriched_df)

    return enriched_df
```

### 3. Creating dbt Models

```sql
-- dbt/models/silver/customers.sql
{{
  config(
    materialized='incremental',
    unique_key='customer_id',
    tags=['pii', 'silver']
  )
}}

SELECT
    customer_id,
    email,
    first_name,
    last_name,
    created_at,
    updated_at
FROM {{ ref('raw_customers') }}
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
```

### 4. Testing

```python
# tests/test_assets.py
from orchestration.assets.cleaned import customers

def test_customers_asset():
    """Test customers asset with mock data."""
    # Use fixture data
    result = customers(mock_context, mock_raw_customers)

    # Validate schema
    assert "customer_id" in result.columns
    assert len(result) > 0

    # Validate no PII leakage
    assert not result["email"].str.contains("@").any()
```

## CI/CD Integration

### Build Workflow

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy
on:
  push:
    branches: [main]
  pull_request:

env:
  PLATFORM_CONFIG_VERSION: "platform-config-v1.2.3"  # Pin platform version

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run tests
        run: |
          pip install -e ".[dev]"
          pytest --cov=orchestration

      - name: Lint
        run: |
          ruff check .
          mypy orchestration/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download platform config artifact
        run: |
          gh release download $PLATFORM_CONFIG_VERSION \
            --repo myorg/platform-config \
            --pattern 'platform/dev/platform.yaml' \
            --output platform.yaml

      - name: Compile artifacts
        run: |
          floe compile \
            --floe-yaml=floe.yaml \
            --platform-yaml=platform.yaml \
            --output=compiled/

      - name: Build Docker image
        run: |
          docker build \
            --build-arg COMPILED_ARTIFACTS=compiled/ \
            -t ghcr.io/myorg/customer-analytics:${{ github.sha }} \
            .

      - name: Push image
        run: |
          echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push ghcr.io/myorg/customer-analytics:${{ github.sha }}

  deploy-dev:
    needs: build
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - name: Configure kubectl
        run: |
          aws eks update-kubeconfig --name floe-dev-cluster --region us-east-1

      - name: Deploy with Helm
        run: |
          helm upgrade --install customer-analytics \
            oci://ghcr.io/myorg/floe-dagster \
            --namespace analytics --create-namespace \
            --set image.tag=${{ github.sha }} \
            --values values-dev.yaml \
            --wait --timeout 5m

  deploy-prod:
    needs: build
    runs-on: ubuntu-latest
    environment: prod
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Configure kubectl
        run: |
          aws eks update-kubeconfig --name floe-prod-cluster --region us-east-1

      - name: Deploy with Helm
        run: |
          helm upgrade --install customer-analytics \
            oci://ghcr.io/myorg/floe-dagster \
            --namespace analytics --create-namespace \
            --set image.tag=${{ github.sha }} \
            --values values-prod.yaml \
            --wait --timeout 10m
```

### Key Steps Explained

1. **Test**: Run unit tests and linting
2. **Download Platform Config**: Fetch versioned platform.yaml artifact
3. **Compile**: Merge floe.yaml + platform.yaml → CompiledArtifacts
4. **Build**: Create Docker image with compiled artifacts baked in
5. **Deploy**: Update Helm release with new image tag

## Dockerfile

Multi-stage build that bakes CompiledArtifacts into the image:

```dockerfile
# Dockerfile
FROM python:3.11-slim AS builder

WORKDIR /build

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY orchestration/ ./orchestration/
COPY dbt/ ./dbt/
COPY cube/ ./cube/

# Copy CompiledArtifacts (created by floe compile in CI)
ARG COMPILED_ARTIFACTS=compiled/
COPY ${COMPILED_ARTIFACTS} /app/compiled/

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /build /app

# Copy demo code
COPY orchestration/ /app/demo/orchestration/
COPY dbt/ /app/demo/dbt/
COPY cube/ /app/demo/cube/

# Set environment variables
ENV PYTHONPATH=/app
ENV DBT_PROFILES_DIR=/app/demo
ENV DAGSTER_HOME=/tmp/dagster_home

# Expose Dagster gRPC port
EXPOSE 3030

# Run Dagster code server
CMD ["dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "3030", "-m", "demo.orchestration.definitions"]
```

## Platform Config Integration

### How platform.yaml is Used

At runtime, your code loads platform configuration:

```python
# orchestration/definitions.py
from floe_dagster import Definitions
from floe_dagster.resources import CatalogResource, StorageResource

# Platform config loaded from /etc/floe/platform.yaml (mounted by K8s)
# Credentials loaded from environment variables (K8s secrets)
defs = Definitions(
    assets=load_assets_from_modules([assets]),
    resources={
        "catalog": CatalogResource.from_platform_config(),
        "storage": StorageResource.from_platform_config(),
    }
)
```

### Local vs Cloud Differences

**Local** (`platform/local/platform.yaml`):
```yaml
catalogs:
  default:
    type: polaris
    uri: "http://floe-infra-polaris:8181/api/catalog"  # K8s service
    credentials:
      mode: oauth2
      client_id: {secret_ref: polaris-client-id}
```

**Dev** (`platform/dev/platform.yaml`):
```yaml
catalogs:
  default:
    type: polaris
    uri: "https://polaris.dev.myorg.com/api/catalog"  # Public endpoint
    credentials:
      mode: oauth2
      client_id: {secret_ref: polaris-client-id}
```

**Your code doesn't change**—platform.yaml handles the differences.

## Common Tasks

### Add New Bronze Table

1. Create dbt seed or ingestion asset:
   ```python
   @asset(group_name="bronze")
   def raw_events(context):
       """Ingest raw event stream."""
       ...
   ```

2. Update `floe.yaml` governance:
   ```yaml
   governance:
     data_classification:
       tables:
         demo.bronze.raw_events:
           sensitivity: public
           retention: 2555d
   ```

3. Test locally:
   ```bash
   dagster asset materialize --select raw_events
   ```

### Add Silver Transformation

1. Create dbt model:
   ```sql
   -- dbt/models/silver/events_cleaned.sql
   SELECT * FROM {{ ref('raw_events') }}
   WHERE event_type IS NOT NULL
   ```

2. Create Dagster asset:
   ```python
   @dbt_asset(model_name="events_cleaned", group_name="silver")
   def events_cleaned(context):
       ...
   ```

3. Test:
   ```bash
   dbt run --select events_cleaned
   ```

### Add Gold Metric

1. Create dbt model:
   ```sql
   -- dbt/models/gold/daily_active_users.sql
   SELECT
       DATE_TRUNC('day', event_time) AS date,
       COUNT(DISTINCT user_id) AS dau
   FROM {{ ref('events_cleaned') }}
   GROUP BY 1
   ```

2. Create Cube view:
   ```yaml
   # cube/views/engagement_dashboard.yml
   cubes:
     - name: daily_active_users
       sql: "SELECT * FROM demo.gold.daily_active_users"
       measures:
         - name: dau
           type: sum
   ```

## Troubleshooting

### Platform Config Not Found

```python
# Check environment variable
import os
print(os.getenv("FLOE_PLATFORM_FILE"))  # Should be /etc/floe/platform.yaml

# Verify file exists in container
ls -l /etc/floe/platform.yaml
```

### Credentials Not Available

```bash
# Check environment variables in pod
kubectl exec -it <dagster-pod> -n floe -- env | grep -E '(POLARIS|AWS)'

# Should see:
# POLARIS_CLIENT_ID=demo_client
# POLARIS_CLIENT_SECRET=demo_secret_k8s
# AWS_ACCESS_KEY_ID=minioadmin
# AWS_SECRET_ACCESS_KEY=minioadmin
```

### dbt Profile Not Found

```python
# Check DBT_PROFILES_DIR
import os
print(os.getenv("DBT_PROFILES_DIR"))  # Should be /app/demo

# Verify profiles.yml exists
cat /app/demo/profiles.yml
```

## Best Practices

1. **Never hardcode infrastructure details** - Use logical references in `floe.yaml`
2. **Never commit credentials** - All secrets via environment variables
3. **Test locally first** - Validate assets before deploying
4. **Pin platform-config versions** - Don't use "latest" in CI/CD
5. **Use Medallion Architecture** - Bronze → Silver → Gold data flow
6. **Tag PII data** - Enable auto-tagging in governance config
7. **Monitor lineage** - OpenLineage tracks all data transformations
8. **Version your schemas** - Use Pydantic models for type safety

## References

- [ADR-0002: Three-Tier Configuration Architecture](../../docs/adr/0002-three-tier-config.md)
- [Pipeline Configuration Guide](../../docs/pipeline-config.md)
- [Platform Config Repo](../platform-config/README.md)
- [Dagster Documentation](https://docs.dagster.io/)
- [dbt Documentation](https://docs.getdbt.com/)
- [Cube.js Documentation](https://cube.dev/docs/)
