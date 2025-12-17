# OpenTelemetry Python SDK Research

## Overview

This document provides a comprehensive guide to implementing OpenTelemetry tracing in Python, based on the latest documentation and best practices as of December 2025.

---

## 1. TracerProvider and Tracer Setup

### Global TracerProvider Initialization

**Best Practice**: Applications should use a single global TracerProvider and set it once at application startup.

```python
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def initialize_tracing(
    service_name: str,
    otlp_endpoint: str | None = None,
    enabled: bool = True
) -> trace.TracerProvider:
    """Initialize OpenTelemetry tracing with OTLP exporter.

    Args:
        service_name: Name of the service for resource attributes
        otlp_endpoint: OTLP endpoint URL (e.g., "http://localhost:4317")
        enabled: Whether tracing is enabled (uses NoOp if False)

    Returns:
        Configured TracerProvider instance
    """
    # If disabled, use NoOpTracerProvider for graceful degradation
    if not enabled:
        from opentelemetry.trace import NoOpTracerProvider
        provider = NoOpTracerProvider()
        trace.set_tracer_provider(provider)
        return provider

    # Create resource with service information
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        "service.version": "1.0.0",
        "deployment.environment": "production",
    })

    # Create TracerProvider with resource
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter if endpoint provided
    if otlp_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # Use insecure=False with proper TLS in production
        )
        # Use BatchSpanProcessor for production (better performance)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

    # Set as global default (can only be done once)
    trace.set_tracer_provider(provider)

    return provider


# Initialize tracing at application startup
tracer_provider = initialize_tracing(
    service_name="floe-runtime",
    otlp_endpoint="http://localhost:4317",
    enabled=True
)

# Get a tracer for your module
tracer = trace.get_tracer(__name__)
```

**Key Points**:
- The global TracerProvider can only be set once; subsequent attempts will log a warning
- Use `BatchSpanProcessor` for production (better performance than `SimpleSpanProcessor`)
- Set attributes at span creation when possible (samplers only see creation-time attributes)

---

## 2. Creating Trace Spans with Attributes

### Basic Span Creation

```python
from __future__ import annotations

from opentelemetry import trace
from typing import Any

tracer = trace.get_tracer(__name__)

def process_data(data: dict[str, Any]) -> dict[str, Any]:
    """Process data with tracing."""
    # Create a span with attributes at creation (preferred for sampling)
    with tracer.start_as_current_span(
        "process_data",  # Span name: {verb} {object} pattern
        attributes={
            "operation.type": "batch",
            "data.size": len(data),
        }
    ) as span:
        # Add attributes during execution
        span.set_attribute("processing.started", True)

        result = perform_processing(data)

        # Add result attributes
        span.set_attribute("result.count", len(result))
        span.set_attribute("processing.success", True)

        return result
```

### Semantic Attributes (Recommended)

Use semantic conventions for common operations to ensure consistency across systems:

```python
from opentelemetry.semconv.trace import SpanAttributes

def make_http_request(url: str, method: str = "GET") -> dict[str, Any]:
    """Make HTTP request with semantic attributes."""
    with tracer.start_as_current_span(
        f"{method} {url}",  # Span name follows {method} {route} convention
        attributes={
            SpanAttributes.HTTP_METHOD: method,
            SpanAttributes.HTTP_URL: url,
            SpanAttributes.HTTP_SCHEME: "https",
        }
    ) as span:
        response = requests.get(url)

        # Add response attributes
        span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, response.status_code)
        span.set_attribute(SpanAttributes.HTTP_RESPONSE_CONTENT_LENGTH, len(response.content))

        return response.json()
```

### Setting Multiple Attributes

```python
def process_pipeline(pipeline_id: str, stage: str) -> None:
    """Process pipeline stage with multiple attributes."""
    with tracer.start_as_current_span(
        "process pipeline_stage",  # Low-cardinality span name
        attributes={
            "pipeline.id": pipeline_id,  # High-cardinality data in attributes
            "pipeline.stage": stage,
            "pipeline.version": "2.0.0",
        }
    ) as span:
        # Process pipeline
        span.set_attribute("stage.started_at", "2025-12-16T10:00:00Z")

        # Set multiple attributes at once
        span.set_attributes({
            "stage.duration_ms": 1234,
            "stage.records_processed": 10000,
            "stage.status": "completed",
        })
```

### Supported Attribute Types

Span attributes support these types:
- `str`
- `bool`
- `int`
- `float`
- `Sequence[str]`
- `Sequence[bool]`
- `Sequence[int]`
- `Sequence[float]`

**Important**: Setting `None` values is undefined behavior and strongly discouraged.

---

## 3. OTLP Exporter Configuration

### gRPC Exporter (Default Protocol)

```python
from __future__ import annotations

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# gRPC exporter configuration
grpc_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",  # Default gRPC endpoint
    insecure=True,  # Set to False for production with TLS
    credentials=None,  # ChannelCredentials for secure connections
    headers={  # Optional headers
        "api-key": "your-api-key",
    },
    timeout=10,  # Timeout in seconds
    compression=None,  # Or "gzip" for compression
)

# Add to TracerProvider
processor = BatchSpanProcessor(grpc_exporter)
tracer_provider.add_span_processor(processor)
```

### HTTP Exporter

```python
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter

# HTTP exporter configuration
http_exporter = HTTPSpanExporter(
    endpoint="http://localhost:4318/v1/traces",  # Note: must include /v1/traces path
    headers={
        "Authorization": "Bearer your-token",
    },
    timeout=10,  # Timeout in seconds
    compression=None,  # Or "gzip"
)

processor = BatchSpanProcessor(http_exporter)
tracer_provider.add_span_processor(processor)
```

### Environment Variable Configuration

OpenTelemetry supports configuration via environment variables:

```bash
# Protocol selection (http/protobuf or grpc)
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc

# Endpoint configuration (all signals)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Signal-specific endpoints
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://localhost:4318

# Headers (comma-separated key=value pairs)
export OTEL_EXPORTER_OTLP_HEADERS="api-key=value,other-header=value"
export OTEL_EXPORTER_OTLP_TRACES_HEADERS="trace-specific-header=value"

# Timeout (milliseconds)
export OTEL_EXPORTER_OTLP_TIMEOUT=10000

# Compression
export OTEL_EXPORTER_OTLP_COMPRESSION=gzip
```

**Endpoint Defaults**:
- gRPC: `0.0.0.0:4317`
- HTTP: `0.0.0.0:4318`

**Important**: For OTLP/HTTP, the SDK automatically constructs signal-specific URLs by appending `/v1/traces`, `/v1/metrics`, or `/v1/logs` to the base endpoint.

### Installation

```bash
# Install all exporters (includes both gRPC and HTTP)
pip install opentelemetry-exporter-otlp

# Or install specific exporter to avoid unnecessary dependencies
pip install opentelemetry-exporter-otlp-proto-grpc
pip install opentelemetry-exporter-otlp-proto-http
```

---

## 4. Context Propagation Between Spans

### Automatic Context Propagation (Nested Spans)

OpenTelemetry Python automatically propagates context when creating nested spans:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def parent_operation() -> None:
    """Parent span automatically becomes the context for child spans."""
    with tracer.start_as_current_span("parent_operation") as parent:
        parent.set_attribute("level", "parent")

        # Child span automatically inherits parent context
        child_operation()


def child_operation() -> None:
    """Child span is automatically linked to parent via context."""
    with tracer.start_as_current_span("child_operation") as child:
        child.set_attribute("level", "child")

        # Get current span from context
        current = trace.get_current_span()
        ctx = current.get_span_context()

        print(f"Trace ID: {format(ctx.trace_id, '032x')}")
        print(f"Span ID: {format(ctx.span_id, '016x')}")

        # Grandchild span
        grandchild_operation()


def grandchild_operation() -> None:
    """Grandchild span continues the trace."""
    with tracer.start_as_current_span("grandchild_operation") as grandchild:
        grandchild.set_attribute("level", "grandchild")
```

### Async Context Propagation

Context is automatically propagated in async/await code:

```python
import asyncio
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def async_parent() -> None:
    """Parent async operation."""
    with tracer.start_as_current_span("async_parent") as parent:
        parent.set_attribute("async", True)

        # Context propagates across async calls
        await async_child()


async def async_child() -> None:
    """Child async operation inherits context."""
    with tracer.start_as_current_span("async_child") as child:
        child.set_attribute("async", True)
        await asyncio.sleep(0.1)


# Run async code
asyncio.run(async_parent())
```

### Manual Context Propagation (Cross-Service)

For cross-service communication, use propagators to inject/extract context:

```python
from opentelemetry import trace
from opentelemetry.propagate import inject, extract
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

tracer = trace.get_tracer(__name__)

# Sender side: Inject context into HTTP headers
def send_request(url: str) -> None:
    """Send HTTP request with trace context."""
    with tracer.start_as_current_span("http_request") as span:
        headers = {}

        # Inject trace context into headers (W3C TraceContext format)
        inject(headers)

        # headers now contains: {"traceparent": "00-trace_id-span_id-01"}
        response = requests.get(url, headers=headers)


# Receiver side: Extract context from HTTP headers
def receive_request(headers: dict[str, str]) -> None:
    """Receive HTTP request and extract trace context."""
    # Extract context from headers
    ctx = extract(headers)

    # Create span with extracted context as parent
    with tracer.start_as_current_span("handle_request", context=ctx) as span:
        span.set_attribute("received", True)
        # This span is now part of the same trace
```

### SpanContext Structure

The `SpanContext` class contains immutable trace propagation data:

```python
from opentelemetry import trace

def inspect_span_context() -> None:
    """Inspect current span context."""
    current_span = trace.get_current_span()
    ctx = current_span.get_span_context()

    print(f"Trace ID (128-bit): {format(ctx.trace_id, '032x')}")
    print(f"Span ID (64-bit): {format(ctx.span_id, '016x')}")
    print(f"Is Remote: {ctx.is_remote}")
    print(f"Trace Flags: {ctx.trace_flags}")
    print(f"Trace State: {ctx.trace_state}")
```

**Key Fields**:
- `trace_id`: 128-bit trace identifier (formatted as 32-char hex)
- `span_id`: 64-bit span identifier (formatted as 16-char hex)
- `is_remote`: True if propagated from a remote parent
- `trace_flags`: Sampling and other flags
- `trace_state`: Vendor-specific trace state

---

## 5. Structlog Integration for Log Correlation

### Structlog Processor for OpenTelemetry

Inject trace_id and span_id into structured logs using a custom processor:

```python
from __future__ import annotations

import structlog
from opentelemetry import trace

def add_opentelemetry_spans(
    logger: structlog.BoundLogger,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor to inject OpenTelemetry trace context.

    Adds span_id, trace_id, and parent_span_id to log records.
    """
    span = trace.get_current_span()

    # Check if span is recording (not a NoOp span)
    if not span.is_recording():
        event_dict["span"] = None
        return event_dict

    # Get span context
    ctx = span.get_span_context()

    # Get parent span if available
    parent = getattr(span, "parent", None)

    # Add trace context to log event
    event_dict["span"] = {
        "span_id": format(ctx.span_id, "016x"),  # 16-char hex
        "trace_id": format(ctx.trace_id, "032x"),  # 32-char hex
        "parent_span_id": None if not parent else format(parent.span_id, "016x"),
    }

    return event_dict


# Configure structlog with OpenTelemetry processor
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_opentelemetry_spans,  # Add trace context
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

# Usage
logger = structlog.get_logger(__name__)

def process_order(order_id: str) -> None:
    """Process order with trace-correlated logs."""
    with tracer.start_as_current_span(
        "process order",
        attributes={"order.id": order_id}
    ) as span:
        # Log automatically includes span_id and trace_id
        logger.info("order_processing_started", order_id=order_id)

        try:
            # Process order
            logger.info("order_validated", order_id=order_id)
            # ...
            logger.info("order_completed", order_id=order_id)
        except Exception as e:
            logger.error("order_failed", order_id=order_id, error=str(e))
            raise
```

**Example Log Output** (JSON):
```json
{
  "event": "order_processing_started",
  "order_id": "12345",
  "timestamp": "2025-12-16T10:30:00.000000Z",
  "level": "info",
  "logger": "my_module",
  "span": {
    "span_id": "00f067aa0ba902b7",
    "trace_id": "00000000000000004bf92f3577b34da6",
    "parent_span_id": null
  }
}
```

### Alternative: Standard Logging Integration

OpenTelemetry provides automatic integration with Python's standard logging:

```python
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Automatically inject trace context into standard logging
LoggingInstrumentor().instrument(
    set_logging_format=True,  # Set format with trace fields
    log_hook=lambda span, record: None,  # Optional custom hook
)

# Log format will include: trace_id=%(otelTraceID)s span_id=%(otelSpanID)s
import logging

logger = logging.getLogger(__name__)

def process_data() -> None:
    """Process data with automatic trace context in logs."""
    with tracer.start_as_current_span("process_data") as span:
        # These logs automatically include trace_id and span_id
        logger.info("Processing started")
        logger.info("Processing completed")
```

**Key Points**:
- Logs not associated with traced operations will have empty trace_id/span_id
- trace_id is formatted as 32-character lowercase hex (no 0x prefix)
- span_id is formatted as 16-character lowercase hex (no 0x prefix)

---

## 6. Graceful Degradation When OTLP Endpoint is Unavailable

### Using NoOpTracerProvider

Disable tracing gracefully when observability is not available:

```python
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.trace import NoOpTracerProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import logging

logger = logging.getLogger(__name__)

def initialize_tracing_with_fallback(
    service_name: str,
    otlp_endpoint: str | None = None,
    enabled: bool = True
) -> trace.TracerProvider:
    """Initialize tracing with graceful fallback to NoOp.

    Args:
        service_name: Service name for resource attributes
        otlp_endpoint: OTLP endpoint (None disables export)
        enabled: Master switch for tracing

    Returns:
        TracerProvider (NoOp if disabled or export fails)
    """
    # Check if tracing is explicitly disabled
    if not enabled:
        logger.info("Tracing disabled - using NoOpTracerProvider")
        provider = NoOpTracerProvider()
        trace.set_tracer_provider(provider)
        return provider

    # If no endpoint provided, use NoOp
    if not otlp_endpoint:
        logger.warning("No OTLP endpoint provided - using NoOpTracerProvider")
        provider = NoOpTracerProvider()
        trace.set_tracer_provider(provider)
        return provider

    try:
        # Create real TracerProvider
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource

        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)

        # Try to create exporter
        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,
            timeout=5,  # Short timeout for quick failure
        )

        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)
        logger.info(f"Tracing initialized successfully: {otlp_endpoint}")

        return provider

    except Exception as e:
        # If setup fails, fall back to NoOp
        logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
        logger.warning("Falling back to NoOpTracerProvider")

        provider = NoOpTracerProvider()
        trace.set_tracer_provider(provider)
        return provider


# Usage
tracer_provider = initialize_tracing_with_fallback(
    service_name="floe-runtime",
    otlp_endpoint="http://localhost:4317",
    enabled=True
)

# Get tracer (works whether real or NoOp)
tracer = trace.get_tracer(__name__)

# This code works regardless of tracing state
with tracer.start_as_current_span("operation") as span:
    span.set_attribute("key", "value")
    # If NoOp: all operations are no-ops
    # If real: operations are recorded
```

### Environment Variable Fallback

```python
import os
from opentelemetry import trace
from opentelemetry.trace import NoOpTracerProvider

def initialize_from_environment() -> trace.TracerProvider:
    """Initialize tracing from environment with fallback."""
    # Check SDK disable flag
    sdk_disabled = os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true"
    if sdk_disabled:
        logger.info("OTEL_SDK_DISABLED=true - using NoOpTracerProvider")
        provider = NoOpTracerProvider()
        trace.set_tracer_provider(provider)
        return provider

    # Get endpoint from environment
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        logger.warning("OTEL_EXPORTER_OTLP_ENDPOINT not set - using NoOpTracerProvider")
        provider = NoOpTracerProvider()
        trace.set_tracer_provider(provider)
        return provider

    # Initialize with endpoint
    return initialize_tracing_with_fallback(
        service_name=os.getenv("OTEL_SERVICE_NAME", "unknown-service"),
        otlp_endpoint=otlp_endpoint,
        enabled=True
    )
```

### Handling Export Failures

OpenTelemetry exporters have built-in retry logic with exponential backoff:

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# BatchSpanProcessor configuration for resilience
processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,  # Max spans queued (default)
    schedule_delay_millis=5000,  # Export every 5 seconds (default)
    max_export_batch_size=512,  # Max spans per batch (default)
    export_timeout_millis=30000,  # Export timeout (default)
)
```

**Known Issues**:
- When OTLP endpoint becomes unavailable, the SDK logs warnings like:
  ```
  Transient error StatusCode.UNAVAILABLE encountered while exporting metrics, retrying in 8s.
  ```
- Exporters use exponential backoff with jitter for retries
- If endpoint remains unavailable beyond max retry duration (default 5 minutes), oldest data is dropped

### Graceful Shutdown

```python
def shutdown_tracing() -> None:
    """Gracefully shutdown tracing."""
    provider = trace.get_tracer_provider()

    # Only shutdown if it's a real provider (not NoOp)
    if hasattr(provider, "shutdown"):
        logger.info("Shutting down TracerProvider")
        provider.shutdown()

        # After shutdown, subsequent get_tracer() calls return NoOp
```

**Important**: Shutdown must be called only once per TracerProvider. After shutdown:
- Subsequent `get_tracer()` calls return NoOp tracers
- Calls to `OnStart`, `OnEnd`, `ForceFlush` are ignored gracefully

---

## 7. Best Practices for Span Naming and Attributes

### Span Naming Conventions

#### The {verb} {object} Pattern

Use the `{verb} {object}` pattern for span names to ensure low cardinality:

```python
# Good: Low-cardinality span names
with tracer.start_as_current_span("process payment") as span:
    span.set_attribute("payment.id", "12345")  # High-cardinality data in attributes

with tracer.start_as_current_span("send email") as span:
    span.set_attribute("email.recipient", "user@example.com")

with tracer.start_as_current_span("calculate total") as span:
    span.set_attribute("calculation.type", "order_total")

# Bad: High-cardinality span names
with tracer.start_as_current_span(f"process payment {payment_id}"):  # ❌
    pass

with tracer.start_as_current_span(f"send email to {email}"):  # ❌
    pass
```

**Why Low Cardinality Matters**:
- Enables grouping all spans for the same operation
- Reduces storage costs
- Improves query performance
- Makes metrics aggregation possible

#### Semantic Convention Patterns

Follow semantic conventions for common operations:

```python
# HTTP spans: {method} {route}
with tracer.start_as_current_span("GET /api/users/:id"):
    pass

# Database spans: {db.operation} {db.name}.{db.collection}
with tracer.start_as_current_span("SELECT customers"):
    pass

# RPC spans: {rpc.service}/{rpc.method}
with tracer.start_as_current_span("UserService/GetUser"):
    pass

# Messaging spans: {destination} send/receive
with tracer.start_as_current_span("orders send"):
    pass
```

### Attribute Naming Conventions

#### Structure Pattern: {domain}.{component}.{property}

Use dot notation to separate hierarchical components:

```python
# Good: Structured attribute names
span.set_attribute("database.connection.pool_size", 10)
span.set_attribute("http.request.body.size", 1024)
span.set_attribute("pipeline.stage.duration_ms", 500)

# Bad: Flat attribute names
span.set_attribute("db_conn_pool_size", 10)  # ❌
span.set_attribute("requestBodySize", 1024)  # ❌
```

#### Use Semantic Conventions When Available

```python
from opentelemetry.semconv.trace import SpanAttributes

# Always use semantic conventions when they match your use case
span.set_attribute(SpanAttributes.HTTP_METHOD, "POST")
span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, 200)
span.set_attribute(SpanAttributes.DB_SYSTEM, "postgresql")
span.set_attribute(SpanAttributes.DB_NAME, "customers")
span.set_attribute(SpanAttributes.DB_OPERATION, "SELECT")
```

**Available Semantic Attribute Categories**:
- `http.*`: HTTP client/server attributes
- `db.*`: Database attributes
- `messaging.*`: Message queue attributes
- `rpc.*`: RPC attributes
- `network.*`: Network attributes
- `server.*`: Server attributes

#### Custom Attribute Naming

When creating custom attributes, follow these rules:

```python
# Start with domain/technology, NOT company name
span.set_attribute("pipeline.stage", "transform")  # ✅
span.set_attribute("acme.pipeline.stage", "transform")  # ❌

# Use reverse domain for company-specific attributes
span.set_attribute("com.acme.custom_field", "value")  # ✅

# Use lowercase with underscores
span.set_attribute("order.total_amount", 99.99)  # ✅
span.set_attribute("order.totalAmount", 99.99)  # ❌ (camelCase)
span.set_attribute("order.TotalAmount", 99.99)  # ❌ (PascalCase)
```

#### Character Set Restrictions

- Use printable Basic Latin characters (U+0021 to U+007E)
- Recommended: lowercase letters, numbers, underscore, dot
- Must start with a letter
- Must end with alphanumeric character
- No consecutive delimiters (`..` or `__`)

```python
# Valid attribute names
span.set_attribute("my_attribute", "value")  # ✅
span.set_attribute("my.nested.attribute", "value")  # ✅
span.set_attribute("attr123", "value")  # ✅

# Invalid attribute names
span.set_attribute("_private", "value")  # ❌ (starts with underscore)
span.set_attribute("my..attribute", "value")  # ❌ (consecutive dots)
span.set_attribute("my-attribute", "value")  # ❌ (hyphen not recommended)
```

#### Reserved Namespaces

**NEVER use the `otel.*` prefix** - it's reserved for OpenTelemetry specification:

```python
# Forbidden: otel.* namespace is reserved
span.set_attribute("otel.custom_field", "value")  # ❌

# Correct: Use your own namespace
span.set_attribute("custom.field", "value")  # ✅
```

### Complete Example: Best Practices

```python
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.semconv.trace import SpanAttributes
from typing import Any

tracer = trace.get_tracer(__name__)

def process_customer_order(order_id: str, customer_id: str) -> dict[str, Any]:
    """Process customer order with OpenTelemetry best practices.

    Demonstrates:
    - Low-cardinality span name ({verb} {object})
    - High-cardinality data in attributes
    - Semantic conventions where applicable
    - Structured custom attributes
    - Nested spans with context propagation
    """
    # Parent span: Low-cardinality name
    with tracer.start_as_current_span(
        "process order",  # {verb} {object} pattern
        attributes={
            # High-cardinality identifiers in attributes
            "order.id": order_id,
            "order.customer_id": customer_id,
            "order.source": "web",
        }
    ) as span:
        # Child span: Validate order
        with tracer.start_as_current_span(
            "validate order",
            attributes={
                "validation.type": "business_rules",
            }
        ) as validation_span:
            is_valid = validate_order(order_id)
            validation_span.set_attribute("validation.success", is_valid)

        # Child span: Fetch customer data (database operation)
        with tracer.start_as_current_span(
            "SELECT customers",  # Semantic convention for DB
            attributes={
                SpanAttributes.DB_SYSTEM: "postgresql",
                SpanAttributes.DB_NAME: "orders_db",
                SpanAttributes.DB_OPERATION: "SELECT",
                SpanAttributes.DB_SQL_TABLE: "customers",
                "db.query.duration_ms": 15,
            }
        ) as db_span:
            customer = fetch_customer(customer_id)

        # Child span: Call payment service (HTTP operation)
        with tracer.start_as_current_span(
            "POST /api/payments",  # {method} {route} pattern
            attributes={
                SpanAttributes.HTTP_METHOD: "POST",
                SpanAttributes.HTTP_URL: "https://payment.api/api/payments",
                SpanAttributes.HTTP_REQUEST_CONTENT_LENGTH: 256,
            }
        ) as http_span:
            payment_result = process_payment(order_id)
            http_span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, 200)

        # Set final attributes on parent span
        span.set_attribute("order.status", "completed")
        span.set_attribute("order.total_amount", 99.99)
        span.set_attribute("order.processing_time_ms", 1234)

        return {
            "order_id": order_id,
            "status": "completed",
        }
```

---

## 8. Complete Working Example

```python
from __future__ import annotations

import os
import logging
import structlog
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import NoOpTracerProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.semconv.trace import SpanAttributes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_opentelemetry_spans(
    logger: structlog.BoundLogger,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inject OpenTelemetry trace context into logs."""
    span = trace.get_current_span()

    if not span.is_recording():
        event_dict["span"] = None
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["span"] = {
        "span_id": format(ctx.span_id, "016x"),
        "trace_id": format(ctx.trace_id, "032x"),
        "parent_span_id": None if not parent else format(parent.span_id, "016x"),
    }

    return event_dict


# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_opentelemetry_spans,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

slog = structlog.get_logger(__name__)


def initialize_tracing(
    service_name: str,
    otlp_endpoint: str | None = None,
    enabled: bool = True
) -> trace.TracerProvider:
    """Initialize OpenTelemetry tracing with graceful fallback."""
    if not enabled or not otlp_endpoint:
        logger.info("Tracing disabled - using NoOpTracerProvider")
        provider = NoOpTracerProvider()
        trace.set_tracer_provider(provider)
        return provider

    try:
        resource = Resource(attributes={
            SERVICE_NAME: service_name,
            "service.version": "1.0.0",
        })

        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,
            timeout=5,
        )

        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)
        logger.info(f"Tracing initialized: {otlp_endpoint}")

        return provider

    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
        provider = NoOpTracerProvider()
        trace.set_tracer_provider(provider)
        return provider


# Initialize tracing
tracer_provider = initialize_tracing(
    service_name="floe-runtime",
    otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
    enabled=os.getenv("OTEL_SDK_DISABLED", "false").lower() != "true"
)

# Get tracer
tracer = trace.get_tracer(__name__)


def process_pipeline(pipeline_id: str) -> dict[str, Any]:
    """Process data pipeline with tracing and log correlation."""
    with tracer.start_as_current_span(
        "process pipeline",
        attributes={
            "pipeline.id": pipeline_id,
            "pipeline.version": "2.0.0",
        }
    ) as span:
        slog.info("pipeline_started", pipeline_id=pipeline_id)

        try:
            # Extract stage
            with tracer.start_as_current_span(
                "extract data",
                attributes={
                    "pipeline.stage": "extract",
                }
            ) as extract_span:
                slog.info("extract_started", pipeline_id=pipeline_id)
                records = extract_data()
                extract_span.set_attribute("extract.record_count", len(records))
                slog.info("extract_completed", record_count=len(records))

            # Transform stage
            with tracer.start_as_current_span(
                "transform data",
                attributes={
                    "pipeline.stage": "transform",
                }
            ) as transform_span:
                slog.info("transform_started", pipeline_id=pipeline_id)
                transformed = transform_data(records)
                transform_span.set_attribute("transform.record_count", len(transformed))
                slog.info("transform_completed", record_count=len(transformed))

            # Load stage (database operation)
            with tracer.start_as_current_span(
                "INSERT records",
                attributes={
                    SpanAttributes.DB_SYSTEM: "postgresql",
                    SpanAttributes.DB_NAME: "warehouse",
                    SpanAttributes.DB_OPERATION: "INSERT",
                    SpanAttributes.DB_SQL_TABLE: "fact_table",
                    "pipeline.stage": "load",
                }
            ) as load_span:
                slog.info("load_started", pipeline_id=pipeline_id)
                load_data(transformed)
                load_span.set_attribute("load.record_count", len(transformed))
                slog.info("load_completed", record_count=len(transformed))

            # Set final span attributes
            span.set_attribute("pipeline.status", "completed")
            span.set_attribute("pipeline.total_records", len(transformed))
            slog.info("pipeline_completed", pipeline_id=pipeline_id, status="success")

            return {
                "pipeline_id": pipeline_id,
                "status": "completed",
                "records": len(transformed),
            }

        except Exception as e:
            span.set_attribute("pipeline.status", "failed")
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            slog.error("pipeline_failed", pipeline_id=pipeline_id, error=str(e))
            raise


def extract_data() -> list[dict[str, Any]]:
    """Extract data from source."""
    return [{"id": i, "value": i * 10} for i in range(100)]


def transform_data(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transform data."""
    return [{"id": r["id"], "value": r["value"] * 2} for r in records]


def load_data(records: list[dict[str, Any]]) -> None:
    """Load data to destination."""
    pass  # Simulate database insert


if __name__ == "__main__":
    # Run pipeline
    result = process_pipeline("pipeline-123")
    print(f"Result: {result}")

    # Graceful shutdown
    if hasattr(tracer_provider, "shutdown"):
        tracer_provider.shutdown()
```

---

## Summary

### Key Takeaways

1. **TracerProvider**: Use a single global TracerProvider, set once at startup
2. **Span Creation**: Use `start_as_current_span()` with descriptive names following `{verb} {object}` pattern
3. **Attributes**: Set attributes at span creation for samplers; use semantic conventions when available
4. **OTLP Export**: Configure via code or environment variables; use gRPC (port 4317) or HTTP (port 4318)
5. **Context Propagation**: Automatic for nested spans; manual inject/extract for cross-service calls
6. **Structlog Integration**: Use custom processor to inject trace_id and span_id into logs
7. **Graceful Degradation**: Use NoOpTracerProvider when tracing is disabled or unavailable
8. **Span Naming**: Low-cardinality names, high-cardinality data in attributes
9. **Attribute Naming**: Use `{domain}.{component}.{property}` structure with semantic conventions

### Installation

```bash
# Core packages
pip install opentelemetry-api opentelemetry-sdk

# OTLP exporters
pip install opentelemetry-exporter-otlp-proto-grpc  # For gRPC
pip install opentelemetry-exporter-otlp-proto-http  # For HTTP

# Semantic conventions
pip install opentelemetry-semantic-conventions

# Structlog (for log correlation)
pip install structlog
```

---

## Sources

### Span Creation and Attributes
- [OpenTelemetry Python Span API](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.span.html)
- [Python Instrumentation Guide](https://opentelemetry.io/docs/languages/python/instrumentation/)
- [OpenTelemetry Trace Package](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html)
- [OpenTelemetry SDK Trace](https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.html)
- [Python Cookbook](https://opentelemetry.io/docs/languages/python/cookbook/)

### OTLP Exporter Configuration
- [OTLP Exporter Configuration](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/)
- [OpenTelemetry OTLP Exporters](https://opentelemetry-python.readthedocs.io/en/latest/exporter/otlp/otlp.html)
- [Python Exporters Guide](https://opentelemetry.io/docs/languages/python/exporters/)
- [opentelemetry-exporter-otlp-proto-grpc PyPI](https://pypi.org/project/opentelemetry-exporter-otlp-proto-grpc/)

### Context Propagation
- [Python Propagation Guide](https://opentelemetry.io/docs/languages/python/propagation/)
- [Context Propagation Concepts](https://opentelemetry.io/docs/concepts/context-propagation/)
- [Basic Context Examples](https://opentelemetry-python.readthedocs.io/en/stable/examples/basic_context/README.html)
- [OpenTelemetry Context Propagation (Last9)](https://last9.io/blog/opentelemetry-context-propagation/)

### Structlog Integration
- [OpenTelemetry Logging Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html)
- [Structlog Frameworks Integration](https://www.structlog.org/en/stable/frameworks.html)
- [Python TraceId and SpanId Injection (Sumo Logic)](https://help.sumologic.com/docs/apm/traces/get-started-transaction-tracing/opentelemetry-instrumentation/python/traceid-spanid-injection-into-logs/)

### Graceful Degradation
- [Tracing SDK Specification](https://opentelemetry.io/docs/specs/otel/trace/sdk/)
- [OpenTelemetry Trace Package](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html)
- [Collector Resiliency](https://opentelemetry.io/docs/collector/resiliency/)
- [OTLP Protocol Exporter](https://opentelemetry.io/docs/specs/otel/protocol/exporter/)

### Best Practices
- [How to Name Your Spans](https://opentelemetry.io/blog/2025/how-to-name-your-spans/)
- [How to Name Your Span Attributes](https://opentelemetry.io/blog/2025/how-to-name-your-span-attributes/)
- [OpenTelemetry Best Practices: Naming (Honeycomb)](https://www.honeycomb.io/blog/opentelemetry-best-practices-naming)
- [Semantic Conventions Overview](https://opentelemetry.io/docs/concepts/semantic-conventions/)
- [Semantic Naming Conventions](https://opentelemetry.io/docs/specs/semconv/general/naming/)
- [OTel Naming Best Practices (Last9)](https://last9.io/blog/otel-naming-best-practices/)

### TracerProvider Setup
- [Python Instrumentation Guide](https://opentelemetry.io/docs/languages/python/instrumentation/)
- [Python Cookbook](https://opentelemetry.io/docs/languages/python/cookbook/)
- [OpenTelemetry Trace Package](https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html)
- [Quick Guide for Python Instrumentation (Last9)](https://last9.io/blog/opentelemetry-python-instrumentation/)
