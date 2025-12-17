"""Custom pytest marker definitions for floe-runtime.

This module defines custom pytest markers for categorizing tests.

Markers:
    slow: Tests that take > 1 second
    integration: Tests requiring external services
    contract: Cross-package contract validation tests
    e2e: End-to-end tests
    adapter(name): Tests for a specific adapter
    requires_dbt: Tests requiring dbt-core installed
    requires_container: Tests requiring Docker

Usage:
    @pytest.mark.slow
    def test_expensive_operation():
        ...

    @pytest.mark.adapter("snowflake")
    def test_snowflake_profile():
        ...

Run specific markers:
    pytest -m "not slow"           # Skip slow tests
    pytest -m integration          # Only integration tests
    pytest -m "adapter and duckdb" # Only DuckDB adapter tests
"""

from __future__ import annotations
