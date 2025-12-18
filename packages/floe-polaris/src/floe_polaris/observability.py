"""Structured logging and OpenTelemetry spans for floe-polaris.

This module provides:
- Structured logging setup via structlog
- OpenTelemetry span helpers for catalog operations
- Trace context propagation utilities
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import structlog
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

if TYPE_CHECKING:
    from opentelemetry.trace import Span, Tracer
    from structlog.stdlib import BoundLogger

# Module-level logger and tracer
_logger: BoundLogger | None = None
_tracer: Tracer | None = None

# Tracer name for OpenTelemetry
TRACER_NAME = "floe.polaris"


def get_logger() -> BoundLogger:
    """Get the module logger, creating it if necessary.

    Returns:
        Configured structlog BoundLogger instance.

    Example:
        >>> logger = get_logger()
        >>> logger.info("catalog_connected", uri="http://localhost:8181")
    """
    global _logger
    if _logger is None:
        _logger = structlog.get_logger(TRACER_NAME)
    assert _logger is not None  # Type narrowing for mypy
    return _logger


def get_tracer() -> Tracer:
    """Get the OpenTelemetry tracer for floe-polaris.

    Returns:
        OpenTelemetry Tracer instance.

    Example:
        >>> tracer = get_tracer()
        >>> with tracer.start_as_current_span("my_operation"):
        ...     do_work()
    """
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(TRACER_NAME)
    return _tracer


def configure_logging(
    *,
    log_level: str = "INFO",
    json_format: bool = True,
    add_timestamp: bool = True,
) -> None:
    """Configure structured logging for floe-polaris.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: If True, output JSON format. If False, output human-readable.
        add_timestamp: If True, add ISO timestamp to log entries.

    Example:
        >>> configure_logging(log_level="DEBUG", json_format=False)
    """
    import logging

    processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if add_timestamp:
        processors.insert(0, structlog.processors.TimeStamper(fmt="iso"))

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set log level for the stdlib handler
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
    )


@contextmanager
def span(
    name: str,
    *,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
    log_start: bool = True,
    log_end: bool = True,
) -> Iterator[Span]:
    """Create an OpenTelemetry span with structured logging.

    Args:
        name: Span name (e.g., "create_namespace", "load_table").
        kind: Span kind (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER).
        attributes: Optional span attributes.
        log_start: If True, log span start.
        log_end: If True, log span end with duration.

    Yields:
        OpenTelemetry Span instance.

    Example:
        >>> with span("create_namespace", attributes={"namespace": "bronze"}):
        ...     catalog.create_namespace("bronze")
    """
    tracer = get_tracer()
    logger = get_logger()
    attrs = attributes or {}

    with tracer.start_as_current_span(name, kind=kind, attributes=attrs) as s:
        if log_start:
            logger.debug(f"{name}_started", **attrs)
        try:
            yield s
            s.set_status(Status(StatusCode.OK))
            if log_end:
                logger.info(f"{name}_completed", **attrs)
        except Exception as exc:
            s.set_status(Status(StatusCode.ERROR, str(exc)))
            s.record_exception(exc)
            logger.error(f"{name}_failed", error=str(exc), **attrs)
            raise


@contextmanager
def catalog_operation(
    operation: str,
    *,
    uri: str | None = None,
    warehouse: str | None = None,
    namespace: str | None = None,
    table: str | None = None,
) -> Iterator[Span]:
    """Create a span for catalog operations with standard attributes.

    Convenience wrapper around span() with catalog-specific attributes.

    Args:
        operation: Operation name (e.g., "list_namespaces", "load_table").
        uri: Catalog URI.
        warehouse: Warehouse name.
        namespace: Namespace being operated on.
        table: Table being operated on.

    Yields:
        OpenTelemetry Span instance.

    Example:
        >>> with catalog_operation("load_table", namespace="bronze", table="customers"):
        ...     catalog.load_table("bronze.customers")
    """
    attrs: dict[str, Any] = {"catalog.operation": operation}
    if uri:
        attrs["catalog.uri"] = uri
    if warehouse:
        attrs["catalog.warehouse"] = warehouse
    if namespace:
        attrs["catalog.namespace"] = namespace
    if table:
        attrs["catalog.table"] = table

    with span(f"catalog.{operation}", kind=SpanKind.CLIENT, attributes=attrs) as s:
        yield s


def log_retry_attempt(
    operation: str,
    attempt: int,
    max_attempts: int,
    wait_seconds: float,
    error: str,
) -> None:
    """Log a retry attempt for observability.

    Args:
        operation: Operation being retried.
        attempt: Current attempt number.
        max_attempts: Maximum attempts configured.
        wait_seconds: Time waiting before retry.
        error: Error message that triggered retry.

    Example:
        >>> log_retry_attempt("load_table", 2, 3, 1.5, "Connection timeout")
    """
    logger = get_logger()
    logger.warning(
        "operation_retry",
        operation=operation,
        attempt=attempt,
        max_attempts=max_attempts,
        wait_seconds=wait_seconds,
        error=error,
    )
