"""dbt resource configuration for floe-runtime.

T045: [US1] Implement DbtCliResource configuration

Provides batteries-included dbt integration via dagster-dbt.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dagster_dbt import DbtCliResource


def create_dbt_cli_resource(
    artifacts: dict[str, Any] | None = None,
    project_dir: str | Path | None = None,
    profiles_dir: str | Path | None = None,
) -> DbtCliResource:
    """Create DbtCliResource from CompiledArtifacts or explicit paths.

    Priority order:
    1. Explicit project_dir/profiles_dir parameters
    2. Values from artifacts dict
    3. Environment variables (DBT_PROJECT_DIR, DBT_PROFILES_DIR)
    4. Defaults ("demo/dbt", "demo/dbt")

    Args:
        artifacts: Optional CompiledArtifacts dictionary containing dbt configuration.
        project_dir: Optional explicit project directory path.
        profiles_dir: Optional explicit profiles directory path.

    Returns:
        Configured DbtCliResource.

    Example:
        >>> # From artifacts
        >>> resource = create_dbt_cli_resource(artifacts)
        >>>
        >>> # Explicit paths
        >>> resource = create_dbt_cli_resource(
        ...     project_dir="demo/dbt",
        ...     profiles_dir="demo/dbt"
        ... )
        >>>
        >>> # Use in Definitions
        >>> definitions = Definitions(resources={"dbt": resource})
    """
    # Determine project directory
    if project_dir is not None:
        project_path = Path(project_dir)
    elif artifacts and "dbt_project_path" in artifacts:
        project_path = Path(artifacts["dbt_project_path"])
    elif "DBT_PROJECT_DIR" in os.environ:
        project_path = Path(os.environ["DBT_PROJECT_DIR"])
    elif "DBT_PROFILES_DIR" in os.environ:
        # Use profiles dir as project dir (demo has dbt_project.yml in same dir as profiles.yml)
        project_path = Path(os.environ["DBT_PROFILES_DIR"])
    else:
        # Default to demo for demo project
        project_path = Path("demo")

    # Determine profiles directory
    if profiles_dir is not None:
        profiles_path = Path(profiles_dir)
    elif artifacts and "dbt_profiles_path" in artifacts:
        profiles_path = Path(artifacts["dbt_profiles_path"])
    elif "DBT_PROFILES_DIR" in os.environ:
        profiles_path = Path(os.environ["DBT_PROFILES_DIR"])
    else:
        # Default to demo (profiles.yml is in project root for demo)
        profiles_path = Path("demo")

    # Resolve to absolute paths
    project_abs = project_path.resolve()
    profiles_abs = profiles_path.resolve()

    return DbtCliResource(
        project_dir=project_abs,
        profiles_dir=profiles_abs,
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
