"""Unit tests for RedshiftProfileGenerator.

T018: [P] [US2] Unit tests for RedshiftProfileGenerator
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGeneratorConfig


class TestRedshiftProfileGenerator:
    """Test suite for Redshift profile generation."""

    @pytest.fixture
    def generator(self) -> Any:
        """Create RedshiftProfileGenerator instance."""
        from floe_dbt.profiles.redshift import RedshiftProfileGenerator

        return RedshiftProfileGenerator()

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
        redshift_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that generate returns correct structure."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": redshift_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)

        assert config.target_name in result
        target = result[config.target_name]
        assert target["type"] == "redshift"
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
        """Test that default Redshift port 5439 is used when not specified."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "redshift",
                "properties": {
                    "host": "cluster.abc.us-east-1.redshift.amazonaws.com",
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["port"] == 5439

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
                "target": "redshift",
                "properties": {
                    "host": "cluster.abc.us-east-1.redshift.amazonaws.com",
                    "port": 5440,
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["port"] == 5440

    def test_generate_uses_env_var_for_credentials(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        redshift_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that credentials use env_var() template syntax."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": redshift_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        # Password and user should use env_var template
        assert "env_var" in str(target["password"]) or "REDSHIFT" in str(target["password"])
        assert "env_var" in str(target["user"]) or "REDSHIFT" in str(target["user"])

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
                "target": "redshift",
                "properties": {
                    "host": "cluster.abc.redshift.amazonaws.com",
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
        redshift_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that thread count from config is used."""
        config = ProfileGeneratorConfig(
            profile_name="floe",
            target_name="prod",
            threads=12,
        )
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": redshift_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["threads"] == 12

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
                "target": "redshift",
                "properties": {
                    "host": "cluster.abc.redshift.amazonaws.com",
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
        assert "env_var" in str(target["password"]) or "REDSHIFT" in str(target["password"])
