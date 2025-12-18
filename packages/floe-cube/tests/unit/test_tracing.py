"""Unit tests for OpenTelemetry tracing functionality.

T060-T064: [US7] Unit tests for OpenTelemetry tracing.
T067-T071: [US7] Unit tests for QueryTracer class.

Tests cover:
- QueryTraceSpan model validation (T060)
- Span hierarchy creation (T061)
- Safe attribute validation (T062)
- W3C Trace Context extraction (T063)
- Tracing disabled behavior (T064)
- QueryTracer class functionality (T067-T071)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from floe_cube.models import (
    FORBIDDEN_SPAN_ATTRIBUTES,
    QueryTraceSpan,
    SpanKind,
    SpanStatus,
)
from floe_cube.tracing import QueryTracer, create_noop_tracer

if TYPE_CHECKING:
    pass


class TestQueryTraceSpanValidation:
    """T060: Unit test QueryTraceSpan model validates required fields."""

    def test_valid_span(self) -> None:
        """QueryTraceSpan should accept valid W3C format IDs."""
        span = QueryTraceSpan(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
            status=SpanStatus.UNSET,
        )

        assert span.trace_id == "0af7651916cd43dd8448eb211c80319c"
        assert span.span_id == "b7ad6b7169203331"
        assert span.name == "cube.query"
        assert span.kind == SpanKind.SERVER
        assert span.status == SpanStatus.UNSET
        assert span.parent_span_id is None
        assert span.end_time is None
        assert span.attributes == {}

    def test_trace_id_required(self) -> None:
        """QueryTraceSpan should require trace_id."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
            )

        assert "trace_id" in str(exc_info.value)

    def test_span_id_required(self) -> None:
        """QueryTraceSpan should require span_id."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
            )

        assert "span_id" in str(exc_info.value)

    def test_name_required(self) -> None:
        """QueryTraceSpan should require name."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
            )

        assert "name" in str(exc_info.value)

    def test_kind_required(self) -> None:
        """QueryTraceSpan should require kind."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                name="cube.query",
                start_time=datetime.now(tz=timezone.utc),
            )

        assert "kind" in str(exc_info.value)

    def test_start_time_required(self) -> None:
        """QueryTraceSpan should require start_time."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
            )

        assert "start_time" in str(exc_info.value)

    def test_trace_id_must_be_32_hex(self) -> None:
        """QueryTraceSpan trace_id must be 32 lowercase hex characters."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="invalid",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
            )

        assert "32 lowercase hex" in str(exc_info.value)

    def test_trace_id_rejects_uppercase(self) -> None:
        """QueryTraceSpan trace_id must be lowercase."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0AF7651916CD43DD8448EB211C80319C",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
            )

        assert "32 lowercase hex" in str(exc_info.value)

    def test_span_id_must_be_16_hex(self) -> None:
        """QueryTraceSpan span_id must be 16 lowercase hex characters."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="invalid",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
            )

        assert "16 lowercase hex" in str(exc_info.value)

    def test_parent_span_id_validation(self) -> None:
        """QueryTraceSpan parent_span_id must be valid format if provided."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                parent_span_id="invalid",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
            )

        assert "16 lowercase hex" in str(exc_info.value)

    def test_valid_parent_span_id(self) -> None:
        """QueryTraceSpan should accept valid parent_span_id."""
        span = QueryTraceSpan(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            parent_span_id="c7ad6b7169203332",
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
        )

        assert span.parent_span_id == "c7ad6b7169203332"

    def test_is_frozen(self) -> None:
        """QueryTraceSpan should be immutable."""
        span = QueryTraceSpan(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
        )

        with pytest.raises(ValidationError):
            span.name = "modified"  # type: ignore[misc]

    def test_rejects_extra_fields(self) -> None:
        """QueryTraceSpan should reject extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()


class TestSpanHierarchy:
    """T061: Unit test tracer creates span hierarchy."""

    def test_span_hierarchy_names(self) -> None:
        """Span names should follow cube.* convention for hierarchy."""
        start = datetime.now(tz=timezone.utc)
        parent_span_id = "c7ad6b7169203332"

        # Root SERVER span
        root_span = QueryTraceSpan(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=start,
        )

        # Child INTERNAL span
        parse_span = QueryTraceSpan(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="a7ad6b7169203333",
            parent_span_id=root_span.span_id,
            name="cube.parse",
            kind=SpanKind.INTERNAL,
            start_time=start,
        )

        # Verify hierarchy
        assert root_span.parent_span_id is None
        assert parse_span.parent_span_id == root_span.span_id
        assert root_span.kind == SpanKind.SERVER
        assert parse_span.kind == SpanKind.INTERNAL

    def test_span_kinds_valid(self) -> None:
        """All SpanKind values should be valid."""
        assert SpanKind.SERVER.value == "SERVER"
        assert SpanKind.CLIENT.value == "CLIENT"
        assert SpanKind.INTERNAL.value == "INTERNAL"

    def test_span_statuses_valid(self) -> None:
        """All SpanStatus values should be valid."""
        assert SpanStatus.OK.value == "OK"
        assert SpanStatus.ERROR.value == "ERROR"
        assert SpanStatus.UNSET.value == "UNSET"

    def test_full_span_hierarchy(self) -> None:
        """Create a realistic span hierarchy for a query."""
        trace_id = "0af7651916cd43dd8448eb211c80319c"
        start = datetime.now(tz=timezone.utc)

        # cube.query (root SERVER span)
        query_span = QueryTraceSpan(
            trace_id=trace_id,
            span_id="b7ad6b7169203331",
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=start,
        )

        # cube.parse (INTERNAL)
        parse_span = QueryTraceSpan(
            trace_id=trace_id,
            span_id="a7ad6b7169203332",
            parent_span_id=query_span.span_id,
            name="cube.parse",
            kind=SpanKind.INTERNAL,
            start_time=start,
        )

        # cube.security (INTERNAL)
        security_span = QueryTraceSpan(
            trace_id=trace_id,
            span_id="a7ad6b7169203333",
            parent_span_id=query_span.span_id,
            name="cube.security",
            kind=SpanKind.INTERNAL,
            start_time=start,
        )

        # cube.execute (INTERNAL)
        execute_span = QueryTraceSpan(
            trace_id=trace_id,
            span_id="a7ad6b7169203334",
            parent_span_id=query_span.span_id,
            name="cube.execute",
            kind=SpanKind.INTERNAL,
            start_time=start,
        )

        # database.query (CLIENT - actual DB call)
        db_span = QueryTraceSpan(
            trace_id=trace_id,
            span_id="a7ad6b7169203335",
            parent_span_id=execute_span.span_id,
            name="database.query",
            kind=SpanKind.CLIENT,
            start_time=start,
        )

        # cube.response (INTERNAL)
        response_span = QueryTraceSpan(
            trace_id=trace_id,
            span_id="a7ad6b7169203336",
            parent_span_id=query_span.span_id,
            name="cube.response",
            kind=SpanKind.INTERNAL,
            start_time=start,
        )

        # Verify all spans share same trace_id
        assert all(
            s.trace_id == trace_id
            for s in [
                query_span,
                parse_span,
                security_span,
                execute_span,
                db_span,
                response_span,
            ]
        )

        # Verify hierarchy: db_span is child of execute_span
        assert db_span.parent_span_id == execute_span.span_id

        # Verify hierarchy: execute_span is child of query_span
        assert execute_span.parent_span_id == query_span.span_id


class TestSafeAttributes:
    """T062: Unit test span attributes include safe metadata only."""

    def test_safe_attributes_allowed(self) -> None:
        """Safe attributes like cube.name should be allowed."""
        span = QueryTraceSpan(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
            attributes={
                "cube.name": "orders",
                "cube.measures_count": 2,
                "cube.dimensions_count": 3,
                "cube.filter_count": 1,
                "cube.row_count": 100,
            },
        )

        assert span.attributes["cube.name"] == "orders"
        assert span.attributes["cube.measures_count"] == 2
        assert span.attributes["cube.filter_count"] == 1

    def test_boolean_attributes_allowed(self) -> None:
        """Boolean attributes should be allowed."""
        span = QueryTraceSpan(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
            attributes={
                "cube.cache_hit": True,
                "cube.pre_aggregation_used": False,
            },
        )

        assert span.attributes["cube.cache_hit"] is True
        assert span.attributes["cube.pre_aggregation_used"] is False

    def test_forbidden_filter_value_rejected(self) -> None:
        """Attributes containing 'filter_value' should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
                attributes={"filter_value": "org_abc"},
            )

        assert "filter_value" in str(exc_info.value)
        assert "security" in str(exc_info.value).lower()

    def test_forbidden_jwt_rejected(self) -> None:
        """Attributes containing 'jwt' should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
                attributes={"jwt_token": "eyJ..."},
            )

        assert "jwt" in str(exc_info.value)

    def test_forbidden_password_rejected(self) -> None:
        """Attributes containing 'password' should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
                attributes={"user_password": "secret123"},
            )

        assert "password" in str(exc_info.value)

    def test_forbidden_row_data_rejected(self) -> None:
        """Attributes containing 'row_data' should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
                attributes={"query_row_data": "sensitive"},
            )

        assert "row_data" in str(exc_info.value)

    def test_forbidden_api_key_rejected(self) -> None:
        """Attributes containing 'api_key' should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
                attributes={"cube_api_key": "xyz123"},
            )

        assert "api_key" in str(exc_info.value)

    def test_forbidden_user_email_rejected(self) -> None:
        """Attributes containing 'user_email' should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
                attributes={"user_email": "user@example.com"},
            )

        assert "user_email" in str(exc_info.value)

    def test_forbidden_attributes_set_is_complete(self) -> None:
        """FORBIDDEN_SPAN_ATTRIBUTES should contain all forbidden terms."""
        assert "filter_value" in FORBIDDEN_SPAN_ATTRIBUTES
        assert "jwt" in FORBIDDEN_SPAN_ATTRIBUTES
        assert "token" in FORBIDDEN_SPAN_ATTRIBUTES
        assert "password" in FORBIDDEN_SPAN_ATTRIBUTES
        assert "secret" in FORBIDDEN_SPAN_ATTRIBUTES
        assert "api_key" in FORBIDDEN_SPAN_ATTRIBUTES
        assert "row_data" in FORBIDDEN_SPAN_ATTRIBUTES
        assert "pii" in FORBIDDEN_SPAN_ATTRIBUTES

    def test_case_insensitive_forbidden_check(self) -> None:
        """Forbidden attribute check should be case-insensitive."""
        with pytest.raises(ValidationError):
            QueryTraceSpan(
                trace_id="0af7651916cd43dd8448eb211c80319c",
                span_id="b7ad6b7169203331",
                name="cube.query",
                kind=SpanKind.SERVER,
                start_time=datetime.now(tz=timezone.utc),
                attributes={"JWT_TOKEN": "eyJ..."},
            )


class TestW3CTraceContext:
    """T063: Unit test W3C Trace Context extraction from headers."""

    def test_valid_trace_context_ids(self) -> None:
        """W3C Trace Context IDs should be valid format."""
        # Example from W3C Trace Context spec
        trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        span_id = "00f067aa0ba902b7"

        span = QueryTraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
        )

        assert span.trace_id == trace_id
        assert span.span_id == span_id

    def test_traceparent_header_format(self) -> None:
        """Validate trace IDs match W3C traceparent format."""
        # W3C traceparent format: {version}-{trace-id}-{parent-id}-{trace-flags}
        # Example: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
        trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        parent_span_id = "00f067aa0ba902b7"
        span_id = "b7ad6b7169203331"

        span = QueryTraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
        )

        # Verify IDs can be used to construct traceparent header
        reconstructed = f"00-{span.trace_id}-{span.parent_span_id}-01"
        assert reconstructed == f"00-{trace_id}-{parent_span_id}-01"

    def test_propagated_context_inheritance(self) -> None:
        """Spans should inherit trace_id from propagated context."""
        propagated_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        propagated_span_id = "00f067aa0ba902b7"

        # Child span from propagated context
        child_span = QueryTraceSpan(
            trace_id=propagated_trace_id,  # Same trace_id
            span_id="b7ad6b7169203331",  # New span_id
            parent_span_id=propagated_span_id,  # Parent from incoming request
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
        )

        assert child_span.trace_id == propagated_trace_id
        assert child_span.parent_span_id == propagated_span_id
        assert child_span.span_id != propagated_span_id  # New span has new ID


class TestTracingDisabled:
    """T064: Unit test tracing disabled produces no spans.

    Note: This tests the model behavior. When tracing is disabled,
    the QueryTracer class (not yet implemented) should not create
    any QueryTraceSpan instances.
    """

    def test_span_model_exists_independent_of_tracing_flag(self) -> None:
        """QueryTraceSpan model should exist regardless of tracing flag.

        The model itself doesn't have a 'disabled' state - that's
        controlled by the TracerProvider configuration.
        """
        # Model can always be instantiated
        span = QueryTraceSpan(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
        )

        assert span is not None

    def test_span_attributes_for_disabled_detection(self) -> None:
        """Tracing disabled can be indicated via attributes."""
        # This pattern allows downstream code to detect disabled tracing
        span = QueryTraceSpan(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
            attributes={"tracing.sampled": False},
        )

        assert span.attributes.get("tracing.sampled") is False


class TestQueryTracerInitialization:
    """T067: Unit test TracerProvider initialization."""

    def test_tracer_default_initialization(self) -> None:
        """QueryTracer should initialize with default settings."""
        tracer = QueryTracer()

        assert tracer.service_name == "floe-cube"
        assert tracer.enabled is True

    def test_tracer_custom_service_name(self) -> None:
        """QueryTracer should accept custom service name."""
        tracer = QueryTracer(service_name="my-cube-service")

        assert tracer.service_name == "my-cube-service"

    def test_tracer_disabled_mode(self) -> None:
        """QueryTracer should support disabled mode."""
        tracer = QueryTracer(enabled=False)

        assert tracer.enabled is False

    def test_noop_tracer_factory(self) -> None:
        """create_noop_tracer should return disabled tracer."""
        tracer = create_noop_tracer()

        assert tracer.enabled is False

    def test_tracer_otlp_endpoint(self) -> None:
        """QueryTracer should accept OTLP endpoint."""
        tracer = QueryTracer(otlp_endpoint="http://localhost:4317")

        assert tracer.otlp_endpoint == "http://localhost:4317"


class TestQueryTracerTraceQuery:
    """T068: Unit test trace_query function with W3C context extraction."""

    def test_trace_query_creates_span(self) -> None:
        """trace_query should create a span when enabled."""
        tracer = QueryTracer()

        with tracer.trace_query(cube_name="orders") as span:
            assert span is not None
            assert span.name == "cube.query"
            assert span.kind == SpanKind.SERVER
            assert span.attributes["cube.name"] == "orders"

    def test_trace_query_disabled_returns_none(self) -> None:
        """trace_query should return None when disabled."""
        tracer = QueryTracer(enabled=False)

        with tracer.trace_query(cube_name="orders") as span:
            assert span is None

    def test_trace_query_extracts_traceparent(self) -> None:
        """trace_query should extract W3C traceparent header."""
        tracer = QueryTracer()
        traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

        with tracer.trace_query(
            cube_name="orders",
            headers={"traceparent": traceparent},
        ) as span:
            assert span is not None
            assert span.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
            assert span.parent_span_id == "00f067aa0ba902b7"

    def test_trace_query_generates_trace_id_without_header(self) -> None:
        """trace_query should generate trace_id when no traceparent."""
        tracer = QueryTracer()

        with tracer.trace_query(cube_name="orders") as span:
            assert span is not None
            assert len(span.trace_id) == 32
            assert span.parent_span_id is None

    def test_trace_query_with_all_attributes(self) -> None:
        """trace_query should include all safe attributes."""
        tracer = QueryTracer()

        with tracer.trace_query(
            cube_name="orders",
            measures_count=3,
            dimensions_count=2,
            filter_count=1,
            openlineage_run_id="abc-123",
        ) as span:
            assert span is not None
            assert span.attributes["cube.name"] == "orders"
            assert span.attributes["cube.measures_count"] == 3
            assert span.attributes["cube.dimensions_count"] == 2
            assert span.attributes["cube.filter_count"] == 1
            assert span.attributes["openlineage.run_id"] == "abc-123"


class TestQueryTracerSpanHierarchy:
    """T069: Unit test span hierarchy creation."""

    def test_create_child_span(self) -> None:
        """create_child_span should create child with parent link."""
        tracer = QueryTracer()

        with tracer.trace_query(cube_name="orders") as parent:
            assert parent is not None
            child = tracer.create_child_span(
                parent=parent,
                name="cube.execute",
            )

            assert child is not None
            assert child.trace_id == parent.trace_id
            assert child.parent_span_id == parent.span_id
            assert child.name == "cube.execute"
            assert child.kind == SpanKind.INTERNAL

    def test_create_child_span_with_custom_kind(self) -> None:
        """create_child_span should support custom kind."""
        tracer = QueryTracer()

        with tracer.trace_query(cube_name="orders") as parent:
            assert parent is not None
            child = tracer.create_child_span(
                parent=parent,
                name="database.query",
                kind=SpanKind.CLIENT,
            )

            assert child is not None
            assert child.kind == SpanKind.CLIENT

    def test_create_child_span_disabled_returns_none(self) -> None:
        """create_child_span should return None when disabled."""
        tracer = QueryTracer(enabled=False)

        # Create a mock parent span for testing
        parent = QueryTraceSpan(
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            name="cube.query",
            kind=SpanKind.SERVER,
            start_time=datetime.now(tz=timezone.utc),
        )

        child = tracer.create_child_span(parent=parent, name="cube.execute")
        assert child is None


class TestQueryTracerSafeAttributes:
    """T070: Unit test safe attribute injection."""

    def test_inject_safe_attributes(self) -> None:
        """inject_safe_attributes should add safe attributes."""
        tracer = QueryTracer()

        with tracer.trace_query(cube_name="orders") as span:
            assert span is not None
            updated = tracer.inject_safe_attributes(
                span,
                {"cube.cache_hit": True, "cube.execution_time_ms": 150},
            )

            assert updated is not None
            assert updated.attributes["cube.cache_hit"] is True
            assert updated.attributes["cube.execution_time_ms"] == 150

    def test_inject_safe_attributes_filters_forbidden(self) -> None:
        """inject_safe_attributes should filter forbidden attributes."""
        tracer = QueryTracer()

        with tracer.trace_query(cube_name="orders") as span:
            assert span is not None
            updated = tracer.inject_safe_attributes(
                span,
                {
                    "cube.name": "orders",
                    "jwt_token": "eyJ...",  # Should be filtered
                    "password": "secret",  # Should be filtered
                },
            )

            assert updated is not None
            assert updated.attributes["cube.name"] == "orders"
            assert "jwt_token" not in updated.attributes
            assert "password" not in updated.attributes

    def test_inject_safe_attributes_none_span(self) -> None:
        """inject_safe_attributes should handle None span."""
        tracer = QueryTracer()

        result = tracer.inject_safe_attributes(None, {"key": "value"})
        assert result is None

    def test_create_span_filters_unsafe_attributes(self) -> None:
        """create_span should filter unsafe attributes."""
        tracer = QueryTracer()

        span = tracer.create_span(
            name="test.span",
            kind=SpanKind.INTERNAL,
            attributes={
                "safe.key": "value",
                "api_key_secret": "should_be_filtered",
            },
        )

        assert span is not None
        assert "safe.key" in span.attributes
        assert "api_key_secret" not in span.attributes


class TestQueryTracerRecordResult:
    """T071: Unit test record_query_result for span status."""

    def test_record_query_result_sets_row_count(self) -> None:
        """record_query_result should set row_count attribute."""
        tracer = QueryTracer()

        with tracer.trace_query(cube_name="orders") as span:
            assert span is not None
            updated = tracer.record_query_result(span, row_count=100)

            assert updated is not None
            assert updated.attributes["cube.row_count"] == 100
            assert updated.status == SpanStatus.OK
            assert updated.end_time is not None

    def test_record_query_result_sets_error_status(self) -> None:
        """record_query_result should set ERROR status."""
        tracer = QueryTracer()

        with tracer.trace_query(cube_name="orders") as span:
            assert span is not None
            updated = tracer.record_query_result(
                span,
                error_type="ValidationError",
                status=SpanStatus.ERROR,
            )

            assert updated is not None
            assert updated.status == SpanStatus.ERROR
            assert updated.attributes["cube.error_type"] == "ValidationError"

    def test_record_query_result_none_span(self) -> None:
        """record_query_result should handle None span."""
        tracer = QueryTracer()

        result = tracer.record_query_result(None, row_count=100)
        assert result is None

    def test_record_query_result_preserves_original_attributes(self) -> None:
        """record_query_result should preserve original span attributes."""
        tracer = QueryTracer()

        with tracer.trace_query(
            cube_name="orders",
            measures_count=2,
        ) as span:
            assert span is not None
            updated = tracer.record_query_result(span, row_count=50)

            assert updated is not None
            # Original attributes preserved
            assert updated.attributes["cube.name"] == "orders"
            assert updated.attributes["cube.measures_count"] == 2
            # New attribute added
            assert updated.attributes["cube.row_count"] == 50


class TestTraceparentParsing:
    """Additional tests for W3C traceparent header parsing."""

    def test_invalid_traceparent_generates_new_trace(self) -> None:
        """Invalid traceparent should generate new trace_id."""
        tracer = QueryTracer()

        with tracer.trace_query(
            cube_name="orders",
            headers={"traceparent": "invalid-header"},
        ) as span:
            assert span is not None
            assert len(span.trace_id) == 32
            assert span.parent_span_id is None

    def test_uppercase_traceparent_header_key(self) -> None:
        """Traceparent with uppercase key should be handled."""
        tracer = QueryTracer()
        traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

        with tracer.trace_query(
            cube_name="orders",
            headers={"Traceparent": traceparent},
        ) as span:
            assert span is not None
            assert span.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"

    def test_no_headers_generates_new_trace(self) -> None:
        """No headers should generate new trace_id."""
        tracer = QueryTracer()

        with tracer.trace_query(cube_name="orders", headers=None) as span:
            assert span is not None
            assert len(span.trace_id) == 32
            assert span.parent_span_id is None

    def test_empty_headers_generates_new_trace(self) -> None:
        """Empty headers should generate new trace_id."""
        tracer = QueryTracer()

        with tracer.trace_query(cube_name="orders", headers={}) as span:
            assert span is not None
            assert len(span.trace_id) == 32
            assert span.parent_span_id is None
