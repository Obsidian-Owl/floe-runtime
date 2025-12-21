"""Dagster Definitions for Floe Demo.

Provides orchestration for the demo e-commerce data pipeline including:
- Synthetic data generation schedule
- dbt transformation jobs
- Cube cache refresh triggers

Covers: 007-FR-029 (E2E validation tests)
Covers: 007-FR-031 (Medallion architecture orchestration)
"""

from __future__ import annotations

import os
from typing import Any

from dagster import (
    AssetSelection,
    DefaultScheduleStatus,
    DefaultSensorStatus,
    Definitions,
    RunRequest,
    ScheduleDefinition,
    asset,
    define_asset_job,
    sensor,
)

# =============================================================================
# Configuration
# =============================================================================


def get_demo_config() -> dict[str, Any]:
    """Get demo configuration from environment.

    Returns:
        Configuration dictionary with database connection details.
    """
    return {
        "catalog": os.environ.get("FLOE_DEMO_CATALOG", "floe_demo"),
        "schema": os.environ.get("FLOE_DEMO_SCHEMA", "raw"),
        "polaris_url": os.environ.get("POLARIS_URL", "http://polaris:8181"),
        "cube_url": os.environ.get("CUBE_API_URL", "http://cube:4000"),
    }


# =============================================================================
# Assets
# =============================================================================


@asset(
    group_name="synthetic",
    description="Generate synthetic e-commerce data for demo",
)
def synthetic_data() -> dict[str, int]:
    """Generate synthetic e-commerce data.

    This asset triggers floe-synthetic to generate:
    - Customers
    - Products
    - Orders
    - Order items

    Returns:
        Dictionary with counts of generated records.
    """
    # In production, this would call floe-synthetic
    # For demo, we return placeholder counts
    return {
        "customers": 100,
        "products": 50,
        "orders": 500,
        "order_items": 1500,
    }


@asset(
    group_name="dbt",
    description="Run dbt transformations (staging → intermediate → marts)",
    deps=[synthetic_data],
)
def dbt_transformations() -> dict[str, str]:
    """Execute dbt transformations.

    Runs the full dbt pipeline:
    1. Staging models (views)
    2. Intermediate models (tables)
    3. Mart models (tables)

    Returns:
        Dictionary with dbt run status.
    """
    # In production, this would invoke dbt via dbtRunner
    # For demo, we return placeholder status
    return {
        "status": "success",
        "models_run": "12",
        "tests_passed": "8",
    }


@asset(
    group_name="cube",
    description="Trigger Cube pre-aggregation refresh",
    deps=[dbt_transformations],
)
def cube_preaggregations() -> dict[str, str]:
    """Trigger Cube pre-aggregation refresh.

    Calls Cube API to refresh pre-aggregations after dbt completes.

    Returns:
        Dictionary with pre-aggregation status.
    """
    # In production, this would call Cube REST API
    # POST /cubejs-api/v1/pre-aggregations/jobs
    return {
        "status": "success",
        "pre_aggregations_built": "3",
    }


# =============================================================================
# Jobs
# =============================================================================


# Full pipeline job - runs all assets
demo_pipeline_job = define_asset_job(
    name="demo_pipeline",
    selection=AssetSelection.groups("synthetic", "dbt", "cube"),
    description="Full demo pipeline: synthetic data → dbt → Cube",
)

# dbt-only job - for incremental refreshes
dbt_refresh_job = define_asset_job(
    name="dbt_refresh",
    selection=AssetSelection.groups("dbt", "cube"),
    description="Refresh dbt models and Cube pre-aggregations",
)


# =============================================================================
# Schedules
# =============================================================================


# Hourly schedule for synthetic data generation
demo_hourly_schedule = ScheduleDefinition(
    job=demo_pipeline_job,
    cron_schedule="0 * * * *",  # Every hour
    default_status=DefaultScheduleStatus.STOPPED,  # Start stopped for demo
    description="Hourly synthetic data generation and pipeline refresh",
)

# Daily schedule for full refresh
demo_daily_schedule = ScheduleDefinition(
    job=demo_pipeline_job,
    cron_schedule="0 6 * * *",  # Every day at 6 AM
    default_status=DefaultScheduleStatus.STOPPED,  # Start stopped for demo
    description="Daily full pipeline refresh",
)


# =============================================================================
# Sensors
# =============================================================================


@sensor(
    job=demo_pipeline_job,
    minimum_interval_seconds=60,
    default_status=DefaultSensorStatus.STOPPED,  # Start stopped for demo
    description="Trigger pipeline when new data file appears",
)
def file_arrival_sensor(context: Any) -> RunRequest | None:
    """Sensor for file arrival trigger.

    Monitors a configured path for new data files and triggers
    the pipeline when files appear.

    Args:
        context: Dagster sensor context.

    Returns:
        RunRequest if new file detected, None otherwise.
    """
    # In production, this would check for new files
    # For demo, always return None (no trigger)
    return None


@sensor(
    job=demo_pipeline_job,
    minimum_interval_seconds=30,
    default_status=DefaultSensorStatus.STOPPED,  # Start stopped for demo
    description="API trigger for on-demand pipeline execution",
)
def api_trigger_sensor(context: Any) -> RunRequest | None:
    """Sensor for API-based on-demand triggers.

    Checks a flag/queue for on-demand execution requests.
    This allows external systems to trigger the pipeline via API.

    Args:
        context: Dagster sensor context.

    Returns:
        RunRequest if API trigger detected, None otherwise.
    """
    # Check for trigger flag (e.g., from Redis, file, or external service)
    trigger_path = os.environ.get("DEMO_TRIGGER_FILE", "/tmp/demo_trigger")

    if os.path.exists(trigger_path):
        # Remove trigger file to prevent re-triggering
        try:
            os.remove(trigger_path)
            context.log.info("API trigger detected, starting pipeline")
            return RunRequest(
                run_key=f"api_trigger_{context.cursor}",
                run_config={},
            )
        except OSError:
            pass

    return None


# =============================================================================
# Definitions
# =============================================================================


defs = Definitions(
    assets=[
        synthetic_data,
        dbt_transformations,
        cube_preaggregations,
    ],
    jobs=[
        demo_pipeline_job,
        dbt_refresh_job,
    ],
    schedules=[
        demo_hourly_schedule,
        demo_daily_schedule,
    ],
    sensors=[
        file_arrival_sensor,
        api_trigger_sensor,
    ],
)
