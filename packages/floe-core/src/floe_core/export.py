"""JSON Schema export functions for floe-runtime.

T048: [US3] Implement export_floe_spec_schema() function
T049: [US3] Add $schema and $id metadata to exported schema
T053: [US4] Implement export_compiled_artifacts_schema() function
T054: [US4] Export all export functions from export.py

This module provides functions to export JSON Schema Draft 2020-12 schemas
from Pydantic models for IDE autocomplete and cross-language validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from floe_core.compiler.models import CompiledArtifacts
from floe_core.schemas import FloeSpec


def export_floe_spec_schema(
    output_path: Path | str | None = None,
) -> dict[str, Any]:
    """Export FloeSpec JSON Schema for IDE autocomplete.

    Generates JSON Schema Draft 2020-12 from the FloeSpec Pydantic model,
    suitable for use with VS Code YAML extension and other IDE tools.

    Args:
        output_path: Optional path to write schema file. If provided,
            creates parent directories as needed.

    Returns:
        Dictionary containing the JSON Schema.

    Example:
        >>> schema = export_floe_spec_schema()
        >>> schema["$schema"]
        'https://json-schema.org/draft/2020-12/schema'

        >>> # Export to file
        >>> export_floe_spec_schema(Path("schemas/floe-spec.schema.json"))
    """
    # Generate schema from Pydantic model
    schema = FloeSpec.model_json_schema()

    # Add JSON Schema Draft 2020-12 metadata
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://floe.dev/schemas/floe-spec.schema.json"

    # Ensure additionalProperties is set at root level
    if "additionalProperties" not in schema:
        schema["additionalProperties"] = False

    # Write to file if path provided
    if output_path is not None:
        _write_schema_file(schema, output_path)

    return schema


def export_compiled_artifacts_schema(
    output_path: Path | str | None = None,
) -> dict[str, Any]:
    """Export CompiledArtifacts JSON Schema for cross-language validation.

    Generates JSON Schema Draft 2020-12 from the CompiledArtifacts Pydantic model,
    suitable for validation in Go, TypeScript, and other languages.

    Args:
        output_path: Optional path to write schema file. If provided,
            creates parent directories as needed.

    Returns:
        Dictionary containing the JSON Schema.

    Example:
        >>> schema = export_compiled_artifacts_schema()
        >>> schema["title"]
        'CompiledArtifacts'

        >>> # Export to file
        >>> export_compiled_artifacts_schema(Path("schemas/compiled-artifacts.schema.json"))
    """
    # Generate schema from Pydantic model
    schema = CompiledArtifacts.model_json_schema()

    # Add JSON Schema Draft 2020-12 metadata
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://floe.dev/schemas/compiled-artifacts.schema.json"

    # Ensure additionalProperties is set at root level
    if "additionalProperties" not in schema:
        schema["additionalProperties"] = False

    # Write to file if path provided
    if output_path is not None:
        _write_schema_file(schema, output_path)

    return schema


def _write_schema_file(schema: dict[str, Any], path: Path | str) -> None:
    """Write schema to JSON file.

    Args:
        schema: Schema dictionary to write.
        path: Output file path.
    """
    output_path = Path(path)

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with pretty formatting
    output_path.write_text(json.dumps(schema, indent=2))
