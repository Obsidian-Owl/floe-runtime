"""Docker Compose service lifecycle fixtures for E2E testing.

This module provides pytest fixtures for managing Docker Compose services
during integration and E2E tests. It handles:

- Starting/stopping Docker Compose profiles
- Health check waiting
- Service URL resolution (context-aware: host vs Docker network)
- Cleanup after tests

The fixtures automatically detect whether tests are running inside Docker
(via the test-runner container) or from the host machine, and use the
appropriate hostnames for service communication.

Usage:
    ```python
    @pytest.mark.integration
    def test_polaris_connection(docker_services):
        '''Test requires Docker services.'''
        polaris_url = docker_services.get_url("polaris", 8181)
        # Returns http://polaris:8181 inside Docker
        # Returns http://localhost:8181 from host
    ```

Requirements:
    - Docker and Docker Compose installed
    - testing/docker/docker-compose.yml available
    - For integration tests: run via `make test-integration` (recommended)
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass, field
import os
from pathlib import Path
import subprocess
import time
from typing import Any, TypeVar

import pytest
import requests

# Type variable for generic polling functions
T = TypeVar("T")

# Path to docker-compose.yml relative to repository root
DOCKER_COMPOSE_DIR = Path(__file__).parent.parent / "docker"
DOCKER_COMPOSE_FILE = DOCKER_COMPOSE_DIR / "docker-compose.yml"
POLARIS_CREDENTIALS_FILE = DOCKER_COMPOSE_DIR / "config" / "polaris-credentials.env"

# Default timeout for service health checks (seconds)
DEFAULT_TIMEOUT = 120

# Default polling configuration
DEFAULT_POLL_INTERVAL = 0.5
DEFAULT_POLL_TIMEOUT = 10.0


def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = DEFAULT_POLL_TIMEOUT,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    description: str = "condition",
) -> bool:
    """Wait for a condition to become True using polling.

    This is a generic polling helper that replaces hardcoded time.sleep() calls
    in tests. Instead of sleeping for a fixed duration and hoping an operation
    completed, this function polls until the condition is met or timeout occurs.

    Args:
        condition: Callable that returns True when the condition is met.
            Should not raise exceptions for transient failures.
        timeout: Maximum time to wait in seconds. Default: 10.0
        poll_interval: Time between polls in seconds. Default: 0.5
        description: Human-readable description for error messages.

    Returns:
        True if condition was met within timeout, False otherwise.

    Example:
        >>> def job_exists():
        ...     jobs = marquez_client.get_jobs(namespace)
        ...     return "my_job" in [j["name"] for j in jobs]
        >>> wait_for_condition(job_exists, timeout=15, description="job to appear")
        True

        >>> # Can also be used inline with lambda
        >>> wait_for_condition(
        ...     lambda: len(jaeger.get_traces(service="test")) > 0,
        ...     timeout=5,
        ...     description="traces to be exported"
        ... )
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if condition():
                return True
        except Exception:
            # Ignore exceptions during polling - service may not be ready yet
            pass
        time.sleep(poll_interval)
    return False


def poll_until(
    fetch_func: Callable[[], T],
    check_func: Callable[[T], bool],
    timeout: float = DEFAULT_POLL_TIMEOUT,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    description: str = "expected result",
) -> T | None:
    """Poll until a check function returns True on fetched data.

    Two-phase polling: fetches data then checks it. Useful when you need
    to verify the fetched data, not just that an operation succeeded.

    Args:
        fetch_func: Callable that fetches data (e.g., API call).
        check_func: Callable that takes fetched data and returns True if valid.
        timeout: Maximum time to wait in seconds. Default: 10.0
        poll_interval: Time between polls in seconds. Default: 0.5
        description: Human-readable description for error messages.

    Returns:
        The fetched data that passed the check, or None if timeout.

    Example:
        >>> result = poll_until(
        ...     fetch_func=lambda: marquez_client.get_runs(job_name),
        ...     check_func=lambda runs: len(runs) > 0 and runs[0]["state"] == "COMPLETED",
        ...     timeout=15,
        ...     description="run to complete"
        ... )
        >>> assert result is not None
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            data = fetch_func()
            if check_func(data):
                return data
        except Exception:
            # Ignore exceptions during polling - service may not be ready yet
            pass
        time.sleep(poll_interval)
    return None


def is_running_in_docker() -> bool:
    """Detect if tests are running inside a Docker container.

    This is used to determine whether to use internal Docker hostnames
    (e.g., 'polaris', 'localstack') or external localhost endpoints.

    Detection methods:
    1. DOCKER_CONTAINER environment variable (set by test-runner container)
    2. /.dockerenv file exists (Docker creates this)
    3. /proc/1/cgroup contains 'docker' (Linux containers)

    Returns:
        True if running inside Docker, False otherwise

    Example:
        >>> is_running_in_docker()
        True  # When running via `make test-integration`
        False # When running `uv run pytest` from host
    """
    # Check environment variable (most reliable - we set this explicitly)
    if os.environ.get("DOCKER_CONTAINER") == "1":
        return True

    # Check for Docker's env file
    if Path("/.dockerenv").exists():
        return True

    # Check cgroup (Linux only)
    try:
        with open("/proc/1/cgroup") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        pass

    return False


def get_service_host(service: str) -> str:
    """Get the appropriate hostname for a service based on execution context.

    When running inside Docker (via test-runner), uses the internal
    Docker network hostname. When running from the host machine,
    uses localhost.

    Args:
        service: Service name (e.g., 'polaris', 'localstack', 'postgres')

    Returns:
        Hostname to use for connecting to the service

    Example:
        >>> get_service_host("polaris")
        'polaris'  # Inside Docker
        'localhost'  # From host
    """
    if is_running_in_docker():
        return service
    return "localhost"


# Service health check endpoints
SERVICE_HEALTH_CHECKS: dict[str, dict[str, Any]] = {
    "postgres": {
        "type": "tcp",
        "port": 5432,
    },
    "localstack": {
        "type": "http",
        "port": 4566,
        "path": "/_localstack/health",
    },
    "polaris": {
        "type": "http",
        "port": 8181,
        "path": "/api/catalog/v1/config",
    },
    "trino": {
        "type": "http",
        "port": 8080,
        "path": "/v1/info",
    },
    "jaeger": {
        "type": "http",
        "port": 16686,
        "path": "/",
    },
    "marquez": {
        "type": "http",
        "port": 5001,
        "path": "/healthcheck",
    },
    "cube": {
        "type": "http",
        "port": 4000,
        "path": "/readyz",
    },
}


def is_service_available(service: str, timeout: float = 5.0) -> bool:
    """Check if a service is available and responding.

    Uses the health check configuration from SERVICE_HEALTH_CHECKS to verify
    that a service is running and ready to accept connections.

    Args:
        service: Service name (e.g., 'polaris', 'localstack', 'postgres')
        timeout: Maximum time to wait for service response

    Returns:
        True if the service is available, False otherwise

    Example:
        >>> is_service_available("polaris")
        True  # When Polaris is running
        False # When Polaris is not available
    """
    if service not in SERVICE_HEALTH_CHECKS:
        return False

    check = SERVICE_HEALTH_CHECKS[service]
    check_type = check["type"]
    port = check["port"]
    host = get_service_host(service)

    if check_type == "tcp":
        import socket

        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False
    elif check_type == "http":
        path = check.get("path", "/")
        try:
            response = requests.get(
                f"http://{host}:{port}{path}",
                timeout=timeout,
            )
            return bool(response.status_code < 500)
        except requests.RequestException:
            return False

    return False


@dataclass
class DockerServices:
    """Manager for Docker Compose services during testing.

    Provides methods to interact with Docker Compose services,
    check their health, and get their URLs.

    Automatically detects whether tests are running inside Docker
    (via test-runner) or from the host machine, and uses the
    appropriate hostnames accordingly.

    Attributes:
        compose_file: Path to docker-compose.yml
        profile: Docker Compose profile to use
        project_name: Docker Compose project name
        started_services: Set of services that were started
    """

    compose_file: Path
    profile: str = "storage"
    project_name: str = "floe-test"
    started_services: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Initialize context-aware hostname resolution."""
        self._in_docker = is_running_in_docker()

    def _get_host(self, service: str) -> str:
        """Get hostname for a service based on execution context.

        Args:
            service: Service name

        Returns:
            Internal hostname if in Docker, localhost otherwise
        """
        return service if self._in_docker else "localhost"

    def get_url(self, service: str, port: int, protocol: str = "http") -> str:
        """Get the URL for a service.

        Automatically uses internal Docker hostname when running
        inside Docker network, or localhost when running from host.

        Args:
            service: Service name (e.g., 'polaris', 'localstack')
            port: Port number
            protocol: URL protocol (http, https, etc.)

        Returns:
            Full URL to the service endpoint

        Example:
            >>> services.get_url("polaris", 8181)
            'http://polaris:8181'  # Inside Docker
            'http://localhost:8181'  # From host
        """
        host = self._get_host(service)
        return f"{protocol}://{host}:{port}"

    def get_connection_string(
        self,
        service: str,
        *,
        database: str = "postgres",
        user: str = "postgres",
        password: str = "postgres",
    ) -> str:
        """Get PostgreSQL connection string.

        Args:
            service: Service name (should be 'postgres')
            database: Database name
            user: Username
            password: Password

        Returns:
            PostgreSQL connection string
        """
        host = self._get_host(service)
        return f"postgresql://{user}:{password}@{host}:5432/{database}"

    def get_s3_config(self) -> dict[str, str]:
        """Get S3/LocalStack configuration for PyIceberg.

        Returns:
            Dictionary with S3 configuration suitable for PyIceberg
        """
        host = self._get_host("localstack")
        return {
            "s3.endpoint": f"http://{host}:4566",
            "s3.access-key-id": os.environ.get("AWS_ACCESS_KEY_ID", "test"),
            "s3.secret-access-key": os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
            "s3.region": os.environ.get("AWS_REGION", "us-east-1"),
            "s3.path-style-access": "true",
        }

    def get_polaris_config(self) -> dict[str, str]:
        """Get Polaris REST catalog configuration for PyIceberg.

        Returns:
            Dictionary with catalog configuration suitable for PyIceberg
        """
        host = self._get_host("polaris")
        return {
            "type": "rest",
            "uri": f"http://{host}:8181/api/catalog",
            "warehouse": "warehouse",
            **self.get_s3_config(),
        }

    def wait_for_service(
        self,
        service: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> bool:
        """Wait for a service to become healthy.

        Args:
            service: Service name
            timeout: Maximum time to wait in seconds

        Returns:
            True if service is healthy, False if timeout

        Raises:
            ValueError: If service is unknown
        """
        if service not in SERVICE_HEALTH_CHECKS:
            raise ValueError(f"Unknown service: {service}")

        check = SERVICE_HEALTH_CHECKS[service]
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self._check_service_health(service, check):
                return True
            time.sleep(2)

        return False

    def _check_service_health(
        self,
        service: str,
        check: dict[str, Any],
    ) -> bool:
        """Check if a service is healthy.

        Args:
            service: Service name
            check: Health check configuration

        Returns:
            True if healthy, False otherwise
        """
        check_type = check["type"]
        port = check["port"]

        if check_type == "tcp":
            return self._check_tcp(port, service)
        elif check_type == "http":
            path = check.get("path", "/")
            return self._check_http(port, path, service)

        return False

    def _check_tcp(self, port: int, service: str = "localhost") -> bool:
        """Check TCP connectivity."""
        import socket

        host = self._get_host(service)
        try:
            with socket.create_connection((host, port), timeout=5):
                return True
        except OSError:
            return False

    def _check_http(self, port: int, path: str, service: str = "localhost") -> bool:
        """Check HTTP endpoint."""
        host = self._get_host(service)
        try:
            url = f"http://{host}:{port}{path}"
            response = requests.get(url, timeout=5)
            return bool(response.status_code < 500)
        except requests.RequestException:
            return False

    def start(self) -> None:
        """Start Docker Compose services."""
        cmd = [
            "docker",
            "compose",
            "-f",
            str(self.compose_file),
            "-p",
            self.project_name,
            "--profile",
            self.profile,
            "up",
            "-d",
            "--wait",
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def stop(self) -> None:
        """Stop Docker Compose services."""
        cmd = [
            "docker",
            "compose",
            "-f",
            str(self.compose_file),
            "-p",
            self.project_name,
            "--profile",
            self.profile,
            "down",
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def logs(self, service: str | None = None) -> str:
        """Get logs from services.

        Args:
            service: Optional service name, or all services if None

        Returns:
            Log output as string
        """
        cmd = [
            "docker",
            "compose",
            "-f",
            str(self.compose_file),
            "-p",
            self.project_name,
            "logs",
        ]
        if service:
            cmd.append(service)

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout


def docker_compose_file() -> Path:
    """Get the path to docker-compose.yml.

    Returns:
        Path to docker-compose.yml

    Raises:
        FileNotFoundError: If docker-compose.yml doesn't exist
    """
    if not DOCKER_COMPOSE_FILE.exists():
        raise FileNotFoundError(
            f"Docker Compose file not found: {DOCKER_COMPOSE_FILE}\n"
            "Run from repository root or set FLOE_DOCKER_COMPOSE_PATH"
        )
    return DOCKER_COMPOSE_FILE


def load_polaris_credentials() -> dict[str, str]:
    """Load Polaris credentials from the auto-generated credentials file.

    The credentials file is generated by the polaris-init container when
    Docker Compose services start. It contains the auto-generated OAuth2
    client credentials for the Polaris catalog.

    Returns:
        Dictionary of environment variables from the credentials file

    Raises:
        FileNotFoundError: If credentials file doesn't exist (run docker compose first)

    Example:
        >>> creds = load_polaris_credentials()
        >>> creds["POLARIS_CLIENT_ID"]
        '2eb9c356212270e9'
    """
    if not POLARIS_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Polaris credentials file not found: {POLARIS_CREDENTIALS_FILE}\n"
            "Start Docker services first:\n"
            "  cd testing/docker && docker compose --profile storage up -d"
        )

    credentials: dict[str, str] = {}
    with open(POLARIS_CREDENTIALS_FILE) as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Parse KEY=VALUE format
            if "=" in line:
                key, value = line.split("=", 1)
                credentials[key] = value

    return credentials


def ensure_polaris_credentials_in_env() -> None:
    """Load Polaris credentials into environment variables if not already set.

    This function loads the auto-generated credentials file and sets the
    environment variables if they are not already defined. This allows
    tests to automatically pick up the dynamic credentials without manual
    configuration.

    Call this at the start of integration tests or in conftest.py.

    Example:
        >>> from testing.fixtures.services import ensure_polaris_credentials_in_env
        >>> ensure_polaris_credentials_in_env()
        >>> os.environ["POLARIS_CLIENT_ID"]  # Now available
        '2eb9c356212270e9'
    """
    try:
        creds = load_polaris_credentials()
        for key, value in creds.items():
            # Only set if not already defined (allow manual override)
            if key not in os.environ:
                os.environ[key] = value
    except FileNotFoundError:
        # Silently skip if file doesn't exist - tests will fail with better errors
        pass


def wait_for_services(
    services: list[str],
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, bool]:
    """Wait for multiple services to become healthy.

    Args:
        services: List of service names to wait for
        timeout: Maximum time to wait for each service

    Returns:
        Dictionary mapping service names to health status
    """
    docker = DockerServices(
        compose_file=DOCKER_COMPOSE_FILE,
        profile="full",
    )

    results = {}
    for service in services:
        results[service] = docker.wait_for_service(service, timeout)

    return results


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def docker_compose_path() -> Path:
    """Fixture providing path to docker-compose.yml."""
    return docker_compose_file()


@pytest.fixture(scope="session")
def docker_services_base(docker_compose_path: Path) -> DockerServices:
    """Fixture providing DockerServices manager (base profile - no storage)."""
    return DockerServices(
        compose_file=docker_compose_path,
        profile="",  # Base profile only
        project_name="floe-test-base",
    )


@pytest.fixture(scope="session")
def docker_services_storage(docker_compose_path: Path) -> DockerServices:
    """Fixture providing DockerServices manager (storage profile).

    Includes: PostgreSQL, LocalStack (S3+STS+IAM), Polaris, Jaeger
    """
    return DockerServices(
        compose_file=docker_compose_path,
        profile="storage",
        project_name="floe-test-storage",
    )


@pytest.fixture(scope="session")
def docker_services_compute(docker_compose_path: Path) -> DockerServices:
    """Fixture providing DockerServices manager (compute profile).

    Includes: All storage services + Trino, Spark
    """
    return DockerServices(
        compose_file=docker_compose_path,
        profile="compute",
        project_name="floe-test-compute",
    )


@pytest.fixture(scope="session")
def docker_services_full(docker_compose_path: Path) -> DockerServices:
    """Fixture providing DockerServices manager (full profile).

    Includes: All services (storage + compute + Cube + Marquez)
    """
    return DockerServices(
        compose_file=docker_compose_path,
        profile="full",
        project_name="floe-test-full",
    )


# Alias for most common use case
@pytest.fixture(scope="session")
def docker_services(docker_services_storage: DockerServices) -> DockerServices:
    """Default fixture alias for storage profile."""
    return docker_services_storage


# =============================================================================
# Auto-start Fixtures (use with caution - slow!)
# =============================================================================


@pytest.fixture(scope="session")
def running_storage_services(
    docker_services_storage: DockerServices,
) -> Generator[DockerServices, None, None]:
    """Fixture that automatically starts storage services.

    WARNING: This fixture starts Docker containers. Use sparingly and only
    in integration tests marked with @pytest.mark.integration.

    Yields:
        DockerServices with running storage services
    """
    docker_services_storage.start()
    yield docker_services_storage
    docker_services_storage.stop()


@pytest.fixture(scope="session")
def running_full_services(
    docker_services_full: DockerServices,
) -> Generator[DockerServices, None, None]:
    """Fixture that automatically starts all services.

    WARNING: This fixture starts Docker containers. Use sparingly and only
    in E2E tests marked with @pytest.mark.e2e.

    Yields:
        DockerServices with all running services
    """
    docker_services_full.start()
    yield docker_services_full
    docker_services_full.stop()


# =============================================================================
# Two-Tier Configuration Architecture Validation
# =============================================================================


def is_platform_config_loaded() -> bool:
    """Check if platform.yaml is being loaded (not falling back to env vars).

    The Two-Tier Architecture requires platform.yaml to be loaded instead of
    falling back to environment variables. This function validates that the
    platform config is properly resolved.

    Returns:
        True if platform config is loaded from platform.yaml, False if fallback.

    Usage in tests:
        >>> from testing.fixtures.services import is_platform_config_loaded
        >>> assert is_platform_config_loaded(), "Platform config not loaded!"
    """
    try:
        from floe_core.compiler.platform_resolver import PlatformResolver

        resolver = PlatformResolver()
        platform = resolver.load()
        return platform is not None
    except ImportError:
        # floe_core not available
        return False
    except Exception:
        # PlatformNotFoundError or other loading errors
        return False


def get_platform_config_source() -> str:
    """Get description of where platform config is loaded from.

    Useful for debugging and test assertions.

    Returns:
        String describing the config source (e.g., "platform/local/platform.yaml")
        or "environment variables (fallback)" if platform.yaml not found.
    """
    try:
        from floe_core.compiler.platform_resolver import PlatformResolver

        resolver = PlatformResolver()
        # Try to find the path without loading
        env = os.environ.get("FLOE_PLATFORM_ENV", "local")
        for search_path in resolver._search_paths:
            candidate = search_path / env / "platform.yaml"
            if candidate.exists():
                return str(candidate)
        return "environment variables (fallback)"
    except Exception:
        return "environment variables (fallback)"


@pytest.fixture(scope="session")
def platform_config_validation() -> dict[str, Any]:
    """Fixture that validates Two-Tier Configuration is properly loaded.

    Use this fixture in integration tests to verify that platform.yaml
    is being used instead of falling back to environment variables.

    Returns:
        Dictionary with validation results:
            - loaded: bool - Whether platform.yaml was successfully loaded
            - source: str - Description of config source
            - env: str - FLOE_PLATFORM_ENV value
            - platform_spec: PlatformSpec or None

    Example:
        >>> def test_platform_config(platform_config_validation):
        ...     assert platform_config_validation["loaded"], (
        ...         f"Platform config not loaded! Source: {platform_config_validation['source']}"
        ...     )
    """
    result: dict[str, Any] = {
        "loaded": False,
        "source": "unknown",
        "env": os.environ.get("FLOE_PLATFORM_ENV", "not set"),
        "platform_spec": None,
    }

    try:
        from floe_core.compiler.platform_resolver import PlatformResolver

        resolver = PlatformResolver()
        platform = resolver.load()
        result["loaded"] = True
        result["platform_spec"] = platform
        result["source"] = get_platform_config_source()
    except ImportError:
        result["source"] = "floe_core not available"
    except Exception as e:
        result["source"] = f"error: {e}"

    return result


@pytest.fixture
def require_platform_config(platform_config_validation: dict[str, Any]) -> None:
    """Fixture that fails the test if platform.yaml is not loaded.

    Use this fixture to ensure tests only run when Two-Tier Configuration
    is properly set up.

    Raises:
        pytest.fail: If platform.yaml is not loaded.

    Example:
        >>> @pytest.mark.integration
        ... def test_catalog_connection(require_platform_config):
        ...     '''This test requires platform.yaml to be loaded.'''
        ...     pass
    """
    if not platform_config_validation["loaded"]:
        pytest.fail(
            f"Two-Tier Configuration not properly set up!\n"
            f"  FLOE_PLATFORM_ENV: {platform_config_validation['env']}\n"
            f"  Source: {platform_config_validation['source']}\n"
            f"  Expected: platform.yaml loaded via FLOE_PLATFORM_ENV\n"
            f"  Action: Ensure platform/{platform_config_validation['env']}/platform.yaml exists"
        )
