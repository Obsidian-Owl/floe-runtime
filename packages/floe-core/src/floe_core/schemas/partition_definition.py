"""Partition definition models for floe-runtime.

T005: [010-orchestration-auto-discovery] Partition definitions with discriminated union
Covers: TimeWindowPartition, StaticPartition, MultiPartition, DynamicPartition

This module defines partition schemes for incremental data processing with various
partitioning strategies including time-based, static, multi-dimensional, and dynamic.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Discriminator, Field

# Constants for repeated validation patterns
IDENTIFIER_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*$"
"""Regex pattern for valid identifiers."""

DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
"""Regex pattern for YYYY-MM-DD date format."""

CRON_PATTERN = r"^([0-9*,-/]+\s){4,5}[0-9*,-/]+$"
"""Regex pattern for cron expressions (5 or 6 fields)."""

FUNCTION_PATH_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*\.[a-zA-Z][a-zA-Z0-9_]*$"
"""Regex pattern for module.function references."""


class TimeWindowPartition(BaseModel):
    """Time-based partitioning with configurable frequency and timezone support.

    Attributes:
        type: Partition type discriminator.
        start: Start date in YYYY-MM-DD format.
        cron_schedule: Cron expression defining partition frequency.
        timezone: Timezone for partition boundaries (IANA timezone name).
        end: End date in YYYY-MM-DD format (optional).
        fmt: Date format for partition keys using strftime format.

    Example:
        >>> partition = TimeWindowPartition(
        ...     type="time_window",
        ...     start="2024-01-01",
        ...     cron_schedule="0 0 * * *",
        ...     timezone="UTC",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["time_window"] = Field(
        default="time_window",
        description="Partition type discriminator",
    )
    start: str = Field(
        ...,
        pattern=DATE_PATTERN,
        description="Start date in YYYY-MM-DD format",
    )
    cron_schedule: str = Field(
        ...,
        pattern=CRON_PATTERN,
        description=(
            "Cron expression defining partition frequency (5 or 6 fields). "
            "Must match time window frequency"
        ),
    )
    timezone: str = Field(
        default="UTC",
        description="Timezone for partition boundaries (IANA timezone name)",
    )
    end: str | None = Field(
        default=None,
        pattern=DATE_PATTERN,
        description="End date in YYYY-MM-DD format (optional)",
    )
    fmt: str | None = Field(
        default=None,
        description="Date format for partition keys using strftime format",
    )


class StaticPartition(BaseModel):
    """Static partitioning with predefined partition keys.

    Attributes:
        type: Partition type discriminator.
        partition_keys: List of static partition key values.

    Example:
        >>> partition = StaticPartition(
        ...     type="static",
        ...     partition_keys=["us-east", "us-west", "eu-central"],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["static"] = Field(
        default="static",
        description="Partition type discriminator",
    )
    partition_keys: list[str] = Field(
        ...,
        min_length=1,
        description="List of static partition key values. Must be non-empty with unique values",
    )

    def __init__(self, **data):
        # Validate partition keys are unique and non-empty
        partition_keys = data.get("partition_keys", [])
        if len(set(partition_keys)) != len(partition_keys):
            msg = "Partition keys must be unique"
            raise ValueError(msg)
        for key in partition_keys:
            if not key.strip():
                msg = "Partition keys cannot be empty"
                raise ValueError(msg)
        super().__init__(**data)


class MultiPartition(BaseModel):
    """Multi-dimensional partitioning combining multiple partition definitions.

    Attributes:
        type: Partition type discriminator.
        partitions: Named sub-partition definitions.

    Example:
        >>> partition = MultiPartition(
        ...     type="multi",
        ...     partitions={
        ...         "date": TimeWindowPartition(
        ...             start="2024-01-01",
        ...             cron_schedule="0 0 * * *",
        ...         ),
        ...         "region": StaticPartition(
        ...             partition_keys=["us", "eu", "ap"],
        ...         ),
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["multi"] = Field(
        default="multi",
        description="Partition type discriminator",
    )
    partitions: dict[str, PartitionDefinition] = Field(
        ...,
        min_length=1,
        description="Named sub-partition definitions",
    )

    def __init__(self, **data):
        # Validate partition keys are valid identifiers
        partitions = data.get("partitions", {})
        for key in partitions:
            if not re.match(IDENTIFIER_PATTERN, key):
                msg = f"Partition key must be valid identifier: {key}"
                raise ValueError(msg)
        super().__init__(**data)


class DynamicPartition(BaseModel):
    """Dynamic partitioning with runtime partition generation.

    Attributes:
        type: Partition type discriminator.
        fn: Function reference for dynamic partition generation.

    Example:
        >>> partition = DynamicPartition(
        ...     type="dynamic",
        ...     fn="demo.partitions.get_active_customers",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["dynamic"] = Field(
        default="dynamic",
        description="Partition type discriminator",
    )
    fn: str | None = Field(
        default=None,
        pattern=FUNCTION_PATH_PATTERN,
        description="Function reference for dynamic partition generation (module.function format)",
    )


# Union type with discriminator on "type" field
PartitionDefinition = Annotated[
    TimeWindowPartition | StaticPartition | MultiPartition | DynamicPartition,
    Discriminator("type"),
]
"""Partition definition with discriminated union for various partitioning strategies."""
