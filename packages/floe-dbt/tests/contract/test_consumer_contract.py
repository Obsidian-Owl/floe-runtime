"""Consumer-driven contract tests for floe-dbt.

These tests define what floe-dbt EXPECTS from CompiledArtifacts.
The floe-dbt team "owns" these tests - they document our requirements.

If floe-core changes CompiledArtifacts in a way that breaks these tests,
the floe-core team must either:
1. Update their change to maintain compatibility
2. Coordinate with floe-dbt team to update these expectations

Requirements covered:
- FR-011: All FloeSpec sections in CompiledArtifacts
- FR-012: dbt-specific fields in CompiledArtifacts
"""

from __future__ import annotations

import pytest

from floe_core.compiler.models import CompiledArtifacts
from floe_core.schemas import ComputeTarget
from testing.fixtures.golden_artifacts import (
    load_golden_artifact,
    list_artifacts,
)


class TestDbtRequiredFields:
    """Test fields that floe-dbt REQUIRES from CompiledArtifacts.

    These are non-negotiable requirements. If these fields are missing
    or have the wrong type, floe-dbt cannot generate profiles.yml.
    """

    @pytest.mark.requirement("001-FR-011")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_has_compute_target(self, artifact_name: str) -> None:
        """dbt requires compute target to determine adapter."""
        artifact = load_golden_artifact("v1.0.0", artifact_name)
        compiled = CompiledArtifacts.model_validate(artifact)

        # REQUIRED: compute config with target
        assert compiled.compute is not None
        assert compiled.compute.target is not None

        # REQUIRED: target is valid dbt adapter name
        valid_adapters = ["duckdb", "snowflake", "bigquery", "redshift",
                         "databricks", "postgres", "spark"]
        assert compiled.compute.target.value in valid_adapters

    @pytest.mark.requirement("001-FR-011")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_has_compute_properties(self, artifact_name: str) -> None:
        """dbt requires compute properties for connection config."""
        artifact = load_golden_artifact("v1.0.0", artifact_name)
        compiled = CompiledArtifacts.model_validate(artifact)

        # REQUIRED: properties dict exists
        assert compiled.compute.properties is not None
        assert isinstance(compiled.compute.properties, dict)

    @pytest.mark.requirement("001-FR-012")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_has_dbt_profiles_path(self, artifact_name: str) -> None:
        """dbt requires profiles path for output location."""
        artifact = load_golden_artifact("v1.0.0", artifact_name)
        compiled = CompiledArtifacts.model_validate(artifact)

        # REQUIRED: profiles path for writing profiles.yml
        assert compiled.dbt_profiles_path is not None
        assert isinstance(compiled.dbt_profiles_path, str)
        assert len(compiled.dbt_profiles_path) > 0


class TestDbtTargetSpecificFields:
    """Test target-specific fields that dbt needs for each adapter."""

    @pytest.mark.requirement("001-FR-011")
    def test_duckdb_properties(self) -> None:
        """DuckDB requires path property."""
        artifact = load_golden_artifact("v1.0.0", "minimal.json")
        compiled = CompiledArtifacts.model_validate(artifact)

        if compiled.compute.target == ComputeTarget.duckdb:
            # DuckDB needs path (can be :memory:)
            assert "path" in compiled.compute.properties

    @pytest.mark.requirement("001-FR-011")
    def test_snowflake_properties(self) -> None:
        """Snowflake requires account, warehouse properties."""
        artifact = load_golden_artifact("v1.0.0", "production.json")
        compiled = CompiledArtifacts.model_validate(artifact)

        if compiled.compute.target == ComputeTarget.snowflake:
            props = compiled.compute.properties
            # Snowflake required properties
            assert "account" in props
            assert "warehouse" in props

    @pytest.mark.requirement("001-FR-011")
    def test_postgres_properties(self) -> None:
        """PostgreSQL requires host, database properties."""
        artifact = load_golden_artifact("v1.0.0", "docker_integration.json")
        compiled = CompiledArtifacts.model_validate(artifact)

        if compiled.compute.target == ComputeTarget.postgres:
            props = compiled.compute.properties
            # Postgres required properties
            assert "host" in props
            assert "database" in props


class TestDbtSecretReferences:
    """Test secret reference handling for credentials."""

    @pytest.mark.requirement("001-FR-011")
    def test_connection_secret_ref_optional(self) -> None:
        """connection_secret_ref is optional (DuckDB doesn't need it)."""
        minimal = load_golden_artifact("v1.0.0", "minimal.json")
        compiled = CompiledArtifacts.model_validate(minimal)

        # DuckDB: no secret needed
        assert compiled.compute.connection_secret_ref is None

    @pytest.mark.requirement("001-FR-011")
    def test_connection_secret_ref_when_present(self) -> None:
        """connection_secret_ref is a valid K8s secret name when present."""
        production = load_golden_artifact("v1.0.0", "production.json")
        compiled = CompiledArtifacts.model_validate(production)

        # Snowflake: secret needed
        assert compiled.compute.connection_secret_ref is not None
        # Should be valid K8s name (alphanumeric, dashes)
        import re
        pattern = r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$"
        assert re.match(pattern, compiled.compute.connection_secret_ref)


class TestDbtProfilesGeneration:
    """Test that artifacts have what's needed for profiles.yml generation."""

    @pytest.mark.requirement("001-FR-012")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_can_generate_profiles_yml(self, artifact_name: str) -> None:
        """Artifact has all fields needed for profiles.yml generation."""
        artifact = load_golden_artifact("v1.0.0", artifact_name)
        compiled = CompiledArtifacts.model_validate(artifact)

        # Required for profiles.yml
        assert compiled.compute.target is not None
        assert compiled.compute.properties is not None
        assert compiled.dbt_profiles_path is not None

        # Target-specific validation
        target = compiled.compute.target.value
        props = compiled.compute.properties

        if target == "duckdb":
            assert "path" in props
        elif target == "snowflake":
            assert "account" in props
        elif target == "postgres":
            assert "host" in props


class TestDbtTransformConfig:
    """Test transform configuration for dbt projects."""

    @pytest.mark.requirement("001-FR-011")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_transform_type_is_dbt(self, artifact_name: str) -> None:
        """First transform type must be dbt."""
        artifact = load_golden_artifact("v1.0.0", artifact_name)
        compiled = CompiledArtifacts.model_validate(artifact)

        # At least one transform
        assert len(compiled.transforms) > 0

        # First transform is dbt
        assert compiled.transforms[0].type == "dbt"

    @pytest.mark.requirement("001-FR-011")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_transform_has_path(self, artifact_name: str) -> None:
        """Transform must have path to dbt project."""
        artifact = load_golden_artifact("v1.0.0", artifact_name)
        compiled = CompiledArtifacts.model_validate(artifact)

        for transform in compiled.transforms:
            assert transform.path is not None
            assert isinstance(transform.path, str)


class TestDbtBackwardCompatibility:
    """Test that older artifacts still work with current dbt code."""

    @pytest.mark.requirement("001-FR-015")
    def test_v1_0_0_artifacts_work(self) -> None:
        """All v1.0.0 artifacts work with current dbt expectations."""
        for artifact_name in list_artifacts("v1.0.0"):
            artifact = load_golden_artifact("v1.0.0", artifact_name)
            compiled = CompiledArtifacts.model_validate(artifact)

            # Core dbt requirements
            assert compiled.compute is not None
            assert compiled.compute.target is not None
            assert compiled.compute.properties is not None
            assert compiled.dbt_profiles_path is not None
            assert len(compiled.transforms) > 0
