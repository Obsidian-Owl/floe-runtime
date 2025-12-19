"""Abstract test base classes for floe-runtime.

This module provides base test classes that define standard test suites
for various plugin types. Concrete test classes inherit from these bases
and implement abstract methods to specify plugin-specific behavior.

Pattern: Following dbt's adapter testing approach where base classes define
the contract and concrete classes inherit the test suite.

Exports:
    BaseProfileGeneratorTests: Base class for ProfileGenerator adapter tests
    BaseCredentialProfileGeneratorTests: Extended base for credential-requiring adapters
    IntegrationTestBase: Base class for Docker service integration tests
    PolarisIntegrationTestBase: Base class for Polaris catalog tests
    CubeIntegrationTestBase: Base class for Cube semantic layer tests
    PostgresIntegrationTestBase: Base class for PostgreSQL tests
    DbtIntegrationTestBase: Base class for dbt integration tests
"""

from __future__ import annotations

from testing.base_classes.adapter_test_base import (
    BaseCredentialProfileGeneratorTests,
    BaseProfileGeneratorTests,
)
from testing.base_classes.integration_test_base import (
    CubeIntegrationTestBase,
    DbtIntegrationTestBase,
    IntegrationTestBase,
    PolarisIntegrationTestBase,
    PostgresIntegrationTestBase,
)

__all__ = [
    # Profile generator base classes
    "BaseProfileGeneratorTests",
    "BaseCredentialProfileGeneratorTests",
    # Integration test base classes
    "IntegrationTestBase",
    "PolarisIntegrationTestBase",
    "CubeIntegrationTestBase",
    "PostgresIntegrationTestBase",
    "DbtIntegrationTestBase",
]
