"""floe dev command - Start development server.

T038-T039: Implement dev command stub (P3)

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
    "-p",
    "--port",
    "port",
    type=int,
    default=3000,
    help="Port for development server [default: 3000]",
)
def dev(file_path: str, port: int) -> None:
    """Start Dagster development server.

    Launches a local Dagster UI for pipeline development and testing.

    **Note**: This command requires the floe-dagster package.

    Examples:

        floe dev

        floe dev --port 3001

        floe dev --file path/to/floe.yaml
    """
    error("floe-dagster not installed.")
    error("")
    error("The 'dev' command requires the floe-dagster package for Dagster development UI.")
    error("")
    error("Install with:")
    error("  pip install floe-dagster")
    error("")
    error("Or add to your dependencies:")
    error('  "floe-dagster"')
    raise SystemExit(2)
