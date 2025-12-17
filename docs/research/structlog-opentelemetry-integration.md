# Structlog + OpenTelemetry Integration for Trace Context Injection

## Overview

This document outlines how to integrate structlog with OpenTelemetry for automatic trace context injection into structured logs. This enables correlation between logs and traces in observability backends like Datadog, SigNoz, Grafana, and others.

## Key Concepts

### Trace Context Correlation

OpenTelemetry SDKs can automatically correlate logs with traces by injecting context (Trace ID, Span ID) into log records. The W3C Trace Context specification defines:

- **Trace ID**: 32-character lowercase hexadecimal string (16 bytes) - unique identifier for a distributed trace
- **Span ID**: 16-character lowercase hexadecimal string (8 bytes) - identifier for a specific span/operation within that trace

This correlation creates a two-way debugging workflow:
- From a trace → jump to logs that occurred within spans
- From a log → pivot back to the full distributed trace

## Custom Structlog Processor Implementation

### Official structlog Approach (Recommended)

From the [structlog documentation](https://www.structlog.org/en/stable/frameworks.html), the recommended processor:

```python
"""Structlog processor for OpenTelemetry trace context injection."""

from __future__ import annotations

from typing import Any
from opentelemetry import trace


def add_opentelemetry_spans(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add OpenTelemetry span context to structlog event dictionary.

    This processor extracts the current span context and injects trace_id,
    span_id, and parent_span_id into the log event. This enables correlation
    between logs and traces in observability backends.

    Args:
        logger: The wrapped logger instance (unused but required by protocol)
        method_name: The name of the method called on the logger (unused)
        event_dict: The event dictionary to be logged

    Returns:
        The event dictionary enriched with span context if a span is recording

    Example:
        >>> import structlog
        >>> structlog.configure(
        ...     processors=[
        ...         add_opentelemetry_spans,
        ...         structlog.processors.JSONRenderer(),
        ...     ]
        ... )
    """
    span = trace.get_current_span()

    # Check if span is recording to avoid unnecessary computation
    if not span.is_recording():
        event_dict["span"] = None
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    # W3C Trace Context format: lowercase hex strings
    event_dict["span"] = {
        "span_id": format(ctx.span_id, "016x"),  # 16 hex chars (8 bytes)
        "trace_id": format(ctx.trace_id, "032x"),  # 32 hex chars (16 bytes)
        "parent_span_id": None if not parent else format(parent.span_id, "016x"),
    }

    return event_dict
```

### Alternative Flat Structure

For simpler log queries, use a flat structure instead of nested:

```python
"""Structlog processor with flat trace context fields."""

from __future__ import annotations

from typing import Any
from opentelemetry import trace


def add_trace_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add OpenTelemetry trace context as flat fields.

    This processor adds trace_id and span_id directly to the event dict
    rather than nesting them under a 'span' key. This makes querying
    logs easier in some observability backends.

    Args:
        logger: The wrapped logger instance (unused)
        method_name: The name of the method called (unused)
        event_dict: The event dictionary to be logged

    Returns:
        The event dictionary with trace_id and span_id fields added

    Example JSON output:
        {
            "event": "Processing pipeline",
            "timestamp": "2025-12-16T10:30:45.123456Z",
            "level": "info",
            "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
            "span_id": "00f067aa0ba902b7"
        }
    """
    span = trace.get_current_span()

    # Only add context if span is actively recording
    if span.is_recording():
        ctx = span.get_span_context()
        # Format as lowercase hex per W3C Trace Context spec
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")

    return event_dict
```

## Extracting Current Span Context from OpenTelemetry

### Getting the Current Span

From the [OpenTelemetry Python API](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html):

```python
"""Examples of accessing OpenTelemetry span context."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


def get_trace_context() -> tuple[str, str] | None:
    """
    Extract trace_id and span_id from current span.

    Returns:
        Tuple of (trace_id, span_id) as hex strings, or None if no active span

    Example:
        >>> context = get_trace_context()
        >>> if context:
        ...     trace_id, span_id = context
        ...     print(f"Trace: {trace_id}, Span: {span_id}")
    """
    span = trace.get_current_span()

    if not span.is_recording():
        return None

    ctx = span.get_span_context()

    # Format per W3C Trace Context specification
    trace_id = format(ctx.trace_id, "032x")  # 32 lowercase hex chars
    span_id = format(ctx.span_id, "016x")    # 16 lowercase hex chars

    return trace_id, span_id


def set_span_attributes_conditionally(user_id: str, email: str) -> None:
    """
    Set span attributes only if span is recording.

    Best practice: Check is_recording() before expensive operations
    to avoid unnecessary computation when span is not being recorded.

    Args:
        user_id: User identifier
        email: User email address
    """
    span = trace.get_current_span()

    # Best practice: Check if span is recording before expensive operations
    if span.is_recording():
        span.set_attribute("user.id", user_id)
        span.set_attribute("user.email", email)


def example_span_with_error_handling() -> None:
    """
    Example of proper span usage with error handling.

    This pattern shows:
    - Using context manager for automatic span lifecycle
    - Checking is_recording() before setting attributes
    - Recording exceptions and setting error status
    """
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("process-user") as span:
        # Check if span is being recorded to avoid unnecessary work
        if span.is_recording():
            span.set_attribute("operation.type", "user_processing")
            span.set_attribute("service.name", "floe-runtime")

        try:
            # Perform work
            result = process_user_data()

            if span.is_recording():
                span.set_attribute("operation.result", "success")

            return result

        except Exception as exc:
            # Record exception and set error status
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise


def create_span_with_link() -> None:
    """
    Create a span linked to the current span context.

    Useful for linking related spans across different traces.
    """
    tracer = trace.get_tracer(__name__)

    # Get current span context to create link
    current_ctx = trace.get_current_span().get_span_context()
    link = trace.Link(current_ctx)

    # Start new span with link to current span
    with tracer.start_as_current_span("linked-operation", links=[link]) as span:
        # Span is now linked to the original context
        pass
```

### Understanding `is_recording()`

The `is_recording()` method is critical for performance optimization:

- **Returns**: `True` if the span is active and recording events/attributes
- **Best Practice**: Check before expensive operations like computing attributes
- **Why It Matters**: Non-recording spans (e.g., when not sampled) skip unnecessary work

From the [OpenTelemetry Python documentation](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.span.html):

> "Check if span is being recorded to avoid expensive computations"

## Complete Structlog Configuration

### Production-Ready Configuration

```python
"""Production-ready structlog configuration with OpenTelemetry integration."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from opentelemetry import trace


def add_trace_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add OpenTelemetry trace context to logs."""
    span = trace.get_current_span()

    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
        # Add trace flags for sampling information
        event_dict["trace_flags"] = format(ctx.trace_flags, "02x")

    return event_dict


def configure_structlog() -> None:
    """
    Configure structlog with OpenTelemetry trace context injection.

    This configuration:
    - Adds ISO timestamps
    - Injects trace context (trace_id, span_id, trace_flags)
    - Formats stack traces
    - Renders as JSON for observability backends
    - Integrates with standard library logging
    """
    # Configure shared processors for both structlog and stdlib logging
    shared_processors: list[Any] = [
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add ISO timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Inject OpenTelemetry trace context
        add_trace_context,
        # Format stack info
        structlog.processors.StackInfoRenderer(),
        # Format exception info
        structlog.processors.format_exc_info,
    ]

    # Configure structlog
    structlog.configure(
        # Processors for structlog loggers
        processors=shared_processors + [
            # Prepare event dict for stdlib logging
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # Use stdlib logging for actual output
        wrapper_class=structlog.stdlib.BoundLogger,
        # Use dict as context class
        context_class=dict,
        # Use stdlib LoggerFactory
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Enable caching for performance
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog processors
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Add structlog formatter to stdlib root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            # Foreign log entries (from third-party libraries)
            foreign_pre_chain=shared_processors,
            # Structlog log entries
            processors=[
                # Remove _record and _from_structlog keys
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                # Render as JSON
                structlog.processors.JSONRenderer(),
            ],
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


# Example usage
if __name__ == "__main__":
    configure_structlog()

    logger = structlog.get_logger(__name__)

    # Logs without trace context (no active span)
    logger.info("application_started", version="1.0.0")

    # Logs with trace context (inside a span)
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("example-operation") as span:
        logger.info(
            "processing_pipeline",
            pipeline_id="pipeline-123",
            status="running"
        )

        # Logs will include trace_id and span_id
        logger.warning(
            "pipeline_slow",
            pipeline_id="pipeline-123",
            duration_ms=5000
        )
```

## JSON Log Format with Trace Fields

### Example Log Output

When logs are emitted inside an OpenTelemetry span, they will include trace context:

```json
{
  "event": "processing_pipeline",
  "pipeline_id": "pipeline-123",
  "status": "running",
  "timestamp": "2025-12-16T10:30:45.123456Z",
  "level": "info",
  "logger": "floe_runtime.pipeline",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "trace_flags": "01"
}
```

When logs are emitted **outside** a span (no active trace):

```json
{
  "event": "application_started",
  "version": "1.0.0",
  "timestamp": "2025-12-16T10:30:40.123456Z",
  "level": "info",
  "logger": "floe_runtime.main"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | string | 32-character lowercase hex string identifying the distributed trace |
| `span_id` | string | 16-character lowercase hex string identifying the current span |
| `trace_flags` | string | 2-character hex string with trace flags (01 = sampled, 00 = not sampled) |
| `parent_span_id` | string | (Optional) 16-character hex string identifying the parent span |
| `timestamp` | string | ISO 8601 timestamp with microseconds |
| `level` | string | Log level (debug, info, warning, error, critical) |
| `logger` | string | Logger name (usually module path) |
| `event` | string | Log message/event description |

## Integration with Dagster Logging

### Current State

Dagster does not have first-class OpenTelemetry support yet, but it's a [highly requested feature](https://github.com/dagster-io/dagster/issues/12353):

- **Issue #12353**: Support for OpenTelemetry traces and span/trace IDs in log lines
- **Issue #11191**: Implement a default telemetry provider parallel to the default logger (OTel/OpenTelemetry)

### Workaround: Custom Logging Configuration

You can integrate structlog with Dagster by configuring custom logging in `dagster.yaml`:

```yaml
# dagster.yaml
python_logs:
  # Use custom logging configuration
  python_log_level: INFO

  # Configure handlers
  handlers:
    console:
      class: logging.StreamHandler
      stream: ext://sys.stdout
      formatter: structlog_formatter

  # Configure formatters
  formatters:
    structlog_formatter:
      (): structlog.stdlib.ProcessorFormatter
      processors:
        - structlog.stdlib.ProcessorFormatter.remove_processors_meta
        - structlog.processors.JSONRenderer
      foreign_pre_chain:
        - structlog.stdlib.add_log_level
        - structlog.processors.TimeStamper:
            fmt: iso
        - add_trace_context  # Custom processor

  # Root logger configuration
  root:
    level: INFO
    handlers:
      - console
```

### Programmatic Configuration

```python
"""Integrate structlog with Dagster logging."""

from __future__ import annotations

import logging
from typing import Any

import structlog
from dagster import OpExecutionContext, op, job
from opentelemetry import trace


def add_dagster_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add Dagster execution context to logs.

    This processor can extract Dagster-specific context like:
    - Run ID
    - Job/Asset name
    - Step key
    """
    # Note: This requires passing context through structlog.bind()
    # or using contextvars
    return event_dict


def add_trace_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add OpenTelemetry trace context."""
    span = trace.get_current_span()

    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")

    return event_dict


def configure_dagster_logging() -> None:
    """Configure structlog for Dagster with OpenTelemetry."""
    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_trace_context,  # OpenTelemetry context
        add_dagster_context,  # Dagster context
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


@op
def example_op(context: OpExecutionContext) -> str:
    """
    Example Dagster op with structured logging and trace context.

    Logs will include:
    - Dagster context (run_id, op_name)
    - OpenTelemetry trace context (trace_id, span_id)
    """
    # Get structlog logger
    logger = structlog.get_logger(__name__)

    # Bind Dagster context to logger
    log = logger.bind(
        run_id=context.run_id,
        op_name=context.op_def.name,
    )

    # Start OpenTelemetry span
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("dagster-op-execution") as span:
        if span.is_recording():
            span.set_attribute("dagster.run_id", context.run_id)
            span.set_attribute("dagster.op_name", context.op_def.name)

        log.info("op_started")

        # Perform work
        result = "processed"

        log.info("op_completed", result=result)

        return result


@job
def example_job():
    """Example Dagster job."""
    example_op()
```

### Expected Log Output from Dagster

```json
{
  "event": "op_started",
  "run_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "op_name": "example_op",
  "timestamp": "2025-12-16T10:30:45.123456Z",
  "level": "info",
  "logger": "floe_runtime.ops.example_op",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

## Correlation in Observability Backends

### How Backends Correlate Logs and Traces

Observability backends use the `trace_id` and `span_id` fields to link logs to traces:

1. **Datadog**: Automatically detects `trace_id` and `span_id` fields (both Datadog and OpenTelemetry conventions)
2. **SigNoz**: Native OpenTelemetry support - uses `trace_id` and `span_id` for correlation
3. **Grafana Tempo + Loki**: Correlates via `trace_id` label in Loki logs
4. **Jaeger**: Can link to logs if they include `trace_id` and `span_id`
5. **Elastic APM**: Correlates using `trace.id` and `span.id` fields

### Backend-Specific Field Mappings

Different backends may expect different field names:

```python
"""Backend-specific trace context processors."""

from __future__ import annotations

from typing import Any
from opentelemetry import trace


def add_trace_context_datadog(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add trace context in Datadog format.

    Datadog expects:
    - dd.trace_id (decimal format, lower 64 bits)
    - dd.span_id (decimal format)
    """
    span = trace.get_current_span()

    if span.is_recording():
        ctx = span.get_span_context()
        # Datadog uses decimal format and lower 64 bits of trace_id
        event_dict["dd.trace_id"] = str(ctx.trace_id & 0xFFFFFFFFFFFFFFFF)
        event_dict["dd.span_id"] = str(ctx.span_id)

        # Also include OpenTelemetry standard fields
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")

    return event_dict


def add_trace_context_elastic(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add trace context in Elastic APM format.

    Elastic expects:
    - trace.id (hex string)
    - span.id (hex string)
    """
    span = trace.get_current_span()

    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace"] = {
            "id": format(ctx.trace_id, "032x")
        }
        event_dict["span"] = {
            "id": format(ctx.span_id, "016x")
        }

    return event_dict


def add_trace_context_universal(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add trace context in multiple formats for compatibility.

    This processor adds trace context in formats compatible with:
    - OpenTelemetry standard
    - Datadog
    - Elastic APM
    """
    span = trace.get_current_span()

    if span.is_recording():
        ctx = span.get_span_context()

        # OpenTelemetry standard (hex strings)
        trace_id_hex = format(ctx.trace_id, "032x")
        span_id_hex = format(ctx.span_id, "016x")

        # Add OpenTelemetry standard fields
        event_dict["trace_id"] = trace_id_hex
        event_dict["span_id"] = span_id_hex
        event_dict["trace_flags"] = format(ctx.trace_flags, "02x")

        # Add Datadog fields (decimal, lower 64 bits)
        event_dict["dd"] = {
            "trace_id": str(ctx.trace_id & 0xFFFFFFFFFFFFFFFF),
            "span_id": str(ctx.span_id),
        }

        # Add Elastic fields (nested structure)
        event_dict["trace"] = {"id": trace_id_hex}
        event_dict["span"] = {"id": span_id_hex}

    return event_dict
```

### Example: Querying Logs by Trace ID

Once logs are enriched with trace context, you can query them:

**Grafana Loki**:
```logql
{namespace="floe-runtime"} | json | trace_id="4bf92f3577b34da6a3ce929d0e0e4736"
```

**Datadog**:
```
trace_id:4bf92f3577b34da6a3ce929d0e0e4736
```

**Elasticsearch (Elastic APM)**:
```json
{
  "query": {
    "term": {
      "trace.id": "4bf92f3577b34da6a3ce929d0e0e4736"
    }
  }
}
```

**SigNoz**:
```
trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
```

## Best Practices

### 1. Always Check `is_recording()`

```python
span = trace.get_current_span()
if span.is_recording():
    # Only do expensive work if span is being recorded
    span.set_attribute("expensive.computation", compute_expensive_value())
```

### 2. Use Structured Logging Consistently

```python
# Good: Structured fields
logger.info("pipeline_completed", pipeline_id="123", duration_ms=1500)

# Bad: String interpolation
logger.info(f"Pipeline 123 completed in 1500ms")
```

### 3. Include Both Trace Context and Business Context

```python
logger = structlog.get_logger(__name__)
log = logger.bind(
    pipeline_id=pipeline_id,
    user_id=user_id,
    environment="production",
)

with tracer.start_as_current_span("process-pipeline"):
    # Logs will include both business context AND trace context
    log.info("processing_started")
```

### 4. Format IDs per W3C Specification

```python
# Correct: Lowercase hex, proper padding
trace_id = format(ctx.trace_id, "032x")  # 32 chars
span_id = format(ctx.span_id, "016x")    # 16 chars

# Incorrect: Wrong format
trace_id = hex(ctx.trace_id)  # Has '0x' prefix
trace_id = str(ctx.trace_id)  # Decimal, not hex
```

### 5. Handle Logs Outside Spans Gracefully

```python
def add_trace_context(logger, method_name, event_dict):
    """Add trace context only if available."""
    span = trace.get_current_span()

    # Don't add fields if no active span
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")

    # Return event_dict regardless
    return event_dict
```

## Testing Trace Context Injection

### Unit Test Example

```python
"""Test structlog OpenTelemetry integration."""

from __future__ import annotations

import json
from io import StringIO

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter


def test_trace_context_injection():
    """Test that trace context is injected into logs."""
    # Setup OpenTelemetry
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    # Setup structlog with string output
    output = StringIO()
    structlog.configure(
        processors=[
            add_trace_context,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=output),
    )

    logger = structlog.get_logger()

    # Create a span and log inside it
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test-span") as span:
        ctx = span.get_span_context()
        expected_trace_id = format(ctx.trace_id, "032x")
        expected_span_id = format(ctx.span_id, "016x")

        logger.info("test_event", key="value")

    # Parse logged JSON
    output.seek(0)
    log_line = output.read().strip()
    log_data = json.loads(log_line)

    # Assert trace context is present
    assert "trace_id" in log_data
    assert "span_id" in log_data
    assert log_data["trace_id"] == expected_trace_id
    assert log_data["span_id"] == expected_span_id
    assert log_data["event"] == "test_event"
    assert log_data["key"] == "value"


def test_no_trace_context_outside_span():
    """Test that logs outside spans don't have trace context."""
    output = StringIO()
    structlog.configure(
        processors=[
            add_trace_context,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=output),
    )

    logger = structlog.get_logger()
    logger.info("test_event", key="value")

    # Parse logged JSON
    output.seek(0)
    log_line = output.read().strip()
    log_data = json.loads(log_line)

    # Assert no trace context
    assert "trace_id" not in log_data
    assert "span_id" not in log_data
    assert log_data["event"] == "test_event"
```

## Summary

### Key Takeaways

1. **Structlog requires manual processor** - Unlike stdlib logging, structlog needs a custom processor for trace context injection

2. **Use `trace.get_current_span()`** - OpenTelemetry API to retrieve the current span

3. **Format as lowercase hex** - Per W3C Trace Context specification:
   - `trace_id`: 32-character lowercase hex string
   - `span_id`: 16-character lowercase hex string

4. **Check `is_recording()`** - Avoid expensive operations when span is not being recorded

5. **JSON structured logging** - Use `JSONRenderer` for observability backend compatibility

6. **Dagster integration pending** - First-class OpenTelemetry support is a requested feature; use custom logging configuration as workaround

7. **Backend compatibility** - Different backends may expect different field names/formats; consider universal processor for multi-backend support

## Sources

- [Structlog Frameworks Documentation](https://www.structlog.org/en/stable/frameworks.html)
- [OpenTelemetry Python Logging Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html)
- [OpenTelemetry Python Trace API](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html)
- [OpenTelemetry Python Span Documentation](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.span.html)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [Dagster Issue #12353: OpenTelemetry Support](https://github.com/dagster-io/dagster/issues/12353)
- [Dagster Issue #11191: Default Telemetry Provider](https://github.com/dagster-io/dagster/issues/11191)
- [Datadog OpenTelemetry Log Correlation](https://docs.datadoghq.com/tracing/other_telemetry/connect_logs_and_traces/opentelemetry/)
- [Leveling Up Your Python Logs with Structlog - Dash0](https://www.dash0.com/guides/python-logging-with-structlog)
- [Complete Guide to Logging with StructLog in Python - SigNoz](https://signoz.io/guides/structlog/)
