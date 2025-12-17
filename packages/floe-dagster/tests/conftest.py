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

# Constants for test fixtures to avoid duplication
PROFILES_DIR = ".floe/profiles"
MODEL_UNIQUE_ID = "model.my_project.customers"
SOURCE_UNIQUE_ID = "source.my_project.raw.raw_customers"


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
        "transforms": [{"type": "dbt", "project_dir": ".", "profiles_dir": PROFILES_DIR}],
        "consumption": {"enabled": False},
        "governance": {"enabled": False},
        "observability": {"traces": {"enabled": False}, "lineage": {"enabled": False}},
        "catalog": None,
        "dbt_manifest_path": "target/manifest.json",
        "dbt_project_path": ".",
        "dbt_profiles_path": PROFILES_DIR,
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
        "transforms": [{"type": "dbt", "project_dir": ".", "profiles_dir": PROFILES_DIR}],
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
        "dbt_profiles_path": PROFILES_DIR,
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
        "unique_id": MODEL_UNIQUE_ID,
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
            "nodes": [SOURCE_UNIQUE_ID],
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
            MODEL_UNIQUE_ID: sample_dbt_manifest_node,
        },
        "sources": {
            SOURCE_UNIQUE_ID: {
                "unique_id": SOURCE_UNIQUE_ID,
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
            MODEL_UNIQUE_ID: [SOURCE_UNIQUE_ID],
        },
        "child_map": {
            SOURCE_UNIQUE_ID: [MODEL_UNIQUE_ID],
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


@pytest.fixture
def in_memory_span_exporter() -> Any:
    """In-memory span exporter for verifying OTel spans in tests.

    This provides a real OTel tracing setup that captures spans in memory,
    allowing tests to verify span names, attributes, and relationships
    without requiring an external collector.

    Usage:
        def test_tracing(in_memory_span_exporter):
            exporter, provider = in_memory_span_exporter
            tracer = provider.get_tracer("test")

            with tracer.start_as_current_span("operation") as span:
                span.set_attribute("key", "value")

            spans = exporter.get_finished_spans()
            assert len(spans) == 1
            assert spans[0].name == "operation"

            exporter.clear()  # Clean up for next test
    """
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    yield exporter, provider

    # Cleanup
    exporter.shutdown()
    provider.shutdown()


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
