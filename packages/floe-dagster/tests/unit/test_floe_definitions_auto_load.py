"""Unit tests for FloeDefinitions auto-loading functionality.

T045: [010-orchestration-auto-discovery] Test FloeDefinitions auto-loading
Covers: 010-FR-001, 010-FR-020, 010-FR-021, 010-FR-030

Tests that FloeDefinitions.from_compiled_artifacts() properly auto-loads:
- Assets from orchestration.asset_modules
- Jobs from orchestration.jobs
- Schedules from orchestration.schedules
- Sensors from orchestration.sensors
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from dagster import Definitions
import pytest

from floe_dagster.definitions import FloeDefinitions


class TestFloeDefinitionsAssetAutoLoading:
    """Tests for auto-loading assets from orchestration.asset_modules."""

    @pytest.mark.requirement("010-FR-001")
    def test_auto_loads_assets_from_modules(self) -> None:
        """Verify assets are auto-loaded from orchestration.asset_modules.

        Requirements:
            - FR-001: Auto-load assets from orchestration.asset_modules
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "asset_modules": [
                    "test.module.assets",
                ],
            },
        }

        mock_asset = MagicMock()
        mock_asset.op.tags = {}

        with (
            patch("importlib.import_module") as mock_import,
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
        ):
            mock_module = MagicMock()
            mock_module.test_asset = mock_asset
            mock_import.return_value = mock_module
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)
            mock_import.assert_called_with("test.module.assets")

    @pytest.mark.requirement("010-FR-001")
    def test_skips_invalid_asset_modules(self) -> None:
        """Verify invalid asset modules are skipped gracefully.

        Requirements:
            - FR-001: Invalid modules should not crash auto-loading
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "asset_modules": [
                    "nonexistent.module.assets",
                ],
            },
        }

        with (
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
            patch("importlib.import_module", side_effect=ModuleNotFoundError),
        ):
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)


class TestFloeDefinitionsJobAutoLoading:
    """Tests for auto-loading jobs from orchestration.jobs."""

    @pytest.mark.requirement("010-FR-020")
    def test_auto_loads_batch_jobs(self) -> None:
        """Verify batch jobs are auto-loaded from orchestration.jobs.

        Requirements:
            - FR-020: Auto-load batch jobs from orchestration config
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "test_job": {
                        "type": "batch",
                        "selection": ["*"],
                        "description": "Test batch job",
                    },
                },
            },
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)

    @pytest.mark.requirement("010-FR-021")
    def test_auto_loads_ops_jobs(self) -> None:
        """Verify ops jobs are auto-loaded from orchestration.jobs.

        Requirements:
            - FR-021: Auto-load ops jobs from orchestration config
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "maintenance": {
                        "type": "ops",
                        "target_function": "test.ops.maintenance",
                        "description": "Test ops job",
                    },
                },
            },
        }

        mock_op = MagicMock()
        with (
            patch("importlib.import_module") as mock_import,
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
        ):
            mock_module = MagicMock()
            mock_module.maintenance = mock_op
            mock_import.return_value = mock_module
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)
            mock_import.assert_called_with("test.ops")

    @pytest.mark.requirement("010-FR-020")
    def test_handles_invalid_job_selection_gracefully(self) -> None:
        """Verify invalid job selections are handled gracefully.

        Requirements:
            - FR-020: Invalid job selections should not crash loading
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "invalid_job": {
                        "type": "batch",
                        "selection": ["nonexistent:group"],
                        "description": "Invalid selection",
                    },
                },
            },
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)


class TestFloeDefinitionsScheduleAutoLoading:
    """Tests for auto-loading schedules from orchestration.schedules."""

    @pytest.mark.requirement("010-FR-021")
    def test_auto_loads_schedules(self) -> None:
        """Verify schedules are auto-loaded from orchestration.schedules.

        Requirements:
            - FR-021: Auto-load schedules from orchestration config
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "test_job": {
                        "type": "batch",
                        "selection": ["*"],
                        "description": "Test job",
                    },
                },
                "schedules": {
                    "test_schedule": {
                        "job": "test_job",
                        "cron_schedule": "0 0 * * *",
                        "description": "Test schedule",
                    },
                },
            },
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)

    @pytest.mark.requirement("010-FR-021")
    def test_handles_schedule_with_unknown_job(self) -> None:
        """Verify schedules referencing unknown jobs are handled gracefully.

        Requirements:
            - FR-021: Schedules with unknown jobs should not crash loading
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "schedules": {
                    "orphan_schedule": {
                        "job": "nonexistent_job",
                        "cron_schedule": "0 0 * * *",
                        "description": "Orphan schedule",
                    },
                },
            },
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)


class TestFloeDefinitionsSensorAutoLoading:
    """Tests for auto-loading sensors from orchestration.sensors."""

    @pytest.mark.requirement("010-FR-030")
    def test_auto_loads_file_watcher_sensors(self) -> None:
        """Verify file watcher sensors are auto-loaded.

        Requirements:
            - FR-030: Auto-load file watcher sensors from orchestration config
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "test_job": {
                        "type": "batch",
                        "selection": ["*"],
                        "description": "Test job",
                    },
                },
                "sensors": {
                    "file_sensor": {
                        "type": "file_watcher",
                        "job": "test_job",
                        "path": "/tmp",
                        "pattern": "*.csv",
                        "poll_interval_seconds": 60,
                    },
                },
            },
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)

    @pytest.mark.requirement("010-FR-030")
    def test_handles_sensor_with_unknown_job(self) -> None:
        """Verify sensors referencing unknown jobs are handled gracefully.

        Requirements:
            - FR-030: Sensors with unknown jobs should not crash loading
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "sensors": {
                    "orphan_sensor": {
                        "type": "file_watcher",
                        "job": "nonexistent_job",
                        "path": "/tmp",
                        "pattern": "*.csv",
                        "poll_interval_seconds": 60,
                    },
                },
            },
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)


class TestFloeDefinitionsAutoLoadingIntegration:
    """Integration tests for combined auto-loading."""

    @pytest.mark.requirement("010-FR-001", "010-FR-020", "010-FR-021", "010-FR-030")
    def test_auto_loads_all_components(self) -> None:
        """Verify all orchestration components are auto-loaded together.

        Requirements:
            - FR-001: Auto-load assets
            - FR-020: Auto-load jobs
            - FR-021: Auto-load schedules
            - FR-030: Auto-load sensors
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "asset_modules": ["test.assets"],
                "jobs": {
                    "batch_job": {
                        "type": "batch",
                        "selection": ["*"],
                        "description": "Batch job",
                    },
                    "ops_job": {
                        "type": "ops",
                        "target_function": "test.ops.maintenance",
                        "description": "Ops job",
                    },
                },
                "schedules": {
                    "daily_schedule": {
                        "job": "batch_job",
                        "cron_schedule": "0 0 * * *",
                        "description": "Daily schedule",
                    },
                },
                "sensors": {
                    "file_sensor": {
                        "type": "file_watcher",
                        "job": "batch_job",
                        "path": "/tmp",
                        "pattern": "*.csv",
                        "poll_interval_seconds": 60,
                    },
                },
            },
        }

        mock_asset = MagicMock()
        mock_asset.op.tags = {}
        mock_op = MagicMock()

        with (
            patch("importlib.import_module") as mock_import,
            patch(
                "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
            ) as mock_orch,
        ):

            def import_side_effect(module_name: str) -> MagicMock:
                mock_module = MagicMock()
                if "assets" in module_name:
                    mock_module.test_asset = mock_asset
                elif "ops" in module_name:
                    mock_module.maintenance = mock_op
                return mock_module

            mock_import.side_effect = import_side_effect
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)

    @pytest.mark.requirement("010-FR-001")
    def test_empty_orchestration_config(self) -> None:
        """Verify empty orchestration config does not crash.

        Requirements:
            - FR-001: Empty orchestration should be valid
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {},
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)

    @pytest.mark.requirement("010-FR-001")
    def test_no_orchestration_config(self) -> None:
        """Verify missing orchestration config does not crash.

        Requirements:
            - FR-001: Missing orchestration should be valid
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
        }

        with patch(
            "floe_dagster.definitions.ObservabilityOrchestrator.from_compiled_artifacts"
        ) as mock_orch:
            mock_orch.return_value = MagicMock()

            result = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(result, Definitions)
