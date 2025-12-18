"""Unit tests for floe_cube.config configuration generator.

T013: [US1] Unit test - config generator creates valid cube.js for each database_type
T014: [US1] Unit test - config generator references K8s secrets (never embeds credentials)

Tests FR-001, FR-002, FR-003, FR-004:
- FR-001: Generate Cube configuration from ConsumptionConfig
- FR-002: Support all database_type values (postgres, snowflake, bigquery, databricks, trino)
- FR-003: Reference Kubernetes secrets (never embed secrets)
- FR-004: Generate valid cube.js configuration file format
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

# Note: These tests are written BEFORE the config module exists (TDD).
# They will fail until T016-T020 implementation is complete.


class TestCubeConfigGenerator:
    """Tests for Cube configuration generation from ConsumptionConfig."""

    @pytest.fixture
    def minimal_consumption_config(self) -> dict[str, Any]:
        """Minimal ConsumptionConfig for testing."""
        return {
            "enabled": True,
            "database_type": "postgres",
            "port": 4000,
            "api_secret_ref": None,
            "dev_mode": False,
            "pre_aggregations": {
                "refresh_schedule": "*/30 * * * *",
                "timezone": "UTC",
            },
            "security": {
                "row_level": True,
                "filter_column": "organization_id",
            },
        }

    @pytest.fixture
    def full_consumption_config(self) -> dict[str, Any]:
        """Full ConsumptionConfig for testing."""
        return {
            "enabled": True,
            "database_type": "snowflake",
            "port": 8080,
            "api_secret_ref": "cube-api-secret",
            "dev_mode": True,
            "pre_aggregations": {
                "refresh_schedule": "0 * * * *",
                "timezone": "America/New_York",
            },
            "security": {
                "row_level": True,
                "filter_column": "org_id",
            },
        }

    # T013: Config generator creates valid cube.js for each database_type

    def test_postgres_database_driver_template(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """Postgres database type should use correct driver configuration."""
        from floe_cube.config import CubeConfigGenerator

        minimal_consumption_config["database_type"] = "postgres"
        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        assert "CUBEJS_DB_TYPE" in config
        assert config["CUBEJS_DB_TYPE"] == "postgres"

    def test_snowflake_database_driver_template(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """Snowflake database type should use correct driver configuration."""
        from floe_cube.config import CubeConfigGenerator

        minimal_consumption_config["database_type"] = "snowflake"
        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        assert "CUBEJS_DB_TYPE" in config
        assert config["CUBEJS_DB_TYPE"] == "snowflake"

    def test_bigquery_database_driver_template(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """BigQuery database type should use correct driver configuration."""
        from floe_cube.config import CubeConfigGenerator

        minimal_consumption_config["database_type"] = "bigquery"
        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        assert "CUBEJS_DB_TYPE" in config
        assert config["CUBEJS_DB_TYPE"] == "bigquery"

    def test_databricks_database_driver_template(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """Databricks database type should use correct driver configuration."""
        from floe_cube.config import CubeConfigGenerator

        minimal_consumption_config["database_type"] = "databricks"
        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        assert "CUBEJS_DB_TYPE" in config
        assert config["CUBEJS_DB_TYPE"] == "databricks-jdbc"

    def test_trino_database_driver_template(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """Trino database type should use correct driver configuration."""
        from floe_cube.config import CubeConfigGenerator

        minimal_consumption_config["database_type"] = "trino"
        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        assert "CUBEJS_DB_TYPE" in config
        assert config["CUBEJS_DB_TYPE"] == "trino"

    def test_duckdb_database_driver_template(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """DuckDB database type should use correct driver configuration."""
        from floe_cube.config import CubeConfigGenerator

        minimal_consumption_config["database_type"] = "duckdb"
        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        assert "CUBEJS_DB_TYPE" in config
        assert config["CUBEJS_DB_TYPE"] == "duckdb"

    def test_invalid_database_type_raises_error(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """Invalid database type should raise ValueError."""
        from floe_cube.config import CubeConfigGenerator

        minimal_consumption_config["database_type"] = "invalid_db"
        generator = CubeConfigGenerator(minimal_consumption_config)

        with pytest.raises(ValueError) as exc_info:
            generator.generate()

        assert "database_type" in str(exc_info.value).lower()
        assert "invalid_db" in str(exc_info.value)

    def test_api_port_configuration(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """API port should be configurable."""
        from floe_cube.config import CubeConfigGenerator

        minimal_consumption_config["port"] = 9090
        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        assert "CUBEJS_API_PORT" in config
        assert config["CUBEJS_API_PORT"] == "9090"

    def test_dev_mode_configuration(
        self,
        full_consumption_config: dict[str, Any],
    ) -> None:
        """Dev mode should be configured when enabled."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(full_consumption_config)
        config = generator.generate()

        assert "CUBEJS_DEV_MODE" in config
        assert config["CUBEJS_DEV_MODE"] == "true"

    def test_dev_mode_disabled_by_default(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """Dev mode should be disabled by default."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        # Either not set or set to false
        assert config.get("CUBEJS_DEV_MODE", "false") in ("false", None)

    def test_pre_aggregations_refresh_schedule(
        self,
        full_consumption_config: dict[str, Any],
    ) -> None:
        """Pre-aggregation refresh schedule should be configured."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(full_consumption_config)
        config = generator.generate()

        assert "CUBEJS_SCHEDULED_REFRESH_DEFAULT" in config
        assert config["CUBEJS_SCHEDULED_REFRESH_DEFAULT"] == "true"

    # T014: Config generator references K8s secrets (never embeds credentials)

    def test_api_secret_ref_environment_variable(
        self,
        full_consumption_config: dict[str, Any],
    ) -> None:
        """API secret should reference K8s secret via environment variable."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(full_consumption_config)
        config = generator.generate()

        # Should reference secret, not contain the actual value
        assert "CUBEJS_API_SECRET" in config
        # The value should be an env var reference or k8s secret reference
        assert config["CUBEJS_API_SECRET"].startswith("${")
        assert "cube-api-secret" in config["CUBEJS_API_SECRET"]

    def test_api_secret_not_embedded_plaintext(
        self,
        full_consumption_config: dict[str, Any],
    ) -> None:
        """API secrets should NEVER be embedded as plaintext."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(full_consumption_config)
        config = generator.generate()

        # Verify the secret value is NOT the secret name directly
        # but rather a reference to retrieve it
        for key, value in config.items():
            if ("SECRET" in key or "PASSWORD" in key or "KEY" in key) and value is not None:
                assert (
                    value.startswith("${") or value == ""
                ), f"Secret {key} appears to contain plaintext value"

    def test_database_credentials_use_secret_refs(
        self,
        minimal_consumption_config: dict[str, Any],
    ) -> None:
        """Database credentials should use secret references."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(minimal_consumption_config)
        config = generator.generate()

        # Database password should not be in the config directly
        # Instead it should reference env vars or k8s secrets
        db_related_keys = [k for k in config if "DB" in k]
        for key in db_related_keys:
            if "PASS" in key or "SECRET" in key:
                value = config.get(key)
                if value:
                    assert value.startswith(
                        "${"
                    ), f"{key} should reference secret, not contain value"

    def test_no_hardcoded_credentials_in_config(
        self,
        full_consumption_config: dict[str, Any],
    ) -> None:
        """Generated config should never contain hardcoded credentials."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(full_consumption_config)
        config_str = generator.generate_file_content()

        # Check that common secret patterns are not present
        sensitive_patterns = [
            "password=",
            "secret=",
            "api_key=",
            "token=",
            "-----BEGIN",  # PEM keys
        ]
        for pattern in sensitive_patterns:
            assert (
                pattern.lower() not in config_str.lower()
            ), f"Sensitive pattern '{pattern}' found in config"


class TestCubeConfigFileWriter:
    """Tests for writing Cube configuration to file."""

    @pytest.fixture
    def consumption_config(self) -> dict[str, Any]:
        """ConsumptionConfig for file writing tests."""
        return {
            "enabled": True,
            "database_type": "postgres",
            "port": 4000,
            "api_secret_ref": "cube-secret",
            "dev_mode": False,
            "pre_aggregations": {
                "refresh_schedule": "*/30 * * * *",
                "timezone": "UTC",
            },
            "security": {
                "row_level": True,
                "filter_column": "organization_id",
            },
        }

    def test_write_config_to_floe_directory(
        self,
        tmp_path: Path,
        consumption_config: dict[str, Any],
    ) -> None:
        """Config should be written to .floe/cube/ directory."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(consumption_config)
        output_dir = tmp_path / ".floe" / "cube"
        generator.write_config(output_dir)

        config_file = output_dir / "cube.js"
        assert config_file.exists()

    def test_written_config_is_valid_javascript(
        self,
        tmp_path: Path,
        consumption_config: dict[str, Any],
    ) -> None:
        """Generated cube.js should be valid JavaScript module format."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(consumption_config)
        output_dir = tmp_path / ".floe" / "cube"
        generator.write_config(output_dir)

        config_file = output_dir / "cube.js"
        content = config_file.read_text()

        # Should be a valid module.exports
        assert "module.exports" in content

    def test_creates_output_directory_if_not_exists(
        self,
        tmp_path: Path,
        consumption_config: dict[str, Any],
    ) -> None:
        """Should create output directory if it doesn't exist."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator(consumption_config)
        output_dir = tmp_path / "nonexistent" / ".floe" / "cube"

        # Directory doesn't exist
        assert not output_dir.exists()

        generator.write_config(output_dir)

        # Now it should exist with the config file
        assert output_dir.exists()
        assert (output_dir / "cube.js").exists()


class TestDatabaseDriverTemplates:
    """Tests for database driver template selection."""

    @pytest.mark.parametrize(
        "db_type,expected_driver",
        [
            ("postgres", "postgres"),
            ("snowflake", "snowflake"),
            ("bigquery", "bigquery"),
            ("databricks", "databricks-jdbc"),
            ("trino", "trino"),
            ("duckdb", "duckdb"),
        ],
    )
    def test_database_driver_mapping(
        self,
        db_type: str,
        expected_driver: str,
    ) -> None:
        """Each database type should map to correct Cube driver."""
        from floe_cube.config import get_cube_driver_type

        result = get_cube_driver_type(db_type)
        assert result == expected_driver

    def test_unknown_database_type_raises(self) -> None:
        """Unknown database type should raise ValueError."""
        from floe_cube.config import get_cube_driver_type

        with pytest.raises(ValueError) as exc_info:
            get_cube_driver_type("oracle")

        assert "oracle" in str(exc_info.value).lower()
        assert "unsupported" in str(exc_info.value).lower()


class TestConfigGeneratorWithCompiledArtifacts:
    """Tests for generating config from actual CompiledArtifacts."""

    def test_from_compiled_artifacts(self, sample_compiled_artifacts: Any) -> None:
        """Should generate config from CompiledArtifacts."""
        from floe_cube.config import CubeConfigGenerator

        generator = CubeConfigGenerator.from_compiled_artifacts(sample_compiled_artifacts)
        config = generator.generate()

        assert "CUBEJS_DB_TYPE" in config
        assert "CUBEJS_API_PORT" in config

    @pytest.fixture
    def sample_compiled_artifacts(self) -> Any:
        """Sample CompiledArtifacts-like object for testing.

        Uses a mock with model_dump() method since that's what
        CubeConfigGenerator.from_compiled_artifacts expects.
        """
        from unittest.mock import MagicMock

        # Create a mock object that has a consumption attribute with model_dump()
        consumption_mock = MagicMock()
        consumption_mock.model_dump.return_value = {
            "enabled": True,
            "database_type": "duckdb",
            "port": 4000,
            "dev_mode": False,
            # Omit None values - the code handles missing keys with .get()
        }

        artifacts_mock = MagicMock()
        artifacts_mock.consumption = consumption_mock

        return artifacts_mock


class TestObservabilityConfig:
    """Tests for observability configuration (T088)."""

    def test_openlineage_endpoint_configuration(self) -> None:
        """OpenLineage endpoint should be configured when provided."""
        from floe_cube.config import CubeConfigGenerator

        config = {
            "database_type": "postgres",
            "observability": {
                "openlineage_endpoint": "http://localhost:5000",
            },
        }
        generator = CubeConfigGenerator(config)
        result = generator.generate()

        assert result["FLOE_OPENLINEAGE_ENDPOINT"] == "http://localhost:5000"
        assert result["FLOE_OPENLINEAGE_ENABLED"] == "true"

    def test_openlineage_namespace_configuration(self) -> None:
        """OpenLineage namespace should be configurable."""
        from floe_cube.config import CubeConfigGenerator

        config = {
            "database_type": "postgres",
            "observability": {
                "openlineage_endpoint": "http://localhost:5000",
                "openlineage_namespace": "my-custom-namespace",
            },
        }
        generator = CubeConfigGenerator(config)
        result = generator.generate()

        assert result["FLOE_OPENLINEAGE_NAMESPACE"] == "my-custom-namespace"

    def test_openlineage_not_configured_when_no_endpoint(self) -> None:
        """OpenLineage should not be configured when endpoint is not provided."""
        from floe_cube.config import CubeConfigGenerator

        config = {
            "database_type": "postgres",
        }
        generator = CubeConfigGenerator(config)
        result = generator.generate()

        assert "FLOE_OPENLINEAGE_ENDPOINT" not in result
        assert "FLOE_OPENLINEAGE_ENABLED" not in result

    def test_openlineage_not_enabled_with_only_namespace(self) -> None:
        """OpenLineage should not be enabled with only namespace (no endpoint)."""
        from floe_cube.config import CubeConfigGenerator

        config = {
            "database_type": "postgres",
            "observability": {
                "openlineage_namespace": "my-namespace",
            },
        }
        generator = CubeConfigGenerator(config)
        result = generator.generate()

        # Namespace is set but endpoint is not, so OpenLineage is not enabled
        assert "FLOE_OPENLINEAGE_ENABLED" not in result
        # Namespace should still be set for when endpoint is provided via env var
        assert result.get("FLOE_OPENLINEAGE_NAMESPACE") == "my-namespace"


class TestCubeStoreConfig:
    """Tests for Cube Store configuration (T094)."""

    def test_cube_store_s3_bucket_configuration(self) -> None:
        """S3 bucket should configure Cube Store."""
        from floe_cube.config import CubeConfigGenerator

        config = {
            "database_type": "postgres",
            "cube_store": {
                "s3_bucket": "my-pre-aggregations-bucket",
            },
        }
        generator = CubeConfigGenerator(config)
        result = generator.generate()

        assert result["CUBEJS_EXT_DB_TYPE"] == "cubestore"
        assert result["CUBEJS_CUBESTORE_S3_BUCKET"] == "my-pre-aggregations-bucket"

    def test_cube_store_s3_region_configuration(self) -> None:
        """S3 region should be configurable."""
        from floe_cube.config import CubeConfigGenerator

        config = {
            "database_type": "postgres",
            "cube_store": {
                "s3_bucket": "my-bucket",
                "s3_region": "us-west-2",
            },
        }
        generator = CubeConfigGenerator(config)
        result = generator.generate()

        assert result["CUBEJS_CUBESTORE_S3_REGION"] == "us-west-2"

    def test_cube_store_s3_credentials_use_secret_refs(self) -> None:
        """S3 credentials should reference K8s secrets."""
        from floe_cube.config import CubeConfigGenerator

        config = {
            "database_type": "postgres",
            "cube_store": {
                "s3_bucket": "my-bucket",
                "s3_access_key_ref": "aws-access-key",
                "s3_secret_key_ref": "aws-secret-key",
            },
        }
        generator = CubeConfigGenerator(config)
        result = generator.generate()

        # Credentials should be secret references, not plaintext
        assert result["CUBEJS_CUBESTORE_AWS_ACCESS_KEY_ID"] == "${aws-access-key}"
        assert result["CUBEJS_CUBESTORE_AWS_SECRET_ACCESS_KEY"] == "${aws-secret-key}"

    def test_cube_store_custom_s3_endpoint(self) -> None:
        """Custom S3 endpoint for MinIO/LocalStack should be configurable."""
        from floe_cube.config import CubeConfigGenerator

        config = {
            "database_type": "postgres",
            "cube_store": {
                "s3_bucket": "my-bucket",
                "s3_endpoint": "http://localhost:4566",
            },
        }
        generator = CubeConfigGenerator(config)
        result = generator.generate()

        assert result["CUBEJS_CUBESTORE_S3_ENDPOINT"] == "http://localhost:4566"

    def test_cube_store_not_configured_without_bucket(self) -> None:
        """Cube Store should not be configured without S3 bucket."""
        from floe_cube.config import CubeConfigGenerator

        config = {
            "database_type": "postgres",
        }
        generator = CubeConfigGenerator(config)
        result = generator.generate()

        assert "CUBEJS_EXT_DB_TYPE" not in result
        assert "CUBEJS_CUBESTORE_S3_BUCKET" not in result

    def test_cube_store_full_configuration(self) -> None:
        """Full Cube Store configuration should include all settings."""
        from floe_cube.config import CubeConfigGenerator

        config = {
            "database_type": "postgres",
            "cube_store": {
                "s3_bucket": "prod-preagg-bucket",
                "s3_region": "eu-west-1",
                "s3_access_key_ref": "cube-aws-access-key",
                "s3_secret_key_ref": "cube-aws-secret-key",
                "s3_endpoint": "https://s3.eu-west-1.amazonaws.com",
            },
        }
        generator = CubeConfigGenerator(config)
        result = generator.generate()

        assert result["CUBEJS_EXT_DB_TYPE"] == "cubestore"
        assert result["CUBEJS_CUBESTORE_S3_BUCKET"] == "prod-preagg-bucket"
        assert result["CUBEJS_CUBESTORE_S3_REGION"] == "eu-west-1"
        assert result["CUBEJS_CUBESTORE_AWS_ACCESS_KEY_ID"] == "${cube-aws-access-key}"
        assert result["CUBEJS_CUBESTORE_AWS_SECRET_ACCESS_KEY"] == "${cube-aws-secret-key}"
        assert result["CUBEJS_CUBESTORE_S3_ENDPOINT"] == "https://s3.eu-west-1.amazonaws.com"
