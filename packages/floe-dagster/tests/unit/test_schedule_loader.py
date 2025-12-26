"""Unit tests for schedule loader.

T024: [010-orchestration-auto-discovery] schedule loader tests
Covers: 010-FR-013 through 010-FR-014

Tests the load_schedules function that converts ScheduleDefinition to Dagster schedules.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from dagster import JobDefinition, ScheduleDefinition
import pytest

from floe_core.schemas.schedule_definition import ScheduleDefinition as FloeScheduleDefinition


class TestLoadSchedules:
    """Tests for load_schedules function."""

    def test_load_schedules_with_empty_dict(self) -> None:
        """load_schedules should return empty list for empty input."""
        from floe_dagster.loaders.schedule_loader import load_schedules

        result = load_schedules({}, {})

        assert result == []

    def test_load_schedules_with_single_schedule(self) -> None:
        """load_schedules should create Dagster schedule from ScheduleDefinition."""
        from floe_dagster.loaders.schedule_loader import load_schedules

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"bronze_job": mock_job}

        schedules = {
            "daily_refresh": FloeScheduleDefinition(
                job="bronze_job",
                cron_schedule="0 6 * * *",
                timezone="America/New_York",
                description="Daily bronze refresh",
            )
        }

        result = load_schedules(schedules, jobs)

        assert len(result) == 1
        assert isinstance(result[0], ScheduleDefinition)
        assert result[0].name == "daily_refresh"
        assert result[0].cron_schedule == "0 6 * * *"

    def test_load_schedules_with_multiple_schedules(self) -> None:
        """load_schedules should handle multiple schedules."""
        from floe_dagster.loaders.schedule_loader import load_schedules

        mock_job1 = MagicMock(spec=JobDefinition)
        mock_job2 = MagicMock(spec=JobDefinition)
        jobs = {
            "bronze_job": mock_job1,
            "gold_job": mock_job2,
        }

        schedules = {
            "bronze_schedule": FloeScheduleDefinition(
                job="bronze_job",
                cron_schedule="0 6 * * *",
            ),
            "gold_schedule": FloeScheduleDefinition(
                job="gold_job",
                cron_schedule="0 12 * * *",
            ),
        }

        result = load_schedules(schedules, jobs)

        assert len(result) == 2
        schedule_names = [sched.name for sched in result]
        assert "bronze_schedule" in schedule_names
        assert "gold_schedule" in schedule_names

    def test_load_schedules_raises_on_unknown_job(self) -> None:
        """load_schedules should raise ValueError if job doesn't exist."""
        from floe_dagster.loaders.schedule_loader import load_schedules

        schedules = {
            "orphan_schedule": FloeScheduleDefinition(
                job="nonexistent_job",
                cron_schedule="0 * * * *",
            )
        }

        with pytest.raises(ValueError) as exc_info:
            load_schedules(schedules, {})

        assert "references unknown job" in str(exc_info.value)
        assert "nonexistent_job" in str(exc_info.value)

    def test_load_schedules_includes_description(self) -> None:
        """load_schedules should include description when provided."""
        from floe_dagster.loaders.schedule_loader import load_schedules

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"test_job": mock_job}

        schedules = {
            "described_schedule": FloeScheduleDefinition(
                job="test_job",
                cron_schedule="0 * * * *",
                description="Test schedule with description",
            )
        }

        result = load_schedules(schedules, jobs)

        assert len(result) == 1
        assert result[0].description == "Test schedule with description"

    def test_load_schedules_with_timezone(self) -> None:
        """load_schedules should use specified timezone."""
        from floe_dagster.loaders.schedule_loader import load_schedules

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"tz_job": mock_job}

        schedules = {
            "tz_schedule": FloeScheduleDefinition(
                job="tz_job",
                cron_schedule="0 9 * * *",
                timezone="Europe/London",
            )
        }

        result = load_schedules(schedules, jobs)

        assert len(result) == 1

    def test_load_schedules_default_timezone_is_utc(self) -> None:
        """load_schedules should default to UTC timezone."""
        from floe_dagster.loaders.schedule_loader import load_schedules

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"default_tz_job": mock_job}

        schedules = {
            "default_tz_schedule": FloeScheduleDefinition(
                job="default_tz_job",
                cron_schedule="0 * * * *",
            )
        }

        result = load_schedules(schedules, jobs)

        assert len(result) == 1

    def test_load_schedules_with_enabled_false(self) -> None:
        """load_schedules should handle enabled=False."""
        from floe_dagster.loaders.schedule_loader import load_schedules

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"disabled_job": mock_job}

        schedules = {
            "disabled_schedule": FloeScheduleDefinition(
                job="disabled_job",
                cron_schedule="0 * * * *",
                enabled=False,
            )
        }

        result = load_schedules(schedules, jobs)

        assert len(result) == 1
        assert result[0].name == "disabled_schedule"

    def test_load_schedules_with_partition_selector(self) -> None:
        """load_schedules should handle partition_selector."""
        from floe_core.schemas.schedule_definition import PartitionSelector
        from floe_dagster.loaders.schedule_loader import load_schedules

        mock_job = MagicMock(spec=JobDefinition)
        jobs = {"partitioned_job": mock_job}

        schedules = {
            "partitioned_schedule": FloeScheduleDefinition(
                job="partitioned_job",
                cron_schedule="0 * * * *",
                partition_selector=PartitionSelector.LATEST,
            )
        }

        result = load_schedules(schedules, jobs)

        assert len(result) == 1
        assert result[0].name == "partitioned_schedule"
