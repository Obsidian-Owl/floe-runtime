"""OpenTelemetry integration for pipeline observability.

T012: Create observability subpackage __init__.py
T077: [US4] Update observability __init__.py with public exports
T089: [US6] Update observability __init__.py with ObservabilityOrchestrator

This package provides OpenTelemetry tracing, structured logging, and unified
observability orchestration for pipeline execution monitoring.

Key Components:
    - TracingConfig: Configuration for OpenTelemetry tracing
    - TracingManager: Manages trace spans for asset materialization
    - ObservabilityOrchestrator: Unified tracing + lineage context manager
    - AssetRunContext: Context returned by ObservabilityOrchestrator.asset_run()
    - JSONFormatter: JSON log formatter with trace context injection
    - BoundLogger: Logger with bound context for structured logging
    - configure_logging: Configure structured logging with JSON format
    - get_logger: Get a logger instance

Features:
    - Automatic span creation for each asset materialization
    - Trace context propagation to logs (trace_id, span_id)
    - OTLP export when endpoint configured
    - Zero overhead when observability disabled (NoOpTracerProvider)
    - JSON-formatted logs with automatic trace context injection
    - Unified observability via ObservabilityOrchestrator (batteries-included)
    - Graceful degradation when tracing/lineage unavailable

Example (Low-Level API):
    >>> from floe_dagster.observability import TracingConfig, TracingManager
    >>> config = TracingConfig(endpoint="http://otel:4317")
    >>> manager = TracingManager(config)
    >>> manager.configure()
    >>> with manager.start_span("materialize_model", {"model": "customers"}) as span:
    ...     # ... execute model ...
    ...     span.set_attribute("rows_affected", 1000)

Example (High-Level API - Recommended):
    >>> from floe_dagster.observability import ObservabilityOrchestrator
    >>> orchestrator = ObservabilityOrchestrator.from_compiled_artifacts(artifacts)
    >>> with orchestrator.asset_run("bronze_customers", outputs=["demo.bronze"]) as ctx:
    ...     # Business logic - observability automatic
    ...     ctx.set_attribute("rows_processed", 1000)

    >>> from floe_dagster.observability import configure_logging
    >>> logger = configure_logging("my_module", tracing_manager=manager)
    >>> logger.info("Processing started", extra={"pipeline_id": "abc123"})
"""

from __future__ import annotations

from floe_dagster.observability.config import TracingConfig
from floe_dagster.observability.logging import (
    BoundLogger,
    JSONFormatter,
    configure_logging,
    get_logger,
)
from floe_dagster.observability.orchestrator import (
    AssetRunContext,
    ObservabilityOrchestrator,
)
from floe_dagster.observability.tracing import TracingManager

__all__: list[str] = [
    # Core configuration
    "TracingConfig",
    "TracingManager",
    # Unified orchestration (batteries-included API)
    "ObservabilityOrchestrator",
    "AssetRunContext",
    # Logging utilities
    "JSONFormatter",
    "BoundLogger",
    "configure_logging",
    "get_logger",
]
