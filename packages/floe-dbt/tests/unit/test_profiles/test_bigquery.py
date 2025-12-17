"""Unit tests for BigQueryProfileGenerator.

T017: [P] [US2] Unit tests for BigQueryProfileGenerator

This module uses the BaseProfileGeneratorTests pattern for standardized
adapter testing. BigQuery-specific tests are added for auth methods.
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGenerator, ProfileGeneratorConfig
from testing.base_classes.adapter_test_base import BaseProfileGeneratorTests


class TestBigQueryProfileGenerator(BaseProfileGeneratorTests):
    """Test suite for BigQuery profile generation.

    Inherits from BaseProfileGeneratorTests to get standardized tests.
    BigQuery-specific tests cover OAuth vs service account auth.
    """

    @pytest.fixture
    def generator(self) -> ProfileGenerator:
        """Create BigQueryProfileGenerator instance."""
        from floe_dbt.profiles.bigquery import BigQueryProfileGenerator

        return BigQueryProfileGenerator()

    @property
    def target_type(self) -> str:
        """BigQuery adapter type."""
        return "bigquery"

    @property
    def required_fields(self) -> set[str]:
        """Required fields in BigQuery profile."""
        return {"type", "project", "method", "threads"}

    def get_minimal_artifacts(self) -> dict[str, Any]:
        """Minimal CompiledArtifacts for BigQuery."""
        return {
            "version": "1.0.0",
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "my-gcp-project",
                    "dataset": "analytics",
                    "method": "oauth",
                },
            },
            "transforms": [],
        }

    # =========================================================================
    # BigQuery-specific tests
    # =========================================================================

    def test_generate_oauth_method(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test OAuth authentication method configuration."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "my-project",
                    "dataset": "analytics",
                    "method": "oauth",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        target = result[config.target_name]

        assert target["method"] == "oauth"
        # OAuth shouldn't have keyfile
        assert "keyfile" not in target or target.get("keyfile") is None

    def test_generate_service_account_method(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test service account authentication method configuration."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "my-project",
                    "dataset": "analytics",
                    "method": "service-account",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        target = result[config.target_name]

        assert target["method"] == "service-account"
        # Service account should reference keyfile via env_var
        assert "keyfile" in target
        assert "GOOGLE_APPLICATION_CREDENTIALS" in str(target["keyfile"]) or "env_var" in str(
            target["keyfile"]
        )

    def test_generate_includes_location(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that location is included when specified."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "my-project",
                    "dataset": "analytics",
                    "location": "EU",
                    "method": "oauth",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["location"] == "EU"

    def test_generate_includes_dataset(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that dataset is included."""
        result = generator.generate(self.get_minimal_artifacts(), config)
        assert config.target_name is not None
        assert "dataset" in result[config.target_name]

    def test_generate_uses_project_from_properties(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that project ID is taken from properties."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "custom-gcp-project-123",
                    "dataset": "data",
                    "method": "oauth",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["project"] == "custom-gcp-project-123"
