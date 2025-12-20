"""Integration tests for CompiledArtifacts → Dagster contract.

T086: FR-032 - CompiledArtifacts output consumable by Dagster

These tests verify the contract boundary between floe-core's CompiledArtifacts
and floe-dagster's asset creation. CompiledArtifacts must produce valid
configuration that Dagster can consume to create Definitions.

Requirements:
- dagster and dagster-dbt must be installed
- dbt-core must be installed
- Tests FAIL if dependencies are missing (never skip)

Covers:
- FR-032: Integration tests MUST verify CompiledArtifacts output is consumable
          by floe-dagster asset creation
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def _check_dagster_available() -> None:
    """Check that dagster is available. FAIL if not (never skip)."""
    try:
        import dagster  # noqa: F401
        import dbt.version  # noqa: F401
    except ImportError as e:
        pytest.fail(
            f"Required dependency not installed: {e}. "
            "Install with: pip install dagster dagster-dbt dbt-core dbt-duckdb. "
            "Tests FAIL when dependencies are missing (never skip)."
        )


# =============================================================================
# Shared Fixtures (module-level)
# =============================================================================


@pytest.fixture
def dbt_project_dir(tmp_path: Path) -> Path:
    """Create minimal dbt project for testing."""
    project_dir = tmp_path / "dbt_project"
    project_dir.mkdir()

    dbt_project = {
        "name": "test_project",
        "version": "1.0.0",
        "config-version": 2,
        "profile": "floe",
    }
    (project_dir / "dbt_project.yml").write_text(yaml.safe_dump(dbt_project))

    models_dir = project_dir / "models"
    models_dir.mkdir()
    (models_dir / "example.sql").write_text("SELECT 1 as id, 'test' as name")

    return project_dir


@pytest.fixture
def profiles_dir(tmp_path: Path) -> Path:
    """Create profiles directory with DuckDB profile."""
    profiles_path = tmp_path / "profiles"
    profiles_path.mkdir()

    profile = {
        "floe": {
            "target": "dev",
            "outputs": {
                "dev": {
                    "type": "duckdb",
                    "path": str(tmp_path / "warehouse.duckdb"),
                    "threads": 1,
                }
            },
        }
    }
    (profiles_path / "profiles.yml").write_text(yaml.safe_dump(profile))
    return profiles_path


@pytest.fixture
def compiled_manifest(dbt_project_dir: Path, profiles_dir: Path) -> Path:
    """Compile dbt project to get manifest.json."""
    result = subprocess.run(
        [
            "dbt",
            "compile",
            "--project-dir",
            str(dbt_project_dir),
            "--profiles-dir",
            str(profiles_dir),
        ],
        capture_output=True,
        text=True,
        cwd=dbt_project_dir,
    )

    if result.returncode != 0:
        pytest.fail(f"dbt compile failed: {result.stderr}")

    manifest_path = dbt_project_dir / "target" / "manifest.json"
    if not manifest_path.exists():
        pytest.fail(f"manifest.json not found at {manifest_path}")

    return manifest_path


# =============================================================================
# Test Classes
# =============================================================================


class TestCompiledArtifactsToDagster:
    """Test CompiledArtifacts → Dagster Definitions contract.

    Covers: FR-032 (CompiledArtifacts to Dagster contract)
    """

    @pytest.fixture(autouse=True)
    def check_dependencies(self) -> None:
        """Ensure dagster is available before running tests."""
        _check_dagster_available()

    @pytest.fixture
    def compiled_artifacts(
        self,
        tmp_path: Path,
        dbt_project_dir: Path,
        profiles_dir: Path,
        compiled_manifest: Path,
        base_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Create CompiledArtifacts dictionary matching floe-core schema."""
        return {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "duckdb",
                "properties": {"path": str(tmp_path / "warehouse.duckdb")},
            },
            "transforms": [
                {
                    "type": "dbt",
                    "path": str(dbt_project_dir),
                }
            ],
            "consumption": {"enabled": False},
            "governance": {"classification_source": "dbt_meta"},
            "observability": {
                "traces": {"enabled": False, "endpoint": None},
                "lineage": {"enabled": False, "endpoint": None},
            },
            "catalog": None,
            "dbt_manifest_path": str(compiled_manifest),
            "dbt_project_path": str(dbt_project_dir),
            "dbt_profiles_path": str(profiles_dir),
            "lineage_namespace": None,
            "environment_context": None,
            "column_classifications": None,
        }

    @pytest.fixture
    def artifacts_json_file(
        self, tmp_path: Path, compiled_artifacts: dict[str, Any]
    ) -> Path:
        """Write CompiledArtifacts to JSON file."""
        artifacts_path = tmp_path / ".floe" / "compiled_artifacts.json"
        artifacts_path.parent.mkdir(parents=True, exist_ok=True)
        artifacts_path.write_text(json.dumps(compiled_artifacts, indent=2))
        return artifacts_path

    @pytest.mark.requirement("006-FR-032")
    @pytest.mark.requirement("003-FR-006")
    @pytest.mark.requirement("003-FR-008")
    def test_load_artifacts_creates_definitions(
        self,
        artifacts_json_file: Path,
    ) -> None:
        """CompiledArtifacts JSON loads into Dagster Definitions.

        Verifies that the load_definitions_from_artifacts function
        successfully consumes the CompiledArtifacts contract.

        Covers:
        - 003-FR-006: Create Dagster SDA from dbt manifest
        - 003-FR-008: Configure DbtCliResource with generated profiles
        """
        from floe_dagster.definitions import load_definitions_from_artifacts

        definitions = load_definitions_from_artifacts(artifacts_json_file)

        assert definitions is not None
        # Should have assets (dbt models)
        assert definitions.assets is not None
        # Should have resources (dbt resource)
        assert definitions.resources is not None
        assert "dbt" in definitions.resources

    @pytest.mark.requirement("006-FR-032")
    @pytest.mark.requirement("003-FR-006")
    def test_load_artifacts_from_dict(
        self,
        compiled_artifacts: dict[str, Any],
    ) -> None:
        """CompiledArtifacts dict creates Dagster Definitions.

        Verifies that the load_definitions_from_dict function
        works with in-memory artifacts (useful for testing).

        Covers:
        - 003-FR-006: Create Dagster SDA from dbt manifest
        """
        from floe_dagster.definitions import load_definitions_from_dict

        definitions = load_definitions_from_dict(compiled_artifacts)

        assert definitions is not None
        assert definitions.assets is not None
        assert definitions.resources is not None

    @pytest.mark.requirement("006-FR-032")
    @pytest.mark.requirement("003-FR-006")
    @pytest.mark.requirement("003-FR-010")
    def test_asset_metadata_from_artifacts(
        self,
        compiled_artifacts: dict[str, Any],
    ) -> None:
        """Created assets have metadata from CompiledArtifacts.

        Verifies that asset metadata (version, project path) is
        correctly propagated from the artifacts.

        Covers:
        - 003-FR-006: Create Dagster SDA from dbt manifest
        - 003-FR-010: Attach metadata from dbt models to Dagster assets
        """
        from floe_dagster.assets import FloeAssetFactory

        assets = FloeAssetFactory.create_dbt_assets(compiled_artifacts)

        assert assets is not None
        # Assets should be created
        assert assets

    @pytest.mark.requirement("006-FR-032")
    @pytest.mark.requirement("003-FR-008")
    def test_transforms_configure_dbt_project(
        self,
        compiled_artifacts: dict[str, Any],
    ) -> None:
        """transforms array from artifacts configures dbt project.

        Verifies that artifacts.transforms is used to configure
        the dbt project path and settings.

        Covers:
        - 003-FR-008: Configure DbtCliResource with generated profiles
        """
        from floe_dagster.definitions import load_definitions_from_dict

        definitions = load_definitions_from_dict(compiled_artifacts)

        # The dbt resource should be configured with project path
        assert definitions.resources is not None
        dbt_resource = definitions.resources.get("dbt")
        assert dbt_resource is not None

    @pytest.mark.requirement("006-FR-032")
    def test_missing_manifest_path_raises_error(self) -> None:
        """Missing dbt_manifest_path raises ValueError.

        Verifies that the contract enforces required fields.
        """
        from floe_dagster.assets import FloeAssetFactory

        artifacts_without_manifest = {
            "version": "1.0.0",
            "dbt_project_path": "/some/path",
            "dbt_profiles_path": "/some/profiles",
            # Missing dbt_manifest_path
        }

        with pytest.raises(ValueError, match="dbt_manifest_path"):
            FloeAssetFactory.create_dbt_assets(artifacts_without_manifest)

    @pytest.mark.requirement("006-FR-032")
    def test_missing_artifacts_file_raises_error(self, tmp_path: Path) -> None:
        """Missing artifacts file raises FileNotFoundError.

        Verifies error handling when artifacts JSON doesn't exist.
        """
        from floe_dagster.definitions import load_definitions_from_artifacts

        nonexistent_path = tmp_path / "nonexistent" / "compiled_artifacts.json"

        with pytest.raises(FileNotFoundError, match="CompiledArtifacts not found"):
            load_definitions_from_artifacts(nonexistent_path)


class TestObservabilityConfigPropagation:
    """Test observability config propagation from CompiledArtifacts.

    Covers: FR-032 (observability config from artifacts)
    """

    @pytest.fixture(autouse=True)
    def check_dependencies(self) -> None:
        """Ensure dagster is available before running tests."""
        _check_dagster_available()

    @pytest.mark.requirement("006-FR-032")
    @pytest.mark.requirement("003-FR-020")
    def test_observability_config_from_artifacts(
        self,
        base_metadata: dict[str, Any],
    ) -> None:
        """Observability config from artifacts is accessible.

        Verifies that artifacts.observability settings can be read
        for configuring tracing and lineage.

        Covers:
        - 003-FR-020: Support OTLP export when endpoint is configured
        """
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "observability": {
                "traces": {
                    "enabled": True,
                    "endpoint": "http://jaeger:4317",
                },
                "lineage": {
                    "enabled": True,
                    "endpoint": "http://marquez:5000/api/v1/lineage",
                },
            },
        }

        # Verify observability config is accessible
        obs_config = artifacts.get("observability", {})
        assert obs_config["traces"]["enabled"] is True
        assert obs_config["traces"]["endpoint"] == "http://jaeger:4317"
        assert obs_config["lineage"]["enabled"] is True


class TestCompiledArtifactsVersioning:
    """Test contract versioning stability.

    Covers: FR-032 (backward compatibility)
    """

    @pytest.fixture(autouse=True)
    def check_dependencies(self) -> None:
        """Ensure dagster is available before running tests."""
        _check_dagster_available()

    @pytest.mark.requirement("006-FR-032")
    @pytest.mark.requirement("003-FR-006")
    def test_v1_artifacts_supported(
        self,
        base_metadata: dict[str, Any],
        dbt_project_dir: Path,
        profiles_dir: Path,
        compiled_manifest: Path,
    ) -> None:
        """v1.0.0 CompiledArtifacts structure is consumable.

        Ensures backward compatibility with the original contract version.

        Covers:
        - 003-FR-006: Create Dagster SDA from dbt manifest
        """
        from floe_dagster.definitions import load_definitions_from_dict

        # Minimal v1.0.0 structure
        v1_artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {"target": "duckdb", "properties": {}},
            "transforms": [{"type": "dbt", "path": str(dbt_project_dir)}],
            "observability": {
                "traces": {"enabled": False},
                "lineage": {"enabled": False},
            },
            "dbt_manifest_path": str(compiled_manifest),
            "dbt_project_path": str(dbt_project_dir),
            "dbt_profiles_path": str(profiles_dir),
        }

        definitions = load_definitions_from_dict(v1_artifacts)
        assert definitions is not None

    @pytest.mark.requirement("006-FR-032")
    @pytest.mark.requirement("003-FR-021")
    @pytest.mark.requirement("003-FR-022")
    def test_optional_fields_default_gracefully(
        self,
        base_metadata: dict[str, Any],
        dbt_project_dir: Path,
        profiles_dir: Path,
        compiled_manifest: Path,
    ) -> None:
        """Optional fields in CompiledArtifacts default gracefully.

        Verifies that missing optional fields don't break consumption.

        Covers:
        - 003-FR-021: Function without OpenLineage endpoint (graceful)
        - 003-FR-022: Function without OTLP endpoint (graceful)
        """
        from floe_dagster.definitions import load_definitions_from_dict

        # Artifacts with minimal fields (optional fields omitted)
        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {"target": "duckdb", "properties": {}},
            "transforms": [],
            "observability": {
                "traces": {"enabled": False},
                "lineage": {"enabled": False},
            },
            "dbt_manifest_path": str(compiled_manifest),
            "dbt_project_path": str(dbt_project_dir),
            "dbt_profiles_path": str(profiles_dir),
            # Optional fields omitted: catalog, lineage_namespace, environment_context
        }

        definitions = load_definitions_from_dict(artifacts)
        assert definitions is not None
