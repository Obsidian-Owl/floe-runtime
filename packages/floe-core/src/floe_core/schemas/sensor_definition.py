"""Sensor definition models for floe-runtime.

T008: [010-orchestration-auto-discovery] Sensor definitions with discriminated union
Covers: FileWatcherSensor, AssetSensor, RunStatusSensor, CustomSensor

This module defines event-driven sensors that trigger jobs based on external conditions
including file arrivals, asset materialization, job status changes, and custom logic.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Discriminator, Field

# Constants for repeated validation patterns
IDENTIFIER_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*$"
"""Regex pattern for valid identifiers."""

FUNCTION_PATH_PATTERN = (
    r"^[a-zA-Z][a-zA-Z0-9_]*(\\.[a-zA-Z][a-zA-Z0-9_]*)*\\.[a-zA-Z][a-zA-Z0-9_]*$"
)
"""Regex pattern for module.function references."""


class RunStatus(str, Enum):
    """Job run status types for status sensors.

    Values:
        SUCCESS: Job completed successfully.
        FAILURE: Job failed with error.
        STARTED: Job execution started.
    """

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    STARTED = "STARTED"


class FileWatcherSensor(BaseModel):
    """File system watcher sensor that triggers jobs when files appear.

    Attributes:
        type: Sensor type discriminator.
        job: Reference to job name (must exist in jobs dictionary).
        path: LOCAL directory or file path to watch.
        pattern: Regex pattern to match file names.
        poll_interval_seconds: Polling frequency in seconds.
        description: Sensor description (max 500 characters).

    Example:
        >>> sensor = FileWatcherSensor(
        ...     type="file_watcher",
        ...     job="bronze_refresh",
        ...     path="./incoming/",
        ...     pattern="customers_*.csv",
        ...     poll_interval_seconds=60,
        ...     description="Trigger when customer data arrives",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["file_watcher"] = Field(
        default="file_watcher",
        description="Sensor type discriminator",
    )
    job: str = Field(
        ...,
        pattern=IDENTIFIER_PATTERN,
        description="Reference to job name (must exist in jobs dictionary)",
    )
    path: str = Field(
        ...,
        description=(
            "LOCAL directory or file path to watch "
            "(relative to project root or absolute local path). "
            "MUST NOT contain S3, HTTP, or external endpoints - those belong in platform.yaml. "
            "Supports environment variable interpolation"
        ),
    )
    pattern: str | None = Field(
        default=None,
        description="Regex pattern to match file names",
    )
    poll_interval_seconds: int = Field(
        default=30,
        ge=1,
        description="Polling frequency in seconds",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Sensor description (max 500 characters)",
    )


class AssetSensor(BaseModel):
    """Asset materialization sensor that triggers jobs when watched assets are updated.

    Attributes:
        type: Sensor type discriminator.
        job: Reference to job name (must exist in jobs dictionary).
        watched_assets: Asset names to watch for materialization events.
        poll_interval_seconds: Polling frequency in seconds.
        description: Sensor description (max 500 characters).

    Example:
        >>> sensor = AssetSensor(
        ...     type="asset_sensor",
        ...     job="gold_pipeline",
        ...     watched_assets=["bronze_customers", "bronze_orders"],
        ...     poll_interval_seconds=30,
        ...     description="Trigger when bronze assets update",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["asset_sensor"] = Field(
        default="asset_sensor",
        description="Sensor type discriminator",
    )
    job: str = Field(
        ...,
        pattern=IDENTIFIER_PATTERN,
        description="Reference to job name (must exist in jobs dictionary)",
    )
    watched_assets: list[str] = Field(
        ...,
        min_length=1,
        description="Asset names to watch for materialization events",
    )
    poll_interval_seconds: int = Field(
        default=30,
        ge=1,
        description="Polling frequency in seconds",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Sensor description (max 500 characters)",
    )

    def __init__(self, **data):
        # Validate watched assets are non-empty
        watched_assets = data.get("watched_assets", [])
        for asset in watched_assets:
            if not asset.strip():
                msg = "Watched asset names cannot be empty"
                raise ValueError(msg)
        super().__init__(**data)


class RunStatusSensor(BaseModel):
    """Job run status sensor that triggers jobs based on other job status changes.

    Attributes:
        type: Sensor type discriminator.
        job: Reference to job name (must exist in jobs dictionary).
        watched_jobs: Job names to watch for status changes.
        status: Job status to watch for.
        poll_interval_seconds: Polling frequency in seconds.
        description: Sensor description (max 500 characters).

    Example:
        >>> sensor = RunStatusSensor(
        ...     type="run_status",
        ...     job="send_alert",
        ...     watched_jobs=["bronze_refresh", "gold_pipeline"],
        ...     status=RunStatus.FAILURE,
        ...     poll_interval_seconds=30,
        ...     description="Send alert on pipeline failures",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["run_status"] = Field(
        default="run_status",
        description="Sensor type discriminator",
    )
    job: str = Field(
        ...,
        pattern=IDENTIFIER_PATTERN,
        description="Reference to job name (must exist in jobs dictionary)",
    )
    watched_jobs: list[str] = Field(
        ...,
        min_length=1,
        description="Job names to watch for status changes (must exist in jobs dictionary)",
    )
    status: RunStatus = Field(
        ...,
        description="Job status to watch for",
    )
    poll_interval_seconds: int = Field(
        default=30,
        ge=1,
        description="Polling frequency in seconds",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Sensor description (max 500 characters)",
    )

    def __init__(self, **data):
        # Validate watched jobs use valid identifiers
        watched_jobs = data.get("watched_jobs", [])
        for job_name in watched_jobs:
            if not job_name.strip():
                msg = "Watched job names cannot be empty"
                raise ValueError(msg)
        super().__init__(**data)


class CustomSensor(BaseModel):
    """Custom sensor with user-defined logic function.

    Attributes:
        type: Sensor type discriminator.
        job: Reference to job name (must exist in jobs dictionary).
        target_function: Module.function reference for sensor logic.
        args: Function arguments as key-value pairs.
        poll_interval_seconds: Polling frequency in seconds.
        description: Sensor description (max 500 characters).

    Example:
        >>> sensor = CustomSensor(
        ...     type="custom",
        ...     job="special_process",
        ...     target_function="demo.sensors.check_local_condition",
        ...     args={"file_path": "./status/ready.flag", "threshold": 1000},
        ...     poll_interval_seconds=60,
        ...     description="Check custom condition",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["custom"] = Field(
        default="custom",
        description="Sensor type discriminator",
    )
    job: str = Field(
        ...,
        pattern=IDENTIFIER_PATTERN,
        description="Reference to job name (must exist in jobs dictionary)",
    )
    target_function: str = Field(
        ...,
        pattern=FUNCTION_PATH_PATTERN,
        description="Module.function reference for sensor logic (must be importable and callable)",
    )
    args: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Function arguments as key-value pairs (must be JSON serializable). "
            "MUST NOT contain endpoints, credentials, or infrastructure details - "
            "those belong in platform.yaml"
        ),
    )
    poll_interval_seconds: int = Field(
        default=30,
        ge=1,
        description="Polling frequency in seconds",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Sensor description (max 500 characters)",
    )


# Union type with discriminator on "type" field
SensorDefinition = Annotated[
    FileWatcherSensor | AssetSensor | RunStatusSensor | CustomSensor,
    Discriminator("type"),
]
"""Sensor definition with discriminated union for different sensor types."""
