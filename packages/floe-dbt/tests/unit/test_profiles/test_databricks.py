"""Unit tests for DatabricksProfileGenerator.

T019: [P] [US2] Unit tests for DatabricksProfileGenerator
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGeneratorConfig


class TestDatabricksProfileGenerator:
    """Test suite for Databricks profile generation."""

    @pytest.fixture
    def generator(self) -> Any:
        """Create DatabricksProfileGenerator instance."""
        from floe_dbt.profiles.databricks import DatabricksProfileGenerator

        return DatabricksProfileGenerator()

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
        databricks_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that generate returns correct structure."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": databricks_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)

        assert config.target_name in result
        target = result[config.target_name]
        assert target["type"] == "databricks"
        assert "host" in target
        assert "http_path" in target
        assert "token" in target

    def test_generate_includes_unity_catalog(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        databricks_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that Unity Catalog configuration is included."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": databricks_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        assert "catalog" in target
        assert "schema" in target

    def test_generate_uses_env_var_for_token(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        databricks_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that token uses env_var() template syntax."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": databricks_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        assert "env_var" in str(target["token"]) or "DATABRICKS" in str(target["token"])

    def test_generate_uses_host_from_properties(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that host is taken from properties."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "databricks",
                "properties": {
                    "host": "custom-workspace.cloud.databricks.com",
                    "http_path": "/sql/1.0/warehouses/abc",
                    "catalog": "main",
                    "schema": "default",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["host"] == "custom-workspace.cloud.databricks.com"

    def test_generate_threads_from_config(
        self,
        generator: Any,
        databricks_compute_config: dict[str, Any],
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
            "compute": databricks_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["threads"] == 8

    def test_never_hardcodes_token(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that token is never hardcoded (FR-003)."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "databricks",
                "properties": {
                    "host": "workspace.databricks.com",
                    "http_path": "/sql/1.0/warehouses/abc",
                    "catalog": "main",
                    "schema": "default",
                    "token": "dapi-secret-token-12345",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        assert target["token"] != "dapi-secret-token-12345"
        assert "env_var" in str(target["token"]) or "DATABRICKS" in str(target["token"])

    def test_generate_supports_sql_warehouse_path(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that SQL warehouse HTTP path is correctly set."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "databricks",
                "properties": {
                    "host": "workspace.databricks.com",
                    "http_path": "/sql/protocolv1/o/123456789/0123-456-abc",
                    "catalog": "main",
                    "schema": "default",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["http_path"] == "/sql/protocolv1/o/123456789/0123-456-abc"
