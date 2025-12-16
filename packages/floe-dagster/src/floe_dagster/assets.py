"""Dagster asset factory for floe-runtime.

T044: [US1] Implement FloeAssetFactory.create_dbt_assets using @dbt_assets decorator
T046: [US1] Implement FloeAssetFactory.create_definitions
T066: [US3] Integrate OpenLineageEmitter into FloeAssetFactory asset execution
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from dagster import AssetsDefinition, Definitions
from dagster_dbt import DbtCliResource, dbt_assets

from floe_dagster.lineage import (
    LineageDatasetBuilder,
    OpenLineageConfig,
    OpenLineageEmitter,
)
from floe_dagster.resources import create_dbt_cli_resource
from floe_dagster.translator import FloeTranslator

logger = logging.getLogger(__name__)


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
        the @dbt_assets decorator with FloeTranslator. Integrates
        OpenLineage emission for data lineage tracking.

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

        # Create translator for metadata extraction
        translator = FloeTranslator()

        # Configure OpenLineage emitter (graceful degradation if not configured)
        lineage_config = OpenLineageConfig.from_artifacts(artifacts)
        lineage_emitter = OpenLineageEmitter(lineage_config)

        # Build namespace prefix from compute target
        compute = artifacts.get("compute", {})
        namespace_prefix = cls._build_namespace_prefix(compute)
        dataset_builder = LineageDatasetBuilder(
            namespace_prefix=namespace_prefix,
            include_classifications=True,
        )

        # Load manifest for lineage tracking
        manifest_dict = cls._load_manifest(manifest_file)

        @dbt_assets(manifest=manifest_file, dagster_dbt_translator=translator)
        def floe_dbt_assets(context, dbt: DbtCliResource):
            """Execute dbt models as Dagster assets with lineage tracking."""
            # Emit START event for the overall dbt run
            run_id = lineage_emitter.emit_start(
                job_name="dbt_run",
                inputs=[],
                outputs=[],
            )

            try:
                # Execute dbt and stream events
                for event in dbt.cli(["run"], context=context).stream():
                    yield event

                # Build output datasets from executed models
                outputs = []
                models = cls._filter_models(manifest_dict)
                for model_node in models.values():
                    dataset = dataset_builder.build_from_dbt_node(model_node)
                    outputs.append(dataset)

                # Emit COMPLETE event
                lineage_emitter.emit_complete(
                    run_id=run_id,
                    job_name="dbt_run",
                    inputs=[],
                    outputs=outputs,
                )

            except Exception as e:
                # Emit FAIL event on error
                lineage_emitter.emit_fail(
                    run_id=run_id,
                    job_name="dbt_run",
                    error_message=str(e),
                )
                raise

        return floe_dbt_assets

    @classmethod
    def _build_namespace_prefix(cls, compute: dict[str, Any]) -> str:
        """Build OpenLineage namespace prefix from compute config.

        Args:
            compute: Compute configuration from CompiledArtifacts.

        Returns:
            Namespace prefix string (e.g., "snowflake://account").
        """
        target = compute.get("target", "unknown")
        properties = compute.get("properties", {})

        # Build target-specific namespace
        if target == "snowflake":
            account = properties.get("account", "unknown")
            return f"snowflake://{account}"
        elif target == "bigquery":
            project = properties.get("project", "unknown")
            return f"bigquery://{project}"
        elif target == "redshift":
            host = properties.get("host", "unknown")
            return f"redshift://{host}"
        elif target == "databricks":
            host = properties.get("host", "unknown")
            return f"databricks://{host}"
        elif target == "postgres":
            host = properties.get("host", "localhost")
            return f"postgres://{host}"
        elif target == "duckdb":
            path = properties.get("path", ":memory:")
            return f"duckdb://{path}"
        elif target == "spark":
            return "spark://cluster"
        else:
            return f"{target}://default"

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
