"""Rich console output utilities for floe-cli.

T006: Implement output.py - Rich console output utilities

This module provides formatted console output with Rich,
supporting colored success/error/warning messages and
respecting NO_COLOR environment variable.
"""

from __future__ import annotations

import os
from typing import Any

from rich.console import Console

# Detect color settings
# Rich automatically respects NO_COLOR, but we also support --no-color flag
_force_no_color = os.environ.get("NO_COLOR") is not None


def create_console(no_color: bool = False) -> Console:
    """Create a Rich Console instance with appropriate color settings.

    Args:
        no_color: If True, disable colored output. Also respects NO_COLOR env var.

    Returns:
        Configured Console instance.
    """
    force_terminal = None
    if no_color or _force_no_color:
        force_terminal = False
    return Console(force_terminal=force_terminal, no_color=no_color or _force_no_color)


# Default console instance
console = create_console()


def success(message: str, **kwargs: Any) -> None:
    """Print a success message with green checkmark.

    Args:
        message: The message to display.
        **kwargs: Additional arguments passed to console.print().

    Example:
        >>> success("Configuration valid")
        ✓ Configuration valid
    """
    console.print(f"[green]✓[/green] {message}", **kwargs)


def error(message: str, **kwargs: Any) -> None:
    """Print an error message with red X.

    Args:
        message: The error message to display.
        **kwargs: Additional arguments passed to console.print().

    Example:
        >>> error("Validation failed: missing 'name' field")
        ✗ Validation failed: missing 'name' field
    """
    console.print(f"[red]✗[/red] {message}", **kwargs)


def warning(message: str, **kwargs: Any) -> None:
    """Print a warning message with yellow triangle.

    Args:
        message: The warning message to display.
        **kwargs: Additional arguments passed to console.print().

    Example:
        >>> warning("Deprecated option '--old-flag'")
        ⚠ Deprecated option '--old-flag'
    """
    console.print(f"[yellow]⚠[/yellow] {message}", **kwargs)


def info(message: str, **kwargs: Any) -> None:
    """Print an informational message.

    Args:
        message: The message to display.
        **kwargs: Additional arguments passed to console.print().

    Example:
        >>> info("Compiling configuration...")
        Compiling configuration...
    """
    console.print(message, **kwargs)


def print_json(data: dict[str, Any], **kwargs: Any) -> None:
    """Print JSON data with syntax highlighting.

    Args:
        data: Dictionary to print as JSON.
        **kwargs: Additional arguments passed to console.print_json().

    Example:
        >>> print_json({"name": "test", "version": "1.0.0"})
        {
          "name": "test",
          "version": "1.0.0"
        }
    """
    import json

    console.print_json(json.dumps(data), **kwargs)


def set_no_color(no_color: bool) -> None:
    """Update the global console to enable/disable colors.

    Args:
        no_color: If True, disable colored output.

    Note:
        This updates the module-level console instance.
    """
    global console
    console = create_console(no_color=no_color)
