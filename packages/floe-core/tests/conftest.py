"""Shared pytest fixtures for floe-core tests.

This module provides common fixtures used across unit, integration,
and contract tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def sample_floe_yaml() -> dict[str, Any]:
    """Return a minimal valid floe.yaml configuration.

    Returns:
        Dictionary representing a valid floe.yaml structure.
    """
    return {
        "name": "test-project",
        "version": "1.0.0",
        "compute": {
            "target": "duckdb",
        },
        "transforms": [
            {
                "type": "dbt",
                "project_dir": "./dbt",
            }
        ],
    }


@pytest.fixture
def sample_floe_yaml_full() -> dict[str, Any]:
    """Return a comprehensive floe.yaml configuration with all optional fields.

    Returns:
        Dictionary representing a full floe.yaml with all sections populated.
    """
    return {
        "name": "full-test-project",
        "version": "2.0.0",
        "compute": {
            "target": "snowflake",
            "connection_secret_ref": "my-snowflake-secret",
            "properties": {
                "account": "xy12345.us-east-1",
                "warehouse": "COMPUTE_WH",
            },
        },
        "transforms": [
            {
                "type": "dbt",
                "project_dir": "./dbt",
                "profiles_dir": ".floe/profiles",
                "target": "prod",
            }
        ],
        "consumption": {
            "enabled": True,
            "database_type": "snowflake",
            "port": 4000,
            "pre_aggregations": {
                "enabled": True,
            },
            "security": {
                "api_scopes_enabled": True,
            },
        },
        "governance": {
            "classification_source": "dbt_meta",
        },
        "observability": {
            "traces_enabled": True,
            "metrics_enabled": True,
        },
        "catalog": {
            "type": "polaris",
            "uri": "https://polaris.example.com/api/catalog",
            "warehouse": "my_warehouse",
        },
    }


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory.

    Returns:
        Path to the fixtures directory.
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_floe_project(tmp_path: Path, sample_floe_yaml: dict[str, Any]) -> Path:
    """Create a temporary floe project with floe.yaml.

    Args:
        tmp_path: pytest's temporary path fixture.
        sample_floe_yaml: Sample floe.yaml content.

    Returns:
        Path to the temporary project directory.
    """
    import yaml

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    floe_yaml = project_dir / "floe.yaml"
    floe_yaml.write_text(yaml.dump(sample_floe_yaml))

    return project_dir
