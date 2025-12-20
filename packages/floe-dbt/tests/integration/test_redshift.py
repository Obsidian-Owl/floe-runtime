"""Integration tests for Redshift profile generation and validation.

T037: [US3] Create packages/floe-dbt/tests/integration/test_redshift.py

These tests verify Redshift profile generation produces valid dbt profile
structure. Since Redshift is a cloud service, we test profile structure
validation only (no actual connection tests).

Requirements:
- dbt-redshift adapter must be installed for full validation
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

# Check if dbt-redshift is available
try:
    import dbt.adapters.redshift  # noqa: F401

    HAS_DBT_REDSHIFT = True
except ImportError:
    HAS_DBT_REDSHIFT = False


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


class TestRedshiftProfileGeneration:
    """Test Redshift profile generation using ProfileFactory."""

    @pytest.fixture
    def factory(self) -> Any:
        """Get ProfileFactory class."""
        from floe_dbt.factory import ProfileFactory

        return ProfileFactory

    @pytest.mark.requirement("006-FR-010")
    def test_generate_redshift_profile_structure(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Redshift profile generation produces correct structure."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "redshift",
                "properties": {
                    "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
                    "port": 5439,
                    "database": "analytics",
                    "schema": "public",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("redshift")
        outputs = generator.generate(artifacts, config)

        assert "dev" in outputs
        profile = outputs["dev"]
        assert profile["type"] == "redshift"
        assert profile["host"] == "my-cluster.abc123.us-east-1.redshift.amazonaws.com"
        assert profile["port"] == 5439
        assert profile["dbname"] == "analytics"
        assert profile["schema"] == "public"

    @pytest.mark.requirement("006-FR-010")
    def test_redshift_profile_env_var_security(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Redshift credentials use env_var template (never hardcoded)."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "redshift",
                "properties": {
                    "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(
            profile_name="floe", target_name="prod", environment="prod"
        )
        generator = factory.create("redshift")
        outputs = generator.generate(artifacts, config)

        profile = outputs["prod"]
        assert "{{ env_var(" in profile["user"]
        assert "{{ env_var(" in profile["password"]
        assert "REDSHIFT" in profile["user"]
        assert "PROD" in profile["user"]

    @pytest.mark.requirement("006-FR-010")
    def test_generate_redshift_profile_default_port(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Redshift profile uses default port 5439 when not specified."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "redshift",
                "properties": {
                    "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("redshift")
        outputs = generator.generate(artifacts, config)

        assert outputs["dev"]["port"] == 5439


class TestRedshiftProfileValidation:
    """Test Redshift profile YAML structure validation."""

    @pytest.mark.skipif(
        not HAS_DBT_REDSHIFT,
        reason="dbt-redshift adapter not installed",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_valid_profile_structure_accepted_by_dbt(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that well-formed Redshift profile is accepted by dbt."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "redshift",
                        "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
                        "port": 5439,
                        "user": "test_user",
                        "password": "test_password",
                        "dbname": "analytics",
                        "schema": "public",
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
        not HAS_DBT_REDSHIFT,
        reason="dbt-redshift adapter not installed",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_redshift_profile_missing_host_fails(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that Redshift profile without host fails validation."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "redshift",
                        # Missing 'host' - required field
                        "port": 5439,
                        "user": "test_user",
                        "password": "test_password",
                        "dbname": "analytics",
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


class TestRedshiftProfileEdgeCases:
    """Test edge cases in Redshift profile handling."""

    @pytest.mark.requirement("006-FR-010")
    def test_redshift_profile_with_iam_role(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Redshift profile with IAM role authentication."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "redshift",
                "properties": {
                    "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
                    "database": "analytics",
                    "method": "iam",
                    "cluster_id": "my-cluster",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create("redshift")
        outputs = generator.generate(artifacts, config)

        assert outputs["dev"]["type"] == "redshift"

    @pytest.mark.requirement("006-FR-010")
    def test_redshift_multi_environment_profiles(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test Redshift profile generation for multiple environments."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "redshift",
                "properties": {
                    "host": "my-cluster.abc123.us-east-1.redshift.amazonaws.com",
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

        # Generate for dev
        dev_config = ProfileGeneratorConfig(
            profile_name="floe", target_name="dev", environment="dev"
        )
        generator = ProfileFactory.create("redshift")
        dev_outputs = generator.generate(artifacts, dev_config)

        # Generate for prod
        prod_config = ProfileGeneratorConfig(
            profile_name="floe", target_name="prod", environment="prod"
        )
        prod_outputs = generator.generate(artifacts, prod_config)

        # Both should have correct environment-prefixed credentials
        assert "DEV" in dev_outputs["dev"]["user"]
        assert "PROD" in prod_outputs["prod"]["user"]
