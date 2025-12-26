"""Unit tests for sensor loader.

T033: [010-orchestration-auto-discovery] Create sensor loader tests
Covers: 010-FR-030 through 010-FR-032

Tests the load_sensors function that converts SensorDefinition to Dagster sensors.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from dagster import JobDefinition, SensorDefinition
import pytest

from floe_core.schemas.sensor_definition import (
    AssetSensor,
    CustomSensor,
    FileWatcherSensor,
    RunStatus,
    RunStatusSensor,
)


class TestLoadSensors:
    """Tests for load_sensors function."""

    def test_load_sensors_with_empty_dict(self) -> None:
        """load_sensors should return empty list for empty input."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        result = load_sensors({}, {})

        assert result == []

    def test_load_sensors_raises_on_unknown_job(self) -> None:
        """load_sensors should raise ValueError if job doesn't exist."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        sensors = {
            "orphan_sensor": FileWatcherSensor(
                type="file_watcher",
                job="nonexistent_job",
                path="/tmp",
            )
        }

        with pytest.raises(ValueError) as exc_info:
            load_sensors(sensors, {})

        assert "references unknown job" in str(exc_info.value)
        assert "nonexistent_job" in str(exc_info.value)

    def test_load_sensors_raises_on_unknown_sensor_type(self) -> None:
        """load_sensors should raise NotImplementedError for unknown sensor types."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"test_job": mock_job}

        mock_sensor = MagicMock()
        mock_sensor.type = "unknown_type"
        mock_sensor.job = "test_job"

        sensors = {"bad_sensor": mock_sensor}

        with pytest.raises(NotImplementedError) as exc_info:
            load_sensors(sensors, jobs)

        assert "not yet implemented" in str(exc_info.value)


class TestFileWatcherSensor:
    """Tests for FileWatcherSensor creation."""

    def test_create_file_watcher_sensor(self) -> None:
        """Should create file watcher sensor with correct configuration."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"bronze_job": mock_job}

        sensors = {
            "file_arrival": FileWatcherSensor(
                type="file_watcher",
                job="bronze_job",
                path="/data/incoming",
                pattern="*.csv",
                poll_interval_seconds=60,
            )
        }

        result = load_sensors(sensors, jobs)

        assert len(result) == 1
        assert isinstance(result[0], SensorDefinition)
        assert result[0].name == "file_arrival"

    def test_file_watcher_sensor_default_pattern(self) -> None:
        """File watcher should use default pattern if not specified."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"test_job": mock_job}

        sensors = {
            "watcher": FileWatcherSensor(
                type="file_watcher",
                job="test_job",
                path="/data",
            )
        }

        result = load_sensors(sensors, jobs)

        assert len(result) == 1
        assert result[0].name == "watcher"

    def test_file_watcher_sensor_with_custom_poll_interval(self) -> None:
        """File watcher should respect custom poll interval."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"poll_job": mock_job}

        sensors = {
            "fast_watcher": FileWatcherSensor(
                type="file_watcher",
                job="poll_job",
                path="/data",
                poll_interval_seconds=10,
            )
        }

        result = load_sensors(sensors, jobs)

        assert len(result) == 1


class TestAssetSensor:
    """Tests for AssetSensor creation."""

    def test_create_asset_sensor_single_asset(self) -> None:
        """Should create asset sensor for single watched asset."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"downstream_job": mock_job}

        sensors = {
            "bronze_watcher": AssetSensor(
                type="asset_sensor",
                job="downstream_job",
                watched_assets=["bronze_customers"],
                poll_interval_seconds=30,
            )
        }

        result = load_sensors(sensors, jobs)

        assert len(result) == 1
        assert isinstance(result[0], SensorDefinition)
        assert result[0].name == "bronze_watcher"

    def test_asset_sensor_raises_on_multiple_assets(self) -> None:
        """Asset sensor should raise ValueError if watching multiple assets."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"test_job": mock_job}

        sensors = {
            "multi_watcher": AssetSensor(
                type="asset_sensor",
                job="test_job",
                watched_assets=["asset1", "asset2"],
            )
        }

        with pytest.raises(ValueError) as exc_info:
            load_sensors(sensors, jobs)

        assert "must watch exactly one asset" in str(exc_info.value)
        assert "Got 2 assets" in str(exc_info.value)

    def test_asset_sensor_validates_minimum_assets(self) -> None:
        """Asset sensor schema should prevent empty watched_assets list."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            AssetSensor(
                type="asset_sensor",
                job="test_job",
                watched_assets=[],
            )

        assert "too_short" in str(exc_info.value)


class TestRunStatusSensor:
    """Tests for RunStatusSensor creation."""

    def test_create_run_status_sensor_success(self) -> None:
        """Should create run status sensor for SUCCESS status."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"reporting_job": mock_job}

        sensors = {
            "success_reporter": RunStatusSensor(
                type="run_status",
                job="reporting_job",
                watched_jobs=["bronze_job", "silver_job"],
                status=RunStatus.SUCCESS,
                poll_interval_seconds=15,
            )
        }

        result = load_sensors(sensors, jobs)

        assert len(result) == 1
        assert isinstance(result[0], SensorDefinition)
        assert result[0].name == "success_reporter"

    def test_create_run_status_sensor_failure(self) -> None:
        """Should create run status sensor for FAILURE status."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"alert_job": mock_job}

        sensors = {
            "failure_alerter": RunStatusSensor(
                type="run_status",
                job="alert_job",
                watched_jobs=["production_job"],
                status=RunStatus.FAILURE,
            )
        }

        result = load_sensors(sensors, jobs)

        assert len(result) == 1
        assert result[0].name == "failure_alerter"

    def test_create_run_status_sensor_started(self) -> None:
        """Should create run status sensor for STARTED status."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"tracker_job": mock_job}

        sensors = {
            "start_tracker": RunStatusSensor(
                type="run_status",
                job="tracker_job",
                watched_jobs=["etl_job"],
                status=RunStatus.STARTED,
            )
        }

        result = load_sensors(sensors, jobs)

        assert len(result) == 1

    def test_run_status_sensor_all_statuses_supported(self) -> None:
        """Should support all RunStatus enum values."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"test_job": mock_job}

        for status in [RunStatus.SUCCESS, RunStatus.FAILURE, RunStatus.STARTED]:
            sensors = {
                f"{status.value}_sensor": RunStatusSensor(
                    type="run_status",
                    job="test_job",
                    watched_jobs=["monitored_job"],
                    status=status,
                )
            }

            result = load_sensors(sensors, jobs)
            assert len(result) == 1


class TestCustomSensor:
    """Tests for CustomSensor creation."""

    def test_create_custom_sensor(self) -> None:
        """Should create custom sensor with target function."""
        from unittest.mock import patch

        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"custom_job": mock_job}

        sensors = {
            "api_poller": CustomSensor(
                type="custom",
                job="custom_job",
                target_function="demo.orchestration.sensors.poll_api",
                args={"endpoint": "https://api.example.com"},
                poll_interval_seconds=300,
            )
        }

        mock_function = MagicMock()
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.poll_api = mock_function
            mock_import.return_value = mock_module

            result = load_sensors(sensors, jobs)

            assert len(result) == 1
            assert isinstance(result[0], SensorDefinition)
            assert result[0].name == "api_poller"
            mock_import.assert_called_once_with("demo.orchestration.sensors")

    def test_custom_sensor_without_args(self) -> None:
        """Custom sensor should work without args."""
        from unittest.mock import patch

        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"simple_job": mock_job}

        sensors = {
            "simple_custom": CustomSensor(
                type="custom",
                job="simple_job",
                target_function="app.sensors.simple_check",
            )
        }

        mock_function = MagicMock()
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.simple_check = mock_function
            mock_import.return_value = mock_module

            result = load_sensors(sensors, jobs)

            assert len(result) == 1


class TestLoadSensorsMultiple:
    """Tests for loading multiple sensors of different types."""

    def test_load_multiple_sensor_types(self) -> None:
        """Should handle multiple sensors of different types."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job1 = MagicMock(spec=JobDefinition)
        mock_job2 = MagicMock(spec=JobDefinition)
        mock_job3 = MagicMock(spec=JobDefinition)

        jobs = {
            "job1": mock_job1,
            "job2": mock_job2,
            "job3": mock_job3,
        }

        sensors = {
            "file_sensor": FileWatcherSensor(
                type="file_watcher",
                job="job1",
                path="/data",
            ),
            "asset_sensor": AssetSensor(
                type="asset_sensor",
                job="job2",
                watched_assets=["my_asset"],
            ),
            "status_sensor": RunStatusSensor(
                type="run_status",
                job="job3",
                watched_jobs=["upstream_job"],
                status=RunStatus.SUCCESS,
            ),
        }

        result = load_sensors(sensors, jobs)

        assert len(result) == 3
        sensor_names = [sensor.name for sensor in result]
        assert "file_sensor" in sensor_names
        assert "asset_sensor" in sensor_names
        assert "status_sensor" in sensor_names

    def test_load_multiple_sensors_same_type(self) -> None:
        """Should handle multiple sensors of the same type."""
        from floe_dagster.loaders.sensor_loader import load_sensors

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"processor": mock_job}

        sensors = {
            "csv_watcher": FileWatcherSensor(
                type="file_watcher",
                job="processor",
                path="/data/csv",
                pattern="*.csv",
            ),
            "json_watcher": FileWatcherSensor(
                type="file_watcher",
                job="processor",
                path="/data/json",
                pattern="*.json",
            ),
            "xml_watcher": FileWatcherSensor(
                type="file_watcher",
                job="processor",
                path="/data/xml",
                pattern="*.xml",
            ),
        }

        result = load_sensors(sensors, jobs)

        assert len(result) == 3
        sensor_names = [sensor.name for sensor in result]
        assert "csv_watcher" in sensor_names
        assert "json_watcher" in sensor_names
        assert "xml_watcher" in sensor_names
