"""Unit tests for SnowflakeProfileGenerator.

T016: [P] [US2] Unit tests for SnowflakeProfileGenerator
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGeneratorConfig


class TestSnowflakeProfileGenerator:
    """Test suite for Snowflake profile generation."""

    @pytest.fixture
    def generator(self) -> Any:
        """Create SnowflakeProfileGenerator instance."""
        from floe_dbt.profiles.snowflake import SnowflakeProfileGenerator

        return SnowflakeProfileGenerator()

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
        snowflake_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test that generate returns correct structure."""
        result = generator.generate(snowflake_compiled_artifacts, config)

        assert config.target_name in result
        target = result[config.target_name]
        assert target["type"] == "snowflake"
        assert "account" in target
        assert "user" in target
        assert "password" in target

    def test_generate_uses_env_var_for_credentials(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        snowflake_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test that credentials use env_var() template syntax."""
        result = generator.generate(snowflake_compiled_artifacts, config)
        target = result[config.target_name]

        # Password should use env_var template
        assert "env_var" in str(target["password"]) or "SNOWFLAKE_PASSWORD" in str(
            target["password"]
        )
        # User should use env_var template
        assert "env_var" in str(target["user"]) or "SNOWFLAKE_USER" in str(target["user"])

    def test_generate_includes_warehouse_config(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        snowflake_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test that warehouse configuration is included."""
        result = generator.generate(snowflake_compiled_artifacts, config)
        target = result[config.target_name]

        assert "warehouse" in target
        assert "database" in target
        assert "schema" in target

    def test_generate_includes_role(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        snowflake_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test that role is included when specified."""
        result = generator.generate(snowflake_compiled_artifacts, config)
        target = result[config.target_name]

        assert "role" in target

    def test_generate_uses_account_from_properties(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that account is taken from properties."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "snowflake",
                "properties": {
                    "account": "custom_account.us-west-2.aws",
                    "warehouse": "WH",
                    "database": "DB",
                    "schema": "SCHEMA",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["account"] == "custom_account.us-west-2.aws"

    def test_generate_threads_from_config(
        self,
        generator: Any,
        snowflake_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Test that thread count from config is used."""
        config = ProfileGeneratorConfig(
            profile_name="floe",
            target_name="prod",
            threads=16,
        )

        result = generator.generate(snowflake_compiled_artifacts, config)
        assert result[config.target_name]["threads"] == 16

    def test_never_hardcodes_credentials(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that credentials are never hardcoded (FR-003)."""
        # Even if password is in properties, it should use env_var reference
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "snowflake",
                "properties": {
                    "account": "acc",
                    "warehouse": "WH",
                    "database": "DB",
                    "schema": "S",
                    # These should NOT be used directly
                    "password": "secret123",
                    "user": "admin",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        # Should use env_var, not the actual values
        assert target["password"] != "secret123"
        assert "env_var" in str(target["password"]) or "SNOWFLAKE" in str(target["password"])
