"""Shared test fixtures for floe-runtime packages.

This module provides factory functions and fixtures for creating test data
that can be shared across all packages.

Exports:
    CompiledArtifacts fixtures:
        make_compiled_artifacts: Factory for creating CompiledArtifacts dicts
        make_minimal_artifacts: Factory for minimal CompiledArtifacts
        COMPUTE_CONFIGS: Pre-defined compute configurations for all 7 targets
        base_metadata: Factory for creating artifact metadata

    Docker service fixtures:
        DockerServices: Manager class for Docker Compose services
        docker_compose_file: Get path to docker-compose.yml
        get_service_host: Get hostname for a service (Docker or localhost)
        is_service_available: Check if a service is available
        poll_until: Poll until a check function returns True on fetched data
        wait_for_condition: Wait for a condition to become True using polling
        wait_for_services: Wait for multiple services to be healthy

    Two-Tier Configuration fixtures:
        is_platform_config_loaded: Check if platform.yaml is being used
        get_platform_config_source: Get path to loaded platform.yaml
        platform_config_validation: pytest fixture for validation
        require_platform_config: pytest fixture that fails if not loaded

    Observability fixtures:
        JaegerClient: Client for querying Jaeger trace data
        MarquezClient: Client for querying Marquez lineage data

Usage:
    ```python
    from testing.fixtures import make_compiled_artifacts, DockerServices

    # Create test artifacts
    artifacts = make_compiled_artifacts("duckdb")

    # Use Docker services in tests
    services = DockerServices(compose_file, profile="storage")

    # Validate Two-Tier Configuration
    from testing.fixtures import is_platform_config_loaded
    assert is_platform_config_loaded(), "Platform config not loaded!"

    # Use observability clients
    from testing.fixtures import JaegerClient, MarquezClient
    jaeger = JaegerClient()
    marquez = MarquezClient()
    ```
"""

from __future__ import annotations

from testing.fixtures.artifacts import (
    COMPUTE_CONFIGS,
    base_metadata,
    make_compiled_artifacts,
    make_minimal_artifacts,
)
from testing.fixtures.observability import (
    JaegerClient,
    MarquezClient,
)
from testing.fixtures.services import (
    DockerServices,
    docker_compose_file,
    get_platform_config_source,
    get_service_host,
    is_platform_config_loaded,
    is_service_available,
    poll_until,
    wait_for_condition,
    wait_for_services,
)

__all__ = [
    # Artifact fixtures
    "COMPUTE_CONFIGS",
    "base_metadata",
    "make_compiled_artifacts",
    "make_minimal_artifacts",
    # Docker service fixtures
    "DockerServices",
    "docker_compose_file",
    "get_service_host",
    "is_service_available",
    "poll_until",
    "wait_for_condition",
    "wait_for_services",
    # Two-Tier Configuration validation
    "get_platform_config_source",
    "is_platform_config_loaded",
    # Observability fixtures
    "JaegerClient",
    "MarquezClient",
]
