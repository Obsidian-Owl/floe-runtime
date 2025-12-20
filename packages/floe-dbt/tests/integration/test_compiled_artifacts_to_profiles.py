"""Integration tests for CompiledArtifacts → profiles.yml contract.

T085: FR-033 - CompiledArtifacts generates valid dbt profiles

These tests verify the contract boundary between floe-core's CompiledArtifacts
and floe-dbt's profile generation. The CompiledArtifacts.compute config must
produce valid profiles.yml files that dbt can parse and use.

Requirements:
- dbt-core must be installed
- Tests FAIL if infrastructure is missing (never skip)

Covers:
- FR-033: Integration tests MUST verify CompiledArtifacts output is parseable
          by floe-dbt profile generators
"""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

import pytest
import yaml

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def _check_dbt_available() -> None:
    """Check that dbt-core is available. FAIL if not (never skip)."""
    try:
        import dbt.version  # noqa: F401
    except ImportError:
        pytest.fail(
            "dbt-core not installed. "
            "Install with: pip install dbt-core dbt-duckdb. "
            "Tests FAIL when dependencies are missing (never skip)."
        )


class TestCompiledArtifactsToProfiles:
    """Test CompiledArtifacts → profiles.yml contract.

    Covers: FR-033 (CompiledArtifacts to dbt profiles contract)
    """

    @pytest.fixture(autouse=True)
    def check_dependencies(self) -> None:
        """Ensure dbt is available before running tests."""
        _check_dbt_available()

    @pytest.fixture
    def dbt_project_dir(self, tmp_path: Path) -> Path:
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

        # Create models directory (required by dbt)
        models_dir = project_dir / "models"
        models_dir.mkdir()

        return project_dir

    @pytest.fixture
    def profiles_dir(self, tmp_path: Path) -> Path:
        """Create profiles directory."""
        profiles_path = tmp_path / "profiles"
        profiles_path.mkdir()
        return profiles_path

    @pytest.mark.requirement("006-FR-033")
    @pytest.mark.requirement("003-FR-001")
    def test_artifacts_generate_valid_profiles_yml(
        self,
        minimal_compiled_artifacts: dict[str, Any],
        profiles_dir: Path,
    ) -> None:
        """CompiledArtifacts compute config generates valid profiles.yml.

        Verifies that the contract between CompiledArtifacts and ProfileFactory
        produces structurally valid YAML that follows dbt's expected format.

        Covers:
        - 003-FR-001: Generate valid dbt profiles.yml from CompiledArtifacts
        """
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig
        from floe_dbt.writer import ProfileWriter

        # Extract compute config from artifacts (contract boundary)
        compute = minimal_compiled_artifacts["compute"]
        target = compute["target"]

        # Generate profile using factory (consuming the contract)
        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create(target)
        outputs = generator.generate(minimal_compiled_artifacts, config)

        # Build full profile structure
        profile = {
            config.profile_name: {
                "target": config.target_name,
                "outputs": outputs,
            }
        }

        # Write to profiles.yml
        writer = ProfileWriter()
        profiles_path = profiles_dir / "profiles.yml"
        writer.write(profile, profiles_path)

        # Verify file was created and is valid YAML
        assert profiles_path.exists(), "profiles.yml not created"
        content = profiles_path.read_text()

        # Parse back to verify structure
        parsed = yaml.safe_load(content)
        assert "floe" in parsed, "Profile name 'floe' not in output"
        assert "target" in parsed["floe"], "Target not specified"
        assert "outputs" in parsed["floe"], "Outputs section missing"
        assert "dev" in parsed["floe"]["outputs"], "Target 'dev' not in outputs"

    @pytest.mark.requirement("006-FR-033")
    @pytest.mark.requirement("003-FR-001")
    @pytest.mark.requirement("003-FR-005")
    def test_profiles_yml_parseable_by_dbt(
        self,
        minimal_compiled_artifacts: dict[str, Any],
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Generated profiles.yml passes dbt debug validation.

        This is the ultimate contract test: dbt itself can parse and use
        the generated profile.

        Covers:
        - 003-FR-001: Generate valid dbt profiles.yml from CompiledArtifacts
        - 003-FR-005: Write profiles to the specified path
        """
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig
        from floe_dbt.writer import ProfileWriter

        # Generate profile from CompiledArtifacts
        compute = minimal_compiled_artifacts["compute"]
        target = compute["target"]

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create(target)
        outputs = generator.generate(minimal_compiled_artifacts, config)

        profile = {
            config.profile_name: {
                "target": config.target_name,
                "outputs": outputs,
            }
        }

        writer = ProfileWriter()
        profiles_path = profiles_dir / "profiles.yml"
        writer.write(profile, profiles_path)

        # Run dbt debug to validate
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

        assert result.returncode == 0, (
            f"dbt debug failed with generated profile.\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.requirement("006-FR-033")
    @pytest.mark.requirement("003-FR-004")
    def test_target_configs_resolve_correctly(
        self,
        minimal_compiled_artifacts: dict[str, Any],
    ) -> None:
        """Target-specific properties from artifacts appear in generated profile.

        Verifies that compute.properties from CompiledArtifacts are correctly
        propagated to the generated profile output.

        Covers:
        - 003-FR-004: Allow properties override via FloeSpec compute.properties
        """
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        # Extract compute config
        compute = minimal_compiled_artifacts["compute"]
        target = compute["target"]
        properties = compute.get("properties", {})

        # Generate profile
        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create(target)
        outputs = generator.generate(minimal_compiled_artifacts, config)

        # Verify target-specific properties appear in output
        # For DuckDB, 'path' should be preserved
        if target == "duckdb":
            assert "dev" in outputs
            dev_config = outputs["dev"]
            assert dev_config["type"] == "duckdb"
            assert dev_config["path"] == properties.get("path", ":memory:")

    @pytest.mark.requirement("006-FR-033")
    @pytest.mark.requirement("003-FR-002")
    def test_all_supported_targets_generate_profiles(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """All supported compute targets can generate profiles from artifacts.

        Verifies that the contract supports all 7 compute targets defined
        in CompiledArtifacts.compute.target.

        Covers:
        - 003-FR-002: Support all 7 compute targets
        """
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        # Test all supported targets
        target_configs = {
            "duckdb": {"path": ":memory:"},
            "postgres": {"host": "localhost", "port": 5432, "database": "test"},
            "snowflake": {
                "account": "test.us-east-1",
                "warehouse": "WH",
                "database": "DB",
            },
            "bigquery": {"project": "my-project", "dataset": "analytics"},
            "redshift": {"host": "cluster.redshift.amazonaws.com", "database": "db"},
            "databricks": {
                "host": "workspace.databricks.net",
                "http_path": "/sql/1.0/warehouses/abc",
            },
            "spark": {"host": "spark://master:7077", "method": "thrift"},
        }

        for target, properties in target_configs.items():
            # Build CompiledArtifacts-style dict
            artifacts = {
                "version": "1.0.0",
                "metadata": base_metadata,
                "compute": {"target": target, "properties": properties},
                "transforms": [],
            }

            # Generate profile
            config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
            generator = ProfileFactory.create(target)
            outputs = generator.generate(artifacts, config)

            # Verify output structure
            assert "dev" in outputs, f"Target '{target}' did not generate 'dev' output"
            assert outputs["dev"]["type"] == target, f"Target type mismatch for {target}"


class TestCompiledArtifactsContractVersioning:
    """Test contract versioning between CompiledArtifacts and profile generation.

    Covers: FR-033 (contract stability)
    """

    @pytest.fixture(autouse=True)
    def check_dependencies(self) -> None:
        """Ensure dbt is available before running tests."""
        _check_dbt_available()

    @pytest.mark.requirement("006-FR-033")
    @pytest.mark.requirement("003-FR-001")
    def test_v1_artifacts_structure_supported(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """v1.0.0 CompiledArtifacts structure generates valid profiles.

        Ensures backward compatibility with the original contract version.

        Covers:
        - 003-FR-001: Generate valid dbt profiles.yml from CompiledArtifacts
        """
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        # v1.0.0 minimal structure
        artifacts_v1 = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "duckdb",
                "properties": {"path": ":memory:"},
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create("duckdb")
        outputs = generator.generate(artifacts_v1, config)

        assert "dev" in outputs
        assert outputs["dev"]["type"] == "duckdb"

    @pytest.mark.requirement("006-FR-033")
    @pytest.mark.requirement("003-FR-003")
    def test_optional_fields_handled_gracefully(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Profile generation handles optional CompiledArtifacts fields.

        Optional fields like connection_secret_ref should not break generation.

        Covers:
        - 003-FR-003: Use environment variable references for credentials
        """
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        # Artifacts with optional fields set to None
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "duckdb",
                "connection_secret_ref": None,  # Optional, can be None
                "properties": {"path": ":memory:"},
            },
            "transforms": [],
            "catalog": None,  # Optional
            "lineage_namespace": None,  # Optional
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = ProfileFactory.create("duckdb")

        # Should not raise despite None values
        outputs = generator.generate(artifacts, config)
        assert "dev" in outputs
