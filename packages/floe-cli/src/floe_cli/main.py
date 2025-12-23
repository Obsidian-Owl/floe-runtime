"""CLI entry point for floe-runtime.

T008: Update main.py - LazyGroup implementation

This module defines the main CLI group using LazyGroup pattern
for fast --help performance (< 500ms target).
"""

from __future__ import annotations

import importlib
from typing import Any

import click
import rich_click as rclick

from floe_cli import __version__
from floe_cli.output import set_no_color

# Configure rich-click for better help formatting
rclick.rich_click.TEXT_MARKUP = "markdown"
rclick.rich_click.SHOW_ARGUMENTS = True
rclick.rich_click.GROUP_ARGUMENTS_OPTIONS = True


class LazyGroup(rclick.RichGroup):
    """Click group that loads commands lazily for fast --help performance.

    Commands are only imported when actually invoked, not at import time.
    This ensures 'floe --help' completes in < 500ms even with heavy dependencies.

    Attributes:
        lazy_subcommands: Mapping of command names to module paths.
    """

    def __init__(
        self,
        *args: Any,
        lazy_subcommands: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize LazyGroup.

        Args:
            *args: Positional arguments for parent class.
            lazy_subcommands: Mapping of command name to module path.
                Format: {"validate": "floe_cli.commands.validate.validate"}
            **kwargs: Keyword arguments for parent class.
        """
        super().__init__(*args, **kwargs)
        self.lazy_subcommands: dict[str, str] = lazy_subcommands or {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        """Return list of available command names.

        Args:
            ctx: Click context.

        Returns:
            Sorted list of command names.
        """
        # Combine lazy commands with any directly registered commands
        commands = set(super().list_commands(ctx))
        commands.update(self.lazy_subcommands.keys())
        return sorted(commands)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Get a command by name, loading lazily if needed.

        Args:
            ctx: Click context.
            cmd_name: Name of the command to get.

        Returns:
            Click Command instance, or None if not found.
        """
        # First try directly registered commands
        cmd = super().get_command(ctx, cmd_name)  # type: ignore[arg-type]
        if cmd is not None:
            return cmd

        # Then try lazy loading
        if cmd_name not in self.lazy_subcommands:
            return None

        module_path = self.lazy_subcommands[cmd_name]
        module_name, attr_name = module_path.rsplit(".", 1)
        mod = importlib.import_module(module_name)
        return getattr(mod, attr_name)  # type: ignore[no-any-return]


# Define lazy command mappings
LAZY_COMMANDS = {
    "validate": "floe_cli.commands.validate.validate",
    "compile": "floe_cli.commands.compile.compile_cmd",
    "init": "floe_cli.commands.init.init",
    "run": "floe_cli.commands.run.run",
    "dev": "floe_cli.commands.dev.dev",
    "schema": "floe_cli.commands.schema.schema",
    "preflight": "floe_cli.commands.preflight.preflight",
    "platform": "floe_cli.commands.platform.platform",
}


@click.command(cls=LazyGroup, lazy_subcommands=LAZY_COMMANDS)
@click.version_option(version=__version__, prog_name="floe")
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    help="Disable colored output.",
    is_eager=True,
    expose_value=False,
    callback=lambda ctx, param, value: set_no_color(value) if value else None,
)
def cli() -> None:
    """Floe Runtime - Open-Source Data Execution Layer.

    Validate, compile, and run data pipelines with floe.yaml configuration.

    **Getting Started:**

    - `floe init` - Create a new floe project
    - `floe validate` - Validate your configuration
    - `floe compile` - Generate pipeline artifacts
    - `floe schema export` - Export JSON Schema for IDE support

    **Learn More:**

    - Documentation: https://github.com/your-org/floe-runtime
    - Report issues: https://github.com/your-org/floe-runtime/issues
    """
    pass


if __name__ == "__main__":
    cli()
