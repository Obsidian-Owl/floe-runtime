"""floe validate command - Validate floe.yaml configuration.

T016-T019: Implement validate command with FloeSpec integration
"""

from __future__ import annotations

from pathlib import Path

import click

from floe_cli.output import error, success


@click.command()
@click.option(
    "-f",
    "--file",
    "file_path",
    type=click.Path(exists=False),
    default="./floe.yaml",
    help="Path to floe.yaml [default: ./floe.yaml]",
)
def validate(file_path: str) -> None:
    """Validate floe.yaml configuration.

    Validates the configuration file against the FloeSpec schema.
    Reports validation errors with field paths and helpful messages.

    Examples:

        floe validate

        floe validate --file path/to/floe.yaml
    """
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        error(f"File not found: {file_path}")
        error("\nRun 'floe init' to create a new project, or use --file to specify a path.")
        raise SystemExit(2)

    try:
        # Import here to avoid heavy imports at CLI startup
        from floe_core import FloeSpec

        FloeSpec.from_yaml(path)
        success("Configuration valid")

    except FileNotFoundError:
        error(f"File not found: {file_path}")
        raise SystemExit(2) from None

    except Exception as e:
        # Handle YAML and validation errors
        from pydantic import ValidationError as PydanticValidationError

        from floe_cli.errors import (
            format_pydantic_error,
            handle_yaml_error,
        )

        if "yaml" in type(e).__module__.lower():
            handle_yaml_error(e, file_path)
        elif isinstance(e, PydanticValidationError):
            formatted = format_pydantic_error(e)
            error(f"Invalid configuration in {file_path}:\n{formatted}")
            raise SystemExit(1) from None
        else:
            error(f"Validation failed: {e}")
            raise SystemExit(1) from None
