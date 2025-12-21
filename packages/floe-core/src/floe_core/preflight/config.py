"""Preflight configuration model.

Configuration for pre-deployment validation checks.

Covers: 007-FR-005 (pre-deployment validation)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ComputeCheckConfig(BaseModel):
    """Configuration for compute engine connectivity checks.

    Attributes:
        enabled: Whether to check compute connectivity
        timeout_seconds: Connection timeout in seconds
        type: Compute engine type (trino, snowflake, bigquery, databricks)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=True, description="Enable compute check")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")
    type: str = Field(default="trino", description="Compute engine type")


class StorageCheckConfig(BaseModel):
    """Configuration for storage connectivity checks.

    Attributes:
        enabled: Whether to check storage connectivity
        timeout_seconds: Connection timeout in seconds
        bucket: S3/GCS/ADLS bucket to verify access
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=True, description="Enable storage check")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")
    bucket: str = Field(default="", description="Storage bucket name")


class CatalogCheckConfig(BaseModel):
    """Configuration for catalog connectivity checks.

    Attributes:
        enabled: Whether to check catalog connectivity
        timeout_seconds: Connection timeout in seconds
        uri: Catalog REST API URI
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=True, description="Enable catalog check")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")
    uri: str = Field(default="", description="Catalog URI")


class PostgresCheckConfig(BaseModel):
    """Configuration for PostgreSQL connectivity checks.

    Validates Dagster metadata database connectivity.

    Attributes:
        enabled: Whether to check PostgreSQL connectivity
        timeout_seconds: Connection timeout in seconds
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=True, description="Enable PostgreSQL check")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")
    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL port")
    database: str = Field(default="dagster", description="Database name")


class OTelCheckConfig(BaseModel):
    """Configuration for OpenTelemetry collector checks.

    Attributes:
        enabled: Whether to check OTel connectivity
        timeout_seconds: Connection timeout in seconds
        endpoint: OTel collector endpoint
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=False, description="Enable OTel check (optional)")
    timeout_seconds: int = Field(default=10, ge=1, le=60, description="Timeout in seconds")
    endpoint: str = Field(default="", description="OTel collector endpoint")


class PreflightConfig(BaseModel):
    """Configuration for preflight validation.

    Defines which checks to run and their parameters.

    Attributes:
        compute: Compute engine check configuration
        storage: Storage check configuration
        catalog: Catalog check configuration
        postgres: PostgreSQL check configuration
        otel: OpenTelemetry check configuration
        fail_fast: Stop on first failure
        verbose: Enable verbose output

    Example:
        >>> config = PreflightConfig(
        ...     compute=ComputeCheckConfig(type="trino"),
        ...     storage=StorageCheckConfig(bucket="my-bucket"),
        ...     fail_fast=True,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    compute: ComputeCheckConfig = Field(
        default_factory=ComputeCheckConfig,
        description="Compute engine check config",
    )
    storage: StorageCheckConfig = Field(
        default_factory=StorageCheckConfig,
        description="Storage check config",
    )
    catalog: CatalogCheckConfig = Field(
        default_factory=CatalogCheckConfig,
        description="Catalog check config",
    )
    postgres: PostgresCheckConfig = Field(
        default_factory=PostgresCheckConfig,
        description="PostgreSQL check config",
    )
    otel: OTelCheckConfig = Field(
        default_factory=OTelCheckConfig,
        description="OTel check config",
    )
    fail_fast: bool = Field(default=False, description="Stop on first failure")
    verbose: bool = Field(default=False, description="Verbose output")
