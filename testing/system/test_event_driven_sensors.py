"""Integration tests for event-driven sensor auto-loading.

T035: [010-orchestration-auto-discovery] Test event-driven sensor integration
Covers: 010-FR-030, 010-FR-031, 010-FR-032

Tests that sensors defined in orchestration configuration are automatically loaded
and appear in Dagster Definitions, validating end-to-end sensor auto-discovery.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from dagster import Definitions, JobDefinition, SensorDefinition
import pytest

from floe_dagster.definitions import FloeDefinitions
from testing.base_classes import IntegrationTestBase


class TestEventDrivenSensors(IntegrationTestBase):
    """Integration tests for event-driven sensor auto-loading."""

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-030", "010-FR-031", "010-FR-032")
    def test_auto_load_file_watcher_sensor(self) -> None:
        """Verify file watcher sensor is auto-loaded from orchestration config.

        Requirements:
            - FR-030: Auto-load sensors from orchestration config
            - FR-031: Support file watcher sensor type
            - FR-032: Link sensors to jobs
        """
        mock_job = MagicMock(spec=JobDefinition)
        mock_job.name = "bronze_refresh"

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "sensors": {
                    "file_arrival": {
                        "type": "file_watcher",
                        "job": "bronze_refresh",
                        "path": "/data/incoming",
                        "pattern": "*.csv",
                        "poll_interval_seconds": 60,
                    }
                }
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(
            artifacts_dict=artifacts,
            jobs=[mock_job],
        )

        assert isinstance(defs, Definitions)
        assert defs.sensors is not None
        assert len(defs.sensors) == 1

        sensor = list(defs.sensors)[0]
        assert isinstance(sensor, SensorDefinition)
        assert sensor.name == "file_arrival"

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-030", "010-FR-031", "010-FR-032")
    def test_auto_load_asset_sensor(self) -> None:
        """Verify asset sensor is auto-loaded from orchestration config.

        Requirements:
            - FR-030: Auto-load sensors from orchestration config
            - FR-031: Support asset sensor type
            - FR-032: Link sensors to jobs
        """
        mock_job = MagicMock(spec=JobDefinition)
        mock_job.name = "downstream_job"

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "sensors": {
                    "bronze_watcher": {
                        "type": "asset_sensor",
                        "job": "downstream_job",
                        "watched_assets": ["bronze_customers"],
                        "poll_interval_seconds": 30,
                    }
                }
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(
            artifacts_dict=artifacts,
            jobs=[mock_job],
        )

        assert isinstance(defs, Definitions)
        assert defs.sensors is not None
        assert len(defs.sensors) == 1

        sensor = list(defs.sensors)[0]
        assert isinstance(sensor, SensorDefinition)
        assert sensor.name == "bronze_watcher"

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-030", "010-FR-031", "010-FR-032")
    def test_auto_load_run_status_sensor(self) -> None:
        """Verify run status sensor is auto-loaded from orchestration config.

        Requirements:
            - FR-030: Auto-load sensors from orchestration config
            - FR-031: Support run status sensor type
            - FR-032: Link sensors to jobs
        """
        mock_job = MagicMock(spec=JobDefinition)
        mock_job.name = "alert_job"

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "sensors": {
                    "failure_alerter": {
                        "type": "run_status",
                        "job": "alert_job",
                        "watched_jobs": ["production_job"],
                        "status": "FAILURE",
                        "poll_interval_seconds": 15,
                    }
                }
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(
            artifacts_dict=artifacts,
            jobs=[mock_job],
        )

        assert isinstance(defs, Definitions)
        assert defs.sensors is not None
        assert len(defs.sensors) == 1

        sensor = list(defs.sensors)[0]
        assert isinstance(sensor, SensorDefinition)
        assert sensor.name == "failure_alerter"

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-030", "010-FR-031", "010-FR-032")
    def test_auto_load_custom_sensor(self) -> None:
        """Verify custom sensor is auto-loaded from orchestration config.

        Requirements:
            - FR-030: Auto-load sensors from orchestration config
            - FR-031: Support custom sensor type
            - FR-032: Link sensors to jobs
        """
        from unittest.mock import patch

        mock_job = MagicMock(spec=JobDefinition)
        mock_job.name = "custom_job"

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "sensors": {
                    "api_poller": {
                        "type": "custom",
                        "job": "custom_job",
                        "target_function": "testing.fixtures.test_sensors.poll_api",
                        "args": {"threshold": 100},
                        "poll_interval_seconds": 300,
                    }
                }
            },
        }

        mock_function = MagicMock()
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.poll_api = mock_function
            mock_import.return_value = mock_module

            defs = FloeDefinitions.from_compiled_artifacts(
                artifacts_dict=artifacts,
                jobs=[mock_job],
            )

            assert isinstance(defs, Definitions)
            assert defs.sensors is not None
            assert len(defs.sensors) == 1

            sensor = list(defs.sensors)[0]
            assert isinstance(sensor, SensorDefinition)
            assert sensor.name == "api_poller"

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-030", "010-FR-031", "010-FR-032")
    def test_auto_load_multiple_sensors(self) -> None:
        """Verify multiple sensors of different types are auto-loaded.

        Requirements:
            - FR-030: Auto-load multiple sensors from orchestration config
            - FR-031: Support all sensor types
            - FR-032: Link sensors to respective jobs
        """
        mock_job1 = MagicMock(spec=JobDefinition)
        mock_job1.name = "job1"

        mock_job2 = MagicMock(spec=JobDefinition)
        mock_job2.name = "job2"

        mock_job3 = MagicMock(spec=JobDefinition)
        mock_job3.name = "job3"

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "sensors": {
                    "file_sensor": {
                        "type": "file_watcher",
                        "job": "job1",
                        "path": "/data",
                        "poll_interval_seconds": 60,
                    },
                    "asset_sensor": {
                        "type": "asset_sensor",
                        "job": "job2",
                        "watched_assets": ["my_asset"],
                        "poll_interval_seconds": 30,
                    },
                    "status_sensor": {
                        "type": "run_status",
                        "job": "job3",
                        "watched_jobs": ["upstream_job"],
                        "status": "SUCCESS",
                        "poll_interval_seconds": 15,
                    },
                }
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(
            artifacts_dict=artifacts,
            jobs=[mock_job1, mock_job2, mock_job3],
        )

        assert isinstance(defs, Definitions)
        assert defs.sensors is not None
        assert len(defs.sensors) == 3

        sensor_names = {sensor.name for sensor in defs.sensors}
        assert sensor_names == {"file_sensor", "asset_sensor", "status_sensor"}

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-030")
    def test_combines_auto_loaded_with_explicit_sensors(self) -> None:
        """Verify auto-loaded sensors combine with explicitly passed sensors.

        Requirements:
            - FR-030: Auto-discovered sensors work alongside explicit sensors
        """
        from dagster import SkipReason, sensor

        mock_job1 = MagicMock(spec=JobDefinition)
        mock_job1.name = "job1"

        mock_job2 = MagicMock(spec=JobDefinition)
        mock_job2.name = "job2"

        @sensor(name="explicit_sensor", job=mock_job2)
        def _explicit_sensor(context):
            yield SkipReason("Example sensor")

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "sensors": {
                    "config_sensor": {
                        "type": "file_watcher",
                        "job": "job1",
                        "path": "/data",
                        "poll_interval_seconds": 60,
                    }
                }
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(
            artifacts_dict=artifacts,
            jobs=[mock_job1, mock_job2],
            sensors=[_explicit_sensor],
        )

        assert isinstance(defs, Definitions)
        assert defs.sensors is not None
        assert len(defs.sensors) == 2

        sensor_names = {sensor.name for sensor in defs.sensors}
        assert sensor_names == {"config_sensor", "explicit_sensor"}

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-030")
    def test_empty_sensors_config_does_not_error(self) -> None:
        """Verify empty sensors config does not cause errors.

        Requirements:
            - FR-030: Empty configuration is valid
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "sensors": {},
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

        assert isinstance(defs, Definitions)

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-030")
    def test_missing_sensors_key_does_not_error(self) -> None:
        """Verify missing sensors key does not cause errors.

        Requirements:
            - FR-030: Missing configuration is valid
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {},
        }

        defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

        assert isinstance(defs, Definitions)
