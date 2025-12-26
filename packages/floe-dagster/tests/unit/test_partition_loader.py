"""Unit tests for partition loader.

T025: [010-orchestration-auto-discovery] partition loader tests
Covers: 010-FR-015 through 010-FR-017

Tests the load_partitions function that converts PartitionDefinition to Dagster partitions.
"""

from __future__ import annotations

from dagster import (
    DynamicPartitionsDefinition,
    MultiPartitionsDefinition,
    StaticPartitionsDefinition,
    TimeWindowPartitionsDefinition,
)
import pytest

from floe_core.schemas.partition_definition import (
    DynamicPartition,
    MultiPartition,
    StaticPartition,
    TimeWindowPartition,
)


class TestLoadPartitions:
    """Tests for load_partitions function."""

    def test_load_partitions_with_empty_dict(self) -> None:
        """load_partitions should return empty dict for empty input."""
        from floe_dagster.loaders.partition_loader import load_partitions

        result = load_partitions({})

        assert result == {}

    def test_load_partitions_with_time_window(self) -> None:
        """load_partitions should create Dagster time window partition."""
        from floe_dagster.loaders.partition_loader import load_partitions

        partitions = {
            "daily": TimeWindowPartition(
                type="time_window",
                start="2024-01-01",
                cron_schedule="0 0 * * *",
                timezone="UTC",
            )
        }

        result = load_partitions(partitions)

        assert len(result) == 1
        assert "daily" in result
        assert isinstance(result["daily"], TimeWindowPartitionsDefinition)

    def test_load_partitions_with_static(self) -> None:
        """load_partitions should create Dagster static partition."""
        from floe_dagster.loaders.partition_loader import load_partitions

        partitions = {
            "regions": StaticPartition(
                type="static",
                partition_keys=["us-east", "us-west", "eu-central"],
            )
        }

        result = load_partitions(partitions)

        assert len(result) == 1
        assert "regions" in result
        assert isinstance(result["regions"], StaticPartitionsDefinition)

    def test_load_partitions_with_dynamic(self) -> None:
        """load_partitions should create Dagster dynamic partition."""
        from floe_dagster.loaders.partition_loader import load_partitions

        partitions = {
            "customers": DynamicPartition(
                type="dynamic",
                fn="demo.partitions.get_active_customers",
            )
        }

        result = load_partitions(partitions)

        assert len(result) == 1
        assert "customers" in result
        assert isinstance(result["customers"], DynamicPartitionsDefinition)

    def test_load_partitions_with_multi(self) -> None:
        """load_partitions should create Dagster multi partition."""
        from floe_dagster.loaders.partition_loader import load_partitions

        partitions = {
            "date_region": MultiPartition(
                type="multi",
                partitions={
                    "date": TimeWindowPartition(
                        start="2024-01-01",
                        cron_schedule="0 0 * * *",
                    ),
                    "region": StaticPartition(
                        partition_keys=["us", "eu", "ap"],
                    ),
                },
            )
        }

        result = load_partitions(partitions)

        assert len(result) == 1
        assert "date_region" in result
        assert isinstance(result["date_region"], MultiPartitionsDefinition)

    def test_load_partitions_with_multiple_partitions(self) -> None:
        """load_partitions should handle multiple partitions."""
        from floe_dagster.loaders.partition_loader import load_partitions

        partitions = {
            "daily": TimeWindowPartition(
                start="2024-01-01",
                cron_schedule="0 0 * * *",
            ),
            "regions": StaticPartition(
                partition_keys=["us", "eu"],
            ),
        }

        result = load_partitions(partitions)

        assert len(result) == 2
        assert "daily" in result
        assert "regions" in result

    def test_load_partitions_raises_on_unknown_type(self) -> None:
        """load_partitions should raise ValueError for unknown partition type."""
        from unittest.mock import MagicMock

        from floe_dagster.loaders.partition_loader import load_partitions

        partitions = {"invalid": MagicMock(type="unknown_type")}

        with pytest.raises(ValueError) as exc_info:
            load_partitions(partitions)

        assert "Unknown partition type" in str(exc_info.value)


class TestCreateTimeWindowPartition:
    """Tests for _create_time_window_partition helper."""

    def test_create_time_window_partition_with_minimal_config(self) -> None:
        """_create_time_window_partition should work with minimal config."""
        from floe_dagster.loaders.partition_loader import _create_time_window_partition

        partition_def = TimeWindowPartition(
            type="time_window",
            start="2024-01-01",
            cron_schedule="0 0 * * *",
        )

        result = _create_time_window_partition(partition_def)

        assert isinstance(result, TimeWindowPartitionsDefinition)

    def test_create_time_window_partition_with_end_date(self) -> None:
        """_create_time_window_partition should include end date."""
        from floe_dagster.loaders.partition_loader import _create_time_window_partition

        partition_def = TimeWindowPartition(
            type="time_window",
            start="2024-01-01",
            end="2024-12-31",
            cron_schedule="0 0 * * *",
        )

        result = _create_time_window_partition(partition_def)

        assert isinstance(result, TimeWindowPartitionsDefinition)

    def test_create_time_window_partition_with_custom_timezone(self) -> None:
        """_create_time_window_partition should use custom timezone."""
        from floe_dagster.loaders.partition_loader import _create_time_window_partition

        partition_def = TimeWindowPartition(
            type="time_window",
            start="2024-01-01",
            cron_schedule="0 0 * * *",
            timezone="America/New_York",
        )

        result = _create_time_window_partition(partition_def)

        assert isinstance(result, TimeWindowPartitionsDefinition)

    def test_create_time_window_partition_with_custom_format(self) -> None:
        """_create_time_window_partition should use custom format for partition keys."""
        from floe_dagster.loaders.partition_loader import _create_time_window_partition

        partition_def = TimeWindowPartition(
            type="time_window",
            start="2024-01-01",
            cron_schedule="0 0 * * *",
            fmt="%Y-%m-%d",
        )

        result = _create_time_window_partition(partition_def)

        assert isinstance(result, TimeWindowPartitionsDefinition)


class TestCreateStaticPartition:
    """Tests for _create_static_partition helper."""

    def test_create_static_partition_with_keys(self) -> None:
        """_create_static_partition should create partition with keys."""
        from floe_dagster.loaders.partition_loader import _create_static_partition

        partition_def = StaticPartition(
            type="static",
            partition_keys=["key1", "key2", "key3"],
        )

        result = _create_static_partition(partition_def)

        assert isinstance(result, StaticPartitionsDefinition)

    def test_create_static_partition_with_single_key(self) -> None:
        """_create_static_partition should work with single key."""
        from floe_dagster.loaders.partition_loader import _create_static_partition

        partition_def = StaticPartition(
            type="static",
            partition_keys=["only_key"],
        )

        result = _create_static_partition(partition_def)

        assert isinstance(result, StaticPartitionsDefinition)


class TestCreateMultiPartition:
    """Tests for _create_multi_partition helper."""

    def test_create_multi_partition_with_sub_partitions(self) -> None:
        """_create_multi_partition should create multi partition."""
        from floe_dagster.loaders.partition_loader import _create_multi_partition

        partition_def = MultiPartition(
            type="multi",
            partitions={
                "date": TimeWindowPartition(
                    start="2024-01-01",
                    cron_schedule="0 0 * * *",
                ),
                "region": StaticPartition(
                    partition_keys=["us", "eu"],
                ),
            },
        )

        result = _create_multi_partition(partition_def)

        assert isinstance(result, MultiPartitionsDefinition)


class TestCreateDynamicPartition:
    """Tests for _create_dynamic_partition helper."""

    def test_create_dynamic_partition_with_name(self) -> None:
        """_create_dynamic_partition should create dynamic partition with name."""
        from floe_dagster.loaders.partition_loader import _create_dynamic_partition

        partition_def = DynamicPartition(
            type="dynamic",
            fn="demo.partitions.get_customers",
        )

        result = _create_dynamic_partition("customers", partition_def)

        assert isinstance(result, DynamicPartitionsDefinition)
        assert result.name == "customers"

    def test_create_dynamic_partition_without_fn(self) -> None:
        """_create_dynamic_partition should work without fn."""
        from floe_dagster.loaders.partition_loader import _create_dynamic_partition

        partition_def = DynamicPartition(
            type="dynamic",
        )

        result = _create_dynamic_partition("dynamic_name", partition_def)

        assert isinstance(result, DynamicPartitionsDefinition)
        assert result.name == "dynamic_name"
