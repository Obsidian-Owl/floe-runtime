"""Docker Compose service lifecycle fixtures for E2E testing.

This module provides pytest fixtures for managing Docker Compose services
during integration and E2E tests. It handles:

- Starting/stopping Docker Compose profiles
- Health check waiting
- Service URL resolution
- Cleanup after tests

Usage:
    ```python
    @pytest.mark.integration
    def test_polaris_connection(docker_services):
        '''Test requires Docker services.'''
        polaris_url = docker_services.get_url("polaris", 8181)
        # ... test code
    ```

Requirements:
    - Docker and Docker Compose installed
    - testing/docker/docker-compose.yml available
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import requests


# Path to docker-compose.yml relative to repository root
DOCKER_COMPOSE_DIR = Path(__file__).parent.parent / "docker"
DOCKER_COMPOSE_FILE = DOCKER_COMPOSE_DIR / "docker-compose.yml"

# Default timeout for service health checks (seconds)
DEFAULT_TIMEOUT = 120

# Service health check endpoints
SERVICE_HEALTH_CHECKS: dict[str, dict[str, Any]] = {
    "postgres": {
        "type": "tcp",
        "port": 5432,
    },
    "minio": {
        "type": "http",
        "port": 9000,
        "path": "/minio/health/live",
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


@dataclass
class DockerServices:
    """Manager for Docker Compose services during testing.

    Provides methods to interact with Docker Compose services,
    check their health, and get their URLs.

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
    _host: str = "localhost"

    def get_url(self, service: str, port: int, protocol: str = "http") -> str:
        """Get the URL for a service.

        Args:
            service: Service name (e.g., 'polaris', 'minio')
            port: Port number
            protocol: URL protocol (http, https, etc.)

        Returns:
            Full URL to the service endpoint
        """
        return f"{protocol}://{self._host}:{port}"

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
        return f"postgresql://{user}:{password}@{self._host}:5432/{database}"

    def get_s3_config(self) -> dict[str, str]:
        """Get S3/MinIO configuration for PyIceberg.

        Returns:
            Dictionary with S3 configuration suitable for PyIceberg
        """
        return {
            "s3.endpoint": f"http://{self._host}:9000",
            "s3.access-key-id": os.environ.get("MINIO_ROOT_USER", "minioadmin"),
            "s3.secret-access-key": os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin"),
            "s3.region": os.environ.get("AWS_REGION", "us-east-1"),
            "s3.path-style-access": "true",
        }

    def get_polaris_config(self) -> dict[str, str]:
        """Get Polaris REST catalog configuration for PyIceberg.

        Returns:
            Dictionary with catalog configuration suitable for PyIceberg
        """
        return {
            "type": "rest",
            "uri": f"http://{self._host}:8181/api/catalog",
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
            return self._check_tcp(port)
        elif check_type == "http":
            path = check.get("path", "/")
            return self._check_http(port, path)

        return False

    def _check_tcp(self, port: int) -> bool:
        """Check TCP connectivity."""
        import socket

        try:
            with socket.create_connection((self._host, port), timeout=5):
                return True
        except (OSError, ConnectionRefusedError):
            return False

    def _check_http(self, port: int, path: str) -> bool:
        """Check HTTP endpoint."""
        try:
            url = f"http://{self._host}:{port}{path}"
            response = requests.get(url, timeout=5)
            return response.status_code < 500
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

    Includes: PostgreSQL, MinIO, Polaris, Jaeger
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
def running_storage_services(docker_services_storage: DockerServices) -> DockerServices:
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
def running_full_services(docker_services_full: DockerServices) -> DockerServices:
    """Fixture that automatically starts all services.

    WARNING: This fixture starts Docker containers. Use sparingly and only
    in E2E tests marked with @pytest.mark.e2e.

    Yields:
        DockerServices with all running services
    """
    docker_services_full.start()
    yield docker_services_full
    docker_services_full.stop()
