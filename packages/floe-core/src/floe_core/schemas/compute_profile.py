"""Compute profile models for floe-runtime.

This module defines compute backend configuration including:
- ComputeProfile: dbt adapter configuration for the two-tier architecture
- Uses ComputeTarget enum from compute.py

Note: ComputeProfile wraps the existing ComputeTarget/ComputeConfig
      with CredentialConfig integration for the platform.yaml pattern.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from floe_core.schemas.compute import ComputeTarget
from floe_core.schemas.credential_config import CredentialConfig

# Default compute type for local development
DEFAULT_COMPUTE_TYPE = ComputeTarget.duckdb


class ComputeProfile(BaseModel):
    """Compute engine configuration for platform.yaml.

    Defines connection parameters for dbt compute targets.
    Uses CredentialConfig for consistent credential management.

    Attributes:
        type: Compute target type (duckdb, snowflake, bigquery, etc.).
        properties: Target-specific connection properties.
        credentials: Credential configuration.

    Example:
        >>> profile = ComputeProfile(
        ...     type=ComputeTarget.snowflake,
        ...     properties={
        ...         "account": "acme.us-east-1",
        ...         "warehouse": "ANALYTICS_WH",
        ...         "database": "PROD",
        ...     },
        ...     credentials=CredentialConfig(
        ...         mode=CredentialMode.STATIC,
        ...         secret_ref="snowflake-credentials",
        ...     ),
        ... )

    Target-specific properties:
        DuckDB:
            - path: Database file path or ":memory:" (default: ":memory:")
            - threads: Number of threads (default: 4)
            - memory_limit: Memory limit (e.g., "4GB")

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

        Redshift:
            - host: Cluster endpoint (required)
            - port: Connection port (default: 5439)
            - database: Database name

        Databricks:
            - host: Workspace URL (required)
            - http_path: SQL warehouse HTTP path
            - catalog: Unity Catalog name

        PostgreSQL:
            - host: Database host (required)
            - port: Connection port (default: 5432)
            - database: Database name

        Spark:
            - host: Spark master URL
            - method: Connection method (thrift, http)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: ComputeTarget = Field(
        default=DEFAULT_COMPUTE_TYPE,
        description="Compute target type (dbt adapter)",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Target-specific connection properties",
    )
    credentials: CredentialConfig = Field(
        default_factory=CredentialConfig,
        description="Credential configuration",
    )
