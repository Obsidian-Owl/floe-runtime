"""floe compile command - Generate CompiledArtifacts.

T021-T025: Implement compile command with Compiler integration
"""

from __future__ import annotations

from pathlib import Path

import click

from floe_cli.output import error, success


@click.command("compile")
@click.option(
    "-f",
    "--file",
    "file_path",
    type=click.Path(exists=False),
    default="./floe.yaml",
    help="Path to floe.yaml [default: ./floe.yaml]",
)
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(),
    default=".floe/",
    help="Output directory [default: .floe/]",
)
@click.option(
    "-t",
    "--target",
    "target",
    type=str,
    default=None,
    help="Compute target (must exist in spec)",
)
def compile_cmd(file_path: str, output_path: str, target: str | None) -> None:
    """Generate CompiledArtifacts from floe.yaml.

    Compiles the configuration file into artifacts that can be
    consumed by downstream tools (Dagster, dbt).

    Examples:

        floe compile

        floe compile --output build/artifacts/

        floe compile --target snowflake
    """
    path = Path(file_path)
    output = Path(output_path)

    # Check if file exists
    if not path.exists():
        error(f"File not found: {file_path}")
        error("\nRun 'floe init' to create a new project, or use --file to specify a path.")
        raise SystemExit(2)

    try:
        # Import here to avoid heavy imports at CLI startup
        from floe_core import Compiler, FloeSpec

        # Validate first
        spec = FloeSpec.from_yaml(path)

        # Check target if specified
        if target is not None:
            valid_targets = [spec.compute.target.value]
            if target not in valid_targets:
                error(f"Target not found: {target}")
                error(f"Available targets: {', '.join(valid_targets)}")
                raise SystemExit(1)

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        # Compile (target validation done above, Compiler uses spec's target)
        compiler = Compiler()
        artifacts = compiler.compile(path)

        # Write artifacts
        artifacts_path = output / "compiled_artifacts.json"
        artifacts_path.write_text(artifacts.model_dump_json(indent=2))

        success(f"Compiled to {artifacts_path}")

    except PermissionError:
        error(f"Cannot write to: {output_path}")
        raise SystemExit(2) from None

    except Exception as e:
        from pydantic import ValidationError as PydanticValidationError

        from floe_cli.errors import format_pydantic_error

        if isinstance(e, PydanticValidationError):
            formatted = format_pydantic_error(e)
            error(f"Validation failed:\n{formatted}")
            raise SystemExit(1) from None
        else:
            error(f"Compilation failed: {e}")
            raise SystemExit(1) from None
