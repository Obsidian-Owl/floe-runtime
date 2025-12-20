"""Golden artifact contract tests.

These tests validate that all golden artifacts can be loaded and validated
against the CompiledArtifacts model. If these tests fail, it means the
contract has changed in a way that breaks backward compatibility.

Requirements covered:
- FR-009: CompiledArtifacts immutability and extra field rejection
- FR-015: 3-version backward compatibility
- FR-022: JSON Schema export for cross-language validation

Test markers:
- @pytest.mark.requirement: Links to feature requirements
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from floe_core.compiler.models import CompiledArtifacts
from testing.fixtures.golden_artifacts import (
    GOLDEN_ARTIFACTS_DIR,
    load_all_golden_artifacts,
    load_golden_artifact,
    list_artifacts,
    list_versions,
)

if TYPE_CHECKING:
    from typing import Any


class TestGoldenArtifactLoading:
    """Test that golden artifacts can be loaded correctly."""

    @pytest.mark.requirement("001-FR-009")
    def test_load_minimal_artifact(self) -> None:
        """Load minimal artifact and validate structure."""
        artifact = load_golden_artifact("v1.0.0", "minimal.json")

        assert artifact["version"] == "1.0.0"
        assert "metadata" in artifact
        assert "compute" in artifact
        assert "transforms" in artifact

    @pytest.mark.requirement("001-FR-009")
    def test_load_full_artifact(self) -> None:
        """Load full artifact with all fields populated."""
        artifact = load_golden_artifact("v1.0.0", "full.json")

        assert artifact["version"] == "1.0.0"
        assert artifact["catalog"] is not None
        assert artifact["environment_context"] is not None
        assert artifact["column_classifications"] is not None

    @pytest.mark.requirement("001-FR-009")
    def test_load_all_artifacts(self) -> None:
        """Load all artifacts for a version."""
        artifacts = load_all_golden_artifacts("v1.0.0")

        assert len(artifacts) == 4
        assert "minimal.json" in artifacts
        assert "full.json" in artifacts
        assert "docker_integration.json" in artifacts
        assert "production.json" in artifacts

    def test_invalid_version_raises(self) -> None:
        """Invalid version raises ValueError."""
        with pytest.raises(ValueError, match="Unknown version"):
            load_golden_artifact("v99.0.0", "minimal.json")

    def test_invalid_artifact_raises(self) -> None:
        """Invalid artifact name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown artifact"):
            load_golden_artifact("v1.0.0", "nonexistent.json")


class TestGoldenArtifactContractValidation:
    """Test that golden artifacts validate against CompiledArtifacts model.

    These are the critical contract tests. If these fail, the contract is broken.
    """

    @pytest.mark.requirement("001-FR-009")
    @pytest.mark.requirement("001-FR-015")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_all_v1_artifacts_validate(self, artifact_name: str) -> None:
        """All v1.0.0 artifacts MUST validate against CompiledArtifacts.

        This is the core contract test. If this fails, backward compatibility
        is broken.
        """
        artifact_data = load_golden_artifact("v1.0.0", artifact_name)

        # This MUST NOT raise - if it does, the contract is broken
        compiled = CompiledArtifacts.model_validate(artifact_data)

        # Basic sanity checks
        assert compiled.version == "1.0.0"
        assert compiled.metadata is not None
        assert compiled.compute is not None
        assert len(compiled.transforms) > 0

    @pytest.mark.requirement("001-FR-009")
    def test_minimal_artifact_has_defaults(self) -> None:
        """Minimal artifact uses model defaults correctly."""
        artifact_data = load_golden_artifact("v1.0.0", "minimal.json")
        compiled = CompiledArtifacts.model_validate(artifact_data)

        # These should use defaults
        assert compiled.dbt_profiles_path == ".floe/profiles"
        assert compiled.consumption.enabled is False
        assert compiled.governance.classification_source == "dbt_meta"
        assert compiled.observability.traces is True

    @pytest.mark.requirement("001-FR-009")
    def test_full_artifact_has_all_fields(self) -> None:
        """Full artifact has all optional fields populated."""
        artifact_data = load_golden_artifact("v1.0.0", "full.json")
        compiled = CompiledArtifacts.model_validate(artifact_data)

        # All optional fields should be populated
        assert compiled.catalog is not None
        assert compiled.environment_context is not None
        assert compiled.column_classifications is not None
        assert compiled.lineage_namespace is not None
        assert compiled.dbt_manifest_path is not None

    @pytest.mark.requirement("001-FR-009")
    def test_artifact_is_immutable(self) -> None:
        """Compiled artifacts are immutable (frozen)."""
        artifact_data = load_golden_artifact("v1.0.0", "minimal.json")
        compiled = CompiledArtifacts.model_validate(artifact_data)

        with pytest.raises(Exception):  # ValidationError for frozen model
            compiled.version = "2.0.0"  # type: ignore[misc]

    @pytest.mark.requirement("001-FR-009")
    def test_artifact_rejects_extra_fields(self) -> None:
        """Artifacts with extra fields are rejected."""
        artifact_data = load_golden_artifact("v1.0.0", "minimal.json")
        artifact_data["unexpected_field"] = "should fail"

        with pytest.raises(Exception):  # ValidationError for extra="forbid"
            CompiledArtifacts.model_validate(artifact_data)


class TestGoldenArtifactRoundTrip:
    """Test JSON serialization round-trip for golden artifacts."""

    @pytest.mark.requirement("001-FR-022")
    @pytest.mark.parametrize("artifact_name", list_artifacts("v1.0.0"))
    def test_json_round_trip(self, artifact_name: str) -> None:
        """Artifacts survive JSON serialization round-trip."""
        artifact_data = load_golden_artifact("v1.0.0", artifact_name)

        # Load, serialize, deserialize
        compiled = CompiledArtifacts.model_validate(artifact_data)
        json_str = compiled.model_dump_json()
        reloaded = CompiledArtifacts.model_validate_json(json_str)

        # Should be equivalent
        assert reloaded.version == compiled.version
        assert reloaded.compute.target == compiled.compute.target
        assert len(reloaded.transforms) == len(compiled.transforms)

    @pytest.mark.requirement("001-FR-022")
    def test_json_schema_exists(self) -> None:
        """JSON Schema file exists for v1.0.0."""
        schema_path = (
            GOLDEN_ARTIFACTS_DIR.parent / "schemas" / "compiled_artifacts.v1.0.0.schema.json"
        )
        assert schema_path.exists(), f"Schema file missing: {schema_path}"

        # Schema should be valid JSON
        with schema_path.open() as f:
            schema = json.load(f)

        assert "$defs" in schema
        assert "properties" in schema


class TestGoldenArtifactSpecificValues:
    """Test specific field values in golden artifacts.

    These tests verify that the golden artifacts contain the expected
    values for key fields, serving as regression tests.
    """

    @pytest.mark.requirement("001-FR-011")
    def test_minimal_compute_target(self) -> None:
        """Minimal artifact has duckdb target."""
        artifact_data = load_golden_artifact("v1.0.0", "minimal.json")
        compiled = CompiledArtifacts.model_validate(artifact_data)

        assert compiled.compute.target.value == "duckdb"
        assert compiled.compute.properties.get("path") == ":memory:"

    @pytest.mark.requirement("001-FR-011")
    def test_production_compute_target(self) -> None:
        """Production artifact has snowflake target."""
        artifact_data = load_golden_artifact("v1.0.0", "production.json")
        compiled = CompiledArtifacts.model_validate(artifact_data)

        assert compiled.compute.target.value == "snowflake"
        assert compiled.compute.connection_secret_ref == "snowflake-prod-creds"

    @pytest.mark.requirement("001-FR-011")
    def test_docker_integration_hostnames(self) -> None:
        """Docker integration artifact uses Docker network hostnames."""
        artifact_data = load_golden_artifact("v1.0.0", "docker_integration.json")
        compiled = CompiledArtifacts.model_validate(artifact_data)

        # Docker hostnames (no localhost)
        assert compiled.catalog is not None
        assert "polaris:8181" in compiled.catalog.uri
        assert compiled.observability.otlp_endpoint == "http://jaeger:4317"
        assert compiled.observability.lineage_endpoint == "http://marquez:5001"

    @pytest.mark.requirement("001-FR-011")
    def test_full_classifications_structure(self) -> None:
        """Full artifact has properly structured classifications."""
        artifact_data = load_golden_artifact("v1.0.0", "full.json")
        compiled = CompiledArtifacts.model_validate(artifact_data)

        assert compiled.column_classifications is not None
        assert "customers" in compiled.column_classifications
        assert "email" in compiled.column_classifications["customers"]

        email_class = compiled.column_classifications["customers"]["email"]
        assert email_class.classification == "pii"
        assert email_class.pii_type == "email"
        assert email_class.sensitivity == "high"


class TestVersionListing:
    """Test version and artifact listing utilities."""

    def test_list_versions(self) -> None:
        """List available versions."""
        versions = list_versions()
        assert "v1.0.0" in versions

    def test_list_artifacts(self) -> None:
        """List artifacts for a version."""
        artifacts = list_artifacts("v1.0.0")
        assert len(artifacts) == 4
        assert "minimal.json" in artifacts
