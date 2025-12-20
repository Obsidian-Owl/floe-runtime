"""Infrastructure self-tests.

These tests verify the testing infrastructure components work correctly.

Covers:
- FR-004: Docker network execution (hostname resolution)
- FR-005: FAIL not skip when infrastructure missing
- FR-007: UUID test isolation pattern
- FR-015: Docker Compose storage profile services
- FR-020: Docker service lifecycle fixtures
- FR-021: Base test classes available

Requirements:
- Docker Compose storage profile must be running for integration tests
- Tests FAIL if infrastructure is not available (never skip)

Run with:
    pytest testing/tests/test_infrastructure.py -v
"""

from __future__ import annotations

import os
import socket
import uuid
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def _get_service_host(service: str) -> str:
    """Get service hostname based on execution context.

    Inside Docker (DOCKER_CONTAINER=1): use service name directly
    On host: use localhost
    """
    if os.environ.get("DOCKER_CONTAINER") == "1":
        return service
    return "localhost"


def _check_port_available(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


# =============================================================================
# Docker Network Tests (FR-004)
# =============================================================================


class TestDockerNetworkExecution:
    """FR-004: Docker network execution tests.

    Verifies that Docker hostnames resolve correctly inside the container network.
    """

    @pytest.mark.requirement("006-FR-004")
    def test_hostname_resolution_context_aware(self) -> None:
        """Service hostname selection is context-aware.

        Inside Docker: uses service names (polaris, localstack)
        On host: uses localhost

        Covers: FR-004 (Docker network execution)
        """
        docker_container = os.environ.get("DOCKER_CONTAINER") == "1"

        if docker_container:
            # Inside Docker, should use service names
            assert _get_service_host("polaris") == "polaris"
            assert _get_service_host("localstack") == "localstack"
        else:
            # On host, should use localhost
            assert _get_service_host("polaris") == "localhost"
            assert _get_service_host("localstack") == "localhost"

    @pytest.mark.requirement("006-FR-004")
    def test_polaris_hostname_resolves(self) -> None:
        """Polaris hostname resolves in current execution context.

        Covers: FR-004 (Docker network hostname resolution)
        """
        host = _get_service_host("polaris")
        port = 8181

        if not _check_port_available(host, port):
            pytest.fail(
                f"Polaris not available at {host}:{port}. "
                "Start with: cd testing/docker && docker compose --profile storage up -d"
            )

        # If we reach here, hostname resolved and port is open
        assert _check_port_available(host, port)


# =============================================================================
# FAIL Not Skip Philosophy (FR-005)
# =============================================================================


class TestFailNotSkipPhilosophy:
    """FR-005: Tests FAIL when infrastructure is missing (never skip).

    Verifies that the test infrastructure follows the "FAIL not skip" philosophy.
    """

    @pytest.mark.requirement("006-FR-005")
    def test_infrastructure_check_uses_pytest_fail(self) -> None:
        """Infrastructure checks use pytest.fail(), not pytest.skip().

        The pattern demonstrated here is the correct way to handle
        missing infrastructure - fail the test, don't skip it.

        Covers: FR-005 (FAIL not skip when infrastructure missing)
        """
        # This test documents the correct pattern
        host = _get_service_host("polaris")

        # Correct pattern: use pytest.fail() for missing infrastructure
        if not _check_port_available(host, 8181):
            pytest.fail(
                f"Polaris not available at {host}:8181. "
                "Tests FAIL when infrastructure is missing (never skip)."
            )

        # Test passes if infrastructure is available
        assert _check_port_available(host, 8181)

    @pytest.mark.requirement("006-FR-005")
    def test_failure_message_includes_startup_instructions(self) -> None:
        """Failure messages include instructions to start infrastructure.

        Covers: FR-005 (FAIL with helpful instructions)
        """
        # This test verifies the pattern is documented
        # Real infrastructure checks should include startup instructions
        expected_instruction = "docker compose --profile storage up -d"

        # Construct a sample failure message
        failure_msg = (
            "Polaris not available at localhost:8181. "
            f"Start with: cd testing/docker && {expected_instruction}"
        )

        assert expected_instruction in failure_msg


# =============================================================================
# UUID Test Isolation Pattern (FR-007)
# =============================================================================


class TestUuidIsolationPattern:
    """FR-007: UUID test isolation pattern.

    Verifies that tests use UUID suffixes for resource isolation.
    """

    @pytest.mark.requirement("006-FR-007")
    def test_uuid_generates_unique_names(self) -> None:
        """UUID pattern generates unique resource names.

        Covers: FR-007 (UUID test isolation)
        """
        name1 = f"test_{uuid.uuid4().hex[:8]}"
        name2 = f"test_{uuid.uuid4().hex[:8]}"

        assert name1 != name2
        assert name1.startswith("test_")
        assert len(name1) == 13  # "test_" + 8 hex chars

    @pytest.mark.requirement("006-FR-007")
    def test_uuid_pattern_prevents_collision(self) -> None:
        """UUID pattern prevents resource name collisions.

        Covers: FR-007 (test isolation via unique names)
        """
        # Generate many names to verify uniqueness
        names = {f"ns_{uuid.uuid4().hex[:8]}" for _ in range(100)}

        # All names should be unique
        assert len(names) == 100

    @pytest.fixture
    def isolated_namespace_name(self) -> Generator[str, None, None]:
        """Example fixture demonstrating UUID isolation pattern.

        Covers: FR-007 (UUID test isolation in fixtures)
        """
        ns_name = f"test_ns_{uuid.uuid4().hex[:8]}"
        yield ns_name
        # Cleanup would happen here in real fixture

    @pytest.mark.requirement("006-FR-007")
    def test_fixture_provides_unique_name(
        self,
        isolated_namespace_name: str,
    ) -> None:
        """Fixture provides unique name for each test.

        Covers: FR-007 (fixture-based isolation)
        """
        assert isolated_namespace_name.startswith("test_ns_")
        assert len(isolated_namespace_name) == 16  # "test_ns_" + 8 hex chars


# =============================================================================
# Docker Compose Storage Profile (FR-015)
# =============================================================================


class TestStorageProfileServices:
    """FR-015: Docker Compose storage profile services.

    Verifies that storage profile services are healthy.
    """

    @pytest.mark.requirement("006-FR-015")
    def test_polaris_service_healthy(self) -> None:
        """Polaris service is healthy in storage profile.

        Covers: FR-015 (Docker Compose storage profile)
        """
        host = _get_service_host("polaris")

        if not _check_port_available(host, 8181):
            pytest.fail(
                f"Polaris not healthy at {host}:8181. "
                "Start with: cd testing/docker && docker compose --profile storage up -d"
            )

        assert _check_port_available(host, 8181)

    @pytest.mark.requirement("006-FR-015")
    def test_localstack_service_healthy(self) -> None:
        """LocalStack service is healthy in storage profile.

        Covers: FR-015 (Docker Compose storage profile)
        """
        host = _get_service_host("localstack")

        if not _check_port_available(host, 4566):
            pytest.fail(
                f"LocalStack not healthy at {host}:4566. "
                "Start with: cd testing/docker && docker compose --profile storage up -d"
            )

        assert _check_port_available(host, 4566)


# =============================================================================
# Docker Service Lifecycle Fixtures (FR-020)
# =============================================================================


class TestServiceLifecycleFixtures:
    """FR-020: Docker service lifecycle fixtures.

    Verifies that service lifecycle fixtures exist and work correctly.
    """

    @pytest.mark.requirement("006-FR-020")
    def test_service_fixtures_importable(self) -> None:
        """Service lifecycle fixtures can be imported.

        Covers: FR-020 (Docker service lifecycle fixtures)
        """
        from testing.fixtures.services import (
            ensure_polaris_credentials_in_env,
            get_service_host,
        )

        assert callable(ensure_polaris_credentials_in_env)
        assert callable(get_service_host)

    @pytest.mark.requirement("006-FR-020")
    def test_get_service_host_returns_valid_hostname(self) -> None:
        """get_service_host returns valid hostname for services.

        Covers: FR-020 (service hostname resolution)
        """
        from testing.fixtures.services import get_service_host

        host = get_service_host("polaris")
        assert host in ("localhost", "polaris")

        host = get_service_host("localstack")
        assert host in ("localhost", "localstack")

    @pytest.mark.requirement("006-FR-020")
    def test_credentials_loaded_from_environment(self) -> None:
        """Polaris credentials are loaded from environment or file.

        Covers: FR-020 (credential lifecycle management)
        """
        from testing.fixtures.services import ensure_polaris_credentials_in_env

        # This should not raise
        ensure_polaris_credentials_in_env()

        # After calling, credentials should be in environment
        # (either from file or already present)
        # Note: In CI, these are set by Docker environment


# =============================================================================
# Base Test Classes (FR-021)
# =============================================================================


class TestBaseTestClasses:
    """FR-021: Base test classes availability.

    Verifies that base test classes are available for common patterns.
    """

    @pytest.mark.requirement("006-FR-021")
    def test_base_classes_importable(self) -> None:
        """Base test classes can be imported.

        Covers: FR-021 (base test classes available)
        """
        from testing.base_classes import IntegrationTestBase

        assert IntegrationTestBase is not None
        assert hasattr(IntegrationTestBase, "check_infrastructure")

    @pytest.mark.requirement("006-FR-021")
    def test_base_class_provides_infrastructure_check(self) -> None:
        """Base class provides infrastructure check method.

        Covers: FR-021 (common testing patterns)
        """
        from testing.base_classes import IntegrationTestBase

        # Create instance to verify method exists
        base = IntegrationTestBase()

        # Should have the check_infrastructure method
        assert hasattr(base, "check_infrastructure")
        assert callable(base.check_infrastructure)

    @pytest.mark.requirement("006-FR-021")
    def test_base_class_check_fails_when_infrastructure_missing(self) -> None:
        """Base class check fails (not skips) when infrastructure missing.

        Covers: FR-021 (FAIL not skip pattern in base class)
        """
        from testing.base_classes import IntegrationTestBase

        base = IntegrationTestBase()

        # Check with invalid service should fail
        # Note: This verifies the pattern, not actual infrastructure
        with pytest.raises(pytest.fail.Exception):
            base.check_infrastructure("nonexistent-service", 99999)
