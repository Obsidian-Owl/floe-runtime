"""Shared pytest fixtures for floe-cube tests.

This module provides common fixtures used across unit, integration,
and contract tests for the Cube semantic layer integration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def sample_cube_config() -> dict[str, Any]:
    """Return a minimal valid Cube configuration.

    Returns:
        Dictionary representing a valid CubeConfig structure.
    """
    return {
        "database_type": "postgres",
        "api_port": 4000,
        "sql_port": 15432,
        "dev_mode": True,
    }


@pytest.fixture
def sample_cube_config_full() -> dict[str, Any]:
    """Return a comprehensive Cube configuration with all optional fields.

    Returns:
        Dictionary representing a full CubeConfig with all sections populated.
    """
    return {
        "database_type": "snowflake",
        "api_port": 4000,
        "sql_port": 15432,
        "api_secret_ref": "CUBEJS_API_SECRET",
        "dev_mode": False,
        "jwt_audience": "cube-api",
        "jwt_issuer": "https://auth.example.com",
        "traces_enabled": True,
        "otel_endpoint": "http://jaeger:4317",
        "lineage_enabled": True,
        "lineage_endpoint": "http://marquez:5000",
    }


@pytest.fixture
def sample_dbt_manifest() -> dict[str, Any]:
    """Return a minimal dbt manifest.json structure.

    Returns:
        Dictionary representing a valid dbt manifest.json.
    """
    return {
        "metadata": {
            "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v12.json",
            "dbt_version": "1.8.0",
            "project_name": "test_project",
        },
        "nodes": {
            "model.test_project.customers": {
                "name": "customers",
                "resource_type": "model",
                "schema": "public",
                "database": "test_db",
                "columns": {
                    "id": {
                        "name": "id",
                        "data_type": "integer",
                        "description": "Customer ID",
                    },
                    "email": {
                        "name": "email",
                        "data_type": "text",
                        "description": "Customer email",
                    },
                    "created_at": {
                        "name": "created_at",
                        "data_type": "timestamp",
                        "description": "Account creation timestamp",
                    },
                },
                "meta": {
                    "cube": {
                        "measures": [
                            {"name": "count", "type": "count"},
                        ],
                    },
                },
            },
            "model.test_project.orders": {
                "name": "orders",
                "resource_type": "model",
                "schema": "public",
                "database": "test_db",
                "columns": {
                    "id": {
                        "name": "id",
                        "data_type": "integer",
                        "description": "Order ID",
                    },
                    "customer_id": {
                        "name": "customer_id",
                        "data_type": "integer",
                        "description": "Customer foreign key",
                    },
                    "amount": {
                        "name": "amount",
                        "data_type": "numeric",
                        "description": "Order amount",
                    },
                    "status": {
                        "name": "status",
                        "data_type": "text",
                        "description": "Order status",
                    },
                },
                "meta": {
                    "cube": {
                        "measures": [
                            {"name": "count", "type": "count"},
                            {"name": "total_amount", "type": "sum", "sql": "amount"},
                        ],
                        "joins": [
                            {
                                "name": "customers",
                                "relationship": "many_to_one",
                                "sql": "${CUBE}.customer_id = ${customers}.id",
                            },
                        ],
                    },
                },
            },
        },
    }


@pytest.fixture
def sample_security_context() -> dict[str, Any]:
    """Return a sample SecurityContext for row-level security testing.

    Returns:
        Dictionary representing a valid SecurityContext.
    """
    return {
        "user_id": "user_123",
        "roles": ["analyst", "viewer"],
        "filter_claims": {
            "organization_id": "org_abc",
            "department": "engineering",
        },
        "exp": 1735689600,  # 2025-01-01 00:00:00 UTC
    }


@pytest.fixture
def sample_jwt_payload() -> dict[str, Any]:
    """Return a sample JWT payload for security testing.

    Returns:
        Dictionary representing a valid JWT payload.
    """
    return {
        "sub": "user_123",
        "aud": "cube-api",
        "iss": "https://auth.example.com",
        "exp": 1735689600,
        "iat": 1735603200,
        "organization_id": "org_abc",
        "roles": ["analyst", "viewer"],
    }


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory.

    Returns:
        Path to the fixtures directory.
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_cube_project(tmp_path: Path) -> Path:
    """Create a temporary directory structure for Cube output.

    Args:
        tmp_path: pytest's temporary path fixture.

    Returns:
        Path to the temporary Cube project directory.
    """
    cube_dir = tmp_path / ".floe" / "cube"
    cube_dir.mkdir(parents=True)

    schema_dir = cube_dir / "schema"
    schema_dir.mkdir()

    return cube_dir


@pytest.fixture
def tmp_dbt_project(
    tmp_path: Path, sample_dbt_manifest: dict[str, Any]
) -> Path:
    """Create a temporary dbt project with manifest.json.

    Args:
        tmp_path: pytest's temporary path fixture.
        sample_dbt_manifest: Sample manifest.json content.

    Returns:
        Path to the temporary dbt project directory.
    """
    import json

    project_dir = tmp_path / "dbt_project"
    project_dir.mkdir()

    target_dir = project_dir / "target"
    target_dir.mkdir()

    manifest_path = target_dir / "manifest.json"
    manifest_path.write_text(json.dumps(sample_dbt_manifest, indent=2))

    return project_dir
