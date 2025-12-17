"""OpenTelemetry tracing manager.

T072: [US4] Implement TracingManager.configure with OTLP exporter
T073: [US4] Implement TracingManager.start_span with asset attributes
T074: [US4] Implement NoOpTracerProvider for graceful degradation
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.trace import NoOpTracerProvider, Span, Status, StatusCode

from floe_dagster.observability.config import TracingConfig

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer

logger = logging.getLogger(__name__)


class TracingManager:
    """Manager for OpenTelemetry tracing.

    Handles TracerProvider configuration, span creation, and trace context
    management. Implements graceful degradation when tracing is disabled.

    Attributes:
        config: Tracing configuration
        enabled: Whether tracing is enabled

    Example:
        >>> config = TracingConfig(endpoint="http://localhost:4317")
        >>> manager = TracingManager(config)
        >>> manager.configure()
        >>> with manager.start_span("dbt_run", {"model": "stg_customers"}) as span:
        ...     # Execute model
        ...     manager.set_status_ok(span)

    Graceful Degradation:
        When endpoint is None or unavailable, uses NoOpTracerProvider.
        All span operations become no-ops with minimal overhead.

        >>> disabled_config = TracingConfig()  # endpoint=None
        >>> manager = TracingManager(disabled_config)
        >>> manager.configure()
        >>> manager.enabled
        False
    """

    def __init__(self, config: TracingConfig) -> None:
        """Initialize TracingManager.

        Args:
            config: Tracing configuration.
        """
        self.config = config
        self._provider: trace.TracerProvider | None = None
        self._tracer: Tracer | None = None
        self._configured = False

    @property
    def enabled(self) -> bool:
        """Check if tracing is enabled.

        Returns:
            True if endpoint is configured, False otherwise.
        """
        return self.config.enabled

    def configure(self) -> None:
        """Configure the TracerProvider.

        Sets up the tracer provider with OTLP exporter if enabled,
        or NoOpTracerProvider for graceful degradation.

        This method should be called once at application startup.
        """
        if self._configured:
            logger.warning("TracingManager already configured - skipping")
            return

        if not self.enabled:
            # Graceful degradation - use NoOp
            logger.debug("Tracing disabled - using NoOpTracerProvider")
            self._provider = NoOpTracerProvider()
            self._tracer = self._provider.get_tracer("floe-dagster")
            self._configured = True
            return

        # Create resource with service information
        resource_attributes = {
            SERVICE_NAME: self.config.service_name,
        }
        resource_attributes.update(self.config.attributes)

        resource = Resource(attributes=resource_attributes)

        # Create TracerProvider
        self._provider = TracerProvider(resource=resource)

        # Configure OTLP exporter
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(
                endpoint=self.config.endpoint,
                insecure=True,  # Use TLS in production
            )

            # Use BatchSpanProcessor for efficiency (or Simple for debugging)
            if self.config.batch_export:
                self._provider.add_span_processor(BatchSpanProcessor(exporter))
            else:
                self._provider.add_span_processor(SimpleSpanProcessor(exporter))

            logger.info(
                "Configured OTLP tracing to %s (batch=%s)",
                self.config.endpoint,
                self.config.batch_export,
            )

        except ImportError:
            logger.warning(
                "opentelemetry-exporter-otlp-proto-grpc not installed. "
                "Install with: pip install opentelemetry-exporter-otlp-proto-grpc"
            )
            # Fall back to NoOp
            self._provider = NoOpTracerProvider()

        self._tracer = self._provider.get_tracer(
            "floe-dagster",
            schema_url="https://opentelemetry.io/schemas/1.21.0",
        )
        self._configured = True

    def get_tracer(self, name: str) -> Tracer:
        """Get a tracer instance.

        Args:
            name: Name for the tracer (typically module name).

        Returns:
            Tracer instance.
        """
        if not self._configured:
            self.configure()

        if self._provider is None:
            return trace.get_tracer(name)

        return self._provider.get_tracer(name)

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[Span]:
        """Start a new span as a context manager.

        Creates a span with the given name and attributes. The span
        is automatically ended when the context exits.

        Args:
            name: Span name (e.g., "dbt_run", "materialize_model").
            attributes: Optional span attributes.

        Yields:
            Active span.

        Example:
            >>> with manager.start_span("dbt_run", {"model": "stg_customers"}):
            ...     # Execute model
            ...     pass
        """
        if not self._configured:
            self.configure()

        if self._tracer is None:
            # Should not happen, but handle gracefully
            with trace.get_tracer(__name__).start_as_current_span(name) as span:
                yield span
            return

        span_attributes = attributes or {}

        with self._tracer.start_as_current_span(
            name,
            attributes=span_attributes,
        ) as span:
            yield span

    def record_exception(self, span: Span, exception: Exception) -> None:
        """Record an exception on the span.

        Args:
            span: Span to record exception on.
            exception: Exception to record.
        """
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))

    def set_status_ok(self, span: Span) -> None:
        """Set span status to OK.

        Args:
            span: Span to update.
        """
        span.set_status(Status(StatusCode.OK))

    def set_status_error(self, span: Span, description: str) -> None:
        """Set span status to ERROR.

        Args:
            span: Span to update.
            description: Error description.
        """
        span.set_status(Status(StatusCode.ERROR, description))

    def get_current_trace_context(self) -> dict[str, str | None]:
        """Get current trace context (trace_id, span_id).

        Returns:
            Dictionary with trace_id and span_id, or None values if no active span.
        """
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context()

        if span_context.is_valid:
            return {
                "trace_id": format(span_context.trace_id, "032x"),
                "span_id": format(span_context.span_id, "016x"),
            }

        return {
            "trace_id": None,
            "span_id": None,
        }

    def shutdown(self) -> None:
        """Shutdown the tracer provider.

        Flushes pending spans and releases resources.
        """
        if self._provider and hasattr(self._provider, "shutdown"):
            self._provider.shutdown()

    def __enter__(self) -> TracingManager:
        """Enter context manager - configure tracing."""
        self.configure()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager - shutdown tracing."""
        self.shutdown()
