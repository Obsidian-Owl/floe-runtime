"""Unit tests for Dagster definitions entry point.

T047: [US1] Create Dagster definitions entry point
T098: [US6] Create FloeDefinitions.from_compiled_artifacts() factory

Tests for FloeDefinitions, load_definitions_from_artifacts, and load_definitions_from_dict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from dagster import Definitions, asset
import pytest

from floe_dagster.decorators import ORCHESTRATOR_RESOURCE_KEY
from floe_dagster.definitions import FloeDefinitions


class TestLoadDefinitionsFromArtifacts:
    """Tests for load_definitions_from_artifacts function."""

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """Test that missing artifacts file raises FileNotFoundError."""
        from floe_dagster.definitions import load_definitions_from_artifacts

        with pytest.raises(FileNotFoundError) as exc_info:
            load_definitions_from_artifacts(tmp_path / "nonexistent.json")

        assert "CompiledArtifacts not found" in str(exc_info.value)
        assert "floe compile" in str(exc_info.value)

    def test_loads_from_valid_file(self, tmp_path: Path) -> None:
        """Test loading from valid artifacts file."""
        from floe_dagster.definitions import load_definitions_from_artifacts

        # Create minimal artifacts file
        artifacts = {
            "version": "1.0.0",
            "dbt_manifest_path": str(tmp_path / "manifest.json"),
            "dbt_project_path": str(tmp_path),
            "compute": {"target": "duckdb", "properties": {}},
        }
        artifacts_path = tmp_path / "compiled_artifacts.json"
        artifacts_path.write_text(json.dumps(artifacts))

        # Create mock manifest
        manifest = {"nodes": {}, "metadata": {}}
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        # Should not raise - loads successfully
        with patch("floe_dagster.definitions.FloeAssetFactory.create_definitions") as mock_create:
            mock_create.return_value = MagicMock()
            result = load_definitions_from_artifacts(str(artifacts_path))
            assert result is not None
            mock_create.assert_called_once_with(artifacts)


class TestLoadDefinitionsFromDict:
    """Tests for load_definitions_from_dict function."""

    def test_creates_definitions_from_dict(self) -> None:
        """Test creating definitions from dictionary."""
        from floe_dagster.definitions import load_definitions_from_dict

        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "dbt_manifest_path": "/path/to/manifest.json",
            "dbt_project_path": "/path/to/project",
            "compute": {"target": "duckdb", "properties": {}},
        }

        with patch("floe_dagster.definitions.FloeAssetFactory.create_definitions") as mock_create:
            mock_create.return_value = MagicMock()
            result = load_definitions_from_dict(artifacts)
            assert result is not None
            mock_create.assert_called_once_with(artifacts)


class TestFloeDefinitionsFromCompiledArtifacts:
    """Tests for FloeDefinitions.from_compiled_artifacts() factory."""

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """Test that missing artifacts file raises FileNotFoundError.

        When platform.yaml is not available and artifacts file doesn't exist,
        should raise FileNotFoundError with helpful message.
        """
        # Mock _load_platform_config to return None (no platform.yaml found)
        with (
            patch.object(FloeDefinitions, "_load_platform_config", return_value=None),
            pytest.raises(FileNotFoundError) as exc_info,
        ):
            FloeDefinitions.from_compiled_artifacts(artifacts_path=tmp_path / "nonexistent.json")

        assert "CompiledArtifacts not found" in str(exc_info.value)
        assert "floe compile" in str(exc_info.value)

    def test_loads_from_artifacts_dict(self) -> None:
        """Test loading from artifacts dictionary (no file needed)."""
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            assert isinstance(result, Definitions)
            mock_orch.assert_called_once()

    def test_loads_from_file(self, tmp_path: Path) -> None:
        """Test loading from artifacts file."""
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
        }
        artifacts_path = tmp_path / "compiled_artifacts.json"
        artifacts_path.write_text(json.dumps(artifacts))

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_path=str(artifacts_path),
            )

            assert isinstance(result, Definitions)
            mock_orch.assert_called_once()

    def test_artifacts_dict_takes_precedence_over_file(self, tmp_path: Path) -> None:
        """Test that artifacts_dict takes precedence over artifacts_path."""
        # Create file with different content
        file_artifacts = {"version": "file", "observability": {}}
        artifacts_path = tmp_path / "compiled_artifacts.json"
        artifacts_path.write_text(json.dumps(file_artifacts))

        # Pass dict with different content
        dict_artifacts = {"version": "dict", "observability": {}}

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            FloeDefinitions.from_compiled_artifacts(
                artifacts_path=str(artifacts_path),
                artifacts_dict=dict_artifacts,
            )

            # Should use dict version, not file
            call_args = mock_orch.call_args[0][0]
            assert call_args["version"] == "dict"

    def test_initializes_orchestrator_with_namespace(self) -> None:
        """Test that orchestrator is initialized with custom namespace."""
        artifacts = {"version": "2.0.0", "observability": {}}

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
                namespace="custom_namespace",
            )

            mock_orch.assert_called_once_with(artifacts, namespace="custom_namespace")

    def test_orchestrator_available_as_resource(self) -> None:
        """Test that orchestrator is injected as resource."""
        artifacts = {"version": "2.0.0", "observability": {}}
        mock_orchestrator = MagicMock()

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = mock_orchestrator

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            # Check orchestrator is in resources
            assert result.resources is not None
            assert ORCHESTRATOR_RESOURCE_KEY in result.resources


class TestFloeDefinitionsWithCatalog:
    """Tests for FloeDefinitions catalog resource creation."""

    def test_creates_catalog_resource_from_resolved_catalog(self) -> None:
        """Test catalog resource is created from resolved_catalog."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "resolved_catalog": {
                "uri": "http://polaris:8181",
                "warehouse": "demo_catalog",
                "credentials": {},
            },
        }

        with (
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
            patch(
                "floe_dagster.definitions.PolarisCatalogResource.from_compiled_artifacts"
            ) as mock_catalog,
        ):
            mock_orch.return_value = MagicMock()
            mock_catalog.return_value = MagicMock(warehouse="demo_catalog")

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            mock_catalog.assert_called_once_with(artifacts)
            assert result.resources is not None
            assert "catalog" in result.resources

    def test_creates_catalog_resource_from_catalogs_dict(self) -> None:
        """Test catalog resource is created from catalogs dict (v1 format)."""
        artifacts = {
            "version": "1.0.0",
            "observability": {},
            "catalogs": {
                "default": {
                    "uri": "http://polaris:8181",
                    "warehouse": "demo_catalog",
                    "credentials": {},
                }
            },
        }

        with (
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
            patch(
                "floe_dagster.definitions.PolarisCatalogResource.from_compiled_artifacts"
            ) as mock_catalog,
        ):
            mock_orch.return_value = MagicMock()
            mock_catalog.return_value = MagicMock(warehouse="demo_catalog")

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            mock_catalog.assert_called_once()
            assert result.resources is not None
            assert "catalog" in result.resources

    def test_no_catalog_resource_when_no_catalog_config(self) -> None:
        """Test no catalog resource created when no catalog config."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            # Resources may still be present (orchestrator), just no catalog
            if result.resources:
                assert "catalog" not in result.resources

    def test_graceful_degradation_on_catalog_creation_failure(self) -> None:
        """Test that catalog creation failure doesn't break definitions."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "resolved_catalog": {"uri": "invalid", "warehouse": "bad"},
        }

        with (
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
            patch(
                "floe_dagster.definitions.PolarisCatalogResource.from_compiled_artifacts"
            ) as mock_catalog,
        ):
            mock_orch.return_value = MagicMock()
            mock_catalog.side_effect = ValueError("Invalid catalog config")

            # Should not raise - graceful degradation
            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            assert isinstance(result, Definitions)
            # Resources should exist but no catalog due to failure
            if result.resources:
                assert "catalog" not in result.resources


class TestFloeDefinitionsWithAssets:
    """Tests for FloeDefinitions with custom assets."""

    def test_includes_custom_assets(self) -> None:
        """Test that custom assets are included in definitions."""

        @asset
        def test_asset() -> dict[str, Any]:
            return {"rows": 100}

        artifacts = {"version": "2.0.0", "observability": {}}

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
                assets=[test_asset],
            )

            # Verify asset is included
            asset_graph = result.resolve_asset_graph()
            asset_keys = asset_graph.get_all_asset_keys()
            assert len(asset_keys) == 1
            assert "test_asset" in str(list(asset_keys)[0])

    def test_includes_multiple_assets(self) -> None:
        """Test that multiple assets are included."""

        @asset
        def asset_one() -> dict[str, Any]:
            return {}

        @asset
        def asset_two() -> dict[str, Any]:
            return {}

        artifacts = {"version": "2.0.0", "observability": {}}

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
                assets=[asset_one, asset_two],
            )

            asset_graph = result.resolve_asset_graph()
            assert len(asset_graph.get_all_asset_keys()) == 2


class TestFloeDefinitionsWithJobsAndSchedules:
    """Tests for FloeDefinitions with jobs and schedules."""

    def test_includes_jobs(self) -> None:
        """Test that jobs are included in definitions."""
        from dagster import define_asset_job

        @asset
        def my_asset() -> dict[str, Any]:
            return {}

        my_job = define_asset_job("my_job", selection="my_asset")

        artifacts = {"version": "2.0.0", "observability": {}}

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
                assets=[my_asset],
                jobs=[my_job],
            )

            # Dagster 1.11+: use resolve_job_def for asset jobs
            job_def = result.resolve_job_def("my_job")
            assert job_def is not None

    def test_includes_schedules(self) -> None:
        """Test that schedules are included in definitions."""
        from dagster import ScheduleDefinition, define_asset_job

        @asset
        def scheduled_asset() -> dict[str, Any]:
            return {}

        job = define_asset_job("scheduled_job", selection="scheduled_asset")
        schedule = ScheduleDefinition(
            name="my_schedule",
            job=job,
            cron_schedule="0 * * * *",
        )

        artifacts = {"version": "2.0.0", "observability": {}}

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
                assets=[scheduled_asset],
                jobs=[job],
                schedules=[schedule],
            )

            # Dagster 1.11+: use resolve_schedule_def for schedules
            schedule_def = result.resolve_schedule_def("my_schedule")
            assert schedule_def is not None


class TestFloeDefinitionsFromDict:
    """Tests for FloeDefinitions.from_dict() convenience method."""

    def test_from_dict_wraps_from_compiled_artifacts(self) -> None:
        """Test that from_dict is a convenience wrapper."""
        artifacts = {"version": "2.0.0", "observability": {}}

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_dict(
                artifacts,
                namespace="test_ns",
            )

            assert isinstance(result, Definitions)
            mock_orch.assert_called_once_with(artifacts, namespace="test_ns")

    def test_from_dict_passes_all_parameters(self) -> None:
        """Test that from_dict passes all parameters correctly."""

        @asset
        def dict_asset() -> dict[str, Any]:
            return {}

        artifacts = {"version": "2.0.0", "observability": {}}

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_dict(
                artifacts,
                assets=[dict_asset],
            )

            asset_graph = result.resolve_asset_graph()
            assert len(asset_graph.get_all_asset_keys()) == 1


class TestFloeDefinitionsOrchestrationAutoLoading:
    """Tests for FloeDefinitions orchestration auto-loading."""

    def test_auto_loads_jobs_from_orchestration_config(self) -> None:
        """Test jobs are auto-loaded from orchestration config."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "orchestration": {
                "jobs": {
                    "bronze_job": {
                        "type": "batch",
                        "selection": ["*"],
                    }
                }
            },
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            assert isinstance(result, Definitions)
            job_def = result.resolve_job_def("bronze_job")
            assert job_def is not None

    def test_auto_loads_schedules_from_orchestration_config(self) -> None:
        """Test schedules are auto-loaded from orchestration config."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "orchestration": {
                "jobs": {
                    "bronze_job": {
                        "type": "batch",
                        "selection": ["*"],
                    }
                },
                "schedules": {
                    "daily_bronze": {
                        "job": "bronze_job",
                        "cron_schedule": "0 6 * * *",
                    }
                },
            },
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            assert isinstance(result, Definitions)
            schedule_def = result.resolve_schedule_def("daily_bronze")
            assert schedule_def is not None

    def test_auto_loads_partitions_from_orchestration_config(self) -> None:
        """Test partitions are auto-loaded from orchestration config."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "orchestration": {
                "partitions": {
                    "daily": {
                        "type": "time_window",
                        "start": "2024-01-01",
                        "cron_schedule": "0 0 * * *",
                    }
                }
            },
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            assert isinstance(result, Definitions)

    def test_graceful_degradation_on_job_loading_failure(self) -> None:
        """Test graceful degradation when job loading fails."""
        artifacts = {
            "version": "2.0.0",
            "observability": {},
            "orchestration": {
                "jobs": {
                    "invalid_job": {
                        "type": "unknown_type",
                    }
                }
            },
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
            )

            assert isinstance(result, Definitions)


class TestFloeDefinitionsPlatformLoading:
    """Tests for FloeDefinitions platform.yaml auto-loading (Two-Tier Architecture)."""

    def test_loads_from_platform_yaml_when_no_artifacts_provided(self) -> None:
        """Test that platform.yaml is loaded when no artifacts are provided."""
        mock_platform = MagicMock()
        mock_platform.observability = None

        mock_catalog = MagicMock()
        mock_catalog.get_uri.return_value = "http://polaris:8181/api/catalog"
        mock_catalog.warehouse = "demo"
        mock_catalog.credentials = None
        mock_platform.get_catalog_profile.return_value = mock_catalog

        mock_storage = MagicMock()
        mock_storage.get_endpoint.return_value = "http://localstack:4566"
        mock_storage.region = "us-east-1"
        mock_storage.path_style_access = True
        mock_platform.get_storage_profile.return_value = mock_storage

        with (
            patch.object(FloeDefinitions, "_load_platform_config", return_value=mock_platform),
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
        ):
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts()

            assert isinstance(result, Definitions)
            # Platform config was used
            mock_platform.get_catalog_profile.assert_called_once_with("default")

    def test_artifacts_dict_takes_precedence_over_platform(self) -> None:
        """Test that explicit artifacts_dict takes precedence over platform.yaml."""
        artifacts = {"version": "2.0.0", "observability": {}}

        mock_platform = MagicMock()

        with (
            patch.object(
                FloeDefinitions, "_load_platform_config", return_value=mock_platform
            ) as mock_load,
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
        ):
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)
            # Platform config should NOT be loaded when artifacts_dict is provided
            mock_load.assert_not_called()

    def test_build_artifacts_from_platform_with_observability(self) -> None:
        """Test _build_artifacts_from_platform includes observability config."""
        mock_platform = MagicMock()

        mock_obs = MagicMock()
        mock_obs.traces = True
        mock_obs.otlp_endpoint = "http://jaeger:4317"
        mock_obs.lineage = True
        mock_obs.lineage_endpoint = "http://marquez:5000"
        mock_obs.attributes = {"service.name": "test-service", "namespace": "test"}
        mock_platform.observability = mock_obs

        mock_catalog = MagicMock()
        mock_catalog.get_uri.return_value = "http://polaris:8181"
        mock_catalog.warehouse = "test_warehouse"
        mock_catalog.credentials = None
        mock_platform.get_catalog_profile.return_value = mock_catalog

        mock_storage = MagicMock()
        mock_storage.get_endpoint.return_value = None
        mock_storage.region = "us-east-1"
        mock_storage.path_style_access = False
        mock_platform.get_storage_profile.return_value = mock_storage

        result = FloeDefinitions._build_artifacts_from_platform(mock_platform)

        assert result["version"] == "2.0.0"
        assert result["resolved_catalog"]["uri"] == "http://polaris:8181"
        assert result["resolved_catalog"]["warehouse"] == "test_warehouse"
        assert result["observability"]["tracing"]["enabled"] is True
        assert result["observability"]["tracing"]["endpoint"] == "http://jaeger:4317"
        assert result["observability"]["lineage"]["enabled"] is True
        assert result["observability"]["lineage"]["endpoint"] == "http://marquez:5000"

    def test_load_platform_config_from_env_var(self, tmp_path: Path) -> None:
        """Test loading platform config from FLOE_PLATFORM_FILE env var."""
        # Create a minimal platform.yaml
        platform_file = tmp_path / "platform.yaml"
        platform_file.write_text(
            """
version: "1.0.0"
catalogs:
  default:
    uri: http://test-polaris:8181/api/catalog
    warehouse: test_warehouse
"""
        )

        with patch.dict("os.environ", {"FLOE_PLATFORM_FILE": str(platform_file)}):
            result = FloeDefinitions._load_platform_config()

            assert result is not None
            assert result.catalogs["default"].warehouse == "test_warehouse"

    def test_load_platform_config_returns_none_when_not_found(self) -> None:
        """Test _load_platform_config returns None when platform.yaml not found."""
        # Clear all platform-related env vars and ensure no platform.yaml is found
        with (
            patch.dict(
                "os.environ",
                {"FLOE_PLATFORM_FILE": "/nonexistent/path.yaml"},
                clear=False,
            ),
            patch(
                "floe_core.compiler.platform_resolver.PlatformResolver.load",
                side_effect=Exception("Not found"),
            ),
        ):
            result = FloeDefinitions._load_platform_config()
            # Should return None (graceful degradation), not raise
            assert result is None
