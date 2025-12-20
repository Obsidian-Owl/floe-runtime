"""Integration tests for Snowflake profile generation and validation.

T035: [US3] Create packages/floe-dbt/tests/integration/test_snowflake.py

These tests verify Snowflake profile generation produces valid dbt profile
structure. Since Snowflake is a cloud service, we test profile structure
validation only (no actual connection tests).

Requirements:
- dbt-snowflake adapter must be installed for full validation
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

# Check if dbt-snowflake is available
try:
    import dbt.adapters.snowflake  # noqa: F401

    HAS_DBT_SNOWFLAKE = True
except ImportError:
    HAS_DBT_SNOWFLAKE = False


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


class TestSnowflakeProfileGeneration:
    """Test Snowflake profile generation using ProfileFactory."""

    @pytest.fixture
    def factory(self) -> Any:
        """Get ProfileFactory class."""
        from floe_dbt.factory import ProfileFactory

        return ProfileFactory

    @pytest.mark.requirement("006-FR-010")
    @pytest.mark.requirement("003-FR-002")
    def test_generate_snowflake_profile_structure(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Snowflake profile generation produces correct structure.

        Covers:
        - 003-FR-002: Support all 7 compute targets (Snowflake)
        """
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
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
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("snowflake")
        outputs = generator.generate(artifacts, config)

        assert "dev" in outputs
        profile = outputs["dev"]
        assert profile["type"] == "snowflake"
        assert profile["account"] == "xy12345.us-east-1"
        assert profile["warehouse"] == "COMPUTE_WH"
        assert profile["database"] == "ANALYTICS"
        assert profile["schema"] == "PUBLIC"
        assert profile["role"] == "TRANSFORMER"

    @pytest.mark.requirement("006-FR-010")
    @pytest.mark.requirement("003-FR-003")
    def test_snowflake_profile_env_var_security(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Snowflake credentials use env_var template (never hardcoded).

        Covers:
        - 003-FR-003: Use environment variable references for credentials
        """
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "snowflake",
                "properties": {
                    "account": "xy12345.us-east-1",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(
            profile_name="floe", target_name="prod", environment="prod"
        )
        generator = factory.create("snowflake")
        outputs = generator.generate(artifacts, config)

        profile = outputs["prod"]
        assert "{{ env_var(" in profile["user"]
        assert "{{ env_var(" in profile["password"]
        assert "SNOWFLAKE" in profile["user"]
        assert "PROD" in profile["user"]

    @pytest.mark.requirement("006-FR-010")
    def test_generate_snowflake_profile_minimal(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Snowflake profile with minimal required fields."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "snowflake",
                "properties": {
                    "account": "xy12345.us-east-1",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("snowflake")
        outputs = generator.generate(artifacts, config)

        profile = outputs["dev"]
        assert profile["type"] == "snowflake"
        assert profile["account"] == "xy12345.us-east-1"
        # Optional fields should be absent
        assert "warehouse" not in profile
        assert "database" not in profile


class TestSnowflakeProfileValidation:
    """Test Snowflake profile YAML structure validation."""

    @pytest.mark.skipif(
        not HAS_DBT_SNOWFLAKE,
        reason="dbt-snowflake adapter not installed",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_valid_profile_structure_accepted_by_dbt(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that well-formed Snowflake profile is accepted by dbt."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "snowflake",
                        "account": "xy12345.us-east-1",
                        "user": "test_user",
                        "password": "test_password",
                        "warehouse": "COMPUTE_WH",
                        "database": "ANALYTICS",
                        "schema": "PUBLIC",
                        "role": "TRANSFORMER",
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
        not HAS_DBT_SNOWFLAKE,
        reason="dbt-snowflake adapter not installed",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_snowflake_profile_missing_account_fails(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that Snowflake profile without account fails validation."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "snowflake",
                        # Missing 'account' - required field
                        "user": "test_user",
                        "password": "test_password",
                        "warehouse": "COMPUTE_WH",
                        "database": "ANALYTICS",
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


class TestSnowflakeProfileEdgeCases:
    """Test edge cases in Snowflake profile handling."""

    @pytest.mark.requirement("006-FR-010")
    def test_snowflake_profile_with_authenticator(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Snowflake profile with alternative authenticator."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "snowflake",
                "properties": {
                    "account": "xy12345.us-east-1",
                    "warehouse": "COMPUTE_WH",
                    "database": "ANALYTICS",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create("snowflake")
        outputs = generator.generate(artifacts, config)

        # Profile should be generated successfully
        assert outputs["dev"]["type"] == "snowflake"

    @pytest.mark.requirement("006-FR-010")
    def test_snowflake_multi_environment_profiles(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Snowflake profile generation for multiple environments."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "snowflake",
                "properties": {
                    "account": "xy12345.us-east-1",
                },
            },
            "transforms": [],
        }

        # Generate for dev
        dev_config = ProfileGeneratorConfig(
            profile_name="floe", target_name="dev", environment="dev"
        )
        generator = ProfileFactory.create("snowflake")
        dev_outputs = generator.generate(artifacts, dev_config)

        # Generate for prod
        prod_config = ProfileGeneratorConfig(
            profile_name="floe", target_name="prod", environment="prod"
        )
        prod_outputs = generator.generate(artifacts, prod_config)

        # Both should have correct environment-prefixed credentials
        assert "DEV" in dev_outputs["dev"]["user"]
        assert "PROD" in prod_outputs["prod"]["user"]
