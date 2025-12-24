# Data Engineer Quickstart: Building a Data Product

Build a complete bronze/silver/gold data pipeline in **~50 lines of Python** and **15 minutes**.

## What You'll Build

A production-ready e-commerce analytics pipeline with:
- **Bronze layer**: Raw synthetic data to Iceberg tables
- **Silver layer**: dbt staging transformations
- **Gold layer**: dbt mart aggregations
- **Observability**: Automatic tracing (Jaeger) and lineage (Marquez)

## Why floe-runtime?

| Traditional Approach | floe-runtime |
|---------------------|--------------|
| 50-100 LOC for simple pipeline | **10-15 LOC** |
| Manual profiles.yml management | **No profiles.yml** |
| Credential exposure to data engineers | **Zero credential exposure** |
| Bolt-on observability | **Built-in observability** |
| 2-3 hours setup | **15 minutes** |

## Prerequisites

- Python 3.10+
- `uv` package manager (or pip)
- Docker (for local infrastructure)

## Step 1: Create Your Pipeline Definition (floe.yaml)

`floe.yaml` is the **only file** you need for pipeline definition. No profiles.yml, no credentials, no infrastructure details.

```yaml
# floe.yaml - Data Engineer's view (clean, no infrastructure)
name: ecommerce-analytics
version: "1.0.0"

# Logical references - platform team configures the actual infrastructure
storage: default
catalog: default
compute: default

transforms:
  - name: bronze_layer
    type: python
    description: Raw data ingestion

  - name: silver_layer
    type: dbt
    description: Staging transformations

  - name: gold_layer
    type: dbt
    description: Business aggregations
```

**Key insight**: You reference `storage: default`, `catalog: default`, `compute: default`. The platform team maps these to real infrastructure in `platform.yaml`. You never see credentials or endpoints.

## Step 2: Write Your Bronze Assets

```python
# definitions.py
from floe_dagster import floe_asset, FloeDefinitions
from floe_dagster.resources import PolarisCatalogResource

@floe_asset(
    group_name="bronze",
    outputs=["demo.bronze_customers"],
)
def bronze_customers(context, catalog: PolarisCatalogResource):
    """Generate customer data and write to Iceberg.

    Pure business logic - no observability boilerplate.
    """
    from floe_synthetic.generators.ecommerce import EcommerceGenerator

    # Generate data
    generator = EcommerceGenerator(seed=42)
    customers = generator.generate_customers(count=1000)

    # One-line write (auto-creates table, handles schema evolution)
    snapshot = catalog.write_table("demo.bronze_customers", customers)

    return {"rows": customers.num_rows, "snapshot_id": snapshot.snapshot_id}


@floe_asset(
    group_name="bronze",
    outputs=["demo.bronze_orders"],
    deps=["bronze_customers"],  # Dependency on customers
)
def bronze_orders(context, catalog: PolarisCatalogResource):
    """Generate order data linked to customers."""
    from floe_synthetic.generators.ecommerce import EcommerceGenerator

    generator = EcommerceGenerator(seed=42)
    generator.generate_customers(count=1000)  # Establish FK relationships
    orders = generator.generate_orders(count=5000)

    snapshot = catalog.write_table("demo.bronze_orders", orders)
    return {"rows": orders.num_rows, "snapshot_id": snapshot.snapshot_id}
```

**Lines of code**: ~30 for two complete bronze assets with automatic:
- Table creation (if not exists)
- Schema evolution
- OpenTelemetry tracing
- OpenLineage lineage emission

## Step 3: Add dbt Transformations (Silver/Gold)

Create dbt models that query your bronze tables:

```sql
-- models/staging/stg_customers.sql
SELECT
    customer_id,
    UPPER(email) as email,
    first_name || ' ' || last_name as full_name,
    created_at
FROM {{ source('bronze', 'bronze_customers') }}
WHERE email IS NOT NULL
```

```sql
-- models/marts/customer_orders.sql
SELECT
    c.customer_id,
    c.full_name,
    COUNT(o.order_id) as total_orders,
    SUM(o.amount) as total_spent
FROM {{ ref('stg_customers') }} c
LEFT JOIN {{ ref('stg_orders') }} o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.full_name
```

**Note**: You write standard dbt models. floe-runtime handles the compute target (DuckDB locally, Snowflake in prod) automatically based on `platform.yaml`.

## Step 4: Wire Everything Together

```python
# definitions.py (continued)
from dagster import define_asset_job, ScheduleDefinition

# Define jobs
bronze_job = define_asset_job(
    name="bronze_pipeline",
    selection="*bronze*",
)

# Define schedules
daily_refresh = ScheduleDefinition(
    name="daily_refresh",
    job=bronze_job,
    cron_schedule="0 6 * * *",  # 6 AM daily
)

# One-line wiring - batteries-included
defs = FloeDefinitions.from_compiled_artifacts(
    assets=[bronze_customers, bronze_orders],
    jobs=[bronze_job],
    schedules=[daily_refresh],
)
```

## What You Get (for Free)

### Automatic Observability

Every asset execution automatically creates:

1. **OpenTelemetry traces** - visible in Jaeger
   - Span per asset with timing
   - Error recording on failures
   - Correlation IDs across the pipeline

2. **OpenLineage events** - visible in Marquez
   - START/COMPLETE/FAIL events
   - Input/output dataset tracking
   - Cross-system lineage graphs

### Automatic Table Management

`catalog.write_table()` handles:
- Table creation if not exists
- Schema evolution (new columns added automatically)
- Overwrite or append modes
- Snapshot tracking

### Portability

Same code works:
- **Locally**: DuckDB + LocalStack
- **Kubernetes**: Trino + S3
- **Cloud**: Snowflake + native S3

Just change `platform.yaml` - your code stays the same.

## What You DON'T Need to Do

| Traditional | floe-runtime |
|-------------|--------------|
| Write profiles.yml | Abstracted away |
| Configure database connections | Platform team handles |
| Set up Jaeger/OpenTelemetry | Built-in |
| Set up Marquez/OpenLineage | Built-in |
| Manage credentials | Never exposed |
| Write observability boilerplate | Automatic |
| Handle table creation | `write_table()` does it |

## Running Locally

```bash
# Start infrastructure (Polaris, LocalStack, Jaeger, Marquez)
make up-demo

# Run Dagster
dagster dev -m demo.orchestration.definitions

# View observability
open http://localhost:16686  # Jaeger traces
open http://localhost:3000   # Marquez lineage
```

## Complete Example

Here's the full `definitions.py` (~50 lines):

```python
"""Complete e-commerce data product in ~50 lines."""
from typing import Dict, Any

from dagster import AssetExecutionContext, define_asset_job, ScheduleDefinition
from floe_dagster import floe_asset, FloeDefinitions
from floe_dagster.resources import PolarisCatalogResource


@floe_asset(group_name="bronze", outputs=["demo.bronze_customers"])
def bronze_customers(context: AssetExecutionContext, catalog: PolarisCatalogResource) -> Dict[str, Any]:
    from floe_synthetic.generators.ecommerce import EcommerceGenerator
    generator = EcommerceGenerator(seed=42)
    customers = generator.generate_customers(count=1000)
    snapshot = catalog.write_table("demo.bronze_customers", customers)
    return {"rows": customers.num_rows, "snapshot_id": snapshot.snapshot_id}


@floe_asset(group_name="bronze", outputs=["demo.bronze_orders"], deps=["bronze_customers"])
def bronze_orders(context: AssetExecutionContext, catalog: PolarisCatalogResource) -> Dict[str, Any]:
    from floe_synthetic.generators.ecommerce import EcommerceGenerator
    generator = EcommerceGenerator(seed=42)
    generator.generate_customers(count=1000)
    orders = generator.generate_orders(count=5000)
    snapshot = catalog.write_table("demo.bronze_orders", orders)
    return {"rows": orders.num_rows, "snapshot_id": snapshot.snapshot_id}


# Jobs and schedules
bronze_job = define_asset_job(name="bronze_pipeline", selection="*bronze*")
daily_refresh = ScheduleDefinition(name="daily_refresh", job=bronze_job, cron_schedule="0 6 * * *")

# One-line wiring
defs = FloeDefinitions.from_compiled_artifacts(
    assets=[bronze_customers, bronze_orders],
    jobs=[bronze_job],
    schedules=[daily_refresh],
)
```

## Next Steps

1. **Add more assets**: Follow the same pattern for products, order items, etc.
2. **Add dbt models**: Create staging and mart transformations
3. **Add data quality**: Use dbt tests or Great Expectations
4. **Deploy to Kubernetes**: Same code, different `platform.yaml`

## Comparison: Traditional vs floe-runtime

### Traditional dbt + Dagster Setup

```python
# 1. profiles.yml (external file, contains credentials)
# 2. dbt_project.yml
# 3. Dagster resource configuration
# 4. OpenTelemetry setup (~30 lines)
# 5. OpenLineage setup (~20 lines)
# 6. Asset with manual tracing
# 7. Manual table management
# Total: 100-150 lines, 3+ files, credentials exposed
```

### floe-runtime Setup

```python
# 1. floe.yaml (no credentials)
# 2. definitions.py (~50 lines)
# Total: 50 lines, 2 files, zero credentials
```

## Architecture

```
Data Engineer (you)              Platform Engineer (them)
       │                                  │
       ▼                                  ▼
   floe.yaml ─────────────────────► platform.yaml
   (pipelines)                      (infrastructure)
       │                                  │
       └──────────► floe compile ◄────────┘
                         │
                         ▼
               CompiledArtifacts
                         │
                         ▼
               FloeDefinitions
              (batteries-included)
```

**Key principle**: You write business logic. Platform team handles infrastructure. The two never mix.
