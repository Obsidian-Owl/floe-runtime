"""Loaders for converting floe-core schemas to Dagster definitions.

This module provides loaders that convert declarative configuration from floe.yaml
into Dagster definitions (assets, jobs, schedules, sensors).

Auto-discovery loaders (T047):
- asset_loader: Load assets from Python modules
- dbt_loader: Load dbt models as individual assets
- job_loader: Load batch and ops jobs
- schedule_loader: Load cron schedules
- sensor_loader: Load file watchers and custom sensors
- partition_loader: Load partition definitions
"""

from __future__ import annotations

from floe_dagster.loaders.asset_loader import load_assets_from_modules
from floe_dagster.loaders.dbt_loader import load_dbt_assets
from floe_dagster.loaders.job_loader import load_jobs
from floe_dagster.loaders.partition_loader import load_partitions
from floe_dagster.loaders.schedule_loader import load_schedules
from floe_dagster.loaders.sensor_loader import load_sensors

__all__: list[str] = [
    "load_assets_from_modules",
    "load_dbt_assets",
    "load_jobs",
    "load_partitions",
    "load_schedules",
    "load_sensors",
]
