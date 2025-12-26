"""Schedule loader for converting ScheduleDefinition to Dagster schedules.

T021: [010-orchestration-auto-discovery] Create schedule loader
Covers: 010-FR-013 through 010-FR-014

This module converts ScheduleDefinition from floe.yaml into Dagster schedule definitions,
supporting cron-based job execution with timezone and partition selection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dagster import JobDefinition as DagsterJobDefinition
    from dagster import ScheduleDefinition as DagsterScheduleDefinition

    from floe_core.schemas.schedule_definition import ScheduleDefinition


def load_schedules(
    schedules: dict[str, ScheduleDefinition],
    jobs: dict[str, DagsterJobDefinition],
) -> list[DagsterScheduleDefinition]:
    """Load schedules from ScheduleDefinition dictionary.

    Converts ScheduleDefinition configurations from floe.yaml into Dagster schedule
    definitions, linking them to existing Dagster jobs.

    Args:
        schedules: Dictionary of schedule name to ScheduleDefinition.
        jobs: Dictionary of job name to Dagster JobDefinition for linking.

    Returns:
        List of Dagster ScheduleDefinition objects.

    Raises:
        ValueError: If referenced job doesn't exist.

    Example:
        >>> from floe_core.schemas.schedule_definition import ScheduleDefinition
        >>> schedules_config = {
        ...     "daily_refresh": ScheduleDefinition(
        ...         job="bronze_job",
        ...         cron_schedule="0 6 * * *",
        ...         timezone="UTC",
        ...     )
        ... }
        >>> dagster_schedules = load_schedules(schedules_config, dagster_jobs)
    """
    if not schedules:
        return []

    from dagster import ScheduleDefinition as DagsterScheduleDef

    dagster_schedules: list[DagsterScheduleDefinition] = []

    for schedule_name, schedule_def in schedules.items():
        if schedule_def.job not in jobs:
            msg = (
                f"Schedule '{schedule_name}' references unknown job '{schedule_def.job}'. "
                f"Available jobs: {list(jobs.keys())}"
            )
            raise ValueError(msg)

        target_job = jobs[schedule_def.job]

        schedule_kwargs = {
            "name": schedule_name,
            "job": target_job,
            "cron_schedule": schedule_def.cron_schedule,
            "execution_timezone": schedule_def.timezone,
        }

        if schedule_def.description:
            schedule_kwargs["description"] = schedule_def.description

        if schedule_def.partition_selector:
            schedule_kwargs["default_status"] = "RUNNING" if schedule_def.enabled else "STOPPED"

        dagster_schedule = DagsterScheduleDef(**schedule_kwargs)
        dagster_schedules.append(dagster_schedule)

    return dagster_schedules
