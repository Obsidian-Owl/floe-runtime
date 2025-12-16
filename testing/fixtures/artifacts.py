"""Shared CompiledArtifacts fixtures for cross-package testing.

This module provides factory functions and fixtures for creating
CompiledArtifacts instances with various configurations.

The factories here mirror the structure in packages/floe-dbt/tests/conftest.py
but are designed for cross-package use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def base_metadata(
    *,
    floe_core_version: str = "0.1.0",
    source_hash: str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
) -> dict[str, Any]:
    """Create base artifact metadata.

    Args:
        floe_core_version: Version of floe-core that compiled the artifacts.
        source_hash: SHA256 hash of the source floe.yaml.

    Returns:
        Metadata dictionary for CompiledArtifacts.
    """
    return {
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "floe_core_version": floe_core_version,
        "source_hash": source_hash,
    }


# Pre-defined compute configurations for all 7 supported targets
COMPUTE_CONFIGS: dict[str, dict[str, Any]] = {
    "duckdb": {
        "target": "duckdb",
        "connection_secret_ref": None,
        "properties": {
            "path": ":memory:",
            "threads": 4,
        },
    },
    "snowflake": {
        "target": "snowflake",
        "connection_secret_ref": "snowflake-creds",
        "properties": {
            "account": "xy12345.us-east-1",
            "warehouse": "COMPUTE_WH",
            "database": "ANALYTICS",
            "schema": "PUBLIC",
            "role": "TRANSFORMER",
        },
    },
    "bigquery": {
        "target": "bigquery",
        "connection_secret_ref": None,
        "properties": {
            "project": "my-gcp-project",
            "dataset": "analytics",
            "location": "US",
            "method": "oauth",
        },
    },
    "redshift": {
        "target": "redshift",
        "connection_secret_ref": "redshift-creds",
        "properties": {
            "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
            "port": 5439,
            "database": "analytics",
            "schema": "public",
        },
    },
    "databricks": {
        "target": "databricks",
        "connection_secret_ref": "databricks-creds",
        "properties": {
            "host": "adb-1234567890.12.azuredatabricks.net",
            "http_path": "/sql/1.0/warehouses/abc123",
            "catalog": "main",
            "schema": "default",
        },
    },
    "postgres": {
        "target": "postgres",
        "connection_secret_ref": "postgres-creds",
        "properties": {
            "host": "localhost",
            "port": 5432,
            "database": "analytics",
            "schema": "public",
        },
    },
    "spark": {
        "target": "spark",
        "connection_secret_ref": None,
        "properties": {
            "host": "spark://master:7077",
            "method": "thrift",
            "schema": "default",
        },
    },
}


def make_compiled_artifacts(
    target: str = "duckdb",
    *,
    environment: str = "dev",
    observability_enabled: bool = False,
    lineage_enabled: bool = False,
    with_classifications: bool = False,
    dbt_profiles_path: str = ".floe/profiles",
    metadata: dict[str, Any] | None = None,
    compute_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Factory for creating CompiledArtifacts test fixtures.

    This factory creates CompiledArtifacts-compatible dictionaries for testing.
    All fields match the expected structure of the CompiledArtifacts Pydantic model.

    Args:
        target: Compute target name (duckdb, snowflake, bigquery, etc.).
        environment: Environment name (dev, staging, prod).
        observability_enabled: Enable traces and metrics.
        lineage_enabled: Enable OpenLineage integration.
        with_classifications: Include sample column classifications.
        dbt_profiles_path: Path for dbt profiles output.
        metadata: Override metadata dict. If None, uses defaults.
        compute_overrides: Override specific compute properties.

    Returns:
        CompiledArtifacts-compatible dictionary.

    Raises:
        ValueError: If target is not one of the 7 supported targets.

    Example:
        >>> artifacts = make_compiled_artifacts("snowflake", environment="prod")
        >>> artifacts["compute"]["target"]
        'snowflake'
    """
    if target not in COMPUTE_CONFIGS:
        supported = ", ".join(sorted(COMPUTE_CONFIGS.keys()))
        raise ValueError(f"Unknown target '{target}'. Supported: {supported}")

    # Get base compute config and apply overrides
    compute = COMPUTE_CONFIGS[target].copy()
    if compute_overrides:
        compute["properties"] = {**compute.get("properties", {}), **compute_overrides}

    # Build observability config
    observability: dict[str, Any] = {
        "traces": {"enabled": observability_enabled},
        "lineage": {"enabled": lineage_enabled},
    }

    # Build classifications if requested
    column_classifications: dict[str, Any] | None = None
    if with_classifications:
        column_classifications = {
            "customers": {
                "email": {"classification": "pii", "pii_type": "email"},
                "phone": {"classification": "pii", "pii_type": "phone"},
            },
        }

    # Build environment context if not dev
    environment_context: dict[str, Any] | None = None
    if environment != "dev":
        environment_context = {
            "environment": environment,
            "tenant_id": f"tenant-{environment}",
        }

    return {
        "version": "1.0.0",
        "metadata": metadata or base_metadata(),
        "compute": compute,
        "transforms": [{"type": "dbt", "project_dir": ".", "profiles_dir": dbt_profiles_path}],
        "consumption": {"enabled": False},
        "governance": {"enabled": False},
        "observability": observability,
        "catalog": None,
        "dbt_manifest_path": None,
        "dbt_project_path": ".",
        "dbt_profiles_path": dbt_profiles_path,
        "lineage_namespace": "floe" if lineage_enabled else None,
        "environment_context": environment_context,
        "column_classifications": column_classifications,
    }


def make_minimal_artifacts(target: str = "duckdb") -> dict[str, Any]:
    """Create minimal CompiledArtifacts with only required fields.

    Useful for testing backward compatibility and minimal configurations.

    Args:
        target: Compute target name.

    Returns:
        Minimal CompiledArtifacts-compatible dictionary.
    """
    return {
        "version": "1.0.0",
        "metadata": base_metadata(),
        "compute": {"target": target},
        "transforms": [{"type": "dbt", "path": "./dbt"}],
        "consumption": {},
        "governance": {},
        "observability": {},
    }
