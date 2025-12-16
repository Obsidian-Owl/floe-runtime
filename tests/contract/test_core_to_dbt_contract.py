"""Contract tests for floe-core to floe-dbt integration.

These tests validate that CompiledArtifacts produced by floe-core
can be consumed by floe-dbt profile generators.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


@pytest.mark.contract
class TestCoreToDbtContract:
    """Contract tests between floe-core and floe-dbt."""

    def test_compiled_artifacts_compute_config_consumable(self) -> None:
        """Test that CompiledArtifacts.compute can be used by profile generators."""
        from floe_core.compiler import CompiledArtifacts
        from floe_dbt.profiles.base import ProfileGeneratorConfig
        from floe_dbt.profiles.duckdb import DuckDBProfileGenerator

        # Create CompiledArtifacts
        artifacts = CompiledArtifacts.model_validate({
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {
                "target": "duckdb",
                "properties": {"path": ":memory:"},
            },
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "consumption": {},
            "governance": {},
            "observability": {},
        })

        # Convert to dict format expected by profile generators
        artifacts_dict = artifacts.model_dump(mode="json")

        # Profile generator should consume this successfully
        generator = DuckDBProfileGenerator()
        config = ProfileGeneratorConfig(
            profile_name="test",
            target_name="dev",
            threads=4,
        )

        profile = generator.generate(artifacts_dict, config)

        assert "dev" in profile
        assert profile["dev"]["type"] == "duckdb"

    def test_compute_properties_passed_to_generators(self) -> None:
        """Test that compute.properties are accessible to generators."""
        from floe_core.compiler import CompiledArtifacts
        from floe_dbt.profiles.base import ProfileGeneratorConfig
        from floe_dbt.profiles.snowflake import SnowflakeProfileGenerator

        artifacts = CompiledArtifacts.model_validate({
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {
                "target": "snowflake",
                "properties": {
                    "account": "xy12345.us-east-1",
                    "warehouse": "COMPUTE_WH",
                    "database": "ANALYTICS",
                    "schema": "PUBLIC",
                    "role": "TRANSFORMER",
                },
            },
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "consumption": {},
            "governance": {},
            "observability": {},
        })

        artifacts_dict = artifacts.model_dump(mode="json")

        generator = SnowflakeProfileGenerator()
        config = ProfileGeneratorConfig(
            profile_name="test",
            target_name="prod",
            threads=8,
        )

        profile = generator.generate(artifacts_dict, config)

        # Properties should be accessible in profile
        assert profile["prod"]["account"] == "xy12345.us-east-1"
        assert profile["prod"]["warehouse"] == "COMPUTE_WH"
        assert profile["prod"]["role"] == "TRANSFORMER"


@pytest.mark.contract
class TestCompiledArtifactsSerializationContract:
    """Tests for JSON serialization contract between packages."""

    def test_compiled_artifacts_json_round_trip(self) -> None:
        """Test CompiledArtifacts survives JSON round-trip for IPC."""
        from floe_core.compiler import CompiledArtifacts

        original = CompiledArtifacts.model_validate({
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "consumption": {},
            "governance": {},
            "observability": {},
        })

        # Serialize to JSON (as would happen in file/IPC)
        json_str = original.model_dump_json()

        # Deserialize (as floe-dbt would)
        loaded = CompiledArtifacts.model_validate_json(json_str)

        assert loaded.version == original.version
        assert loaded.compute.target == original.compute.target
        assert loaded.metadata.source_hash == original.metadata.source_hash

    def test_compiled_artifacts_dict_mode_for_generators(self) -> None:
        """Test model_dump(mode='json') produces generator-compatible dict."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts.model_validate({
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {
                "target": "duckdb",
                "properties": {"path": "/data/warehouse.db"},
            },
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "consumption": {},
            "governance": {},
            "observability": {},
        })

        # This is how profile generators receive artifacts
        artifacts_dict = artifacts.model_dump(mode="json")

        # Should be a plain dict
        assert isinstance(artifacts_dict, dict)

        # Target should be string (not ComputeTarget enum)
        assert isinstance(artifacts_dict["compute"]["target"], str)

        # Properties should be accessible
        assert artifacts_dict["compute"]["properties"]["path"] == "/data/warehouse.db"


@pytest.mark.contract
class TestProfileGeneratorConfigContract:
    """Tests for ProfileGeneratorConfig contract."""

    def test_config_provides_required_fields(self) -> None:
        """Test ProfileGeneratorConfig provides what generators need."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        config = ProfileGeneratorConfig(
            profile_name="analytics",
            target_name="prod",
            threads=16,
        )

        # These fields are required by contract
        assert config.profile_name == "analytics"
        assert config.target_name == "prod"
        assert config.threads == 16

    def test_config_secret_env_var_format(self) -> None:
        """Test secret env var template matches dbt format."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        config = ProfileGeneratorConfig(
            profile_name="test",
            target_name="dev",
            threads=4,
        )

        # Format expected by dbt profiles.yml (service + secret_name)
        secret_ref = config.get_secret_env_var("SNOWFLAKE", "PASSWORD")

        # Expected format: {{ env_var('SERVICE_ENVIRONMENT_SECRET') }}
        assert "env_var" in secret_ref
        assert "SNOWFLAKE" in secret_ref
        assert "PASSWORD" in secret_ref

    def test_config_threads_default(self) -> None:
        """Test threads has sensible default."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        config = ProfileGeneratorConfig(
            profile_name="test",
            target_name="dev",
        )

        # Default should be non-zero
        assert config.threads >= 1


@pytest.mark.contract
class TestProfileGeneratorProtocolContract:
    """Tests for ProfileGenerator Protocol compliance."""

    def test_all_known_generators_implement_protocol(self) -> None:
        """Test all known generators implement ProfileGenerator Protocol."""
        from floe_dbt.profiles.base import ProfileGenerator
        from floe_dbt.profiles.bigquery import BigQueryProfileGenerator
        from floe_dbt.profiles.databricks import DatabricksProfileGenerator
        from floe_dbt.profiles.duckdb import DuckDBProfileGenerator
        from floe_dbt.profiles.postgres import PostgreSQLProfileGenerator
        from floe_dbt.profiles.redshift import RedshiftProfileGenerator
        from floe_dbt.profiles.snowflake import SnowflakeProfileGenerator
        from floe_dbt.profiles.spark import SparkProfileGenerator

        generators = [
            DuckDBProfileGenerator(),
            SnowflakeProfileGenerator(),
            BigQueryProfileGenerator(),
            RedshiftProfileGenerator(),
            DatabricksProfileGenerator(),
            PostgreSQLProfileGenerator(),
            SparkProfileGenerator(),
        ]

        for generator in generators:
            assert isinstance(generator, ProfileGenerator), (
                f"{generator.__class__.__name__} doesn't implement Protocol"
            )

    def test_generator_generate_signature(self) -> None:
        """Test generator.generate() has correct signature."""
        import inspect

        from floe_dbt.profiles.duckdb import DuckDBProfileGenerator

        generator = DuckDBProfileGenerator()

        # Check signature matches Protocol
        sig = inspect.signature(generator.generate)
        params = list(sig.parameters.keys())

        # Should have artifacts and config parameters
        assert len(params) >= 2
        assert "dict" in str(sig.return_annotation) or sig.return_annotation == dict
