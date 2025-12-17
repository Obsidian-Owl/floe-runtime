"""Shared test fixtures for floe-dbt tests.

T013: Create shared test fixtures for CompiledArtifacts mocking

This module provides pytest fixtures for testing profile generators
with mock CompiledArtifacts data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

# Type alias for CompiledArtifacts to avoid import dependency
# In tests, we'll use dicts that match the expected structure
CompiledArtifactsDict = dict[str, Any]

# Constants for test fixtures to avoid duplication
PROFILES_DIR = ".floe/profiles"


@pytest.fixture
def base_metadata() -> dict[str, Any]:
    """Base artifact metadata fixture."""
    return {
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "floe_core_version": "0.1.0",
        "source_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }


@pytest.fixture
def duckdb_compute_config() -> dict[str, Any]:
    """DuckDB compute configuration fixture."""
    return {
        "target": "duckdb",
        "connection_secret_ref": None,
        "properties": {
            "path": ":memory:",
            "threads": 4,
        },
    }


@pytest.fixture
def snowflake_compute_config() -> dict[str, Any]:
    """Snowflake compute configuration fixture."""
    return {
        "target": "snowflake",
        "connection_secret_ref": "snowflake-creds",
        "properties": {
            "account": "xy12345.us-east-1",
            "warehouse": "COMPUTE_WH",
            "database": "ANALYTICS",
            "schema": "PUBLIC",
            "role": "TRANSFORMER",
        },
    }


@pytest.fixture
def bigquery_compute_config() -> dict[str, Any]:
    """BigQuery compute configuration fixture."""
    return {
        "target": "bigquery",
        "connection_secret_ref": None,
        "properties": {
            "project": "my-gcp-project",
            "dataset": "analytics",
            "location": "US",
            "method": "oauth",
        },
    }


@pytest.fixture
def redshift_compute_config() -> dict[str, Any]:
    """Redshift compute configuration fixture."""
    return {
        "target": "redshift",
        "connection_secret_ref": "redshift-creds",
        "properties": {
            "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
            "port": 5439,
            "database": "analytics",
            "schema": "public",
        },
    }


@pytest.fixture
def databricks_compute_config() -> dict[str, Any]:
    """Databricks compute configuration fixture."""
    return {
        "target": "databricks",
        "connection_secret_ref": "databricks-creds",
        "properties": {
            "host": "adb-1234567890.12.azuredatabricks.net",
            "http_path": "/sql/1.0/warehouses/abc123",
            "catalog": "main",
            "schema": "default",
        },
    }


@pytest.fixture
def postgres_compute_config() -> dict[str, Any]:
    """PostgreSQL compute configuration fixture."""
    return {
        "target": "postgres",
        "connection_secret_ref": "postgres-creds",
        "properties": {
            "host": "localhost",
            "port": 5432,
            "database": "analytics",
            "schema": "public",
        },
    }


@pytest.fixture
def spark_compute_config() -> dict[str, Any]:
    """Spark compute configuration fixture."""
    return {
        "target": "spark",
        "connection_secret_ref": None,
        "properties": {
            "host": "spark://master:7077",
            "method": "thrift",
            "schema": "default",
        },
    }


@pytest.fixture
def minimal_compiled_artifacts(
    base_metadata: dict[str, Any],
    duckdb_compute_config: dict[str, Any],
) -> CompiledArtifactsDict:
    """Minimal CompiledArtifacts fixture with DuckDB target."""
    return {
        "version": "1.0.0",
        "metadata": base_metadata,
        "compute": duckdb_compute_config,
        "transforms": [{"type": "dbt", "project_dir": ".", "profiles_dir": PROFILES_DIR}],
        "consumption": {"enabled": False},
        "governance": {"enabled": False},
        "observability": {"traces": {"enabled": False}, "lineage": {"enabled": False}},
        "catalog": None,
        "dbt_manifest_path": None,
        "dbt_project_path": ".",
        "dbt_profiles_path": PROFILES_DIR,
        "lineage_namespace": None,
        "environment_context": None,
        "column_classifications": None,
    }


@pytest.fixture
def snowflake_compiled_artifacts(
    base_metadata: dict[str, Any],
    snowflake_compute_config: dict[str, Any],
) -> CompiledArtifactsDict:
    """CompiledArtifacts fixture with Snowflake target."""
    return {
        "version": "1.0.0",
        "metadata": base_metadata,
        "compute": snowflake_compute_config,
        "transforms": [{"type": "dbt", "project_dir": ".", "profiles_dir": PROFILES_DIR}],
        "consumption": {"enabled": False},
        "governance": {"enabled": False},
        "observability": {"traces": {"enabled": False}, "lineage": {"enabled": False}},
        "catalog": None,
        "dbt_manifest_path": None,
        "dbt_project_path": ".",
        "dbt_profiles_path": PROFILES_DIR,
        "lineage_namespace": None,
        "environment_context": None,
        "column_classifications": None,
    }


def make_compiled_artifacts(
    compute_config: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    dbt_profiles_path: str = PROFILES_DIR,
) -> CompiledArtifactsDict:
    """Factory function to create CompiledArtifacts dicts for testing.

    Args:
        compute_config: Compute target configuration dict.
        metadata: Optional metadata dict. If None, uses default values.
        dbt_profiles_path: Path for dbt profiles output.

    Returns:
        CompiledArtifacts-compatible dictionary.
    """
    if metadata is None:
        metadata = {
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "floe_core_version": "0.1.0",
            "source_hash": "test_hash",
        }

    return {
        "version": "1.0.0",
        "metadata": metadata,
        "compute": compute_config,
        "transforms": [{"type": "dbt", "project_dir": ".", "profiles_dir": dbt_profiles_path}],
        "consumption": {"enabled": False},
        "governance": {"enabled": False},
        "observability": {"traces": {"enabled": False}, "lineage": {"enabled": False}},
        "catalog": None,
        "dbt_manifest_path": None,
        "dbt_project_path": ".",
        "dbt_profiles_path": dbt_profiles_path,
        "lineage_namespace": None,
        "environment_context": None,
        "column_classifications": None,
    }
