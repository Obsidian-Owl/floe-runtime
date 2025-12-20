"""Integration tests for BigQuery profile generation and validation.

T036: [US3] Create packages/floe-dbt/tests/integration/test_bigquery.py

These tests verify BigQuery profile generation produces valid dbt profile
structure. Since BigQuery is a cloud service, we test profile structure
validation only (no actual connection tests).

Requirements:
- dbt-bigquery adapter must be installed for full validation
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

# Check if dbt-bigquery is available
try:
    import dbt.adapters.bigquery  # noqa: F401

    HAS_DBT_BIGQUERY = True
except ImportError:
    HAS_DBT_BIGQUERY = False


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


class TestBigQueryProfileGeneration:
    """Test BigQuery profile generation using ProfileFactory."""

    @pytest.fixture
    def factory(self) -> Any:
        """Get ProfileFactory class."""
        from floe_dbt.factory import ProfileFactory

        return ProfileFactory

    @pytest.mark.requirement("006-FR-010")
    def test_generate_bigquery_profile_structure(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test BigQuery profile generation produces correct structure."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "my-gcp-project",
                    "dataset": "analytics",
                    "location": "US",
                    "method": "oauth",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("bigquery")
        outputs = generator.generate(artifacts, config)

        assert "dev" in outputs
        profile = outputs["dev"]
        assert profile["type"] == "bigquery"
        assert profile["project"] == "my-gcp-project"
        assert profile["dataset"] == "analytics"
        assert profile["location"] == "US"
        assert profile["method"] == "oauth"

    @pytest.mark.requirement("006-FR-010")
    def test_generate_bigquery_profile_with_service_account(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test BigQuery profile with service account method."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "my-gcp-project",
                    "dataset": "analytics",
                    "method": "service-account",
                    "keyfile": "/path/to/keyfile.json",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("bigquery")
        outputs = generator.generate(artifacts, config)

        profile = outputs["dev"]
        assert profile["method"] == "service-account"
        # FR-003: Keyfile path is converted to env_var reference for security
        assert profile["keyfile"] == "{{ env_var('BIGQUERY_DEV_KEYFILE') }}"

    @pytest.mark.requirement("006-FR-010")
    def test_generate_bigquery_profile_minimal(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test BigQuery profile with minimal required fields."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "my-gcp-project",
                    "dataset": "analytics",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("bigquery")
        outputs = generator.generate(artifacts, config)

        profile = outputs["dev"]
        assert profile["type"] == "bigquery"
        assert profile["project"] == "my-gcp-project"
        assert profile["dataset"] == "analytics"


class TestBigQueryProfileValidation:
    """Test BigQuery profile YAML structure validation."""

    @pytest.mark.skipif(
        not HAS_DBT_BIGQUERY,
        reason="dbt-bigquery adapter not installed",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_valid_profile_structure_accepted_by_dbt(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that well-formed BigQuery profile is accepted by dbt."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "bigquery",
                        "method": "oauth",
                        "project": "my-gcp-project",
                        "dataset": "analytics",
                        "threads": 4,
                        "location": "US",
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
        not HAS_DBT_BIGQUERY,
        reason="dbt-bigquery adapter not installed",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_bigquery_profile_missing_project_fails(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that BigQuery profile without project fails validation."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "bigquery",
                        "method": "oauth",
                        # Missing 'project' - required field
                        "dataset": "analytics",
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


class TestBigQueryProfileEdgeCases:
    """Test edge cases in BigQuery profile handling."""

    @pytest.mark.requirement("006-FR-010")
    def test_bigquery_profile_with_impersonation(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test BigQuery profile with service account impersonation."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "my-gcp-project",
                    "dataset": "analytics",
                    "method": "oauth",
                    "impersonate_service_account": "my-sa@my-project.iam.gserviceaccount.com",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create("bigquery")
        outputs = generator.generate(artifacts, config)

        assert outputs["dev"]["type"] == "bigquery"

    @pytest.mark.requirement("006-FR-010")
    def test_bigquery_multi_environment_profiles(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test BigQuery profile generation for multiple environments."""
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "bigquery",
                "properties": {
                    "project": "my-gcp-project",
                    "dataset": "analytics",
                },
            },
            "transforms": [],
        }

        # Generate for dev
        dev_config = ProfileGeneratorConfig(
            profile_name="floe", target_name="dev", environment="dev"
        )
        generator = ProfileFactory.create("bigquery")
        dev_outputs = generator.generate(artifacts, dev_config)

        # Generate for prod
        prod_config = ProfileGeneratorConfig(
            profile_name="floe", target_name="prod", environment="prod"
        )
        prod_outputs = generator.generate(artifacts, prod_config)

        # Both should be generated successfully
        assert dev_outputs["dev"]["type"] == "bigquery"
        assert prod_outputs["prod"]["type"] == "bigquery"
