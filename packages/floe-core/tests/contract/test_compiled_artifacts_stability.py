"""Contract test for CompiledArtifacts stability.

T039: [US2] Contract test for CompiledArtifacts stability

Tests that CompiledArtifacts maintains backward compatibility and
contract stability for downstream consumers.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest


class TestCompiledArtifactsContractStability:
    """Tests for CompiledArtifacts contract stability."""

    def test_contract_version_exists(self) -> None:
        """Test CompiledArtifacts has version field."""
        from floe_core.compiler import CompiledArtifacts

        # Get schema
        schema = CompiledArtifacts.model_json_schema()

        assert "version" in schema["properties"]

    def test_contract_default_version(self, sample_compiled_artifacts: dict) -> None:
        """Test default contract version is 1.0.0."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(**sample_compiled_artifacts)

        assert artifacts.version == "1.0.0"

    def test_contract_required_fields(self) -> None:
        """Test CompiledArtifacts has required fields.

        In Two-Tier Architecture:
        - compute is OPTIONAL (legacy field, use resolved_profiles)
        - metadata and transforms remain required
        """
        from floe_core.compiler import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()
        required = schema.get("required", [])

        # Core required fields
        assert "metadata" in required
        assert "transforms" in required
        # Note: compute is now optional (Two-Tier: use resolved_profiles instead)

    def test_contract_frozen_immutable(self, sample_compiled_artifacts: dict) -> None:
        """Test contract is frozen (immutable)."""
        from pydantic import ValidationError

        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(**sample_compiled_artifacts)

        with pytest.raises(ValidationError):
            artifacts.version = "2.0.0"  # type: ignore[misc]

    def test_contract_extra_forbid(self, sample_compiled_artifacts: dict) -> None:
        """Test contract rejects unknown fields."""
        from pydantic import ValidationError

        from floe_core.compiler import CompiledArtifacts

        sample_compiled_artifacts["unknown_field"] = "value"

        with pytest.raises(ValidationError) as exc_info:
            CompiledArtifacts(**sample_compiled_artifacts)

        assert "extra_forbidden" in str(exc_info.value)


class TestCompiledArtifactsJSONSchemaExport:
    """Tests for JSON Schema export."""

    def test_json_schema_export(self) -> None:
        """Test CompiledArtifacts exports valid JSON Schema."""
        from floe_core.compiler import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()

        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "type" in schema
        assert schema["type"] == "object"

    def test_json_schema_has_all_fields(self) -> None:
        """Test JSON Schema contains all expected fields."""
        from floe_core.compiler import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()
        properties = schema["properties"]

        expected_fields = [
            "version",
            "metadata",
            "compute",
            "transforms",
            "consumption",
            "governance",
            "observability",
            "catalog",
            "dbt_manifest_path",
            "dbt_project_path",
            "dbt_profiles_path",
            "lineage_namespace",
            "environment_context",
            "column_classifications",
        ]

        for field in expected_fields:
            assert field in properties, f"Missing field: {field}"

    def test_json_schema_is_valid_json(self) -> None:
        """Test JSON Schema can be serialized to JSON."""
        from floe_core.compiler import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()
        json_str = json.dumps(schema)

        # Should be valid JSON
        loaded = json.loads(json_str)
        assert loaded == schema


class TestCompiledArtifactsBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_v1_contract_fields_present(self) -> None:
        """Test v1.0.0 contract fields are present."""
        from floe_core.compiler import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()
        properties = schema["properties"]

        # v1.0.0 core fields
        v1_fields = [
            "version",
            "metadata",
            "compute",
            "transforms",
            "consumption",
            "governance",
            "observability",
        ]

        for field in v1_fields:
            assert field in properties, f"v1 field missing: {field}"

    def test_optional_fields_have_defaults(self, sample_compiled_artifacts_minimal: dict) -> None:
        """Test optional fields have defaults (non-breaking additions)."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(**sample_compiled_artifacts_minimal)

        # Optional fields should have None or default values
        assert artifacts.catalog is None
        assert artifacts.dbt_manifest_path is None
        assert artifacts.dbt_project_path is None
        assert artifacts.lineage_namespace is None
        assert artifacts.environment_context is None
        assert artifacts.column_classifications is None

    def test_deserialize_v1_payload(self) -> None:
        """Test v1.0.0 payload can be deserialized."""
        from floe_core.compiler import CompiledArtifacts

        # Simulated v1.0.0 payload (minimal required fields only)
        v1_payload = {
            "version": "1.0.0",
            "metadata": {
                "compiled_at": datetime.now(timezone.utc).isoformat(),
                "floe_core_version": "0.1.0",
                "source_hash": "abc123",
            },
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            # v1.0.0 uses defaults for these
            "consumption": {"enabled": False},
            "governance": {"classification_source": "dbt_meta"},
            "observability": {"traces": True},
        }

        # Should deserialize without error
        artifacts = CompiledArtifacts.model_validate(v1_payload)

        assert artifacts.version == "1.0.0"
        assert artifacts.compute is not None
        assert artifacts.compute.target.value == "duckdb"


class TestCompiledArtifactsFieldTypes:
    """Tests for field type stability."""

    def test_metadata_structure(self, sample_compiled_artifacts: dict) -> None:
        """Test metadata field structure."""
        from floe_core.compiler import ArtifactMetadata, CompiledArtifacts

        artifacts = CompiledArtifacts(**sample_compiled_artifacts)

        assert isinstance(artifacts.metadata, ArtifactMetadata)
        assert isinstance(artifacts.metadata.compiled_at, datetime)
        assert isinstance(artifacts.metadata.floe_core_version, str)
        assert isinstance(artifacts.metadata.source_hash, str)

    def test_compute_structure(self, sample_compiled_artifacts: dict) -> None:
        """Test compute field structure (legacy field, now optional)."""
        from floe_core.compiler import CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget

        artifacts = CompiledArtifacts(**sample_compiled_artifacts)

        # compute is optional in Two-Tier, but fixture provides it
        assert artifacts.compute is not None
        assert isinstance(artifacts.compute, ComputeConfig)
        assert isinstance(artifacts.compute.target, ComputeTarget)

    def test_transforms_structure(self, sample_compiled_artifacts: dict) -> None:
        """Test transforms field structure."""
        from floe_core.compiler import CompiledArtifacts
        from floe_core.schemas import TransformConfig

        artifacts = CompiledArtifacts(**sample_compiled_artifacts)

        assert isinstance(artifacts.transforms, list)
        assert len(artifacts.transforms) > 0
        assert isinstance(artifacts.transforms[0], TransformConfig)

    def test_consumption_structure(self, sample_compiled_artifacts: dict) -> None:
        """Test consumption field structure."""
        from floe_core.compiler import CompiledArtifacts
        from floe_core.schemas import ConsumptionConfig

        artifacts = CompiledArtifacts(**sample_compiled_artifacts)

        assert isinstance(artifacts.consumption, ConsumptionConfig)
        assert isinstance(artifacts.consumption.enabled, bool)

    def test_governance_structure(self, sample_compiled_artifacts: dict) -> None:
        """Test governance field structure."""
        from floe_core.compiler import CompiledArtifacts
        from floe_core.schemas import GovernanceConfig

        artifacts = CompiledArtifacts(**sample_compiled_artifacts)

        assert isinstance(artifacts.governance, GovernanceConfig)

    def test_observability_structure(self, sample_compiled_artifacts: dict) -> None:
        """Test observability field structure."""
        from floe_core.compiler import CompiledArtifacts
        from floe_core.schemas import ObservabilityConfig

        artifacts = CompiledArtifacts(**sample_compiled_artifacts)

        assert isinstance(artifacts.observability, ObservabilityConfig)


class TestCompiledArtifactsCrossLanguageContract:
    """Tests for cross-language contract validation."""

    def test_json_serialization_stable(self, sample_compiled_artifacts: dict) -> None:
        """Test JSON serialization produces stable output."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(**sample_compiled_artifacts)

        # Serialize multiple times
        json1 = artifacts.model_dump_json()
        json2 = artifacts.model_dump_json()

        # Should be deterministic
        assert json1 == json2

    def test_json_schema_for_validation(self) -> None:
        """Test JSON Schema can be used for external validation."""
        from floe_core.compiler import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()

        # Schema should include title
        assert "title" in schema or "CompiledArtifacts" in str(schema)

        # Should have $defs for nested models
        # (Pydantic v2 puts nested model schemas here)
        if "$defs" in schema:
            assert len(schema["$defs"]) > 0

    def test_json_round_trip_preserves_types(self, sample_compiled_artifacts: dict) -> None:
        """Test JSON round-trip preserves types correctly."""
        from floe_core.compiler import CompiledArtifacts

        original = CompiledArtifacts(**sample_compiled_artifacts)

        # Serialize to JSON string
        json_str = original.model_dump_json()

        # Deserialize
        loaded = CompiledArtifacts.model_validate_json(json_str)

        # Types should be preserved
        assert isinstance(loaded.version, type(original.version))
        # compute is optional in Two-Tier, check before accessing
        assert loaded.compute is not None
        assert original.compute is not None
        assert isinstance(loaded.compute.target, type(original.compute.target))
        assert isinstance(loaded.metadata.compiled_at, type(original.metadata.compiled_at))


# Fixtures for contract tests
@pytest.fixture
def sample_compiled_artifacts() -> dict[str, Any]:
    """Return sample CompiledArtifacts as dict."""
    return {
        "version": "1.0.0",
        "metadata": {
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "floe_core_version": "0.1.0",
            "source_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        "compute": {"target": "duckdb"},
        "transforms": [{"type": "dbt", "path": "./dbt"}],
        "consumption": {"enabled": False},
        "governance": {"classification_source": "dbt_meta"},
        "observability": {"traces": True, "metrics": True, "lineage": True},
    }


@pytest.fixture
def sample_compiled_artifacts_minimal() -> dict[str, Any]:
    """Return minimal CompiledArtifacts (required fields only)."""
    return {
        "metadata": {
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "floe_core_version": "0.1.0",
            "source_hash": "abc123",
        },
        "compute": {"target": "duckdb"},
        "transforms": [{"type": "dbt", "path": "./dbt"}],
        "consumption": {},
        "governance": {},
        "observability": {},
    }
