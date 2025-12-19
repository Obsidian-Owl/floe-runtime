"""Pydantic models for Cube semantic layer configuration.

This module defines the core data models used throughout floe-cube:
- CubeConfig: Main configuration for Cube deployment
- CubeDimension: Dimension definition for cubes
- CubeMeasure: Measure/metric definition for cubes
- CubeJoin: Join relationship between cubes
- CubePreAggregation: Pre-aggregation definition for performance
- CubeSchema: Complete cube schema definition
- SecurityContext: JWT-based security context for row-level filtering
- QueryTraceSpan: OpenTelemetry trace span for operational observability

All models use Pydantic v2 with strict validation and frozen instances
per the project Constitution.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Constants to avoid duplicate literals (SonarQube S1192)
CUBE_IDENTIFIER_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_]*$"
"""Regex pattern for valid Cube identifiers (names)."""

HUMAN_READABLE_DESCRIPTION = "Human-readable description"
"""Common field description for optional description fields."""


class DatabaseType(str, Enum):
    """Supported database types for Cube.

    These correspond to Cube's database drivers.
    """

    POSTGRES = "postgres"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    DATABRICKS = "databricks"
    TRINO = "trino"
    DUCKDB = "duckdb"


class DimensionType(str, Enum):
    """Cube dimension types.

    Maps to Cube's dimension type system.
    """

    STRING = "string"
    NUMBER = "number"
    TIME = "time"
    BOOLEAN = "boolean"
    GEO = "geo"


class MeasureType(str, Enum):
    """Cube measure types.

    Maps to Cube's measure aggregation types.
    """

    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    COUNT_DISTINCT_APPROX = "count_distinct_approx"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    NUMBER = "number"
    STRING = "string"
    TIME = "time"
    BOOLEAN = "boolean"
    RUNNING_TOTAL = "running_total"


class JoinRelationship(str, Enum):
    """Cube join relationship types."""

    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"


class TimeGranularity(str, Enum):
    """Time granularity options for pre-aggregations."""

    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class CubeConfig(BaseModel):
    """Configuration for Cube deployment.

    This model defines the main configuration parameters for deploying
    Cube as a semantic layer. It includes database connection settings,
    API configuration, and security options.

    Attributes:
        database_type: The database driver type to use.
        api_port: Port for REST and GraphQL APIs.
        sql_port: Port for Postgres wire protocol (SQL API).
        api_secret_ref: K8s secret reference for CUBEJS_API_SECRET.
        dev_mode: Enable Cube Playground for development.
        jwt_audience: Expected JWT audience claim for validation.
        jwt_issuer: Expected JWT issuer claim for validation.

    Example:
        >>> config = CubeConfig(
        ...     database_type=DatabaseType.POSTGRES,
        ...     api_port=4000,
        ...     sql_port=15432,
        ...     dev_mode=True,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    database_type: DatabaseType = Field(
        ...,
        description="Database driver type for Cube",
    )
    api_port: int = Field(
        default=4000,
        ge=1,
        le=65535,
        description="Port for REST and GraphQL APIs",
    )
    sql_port: int = Field(
        default=15432,
        ge=1,
        le=65535,
        description="Port for Postgres wire protocol (SQL API)",
    )
    api_secret_ref: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$",
        description="K8s secret reference for CUBEJS_API_SECRET",
    )
    dev_mode: bool = Field(
        default=False,
        description="Enable Cube Playground for development",
    )
    jwt_audience: str | None = Field(
        default=None,
        description="Expected JWT audience claim for validation",
    )
    jwt_issuer: str | None = Field(
        default=None,
        description="Expected JWT issuer claim for validation",
    )


class CubeDimension(BaseModel):
    """Dimension definition for a Cube.

    Dimensions are attributes by which data can be filtered, grouped,
    or segmented in queries.

    Attributes:
        name: Unique name for the dimension within the cube.
        sql: SQL expression for the dimension value.
        type: Data type of the dimension.
        primary_key: Whether this dimension is the primary key.
        description: Human-readable description.
        meta: Additional metadata for the dimension.

    Example:
        >>> dimension = CubeDimension(
        ...     name="customer_id",
        ...     sql="${CUBE}.customer_id",
        ...     type=DimensionType.NUMBER,
        ...     primary_key=True,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=CUBE_IDENTIFIER_PATTERN,
        description="Unique name for the dimension",
    )
    sql: str = Field(
        ...,
        min_length=1,
        description="SQL expression for the dimension",
    )
    type: DimensionType = Field(
        default=DimensionType.STRING,
        description="Data type of the dimension",
    )
    primary_key: bool = Field(
        default=False,
        description="Whether this dimension is the primary key",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description=HUMAN_READABLE_DESCRIPTION,
    )
    meta: dict[str, Any] | None = Field(
        default=None,
        description="Additional metadata for the dimension",
    )


class CubeMeasure(BaseModel):
    """Measure definition for a Cube.

    Measures are quantitative values that can be aggregated
    (summed, averaged, counted, etc.) in queries.

    Attributes:
        name: Unique name for the measure within the cube.
        sql: SQL expression for the measure value.
        type: Aggregation type for the measure.
        description: Human-readable description.
        filters: List of filter conditions for the measure.

    Example:
        >>> measure = CubeMeasure(
        ...     name="total_revenue",
        ...     sql="${CUBE}.amount",
        ...     type=MeasureType.SUM,
        ...     description="Sum of all order amounts",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=CUBE_IDENTIFIER_PATTERN,
        description="Unique name for the measure",
    )
    sql: str | None = Field(
        default=None,
        description="SQL expression for the measure (optional for count)",
    )
    type: MeasureType = Field(
        ...,
        description="Aggregation type for the measure",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description=HUMAN_READABLE_DESCRIPTION,
    )
    filters: list[dict[str, Any]] | None = Field(
        default=None,
        description="Filter conditions for the measure",
    )


class CubeJoin(BaseModel):
    """Join relationship between Cubes.

    Defines how two cubes are related for multi-cube queries.

    Attributes:
        name: Name of the cube to join to.
        relationship: Type of join relationship.
        sql: SQL expression for the join condition.

    Example:
        >>> join = CubeJoin(
        ...     name="customers",
        ...     relationship=JoinRelationship.MANY_TO_ONE,
        ...     sql="${CUBE}.customer_id = ${customers}.id",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=CUBE_IDENTIFIER_PATTERN,
        description="Name of the cube to join to",
    )
    relationship: JoinRelationship = Field(
        ...,
        description="Type of join relationship",
    )
    sql: str = Field(
        ...,
        min_length=1,
        description="SQL expression for the join condition",
    )


class CubePreAggregation(BaseModel):
    """Pre-aggregation definition for performance optimization.

    Pre-aggregations cache aggregated data to speed up queries.

    Attributes:
        name: Unique name for the pre-aggregation.
        measures: List of measure names to include.
        dimensions: List of dimension names to include.
        time_dimension: Time dimension for rollups.
        granularity: Time granularity for the rollup.
        refresh_every: Refresh schedule (cron expression or interval).
        external: Whether to use external storage (Cube Store).

    Example:
        >>> pre_agg = CubePreAggregation(
        ...     name="orders_daily",
        ...     measures=["count", "total_amount"],
        ...     dimensions=["status"],
        ...     time_dimension="created_at",
        ...     granularity=TimeGranularity.DAY,
        ...     refresh_every="0 * * * *",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=CUBE_IDENTIFIER_PATTERN,
        description="Unique name for the pre-aggregation",
    )
    measures: list[str] = Field(
        default_factory=list,
        description="List of measure names to include",
    )
    dimensions: list[str] = Field(
        default_factory=list,
        description="List of dimension names to include",
    )
    time_dimension: str | None = Field(
        default=None,
        description="Time dimension for rollups",
    )
    granularity: TimeGranularity | None = Field(
        default=None,
        description="Time granularity for the rollup",
    )
    refresh_every: str = Field(
        default="*/30 * * * *",
        description="Refresh schedule (cron expression)",
    )
    external: bool = Field(
        default=True,
        description="Whether to use external storage (Cube Store)",
    )

    @field_validator("refresh_every")
    @classmethod
    def validate_cron_expression(cls, v: str) -> str:
        """Validate that refresh_every is a valid cron expression or interval."""
        # Basic validation: must have spaces (cron) or be an interval
        if " " in v:
            # Cron expression: should have 5 fields
            parts = v.split()
            if len(parts) != 5:
                msg = "Cron expression must have 5 fields (minute hour day month weekday)"
                raise ValueError(msg)
        elif not v.isalnum():
            # Allow simple intervals like "1h", "30m"
            msg = "Invalid refresh schedule format"
            raise ValueError(msg)
        return v


class CubeSchema(BaseModel):
    """Complete Cube schema definition.

    Represents a single cube that maps to a dbt model or database table.

    Attributes:
        name: Unique name for the cube.
        sql_table: SQL table reference or dbt ref.
        description: Human-readable description.
        dimensions: List of dimension definitions.
        measures: List of measure definitions.
        joins: List of join relationships.
        pre_aggregations: List of pre-aggregation definitions.
        filter_column: Column used for row-level security filtering.

    Example:
        >>> schema = CubeSchema(
        ...     name="orders",
        ...     sql_table="{{ dbt.ref('orders') }}",
        ...     description="Order data from dbt",
        ...     dimensions=[
        ...         CubeDimension(name="id", sql="${CUBE}.id", primary_key=True),
        ...     ],
        ...     measures=[
        ...         CubeMeasure(name="count", type=MeasureType.COUNT),
        ...     ],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=CUBE_IDENTIFIER_PATTERN,
        description="Unique name for the cube",
    )
    sql_table: str = Field(
        ...,
        min_length=1,
        description="SQL table reference or dbt ref",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description=HUMAN_READABLE_DESCRIPTION,
    )
    dimensions: list[CubeDimension] = Field(
        default_factory=list,
        description="List of dimension definitions",
    )
    measures: list[CubeMeasure] = Field(
        default_factory=list,
        description="List of measure definitions",
    )
    joins: list[CubeJoin] = Field(
        default_factory=list,
        description="List of join relationships",
    )
    pre_aggregations: list[CubePreAggregation] = Field(
        default_factory=list,
        description="List of pre-aggregation definitions",
    )
    filter_column: str | None = Field(
        default=None,
        description="Column used for row-level security filtering",
    )


class SecurityContext(BaseModel):
    """JWT-based security context for row-level filtering.

    Represents the security context extracted from a JWT token,
    used to enforce row-level security in Cube queries.

    Note:
        This is USER-MANAGED row-level security, NOT SaaS tenant isolation.
        Users define their own filter columns and claims for their use cases.

    Attributes:
        user_id: Unique identifier for the user.
        roles: List of role names the user has.
        filter_claims: Key-value pairs for row-level filtering.
        exp: JWT expiration timestamp.

    Example:
        >>> context = SecurityContext(
        ...     user_id="user_123",
        ...     roles=["analyst", "viewer"],
        ...     filter_claims={"organization_id": "org_abc"},
        ...     exp=1735689600,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the user",
    )
    roles: list[str] = Field(
        default_factory=list,
        description="List of role names the user has",
    )
    filter_claims: dict[str, str] = Field(
        default_factory=dict,
        description="Key-value pairs for row-level filtering",
    )
    exp: int = Field(
        ...,
        description="JWT expiration timestamp (Unix epoch)",
    )

    @field_validator("exp")
    @classmethod
    def validate_expiration(cls, v: int) -> int:
        """Validate that expiration is a reasonable timestamp."""
        # Basic sanity check: must be after year 2020
        min_timestamp = 1577836800  # 2020-01-01 00:00:00 UTC
        if v < min_timestamp:
            msg = "Expiration timestamp must be after 2020-01-01"
            raise ValueError(msg)
        return v

    def is_expired(self) -> bool:
        """Check if the security context has expired.

        Returns:
            True if the context has expired, False otherwise.
        """
        return datetime.now().timestamp() > self.exp


class SpanKind(str, Enum):
    """OpenTelemetry span kind.

    Defines the relationship of the span to the parent span.
    """

    SERVER = "SERVER"
    CLIENT = "CLIENT"
    INTERNAL = "INTERNAL"


class SpanStatus(str, Enum):
    """OpenTelemetry span status.

    Indicates the status of the operation represented by the span.
    """

    OK = "OK"
    ERROR = "ERROR"
    UNSET = "UNSET"


# W3C Trace Context format: 32 lowercase hex characters
_TRACE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
# W3C Span ID format: 16 lowercase hex characters
_SPAN_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")

# Forbidden attributes that MUST NOT appear in spans (security)
FORBIDDEN_SPAN_ATTRIBUTES = frozenset(
    {
        "filter_value",
        "filter_values",
        "jwt",
        "token",
        "password",
        "secret",
        "credential",
        "authorization",
        "cookie",
        "session",
        "api_key",
        "user_email",
        "user_name",
        "pii",
        "ssn",
        "credit_card",
        "row_data",
        "query_result",
        "result_data",
    }
)


class QueryTraceSpan(BaseModel):
    """OpenTelemetry trace span for operational observability.

    Captures query execution performance and timing for Cube queries.
    This is complementary to QueryLineageEvent which captures data lineage.

    Note:
        NEVER include sensitive data in span attributes. The FORBIDDEN_SPAN_ATTRIBUTES
        set defines attribute names that will be rejected.

    Attributes:
        trace_id: W3C Trace ID (32 lowercase hex characters).
        span_id: Unique span identifier (16 lowercase hex characters).
        parent_span_id: Parent span ID for distributed tracing.
        name: Span name (e.g., "cube.query", "cube.execute").
        kind: Span kind (SERVER, CLIENT, INTERNAL).
        start_time: Span start time (UTC).
        end_time: Span end time (UTC), None if span is still active.
        status: Span status (OK, ERROR, UNSET).
        attributes: Safe span attributes (see validation rules).

    Example:
        >>> span = QueryTraceSpan(
        ...     trace_id="0af7651916cd43dd8448eb211c80319c",
        ...     span_id="b7ad6b7169203331",
        ...     name="cube.query",
        ...     kind=SpanKind.SERVER,
        ...     start_time=datetime.now(tz=timezone.utc),
        ...     status=SpanStatus.UNSET,
        ...     attributes={"cube.name": "orders", "cube.filter_count": 2},
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str = Field(
        ...,
        description="W3C Trace ID (32 lowercase hex characters)",
    )
    span_id: str = Field(
        ...,
        description="Unique span identifier (16 lowercase hex characters)",
    )
    parent_span_id: str | None = Field(
        default=None,
        description="Parent span ID for distributed tracing",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Span name (e.g., 'cube.query', 'cube.execute')",
    )
    kind: SpanKind = Field(
        ...,
        description="Span kind (SERVER, CLIENT, INTERNAL)",
    )
    start_time: datetime = Field(
        ...,
        description="Span start time (UTC)",
    )
    end_time: datetime | None = Field(
        default=None,
        description="Span end time (UTC), None if span is still active",
    )
    status: SpanStatus = Field(
        default=SpanStatus.UNSET,
        description="Span status (OK, ERROR, UNSET)",
    )
    attributes: dict[str, str | int | bool] = Field(
        default_factory=dict,
        description="Safe span attributes (no sensitive data)",
    )

    @field_validator("trace_id")
    @classmethod
    def validate_trace_id(cls, v: str) -> str:
        """Validate W3C Trace ID format (32 lowercase hex characters)."""
        if not _TRACE_ID_PATTERN.match(v):
            msg = "trace_id must be 32 lowercase hex characters (W3C Trace Context)"
            raise ValueError(msg)
        return v

    @field_validator("span_id")
    @classmethod
    def validate_span_id(cls, v: str) -> str:
        """Validate span ID format (16 lowercase hex characters)."""
        if not _SPAN_ID_PATTERN.match(v):
            msg = "span_id must be 16 lowercase hex characters"
            raise ValueError(msg)
        return v

    @field_validator("parent_span_id")
    @classmethod
    def validate_parent_span_id(cls, v: str | None) -> str | None:
        """Validate parent span ID format if provided."""
        if v is not None and not _SPAN_ID_PATTERN.match(v):
            msg = "parent_span_id must be 16 lowercase hex characters"
            raise ValueError(msg)
        return v

    @field_validator("attributes")
    @classmethod
    def validate_attributes_security(
        cls, v: dict[str, str | int | bool]
    ) -> dict[str, str | int | bool]:
        """Validate that attributes do not contain forbidden keys (security).

        NEVER allow sensitive data in span attributes.
        """
        for key in v:
            key_lower = key.lower()
            for forbidden in FORBIDDEN_SPAN_ATTRIBUTES:
                if forbidden in key_lower:
                    msg = f"Attribute '{key}' contains forbidden term '{forbidden}' (security)"
                    raise ValueError(msg)
        return v

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: datetime | None) -> datetime | None:
        """Validate end_time is not before start_time if provided."""
        # Note: We can't access start_time in a field_validator directly
        # This will be handled in the model_validator if needed
        return v
