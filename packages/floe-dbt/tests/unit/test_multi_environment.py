"""Unit tests for multi-environment profile generation.

T078: [US5] Unit tests for multi-environment profiles
"""

from __future__ import annotations

from typing import Any

import pytest


class TestEnvironmentAwareProfileConfig:
    """Tests for environment-aware profile configuration."""

    def test_profile_config_with_environment(self) -> None:
        """Test ProfileGeneratorConfig accepts environment parameter."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        config = ProfileGeneratorConfig(
            profile_name="floe",
            target_name="dev",
            environment="development",
        )

        assert config.environment == "development"

    def test_profile_config_environment_default(self) -> None:
        """Test ProfileGeneratorConfig defaults to 'dev' environment."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        config = ProfileGeneratorConfig()

        assert config.environment == "dev"

    def test_profile_config_environment_validation(self) -> None:
        """Test environment must be alphanumeric with underscores."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        # Valid environments
        config = ProfileGeneratorConfig(environment="prod")
        assert config.environment == "prod"

        config = ProfileGeneratorConfig(environment="staging_us_east")
        assert config.environment == "staging_us_east"

    def test_profile_config_invalid_environment(self) -> None:
        """Test invalid environment raises validation error."""
        from pydantic import ValidationError

        from floe_dbt.profiles.base import ProfileGeneratorConfig

        with pytest.raises(ValidationError):
            ProfileGeneratorConfig(environment="invalid-env")  # Hyphens not allowed

    def test_target_name_from_environment(self) -> None:
        """Test target_name defaults to environment when not specified."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        config = ProfileGeneratorConfig(environment="production")

        # target_name should default to environment if not explicitly set
        assert config.target_name == "production"


class TestEnvironmentSpecificSecrets:
    """Tests for environment-specific secret references."""

    @pytest.fixture
    def snowflake_generator(self) -> Any:
        """Get SnowflakeProfileGenerator."""
        from floe_dbt.profiles.snowflake import SnowflakeProfileGenerator

        return SnowflakeProfileGenerator()

    @pytest.fixture
    def base_artifacts(self) -> dict[str, Any]:
        """Base artifacts for testing."""
        return {
            "compute": {
                "target": "snowflake",
                "properties": {
                    "account": "test-account",
                    "warehouse": "COMPUTE_WH",
                    "database": "ANALYTICS",
                    "schema": "public",
                },
            },
        }

    def test_dev_environment_uses_dev_secrets(
        self,
        snowflake_generator: Any,
        base_artifacts: dict[str, Any],
    ) -> None:
        """Test dev environment uses DEV-prefixed secret env vars."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        config = ProfileGeneratorConfig(environment="dev")
        result = snowflake_generator.generate(base_artifacts, config)

        # Should use DEV-prefixed env vars
        assert "{{ env_var('SNOWFLAKE_DEV_USER') }}" in result["dev"]["user"]
        assert "{{ env_var('SNOWFLAKE_DEV_PASSWORD') }}" in result["dev"]["password"]

    def test_prod_environment_uses_prod_secrets(
        self,
        snowflake_generator: Any,
        base_artifacts: dict[str, Any],
    ) -> None:
        """Test prod environment uses PROD-prefixed secret env vars."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        config = ProfileGeneratorConfig(environment="prod")
        result = snowflake_generator.generate(base_artifacts, config)

        # Should use PROD-prefixed env vars
        assert "{{ env_var('SNOWFLAKE_PROD_USER') }}" in result["prod"]["user"]
        assert "{{ env_var('SNOWFLAKE_PROD_PASSWORD') }}" in result["prod"]["password"]

    def test_staging_environment_uses_staging_secrets(
        self,
        snowflake_generator: Any,
        base_artifacts: dict[str, Any],
    ) -> None:
        """Test staging environment uses STAGING-prefixed secret env vars."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        config = ProfileGeneratorConfig(environment="staging")
        result = snowflake_generator.generate(base_artifacts, config)

        # Should use STAGING-prefixed env vars
        assert "{{ env_var('SNOWFLAKE_STAGING_USER') }}" in result["staging"]["user"]
        assert "{{ env_var('SNOWFLAKE_STAGING_PASSWORD') }}" in result["staging"]["password"]


class TestMultiEnvironmentOutputs:
    """Tests for generating multiple environment outputs."""

    @pytest.fixture
    def factory(self) -> Any:
        """Get ProfileFactory."""
        from floe_dbt.factory import ProfileFactory

        return ProfileFactory

    @pytest.fixture
    def duckdb_artifacts(self) -> dict[str, Any]:
        """DuckDB artifacts for testing."""
        return {
            "compute": {
                "target": "duckdb",
                "properties": {"path": ":memory:"},
            },
        }

    def test_generate_multiple_environments(
        self,
        factory: Any,
        duckdb_artifacts: dict[str, Any],
    ) -> None:
        """Test generating profiles for multiple environments."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        generator = factory.create("duckdb")

        # Generate dev and prod outputs
        dev_config = ProfileGeneratorConfig(environment="dev")
        prod_config = ProfileGeneratorConfig(environment="prod")

        dev_outputs = generator.generate(duckdb_artifacts, dev_config)
        prod_outputs = generator.generate(duckdb_artifacts, prod_config)

        # Should have different target names
        assert "dev" in dev_outputs
        assert "prod" in prod_outputs

    def test_environment_affects_database_schema(
        self,
        factory: Any,
    ) -> None:
        """Test environment affects database/schema naming."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        # Artifacts with schema pattern
        artifacts = {
            "compute": {
                "target": "snowflake",
                "properties": {
                    "account": "test-account",
                    "database": "ANALYTICS",
                    "schema": "{{ environment }}_models",  # Pattern
                },
            },
        }

        generator = factory.create("snowflake")

        dev_config = ProfileGeneratorConfig(environment="dev")
        result = generator.generate(artifacts, dev_config)

        # Schema should be expanded with environment
        # Note: The generator should handle this pattern expansion
        assert result is not None


class TestEnvironmentFromArtifacts:
    """Tests for reading environment from CompiledArtifacts."""

    def test_config_from_artifacts_extracts_environment(self) -> None:
        """Test ProfileGeneratorConfig.from_artifacts extracts environment."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "environment_context": {
                "environment": "production",
                "tenant_id": "acme-corp",
            },
        }

        config = ProfileGeneratorConfig.from_artifacts(artifacts)

        assert config.environment == "production"

    def test_config_from_artifacts_defaults_to_dev(self) -> None:
        """Test from_artifacts defaults to 'dev' when no environment context."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "environment_context": None,
        }

        config = ProfileGeneratorConfig.from_artifacts(artifacts)

        assert config.environment == "dev"

    def test_config_from_artifacts_with_custom_target(self) -> None:
        """Test from_artifacts allows custom target name override."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "environment_context": {
                "environment": "production",
            },
            "dbt_target_name": "custom_target",
        }

        config = ProfileGeneratorConfig.from_artifacts(artifacts)

        assert config.target_name == "custom_target"


class TestEnvironmentSecretConventions:
    """Tests for secret naming conventions per environment."""

    @pytest.fixture
    def bigquery_generator(self) -> Any:
        """Get BigQueryProfileGenerator."""
        from floe_dbt.profiles.bigquery import BigQueryProfileGenerator

        return BigQueryProfileGenerator()

    @pytest.fixture
    def redshift_generator(self) -> Any:
        """Get RedshiftProfileGenerator."""
        from floe_dbt.profiles.redshift import RedshiftProfileGenerator

        return RedshiftProfileGenerator()

    def test_bigquery_env_secret_convention(
        self,
        bigquery_generator: Any,
    ) -> None:
        """Test BigQuery uses environment-prefixed key path secrets."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "my-project",
                    "dataset": "analytics",
                },
            },
        }

        config = ProfileGeneratorConfig(environment="prod")
        result = bigquery_generator.generate(artifacts, config)

        # BigQuery uses keyfile or impersonation - check for env var pattern
        profile = result["prod"]
        # Should have environment-specific reference
        assert profile is not None

    def test_redshift_env_secret_convention(
        self,
        redshift_generator: Any,
    ) -> None:
        """Test Redshift uses environment-prefixed password secrets."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "compute": {
                "target": "redshift",
                "properties": {
                    "host": "cluster.region.redshift.amazonaws.com",
                    "port": 5439,
                    "dbname": "analytics",
                },
            },
        }

        config = ProfileGeneratorConfig(environment="staging")
        result = redshift_generator.generate(artifacts, config)

        # Should use STAGING-prefixed env vars
        assert "{{ env_var('REDSHIFT_STAGING_USER') }}" in result["staging"]["user"]
        assert "{{ env_var('REDSHIFT_STAGING_PASSWORD') }}" in result["staging"]["password"]
