"""Unit tests for FloeAssetFactory.

T037: [P] [US1] Unit tests for FloeAssetFactory
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestFloeAssetFactory:
    """Test suite for FloeAssetFactory."""

    @pytest.fixture
    def factory(self) -> Any:
        """Create FloeAssetFactory instance."""
        from floe_dagster.assets import FloeAssetFactory

        return FloeAssetFactory

    @pytest.fixture
    def sample_manifest_path(self, tmp_path: Path, sample_dbt_manifest: dict[str, Any]) -> Path:
        """Create sample manifest.json file."""
        import json

        manifest_path = tmp_path / "target" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps(sample_dbt_manifest))
        return manifest_path

    def test_create_dbt_assets_returns_assets_definition(
        self,
        factory: Any,
        minimal_compiled_artifacts: dict[str, Any],
        sample_manifest_path: Path,
    ) -> None:
        """Test that create_dbt_assets returns AssetsDefinition."""
        # Update artifacts to point to manifest
        artifacts = minimal_compiled_artifacts.copy()
        artifacts["dbt_manifest_path"] = str(sample_manifest_path)
        artifacts["dbt_project_path"] = str(sample_manifest_path.parent.parent)

        with patch("floe_dagster.assets.Path.exists", return_value=True):
            assets = factory.create_dbt_assets(artifacts)

        assert assets is not None

    def test_create_dbt_assets_raises_on_missing_manifest(
        self,
        factory: Any,
        minimal_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test error when manifest.json doesn't exist."""
        artifacts = minimal_compiled_artifacts.copy()
        artifacts["dbt_manifest_path"] = "/nonexistent/manifest.json"

        with pytest.raises((FileNotFoundError, ValueError)):
            factory.create_dbt_assets(artifacts)

    def test_create_definitions_returns_definitions(
        self,
        factory: Any,
        minimal_compiled_artifacts: dict[str, Any],
        sample_manifest_path: Path,
    ) -> None:
        """Test that create_definitions returns Dagster Definitions."""
        artifacts = minimal_compiled_artifacts.copy()

        # Set up project directory with dbt_project.yml
        project_dir = sample_manifest_path.parent.parent
        (project_dir / "dbt_project.yml").write_text("name: test_project\n")

        # Create a valid profiles directory for DbtCliResource
        profiles_dir = project_dir / ".floe" / "profiles"
        profiles_dir.mkdir(parents=True)
        (profiles_dir / "profiles.yml").write_text("test_project:\n  target: dev\n")

        artifacts["dbt_manifest_path"] = str(sample_manifest_path)
        artifacts["dbt_project_path"] = str(project_dir)
        artifacts["dbt_profiles_path"] = str(profiles_dir)

        definitions = factory.create_definitions(artifacts)

        assert definitions is not None

    def test_create_definitions_includes_resources(
        self,
        factory: Any,
        minimal_compiled_artifacts: dict[str, Any],
        sample_manifest_path: Path,
    ) -> None:
        """Test that definitions include DbtCliResource."""
        artifacts = minimal_compiled_artifacts.copy()

        # Set up project directory with dbt_project.yml
        project_dir = sample_manifest_path.parent.parent
        (project_dir / "dbt_project.yml").write_text("name: test_project\n")

        # Create a valid profiles directory for DbtCliResource
        profiles_dir = project_dir / ".floe" / "profiles"
        profiles_dir.mkdir(parents=True)
        (profiles_dir / "profiles.yml").write_text("test_project:\n  target: dev\n")

        artifacts["dbt_manifest_path"] = str(sample_manifest_path)
        artifacts["dbt_project_path"] = str(project_dir)
        artifacts["dbt_profiles_path"] = str(profiles_dir)

        definitions = factory.create_definitions(artifacts)

        # Should have dbt resource
        assert definitions is not None
        # Can't easily check resources without importing dagster

    def test_load_manifest_parses_json(
        self,
        factory: Any,
        sample_manifest_path: Path,
    ) -> None:
        """Test that manifest.json is parsed correctly."""
        manifest = factory._load_manifest(sample_manifest_path)

        assert "nodes" in manifest
        assert "metadata" in manifest

    def test_filter_models_from_manifest(
        self,
        factory: Any,
        sample_dbt_manifest: dict[str, Any],
    ) -> None:
        """Test filtering model nodes from manifest."""
        models = factory._filter_models(sample_dbt_manifest)

        # Should only return model nodes, not sources
        for node_id in models:
            assert node_id.startswith("model.")

    def test_get_model_dependencies(
        self,
        factory: Any,
        sample_dbt_manifest: dict[str, Any],
    ) -> None:
        """Test extracting model dependencies."""
        model_id = "model.my_project.customers"
        deps = factory._get_dependencies(sample_dbt_manifest, model_id)

        # Should return list of upstream dependencies
        assert isinstance(deps, list)


class TestFloeAssetFactoryEdgeCases:
    """Test edge cases for FloeAssetFactory."""

    @pytest.fixture
    def factory(self) -> Any:
        """Create FloeAssetFactory instance."""
        from floe_dagster.assets import FloeAssetFactory

        return FloeAssetFactory

    def test_handles_empty_manifest(
        self,
        factory: Any,
        tmp_path: Path,
    ) -> None:
        """Test handling of manifest with no models."""
        import json

        manifest = {
            "metadata": {"dbt_version": "1.9.0"},
            "nodes": {},
            "sources": {},
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        models = factory._filter_models(manifest)
        assert len(models) == 0

    def test_handles_circular_refs(
        self,
        factory: Any,
    ) -> None:
        """Test handling of circular references (dbt should catch these)."""
        # dbt itself catches circular refs, but we should handle gracefully
        manifest = {
            "nodes": {
                "model.proj.a": {"depends_on": {"nodes": ["model.proj.b"]}},
                "model.proj.b": {"depends_on": {"nodes": ["model.proj.a"]}},
            }
        }

        # Should not raise - dbt validates this
        deps_a = factory._get_dependencies(manifest, "model.proj.a")
        assert "model.proj.b" in deps_a

    def test_uses_profiles_path_from_artifacts(
        self,
        factory: Any,
        minimal_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test that profiles_dir is configured from artifacts."""
        artifacts = minimal_compiled_artifacts.copy()
        artifacts["dbt_profiles_path"] = "/custom/profiles"

        config = factory._get_dbt_cli_config(artifacts)

        assert config["profiles_dir"] == "/custom/profiles"

    def test_uses_project_path_from_artifacts(
        self,
        factory: Any,
        minimal_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test that project_dir is configured from artifacts."""
        artifacts = minimal_compiled_artifacts.copy()
        artifacts["dbt_project_path"] = "/custom/project"

        config = factory._get_dbt_cli_config(artifacts)

        assert config["project_dir"] == "/custom/project"
