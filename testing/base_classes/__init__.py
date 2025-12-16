"""Abstract test base classes for floe-runtime.

This module provides base test classes that define standard test suites
for various plugin types. Concrete test classes inherit from these bases
and implement abstract methods to specify plugin-specific behavior.

Pattern: Following dbt's adapter testing approach where base classes define
the contract and concrete classes inherit the test suite.

Exports:
    BaseProfileGeneratorTests: Base class for ProfileGenerator adapter tests
"""

from __future__ import annotations

from testing.base_classes.adapter_test_base import BaseProfileGeneratorTests

__all__ = [
    "BaseProfileGeneratorTests",
]
