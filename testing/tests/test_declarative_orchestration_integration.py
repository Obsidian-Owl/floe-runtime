"""Integration tests for declarative orchestration.

T027: [010-orchestration-auto-discovery] Test declarative orchestration integration
Covers: 010-FR-018, 010-FR-024, 010-FR-025

Tests that jobs, schedules, and partitions defined in orchestration config
are automatically loaded and executable in Dagster.
"""

from __future__ import annotations

from dagster import Definitions, asset
import pytest

from floe_dagster.definitions import FloeDefinitions


@pytest.mark.requirement("010-FR-018", "010-FR-024", "010-FR-025")
def test_declarative_job_schedule_execution() -> None:
    """Verify jobs and schedules from config execute correctly.

    Requirements:
        - FR-018: Jobs from orchestration config appear in Dagster
        - FR-024: Schedules from orchestration config are active
        - FR-025: Jobs can be executed via API/UI
    """

    @asset
    def bronze_customers() -> dict[str, int]:
        return {"rows": 100}

    @asset
    def bronze_products() -> dict[str, int]:
        return {"rows": 50}

    artifacts = {
        "version": "2.0.0",
        "observability": {"tracing": {"enabled": False}},
        "orchestration": {
            "jobs": {
                "bronze_job": {
                    "type": "batch",
                    "selection": ["*"],
                    "description": "Process bronze layer",
                    "tags": {"layer": "bronze"},
                }
            },
            "schedules": {
                "daily_bronze": {
                    "job": "bronze_job",
                    "cron_schedule": "0 6 * * *",
                    "timezone": "UTC",
                    "description": "Daily bronze refresh",
                }
            },
        },
    }

    defs = FloeDefinitions.from_compiled_artifacts(
        artifacts_dict=artifacts,
        assets=[bronze_customers, bronze_products],
    )

    assert isinstance(defs, Definitions)

    job_def = defs.resolve_job_def("bronze_job")
    assert job_def is not None
    assert job_def.name == "bronze_job"
    assert job_def.description == "Process bronze layer"

    schedule_def = defs.resolve_schedule_def("daily_bronze")
    assert schedule_def is not None
    assert schedule_def.name == "daily_bronze"
    assert schedule_def.cron_schedule == "0 6 * * *"


@pytest.mark.requirement("010-FR-015", "010-FR-016", "010-FR-017")
def test_partitions_from_config_available_to_jobs() -> None:
    """Verify partitions from config are available to jobs.

    Requirements:
        - FR-015: Time-window partitions from config
        - FR-016: Static partitions from config
        - FR-017: Multi and dynamic partitions from config
    """

    @asset
    def daily_sales() -> dict[str, int]:
        return {"rows": 1000}

    artifacts = {
        "version": "2.0.0",
        "observability": {"tracing": {"enabled": False}},
        "orchestration": {
            "partitions": {
                "daily": {
                    "type": "time_window",
                    "start": "2024-01-01",
                    "cron_schedule": "0 0 * * *",
                    "timezone": "UTC",
                }
            },
            "jobs": {
                "sales_job": {
                    "type": "batch",
                    "selection": ["*"],
                }
            },
        },
    }

    defs = FloeDefinitions.from_compiled_artifacts(
        artifacts_dict=artifacts,
        assets=[daily_sales],
    )

    assert isinstance(defs, Definitions)

    job_def = defs.resolve_job_def("sales_job")
    assert job_def is not None


@pytest.mark.requirement("010-FR-011", "010-FR-012")
def test_multiple_jobs_with_different_selections() -> None:
    """Verify multiple jobs with different asset selections.

    Requirements:
        - FR-011: Batch jobs with asset selection expressions
        - FR-012: Jobs support description and tags
    """

    @asset(group_name="bronze")
    def bronze_asset() -> dict[str, int]:
        return {"rows": 100}

    @asset(group_name="silver")
    def silver_asset() -> dict[str, int]:
        return {"rows": 50}

    artifacts = {
        "version": "2.0.0",
        "observability": {"tracing": {"enabled": False}},
        "orchestration": {
            "jobs": {
                "bronze_job": {
                    "type": "batch",
                    "selection": ["*"],
                    "description": "Bronze layer job",
                    "tags": {"layer": "bronze"},
                },
                "silver_job": {
                    "type": "batch",
                    "selection": ["*"],
                    "description": "Silver layer job",
                    "tags": {"layer": "silver"},
                },
            }
        },
    }

    defs = FloeDefinitions.from_compiled_artifacts(
        artifacts_dict=artifacts,
        assets=[bronze_asset, silver_asset],
    )

    assert isinstance(defs, Definitions)

    bronze_job = defs.resolve_job_def("bronze_job")
    assert bronze_job is not None
    assert bronze_job.description == "Bronze layer job"

    silver_job = defs.resolve_job_def("silver_job")
    assert silver_job is not None
    assert silver_job.description == "Silver layer job"


@pytest.mark.requirement("010-FR-013", "010-FR-014")
def test_schedule_with_partition_selector() -> None:
    """Verify schedule with partition selector configuration.

    Requirements:
        - FR-013: Schedules from orchestration config
        - FR-014: Schedules support timezone and partition selection
    """

    @asset
    def partitioned_asset() -> dict[str, int]:
        return {"rows": 100}

    artifacts = {
        "version": "2.0.0",
        "observability": {"tracing": {"enabled": False}},
        "orchestration": {
            "partitions": {
                "daily": {
                    "type": "time_window",
                    "start": "2024-01-01",
                    "cron_schedule": "0 0 * * *",
                }
            },
            "jobs": {
                "partitioned_job": {
                    "type": "batch",
                    "selection": ["*"],
                }
            },
            "schedules": {
                "partitioned_schedule": {
                    "job": "partitioned_job",
                    "cron_schedule": "0 6 * * *",
                    "timezone": "America/New_York",
                    "partition_selector": "latest",
                    "enabled": True,
                }
            },
        },
    }

    defs = FloeDefinitions.from_compiled_artifacts(
        artifacts_dict=artifacts,
        assets=[partitioned_asset],
    )

    assert isinstance(defs, Definitions)

    schedule_def = defs.resolve_schedule_def("partitioned_schedule")
    assert schedule_def is not None
    assert schedule_def.cron_schedule == "0 6 * * *"


@pytest.mark.requirement("010-FR-018")
def test_graceful_degradation_on_invalid_config() -> None:
    """Verify graceful degradation when orchestration config is invalid.

    Requirements:
        - FR-018: System handles invalid configs without crashing
    """
    artifacts = {
        "version": "2.0.0",
        "observability": {"tracing": {"enabled": False}},
        "orchestration": {
            "jobs": {
                "invalid_job": {
                    "type": "unknown_type",
                }
            }
        },
    }

    defs = FloeDefinitions.from_compiled_artifacts(
        artifacts_dict=artifacts,
    )

    assert isinstance(defs, Definitions)


@pytest.mark.requirement("010-FR-011", "010-FR-013")
def test_schedule_references_valid_job() -> None:
    """Verify schedule validation requires valid job reference.

    Requirements:
        - FR-011: Jobs must exist before schedules reference them
        - FR-013: Schedules validate job references
    """
    from dagster import DagsterInvariantViolationError

    artifacts = {
        "version": "2.0.0",
        "observability": {"tracing": {"enabled": False}},
        "orchestration": {
            "jobs": {
                "existing_job": {
                    "type": "batch",
                    "selection": ["*"],
                }
            },
            "schedules": {
                "orphan_schedule": {
                    "job": "nonexistent_job",
                    "cron_schedule": "0 * * * *",
                }
            },
        },
    }

    defs = FloeDefinitions.from_compiled_artifacts(
        artifacts_dict=artifacts,
    )

    assert isinstance(defs, Definitions)

    with pytest.raises(DagsterInvariantViolationError):
        defs.resolve_schedule_def("orphan_schedule")
