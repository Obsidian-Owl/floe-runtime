"""Unit tests for dbt auto-loading integration in FloeDefinitions.

T019: [010-orchestration-auto-discovery] Test dbt auto-loading integration
Covers: 010-FR-008 through 010-FR-010

Tests that FloeDefinitions.from_compiled_artifacts() auto-loads dbt assets
when orchestration.dbt config is present in CompiledArtifacts.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from dagster import AssetsDefinition
import pytest

from floe_dagster.definitions import FloeDefinitions


class TestDbtAutoLoading:
    """Tests for dbt auto-loading in FloeDefinitions."""

    @pytest.fixture
    def sample_manifest_path(self, tmp_path: Path) -> Path:
        """Create sample manifest.json file."""
        manifest_path = tmp_path / "target" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)

        minimal_manifest = {
            "metadata": {"dbt_version": "1.5.0"},
            "nodes": {},
            "sources": {},
        }

        manifest_path.write_text(json.dumps(minimal_manifest))
        return manifest_path

    def test_auto_loads_dbt_assets_from_orchestration_config(
        self, sample_manifest_path: Path
    ) -> None:
        """Auto-load dbt assets when orchestration.dbt is present."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "orchestration": {
                "dbt": {
                    "manifest_path": str(sample_manifest_path),
                }
            },
        }

        with (
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
            patch("floe_dagster.loaders.dbt_loader.load_dbt_assets") as mock_load_dbt,
        ):
            mock_orch.return_value = MagicMock()
            mock_dbt_asset = MagicMock(spec=AssetsDefinition)
            mock_load_dbt.return_value = mock_dbt_asset

            FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            mock_load_dbt.assert_called_once()
            call_args = mock_load_dbt.call_args[0][0]
            assert call_args.manifest_path == str(sample_manifest_path)

    def test_does_not_load_dbt_when_no_orchestration_config(self) -> None:
        """Should not load dbt assets when orchestration.dbt is absent."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
        }

        with (
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
            patch("floe_dagster.loaders.dbt_loader.load_dbt_assets") as mock_load_dbt,
        ):
            mock_orch.return_value = MagicMock()

            FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            mock_load_dbt.assert_not_called()

    def test_passes_all_dbt_config_fields_to_loader(self, sample_manifest_path: Path) -> None:
        """All DbtConfig fields should be passed to load_dbt_assets."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "orchestration": {
                "dbt": {
                    "manifest_path": str(sample_manifest_path),
                    "project_dir": "demo/dbt",
                    "profiles_dir": ".floe/profiles",
                    "target": "dev",
                    "observability_level": "per_model",
                }
            },
        }

        with (
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
            patch("floe_dagster.loaders.dbt_loader.load_dbt_assets") as mock_load_dbt,
        ):
            mock_orch.return_value = MagicMock()
            mock_load_dbt.return_value = MagicMock(spec=AssetsDefinition)

            FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            call_args = mock_load_dbt.call_args[0][0]
            assert call_args.manifest_path == str(sample_manifest_path)
            assert call_args.project_dir == "demo/dbt"
            assert call_args.profiles_dir == ".floe/profiles"
            assert call_args.target == "dev"
            assert call_args.observability_level.value == "per_model"

    def test_graceful_degradation_on_dbt_loading_failure(self, sample_manifest_path: Path) -> None:
        """Should not break definitions if dbt auto-loading fails."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "orchestration": {
                "dbt": {
                    "manifest_path": str(sample_manifest_path),
                }
            },
        }

        with (
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
            patch("floe_dagster.loaders.dbt_loader.load_dbt_assets") as mock_load_dbt,
        ):
            mock_orch.return_value = MagicMock()
            mock_load_dbt.side_effect = ValueError("Invalid dbt config")

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            assert result is not None

    def test_respects_per_model_observability_level(self, sample_manifest_path: Path) -> None:
        """Should use per-model observability when configured."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "orchestration": {
                "dbt": {
                    "manifest_path": str(sample_manifest_path),
                    "observability_level": "per_model",
                }
            },
        }

        with (
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
            patch(
                "floe_dagster.assets.FloeAssetFactory.create_dbt_assets_with_per_model_observability"
            ) as mock_per_model,
        ):
            mock_orch.return_value = MagicMock()
            mock_per_model.return_value = MagicMock(spec=AssetsDefinition)

            FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            assert mock_per_model.called

    def test_respects_job_level_observability_level(self, sample_manifest_path: Path) -> None:
        """Should use job-level observability when configured."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "orchestration": {
                "dbt": {
                    "manifest_path": str(sample_manifest_path),
                    "observability_level": "job_level",
                }
            },
        }

        with (
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
            patch("floe_dagster.assets.FloeAssetFactory.create_dbt_assets") as mock_job_level,
        ):
            mock_orch.return_value = MagicMock()
            mock_job_level.return_value = MagicMock(spec=AssetsDefinition)

            FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            assert mock_job_level.called
