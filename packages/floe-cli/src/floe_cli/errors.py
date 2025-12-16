"""CLI error handling for floe-cli.

T007: Implement errors.py - CLI error handling

This module provides CLI-specific error handling that wraps
floe-core exceptions and provides user-friendly messages
with appropriate exit codes.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, NoReturn

import click
from pydantic import ValidationError as PydanticValidationError

from floe_cli.output import error

if TYPE_CHECKING:
    from pydantic_core import ErrorDetails


# Exit codes following sysexits.h convention
EXIT_SUCCESS = 0
EXIT_USER_ERROR = 1  # User error (validation, missing file)
EXIT_SYSTEM_ERROR = 2  # System error (permissions, write failure)


class CLIError(click.ClickException):
    """CLI-specific exception with exit code support.

    This exception provides user-friendly error messages
    and appropriate exit codes for CLI usage.

    Attributes:
        message: User-facing error message.
        exit_code: Exit code for the CLI (default: 1).
    """

    def __init__(self, message: str, exit_code: int = EXIT_USER_ERROR) -> None:
        """Initialize CLIError.

        Args:
            message: User-facing error message.
            exit_code: Exit code for the CLI.
        """
        super().__init__(message)
        self.exit_code = exit_code

    def show(self, file: object = None) -> None:
        """Display the error message using Rich formatting.

        Args:
            file: Output file (unused, for Click compatibility).
        """
        error(self.format_message())


def format_pydantic_error(err: PydanticValidationError) -> str:
    """Format Pydantic validation error into user-friendly message.

    Args:
        err: Pydantic ValidationError instance.

    Returns:
        Formatted error message with field paths and issues.

    Example:
        >>> format_pydantic_error(err)
        "Validation failed:\\n  - compute.target: Input should be 'duckdb'..."
    """
    errors: list[ErrorDetails] = err.errors()
    lines = ["Validation failed:"]

    for e in errors:
        # Build field path (e.g., "compute.target")
        loc = ".".join(str(x) for x in e["loc"])
        msg = e["msg"]
        lines.append(f"  - {loc}: {msg}")

    return "\n".join(lines)


def handle_yaml_error(err: Exception, file_path: str) -> NoReturn:
    """Handle YAML parsing errors with line number information.

    Args:
        err: YAML parsing exception.
        file_path: Path to the file being parsed.

    Raises:
        CLIError: Always raises with formatted error message.
    """
    # yaml.YAMLError has mark attribute with line info
    error_msg = str(err)
    if hasattr(err, "problem_mark") and err.problem_mark is not None:
        mark = err.problem_mark
        line = mark.line + 1
        col = mark.column + 1
        error_msg = f"YAML syntax error at line {line}, column {col}: {err.problem}"  # type: ignore[attr-defined]

    raise CLIError(f"Invalid YAML in {file_path}: {error_msg}")


def handle_validation_error(err: PydanticValidationError, file_path: str) -> NoReturn:
    """Handle Pydantic validation errors with user-friendly messages.

    Args:
        err: Pydantic ValidationError instance.
        file_path: Path to the file being validated.

    Raises:
        CLIError: Always raises with formatted error message.
    """
    formatted = format_pydantic_error(err)
    raise CLIError(f"Invalid configuration in {file_path}:\n{formatted}")


def handle_file_not_found(file_path: str) -> NoReturn:
    """Handle file not found errors with helpful suggestions.

    Args:
        file_path: Path to the missing file.

    Raises:
        CLIError: Always raises with formatted error message.
    """
    raise CLIError(
        f"File not found: {file_path}\n\n"
        "Run 'floe init' to create a new project, or use --file to specify a path.",
        exit_code=EXIT_SYSTEM_ERROR,
    )


def handle_permission_error(path: str, operation: str = "access") -> NoReturn:
    """Handle permission errors.

    Args:
        path: Path that caused the permission error.
        operation: Operation that failed (read, write, etc.).

    Raises:
        CLIError: Always raises with formatted error message.
    """
    raise CLIError(
        f"Permission denied: Cannot {operation} {path}",
        exit_code=EXIT_SYSTEM_ERROR,
    )


def exit_with_error(message: str, exit_code: int = EXIT_USER_ERROR) -> NoReturn:
    """Exit the CLI with an error message.

    Args:
        message: Error message to display.
        exit_code: Exit code for the CLI.

    Note:
        This function never returns - it always calls sys.exit().
    """
    error(message)
    sys.exit(exit_code)
