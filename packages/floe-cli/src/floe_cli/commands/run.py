"""floe run command - Execute the data pipeline.

T038-T039: Implement run command stub (P3)

Note: This is a stub command. Full implementation requires
the floe-dagster package which is not yet available.
"""

from __future__ import annotations

import click

from floe_cli.output import error


@click.command()
@click.option(
    "-f",
    "--file",
    "file_path",
    type=click.Path(exists=False),
    default="./floe.yaml",
    help="Path to floe.yaml [default: ./floe.yaml]",
)
@click.option(
    "-s",
    "--select",
    "select",
    type=str,
    default=None,
    help="Model selection (dbt-style selector)",
)
def run(file_path: str, select: str | None) -> None:
    """Execute pipeline via Dagster.

    Runs the compiled pipeline using Dagster orchestration.

    **Note**: This command requires the floe-dagster package.

    Examples:

        floe run

        floe run --select my_model

        floe run --file path/to/floe.yaml
    """
    error("floe-dagster not installed.")
    error("")
    error("The 'run' command requires the floe-dagster package for Dagster orchestration.")
    error("")
    error("Install with:")
    error("  pip install floe-dagster")
    error("")
    error("Or add to your dependencies:")
    error('  "floe-dagster"')
    raise SystemExit(2)
