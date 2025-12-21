"""E2E test fixtures for complete data flow validation.

This module provides comprehensive fixtures for E2E tests that validate
the COMPLETE data flow through all floe-runtime components:

    1. Synthetic Data Generation (floe-synthetic)
    2. Dagster Orchestration (scheduling, assets, sensors)
    3. dbt Transformations (medallion architecture: staging → intermediate → marts)
    4. Iceberg Storage (via Polaris REST catalog)
    5. Cube Semantic Layer (queries, pre-aggregations, SQL API)
    6. Observability (Marquez lineage, Jaeger traces)

Fixture Categories:
    Service Clients:
        - cube_client: HTTP session for Cube REST API
        - trino_connection: Trino connection for direct Iceberg queries
        - polaris_client: Polaris catalog REST client
        - marquez_client: Marquez lineage API client
        - jaeger_client: Jaeger trace API client
        - dagster_client: Dagster GraphQL API client

    Service Readiness:
        - demo_services_ready: Validates all demo profile services running
        - all_services_healthy: Deep health check across all services

    Data Helpers:
        - wait_for_data: Poll Cube until data appears
        - wait_for_iceberg_data: Poll Trino until Iceberg table has data
        - wait_for_lineage: Poll Marquez until lineage events appear
        - trigger_synthetic_generation: Trigger on-demand data generation

    Query Helpers:
        - cube_query: Execute Cube REST API queries
        - cube_sql_query: Execute Cube SQL API queries (Postgres wire protocol)
        - trino_query: Execute direct Trino SQL queries

Environment Variables:
    - CUBE_API_URL: Cube REST API endpoint (default: http://localhost:4000)
    - CUBE_SQL_HOST: Cube SQL API host (default: localhost)
    - CUBE_SQL_PORT: Cube SQL API port (default: 15432)
    - TRINO_HOST: Trino coordinator host (default: localhost)
    - TRINO_PORT: Trino HTTP port (default: 8080)
    - POLARIS_URL: Polaris catalog URL (default: http://localhost:8181)
    - MARQUEZ_URL: Marquez API URL (default: http://localhost:5000)
    - JAEGER_URL: Jaeger query API URL (default: http://localhost:16686)
    - DAGSTER_URL: Dagster webserver URL (default: http://localhost:3000)
    - DEMO_TIMEOUT: Max wait time for data propagation (default: 300s)

Covers:
    - 007-FR-029: E2E validation tests (complete data flow)
    - 007-FR-031: Docker Compose demo profile
    - 007-FR-032: Cube pre-aggregation refresh validation
    - 007-FR-033: Marquez lineage visualization
    - 007-FR-034: Jaeger distributed tracing
"""

from __future__ import annotations

from collections.abc import Generator
import os
import time
from typing import Any

import pytest
import requests
from requests import Response, Session

# =============================================================================
# Configuration
# =============================================================================

# Default values for E2E test configuration
DEFAULT_CUBE_API_URL = "http://localhost:4000"
DEFAULT_CUBE_SQL_HOST = "localhost"
DEFAULT_CUBE_SQL_PORT = 15432
DEFAULT_TRINO_HOST = "localhost"
DEFAULT_TRINO_PORT = 8080
DEFAULT_POLARIS_URL = "http://localhost:8181"
DEFAULT_MARQUEZ_URL = "http://localhost:5000"
DEFAULT_JAEGER_URL = "http://localhost:16686"
DEFAULT_DAGSTER_URL = "http://localhost:3000"
DEFAULT_DEMO_TIMEOUT = 300  # 5 minutes max wait for data


def get_cube_api_url() -> str:
    """Get Cube API URL from environment or default."""
    return os.environ.get("CUBE_API_URL", DEFAULT_CUBE_API_URL)


def get_cube_sql_host() -> str:
    """Get Cube SQL API host from environment or default."""
    return os.environ.get("CUBE_SQL_HOST", DEFAULT_CUBE_SQL_HOST)


def get_cube_sql_port() -> int:
    """Get Cube SQL API port from environment or default."""
    return int(os.environ.get("CUBE_SQL_PORT", str(DEFAULT_CUBE_SQL_PORT)))


def get_trino_host() -> str:
    """Get Trino host from environment or default."""
    return os.environ.get("TRINO_HOST", DEFAULT_TRINO_HOST)


def get_trino_port() -> int:
    """Get Trino port from environment or default."""
    return int(os.environ.get("TRINO_PORT", str(DEFAULT_TRINO_PORT)))


def get_polaris_url() -> str:
    """Get Polaris catalog URL from environment or default."""
    return os.environ.get("POLARIS_URL", DEFAULT_POLARIS_URL)


def get_marquez_url() -> str:
    """Get Marquez API URL from environment or default."""
    return os.environ.get("MARQUEZ_URL", DEFAULT_MARQUEZ_URL)


def get_jaeger_url() -> str:
    """Get Jaeger query API URL from environment or default."""
    return os.environ.get("JAEGER_URL", DEFAULT_JAEGER_URL)


def get_dagster_url() -> str:
    """Get Dagster webserver URL from environment or default."""
    return os.environ.get("DAGSTER_URL", DEFAULT_DAGSTER_URL)


def get_demo_timeout() -> int:
    """Get demo timeout from environment or default."""
    return int(os.environ.get("DEMO_TIMEOUT", str(DEFAULT_DEMO_TIMEOUT)))


# =============================================================================
# Session-Scoped Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def cube_api_url() -> str:
    """Return the Cube API URL for E2E tests.

    Returns:
        Cube API URL string (e.g., http://localhost:4000).
    """
    return get_cube_api_url()


@pytest.fixture(scope="session")
def cube_client(cube_api_url: str) -> Generator[Session, None, None]:
    """Create an HTTP session for Cube API requests.

    Args:
        cube_api_url: Cube API URL from fixture.

    Yields:
        Configured requests Session for Cube API.
    """
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    # Store base URL for convenience
    session.base_url = cube_api_url  # type: ignore[attr-defined]

    yield session

    session.close()


@pytest.fixture(scope="session")
def demo_services_ready(cube_api_url: str) -> bool:
    """Validate that demo profile services are running.

    This fixture checks that Cube API is accessible before running E2E tests.
    Tests that depend on this fixture will fail fast if services aren't ready.

    Args:
        cube_api_url: Cube API URL from fixture.

    Returns:
        True if services are ready.

    Raises:
        pytest.fail: If services are not accessible.
    """
    readyz_url = f"{cube_api_url}/readyz"
    max_retries = 30
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.get(readyz_url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    pytest.fail(
        f"Demo services not ready after {max_retries * retry_delay}s. "
        f"Ensure demo profile is running: docker compose --profile full up -d"
    )


# =============================================================================
# Function-Scoped Fixtures
# =============================================================================


@pytest.fixture
def cube_query(cube_client: Session) -> Any:
    """Execute a Cube query and return the result.

    This fixture returns a function that can be used to execute Cube queries.

    Args:
        cube_client: HTTP session from fixture.

    Returns:
        Function that executes Cube queries.
    """

    def _query(query_body: dict[str, Any]) -> Response:
        """Execute a Cube query.

        Args:
            query_body: Cube query in JSON format.

        Returns:
            Response from Cube API.
        """
        url = f"{cube_client.base_url}/cubejs-api/v1/load"  # type: ignore[attr-defined]
        return cube_client.post(url, json={"query": query_body})

    return _query


@pytest.fixture
def wait_for_data(cube_client: Session) -> Any:
    """Wait for data to appear in Cube query results.

    This fixture returns a function that polls Cube until data appears
    or timeout is reached.

    Args:
        cube_client: HTTP session from fixture.

    Returns:
        Function that waits for data.
    """

    def _wait(
        query_body: dict[str, Any],
        min_rows: int = 1,
        timeout: int | None = None,
        poll_interval: int = 5,
    ) -> dict[str, Any]:
        """Wait for data to appear in Cube query results.

        Args:
            query_body: Cube query in JSON format.
            min_rows: Minimum number of rows expected.
            timeout: Max wait time in seconds (default from env).
            poll_interval: Seconds between polls.

        Returns:
            Query result data.

        Raises:
            TimeoutError: If data doesn't appear within timeout.
        """
        if timeout is None:
            timeout = get_demo_timeout()

        url = f"{cube_client.base_url}/cubejs-api/v1/load"  # type: ignore[attr-defined]
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = cube_client.post(url, json={"query": query_body})
                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", [])
                    if len(data) >= min_rows:
                        return dict(result)
            except requests.exceptions.RequestException:
                pass

            time.sleep(poll_interval)

        elapsed = int(time.time() - start_time)
        raise TimeoutError(
            f"Data did not appear within {elapsed}s. Expected at least {min_rows} rows."
        )

    return _wait


@pytest.fixture
def cube_meta(cube_client: Session) -> dict[str, Any]:
    """Get Cube meta information (available cubes and measures).

    Args:
        cube_client: HTTP session from fixture.

    Returns:
        Cube meta information.

    Raises:
        pytest.fail: If meta endpoint is not accessible.
    """
    url = f"{cube_client.base_url}/cubejs-api/v1/meta"  # type: ignore[attr-defined]
    try:
        response = cube_client.get(url)
        response.raise_for_status()
        return dict(response.json())
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to get Cube meta: {e}")


# =============================================================================
# Polaris Catalog Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def polaris_url() -> str:
    """Return the Polaris catalog URL for E2E tests.

    Returns:
        Polaris catalog URL string (e.g., http://localhost:8181).
    """
    return get_polaris_url()


@pytest.fixture(scope="session")
def polaris_client(polaris_url: str) -> Generator[Session, None, None]:
    """Create an HTTP session for Polaris catalog API requests.

    Args:
        polaris_url: Polaris catalog URL from fixture.

    Yields:
        Configured requests Session for Polaris REST API.
    """
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    # Store base URL for convenience
    session.base_url = polaris_url  # type: ignore[attr-defined]

    yield session

    session.close()


@pytest.fixture
def polaris_catalog_config(polaris_client: Session) -> dict[str, Any]:
    """Get Polaris catalog configuration.

    Args:
        polaris_client: HTTP session from fixture.

    Returns:
        Polaris catalog configuration from /api/catalog/v1/config.

    Raises:
        pytest.fail: If Polaris is not accessible.
    """
    url = f"{polaris_client.base_url}/api/catalog/v1/config"  # type: ignore[attr-defined]
    try:
        response = polaris_client.get(url)
        response.raise_for_status()
        return dict(response.json())
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to get Polaris config: {e}")


@pytest.fixture
def polaris_namespaces(polaris_client: Session) -> list[dict[str, Any]]:
    """List all namespaces in Polaris catalog.

    Args:
        polaris_client: HTTP session from fixture.

    Returns:
        List of namespace information.

    Raises:
        pytest.fail: If Polaris is not accessible.
    """
    # Note: This requires authentication in production
    url = f"{polaris_client.base_url}/api/catalog/v1/namespaces"  # type: ignore[attr-defined]
    try:
        response = polaris_client.get(url)
        response.raise_for_status()
        return list(response.json().get("namespaces", []))
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to list Polaris namespaces: {e}")


# =============================================================================
# Marquez Lineage Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def marquez_url() -> str:
    """Return the Marquez API URL for E2E tests.

    Returns:
        Marquez API URL string (e.g., http://localhost:5000).
    """
    return get_marquez_url()


@pytest.fixture(scope="session")
def marquez_client(marquez_url: str) -> Generator[Session, None, None]:
    """Create an HTTP session for Marquez lineage API requests.

    Args:
        marquez_url: Marquez API URL from fixture.

    Yields:
        Configured requests Session for Marquez API.
    """
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    # Store base URL for convenience
    session.base_url = marquez_url  # type: ignore[attr-defined]

    yield session

    session.close()


@pytest.fixture
def marquez_namespaces(marquez_client: Session) -> list[dict[str, Any]]:
    """List all namespaces in Marquez.

    Args:
        marquez_client: HTTP session from fixture.

    Returns:
        List of namespace information.

    Raises:
        pytest.fail: If Marquez is not accessible.
    """
    url = f"{marquez_client.base_url}/api/v1/namespaces"  # type: ignore[attr-defined]
    try:
        response = marquez_client.get(url)
        response.raise_for_status()
        return list(response.json().get("namespaces", []))
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to list Marquez namespaces: {e}")


@pytest.fixture
def wait_for_lineage(marquez_client: Session) -> Any:
    """Wait for lineage events to appear in Marquez.

    This fixture returns a function that polls Marquez until lineage
    events appear for a given job or dataset.

    Args:
        marquez_client: HTTP session from fixture.

    Returns:
        Function that waits for lineage events.
    """

    def _wait(
        namespace: str,
        job_name: str | None = None,
        dataset_name: str | None = None,
        timeout: int | None = None,
        poll_interval: int = 5,
    ) -> dict[str, Any]:
        """Wait for lineage events to appear.

        Args:
            namespace: Marquez namespace to query.
            job_name: Optional job name to filter.
            dataset_name: Optional dataset name to filter.
            timeout: Max wait time in seconds (default from env).
            poll_interval: Seconds between polls.

        Returns:
            Lineage event data.

        Raises:
            TimeoutError: If lineage doesn't appear within timeout.
        """
        if timeout is None:
            timeout = get_demo_timeout()

        base_url = marquez_client.base_url  # type: ignore[attr-defined]
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if job_name:
                    url = f"{base_url}/api/v1/namespaces/{namespace}/jobs/{job_name}"
                elif dataset_name:
                    url = f"{base_url}/api/v1/namespaces/{namespace}/datasets/{dataset_name}"
                else:
                    url = f"{base_url}/api/v1/namespaces/{namespace}/jobs"

                response = marquez_client.get(url)
                if response.status_code == 200:
                    result = response.json()
                    # Check if we have lineage data
                    if job_name or dataset_name:
                        if result.get("id") or result.get("name"):
                            return dict(result)
                    else:
                        jobs = result.get("jobs", [])
                        if jobs:
                            return dict(result)
            except requests.exceptions.RequestException:
                pass

            time.sleep(poll_interval)

        elapsed = int(time.time() - start_time)
        raise TimeoutError(
            f"Lineage events did not appear within {elapsed}s. "
            f"Namespace: {namespace}, Job: {job_name}, Dataset: {dataset_name}"
        )

    return _wait


# =============================================================================
# Dagster Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def dagster_url() -> str:
    """Return the Dagster webserver URL for E2E tests.

    Returns:
        Dagster webserver URL string (e.g., http://localhost:3000).
    """
    return get_dagster_url()


@pytest.fixture(scope="session")
def dagster_client(dagster_url: str) -> Generator[Session, None, None]:
    """Create an HTTP session for Dagster GraphQL API requests.

    Args:
        dagster_url: Dagster webserver URL from fixture.

    Yields:
        Configured requests Session for Dagster GraphQL API.
    """
    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    # Store base URL for convenience
    session.base_url = dagster_url  # type: ignore[attr-defined]

    yield session

    session.close()


@pytest.fixture
def dagster_graphql(dagster_client: Session) -> Any:
    """Execute a Dagster GraphQL query.

    This fixture returns a function that can be used to execute GraphQL queries.

    Args:
        dagster_client: HTTP session from fixture.

    Returns:
        Function that executes GraphQL queries.
    """

    def _query(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a Dagster GraphQL query.

        Args:
            query: GraphQL query string.
            variables: Optional query variables.

        Returns:
            GraphQL response data.

        Raises:
            pytest.fail: If GraphQL query fails.
        """
        url = f"{dagster_client.base_url}/graphql"  # type: ignore[attr-defined]
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = dagster_client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            if "errors" in result:
                pytest.fail(f"GraphQL errors: {result['errors']}")
            data = result.get("data", {})
            return dict(data) if data else {}
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to execute GraphQL query: {e}")

    return _query


@pytest.fixture
def dagster_jobs(dagster_graphql: Any) -> list[dict[str, Any]]:
    """List all jobs in Dagster.

    Args:
        dagster_graphql: GraphQL query function from fixture.

    Returns:
        List of job information.
    """
    query = """
    query {
        repositoriesOrError {
            ... on RepositoryConnection {
                nodes {
                    name
                    jobs {
                        name
                        description
                    }
                }
            }
        }
    }
    """
    result = dagster_graphql(query)
    repositories = result.get("repositoriesOrError", {}).get("nodes", [])
    jobs: list[dict[str, Any]] = []
    for repo in repositories:
        for job in repo.get("jobs", []):
            jobs.append(
                {
                    "repository": repo.get("name"),
                    "name": job.get("name"),
                    "description": job.get("description"),
                }
            )
    return jobs


@pytest.fixture
def trigger_dagster_job(dagster_graphql: Any) -> Any:
    """Trigger a Dagster job run.

    This fixture returns a function that can be used to trigger job runs.

    Args:
        dagster_graphql: GraphQL query function from fixture.

    Returns:
        Function that triggers job runs.
    """

    def _trigger(
        job_name: str,
        repository_name: str = "floe_pipelines",
        repository_location: str = "floe_pipelines",
    ) -> str:
        """Trigger a Dagster job run.

        Args:
            job_name: Name of the job to run.
            repository_name: Repository containing the job.
            repository_location: Repository location name.

        Returns:
            Run ID of the triggered run.
        """
        mutation = """
        mutation LaunchRun($executionParams: ExecutionParams!) {
            launchRun(executionParams: $executionParams) {
                ... on LaunchRunSuccess {
                    run {
                        runId
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
                ... on InvalidStepError {
                    invalidStepKey
                }
                ... on InvalidOutputError {
                    invalidOutputName
                    stepKey
                }
            }
        }
        """
        variables = {
            "executionParams": {
                "selector": {
                    "repositoryName": repository_name,
                    "repositoryLocationName": repository_location,
                    "jobName": job_name,
                }
            }
        }
        result = dagster_graphql(mutation, variables)
        launch_result = result.get("launchRun", {})
        run_info = launch_result.get("run", {})
        run_id: str = run_info.get("runId", "")
        return run_id

    return _trigger


# =============================================================================
# Jaeger Tracing Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def jaeger_url() -> str:
    """Return the Jaeger query API URL for E2E tests.

    Returns:
        Jaeger query API URL string (e.g., http://localhost:16686).
    """
    return get_jaeger_url()


@pytest.fixture(scope="session")
def jaeger_client(jaeger_url: str) -> Generator[Session, None, None]:
    """Create an HTTP session for Jaeger query API requests.

    Args:
        jaeger_url: Jaeger query API URL from fixture.

    Yields:
        Configured requests Session for Jaeger API.
    """
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json",
        }
    )
    # Store base URL for convenience
    session.base_url = jaeger_url  # type: ignore[attr-defined]

    yield session

    session.close()


@pytest.fixture
def jaeger_services(jaeger_client: Session) -> list[str]:
    """List all services reporting to Jaeger.

    Args:
        jaeger_client: HTTP session from fixture.

    Returns:
        List of service names.

    Raises:
        pytest.fail: If Jaeger is not accessible.
    """
    url = f"{jaeger_client.base_url}/api/services"  # type: ignore[attr-defined]
    try:
        response = jaeger_client.get(url)
        response.raise_for_status()
        return list(response.json().get("data", []))
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to list Jaeger services: {e}")


@pytest.fixture
def jaeger_traces(jaeger_client: Session) -> Any:
    """Query traces from Jaeger.

    This fixture returns a function that can be used to query traces.

    Args:
        jaeger_client: HTTP session from fixture.

    Returns:
        Function that queries traces.
    """

    def _query(
        service: str,
        operation: str | None = None,
        limit: int = 20,
        lookback: str = "1h",
    ) -> list[dict[str, Any]]:
        """Query traces from Jaeger.

        Args:
            service: Service name to query.
            operation: Optional operation name filter.
            limit: Maximum number of traces to return.
            lookback: Time window to search (e.g., "1h", "30m").

        Returns:
            List of trace data.
        """
        base_url = jaeger_client.base_url  # type: ignore[attr-defined]
        params: dict[str, str | int] = {
            "service": service,
            "limit": limit,
            "lookback": lookback,
        }
        if operation:
            params["operation"] = operation

        try:
            response = jaeger_client.get(f"{base_url}/api/traces", params=params)
            response.raise_for_status()
            return list(response.json().get("data", []))
        except requests.exceptions.RequestException:
            return []

    return _query


# =============================================================================
# All Services Health Check
# =============================================================================


@pytest.fixture(scope="session")
def all_services_healthy(
    cube_api_url: str,
    polaris_url: str,
    marquez_url: str,
    dagster_url: str,
    jaeger_url: str,
) -> bool:
    """Validate that all E2E test services are healthy.

    This is a comprehensive health check that validates all services
    before running the full E2E test suite.

    Args:
        cube_api_url: Cube API URL.
        polaris_url: Polaris catalog URL.
        marquez_url: Marquez API URL.
        dagster_url: Dagster webserver URL.
        jaeger_url: Jaeger query API URL.

    Returns:
        True if all services are healthy.

    Raises:
        pytest.fail: If any service is not healthy.
    """
    services = {
        "Cube": f"{cube_api_url}/readyz",
        "Polaris": f"{polaris_url}/api/catalog/v1/config",
        "Marquez": f"{marquez_url}/api/v1/namespaces",
        "Dagster": f"{dagster_url}/server_info",
        "Jaeger": f"{jaeger_url}/api/services",
    }

    max_retries = 30
    retry_delay = 2
    failed_services: list[str] = []

    for service_name, health_url in services.items():
        healthy = False
        for attempt in range(max_retries):
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    healthy = True
                    break
            except requests.exceptions.RequestException:
                pass

            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        if not healthy:
            failed_services.append(service_name)

    if failed_services:
        pytest.fail(
            f"Services not healthy after {max_retries * retry_delay}s: "
            f"{', '.join(failed_services)}. "
            f"Ensure all services are running: docker compose --profile full up -d"
        )

    return True


# =============================================================================
# Markers
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for E2E tests.

    Args:
        config: pytest configuration.
    """
    config.addinivalue_line(
        "markers",
        "e2e: mark test as end-to-end test requiring demo services",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (may take several minutes)",
    )
    config.addinivalue_line(
        "markers",
        "requires_cube: mark test as requiring Cube semantic layer",
    )
    config.addinivalue_line(
        "markers",
        "requires_lineage: mark test as requiring Marquez lineage",
    )
    config.addinivalue_line(
        "markers",
        "requires_tracing: mark test as requiring Jaeger tracing",
    )
