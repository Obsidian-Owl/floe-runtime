# Dagster API Reference

> **Current Version**: Dagster 1.x (as of 2025)
>
> **Documentation**: https://docs.dagster.io
>
> **Python Support**: 3.9 - 3.13

## Core Concepts

### Software-Defined Assets

Assets represent logical data units (tables, datasets, ML models) with dependency tracking.

**Basic Asset**:
```python
from dagster import asset

@asset
def my_table():
    """Materialize my_table asset."""
    return some_dataframe
```

**Asset with Dependencies**:
```python
@asset
def downstream_table(my_table):
    """Depends on my_table."""
    return transform(my_table)
```

**Multi-Asset** (shared computation):
```python
from dagster import multi_asset, AssetOut

@multi_asset(
    outs={
        "table_a": AssetOut(),
        "table_b": AssetOut(),
    }
)
def compute_tables():
    """Materialize multiple assets from single computation."""
    return table_a, table_b
```

## Resources

Resources provide external services (databases, APIs, storage) to assets.

**ConfigurableResource** (recommended for v1.x):
```python
from dagster import ConfigurableResource
from pydantic import Field

class DatabaseResource(ConfigurableResource):
    """Database connection resource."""
    host: str
    port: int = Field(default=5432)

    def query(self, sql: str):
        # Implementation
        pass
```

**Binding Resources to Assets**:
```python
from dagster import Definitions

defs = Definitions(
    assets=[my_table, downstream_table],
    resources={
        "database": DatabaseResource(host="localhost"),
    }
)
```

## IO Managers

IO managers control how asset data is stored and retrieved.

**Custom IO Manager**:
```python
from dagster import IOManager

class MyIOManager(IOManager):
    def handle_output(self, context, obj):
        """Store asset output."""
        # Write obj to storage
        pass

    def load_input(self, context):
        """Load asset input."""
        # Read from storage
        return data
```

**Attaching IO Manager**:
```python
from dagster import Definitions

defs = Definitions(
    assets=[my_table],
    resources={
        "io_manager": MyIOManager(),
    }
)
```

## Schedules

Time-based automation of asset materialization.

**Schedule Decorator**:
```python
from dagster import schedule, RunRequest

@schedule(cron_schedule="0 9 * * 1", job=my_job)
def monday_schedule():
    """Run every Monday at 9am."""
    return RunRequest()
```

**Asset-based Schedule**:
```python
from dagster import AssetSelection, define_asset_job, ScheduleDefinition

daily_job = define_asset_job("daily_job", selection=AssetSelection.all())
daily_schedule = ScheduleDefinition(job=daily_job, cron_schedule="0 0 * * *")
```

## Sensors

Event-based automation of asset materialization.

**Sensor Decorator**:
```python
from dagster import sensor, RunRequest

@sensor(job=my_job)
def file_sensor(context):
    """Trigger when file appears."""
    if file_exists():
        yield RunRequest()
```

**Asset Sensor** (monitor asset materializations):
```python
from dagster import asset_sensor, AssetKey

@asset_sensor(asset_key=AssetKey("upstream_table"), job=downstream_job)
def react_to_upstream(context):
    """Trigger when upstream_table materializes."""
    yield RunRequest()
```

## dbt Integration

**dagster-dbt** library provides dbt integration.

**Load Assets from dbt Project**:
```python
from dagster_dbt import DbtProject, load_assets_from_dbt_project

dbt_project = DbtProject(project_dir="path/to/dbt/project")
dbt_assets = load_assets_from_dbt_project(dbt_project)
```

**Load Assets from Manifest**:
```python
from dagster_dbt import load_assets_from_dbt_manifest

dbt_assets = load_assets_from_dbt_manifest(
    manifest_json=dbt_manifest_path
)
```

**DbtCliResource** (execute dbt commands):
```python
from dagster_dbt import DbtCliResource

dbt_resource = DbtCliResource(
    project_dir="path/to/dbt/project",
    profiles_dir="path/to/profiles",
    target="dev"
)
```

## Partitions

Partition assets by time or dimension.

**Daily Partitions**:
```python
from dagster import asset, DailyPartitionsDefinition

daily_partitions = DailyPartitionsDefinition(start_date="2025-01-01")

@asset(partitions_def=daily_partitions)
def daily_table(context):
    """Partitioned by day."""
    partition_key = context.partition_key  # "2025-01-15"
    return compute_for_date(partition_key)
```

**Static Partitions**:
```python
from dagster import StaticPartitionsDefinition

partitions = StaticPartitionsDefinition(["us", "eu", "asia"])

@asset(partitions_def=partitions)
def regional_table(context):
    """Partitioned by region."""
    region = context.partition_key
    return compute_for_region(region)
```

## Metadata

Attach metadata to assets for observability.

**Asset Metadata**:
```python
from dagster import asset, MetadataValue

@asset(
    metadata={
        "description": "Customer dimension table",
        "owner": "data-team",
        "pii": True,
    }
)
def customers():
    return dataframe
```

**Runtime Metadata** (computed during materialization):
```python
from dagster import Output, MetadataValue

@asset
def my_table(context):
    df = compute()

    return Output(
        df,
        metadata={
            "row_count": MetadataValue.int(len(df)),
            "columns": MetadataValue.text(str(df.columns.tolist())),
        }
    )
```

## Definitions

Top-level object that bundles assets, resources, schedules, sensors.

**Definitions**:
```python
from dagster import Definitions

defs = Definitions(
    assets=[table_a, table_b],
    resources={
        "database": DatabaseResource(host="localhost"),
        "io_manager": MyIOManager(),
    },
    schedules=[daily_schedule],
    sensors=[file_sensor],
)
```

## Key Patterns

### Asset Dependencies

**Implicit** (function parameter name matches asset name):
```python
@asset
def upstream():
    return data

@asset
def downstream(upstream):  # Depends on 'upstream' asset
    return transform(upstream)
```

**Explicit** (using `AssetIn`):
```python
from dagster import AssetIn

@asset(ins={"input_data": AssetIn("upstream")})
def downstream(input_data):
    return transform(input_data)
```

### Asset Selection

Select subsets of assets for jobs or schedules:

```python
from dagster import AssetSelection, define_asset_job

# All assets
all_job = define_asset_job("all", selection=AssetSelection.all())

# By key
specific_job = define_asset_job("specific", selection=AssetSelection.keys("table_a"))

# By group
group_job = define_asset_job("group", selection=AssetSelection.groups("analytics"))

# Upstream/downstream
upstream_job = define_asset_job(
    "upstream",
    selection=AssetSelection.keys("table_a").upstream()
)
```

### Asset Groups

Organize assets into logical groups:

```python
@asset(group_name="analytics")
def analytics_table():
    return data

@asset(group_name="ml")
def ml_features():
    return features
```

## Testing

**Unit Testing Assets**:
```python
from dagster import materialize

def test_my_asset():
    result = materialize([my_asset])
    assert result.success

    # Access materialized output
    output = result.output_for_node("my_asset")
    assert len(output) > 0
```

**Testing with Resources**:
```python
def test_asset_with_resources():
    result = materialize(
        [my_asset],
        resources={"database": DatabaseResource(host="test-db")}
    )
    assert result.success
```

## Development Commands

```bash
# Install Dagster
pip install dagster dagster-webserver dagster-dbt

# Verify installation
dagster --version

# Run development server
dagster dev

# Materialize assets
dagster asset materialize
dagster asset materialize --select asset_name

# List assets
dagster asset list
```

## Important Version Notes

- **Dagster 1.x**: Major API stabilization, `ConfigurableResource` recommended
- **Python Support**: 3.9 - 3.13 (as of 2025)
- **dagster-dbt**: Separate package for dbt integration
- **Breaking Changes**: v0.x → v1.x had significant API changes

## References

- [Dagster Docs](https://docs.dagster.io)
- [Software-Defined Assets](https://docs.dagster.io/concepts/assets/software-defined-assets)
- [Resources API](https://docs.dagster.io/api/dagster/resources)
- [IO Managers API](https://docs.dagster.io/api/python-api/io-managers)
- [dagster-dbt](https://docs.dagster.io/_apidocs/libraries/dagster-dbt)
- [GitHub Repository](https://github.com/dagster-io/dagster)
