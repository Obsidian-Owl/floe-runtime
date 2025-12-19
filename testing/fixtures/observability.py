"""Observability client helpers for integration testing.

This module provides helper classes for interacting with observability services
(Jaeger for traces, Marquez for lineage) during integration tests.

Classes:
    JaegerClient: Client for querying Jaeger trace data
    MarquezClient: Client for querying Marquez lineage data

Usage:
    ```python
    from testing.fixtures import JaegerClient, MarquezClient

    # Verify traces were created
    jaeger = JaegerClient()
    traces = jaeger.get_traces(service="floe-cube", operation="query")
    assert len(traces) > 0

    # Verify lineage events
    marquez = MarquezClient()
    events = marquez.get_lineage_events(job_name="my_pipeline")
    assert marquez.verify_event_facets(events[0], {"type": "START"})
    ```

Note:
    - T004 creates stub classes with method signatures
    - T009 implements full JaegerClient functionality
    - T010 implements full MarquezClient functionality

See Also:
    - testing/docker/docker-compose.yml for service configuration
    - specs/006-integration-testing/spec.md FR-029 for graceful degradation
"""

from __future__ import annotations

from typing import Any

from testing.fixtures.services import get_service_host


class JaegerClient:
    """Client for querying Jaeger trace data in integration tests.

    This client provides methods to query traces from a Jaeger instance
    and verify span attributes match expected values.

    Attributes:
        base_url: Base URL for the Jaeger API (default: http://localhost:16686)

    Example:
        >>> client = JaegerClient()
        >>> traces = client.get_traces("floe-cube", "query")
        >>> assert len(traces) > 0
        >>> assert client.verify_span_attributes(traces[0], {"http.method": "POST"})

    Note:
        Full implementation added in T009.
    """

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize JaegerClient.

        Args:
            base_url: Base URL for Jaeger API. If None, uses environment-aware
                      default (Docker hostname when running in container,
                      localhost otherwise).
        """
        if base_url is None:
            host = get_service_host("jaeger")
            base_url = f"http://{host}:16686"
        self.base_url = base_url

    def get_traces(
        self,
        service: str,
        operation: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Query traces from Jaeger.

        Args:
            service: Service name to query traces for.
            operation: Optional operation name to filter traces.
            limit: Maximum number of traces to return.

        Returns:
            List of trace dictionaries containing spans and metadata.

        Raises:
            NotImplementedError: Until T009 implements this method.

        Note:
            Full implementation added in T009.
        """
        raise NotImplementedError("get_traces will be implemented in T009")

    def verify_span_attributes(
        self,
        trace: dict[str, Any],
        expected: dict[str, Any],
    ) -> bool:
        """Verify a trace contains spans with expected attributes.

        Args:
            trace: Trace dictionary from get_traces().
            expected: Dictionary of expected attribute key-value pairs.

        Returns:
            True if all expected attributes are found in any span.

        Raises:
            NotImplementedError: Until T009 implements this method.

        Note:
            Full implementation added in T009.
        """
        raise NotImplementedError("verify_span_attributes will be implemented in T009")


class MarquezClient:
    """Client for querying Marquez lineage data in integration tests.

    This client provides methods to query OpenLineage events from a Marquez
    instance and verify event facets match expected values.

    Attributes:
        base_url: Base URL for the Marquez API (default: http://localhost:5002)

    Example:
        >>> client = MarquezClient()
        >>> events = client.get_lineage_events("my_pipeline_job")
        >>> assert len(events) > 0
        >>> assert client.verify_event_facets(events[0], {"eventType": "START"})

    Note:
        Full implementation added in T010.
    """

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize MarquezClient.

        Args:
            base_url: Base URL for Marquez API. If None, uses environment-aware
                      default (Docker hostname when running in container,
                      localhost otherwise).
        """
        if base_url is None:
            host = get_service_host("marquez")
            # Use port 5000 inside Docker, 5002 from host
            port = "5000" if host == "marquez" else "5002"
            base_url = f"http://{host}:{port}"
        self.base_url = base_url

    def get_lineage_events(
        self,
        job_name: str,
        namespace: str = "default",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Query lineage events from Marquez.

        Args:
            job_name: Job name to query events for.
            namespace: Namespace containing the job.
            limit: Maximum number of events to return.

        Returns:
            List of OpenLineage event dictionaries.

        Raises:
            NotImplementedError: Until T010 implements this method.

        Note:
            Full implementation added in T010.
        """
        raise NotImplementedError("get_lineage_events will be implemented in T010")

    def verify_event_facets(
        self,
        event: dict[str, Any],
        expected: dict[str, Any],
    ) -> bool:
        """Verify an event contains expected facets.

        Args:
            event: Event dictionary from get_lineage_events().
            expected: Dictionary of expected facet key-value pairs.

        Returns:
            True if all expected facets are found in the event.

        Raises:
            NotImplementedError: Until T010 implements this method.

        Note:
            Full implementation added in T010.
        """
        raise NotImplementedError("verify_event_facets will be implemented in T010")


__all__ = [
    "JaegerClient",
    "MarquezClient",
]
