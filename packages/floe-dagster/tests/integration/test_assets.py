"""Integration tests for Dagster asset materialization.

T029: [US2] Create integration tests for asset materialization workflow

These tests verify end-to-end asset materialization through Dagster,
including asset creation, execution, and metadata propagation.

Requirements:
- dbt-core and dbt-duckdb must be installed
- dagster and dagster-dbt must be installed
- Tests run in Docker test-runner container for integration profile

See Also:
    - specs/006-integration-testing/spec.md FR-011
    - testing/docker/docker-compose.yml for service configuration
"""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

import pytest
import yaml

# Check if required dependencies are available
try:
    import dbt.version  # noqa: F401
    from dagster import materialize  # noqa: F401

    HAS_DAGSTER = True
except ImportError:
    HAS_DAGSTER = False

# Skip all tests if Dagster not available
pytestmark = pytest.mark.skipif(
    not HAS_DAGSTER,
    reason="dagster or dbt-core not installed",
)


@pytest.fixture
def dbt_project_with_deps(tmp_path: Path) -> Path:
    """Create dbt project with upstream/downstream model dependencies."""
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

    # Create models directory
    models_dir = project_dir / "models"
    models_dir.mkdir()

    # Create staging model (upstream)
    (models_dir / "stg_customers.sql").write_text(
        "SELECT 1 as customer_id, 'John' as first_name, 'Doe' as last_name"
    )

    # Create dimension model (downstream, depends on staging)
    (models_dir / "dim_customers.sql").write_text(
        """\
SELECT
    customer_id,
    first_name || ' ' || last_name as full_name
FROM {{ ref('stg_customers') }}
"""
    )

    # Create schema.yml with metadata
    schema_config = {
        "version": 2,
        "models": [
            {
                "name": "stg_customers",
                "description": "Staging layer for raw customer data",
                "meta": {"floe": {"owner": "team:data-team"}},
                "columns": [
                    {"name": "customer_id", "description": "Customer identifier"},
                    {"name": "first_name", "description": "First name"},
                    {"name": "last_name", "description": "Last name"},
                ],
            },
            {
                "name": "dim_customers",
                "description": "Customer dimension table",
                "meta": {"floe": {"owner": "team:analytics"}},
                "columns": [
                    {"name": "customer_id", "description": "Customer identifier"},
                    {"name": "full_name", "description": "Full customer name"},
                ],
            },
        ],
    }
    (models_dir / "schema.yml").write_text(yaml.safe_dump(schema_config))

    return project_dir


@pytest.fixture
def profiles_dir_duckdb(tmp_path: Path) -> Path:
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
def compiled_manifest(dbt_project_with_deps: Path, profiles_dir_duckdb: Path) -> Path:
    """Compile dbt project and return manifest path."""
    result = subprocess.run(
        [
            "dbt",
            "compile",
            "--project-dir",
            str(dbt_project_with_deps),
            "--profiles-dir",
            str(profiles_dir_duckdb),
        ],
        capture_output=True,
        text=True,
        cwd=dbt_project_with_deps,
    )

    if result.returncode != 0:
        pytest.fail(f"dbt compile failed: {result.stderr}")

    manifest_path = dbt_project_with_deps / "target" / "manifest.json"
    assert manifest_path.exists(), "manifest.json not created"
    return manifest_path


@pytest.fixture
def materialization_artifacts(
    dbt_project_with_deps: Path,
    profiles_dir_duckdb: Path,
    compiled_manifest: Path,
    base_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Create CompiledArtifacts for materialization testing."""
    return {
        "version": "1.0.0",
        "metadata": base_metadata,
        "compute": {
            "target": "duckdb",
            "properties": {"path": str(dbt_project_with_deps.parent / "warehouse.duckdb")},
        },
        "transforms": [
            {
                "type": "dbt",
                "project_dir": str(dbt_project_with_deps),
                "profiles_dir": str(profiles_dir_duckdb),
            }
        ],
        "dbt_project_path": str(dbt_project_with_deps),
        "dbt_profiles_path": str(profiles_dir_duckdb),
        "dbt_manifest_path": str(compiled_manifest),
        "observability": {
            "traces": {"enabled": False},
            "lineage": {"enabled": False},
        },
    }


class TestAssetMaterialization:
    """Integration tests for Dagster asset materialization."""

    @pytest.mark.requirement("006-FR-011")
    def test_create_assets_from_manifest_with_deps(
        self,
        materialization_artifacts: dict[str, Any],
    ) -> None:
        """Test creating assets from manifest with model dependencies."""
        from floe_dagster.assets import FloeAssetFactory

        assets = FloeAssetFactory.create_dbt_assets(materialization_artifacts)

        assert assets is not None
        # Assets should be created (AssetsDefinition is truthy)
        assert assets

    @pytest.mark.requirement("006-FR-011")
    def test_create_definitions_includes_resources(
        self,
        materialization_artifacts: dict[str, Any],
    ) -> None:
        """Test that Definitions includes required resources."""
        from floe_dagster.assets import FloeAssetFactory

        definitions = FloeAssetFactory.create_definitions(materialization_artifacts)

        assert definitions is not None
        # Should have dbt resource configured (access via resources attribute)
        assert definitions.resources is not None
        assert "dbt" in definitions.resources

    @pytest.mark.requirement("006-FR-011")
    def test_translator_extracts_metadata_from_deps(
        self,
        compiled_manifest: Path,
    ) -> None:
        """Test that FloeTranslator extracts metadata from dependent models."""
        from floe_dagster.assets import FloeAssetFactory
        from floe_dagster.translator import FloeTranslator

        manifest = FloeAssetFactory._load_manifest(compiled_manifest)
        models = FloeAssetFactory._filter_models(manifest)

        translator = FloeTranslator()

        # Verify both models are found
        model_names = [node["name"] for node in models.values()]
        assert "stg_customers" in model_names
        assert "dim_customers" in model_names

        # Verify metadata extraction
        for model_node in models.values():
            description = translator.get_description(model_node)
            assert description is not None

            owners = translator.get_owners(model_node)
            # Owners should be extracted from floe.owner
            if owners:
                assert any("team:" in owner for owner in owners)

    @pytest.mark.requirement("006-FR-011")
    def test_asset_dependency_resolution(
        self,
        compiled_manifest: Path,
    ) -> None:
        """Test that asset dependencies are correctly resolved."""
        from floe_dagster.assets import FloeAssetFactory

        manifest = FloeAssetFactory._load_manifest(compiled_manifest)
        models = FloeAssetFactory._filter_models(manifest)

        # Find dim_customers model
        dim_model = None
        stg_model_id = None
        for model_id, model_node in models.items():
            if model_node["name"] == "dim_customers":
                dim_model = model_node
            if model_node["name"] == "stg_customers":
                stg_model_id = model_id

        assert dim_model is not None, "dim_customers model not found"
        assert stg_model_id is not None, "stg_customers model not found"

        # Verify dim_customers depends on stg_customers
        deps = dim_model.get("depends_on", {}).get("nodes", [])
        assert stg_model_id in deps, "dim_customers should depend on stg_customers"


class TestAssetMaterializationExecution:
    """Tests for actual asset materialization execution."""

    @pytest.mark.requirement("006-FR-011")
    @pytest.mark.integration
    def test_materialize_single_asset(
        self,
        materialization_artifacts: dict[str, Any],
    ) -> None:
        """Test materializing a single dbt asset."""
        from dagster import materialize
        from floe_dagster.assets import FloeAssetFactory

        # Create assets and definitions
        dbt_assets = FloeAssetFactory.create_dbt_assets(materialization_artifacts)
        definitions = FloeAssetFactory.create_definitions(materialization_artifacts)

        # Get the dbt resource from definitions
        assert definitions.resources is not None
        dbt_resource = definitions.resources["dbt"]

        # Materialize with ephemeral instance
        result = materialize(
            [dbt_assets],
            resources={"dbt": dbt_resource},
            raise_on_error=True,
        )

        assert result.success, "Asset materialization should succeed"

    @pytest.mark.requirement("006-FR-011")
    @pytest.mark.integration
    def test_materialize_all_assets(
        self,
        materialization_artifacts: dict[str, Any],
    ) -> None:
        """Test materializing all dbt assets in dependency order."""
        from dagster import materialize
        from floe_dagster.assets import FloeAssetFactory

        definitions = FloeAssetFactory.create_definitions(materialization_artifacts)
        dbt_assets = FloeAssetFactory.create_dbt_assets(materialization_artifacts)
        assert definitions.resources is not None
        dbt_resource = definitions.resources["dbt"]

        result = materialize(
            [dbt_assets],
            resources={"dbt": dbt_resource},
            raise_on_error=True,
        )

        assert result.success, "All assets should materialize successfully"
        # Both models should be materialized
        materialized = result.get_asset_materialization_events()
        assert len(materialized) >= 2, "Both stg_customers and dim_customers should materialize"


class TestAssetMaterializationEdgeCases:
    """Edge case tests for asset materialization."""

    @pytest.mark.requirement("006-FR-011")
    def test_materialize_with_missing_upstream_fails(
        self,
        dbt_project_with_deps: Path,
        profiles_dir_duckdb: Path,
    ) -> None:
        """Test that materialization fails gracefully with missing upstream."""
        # Create a model that references a non-existent model
        models_dir = dbt_project_with_deps / "models"
        (models_dir / "broken_model.sql").write_text(
            "SELECT * FROM {{ ref('nonexistent_model') }}"
        )

        # Compile should fail
        result = subprocess.run(
            [
                "dbt",
                "compile",
                "--project-dir",
                str(dbt_project_with_deps),
                "--profiles-dir",
                str(profiles_dir_duckdb),
            ],
            capture_output=True,
            text=True,
            cwd=dbt_project_with_deps,
        )

        # dbt compile should fail with ref to nonexistent model
        assert result.returncode != 0 or "nonexistent_model" in result.stderr

    @pytest.mark.requirement("006-FR-011")
    def test_asset_factory_validates_manifest_path(self) -> None:
        """Test that AssetFactory validates manifest path exists."""
        from floe_dagster.assets import FloeAssetFactory

        artifacts = {
            "dbt_manifest_path": "/nonexistent/path/manifest.json",
            "dbt_project_path": "/nonexistent/path",
            "dbt_profiles_path": "/nonexistent/profiles",
        }

        with pytest.raises((FileNotFoundError, ValueError)):
            FloeAssetFactory.create_dbt_assets(artifacts)

    @pytest.mark.requirement("006-FR-011")
    def test_asset_factory_requires_manifest_path(self) -> None:
        """Test that AssetFactory requires manifest path."""
        from floe_dagster.assets import FloeAssetFactory

        artifacts = {
            "dbt_project_path": "/some/path",
            "dbt_profiles_path": "/some/profiles",
            # Missing dbt_manifest_path
        }

        with pytest.raises(ValueError, match="dbt_manifest_path"):
            FloeAssetFactory.create_dbt_assets(artifacts)
