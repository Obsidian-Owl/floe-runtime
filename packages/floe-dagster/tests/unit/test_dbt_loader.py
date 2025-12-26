"""Unit tests for dbt loader.

T017: [010-orchestration-auto-discovery] dbt loader tests with manifest validation
Covers: 010-FR-008 through 010-FR-010

Tests the load_dbt_assets function that converts DbtConfig to Dagster @dbt_assets.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from floe_core.schemas.orchestration_config import DbtConfig, ObservabilityLevel


class TestLoadDbtAssets:
    """Tests for load_dbt_assets function."""

    @pytest.fixture
    def sample_manifest_path(self, tmp_path: Path) -> Path:
        """Create sample manifest.json file."""
        import json

        manifest_path = tmp_path / "target" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)

        minimal_manifest = {
            "metadata": {"dbt_version": "1.5.0"},
            "nodes": {},
            "sources": {},
        }

        manifest_path.write_text(json.dumps(minimal_manifest))
        return manifest_path

    def test_load_dbt_assets_with_none_config(self) -> None:
        """load_dbt_assets should return None for None config."""
        from floe_dagster.loaders.dbt_loader import load_dbt_assets

        result = load_dbt_assets(None)  # type: ignore[arg-type]

        assert result is None

    def test_load_dbt_assets_with_valid_config(self, sample_manifest_path: Path) -> None:
        """load_dbt_assets should return AssetsDefinition for valid config."""
        from floe_dagster.loaders.dbt_loader import load_dbt_assets

        config = DbtConfig(manifest_path=str(sample_manifest_path))

        with patch(
            "floe_dagster.assets.FloeAssetFactory.create_dbt_assets_with_per_model_observability"
        ) as mock_create:
            mock_create.return_value = MagicMock()
            result = load_dbt_assets(config)

        assert result is not None
        assert mock_create.called

    def test_load_dbt_assets_calls_per_model_observability_by_default(
        self, sample_manifest_path: Path
    ) -> None:
        """load_dbt_assets should use per-model observability by default."""
        from floe_dagster.loaders.dbt_loader import load_dbt_assets

        config = DbtConfig(manifest_path=str(sample_manifest_path))

        with patch(
            "floe_dagster.assets.FloeAssetFactory.create_dbt_assets_with_per_model_observability"
        ) as mock_per_model:
            mock_per_model.return_value = MagicMock()
            load_dbt_assets(config)

        assert mock_per_model.called

    def test_load_dbt_assets_calls_job_level_for_job_level_observability(
        self, sample_manifest_path: Path
    ) -> None:
        """load_dbt_assets should use job-level observability when configured."""
        from floe_dagster.loaders.dbt_loader import load_dbt_assets

        config = DbtConfig(
            manifest_path=str(sample_manifest_path),
            observability_level=ObservabilityLevel.JOB_LEVEL,
        )

        with patch("floe_dagster.assets.FloeAssetFactory.create_dbt_assets") as mock_job_level:
            mock_job_level.return_value = MagicMock()
            load_dbt_assets(config)

        assert mock_job_level.called

    def test_load_dbt_assets_raises_on_missing_manifest(self) -> None:
        """load_dbt_assets should raise FileNotFoundError if manifest doesn't exist."""
        from floe_dagster.loaders.dbt_loader import load_dbt_assets

        config = DbtConfig(manifest_path="/nonexistent/manifest.json")

        with pytest.raises(FileNotFoundError) as exc_info:
            load_dbt_assets(config)

        assert "manifest.json not found" in str(exc_info.value)
        assert "dbt compile" in str(exc_info.value)

    def test_load_dbt_assets_passes_all_config_fields(self, sample_manifest_path: Path) -> None:
        """load_dbt_assets should pass all DbtConfig fields to artifacts."""
        from floe_dagster.loaders.dbt_loader import load_dbt_assets

        config = DbtConfig(
            manifest_path=str(sample_manifest_path),
            project_dir="demo/dbt",
            profiles_dir=".floe/profiles",
            target="dev",
        )

        with patch(
            "floe_dagster.assets.FloeAssetFactory.create_dbt_assets_with_per_model_observability"
        ) as mock_create:
            mock_create.return_value = MagicMock()
            load_dbt_assets(config)

            call_args = mock_create.call_args[0][0]
            assert call_args["dbt_manifest_path"] == str(sample_manifest_path)
            assert call_args["dbt_project_path"] == "demo/dbt"
            assert call_args["dbt_profiles_dir"] == ".floe/profiles"
            assert call_args["compute"]["target"] == "dev"


class TestBuildArtifactsFromConfig:
    """Tests for _build_artifacts_from_config helper."""

    def test_build_artifacts_minimal_config(self) -> None:
        """_build_artifacts_from_config should work with minimal config."""
        from floe_dagster.loaders.dbt_loader import _build_artifacts_from_config

        config = DbtConfig(manifest_path="target/manifest.json")

        artifacts = _build_artifacts_from_config(config)

        assert artifacts["dbt_manifest_path"] == "target/manifest.json"
        assert "dbt_project_path" not in artifacts
        assert "dbt_profiles_dir" not in artifacts
        assert "compute" not in artifacts

    def test_build_artifacts_full_config(self) -> None:
        """_build_artifacts_from_config should include all optional fields."""
        from floe_dagster.loaders.dbt_loader import _build_artifacts_from_config

        config = DbtConfig(
            manifest_path="target/manifest.json",
            project_dir="demo/dbt",
            profiles_dir=".floe/profiles",
            target="dev",
        )

        artifacts = _build_artifacts_from_config(config)

        assert artifacts["dbt_manifest_path"] == "target/manifest.json"
        assert artifacts["dbt_project_path"] == "demo/dbt"
        assert artifacts["dbt_profiles_dir"] == ".floe/profiles"
        assert artifacts["compute"]["target"] == "dev"
