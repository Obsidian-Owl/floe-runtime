"""Shared pytest fixtures for floe-core tests.

This module provides common fixtures used across unit, integration,
and contract tests.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
import structlog


@pytest.fixture(autouse=True)
def configure_structlog_for_tests() -> None:
    """Configure structlog to output to stdout for test capture.

    This fixture ensures structlog outputs to stdout so that capsys
    can capture the output in tests. Without this, structlog may use
    different processors depending on test execution order.
    """
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,  # Important for test isolation
    )


@pytest.fixture
def sample_floe_yaml() -> dict[str, Any]:
    """Return a minimal valid floe.yaml configuration (Two-Tier Architecture).

    In Two-Tier Architecture:
    - FloeSpec uses logical profile references (storage, catalog, compute)
    - PlatformSpec contains actual infrastructure configuration
    - Same floe.yaml works across dev/staging/prod

    Returns:
        Dictionary representing a valid floe.yaml structure.
    """
    return {
        "name": "test-project",
        "version": "1.0.0",
        # Two-Tier: Use profile references (strings), not inline config
        "storage": "default",
        "catalog": "default",
        "compute": "default",
        "transforms": [
            {
                "type": "dbt",
                "path": "./dbt",
            }
        ],
    }


@pytest.fixture
def sample_floe_yaml_full() -> dict[str, Any]:
    """Return a comprehensive floe.yaml configuration with all optional fields.

    In Two-Tier Architecture, floe.yaml uses profile references.
    Infrastructure details are in platform.yaml (see sample_platform_yaml).

    Returns:
        Dictionary representing a full floe.yaml with all sections populated.
    """
    return {
        "name": "full-test-project",
        "version": "2.0.0",
        # Two-Tier: Use profile references (strings)
        "storage": "default",
        "catalog": "analytics",  # Non-default profile
        "compute": "snowflake",  # Non-default profile
        "transforms": [
            {
                "type": "dbt",
                "path": "./dbt",
                "target": "prod",
            }
        ],
        "consumption": {
            "enabled": True,
            "database_type": "snowflake",
            "port": 4000,
            "pre_aggregations": {
                "refresh_schedule": "0 */6 * * *",
            },
            "security": {
                "row_level": True,
            },
        },
        "governance": {
            "classification_source": "dbt_meta",
        },
        "observability": {
            "traces": True,
            "metrics": True,
        },
    }


@pytest.fixture
def sample_platform_yaml() -> dict[str, Any]:
    """Return a valid platform.yaml configuration for Two-Tier Architecture.

    Platform engineers configure infrastructure in platform.yaml.
    Data engineers reference profiles by name in floe.yaml.

    Returns:
        Dictionary representing a valid platform.yaml structure.
    """
    return {
        "version": "1.0.0",
        "storage": {
            "default": {
                "type": "s3",
                "bucket": "test-bucket",
                "endpoint": "http://minio:9000",
                "region": "us-east-1",
                "path_style_access": True,
            },
        },
        "catalogs": {
            "default": {
                "type": "polaris",
                "uri": "http://polaris:8181/api/catalog",
                "warehouse": "test-warehouse",
                "namespace": "default",
            },
            "analytics": {
                "type": "polaris",
                "uri": "http://polaris:8181/api/catalog",
                "warehouse": "analytics-warehouse",
                "namespace": "analytics",
            },
        },
        "compute": {
            "default": {
                "type": "duckdb",
                "properties": {
                    "path": ":memory:",
                    "threads": 4,
                },
            },
            "snowflake": {
                "type": "snowflake",
                "properties": {
                    "account": "xy12345.us-east-1",
                    "warehouse": "COMPUTE_WH",
                },
                "credentials": {
                    "mode": "static",
                    "secret_ref": "snowflake-credentials",
                },
            },
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
def tmp_floe_project(
    tmp_path: Path,
    sample_floe_yaml: dict[str, Any],
    sample_platform_yaml: dict[str, Any],
) -> Path:
    """Create a temporary floe project with floe.yaml and platform.yaml.

    Two-Tier Architecture requires both:
    - floe.yaml: Data engineer's view (profile references)
    - platform.yaml: Platform engineer's view (infrastructure config)

    Args:
        tmp_path: pytest's temporary path fixture.
        sample_floe_yaml: Sample floe.yaml content.
        sample_platform_yaml: Sample platform.yaml content.

    Returns:
        Path to the temporary project directory.
    """
    import yaml

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Create floe.yaml
    floe_yaml = project_dir / "floe.yaml"
    floe_yaml.write_text(yaml.dump(sample_floe_yaml))

    # Create platform.yaml (Two-Tier Architecture)
    platform_yaml = project_dir / "platform.yaml"
    platform_yaml.write_text(yaml.dump(sample_platform_yaml))

    return project_dir
