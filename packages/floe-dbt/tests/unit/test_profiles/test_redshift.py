"""Unit tests for RedshiftProfileGenerator.

T018: [P] [US2] Unit tests for RedshiftProfileGenerator

This module uses the BaseCredentialProfileGeneratorTests pattern for
standardized adapter testing with credential validation.
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGenerator, ProfileGeneratorConfig
from testing.base_classes.adapter_test_base import BaseCredentialProfileGeneratorTests


class TestRedshiftProfileGenerator(BaseCredentialProfileGeneratorTests):
    """Test suite for Redshift profile generation.

    Inherits from BaseCredentialProfileGeneratorTests to get standardized tests
    plus credential validation tests.
    """

    @pytest.fixture
    def generator(self) -> ProfileGenerator:
        """Create RedshiftProfileGenerator instance."""
        from floe_dbt.profiles.redshift import RedshiftProfileGenerator

        return RedshiftProfileGenerator()

    @property
    def target_type(self) -> str:
        """Redshift adapter type."""
        return "redshift"

    @property
    def required_fields(self) -> set[str]:
        """Required fields in Redshift profile."""
        return {"type", "host", "port", "user", "password", "dbname", "threads"}

    @property
    def credential_fields(self) -> set[str]:
        """Credential fields that must use env_var()."""
        return {"user", "password"}

    def get_minimal_artifacts(self) -> dict[str, Any]:
        """Minimal CompiledArtifacts for Redshift."""
        return {
            "version": "1.0.0",
            "compute": {
                "target": "redshift",
                "properties": {
                    "host": "cluster.abc.us-east-1.redshift.amazonaws.com",
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

    # =========================================================================
    # Redshift-specific tests
    # =========================================================================

    def test_generate_uses_default_port(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that default Redshift port 5439 is used when not specified."""
        result = generator.generate(self.get_minimal_artifacts(), config)
        assert config.target_name is not None
        assert result[config.target_name]["port"] == 5439

    def test_generate_uses_configured_port(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that configured port is used."""
        artifacts = self.get_minimal_artifacts()
        artifacts["compute"]["properties"]["port"] = 5440

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["port"] == 5440

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
