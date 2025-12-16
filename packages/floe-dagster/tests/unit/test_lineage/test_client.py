"""Unit tests for OpenLineageEmitter.

T052: [US3] Unit tests for OpenLineageEmitter
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestOpenLineageEmitter:
    """Tests for OpenLineageEmitter client."""

    @pytest.fixture
    def mock_config(self) -> Any:
        """Create mock OpenLineageConfig."""
        from floe_dagster.lineage.config import OpenLineageConfig

        return OpenLineageConfig(
            endpoint="http://localhost:5000/api/v1/lineage",
            namespace="test",
            producer="test-producer",
        )

    @pytest.fixture
    def disabled_config(self) -> Any:
        """Create disabled OpenLineageConfig."""
        from floe_dagster.lineage.config import OpenLineageConfig

        return OpenLineageConfig()  # endpoint=None

    def test_create_emitter_with_config(self, mock_config: Any) -> None:
        """Test creating emitter with valid config."""
        from floe_dagster.lineage.client import OpenLineageEmitter

        emitter = OpenLineageEmitter(mock_config)

        assert emitter.config == mock_config
        assert emitter.enabled is True

    def test_create_emitter_disabled(self, disabled_config: Any) -> None:
        """Test creating emitter with disabled config (graceful degradation)."""
        from floe_dagster.lineage.client import OpenLineageEmitter

        emitter = OpenLineageEmitter(disabled_config)

        assert emitter.enabled is False

    def test_emit_start_creates_start_event(self, mock_config: Any) -> None:
        """Test emit_start creates and sends START event."""
        from floe_dagster.lineage.client import OpenLineageEmitter
        from floe_dagster.lineage.events import LineageEventType

        emitter = OpenLineageEmitter(mock_config)

        with patch.object(emitter, "_send_event") as mock_send:
            run_id = emitter.emit_start(
                job_name="stg_customers",
                inputs=[],
                outputs=[],
            )

            mock_send.assert_called_once()
            event = mock_send.call_args[0][0]
            assert event.event_type == LineageEventType.START
            assert event.job_name == "stg_customers"
            assert event.run_id == run_id

    def test_emit_complete_creates_complete_event(self, mock_config: Any) -> None:
        """Test emit_complete creates and sends COMPLETE event."""
        from floe_dagster.lineage.client import OpenLineageEmitter
        from floe_dagster.lineage.events import LineageEventType

        emitter = OpenLineageEmitter(mock_config)

        with patch.object(emitter, "_send_event") as mock_send:
            emitter.emit_complete(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_name="stg_customers",
                inputs=[],
                outputs=[],
            )

            mock_send.assert_called_once()
            event = mock_send.call_args[0][0]
            assert event.event_type == LineageEventType.COMPLETE
            assert event.run_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_emit_fail_creates_fail_event(self, mock_config: Any) -> None:
        """Test emit_fail creates and sends FAIL event with error message."""
        from floe_dagster.lineage.client import OpenLineageEmitter
        from floe_dagster.lineage.events import LineageEventType

        emitter = OpenLineageEmitter(mock_config)

        with patch.object(emitter, "_send_event") as mock_send:
            emitter.emit_fail(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_name="fct_orders",
                error_message="Compilation Error: Invalid SQL",
            )

            mock_send.assert_called_once()
            event = mock_send.call_args[0][0]
            assert event.event_type == LineageEventType.FAIL
            assert event.error_message == "Compilation Error: Invalid SQL"

    def test_emit_start_disabled_is_noop(self, disabled_config: Any) -> None:
        """Test emit_start is no-op when disabled (graceful degradation)."""
        from floe_dagster.lineage.client import OpenLineageEmitter

        emitter = OpenLineageEmitter(disabled_config)

        with patch.object(emitter, "_send_event") as mock_send:
            run_id = emitter.emit_start(
                job_name="stg_customers",
                inputs=[],
                outputs=[],
            )

            # Should not send anything
            mock_send.assert_not_called()
            # Should still return a run_id for tracking
            assert run_id is not None

    def test_emit_complete_disabled_is_noop(self, disabled_config: Any) -> None:
        """Test emit_complete is no-op when disabled."""
        from floe_dagster.lineage.client import OpenLineageEmitter

        emitter = OpenLineageEmitter(disabled_config)

        with patch.object(emitter, "_send_event") as mock_send:
            emitter.emit_complete(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_name="stg_customers",
                inputs=[],
                outputs=[],
            )

            mock_send.assert_not_called()

    def test_emit_fail_disabled_is_noop(self, disabled_config: Any) -> None:
        """Test emit_fail is no-op when disabled."""
        from floe_dagster.lineage.client import OpenLineageEmitter

        emitter = OpenLineageEmitter(disabled_config)

        with patch.object(emitter, "_send_event") as mock_send:
            emitter.emit_fail(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_name="fct_orders",
                error_message="Some error",
            )

            mock_send.assert_not_called()

    def test_emit_start_with_datasets(self, mock_config: Any) -> None:
        """Test emit_start includes input and output datasets."""
        from floe_dagster.lineage.client import OpenLineageEmitter
        from floe_dagster.lineage.events import LineageDataset

        emitter = OpenLineageEmitter(mock_config)

        input_datasets = [
            LineageDataset(
                namespace="snowflake://account",
                name="raw.public.customers",
            )
        ]
        output_datasets = [
            LineageDataset(
                namespace="snowflake://account",
                name="analytics.staging.stg_customers",
            )
        ]

        with patch.object(emitter, "_send_event") as mock_send:
            emitter.emit_start(
                job_name="stg_customers",
                inputs=input_datasets,
                outputs=output_datasets,
            )

            event = mock_send.call_args[0][0]
            assert len(event.inputs) == 1
            assert len(event.outputs) == 1

    def test_emit_complete_with_facets(self, mock_config: Any) -> None:
        """Test emit_complete can include schema facets."""
        from floe_dagster.lineage.client import OpenLineageEmitter
        from floe_dagster.lineage.events import LineageDataset

        emitter = OpenLineageEmitter(mock_config)

        output_datasets = [
            LineageDataset(
                namespace="snowflake://account",
                name="analytics.staging.stg_customers",
                facets={
                    "schema": {
                        "fields": [
                            {"name": "id", "type": "INTEGER"},
                            {"name": "email", "type": "VARCHAR"},
                        ]
                    }
                },
            )
        ]

        with patch.object(emitter, "_send_event") as mock_send:
            emitter.emit_complete(
                run_id="550e8400-e29b-41d4-a716-446655440000",
                job_name="stg_customers",
                inputs=[],
                outputs=output_datasets,
            )

            event = mock_send.call_args[0][0]
            assert "schema" in event.outputs[0].facets

    def test_send_event_handles_connection_error(self, mock_config: Any) -> None:
        """Test _send_event handles connection errors gracefully."""
        from floe_dagster.lineage.client import OpenLineageEmitter
        from floe_dagster.lineage.events import LineageEvent, LineageEventType

        emitter = OpenLineageEmitter(mock_config)

        event = LineageEvent(
            event_type=LineageEventType.START,
            run_id="550e8400-e29b-41d4-a716-446655440000",
            job_namespace="test",
            job_name="test_model",
        )

        # Simulate connection error
        with patch("httpx.post") as mock_post:
            mock_post.side_effect = Exception("Connection refused")

            # Should not raise - graceful degradation
            emitter._send_event(event)

    def test_generate_run_id_returns_uuid(self, mock_config: Any) -> None:
        """Test _generate_run_id returns valid UUID string."""
        from floe_dagster.lineage.client import OpenLineageEmitter
        import uuid

        emitter = OpenLineageEmitter(mock_config)

        run_id = emitter._generate_run_id()

        # Should be a valid UUID
        uuid.UUID(run_id)  # Will raise if invalid

    def test_uses_config_namespace(self, mock_config: Any) -> None:
        """Test emitter uses namespace from config."""
        from floe_dagster.lineage.client import OpenLineageEmitter

        emitter = OpenLineageEmitter(mock_config)

        with patch.object(emitter, "_send_event") as mock_send:
            emitter.emit_start(
                job_name="test_model",
                inputs=[],
                outputs=[],
            )

            event = mock_send.call_args[0][0]
            assert event.job_namespace == "test"

    def test_context_manager_usage(self, mock_config: Any) -> None:
        """Test emitter can be used as context manager for run tracking."""
        from floe_dagster.lineage.client import OpenLineageEmitter

        emitter = OpenLineageEmitter(mock_config)

        with patch.object(emitter, "_send_event") as mock_send:
            with emitter.run_context("test_model", inputs=[], outputs=[]) as run_id:
                # START should be emitted
                assert mock_send.call_count == 1
                start_event = mock_send.call_args_list[0][0][0]
                assert start_event.event_type.value == "START"
                assert run_id is not None

            # COMPLETE should be emitted on clean exit
            assert mock_send.call_count == 2
            complete_event = mock_send.call_args_list[1][0][0]
            assert complete_event.event_type.value == "COMPLETE"

    def test_context_manager_emits_fail_on_exception(self, mock_config: Any) -> None:
        """Test context manager emits FAIL event on exception."""
        from floe_dagster.lineage.client import OpenLineageEmitter

        emitter = OpenLineageEmitter(mock_config)

        with patch.object(emitter, "_send_event") as mock_send:
            with pytest.raises(ValueError):
                with emitter.run_context("test_model", inputs=[], outputs=[]):
                    raise ValueError("Something went wrong")

            # FAIL should be emitted on exception
            assert mock_send.call_count == 2
            fail_event = mock_send.call_args_list[1][0][0]
            assert fail_event.event_type.value == "FAIL"
            assert "Something went wrong" in fail_event.error_message
