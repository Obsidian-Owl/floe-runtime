"""Tests for testing.fixtures.observability module.

These tests verify the JaegerClient and MarquezClient helper classes
used for verifying observability in integration tests.

Note: T004 creates the stub classes. T009/T010 implement full functionality.
"""

from __future__ import annotations


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

        # HTTP is intentional for local Docker testing  # nosonar: S5332
        client = JaegerClient(base_url="http://localhost:16686")
        assert client.base_url == "http://localhost:16686"

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

        # HTTP is intentional for local Docker testing  # nosonar: S5332
        client = MarquezClient(base_url="http://localhost:5002")
        assert client.base_url == "http://localhost:5002"

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
