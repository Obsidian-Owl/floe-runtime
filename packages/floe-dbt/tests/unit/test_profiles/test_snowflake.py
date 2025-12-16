"""Unit tests for SnowflakeProfileGenerator.

T016: [P] [US2] Unit tests for SnowflakeProfileGenerator

This module uses the BaseCredentialProfileGeneratorTests pattern for
standardized adapter testing with credential validation.
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGenerator, ProfileGeneratorConfig
from testing.base_classes.adapter_test_base import BaseCredentialProfileGeneratorTests


class TestSnowflakeProfileGenerator(BaseCredentialProfileGeneratorTests):
    """Test suite for Snowflake profile generation.

    Inherits from BaseCredentialProfileGeneratorTests to get standardized tests
    plus credential validation tests.
    """

    @pytest.fixture
    def generator(self) -> ProfileGenerator:
        """Create SnowflakeProfileGenerator instance."""
        from floe_dbt.profiles.snowflake import SnowflakeProfileGenerator

        return SnowflakeProfileGenerator()

    @property
    def target_type(self) -> str:
        """Snowflake adapter type."""
        return "snowflake"

    @property
    def required_fields(self) -> set[str]:
        """Required fields in Snowflake profile."""
        return {"type", "account", "user", "password", "threads"}

    @property
    def credential_fields(self) -> set[str]:
        """Credential fields that must use env_var()."""
        return {"user", "password"}

    def get_minimal_artifacts(self) -> dict[str, Any]:
        """Minimal CompiledArtifacts for Snowflake."""
        return {
            "version": "1.0.0",
            "compute": {
                "target": "snowflake",
                "properties": {
                    "account": "xy12345.us-east-1",
                    "warehouse": "COMPUTE_WH",
                    "database": "ANALYTICS",
                    "schema": "PUBLIC",
                },
            },
            "transforms": [],
        }

    # =========================================================================
    # Snowflake-specific tests
    # =========================================================================

    def test_generate_includes_warehouse_config(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that warehouse configuration is included."""
        result = generator.generate(self.get_minimal_artifacts(), config)
        assert config.target_name is not None
        target = result[config.target_name]

        assert "warehouse" in target
        assert "database" in target
        assert "schema" in target

    def test_generate_includes_role(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that role is included when specified."""
        artifacts = self.get_minimal_artifacts()
        artifacts["compute"]["properties"]["role"] = "TRANSFORMER"

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["role"] == "TRANSFORMER"

    def test_generate_uses_account_from_properties(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that account is taken from properties."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
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
        assert config.target_name is not None
        assert result[config.target_name]["account"] == "custom_account.us-west-2.aws"
