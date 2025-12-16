"""Unit tests for DuckDBProfileGenerator.

T015: [P] [US2] Unit tests for DuckDBProfileGenerator
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGeneratorConfig

# Import will work once generator is implemented
# from floe_dbt.profiles.duckdb import DuckDBProfileGenerator


class TestDuckDBProfileGenerator:
    """Test suite for DuckDB profile generation."""

    @pytest.fixture
    def generator(self) -> Any:
        """Create DuckDBProfileGenerator instance."""
        from floe_dbt.profiles.duckdb import DuckDBProfileGenerator

        return DuckDBProfileGenerator()

    @pytest.fixture
    def config(self) -> ProfileGeneratorConfig:
        """Standard profile generator config."""
        return ProfileGeneratorConfig(
            profile_name="floe",
            target_name="dev",
            threads=4,
        )

    def test_generate_returns_valid_structure(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        minimal_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test that generate returns correct structure."""
        result = generator.generate(minimal_compiled_artifacts, config)

        assert config.target_name in result
        target = result[config.target_name]
        assert target["type"] == "duckdb"
        assert "path" in target
        assert "threads" in target

    def test_generate_uses_default_memory_path(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that default path is :memory: when not specified."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "duckdb",
                "properties": {},
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["path"] == ":memory:"

    def test_generate_uses_configured_path(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that configured path is used."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "duckdb",
                "properties": {"path": "/data/warehouse.db"},
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["path"] == "/data/warehouse.db"

    def test_generate_uses_config_threads(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        minimal_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test that thread count from config is used."""
        custom_config = ProfileGeneratorConfig(
            profile_name="floe",
            target_name="dev",
            threads=8,
        )

        result = generator.generate(minimal_compiled_artifacts, custom_config)
        assert result[custom_config.target_name]["threads"] == 8

    def test_generate_includes_extensions_when_specified(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that extensions are included when specified."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "duckdb",
                "properties": {
                    "extensions": ["httpfs", "parquet"],
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name].get("extensions") == ["httpfs", "parquet"]

    def test_generate_custom_target_name(
        self,
        generator: Any,
        minimal_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test generation with custom target name."""
        config = ProfileGeneratorConfig(
            profile_name="floe",
            target_name="production",
            threads=4,
        )

        result = generator.generate(minimal_compiled_artifacts, config)
        assert "production" in result
        assert "dev" not in result
