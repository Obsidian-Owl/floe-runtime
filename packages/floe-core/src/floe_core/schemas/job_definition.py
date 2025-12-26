"""Job definition models for floe-runtime.

T006: [010-orchestration-auto-discovery] Job definitions with discriminated union
Covers: BatchJob, OpsJob, JobDefinition union

This module defines executable jobs that group assets or operations for orchestration,
supporting both batch asset processing and custom operations execution.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Discriminator, Field

# Constants for repeated validation patterns
FUNCTION_PATH_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*\.[a-zA-Z][a-zA-Z0-9_]*$"
"""Regex pattern for module.function references."""


class BatchJob(BaseModel):
    """Batch job for executing asset selections.

    Attributes:
        type: Job type discriminator.
        selection: Asset selection expressions.
        description: Job description (max 500 characters).
        tags: Job metadata tags as key-value pairs.

    Example:
        >>> job = BatchJob(
        ...     type="batch",
        ...     selection=["group:bronze", "asset:customer_data", "+orders"],
        ...     description="Process bronze layer assets",
        ...     tags={"layer": "bronze", "priority": "high"},
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["batch"] = Field(
        default="batch",
        description="Job type discriminator",
    )
    selection: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "Asset selection expressions: group:name, asset:name, "
            "+asset (upstream), asset+ (downstream)"
        ),
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Job description (max 500 characters)",
    )
    tags: dict[str, str] | None = Field(
        default=None,
        description="Job metadata tags as key-value pairs",
    )

    def __init__(self, **data):
        # Validate selection expressions are non-empty
        selection = data.get("selection", [])
        for expr in selection:
            if not expr.strip():
                msg = "Asset selection expressions cannot be empty"
                raise ValueError(msg)
        super().__init__(**data)


class OpsJob(BaseModel):
    """Operations job for executing custom functions.

    Attributes:
        type: Job type discriminator.
        target_function: Module.function reference to execute.
        args: Function arguments as key-value pairs.
        description: Job description (max 500 characters).
        tags: Job metadata tags as key-value pairs.

    Example:
        >>> job = OpsJob(
        ...     type="ops",
        ...     target_function="demo.ops.vacuum.vacuum_old_snapshots",
        ...     args={"retention_days": 30, "dry_run": False},
        ...     description="Remove old table snapshots",
        ...     tags={"category": "maintenance"},
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["ops"] = Field(
        default="ops",
        description="Job type discriminator",
    )
    target_function: str = Field(
        ...,
        pattern=FUNCTION_PATH_PATTERN,
        description="Module.function reference to execute (must be importable)",
    )
    args: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Function arguments as key-value pairs (must be JSON serializable). "
            "MUST NOT contain endpoints, credentials, or infrastructure details - "
            "those belong in platform.yaml"
        ),
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Job description (max 500 characters)",
    )
    tags: dict[str, str] | None = Field(
        default=None,
        description="Job metadata tags as key-value pairs",
    )


# Union type with discriminator on "type" field
JobDefinition = Annotated[
    BatchJob | OpsJob,
    Discriminator("type"),
]
"""Job definition with discriminated union for batch and ops jobs."""
