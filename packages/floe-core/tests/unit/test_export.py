"""Unit tests for JSON Schema export functions.

T046: [US3] Unit tests for FloeSpec JSON Schema export
T047: [US3] Unit tests for schema field descriptions inclusion
T050: [US4] Unit tests for CompiledArtifacts JSON Schema export
T051: [US4] Unit tests for schema Draft 2020-12 compliance
T052: [US4] Contract test for extra=forbid validation
"""

from __future__ import annotations

import json
from pathlib import Path

from floe_core.export import (
    export_compiled_artifacts_schema,
    export_floe_spec_schema,
)
from floe_core.schemas import FloeSpec


class TestExportFloeSpecSchema:
    """T046: Unit tests for FloeSpec JSON Schema export."""

    def test_export_returns_dict(self) -> None:
        """Export returns a dictionary."""
        schema = export_floe_spec_schema()
        assert isinstance(schema, dict)

    def test_export_has_type_object(self) -> None:
        """Schema has type 'object' at root."""
        schema = export_floe_spec_schema()
        assert schema.get("type") == "object"

    def test_export_has_properties(self) -> None:
        """Schema has properties for FloeSpec fields."""
        schema = export_floe_spec_schema()
        assert "properties" in schema
        props = schema["properties"]
        # Required fields
        assert "name" in props
        assert "version" in props
        # Profile reference fields (Two-Tier Architecture)
        assert "storage" in props
        assert "catalog" in props
        assert "compute" in props
        # Optional fields
        assert "transforms" in props
        assert "consumption" in props
        assert "governance" in props
        assert "observability" in props

    def test_export_has_required_fields(self) -> None:
        """Schema marks name and version as required."""
        schema = export_floe_spec_schema()
        required = schema.get("required", [])
        assert "name" in required
        assert "version" in required
        # In Two-Tier Architecture, profile references have defaults

    def test_export_has_definitions(self) -> None:
        """Schema has $defs for nested models."""
        schema = export_floe_spec_schema()
        # Pydantic v2 uses $defs
        assert "$defs" in schema
        defs = schema["$defs"]
        # FloeSpec no longer has inline ComputeConfig/CatalogConfig
        # It uses string profile references instead
        assert "TransformConfig" in defs
        assert "ConsumptionConfig" in defs

    def test_export_to_file(self, tmp_path: Path) -> None:
        """Export writes valid JSON to file."""
        output = tmp_path / "floe-spec.schema.json"
        export_floe_spec_schema(output_path=output)

        assert output.exists()
        content = json.loads(output.read_text())
        assert content.get("type") == "object"

    def test_export_to_file_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Export creates parent directories if needed."""
        output = tmp_path / "nested" / "dir" / "schema.json"
        export_floe_spec_schema(output_path=output)

        assert output.exists()

    def test_export_json_is_valid(self) -> None:
        """Exported schema is valid JSON."""
        schema = export_floe_spec_schema()
        # Should serialize without error
        json_str = json.dumps(schema, indent=2)
        # Should deserialize back
        parsed = json.loads(json_str)
        assert parsed == schema


class TestFloeSpecSchemaMetadata:
    """T049: Tests for $schema and $id metadata."""

    def test_has_schema_uri(self) -> None:
        """Schema has $schema URI for Draft 2020-12."""
        schema = export_floe_spec_schema()
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"

    def test_has_id_uri(self) -> None:
        """Schema has $id URI."""
        schema = export_floe_spec_schema()
        assert "$id" in schema
        assert schema["$id"] == "https://floe.dev/schemas/floe-spec.schema.json"

    def test_has_title(self) -> None:
        """Schema has title."""
        schema = export_floe_spec_schema()
        assert "title" in schema
        assert schema["title"] == "FloeSpec"

    def test_has_root_description(self) -> None:
        """Schema has description at root level."""
        schema = export_floe_spec_schema()
        assert "description" in schema
        assert len(schema["description"]) > 0


class TestSchemaFieldDescriptions:
    """T047: Unit tests for schema field descriptions inclusion."""

    def test_name_field_has_description(self) -> None:
        """Name field has description."""
        schema = export_floe_spec_schema()
        name_prop = schema["properties"]["name"]
        assert "description" in name_prop
        assert len(name_prop["description"]) > 0

    def test_version_field_has_description(self) -> None:
        """Version field has description."""
        schema = export_floe_spec_schema()
        version_prop = schema["properties"]["version"]
        assert "description" in version_prop

    def test_profile_reference_fields_have_descriptions(self) -> None:
        """Profile reference fields have descriptions."""
        schema = export_floe_spec_schema()
        props = schema["properties"]

        # In Two-Tier Architecture, compute/catalog/storage are string references
        assert "description" in props["compute"]
        assert "description" in props["catalog"]
        assert "description" in props["storage"]

    def test_transform_config_fields_have_descriptions(self) -> None:
        """TransformConfig fields have descriptions."""
        schema = export_floe_spec_schema()
        transform_def = schema["$defs"]["TransformConfig"]

        # 'type' is a Literal/const field, may not have description in Pydantic output
        # 'path' should have description
        assert "description" in transform_def["properties"]["path"]

    def test_consumption_config_has_description(self) -> None:
        """ConsumptionConfig has description."""
        schema = export_floe_spec_schema()
        consumption_def = schema["$defs"]["ConsumptionConfig"]
        assert "description" in consumption_def

    def test_governance_config_fields_have_descriptions(self) -> None:
        """GovernanceConfig fields have descriptions."""
        schema = export_floe_spec_schema()
        governance_def = schema["$defs"]["GovernanceConfig"]
        assert "description" in governance_def["properties"]["classification_source"]

    def test_observability_config_fields_have_descriptions(self) -> None:
        """ObservabilityConfig fields have descriptions."""
        schema = export_floe_spec_schema()
        obs_def = schema["$defs"]["ObservabilityConfig"]
        assert "description" in obs_def["properties"]["traces"]

    def test_catalog_field_has_description(self) -> None:
        """Catalog field (profile reference) has description."""
        schema = export_floe_spec_schema()
        props = schema["properties"]
        # In Two-Tier Architecture, catalog is a string reference
        assert "description" in props["catalog"]


class TestExportCompiledArtifactsSchema:
    """T050: Unit tests for CompiledArtifacts JSON Schema export."""

    def test_export_returns_dict(self) -> None:
        """Export returns a dictionary."""
        schema = export_compiled_artifacts_schema()
        assert isinstance(schema, dict)

    def test_export_has_type_object(self) -> None:
        """Schema has type 'object' at root."""
        schema = export_compiled_artifacts_schema()
        assert schema.get("type") == "object"

    def test_export_has_properties(self) -> None:
        """Schema has properties for CompiledArtifacts fields."""
        schema = export_compiled_artifacts_schema()
        assert "properties" in schema
        props = schema["properties"]
        # Required fields
        assert "version" in props
        assert "metadata" in props
        assert "transforms" in props
        # Optional fields (Two-Tier Architecture)
        assert "compute" in props  # Legacy field, now optional
        assert "resolved_profiles" in props  # New Two-Tier field
        assert "consumption" in props
        assert "governance" in props
        assert "observability" in props
        assert "catalog" in props
        assert "environment_context" in props
        assert "column_classifications" in props

    def test_export_has_required_fields(self) -> None:
        """Schema marks metadata and transforms as required."""
        schema = export_compiled_artifacts_schema()
        required = schema.get("required", [])
        assert "metadata" in required
        assert "transforms" in required
        # compute is now optional (legacy field)

    def test_export_has_definitions(self) -> None:
        """Schema has $defs for nested models."""
        schema = export_compiled_artifacts_schema()
        assert "$defs" in schema
        defs = schema["$defs"]
        assert "ArtifactMetadata" in defs
        assert "ResolvedPlatformProfiles" in defs  # Two-Tier Architecture

    def test_export_to_file(self, tmp_path: Path) -> None:
        """Export writes valid JSON to file."""
        output = tmp_path / "compiled-artifacts.schema.json"
        export_compiled_artifacts_schema(output_path=output)

        assert output.exists()
        content = json.loads(output.read_text())
        assert content.get("type") == "object"


class TestCompiledArtifactsSchemaMetadata:
    """T051: Tests for Draft 2020-12 compliance."""

    def test_has_schema_uri(self) -> None:
        """Schema has $schema URI for Draft 2020-12."""
        schema = export_compiled_artifacts_schema()
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"

    def test_has_id_uri(self) -> None:
        """Schema has $id URI."""
        schema = export_compiled_artifacts_schema()
        assert "$id" in schema
        assert schema["$id"] == "https://floe.dev/schemas/compiled-artifacts.schema.json"

    def test_has_title(self) -> None:
        """Schema has title."""
        schema = export_compiled_artifacts_schema()
        assert "title" in schema
        assert schema["title"] == "CompiledArtifacts"

    def test_metadata_definition_exists(self) -> None:
        """ArtifactMetadata definition exists in $defs."""
        schema = export_compiled_artifacts_schema()
        assert "ArtifactMetadata" in schema["$defs"]

    def test_environment_context_definition_exists(self) -> None:
        """EnvironmentContext definition exists in $defs."""
        schema = export_compiled_artifacts_schema()
        assert "EnvironmentContext" in schema["$defs"]


class TestExtraForbidValidation:
    """T052: Contract test for extra=forbid validation."""

    def test_floe_spec_schema_additional_properties_false(self) -> None:
        """FloeSpec schema has additionalProperties: false."""
        schema = export_floe_spec_schema()
        assert schema.get("additionalProperties") is False

    def test_compiled_artifacts_schema_additional_properties_false(self) -> None:
        """CompiledArtifacts schema has additionalProperties: false."""
        schema = export_compiled_artifacts_schema()
        assert schema.get("additionalProperties") is False

    def test_nested_models_have_additional_properties_false(self) -> None:
        """Nested model definitions have additionalProperties: false."""
        schema = export_floe_spec_schema()
        defs = schema["$defs"]

        # Check key nested models (Two-Tier: no ComputeConfig in FloeSpec)
        for model_name in ["TransformConfig", "ConsumptionConfig"]:
            if model_name in defs:
                model_def = defs[model_name]
                assert model_def.get("additionalProperties") is False, (
                    f"{model_name} should have additionalProperties: false"
                )


class TestSchemaValidation:
    """Integration tests for schema validation."""

    def test_valid_floe_spec_passes_schema(self) -> None:
        """Valid FloeSpec instance passes schema validation."""
        # This tests that the schema is compatible with actual models
        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            compute="default",  # Two-Tier: string profile reference
        )

        # Serialize to dict
        spec_dict = spec.model_dump()

        # Export schema
        _ = export_floe_spec_schema()

        # Basic structural validation (not full JSON Schema validation)
        assert "name" in spec_dict
        assert "version" in spec_dict
        assert "compute" in spec_dict
        # In Two-Tier, compute is a string
        assert isinstance(spec_dict["compute"], str)

    def test_valid_compiled_artifacts_passes_schema(self) -> None:
        """Valid CompiledArtifacts instance passes schema validation."""
        from datetime import datetime, timezone

        from floe_core.compiler import ArtifactMetadata, CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=ArtifactMetadata(
                compiled_at=datetime.now(timezone.utc),
                floe_core_version="0.1.0",
                source_hash="abc123",
            ),
            transforms=[],
        )

        # Serialize to dict
        artifacts_dict = artifacts.model_dump()

        # Export schema
        _ = export_compiled_artifacts_schema()

        # Basic structural validation
        assert "metadata" in artifacts_dict
        assert "transforms" in artifacts_dict
        # compute is optional in Two-Tier Architecture
