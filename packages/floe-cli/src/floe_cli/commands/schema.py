"""floe schema command - Export JSON Schema.

T026-T030: Implement schema export command
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from floe_cli.output import error, success


@click.group()
def schema() -> None:
    """Manage JSON Schema for IDE support.

    Export FloeSpec JSON Schema for IDE autocomplete and validation.

    **Commands:**

    - `floe schema export` - Export JSON Schema to file
    """
    pass


@schema.command("export")
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(),
    default="./schemas/floe.schema.json",
    help="Output path [default: ./schemas/floe.schema.json]",
)
def export_schema(output_path: str) -> None:
    """Export FloeSpec JSON Schema.

    Exports the JSON Schema for floe.yaml configuration to enable
    IDE autocomplete and validation.

    Examples:

        floe schema export

        floe schema export --output custom/path/schema.json
    """
    output = Path(output_path)

    try:
        # Import here to avoid heavy imports at CLI startup
        from floe_core import FloeSpec

        # Create output directory
        output.parent.mkdir(parents=True, exist_ok=True)

        # Generate JSON Schema
        json_schema = FloeSpec.model_json_schema()

        # Add $schema and $id metadata
        json_schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        json_schema["$id"] = "https://floe.dev/schemas/floe.schema.json"

        # Write schema
        output.write_text(json.dumps(json_schema, indent=2))

        success(f"Schema exported to {output}")

    except PermissionError:
        error(f"Cannot write to: {output_path}")
        raise SystemExit(2) from None

    except Exception as e:
        error(f"Schema export failed: {e}")
        raise SystemExit(1) from None
