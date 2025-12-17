"""Shared testing infrastructure for floe-runtime.

This package provides reusable test fixtures, base classes, and utilities
for testing across all floe-runtime packages.

Modules:
    fixtures: Shared pytest fixtures for CompiledArtifacts, adapters, containers
    base_classes: Abstract test base classes for adapter testing (dbt pattern)
    markers: Custom pytest marker definitions

Usage:
    In your conftest.py:
        from testing.fixtures.artifacts import make_compiled_artifacts
        from testing.base_classes.adapter_test_base import BaseProfileGeneratorTests

Example:
    class TestMyAdapter(BaseProfileGeneratorTests):
        @pytest.fixture
        def generator(self):
            return MyAdapterGenerator()

        @property
        def target_type(self) -> str:
            return "my_adapter"
"""

from __future__ import annotations
