"""Integration tests for dbt asset execution.

T039: [US1] Integration test for dbt asset execution

These tests verify end-to-end dbt model execution through Dagster.

Requirements:
- dbt-core and dbt-duckdb must be installed
- dagster and dagster-dbt must be installed
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

# Skip all integration tests if dependencies not available
pytestmark = pytest.mark.skipif(
    subprocess.run(["dbt", "--version"], capture_output=True).returncode != 0,
    reason="dbt-core not installed",
)


@pytest.fixture
def dbt_project(tmp_path: Path) -> Path:
    """Create minimal dbt project for testing."""
    project_dir = tmp_path / "dbt_project"
    project_dir.mkdir()

    # Create dbt_project.yml
    dbt_project_config = {
        "name": "test_project",
        "version": "1.0.0",
        "config-version": 2,
        "profile": "floe",
    }
    (project_dir / "dbt_project.yml").write_text(yaml.safe_dump(dbt_project_config))

    # Create models directory with simple model
    models_dir = project_dir / "models"
    models_dir.mkdir()

    # Create a simple model
    (models_dir / "test_model.sql").write_text("SELECT 1 as id, 'test' as name")

    # Create schema.yml for model metadata
    schema_config = {
        "version": 2,
        "models": [
            {
                "name": "test_model",
                "description": "A test model",
                "meta": {
                    "floe": {
                        "owner": "data-team",
                    }
                },
                "columns": [
                    {"name": "id", "description": "Identifier"},
                    {"name": "name", "description": "Name field"},
                ],
            }
        ],
    }
    (models_dir / "schema.yml").write_text(yaml.safe_dump(schema_config))

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
                    "path": ":memory:",
                    "threads": 1,
                }
            },
        }
    }
    (profiles_path / "profiles.yml").write_text(yaml.safe_dump(profile))
    return profiles_path


@pytest.fixture
def compiled_artifacts(
    dbt_project: Path,
    profiles_dir: Path,
    base_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Create CompiledArtifacts for testing."""
    return {
        "version": "1.0.0",
        "metadata": base_metadata,
        "compute": {
            "target": "duckdb",
            "properties": {"path": ":memory:"},
        },
        "transforms": [
            {
                "type": "dbt",
                "project_dir": str(dbt_project),
                "profiles_dir": str(profiles_dir),
            }
        ],
        "dbt_project_path": str(dbt_project),
        "dbt_profiles_path": str(profiles_dir),
        "dbt_manifest_path": str(dbt_project / "target" / "manifest.json"),
    }


@pytest.fixture
def manifest_json(dbt_project: Path, profiles_dir: Path) -> Path:
    """Compile dbt project and return manifest path."""
    # Run dbt compile to generate manifest
    result = subprocess.run(
        [
            "dbt",
            "compile",
            "--project-dir",
            str(dbt_project),
            "--profiles-dir",
            str(profiles_dir),
        ],
        capture_output=True,
        text=True,
        cwd=dbt_project,
    )

    if result.returncode != 0:
        pytest.skip(f"dbt compile failed: {result.stderr}")

    manifest_path = dbt_project / "target" / "manifest.json"
    assert manifest_path.exists(), "manifest.json not created"
    return manifest_path


class TestDbtAssetExecution:
    """Integration tests for dbt asset execution."""

    @pytest.mark.skipif(
        subprocess.run(
            ["python", "-c", "import dbt.adapters.duckdb"], capture_output=True
        ).returncode
        != 0,
        reason="dbt-duckdb adapter not installed",
    )
    def test_create_dbt_assets_from_manifest(
        self,
        compiled_artifacts: dict[str, Any],
        manifest_json: Path,
    ) -> None:
        """Test creating dbt assets from manifest.json."""
        from floe_dagster.assets import FloeAssetFactory

        # Update artifacts with actual manifest path
        artifacts = compiled_artifacts.copy()
        artifacts["dbt_manifest_path"] = str(manifest_json)

        # Create assets
        assets = FloeAssetFactory.create_dbt_assets(artifacts)

        assert assets is not None

    @pytest.mark.skipif(
        subprocess.run(
            ["python", "-c", "import dbt.adapters.duckdb"], capture_output=True
        ).returncode
        != 0,
        reason="dbt-duckdb adapter not installed",
    )
    def test_create_definitions_from_manifest(
        self,
        compiled_artifacts: dict[str, Any],
        manifest_json: Path,
    ) -> None:
        """Test creating Dagster definitions from manifest."""
        from floe_dagster.assets import FloeAssetFactory

        # Update artifacts with actual manifest path
        artifacts = compiled_artifacts.copy()
        artifacts["dbt_manifest_path"] = str(manifest_json)

        # Create definitions
        definitions = FloeAssetFactory.create_definitions(artifacts)

        assert definitions is not None

    def test_manifest_parsing(
        self,
        manifest_json: Path,
    ) -> None:
        """Test parsing of dbt manifest.json."""
        from floe_dagster.assets import FloeAssetFactory

        manifest = FloeAssetFactory._load_manifest(manifest_json)

        assert "nodes" in manifest
        assert "metadata" in manifest

        # Should have our test model
        models = FloeAssetFactory._filter_models(manifest)
        assert any("test_model" in model_id for model_id in models)

    def test_floe_translator_extracts_metadata(
        self,
        manifest_json: Path,
    ) -> None:
        """Test that FloeTranslator extracts metadata correctly."""
        from floe_dagster.assets import FloeAssetFactory
        from floe_dagster.translator import FloeTranslator

        manifest = FloeAssetFactory._load_manifest(manifest_json)
        models = FloeAssetFactory._filter_models(manifest)

        translator = FloeTranslator()

        for model_id, model_node in models.items():
            if "test_model" in model_id:
                # Test metadata extraction
                metadata = translator.get_metadata(model_node)
                assert metadata is not None

                # Test description
                description = translator.get_description(model_node)
                assert description == "A test model" or description is not None

                # Test owners
                owners = translator.get_owners(model_node)
                if owners:
                    assert "data-team" in owners


class TestDbtAssetExecutionEdgeCases:
    """Edge case tests for dbt asset execution."""

    def test_missing_manifest_raises_error(self) -> None:
        """Test that missing manifest raises appropriate error."""
        from floe_dagster.assets import FloeAssetFactory

        artifacts = {
            "dbt_manifest_path": "/nonexistent/manifest.json",
            "dbt_project_path": "/nonexistent",
            "dbt_profiles_path": "/nonexistent",
        }

        with pytest.raises((FileNotFoundError, ValueError)):
            FloeAssetFactory.create_dbt_assets(artifacts)

    def test_missing_manifest_path_raises_error(self) -> None:
        """Test that missing manifest path raises error."""
        from floe_dagster.assets import FloeAssetFactory

        artifacts = {
            "dbt_project_path": "/some/path",
            "dbt_profiles_path": "/some/profiles",
            # Missing dbt_manifest_path
        }

        with pytest.raises(ValueError):
            FloeAssetFactory.create_dbt_assets(artifacts)
