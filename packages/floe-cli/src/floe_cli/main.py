"""CLI entry point for floe-runtime.

This module defines the main CLI group and registers all subcommands.

TODO: Implement per docs/04-building-blocks.md section 3.3
"""

from __future__ import annotations

import click

from floe_cli import __version__


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """Floe Runtime CLI - Build and run data pipelines."""
    pass


# Subcommands will be imported and registered here
# from floe_cli.commands import init, validate, compile, run, dev
