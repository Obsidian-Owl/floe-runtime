"""Integration tests for profile validation with dbt debug.

T024: [US2] Integration test for profile validation

These tests verify that generated profiles.yml files are valid
by running `dbt debug` against them.

Requirements:
- dbt-core must be installed
- For target-specific tests, the appropriate adapter must be installed
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

# Skip all integration tests if dbt not available
pytestmark = pytest.mark.skipif(
    subprocess.run(["dbt", "--version"], capture_output=True).returncode != 0,
    reason="dbt-core not installed",
)


@pytest.fixture
def dbt_project_dir(tmp_path: Path) -> Path:
    """Create minimal dbt project for validation testing."""
    project_dir = tmp_path / "dbt_project"
    project_dir.mkdir()

    # Create minimal dbt_project.yml
    dbt_project = {
        "name": "test_project",
        "version": "1.0.0",
        "config-version": 2,
        "profile": "floe",
    }
    (project_dir / "dbt_project.yml").write_text(yaml.safe_dump(dbt_project))

    # Create models directory
    models_dir = project_dir / "models"
    models_dir.mkdir()

    return project_dir


@pytest.fixture
def profiles_dir(tmp_path: Path) -> Path:
    """Create profiles directory."""
    profiles_path = tmp_path / "profiles"
    profiles_path.mkdir()
    return profiles_path


class TestDuckDBProfileValidation:
    """Test DuckDB profile validation with dbt debug."""

    @pytest.fixture
    def duckdb_profile(self, profiles_dir: Path) -> Path:
        """Generate DuckDB profile for testing."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "duckdb",
                        "path": ":memory:",
                        "threads": 4,
                    }
                },
            }
        }
        profiles_path = profiles_dir / "profiles.yml"
        profiles_path.write_text(yaml.safe_dump(profile))
        return profiles_path

    @pytest.mark.skipif(
        subprocess.run(
            ["python", "-c", "import dbt.adapters.duckdb"], capture_output=True
        ).returncode
        != 0,
        reason="dbt-duckdb adapter not installed",
    )
    def test_dbt_debug_succeeds(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
        duckdb_profile: Path,
    ) -> None:
        """Test that dbt debug succeeds with generated DuckDB profile."""
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

        # dbt debug should succeed
        assert result.returncode == 0, f"dbt debug failed: {result.stderr}"
        assert "Connection test: OK" in result.stdout or "All checks passed" in result.stdout


class TestProfileValidationWithFactory:
    """Test profile validation using ProfileFactory."""

    @pytest.fixture
    def factory(self) -> Any:
        """Get ProfileFactory class."""
        from floe_dbt.factory import ProfileFactory

        return ProfileFactory

    @pytest.fixture
    def writer(self) -> Any:
        """Get ProfileWriter instance."""
        from floe_dbt.writer import ProfileWriter

        return ProfileWriter()

    @pytest.mark.skipif(
        subprocess.run(
            ["python", "-c", "import dbt.adapters.duckdb"], capture_output=True
        ).returncode
        != 0,
        reason="dbt-duckdb adapter not installed",
    )
    def test_generated_duckdb_profile_validates(
        self,
        factory: Any,
        writer: Any,
        dbt_project_dir: Path,
        profiles_dir: Path,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test end-to-end: generate DuckDB profile and validate with dbt."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        # Create artifacts
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "duckdb",
                "properties": {"path": ":memory:"},
            },
            "transforms": [],
        }

        # Generate profile
        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("duckdb")
        outputs = generator.generate(artifacts, config)

        # Build full profile structure
        profile = {
            config.profile_name: {
                "target": config.target_name,
                "outputs": outputs,
            }
        }

        # Write profile
        profiles_path = profiles_dir / "profiles.yml"
        writer.write(profile, profiles_path)

        # Validate with dbt debug
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

        assert result.returncode == 0, f"dbt debug failed: {result.stderr}"


class TestProfileValidationEdgeCases:
    """Test edge cases in profile validation."""

    def test_invalid_profile_structure_fails(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that invalid profile structure causes dbt debug to fail."""
        # Create intentionally invalid profile (missing required fields)
        invalid_profile = {
            "floe": {
                "target": "dev",
                # Missing 'outputs' key
            }
        }
        profiles_path = profiles_dir / "profiles.yml"
        profiles_path.write_text(yaml.safe_dump(invalid_profile))

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

        # dbt debug should fail for invalid profile
        assert result.returncode != 0

    def test_missing_profile_fails(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that missing profile file causes dbt debug to fail."""
        # Don't create profiles.yml

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

        # dbt debug should fail when profiles.yml is missing
        assert result.returncode != 0
