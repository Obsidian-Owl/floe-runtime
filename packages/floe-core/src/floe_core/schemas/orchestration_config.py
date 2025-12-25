"""Orchestration configuration models for floe-runtime.

T004, T011: [010-orchestration-auto-discovery] OrchestrationConfig and DbtConfig
Covers: Orchestration auto-discovery with declarative pipeline configuration

This module defines the top-level orchestration configuration that eliminates 200+ lines
of boilerplate by enabling auto-discovery of assets from modules and dbt manifests.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from .asset_config import AssetConfig
from .backfill_definition import BackfillDefinition
from .job_definition import JobDefinition
from .partition_definition import PartitionDefinition
from .schedule_definition import ScheduleDefinition
from .sensor_definition import SensorDefinition

# Constants for repeated validation patterns
IDENTIFIER_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*$"
"""Regex pattern for valid identifiers."""

MODULE_PATH_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$"
"""Regex pattern for Python module paths."""


class ObservabilityLevel(str, Enum):
    """dbt observability granularity levels.

    Values:
        PER_MODEL: Create individual assets for each dbt model.
        JOB_LEVEL: Treat dbt as a single job.
    """

    PER_MODEL = "per_model"
    JOB_LEVEL = "job_level"


class DbtConfig(BaseModel):
    """Configuration for dbt integration with per-model observability support.

    Attributes:
        manifest_path: Path to dbt manifest.json file.
        observability_level: Level of observability granularity.
        project_dir: dbt project directory path.
        profiles_dir: dbt profiles directory path.
        target: dbt target name.

    Example:
        >>> config = DbtConfig(
        ...     manifest_path="target/manifest.json",
        ...     observability_level=ObservabilityLevel.PER_MODEL,
        ...     target="dev",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_path: str = Field(
        ...,
        description=(
            "Path to dbt manifest.json file. "
            "Supports environment variable interpolation: ${DBT_MANIFEST_PATH:default_value}"
        ),
    )
    observability_level: ObservabilityLevel = Field(
        default=ObservabilityLevel.PER_MODEL,
        description=(
            "Level of observability granularity: per_model creates individual assets "
            "for each dbt model, job_level treats dbt as a single job"
        ),
    )
    project_dir: str | None = Field(
        default=None,
        description=("dbt project directory path. If not specified, inferred from manifest path"),
    )
    profiles_dir: str | None = Field(
        default=None,
        description=("dbt profiles directory path. If not specified, uses .floe/profiles"),
    )
    target: str | None = Field(
        default=None,
        pattern=IDENTIFIER_PATTERN,
        description="dbt target name. Must be a valid identifier",
    )


class OrchestrationConfig(BaseModel):
    """Orchestration configuration for floe.yaml.

    Enables declarative pipeline configuration that eliminates 200+ lines of boilerplate
    by auto-discovering assets from modules and dbt manifests.

    ⚠️  CRITICAL: This is DATA ENGINEER configuration only. MUST NOT contain infrastructure details:
    ❌ Forbidden: Endpoints (OTLP, S3, HTTP), credentials, bucket names, regions
    ✅ Allowed: Asset modules, schedules, LOCAL file paths, logical references

    Infrastructure details belong in platform.yaml (platform engineer responsibility).

    Attributes:
        asset_modules: Python module paths for asset auto-discovery.
        dbt: dbt integration configuration for per-model observability support.
        partitions: Named partition definitions that can be referenced by asset configurations.
        assets: Pattern-based asset configurations using glob patterns.
        jobs: Job definitions for grouping assets or operations.
        schedules: Schedule definitions for cron-based job execution.
        sensors: Sensor definitions for event-driven job execution.
        backfills: Backfill definitions for historical data processing.

    Example:
        >>> config = OrchestrationConfig(
        ...     asset_modules=["demo.assets.bronze", "demo.assets.gold"],
        ...     dbt=DbtConfig(manifest_path="target/manifest.json"),
        ...     partitions={
        ...         "daily": {
        ...             "type": "time_window",
        ...             "start": "2024-01-01",
        ...             "cron_schedule": "0 0 * * *",
        ...         }
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_modules: list[str] = Field(
        default_factory=list,
        description=(
            "Python module paths for asset auto-discovery. "
            "Modules must be valid Python import paths "
            "(e.g., 'demo.assets.bronze', 'my_package.data.gold')"
        ),
    )
    dbt: DbtConfig | None = Field(
        default=None,
        description="dbt integration configuration for per-model observability support",
    )
    partitions: dict[str, PartitionDefinition] = Field(
        default_factory=dict,
        description=(
            "Named partition definitions that can be referenced by asset configurations. "
            "Keys must be valid identifiers"
        ),
    )
    assets: dict[str, AssetConfig] = Field(
        default_factory=dict,
        description=(
            "Pattern-based asset configurations using glob patterns. "
            "Keys support glob syntax: *, ?, [abc], {a,b,c}"
        ),
    )
    jobs: dict[str, JobDefinition] = Field(
        default_factory=dict,
        description=(
            "Job definitions for grouping assets or operations. Job names must be valid identifiers"
        ),
    )
    schedules: dict[str, ScheduleDefinition] = Field(
        default_factory=dict,
        description=(
            "Schedule definitions for cron-based job execution. "
            "Schedule names must be valid identifiers"
        ),
    )
    sensors: dict[str, SensorDefinition] = Field(
        default_factory=dict,
        description=(
            "Sensor definitions for event-driven job execution. "
            "Sensor names must be valid identifiers"
        ),
    )
    backfills: dict[str, BackfillDefinition] = Field(
        default_factory=dict,
        description=(
            "Backfill definitions for historical data processing. "
            "Backfill names must be valid identifiers"
        ),
    )

    def __init__(self, **data):
        # Validate module paths match pattern
        asset_modules = data.get("asset_modules", [])
        for module_path in asset_modules:
            if not re.match(MODULE_PATH_PATTERN, module_path):
                msg = f"Invalid module path: {module_path}"
                raise ValueError(msg)

        # Validate dictionary keys are valid identifiers
        for dict_name in ["partitions", "jobs", "schedules", "sensors", "backfills"]:
            dict_value = data.get(dict_name, {})
            if isinstance(dict_value, dict):
                for key in dict_value:
                    if not re.match(IDENTIFIER_PATTERN, key):
                        msg = f"Invalid identifier in {dict_name}: {key}"
                        raise ValueError(msg)

        super().__init__(**data)
