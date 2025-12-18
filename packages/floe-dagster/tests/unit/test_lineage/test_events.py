"""Unit tests for LineageEvent and LineageDataset models.

T049: [US3] Unit tests for LineageEvent model
T050: [US3] Unit tests for LineageDataset model
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import ValidationError
import pytest


class TestLineageEventType:
    """Tests for LineageEventType enum."""

    def test_event_types_defined(self) -> None:
        """Test all OpenLineage run event types are defined."""
        from floe_dagster.lineage.events import LineageEventType

        assert LineageEventType.START == "START"
        assert LineageEventType.RUNNING == "RUNNING"
        assert LineageEventType.COMPLETE == "COMPLETE"
        assert LineageEventType.FAIL == "FAIL"
        assert LineageEventType.ABORT == "ABORT"

    def test_event_type_is_string_enum(self) -> None:
        """Test LineageEventType is a string enum for serialization."""
        from floe_dagster.lineage.events import LineageEventType

        # Should be usable as string via .value
        event_type = LineageEventType.START
        assert event_type.value == "START"
        # String comparison works via inheritance from str
        assert event_type == "START"


class TestLineageDataset:
    """Tests for LineageDataset model (T050)."""

    def test_create_minimal_dataset(self) -> None:
        """Test creating dataset with required fields only."""
        from floe_dagster.lineage.events import LineageDataset

        dataset = LineageDataset(
            namespace="snowflake://account",
            name="database.schema.table",
        )

        assert dataset.namespace == "snowflake://account"
        assert dataset.name == "database.schema.table"
        assert dataset.facets == {}

    def test_create_dataset_with_facets(self) -> None:
        """Test creating dataset with facets."""
        from floe_dagster.lineage.events import LineageDataset

        facets = {
            "schema": {
                "fields": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "email", "type": "VARCHAR"},
                ]
            },
            "dataSource": {
                "name": "production",
                "uri": "snowflake://account",
            },
        }

        dataset = LineageDataset(
            namespace="snowflake://account",
            name="analytics.staging.users",
            facets=facets,
        )

        assert dataset.facets == facets
        assert "schema" in dataset.facets
        assert "dataSource" in dataset.facets

    def test_dataset_is_frozen(self) -> None:
        """Test LineageDataset is immutable."""
        from floe_dagster.lineage.events import LineageDataset

        dataset = LineageDataset(
            namespace="snowflake://account",
            name="database.schema.table",
        )

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            dataset.name = "different.table"  # type: ignore[misc]

    def test_dataset_requires_namespace(self) -> None:
        """Test namespace is required."""
        from floe_dagster.lineage.events import LineageDataset

        with pytest.raises(ValidationError) as exc_info:
            LineageDataset(name="database.schema.table")  # type: ignore[call-arg]

        assert "namespace" in str(exc_info.value)

    def test_dataset_requires_name(self) -> None:
        """Test name is required."""
        from floe_dagster.lineage.events import LineageDataset

        with pytest.raises(ValidationError) as exc_info:
            LineageDataset(namespace="snowflake://account")  # type: ignore[call-arg]

        assert "name" in str(exc_info.value)

    def test_dataset_forbids_extra_fields(self) -> None:
        """Test extra fields are rejected."""
        from floe_dagster.lineage.events import LineageDataset

        with pytest.raises(ValidationError) as exc_info:
            LineageDataset(
                namespace="snowflake://account",
                name="database.schema.table",
                extra_field="not allowed",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()


class TestLineageEvent:
    """Tests for LineageEvent model (T049)."""

    def test_create_start_event(self) -> None:
        """Test creating a START event."""
        from floe_dagster.lineage.events import LineageEvent, LineageEventType

        event = LineageEvent(
            event_type=LineageEventType.START,
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_namespace="floe",
            job_name="stg_customers",
        )

        assert event.event_type == LineageEventType.START
        assert event.run_id == "550e8400-e29b-41d4-a716-446655440000"
        assert event.job_namespace == "floe"
        assert event.job_name == "stg_customers"
        assert event.inputs == []
        assert event.outputs == []
        assert event.error_message is None

    def test_create_complete_event_with_datasets(self) -> None:
        """Test creating a COMPLETE event with input/output datasets."""
        from floe_dagster.lineage.events import (
            LineageDataset,
            LineageEvent,
            LineageEventType,
        )

        input_dataset = LineageDataset(
            namespace="snowflake://account",
            name="raw.public.customers",
        )
        output_dataset = LineageDataset(
            namespace="snowflake://account",
            name="analytics.staging.stg_customers",
        )

        event = LineageEvent(
            event_type=LineageEventType.COMPLETE,
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_namespace="floe",
            job_name="stg_customers",
            inputs=[input_dataset],
            outputs=[output_dataset],
        )

        assert event.event_type == LineageEventType.COMPLETE
        assert len(event.inputs) == 1
        assert len(event.outputs) == 1
        assert event.inputs[0].name == "raw.public.customers"
        assert event.outputs[0].name == "analytics.staging.stg_customers"

    def test_create_fail_event_with_error(self) -> None:
        """Test creating a FAIL event with error message."""
        from floe_dagster.lineage.events import LineageEvent, LineageEventType

        event = LineageEvent(
            event_type=LineageEventType.FAIL,
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_namespace="floe",
            job_name="fct_orders",
            error_message="Compilation Error: Syntax error near 'SELECT'",
        )

        assert event.event_type == LineageEventType.FAIL
        assert event.error_message == "Compilation Error: Syntax error near 'SELECT'"

    def test_event_time_defaults_to_now(self) -> None:
        """Test event_time defaults to current time."""
        from floe_dagster.lineage.events import LineageEvent, LineageEventType

        before = datetime.now(timezone.utc)

        event = LineageEvent(
            event_type=LineageEventType.START,
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_namespace="floe",
            job_name="test_model",
        )

        after = datetime.now(timezone.utc)

        # Event time should be between before and after
        assert before <= event.event_time <= after

    def test_event_with_explicit_time(self) -> None:
        """Test creating event with explicit timestamp."""
        from floe_dagster.lineage.events import LineageEvent, LineageEventType

        event_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        event = LineageEvent(
            event_type=LineageEventType.COMPLETE,
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_namespace="floe",
            job_name="test_model",
            event_time=event_time,
        )

        assert event.event_time == event_time

    def test_event_is_frozen(self) -> None:
        """Test LineageEvent is immutable."""
        from floe_dagster.lineage.events import LineageEvent, LineageEventType

        event = LineageEvent(
            event_type=LineageEventType.START,
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_namespace="floe",
            job_name="test_model",
        )

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            event.event_type = LineageEventType.COMPLETE  # type: ignore[misc]

    def test_event_forbids_extra_fields(self) -> None:
        """Test extra fields are rejected."""
        from floe_dagster.lineage.events import LineageEvent, LineageEventType

        with pytest.raises(ValidationError) as exc_info:
            LineageEvent(
                event_type=LineageEventType.START,
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_namespace="floe",
                job_name="test_model",
                custom_field="not allowed",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()

    def test_event_requires_event_type(self) -> None:
        """Test event_type is required."""
        from floe_dagster.lineage.events import LineageEvent

        with pytest.raises(ValidationError) as exc_info:
            LineageEvent(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_namespace="floe",
                job_name="test_model",
            )  # type: ignore[call-arg]

        assert "event_type" in str(exc_info.value)

    def test_event_requires_run_id(self) -> None:
        """Test run_id is required."""
        from floe_dagster.lineage.events import LineageEvent, LineageEventType

        with pytest.raises(ValidationError) as exc_info:
            LineageEvent(
                event_type=LineageEventType.START,
                job_namespace="floe",
                job_name="test_model",
            )  # type: ignore[call-arg]

        assert "run_id" in str(exc_info.value)

    def test_to_openlineage_dict(self) -> None:
        """Test conversion to OpenLineage-compatible dictionary."""
        from floe_dagster.lineage.events import (
            LineageDataset,
            LineageEvent,
            LineageEventType,
        )

        input_dataset = LineageDataset(
            namespace="snowflake://account",
            name="raw.public.customers",
        )
        output_dataset = LineageDataset(
            namespace="snowflake://account",
            name="analytics.staging.stg_customers",
        )

        event = LineageEvent(
            event_type=LineageEventType.COMPLETE,
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_namespace="floe",
            job_name="stg_customers",
            inputs=[input_dataset],
            outputs=[output_dataset],
        )

        openlineage_dict = event.to_openlineage_dict()

        # Should have all required OpenLineage fields
        assert openlineage_dict["eventType"] == "COMPLETE"
        assert openlineage_dict["run"]["runId"] == "550e8400-e29b-41d4-a716-446655440000"
        assert openlineage_dict["job"]["namespace"] == "floe"
        assert openlineage_dict["job"]["name"] == "stg_customers"
        assert "eventTime" in openlineage_dict
        assert len(openlineage_dict["inputs"]) == 1
        assert len(openlineage_dict["outputs"]) == 1
