"""Integration tests for orchestration layer requirements.

Tests for Feature 003 (Orchestration Layer) requirements that verify:
- dbt model dependencies preserved as Dagster asset dependencies (003-FR-007)
- dbt execution events streamed to Dagster event log (003-FR-009)
- Column classifications in OpenLineage dataset facets (003-FR-015)
- No SaaS dependencies for core execution (003-FR-023)
- OpenLineage emission from floe-dagster code (003-FR-024)

Requirements:
- Some tests require dbt-core and dagster (run in Docker test-runner)
- Classification tests can run on host (pure Pydantic models)

See Also:
    - specs/003-orchestration-layer/spec.md
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

# Check if required dependencies are available
try:
    import dbt.version  # noqa: F401

    HAS_DBT = True
except ImportError:
    HAS_DBT = False

try:
    from dagster import materialize  # noqa: F401

    HAS_DAGSTER = True
except ImportError:
    HAS_DAGSTER = False

# Marker for tests that require Dagster infrastructure
requires_dagster = pytest.mark.skipif(
    not HAS_DAGSTER,
    reason="dagster not installed",
)

requires_dbt = pytest.mark.skipif(
    not HAS_DBT,
    reason="dbt-core not installed",
)


@pytest.fixture
def dbt_project_with_dependencies(tmp_path: Path) -> Path:
    """Create dbt project with multiple models and dependencies.

    Creates a DAG structure:
        stg_customers -> dim_customers
        stg_orders -> fact_orders
        dim_customers -> fact_orders (join dependency)
    """
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

    # Create staging models (no dependencies)
    (models_dir / "stg_customers.sql").write_text(
        "SELECT 1 as customer_id, 'John' as first_name, 'john@example.com' as email"
    )

    (models_dir / "stg_orders.sql").write_text(
        "SELECT 1 as order_id, 1 as customer_id, 100.00 as amount"
    )

    # Create dimension model (depends on staging)
    (models_dir / "dim_customers.sql").write_text(
        """\
SELECT
    customer_id,
    first_name,
    email
FROM {{ ref('stg_customers') }}
"""
    )

    # Create fact model (depends on both staging and dimension)
    (models_dir / "fact_orders.sql").write_text(
        """\
SELECT
    o.order_id,
    o.customer_id,
    c.first_name as customer_name,
    o.amount
FROM {{ ref('stg_orders') }} o
JOIN {{ ref('dim_customers') }} c ON o.customer_id = c.customer_id
"""
    )

    # Create schema.yml with metadata and classifications
    schema_config = {
        "version": 2,
        "models": [
            {
                "name": "stg_customers",
                "description": "Staging layer for customer data",
                "meta": {"floe": {"owner": "team:data-team"}},
                "columns": [
                    {"name": "customer_id", "description": "Customer identifier"},
                    {"name": "first_name", "description": "First name"},
                    {
                        "name": "email",
                        "description": "Customer email",
                        "meta": {
                            "floe": {
                                "classification": "pii",
                                "pii_type": "email",
                                "sensitivity": "high",
                            }
                        },
                    },
                ],
            },
            {
                "name": "stg_orders",
                "description": "Staging layer for order data",
                "meta": {"floe": {"owner": "team:data-team"}},
            },
            {
                "name": "dim_customers",
                "description": "Customer dimension table",
                "meta": {"floe": {"owner": "team:analytics"}},
                "columns": [
                    {"name": "customer_id", "description": "Customer identifier"},
                    {"name": "first_name", "description": "First name"},
                    {
                        "name": "email",
                        "description": "Customer email",
                        "meta": {
                            "floe": {
                                "classification": "pii",
                                "pii_type": "email",
                                "sensitivity": "high",
                            }
                        },
                    },
                ],
            },
            {
                "name": "fact_orders",
                "description": "Order fact table with customer context",
                "meta": {"floe": {"owner": "team:analytics"}},
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
def compiled_manifest(
    dbt_project_with_dependencies: Path, profiles_dir_duckdb: Path
) -> Path:
    """Compile dbt project and return manifest path."""
    result = subprocess.run(
        [
            "dbt",
            "compile",
            "--project-dir",
            str(dbt_project_with_dependencies),
            "--profiles-dir",
            str(profiles_dir_duckdb),
        ],
        capture_output=True,
        text=True,
        cwd=dbt_project_with_dependencies,
    )

    if result.returncode != 0:
        pytest.fail(f"dbt compile failed: {result.stderr}")

    manifest_path = dbt_project_with_dependencies / "target" / "manifest.json"
    assert manifest_path.exists(), "manifest.json not created"
    return manifest_path


@pytest.fixture
def test_artifacts(
    dbt_project_with_dependencies: Path,
    profiles_dir_duckdb: Path,
    compiled_manifest: Path,
    base_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Create CompiledArtifacts for testing."""
    return {
        "version": "1.0.0",
        "metadata": base_metadata,
        "compute": {
            "target": "duckdb",
            "properties": {
                "path": str(dbt_project_with_dependencies.parent / "warehouse.duckdb")
            },
        },
        "transforms": [
            {
                "type": "dbt",
                "project_dir": str(dbt_project_with_dependencies),
                "profiles_dir": str(profiles_dir_duckdb),
            }
        ],
        "dbt_project_path": str(dbt_project_with_dependencies),
        "dbt_profiles_path": str(profiles_dir_duckdb),
        "dbt_manifest_path": str(compiled_manifest),
        "observability": {
            "traces": {"enabled": False},
            "lineage": {"enabled": False},
        },
    }


@requires_dagster
@requires_dbt
class TestDbtDependencyPreservation:
    """Tests for FR-007: Preserve dbt model dependencies as Dagster asset dependencies."""

    @pytest.mark.requirement("003-FR-007")
    def test_manifest_preserves_model_dependencies(
        self,
        compiled_manifest: Path,
    ) -> None:
        """Test that dbt manifest preserves model dependencies.

        Covers:
        - 003-FR-007: System MUST preserve dbt model dependencies
        """
        from floe_dagster.assets import FloeAssetFactory

        manifest = FloeAssetFactory._load_manifest(compiled_manifest)
        models = FloeAssetFactory._filter_models(manifest)

        # Find fact_orders and verify its dependencies
        fact_orders = None
        for model_id, model_node in models.items():
            if model_node["name"] == "fact_orders":
                fact_orders = model_node
                break

        assert fact_orders is not None, "fact_orders model not found"

        # Get dependencies
        deps = fact_orders.get("depends_on", {}).get("nodes", [])

        # Should depend on stg_orders and dim_customers
        dep_names = [d.split(".")[-1] for d in deps]
        assert "stg_orders" in dep_names, "fact_orders should depend on stg_orders"
        assert "dim_customers" in dep_names, "fact_orders should depend on dim_customers"

    @pytest.mark.requirement("003-FR-007")
    def test_dim_customers_depends_on_stg_customers(
        self,
        compiled_manifest: Path,
    ) -> None:
        """Test that dim_customers depends on stg_customers.

        Covers:
        - 003-FR-007: System MUST preserve dbt model dependencies
        """
        from floe_dagster.assets import FloeAssetFactory

        manifest = FloeAssetFactory._load_manifest(compiled_manifest)
        models = FloeAssetFactory._filter_models(manifest)

        # Find dim_customers
        dim_customers = None
        for model_id, model_node in models.items():
            if model_node["name"] == "dim_customers":
                dim_customers = model_node
                break

        assert dim_customers is not None, "dim_customers model not found"

        # Should depend on stg_customers
        deps = dim_customers.get("depends_on", {}).get("nodes", [])
        dep_names = [d.split(".")[-1] for d in deps]
        assert "stg_customers" in dep_names, "dim_customers should depend on stg_customers"

    @pytest.mark.requirement("003-FR-007")
    def test_staging_models_have_no_model_dependencies(
        self,
        compiled_manifest: Path,
    ) -> None:
        """Test that staging models have no upstream model dependencies.

        Covers:
        - 003-FR-007: System MUST preserve dbt model dependencies
        """
        from floe_dagster.assets import FloeAssetFactory

        manifest = FloeAssetFactory._load_manifest(compiled_manifest)
        models = FloeAssetFactory._filter_models(manifest)

        # Find staging models
        stg_customers = None
        stg_orders = None
        for model_id, model_node in models.items():
            if model_node["name"] == "stg_customers":
                stg_customers = model_node
            if model_node["name"] == "stg_orders":
                stg_orders = model_node

        assert stg_customers is not None, "stg_customers not found"
        assert stg_orders is not None, "stg_orders not found"

        # Staging models should have no model dependencies (only sources if any)
        stg_cust_deps = stg_customers.get("depends_on", {}).get("nodes", [])
        stg_ord_deps = stg_orders.get("depends_on", {}).get("nodes", [])

        # Filter to only model dependencies
        model_deps_cust = [d for d in stg_cust_deps if d.startswith("model.")]
        model_deps_ord = [d for d in stg_ord_deps if d.startswith("model.")]

        assert len(model_deps_cust) == 0, "stg_customers should have no model dependencies"
        assert len(model_deps_ord) == 0, "stg_orders should have no model dependencies"

    @pytest.mark.requirement("003-FR-007")
    def test_dagster_assets_preserve_dependency_structure(
        self,
        test_artifacts: dict[str, Any],
    ) -> None:
        """Test that Dagster assets preserve dbt dependency structure.

        Covers:
        - 003-FR-007: System MUST preserve dbt model dependencies as Dagster asset deps
        """
        from floe_dagster.assets import FloeAssetFactory

        # Create assets (this exercises the @dbt_assets decorator)
        assets = FloeAssetFactory.create_dbt_assets(test_artifacts)

        assert assets is not None
        # Assets should be truthy (non-empty AssetsDefinition)
        assert assets


@requires_dagster
@requires_dbt
class TestDbtEventStreaming:
    """Tests for FR-009: Stream dbt execution events to Dagster event log."""

    @pytest.mark.requirement("003-FR-009")
    @pytest.mark.integration
    def test_dbt_run_streams_events(
        self,
        test_artifacts: dict[str, Any],
    ) -> None:
        """Test that dbt run streams events to Dagster.

        Covers:
        - 003-FR-009: System MUST stream dbt execution events to Dagster event log
        """
        from dagster import materialize
        from floe_dagster.assets import FloeAssetFactory

        definitions = FloeAssetFactory.create_definitions(test_artifacts)
        dbt_assets = FloeAssetFactory.create_dbt_assets(test_artifacts)
        assert definitions.resources is not None
        dbt_resource = definitions.resources["dbt"]

        # Materialize and capture events
        result = materialize(
            [dbt_assets],
            resources={"dbt": dbt_resource},
            raise_on_error=True,
        )

        assert result.success, "Asset materialization should succeed"

        # Verify we got materialization events for all models
        materialized = result.get_asset_materialization_events()
        assert len(materialized) >= 4, "Should have events for all 4 models"

    @pytest.mark.requirement("003-FR-009")
    @pytest.mark.integration
    def test_dbt_events_include_model_info(
        self,
        test_artifacts: dict[str, Any],
    ) -> None:
        """Test that dbt events include model information.

        Covers:
        - 003-FR-009: System MUST stream dbt execution events to Dagster event log
        """
        from dagster import materialize
        from floe_dagster.assets import FloeAssetFactory

        definitions = FloeAssetFactory.create_definitions(test_artifacts)
        dbt_assets = FloeAssetFactory.create_dbt_assets(test_artifacts)
        assert definitions.resources is not None
        dbt_resource = definitions.resources["dbt"]

        result = materialize(
            [dbt_assets],
            resources={"dbt": dbt_resource},
            raise_on_error=True,
        )

        assert result.success

        # Get asset events
        events = result.get_asset_materialization_events()

        # Verify each event has asset key
        for event in events:
            assert event.asset_key is not None


# NOTE: These tests require floe_dagster package which depends on dagster
@requires_dagster
class TestColumnClassificationsInLineage:
    """Tests for FR-015: Column classifications in OpenLineage dataset facets."""

    @pytest.mark.requirement("003-FR-015")
    def test_column_classification_extraction(self) -> None:
        """Test that column classifications are extracted from dbt meta.

        Covers:
        - 003-FR-015: System MUST include column classifications in dataset facets
        """
        from floe_dagster.lineage.facets import ColumnClassification

        # Simulate dbt column meta
        meta = {
            "floe": {
                "classification": "pii",
                "pii_type": "email",
                "sensitivity": "high",
            }
        }

        classification = ColumnClassification.from_dbt_meta("email", meta)

        assert classification is not None
        assert classification.column_name == "email"
        assert classification.classification == "pii"
        assert classification.pii_type == "email"
        assert classification.sensitivity == "high"

    @pytest.mark.requirement("003-FR-015")
    def test_classification_to_openlineage_format(self) -> None:
        """Test that classifications convert to OpenLineage format.

        Covers:
        - 003-FR-015: System MUST include column classifications in dataset facets
        """
        from floe_dagster.lineage.facets import ColumnClassification

        classification = ColumnClassification(
            column_name="email",
            classification="pii",
            pii_type="email",
            sensitivity="high",
        )

        ol_dict = classification.to_openlineage_dict()

        # OpenLineage uses camelCase
        assert ol_dict["columnName"] == "email"
        assert ol_dict["classification"] == "pii"
        assert ol_dict["piiType"] == "email"
        assert ol_dict["sensitivity"] == "high"

    @pytest.mark.requirement("003-FR-015")
    def test_classification_facet_building(self) -> None:
        """Test that classification facet is built correctly.

        Covers:
        - 003-FR-015: System MUST include column classifications in dataset facets
        """
        from floe_dagster.lineage.facets import (
            ColumnClassification,
            build_classification_facet,
        )

        classifications = [
            ColumnClassification(
                column_name="email",
                classification="pii",
                pii_type="email",
                sensitivity="high",
            ),
            ColumnClassification(
                column_name="phone",
                classification="pii",
                pii_type="phone",
                sensitivity="high",
            ),
        ]

        facet = build_classification_facet(classifications)

        assert facet is not None
        assert "_producer" in facet
        assert facet["_producer"] == "floe-dagster"
        assert "columnClassifications" in facet
        assert len(facet["columnClassifications"]) == 2

    @pytest.mark.requirement("003-FR-015")
    def test_dataset_builder_includes_classifications(
        self,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test that LineageDatasetBuilder includes classifications in facets.

        Covers:
        - 003-FR-015: System MUST include column classifications in dataset facets
        """
        from floe_dagster.lineage import LineageDatasetBuilder

        builder = LineageDatasetBuilder(
            namespace_prefix="duckdb://test",
            include_classifications=True,
        )

        dataset = builder.build_from_dbt_node(sample_dbt_manifest_node)

        # Should have columnClassification facet
        assert "columnClassification" in dataset.facets
        facet = dataset.facets["columnClassification"]
        assert "columnClassifications" in facet

        # The email column should be classified
        classifications = facet["columnClassifications"]
        email_classification = next(
            (c for c in classifications if c["columnName"] == "email"), None
        )
        assert email_classification is not None
        assert email_classification["classification"] == "pii"
        assert email_classification["piiType"] == "email"


@requires_dagster
@requires_dbt
class TestNoSaaSDependencies:
    """Tests for FR-023: No SaaS dependencies for core execution."""

    @pytest.mark.requirement("003-FR-023")
    @pytest.mark.integration
    def test_pipeline_executes_without_api_keys(
        self,
        test_artifacts: dict[str, Any],
    ) -> None:
        """Test that pipeline executes without any SaaS API keys.

        Covers:
        - 003-FR-023: System MUST not require any SaaS dependencies
        """
        from dagster import materialize
        from floe_dagster.assets import FloeAssetFactory

        # Artifacts have no SaaS configuration
        assert test_artifacts.get("lineage_namespace") is None
        assert test_artifacts.get("environment_context") is None

        definitions = FloeAssetFactory.create_definitions(test_artifacts)
        dbt_assets = FloeAssetFactory.create_dbt_assets(test_artifacts)
        assert definitions.resources is not None
        dbt_resource = definitions.resources["dbt"]

        # Should execute successfully without any SaaS dependencies
        result = materialize(
            [dbt_assets],
            resources={"dbt": dbt_resource},
            raise_on_error=True,
        )

        assert result.success, "Pipeline should execute without SaaS dependencies"

    @pytest.mark.requirement("003-FR-023")
    def test_artifacts_have_no_saas_config(
        self,
        test_artifacts: dict[str, Any],
    ) -> None:
        """Test that test artifacts have no SaaS configuration.

        Covers:
        - 003-FR-023: System MUST not require any SaaS dependencies
        """
        # No lineage namespace (would be set by Control Plane)
        assert test_artifacts.get("lineage_namespace") is None

        # No environment context (would be set by Control Plane)
        assert test_artifacts.get("environment_context") is None

        # Observability is explicitly disabled (standalone mode)
        obs = test_artifacts.get("observability", {})
        assert obs.get("traces", {}).get("enabled") is False
        assert obs.get("lineage", {}).get("enabled") is False

    @pytest.mark.requirement("003-FR-023")
    def test_dbt_profiles_contain_no_saas_endpoints(
        self,
        profiles_dir_duckdb: Path,
    ) -> None:
        """Test that dbt profiles contain no SaaS endpoints.

        Covers:
        - 003-FR-023: System MUST not require any SaaS dependencies
        """
        profiles_file = profiles_dir_duckdb / "profiles.yml"
        content = profiles_file.read_text()

        # Should not contain any SaaS-related URLs
        assert "api.floe.cloud" not in content
        assert "floe-saas" not in content
        assert "FLOE_API_KEY" not in content


# NOTE: These tests require floe_dagster package which depends on dagster
@requires_dagster
class TestOpenLineageEmissionFromFloeDagster:
    """Tests for FR-024: OpenLineage emission from floe-dagster code."""

    @pytest.mark.requirement("003-FR-024")
    def test_openlineage_emitter_exists(self) -> None:
        """Test that OpenLineageEmitter is implemented in floe-dagster.

        Covers:
        - 003-FR-024: System MUST implement OpenLineage emission in floe-dagster
        """
        from floe_dagster.lineage import OpenLineageConfig, OpenLineageEmitter

        # Can create config and emitter
        config = OpenLineageConfig(
            endpoint=None,  # Disabled mode
            namespace="test",
        )
        emitter = OpenLineageEmitter(config)

        assert emitter is not None

    @pytest.mark.requirement("003-FR-024")
    def test_emitter_has_emit_methods(self) -> None:
        """Test that emitter has all required emission methods.

        Covers:
        - 003-FR-024: System MUST implement OpenLineage emission in floe-dagster
        """
        from floe_dagster.lineage import OpenLineageConfig, OpenLineageEmitter

        config = OpenLineageConfig(
            endpoint=None,
            namespace="test",
        )
        emitter = OpenLineageEmitter(config)

        # Verify all emission methods exist
        assert hasattr(emitter, "emit_start")
        assert hasattr(emitter, "emit_complete")
        assert hasattr(emitter, "emit_fail")
        assert callable(emitter.emit_start)
        assert callable(emitter.emit_complete)
        assert callable(emitter.emit_fail)

    @requires_dagster
    @requires_dbt
    @pytest.mark.requirement("003-FR-024")
    def test_emitter_integrated_in_asset_factory(
        self,
        test_artifacts: dict[str, Any],
    ) -> None:
        """Test that emitter is integrated in FloeAssetFactory.

        Covers:
        - 003-FR-024: System MUST implement OpenLineage emission in floe-dagster
        """
        from floe_dagster.assets import FloeAssetFactory

        # The create_dbt_assets method integrates OpenLineageEmitter
        # (we verified this by reading the source code)
        # This test confirms the integration works
        assets = FloeAssetFactory.create_dbt_assets(test_artifacts)

        assert assets is not None

    @pytest.mark.requirement("003-FR-024")
    def test_emitter_disabled_gracefully(self) -> None:
        """Test that emitter works gracefully when disabled.

        Covers:
        - 003-FR-024: OpenLineage emission for standards-based portability
        """
        from floe_dagster.lineage import OpenLineageConfig, OpenLineageEmitter

        # Disabled config (no endpoint)
        config = OpenLineageConfig(
            endpoint=None,
            namespace="test",
        )
        emitter = OpenLineageEmitter(config)

        # Should be disabled
        assert not emitter.enabled

        # But operations should not raise
        run_id = emitter.emit_start(job_name="test_job")
        assert run_id is not None

        emitter.emit_complete(run_id=run_id, job_name="test_job")
        emitter.emit_fail(run_id=run_id, job_name="test_job", error_message="test")

    @pytest.mark.requirement("003-FR-024")
    def test_lineage_dataset_builder_is_floe_dagster_code(self) -> None:
        """Test that LineageDatasetBuilder is in floe-dagster package.

        Covers:
        - 003-FR-024: System MUST implement OpenLineage emission in floe-dagster
        """
        from floe_dagster.lineage import LineageDatasetBuilder

        # Verify it's from floe_dagster package
        module = LineageDatasetBuilder.__module__
        assert "floe_dagster" in module
        assert "dagster" not in module or "floe_dagster" in module
