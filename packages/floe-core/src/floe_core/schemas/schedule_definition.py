"""Schedule definition models for floe-runtime.

T007: [010-orchestration-auto-discovery] Schedule definitions for cron-based job execution
Covers: ScheduleDefinition for automatic job scheduling

This module defines cron-based schedules for automatic job execution with timezone
support and partition selection for partitioned jobs.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# Constants for repeated validation patterns
IDENTIFIER_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*$"
"""Regex pattern for valid identifiers."""

CRON_PATTERN = r"^([0-9*,-/]+\s){4,5}[0-9*,-/]+$"
"""Regex pattern for cron expressions (5 or 6 fields)."""


class PartitionSelector(str, Enum):
    """Partition selection strategies for partitioned jobs.

    Values:
        LATEST: Select most recent partition.
        ALL: Select all available partitions.
    """

    LATEST = "latest"
    ALL = "all"


class ScheduleDefinition(BaseModel):
    """Cron-based schedule for automatic job execution.

    Attributes:
        job: Reference to job name (must exist in jobs dictionary).
        cron_schedule: Cron expression for schedule frequency.
        timezone: Schedule timezone (IANA timezone name).
        enabled: Whether schedule is active.
        partition_selector: Partition selection for partitioned jobs.
        description: Schedule description (max 500 characters).

    Example:
        >>> schedule = ScheduleDefinition(
        ...     job="bronze_refresh",
        ...     cron_schedule="0 6 * * *",
        ...     timezone="America/New_York",
        ...     enabled=True,
        ...     partition_selector=PartitionSelector.LATEST,
        ...     description="Daily bronze layer refresh at 6 AM",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    job: str = Field(
        ...,
        pattern=IDENTIFIER_PATTERN,
        description="Reference to job name (must exist in jobs dictionary)",
    )
    cron_schedule: str = Field(
        ...,
        pattern=CRON_PATTERN,
        description=(
            "Cron expression for schedule frequency (5 or 6 fields). "
            "Supports environment variable interpolation"
        ),
    )
    timezone: str = Field(
        default="UTC",
        description="Schedule timezone (IANA timezone name)",
    )
    enabled: bool = Field(
        default=True,
        description=("Whether schedule is active. Supports environment variable interpolation"),
    )
    partition_selector: PartitionSelector | None = Field(
        default=None,
        description=(
            "Partition selection for partitioned jobs: latest (most recent), all (all partitions)"
        ),
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Schedule description (max 500 characters)",
    )
