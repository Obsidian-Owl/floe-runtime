"""Partition loader for converting PartitionDefinition to Dagster partitions.

T022: [010-orchestration-auto-discovery] Create partition loader
Covers: 010-FR-015 through 010-FR-017

This module converts PartitionDefinition from floe.yaml into Dagster partition definitions,
supporting time-window, static, multi, and dynamic partitioning strategies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dagster import PartitionsDefinition as DagsterPartitionsDefinition

    from floe_core.schemas.partition_definition import PartitionDefinition


def load_partitions(
    partitions: dict[str, PartitionDefinition],
) -> dict[str, DagsterPartitionsDefinition]:
    """Load partitions from PartitionDefinition dictionary.

    Converts PartitionDefinition configurations from floe.yaml into Dagster partition
    definitions, supporting time-window, static, multi, and dynamic partitions.

    Args:
        partitions: Dictionary of partition name to PartitionDefinition.

    Returns:
        Dictionary of partition name to Dagster PartitionsDefinition.

    Example:
        >>> from floe_core.schemas.partition_definition import TimeWindowPartition
        >>> partitions_config = {
        ...     "daily": TimeWindowPartition(
        ...         type="time_window",
        ...         start="2024-01-01",
        ...         cron_schedule="0 0 * * *",
        ...     )
        ... }
        >>> dagster_partitions = load_partitions(partitions_config)
    """
    if not partitions:
        return {}

    dagster_partitions: dict[str, DagsterPartitionsDefinition] = {}

    for partition_name, partition_def in partitions.items():
        if partition_def.type == "time_window":
            dagster_partition = _create_time_window_partition(partition_def)
        elif partition_def.type == "static":
            dagster_partition = _create_static_partition(partition_def)
        elif partition_def.type == "multi":
            dagster_partition = _create_multi_partition(partition_def)
        elif partition_def.type == "dynamic":
            dagster_partition = _create_dynamic_partition(partition_name, partition_def)
        else:
            msg = f"Unknown partition type: {partition_def.type}"
            raise ValueError(msg)

        dagster_partitions[partition_name] = dagster_partition

    return dagster_partitions


def _create_time_window_partition(
    partition_def: PartitionDefinition,
) -> DagsterPartitionsDefinition:
    """Create Dagster time window partition from TimeWindowPartition.

    Args:
        partition_def: TimeWindowPartition definition.

    Returns:
        Dagster TimeWindowPartitionsDefinition.
    """
    from dagster import TimeWindowPartitionsDefinition

    kwargs: dict[str, Any] = {
        "cron_schedule": partition_def.cron_schedule,
        "start": partition_def.start,
        "timezone": partition_def.timezone,
        "fmt": partition_def.fmt or "%Y-%m-%d",
    }

    if partition_def.end:
        kwargs["end"] = partition_def.end

    return TimeWindowPartitionsDefinition(**kwargs)


def _create_static_partition(
    partition_def: PartitionDefinition,
) -> DagsterPartitionsDefinition:
    """Create Dagster static partition from StaticPartition.

    Args:
        partition_def: StaticPartition definition.

    Returns:
        Dagster StaticPartitionsDefinition.
    """
    from dagster import StaticPartitionsDefinition

    return StaticPartitionsDefinition(partition_def.partition_keys)


def _create_multi_partition(
    partition_def: PartitionDefinition,
) -> DagsterPartitionsDefinition:
    """Create Dagster multi partition from MultiPartition.

    Args:
        partition_def: MultiPartition definition.

    Returns:
        Dagster MultiPartitionsDefinition.
    """
    from dagster import MultiPartitionsDefinition

    sub_partitions = load_partitions(partition_def.partitions)

    return MultiPartitionsDefinition(sub_partitions)


def _create_dynamic_partition(
    partition_name: str,
    partition_def: PartitionDefinition,
) -> DagsterPartitionsDefinition:
    """Create Dagster dynamic partition from DynamicPartition.

    Args:
        partition_name: Name of the partition.
        partition_def: DynamicPartition definition.

    Returns:
        Dagster DynamicPartitionsDefinition.
    """
    from dagster import DynamicPartitionsDefinition

    return DynamicPartitionsDefinition(name=partition_name)
