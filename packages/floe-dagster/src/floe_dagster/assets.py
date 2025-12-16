"""Dagster asset factory for floe-runtime.

T044: [US1] Implement FloeAssetFactory.create_dbt_assets using @dbt_assets decorator
T046: [US1] Implement FloeAssetFactory.create_definitions
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dagster import AssetsDefinition, Definitions
from dagster_dbt import DbtCliResource, DbtManifest, dbt_assets

from floe_dagster.resources import create_dbt_cli_resource
from floe_dagster.translator import FloeTranslator


class FloeAssetFactory:
    """Factory for creating Dagster assets from dbt projects.

    Creates Dagster Software-Defined Assets from dbt manifest.json,
    using FloeTranslator to include floe-specific metadata.

    Features:
        - Parses dbt manifest.json for model discovery
        - Uses FloeTranslator for metadata extraction
        - Configures DbtCliResource from CompiledArtifacts
        - Creates Definitions for Dagster deployment

    Example:
        >>> assets = FloeAssetFactory.create_dbt_assets(artifacts)
        >>> definitions = FloeAssetFactory.create_definitions(artifacts)
    """

    @classmethod
    def create_dbt_assets(
        cls,
        artifacts: dict[str, Any],
    ) -> AssetsDefinition:
        """Create dbt assets from CompiledArtifacts.

        Reads dbt manifest.json and creates Dagster assets using
        the @dbt_assets decorator with FloeTranslator.

        Args:
            artifacts: CompiledArtifacts dictionary containing dbt configuration.

        Returns:
            AssetsDefinition containing all dbt model assets.

        Raises:
            FileNotFoundError: If manifest.json doesn't exist.
            ValueError: If dbt_manifest_path is not specified.
        """
        manifest_path = artifacts.get("dbt_manifest_path")
        if not manifest_path:
            raise ValueError(
                "dbt_manifest_path not specified in CompiledArtifacts. "
                "Run 'dbt compile' to generate manifest.json."
            )

        manifest_file = Path(manifest_path)
        if not manifest_file.exists():
            raise FileNotFoundError(
                f"dbt manifest.json not found at {manifest_path}. "
                f"Run 'dbt compile' to generate it."
            )

        # Load manifest for @dbt_assets decorator
        dbt_manifest = DbtManifest.read(path=manifest_file)
        translator = FloeTranslator()

        @dbt_assets(manifest=dbt_manifest, dagster_dbt_translator=translator)
        def floe_dbt_assets(context, dbt: DbtCliResource):
            """Execute dbt models as Dagster assets."""
            yield from dbt.cli(["run"], context=context).stream()

        return floe_dbt_assets

    @classmethod
    def create_definitions(
        cls,
        artifacts: dict[str, Any],
    ) -> Definitions:
        """Create complete Dagster Definitions from CompiledArtifacts.

        Creates a complete Dagster Definitions object including:
        - dbt assets from manifest
        - DbtCliResource configured with profiles

        Args:
            artifacts: CompiledArtifacts dictionary.

        Returns:
            Dagster Definitions object ready for deployment.
        """
        # Create dbt assets
        dbt_assets = cls.create_dbt_assets(artifacts)

        # Create dbt resource
        dbt_resource = create_dbt_cli_resource(artifacts)

        return Definitions(
            assets=[dbt_assets],
            resources={"dbt": dbt_resource},
        )

    @classmethod
    def _load_manifest(cls, manifest_path: Path) -> dict[str, Any]:
        """Load dbt manifest.json file.

        Args:
            manifest_path: Path to manifest.json.

        Returns:
            Parsed manifest dictionary.
        """
        with open(manifest_path) as f:
            return json.load(f)

    @classmethod
    def _filter_models(cls, manifest: dict[str, Any]) -> dict[str, Any]:
        """Filter model nodes from manifest.

        Args:
            manifest: Full dbt manifest dictionary.

        Returns:
            Dictionary containing only model nodes.
        """
        return {
            node_id: node
            for node_id, node in manifest.get("nodes", {}).items()
            if node_id.startswith("model.")
        }

    @classmethod
    def _get_dependencies(
        cls, manifest: dict[str, Any], model_id: str
    ) -> list[str]:
        """Get dependencies for a model.

        Args:
            manifest: Full dbt manifest dictionary.
            model_id: Model unique_id to get dependencies for.

        Returns:
            List of upstream node unique_ids.
        """
        node = manifest.get("nodes", {}).get(model_id, {})
        return node.get("depends_on", {}).get("nodes", [])

    @classmethod
    def _get_dbt_cli_config(cls, artifacts: dict[str, Any]) -> dict[str, str]:
        """Get DbtCliResource configuration.

        Args:
            artifacts: CompiledArtifacts dictionary.

        Returns:
            Configuration dictionary.
        """
        return {
            "project_dir": artifacts.get("dbt_project_path", "."),
            "profiles_dir": artifacts.get("dbt_profiles_path", ".floe/profiles"),
        }
