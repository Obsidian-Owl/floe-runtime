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
        wait_for_services: Wait for multiple services to be healthy

Usage:
    ```python
    from testing.fixtures import make_compiled_artifacts, DockerServices

    # Create test artifacts
    artifacts = make_compiled_artifacts("duckdb")

    # Use Docker services in tests
    services = DockerServices(compose_file, profile="storage")
    ```
"""

from __future__ import annotations

from testing.fixtures.artifacts import (
    COMPUTE_CONFIGS,
    base_metadata,
    make_compiled_artifacts,
    make_minimal_artifacts,
)
from testing.fixtures.services import (
    DockerServices,
    docker_compose_file,
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
    "wait_for_services",
]
