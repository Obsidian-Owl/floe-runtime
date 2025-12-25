"""Unit tests for partition definition schemas.

T014: [010-orchestration-auto-discovery] Partition definition validation tests
Covers: 010-FR-011 through 010-FR-016
Tests Pydantic v2 schema validation for partition definitions with discriminated union.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from floe_core.schemas.partition_definition import (
    CRON_PATTERN,
    DATE_PATTERN,
    FUNCTION_PATH_PATTERN,
    IDENTIFIER_PATTERN,
    DynamicPartition,
    MultiPartition,
    PartitionDefinition,
    StaticPartition,
    TimeWindowPartition,
)


class TestTimeWindowPartition:
    """Tests for TimeWindowPartition schema validation."""

    def test_time_window_partition_minimal_valid(self) -> None:
        """TimeWindowPartition should accept minimal valid configuration."""
        partition = TimeWindowPartition(
            type="time_window",
            start="2024-01-01",
            cron_schedule="0 0 * * *",
        )

        assert partition.type == "time_window"
        assert partition.start == "2024-01-01"
        assert partition.cron_schedule == "0 0 * * *"
        assert partition.timezone == "UTC"
        assert partition.end is None
        assert partition.fmt is None

    def test_time_window_partition_full_valid(self) -> None:
        """TimeWindowPartition should accept all optional fields."""
        partition = TimeWindowPartition(
            type="time_window",
            start="2024-01-01",
            cron_schedule="0 0 * * *",
            timezone="America/New_York",
            end="2024-12-31",
            fmt="%Y-%m-%d",
        )

        assert partition.type == "time_window"
        assert partition.start == "2024-01-01"
        assert partition.cron_schedule == "0 0 * * *"
        assert partition.timezone == "America/New_York"
        assert partition.end == "2024-12-31"
        assert partition.fmt == "%Y-%m-%d"

    def test_time_window_partition_requires_start(self) -> None:
        """TimeWindowPartition should require start date."""
        with pytest.raises(ValidationError) as exc_info:
            TimeWindowPartition(  # type: ignore[call-arg]
                type="time_window",
                cron_schedule="0 0 * * *",
            )

        assert "start" in str(exc_info.value)

    def test_time_window_partition_requires_cron_schedule(self) -> None:
        """TimeWindowPartition should require cron_schedule."""
        with pytest.raises(ValidationError) as exc_info:
            TimeWindowPartition(  # type: ignore[call-arg]
                type="time_window",
                start="2024-01-01",
            )

        assert "cron_schedule" in str(exc_info.value)

    def test_time_window_partition_start_must_match_date_pattern(self) -> None:
        """TimeWindowPartition start must match YYYY-MM-DD format."""
        with pytest.raises(ValidationError) as exc_info:
            TimeWindowPartition(
                type="time_window",
                start="01-01-2024",
                cron_schedule="0 0 * * *",
            )

        assert "start" in str(exc_info.value)

    def test_time_window_partition_end_must_match_date_pattern(self) -> None:
        """TimeWindowPartition end must match YYYY-MM-DD format."""
        with pytest.raises(ValidationError) as exc_info:
            TimeWindowPartition(
                type="time_window",
                start="2024-01-01",
                cron_schedule="0 0 * * *",
                end="12/31/2024",
            )

        assert "end" in str(exc_info.value)

    def test_time_window_partition_cron_must_match_pattern(self) -> None:
        """TimeWindowPartition cron_schedule must match cron pattern."""
        with pytest.raises(ValidationError) as exc_info:
            TimeWindowPartition(
                type="time_window",
                start="2024-01-01",
                cron_schedule="invalid",
            )

        assert "cron_schedule" in str(exc_info.value)

    def test_time_window_partition_is_frozen(self) -> None:
        """TimeWindowPartition should be immutable (frozen)."""
        partition = TimeWindowPartition(
            type="time_window",
            start="2024-01-01",
            cron_schedule="0 0 * * *",
        )

        with pytest.raises(ValidationError):
            partition.start = "2024-02-01"  # type: ignore[misc]

    def test_time_window_partition_forbids_extra_fields(self) -> None:
        """TimeWindowPartition should forbid extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            TimeWindowPartition(
                type="time_window",
                start="2024-01-01",
                cron_schedule="0 0 * * *",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "unknown_field" in str(exc_info.value)


class TestStaticPartition:
    """Tests for StaticPartition schema validation."""

    def test_static_partition_valid(self) -> None:
        """StaticPartition should accept valid partition keys."""
        partition = StaticPartition(
            type="static",
            partition_keys=["us-east", "us-west", "eu-central"],
        )

        assert partition.type == "static"
        assert len(partition.partition_keys) == 3
        assert "us-east" in partition.partition_keys

    def test_static_partition_requires_partition_keys(self) -> None:
        """StaticPartition should require partition_keys."""
        with pytest.raises(ValidationError) as exc_info:
            StaticPartition(type="static")  # type: ignore[call-arg]

        assert "partition_keys" in str(exc_info.value)

    def test_static_partition_requires_non_empty_list(self) -> None:
        """StaticPartition should require at least one partition key."""
        with pytest.raises(ValidationError) as exc_info:
            StaticPartition(type="static", partition_keys=[])

        assert "partition_keys" in str(exc_info.value)

    def test_static_partition_requires_unique_keys(self) -> None:
        """StaticPartition should require unique partition keys."""
        with pytest.raises(ValueError) as exc_info:
            StaticPartition(
                type="static",
                partition_keys=["us-east", "us-west", "us-east"],
            )

        assert "unique" in str(exc_info.value).lower()

    def test_static_partition_forbids_empty_keys(self) -> None:
        """StaticPartition should forbid empty partition keys."""
        with pytest.raises(ValueError) as exc_info:
            StaticPartition(
                type="static",
                partition_keys=["us-east", "", "eu-central"],
            )

        assert "empty" in str(exc_info.value).lower()

    def test_static_partition_is_frozen(self) -> None:
        """StaticPartition should be immutable (frozen)."""
        partition = StaticPartition(
            type="static",
            partition_keys=["us-east", "us-west"],
        )

        with pytest.raises(ValidationError):
            partition.partition_keys = ["new-key"]  # type: ignore[misc]

    def test_static_partition_forbids_extra_fields(self) -> None:
        """StaticPartition should forbid extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            StaticPartition(
                type="static",
                partition_keys=["us-east"],
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "unknown_field" in str(exc_info.value)


class TestMultiPartition:
    """Tests for MultiPartition schema validation."""

    def test_multi_partition_valid(self) -> None:
        """MultiPartition should accept valid sub-partition definitions."""
        partition = MultiPartition(
            type="multi",
            partitions={
                "date": TimeWindowPartition(
                    type="time_window",
                    start="2024-01-01",
                    cron_schedule="0 0 * * *",
                ),
                "region": StaticPartition(
                    type="static",
                    partition_keys=["us", "eu", "ap"],
                ),
            },
        )

        assert partition.type == "multi"
        assert len(partition.partitions) == 2
        assert "date" in partition.partitions
        assert "region" in partition.partitions

    def test_multi_partition_requires_partitions(self) -> None:
        """MultiPartition should require partitions."""
        with pytest.raises(ValidationError) as exc_info:
            MultiPartition(type="multi")  # type: ignore[call-arg]

        assert "partitions" in str(exc_info.value)

    def test_multi_partition_requires_non_empty_dict(self) -> None:
        """MultiPartition should require at least one sub-partition."""
        with pytest.raises(ValidationError) as exc_info:
            MultiPartition(type="multi", partitions={})

        assert "partitions" in str(exc_info.value)

    def test_multi_partition_keys_must_be_identifiers(self) -> None:
        """MultiPartition partition keys must be valid identifiers."""
        with pytest.raises(ValueError) as exc_info:
            MultiPartition(
                type="multi",
                partitions={
                    "invalid-key": StaticPartition(
                        type="static",
                        partition_keys=["a", "b"],
                    )
                },
            )

        assert "invalid-key" in str(exc_info.value) or "identifier" in str(exc_info.value).lower()

    def test_multi_partition_is_frozen(self) -> None:
        """MultiPartition should be immutable (frozen)."""
        partition = MultiPartition(
            type="multi",
            partitions={
                "region": StaticPartition(
                    type="static",
                    partition_keys=["us", "eu"],
                )
            },
        )

        with pytest.raises(ValidationError):
            partition.partitions = {}  # type: ignore[misc]

    def test_multi_partition_forbids_extra_fields(self) -> None:
        """MultiPartition should forbid extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            MultiPartition(
                type="multi",
                partitions={
                    "region": StaticPartition(
                        type="static",
                        partition_keys=["us"],
                    )
                },
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "unknown_field" in str(exc_info.value)


class TestDynamicPartition:
    """Tests for DynamicPartition schema validation."""

    def test_dynamic_partition_valid(self) -> None:
        """DynamicPartition should accept valid function reference."""
        partition = DynamicPartition(
            type="dynamic",
            fn="demo.partitions.get_active_customers",
        )

        assert partition.type == "dynamic"
        assert partition.fn == "demo.partitions.get_active_customers"

    def test_dynamic_partition_fn_optional(self) -> None:
        """DynamicPartition should allow fn to be None."""
        partition = DynamicPartition(type="dynamic")

        assert partition.type == "dynamic"
        assert partition.fn is None

    def test_dynamic_partition_fn_must_match_pattern(self) -> None:
        """DynamicPartition fn must match module.function pattern."""
        with pytest.raises(ValidationError) as exc_info:
            DynamicPartition(
                type="dynamic",
                fn="invalid-function-name",
            )

        assert "fn" in str(exc_info.value)

    def test_dynamic_partition_is_frozen(self) -> None:
        """DynamicPartition should be immutable (frozen)."""
        partition = DynamicPartition(type="dynamic")

        with pytest.raises(ValidationError):
            partition.fn = "new.function"  # type: ignore[misc]

    def test_dynamic_partition_forbids_extra_fields(self) -> None:
        """DynamicPartition should forbid extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            DynamicPartition(
                type="dynamic",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "unknown_field" in str(exc_info.value)


class TestPartitionDefinitionUnion:
    """Tests for PartitionDefinition discriminated union."""

    def test_partition_definition_discriminates_on_type(self) -> None:
        """PartitionDefinition should discriminate on type field."""
        time_window: PartitionDefinition = TimeWindowPartition(
            type="time_window",
            start="2024-01-01",
            cron_schedule="0 0 * * *",
        )
        static: PartitionDefinition = StaticPartition(
            type="static",
            partition_keys=["a", "b"],
        )
        multi: PartitionDefinition = MultiPartition(
            type="multi",
            partitions={
                "region": StaticPartition(
                    type="static",
                    partition_keys=["us"],
                )
            },
        )
        dynamic: PartitionDefinition = DynamicPartition(type="dynamic")

        assert isinstance(time_window, TimeWindowPartition)
        assert isinstance(static, StaticPartition)
        assert isinstance(multi, MultiPartition)
        assert isinstance(dynamic, DynamicPartition)


class TestPatternConstants:
    """Tests for validation pattern constants."""

    def test_identifier_pattern_matches_valid_identifiers(self) -> None:
        """IDENTIFIER_PATTERN should match valid Python identifiers."""
        import re

        assert re.match(IDENTIFIER_PATTERN, "my_partition")
        assert re.match(IDENTIFIER_PATTERN, "DailyPartition")
        assert re.match(IDENTIFIER_PATTERN, "partition123")
        assert not re.match(IDENTIFIER_PATTERN, "123partition")
        assert not re.match(IDENTIFIER_PATTERN, "my-partition")
        assert not re.match(IDENTIFIER_PATTERN, "my.partition")

    def test_date_pattern_matches_valid_dates(self) -> None:
        """DATE_PATTERN should match YYYY-MM-DD format."""
        import re

        assert re.match(DATE_PATTERN, "2024-01-01")
        assert re.match(DATE_PATTERN, "2024-12-31")
        assert not re.match(DATE_PATTERN, "01-01-2024")
        assert not re.match(DATE_PATTERN, "2024/01/01")
        assert not re.match(DATE_PATTERN, "2024-1-1")

    def test_cron_pattern_matches_valid_cron(self) -> None:
        """CRON_PATTERN should match valid cron expressions."""
        import re

        assert re.match(CRON_PATTERN, "0 0 * * *")
        assert re.match(CRON_PATTERN, "0 0 1 * *")
        assert re.match(CRON_PATTERN, "*/15 * * * *")
        assert not re.match(CRON_PATTERN, "invalid")
        assert not re.match(CRON_PATTERN, "0 0")

    def test_function_path_pattern_matches_valid_functions(self) -> None:
        """FUNCTION_PATH_PATTERN should match module.function references."""
        import re

        assert re.match(FUNCTION_PATH_PATTERN, "demo.partitions.get_customers")
        assert re.match(FUNCTION_PATH_PATTERN, "my_package.utils.fn")
        assert not re.match(FUNCTION_PATH_PATTERN, "invalid-function")
        assert not re.match(FUNCTION_PATH_PATTERN, "demo.partitions.")
        assert not re.match(FUNCTION_PATH_PATTERN, "no_module")
