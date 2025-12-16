"""Unit tests for SparkProfileGenerator.

T021: [P] [US2] Unit tests for SparkProfileGenerator
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGeneratorConfig


class TestSparkProfileGenerator:
    """Test suite for Spark profile generation."""

    @pytest.fixture
    def generator(self) -> Any:
        """Create SparkProfileGenerator instance."""
        from floe_dbt.profiles.spark import SparkProfileGenerator

        return SparkProfileGenerator()

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
        spark_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that generate returns correct structure."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": spark_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)

        assert config.target_name in result
        target = result[config.target_name]
        assert target["type"] == "spark"
        assert "method" in target
        assert "host" in target

    def test_generate_thrift_method(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Thrift connection method configuration."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "thrift",
                    "host": "spark-thrift.local",
                    "port": 10000,
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        assert target["method"] == "thrift"
        assert target["host"] == "spark-thrift.local"
        assert target["port"] == 10000

    def test_generate_http_method(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test HTTP connection method configuration."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "http",
                    "host": "spark-http.local",
                    "port": 443,
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        assert target["method"] == "http"

    def test_generate_session_method(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Session connection method configuration."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "session",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        assert target["method"] == "session"

    def test_generate_odbc_method(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test ODBC connection method configuration."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "odbc",
                    "host": "spark.local",
                    "driver": "/opt/spark/lib/libsparkodbc.so",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        target = result[config.target_name]

        assert target["method"] == "odbc"

    def test_generate_uses_default_port(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that default Spark port 10000 is used when not specified."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "thrift",
                    "host": "localhost",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["port"] == 10000

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
                "target": "spark",
                "properties": {
                    "method": "thrift",
                    "host": "localhost",
                    "schema": "analytics",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["schema"] == "analytics"

    def test_generate_threads_from_config(
        self,
        generator: Any,
        spark_compute_config: dict[str, Any],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that thread count from config is used."""
        config = ProfileGeneratorConfig(
            profile_name="floe",
            target_name="prod",
            threads=16,
        )
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": spark_compute_config,
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name]["threads"] == 16

    def test_generate_supports_cluster_config(
        self,
        generator: Any,
        config: ProfileGeneratorConfig,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test that cluster configuration is supported."""
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "thrift",
                    "host": "localhost",
                    "cluster": "my-spark-cluster",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert result[config.target_name].get("cluster") == "my-spark-cluster"
