"""Unit tests for structured logging with trace injection.

T070: [US4] Unit tests for structured logging with trace injection
"""

from __future__ import annotations

from io import StringIO
import json
import logging
from typing import Any

import pytest


class TestStructuredLogging:
    """Tests for structured logging configuration."""

    def test_configure_logging_returns_logger(self) -> None:
        """Test configure_logging returns a configured logger."""
        from floe_dagster.observability.logging import configure_logging

        logger = configure_logging("test_module")

        assert logger is not None
        assert logger.name == "test_module"

    def test_configure_logging_json_format(self) -> None:
        """Test logs are output in JSON format."""
        from floe_dagster.observability.logging import configure_logging

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)

        logger = configure_logging("test_json", handler=handler)
        logger.info("test message")

        output = stream.getvalue()

        # Should be valid JSON
        log_record = json.loads(output.strip())
        assert log_record["message"] == "test message"

    def test_log_includes_timestamp(self) -> None:
        """Test log records include ISO timestamp."""
        from floe_dagster.observability.logging import configure_logging

        stream = StringIO()
        handler = logging.StreamHandler(stream)

        logger = configure_logging("test_timestamp", handler=handler)
        logger.info("test")

        output = stream.getvalue()
        log_record = json.loads(output.strip())

        assert "timestamp" in log_record or "time" in log_record

    def test_log_includes_level(self) -> None:
        """Test log records include log level."""
        from floe_dagster.observability.logging import configure_logging

        stream = StringIO()
        handler = logging.StreamHandler(stream)

        logger = configure_logging("test_level", handler=handler)
        logger.warning("test warning")

        output = stream.getvalue()
        log_record = json.loads(output.strip())

        assert log_record.get("level") == "WARNING" or log_record.get("levelname") == "WARNING"

    def test_log_includes_logger_name(self) -> None:
        """Test log records include logger name."""
        from floe_dagster.observability.logging import configure_logging

        stream = StringIO()
        handler = logging.StreamHandler(stream)

        logger = configure_logging("my.module.name", handler=handler)
        logger.info("test")

        output = stream.getvalue()
        log_record = json.loads(output.strip())

        assert "my.module.name" in str(log_record)


class TestTraceContextInjection:
    """Tests for trace context injection into logs."""

    def test_log_includes_trace_id_when_span_active(self) -> None:
        """Test log records include trace_id when inside a span."""
        from floe_dagster.observability.config import TracingConfig
        from floe_dagster.observability.logging import configure_logging
        from floe_dagster.observability.tracing import TracingManager

        # Setup tracing (disabled for unit test, but structure works)
        config = TracingConfig()
        manager = TracingManager(config)
        manager.configure()

        stream = StringIO()
        handler = logging.StreamHandler(stream)

        logger = configure_logging("test_trace", handler=handler, tracing_manager=manager)

        with manager.start_span("test_operation"):
            logger.info("inside span")

        output = stream.getvalue()
        log_record = json.loads(output.strip())

        # Should have trace context fields
        assert "trace_id" in log_record or "traceId" in log_record

    def test_log_includes_span_id_when_span_active(self) -> None:
        """Test log records include span_id when inside a span."""
        from floe_dagster.observability.config import TracingConfig
        from floe_dagster.observability.logging import configure_logging
        from floe_dagster.observability.tracing import TracingManager

        config = TracingConfig()
        manager = TracingManager(config)
        manager.configure()

        stream = StringIO()
        handler = logging.StreamHandler(stream)

        logger = configure_logging("test_span", handler=handler, tracing_manager=manager)

        with manager.start_span("test_operation"):
            logger.info("inside span")

        output = stream.getvalue()
        log_record = json.loads(output.strip())

        assert "span_id" in log_record or "spanId" in log_record

    def test_log_without_active_span_has_empty_trace_context(self) -> None:
        """Test log records have empty trace context when no span active."""
        from floe_dagster.observability.config import TracingConfig
        from floe_dagster.observability.logging import configure_logging
        from floe_dagster.observability.tracing import TracingManager

        config = TracingConfig()
        manager = TracingManager(config)
        manager.configure()

        stream = StringIO()
        handler = logging.StreamHandler(stream)

        logger = configure_logging("test_no_span", handler=handler, tracing_manager=manager)

        # Log outside of span
        logger.info("outside span")

        output = stream.getvalue()
        log_record = json.loads(output.strip())

        # trace_id should be absent or invalid (all zeros)
        trace_id = log_record.get("trace_id") or log_record.get("traceId")
        if trace_id:
            assert trace_id == "0" * 32 or trace_id == ""


class TestStructuredLoggerWithContext:
    """Tests for structured logger with bound context."""

    def test_bind_context(self) -> None:
        """Test binding context to logger."""
        from floe_dagster.observability.logging import (
            BoundLogger,
            JSONFormatter,
            get_logger,
        )

        # Get a base logger and wrap it with BoundLogger
        base_logger = get_logger("test_bind")
        bound_logger = BoundLogger(base_logger, pipeline_id="abc123", model="stg_customers")

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())

        # Use the bound logger
        bound_logger.addHandler(handler)
        bound_logger.setLevel(logging.INFO)

        bound_logger.info("model started")

        output = stream.getvalue()

        # Should include bound context
        assert "abc123" in output or "pipeline_id" in output

    def test_add_extra_fields(self) -> None:
        """Test adding extra fields to log call."""
        from floe_dagster.observability.logging import configure_logging

        stream = StringIO()
        handler = logging.StreamHandler(stream)

        logger = configure_logging("test_extra", handler=handler)

        # Log with extra fields
        logger.info(
            "model completed",
            extra={"duration_ms": 1234, "rows_affected": 5000},
        )

        output = stream.getvalue()
        log_record = json.loads(output.strip())

        assert log_record.get("duration_ms") == 1234 or "1234" in output
        assert log_record.get("rows_affected") == 5000 or "5000" in output


class TestLogLevels:
    """Tests for different log levels."""

    @pytest.fixture
    def logger_with_stream(self) -> tuple[Any, StringIO]:
        """Create logger with captured stream."""
        from floe_dagster.observability.logging import configure_logging

        stream = StringIO()
        handler = logging.StreamHandler(stream)

        logger = configure_logging("test_levels", handler=handler)
        return logger, stream

    def test_debug_level(self, logger_with_stream: tuple[Any, StringIO]) -> None:
        """Test debug level logging."""
        logger, stream = logger_with_stream
        logger.setLevel(logging.DEBUG)

        logger.debug("debug message")

        output = stream.getvalue()
        assert "debug message" in output

    def test_info_level(self, logger_with_stream: tuple[Any, StringIO]) -> None:
        """Test info level logging."""
        logger, stream = logger_with_stream

        logger.info("info message")

        output = stream.getvalue()
        assert "info message" in output

    def test_warning_level(self, logger_with_stream: tuple[Any, StringIO]) -> None:
        """Test warning level logging."""
        logger, stream = logger_with_stream

        logger.warning("warning message")

        output = stream.getvalue()
        assert "warning message" in output

    def test_error_level(self, logger_with_stream: tuple[Any, StringIO]) -> None:
        """Test error level logging."""
        logger, stream = logger_with_stream

        logger.error("error message")

        output = stream.getvalue()
        assert "error message" in output

    def test_exception_includes_traceback(self, logger_with_stream: tuple[Any, StringIO]) -> None:
        """Test exception logging includes traceback."""
        logger, stream = logger_with_stream

        try:
            raise ValueError("test exception")
        except ValueError:
            logger.exception("caught exception")

        output = stream.getvalue()
        assert "ValueError" in output
        assert "test exception" in output
