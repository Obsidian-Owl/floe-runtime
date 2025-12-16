"""Unit tests for PostgreSQLProfileGenerator.

T020: [P] [US2] Unit tests for PostgreSQLProfileGenerator
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGeneratorConfig


class TestPostgreSQLProfileGenerator:
    """Test suite for PostgreSQL profile generation."""

    @pytest.fixture
    def generator(self) -> Any:
        """Create PostgreSQLProfileGenerator instance."""
        from floe_dbt.profiles.postgres import PostgreSQLProfileGenerator

        return PostgreSQLProfileGenerator()

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
        postgres_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that generate returns correct structure."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": postgres_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)

        assert config.target_name in result
        target = result[config.target_name]
        assert target["type"] == "postgres"
        assert "host" in target
        assert "port" in target
        assert "user" in target
        assert "password" in target
        assert "dbname" in target

    def test_generate_uses_default_port(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that default PostgreSQL port 5432 is used when not specified."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "postgres",
                "properties": {
                    "host": "localhost",
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["port"] == 5432

    def test_generate_uses_configured_port(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that configured port is used."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "postgres",
                "properties": {
                    "host": "localhost",
                    "port": 5433,
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["port"] == 5433

    def test_generate_uses_env_var_for_credentials(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        postgres_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that credentials use env_var() template syntax."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": postgres_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        # Password and user should use env_var template
        assert "env_var" in str(target["password"]) or "POSTGRES" in str(target["password"])
        assert "env_var" in str(target["user"]) or "POSTGRES" in str(target["user"])

    def test_generate_includes_schema(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that schema is included when specified."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "postgres",
                "properties": {
                    "host": "localhost",
                    "database": "analytics",
                    "schema": "dbt_prod",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["schema"] == "dbt_prod"

    def test_generate_threads_from_config(
        self,
        generator: Any,
        postgres_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that thread count from config is used."""
        config = ProfileGeneratorConfig(
            profile_name="floe",
            target_name="prod",
            threads=8,
        )
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": postgres_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["threads"] == 8

    def test_never_hardcodes_credentials(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that credentials are never hardcoded (FR-003)."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "postgres",
                "properties": {
                    "host": "localhost",
                    "database": "db",
                    "password": "secret123",
                    "user": "admin",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        assert target["password"] != "secret123"
        assert "env_var" in str(target["password"]) or "POSTGRES" in str(target["password"])

    def test_generate_uses_dbname_from_database(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that dbname is derived from database property."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
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
        assert result[config.target_name]["dbname"] == "my_analytics_db"
