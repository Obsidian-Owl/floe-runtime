"""Unit tests for OpenLineage event emitter.

T074: Unit test QueryLineageEvent model validates required fields
T075: Unit test emit_start creates START event with correct facets
T076: Unit test emit_complete creates COMPLETE event
T077: Unit test emit_fail sanitizes error message
T078: Unit test emission failure logs warning and continues
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from floe_cube.lineage import (
    MAX_ERROR_LENGTH,
    EventType,
    QueryLineageEmitter,
    QueryLineageEvent,
    sanitize_error_message,
)


class TestQueryLineageEventModel:
    """T074: Unit test QueryLineageEvent model validates required fields."""

    def test_valid_event_all_fields(self) -> None:
        """Test creating a valid event with all fields."""
        event = QueryLineageEvent(
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_name="cube.orders.query",
            namespace="floe-cube",
            event_type=EventType.START,
            event_time=datetime.now(tz=timezone.utc),
            inputs=["orders"],
            sql="SELECT * FROM orders",
        )

        assert event.run_id == "550e8400-e29b-41d4-a716-446655440000"
        assert event.job_name == "cube.orders.query"
        assert event.namespace == "floe-cube"
        assert event.event_type == EventType.START
        assert event.inputs == ["orders"]
        assert event.sql == "SELECT * FROM orders"

    def test_valid_event_minimal_fields(self) -> None:
        """Test creating a valid event with minimal fields."""
        event = QueryLineageEvent(
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_name="cube.orders.query",
            event_type=EventType.COMPLETE,
            event_time=datetime.now(tz=timezone.utc),
            inputs=["orders"],
        )

        assert event.namespace == "floe-cube"  # Default value
        assert event.sql is None
        assert event.row_count is None
        assert event.error is None

    def test_invalid_run_id_not_uuid(self) -> None:
        """Test that invalid run_id (not UUID) raises error."""
        with pytest.raises(ValueError, match="run_id must be a valid UUID"):
            QueryLineageEvent(
                run_id="not-a-uuid",
                job_name="cube.orders.query",
                event_type=EventType.START,
                event_time=datetime.now(tz=timezone.utc),
                inputs=["orders"],
            )

    def test_invalid_job_name_format(self) -> None:
        """Test that invalid job_name format raises error."""
        with pytest.raises(ValueError, match="String should match pattern"):
            QueryLineageEvent(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_name="invalid-job-name",
                event_type=EventType.START,
                event_time=datetime.now(tz=timezone.utc),
                inputs=["orders"],
            )

    def test_job_name_must_match_pattern(self) -> None:
        """Test that job_name must match cube.{name}.query pattern."""
        valid_names = [
            "cube.orders.query",
            "cube.customers.query",
            "cube.order_items.query",
            "cube.ABC123.query",
        ]

        for job_name in valid_names:
            event = QueryLineageEvent(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_name=job_name,
                event_type=EventType.START,
                event_time=datetime.now(tz=timezone.utc),
                inputs=[],
            )
            assert event.job_name == job_name

    def test_event_time_must_be_utc(self) -> None:
        """Test that event_time must be timezone-aware."""
        with pytest.raises(ValueError, match="event_time must be timezone-aware"):
            QueryLineageEvent(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_name="cube.orders.query",
                event_type=EventType.START,
                event_time=datetime.now(),  # No timezone
                inputs=["orders"],
            )

    def test_row_count_must_be_non_negative(self) -> None:
        """Test that row_count must be >= 0."""
        with pytest.raises(ValueError, match="greater than or equal"):
            QueryLineageEvent(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_name="cube.orders.query",
                event_type=EventType.COMPLETE,
                event_time=datetime.now(tz=timezone.utc),
                inputs=["orders"],
                row_count=-1,
            )

    def test_error_max_length(self) -> None:
        """Test that error is truncated to max length."""
        long_error = "x" * 1000
        event = QueryLineageEvent(
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_name="cube.orders.query",
            event_type=EventType.FAIL,
            event_time=datetime.now(tz=timezone.utc),
            inputs=["orders"],
            error=long_error,
        )

        assert event.error is not None
        assert len(event.error) <= MAX_ERROR_LENGTH

    def test_event_type_values(self) -> None:
        """Test all event type values."""
        assert EventType.START.value == "START"
        assert EventType.COMPLETE.value == "COMPLETE"
        assert EventType.FAIL.value == "FAIL"


class TestSanitizeErrorMessage:
    """T077: Unit test emit_fail sanitizes error message."""

    def test_sanitizes_password(self) -> None:
        """Test that passwords are sanitized."""
        message = "Connection failed: password='secret123'"
        result = sanitize_error_message(message)
        assert "secret123" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_token(self) -> None:
        """Test that tokens are sanitized."""
        message = "Auth failed: token='abc123xyz'"
        result = sanitize_error_message(message)
        assert "abc123xyz" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_api_key(self) -> None:
        """Test that API keys are sanitized."""
        message = "Request failed: api_key='my-secret-key'"
        result = sanitize_error_message(message)
        assert "my-secret-key" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_authorization_header(self) -> None:
        """Test that authorization headers are sanitized."""
        message = "Auth failed: Authorization: Bearer eyJhbGciOiJIUzI1NiJ9"
        result = sanitize_error_message(message)
        assert "eyJhbGciOiJIUzI1NiJ9" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_filter_values(self) -> None:
        """Test that WHERE clause filter values are sanitized."""
        message = "Query error: WHERE organization_id='org_12345'"
        result = sanitize_error_message(message)
        assert "org_12345" not in result
        assert "[REDACTED]" in result

    def test_truncates_long_messages(self) -> None:
        """Test that long messages are truncated."""
        long_message = "Error: " + "x" * 1000
        result = sanitize_error_message(long_message)
        assert len(result) <= MAX_ERROR_LENGTH
        assert result.endswith("...")

    def test_preserves_safe_messages(self) -> None:
        """Test that safe messages are preserved."""
        message = "Connection timeout after 30 seconds"
        result = sanitize_error_message(message)
        assert result == message


class TestQueryLineageEmitter:
    """Tests for QueryLineageEmitter class."""

    def test_emitter_disabled_when_no_endpoint(self) -> None:
        """Test that emitter is disabled when endpoint is None."""
        emitter = QueryLineageEmitter(endpoint=None)
        assert not emitter.enabled

    def test_emitter_disabled_explicitly(self) -> None:
        """Test that emitter can be disabled explicitly."""
        emitter = QueryLineageEmitter(
            endpoint="http://localhost:5000",
            enabled=False,
        )
        assert not emitter.enabled

    def test_emit_start_returns_run_id(self) -> None:
        """T075: Test emit_start creates START event with correct facets."""
        emitter = QueryLineageEmitter(endpoint=None)  # Disabled
        run_id = emitter.emit_start(cube_name="orders")

        # Should still return a valid UUID even when disabled
        import uuid

        uuid.UUID(run_id)  # Should not raise

    def test_emit_start_uses_provided_run_id(self) -> None:
        """Test emit_start uses provided run_id."""
        emitter = QueryLineageEmitter(endpoint=None)
        expected_run_id = "550e8400-e29b-41d4-a716-446655440000"
        run_id = emitter.emit_start(cube_name="orders", run_id=expected_run_id)

        assert run_id == expected_run_id

    def test_emit_complete_when_disabled(self) -> None:
        """T076: Test emit_complete returns gracefully when disabled."""
        emitter = QueryLineageEmitter(endpoint=None)
        # Should not raise
        emitter.emit_complete(
            run_id="550e8400-e29b-41d4-a716-446655440000",
            cube_name="orders",
            row_count=100,
        )

    def test_emit_fail_when_disabled(self) -> None:
        """Test emit_fail returns gracefully when disabled."""
        emitter = QueryLineageEmitter(endpoint=None)
        # Should not raise
        emitter.emit_fail(
            run_id="550e8400-e29b-41d4-a716-446655440000",
            cube_name="orders",
            error="Something went wrong",
        )

    def test_emit_fail_with_exception(self) -> None:
        """Test emit_fail accepts Exception objects."""
        emitter = QueryLineageEmitter(endpoint=None)
        # Should not raise
        emitter.emit_fail(
            run_id="550e8400-e29b-41d4-a716-446655440000",
            cube_name="orders",
            error=ValueError("Query failed"),
        )


class TestQueryLineageEmitterWithMockClient:
    """Tests for QueryLineageEmitter with mock OpenLineage client."""

    @pytest.fixture
    def emitter_with_mock(self) -> QueryLineageEmitter:
        """Create an emitter with mock _emit_event_internal."""
        # Create emitter without actual client (endpoint=None disables it)
        emitter = QueryLineageEmitter(
            endpoint=None,
            namespace="test-namespace",
        )
        # Force enable it for testing
        emitter.enabled = True
        return emitter

    def test_emit_start_calls_client(self, emitter_with_mock: QueryLineageEmitter) -> None:
        """T075: Test emit_start creates START event with correct facets."""
        with patch.object(emitter_with_mock, "_emit_event") as mock_emit:
            run_id = emitter_with_mock.emit_start(
                cube_name="orders",
                inputs=["orders", "customers"],
                sql="SELECT * FROM orders",
            )

            mock_emit.assert_called_once()
            event = mock_emit.call_args[0][0]

            assert event.event_type == EventType.START
            assert event.job_name == "cube.orders.query"
            assert event.inputs == ["orders", "customers"]
            assert event.sql == "SELECT * FROM orders"
            assert event.run_id == run_id

    def test_emit_complete_calls_client(self, emitter_with_mock: QueryLineageEmitter) -> None:
        """T076: Test emit_complete creates COMPLETE event."""
        with patch.object(emitter_with_mock, "_emit_event") as mock_emit:
            emitter_with_mock.emit_complete(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                cube_name="orders",
                row_count=100,
            )

            mock_emit.assert_called_once()
            event = mock_emit.call_args[0][0]

            assert event.event_type == EventType.COMPLETE
            assert event.job_name == "cube.orders.query"
            assert event.row_count == 100

    def test_emit_fail_calls_client_with_sanitized_error(
        self, emitter_with_mock: QueryLineageEmitter
    ) -> None:
        """T077: Test emit_fail sanitizes error message."""
        with patch.object(emitter_with_mock, "_emit_event") as mock_emit:
            emitter_with_mock.emit_fail(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                cube_name="orders",
                error="Connection failed: password='secret123'",
            )

            mock_emit.assert_called_once()
            event = mock_emit.call_args[0][0]

            assert event.event_type == EventType.FAIL
            assert event.error is not None
            assert "secret123" not in event.error
            assert "[REDACTED]" in event.error


class TestEmissionFailureLogsWarning:
    """T078: Unit test emission failure logs warning and continues."""

    def test_emission_failure_logs_warning(self) -> None:
        """Test that emission failure logs warning and continues."""
        emitter = QueryLineageEmitter(endpoint=None)
        emitter.enabled = True
        emitter._client = MagicMock()

        # Make _emit_event_internal raise an exception
        with (
            patch.object(
                emitter,
                "_emit_event_internal",
                side_effect=Exception("Connection refused"),
            ),
            patch("floe_cube.lineage.logger") as mock_logger,
        ):
            # Should not raise - just log warning
            emitter.emit_start(cube_name="orders")

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[0][0] == "openlineage_emission_failed"
            assert "Connection refused" in call_args[1]["error"]

    def test_emission_failure_returns_run_id(self) -> None:
        """Test that emission failure still returns run_id."""
        import uuid

        emitter = QueryLineageEmitter(endpoint=None)
        emitter.enabled = True
        emitter._client = MagicMock()

        with (
            patch.object(
                emitter,
                "_emit_event_internal",
                side_effect=Exception("Connection refused"),
            ),
            patch("floe_cube.lineage.logger"),
        ):
            result_run_id = emitter.emit_start(cube_name="orders")
            # Should still return a valid UUID
            uuid.UUID(result_run_id)  # Should not raise

    def test_emit_complete_failure_does_not_raise(self) -> None:
        """Test that emit_complete failure does not raise."""
        emitter = QueryLineageEmitter(endpoint=None)
        emitter.enabled = True
        emitter._client = MagicMock()

        with (
            patch.object(
                emitter,
                "_emit_event_internal",
                side_effect=Exception("Connection refused"),
            ),
            patch("floe_cube.lineage.logger"),
        ):
            # Should not raise
            emitter.emit_complete(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                cube_name="orders",
                row_count=100,
            )

    def test_emit_fail_failure_does_not_raise(self) -> None:
        """Test that emit_fail failure does not raise."""
        emitter = QueryLineageEmitter(endpoint=None)
        emitter.enabled = True
        emitter._client = MagicMock()

        with (
            patch.object(
                emitter,
                "_emit_event_internal",
                side_effect=Exception("Connection refused"),
            ),
            patch("floe_cube.lineage.logger"),
        ):
            # Should not raise
            emitter.emit_fail(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                cube_name="orders",
                error="Query failed",
            )
