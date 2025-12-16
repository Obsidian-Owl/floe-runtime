"""Unit tests for SparkProfileGenerator.

T021: [P] [US2] Unit tests for SparkProfileGenerator

This module uses the BaseProfileGeneratorTests pattern for standardized
adapter testing. Spark-specific tests cover different connection methods.
"""

from __future__ import annotations

from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGenerator, ProfileGeneratorConfig
from testing.base_classes.adapter_test_base import BaseProfileGeneratorTests


class TestSparkProfileGenerator(BaseProfileGeneratorTests):
    """Test suite for Spark profile generation.

    Inherits from BaseProfileGeneratorTests to get standardized tests.
    Spark-specific tests cover thrift, http, odbc, and session methods.
    """

    @pytest.fixture
    def generator(self) -> ProfileGenerator:
        """Create SparkProfileGenerator instance."""
        from floe_dbt.profiles.spark import SparkProfileGenerator

        return SparkProfileGenerator()

    @property
    def target_type(self) -> str:
        """Spark adapter type."""
        return "spark"

    @property
    def required_fields(self) -> set[str]:
        """Required fields in Spark profile."""
        return {"type", "method", "threads"}

    def get_minimal_artifacts(self) -> dict[str, Any]:
        """Minimal CompiledArtifacts for Spark."""
        return {
            "version": "1.0.0",
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "thrift",
                    "host": "spark-thrift.local",
                },
            },
            "transforms": [],
        }

    # =========================================================================
    # Spark-specific tests
    # =========================================================================

    def test_generate_thrift_method(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test Thrift connection method configuration."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
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
        assert config.target_name is not None
        target = result[config.target_name]

        assert target["method"] == "thrift"
        assert target["host"] == "spark-thrift.local"
        assert target["port"] == 10000

    def test_generate_http_method(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test HTTP connection method configuration."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
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
        assert config.target_name is not None
        assert result[config.target_name]["method"] == "http"

    def test_generate_session_method(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test Session connection method configuration."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "session",
                },
            },
            "transforms": [],
        }

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["method"] == "session"

    def test_generate_odbc_method(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test ODBC connection method configuration."""
        artifacts: dict[str, Any] = {
            "version": "1.0.0",
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
        assert config.target_name is not None
        assert result[config.target_name]["method"] == "odbc"

    def test_generate_uses_default_port(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that default Spark port 10000 is used when not specified."""
        result = generator.generate(self.get_minimal_artifacts(), config)
        assert config.target_name is not None
        assert result[config.target_name]["port"] == 10000

    def test_generate_includes_schema(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that schema is included when specified."""
        artifacts = self.get_minimal_artifacts()
        artifacts["compute"]["properties"]["schema"] = "analytics"

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name]["schema"] == "analytics"

    def test_generate_supports_cluster_config(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that cluster configuration is supported."""
        artifacts = self.get_minimal_artifacts()
        artifacts["compute"]["properties"]["cluster"] = "my-spark-cluster"

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert result[config.target_name].get("cluster") == "my-spark-cluster"
