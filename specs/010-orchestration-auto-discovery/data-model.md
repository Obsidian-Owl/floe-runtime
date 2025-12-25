# Data Model: Orchestration Auto-Discovery

**Feature Branch**: `010-orchestration-auto-discovery`
**Created**: 2025-12-26
**Related Documents**:
- [Feature Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Research Document](./research.md)

## Overview

This document defines the data model for the orchestration auto-discovery feature that eliminates 200+ lines of boilerplate by enabling declarative pipeline configuration. The model uses Pydantic v2 for validation and supports environment variable interpolation with `${VAR:default}` syntax.

⚠️ **CRITICAL - Two-Tier Configuration Architecture**: This orchestration config is strictly for **data engineers** and contains ONLY logical references. Infrastructure details belong in `platform.yaml`:

**floe.yaml** (Data Engineer scope):
- ✅ Asset modules (Python import paths)
- ✅ Job definitions and schedules (logical)
- ✅ LOCAL file paths for sensors (./data/, /tmp/)
- ✅ Partition definitions (time windows, static values)

**platform.yaml** (Platform Engineer scope):
- ❌ Infrastructure endpoints (OTLP, S3, HTTP)
- ❌ Credentials and connection strings
- ❌ Cloud storage buckets and regions
- ❌ Service discovery configurations

**Data engineers NEVER see infrastructure details.**

## Entity Relationship Diagram

```mermaid
graph TB
    OC[OrchestrationConfig] --> AM[asset_modules: List[str]]
    OC --> DBT[dbt: DbtConfig]
    OC --> PD[partitions: Dict[str, PartitionDefinition]]
    OC --> AC[assets: Dict[str, AssetConfig]]
    OC --> JD[jobs: Dict[str, JobDefinition]]
    OC --> SD[schedules: Dict[str, ScheduleDefinition]]
    OC --> SE[sensors: Dict[str, SensorDefinition]]
    OC --> BD[backfills: Dict[str, BackfillDefinition]]

    PD --> TPD[TimeWindowPartition]
    PD --> SPD[StaticPartition]
    PD --> MPD[MultiPartition]
    PD --> DPD[DynamicPartition]

    JD --> BJD[BatchJob]
    JD --> OJD[OpsJob]

    SE --> FWS[FileWatcherSensor]
    SE --> AS[AssetSensor]
    SE --> RSS[RunStatusSensor]
    SE --> CS[CustomSensor]

    SD --> JD
    SE --> JD
    BD --> JD
    AC --> PD
```

---

## Entity: OrchestrationConfig

**Purpose**: Top-level orchestration configuration that extends floe.yaml with declarative pipeline orchestration capabilities.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| asset_modules | List[str] | No | Python module paths for asset auto-discovery | Valid module paths |
| dbt | DbtConfig \| None | No | dbt integration configuration | Valid DbtConfig schema |
| partitions | Dict[str, PartitionDefinition] | No | Named partition definitions | Valid partition configs |
| assets | Dict[str, AssetConfig] | No | Pattern-based asset configurations | Valid asset patterns |
| jobs | Dict[str, JobDefinition] | No | Job definitions | Valid job configurations |
| schedules | Dict[str, ScheduleDefinition] | No | Schedule definitions | Valid schedule configurations |
| sensors | Dict[str, SensorDefinition] | No | Sensor definitions | Valid sensor configurations |
| backfills | Dict[str, BackfillDefinition] | No | Backfill definitions | Valid backfill configurations |

**Relationships**:
- Contains all orchestration entity definitions as named dictionaries
- Schedules, sensors, and backfills reference jobs by name
- Asset configurations reference partitions by name
- Environment variable interpolation applies to all nested fields

**Validation Rules**:
- All referenced job names must exist in the jobs dictionary
- All referenced partition names must exist in the partitions dictionary
- Module paths must be valid Python import paths
- Environment variable syntax `${VAR:default}` validated throughout

**Examples**:
```yaml
orchestration:
  asset_modules:
    - "demo.assets.bronze"
    - "demo.assets.gold"
    - "demo.assets.ops"

  dbt:
    manifest_path: "target/manifest.json"
    observability_level: "per_model"

  partitions:
    daily_partition:
      type: "time_window"
      start: "2024-01-01"
      cron_schedule: "0 0 * * *"
      timezone: "UTC"

  assets:
    "bronze_*":
      partitions: "daily_partition"
      automation_condition: "eager"

  jobs:
    bronze_refresh:
      type: "batch"
      selection:
        - "group:bronze"
      description: "Refresh bronze layer data"

  schedules:
    daily_bronze:
      job: "bronze_refresh"
      cron_schedule: "${BRONZE_CRON:0 6 * * *}"
      enabled: "${SCHEDULE_ENABLED:true}"
```

---

## Entity: DbtConfig

**Purpose**: Configuration for dbt integration with per-model observability support.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| manifest_path | str | Yes | Path to dbt manifest.json file | File exists, valid JSON |
| observability_level | str | No | "per_model" or "job_level" | Enum validation |
| project_dir | str | No | dbt project directory | Directory exists |
| profiles_dir | str | No | dbt profiles directory | Directory exists |
| target | str | No | dbt target name | Valid identifier |

**Relationships**:
- Used by OrchestrationConfig for dbt asset auto-discovery
- Creates individual assets for each model in manifest.json

**Validation Rules**:
- manifest_path must point to valid dbt manifest file
- observability_level defaults to "per_model"
- Paths support environment variable interpolation

**Examples**:
```yaml
dbt:
  manifest_path: "${DBT_MANIFEST_PATH:target/manifest.json}"
  observability_level: "per_model"
  project_dir: "dbt_project"
  target: "${DBT_TARGET:dev}"
```

---

## Entity: PartitionDefinition

**Purpose**: Defines partition schemes for incremental data processing with various partitioning strategies.

**Fields** (Union type with discriminated variants):

### TimeWindowPartition

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| type | Literal["time_window"] | Yes | Partition type identifier | Must be "time_window" |
| start | str | Yes | Start date in YYYY-MM-DD format | Valid date format |
| cron_schedule | str | Yes | Cron expression for partition frequency | Valid cron expression |
| timezone | str | No | Timezone for partition boundaries | Valid timezone, defaults to "UTC" |
| end | str \| None | No | End date in YYYY-MM-DD format | Valid date format or null |
| fmt | str \| None | No | Date format for partition keys | Valid strftime format |

### StaticPartition

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| type | Literal["static"] | Yes | Partition type identifier | Must be "static" |
| partition_keys | List[str] | Yes | Static partition key values | Non-empty list, unique values |

### MultiPartition

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| type | Literal["multi"] | Yes | Partition type identifier | Must be "multi" |
| partitions | Dict[str, PartitionDefinition] | Yes | Named sub-partition definitions | Valid partition definitions |

### DynamicPartition

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| type | Literal["dynamic"] | Yes | Partition type identifier | Must be "dynamic" |
| fn | str \| None | No | Function name for dynamic partition generation | Valid function reference |

**Relationships**:
- Referenced by AssetConfig to apply partitioning to asset patterns
- Used by BackfillDefinition to define partition ranges
- MultiPartition can contain nested partition definitions

**Validation Rules**:
- TimeWindowPartition: cron_schedule must match time window frequency
- StaticPartition: partition_keys must be non-empty and contain unique values
- MultiPartition: all sub-partitions must be valid PartitionDefinitions
- Environment variable interpolation supported in all string fields

**State Transitions**:
- Partition definitions are immutable once applied to materialized assets
- Changing partition scheme requires backfill or asset recreation

**Examples**:
```yaml
# Daily time-based partitioning
daily_partition:
  type: "time_window"
  start: "2024-01-01"
  cron_schedule: "0 0 * * *"  # Daily at midnight
  timezone: "America/New_York"

# Static regional partitioning
regional_partition:
  type: "static"
  partition_keys: ["us-east", "us-west", "eu-central"]

# Multi-dimensional partitioning
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

# Dynamic partitioning
customer_partition:
  type: "dynamic"
  fn: "get_active_customers"
```

---

## Entity: AssetConfig

**Purpose**: Pattern-based configuration that applies partitions, automation conditions, and policies to matching assets.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| partitions | str \| None | No | Reference to named partition definition | Must exist in partitions dict |
| automation_condition | str \| None | No | Asset automation condition | Valid condition type |
| backfill_policy | str \| None | No | Backfill policy for the asset | Valid policy type |
| compute_kind | str \| None | No | Compute resource kind | Valid compute kind |
| group_name | str \| None | No | Asset group override | Valid identifier |

**Relationships**:
- Pattern key (dict key) matches against asset names using glob patterns
- References PartitionDefinition by name for partitioned assets
- Applied to assets discovered from modules or dbt

**Validation Rules**:
- Pattern keys support glob syntax: `*`, `?`, `[abc]`, `{a,b,c}`
- Referenced partition names must exist in the partitions dictionary
- automation_condition must be one of: "eager", "on_cron", "on_missing"
- Environment variable interpolation supported in all fields

**Examples**:
```yaml
assets:
  # Apply daily partitions to all bronze assets
  "bronze_*":
    partitions: "daily_partition"
    automation_condition: "eager"
    group_name: "bronze"

  # Configure gold layer assets
  "customer_*":
    partitions: "monthly_partition"
    automation_condition: "on_cron"
    compute_kind: "high_memory"

  # Ops assets with specific policies
  "ops_*":
    automation_condition: "on_missing"
    backfill_policy: "lazy"
```

---

## Entity: JobDefinition

**Purpose**: Defines executable jobs that group assets or operations for orchestration.

**Fields** (Union type with discriminated variants):

### BatchJob

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| type | Literal["batch"] | Yes | Job type identifier | Must be "batch" |
| selection | List[str] | Yes | Asset selection expressions | Valid selection syntax |
| description | str \| None | No | Job description | Max 500 characters |
| tags | Dict[str, str] \| None | No | Job metadata tags | Key-value pairs |

### OpsJob

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| type | Literal["ops"] | Yes | Job type identifier | Must be "ops" |
| target_function | str | Yes | Module.function to execute | Valid function reference |
| args | Dict[str, Any] \| None | No | Function arguments | Serializable values |
| description | str \| None | No | Job description | Max 500 characters |
| tags | Dict[str, str] \| None | No | Job metadata tags | Key-value pairs |

**Relationships**:
- Referenced by ScheduleDefinition, SensorDefinition, and BackfillDefinition
- BatchJob selections resolve to actual assets at runtime
- OpsJob target_function must be importable from the configured modules

**Validation Rules**:
- BatchJob: selection expressions must use valid syntax (group:name, asset:name, +asset, asset+)
- OpsJob: target_function must reference an existing callable
- Job names must be unique across the jobs dictionary
- Environment variable interpolation supported in all string fields

**Examples**:
```yaml
jobs:
  # Batch job selecting bronze assets
  bronze_refresh:
    type: "batch"
    selection:
      - "group:bronze"
      - "asset:external_data"
    description: "Refresh all bronze layer data sources"
    tags:
      layer: "bronze"
      priority: "high"

  # Ops job for maintenance
  vacuum_tables:
    type: "ops"
    target_function: "demo.ops.vacuum.vacuum_old_snapshots"
    args:
      retention_days: "${VACUUM_RETENTION_DAYS:30}"
      dry_run: false
    description: "Remove old table snapshots"

  # Complex asset selection
  gold_pipeline:
    type: "batch"
    selection:
      - "group:gold"
      - "+customer_orders"  # Include upstream dependencies
      - "revenue_by_product+"  # Include downstream dependencies
```

---

## Entity: ScheduleDefinition

**Purpose**: Defines cron-based schedules for automatic job execution.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| job | str | Yes | Reference to job name | Must exist in jobs dict |
| cron_schedule | str | Yes | Cron expression for schedule | Valid cron syntax |
| timezone | str | No | Schedule timezone | Valid timezone, defaults to "UTC" |
| enabled | bool | No | Whether schedule is active | Defaults to true |
| partition_selector | str \| None | No | Partition selection for partitioned jobs | "latest", "all", or custom |
| description | str \| None | No | Schedule description | Max 500 characters |

**Relationships**:
- References JobDefinition by name
- Applies to both batch and ops jobs
- Environment variable overrides enable per-environment scheduling

**Validation Rules**:
- job must exist in the jobs dictionary
- cron_schedule must be valid cron expression (5 or 6 fields)
- timezone must be valid IANA timezone name
- partition_selector only applies to jobs with partitioned assets

**State Transitions**:
- enabled: false → true (schedule activation)
- enabled: true → false (schedule deactivation)
- Schedule modifications require restart to take effect

**Examples**:
```yaml
schedules:
  # Daily bronze refresh at 6 AM
  daily_bronze:
    job: "bronze_refresh"
    cron_schedule: "0 6 * * *"
    timezone: "America/New_York"
    enabled: "${SCHEDULE_ENABLED:true}"
    partition_selector: "latest"
    description: "Daily bronze layer refresh"

  # Weekly maintenance
  weekly_vacuum:
    job: "vacuum_tables"
    cron_schedule: "0 2 * * 0"  # Sunday 2 AM
    enabled: true
    description: "Weekly table maintenance"

  # Hourly incremental processing
  hourly_gold:
    job: "gold_pipeline"
    cron_schedule: "0 * * * *"
    partition_selector: "latest"
```

---

## Entity: SensorDefinition

**Purpose**: Defines event-driven sensors that trigger jobs based on external conditions.

**Fields** (Union type with discriminated variants):

### FileWatcherSensor

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| type | Literal["file_watcher"] | Yes | Sensor type identifier | Must be "file_watcher" |
| job | str | Yes | Reference to job name | Must exist in jobs dict |
| path | str | Yes | Directory or file path to watch | Valid filesystem path |
| pattern | str | No | File name pattern to match | Valid regex pattern |
| poll_interval_seconds | int | No | Polling frequency | Positive integer, defaults to 30 |
| description | str \| None | No | Sensor description | Max 500 characters |

### AssetSensor

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| type | Literal["asset_sensor"] | Yes | Sensor type identifier | Must be "asset_sensor" |
| job | str | Yes | Reference to job name | Must exist in jobs dict |
| watched_assets | List[str] | Yes | Asset names to watch for materialization | Valid asset references |
| poll_interval_seconds | int | No | Polling frequency | Positive integer, defaults to 30 |
| description | str \| None | No | Sensor description | Max 500 characters |

### RunStatusSensor

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| type | Literal["run_status"] | Yes | Sensor type identifier | Must be "run_status" |
| job | str | Yes | Reference to job name | Must exist in jobs dict |
| watched_jobs | List[str] | Yes | Job names to watch for status changes | Valid job references |
| status | str | Yes | Status to watch for | "SUCCESS", "FAILURE", "STARTED" |
| poll_interval_seconds | int | No | Polling frequency | Positive integer, defaults to 30 |
| description | str \| None | No | Sensor description | Max 500 characters |

### CustomSensor

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| type | Literal["custom"] | Yes | Sensor type identifier | Must be "custom" |
| job | str | Yes | Reference to job name | Must exist in jobs dict |
| target_function | str | Yes | Module.function for sensor logic | Valid function reference |
| args | Dict[str, Any] \| None | No | Function arguments | Serializable values |
| poll_interval_seconds | int | No | Polling frequency | Positive integer, defaults to 30 |
| description | str \| None | No | Sensor description | Max 500 characters |

**Relationships**:
- All sensor types reference JobDefinition by name
- AssetSensor and RunStatusSensor reference other orchestration entities
- CustomSensor target_function must be importable

**Validation Rules**:
- job must exist in the jobs dictionary
- watched_assets must reference existing assets
- watched_jobs must reference existing jobs
- poll_interval_seconds must be positive
- Custom sensor function must be callable

**Examples**:
```yaml
sensors:
  # File arrival trigger (LOCAL path only)
  bronze_file_trigger:
    type: "file_watcher"
    job: "bronze_refresh"
    path: "./incoming/"                    # LOCAL path only (no S3/HTTP)
    pattern: "customers_*.csv"
    poll_interval_seconds: 60
    description: "Trigger bronze refresh when customer data arrives"

  # Asset materialization trigger
  gold_dependency_trigger:
    type: "asset_sensor"
    job: "gold_pipeline"
    watched_assets:
      - "bronze_customers"
      - "bronze_orders"
    description: "Trigger gold pipeline when bronze assets update"

  # Job failure notification
  failure_alert:
    type: "run_status"
    job: "send_alert"
    watched_jobs:
      - "bronze_refresh"
      - "gold_pipeline"
    status: "FAILURE"
    description: "Send alert on pipeline failures"

  # Custom sensor logic (LOCAL resources only)
  custom_trigger:
    type: "custom"
    job: "special_process"
    target_function: "demo.sensors.check_local_condition"
    args:
      file_path: "./status/ready.flag"     # LOCAL path only (no endpoints)
      threshold: 1000
```

---

## Entity: BackfillDefinition

**Purpose**: Defines historical backfill configurations for processing past data partitions.

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| job | str | Yes | Reference to job name | Must exist in jobs dict |
| partition_range | Dict[str, str] | Yes | Start and end partition keys | Valid partition range |
| batch_size | int | No | Max partitions per execution | Positive integer, defaults to 10 |
| description | str \| None | No | Backfill description | Max 500 characters |
| tags | Dict[str, str] \| None | No | Backfill metadata tags | Key-value pairs |

**Relationships**:
- References JobDefinition by name
- partition_range must align with job's asset partition definitions
- Used for historical data processing and recovery scenarios

**Validation Rules**:
- job must exist and reference partitioned assets
- partition_range start must be before or equal to end
- batch_size must be positive integer
- Partition keys must match the format of referenced partition definitions

**Examples**:
```yaml
backfills:
  # Historical data backfill
  bronze_2024_backfill:
    job: "bronze_refresh"
    partition_range:
      start: "2024-01-01"
      end: "2024-12-31"
    batch_size: 5
    description: "Backfill 2024 bronze data"
    tags:
      year: "2024"
      priority: "low"

  # Regional backfill
  eu_regional_backfill:
    job: "regional_process"
    partition_range:
      start: "eu-central"
      end: "eu-west"
    batch_size: 1
    description: "Backfill EU regional data"
```

---

## Validation Rules Summary

### Cross-Entity Validation

1. **Job References**: All job references in schedules, sensors, and backfills must exist
2. **Partition References**: All partition references in asset configs must exist
3. **Asset Selection**: Job selections must resolve to at least one asset
4. **Circular Dependencies**: Asset dependency graphs must be acyclic
5. **Environment Variables**: All `${VAR:default}` expressions must be valid

### Pydantic Validators

```python
from pydantic import validator, root_validator
from typing import Dict, Any

class OrchestrationConfig(BaseModel):
    """Top-level orchestration configuration."""

    @root_validator
    def validate_job_references(cls, values):
        """Validate all job references exist."""
        jobs = values.get("jobs", {})

        # Check schedule job references
        for schedule in values.get("schedules", {}).values():
            if schedule.job not in jobs:
                raise ValueError(f"Schedule references non-existent job: {schedule.job}")

        # Check sensor job references
        for sensor in values.get("sensors", {}).values():
            if sensor.job not in jobs:
                raise ValueError(f"Sensor references non-existent job: {sensor.job}")

        return values

    @validator("asset_modules")
    def validate_module_paths(cls, v):
        """Validate module paths are importable."""
        for module_path in v:
            try:
                importlib.import_module(module_path)
            except ImportError as e:
                raise ValueError(f"Cannot import asset module {module_path}: {e}")
        return v
```

### Environment Variable Interpolation

All string fields support environment variable substitution:
- Syntax: `${VAR_NAME:default_value}`
- Applied during config loading before Pydantic validation
- Supports nested references in complex objects
- Default values optional (syntax: `${VAR_NAME}`)

---

## Migration Considerations

### Breaking Changes
- Removes existing wrapper asset pattern
- Changes FloeDefinitions factory method signature
- Reorganizes demo asset structure

### Compatibility
- New orchestration section is optional - existing pipelines continue working
- Environment variable syntax aligns with existing floe-core patterns
- Dagster objects created match existing patterns for seamless integration

### Upgrade Path
1. Add orchestration section to floe.yaml
2. Organize assets into separate module files
3. Remove manual asset registration from definitions.py
4. Test end-to-end execution with new configuration

This data model enables the declarative orchestration auto-discovery feature while maintaining type safety, clear validation, and environment-specific customization through configuration.