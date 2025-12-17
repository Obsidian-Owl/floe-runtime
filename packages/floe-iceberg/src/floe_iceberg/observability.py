"""Structured logging and OpenTelemetry spans for floe-iceberg.

This module provides:
- Structured logging setup via structlog
- OpenTelemetry span helpers for table read/write operations
- Trace context propagation utilities
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

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
TRACER_NAME = "floe.iceberg"


def get_logger() -> BoundLogger:
    """Get the module logger, creating it if necessary.

    Returns:
        Configured structlog BoundLogger instance.

    Example:
        >>> logger = get_logger()
        >>> logger.info("table_created", table="bronze.customers")
    """
    global _logger
    if _logger is None:
        _logger = structlog.get_logger(TRACER_NAME)
    assert _logger is not None  # Type narrowing for mypy
    return _logger


def get_tracer() -> Tracer:
    """Get the OpenTelemetry tracer for floe-iceberg.

    Returns:
        OpenTelemetry Tracer instance.

    Example:
        >>> tracer = get_tracer()
        >>> with tracer.start_as_current_span("write_table"):
        ...     write_data()
    """
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(TRACER_NAME)
    return _tracer


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
        name: Span name (e.g., "append", "scan", "create_table").
        kind: Span kind (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER).
        attributes: Optional span attributes.
        log_start: If True, log span start.
        log_end: If True, log span end with duration.

    Yields:
        OpenTelemetry Span instance.

    Example:
        >>> with span("append", attributes={"table": "bronze.customers"}):
        ...     manager.append("bronze.customers", data)
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
def table_operation(
    operation: str,
    *,
    table: str | None = None,
    namespace: str | None = None,
    snapshot_id: int | None = None,
    num_rows: int | None = None,
    write_mode: str | None = None,
) -> Iterator[Span]:
    """Create a span for table operations with standard attributes.

    Convenience wrapper around span() with table-specific attributes.

    Args:
        operation: Operation name (e.g., "append", "scan", "create_table").
        table: Fully qualified table identifier.
        namespace: Table namespace.
        snapshot_id: Snapshot ID for time travel operations.
        num_rows: Number of rows affected.
        write_mode: Write mode (append, overwrite).

    Yields:
        OpenTelemetry Span instance.

    Example:
        >>> with table_operation("append", table="bronze.customers", num_rows=100):
        ...     manager.append("bronze.customers", data)
    """
    attrs: dict[str, Any] = {"iceberg.operation": operation}
    if table:
        attrs["iceberg.table"] = table
    if namespace:
        attrs["iceberg.namespace"] = namespace
    if snapshot_id is not None:
        attrs["iceberg.snapshot_id"] = snapshot_id
    if num_rows is not None:
        attrs["iceberg.num_rows"] = num_rows
    if write_mode:
        attrs["iceberg.write_mode"] = write_mode

    with span(f"iceberg.{operation}", kind=SpanKind.CLIENT, attributes=attrs) as s:
        yield s


@contextmanager
def dagster_asset_operation(
    operation: str,
    *,
    asset_key: str | None = None,
    partition_key: str | None = None,
    table: str | None = None,
) -> Iterator[Span]:
    """Create a span for Dagster asset operations.

    Args:
        operation: Operation name (e.g., "handle_output", "load_input").
        asset_key: Dagster asset key string.
        partition_key: Dagster partition key if partitioned.
        table: Mapped Iceberg table identifier.

    Yields:
        OpenTelemetry Span instance.

    Example:
        >>> with dagster_asset_operation(
        ...     "handle_output",
        ...     asset_key="customers",
        ...     table="bronze.customers"
        ... ):
        ...     io_manager.handle_output(context, data)
    """
    attrs: dict[str, Any] = {"dagster.operation": operation}
    if asset_key:
        attrs["dagster.asset_key"] = asset_key
    if partition_key:
        attrs["dagster.partition_key"] = partition_key
    if table:
        attrs["iceberg.table"] = table

    with span(f"dagster.{operation}", kind=SpanKind.INTERNAL, attributes=attrs) as s:
        yield s


def log_materialization(
    table: str,
    snapshot_id: int,
    num_rows: int,
    write_mode: str,
    schema_evolved: bool = False,
) -> None:
    """Log a successful materialization for observability.

    Args:
        table: Fully qualified table identifier.
        snapshot_id: Snapshot ID created by the write.
        num_rows: Number of rows written.
        write_mode: Write mode used (append, overwrite).
        schema_evolved: Whether schema evolution occurred.

    Example:
        >>> log_materialization(
        ...     table="bronze.customers",
        ...     snapshot_id=123456789,
        ...     num_rows=1000,
        ...     write_mode="append",
        ... )
    """
    logger = get_logger()
    logger.info(
        "asset_materialized",
        table=table,
        snapshot_id=snapshot_id,
        num_rows=num_rows,
        write_mode=write_mode,
        schema_evolved=schema_evolved,
    )
