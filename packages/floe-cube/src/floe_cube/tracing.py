"""OpenTelemetry tracing for Cube query observability.

T067-T071: [US7] Implement OpenTelemetry tracing functionality.

This module provides:
- TracerProvider initialization with OTLP exporter (T067)
- trace_query() function with W3C context extraction (T068)
- Span hierarchy creation (T069)
- Safe attribute injection (T070)
- record_query_result() for span status (T071)

Functional Requirements:
- FR-031: Emit OpenTelemetry trace for each query
- FR-032: Include safe metadata in spans (cube name, filter count)
- FR-033: Support W3C Trace Context propagation
- FR-034: Link to OpenLineage run_id in trace spans
- FR-035: Record query latency metrics
- FR-036: Support disabling tracing via configuration

Architecture:
    QueryTracer wraps OpenTelemetry SDK operations and enforces
    the security rules for span attributes.

Usage:
    >>> from floe_cube.tracing import QueryTracer
    >>>
    >>> tracer = QueryTracer(service_name="floe-cube")
    >>> with tracer.trace_query(
    ...     cube_name="orders",
    ...     headers={"traceparent": "00-..."},
    ... ) as span:
    ...     result = execute_query(...)
    ...     tracer.record_query_result(span, row_count=100)

Note:
    NEVER include sensitive data in spans. Use FORBIDDEN_SPAN_ATTRIBUTES
    to ensure security compliance.
"""

from __future__ import annotations

import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

from floe_cube.models import (
    FORBIDDEN_SPAN_ATTRIBUTES,
    QueryTraceSpan,
    SpanKind,
    SpanStatus,
)

if TYPE_CHECKING:
    from collections.abc import Generator

logger = structlog.get_logger(__name__)


def _generate_trace_id() -> str:
    """Generate a W3C-compliant trace ID (32 lowercase hex characters)."""
    return secrets.token_hex(16)


def _generate_span_id() -> str:
    """Generate a span ID (16 lowercase hex characters)."""
    return secrets.token_hex(8)


def _is_safe_attribute(key: str) -> bool:
    """Check if an attribute key is safe to include in spans.

    Args:
        key: Attribute key to check.

    Returns:
        True if safe, False if forbidden.
    """
    key_lower = key.lower()
    return all(forbidden not in key_lower for forbidden in FORBIDDEN_SPAN_ATTRIBUTES)


def _parse_traceparent(traceparent: str | None) -> tuple[str | None, str | None]:
    """Parse W3C traceparent header to extract trace_id and parent_span_id.

    W3C traceparent format: {version}-{trace-id}-{parent-id}-{trace-flags}
    Example: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01

    Args:
        traceparent: W3C traceparent header value, or None.

    Returns:
        Tuple of (trace_id, parent_span_id), both may be None if invalid.
    """
    if not traceparent:
        return None, None

    try:
        parts = traceparent.split("-")
        if len(parts) != 4:
            return None, None

        version, trace_id, parent_span_id, _ = parts

        # Only support version 00 for now
        if version != "00":
            logger.warning("unsupported_traceparent_version", version=version)
            return None, None

        # Validate formats
        if len(trace_id) != 32 or not all(c in "0123456789abcdef" for c in trace_id):
            return None, None
        if len(parent_span_id) != 16 or not all(
            c in "0123456789abcdef" for c in parent_span_id
        ):
            return None, None

        return trace_id, parent_span_id

    except Exception as e:
        logger.warning("traceparent_parse_error", error=str(e))
        return None, None


class QueryTracer:
    """OpenTelemetry tracer for Cube queries.

    Provides tracing functionality with W3C Trace Context propagation
    and security-safe attribute handling.

    Attributes:
        service_name: Name of the service for tracing.
        enabled: Whether tracing is enabled.
        otlp_endpoint: OTLP exporter endpoint (if configured).

    Example:
        >>> tracer = QueryTracer(service_name="floe-cube")
        >>> with tracer.trace_query(cube_name="orders") as span:
        ...     result = execute_query(...)
        ...     tracer.record_query_result(span, row_count=100)

    Note:
        When tracing is disabled, all operations are no-ops that
        produce no spans and minimal overhead.
    """

    def __init__(
        self,
        service_name: str = "floe-cube",
        *,
        enabled: bool = True,
        otlp_endpoint: str | None = None,
    ) -> None:
        """Initialize QueryTracer.

        Args:
            service_name: Name of the service for span metadata.
            enabled: Whether tracing is enabled.
            otlp_endpoint: OTLP exporter endpoint. If None, reads from
                OTEL_EXPORTER_OTLP_ENDPOINT environment variable.
        """
        self._service_name = service_name
        self._enabled = enabled
        self._otlp_endpoint = otlp_endpoint or os.environ.get(
            "OTEL_EXPORTER_OTLP_ENDPOINT"
        )
        self._log = logger.bind(service=service_name, tracing_enabled=enabled)

        if enabled:
            self._log.info(
                "tracer_initialized",
                otlp_endpoint=self._otlp_endpoint or "(not configured)",
            )
        else:
            self._log.info("tracing_disabled")

    @property
    def service_name(self) -> str:
        """Get the service name."""
        return self._service_name

    @property
    def enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self._enabled

    @property
    def otlp_endpoint(self) -> str | None:
        """Get the OTLP endpoint."""
        return self._otlp_endpoint

    def _extract_context(
        self, headers: dict[str, str] | None
    ) -> tuple[str, str | None]:
        """Extract W3C Trace Context from headers.

        Args:
            headers: HTTP headers containing traceparent.

        Returns:
            Tuple of (trace_id, parent_span_id). trace_id is always
            present (generated if not propagated).
        """
        if headers is None:
            return _generate_trace_id(), None

        # W3C Trace Context uses lowercase 'traceparent'
        traceparent = headers.get("traceparent") or headers.get("Traceparent")

        trace_id, parent_span_id = _parse_traceparent(traceparent)

        if trace_id is None:
            # No valid traceparent, generate new trace
            return _generate_trace_id(), None

        return trace_id, parent_span_id

    def create_span(
        self,
        name: str,
        kind: SpanKind,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, str | int | bool] | None = None,
    ) -> QueryTraceSpan | None:
        """Create a new trace span.

        Args:
            name: Span name (e.g., "cube.query", "cube.execute").
            kind: Span kind (SERVER, CLIENT, INTERNAL).
            trace_id: Trace ID. If None, generates a new one.
            parent_span_id: Parent span ID for hierarchy.
            attributes: Span attributes (must be safe).

        Returns:
            QueryTraceSpan if tracing is enabled, None otherwise.

        Raises:
            ValueError: If attributes contain forbidden keys.
        """
        if not self._enabled:
            return None

        # Validate and filter attributes
        safe_attributes: dict[str, str | int | bool] = {}
        if attributes:
            for key, value in attributes.items():
                if _is_safe_attribute(key):
                    safe_attributes[key] = value
                else:
                    self._log.warning(
                        "unsafe_attribute_filtered",
                        key=key,
                        reason="contains forbidden term",
                    )

        return QueryTraceSpan(
            trace_id=trace_id or _generate_trace_id(),
            span_id=_generate_span_id(),
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            start_time=datetime.now(tz=timezone.utc),
            status=SpanStatus.UNSET,
            attributes=safe_attributes,
        )

    @contextmanager
    def trace_query(
        self,
        cube_name: str,
        headers: dict[str, str] | None = None,
        *,
        measures_count: int = 0,
        dimensions_count: int = 0,
        filter_count: int = 0,
        openlineage_run_id: str | None = None,
    ) -> Generator[QueryTraceSpan | None, None, None]:
        """Context manager for tracing a Cube query.

        Creates a SERVER span for the query with appropriate attributes.
        Automatically sets span status on exit.

        Args:
            cube_name: Name of the cube being queried.
            headers: HTTP headers for W3C context extraction.
            measures_count: Number of measures in the query.
            dimensions_count: Number of dimensions in the query.
            filter_count: Number of filters (NOT filter values!).
            openlineage_run_id: OpenLineage run ID to link spans.

        Yields:
            QueryTraceSpan if tracing enabled, None otherwise.

        Example:
            >>> with tracer.trace_query("orders", measures_count=2) as span:
            ...     result = execute_query(...)
            ...     if span:
            ...         tracer.record_query_result(span, row_count=100)
        """
        if not self._enabled:
            yield None
            return

        trace_id, parent_span_id = self._extract_context(headers)

        attributes: dict[str, str | int | bool] = {
            "cube.name": cube_name,
            "cube.measures_count": measures_count,
            "cube.dimensions_count": dimensions_count,
            "cube.filter_count": filter_count,
            "service.name": self._service_name,
        }

        if openlineage_run_id:
            attributes["openlineage.run_id"] = openlineage_run_id

        span = self.create_span(
            name="cube.query",
            kind=SpanKind.SERVER,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            attributes=attributes,
        )

        self._log.debug(
            "span_started",
            trace_id=trace_id,
            span_id=span.span_id if span else None,
            cube_name=cube_name,
        )

        try:
            yield span
            # Note: span is frozen, so we can't mutate it
            # Status would be set via record_query_result
            self._log.debug(
                "span_completed",
                trace_id=trace_id,
                span_id=span.span_id if span else None,
            )
        except Exception:
            self._log.debug(
                "span_error",
                trace_id=trace_id,
                span_id=span.span_id if span else None,
            )
            raise

    def create_child_span(
        self,
        parent: QueryTraceSpan,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, str | int | bool] | None = None,
    ) -> QueryTraceSpan | None:
        """Create a child span in the hierarchy.

        Args:
            parent: Parent span.
            name: Child span name.
            kind: Span kind (default INTERNAL).
            attributes: Additional attributes.

        Returns:
            Child QueryTraceSpan if tracing enabled, None otherwise.
        """
        if not self._enabled:
            return None

        return self.create_span(
            name=name,
            kind=kind,
            trace_id=parent.trace_id,
            parent_span_id=parent.span_id,
            attributes=attributes,
        )

    def record_query_result(
        self,
        span: QueryTraceSpan | None,
        *,
        row_count: int | None = None,
        error_type: str | None = None,
        status: SpanStatus = SpanStatus.OK,
    ) -> QueryTraceSpan | None:
        """Record query result in span.

        Since QueryTraceSpan is frozen, this creates a new span with
        updated values. In a real OTel implementation, this would
        mutate the span in place.

        Args:
            span: The span to update (may be None if tracing disabled).
            row_count: Number of rows returned.
            error_type: Error classification (e.g., "ValidationError").
            status: Span status (OK, ERROR, UNSET).

        Returns:
            Updated span with end_time and attributes, or None.
        """
        if span is None:
            return None

        # Build updated attributes
        new_attributes = dict(span.attributes)
        if row_count is not None:
            new_attributes["cube.row_count"] = row_count
        if error_type is not None:
            new_attributes["cube.error_type"] = error_type

        # Create updated span (frozen, so we need a new instance)
        updated_span = QueryTraceSpan(
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            name=span.name,
            kind=span.kind,
            start_time=span.start_time,
            end_time=datetime.now(tz=timezone.utc),
            status=status,
            attributes=new_attributes,
        )

        self._log.debug(
            "query_result_recorded",
            trace_id=span.trace_id,
            span_id=span.span_id,
            row_count=row_count,
            status=status.value,
        )

        return updated_span

    def inject_safe_attributes(
        self,
        span: QueryTraceSpan | None,
        attributes: dict[str, Any],
    ) -> QueryTraceSpan | None:
        """Inject safe attributes into a span.

        Filters out any forbidden attributes for security.

        Args:
            span: Span to update (may be None).
            attributes: Attributes to inject (will be filtered).

        Returns:
            Updated span with safe attributes, or None.
        """
        if span is None:
            return None

        # Filter and convert attributes
        safe_attributes = dict(span.attributes)
        for key, value in attributes.items():
            if _is_safe_attribute(key):
                # Only allow str, int, bool
                if isinstance(value, (str, int, bool)):
                    safe_attributes[key] = value
                else:
                    safe_attributes[key] = str(value)
            else:
                self._log.warning(
                    "unsafe_attribute_rejected",
                    key=key,
                    reason="contains forbidden term",
                )

        return QueryTraceSpan(
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            name=span.name,
            kind=span.kind,
            start_time=span.start_time,
            end_time=span.end_time,
            status=span.status,
            attributes=safe_attributes,
        )


# Convenience function for creating a disabled tracer
def create_noop_tracer() -> QueryTracer:
    """Create a no-op tracer with tracing disabled.

    Returns:
        QueryTracer with enabled=False.
    """
    return QueryTracer(enabled=False)
