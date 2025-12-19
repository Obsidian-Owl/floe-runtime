"""Consumption configuration models for floe-runtime.

T023: [US1] Implement PreAggregationConfig with defaults
T024: [US1] Implement CubeSecurityConfig with defaults
T025: [US1] Implement ConsumptionConfig with database_type

This module defines configuration models for the Cube semantic layer.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PreAggregationConfig(BaseModel):
    """Configuration for Cube pre-aggregations.

    Attributes:
        refresh_schedule: Cron expression for refresh schedule.
        timezone: Timezone for the schedule.

    Example:
        >>> config = PreAggregationConfig(
        ...     refresh_schedule="0 * * * *",
        ...     timezone="America/New_York"
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    refresh_schedule: str = Field(
        default="*/30 * * * *",
        description="Cron expression for pre-aggregation refresh",
    )
    timezone: str = Field(
        default="UTC",
        description="Timezone for schedule evaluation",
    )


class CubeSecurityConfig(BaseModel):
    """Configuration for Cube row-level security.

    Row-level security filters query results based on JWT claims.
    The filter_column specifies which database column to filter on,
    and the corresponding claim value is extracted from the JWT token.

    Note:
        This is USER-MANAGED row-level security, NOT SaaS tenant isolation.
        Users define their own filter columns and claims for their use cases
        (e.g., organization_id, department, region).

    Attributes:
        row_level: Enable row-level security filtering.
        filter_column: Column name used for row-level filtering.

    Example:
        >>> config = CubeSecurityConfig(
        ...     row_level=True,
        ...     filter_column="organization_id"
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    row_level: bool = Field(
        default=True,
        description="Enable row-level security",
    )
    filter_column: str = Field(
        default="organization_id",
        description="Column for row-level filtering (matches JWT claim name)",
    )


class ConsumptionConfig(BaseModel):
    """Configuration for Cube semantic layer.

    Attributes:
        enabled: Enable Cube semantic layer.
        port: Cube API port.
        api_secret_ref: K8s secret name for Cube API key.
        database_type: Database driver type for Cube (postgres, snowflake, etc.)
        dev_mode: Enable Cube Playground in development.
        pre_aggregations: Pre-aggregation configuration.
        security: Row-level security configuration.

    Example:
        >>> config = ConsumptionConfig(
        ...     enabled=True,
        ...     port=8080,
        ...     database_type="snowflake"
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable Cube semantic layer",
    )
    port: int = Field(
        default=4000,
        description="Cube API port",
    )
    api_secret_ref: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$",
        description="K8s secret name for Cube API key",
    )
    database_type: str | None = Field(
        default=None,
        description="Database driver type (postgres, snowflake, bigquery, etc.)",
    )
    dev_mode: bool = Field(
        default=False,
        description="Enable Cube Playground in development",
    )
    pre_aggregations: PreAggregationConfig = Field(
        default_factory=PreAggregationConfig,
        description="Pre-aggregation configuration",
    )
    security: CubeSecurityConfig = Field(
        default_factory=CubeSecurityConfig,
        description="Row-level security configuration",
    )
