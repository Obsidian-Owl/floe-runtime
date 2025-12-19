"""Abstract base class for integration tests.

T040: [US3] Create IntegrationTestBase class

This module provides a standardized base class for integration tests that
require Docker services (Polaris, LocalStack, PostgreSQL, etc.). It handles:

- Service availability detection with context-aware hostname resolution
- Automatic credential loading from Docker-generated files
- Common test configuration factories
- Cleanup utilities for test isolation
- Timeout and retry configuration

Usage:
    ```python
    from testing.base_classes import IntegrationTestBase

    class TestMyFeature(IntegrationTestBase):
        '''Integration tests for MyFeature.'''

        @pytest.fixture(autouse=True)
        def setup_test(self, polaris_catalog):
            '''Setup test with Polaris catalog.'''
            self.catalog = polaris_catalog

        @pytest.mark.integration
        @pytest.mark.requirement("FR-XXX")
        def test_feature_works(self):
            '''Test that feature works with real services.'''
            # Service URLs resolved based on context (Docker vs host)
            url = self.get_service_url("polaris", 8181)
            assert url == "http://polaris:8181" or url == "http://localhost:8181"
    ```

Requirements:
    - Docker services must be running (via testing/docker/docker-compose.yml)
    - Tests should be marked with @pytest.mark.integration
    - Run via: ./testing/docker/scripts/run-integration-tests.sh
"""

from __future__ import annotations

from collections.abc import Generator
import os
from pathlib import Path
import socket
from typing import Any
from unittest.mock import patch
import uuid

import pytest

# =============================================================================
# Constants
# =============================================================================

# Default timeout for service availability checks
DEFAULT_SERVICE_TIMEOUT = 30

# Paths relative to repository root
TESTING_DIR = Path(__file__).parent.parent
DOCKER_DIR = TESTING_DIR / "docker"
POLARIS_CREDENTIALS_FILE = DOCKER_DIR / "config" / "polaris-credentials.env"


# =============================================================================
# Service Detection Utilities
# =============================================================================


def is_running_in_docker() -> bool:
    """Detect if tests are running inside a Docker container.

    Detection methods (in order):
    1. DOCKER_CONTAINER environment variable (set by test-runner container)
    2. /.dockerenv file exists (Docker creates this)
    3. /proc/1/cgroup contains 'docker' (Linux containers)

    Returns:
        True if running inside Docker, False otherwise
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
    """Get hostname for a service based on execution context.

    Args:
        service: Service name (e.g., 'polaris', 'localstack', 'postgres')

    Returns:
        Internal hostname if in Docker, 'localhost' otherwise
    """
    if is_running_in_docker():
        return service
    return "localhost"


def check_service_available(service: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a service is available via TCP connection.

    Args:
        service: Service name for hostname resolution
        port: Port number to check
        timeout: Connection timeout in seconds

    Returns:
        True if service is reachable, False otherwise
    """
    host = get_service_host(service)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (TimeoutError, ConnectionRefusedError, OSError):
        return False


def load_polaris_credentials() -> dict[str, str]:
    """Load Polaris credentials from Docker-generated file.

    Returns:
        Dictionary of credentials (POLARIS_CLIENT_ID, POLARIS_CLIENT_SECRET, etc.)

    Raises:
        FileNotFoundError: If credentials file doesn't exist
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
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                credentials[key] = value

    return credentials


def ensure_polaris_credentials_in_env() -> None:
    """Load Polaris credentials into environment if not already set.

    Silently skips if credentials file doesn't exist - tests will fail
    with better error messages from the service checks.
    """
    try:
        creds = load_polaris_credentials()
        for key, value in creds.items():
            if key not in os.environ:
                os.environ[key] = value
    except FileNotFoundError:
        pass


# =============================================================================
# Base Test Class
# =============================================================================


class IntegrationTestBase:
    """Abstract base class for integration tests requiring Docker services.

    This class provides common utilities for integration tests that need
    to interact with Docker services like Polaris, LocalStack, PostgreSQL, etc.

    Features:
        - Automatic service availability detection
        - Context-aware hostname resolution (Docker vs host)
        - Polaris credentials auto-loading
        - Test isolation utilities (unique namespace generation)
        - Common configuration factories

    Class Attributes:
        required_services: List of (service_name, port) tuples required for tests
        service_timeout: Timeout in seconds for service availability checks

    Usage:
        class TestMyFeature(IntegrationTestBase):
            required_services = [("polaris", 8181), ("localstack", 4566)]

            @pytest.mark.integration
            def test_something(self):
                assert self.is_service_available("polaris", 8181)
    """

    # Override in subclass to specify required services
    required_services: list[tuple[str, int]] = []

    # Default timeout for service checks
    service_timeout: float = DEFAULT_SERVICE_TIMEOUT

    # ==========================================================================
    # Service Utilities
    # ==========================================================================

    @staticmethod
    def is_running_in_docker() -> bool:
        """Check if tests are running inside Docker container."""
        return is_running_in_docker()

    @staticmethod
    def get_service_host(service: str) -> str:
        """Get hostname for a service based on execution context."""
        return get_service_host(service)

    def get_service_url(
        self,
        service: str,
        port: int,
        protocol: str = "http",
    ) -> str:
        """Get full URL for a service.

        Args:
            service: Service name (e.g., 'polaris', 'localstack')
            port: Port number
            protocol: URL protocol (default: 'http')

        Returns:
            Full URL (e.g., 'http://polaris:8181' or 'http://localhost:8181')
        """
        host = self.get_service_host(service)
        return f"{protocol}://{host}:{port}"

    def is_service_available(
        self,
        service: str,
        port: int,
        timeout: float | None = None,
    ) -> bool:
        """Check if a service is available.

        Args:
            service: Service name
            port: Port number
            timeout: Connection timeout (defaults to class attribute)

        Returns:
            True if service is reachable
        """
        return check_service_available(
            service,
            port,
            timeout=timeout or self.service_timeout,
        )

    def require_services(self) -> None:
        """Assert all required services are available.

        Raises:
            pytest.skip: If any required service is unavailable
        """
        for service, port in self.required_services:
            if not self.is_service_available(service, port):
                pytest.skip(f"Required service unavailable: {service}:{port}")

    # ==========================================================================
    # Polaris Utilities
    # ==========================================================================

    @staticmethod
    def ensure_polaris_credentials() -> None:
        """Load Polaris credentials into environment."""
        ensure_polaris_credentials_in_env()

    def get_polaris_config(self) -> dict[str, Any]:
        """Get Polaris configuration for testing.

        Note: Uses PRINCIPAL_ROLE:ALL scope which grants maximum privileges.
        This should ONLY be used in test environments.

        Returns:
            Configuration dictionary suitable for PolarisCatalogConfig
        """
        self.ensure_polaris_credentials()
        return {
            "uri": os.environ.get(
                "POLARIS_URI",
                self.get_service_url("polaris", 8181) + "/api/catalog",
            ),
            "warehouse": os.environ.get("POLARIS_WAREHOUSE", "warehouse"),
            "client_id": os.environ.get("POLARIS_CLIENT_ID", "root"),
            "client_secret": os.environ.get("POLARIS_CLIENT_SECRET", "s3cr3t"),
            # TESTING ONLY: Maximum privileges for test environment
            "scope": os.environ.get("POLARIS_SCOPE", "PRINCIPAL_ROLE:ALL"),
            # S3 FileIO configuration for LocalStack
            "s3_endpoint": os.environ.get(
                "LOCALSTACK_ENDPOINT",
                self.get_service_url("localstack", 4566),
            ),
            "s3_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID", "test"),
            "s3_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
            "s3_region": os.environ.get("AWS_REGION", "us-east-1"),
            "s3_path_style_access": True,
        }

    # ==========================================================================
    # Test Isolation Utilities
    # ==========================================================================

    @staticmethod
    def generate_unique_namespace(prefix: str = "test") -> str:
        """Generate a unique namespace for test isolation.

        Args:
            prefix: Namespace prefix (default: 'test')

        Returns:
            Unique namespace like 'test_a1b2c3d4'
        """
        suffix = uuid.uuid4().hex[:8]
        return f"{prefix}_{suffix}"

    @staticmethod
    def generate_unique_table_name(prefix: str = "table") -> str:
        """Generate a unique table name for test isolation.

        Args:
            prefix: Table name prefix (default: 'table')

        Returns:
            Unique table name like 'table_a1b2c3d4'
        """
        suffix = uuid.uuid4().hex[:8]
        return f"{prefix}_{suffix}"

    # ==========================================================================
    # Environment Utilities
    # ==========================================================================

    @staticmethod
    def with_env_vars(**env_vars: str) -> Any:
        """Context manager to temporarily set environment variables.

        Args:
            **env_vars: Environment variables to set

        Returns:
            Context manager that sets and restores environment variables

        Example:
            with self.with_env_vars(MY_VAR="value"):
                assert os.environ["MY_VAR"] == "value"
        """
        return patch.dict(os.environ, env_vars)


# =============================================================================
# Service-Specific Base Classes
# =============================================================================


class PolarisIntegrationTestBase(IntegrationTestBase):
    """Base class for tests requiring Polaris catalog.

    Automatically checks Polaris availability and loads credentials.

    Usage:
        class TestPolarisFeature(PolarisIntegrationTestBase):
            @pytest.mark.integration
            def test_catalog_operations(self):
                config = self.get_polaris_config()
                # Use config to create catalog...
    """

    required_services = [("polaris", 8181), ("localstack", 4566)]

    @pytest.fixture(autouse=True)
    def _ensure_polaris_available(self) -> Generator[None, None, None]:
        """Fixture to ensure Polaris is available before each test."""
        self.ensure_polaris_credentials()

        # Check Polaris availability
        if not self.is_service_available("polaris", 8181):
            pytest.skip("Polaris service not available")

        # Check LocalStack availability (required for S3)
        if not self.is_service_available("localstack", 4566):
            pytest.skip("LocalStack service not available")

        yield


class CubeIntegrationTestBase(IntegrationTestBase):
    """Base class for tests requiring Cube semantic layer.

    Automatically checks Cube and dependent services availability.

    Usage:
        class TestCubeQueries(CubeIntegrationTestBase):
            @pytest.mark.integration
            def test_cube_query(self):
                url = self.get_cube_url()
                # Use URL for Cube API calls...
    """

    required_services = [
        ("cube", 4000),
        ("polaris", 8181),
        ("localstack", 4566),
        ("trino", 8080),
    ]

    def get_cube_url(self, path: str = "") -> str:
        """Get Cube API URL.

        Args:
            path: Optional API path (e.g., '/cubejs-api/v1/load')

        Returns:
            Full Cube URL
        """
        base_url = self.get_service_url("cube", 4000)
        return f"{base_url}{path}"

    @pytest.fixture(autouse=True)
    def _ensure_cube_available(self) -> Generator[None, None, None]:
        """Fixture to ensure Cube and dependencies are available."""
        for service, port in self.required_services:
            if not self.is_service_available(service, port):
                pytest.skip(f"{service} service not available")
        yield


class PostgresIntegrationTestBase(IntegrationTestBase):
    """Base class for tests requiring PostgreSQL.

    Usage:
        class TestPostgresFeature(PostgresIntegrationTestBase):
            @pytest.mark.integration
            def test_postgres_query(self):
                conn_str = self.get_postgres_connection_string()
                # Use connection string...
    """

    required_services = [("postgres", 5432)]

    def get_postgres_connection_string(
        self,
        database: str = "postgres",
        user: str = "postgres",
        password: str = "postgres",
    ) -> str:
        """Get PostgreSQL connection string.

        Args:
            database: Database name (default: 'postgres')
            user: Username (default: 'postgres')
            password: Password (default: 'postgres')

        Returns:
            PostgreSQL connection string
        """
        host = self.get_service_host("postgres")
        return f"postgresql://{user}:{password}@{host}:5432/{database}"

    @pytest.fixture(autouse=True)
    def _ensure_postgres_available(self) -> Generator[None, None, None]:
        """Fixture to ensure PostgreSQL is available."""
        if not self.is_service_available("postgres", 5432):
            pytest.skip("PostgreSQL service not available")
        yield


class DbtIntegrationTestBase(IntegrationTestBase):
    """Base class for dbt integration tests.

    Provides utilities for dbt project setup and profile generation testing.

    Usage:
        class TestDbtProfiles(DbtIntegrationTestBase):
            @pytest.fixture
            def dbt_project_dir(self, tmp_path):
                return self.create_minimal_dbt_project(tmp_path)

            @pytest.mark.integration
            def test_profile_generation(self, dbt_project_dir):
                # Test profile generation...
    """

    def create_minimal_dbt_project(
        self,
        project_dir: Path,
        project_name: str = "test_project",
        profile_name: str = "floe",
    ) -> Path:
        """Create a minimal dbt project for testing.

        Args:
            project_dir: Directory to create project in
            project_name: dbt project name
            profile_name: dbt profile name

        Returns:
            Path to created project directory
        """
        import yaml

        project_path = project_dir / project_name
        project_path.mkdir(parents=True, exist_ok=True)

        # Create dbt_project.yml
        dbt_project = {
            "name": project_name,
            "version": "1.0.0",
            "config-version": 2,
            "profile": profile_name,
        }
        (project_path / "dbt_project.yml").write_text(yaml.safe_dump(dbt_project))

        # Create models directory
        models_dir = project_path / "models"
        models_dir.mkdir(exist_ok=True)

        return project_path

    def create_profiles_file(
        self,
        profiles_dir: Path,
        profile_content: dict[str, Any],
    ) -> Path:
        """Create a profiles.yml file.

        Args:
            profiles_dir: Directory to create profiles.yml in
            profile_content: Profile configuration dictionary

        Returns:
            Path to created profiles.yml
        """
        import yaml

        profiles_dir.mkdir(parents=True, exist_ok=True)
        profiles_path = profiles_dir / "profiles.yml"
        profiles_path.write_text(yaml.safe_dump(profile_content))
        return profiles_path
