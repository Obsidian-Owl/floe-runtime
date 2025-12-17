"""Unit tests for DatabricksProfileGenerator.

T019: [P] [US2] Unit tests for DatabricksProfileGenerator

This module uses the BaseCredentialProfileGeneratorTests pattern for
standardized adapter testing with credential validation.
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGenerator, ProfileGeneratorConfig
from testing.base_classes.adapter_test_base import BaseCredentialProfileGeneratorTests


class TestDatabricksProfileGenerator(BaseCredentialProfileGeneratorTests):
    """Test suite for Databricks profile generation.

    Inherits from BaseCredentialProfileGeneratorTests to get standardized tests
    plus credential validation tests.
    """

    @pytest.fixture
    def generator(self) -> ProfileGenerator:
        """Create DatabricksProfileGenerator instance."""
        from floe_dbt.profiles.databricks import DatabricksProfileGenerator

        return DatabricksProfileGenerator()

    @property
    def target_type(self) -> str:
        """Databricks adapter type."""
        return "databricks"

    @property
    def required_fields(self) -> set[str]:
        """Required fields in Databricks profile."""
        return {"type", "host", "http_path", "token", "threads"}

    @property
    def credential_fields(self) -> set[str]:
        """Credential fields that must use env_var()."""
        return {"token"}

    def get_minimal_artifacts(self) -> dict[str, Any]:
        """Minimal CompiledArtifacts for Databricks."""
        return {
            "version": "1.0.0",
            "compute": {
                "target": "databricks",
                "properties": {
                    "host": "adb-1234567890.12.azuredatabricks.net",
                    "http_path": "/sql/1.0/warehouses/abc123",
                    "catalog": "main",
                    "schema": "default",
                },
            },
            "transforms": [],
        }

    # =========================================================================
    # Databricks-specific tests
    # =========================================================================

    def test_generate_includes_unity_catalog(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that Unity Catalog configuration is included."""
        result = generator.generate(self.get_minimal_artifacts(), config)
        assert config.target_name is not None
        target = result[config.target_name]

        assert "catalog" in target
        assert "schema" in target

    def test_generate_uses_host_from_properties(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that host is taken from properties."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
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
        assert config.target_name is not None
        assert result[config.target_name]["host"] == "custom-workspace.cloud.databricks.com"

    def test_generate_supports_sql_warehouse_path(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that SQL warehouse HTTP path is correctly set."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
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
        assert config.target_name is not None
        assert result[config.target_name]["http_path"] == "/sql/protocolv1/o/123456789/0123-456-abc"
