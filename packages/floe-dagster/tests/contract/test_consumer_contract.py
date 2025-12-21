"""Consumer-driven contract tests for floe-dagster.

These tests define what floe-dagster EXPECTS from CompiledArtifacts.
The floe-dagster team "owns" these tests - they document our requirements.

If floe-core changes CompiledArtifacts in a way that breaks these tests,
the floe-core team must either:
1. Update their change to maintain compatibility
2. Coordinate with floe-dagster team to update these expectations

Requirements covered:
- FR-011: All FloeSpec sections in CompiledArtifacts
- FR-012: dbt-specific fields in CompiledArtifacts
- 003-FR-001: Load CompiledArtifacts from JSON file
"""

from __future__ import annotations

import pytest

from floe_core.compiler.models import CompiledArtifacts
from floe_core.schemas import ComputeTarget
from testing.fixtures.golden_artifacts import (
    list_artifacts,
    load_golden_artifact,
)


class TestDagsterRequiredFields:
    """Test fields that floe-dagster REQUIRES from CompiledArtifacts.

    These are non-negotiable requirements. If these fields are missing
    or have the wrong type, floe-dagster cannot function.
    """

    @pytest.mark.requirement("003-FR-001")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_has_compute_config(self, artifact_name: str) -> None:
        """Dagster requires compute config to determine target."""
        artifact = load_golden_artifact("v1.0.0", artifact_name)
        compiled = CompiledArtifacts.model_validate(artifact)

        # REQUIRED: compute config exists
        assert compiled.compute is not None

        # REQUIRED: target is a valid ComputeTarget enum
        assert isinstance(compiled.compute.target, ComputeTarget)

        # REQUIRED: target is one of the supported targets
        supported_targets = [t.value for t in ComputeTarget]
        assert compiled.compute.target.value in supported_targets

    @pytest.mark.requirement("003-FR-001")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_has_transforms_list(self, artifact_name: str) -> None:
        """Dagster requires transforms list to create assets."""
        artifact = load_golden_artifact("v1.0.0", artifact_name)
        compiled = CompiledArtifacts.model_validate(artifact)

        # REQUIRED: transforms is a non-empty list
        assert isinstance(compiled.transforms, list)
        assert len(compiled.transforms) > 0

        # REQUIRED: each transform has type and path
        for transform in compiled.transforms:
            assert transform.type == "dbt"
            assert transform.path is not None

    @pytest.mark.requirement("001-FR-012")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_has_dbt_profiles_path(self, artifact_name: str) -> None:
        """Dagster requires dbt_profiles_path for dagster-dbt integration."""
        artifact = load_golden_artifact("v1.0.0", artifact_name)
        compiled = CompiledArtifacts.model_validate(artifact)

        # REQUIRED: dbt_profiles_path exists and is a string
        assert compiled.dbt_profiles_path is not None
        assert isinstance(compiled.dbt_profiles_path, str)
        assert len(compiled.dbt_profiles_path) > 0

    @pytest.mark.requirement("003-FR-001")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_has_metadata(self, artifact_name: str) -> None:
        """Dagster uses metadata for run tagging."""
        artifact = load_golden_artifact("v1.0.0", artifact_name)
        compiled = CompiledArtifacts.model_validate(artifact)

        # REQUIRED: metadata exists with compilation info
        assert compiled.metadata is not None
        assert compiled.metadata.compiled_at is not None
        assert compiled.metadata.floe_core_version is not None


class TestDagsterOptionalFields:
    """Test optional fields that floe-dagster uses when present.

    These fields enhance functionality but are not required.
    Dagster handles their absence gracefully.
    """

    @pytest.mark.requirement("003-FR-001")
    def test_observability_optional(self) -> None:
        """Observability config is optional but used when present."""
        # Minimal artifact - observability uses defaults
        minimal = load_golden_artifact("v1.0.0", "minimal.json")
        compiled_minimal = CompiledArtifacts.model_validate(minimal)

        # Should have defaults
        assert compiled_minimal.observability is not None
        assert compiled_minimal.observability.traces is True  # Default

        # Full artifact - observability fully configured
        full = load_golden_artifact("v1.0.0", "full.json")
        compiled_full = CompiledArtifacts.model_validate(full)

        assert compiled_full.observability.otlp_endpoint is not None
        assert compiled_full.observability.lineage_endpoint is not None

    @pytest.mark.requirement("003-FR-001")
    def test_manifest_path_optional(self) -> None:
        """dbt_manifest_path is optional - Dagster can compile manifest."""
        minimal = load_golden_artifact("v1.0.0", "minimal.json")
        compiled = CompiledArtifacts.model_validate(minimal)

        # Can be None - Dagster will compile manifest
        # Just verify the field exists
        assert hasattr(compiled, "dbt_manifest_path")

    @pytest.mark.requirement("003-FR-001")
    def test_lineage_namespace_optional(self) -> None:
        """lineage_namespace is optional - used for OpenLineage."""
        minimal = load_golden_artifact("v1.0.0", "minimal.json")
        compiled = CompiledArtifacts.model_validate(minimal)

        # Can be None
        assert hasattr(compiled, "lineage_namespace")

        # When present, should be a string
        full = load_golden_artifact("v1.0.0", "full.json")
        compiled_full = CompiledArtifacts.model_validate(full)
        assert isinstance(compiled_full.lineage_namespace, str)


class TestDagsterAssetCreation:
    """Test that artifacts have what Dagster needs for asset creation."""

    @pytest.mark.requirement("003-FR-001")
    def test_can_create_dbt_asset_definition(self) -> None:
        """Artifact has all fields needed for dbt asset definition."""
        artifact = load_golden_artifact("v1.0.0", "full.json")
        compiled = CompiledArtifacts.model_validate(artifact)

        # Fields needed for @dbt_assets
        assert compiled.transforms[0].type == "dbt"
        assert compiled.transforms[0].path is not None
        assert compiled.dbt_profiles_path is not None

        # Optional but used for metadata
        assert compiled.compute.target is not None

    @pytest.mark.requirement("003-FR-001")
    def test_can_extract_run_config(self) -> None:
        """Artifact has what's needed for Dagster run configuration."""
        artifact = load_golden_artifact("v1.0.0", "production.json")
        compiled = CompiledArtifacts.model_validate(artifact)

        # Run config uses these
        assert compiled.compute.target.value == "snowflake"
        assert compiled.compute.properties is not None

        # Environment context for run tags (optional)
        assert compiled.environment_context is not None
        assert compiled.environment_context.environment_type == "production"


class TestDagsterObservability:
    """Test observability fields used by Dagster for tracing."""

    @pytest.mark.requirement("003-FR-001")
    def test_otel_configuration(self) -> None:
        """Observability config provides OTel settings."""
        artifact = load_golden_artifact("v1.0.0", "docker_integration.json")
        compiled = CompiledArtifacts.model_validate(artifact)

        # Dagster uses these for OTel integration
        assert compiled.observability.traces is True
        assert compiled.observability.otlp_endpoint == "http://jaeger:4317"
        assert "service.name" in compiled.observability.attributes

    @pytest.mark.requirement("003-FR-001")
    def test_lineage_configuration(self) -> None:
        """Observability config provides OpenLineage settings."""
        artifact = load_golden_artifact("v1.0.0", "full.json")
        compiled = CompiledArtifacts.model_validate(artifact)

        # Dagster uses these for OpenLineage
        assert compiled.observability.lineage is True
        assert compiled.observability.lineage_endpoint is not None
        assert compiled.lineage_namespace is not None


class TestDagsterBackwardCompatibility:
    """Test that older artifacts still work with current Dagster code."""

    @pytest.mark.requirement("001-FR-015")
    def test_v1_0_0_artifacts_work(self) -> None:
        """All v1.0.0 artifacts work with current Dagster expectations."""
        for artifact_name in list_artifacts("v1.0.0"):
            artifact = load_golden_artifact("v1.0.0", artifact_name)
            compiled = CompiledArtifacts.model_validate(artifact)

            # Core Dagster requirements
            assert compiled.compute is not None
            assert len(compiled.transforms) > 0
            assert compiled.dbt_profiles_path is not None
            assert compiled.metadata is not None
