"""Unit tests for BigQueryProfileGenerator.

T017: [P] [US2] Unit tests for BigQueryProfileGenerator
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGeneratorConfig


class TestBigQueryProfileGenerator:
    """Test suite for BigQuery profile generation."""

    @pytest.fixture
    def generator(self) -> Any:
        """Create BigQueryProfileGenerator instance."""
        from floe_dbt.profiles.bigquery import BigQueryProfileGenerator

        return BigQueryProfileGenerator()

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
        bigquery_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that generate returns correct structure."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": bigquery_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)

        assert config.target_name in result
        target = result[config.target_name]
        assert target["type"] == "bigquery"
        assert "project" in target
        assert "method" in target

    def test_generate_oauth_method(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test OAuth authentication method configuration."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
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
        target = result[config.target_name]

        assert target["method"] == "oauth"
        # OAuth shouldn't have keyfile
        assert "keyfile" not in target or target.get("keyfile") is None

    def test_generate_service_account_method(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test service account authentication method configuration."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
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
        target = result[config.target_name]

        assert target["method"] == "service-account"
        # Service account should reference keyfile via env_var
        assert "keyfile" in target
        assert "GOOGLE_APPLICATION_CREDENTIALS" in str(target["keyfile"]) or "env_var" in str(
            target["keyfile"]
        )

    def test_generate_includes_location(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that location is included when specified."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
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
        assert result[config.target_name]["location"] == "EU"

    def test_generate_includes_dataset(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        bigquery_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that dataset is included."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": bigquery_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert "dataset" in result[config.target_name]

    def test_generate_threads_from_config(
        self,
        generator: Any,
        bigquery_compute_config: dict[str, Any],
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
            "compute": bigquery_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["threads"] == 8

    def test_generate_uses_project_from_properties(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that project ID is taken from properties."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
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
        assert result[config.target_name]["project"] == "custom-gcp-project-123"
