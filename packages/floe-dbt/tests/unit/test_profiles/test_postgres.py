"""Unit tests for PostgreSQLProfileGenerator.

T020: [P] [US2] Unit tests for PostgreSQLProfileGenerator

This module uses the BaseCredentialProfileGeneratorTests pattern for
standardized adapter testing with credential validation.
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGenerator, ProfileGeneratorConfig
from testing.base_classes.adapter_test_base import BaseCredentialProfileGeneratorTests


class TestPostgreSQLProfileGenerator(BaseCredentialProfileGeneratorTests):
    """Test suite for PostgreSQL profile generation.

    Inherits from BaseCredentialProfileGeneratorTests to get standardized tests
    plus credential validation tests.
    """

    @pytest.fixture
    def generator(self) -> ProfileGenerator:
        """Create PostgreSQLProfileGenerator instance."""
        from floe_dbt.profiles.postgres import PostgreSQLProfileGenerator

        return PostgreSQLProfileGenerator()

    @property
    def target_type(self) -> str:
        """PostgreSQL adapter type."""
        return "postgres"

    @property
    def required_fields(self) -> set[str]:
        """Required fields in PostgreSQL profile."""
        return {"type", "host", "port", "user", "password", "dbname", "threads"}

    @property
    def credential_fields(self) -> set[str]:
        """Credential fields that must use env_var()."""
        return {"user", "password"}

    def get_minimal_artifacts(self) -> dict[str, Any]:
        """Minimal CompiledArtifacts for PostgreSQL."""
        return {
            "version": "1.0.0",
            "compute": {
                "target": "postgres",
                "properties": {
                    "host": "localhost",
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

    # =========================================================================
    # PostgreSQL-specific tests
    # =========================================================================

    def test_generate_uses_default_port(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that default PostgreSQL port 5432 is used when not specified."""
        result = generator.generate(self.get_minimal_artifacts(), config)
        assert config.target_name is not None
        assert result[config.target_name]["port"] == 5432

    def test_generate_uses_configured_port(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that configured port is used."""
        artifacts = self.get_minimal_artifacts()
        artifacts["compute"]["properties"]["port"] = 5433

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["port"] == 5433

    def test_generate_includes_schema(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that schema is included when specified."""
        artifacts = self.get_minimal_artifacts()
        artifacts["compute"]["properties"]["schema"] = "dbt_prod"

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["schema"] == "dbt_prod"

    def test_generate_uses_dbname_from_database(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that dbname is derived from database property."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "compute": {
                "target": "postgres",
                "properties": {
                    "host": "localhost",
                    "database": "my_analytics_db",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["dbname"] == "my_analytics_db"
