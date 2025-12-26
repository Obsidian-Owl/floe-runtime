"""Sensor loader for converting SensorDefinition to Dagster sensors.

T032: [010-orchestration-auto-discovery] Create sensor loader
Covers: 010-FR-030 through 010-FR-032

This module converts SensorDefinition from floe.yaml into Dagster sensor definitions,
supporting file watchers, asset sensors, run status sensors, and custom sensor logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dagster import JobDefinition as DagsterJobDefinition
    from dagster import SensorDefinition as DagsterSensorDefinition

    from floe_core.schemas.sensor_definition import SensorDefinition


def load_sensors(
    sensors: dict[str, SensorDefinition],
    jobs: dict[str, DagsterJobDefinition],
) -> list[DagsterSensorDefinition]:
    """Load sensors from SensorDefinition dictionary.

    Converts SensorDefinition configurations from floe.yaml into Dagster sensor
    definitions, linking them to existing Dagster jobs.

    Args:
        sensors: Dictionary of sensor name to SensorDefinition.
        jobs: Dictionary of job name to Dagster JobDefinition for linking.

    Returns:
        List of Dagster SensorDefinition objects.

    Raises:
        ValueError: If referenced job doesn't exist.
        NotImplementedError: If sensor type is not yet supported.

    Example:
        >>> from floe_core.schemas.sensor_definition import FileWatcherSensor
        >>> sensors_config = {
        ...     "file_arrival": FileWatcherSensor(
        ...         type="file_watcher",
        ...         job="bronze_refresh",
        ...         path="./incoming/",
        ...         pattern="*.csv",
        ...     )
        ... }
        >>> dagster_sensors = load_sensors(sensors_config, dagster_jobs)
    """
    if not sensors:
        return []

    dagster_sensors: list[DagsterSensorDefinition] = []

    for sensor_name, sensor_def in sensors.items():
        if sensor_def.job not in jobs:
            msg = (
                f"Sensor '{sensor_name}' references unknown job '{sensor_def.job}'. "
                f"Available jobs: {list(jobs.keys())}"
            )
            raise ValueError(msg)

        target_job = jobs[sensor_def.job]

        if sensor_def.type == "file_watcher":
            dagster_sensor = _create_file_watcher_sensor(sensor_name, sensor_def, target_job)
        elif sensor_def.type == "asset_sensor":
            dagster_sensor = _create_asset_sensor(sensor_name, sensor_def, target_job)
        elif sensor_def.type == "run_status":
            dagster_sensor = _create_run_status_sensor(sensor_name, sensor_def, target_job)
        elif sensor_def.type == "custom":
            dagster_sensor = _create_custom_sensor(sensor_name, sensor_def, target_job)
        else:
            msg = f"Sensor type '{sensor_def.type}' not yet implemented"
            raise NotImplementedError(msg)

        dagster_sensors.append(dagster_sensor)

    return dagster_sensors


def _create_file_watcher_sensor(
    name: str,
    sensor_def: SensorDefinition,
    job: DagsterJobDefinition,
) -> DagsterSensorDefinition:
    """Create a file watcher sensor."""
    import glob
    import os
    from pathlib import Path

    from dagster import RunRequest, SkipReason, sensor

    path = sensor_def.path
    pattern = sensor_def.pattern or "*"
    poll_interval = sensor_def.poll_interval_seconds

    @sensor(
        name=name,
        job=job,
        minimum_interval_seconds=poll_interval,
        description=f"File watcher sensor monitoring {path} for {pattern}",
    )
    def _file_watcher_sensor(context):
        search_path = Path(path) / pattern
        files = glob.glob(str(search_path))

        if not files:
            return SkipReason(f"No files matching {pattern} found in {path}")

        cursor = context.cursor or "0"
        last_mtime = float(cursor)

        new_files = []
        max_mtime = last_mtime

        for file_path in files:
            mtime = os.path.getmtime(file_path)
            if mtime > last_mtime:
                new_files.append(file_path)
                max_mtime = max(max_mtime, mtime)

        if not new_files:
            return SkipReason("No new files since last check")

        context.update_cursor(str(max_mtime))

        for file_path in new_files:
            yield RunRequest(
                run_key=file_path,
                run_config={},
                tags={"file_path": file_path},
            )

    return _file_watcher_sensor


def _create_asset_sensor(
    name: str,
    sensor_def: SensorDefinition,
    job: DagsterJobDefinition,
) -> DagsterSensorDefinition:
    """Create an asset sensor."""
    from dagster import AssetKey, RunRequest, asset_sensor

    watched_assets = [AssetKey(asset) for asset in sensor_def.watched_assets]
    poll_interval = sensor_def.poll_interval_seconds

    if len(watched_assets) != 1:
        msg = (
            f"Asset sensor '{name}' must watch exactly one asset. "
            f"Got {len(watched_assets)} assets: {sensor_def.watched_assets}"
        )
        raise ValueError(msg)

    @asset_sensor(
        name=name,
        asset_key=watched_assets[0],
        job=job,
        minimum_interval_seconds=poll_interval,
        description=f"Asset sensor watching {sensor_def.watched_assets[0]}",
    )
    def _asset_sensor(context, asset_event):
        yield RunRequest(
            run_key=context.cursor,
            run_config={},
        )

    return _asset_sensor


def _create_run_status_sensor(
    name: str,
    sensor_def: SensorDefinition,
    job: DagsterJobDefinition,
) -> DagsterSensorDefinition:
    """Create a run status sensor."""
    from dagster import DagsterRunStatus, RunRequest, sensor

    watched_jobs = sensor_def.watched_jobs
    status = sensor_def.status
    poll_interval = sensor_def.poll_interval_seconds

    status_map = {
        "success": DagsterRunStatus.SUCCESS,
        "failure": DagsterRunStatus.FAILURE,
        "started": DagsterRunStatus.STARTED,
        "canceled": DagsterRunStatus.CANCELED,
    }
    dagster_status = status_map.get(status.value)

    if not dagster_status:
        msg = f"Invalid run status: {status.value}"
        raise ValueError(msg)

    @sensor(
        name=name,
        job=job,
        run_status_sensor=dagster_status,
        minimum_interval_seconds=poll_interval,
        description=f"Run status sensor for {status.value} on {watched_jobs}",
    )
    def _run_status_sensor(context):
        if context.dagster_run.job_name in watched_jobs:
            yield RunRequest(
                run_key=f"run_{context.dagster_run.run_id}",
                run_config={},
            )

    return _run_status_sensor


def _create_custom_sensor(
    name: str,
    sensor_def: SensorDefinition,
    job: DagsterJobDefinition,
) -> DagsterSensorDefinition:
    """Create a custom sensor."""
    import importlib

    from dagster import sensor

    target_function = sensor_def.target_function
    args = sensor_def.args or {}
    poll_interval = sensor_def.poll_interval_seconds

    module_path, function_name = target_function.rsplit(".", 1)
    module = importlib.import_module(module_path)
    evaluation_fn = getattr(module, function_name)

    @sensor(
        name=name,
        job=job,
        minimum_interval_seconds=poll_interval,
        description=f"Custom sensor using {target_function}",
    )
    def _custom_sensor(context):
        return evaluation_fn(context, **args)

    return _custom_sensor
