"""Unit tests for DuckDBProfileGenerator.

T015: [P] [US2] Unit tests for DuckDBProfileGenerator

This module uses the BaseProfileGeneratorTests pattern for standardized
adapter testing. DuckDB-specific tests are added as additional methods.
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGenerator, ProfileGeneratorConfig
from testing.base_classes.adapter_test_base import BaseProfileGeneratorTests


class TestDuckDBProfileGenerator(BaseProfileGeneratorTests):
    """Test suite for DuckDB profile generation.

    Inherits from BaseProfileGeneratorTests to get standardized tests:
    - test_implements_protocol
    - test_generate_returns_dict
    - test_generate_includes_target_name
    - test_generate_has_correct_type
    - test_generate_has_required_fields
    - test_generate_uses_config_threads
    - test_generate_custom_target_name
    - test_generate_with_different_environments
    """

    @pytest.fixture
    def generator(self) -> ProfileGenerator:
        """Create DuckDBProfileGenerator instance."""
        from floe_dbt.profiles.duckdb import DuckDBProfileGenerator

        return DuckDBProfileGenerator()

    @property
    def target_type(self) -> str:
        """DuckDB adapter type."""
        return "duckdb"

    @property
    def required_fields(self) -> set[str]:
        """Required fields in DuckDB profile."""
        return {"type", "path", "threads"}

    def get_minimal_artifacts(self) -> dict[str, Any]:
        """Minimal CompiledArtifacts for DuckDB."""
        return {
            "version": "1.0.0",
            "compute": {
                "target": "duckdb",
                "properties": {"path": ":memory:"},
            },
            "transforms": [],
        }

    # =========================================================================
    # DuckDB-specific tests (not inherited from base class)
    # =========================================================================

    def test_generate_uses_default_memory_path(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that default path is :memory: when not specified."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "compute": {
                "target": "duckdb",
                "properties": {},
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["path"] == ":memory:"

    def test_generate_uses_configured_path(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that configured path is used."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "compute": {
                "target": "duckdb",
                "properties": {"path": "/data/warehouse.db"},
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["path"] == "/data/warehouse.db"

    def test_generate_includes_extensions_when_specified(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that extensions are included when specified."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "compute": {
                "target": "duckdb",
                "properties": {
                    "path": ":memory:",
                    "extensions": ["httpfs", "parquet"],
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name].get("extensions") == ["httpfs", "parquet"]
