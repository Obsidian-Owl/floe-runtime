"""Structured logging with trace context injection.

T075: [US4] Implement structured logging with trace_id/span_id injection
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from opentelemetry import trace

if TYPE_CHECKING:
    from floe_dagster.observability.tracing import TracingManager


class JSONFormatter(logging.Formatter):
    """JSON log formatter with trace context injection.

    Formats log records as JSON with automatic injection of trace_id
    and span_id from the current OpenTelemetry context.

    Example output:
        {
            "timestamp": "2024-01-15T10:30:00.000Z",
            "level": "INFO",
            "logger": "floe_dagster.assets",
            "message": "Model execution started",
            "trace_id": "abc123...",
            "span_id": "def456...",
            "model": "stg_customers"
        }
    """

    def __init__(self, tracing_manager: "TracingManager | None" = None) -> None:
        """Initialize JSONFormatter.

        Args:
            tracing_manager: Optional tracing manager for context injection.
        """
        super().__init__()
        self._tracing_manager = tracing_manager

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format.

        Returns:
            JSON-formatted string.
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject trace context
        trace_context = self._get_trace_context()
        log_data["trace_id"] = trace_context.get("trace_id", "")
        log_data["span_id"] = trace_context.get("span_id", "")

        # Add extra fields from record
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in (
                    "name",
                    "msg",
                    "args",
                    "created",
                    "filename",
                    "funcName",
                    "levelname",
                    "levelno",
                    "lineno",
                    "module",
                    "msecs",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "stack_info",
                    "exc_info",
                    "exc_text",
                    "thread",
                    "threadName",
                    "message",
                ):
                    # Include custom extra fields
                    if not key.startswith("_") and value is not None:
                        log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

    def _get_trace_context(self) -> dict[str, str]:
        """Get current trace context.

        Returns:
            Dictionary with trace_id and span_id.
        """
        if self._tracing_manager:
            return self._tracing_manager.get_current_trace_context()

        # Fallback to direct OTel API
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context()

        if span_context.is_valid:
            return {
                "trace_id": format(span_context.trace_id, "032x"),
                "span_id": format(span_context.span_id, "016x"),
            }

        return {
            "trace_id": "",
            "span_id": "",
        }


def configure_logging(
    name: str,
    handler: logging.Handler | None = None,
    level: int = logging.INFO,
    tracing_manager: "TracingManager | None" = None,
) -> logging.Logger:
    """Configure structured logging with JSON format.

    Sets up a logger with JSON formatting and optional trace context
    injection from a TracingManager.

    Args:
        name: Logger name.
        handler: Optional custom handler. Uses StreamHandler if None.
        level: Log level. Defaults to INFO.
        tracing_manager: Optional tracing manager for context injection.

    Returns:
        Configured logger.

    Example:
        >>> logger = configure_logging("my_module")
        >>> logger.info("Hello", extra={"user_id": "123"})
        {"timestamp": "...", "level": "INFO", "message": "Hello", "user_id": "123"}
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create handler if not provided
    if handler is None:
        handler = logging.StreamHandler()

    # Set JSON formatter
    formatter = JSONFormatter(tracing_manager=tracing_manager)
    handler.setFormatter(formatter)

    # Add handler
    logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    This is a simple wrapper for logging.getLogger that can be
    extended with additional configuration in the future.

    Args:
        name: Logger name.

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


class BoundLogger:
    """Logger with bound context.

    Wraps a standard logger and automatically includes bound
    context in all log calls.

    Example:
        >>> logger = get_logger("my_module")
        >>> bound = BoundLogger(logger, pipeline_id="abc123")
        >>> bound.info("Started")  # Includes pipeline_id in output
    """

    def __init__(self, logger: logging.Logger, **context: Any) -> None:
        """Initialize BoundLogger.

        Args:
            logger: Underlying logger.
            **context: Context to bind to all log calls.
        """
        self._logger = logger
        self._context = context

    def bind(self, **context: Any) -> "BoundLogger":
        """Create new BoundLogger with additional context.

        Args:
            **context: Additional context to bind.

        Returns:
            New BoundLogger with merged context.
        """
        merged = {**self._context, **context}
        return BoundLogger(self._logger, **merged)

    def _log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Internal log method with context injection.

        Args:
            level: Log level.
            msg: Message format string.
            *args: Message format args.
            **kwargs: Additional kwargs including 'extra'.
        """
        extra = kwargs.pop("extra", {})
        extra.update(self._context)
        kwargs["extra"] = extra
        self._logger.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback."""
        kwargs["exc_info"] = True
        self._log(logging.ERROR, msg, *args, **kwargs)

    # Delegate handler management
    def addHandler(self, handler: logging.Handler) -> None:
        """Add handler to underlying logger."""
        self._logger.addHandler(handler)

    def setLevel(self, level: int) -> None:
        """Set level on underlying logger."""
        self._logger.setLevel(level)
