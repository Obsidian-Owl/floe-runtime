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

import logging
import re
from typing import Any
from urllib.parse import quote

import requests

from testing.fixtures.services import get_service_host, is_running_in_docker

logger = logging.getLogger(__name__)

# Pattern for valid service/operation names (alphanumeric, hyphens, underscores, dots)
_VALID_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def _validate_name(name: str, param_name: str) -> str:
    """Validate and sanitize service/operation names to prevent path traversal.

    Args:
        name: The name to validate.
        param_name: Parameter name for error messages.

    Returns:
        The validated name (unchanged if valid).

    Raises:
        ValueError: If name contains invalid characters or is empty.
    """
    if not name:
        raise ValueError(f"{param_name} cannot be empty")
    if not _VALID_NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid {param_name}: '{name}'. "
            "Only alphanumeric characters, hyphens, underscores, and dots are allowed."
        )
    return name


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
            # HTTP is intentional for local Docker testing
            base_url = f"http://{host}:16686"  # nosonar: S5332
        self.base_url = base_url

    def get_traces(
        self,
        service: str,
        operation: str | None = None,
        limit: int = 20,
        lookback: str = "1h",
    ) -> list[dict[str, Any]]:
        """Query traces from Jaeger.

        Args:
            service: Service name to query traces for.
            operation: Optional operation name to filter traces.
            limit: Maximum number of traces to return.
            lookback: Time window to search for traces (e.g., "1h", "30m").

        Returns:
            List of trace dictionaries containing spans and metadata.
            Each trace contains: traceID, spans, processes, warnings.

        Raises:
            ValueError: If service or operation name contains invalid characters.
            requests.RequestException: If the Jaeger API request fails.

        Example:
            >>> client = JaegerClient()
            >>> traces = client.get_traces("floe-dagster", operation="run_pipeline")
            >>> for trace in traces:
            ...     print(f"Trace {trace['traceID']} has {len(trace['spans'])} spans")
        """
        # Validate inputs to prevent injection
        _validate_name(service, "service")
        if operation:
            _validate_name(operation, "operation")

        # Build query parameters for Jaeger API
        params: dict[str, Any] = {
            "service": service,
            "limit": limit,
            "lookback": lookback,
        }
        if operation:
            params["operation"] = operation

        url = f"{self.base_url}/api/traces"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            traces: list[dict[str, Any]] = data.get("data", [])
            logger.debug(
                "Retrieved %d traces for service=%s operation=%s",
                len(traces),
                service,
                operation,
            )
            return traces
        except requests.RequestException as e:
            logger.warning("Failed to query Jaeger traces: %s", e)
            raise

    def verify_span_attributes(
        self,
        trace: dict[str, Any],
        expected: dict[str, Any],
    ) -> bool:
        """Verify a trace contains spans with expected attributes.

        Searches through all spans in the trace to find one that contains
        all the expected attribute key-value pairs. Tags in Jaeger spans
        are stored as a list of {"key": k, "value": v} dictionaries.

        Args:
            trace: Trace dictionary from get_traces().
            expected: Dictionary of expected attribute key-value pairs.
                      Values are compared as strings.

        Returns:
            True if any span in the trace contains all expected attributes.

        Example:
            >>> client = JaegerClient()
            >>> traces = client.get_traces("floe-dagster")
            >>> if traces:
            ...     has_http = client.verify_span_attributes(
            ...         traces[0], {"http.method": "POST"}
            ...     )
        """
        spans = trace.get("spans", [])

        for span in spans:
            # Jaeger stores tags as list of {"key": k, "value": v}
            tags = span.get("tags", [])
            tag_dict = {tag["key"]: str(tag["value"]) for tag in tags}

            # Check if all expected attributes are present
            if all(tag_dict.get(k) == str(v) for k, v in expected.items()):
                logger.debug(
                    "Found matching span %s with attributes %s",
                    span.get("operationName"),
                    expected,
                )
                return True

        return False

    def get_services(self) -> list[str]:
        """Get list of services that have reported traces to Jaeger.

        Returns:
            List of service names.

        Raises:
            requests.RequestException: If the Jaeger API request fails.
        """
        url = f"{self.base_url}/api/services"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            services: list[str] = data.get("data", [])
            return services
        except requests.RequestException as e:
            logger.warning("Failed to query Jaeger services: %s", e)
            raise

    def get_operations(self, service: str) -> list[str]:
        """Get list of operations for a service.

        Args:
            service: Service name to get operations for.

        Returns:
            List of operation names.

        Raises:
            ValueError: If service name contains invalid characters.
            requests.RequestException: If the Jaeger API request fails.
        """
        # Validate and URL-encode to prevent path traversal
        _validate_name(service, "service")
        safe_service = quote(service, safe="")
        url = f"{self.base_url}/api/services/{safe_service}/operations"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            operations: list[str] = data.get("data", [])
            return operations
        except requests.RequestException as e:
            logger.warning("Failed to query Jaeger operations: %s", e)
            raise

    def is_available(self) -> bool:
        """Check if Jaeger is available and responding.

        Returns:
            True if Jaeger is available, False otherwise.
        """
        try:
            response = requests.get(f"{self.base_url}/api/services", timeout=5)
            return bool(response.status_code == 200)
        except requests.RequestException:
            return False


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
            port = "5000" if is_running_in_docker() else "5002"
            # HTTP is intentional for local Docker testing
            base_url = f"http://{host}:{port}"  # nosonar: S5332
        self.base_url = base_url

    def get_lineage_events(
        self,
        job_name: str,
        namespace: str = "default",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Query lineage events from Marquez for a specific job.

        Retrieves the run history for a job, then fetches facets for each run.
        Events are returned in reverse chronological order (most recent first).

        Args:
            job_name: Job name to query events for.
            namespace: Namespace containing the job.
            limit: Maximum number of runs to return.

        Returns:
            List of run event dictionaries containing run metadata and facets.
            Each event contains: id, state, startedAt, endedAt, facets.

        Raises:
            ValueError: If job_name or namespace contains invalid characters.
            requests.RequestException: If the Marquez API request fails.

        Example:
            >>> client = MarquezClient()
            >>> events = client.get_lineage_events("my_pipeline", namespace="default")
            >>> for event in events:
            ...     print(f"Run {event['id']} state: {event.get('state')}")
        """
        # Validate inputs to prevent path traversal
        _validate_name(job_name, "job_name")
        _validate_name(namespace, "namespace")

        # URL-encode for safety
        safe_namespace = quote(namespace, safe="")
        safe_job = quote(job_name, safe="")

        # Get job runs from Marquez API
        url = f"{self.base_url}/api/v1/namespaces/{safe_namespace}/jobs/{safe_job}/runs"
        params: dict[str, Any] = {"limit": limit}

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            runs: list[dict[str, Any]] = data.get("runs", [])

            # Enrich runs with facets
            events: list[dict[str, Any]] = []
            for run in runs:
                run_id = run.get("id")
                if run_id:
                    # Fetch facets for this run
                    facets = self._get_run_facets(run_id)
                    run["facets"] = facets
                events.append(run)

            logger.debug(
                "Retrieved %d runs for job=%s namespace=%s",
                len(events),
                job_name,
                namespace,
            )
            return events
        except requests.RequestException as e:
            logger.warning("Failed to query Marquez runs: %s", e)
            raise

    def _get_run_facets(self, run_id: str) -> dict[str, Any]:
        """Get facets for a specific run.

        Args:
            run_id: The run ID (UUID format).

        Returns:
            Dictionary of facets for the run.
        """
        # URL-encode the run_id for safety
        safe_run_id = quote(run_id, safe="")
        url = f"{self.base_url}/api/v1/jobs/runs/{safe_run_id}/facets"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            facets: dict[str, Any] = data.get("facets", {})
            return facets
        except requests.RequestException as e:
            logger.debug("Failed to get facets for run %s: %s", run_id, e)
            return {}

    def get_namespaces(self) -> list[str]:
        """Get list of namespaces in Marquez.

        Returns:
            List of namespace names.

        Raises:
            requests.RequestException: If the Marquez API request fails.
        """
        url = f"{self.base_url}/api/v1/namespaces"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            namespaces = data.get("namespaces", [])
            return [ns.get("name", "") for ns in namespaces if ns.get("name")]
        except requests.RequestException as e:
            logger.warning("Failed to query Marquez namespaces: %s", e)
            raise

    def get_jobs(self, namespace: str = "default") -> list[dict[str, Any]]:
        """Get list of jobs in a namespace.

        Args:
            namespace: Namespace to list jobs from.

        Returns:
            List of job dictionaries.

        Raises:
            ValueError: If namespace contains invalid characters.
            requests.RequestException: If the Marquez API request fails.
        """
        _validate_name(namespace, "namespace")
        safe_namespace = quote(namespace, safe="")
        url = f"{self.base_url}/api/v1/namespaces/{safe_namespace}/jobs"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            jobs: list[dict[str, Any]] = data.get("jobs", [])
            return jobs
        except requests.RequestException as e:
            logger.warning("Failed to query Marquez jobs: %s", e)
            raise

    def verify_event_facets(
        self,
        event: dict[str, Any],
        expected: dict[str, Any],
    ) -> bool:
        """Verify an event contains expected facets or top-level fields.

        Checks both top-level event fields (id, state, etc.) and nested
        facets for the expected key-value pairs.

        Args:
            event: Event dictionary from get_lineage_events().
            expected: Dictionary of expected key-value pairs to find.
                      Can match top-level fields or nested facet values.

        Returns:
            True if all expected fields are found in the event.

        Example:
            >>> client = MarquezClient()
            >>> events = client.get_lineage_events("my_job")
            >>> if events:
            ...     # Check run state
            ...     has_completed = client.verify_event_facets(
            ...         events[0], {"state": "COMPLETED"}
            ...     )
        """
        for key, expected_value in expected.items():
            # Check top-level fields first
            if key in event:
                if str(event[key]) != str(expected_value):
                    return False
                continue

            # Check in facets
            facets = event.get("facets", {})
            if key in facets:
                if str(facets[key]) != str(expected_value):
                    return False
                continue

            # Check nested facet structures (e.g., run facets have nested dicts)
            found = False
            for facet_value in facets.values():
                if (
                    isinstance(facet_value, dict)
                    and key in facet_value
                    and str(facet_value[key]) == str(expected_value)
                ):
                    found = True
                    break
            if not found:
                return False

        return True

    def is_available(self) -> bool:
        """Check if Marquez is available and responding.

        Returns:
            True if Marquez is available, False otherwise.
        """
        try:
            response = requests.get(f"{self.base_url}/api/v1/namespaces", timeout=5)
            return bool(response.status_code == 200)
        except requests.RequestException:
            return False


__all__ = [
    "JaegerClient",
    "MarquezClient",
]
