"""Compute configuration models for floe-runtime.

T020: [US1] Implement ComputeTarget enum with 7 targets
T021: [US1] Implement ComputeConfig with secret ref validation

This module defines ComputeTarget enum and ComputeConfig model
for specifying compute targets (dbt adapters).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ComputeTarget(str, Enum):
    """Supported compute targets matching dbt adapter names.

    These values correspond to dbt adapter names for SQL compilation
    and execution targeting.
    """

    duckdb = "duckdb"
    snowflake = "snowflake"
    bigquery = "bigquery"
    redshift = "redshift"
    databricks = "databricks"
    postgres = "postgres"
    spark = "spark"


class ComputeConfig(BaseModel):
    """Configuration for compute target.

    T062: [US5] Document target-specific properties

    Defines which compute target to use and optional connection
    credentials via K8s secret reference.

    Attributes:
        target: Compute target enum value (duckdb, snowflake, etc.)
        connection_secret_ref: Optional K8s secret name for credentials.
            Must match K8s naming convention.
        properties: Target-specific properties. Common properties per target:

            DuckDB:
                - path: Database file path or ":memory:" (default: ":memory:")
                - threads: Number of threads (default: 4)

            Snowflake:
                - account: Snowflake account identifier (required)
                - warehouse: Virtual warehouse name
                - database: Default database
                - schema: Default schema
                - role: User role

            BigQuery:
                - project: GCP project ID (required)
                - dataset: Default dataset
                - location: Dataset location (US, EU, etc.)
                - method: Auth method (oauth, service-account)

            Redshift:
                - host: Cluster endpoint (required)
                - port: Connection port (default: 5439)
                - database: Database name

            Databricks:
                - host: Workspace URL (required)
                - http_path: SQL warehouse HTTP path
                - catalog: Unity Catalog name
                - schema: Default schema

            PostgreSQL:
                - host: Database host (required)
                - port: Connection port (default: 5432)
                - database: Database name
                - schema: Default schema

            Spark:
                - host: Spark master URL
                - method: Connection method (thrift, http)
                - cluster: Cluster identifier

    Example:
        >>> config = ComputeConfig(
        ...     target=ComputeTarget.snowflake,
        ...     connection_secret_ref="snowflake-prod-creds",
        ...     properties={"account": "xy12345.us-east-1", "warehouse": "COMPUTE_WH"}
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    target: ComputeTarget
    connection_secret_ref: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$",
        description="K8s secret name for connection credentials",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Target-specific properties",
    )
