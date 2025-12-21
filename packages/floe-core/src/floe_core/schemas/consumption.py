"""Consumption configuration models for floe-runtime.

T023: [US1] Implement PreAggregationConfig with defaults
T024: [US1] Implement CubeSecurityConfig with defaults
T025: [US1] Implement ConsumptionConfig with database_type

This module defines configuration models for the Cube semantic layer.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Pattern for K8s secret names (RFC 1123 subdomain)
K8S_SECRET_NAME_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$"


class CubeStoreConfig(BaseModel):
    """Configuration for Cube Store pre-aggregation storage.

    Cube Store is a purpose-built columnar storage engine for pre-aggregations.
    It stores data as Parquet files in S3/GCS and provides sub-second query latency.

    Attributes:
        enabled: Enable Cube Store for external pre-aggregation storage.
        s3_bucket: S3 bucket name for pre-aggregation Parquet files.
        s3_region: AWS region for the S3 bucket.
        s3_endpoint: Custom S3 endpoint (for MinIO, LocalStack, etc.).
        s3_access_key_ref: K8s secret name containing S3 access key.
        s3_secret_key_ref: K8s secret name containing S3 secret key.

    Example:
        >>> config = CubeStoreConfig(
        ...     enabled=True,
        ...     s3_bucket="my-cube-preaggs",
        ...     s3_region="us-east-1"
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable Cube Store for external pre-aggregation storage",
    )
    s3_bucket: str | None = Field(
        default=None,
        description="S3 bucket for pre-aggregation Parquet files",
    )
    s3_region: str | None = Field(
        default=None,
        description="AWS region for S3 bucket",
    )
    s3_endpoint: str | None = Field(
        default=None,
        description="Custom S3 endpoint (for MinIO, LocalStack, etc.)",
    )
    s3_access_key_ref: str | None = Field(
        default=None,
        pattern=K8S_SECRET_NAME_PATTERN,
        description="K8s secret name containing S3 access key",
    )
    s3_secret_key_ref: str | None = Field(
        default=None,
        pattern=K8S_SECRET_NAME_PATTERN,
        description="K8s secret name containing S3 secret key",
    )


class ExportBucketConfig(BaseModel):
    """Configuration for Cube export bucket (large pre-aggregation builds).

    Export buckets are used by Trino/Snowflake for datasets >100k rows.
    The source database writes temporary data to this bucket during builds,
    which is then loaded into Cube Store in parallel for faster ingestion.

    Note:
        DuckDB does NOT support export buckets - it uses batching only.
        Export buckets are primarily for Trino, Snowflake, and BigQuery.

    Attributes:
        enabled: Enable export bucket for large pre-aggregation builds.
        bucket_type: Storage type - 's3' or 'gcs'.
        name: Bucket name.
        region: AWS region (for S3 buckets).
        access_key_ref: K8s secret name containing bucket access key.
        secret_key_ref: K8s secret name containing bucket secret key.
        integration: Snowflake storage integration name (Snowflake-specific).

    Example:
        >>> config = ExportBucketConfig(
        ...     enabled=True,
        ...     bucket_type="s3",
        ...     name="my-cube-export",
        ...     region="us-east-1"
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable export bucket for large pre-aggregation builds",
    )
    bucket_type: str | None = Field(
        default=None,
        description="Storage type: 's3' or 'gcs'",
    )
    name: str | None = Field(
        default=None,
        description="Bucket name",
    )
    region: str | None = Field(
        default=None,
        description="AWS region (for S3 buckets)",
    )
    access_key_ref: str | None = Field(
        default=None,
        pattern=K8S_SECRET_NAME_PATTERN,
        description="K8s secret name containing bucket access key",
    )
    secret_key_ref: str | None = Field(
        default=None,
        pattern=K8S_SECRET_NAME_PATTERN,
        description="K8s secret name containing bucket secret key",
    )
    integration: str | None = Field(
        default=None,
        description="Snowflake storage integration name",
    )


class PreAggregationConfig(BaseModel):
    """Configuration for Cube pre-aggregations.

    Pre-aggregations are materialized rollups that improve query performance.
    They can be stored in the source database (external=False) or in Cube Store
    (external=True) for production workloads.

    Attributes:
        refresh_schedule: Cron expression for refresh schedule.
        timezone: Timezone for the schedule.
        external: Use external storage (Cube Store) for pre-aggregations.
            Recommended for production. Set to False for testing.
        cube_store: Cube Store configuration for external pre-aggregations.
        export_bucket: Export bucket for large pre-aggregation builds.

    Example:
        >>> # Testing configuration (source database storage)
        >>> config = PreAggregationConfig(
        ...     refresh_schedule="0 * * * *",
        ...     timezone="America/New_York",
        ...     external=False
        ... )

        >>> # Production configuration (Cube Store + S3)
        >>> config = PreAggregationConfig(
        ...     external=True,
        ...     cube_store=CubeStoreConfig(
        ...         enabled=True,
        ...         s3_bucket="my-cube-preaggs",
        ...         s3_region="us-east-1"
        ...     )
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
    external: bool = Field(
        default=True,
        description="Use external storage (Cube Store) - recommended for production",
    )
    cube_store: CubeStoreConfig = Field(
        default_factory=CubeStoreConfig,
        description="Cube Store configuration for external pre-aggregations",
    )
    export_bucket: ExportBucketConfig = Field(
        default_factory=ExportBucketConfig,
        description="Export bucket for large pre-aggregation builds (Trino/Snowflake)",
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
