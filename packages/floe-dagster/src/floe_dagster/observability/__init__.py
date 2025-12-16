"""OpenTelemetry integration for pipeline observability.

T012: Create observability subpackage __init__.py

This package provides OpenTelemetry tracing and metrics for
pipeline execution monitoring.

Key Components:
    - TracingManager: Manages trace spans for asset materialization
    - LogProcessor: Injects trace context into structured logs
    - MetricsCollector: Collects execution metrics

Features:
    - Automatic span creation for each asset materialization
    - Trace context propagation to logs (trace_id, span_id)
    - OTLP export when endpoint configured
    - Zero overhead when observability disabled

Example:
    >>> from floe_dagster.observability import TracingManager
    >>> tracing = TracingManager()
    >>> tracing.configure(endpoint="http://otel:4317")
    >>> with tracing.start_span("materialize_model", {"model": "customers"}) as span:
    ...     # ... execute model ...
    ...     span.set_attribute("rows_affected", 1000)
"""

from __future__ import annotations

# Components will be exported as implemented
# from floe_dagster.observability.tracing import TracingManager
# from floe_dagster.observability.logging import LogProcessor
# from floe_dagster.observability.metrics import MetricsCollector

__all__: list[str] = [
    # "TracingManager",
    # "LogProcessor",
    # "MetricsCollector",
]
