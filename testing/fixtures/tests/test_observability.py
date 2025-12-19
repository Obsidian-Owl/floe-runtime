"""Tests for testing.fixtures.observability module.

These tests verify the JaegerClient and MarquezClient helper classes
used for verifying observability in integration tests.

Note: T004 creates the stub classes. T009/T010 implement full functionality.
"""

from __future__ import annotations

import pytest


class TestInputValidation:
    """Tests for input validation security measures."""

    def test_validate_name_accepts_valid_service_names(self) -> None:
        """Verify valid service names pass validation."""
        from testing.fixtures.observability import _validate_name

        # Valid names should not raise
        assert _validate_name("floe-dagster", "service") == "floe-dagster"
        assert _validate_name("my_service", "service") == "my_service"
        assert _validate_name("service.name", "service") == "service.name"
        assert _validate_name("MyService123", "service") == "MyService123"

    def test_validate_name_rejects_empty_name(self) -> None:
        """Verify empty names are rejected."""
        from testing.fixtures.observability import _validate_name

        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_name("", "service")

    def test_validate_name_rejects_path_traversal(self) -> None:
        """Verify path traversal attempts are blocked."""
        from testing.fixtures.observability import _validate_name

        # Path traversal attempts
        with pytest.raises(ValueError, match="Invalid service"):
            _validate_name("../etc/passwd", "service")

        with pytest.raises(ValueError, match="Invalid service"):
            _validate_name("foo/../bar", "service")

        with pytest.raises(ValueError, match="Invalid service"):
            _validate_name("/etc/passwd", "service")

    def test_validate_name_rejects_special_characters(self) -> None:
        """Verify special characters that could be exploited are blocked."""
        from testing.fixtures.observability import _validate_name

        invalid_names = [
            "service;rm -rf",  # Command injection
            "service`whoami`",  # Backtick injection
            "service$(id)",  # Command substitution
            "service%00null",  # Null byte
            "service\nheader",  # CRLF injection
            "service with spaces",  # Spaces
        ]

        for name in invalid_names:
            with pytest.raises(ValueError, match="Invalid"):
                _validate_name(name, "service")


class TestJaegerClientVerifySpanAttributes:
    """Tests for JaegerClient.verify_span_attributes method."""

    def test_verify_span_attributes_finds_matching_span(self) -> None:
        """Verify method returns True when span has expected attributes."""
        from testing.fixtures.observability import JaegerClient

        client = JaegerClient()
        trace = {
            "traceID": "abc123",
            "spans": [
                {
                    "operationName": "test_op",
                    "tags": [
                        {"key": "http.method", "value": "POST"},
                        {"key": "http.status_code", "value": 200},
                    ],
                }
            ],
        }

        assert client.verify_span_attributes(trace, {"http.method": "POST"})
        assert client.verify_span_attributes(trace, {"http.status_code": "200"})

    def test_verify_span_attributes_returns_false_when_not_found(self) -> None:
        """Verify method returns False when expected attributes missing."""
        from testing.fixtures.observability import JaegerClient

        client = JaegerClient()
        trace = {
            "traceID": "abc123",
            "spans": [
                {
                    "operationName": "test_op",
                    "tags": [{"key": "http.method", "value": "GET"}],
                }
            ],
        }

        assert not client.verify_span_attributes(trace, {"http.method": "POST"})
        assert not client.verify_span_attributes(trace, {"nonexistent": "value"})

    def test_verify_span_attributes_handles_empty_trace(self) -> None:
        """Verify method handles traces with no spans."""
        from testing.fixtures.observability import JaegerClient
        from typing import Any

        client = JaegerClient()
        trace: dict[str, Any] = {"traceID": "abc123", "spans": []}

        assert not client.verify_span_attributes(trace, {"any": "attr"})

    def test_verify_span_attributes_searches_all_spans(self) -> None:
        """Verify method searches through all spans in trace."""
        from testing.fixtures.observability import JaegerClient

        client = JaegerClient()
        trace = {
            "traceID": "abc123",
            "spans": [
                {"operationName": "op1", "tags": [{"key": "attr", "value": "wrong"}]},
                {"operationName": "op2", "tags": [{"key": "attr", "value": "correct"}]},
            ],
        }

        assert client.verify_span_attributes(trace, {"attr": "correct"})


class TestJaegerClientImport:
    """Tests for JaegerClient class structure."""

    def test_jaeger_client_can_be_imported(self) -> None:
        """Verify JaegerClient can be imported from module."""
        from testing.fixtures.observability import JaegerClient

        # Verify it's a class we can instantiate
        assert callable(JaegerClient)

    def test_jaeger_client_instantiation(self) -> None:
        """Verify JaegerClient can be instantiated with base_url."""
        from testing.fixtures.observability import JaegerClient

        # HTTP is intentional for local Docker testing
        client = JaegerClient(base_url="http://localhost:16686")  # nosonar: S5332
        assert client.base_url == "http://localhost:16686"  # nosonar: S5332

    def test_jaeger_client_default_url(self) -> None:
        """Verify JaegerClient has sensible default base_url."""
        from testing.fixtures.observability import JaegerClient

        client = JaegerClient()
        assert "16686" in client.base_url

    def test_jaeger_client_has_get_traces_method(self) -> None:
        """Verify JaegerClient has get_traces method signature."""
        from testing.fixtures.observability import JaegerClient

        client = JaegerClient()
        # Method should exist with correct signature
        assert hasattr(client, "get_traces")
        assert callable(client.get_traces)

    def test_jaeger_client_has_verify_span_attributes_method(self) -> None:
        """Verify JaegerClient has verify_span_attributes method signature."""
        from testing.fixtures.observability import JaegerClient

        client = JaegerClient()
        assert hasattr(client, "verify_span_attributes")
        assert callable(client.verify_span_attributes)


class TestMarquezClientImport:
    """Tests for MarquezClient class structure."""

    def test_marquez_client_can_be_imported(self) -> None:
        """Verify MarquezClient can be imported from module."""
        from testing.fixtures.observability import MarquezClient

        # Verify it's a class we can instantiate
        assert callable(MarquezClient)

    def test_marquez_client_instantiation(self) -> None:
        """Verify MarquezClient can be instantiated with base_url."""
        from testing.fixtures.observability import MarquezClient

        # HTTP is intentional for local Docker testing
        client = MarquezClient(base_url="http://localhost:5002")  # nosonar: S5332
        assert client.base_url == "http://localhost:5002"  # nosonar: S5332

    def test_marquez_client_default_url(self) -> None:
        """Verify MarquezClient has sensible default base_url."""
        from testing.fixtures.observability import MarquezClient

        client = MarquezClient()
        # Should use 5002 (external) or 5000 (internal) port
        assert "500" in client.base_url

    def test_marquez_client_has_get_lineage_events_method(self) -> None:
        """Verify MarquezClient has get_lineage_events method signature."""
        from testing.fixtures.observability import MarquezClient

        client = MarquezClient()
        assert hasattr(client, "get_lineage_events")
        assert callable(client.get_lineage_events)

    def test_marquez_client_has_verify_event_facets_method(self) -> None:
        """Verify MarquezClient has verify_event_facets method signature."""
        from testing.fixtures.observability import MarquezClient

        client = MarquezClient()
        assert hasattr(client, "verify_event_facets")
        assert callable(client.verify_event_facets)


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_module_exports_jaeger_client(self) -> None:
        """Verify JaegerClient is in module __all__."""
        from testing.fixtures import observability

        assert "JaegerClient" in observability.__all__

    def test_module_exports_marquez_client(self) -> None:
        """Verify MarquezClient is in module __all__."""
        from testing.fixtures import observability

        assert "MarquezClient" in observability.__all__

    def test_clients_exported_from_fixtures_init(self) -> None:
        """Verify clients can be imported from testing.fixtures."""
        from testing.fixtures import JaegerClient, MarquezClient

        assert JaegerClient is not None
        assert MarquezClient is not None
