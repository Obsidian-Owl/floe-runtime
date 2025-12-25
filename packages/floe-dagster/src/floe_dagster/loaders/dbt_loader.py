"""dbt loader for converting DbtConfig to Dagster @dbt_assets.

T015: [010-orchestration-auto-discovery] Create dbt loader
Covers: 010-FR-008 through 010-FR-010

This module converts DbtConfig from floe.yaml into Dagster @dbt_assets definitions,
enabling per-model observability without requiring explicit wrapper code.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from dagster import AssetsDefinition

if TYPE_CHECKING:
    from floe_core.schemas.orchestration_config import DbtConfig


def load_dbt_assets(dbt_config: DbtConfig) -> AssetsDefinition | None:
    """Load dbt assets from DbtConfig.

    Converts DbtConfig from floe.yaml into Dagster @dbt_assets definition using
    the existing create_dbt_assets function from assets.py. Supports both per-model
    and job-level observability.

    Args:
        dbt_config: DbtConfig from OrchestrationConfig.

    Returns:
        AssetsDefinition containing dbt model assets, or None if config is None.

    Raises:
        FileNotFoundError: If manifest.json doesn't exist at manifest_path.
        ValueError: If manifest_path is invalid or cannot be resolved.

    Example:
        >>> from floe_core.schemas.orchestration_config import DbtConfig
        >>> config = DbtConfig(manifest_path="target/manifest.json")
        >>> assets = load_dbt_assets(config)
    """
    if dbt_config is None:
        return None

    manifest_path = Path(dbt_config.manifest_path)
    if not manifest_path.exists():
        msg = (
            f"dbt manifest.json not found at {manifest_path}. "
            "Run 'dbt compile' to generate manifest.json."
        )
        raise FileNotFoundError(msg)

    artifacts = _build_artifacts_from_config(dbt_config)

    from floe_dagster.assets import FloeAssetFactory

    return FloeAssetFactory.create_dbt_assets(artifacts)


def _build_artifacts_from_config(dbt_config: DbtConfig) -> dict:
    """Build CompiledArtifacts dictionary from DbtConfig.

    Args:
        dbt_config: DbtConfig from OrchestrationConfig.

    Returns:
        Dictionary compatible with FloeAssetFactory.create_dbt_assets.
    """
    artifacts = {
        "dbt_manifest_path": str(dbt_config.manifest_path),
    }

    if dbt_config.project_dir:
        artifacts["dbt_project_path"] = dbt_config.project_dir

    if dbt_config.profiles_dir:
        artifacts["dbt_profiles_dir"] = dbt_config.profiles_dir

    if dbt_config.target:
        artifacts["compute"] = {"target": dbt_config.target}

    return artifacts
