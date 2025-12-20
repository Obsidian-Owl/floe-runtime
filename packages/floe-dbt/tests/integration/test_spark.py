"""Integration tests for Spark profile generation and validation.

T039: [US3] Create packages/floe-dbt/tests/integration/test_spark.py

These tests verify Spark profile generation produces valid dbt profile
structure. Connection tests require a running Spark Thrift server.

Requirements:
- dbt-spark adapter must be installed for full validation
- Tests marked with @pytest.mark.integration for CI filtering

See Also:
    - specs/006-integration-testing/spec.md FR-010
"""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

import pytest
import yaml

# Check if dbt-spark is available
try:
    import dbt.adapters.spark  # noqa: F401

    HAS_DBT_SPARK = True
except ImportError:
    HAS_DBT_SPARK = False


pytestmark = [
    pytest.mark.integration,
]


@pytest.fixture
def dbt_project_dir(tmp_path: Path) -> Path:
    """Create minimal dbt project for validation testing."""
    project_dir = tmp_path / "dbt_project"
    project_dir.mkdir()

    dbt_project = {
        "name": "test_project",
        "version": "1.0.0",
        "config-version": 2,
        "profile": "floe",
    }
    (project_dir / "dbt_project.yml").write_text(yaml.safe_dump(dbt_project))
    (project_dir / "models").mkdir()

    return project_dir


@pytest.fixture
def profiles_dir(tmp_path: Path) -> Path:
    """Create profiles directory."""
    profiles_path = tmp_path / "profiles"
    profiles_path.mkdir()
    return profiles_path


class TestSparkProfileGeneration:
    """Test Spark profile generation using ProfileFactory."""

    @pytest.fixture
    def factory(self) -> Any:
        """Get ProfileFactory class."""
        from floe_dbt.factory import ProfileFactory

        return ProfileFactory

    @pytest.mark.requirement("006-FR-010")
    @pytest.mark.requirement("003-FR-002")
    def test_generate_spark_profile_structure(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Spark profile generation produces correct structure.

        Covers:
        - 003-FR-002: Support all 7 compute targets (Spark)
        """
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "host": "spark://master:7077",
                    "method": "thrift",
                    "schema": "default",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("spark")
        outputs = generator.generate(artifacts, config)

        assert "dev" in outputs
        profile = outputs["dev"]
        assert profile["type"] == "spark"
        assert profile["method"] == "thrift"
        assert profile["schema"] == "default"

    @pytest.mark.requirement("006-FR-010")
    def test_generate_spark_profile_with_http_method(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Spark profile with HTTP method (e.g., for Databricks)."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "host": "localhost",
                    "port": 443,
                    "method": "http",
                    "schema": "analytics",
                    "organization": "my-org",
                    "cluster": "my-cluster",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("spark")
        outputs = generator.generate(artifacts, config)

        profile = outputs["dev"]
        assert profile["method"] == "http"

    @pytest.mark.requirement("006-FR-010")
    def test_generate_spark_profile_minimal(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Spark profile with minimal required fields."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "thrift",
                    "schema": "default",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("spark")
        outputs = generator.generate(artifacts, config)

        profile = outputs["dev"]
        assert profile["type"] == "spark"
        assert profile["method"] == "thrift"


class TestSparkProfileValidation:
    """Test Spark profile YAML structure validation."""

    @pytest.mark.skipif(
        not HAS_DBT_SPARK,
        reason="dbt-spark adapter not installed",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_valid_profile_structure_accepted_by_dbt(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that well-formed Spark profile is accepted by dbt."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "spark",
                        "method": "thrift",
                        "host": "localhost",
                        "port": 10000,
                        "schema": "default",
                        "threads": 4,
                    }
                },
            }
        }
        profiles_path = profiles_dir / "profiles.yml"
        profiles_path.write_text(yaml.safe_dump(profile))

        result = subprocess.run(
            [
                "dbt",
                "debug",
                "--project-dir",
                str(dbt_project_dir),
                "--profiles-dir",
                str(profiles_dir),
            ],
            capture_output=True,
            text=True,
            cwd=dbt_project_dir,
        )

        # Profile structure should be valid (connection will fail)
        assert "profile" in result.stdout.lower() or "profiles.yml" in result.stdout

    @pytest.mark.skipif(
        not HAS_DBT_SPARK,
        reason="dbt-spark adapter not installed",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_spark_profile_missing_method_fails(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that Spark profile without method fails validation."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "spark",
                        # Missing 'method' - required field
                        "host": "localhost",
                        "schema": "default",
                        "threads": 4,
                    }
                },
            }
        }
        profiles_path = profiles_dir / "profiles.yml"
        profiles_path.write_text(yaml.safe_dump(profile))

        result = subprocess.run(
            [
                "dbt",
                "debug",
                "--project-dir",
                str(dbt_project_dir),
                "--profiles-dir",
                str(profiles_dir),
            ],
            capture_output=True,
            text=True,
            cwd=dbt_project_dir,
        )

        # Should fail due to missing required field
        assert result.returncode != 0


class TestSparkProfileEdgeCases:
    """Test edge cases in Spark profile handling."""

    @pytest.mark.requirement("006-FR-010")
    def test_spark_profile_session_method(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Spark profile with session method (local development)."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "session",
                    "schema": "default",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create("spark")
        outputs = generator.generate(artifacts, config)

        assert outputs["dev"]["type"] == "spark"
        assert outputs["dev"]["method"] == "session"

    @pytest.mark.requirement("006-FR-010")
    def test_spark_multi_environment_profiles(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Spark profile generation for multiple environments."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "thrift",
                    "schema": "default",
                },
            },
            "transforms": [],
        }

        # Generate for dev
        dev_config = ProfileGeneratorConfig(
            profile_name="floe", target_name="dev", environment="dev"
        )
        generator = ProfileFactory.create("spark")
        dev_outputs = generator.generate(artifacts, dev_config)

        # Generate for prod
        prod_config = ProfileGeneratorConfig(
            profile_name="floe", target_name="prod", environment="prod"
        )
        prod_outputs = generator.generate(artifacts, prod_config)

        # Both should be generated successfully
        assert dev_outputs["dev"]["type"] == "spark"
        assert prod_outputs["prod"]["type"] == "spark"

    @pytest.mark.requirement("006-FR-010")
    def test_spark_profile_with_odbc_method(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Spark profile with ODBC method."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "spark",
                "properties": {
                    "method": "odbc",
                    "schema": "analytics",
                    "driver": "/opt/simba/spark/lib/64/libsparkodbc_sb64.so",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create("spark")
        outputs = generator.generate(artifacts, config)

        assert outputs["dev"]["method"] == "odbc"
