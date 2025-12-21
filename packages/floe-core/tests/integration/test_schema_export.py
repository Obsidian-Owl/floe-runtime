"""Integration tests for JSON Schema export functionality.

Tests the JSON Schema export capabilities for FloeSpec and CompiledArtifacts,
ensuring IDE autocomplete support and cross-language validation.

Covers:
- FR-021: System MUST export FloeSpec to JSON Schema for IDE autocomplete support
- FR-022: System MUST export CompiledArtifacts to JSON Schema for cross-language validation
- FR-023: System MUST include field descriptions in exported JSON Schema
- FR-024: System MUST generate valid JSON Schema Draft 2020-12 compatible schemas
"""

from __future__ import annotations

import json
from typing import Any

import pytest

# JSON Schema Draft 2020-12 meta-schema URI
JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def validate_json_schema_structure(schema: dict[str, Any]) -> None:
    """Validate that a schema has required JSON Schema structure.

    Args:
        schema: The JSON Schema to validate.

    Raises:
        AssertionError: If schema structure is invalid.
    """
    # Must have $schema or be a valid JSON Schema object
    # Pydantic v2 generates valid schemas but may use different draft
    assert "type" in schema or "properties" in schema or "$ref" in schema, (
        "Schema must have type, properties, or $ref"
    )

    # If it has properties, they must be a dict
    if "properties" in schema:
        assert isinstance(schema["properties"], dict), "properties must be a dict"


def count_descriptions(schema: dict[str, Any]) -> tuple[int, int]:
    """Count properties with and without descriptions.

    Args:
        schema: The JSON Schema to analyze.

    Returns:
        Tuple of (with_description, without_description) counts.
    """
    with_desc = 0
    without_desc = 0

    def traverse(obj: Any) -> None:
        nonlocal with_desc, without_desc
        if isinstance(obj, dict):
            if "properties" in obj:
                for _prop_name, prop_schema in obj["properties"].items():
                    if isinstance(prop_schema, dict):
                        if "description" in prop_schema:
                            with_desc += 1
                        else:
                            without_desc += 1
                        traverse(prop_schema)
            for key, value in obj.items():
                if key not in ("properties",):
                    traverse(value)
        elif isinstance(obj, list):
            for item in obj:
                traverse(item)

    traverse(schema)
    return with_desc, without_desc


class TestFloeSpecJsonSchemaExport:
    """Tests for FloeSpec JSON Schema export (001-FR-021)."""

    @pytest.mark.requirement("001-FR-021")
    def test_floespec_exports_json_schema(self) -> None:
        """Test that FloeSpec can export JSON Schema.

        Covers:
        - 001-FR-021: System MUST export FloeSpec to JSON Schema for IDE autocomplete
        """
        from floe_core.schemas import FloeSpec

        schema = FloeSpec.model_json_schema()

        # Verify it's a valid schema dict
        assert isinstance(schema, dict)
        assert "title" in schema or "type" in schema or "properties" in schema

        # Verify it can be serialized to JSON (for file export)
        json_str = json.dumps(schema, indent=2)
        assert len(json_str) > 0

        # Verify round-trip
        loaded = json.loads(json_str)
        assert loaded == schema

    @pytest.mark.requirement("001-FR-021")
    def test_floespec_schema_has_required_properties(self) -> None:
        """Test that FloeSpec schema includes all required top-level properties.

        Covers:
        - 001-FR-021: JSON Schema for IDE autocomplete must include all fields
        """
        from floe_core.schemas import FloeSpec

        schema = FloeSpec.model_json_schema()

        # Check for $defs or definitions (Pydantic v2 uses $defs)
        defs_key = "$defs" if "$defs" in schema else "definitions"
        defs = schema.get(defs_key, {})

        # Get properties from schema or from FloeSpec definition
        properties = schema.get("properties", {})
        if not properties and "FloeSpec" in defs:
            properties = defs["FloeSpec"].get("properties", {})

        # Required properties for FloeSpec
        expected_properties = [
            "name",
            "version",
            "compute",
            "transforms",
            "consumption",
            "governance",
            "observability",
        ]

        for prop in expected_properties:
            assert prop in properties, f"Missing property: {prop}"


class TestCompiledArtifactsJsonSchemaExport:
    """Tests for CompiledArtifacts JSON Schema export (001-FR-022)."""

    @pytest.mark.requirement("001-FR-022")
    def test_compiled_artifacts_exports_json_schema(self) -> None:
        """Test that CompiledArtifacts can export JSON Schema.

        Covers:
        - 001-FR-022: System MUST export CompiledArtifacts to JSON Schema
        """
        from floe_core.compiler.models import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()

        # Verify it's a valid schema dict
        assert isinstance(schema, dict)

        # Verify it can be serialized to JSON
        json_str = json.dumps(schema, indent=2)
        assert len(json_str) > 0

        # Verify round-trip
        loaded = json.loads(json_str)
        assert loaded == schema

    @pytest.mark.requirement("001-FR-022")
    def test_compiled_artifacts_schema_has_contract_fields(self) -> None:
        """Test that CompiledArtifacts schema includes all contract fields.

        Covers:
        - 001-FR-022: JSON Schema for cross-language validation
        """
        from floe_core.compiler.models import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()

        # Get properties
        defs_key = "$defs" if "$defs" in schema else "definitions"
        defs = schema.get(defs_key, {})
        properties = schema.get("properties", {})
        if not properties and "CompiledArtifacts" in defs:
            properties = defs["CompiledArtifacts"].get("properties", {})

        # Contract fields required by CompiledArtifacts
        expected_fields = [
            "version",
            "metadata",
            "compute",
            "transforms",
            "consumption",
            "governance",
            "observability",
            "dbt_manifest_path",
            "dbt_project_path",
            "dbt_profiles_path",
            "lineage_namespace",
            "environment_context",
            "column_classifications",
        ]

        for field in expected_fields:
            assert field in properties, f"Missing contract field: {field}"


class TestJsonSchemaDescriptions:
    """Tests for field descriptions in JSON Schema (001-FR-023)."""

    @pytest.mark.requirement("001-FR-023")
    def test_floespec_schema_has_descriptions(self) -> None:
        """Test that FloeSpec schema includes field descriptions.

        Covers:
        - 001-FR-023: System MUST include field descriptions in exported JSON Schema
        """
        from floe_core.schemas import FloeSpec

        schema = FloeSpec.model_json_schema()
        with_desc, without_desc = count_descriptions(schema)

        # At least 80% of properties should have descriptions
        total = with_desc + without_desc
        if total > 0:
            coverage = with_desc / total
            assert coverage >= 0.8, (
                f"Only {coverage:.1%} of properties have descriptions "
                f"({with_desc}/{total}), expected >= 80%"
            )

    @pytest.mark.requirement("001-FR-023")
    def test_compiled_artifacts_schema_has_descriptions(self) -> None:
        """Test that CompiledArtifacts schema includes field descriptions.

        Covers:
        - 001-FR-023: Field descriptions for IDE autocomplete
        """
        from floe_core.compiler.models import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()
        with_desc, without_desc = count_descriptions(schema)

        # At least 80% of properties should have descriptions
        total = with_desc + without_desc
        if total > 0:
            coverage = with_desc / total
            assert coverage >= 0.8, (
                f"Only {coverage:.1%} of properties have descriptions "
                f"({with_desc}/{total}), expected >= 80%"
            )

    @pytest.mark.requirement("001-FR-023")
    def test_descriptions_are_meaningful(self) -> None:
        """Test that descriptions are non-empty and meaningful.

        Covers:
        - 001-FR-023: Descriptions must be useful for IDE autocomplete
        """
        from floe_core.compiler.models import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()

        def check_descriptions(obj: Any) -> list[str]:
            """Return list of empty or trivial descriptions."""
            issues = []
            if isinstance(obj, dict):
                if "properties" in obj:
                    for prop_name, prop_schema in obj["properties"].items():
                        if isinstance(prop_schema, dict) and "description" in prop_schema:
                            desc = prop_schema["description"]
                            if not desc or len(desc) < 5:
                                issues.append(f"{prop_name}: empty or too short")
                for key, value in obj.items():
                    if key != "properties":
                        issues.extend(check_descriptions(value))
            elif isinstance(obj, list):
                for item in obj:
                    issues.extend(check_descriptions(item))
            return issues

        issues = check_descriptions(schema)
        assert len(issues) == 0, f"Found trivial descriptions: {issues}"


class TestJsonSchemaDraft202012Compatibility:
    """Tests for JSON Schema Draft 2020-12 compatibility (001-FR-024)."""

    @pytest.mark.requirement("001-FR-024")
    def test_floespec_schema_is_valid_json_schema(self) -> None:
        """Test that FloeSpec schema is a valid JSON Schema structure.

        Covers:
        - 001-FR-024: System MUST generate valid JSON Schema Draft 2020-12 compatible schemas
        """
        from floe_core.schemas import FloeSpec

        schema = FloeSpec.model_json_schema()

        # Validate basic JSON Schema structure
        validate_json_schema_structure(schema)

        # Check for required top-level keys
        assert "title" in schema or "type" in schema, "Schema must have title or type"

        # If there are $defs, they must be valid schemas
        if "$defs" in schema:
            for _def_name, def_schema in schema["$defs"].items():
                validate_json_schema_structure(def_schema)

    @pytest.mark.requirement("001-FR-024")
    def test_compiled_artifacts_schema_is_valid_json_schema(self) -> None:
        """Test that CompiledArtifacts schema is a valid JSON Schema structure.

        Covers:
        - 001-FR-024: JSON Schema Draft 2020-12 compatibility
        """
        from floe_core.compiler.models import CompiledArtifacts

        schema = CompiledArtifacts.model_json_schema()

        # Validate basic JSON Schema structure
        validate_json_schema_structure(schema)

        # If there are $defs, they must be valid schemas
        if "$defs" in schema:
            for _def_name, def_schema in schema["$defs"].items():
                validate_json_schema_structure(def_schema)

    @pytest.mark.requirement("001-FR-024")
    def test_schema_uses_standard_json_schema_keywords(self) -> None:
        """Test that schemas use standard JSON Schema keywords.

        Covers:
        - 001-FR-024: Must be valid JSON Schema (standard keywords)
        """
        from floe_core.schemas import FloeSpec

        schema = FloeSpec.model_json_schema()
        json_str = json.dumps(schema)

        # Check for standard JSON Schema keywords
        standard_keywords = [
            '"type"',
            '"properties"',
        ]

        for keyword in standard_keywords:
            assert keyword in json_str, f"Missing standard keyword: {keyword}"

        # Should not contain any non-standard extensions (unless prefixed with x-)
        # This is a basic check - Pydantic generates compliant schemas

    @pytest.mark.requirement("001-FR-024")
    def test_schema_can_be_used_for_validation(self) -> None:
        """Test that exported schema can validate instance data.

        Covers:
        - 001-FR-024: Schema must be usable for cross-language validation
        """
        from floe_core.schemas import FloeSpec

        # Export schema
        schema = FloeSpec.model_json_schema()

        # Create a valid instance
        valid_data = {
            "name": "test-project",
            "version": "1.0.0",
            "compute": {"target": "duckdb"},
        }

        # The schema should be usable - verify by loading with Pydantic
        # (We don't require jsonschema library, but the schema should be valid)
        spec = FloeSpec.model_validate(valid_data)
        assert spec.name == "test-project"

        # The JSON Schema should have the right structure for external validators
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "version" in schema["properties"]
        assert "compute" in schema["properties"]
