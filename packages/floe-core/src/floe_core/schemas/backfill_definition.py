"""Backfill definition models for floe-runtime.

T010: [010-orchestration-auto-discovery] Backfill definitions for historical data processing
Covers: BackfillDefinition for processing past data partitions

This module defines historical backfill configuration for processing past data partitions
with batch size control and metadata tagging.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Constants for repeated validation patterns
IDENTIFIER_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*$"
"""Regex pattern for valid identifiers."""


class PartitionRange(BaseModel):
    """Partition range specification for backfills.

    Attributes:
        start: Start partition key.
        end: End partition key (must be >= start).

    Example:
        >>> range_config = PartitionRange(
        ...     start="2024-01-01",
        ...     end="2024-12-31",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    start: str = Field(
        ...,
        description="Start partition key (format depends on partition definition)",
    )
    end: str = Field(
        ...,
        description="End partition key (must be >= start)",
    )


class BackfillDefinition(BaseModel):
    """Historical backfill configuration for processing past data partitions.

    Attributes:
        job: Reference to job name (must exist in jobs dictionary).
        partition_range: Partition range with start and end keys.
        batch_size: Maximum partitions processed per execution.
        description: Backfill description (max 500 characters).
        tags: Backfill metadata tags as key-value pairs.

    Example:
        >>> backfill = BackfillDefinition(
        ...     job="bronze_refresh",
        ...     partition_range=PartitionRange(
        ...         start="2024-01-01",
        ...         end="2024-12-31",
        ...     ),
        ...     batch_size=5,
        ...     description="Backfill 2024 bronze data",
        ...     tags={"year": "2024", "priority": "low"},
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    job: str = Field(
        ...,
        pattern=IDENTIFIER_PATTERN,
        description=(
            "Reference to job name (must exist in jobs dictionary and reference partitioned assets)"
        ),
    )
    partition_range: PartitionRange = Field(
        ...,
        description=(
            "Partition range with start and end keys matching the job's asset partition format"
        ),
    )
    batch_size: int = Field(
        default=10,
        ge=1,
        description="Maximum partitions processed per execution",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Backfill description (max 500 characters)",
    )
    tags: dict[str, str] | None = Field(
        default=None,
        description="Backfill metadata tags as key-value pairs",
    )
