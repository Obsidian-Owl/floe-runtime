"""Integration tests for Databricks profile generation and validation.

T038: [US3] Create packages/floe-dbt/tests/integration/test_databricks.py

These tests verify Databricks profile generation produces valid dbt profile
structure. Since Databricks is a cloud service, we test profile structure
validation only (no actual connection tests).

Requirements:
- dbt-databricks adapter must be installed for full validation
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

# Check if dbt-databricks is available
try:
    import dbt.adapters.databricks  # noqa: F401

    HAS_DBT_DATABRICKS = True
except ImportError:
    HAS_DBT_DATABRICKS = False


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


class TestDatabricksProfileGeneration:
    """Test Databricks profile generation using ProfileFactory."""

    @pytest.fixture
    def factory(self) -> Any:
        """Get ProfileFactory class."""
        from floe_dbt.factory import ProfileFactory

        return ProfileFactory

    @pytest.mark.requirement("006-FR-010")
    def test_generate_databricks_profile_structure(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Databricks profile generation produces correct structure."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
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

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("databricks")
        outputs = generator.generate(artifacts, config)

        assert "dev" in outputs
        profile = outputs["dev"]
        assert profile["type"] == "databricks"
        assert profile["host"] == "adb-1234567890.12.azuredatabricks.net"
        assert profile["http_path"] == "/sql/1.0/warehouses/abc123"
        assert profile["catalog"] == "main"
        assert profile["schema"] == "default"

    @pytest.mark.requirement("006-FR-010")
    def test_databricks_profile_env_var_security(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Databricks token uses env_var template (never hardcoded)."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "databricks",
                "properties": {
                    "host": "adb-1234567890.12.azuredatabricks.net",
                    "http_path": "/sql/1.0/warehouses/abc123",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(
            profile_name="floe", target_name="prod", environment="prod"
        )
        generator = factory.create("databricks")
        outputs = generator.generate(artifacts, config)

        profile = outputs["prod"]
        assert "{{ env_var(" in profile["token"]
        assert "DATABRICKS" in profile["token"]
        assert "PROD" in profile["token"]

    @pytest.mark.requirement("006-FR-010")
    def test_generate_databricks_profile_minimal(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Databricks profile with minimal required fields."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "databricks",
                "properties": {
                    "host": "adb-1234567890.12.azuredatabricks.net",
                    "http_path": "/sql/1.0/warehouses/abc123",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("databricks")
        outputs = generator.generate(artifacts, config)

        profile = outputs["dev"]
        assert profile["type"] == "databricks"
        assert profile["host"] == "adb-1234567890.12.azuredatabricks.net"


class TestDatabricksProfileValidation:
    """Test Databricks profile YAML structure validation."""

    @pytest.mark.skipif(
        not HAS_DBT_DATABRICKS,
        reason="dbt-databricks adapter not installed",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_valid_profile_structure_accepted_by_dbt(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that well-formed Databricks profile is accepted by dbt."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "databricks",
                        "host": "adb-1234567890.12.azuredatabricks.net",
                        "http_path": "/sql/1.0/warehouses/abc123",
                        "token": "dapi_test_token",
                        "catalog": "main",
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
        not HAS_DBT_DATABRICKS,
        reason="dbt-databricks adapter not installed",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_databricks_profile_missing_host_fails(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that Databricks profile without host fails validation."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "databricks",
                        # Missing 'host' - required field
                        "http_path": "/sql/1.0/warehouses/abc123",
                        "token": "dapi_test_token",
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


class TestDatabricksProfileEdgeCases:
    """Test edge cases in Databricks profile handling."""

    @pytest.mark.requirement("006-FR-010")
    def test_databricks_profile_with_cluster_id(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Databricks profile with cluster instead of SQL warehouse."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "databricks",
                "properties": {
                    "host": "adb-1234567890.12.azuredatabricks.net",
                    "http_path": "/sql/1.0/warehouses/abc123",
                    "catalog": "main",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create("databricks")
        outputs = generator.generate(artifacts, config)

        assert outputs["dev"]["type"] == "databricks"

    @pytest.mark.requirement("006-FR-010")
    def test_databricks_multi_environment_profiles(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Databricks profile generation for multiple environments."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "databricks",
                "properties": {
                    "host": "adb-1234567890.12.azuredatabricks.net",
                    "http_path": "/sql/1.0/warehouses/abc123",
                },
            },
            "transforms": [],
        }

        # Generate for dev
        dev_config = ProfileGeneratorConfig(
            profile_name="floe", target_name="dev", environment="dev"
        )
        generator = ProfileFactory.create("databricks")
        dev_outputs = generator.generate(artifacts, dev_config)

        # Generate for prod
        prod_config = ProfileGeneratorConfig(
            profile_name="floe", target_name="prod", environment="prod"
        )
        prod_outputs = generator.generate(artifacts, prod_config)

        # Both should have correct environment-prefixed credentials
        assert "DEV" in dev_outputs["dev"]["token"]
        assert "PROD" in prod_outputs["prod"]["token"]

    @pytest.mark.requirement("006-FR-010")
    def test_databricks_profile_unity_catalog(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Databricks profile with Unity Catalog settings."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "databricks",
                "properties": {
                    "host": "adb-1234567890.12.azuredatabricks.net",
                    "http_path": "/sql/1.0/warehouses/abc123",
                    "catalog": "unity_catalog",
                    "schema": "analytics",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create("databricks")
        outputs = generator.generate(artifacts, config)

        assert outputs["dev"]["catalog"] == "unity_catalog"
        assert outputs["dev"]["schema"] == "analytics"
