"""Dagster resource configuration for floe-runtime.

T045: [US1] Implement DbtCliResource configuration
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dagster_dbt import DbtCliResource


def create_dbt_cli_resource(artifacts: dict[str, Any]) -> DbtCliResource:
    """Create DbtCliResource from CompiledArtifacts.

    Configures the DbtCliResource with paths from CompiledArtifacts,
    including project directory and profiles directory.

    Args:
        artifacts: CompiledArtifacts dictionary containing dbt configuration.

    Returns:
        Configured DbtCliResource.

    Example:
        >>> resource = create_dbt_cli_resource(artifacts)
        >>> definitions = Definitions(resources={"dbt": resource})
    """
    project_dir = artifacts.get("dbt_project_path", ".")
    profiles_dir = artifacts.get("dbt_profiles_path", ".floe/profiles")

    # Resolve to absolute paths
    project_path = Path(project_dir).resolve()
    profiles_path = Path(profiles_dir).resolve()

    return DbtCliResource(
        project_dir=project_path,
        profiles_dir=profiles_path,
    )


def get_dbt_cli_config(artifacts: dict[str, Any]) -> dict[str, str]:
    """Get DbtCliResource configuration as dictionary.

    Useful for testing and inspection of configuration.

    Args:
        artifacts: CompiledArtifacts dictionary.

    Returns:
        Configuration dictionary with project_dir and profiles_dir.
    """
    return {
        "project_dir": artifacts.get("dbt_project_path", "."),
        "profiles_dir": artifacts.get("dbt_profiles_path", ".floe/profiles"),
    }
