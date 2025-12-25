# Quickstart: Orchestration Auto-Discovery

**Purpose**: Get started with declarative orchestration in 5 minutes
**Audience**: Data Engineers
**Prerequisites**: floe-runtime installed, basic familiarity with Dagster and dbt

## What is Orchestration Auto-Discovery?

Orchestration auto-discovery eliminates 200+ lines of Python boilerplate by enabling declarative pipeline configuration directly in your `floe.yaml` file. Instead of manually registering assets, jobs, schedules, and sensors in Python code, you define them in configuration and let Floe auto-discover and load everything.

⚠️ **CRITICAL - Two-Tier Configuration**: This feature maintains strict separation between:
- **floe.yaml** (data engineers): Asset modules, schedules, LOCAL paths, logical references
- **platform.yaml** (platform engineers): Infrastructure, endpoints, credentials, storage configs

**Data engineers NEVER see infrastructure details.**

**Key Benefits:**
- **95% LOC reduction**: Replace 200+ lines of Python with <50 lines of YAML
- **Per-model observability**: dbt models become individual assets with their own traces and lineage
- **Declarative configuration**: Define jobs, schedules, and sensors without writing Python
- **Auto-discovery**: Assets are loaded automatically from module files
- **Environment portability**: Same config works across dev/staging/prod

## Before & After

**Before** (200+ lines of Python boilerplate):
```python
# definitions.py - Manual asset registration
from dagster import define_asset_job, ScheduleDefinition

@floe_asset(group_name="bronze")
def bronze_customers(context, catalog):
    # Asset implementation...

@floe_asset(group_name="silver", deps=["bronze_customers"])
def silver_staging(context, dbt):
    # Wrapper asset hiding individual dbt models...

demo_bronze_job = define_asset_job(
    name="demo_bronze",
    selection=AssetSelection.groups("bronze")
)

bronze_refresh_schedule = ScheduleDefinition(
    name="bronze_refresh_schedule",
    job=demo_bronze_job,
    cron_schedule="*/5 * * * *"
)

defs = FloeDefinitions.from_compiled_artifacts(
    assets=[bronze_customers, bronze_products, silver_staging, gold_marts],
    jobs=[demo_bronze_job, demo_pipeline_job],
    schedules=[bronze_refresh_schedule, transform_pipeline_schedule],
    sensors=[file_arrival_sensor]
)
```

**After** (<50 lines of YAML):
```yaml
# floe.yaml - Declarative orchestration
orchestration:
  asset_modules:
    - "demo.assets.bronze"
    - "demo.assets.gold"

  dbt:
    manifest_path: "target/manifest.json"
    observability_level: "per_model"

  jobs:
    bronze_refresh:
      type: "batch"
      selection: ["group:bronze"]

  schedules:
    daily_bronze:
      job: "bronze_refresh"
      cron_schedule: "0 6 * * *"
      enabled: "${SCHEDULE_ENABLED:true}"
```

## Quick Start (5 minutes)

### Step 1: Add Orchestration Section to floe.yaml

Add the `orchestration` section to your existing `floe.yaml`:

```yaml
# floe.yaml
name: my-pipeline
version: "1.0.0"

storage: default
catalog: default
compute: default

# Add this orchestration section
orchestration:
  # Auto-discover assets from these modules
  asset_modules:
    - "my_pipeline.assets.bronze"
    - "my_pipeline.assets.gold"

  # Auto-load dbt models as individual assets
  dbt:
    manifest_path: "target/manifest.json"
    observability_level: "per_model"

  # Define jobs declaratively
  jobs:
    bronze_load:
      type: "batch"
      selection: ["group:bronze"]
      description: "Load bronze layer data"

    full_pipeline:
      type: "batch"
      selection: ["group:bronze", "group:silver", "group:gold"]
      description: "Run complete data pipeline"

  # Define schedules declaratively
  schedules:
    daily_refresh:
      job: "bronze_load"
      cron_schedule: "0 6 * * *"
      timezone: "UTC"
      enabled: true
```

### Step 2: Create Asset Module Files

Organize your assets into separate module files by layer:

```bash
mkdir -p my_pipeline/assets
```

Create `my_pipeline/assets/bronze.py`:
```python
from dagster import AssetExecutionContext
from floe_dagster import floe_asset
from floe_dagster.resources import CatalogResource
from typing import Dict, Any

@floe_asset(
    group_name="bronze",
    description="Load customer data from raw to bronze",
    inputs=["raw.customers"],
    outputs=["bronze.customers"],
    compute_kind="python"
)
def bronze_customers(
    context: AssetExecutionContext,
    catalog: CatalogResource,
) -> Dict[str, Any]:
    """Load customer data from raw to bronze layer."""
    raw_data = catalog.read_table("raw.customers")
    snapshot = catalog.write_table("bronze.customers", raw_data)
    return {"rows": raw_data.num_rows, "snapshot_id": snapshot.snapshot_id}

@floe_asset(
    group_name="bronze",
    description="Load order data from raw to bronze",
    inputs=["raw.orders"],
    outputs=["bronze.orders"],
    compute_kind="python",
    deps=["bronze_customers"]
)
def bronze_orders(
    context: AssetExecutionContext,
    catalog: CatalogResource,
) -> Dict[str, Any]:
    """Load order data from raw to bronze layer."""
    raw_data = catalog.read_table("raw.orders")
    snapshot = catalog.write_table("bronze.orders", raw_data)
    return {"rows": raw_data.num_rows, "snapshot_id": snapshot.snapshot_id}
```

### Step 3: Simplify Your Definitions File

Replace your complex `definitions.py` with a simple factory call:

```python
# definitions.py - Simple factory call
from floe_dagster import FloeDefinitions

# Auto-loads assets from orchestration config
defs = FloeDefinitions.from_compiled_artifacts(
    namespace="my_pipeline"
)
```

### Step 4: Run the Pipeline

Compile and run:
```bash
# Compile floe.yaml to generate dbt manifest
floe compile

# Start Dagster with auto-discovered orchestration
dagster dev
```

**That's it!** Your assets, jobs, and schedules are now auto-discovered and visible in the Dagster UI.

## Asset Organization

### Recommended Structure

Organize assets by layer or concern in separate module files:

```
my_pipeline/
├── assets/
│   ├── __init__.py
│   ├── bronze.py      # Bronze layer assets
│   ├── gold.py        # Gold layer assets
│   └── ops.py         # Operational/maintenance assets
├── orchestration/
│   └── definitions.py # Simple factory call
└── floe.yaml         # Orchestration config
```

### Example Asset Module (assets/gold.py)

```python
from dagster import AssetExecutionContext
from floe_dagster import floe_asset
from floe_dagster.resources import CatalogResource
from typing import Dict, Any

@floe_asset(
    group_name="gold",
    description="Customer order summary for analytics",
    inputs=["silver.customers", "silver.orders"],
    outputs=["gold.customer_orders"],
    compute_kind="python"
)
def gold_customer_orders(
    context: AssetExecutionContext,
    catalog: CatalogResource,
) -> Dict[str, Any]:
    """Create customer order summary for analytics."""
    customers = catalog.read_table("silver.customers")
    orders = catalog.read_table("silver.orders")

    # Join and aggregate data
    summary = customers.join(orders, "customer_id").group_by("customer_id")
    snapshot = catalog.write_table("gold.customer_orders", summary)

    return {"rows": summary.num_rows, "snapshot_id": snapshot.snapshot_id}
```

### Using the @floe_asset Decorator

The `@floe_asset` decorator provides:
- **Automatic observability**: Traces and lineage without boilerplate
- **Metadata support**: Group, description, compute kind
- **Dependency declaration**: Via `deps` parameter
- **Input/output specification**: For lineage tracking

```python
@floe_asset(
    group_name="bronze",           # Asset group for job selection
    description="Load data...",    # Asset description
    inputs=["raw.table"],          # Input tables for lineage
    outputs=["bronze.table"],      # Output tables for lineage
    compute_kind="python",         # Compute resource type
    deps=["upstream_asset"]        # Asset dependencies
)
def my_asset(context, catalog):
    # Asset implementation
```

## dbt Integration

### Per-Model Observability

When you configure dbt auto-discovery, each dbt model becomes an individual asset:

```yaml
orchestration:
  dbt:
    manifest_path: "target/manifest.json"
    observability_level: "per_model"  # Individual assets per model
```

**Before** (wrapper asset):
- Single `silver_staging` asset containing all staging models
- No visibility into individual model execution
- No per-model lineage tracking

**After** (per-model assets):
- Individual assets: `stg_customers`, `stg_orders`, `stg_products`, `stg_order_items`
- Per-model execution status and logs
- Detailed lineage from bronze → specific staging model → gold

### dbt Configuration Options

```yaml
dbt:
  manifest_path: "${DBT_MANIFEST_PATH:target/manifest.json}"
  observability_level: "per_model"  # or "job_level"
  project_dir: "dbt_project"
  profiles_dir: "~/.dbt"
  target: "${DBT_TARGET:dev}"
```

### Example dbt Project Structure

```
dbt_project/
├── models/
│   ├── staging/
│   │   ├── stg_customers.sql     # Becomes individual asset
│   │   ├── stg_orders.sql        # Becomes individual asset
│   │   └── stg_products.sql      # Becomes individual asset
│   └── marts/
│       ├── customer_orders.sql   # Becomes individual asset
│       └── revenue_by_product.sql # Becomes individual asset
└── target/
    └── manifest.json             # Auto-loaded by Floe
```

## Jobs & Scheduling

### Job Types

**Batch Jobs** - Select and execute assets:
```yaml
jobs:
  bronze_load:
    type: "batch"
    selection:
      - "group:bronze"              # All bronze assets
      - "asset:external_data"       # Specific asset
    description: "Load bronze layer data"

  gold_pipeline:
    type: "batch"
    selection:
      - "group:gold"
      - "+customer_orders"          # Include upstream dependencies
      - "revenue_by_product+"       # Include downstream dependencies
    description: "Generate gold analytics"
```

**Ops Jobs** - Execute maintenance functions:
```yaml
jobs:
  vacuum_tables:
    type: "ops"
    target_function: "my_pipeline.ops.vacuum.vacuum_old_snapshots"
    args:
      retention_days: "${VACUUM_RETENTION:30}"
      dry_run: false
    description: "Clean up old table snapshots"
```

### Schedule Configuration

```yaml
schedules:
  # Daily bronze refresh
  daily_bronze:
    job: "bronze_load"
    cron_schedule: "0 6 * * *"            # 6 AM UTC
    timezone: "America/New_York"
    enabled: "${SCHEDULE_ENABLED:true}"
    description: "Daily bronze data refresh"

  # Weekly maintenance
  weekly_vacuum:
    job: "vacuum_tables"
    cron_schedule: "0 2 * * 0"            # Sunday 2 AM
    enabled: true
    description: "Weekly table maintenance"

  # Hourly incremental
  hourly_incremental:
    job: "gold_pipeline"
    cron_schedule: "0 * * * *"            # Every hour
    partition_selector: "latest"           # Only latest partition
```

### Environment-Specific Scheduling

Use environment variables for per-environment control:
```yaml
schedules:
  production_job:
    job: "full_pipeline"
    cron_schedule: "${PROD_SCHEDULE:0 6 * * *}"  # 6 AM in prod
    enabled: "${PROD_ENABLED:false}"             # Disabled by default
```

Set environment variables per environment:
```bash
# Production
export PROD_SCHEDULE="0 6 * * *"
export PROD_ENABLED="true"

# Development
export PROD_SCHEDULE="0 */4 * * *"  # Every 4 hours
export PROD_ENABLED="false"         # Manual execution only
```

## Partitions & Backfills

### Time-Based Partitions

```yaml
partitions:
  daily_partition:
    type: "time_window"
    start: "2024-01-01"
    cron_schedule: "0 0 * * *"      # Daily at midnight
    timezone: "UTC"
    fmt: "%Y-%m-%d"

  hourly_partition:
    type: "time_window"
    start: "2024-01-01"
    cron_schedule: "0 * * * *"      # Every hour
    timezone: "America/New_York"

# Apply to assets
assets:
  "bronze_*":
    partitions: "daily_partition"
    automation_condition: "eager"   # Update when upstream changes

  "streaming_*":
    partitions: "hourly_partition"
    automation_condition: "on_missing"  # Backfill missing partitions
```

### Static Partitions

```yaml
partitions:
  regional_partition:
    type: "static"
    partition_keys: ["us-east", "us-west", "eu-central", "ap-southeast"]

assets:
  "regional_*":
    partitions: "regional_partition"
```

### Multi-Dimensional Partitions

```yaml
partitions:
  daily_regional:
    type: "multi"
    partitions:
      date:
        type: "time_window"
        start: "2024-01-01"
        cron_schedule: "0 0 * * *"
      region:
        type: "static"
        partition_keys: ["us", "eu", "ap"]

assets:
  "sales_*":
    partitions: "daily_regional"
```

### Backfill Configuration

```yaml
backfills:
  historical_2024:
    job: "bronze_load"
    partition_range:
      start: "2024-01-01"
      end: "2024-12-31"
    batch_size: 5                   # Process 5 partitions at a time
    description: "Backfill 2024 historical data"
```

## Event-Driven Pipelines

### File Watcher Sensors

```yaml
sensors:
  data_arrival_trigger:
    type: "file_watcher"
    job: "bronze_load"
    path: "./incoming/"                    # LOCAL path only (no S3/HTTP)
    pattern: "customers_*.csv"
    poll_interval_seconds: 60
    description: "Trigger when customer data files arrive"
```

### Asset Materialization Sensors

```yaml
sensors:
  gold_dependency_trigger:
    type: "asset_sensor"
    job: "gold_pipeline"
    watched_assets:
      - "bronze_customers"
      - "bronze_orders"
    description: "Trigger gold pipeline when bronze assets update"
```

### Run Status Sensors

```yaml
sensors:
  failure_notification:
    type: "run_status"
    job: "send_alert"
    watched_jobs:
      - "bronze_load"
      - "gold_pipeline"
    status: "FAILURE"
    description: "Send alert when pipelines fail"
```

### Custom Sensors

```python
# my_pipeline/sensors/custom.py
def check_local_file_condition(context, **kwargs):
    """Custom sensor logic using LOCAL resources only."""
    file_path = kwargs.get("file_path", "./status/ready.flag")
    threshold = kwargs.get("threshold", 1000)

    # Check local file condition (no external endpoints)
    if file_exists_and_meets_condition(file_path, threshold):
        return RunRequest(run_key=f"local_trigger_{context.cursor}")
    return None
```

```yaml
sensors:
  local_condition_sensor:
    type: "custom"
    job: "special_process"
    target_function: "my_pipeline.sensors.custom.check_local_file_condition"
    args:
      file_path: "./status/ready.flag"      # LOCAL path only
      threshold: 1000
    poll_interval_seconds: 120
```

## Complete Example

Here's a complete `floe.yaml` with orchestration auto-discovery:

```yaml
# floe.yaml - Complete orchestration example
name: e-commerce-pipeline
version: "1.0.0"

storage: default
catalog: default
compute: default

transforms:
  - type: dbt
    path: "."
    target: prod

orchestration:
  # Asset auto-discovery
  asset_modules:
    - "ecommerce.assets.bronze"
    - "ecommerce.assets.gold"
    - "ecommerce.assets.ops"

  # dbt per-model assets
  dbt:
    manifest_path: "target/manifest.json"
    observability_level: "per_model"

  # Partition definitions
  partitions:
    daily_partition:
      type: "time_window"
      start: "2024-01-01"
      cron_schedule: "0 0 * * *"
      timezone: "UTC"

    regional_partition:
      type: "static"
      partition_keys: ["us-east", "us-west", "eu-central"]

  # Asset configurations
  assets:
    "bronze_*":
      partitions: "daily_partition"
      automation_condition: "eager"
      group_name: "bronze"

    "gold_*":
      partitions: "daily_partition"
      automation_condition: "on_cron"
      group_name: "gold"

  # Job definitions
  jobs:
    bronze_refresh:
      type: "batch"
      selection: ["group:bronze"]
      description: "Refresh bronze layer data"

    full_pipeline:
      type: "batch"
      selection: ["group:bronze", "group:silver", "group:gold"]
      description: "Complete e-commerce data pipeline"

    weekly_vacuum:
      type: "ops"
      target_function: "ecommerce.ops.maintenance.vacuum_old_snapshots"
      args:
        retention_days: "${VACUUM_RETENTION:30}"
      description: "Clean up old snapshots"

  # Schedule definitions
  schedules:
    daily_bronze:
      job: "bronze_refresh"
      cron_schedule: "0 6 * * *"
      timezone: "America/New_York"
      enabled: "${BRONZE_SCHEDULE_ENABLED:true}"

    weekly_maintenance:
      job: "weekly_vacuum"
      cron_schedule: "0 2 * * 0"
      enabled: true

  # Sensor definitions
  sensors:
    data_arrival:
      type: "file_watcher"
      job: "bronze_refresh"
      path: "./incoming/"               # LOCAL path only
      pattern: "*_data_*.csv"
      poll_interval_seconds: 60

    gold_trigger:
      type: "asset_sensor"
      job: "full_pipeline"
      watched_assets: ["bronze_customers", "bronze_orders"]

  # Backfill definitions
  backfills:
    historical_2024:
      job: "bronze_refresh"
      partition_range:
        start: "2024-01-01"
        end: "2024-12-31"
      batch_size: 10
```

### Demo Asset Module (ecommerce/assets/bronze.py)

```python
from dagster import AssetExecutionContext
from floe_dagster import floe_asset
from floe_dagster.resources import CatalogResource
from typing import Dict, Any

@floe_asset(
    group_name="bronze",
    description="Load customer data from external source",
    inputs=["external.customers"],
    outputs=["bronze.customers"],
    compute_kind="python"
)
def bronze_customers(
    context: AssetExecutionContext,
    catalog: CatalogResource,
) -> Dict[str, Any]:
    """Load and validate customer data into bronze layer."""
    context.log.info("Loading customer data...")

    # Extract
    raw_data = catalog.read_table("external.customers")
    context.log.info(f"Extracted {raw_data.num_rows} customer records")

    # Transform (basic validation)
    validated_data = raw_data.filter(
        raw_data.customer_id.is_not_null() &
        raw_data.email.contains("@")
    )

    # Load
    snapshot = catalog.write_table("bronze.customers", validated_data)
    context.log.info(f"Loaded {validated_data.num_rows} validated records")

    return {
        "raw_rows": raw_data.num_rows,
        "validated_rows": validated_data.num_rows,
        "snapshot_id": snapshot.snapshot_id,
        "table_location": snapshot.metadata.table_metadata.location
    }
```

### Simplified Definitions File

```python
# ecommerce/orchestration/definitions.py
"""Dagster definitions with auto-discovery."""
from floe_dagster import FloeDefinitions

# Auto-loads everything from floe.yaml orchestration section
defs = FloeDefinitions.from_compiled_artifacts(
    namespace="ecommerce"
)
```

## Two-Tier Configuration Architecture

### What Goes Where?

**floe.yaml** (Data Engineer scope):
```yaml
# ✅ ALLOWED in floe.yaml
orchestration:
  asset_modules: ["demo.assets.bronze"]      # Python import paths
  schedules:
    daily: {job: "refresh", cron_schedule: "0 6 * * *"}
  sensors:
    file_watch: {path: "./incoming/", pattern: "*.csv"}  # LOCAL paths only
  partitions:
    daily: {type: "time_window", start: "2024-01-01"}
```

**platform.yaml** (Platform Engineer scope):
```yaml
# ✅ PLATFORM CONCERNS (NOT in floe.yaml)
observability:
  otlp_endpoint: "http://otel-collector:4317"    # Infrastructure
  lineage_endpoint: "http://marquez:5000"        # Infrastructure
storage:
  default:
    type: s3
    bucket: "data-lake-prod"                     # Infrastructure
    endpoint: "s3.amazonaws.com"                 # Infrastructure
```

**❌ VIOLATIONS - Never in floe.yaml:**
- S3 bucket names, endpoints, or credentials
- OTLP/OpenLineage endpoints or infrastructure URLs
- Database connection strings or service URLs
- Cloud provider regions or zones
- Service discovery configurations

## End-to-End Workflow

1. **Configuration**: Define orchestration in `floe.yaml` (logical only)
2. **Platform Setup**: Platform engineers configure infrastructure in `platform.yaml`
3. **Assets**: Organize in module files by layer/concern
4. **Compilation**: Run `floe compile` to generate dbt manifest
5. **Deployment**: Start with `dagster dev` or deploy to production
6. **Execution**: Jobs run automatically via schedules/sensors or manually
7. **Observability**: View per-asset traces in Jaeger, lineage in Marquez

**Benefits Achieved**:
- ✅ 95% reduction in Python boilerplate (200+ → <50 lines)
- ✅ Per-model dbt observability with individual spans
- ✅ Complete lineage tracking: bronze → staging models → marts
- ✅ Environment-portable configuration via environment variables
- ✅ Declarative job and schedule management
- ✅ Event-driven pipeline automation

**Next Steps**:
- Add partitioned processing for incremental data loads
- Configure sensors for real-time event-driven execution
- Set up ops jobs for automated maintenance tasks
- Implement multi-environment deployment with environment-specific overrides