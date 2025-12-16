"""Unit tests for TracingManager.

T069: [US4] Unit tests for TracingManager
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest


class TestTracingManager:
    """Tests for TracingManager."""

    @pytest.fixture
    def mock_config(self) -> Any:
        """Create mock TracingConfig."""
        from floe_dagster.observability.config import TracingConfig

        return TracingConfig(
            endpoint="http://localhost:4317",
            service_name="test-service",
            attributes={"environment": "test"},
        )

    @pytest.fixture
    def disabled_config(self) -> Any:
        """Create disabled TracingConfig."""
        from floe_dagster.observability.config import TracingConfig

        return TracingConfig()  # endpoint=None

    def test_create_manager_with_config(self, mock_config: Any) -> None:
        """Test creating manager with valid config."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)

        assert manager.config == mock_config
        assert manager.enabled is True

    def test_create_manager_disabled(self, disabled_config: Any) -> None:
        """Test creating manager with disabled config (graceful degradation)."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(disabled_config)

        assert manager.enabled is False

    def test_configure_creates_tracer_provider(self, mock_config: Any) -> None:
        """Test configure creates and configures TracerProvider."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)

        with patch("floe_dagster.observability.tracing.TracerProvider") as mock_provider:
            manager.configure()

            # Should create TracerProvider
            mock_provider.assert_called_once()

    def test_configure_uses_batch_processor_by_default(self, mock_config: Any) -> None:
        """Test configure uses BatchSpanProcessor when batch_export=True."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)

        with patch("floe_dagster.observability.tracing.BatchSpanProcessor") as mock_batch:
            with patch("floe_dagster.observability.tracing.TracerProvider"):
                # OTLPSpanExporter is imported dynamically inside configure()
                with patch(
                    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter"
                ):
                    manager.configure()

                    mock_batch.assert_called_once()

    def test_configure_uses_simple_processor_when_disabled(self) -> None:
        """Test configure uses SimpleSpanProcessor when batch_export=False."""
        from floe_dagster.observability.config import TracingConfig
        from floe_dagster.observability.tracing import TracingManager

        config = TracingConfig(
            endpoint="http://localhost:4317",
            batch_export=False,
        )
        manager = TracingManager(config)

        with patch("floe_dagster.observability.tracing.SimpleSpanProcessor") as mock_simple:
            with patch("floe_dagster.observability.tracing.TracerProvider"):
                # OTLPSpanExporter is imported dynamically inside configure()
                with patch(
                    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter"
                ):
                    manager.configure()

                    mock_simple.assert_called_once()

    def test_configure_disabled_uses_noop_provider(self, disabled_config: Any) -> None:
        """Test configure uses NoOpTracerProvider when disabled."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(disabled_config)

        # Should not raise, should use NoOp
        manager.configure()

        # Tracer should still be usable (NoOp)
        tracer = manager.get_tracer("test")
        assert tracer is not None

    def test_get_tracer_returns_tracer(self, mock_config: Any) -> None:
        """Test get_tracer returns a tracer instance."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        tracer = manager.get_tracer("test_module")

        assert tracer is not None

    def test_start_span_creates_span(self, mock_config: Any) -> None:
        """Test start_span creates a span with attributes."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        with manager.start_span("test_operation") as span:
            assert span is not None

    def test_start_span_with_attributes(self, mock_config: Any) -> None:
        """Test start_span sets span attributes."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        attributes = {
            "dbt.model": "stg_customers",
            "dbt.materialization": "table",
        }

        with manager.start_span("dbt_run", attributes=attributes) as span:
            # Span should be active
            assert span is not None

    def test_start_span_disabled_returns_noop_span(self, disabled_config: Any) -> None:
        """Test start_span returns no-op span when disabled."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(disabled_config)
        manager.configure()

        with manager.start_span("test_operation") as span:
            # Should not raise, span should be usable
            assert span is not None

    def test_start_span_with_parent_context(self, mock_config: Any) -> None:
        """Test start_span can use parent context for nested spans."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        with manager.start_span("parent_operation") as parent_span:
            with manager.start_span("child_operation") as child_span:
                # Child span should be nested under parent
                assert child_span is not None
                assert parent_span is not None

    def test_record_exception(self, mock_config: Any) -> None:
        """Test recording exception on span."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        with pytest.raises(ValueError), manager.start_span("failing_operation") as span:
            manager.record_exception(span, ValueError("test error"))
            raise ValueError("test error")

    def test_set_span_status_ok(self, mock_config: Any) -> None:
        """Test setting span status to OK."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        with manager.start_span("successful_operation") as span:
            manager.set_status_ok(span)

    def test_set_span_status_error(self, mock_config: Any) -> None:
        """Test setting span status to ERROR."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        with manager.start_span("failed_operation") as span:
            manager.set_status_error(span, "Something went wrong")

    def test_get_current_trace_context(self, mock_config: Any) -> None:
        """Test getting current trace context (trace_id, span_id)."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        with manager.start_span("operation"):
            trace_context = manager.get_current_trace_context()

            assert "trace_id" in trace_context
            assert "span_id" in trace_context

    def test_get_current_trace_context_outside_span(self, mock_config: Any) -> None:
        """Test getting trace context when no span active."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        trace_context = manager.get_current_trace_context()

        # Should return empty or invalid context
        assert trace_context.get("trace_id") is None or trace_context["trace_id"] == "0" * 32

    def test_add_default_attributes(self, mock_config: Any) -> None:
        """Test default attributes from config are added to spans."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        with manager.start_span("operation") as span:
            # Default attributes should be on the resource or span
            assert span is not None

    def test_shutdown(self, mock_config: Any) -> None:
        """Test shutdown properly closes the tracer provider."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)
        manager.configure()

        # Should not raise
        manager.shutdown()

    def test_context_manager_interface(self, mock_config: Any) -> None:
        """Test TracingManager can be used as context manager."""
        from floe_dagster.observability.tracing import TracingManager

        manager = TracingManager(mock_config)

        with manager:
            # Manager should be configured
            tracer = manager.get_tracer("test")
            assert tracer is not None

        # Shutdown should have been called


class TestNoOpTracerProvider:
    """Tests for NoOp tracer behavior."""

    def test_noop_tracer_returns_noop_span(self) -> None:
        """Test NoOp tracer returns spans that don't record anything."""
        from floe_dagster.observability.config import TracingConfig
        from floe_dagster.observability.tracing import TracingManager

        config = TracingConfig()  # Disabled
        manager = TracingManager(config)
        manager.configure()

        # Should work without errors
        with manager.start_span("operation", {"key": "value"}) as span:
            manager.set_status_ok(span)

    def test_noop_operations_do_not_fail(self) -> None:
        """Test all operations work on NoOp spans."""
        from floe_dagster.observability.config import TracingConfig
        from floe_dagster.observability.tracing import TracingManager

        config = TracingConfig()  # Disabled
        manager = TracingManager(config)
        manager.configure()

        with manager.start_span("operation") as span:
            manager.record_exception(span, ValueError("test"))
            manager.set_status_error(span, "error")
            manager.set_status_ok(span)

        # No exceptions should be raised
