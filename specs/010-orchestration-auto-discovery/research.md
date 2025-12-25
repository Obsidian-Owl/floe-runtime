# Research Document: Orchestration Auto-Discovery

**Feature Branch**: `010-orchestration-auto-discovery`
**Created**: 2025-12-26
**Specification**: [spec.md](./spec.md)
**Implementation Plan**: [plan.md](./plan.md)

This document analyzes key implementation decisions for the orchestration auto-discovery feature that eliminates 200+ LOC of boilerplate by auto-loading dbt models as individual assets with per-model observability.

## Decision 1: Dagster Asset Loading Patterns

**Chosen Approach**: Use Dagster's built-in `load_assets_from_modules()` for auto-discovery

**Rationale**:
- Dagster provides native support for module-based asset discovery via `dagster._core.definitions.module_loaders.load_assets_from_modules.load_assets_from_modules`
- This API is specifically designed for auto-loading assets from Python modules without manual registration
- Leverages existing Dagster patterns that the team and community understand
- Provides built-in error handling and validation for invalid asset definitions
- Integrates seamlessly with Dagster's dependency resolution and execution engine

**Alternatives Considered**:
- **Manual asset registration**: Rejected because it maintains the boilerplate problem we're trying to solve
- **Custom discovery via importlib**: Rejected because it duplicates Dagster's existing functionality and adds maintenance burden
- **Direct module imports**: Rejected because it lacks the validation and error handling of the official API

**Implementation Notes**:
```python
from dagster import load_assets_from_modules
import importlib

def load_assets_from_module_paths(module_paths: list[str]) -> list[AssetsDefinition]:
    """Load assets from configured module paths."""
    modules = []
    for module_path in module_paths:
        try:
            module = importlib.import_module(module_path)
            modules.append(module)
        except ImportError as e:
            logger.error("Failed to import asset module %s: %s", module_path, e)
            raise

    return load_assets_from_modules(modules)
```

## Decision 2: dbt Integration Strategy

**Chosen Approach**: Use existing `FloeAssetFactory.create_dbt_assets_with_per_model_observability()` method

**Rationale**:
- Already implemented at `/packages/floe-dagster/src/floe_dagster/assets.py:295`
- Provides per-model spans and lineage via dbt event stream hooking
- Eliminates broken wrapper asset pattern currently used in demo
- Creates individual asset entries for each dbt model, enabling proper dependency resolution
- Integrates with existing observability infrastructure (TracingManager, OpenLineageEmitter)

**Alternatives Considered**:
- **Wrapper assets (current pattern)**: Rejected because it hides individual model execution and breaks lineage tracking
- **Job-level observability only**: Rejected because it doesn't provide the granular visibility required for medallion architecture debugging

**Implementation Notes**:
The existing method hooks into dbt's event stream to create individual spans:
```python
@classmethod
def create_dbt_assets_with_per_model_observability(
    cls,
    artifacts: dict[str, Any],
) -> AssetsDefinition:
    """Create dbt assets with per-model observability (Level 1).

    This enables full traceability: Bronze → Silver → Gold with
    per-model granularity visible in Jaeger and Marquez.
    """
```

## Decision 3: Orchestration Config Schema Design

**Chosen Approach**: Pydantic v2 models with Union types for partition/job/sensor variants

**Rationale**:
- Leverages existing floe-core patterns with Pydantic v2 for type safety
- Enables JSON Schema export for IDE support and documentation
- Provides validation at config load time with clear error messages
- Union types allow clean modeling of different orchestration object types
- Integrates with existing `${VAR:default}` environment variable interpolation

**Alternatives Considered**:
- **Plain dicts**: Rejected because they lack type safety and validation
- **Custom validators**: Rejected because Pydantic provides superior validation with better error messages
- **Dataclasses**: Rejected because they lack the rich validation and serialization features needed

**Implementation Notes**:
```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Union, Literal
from enum import Enum

class PartitionType(str, Enum):
    """Supported partition types."""
    DAILY = "daily"
    HOURLY = "hourly"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    STATIC = "static"

class DailyPartitionConfig(BaseModel):
    """Daily partition configuration."""
    type: Literal[PartitionType.DAILY]
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str | None = None
    timezone: str = "UTC"

class StaticPartitionConfig(BaseModel):
    """Static partition configuration."""
    type: Literal[PartitionType.STATIC]
    partition_keys: list[str] = Field(..., min_length=1)

PartitionDefinition = Union[DailyPartitionConfig, StaticPartitionConfig, ...]
```

## Decision 4: Asset Module Organization

**Chosen Approach**: Separate files by layer (assets/bronze.py, assets/gold.py, assets/ops.py)

**Rationale**:
- Scales naturally with pipeline growth - each layer can be independently developed
- Enables clean testing where each layer can have focused test suites
- Matches dbt folder organization patterns familiar to data engineers
- Reduces merge conflicts when multiple developers work on different layers
- Aligns with medallion architecture separation of concerns

**Alternatives Considered**:
- **Single definitions.py file**: Rejected because it becomes unwieldy as pipelines grow
- **Organization by domain/team**: Rejected because it doesn't align with the technical architecture layers

**Implementation Notes**:
```yaml
# floe.yaml orchestration section
orchestration:
  asset_modules:
    - "demo.assets.bronze"  # Bronze layer assets
    - "demo.assets.silver"  # Silver layer assets
    - "demo.assets.gold"    # Gold layer assets
    - "demo.assets.ops"     # Operational/utility assets
```

## Decision 5: FloeDefinitions Factory Enhancement

**Chosen Approach**: Enhance existing `from_compiled_artifacts()` to auto-load when orchestration config present

**Rationale**:
- Maintains single canonical factory pattern in codebase
- Pre-1.0 release allows breaking changes without deprecation overhead
- Simpler API for users - one factory method handles all cases
- Leverages existing infrastructure resolution (platform.yaml loading, resource creation)
- Preserves backward compatibility for projects without orchestration config

**Alternatives Considered**:
- **New `from_orchestration_config()` factory**: Rejected because it fragments the API and increases user confusion
- **Separate `from_floe_spec()` factory**: Rejected because it duplicates existing platform resolution logic

**Implementation Notes**:
```python
@classmethod
def from_compiled_artifacts(cls, ...) -> Definitions:
    """Enhanced to auto-load assets from orchestration config."""
    # Existing logic for platform.yaml loading...

    # NEW: Auto-load assets if orchestration config present
    orchestration = artifacts.get("orchestration", {})
    all_assets = list(assets or [])

    if orchestration.get("asset_modules"):
        discovered_assets = cls._load_assets_from_modules(
            orchestration["asset_modules"]
        )
        all_assets.extend(discovered_assets)

    if orchestration.get("dbt"):
        dbt_assets = FloeAssetFactory.create_dbt_assets_with_per_model_observability(
            artifacts
        )
        all_assets.append(dbt_assets)
```

## Decision 6: Partition Definition Mapping

**Chosen Approach**: Map Pydantic PartitionDefinition to Dagster partition types

**Rationale**:
- Creates type-safe conversion layer between config and runtime objects
- Enables validation before Dagster object creation, providing better error messages
- Allows config-time validation of partition parameters (dates, keys, etc.)
- Maintains clear separation between configuration schema and Dagster implementation

**Alternatives Considered**:
- **Direct Dagster object construction**: Rejected because it bypasses validation and error handling
- **Runtime type detection**: Rejected because it pushes errors to execution time rather than config time

**Implementation Notes**:
```python
from dagster import DailyPartitionsDefinition, StaticPartitionsDefinition
from datetime import datetime

def create_dagster_partition_definition(
    config: PartitionDefinition
) -> DailyPartitionsDefinition | StaticPartitionsDefinition:
    """Convert config partition to Dagster partition definition."""
    if config.type == PartitionType.DAILY:
        return DailyPartitionsDefinition(
            start_date=config.start_date,
            end_date=config.end_date,
            timezone=config.timezone,
        )
    elif config.type == PartitionType.STATIC:
        return StaticPartitionsDefinition(config.partition_keys)
    else:
        raise ValueError(f"Unsupported partition type: {config.type}")
```

## Decision 7: Schedule/Sensor Loading Strategy

**Chosen Approach**: Convert config models to Dagster ScheduleDefinition/SensorDefinition in loaders/

**Rationale**:
- Separation of concerns: configuration parsing vs runtime object creation
- Testable loaders that can be unit tested independently
- Reusable patterns for different orchestration object types
- Clear error boundaries between config validation and Dagster object creation

**Alternatives Considered**:
- **Inline conversion in FloeDefinitions**: Rejected because it violates single responsibility principle
- **Custom scheduler/sensor framework**: Rejected because it duplicates Dagster's existing functionality

**Implementation Notes**:
```python
# packages/floe-dagster/src/floe_dagster/loaders/schedules.py
from dagster import ScheduleDefinition, DefaultScheduleStatus

def create_schedule_definition(
    config: ScheduleConfig,
    job: JobDefinition,
) -> ScheduleDefinition:
    """Create Dagster ScheduleDefinition from config."""
    return ScheduleDefinition(
        name=config.name,
        job=job,
        cron_schedule=config.cron_schedule,
        default_status=DefaultScheduleStatus.RUNNING if config.enabled else DefaultScheduleStatus.STOPPED,
        description=config.description,
    )
```

## Decision 8: Demo Refactoring Scope

**Chosen Approach**: Include demo refactoring in feature deliverables

**Rationale**:
- Serves as comprehensive acceptance tests for the auto-discovery feature
- Demonstrates complete end-to-end workflow from config to execution
- Validates that auto-discovery actually eliminates the boilerplate as claimed
- Provides working example for users to follow
- Ensures the feature actually solves the problem it was designed for

**Alternatives Considered**:
- **Separate follow-up task**: Rejected because it delays validation of the feature's core value proposition
- **Minimal demo changes only**: Rejected because it doesn't demonstrate the full capability

**Implementation Notes**:
The demo refactoring will:
1. Remove existing wrapper assets (`silver_staging`, `gold_marts`)
2. Reorganize assets into layer-specific modules (`demo/assets/bronze.py`, `demo/assets/ops.py`)
3. Add orchestration config to `demo/floe.yaml`
4. Update `demo/definitions.py` to use auto-discovery
5. Verify per-model observability works for each dbt model

## Decision 9: Environment Variable Interpolation

**Chosen Approach**: Use `${VAR:default}` syntax with pydantic-settings for environment overrides

**Rationale**:
- Consistent with existing floe-core patterns for environment variable handling
- Standard pattern that works across YAML/JSON configuration formats
- No custom parsing logic required - leverages pydantic-settings
- Supports default values for development environments
- Familiar syntax for data engineers coming from other tools

**Alternatives Considered**:
- **Jinja2 templating**: Rejected because it adds complexity and potential security risks
- **Custom variable substitution**: Rejected because it duplicates existing functionality
- **Python f-strings**: Rejected because they don't work in configuration files

**Implementation Notes**:
```yaml
# floe.yaml with environment overrides
orchestration:
  schedules:
    - name: bronze_refresh
      job: bronze_job
      cron_schedule: "${BRONZE_REFRESH_CRON:*/5 * * * *}"  # Every 5 min default
      enabled: "${SCHEDULE_ENABLED:true}"

  sensors:
    - name: file_watcher
      type: file
      path: "${TRIGGER_FILE_PATH:/tmp/trigger}"
      job: bronze_job
```

## Decision 10: Error Handling Strategy

**Chosen Approach**: Pydantic validation errors at config load, clear error messages with context

**Rationale**:
- Fail fast principle - catch configuration errors before runtime
- Provides actionable error messages with field context
- Prevents runtime failures during pipeline execution
- Aligns with existing floe-core error handling patterns (FR-047)
- Better developer experience with clear error locations

**Alternatives Considered**:
- **Runtime validation**: Rejected because it pushes errors to execution time
- **Warning-only mode**: Rejected because it allows broken configurations to persist
- **Silent failures with defaults**: Rejected because it masks configuration errors

**Implementation Notes**:
```python
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

def load_orchestration_config(config_dict: dict) -> OrchestrationConfig:
    """Load and validate orchestration configuration."""
    try:
        return OrchestrationConfig.model_validate(config_dict)
    except ValidationError as e:
        logger.error(
            "Invalid orchestration configuration in floe.yaml",
            extra={"validation_errors": e.errors()}
        )
        # Re-raise with context
        raise ValueError(
            f"Orchestration configuration validation failed: {e}"
        ) from e
```

## Implementation Sequencing

Based on this research, the recommended implementation sequence is:

1. **Phase 1**: Orchestration config schema (Pydantic models)
2. **Phase 2**: Asset module loading via `load_assets_from_modules()`
3. **Phase 3**: dbt asset integration using existing per-model observability
4. **Phase 4**: Job/schedule/sensor loaders and Dagster object creation
5. **Phase 5**: FloeDefinitions factory enhancement
6. **Phase 6**: Demo refactoring and end-to-end validation

This sequence ensures each component can be tested independently while building toward the complete auto-discovery capability.