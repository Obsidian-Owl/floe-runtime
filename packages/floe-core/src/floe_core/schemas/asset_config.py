"""Asset configuration models for floe-runtime.

T009: [010-orchestration-auto-discovery] Asset configuration for pattern-based settings
Covers: AssetConfig for applying partitions and automation conditions to assets

This module defines pattern-based configuration that applies partitions, automation
conditions, and policies to matching assets using glob patterns.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# Constants for repeated validation patterns
IDENTIFIER_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*$"
"""Regex pattern for valid identifiers."""


class AutomationCondition(str, Enum):
    """Asset automation condition types.

    Values:
        EAGER: Execute immediately when dependencies are ready.
        ON_CRON: Execute on scheduled cron triggers.
        ON_MISSING: Execute when dependencies are missing.
    """

    EAGER = "eager"
    ON_CRON = "on_cron"
    ON_MISSING = "on_missing"


class BackfillPolicy(str, Enum):
    """Asset backfill policy types.

    Values:
        LAZY: Materialize partitions on demand.
        EAGER: Materialize all historical partitions.
    """

    LAZY = "lazy"
    EAGER = "eager"


class AssetConfig(BaseModel):
    """Configuration applied to assets matching the pattern key.

    Pattern keys support glob syntax: *, ?, [abc], {a,b,c}. Configuration is applied
    to assets discovered from modules or dbt that match the pattern.

    Attributes:
        partitions: Reference to named partition definition.
        automation_condition: Asset automation condition.
        backfill_policy: Backfill policy for the asset.
        compute_kind: Compute resource kind identifier.
        group_name: Asset group override (must be valid identifier).

    Example:
        >>> config = AssetConfig(
        ...     partitions="daily_partition",
        ...     automation_condition=AutomationCondition.EAGER,
        ...     backfill_policy=BackfillPolicy.LAZY,
        ...     compute_kind="high_memory",
        ...     group_name="bronze",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    partitions: str | None = Field(
        default=None,
        pattern=IDENTIFIER_PATTERN,
        description=(
            "Reference to named partition definition. Must exist in the partitions dictionary"
        ),
    )
    automation_condition: AutomationCondition | None = Field(
        default=None,
        description=(
            "Asset automation condition: eager (immediate), on_cron (scheduled), "
            "on_missing (when dependencies missing)"
        ),
    )
    backfill_policy: BackfillPolicy | None = Field(
        default=None,
        description="Backfill policy for the asset",
    )
    compute_kind: str | None = Field(
        default=None,
        description="Compute resource kind identifier",
    )
    group_name: str | None = Field(
        default=None,
        pattern=IDENTIFIER_PATTERN,
        description="Asset group override (must be valid identifier)",
    )
