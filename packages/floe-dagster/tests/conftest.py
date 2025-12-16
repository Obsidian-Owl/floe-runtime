"""Shared test fixtures for floe-dagster tests.

T014: Create shared test fixtures for Dagster testing

This module provides pytest fixtures for testing Dagster assets,
translators, and observability components with mock data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


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
    """DuckDB compute configuration fixture for Dagster tests."""
    return {
        "target": "duckdb",
        "connection_secret_ref": None,
        "properties": {
            "path": ":memory:",
            "threads": 4,
        },
    }


@pytest.fixture
def minimal_compiled_artifacts(
    base_metadata: dict[str, Any],
    duckdb_compute_config: dict[str, Any],
) -> dict[str, Any]:
    """Minimal CompiledArtifacts fixture with DuckDB target."""
    return {
        "version": "1.0.0",
        "metadata": base_metadata,
        "compute": duckdb_compute_config,
        "transforms": [{"type": "dbt", "project_dir": ".", "profiles_dir": ".floe/profiles"}],
        "consumption": {"enabled": False},
        "governance": {"enabled": False},
        "observability": {"traces": {"enabled": False}, "lineage": {"enabled": False}},
        "catalog": None,
        "dbt_manifest_path": "target/manifest.json",
        "dbt_project_path": ".",
        "dbt_profiles_path": ".floe/profiles",
        "lineage_namespace": None,
        "environment_context": None,
        "column_classifications": None,
    }


@pytest.fixture
def observability_enabled_artifacts(
    base_metadata: dict[str, Any],
    duckdb_compute_config: dict[str, Any],
) -> dict[str, Any]:
    """CompiledArtifacts with observability enabled."""
    return {
        "version": "1.0.0",
        "metadata": base_metadata,
        "compute": duckdb_compute_config,
        "transforms": [{"type": "dbt", "project_dir": ".", "profiles_dir": ".floe/profiles"}],
        "consumption": {"enabled": False},
        "governance": {"enabled": False},
        "observability": {
            "traces": {
                "enabled": True,
                "otlp_endpoint": "http://localhost:4317",
            },
            "lineage": {
                "enabled": True,
                "openlineage_endpoint": "http://localhost:5000",
            },
        },
        "catalog": None,
        "dbt_manifest_path": "target/manifest.json",
        "dbt_project_path": ".",
        "dbt_profiles_path": ".floe/profiles",
        "lineage_namespace": "floe.test",
        "environment_context": None,
        "column_classifications": {
            "customers": {
                "email": {"type": "pii", "pii_type": "email", "sensitivity": "high"},
                "phone": {"type": "pii", "pii_type": "phone", "sensitivity": "high"},
            }
        },
    }


@pytest.fixture
def sample_dbt_manifest_node() -> dict[str, Any]:
    """Sample dbt manifest node for translator testing."""
    return {
        "unique_id": "model.my_project.customers",
        "name": "customers",
        "resource_type": "model",
        "package_name": "my_project",
        "path": "models/customers.sql",
        "original_file_path": "models/customers.sql",
        "alias": "customers",
        "schema": "analytics",
        "database": "warehouse",
        "description": "Customer dimension table",
        "meta": {
            "floe": {
                "owner": "data-team",
                "classification": "internal",
            }
        },
        "tags": ["pii", "customers"],
        "columns": {
            "customer_id": {
                "name": "customer_id",
                "description": "Primary key",
                "data_type": "varchar",
                "meta": {},
            },
            "email": {
                "name": "email",
                "description": "Customer email address",
                "data_type": "varchar",
                "meta": {
                    "floe": {
                        "classification": "pii",
                        "pii_type": "email",
                        "sensitivity": "high",
                    }
                },
            },
        },
        "depends_on": {
            "nodes": ["source.my_project.raw.raw_customers"],
        },
        "refs": [],
        "sources": [["raw", "raw_customers"]],
        "config": {
            "materialized": "table",
            "schema": "analytics",
        },
    }


@pytest.fixture
def sample_dbt_manifest(sample_dbt_manifest_node: dict[str, Any]) -> dict[str, Any]:
    """Sample dbt manifest.json structure."""
    return {
        "metadata": {
            "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v12.json",
            "dbt_version": "1.9.0",
            "project_name": "my_project",
            "project_id": str(uuid4()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "nodes": {
            "model.my_project.customers": sample_dbt_manifest_node,
        },
        "sources": {
            "source.my_project.raw.raw_customers": {
                "unique_id": "source.my_project.raw.raw_customers",
                "name": "raw_customers",
                "resource_type": "source",
                "source_name": "raw",
                "schema": "raw",
                "database": "warehouse",
                "identifier": "raw_customers",
                "config": {"enabled": True},
            },
        },
        "metrics": {},
        "exposures": {},
        "parent_map": {
            "model.my_project.customers": ["source.my_project.raw.raw_customers"],
        },
        "child_map": {
            "source.my_project.raw.raw_customers": ["model.my_project.customers"],
        },
    }


@pytest.fixture
def mock_dagster_context() -> MagicMock:
    """Mock Dagster AssetExecutionContext."""
    context = MagicMock()
    context.log = MagicMock()
    context.run_id = str(uuid4())
    context.partition_key = None
    return context


@pytest.fixture
def mock_openlineage_client() -> MagicMock:
    """Mock OpenLineage client for testing."""
    client = MagicMock()
    client.emit = MagicMock()
    return client


@pytest.fixture
def mock_tracer() -> MagicMock:
    """Mock OpenTelemetry tracer for testing."""
    tracer = MagicMock()
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=False)
    tracer.start_as_current_span = MagicMock(return_value=span)
    return tracer


def make_dbt_manifest_node(
    name: str,
    schema: str = "analytics",
    database: str = "warehouse",
    description: str = "",
    columns: dict[str, dict[str, Any]] | None = None,
    depends_on: list[str] | None = None,
    meta: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Factory function to create dbt manifest nodes for testing.

    Args:
        name: Model name.
        schema: Database schema.
        database: Database name.
        description: Model description.
        columns: Column definitions.
        depends_on: List of upstream node unique IDs.
        meta: Model metadata.
        tags: Model tags.

    Returns:
        dbt manifest node dictionary.
    """
    return {
        "unique_id": f"model.test_project.{name}",
        "name": name,
        "resource_type": "model",
        "package_name": "test_project",
        "path": f"models/{name}.sql",
        "original_file_path": f"models/{name}.sql",
        "alias": name,
        "schema": schema,
        "database": database,
        "description": description,
        "meta": meta or {},
        "tags": tags or [],
        "columns": columns or {},
        "depends_on": {"nodes": depends_on or []},
        "refs": [],
        "sources": [],
        "config": {"materialized": "table", "schema": schema},
    }
